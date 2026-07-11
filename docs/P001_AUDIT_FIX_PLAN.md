# P001: 后端审计待修复问题清单

> 来源: `BACKEND_AUDIT_FIX_PLAN.md` 中未修复的 30 项
> 创建日期: 2026-07-11
> 完成日期: 2026-07-11

---

## H6 — HIGH（1 项）✅

### H6. quest_extractor O(N×M) 性能问题
- **文件**: `src/quest_extractor/quest_extractor.py`
- **修复**: 预建 `_props_tag_index` 字典，查询 O(1)
- **commit**: `ab6923b`

---

## M — MEDIUM（8 项）

| # | 状态 | 说明 | commit |
|---|------|------|--------|
| M3 | ⏭️ 跳过 | 实际无风险，已评估 | - |
| M4 | ✅ | 目录缓存 `_list_dir_files` | `2f1438a` |
| M6 | ✅ | 预建 `_monsters_by_name` 字典 | `bce4852` |
| M7 | ✅ | 预建 `_spawner_ldg_lower` 字典 | `8002081` |
| M11 | ✅ | 提取分类常量 | `573983c` |
| M12 | ✅ | 提取 `_resolve_item_target` | `019c354` |
| M13 | ✅ | 占位符替换 `rfind` | `54c55ad` |
| M15 | ⏭️ 跳过 | SQLite commit 后无法回滚，FTS 幂等 | - |

---

## L — LOW（21 项）

| # | 状态 | 说明 | commit |
|---|------|------|--------|
| L1 | ✅ | 显式字符串拼接 | `a0af5b1` |
| L2 | ✅ | 移除 `end_step` 副作用 | `3c219f8` |
| L3 | ✅ | 删除空操作 `replace` | `a90f081` |
| L4 | ✅ | 预编译 `_Dummy` 正则 | `3a8f777` |
| L5 | ✅ | 提取 `_TRANSLATION_PREFIXES` | `fffd96e` |
| L6 | ✅ | `while True` 替代 `range(3)` | `568f036` |
| L7 | ✅ | 移除 lazy import | `d5db3e4` |
| L8 | ✅ | 提取 `_NO_SCORE` 常量 | `8ad0d7c` |
| L9 | ⏭️ 跳过 | 两个循环处理不同数据源，无重叠 | - |
| L10 | ✅ | 添加 warning 日志 | `a68eb45` |
| L11 | ✅ | 移至模块级 `_AP_SUFFIX_RE` | `831afb7` |
| L12 | ⏭️ 跳过 | 无此问题 | - |
| L13 | ⏭️ 跳过 | 合并需大量重构，收益低 | - |
| L14 | ✅ | 循环内去重 | `23e390d` |
| L15 | ✅ | per-term `seen_keys` 集合 | `ab337e2` |
| L18 | ✅ | 函数属性缓存替代全局变量 | `61b2a05` |
| L19 | ✅ | 更新注释为 DarkFindV5 | `471a94d` |
| L20 | ✅ | 单反斜杠正则 | `fb20258` |
| L21 | ✅ | 删除空操作条件 | `f136097` |
| L22 | ✅ | 添加 duplicate warning 日志 | `becc2ae` |
| L23 | ✅ | 移除冗余 `dark_mode` 参数 | `4b54ee5` |

---

## 统计

| 状态 | 数量 |
|------|------|
| ✅ 已修复 | 24 |
| ⏭️ 跳过 | 6 |
| **合计** | **30** |
