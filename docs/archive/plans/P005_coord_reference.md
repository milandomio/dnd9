# P005: 坐标引用机制 — 消除掉落页坐标重复

## 问题

掉落详情页（lootdrops）内联了完整的坐标数据，导致大量重复：

| 指标 | 数值 |
|------|------|
| lootdrops 目录总大小 | **1,725 MB** |
| 重复坐标条目数 | **2,692,257** |
| 涉及文件数 | 6,242 |
| 唯一实体数 | 203 |

**典型案例**: `SpectralFabric.json` = 390 KB，其中 `CofferSmall` 的 1080 个坐标占 351 KB。而 `CofferSmall` 的坐标已在 `/props/CofferSmall.json`（287 KB）中存在。

**Top 5 重复实体**:

| 实体 | 总坐标数 | 出现文件数 |
|------|---------|-----------|
| SimpleChestSmall | 825,512 | 793 |
| Mimic_Large_Flat | 634,776 | 1,124 |
| SimpleChestMedium | 547,824 | 1,808 |
| FlatChestLarge | 524,760 | 4,465 |
| SimpleChestLarge | 310,671 | 2,847 |

## 目标

- 掉落页坐标数据 100% 通过引用获取，不再内联任何坐标
- 保留掉落页独有的爆率（drop_rates）、生成率（spawn_rate）等信息
- 实际文件体积缩减 **89%**（1,725 MB → 190 MB）
- 前端加载时按需 fetch 引用实体的坐标数据

## 设计

### 核心思路

掉落页的每个 monster 条目改为"引用 + 覆盖"模式：

```jsonc
// 当前 SpectralFabric.json（390 KB）
{
  "name": "SpectralFabric",
  "monsters": [
    {
      "name": "CofferSmall",
      "translation": "迷你宝盒",
      "coords": [/* 1080 个完整坐标 */],  // ← 重复数据
      "drop_rates": {"PVE": 1.5, "普通": 1.5, "豪客赛": 1.5}
    }
  ]
}

// P005 后 SpectralFabric.json（~39 KB）
{
  "name": "SpectralFabric",
  "monsters": [
    {
      "name": "CofferSmall",
      "translation": "迷你宝盒",
      "ref": "props/CofferSmall",        // ← 引用实体坐标
      "drop_rates": {"PVE": 1.5, "普通": 1.5, "豪客赛": 1.5},
      "max_score": 0.045
    }
  ]
}
```

### 引用条件

**所有 monster 条目均使用引用**，无条件、无阈值。

引用来源优先级：
1. **实体页** — `items/`、`monsters/`、`props/` 下的 JSON 文件
2. **坐标文件** — `coords/` 下的独立坐标文件（为没有实体页的实体创建）
3. **别名解析** — 通过 `og_to_keywords` 解析大小写变体（如 `DwarfHandCannoneer` → `DwarfHandcannoneer`）

### 后端改动

**文件**: `api/src/collector.py`

构建 `ENTITY_PAGE_MAP`：
1. 遍历 items/monsters/props 导出结果，记录 `{entity_name: "items/xxx"}` 映射
2. 为没有实体页的实体创建 `coords/{name}.json` 坐标文件
3. 确保 `all_coords` 中的所有 key 都在 `entity_page_map` 中（覆盖大小写变体）

**文件**: `api/src/lootdrop_builder.py`

在 `build_and_save_lootdrop_details()` 中，`monsters_out` 构建完成后、保存 JSON 之前：

```python
# P005: 所有坐标都用 ref，无阈值
if entity_page_map:
    for _m in monsters_out:
        _ck = _m.pop("_coord_key", None)  # 通过别名解析到的实际 coord key
        ref_page = (entity_page_map.get(_ck) if _ck else None) or entity_page_map.get(_m["entity_name"])
        if ref_page:
            _m["ref"] = ref_page
            _m["coord_count"] = len(_m["coords"])
            del _m["coords"]
```

**关键**：`_coord_key` 跟踪坐标解析过程中实际使用的 key（处理大小写变体、别名等），确保 ref 路径正确。

### 前端改动

**文件**: `web/src/pages/LootdropDetailPage.tsx`

修改坐标加载逻辑：

