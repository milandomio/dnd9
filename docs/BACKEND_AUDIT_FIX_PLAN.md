# 后端代码审计修复计划

> 审计日期: 2025-06-25
> 审计范围: `api/` 全部 50+ Python 源文件
> 发现问题: 60+ 个
> 最后更新: 2026-07-11 (验证完成: 21/51 已确认修复)

---

## ✅ 已修复并验证（21 项）

| 编号 | 严重度 | 问题 | 修复 commit | 验证状态 |
|------|--------|------|-------------|----------|
| C1 | CRITICAL | `get_all_spawner_entries` 未解析 JSON | `ce0a4d0` | ✅ 已验证 |
| C2 | CRITICAL | `get_with_matches` JOIN 条件逻辑错误 | `4241979` | ✅ 已验证 |
| C3 | CRITICAL | 暗黑模式 CSS 颜色错误 | `9312d75` | ✅ 已验证 |
| C4 | CRITICAL | HTML 内容未转义（XSS） | `259c7ed` | ✅ 已验证 |
| H1 | HIGH | `collector.run()` 无 try/finally | `0d4e4c8` | ✅ 已验证 |
| H2 | HIGH | Pipeline 缺少 context manager | `0d4e4c8` | ✅ 已验证 |
| H3 | HIGH | DatabaseManager 缺少 context manager | `4a69489` | ✅ 已验证 |
| H4 | HIGH | `module_builder` 异常类型错误 | `a21c4a7` | ✅ 已验证 |
| H5 | HIGH | `coordinates.py` 变量遮蔽 | `f24ee76` | ✅ 已验证 |
| H7 | HIGH | `page_builder` rstrip 语义错误 | `314f48a` | ✅ 已验证 |
| H8 | HIGH | `translator.py` 死代码 ORE_ITEM_STRIP_RE | `6f6e13a` | ✅ 已验证 |
| M1 | MEDIUM | spawners 操作无显式事务 | `a7a08f1` | ✅ 已验证 |
| M2 | MEDIUM | `_helpers.py` 静默吞异常 | `325aa9f` | ✅ 已验证 |
| M5 | MEDIUM | `lootdrop_builder` 热循环内 import | `ed5162b` | ✅ 已验证 |
| M8 | MEDIUM | `search_engine.py` 死代码 | `3694f63` | ✅ 已验证 |
| M9 | MEDIUM | `index_export.py` GROUP_LABELS 重复定义 | `8a5d276` | ✅ 已验证 |
| M10 | MEDIUM | `dungeon_mode.py` int() 无保护 | `1ade77f` | ✅ 已验证 |
| M14 | MEDIUM | `content_loader` 异常吞错误用 print | `9275c9b` | ✅ 已验证 |
| M16 | MEDIUM | `_rebuild_fts` 死参数 content_table | `34e3a44` | ✅ 已验证 |
| L16 | LOW | `quest_collector._save_json` 死函数 | `350f524` | ✅ 已验证 |
| L17 | LOW | `_is_npc_active` 每次重建 set | `350f524` | ✅ 已验证 |

---

## P0 — CRITICAL（4/4 已完成）✅

### C1. `get_all_spawner_entries` 返回未解析 JSON 字符串
- **文件**: `src/db/repositories/lootdrops.py:47-52`
- **修复**: 在返回前对 `dungeon_grades` 字段做 `json.loads()` 解析 ✅ `ce0a4d0`
- **验证**: Line 59 已有 `json.loads(r["dungeon_grades"])` 调用

### C2. `get_with_matches` JOIN 条件逻辑错误
- **文件**: `src/db/repositories/items.py:33`
- **修复**: 在 lootdrops 导入时去掉变体后缀，将 JOIN 简化为等值连接 ✅ `4241979`
- **验证**: Line 36 使用 `ON e.item_name = l.item_name` 简化连接

### C3. 暗黑模式 CSS 使用亮色主题颜色
- **文件**: `src/quest_extractor/html_template.py:466-505`
- **修复**: 将内容区域颜色改为适配暗色背景的值 ✅ `9312d75`
- **验证**: Line 466 使用 `background-color: #1a3040` 暗色值

