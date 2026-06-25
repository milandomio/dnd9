# 后端代码审计修复计划

> 审计日期: 2025-06-25
> 审计范围: `api/` 全部 50+ Python 源文件
> 发现问题: 60+ 个
> 最后更新: 2025-06-25 (修复进度: 23/60+)

---

## ✅ 已修复（23 项）

| 编号 | 严重度 | 问题 | 修复 commit |
|------|--------|------|-------------|
| C1 | CRITICAL | `get_all_spawner_entries` 未解析 JSON | `ce0a4d0` |
| C2 | CRITICAL | `get_with_matches` JOIN 条件逻辑错误 | `4241979` |
| C3 | CRITICAL | 暗黑模式 CSS 颜色错误 | `9312d75` |
| C4 | CRITICAL | HTML 内容未转义（XSS） | `259c7ed` |
| H1 | HIGH | `collector.run()` 无 try/finally | `0d4e4c8` |
| H2 | HIGH | Pipeline 缺少 context manager | `0d4e4c8` |
| H3 | HIGH | DatabaseManager 缺少 context manager | `4a69489` |
| H4 | HIGH | `module_builder` 异常类型错误 | `a21c4a7` |
| H5 | HIGH | `coordinates.py` 变量遮蔽 | `f24ee76` |
| H7 | HIGH | `page_builder` rstrip 语义错误 | `314f48a` |
| H8 | HIGH | `translator.py` 死代码 ORE_ITEM_STRIP_RE | `6f6e13a` |
| M1 | MEDIUM | spawners 操作无显式事务 | `a7a08f1` |
| M2 | MEDIUM | `_helpers.py` 静默吞异常 | `325aa9f` |
| M5 | MEDIUM | `lootdrop_builder` 热循环内 import | `ed5162b` |
| M8 | MEDIUM | `search_engine.py` 死代码 | `3694f63` |
| M9 | MEDIUM | `index_export.py` GROUP_LABELS 重复定义 | `8a5d276` |
| M10 | MEDIUM | `dungeon_mode.py` int() 无保护 | `1ade77f` |
| M14 | MEDIUM | `content_loader` 异常吞错误用 print | `9275c9b` |
| M16 | MEDIUM | `_rebuild_fts` 死参数 content_table | `34e3a44` |
| L16 | LOW | `quest_collector._save_json` 死函数 | `350f524` |
| L17 | LOW | `_is_npc_active` 每次重建 set | `350f524` |

---

## P0 — CRITICAL（4/4 已完成）

### C1. `get_all_spawner_entries` 返回未解析 JSON 字符串
- **文件**: `src/db/repositories/lootdrops.py:47-52`
- **修复**: 在返回前对 `dungeon_grades` 字段做 `json.loads()` 解析 ✅ `ce0a4d0`

### C2. `get_with_matches` JOIN 条件逻辑错误
- **文件**: `src/db/repositories/items.py:33`
- **修复**: 在 lootdrops 导入时去掉变体后缀，将 JOIN 简化为等值连接 ✅ `4241979`

### C3. 暗黑模式 CSS 使用亮色主题颜色
- **文件**: `src/quest_extractor/html_template.py:466-505`
- **修复**: 将内容区域颜色改为适配暗色背景的值 ✅ `9312d75`

### C4. HTML 内容未转义（XSS）
- **文件**: `src/quest_extractor/content_renderer.py`、`page_builder.py`
- **修复**: 所有用户内容插入 HTML 前调用 `html.escape()` ✅ `259c7ed`

---

## P1 — HIGH（7/8 已完成）

### H1. 资源泄漏：collector.run() 无 try/finally
- **修复**: 用 try/finally 包裹整个管道逻辑 ✅ `0d4e4c8`

### H2. Pipeline 缺少 context manager
- **修复**: 实现 `__enter__`/`__exit__` ✅ `0d4e4c8`

### H3. DatabaseManager 无连接生命周期管理
- **修复**: 实现 context manager 协议 ✅ `4a69489`

### H4. module_builder 异常类型错误
- **修复**: 改为 `except (KeyError, IndexError)` ✅ `a21c4a7`

### H5. coordinates.py 变量遮蔽
- **修复**: 将推导式迭代变量改为 `item` ✅ `f24ee76`

### H6. quest_extractor O(N×M) 性能问题
- **文件**: `src/quest_extractor/quest_extractor.py:564-612`
- **状态**: ⏳ 需要设计索引方案，暂未修复

### H7. page_builder rstrip 语义错误
- **修复**: 改用 `removesuffix()` ✅ `314f48a`

### H8. translator.py 死代码 ORE_ITEM_STRIP_RE
- **修复**: 删除未使用的正则 ✅ `6f6e13a`

---

## P2 — MEDIUM（8/16 已完成）

### 已修复

