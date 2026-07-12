# P002: 容器生成器实体页详情

> 日期: 2026-07-12
> 状态: 待执行

## 问题

容器生成器（如 `ChestSpecial_UnderSea`）生成多种实体类型（如 GoldChest_UnderSea、OrnateChestLarge_UnderSea 等），这些实体在 `group_drop_info` 中有不同的子分类（"黄金宝箱(特殊)"、"狮头宝箱(特殊)"等），但这些子分类没有对应的实体详情页，导致前端无法点击。

## 受影响的容器生成器

| 生成器 | 实体数量 | 子分类示例 |
|--------|---------|-----------|
| ChestSpecial | 10 | 黄金宝箱(特殊), 狮头宝箱(特殊), 卓越宝箱(特殊) |
| ChestSpecial_UnderSea | 3 | 黄金宝箱(特殊), 狮头宝箱(特殊) |
| FrostSkeletonWoodenBarrelRandom | 4 | 冰霜骷髅木栅栏(随机) |
| GoblinMelee_Random | 6 | 哥布林近战(随机) |
| GoblinRanged_Random | 6 | 哥布林远程(随机) |
| Ore_*Random | 4-16 | 各矿石(随机) |

## 修复方案

### 方案 A: 在 lootdrop_builder 中生成虚拟实体条目

在 `build_and_save_lootdrop_details` 中，对容器生成器产生的子分类：
1. 检测 `group_drop_info` 中存在但 `monsters` 中不存在的翻译
2. 为这些翻译创建虚拟实体条目
3. 虚拟实体条目包含坐标引用（ref）指向基础实体

### 方案 B: 在数据库层面增加虚拟 spawner

为容器生成器创建虚拟 spawner 条目，使其在坐标提取阶段就被正确分类。

### 推荐方案 A

修改 `build_and_save_lootdrop_details` 函数：
1. 遍历 `group_drop_info` 中的所有翻译
2. 检查每个翻译是否在 `monsters` 列表中有对应条目
3. 如果没有，创建虚拟实体条目：
   - name: 基础实体名 + 后缀
   - translation: 子分类翻译
   - ref: 指向基础实体详情页
   - coord_count: 0（使用 ref）
4. 将虚拟实体添加到 `monsters` 列表

## 实现步骤

1. 修改 `lootdrop_builder.py` 中的 `build_and_save_lootdrop_details` 函数
2. 在 `monsters` 列表构建完成后，遍历 `group_drop_info` 检查缺失的翻译
3. 为每个缺失的翻译创建虚拟实体条目
4. 测试 Spellbook_7001 页面，确保"黄金宝箱(特殊)"等按钮可点击
