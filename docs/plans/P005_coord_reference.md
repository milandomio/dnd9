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

- 掉落页坐标数据引用实体页（props/items/monsters）的坐标，不再内联
- 保留掉落页独有的爆率（drop_rates）、生成率（spawn_rate）等信息
- 预估文件体积缩减 **80-90%**
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

只有满足以下条件的 monster 条目才使用引用：

1. **实体页存在** — 该实体在 `props/`、`items/` 或 `monsters/` 下有对应的 JSON 文件
2. **坐标完全一致** — 引用实体的坐标集合 ⊇ 掉落页当前的坐标集合（允许引用页有更多坐标）
3. **坐标数量阈值** — `coords.length > N`（建议 N=50，小数据量内联更简单）

不满足条件的条目保持内联坐标（向后兼容）。

### 后端改动

**文件**: `api/src/lootdrop_builder.py`

在 `build_and_save_lootdrop_details()` 中，`monsters_out` 构建完成后、保存 JSON 之前：

```python
# 引用优化：用 ref 替代内联 coords
ENTITY_PAGE_MAP = {}  # {entity_name: "props/xxx"} — 由 collector 构建

for _m in monsters_out:
    entity_name = _m["name"]
    ref_page = ENTITY_PAGE_MAP.get(entity_name)
    if ref_page and len(_m["coords"]) > 50:
        # 验证引用实体的坐标覆盖当前坐标
        ref_coords = all_coords.get(entity_name, [])
        ref_set = {(c["x"], c["y"], c["z"]) for c in ref_coords}
        cur_set = {(c["x"], c["y"], c["z"]) for c in _m["coords"]}
        if cur_set <= ref_set:
            _m["ref"] = ref_page
            _m["coord_count"] = len(_m["coords"])  # 保留数量用于 UI 显示
            del _m["coords"]
```

**文件**: `api/src/collector.py`

构建 `ENTITY_PAGE_MAP`：遍历 items/monsters/props 的导出结果，记录 `{entity_name: "items/xxx"}` 映射。

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

## 预估效果

| 指标 | 当前 | P005 后 |
|------|------|---------|
| lootdrops 目录大小 | 1,725 MB | ~200-400 MB |
| 单页平均大小 | ~750 KB | ~50-100 KB |
| 首次加载带宽 | 中等 | 略增（多 fetch） |
| 后续加载带宽 | 不变 | 显著减少 |
| 构建时间 | 不变 | 略增（坐标验证） |

## 文件清单

| 文件 | 改动 |
|------|------|
| `api/src/collector.py` | 构建 ENTITY_PAGE_MAP，传递给 lootdrop_builder |
| `api/src/lootdrop_builder.py` | 保存前替换 coords 为 ref |
| `web/src/pages/LootdropDetailPage.tsx` | 引用坐标加载 + 合并 |
| `web/scripts/ssg.mjs` | SSR 预加载引用坐标 |
| `docs/plans/P005_coord_reference.md` | 本计划文件 |
