# 修复 _8001 变体 group_drop_info 缺少参考爆率

## 问题

`/lootdrops/RondelDagger_8001/` 的"沉船墓场1层"参考爆率缺失。基底 `RondelDagger` 有 40 个怪物/容器跨越 8 个地图（Inferno/FireDeep/GoblinCave/Ruins/IceAbyss/ShipGraveyard/Crypt/IceCavern），而变体 `RondelDagger_8001` 只有 3 个。

## 根因

`api/src/lootdrop_builder.py:build_merged_loot_map()` 中，`_8001` 变体只分配了自己的怪物列表（`loot_map.get(v8001, [])`），而非继承基底的合并全量列表。代码注释写着"monsters are shared with base"但未实现。**注意：8 个地图是正确的**，RondelDagger（影刃）本身就分布在这些地图中，变体理应继承基底的完整地图分布。

## 修复

**文件**：`api/src/lootdrop_builder.py`（`9ef1a483`）

两处修改：
1. **line 160**：`_8001` 变体继承 `merged_loot[base]`（基底的合并全量怪物列表）而非自己的独占列表
2. **line 168**：第二处 fallback 循环同样修改，使用 `merged_loot[base]` 代替 `loot_map[item_name]`

## 状态

- [x] 代码修复已提交（`9ef1a483`）
- [x] 管道已验证：ShipGraveyard 1 条 → 29 条参考爆率
- [x] **已回滚**（`f3c56bdd`）：_8001 变体回到 `loot_map.get(v8001, [])`（只用自己 spawners）
- [x] 8 个地图分类是**正确的**——RondelDagger（影刃）在游戏数据中就分布于这 8 个地图模块
- [ ] 实际问题是 ShipGraveyard 显示 29 条但前端渲染缺失参考爆率，需另找根因

## 验证方法

```bash
# 检查 RondelDagger_8001 group_drop_info 中 ShipGraveyard 条目数
python3 -c "
import json
d = json.load(open('data/json/lootdrops/RondelDagger_8001.json'))
sg = d.get('group_drop_info', {}).get('ShipGraveyard', [])
print(f'ShipGraveyard entries: {len(sg)} (expected >= 20, was 1)')
"
```
