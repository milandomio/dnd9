# P001: 后端审计待修复问题清单

> 来源: `BACKEND_AUDIT_FIX_PLAN.md` 中未修复的 30 项
> 创建日期: 2026-07-11
> 优先级: H6(1) + M(8) + L(21) = 30 项

---

## H6 — HIGH（1 项）

### H6. quest_extractor O(N×M) 性能问题
- **文件**: `src/quest_extractor/quest_extractor.py:564-612`
- **问题**: 每次调用 `get_explore_target_translation` 时遍历所有任务查找匹配的 asset_path，O(N×M) 复杂度
- **修复方案**: 构建预索引 `{asset_path → translation}` 字典，查询时 O(1)
- **修改位置**: QuestExtractor 初始化时预建索引，`get_explore_target_translation` 改为字典查找

---

## M — MEDIUM（8 项）

### M3. `_strip_prefix` 大小写不一致切片
- **文件**: `src/db/importers/lootdrops.py:78-82`
- **问题**: 大小写不一致切片（实际无风险，已评估）
- **修复方案**: 低优先级，可跳过或添加注释说明

### M4. `_match_in_dir`/`_resolve_img` 重复目录扫描
- **文件**: `src/module_builder.py:26-124`
- **问题**: `_resolve_img` 每次调用都 `iterdir()` 扫描目录，`_match_in_dir` 也重复扫描
- **修复方案**: 添加目录缓存 `{directory → [(stem, path)]}`，同一目录只扫描一次
- **修改位置**: 新增模块级 `dir_cache: dict[Path, list[Path]]`，两个函数优先从缓存读取

### M6. 翻译失败时 O(n) 线性扫描 monsters 列表
- **文件**: `src/entity_export.py:112-126`（export_monsters 函数内）
- **问题**: 翻译失败时遍历 monsters 列表查找 translation_key
- **修复方案**: 提前构建 `{monster_name → translation_key}` 字典
- **修改位置**: 在函数开头构建 `_monster_tk_map = {r["monster_name"]: r["translation_key"] for r in monsters}`

### M7. spawn_rate_cache 未命中时 O(n) 遍历整个缓存
- **文件**: `src/enrichment.py:138-142`
- **问题**: `spawn_rate_cache.get(key)` 未命中时遍历整个缓存寻找近似匹配
- **修复方案**: 预构建二级索引，按 `(map_base, json_filename)` 分组
- **修改位置**: 在 `DropRateEngine.preload()` 中构建 `_grouped_cache: dict[tuple, dict]`

### M11. 硬编码中文 `"不推荐NPC"`
- **文件**: `src/quest_extractor/fetch_checklist.py:75`
- **问题**: `r[8] != "不推荐NPC"` 硬编码中文
- **修复方案**: 提取为模块级常量
- **修改位置**: 定义 `_NOT_RECOMMENDED_CATEGORY = "不推荐NPC"`，引用该常量

### M12. Fetch/UseItem/Checklist 物品解析逻辑三份重复
- **文件**: `src/quest_extractor/content_renderer.py`
- **问题**: `_render_fetch_target`、`_render_useitem_target`、`quest_collector._parse_fetch_content` 逻辑重复
- **修复方案**: 提取公共方法 `_resolve_item_target(content_data)` 返回 `(target_name, loot_state, rarity)`
- **修改位置**: 新增私有方法，三处调用改为调用公共方法

### M13. `rfind("</div>")` 定位 HTML 插入点脆弱
- **文件**: `src/quest_extractor/page_builder.py:340`
- **问题**: 用 `rfind("            </div>")` 定位插入点，HTML 结构变化即失效
- **修复方案**: 改用 `replace()` 或模板标记（如 `<!-- QUEST_CONTENT -->`）
- **修改位置**: 在 `_build_quest_card` 末尾添加占位符，`build_npc_page` 中用 `replace()` 替换

### M15. commit 与 FTS 重建顺序导致不一致风险
- **文件**: `src/db/importers/spawners.py:74-78`
- **问题**: `self.conn.commit()` 后才 `_rebuild_fts()`，FTS 重建失败则数据不一致
- **修复方案**: 将 FTS 重建移到 commit 之前，或用 try/except 包裹
- **修改位置**: 调整 `import_spawner_fallback_entities` 中 commit 和 FTS 重建的顺序

