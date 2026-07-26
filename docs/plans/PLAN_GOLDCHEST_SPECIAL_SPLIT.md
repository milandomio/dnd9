# 黄金宝箱(特殊) 拆成独立 props 页

> 日期: 2026-07-26  
> 状态: **已完成**  
> 关联: `docs/PLAN_CONTAINER_GENERATOR_ENTITIES.md`（P002 降级仅做 gdi↔monsters 图例对齐，**未**解决 props 坐标混装与 100% 误赋）

## 1. 问题

用户在 `/zh-Hans/props/GoldChest/` 看到类似：

```text
(海底)黄金宝箱(特殊) 17.5%[PVE:72.1365%][普通:99.9977%][豪客赛:100%][逆袭赛:100%]
```

该条目**已在 `group_drop_info` 中单独列出且 spawn_rate=17.5 正确**，但：

1. **坐标未拆**：`props/GoldChest.json` 仍混装全部点  
   - `GoldChest` ×50（direct，100%）  
   - `ChestSpecial_UnderSea` ×32（special，17.5%）  
   - `GoldChest__UnderSea` ×5（other/组，100%）  
2. **前端只有一页**：图例/地图无法像「宝藏堆 / 超级宝藏堆」那样点进独立实体  
3. **lootdrop 引用污染**：`黄金宝箱` 使用 `ref: props/GoldChest` 时，P005 会拉回**整页 87 点**，special 点被重新混入「黄金宝箱」；或 virtual 条目 `ref: coords/GoldChest_UnderSea` 无完整 props 语义  
4. **CourtlyDress_7001** 等页看不到干净的「黄金宝箱(特殊)」分类按钮/刷点，根因是实体层未拆，不是前端滤镜 alone

对照（期望模型）：

| 实体 | 页面 | 关系 |
|------|------|------|
| `Hoard01` | `props/Hoard01` | 宝藏堆 |
| `SuperHoard01_9` | `props/SuperHoard01_9` | 超级宝藏堆（**另一实体名**，独立导出） |
| `GoldChest`（现状） | `props/GoldChest` | direct+special+组 **混装** |
| `GoldChest`（目标） | `props/GoldChest` | **仅** direct |
| `GoldChest_special`（目标） | `props/GoldChest_special` | **仅** Special 生成器点，sr=17.5 |

> SuperHoard 在游戏数据里就是独立 keyword；GoldChest special 是 **同一展示名下的 label 分类**，需在导出阶段做**合成实体**（类似合成 key，但落盘为独立 props 文件）。

## 2. 目标

1. 将「黄金宝箱(特殊)」拆成独立 props 详情页（用户命名约定：`/zh-Hans/props/GoldChest_special/`）。  
2. 主页 `GoldChest` **不再包含** special 坐标；gdi 中 special 条目只属于 special 页（或主页 gdi 不再展示 special 行）。  
3. lootdrop 中「黄金宝箱(特殊)」的 `ref` 指向 `props/GoldChest_special`（或等价路径），**禁止**再 ref 整页 `props/GoldChest`。  
4. special 页 spawn_rate / 参考爆率保持 **17.5% × 各模式 drop_rates**，不得 fallback 成 GoldChest 的 100%。  
5. 列表 `props.json` 出现该合成实体（与 SuperHoard 可搜、可进详情一致）。

**非目标（本计划不做或后置）**：

- 全量容器生成器（Goblin*_Random、Ore_*Random 等）一次拆完（可复用同一管道，但首期只做 GoldChest 验证）  
- 改 DB schema / 虚拟 spawner 表  
- 前端大改（尽量零改：独立 JSON + 现有 DetailPage 路由即可）

## 3. 根因（架构）

```
all_coords["GoldChest"]  ← 含多种 original_keyword / label
        │
        ├─ export_props：按 asset 名整包写入 props/GoldChest.json
        ├─ enrichment：按 label 类型写入多条 gdi（翻译已拆，坐标未拆）
        └─ lootdrop_builder：_classify_label 拆 translation，
             但 P005 ref 回 props/GoldChest 又把 special 坐标灌回「黄金宝箱」
```

