# 后端代码审计修复计划

> 审计日期: 2025-06-25
> 审计范围: `api/` 全部 50+ Python 源文件
> 发现问题: 60+ 个

---

## P0 — CRITICAL（需立即修复）

### C1. `get_all_spawner_entries` 返回未解析 JSON 字符串
- **文件**: `src/db/repositories/lootdrops.py:47-52`
- **问题**: `get_all_spawner_entries` 返回 `dict(r)` 直接使用数据库原始值，`dungeon_grades` 字段是 JSON 字符串 `"[]"` 而非 `list[int]`。同文件的 `get_spawner_entries_for_keyword`（line 41）做了 `json.loads()` 解析，但此方法遗漏了。
- **影响**: 调用方期望 `list` 但拿到 `str`，迭代或索引时 TypeError
- **修复**: 在返回前对 `dungeon_grades` 字段做 `json.loads()` 解析

### C2. `get_with_matches` JOIN 条件逻辑错误
- **文件**: `src/db/repositories/items.py:33`
- **问题**: `INSTR(l.item_name||'_', '_')` 只匹配第一个下划线位置，对含多下划线的物品名（如 `Health_Potion_Large`）会截断为 `Health` 做匹配
- **影响**: 物品与掉落数据关联错误
- **修复**: 重新设计 JOIN 条件，使用精确匹配或正确的分隔符解析

### C3. 暗黑模式 CSS 使用亮色主题颜色
- **文件**: `src/quest_extractor/html_template.py:466-505`
- **问题**: `CSS_STYLES_DARK` 中 `.quest-content-section`、`.quest-content-table` 等选择器的背景色和文字色直接复制自亮色主题（`#e3f2fd`、`#333`、`#666`），未适配 `#3a3a3a` 暗色背景
- **影响**: 暗色模式下内容表格低对比度/不可读
- **修复**: 将内容区域颜色改为适配暗色背景的值

### C4. HTML 内容未转义（XSS）
- **文件**: `src/quest_extractor/content_renderer.py:150-242, 652-701`、`page_builder.py:114-155`
- **问题**: 游戏数据（任务名、NPC名、描述、奖励名）直接拼接进 HTML，无 `html.escape()` 转义
- **影响**: 含 `<`、`>`、`&` 的游戏数据会破坏 HTML 结构
- **修复**: 所有内容插入 HTML 前调用 `html.escape()`

---

## P1 — HIGH（短期修复）

### H1. 资源泄漏：collector.run() 无 try/finally
- **文件**: `src/collector.py:397-398`
- **问题**: `db.close()` 和 `pipe.close()` 在 `run()` 尾部，管道任何一步异常都会跳过关闭
- **修复**: 用 `try/finally` 包裹整个管道逻辑

### H2. Pipeline 缺少 context manager
- **文件**: `src/pipeline.py:43-47`
- **问题**: 日志文件通过裸 `open()` 打开，仅靠 `Pipeline.close()` 关闭，无 `__enter__`/`__exit__` 协议
- **修复**: 实现 `__enter__`/`__exit__`，让 `close()` 自动执行

### H3. DatabaseManager 无连接生命周期管理
- **文件**: `src/db/__init__.py:14-16`
- **问题**: `sqlite3.connect()` 在构造函数中调用，无 context manager、无 `__del__`、无 `atexit`
- **修复**: 实现 context manager 协议

### H4. module_builder 异常类型错误
- **文件**: `src/module_builder.py:392-395`
- **问题**: `except KeyError` 捕获 `row["group_parent"]`，但 `sqlite3.Row` 访问不存在的列名抛 `IndexError`
- **修复**: 改为 `except (KeyError, IndexError)`

### H5. coordinates.py 变量遮蔽
- **文件**: `src/db/repositories/coordinates.py:39, 43`
- **问题**: 推导式 `{c["_dup_key"] for c in result[term]}` 中的 `c` 遮蔽了外层游标变量
- **修复**: 将推导式迭代变量改为其他名称（如 `row`）

### H6. quest_extractor O(N×M) 性能问题
- **文件**: `src/quest_extractor/quest_extractor.py:564-612`
- **问题**: `get_props_target_translation` 对每个任务遍历所有 Props JSON 文件并逐一解析
- **修复**: 初始化时构建 `IdTag -> translation` 索引 dict

