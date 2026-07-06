# P004: 变体稀有度按钮 + 神器页面优化

## 目标
为 lootdrop 详情页添加变体稀有度标签和导航按钮，用户可切换查看同一物品的不同品质变体。

## 核心需求（必须全部满足）

1. **所有变体都必须有对应的切换按钮** — 包括 Poor/Common/Uncommon/Rare/Epic/Legend/Unique/Artifact 全部 8 级稀有度
2. **每个变体必须显示对应的爆率** — 按该变体的 `luck_grade` 计算，无掉落数据的变体爆率为 0
3. **每个变体必须显示对应的坐标点** — 按该变体的实际 spawner 过滤，无掉落数据的变体显示基础坐标
4. **每个变体必须有分类按钮** — 变体稀有度按钮组完整显示
5. **`_8001` 神器变体特殊处理**：
   - 标题翻译使用神器自身的翻译（如"冥渊三叉戟"而非"长矛"）
   - 独立条目，不被基础条目覆盖
   - 显示阈值专属（`0.03` 而非 `2.5`）

## 术语
- **变体（variant）**: 同一物品的不同品质版本，后缀 `_\d{4}`（如 `_3001`, `_4001`）
- **神器（artifact）**: 后缀 `_8001` 的特殊变体，独立于普通变体系列
- **raw_name**: `item_entities` 表中的原始游戏资产名（如 `Id_Item_NecklaceOfPeace_3001`），首变体后缀由此确定
- **luck_grade**: 变体后缀首位数字，决定稀有度等级（`_5001` → luck_grade=5 = Epic）

## 实现步骤

### 1. 后端：raw_name 查询 + variant_suffixes 计算

**文件**: `api/src/db/repositories/items.py`
- `ItemEntity` TypedDict 增加 `raw_name` 字段
- `get_all()` 查询 SELECT raw_name

**文件**: `api/src/lootdrop_builder.py`
- `build_loot_index()` 中计算 `variant_suffixes`:
  - `raw_name` 末段数字决定起始后缀（如 `_3001` → `["3001","4001","5001","6001","7001"]`）
  - `_8001` 物品只保留 `["8001"]`
  - 其他条件：`variant_count > 1`
  - **必须生成全部后缀**，不能只生成有掉落数据的后缀
- 将 `variant_suffixes` 写入 loot_index entry

### 2. 后端：游戏数据稀有度提取

**文件**: `api/src/lootdrop_builder.py` → `_get_variant_rarity()`
- 读取 `Id_Item_{name}_{suffix}.json` 游戏解包文件
- 提取 `RarityType.TagName`（如 `Type.Item.Rarity.Legend`）
- 通过 DB `translations` 表翻译 `Text_Code_DCDataBlueprintLibrary_Type_Item_Rarity_{raw}` → 中文
- 返回 `{suffix: cn_name}` 字典
- 写入 detail JSON 的 `variant_rarity` 字段

### 3. 后端：group_drop_info 聚合（_8001）

**文件**: `api/src/lootdrop_builder.py`
- 在 `build_and_save_lootdrop_details()` 中，`_8001` 物品的 `group_drop_info` 改用 "全部来源" 单一分组
- 按怪物翻译聚合：`spawn_rate` 取最大值，`drop_rates` 各模式求和
- 非 `_8001` 物品不变（按地图分组）

### 4. 前端：URL 后缀解析 + 变体导航

**文件**: `web/src/pages/LootdropDetailPage.tsx`
- `VARIANT_NAME_RE = /^(.+?)_(\d{4})$/` 匹配 URL 后缀
- 从 URL pathname 提取 base_name 和 suffix
- `useNavigate` 构建变体按钮组，点击导航到 `/lootdrops/${baseName}_${suffix}/`
- `variant_rarity` 显示稀有度标签（游戏数据覆盖硬编码 `VARIANT_RARITY`）
- 降序排列（8001 > 7001 > ... > 1001）
- **默认高亮第一个变体**（非硬编码 `_6001`）

### 5. SSG：变体路由生成

**文件**: `web/scripts/ssg.mjs`
- 遍历 loot_index，对有 `variant_suffixes` 的物品生成额外路由
- `routeDataKey` 从 URL 剥离 `_\d{4}$` 后缀，回退到基础条目数据
- 神器 `_8001` 路由走 CSR（quick 模式），SSR 只注入 `{name, translation}`

## 关键配置

### 稀有度来源优先级
1. **游戏数据**（`RarityType.TagName` → `translations` 表）— 优先
2. **硬编码** `VARIANT_RARITY` — fallback

### 爆率计算
- `_8001` 物品：`luck_grade=8`，自己的 `lootdrop_rate_items` 条目
- 普通变体：通过 `compute_variant_rate()` 按 `luck_grade` 直接计算
- 无掉落数据的变体：爆率为 0，坐标显示基础坐标
- 百分比格式 `.toFixed(2)`

### 变体起始后缀
- `item_entities.raw_name`（如 `Id_Item_NecklaceOfPeace_3001`）→ 首变体 = 3001
- `range(first_num, first_num + variant_count)` 生成完整序列
- 约 20 个物品（NecklaceOfPeace 等）始于 `_3001` 而非 `_1001`