```typescript
// 当前：直接使用 data.monsters[].coords
// P005：检查 ref 字段，按需 fetch 引用实体坐标

interface LootdropMonster {
  name: string;
  translation: string;
  color: string;
  coords?: LootdropCoord[];   // 内联坐标（小数据量）
  ref?: string;                // 引用路径（如 "props/CofferSmall"）
  coord_count?: number;        // 引用时的坐标数量
  drop_rates?: Record<string, number>;
  max_score?: number;
}

// 加载引用坐标
const [refCoords, setRefCoords] = useState<Map<string, LootdropCoord[]>>(new Map());

useEffect(() => {
  const refsToLoad = monsters
    .filter(m => m.ref && !refCoords.has(m.ref))
    .map(m => m.ref!);
  if (refsToLoad.length === 0) return;

  Promise.all(
    refsToLoad.map(ref =>
      fetch(`/data/json/${ref}.json?v=${dataVersion}`)
        .then(r => r.json())
        .then(entity => [ref, entity.coords || []] as const)
    )
  ).then(results => {
    setRefCoords(prev => {
      const next = new Map(prev);
      for (const [ref, coords] of results) next.set(ref, coords);
      return next;
    });
  });
}, [monsters, dataVersion]);

// 合并坐标
const resolvedMonsters = useMemo(() =>
  monsters.map(m => ({
    ...m,
    coords: m.coords ?? refCoords.get(m.ref!) ?? [],
  })),
  [monsters, refCoords]
);
```

### SSG 改动

**文件**: `web/scripts/ssg.mjs`

SSG 渲染时，引用坐标需要预加载以支持 SSR：

```javascript
// 在渲染 lootdrop 详情页前，预加载引用的实体坐标
for (const [key, data] of Object.entries(ssrDataMap)) {
  if (!key.startsWith('lootdrops/')) continue;
  const item = data.item;
  if (!item?.monsters) continue;

  const refCoords = {};
  for (const m of item.monsters) {
    if (!m.ref) continue;
    const refFile = join(DATA, `${m.ref}.json`);
    try {
      const refEntity = readJSON(refFile);
      refCoords[m.ref] = refEntity.coords || [];
    } catch {}
  }
  if (Object.keys(refCoords).length > 0) {
    data._refCoords = refCoords;  // 注入 SSR 数据
  }
}
```

前端 SSR 注水时，从 `window.__SSR_DATA__` 中读取 `_refCoords`，避免客户端重复 fetch。

## 数据流

```
当前:
  掉落页 fetch → SpectralFabric.json (390KB, 含1080个CofferSmall坐标)
  → 直接渲染

P005 后:
  掉落页 fetch → SpectralFabric.json (39KB, ref: "props/CofferSmall")
  → 检测 ref → fetch CofferSmall.json (287KB, 仅首次)
  → 合并坐标 + 爆率 → 渲染

缓存后:
  掉落页 fetch → SpectralFabric.json (39KB)
  → CofferSmall 坐标已缓存 → 直接合并 → 渲染
```

## 带宽分析

**首次加载单个掉落页**:
- 当前: 390 KB（SpectralFabric.json）
- P005: 39 KB + 287 KB = 326 KB（首次），39 KB（后续，CofferSmall 已缓存）

**加载多个掉落页共享同一实体**:
- 当前: 793 个文件 × SimpleChestSmall 坐标 = 793 × ~200 KB 重复传输
- P005: 1 次 SimpleChestSmall.json + 793 次小文件

**总体带宽节省**: 对于频繁浏览多个掉落页的用户，带宽节省显著。对于单页访问，首次加载略有增加（多一次 fetch），但后续访问更快。

## 实现步骤

### Phase 1: 后端生成引用

1. **构建 ENTITY_PAGE_MAP** — `collector.py` 中遍历 items/monsters/props 导出结果
2. **坐标引用优化** — `lootdrop_builder.py` 中保存前替换 coords 为 ref
3. **验证** — 检查生成的 JSON 中 ref 字段正确、坐标数量匹配

### Phase 2: 前端引用加载

4. **LootdropDetailPage 引用加载** — 检测 ref 字段，fetch 引用实体坐标
5. **坐标合并** — 将引用坐标与掉落页爆率/spawn_rate 信息合并
6. **加载状态** — 引用坐标加载中显示 loading 指示

### Phase 3: SSG 预加载

