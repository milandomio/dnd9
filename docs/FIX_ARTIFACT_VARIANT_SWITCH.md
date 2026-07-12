# 修复：神器变体切换显示

> 日期: 2026-07-12
> 状态: 待执行

## 问题

`HeaterShield_8001` 等神器页面没有显示变体切换按钮，`variant_rarity` 为 None。

## 原因分析

1. `_8001` 物品在 `build_and_save_lootdrop_details` 中计算 `vs = ["1001", "2001", "3001", "4001", "5001", "6001", "7001", "8001"]`
2. 调用 `_get_variant_rarity(item_name, vs, translations)` 时，对于 suffix="8001"，查找文件路径为：
   `ITEM_DIR / f"Id_Item_{item_name}_{suffix}.json"` → `Id_Item_HeaterShield_8001_8001.json`
3. 但实际文件是 `Id_Item_HeaterShield_8001.json`（无额外 `_8001` 后缀）
4. 文件不存在 → `rarity_name = None` → 使用 fallback → 返回 `{"8001": "命名神器"}`
5. **但** 对于 suffix="1001"-"7001"，文件 `Id_Item_HeaterShield_8001_1001.json` 不存在
6. 所有 suffix 都找不到文件 → 全部使用 fallback → `variant_rarity` 应该能正常生成

## 实际问题

检查 `_get_variant_rarity` 函数：对于 `_8001` 物品，suffix 遍历时每个都会查找 `Id_Item_HeaterShield_8001_{suffix}.json`，这些文件都不存在，所以全部走 fallback。

**fallback 已经包含 `"8001": "Artifact"`**，翻译后应为 "命名神器"。

所以 `variant_rarity` 应该能正常生成。问题可能在其他地方。

## 需要验证

1. 确认 `_get_variant_rarity` 对 `_8001` 物品返回正确的 `variant_rarity`
2. 确认前端能正确渲染 8 个变体按钮（1001-8001）
3. 确认点击 8001 按钮能跳转到正确的页面

## 修改方案

### 后端

无需修改。`_get_variant_rarity` 的 fallback 已包含 `"8001": "Artifact"`，翻译后为 "命名神器"。

### 前端

无需修改。前端已支持从 `variant_rarity` 渲染变体按钮。

### 验证步骤

1. 运行管道生成数据
2. 检查 `HeaterShield_8001.json` 的 `variant_rarity` 字段
3. 构建前端并验证页面显示
