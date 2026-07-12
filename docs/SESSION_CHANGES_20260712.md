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

## 待处理问题

### GoblinWarrior/LavaGolem 坐标混入问题
- **问题**: GoblinWarrior 生成器包含 LavaGolem_Nightmare 条目，导致坐标被关联到错误的实体
- **当前状态**: 已回滚尝试的修复（影响 197 个 spawner/entity 组合）
- **根因**: 游戏数据中 GoblinWarrior spawner 有 2 个 LavaGolem_Nightmare 条目（稀有生成）
- **待分析**: 需要更精确的解决方案

### 黄金宝箱(特殊) 缺失
- **问题**: "黄金宝箱(特殊)" 在 group_drop_info 中但不在 monsters 列表中
- **当前状态**: 未修复
- **根因**: ChestSpecial_UnderSea 生成器的坐标没有正确关联

### 容器生成器子分类
- **问题**: 容器生成器（如 ChestSpecial_UnderSea）的子分类按钮（如 "黄金宝箱(特殊)"）没有对应的实体详情页
- **当前状态**: 未修复
- **计划**: 在 `docs/PLAN_CONTAINER_GENERATOR_ENTITIES.md` 中记录

## 文档更新

- `docs/FIX_ARTIFACT_VARIANT_SWITCH.md` - 神器变体切换修复文档
- `docs/PERF_LOOTDROPS_OPTIMIZATION.md` - lootdrops 性能优化记录
- `docs/PLAN_CONTAINER_GENERATOR_ENTITIES.md` - 容器生成器实体页计划