7. **SSG 预加载引用坐标** — 渲染时注入 `_refCoords` 到 SSR 数据
8. **SSR 注水** — 前端从 `__SSR_DATA__` 读取预加载的坐标

### Phase 4: 详情页同步

9. **DetailPage 同步** — items/monsters/props 详情页也支持引用（如果它们引用了其他实体的坐标）
10. **ListPage 适配** — 列表页不需要改动（不加载坐标）

## 风险与缓解

| 风险 | 缓解 |
|------|------|
| 引用实体坐标比掉落页少 | 保存前验证 `cur_set <= ref_set`，不满足则保持内联 |
| 引用实体 JSON 不存在 | try-catch 兜底，回退到内联坐标 |
| 首次加载多一次 fetch | SSG 预加载 + 浏览器缓存 |
| 坐标数据变更不同步 | 引用和被引用数据同一次管道生成，天然同步 |
| 变体页面坐标过滤 | 引用坐标后仍需按 spawner 过滤，逻辑不变 |

## 实际效果

| 指标 | P005 前 | P005 后 | 变化 |
|------|---------|---------|------|
| lootdrops 目录大小 | 1,725 MB | **190 MB** | **-89%** |
| 引用率 | 0% | **100%** | 全量引用 |
| coords/ 目录 | — | 612 KB | 22 个独立坐标文件 |
| 管道构建时间 | ~112s | **~30s** | **-73%** |
| 引用实体数 | 0 | 97,194 | 所有 monster 条目 |

## 已修复问题

### 分类按钮排序失效（阈值错误）

**问题**：变体页面（如 Mitre_6001）错误地应用了神器显示阈值 0.03，导致几乎所有怪物都默认显示，排序效果不明显。

**根因**：`defaultThreshold` 逻辑 `isArtifact || isVariant ? 0.03 : 2.5` 将变体和神器混为一谈。

**修复**：改为 `isArtifact ? 0.03 : 2.5`，只有神器（_8001）使用低阈值，普通变体使用 2.5。

## 后续已修复问题

### 1. 变体爆率计算错误（`drop_rate.py`）

**问题**：变体爆率 fallback 逻辑使用了错误的 `_shared` 除数。

**现象**：
- FrostAmulet_6001 旧锈房-饰品豪客赛=37.5%（实际应为2.895%）
- 根因：rate table 只有 `_5001` items（luck_grade=5），grade 6 fallback 到 `_5001` 时用 luck_grade=6 查 weight（3750），但 `_shared=1`（grade 6 无 items），导致 3750/1/10000=37.5%
- 正确值：weight=5500（grade 5），`_shared=19`（19个 items），5500/19/10000=2.895%

**修复 A**：`compute_variant_rate()` 中 fallback 时始终用 `item_info[0]`（found item 的 luck_grade）覆盖 caller 的 luck_grade。这样 weight 和 `_shared` 使用同一个 grade，结果正确。

**遗留问题**：基础物品（如 `FrostAmulet`，无变体后缀）不应有爆率——它不是一个具体变体，无法锁定。`compute_drop_rate()` fallback 到 `FrostAmulet_5001` 并返回 2.895%，这是错误的。

**决策**：基础物品页（`/lootdrops/FrostAmulet/`）直接重定向到默认变体 `_5001`，不再显示爆率。

**修复 B**：`compute_drop_rate()` 和 `compute_variant_rate()` 中，当 `item_name` 无变体后缀（`_VARIANT_RE` 不匹配，即 `_base is None`）时，跳过追加后缀的 fallback 逻辑。基础物品命中 `rate_items.get(item_name)` 失败后直接 `continue`，返回 0。

**状态**：已修复 → **已回退**。

**回退原因**：基础物品页的 `monsters_out` 依赖 `_group_drop_info`，而 `_group_drop_info` 又依赖 `compute_drop_rate`。如果 base 返回 0，则 `_group_drop_info` 为空 → `monsters_out` 为空 → 基础物品 JSON 不生成 → 依赖 base 的合成变体（`_1001`-`_7001`）也不生成。实际上基础物品页已通过默认重定向 5001 解决了展示问题，爆率错误不会暴露给用户，而 `monsters_out` 必须有完整数据供变体页面派生。