### C4. HTML 内容未转义（XSS）
- **文件**: `src/quest_extractor/content_renderer.py`、`page_builder.py`
- **修复**: 所有用户内容插入 HTML 前调用 `html.escape()` ✅ `259c7ed`
- **验证**: Line 8 导入 `from html import escape as _esc`，全文使用 `_esc()` 函数

---

## P1 — HIGH（7/8 已完成）

### H1. 资源泄漏：collector.run() 无 try/finally
- **修复**: 用 try/finally 包裹整个管道逻辑 ✅ `0d4e4c8`
- **验证**: `collector.py:99` 有 `try:`，`collector.py:434` 有 `finally:`

### H2. Pipeline 缺少 context manager
- **修复**: 实现 `__enter__`/`__exit__` ✅ `0d4e4c8`
- **验证**: `pipeline.py:70-74` 实现了 `__enter__` 和 `__exit__` 方法

### H3. DatabaseManager 无连接生命周期管理
- **修复**: 实现 context manager 协议 ✅ `4a69489`
- **验证**: `db/__init__.py:31-36` 实现了 `__enter__` 和 `__exit__` 方法

### H4. module_builder 异常类型错误
- **修复**: 改为 `except (KeyError, IndexError)` ✅ `a21c4a7`
- **验证**: 异常处理已修正为正确的异常类型

### H5. coordinates.py 变量遮蔽
- **修复**: 将推导式迭代变量改为 `item` ✅ `f24ee76`
- **验证**: `db/repositories/coordinates.py:39` 使用 `for item in result[term]`

### H6. quest_extractor O(N×M) 性能问题
- **文件**: `src/quest_extractor/quest_extractor.py:564-612`
- **状态**: ⏳ 需要设计索引方案，暂未修复
- **说明**: 这是唯一未完成的 HIGH 级别问题

### H7. page_builder rstrip 语义错误
- **修复**: 改用 `removesuffix()` ✅ `314f48a`
- **验证**: `quest_collector.py:125-128` 使用 `.removesuffix()` 方法

### H8. translator.py 死代码 ORE_ITEM_STRIP_RE
- **修复**: 删除未使用的正则 ✅ `6f6e13a`
- **验证**: `translator.py` 中已无 `ORE_ITEM_STRIP_RE` 定义

---

## P2 — MEDIUM（8/16 已完成）

### 已修复并验证

| 编号 | 问题 | commit | 验证位置 |
|------|------|--------|----------|
| M1 | spawners DELETE+INSERT 无显式事务 | `a7a08f1` | `collector.py:158` — `c.execute("BEGIN")` |
| M2 | `_helpers.py` 静默吞异常 | `325aa9f` | `_helpers.py:21` — `log.warning(...)` |
| M5 | `lootdrop_builder` 热循环内 import | `ed5162b` | 导入在模块顶部 |
| M8 | `search_engine.py` 死代码 | `3694f63` | 无明显死代码残留 |
| M9 | `index_export.py` GROUP_LABELS 重复定义 | `8a5d276` | `index_export.py:9-19` 单一定义 |
| M10 | `dungeon_mode.py` int() 无保护 | `1ade77f` | `dungeon_mode.py:27-29` — try/except |
| M14 | `content_loader` 异常吞错误用 print | `9275c9b` | `content_loader.py:11` — `logging.getLogger()` |
| M16 | `_rebuild_fts` 死参数 content_table | `34e3a44` | `db/__init__.py:38` — 仅 `fts_table` 参数 |

### 待修复（8 项）

| 编号 | 文件 | 问题描述 | 优先级 |
|------|------|----------|--------|
| M3 | `importers/lootdrops.py:78-82` | `_strip_prefix` 大小写不一致切片（实际无风险，已评估） | 低 |
| M4 | `module_builder.py:26-124` | `_match_in_dir`/`_resolve_img` 重复目录扫描 | 中 |
| M6 | `entity_export.py` | 翻译失败时 O(n) 线性扫描 monsters 列表 | 中 |
| M7 | `enrichment.py` | spawn_rate_cache 未命中时 O(n) 遍历整个缓存 | 中 |
| M11 | `fetch_checklist.py:75` | 硬编码中文字符串 `"不推荐NPC"` | 低 |
| M12 | `content_renderer.py` | Fetch/UseItem/Checklist 物品解析逻辑三份重复 | 中 |
| M13 | `quest_extractor/page_builder.py:340` | `rfind("</div>")` 定位 HTML 插入点极其脆弱 | 中 |
| M15 | `importers/spawners.py` | commit 与 FTS 重建顺序导致不一致风险 | 中 |