### H7. page_builder rstrip 语义错误
- **文件**: `src/quest_extractor/page_builder.py:308`
- **问题**: `.rstrip('数量')` 是字符级去除，应为子串去除
- **修复**: 改用 `.removesuffix()` 或条件判断

### H8. translator.py 死代码 ORE_ITEM_STRIP_RE
- **文件**: `src/translator.py:18-19`
- **问题**: `ORE_ITEM_STRIP_RE` 与 `ORE_ITEM_COORD_RE` 完全相同且从未被引用
- **修复**: 删除 `ORE_ITEM_STRIP_RE`

---

## P2 — MEDIUM（中期优化）

### M1. spawners 操作无显式事务
- **文件**: `src/collector.py:152-176`
- **问题**: DELETE + executemany 依赖 SQLite 隐式事务，进程中断可能留空表
- **修复**: 使用 `conn.execute("BEGIN")` 显式事务

### M2. _helpers.py 静默吞异常
- **文件**: `src/db/_helpers.py:17-18, 33-34`
- **问题**: `except Exception: pass` 丢弃所有解析/IO 错误
- **修复**: 添加 logging.warning 输出错误信息

### M3. _strip_prefix 大小写不一致切片
- **文件**: `src/db/importers/lootdrops.py:76-79`
- **问题**: `.lower().startswith()` 做大小写不敏感匹配，但切片用原始前缀长度
- **修复**: 使用匹配到的实际前缀长度做切片

### M4. module_builder 重复目录扫描
- **文件**: `src/module_builder.py:28-124`
- **问题**: `_match_in_dir` 和 `_resolve_img` 对同一目录多次调用 `iterdir()`
- **修复**: 缓存目录文件列表，复用

### M5. lootdrop_builder 热循环内 import
- **文件**: `src/lootdrop_builder.py:272`
- **问题**: `from config import TRANSLATION_ALIAS_MAP` 在每次循环迭代中执行
- **修复**: 移至函数顶部或模块级别

### M6. entity_export O(n) 回退扫描
- **文件**: `src/entity_export.py:112-126`
- **问题**: 翻译失败时遍历整个 monsters 列表
- **修复**: 预建 `name -> row` 索引 dict

### M7. enrichment O(n*m) 缓存扫描
- **文件**: `src/enrichment.py:138-142`
- **问题**: spawn_rate_cache 未命中时遍历整个缓存 dict
- **修复**: 预建前缀索引

### M8. search_engine 死代码
- **文件**: `src/search_engine.py:319-320, 567-590`
- **问题**: 双 `continue`（第二个不可达）、`d_coords` 填充后未使用
- **修复**: 删除不可达代码和未使用变量

### M9. index_export GROUP_LABELS 重复定义
- **文件**: `src/index_export.py:159, 281`
- **问题**: 同一字典在两个函数中各定义一次
- **修复**: 提取为模块级常量

### M10. dungeon_mode int() 无保护
- **文件**: `src/dungeon_mode.py:27`
- **问题**: `int(grade)` 无 try/except，非数字输入会 ValueError
- **修复**: 添加异常处理或输入验证

### M11. fetch_checklist 硬编码中文字符串
- **文件**: `src/quest_extractor/fetch_checklist.py:75`
- **问题**: `r[8] != "不推荐NPC"` 硬编码中文
- **修复**: 改用 category 函数或枚举值判断

### M12. quest_extractor 三份重复的物品解析逻辑
- **文件**: `content_renderer.py:417-559`、`fetch_checklist.py:116-152`
- **问题**: Fetch/UseItem/Checklist 中 TypeTag/ItemIdTag 解析逻辑几乎相同
- **修复**: 抽取公共方法到共享模块

### M13. page_builder rfind HTML 插入脆弱
- **文件**: `src/quest_extractor/page_builder.py:337-353`
- **问题**: `rfind("            </div>")` 依赖特定缩进定位插入点
- **修复**: 用标记注释或模板引擎替代

### M14. 多处 except Exception 吞错误
- **文件**: `quest_extractor/content_loader.py:52,129`、`quest_extractor.py:253,291,501,560,609`
- **问题**: 捕获所有异常仅 print，掩盖真实 bug
- **修复**: 缩小异常范围，添加 logging