**当前行为**：`compute_drop_rate` 对 `item_name="HeaterShield"` 允许 fallback 到 `HeaterShield_8001`，返回非零值（豪客赛 0.004 等）。变体页面从 base 继承 `monsters_out`，生成正常。

### 2. 变体页面收录无豪客赛爆率怪物

**问题**：变体页面（如 ShortSword_7001）收录了只有 PVE/普通爆率但无豪客赛爆率的怪物。

**修复**：`lootdrop_builder.py` 中 `_group_drop_info` 和 `variant_gdi` 的过滤条件从 `any(rate > 0)` 改为 `豪客赛 > 0`。

**状态**：已修复（确认：所有页面只显示有豪客赛爆率的怪物）。

### 3. 变体 max_score 使用基础物品的值

**问题**：变体页面的 `max_score` 从基础物品的 `_max_scores` 计算，而非变体-specific 的 `variant_gdi`。

**修复**：在保存变体详情前，从 `variant_gdi` 重新计算 `_v_max_scores` 并赋值给 `variant_monsters`。

**状态**：已修复。

### 4. SSG 预加载 coords/ 纯数组文件失败

**问题**：`coords/*.json` 是纯数组 `[{x,y,z,...}]`，非 `{coords:[...]}` 对象。SSG 预加载和前端 fetch 都用 `entity.coords` 读取，导致坐标为空。

**修复**：`Array.isArray(entity) ? entity : (entity.coords || [])`

**影响文件**：`ssg.mjs`、`LootdropDetailPage.tsx`

**状态**：已修复。

### 5. SSG full build OOM

**问题**：预加载所有 ref coords 到 SSR 数据导致内存溢出。

**修复**：`package.json` 中 `build:full` 添加 `NODE_OPTIONS='--max-old-space-size=4096'`

**状态**：已修复（workaround）。

### 6. 默认变体重定向 6001→5001

**问题**：基础物品页（`/lootdrops/FrostAmulet/`）自动跳转到变体页时默认选择 `6001`，但用户期望的默认变体是 `_5001`（史诗）。

**修复**：`LootdropDetailPage.tsx` 中两处 `defaultSuffix` 逻辑从 `data.variant_suffixes.includes('6001') ? '6001' : ...` 改为 `'5001'`。

**影响文件**：`web/src/pages/LootdropDetailPage.tsx`

**状态**：已修复。

## 验证确认：变体页引用的 spawner 过滤无差异

**问题回顾**：检查中发现变体页面使用 ref 后 `coord_count` 在各变体间完全一致，怀疑 ref 跳过了变体 spawner 过滤（`lootdrop_builder.py:674-675`）。

**数据验证**：
- 以 `GoldBangle1I` 为例，游戏数据中 **只有 `_5001` 一个变体**存在 lootdrop_rate_items 中
- 其他后缀（1001-7001）是代码根据 `variant_count` 合成的虚拟变体
- `get_variant_spawners(item_name)` 对非实际存在的变体返回空集 → fallback 到 `base_spawners`
- 所有变体的 `valid_spawners` 集合完全一致

**结论**：同一物品的所有变体共享同一组 spawner，`coord_count` 一致是**正确的预期行为**。ref 未导致数据丢失或页面异常。

> 注意：如果未来游戏数据出现某个物品的不同变体对应不同 spawner（如 `_5001` 只在宝箱、`_6001` 只在怪物掉落），则需要在此处重新评估。

## 文件清单

| 文件 | 改动 |
|------|------|
| `api/src/collector.py` | 构建 ENTITY_PAGE_MAP + 孤儿坐标文件 |
| `api/src/lootdrop_builder.py` | 全量引用（无阈值）+ `_coord_key` 别名追踪 |
| `web/src/pages/LootdropDetailPage.tsx` | 引用坐标加载 + 合并 + SSR 注水 |
| `web/scripts/ssg.mjs` | SSR 预加载引用坐标 |
| `data/json/coords/` | 22 个独立坐标文件（无实体页的实体） |
| ~~`api/src/drop_rate.py`~~ | ~~修复 B~~ 已回退（见上文"修复 B"节） |
| `web/src/pages/LootdropDetailPage.tsx` | 默认重定向 `6001` → `5001`（2 处） |
| `docs/plans/P005_coord_reference.md` | 本计划文件 |