P002 降级只保证 lootdrop JSON 里 gdi 翻译在 `monsters` 有条目，**不能**修正「ref 整页混坐标」和「props 页混装」。

## 4. 方案

### 4.1 合成实体命名（推荐）

| 合成 name | 坐标来源（label / original_keyword） | 展示名（zh） | translation_key 策略 |
|-----------|--------------------------------------|--------------|----------------------|
| `GoldChest` | `GoldChest`（及非 Special、非组） | 黄金宝箱 | 现有 `Text_DesignData_Props_Props_GoldenChest` |
| `GoldChest_special` | `ChestSpecial`、`ChestSpecial_UnderSea` 等含 `Special` 的生成器 label，且实体解析为 GoldChest / GoldChest_UnderSea | 黄金宝箱(特殊) | 复用同一 key + 后缀展示，或 `df5.hardcoded.GoldChest_special`（若多语言要干净后缀再定） |
| （可选后续）`GoldChest_group` | `GoldChest__UnderSea` 等 other/组 | 黄金宝箱组 / (海底)黄金宝箱组 | 同期或二期 |

**URL**：`/zh-Hans/props/GoldChest_special/`（与用户要求一致；不用 `GoldChest_UnderSea` 当 special 页，因 UnderSea 还混 100% 的 `GoldChest__UnderSea` 点）。

**不采用**：仅改前端过滤、不落盘独立 JSON——lootdrop ref 与 SSG 仍会踩整页。

### 4.2 数据管道改动点

| 步骤 | 文件 | 动作 |
|------|------|------|
| A. 坐标拆分 | `entity_export.export_props` 或 collector 在 export 前预处理 `all_coords` | 从 `GoldChest`（及必要时 `GoldChest_UnderSea`）抽出 special label → 写入 `all_coords["GoldChest_special"]`；从 GoldChest 删除这些点 |
| B. 实体注册 | `module_builder` / props 导出列表 | 将 `GoldChest_special` 注入 props 索引（仿 SuperHoard 注入 `entity_class`） |
| C. 落盘 | `export_props` + `entity_page_map` | 生成 `props/GoldChest_special.json`；`entity_page_map["GoldChest_special"]="props/GoldChest_special"`；coords 兜底页不再作为 lootdrop 主 ref |
| D. enrichment | `enrichment.py` props 段 | special 页 gdi 只含 special 条目（sr=17.5）；GoldChest 页 gdi **去掉** `(海底)黄金宝箱(特殊)` 行，避免一页三套文案叠坐标 |
| E. lootdrop | `lootdrop_builder.py` | 「黄金宝箱(特殊)」优先 `entity_name=GoldChest_special` 或 `ref=props/GoldChest_special`；`_ensure_gdi_monster_entries` / `_resolve_legend_ref` 认合成名；**禁止** special 桶 ref 到 `props/GoldChest` |
| F. 路由 / SSG | 现有 `props/:name` | 合成名落在 props 索引即可被 SSG 扫到；确认 `ssg.mjs` 读 `props.json` 无白名单漏网 |

### 4.3 分类规则（与 lootdrop 对齐）

复用 `lootdrop_builder._classify_label` 语义（可抽到公共模块避免双份）：

- `Special` in label 或 `ChestLarge*` → **special** → `GoldChest_special`  
- `Random` in label → random（本期可不拆页）  
- label 匹配实体 direct → 留在 `GoldChest`  
- 其余 → other/组（二期 `GoldChest_group`）

**关键**：special 桶的 spawn_rate 必须用 `(ChestSpecial_UnderSea, GoldChest_UnderSea)` → **17.5**，禁止对 special 桶用 `spawn_rate_cache["GoldChest"]=100` fallback。

### 4.4 展示文案

