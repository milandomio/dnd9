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

---

## 防御规则：变体后缀拼接前检查

### 问题

拼接变体后缀时，如果物品名已包含 `_?001` 变体后缀，会导致重复拼接：

```
item_name = "HeaterShield_8001"
suffix = "8001"
拼接结果 = "HeaterShield_8001_8001"  ← 错误！

item_name = "HeaterShield_8001"
suffix = "1001"
拼接结果 = "HeaterShield_8001_1001"  ← 错误！
```

### 规则

**在拼接变体后缀前，必须检查物品名是否已包含 `_?001` 模式。**

```python
import re

# 检查物品名是否已包含变体后缀
_VARIANT_SUFFIX_RE = re.compile(r"_\d{4}$")

def is_already_variant(item_name: str) -> bool:
    """检查物品名是否已包含变体后缀（如 _8001, _5001）"""
    return bool(_VARIANT_SUFFIX_RE.search(item_name))

# 正确的拼接逻辑
if is_already_variant(item_name):
    # 物品名已包含变体后缀，不要再次拼接
    # 直接使用物品名作为变体名
    variant_name = item_name
else:
    # 正常拼接
    variant_name = f"{item_name}_{suffix}"
```

### 检查位置

以下函数在拼接变体后缀前必须进行检查：

1. `lootdrop_builder.py` — 变体详情文件生成
2. `drop_rate.py` — 变体爆率计算
3. `enrichment.py` — 变体爆率注入

### 验证方法

运行以下命令检查是否存在重复后缀的文件：

```bash
ls data/json/lootdrops/ | grep -E "_\d{4}_\d{4}\.json"
```

如果输出不为空，说明存在重复后缀问题。
