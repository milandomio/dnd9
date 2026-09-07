# 修复：神器变体切换显示

> 日期: 2026-07-12
> 状态: ✅ 已完成
> commit: `e2f3e6a`

## 问题

1. `HeaterShield_8001` 等神器页面没有显示变体切换按钮
2. `HeaterShield_7001` 等普通变体页面缺少 8001（命名神器）按钮

## 修复内容

### 1. `_8001` 物品包含所有变体

**文件:** `api/src/lootdrop_builder.py`

对于 `_8001` 物品，后缀列表包含全部 8 个变体：

```python
if item_name.endswith("_8001"):
    # _8001 items: include all 8 variants (1001-7001 + 8001)
    vs = ["1001", "2001", "3001", "4001", "5001", "6001", "7001", "8001"]
```

### 2. 普通变体页面也包含 8001

对于 `variant_count >= 8` 的物品（有神器变体），所有变体页面都包含 8001：

```python
# 如果 variant_count >= 8，包含 8001
if variant_count >= 8 and "8001" not in vs:
    vs.append("8001")
```

### 3. 前端自动适配

前端已支持从 `Object.keys(variant_rarity)` 渲染变体按钮，无需修改。

## 效果

| 页面 | 修复前 | 修复后 |
|------|--------|--------|
| HeaterShield_8001 | 无变体按钮 | 8 个按钮（1001-8001） |
| HeaterShield_7001 | 7 个按钮（1001-7001） | 8 个按钮（1001-8001） |
| HeaterShield_5001 | 7 个按钮 | 8 个按钮 |

## 防御规则：变体后缀拼接前检查

### 问题

拼接变体后缀时，如果物品名已包含 `_?001` 变体后缀，会导致重复拼接：

```
item_name = "HeaterShield_8001"
suffix = "8001"
拼接结果 = "HeaterShield_8001_8001"  ← 错误！
```

### 规则

**在拼接变体后缀前，必须检查物品名是否已包含 `_?001` 模式。**

```python
import re

_VARIANT_SUFFIX_RE = re.compile(r"_\d{4}$")

def is_already_variant(item_name: str) -> bool:
    """检查物品名是否已包含变体后缀（如 _8001, _5001）"""
    return bool(_VARIANT_SUFFIX_RE.search(item_name))

# 正确的拼接逻辑
if is_already_variant(item_name):
    # 物品名已包含变体后缀，不要再次拼接
    variant_name = item_name
else:
    # 正常拼接
    variant_name = f"{item_name}_{suffix}"
```

### 验证方法

```bash
ls data/json/lootdrops/ | grep -E "_\d{4}_\d{4}\.json"
```

如果输出不为空，说明存在重复后缀问题。
