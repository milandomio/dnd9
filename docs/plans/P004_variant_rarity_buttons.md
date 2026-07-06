# P004: 变体稀有度按钮 + 神器页面优化

## 目标
为 lootdrop 详情页添加变体稀有度标签和导航按钮，用户可切换查看同一物品的不同品质变体。

## 术语
- **变体（variant）**: 同一物品的不同品质版本，后缀 `_\d{4}`（如 `_3001`, `_4001`）
- **神器（artifact）**: 后缀 `_8001` 的特殊变体，独立于普通变体系列
- **raw_name**: `item_entities` 表中的原始游戏资产名（如 `Id_Item_NecklaceOfPeace_3001`），首变体后缀由此确定

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
- 普通变体：通过 `compute_drop_rate()` 的 `_VARIANT_SUFFIXES` fallback 链匹配
- 百分比格式 `.toFixed(2)`

### 变体起始后缀
- `item_entities.raw_name`（如 `Id_Item_NecklaceOfPeace_3001`）→ 首变体 = 3001
- `range(first_num, first_num + variant_count)` 生成完整序列
- 约 20 个物品（NecklaceOfPeace 等）始于 `_3001` 而非 `_1001`

## 已知问题

### 1. Mitre 等物品未生成详情页
- **症状**: `api/output/json/lootdrops/Mitre.json` 不存在，前端 404
- **原因**: 复杂 — 可能与 `_coord_variant_count` 过滤、`original_keyword` 查找、DB 内容有关
- **修复未完成**: 未找到根本原因，需进一步调试
- **影响**: 所有 variant_count > 1 的物品可能受影响

### 2. 部署依赖
- 数据管道（`python main.py`）必须在 `npm run build` 前运行
- DB 不能被 `_is_db_stale()` 跳过导入（删除 DB 后强制重建）
- 游戏解包 JSON 文件必须存在（`ITEM_DIR/Id_Item_*.json`）

## 回滚前状态
- 当前 HEAD: `e8c0cfe` (Jul 6, 4 revert commits + 2 kept commits)
- 保留的改动: `7cb96c7` (group_drop_info 聚合) + `e525626` (_8001 suffix 隔离)
- 回滚目标: `d7b0d96` (Jun 26)

## 参考
- V4 参考: `v4_reference/group_config.json`
- 技术规范: `docs/REFERENCE.md`