### M15. spawners commit 与 FTS 重建顺序
- **文件**: `src/db/importers/spawners.py:74-78`
- **问题**: fallback 实体先 commit 再重建 FTS，中间失败导致数据与索引不一致
- **修复**: 将 FTS 重建移入同一事务，或最后统一 commit

### M16. _rebuild_fts 四份重复实现
- **文件**: `db/__init__.py:31-34`、`importers/items.py:44-47`、`monsters.py:80-83`、`spawners.py:247-250`
- **问题**: 完全相同的方法在四个文件中各写一遍，且 `content_table` 参数从未使用
- **修复**: 统一到 `db/__init__.py`，删除死参数

---

## P3 — LOW（可选改进）

| 编号 | 文件 | 问题描述 | 修复建议 |
|------|------|----------|----------|
| L1 | `config.py:419-421` | 隐式字符串拼接构建路径 | 合并为单个字符串 |
| L2 | `pipeline_timer.py:33,48` | `summary()`/`save_log()` 调用 `end_step()` 有副作用 | 去除副作用或分离只读方法 |
| L3 | `_helpers.py:94` | `replace("/", "/")` 空操作 | 删除 |
| L4 | `_helpers.py:79` | `re.sub` 未预编译 | 改用模块级编译正则 |
| L5 | `translator.py:79-201` | 翻译前缀列表 5 处拷贝 | 提取为模块级元组 |
| L6 | `translator.py:108-114` | pass2 fuzzy 循环最多 3 次但实际幂等 | 简化为单次调用 |
| L7 | `entity_export.py:174` | 函数内 lazy import 不一致 | 移至模块顶部 |
| L8 | `lootdrop_builder.py:471` | `-1` 哨兵值 | 改为 `0.0` |
| L9 | `enrichment.py:34-264` | 多次读写同一文件 | 合并处理逻辑减少 I/O |
| L10 | `index_export.py:33-35` | quest_items.json 缺失时静默返回 | 添加日志警告 |
| L11 | `search_engine.py:412` | 重复编译同一正则 | 复用已有编译结果 |
| L12 | `search_engine.py:448` | 浮点数精确等于 0 判断 | 改用 `abs(x) > 1e-9` 容差 |
| L13 | `db/__init__.py:62-88` | 三次全表扫描做分类 | 合并为 UNION ALL 查询 |
| L14 | `importers/items.py:16-35` | 构建全行后去重 | 改用 dict 累积 variant count |
| L15 | `repositories/coordinates.py:39` | 嵌套 set 去重 O(n²) | 用独立 set 跟踪 |
| L16 | `quest_collector.py:346-350` | `_save_json` 从未调用 | 删除 |
| L17 | `quest_collector.py:329-343` | `_is_npc_active` 每次重建 set | 改为模块级 frozenset |
| L18 | `quest_collector.py:15` | 模块级可变全局缓存 | 改为参数传递 |
| L19 | `quest_extractor/__init__.py:1` | 注释引用旧项目名 findItemV3 | 更正为 DarkFindV5 |
| L20 | `page_builder.py:88,299` | 双反斜杠正则 `\\\\` 匹配双斜杠 | 改为 `\\` 匹配单斜杠 |
| L21 | `quest_extractor/translator.py:102` | Merchant 前缀过滤是空操作 | 修正过滤逻辑或删除 |
| L22 | `quest_extractor/file_indexer.py:54-57` | 重名文件静默覆盖 | 添加警告日志 |
| L23 | `quest_extractor/html_generator.py:22,59` | dark_mode 双来源（实例属性+参数） | 统一为单一来源 |

---

## 统计汇总

| 严重度 | 数量 | 修复周期 |
|--------|------|----------|
| CRITICAL | 4 | 立即 |
| HIGH | 8 | 1-2 天 |
| MEDIUM | 16 | 1 周内 |
| LOW | 23 | 可选 |
| **合计** | **51** | — |

---

## 修复顺序建议

1. **第一批（P0）**: C1-C4 — 数据正确性和安全性问题
2. **第二批（P1）**: H1-H5 — 资源管理和异常安全
3. **第三批（P2 部分）**: M2, M8, M14, M16 — 低风险清理
4. **第四批（P2 性能）**: M4, M6, M7 — 性能优化
5. **第五批（P2 结构）**: M9, M12, M13 — 代码重复治理
6. **最后（P3）**: L1-L23 — 代码质量改善
