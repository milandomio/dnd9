# 模块别名旋转值覆盖问题

## 问题现象

`monsters/BabyTurtle/` 详情页中 `ShipGraveyard_BladehandRefuge` 地图模块旋转值为 270°，实际应为 0°。手动进入调试模式调整范围后旋转变为 0°（因 `adjOffsets` 初始化 `rotate=0` 覆盖了模块值）。

同类对比：`items/Shackles/` 中 `ShipGraveyard_FloatingVillage` 旋转 0° 正确。

## 根因

两个 `Id_DungeonModule_*.json` 文件的 `SubLevelAsset` 指向同一地图图片，触发了别名合并逻辑：

| 文件 | module_name | SubLevelAsset → sl_base | 合并后 module_name |
|------|------------|------------------------|-------------------|
| `Id_DungeonModule_ShipGraveyard_BladehandRefuge.json` | `ShipGraveyard_BladehandRefuge` | `ShipGraveyard_SkullIsland_D` → `ShipGraveyard_SkullIsland` | `ShipGraveyard_SkullIsland` |
| `Id_DungeonModule_ShipGraveyard_SkullIsland.json` | `ShipGraveyard_SkullIsland` | 自身 → `ShipGraveyard_SkullIsland` | `ShipGraveyard_SkullIsland` |

**处理流程（旧代码）：**

1. BladehandRefuge（字母序靠前）先处理：`sl_base != module_name` → 别名合并 → `module_name = 'ShipGraveyard_SkullIsland'`，旋转查找 `module_rotations.get('ShipGraveyard_SkullIsland')` = **270°**（因为此时 module_name 已被覆盖）
2. SkullIsland 后处理：`INSERT OR REPLACE` 覆盖同一行，旋转 **270°**

**两个不同模块共用同一张地图图片，但旋转值各自独立。** BladehandRefuge 在 Layout 文件中标注旋转 0°，SkullIsland 旋转 270°。别名合并导致旋转值丢失。

## 修复方法

在 `api/src/db/importers/modules.py` 中添加冲突检测：

1. 预索引所有独立模块名（`own_module_names`）
2. 当 `sl_base` 指向另一个**有独立文件**的模块时，不执行别名合并，各自保持独立行
3. 旋转值直接用 `module_name`（原始模块名）查询 `module_rotations`

**关键代码变更：**

```python
# 新增：预索引独立模块名
own_module_names: set[str] = set()
for raw_name in files:
    own_module_names.add(extract_dungeon_module_name(raw_name))

# 别名逻辑中增加冲突检测
if sl_base and sl_base != module_name:
    if sl_base in own_module_names:
        pass  # 各自独立，不合并
    else:
        aliases.append(module_name)
        module_name = sl_base
```

## 影响范围

修复前 DB 中 254 个模块（合并后），修复后 257 个模块（3 个被拆分为独立行）：
- `ShipGraveyard_BladehandRefuge`（旋转 0°）← 此前被合并到 SkullIsland
- 另外 2 个类似冲突模块同步拆分

## 参考

- `api/src/db/importers/modules.py` — 别名合并逻辑
- `api/src/layout_utils.py` — Layout 文件旋转解析
- `api/src/module_builder.py` — `build_map_mappings` 处理 `map_to_module` 映射