---

## P3 — LOW（2/23 已完成）

### 已修复并验证

| 编号 | 问题 | commit | 验证位置 |
|------|------|--------|----------|
| L16 | `quest_collector._save_json` 死函数 | `350f524` | 函数不存在 |
| L17 | `_is_npc_active` 每次重建 set | `350f524` | `quest_collector.py:13-27` — 模块级 `frozenset` |

### 待修复（21 项）

| 编号 | 文件 | 问题描述 | 优先级 |
|------|------|----------|--------|
| L1 | `config.py:419-421` | 隐式字符串拼接构建路径 | 低 |
| L2 | `pipeline_timer.py:33,48` | `summary()`/`save_log()` 调用 `end_step()` 有副作用 | 低 |
| L3 | `_helpers.py:98` | `replace("/", "/")` 空操作 | 低 |
| L4 | `_helpers.py` | `re.sub` 未预编译 | 低 |
| L5 | `translator.py:78-201` | 翻译前缀列表 5 处拷贝 | 低 |
| L6 | `translator.py:107-114` | pass2 fuzzy 循环最多 3 次但实际幂等 | 低 |
| L7 | `entity_export.py` | 函数内 lazy import 不一致 | 低 |
| L8 | `lootdrop_builder.py` | `-1` 哨兵值 | 低 |
| L9 | `enrichment.py` | 多次读写同一文件 | 低 |
| L10 | `index_export.py:46` | quest_items.json 缺失时静默返回 | 低 |
| L11 | `search_engine.py` | 重复编译同一正则 | 低 |
| L12 | `search_engine.py` | 浮点数精确等于 0 判断 | 低 |
| L13 | `db/__init__.py:69-95` | 三次全表扫描做分类 | 低 |
| L14 | `importers/items.py` | 构建全行后去重 | 低 |
| L15 | `repositories/coordinates.py:39` | 嵌套 set 去重 O(n²) | 低 |
| L18 | `quest_collector.py:29` | 模块级可变全局缓存 | 低 |
| L19 | `quest_extractor/__init__.py:1` | 注释引用旧项目名 findItemV3 | 低 |
| L20 | `quest_extractor/page_builder.py:88,299` | 双反斜杠正则 `\\\\` | 低 |
| L21 | `quest_extractor/translator.py:102` | Merchant 前缀过滤是空操作 | 低 |
| L22 | `quest_extractor/file_indexer.py:54-57` | 重名文件静默覆盖 | 低 |
| L23 | `quest_extractor/html_generator.py:22,59` | dark_mode 双来源 | 低 |

---

## 统计汇总

| 严重度 | 总数 | 已修复验证 | 待修复 |
|--------|------|-----------|--------|
| CRITICAL | 4 | 4 | 0 |
| HIGH | 8 | 7 | 1 (H6) |
| MEDIUM | 16 | 8 | 8 |
| LOW | 23 | 2 | 21 |
| **合计** | **51** | **21** | **30** |

---

## 修复顺序建议

1. ~~第一批（P0）: C1-C4~~ ✅ 已完成并验证
2. ~~第二批（P1）: H1-H5, H7-H8~~ ✅ 已完成并验证
3. ~~第三批（P2 部分）: M1, M2, M5, M8, M9, M10, M14, M16~~ ✅ 已完成并验证
4. ~~第四批（LOW 部分）: L16, L17~~ ✅ 已完成并验证
5. **第五批（H6）**: quest_extractor O(N×M) 性能优化 — 优先级最高
6. **第六批（M2 部分）**: M4, M6, M7 — 性能优化
7. **第七批（M2 结构）**: M11, M12, M13, M15 — 代码重复治理
8. **最后（P3）**: L1-L23 — 代码质量改善（可按需选择）

---

## 📋 迁移说明

**待修复的 30 项已迁移至 `docs/P001_AUDIT_FIX_PLAN.md`**，本文档仅保留已验证修复的 21 项记录。

迁移项目: H6, M3-M15, L1-L23
