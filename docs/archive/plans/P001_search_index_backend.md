# P001: search_index.json 生成后移到 Python 管道

## 目标

消除 Python 与 Node/SSG 间的逻辑重复，统一数据入口。

## 改动点

### api/src/collector.py

在已有 JSON 导出流程末尾追加 search_index 构造 + `_save()`：

- items/monsters/props/lootdrops 四条 list：遍历并构造搜索条目
- quest_npc：遍历 questNpcData 构造条目
- dungeon_modules 分组和详情：遍历 modules_data 构造条目
- 导航页（items 列表页等）：固定条目
- props 条目携带 `type` 字段
- 分组标签使用 `quest_collector.py` 中已定义的 GROUP_LABELS，消除 ssg.mjs 中重定义
- 使用 `urllib.parse.quote` 编码 URL

### web/scripts/ssg.mjs

删除：
- 搜索索引构建块（约第 56-133 行）
- GROUP_LABELS 定义
- 复制的 `search_index.json` 文件操作（SSG 会通过数据复制步骤自动复制）

## 不动的

- 前端搜索组件（`/data/json/search_index.json` 接口不变）
- 其他 SSG 逻辑
- 数据管道流程

## 验证

1. `cd api && python main.py` → 确认 `api/output/json/search_index.json` 生成
2. 对比新的 search_index.json 与原版本（从 `data/json/` 或构建产物读旧版本）
3. `cd web && npm run build` → 确认无构建错误
4. 启动 web 确认搜索功能正常

---

## 完成状态

| 项 | 状态 | 完成时间 |
|----|------|---------|
| Python 管道生成 `search_index.json` | ✅ 完成 | 2026-06-22 |
| ssg.mjs 删除搜索索引构建块 | ✅ 完成 | 2026-06-22 |
| GROUP_LABELS 统一为 quest_collector.py 定义 | ✅ 完成 | 2026-06-22 |
| 前端搜索功能正常 | ✅ 验证通过 | 2026-06-25 |