### _8001 神器特殊处理
- **独立条目**：`build_merged_loot_map()` 将 `_8001` 拆为独立条目
- **翻译**：使用 `resolve_name(variant_name, None, "item")` 获取神器自身翻译
- **不被覆盖**：基础条目生成变体文件时跳过 `_8001` 后缀
- **显示阈值**：前端 `defaultThreshold = 0.03`（非变体/神器的 `2.5`）
- **expanded_index**：跳过 `_8001`（已有独立条目）

### 坐标过滤（spawner 匹配）
- **精确匹配**：`get_variant_spawners(item_name)` 追踪 `item → lootdrop_id → group_id → spawner_keyword` 链
- **非全局匹配**：禁止使用 `get_spawners_for_luck_grade(luck_grade)`（返回过多不相关 spawner）
- **无数据变体**：`valid_spawners` 为空时显示基础坐标（不过滤）

## Bug 修复计划（Jul 7）

### Bug 0: 变体按钮生成子变体 — `expanded_index` 传递 `variant_suffixes` 导致递归生成

**症状**: `AdventurerBoots_6001` 等变体页面生成了子变体文件 `AdventurerBoots_6001_6001.json`

**根因**: `expanded_index` 逻辑为每个变体后缀创建独立条目时，将 `variant_suffixes` 传递给了变体条目。当 `build_and_save_lootdrop_details` 处理 `AdventurerBoots_6001` 时，发现它有 `variant_suffixes`，于是再次生成变体文件 `AdventurerBoots_6001_1001.json`、`AdventurerBoots_6001_6001.json` 等。

**修复**: 在 `expanded_index` 生成变体条目时，不传递 `variant_suffixes` 字段。只有基础条目（如 `AdventurerBoots`）保留 `variant_suffixes`，变体条目（如 `AdventurerBoots_6001`）不再有该字段。

**修改文件**: `api/src/lootdrop_builder.py` — `build_and_save_lootdrop_details()` 的 `expanded_index` 逻辑

**验证**:
- `data/json/lootdrops/` 目录下无 `*_XXXX_XXXX.json` 子变体文件
- `lootdrops.json` 中变体条目无 `variant_suffixes` 字段
- 变体详情文件（如 `AdventurerBoots_6001.json`）保留 `variant_suffixes` 供前端渲染按钮

### Bug 1: 坐标过滤错误 — `get_spawners_for_luck_grade()` 返回过多 spawner

**症状**: Spear_6001 显示了不相关的 311 个 spawner 坐标（如 AncientStingray、SkeletonWoodenBarrel）

**根因**: `get_spawners_for_luck_grade(6)` 按 luck_grade 全局匹配——只要某个 rate_id 支持 luck_grade=6 且 weight>0，该 rate_id 关联的所有 group 的所有 spawner 都会被返回。实际上 `lootdrop_rate_items` 中只有 `Spear_5001`(lg=5) 和 `Spear_8001`(lg=8)，`Spear_6001`/`Spear_7001` 根本不存在。

**DB 证据**:
- `lootdrop_rate_items` 中 Spear 相关只有 `Spear_5001`(luck_grade=5) 和 `Spear_8001`(luck_grade=8)
- `ID_Droprate_Monsters_General_2001` 等 rate_id 对 luck_grade=6 weight>0，但这些 group 中并不包含 `Spear_6001`

**修复**: 新增 `DropRateEngine.get_variant_spawners(item_name, luck_grade)`:
1. 从 `_ld_rate_items` 查找包含目标物品的 `lootdrop_id` 集合
2. 从 `_ld_groups` 映射到 `group_id` 集合
3. 从 `_group_to_spawners` 映射到 `spawner_keyword` 集合
4. 返回精确的 spawner 集合（而非全局 luck_grade 匹配）

替代 `lootdrop_builder.py:615` 的 `get_spawners_for_luck_grade(luck_grade)` 调用。

### Bug 2: Spear_8001 翻译显示"长矛"而非"冥渊三叉戟"

**症状**: `http://localhost:8080/lootdrops/Spear_8001/` 标题显示"长矛"

**根因**: 变体 detail 文件的 `translation` 取自 `entry["translation"]`（基础条目 "Spear" 的翻译 = "长矛"）。"Spear" 条目生成了 `Spear_8001.json`(translation="长矛")，按 sort 顺序排在 "Spear_8001" 独立条目之后，覆盖了正确文件。

**DB 证据**: `Text_DesignData_Item_Item_Spear_8001` → "冥渊三叉戟" 存在于 translations 表

**修复**:
1. 变体 detail 的 translation 改用 `resolve_name(variant_name, None, "item")` 而非 `entry["translation"]`
2. "Spear" 基础条目生成变体时，跳过已有独立条目的 `_8001` 后缀

### Bug 3: 生成了不存在的变体文件

**症状**: `Spear_6001.json`、`Spear_7001.json` 有完整坐标数据，但游戏掉落表中不存在这些变体

**根因**: `variant_count=8` 导致 suffixes=["1001","2001",...,"8001"] 全部生成 detail 文件，但只有 5001 和 8001 在 `lootdrop_rate_items` 中有实际数据