| 编号 | 问题 | commit |
|------|------|--------|
| M1 | spawners DELETE+INSERT 无显式事务 | `a7a08f1` |
| M2 | `_helpers.py` 静默吞异常 | `325aa9f` |
| M5 | `lootdrop_builder` 热循环内 import | `ed5162b` |
| M8 | `search_engine.py` 死代码 | `3694f63` |
| M9 | `index_export.py` GROUP_LABELS 重复定义 | `8a5d276` |
| M10 | `dungeon_mode.py` int() 无保护 | `1ade77f` |
| M14 | `content_loader` 异常吞错误用 print | `9275c9b` |
| M16 | `_rebuild_fts` 死参数 content_table | `34e3a44` |

### 待修复

| 编号 | 文件 | 问题描述 |
|------|------|----------|
| M3 | `importers/lootdrops.py:76-79` | `_strip_prefix` 大小写不一致切片（实际无风险，已评估） |
| M4 | `module_builder.py:28-124` | `_match_in_dir`/`_resolve_img` 重复目录扫描 |
| M6 | `entity_export.py:112-126` | 翻译失败时 O(n) 线性扫描 monsters 列表 |
| M7 | `enrichment.py:138-142` | spawn_rate_cache 未命中时 O(n) 遍历整个缓存 |
| M11 | `fetch_checklist.py:75` | 硬编码中文字符串 `"不推荐NPC"` |
| M12 | `content_renderer.py` | Fetch/UseItem/Checklist 物品解析逻辑三份重复 |
| M13 | `page_builder.py:337-353` | `rfind("</div>")` 定位 HTML 插入点极其脆弱 |
| M15 | `importers/spawners.py:74-78` | commit 与 FTS 重建顺序导致不一致风险 |

---

## P3 — LOW（2/23 已完成）

### 已修复

| 编号 | 问题 | commit |
|------|------|--------|
| L16 | `quest_collector._save_json` 死函数 | `350f524` |
| L17 | `_is_npc_active` 每次重建 set | `350f524` |

### 待修复

| 编号 | 文件 | 问题描述 |
|------|------|----------|
| L1 | `config.py:419-421` | 隐式字符串拼接构建路径 |
| L2 | `pipeline_timer.py:33,48` | `summary()`/`save_log()` 调用 `end_step()` 有副作用 |
| L3 | `_helpers.py:94` | `replace("/", "/")` 空操作 |
| L4 | `_helpers.py:79` | `re.sub` 未预编译 |
| L5 | `translator.py:79-201` | 翻译前缀列表 5 处拷贝 |
| L6 | `translator.py:108-114` | pass2 fuzzy 循环最多 3 次但实际幂等 |
| L7 | `entity_export.py:174` | 函数内 lazy import 不一致 |
| L8 | `lootdrop_builder.py:471` | `-1` 哨兵值 |
| L9 | `enrichment.py:34-264` | 多次读写同一文件 |
| L10 | `index_export.py:33-35` | quest_items.json 缺失时静默返回 |
| L11 | `search_engine.py:412` | 重复编译同一正则 |
| L12 | `search_engine.py:448` | 浮点数精确等于 0 判断 |
| L13 | `db/__init__.py:62-88` | 三次全表扫描做分类 |
| L14 | `importers/items.py:16-35` | 构建全行后去重 |
| L15 | `repositories/coordinates.py:39` | 嵌套 set 去重 O(n²) |
| L18 | `quest_collector.py:15` | 模块级可变全局缓存 |
| L19 | `quest_extractor/__init__.py:1` | 注释引用旧项目名 findItemV3 |
| L20 | `page_builder.py:88,299` | 双反斜杠正则 `\\\\` 匹配双斜杠 |
| L21 | `quest_extractor/translator.py:102` | Merchant 前缀过滤是空操作 |
| L22 | `quest_extractor/file_indexer.py:54-57` | 重名文件静默覆盖 |
| L23 | `quest_extractor/html_generator.py:22,59` | dark_mode 双来源 |

---

## 统计汇总

| 严重度 | 总数 | 已修复 | 待修复 |
|--------|------|--------|--------|
| CRITICAL | 4 | 4 | 0 |
| HIGH | 8 | 7 | 1 (H6) |
| MEDIUM | 16 | 8 | 8 |
| LOW | 23 | 2 | 21 |
| **合计** | **51** | **21** | **30** |

---

## 修复顺序建议

1. ~~第一批（P0）: C1-C4~~ ✅ 已完成
2. ~~第二批（P1）: H1-H5, H7-H8~~ ✅ 已完成
3. ~~第三批（P2 部分）: M1, M2, M5, M8, M9, M10, M14, M16~~ ✅ 已完成
4. ~~第四批（LOW 部分）: L16, L17~~ ✅ 已完成
5. 第五批（P2 剩余）: M4, M6, M7 — 性能优化
6. 第六批（P2 结构）: M11, M12, M13, M15 — 代码重复治理
7. 第七批（H6）: quest_extractor O(N×M) 性能优化
8. 最后（P3）: L1-L15, L18-L23 — 代码质量改善