| 位置 | 当前 | 目标 |
|------|------|------|
| props/GoldChest gdi | `(海底)黄金宝箱(特殊)` | **删除**该行（坐标已不在本页） |
| props/GoldChest_special | （无页） | 标题「黄金宝箱(特殊)」；gdi 仅 special，sr=17.5 |
| lootdrop 图例 | `黄金宝箱(特殊)` | 保持；ref → `props/GoldChest_special` |

「(海底)」前缀：enrichment 与 lootdrop 文案不一致。本计划 **统一为 lootdrop 风格「黄金宝箱(特殊)」**（无强制「(海底)」），避免同一概念两套字符串；若需保留海底语义，仅在 special 页 subtitle/debug 标注 UnderSea maps。

## 5. 实现步骤（建议顺序）

1. **抽公共分类**：`_classify_label` → `api/src/label_type.py`（或 translator），export / lootdrop / enrichment 共用。  
2. **拆 `all_coords`**：collector 在 `export_props` 前对 GoldChest 族做 split → `GoldChest_special`。  
3. **导出 + 索引**：props 列表与详情；`entity_page_map` 注册。  
4. **enrichment**：按页过滤 gdi 条目（translation 后缀 / label 类型与页一致）。  
5. **lootdrop_builder**：special 条目 entity_name/ref 指向合成实体；回归 CourtlyDress_7001 / Spellbook_7001。  
6. **管道 + 验收**（见下）。  
7. `SESSION_CHANGES` + commit。

## 6. 验收

| 检查 | 期望 |
|------|------|
| `props/GoldChest.json` coords | **无** `ChestSpecial*` label；约 50 点量级（direct） |
| `props/GoldChest_special.json` | 存在；coords 为 special label；约 32 点 |
| `props.json` | 含 `GoldChest_special`，可进列表 |
| `/props/GoldChest/` gdi | 无「…(特殊)」行；地图无 special 点 |
| `/props/GoldChest_special/` | 标题黄金宝箱(特殊)；参考爆率 **17.5%** × 各模式；地图仅 special 点 |
| `Spellbook_7001` | 「黄金宝箱(特殊)」仍有正确点；`ref` 或 inline 不污染「黄金宝箱」 |
| `CourtlyDress_7001` | 「黄金宝箱(特殊)」为独立图例/可解析坐标；**不再**因 ref GoldChest 显示 100% 混点 |
| 落盘 gdi | 无内部 `_` 键 |

## 7. 风险与范围控制

| 风险 | 缓解 |
|------|------|
| 只拆 GoldChest、其它宝箱仍混装 | 文档标明首期；规则通用后复制到 Ornate/Marvelous |
| 合成名与游戏 keyword 不一致 | 仅站点内部 id；搜索用 translation；不写回 DB |
| SSG/PWA 缓存旧 GoldChest | 部署后 dataVersion/meta 更新；验收硬刷 |
| 双份 `_classify_label` 漂移 | 必须抽公共函数 |
| `GoldChest_UnderSea` coords 页与 special 页重叠 | special 从 UnderSea 再拆；UnderSea 页或废弃为 coords-only，或只留 non-special |

## 8. 与 P002 关系

| P002 降级 | 本计划 |
|-----------|--------|
| lootdrop 内 gdi 翻译有 monsters 条目 | props **物理拆页** |
| virtual + ref 可仍指错页 | ref 指向 `GoldChest_special` |
| 不解决 100% 混点 | 从源头去掉混装 |

P002 计划保持「已完成（降级）」；**本文件为后续架构修复**，完成后可在 P002 文档加链接「坐标混装见 PLAN_GOLDCHEST_SPECIAL_SPLIT」。

## 9. 后续扩展（可选）

同一管道推广：

- `OrnateChest*_special`、`MarvelousChest_special`  
- `*_random` 合成页  
- `GoldChest_group`（海底组 100%）  

每类验收复制 §6 表格即可。