**修复**:
1. 生成变体前调用 `get_variant_spawners()` 检查是否有实际掉落数据
2. 如果返回空集，跳过该变体（不生成 detail 文件）
3. 只将有数据的 suffix 写入 `variant_suffixes` 列表

### Bug 4: lootdrops.json 中有重复 Spear_8001 条目

**症状**: expanded_index 和独立 _8001 条目都生成了 Spear_8001

**根因**: `build_and_save_lootdrop_details()` 的 expanded_index 逻辑为每个 suffix 创建条目（包括 8001），而 `build_merged_loot_map()` 已经将 _8001 拆为独立条目

**修复**: expanded_index 生成时跳过已有独立条目的 _8001 后缀

### Bug 5: 非 _8001 物品的 `variant_suffixes` 包含 "8001"

**症状**: `HeaterShield_5001` 页面显示 _8001 按钮，点击后跳转到不存在的页面

**根因**: `build_loot_index()` 的 `variant_suffixes` 算术生成全部后缀（包括 8001），但 _8001 是独立条目，不应出现在非 _8001 物品的按钮组中

**修复**: 在 `build_loot_index()` 中过滤掉 "8001" 后缀：
```python
variant_suffixes = [s for s in variant_suffixes if s != "8001"]
```

**修改文件**: `api/src/lootdrop_builder.py` — `build_loot_index()` 第 266 行

**验证**:
- `HeaterShield_5001.json` 的 `variant_suffixes` 不包含 "8001"
- `HeaterShield_8001.json` 的 `variant_suffixes` 为 `["8001"]`

### Bug 6: 默认变体按钮硬编码为 _6001

**症状**: 用户访问 `/lootdrops/HeaterShield/` 时，默认高亮 _6001 按钮，但实际应根据 `variant_suffixes` 动态选择

**根因**: 前端代码 `suffix === '6001'` 硬编码了默认按钮

**修复**: 改为优先选择 "6001"（如果存在），否则选择第一个变体：
```tsx
const defaultSuffix = data.variant_suffixes!.includes('6001') ? '6001' : data.variant_suffixes![0];
```

**修改文件**: `web/src/pages/LootdropDetailPage.tsx` — 第 557-559 行

### 修改文件清单

| 文件 | 改动 |
|------|------|
| `api/src/drop_rate.py` | 新增 `get_variant_spawners(item_name)`、`get_base_item_spawners(base_item_name)`、`get_existing_variant_suffixes(base_item_name)`；删除 `get_spawners_for_luck_grade()` |
| `api/src/lootdrop_builder.py` | 替换 spawner 过滤、修复翻译、跳过空变体、去重 _8001、过滤 variant_suffixes 中的 "8001"、expanded_index 不传递 variant_suffixes 给变体条目 |
| `api/src/collector.py` | 移动 DropRateEngine 创建到 build_loot_index 之前 |
| `web/src/pages/LootdropDetailPage.tsx` | 默认变体按钮逻辑：优先选择 "6001"，否则选择第一个变体 |
| `web/src/pages/ListPage.tsx` | 防止为已带后缀的变体名追加 `_6001` |

### 验证

```bash
cd api && python main.py && cd ../web && npm run build
# 启动 web 检查:
# 1. /lootdrops/Spear_6001/ → 无坐标或不生成
# 2. /lootdrops/Spear_8001/ → 标题"冥渊三叉戟"，只含相关坐标
# 3. /lootdrops/Spear_5001/ → 正常显示
# 4. lootdrops.json 中无重复条目
# 5. /lootdrops/HeaterShield_5001/ → variant_suffixes 不含 "8001"，默认高亮 _6001
# 6. /lootdrops/HeaterShield_8001/ → 独立条目，翻译"不朽神盾"，variant_suffixes=["8001"]
# 7. /lootdrops/AdventurerBoots_6001/ → 无子变体文件 AdventurerBoots_6001_6001.json
# 8. data/json/lootdrops/ 目录下无 *_XXXX_XXXX.json 子变体文件
# 9. lootdrops.json 中变体条目无 variant_suffixes 字段
```

## 已知问题

### 1. 部署依赖
- 数据管道（`python main.py`）必须在 `npm run build` 前运行
- DB 不能被 `_is_db_stale()` 跳过导入（删除 DB 后强制重建）
- 游戏解包 JSON 文件必须存在（`ITEM_DIR/Id_Item_*.json`）

### 2. 坐标过滤逻辑
- 变体坐标过滤使用 `get_variant_spawners(variant_name)` 获取精确 spawner 集合
- 如果变体无掉落数据，回退到 `get_base_item_spawners(base_item_name)` 获取基础坐标
- 如果基础坐标也为空，则跳过该变体（不生成详情文件）

## 回滚前状态
- 当前 HEAD: 待更新 (Jul 7, Bug 0-6 修复完成)
- 保留的改动: Bug 0-6 全部修复
- 回滚目标: `d7b0d96` (Jun 26)

## 参考
- V4 参考: `v4_reference/group_config.json`
- 技术规范: `docs/REFERENCE.md`