---

## L — LOW（21 项）

### L1. 隐式字符串拼接构建路径
- **文件**: `src/config.py:419-421`
- **问题**: `"Output/Exports/..." "/Data/..."` 隐式拼接
- **修复方案**: 改为显式拼接或 f-string

### L2. `summary()`/`save_log()` 调用 `end_step()` 有副作用
- **文件**: `src/pipeline_timer.py:33,48`
- **问题**: 读取方法内部修改状态
- **修复方案**: 移除 `end_step()` 调用，或改用 `@property` 标记

### L3. `replace("/", "/")` 空操作
- **文件**: `src/db/_helpers.py:98`
- **问题**: 替换相同字符
- **修复方案**: 删除该调用

### L4. `re.sub` 未预编译
- **文件**: `src/db/_helpers.py`
- **修复方案**: 将热路径正则提取为模块级 `re.compile()`

### L5. 翻译前缀列表 5 处拷贝
- **文件**: `src/translator.py:78-201`
- **修复方案**: 提取为模块级常量 `_TRANSLATION_PREFIXES`

### L6. pass2 fuzzy 循环幂等但迭代 3 次
- **文件**: `src/translator.py:107-114`
- **修复方案**: 改为 `while fuzzy2 != prev:` 无限循环 + break

### L7. 函数内 lazy import 不一致
- **文件**: `src/entity_export.py`
- **修复方案**: 统一为顶部导入

### L8. `-1` 哨兵值
- **文件**: `src/lootdrop_builder.py`
- **修复方案**: 改为 `None` 或专门常量

### L9. 多次读写同一文件
- **文件**: `src/enrichment.py`
- **修复方案**: 读取一次到内存，修改后统一写回

### L10. quest_items.json 缺失时静默返回
- **文件**: `src/index_export.py:46`
- **修复方案**: 添加日志警告

### L11. 重复编译同一正则
- **文件**: `src/search_engine.py:412`
- **修复方案**: 提取为模块级常量

### L12. 浮点数精确等于 0 判断
- **文件**: `src/search_engine.py:448`
- **修复方案**: 改为 `abs(x) < 1e-9`

### L13. 三次全表扫描做分类
- **文件**: `src/db/__init__.py:69-95`
- **修复方案**: 改为单次遍历构建分类

### L14. 构建全行后去重
- **文件**: `src/db/importers/items.py`
- **修复方案**: 使用 `seen` 集合边构建边去重

### L15. 嵌套 set 去重 O(n²)
- **文件**: `src/db/repositories/coordinates.py:39`
- **修复方案**: 使用 `dict.fromkeys()` 或预构建 `seen` 集合

### L18. 模块级可变全局缓存
- **文件**: `src/quest_collector.py:29`
- **修复方案**: 改为函数内局部变量或类属性

### L19. 注释引用旧项目名 findItemV3
- **文件**: `src/quest_extractor/__init__.py:1`
- **修复方案**: 更新注释为 DarkFindV5

### L20. 双反斜杠正则
- **文件**: `src/quest_extractor/page_builder.py:88,299`
- **修复方案**: 改用单反斜杠 raw string `r'...'`

### L21. Merchant 前缀过滤是空操作
- **文件**: `src/quest_extractor/translator.py:102`
- **修复方案**: 验证是否真为空操作，如是则删除条件或修复逻辑

### L22. 重名文件静默覆盖
- **文件**: `src/quest_extractor/file_indexer.py:54-57`
- **修复方案**: 添加警告日志或使用 `dict` 保留所有路径

### L23. dark_mode 双来源
- **文件**: `src/quest_extractor/html_generator.py:22,59`
- **修复方案**: 统一 dark_mode 参数来源，移除冗余

---

## 执行顺序建议

1. **H6** — 性能最关键
2. **M4, M6, M7** — 性能优化
3. **M11, M12, M13, M15** — 代码结构
4. **L1-L23** — 代码质量（可按需选择）
