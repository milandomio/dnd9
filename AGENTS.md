# DarkFindV5 Agent Instructions

## 术语约定

- "我看到" — 指在部署项目的 http://localhost:8080/ 中的某个页面上看到的内容
- "前端" — 指 web 目录
- "后端" — 指 api 目录
- "db" — 指 api/data/darkfindv5.db
- "坐标" — 指录入到db的spawners表中的道具/怪物实体实际在地图位置的数据，包含x、y、z三个REAL字段
- "部署" — 删除db → 运行后端管道 → 构建前端 → 启动web服务到localhost:8080
- "硬编码翻译" — 指 api/src/config.py 中 HARDCODED_TRANSLATIONS 字典里的翻译条目

## V4 参考目录

V4 项目通过符号链接提供只读参考：`v4_reference/`

| 文件 | 说明 |
|------|------|
| `v4_reference/group_config.json` | 分组翻译配置（Cave→哥布林洞穴1层 等） |
| `v4_reference/src/config.py` | MODULE_OFFSET_MAP、MODULE_DISPLAY_OVERRIDE、HARDCODED_TRANSLATIONS |
| `v4_reference/path_config.json` | V4 的路径配置 |
| `v4_reference/output/` | V4 生成的 HTML 页面 |

移植时参考这些文件，但不要修改 V4 原文件。

## MCP Tools

本项目配置了以下 MCP 服务器：

### 1. fmodel-query

用于查询 FModel 导出的游戏数据。

数据路径：`/home/mio/fmod/Output/Exports/DungeonCrawler/Content/DungeonCrawler/`

可用工具：
- `list_directory` — 浏览目录结构
- `search_files` — 按模式搜索文件（如 *.json, *.uasset）
- `read_file` — 读取文件内容
- `get_file_info` — 获取文件详细信息
- `search_json_keys` — 搜索包含特定 key 的 JSON 文件

使用场景：需要查看游戏解包数据时，优先使用 fmodel-query 工具。

### 2. sqlite-debug

用于调试时直接读写项目的 SQLite 数据库。

数据库路径：`/home/mio/fmod/DarkFindV5/api/data/darkfindv5.db`

可用工具：
- `query` — 执行 SQL SELECT 查询
- `execute` — 执行 SQL INSERT/UPDATE/DELETE
- `list_tables` — 列出所有表
- `describe_table` — 查看表结构
- `export_table` — 导出表数据为 JSON

使用场景：调试数据管道时，直接查询数据库验证数据。
