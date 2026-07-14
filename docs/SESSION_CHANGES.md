# 2026-07-12 会话修改记录

## 性能优化

### lootdrops 模块优化（85s → 28s，省 67%）

| 优化 | commit | 效果 |
|------|--------|------|
| compact JSON | `4109ee1` | 省 15s |
| fuzzy candidate_ids 匹配 | `764acc7` | 省 1s |
| 移除 variant_suffixes 冗余 | `ec15e98` | 省 44s |
| 修复 variant 后缀计算 | `3be3910` | 恢复正确后缀 |
| 修复 _8001 变体显示 | `e2f3e6a` | 恢复神器变体切换 |

### 其他优化

- `drop_rate.py`: 添加 `_get_candidate_ids` 缓存
- `drop_rate.py`: 添加 fuzzy matching（FakeDeath/FromFakeDeath 后缀）

## Bug 修复

### 坐标标签翻译问题
- **commit**: `858cc54`
- **问题**: 坐标标签被 HARDCODED_TRANSLATIONS 翻译为中文（如 "ChestMedium" → "中宝箱"）
- **修复**: `build_coord_out` 中移除翻译，直接使用 `original_keyword`

### 双下划线变体分类
- **commit**: `f137cd5`
- **问题**: `GoldChest__UnderSea`（双下划线）被错误分类为 "other" 类型，添加 "组" 后缀
- **修复**: `_classify_label` 中将 `__` 视为 `_` 进行匹配

### 神器变体切换
- **commit**: `6a89a1b`, `e2f3e6a`
- **问题**: `_8001` 物品没有变体切换按钮
- **修复**: 包含 8001 在 variant_rarity 中，所有变体页面显示完整 8 个按钮

### 变体后缀计算
- **commit**: `3be3910`
- **问题**: 移除 variant_suffixes 后，后缀计算从 1001 开始，但部分物品从 3001 开始
- **修复**: 使用 `raw_name` 中的数字作为起始后缀

### lootdrop 列表页变体前缀
- **commit**: `98265d2`
- **问题**: 列表页显示 "[8变体]" 前缀
- **修复**: 移除变体数量显示

## UI/SEO 改进

### 站名改名
- **commit**: `066194b`
- **修改**: DarkFindV5游戏导航 → 越来越黑暗光速指南 DarkFlashNav

### 标题样式
- **commit**: `453e5c2`, `01fd9f3`
- **修改**: 中文名 26px，DarkFlashNav 16px，分两行显示

### SEO 关键词
- **commit**: `2da772a`, `52d9a2f`
- **关键词**: 越来越黑暗, 越来越黑暗玩家指南, 越来越黑暗光速指南, DarkFlashNav, Dark and Darker, 暗黑地牢, ...

## 2026-07-13 会话修改记录

### 多实体刷怪器坐标误扩展修复
- **commit**: `dfffe3d`
- **问题**: GoblinWarrior 的 DCSpawnerDataAsset 包含 LavaGolem_Nightmare 条目，`load_all_spawner_data` 剥离后缀后得到 2 个不同实体名（GoblinWarrior、LavaGolem），触发多实体展开。所有 GoblinWarrior 地图刷怪点都生成了 keyword="LavaGolem" 的坐标，导致 LavaGolem 页面多了 104 个虚假坐标
- **修复**: `search_engine.py:extract_spawners` 中，展开前判断 spawner 基名是否匹配任一实体基名。若匹配，只保留基名一致的实体；若不匹配（如 Random/Special 生成器），保留全部
- **效果**: LavaGolem 坐标从 105 降为 1（真实坐标）；GoblinMelee_Random、ChestSpecial 等不受影响

### lootdrop score 未乘实体生成概率修复
- **commit**: `7703899`
- **问题**: `lootdrop_builder.py:556` 中 per-coord score 使用 `coord.spawn_rate`（未命中 cache 时默认回退 100），未使用实体级 `entity.spawn_rate`。如迷你宝盒组 group_drop_info 中 spawn_rate=3.0，但每个 coord score = 100×25/100=25.0，模块合计 512.5%。实际应为 3.0×25/100=0.75 per coord
- **修复**: 新增 `_sr_lookup` 从 `_group_drop_info` 提取实体级 spawn_rate，score 公式改为 `entity_spawn_rate × 豪客赛 / 100`
- **效果**: 迷你宝盒组 per-coord score 从 25.0 → 0.75，模块合计 ≈15.375%（512.5%×3%）

### 文案修正
- **commit**: `7703899`, `a5afb3e`
- **问题**: 模块卡片显示"单点综合爆率"，应为"综合爆率"
- **修复**: `LootdropDetailPage.tsx:1359` 模块卡片 + `:844` 调试面板标签，去掉了"单点"前缀

## 待处理问题

### 黄金宝箱(特殊) 缺失
- **问题**: "黄金宝箱(特殊)" 在 group_drop_info 中但不在 monsters 列表中
- **当前状态**: 未修复
- **根因**: ChestSpecial_UnderSea 生成器的坐标没有正确关联

### 容器生成器子分类
- **问题**: 容器生成器（如 ChestSpecial_UnderSea）的子分类按钮（如 "黄金宝箱(特殊)"）没有对应的实体详情页
- **当前状态**: 未修复
- **计划**: 在 `docs/PLAN_CONTAINER_GENERATOR_ENTITIES.md` 中记录

## 2026-07-14 会话修改记录

### PWA 图标改为 DND + 圆角
- **修改**: PWA 图标从纯蓝正方形改为圆角蓝底白字 "DND"
- **favicon**: 新增 `web/public/favicon.ico`（16/32/48 三尺寸），`index.html` 添加 `<link rel="icon">`

## 文档更新

- `docs/FIX_ARTIFACT_VARIANT_SWITCH.md` - 神器变体切换修复文档
- `docs/PERF_LOOTDROPS_OPTIMIZATION.md` - lootdrops 性能优化记录
- `docs/PLAN_CONTAINER_GENERATOR_ENTITIES.md` - 容器生成器实体页计划
