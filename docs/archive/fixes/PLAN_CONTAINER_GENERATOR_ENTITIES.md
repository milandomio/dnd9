# P002: 容器生成器子类 gdi ↔ monsters 对齐

> 日期: 2026-07-12  
> 更新: 2026-07-26  
> 状态: **已完成（降级）**（原「实体详情页」目标废弃）

## 原目标（已过时）

容器生成器子分类（如「黄金宝箱(特殊)」）没有独立实体详情页，前端无法点击。

## 现状（2026-07-26）

| 项 | 状态 |
|----|------|
| `_classify_label` 特殊/随机/组 + 坐标拆分 | 已有；Spellbook 等页「黄金宝箱(特殊)」可有真实坐标 |
| 虚拟 monsters 条目（早期方案 A） | 代码曾写过，预算 `break` / 变体滤空会丢，全库几乎 0 产出 |
| gdi 有、monsters 无（参考爆率被前端滤掉） | 仍普遍（高阶 `_7001` 大量） |
| props/monsters 列表出现 UnderSea 变体 | **不做**（另立项） |
| 独立实体详情页 / 列表可点进 | **不做**（本计划范围外） |

## 降级后必做（本计划范围）

**唯一目标**：`group_drop_info` 中每个有效翻译，在同页 `monsters` 中有对应条目，使图例与「参考爆率」可见。

### 实现（`api/src/lootdrop_builder.py`）

1. `_ensure_gdi_monster_entries`：对 gdi 孤儿补虚拟条目（空 coords + 可选 `ref`）
2. `_resolve_legend_ref`：优先 `entity_page_map[_entity_name]`，再精确匹配去后缀后的基础翻译（禁止 `startswith` 误绑）
3. 坐标预算：`coord_count==0` / 仅 ref 条目**始终保留**，`budget<=0` 时 `continue` 而非 `break`
4. 预算裁切后、变体 monsters 过滤后再各跑一遍 ensure
5. 变体路径：spawner 滤空坐标时保留空条目；`variant_gdi` 暂留 `_entity_name` 至 ensure 后剥掉

### 明确不做

- 方案 B（DB 虚拟 spawner）
- UnderSea / 生成器变体写入 props·monsters 列表
- 完整实体详情页、前端跳转详情

## 验收

- `CourtlyDress_7001` / `GoldBangle2H_7001`：原「只在 gdi」的「黄金宝箱(特殊)」「重型华丽宝箱(特殊)(可能上锁)」等出现在 `monsters`
- `Spellbook_7001`：原有真实坐标的「黄金宝箱(特殊)」不回归
- 落盘 JSON 的 `group_drop_info` 无 `_entity_name` 等内部键

## 历史方案（备查）

- **方案 A**：lootdrop 虚拟实体 — **采用并加固**
- **方案 B**：DB 虚拟 spawner — 废弃

## 后续

坐标混装与 100% 误赋：**不在本计划范围**。见 `docs/plans/PLAN_GOLDCHEST_SPECIAL_SPLIT.md`（`GoldChest_special` 独立 props 页）。
