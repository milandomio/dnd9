# DarkFindV5 Agent Instructions

## 术语约定

- "我看到" — 指在部署项目的 http://localhost:8080/ 中的某个页面上看到的内容
- "前端" — 指 web 目录
- "后端" — 指 api 目录
- "db" — 指 api/data/darkfindv5.db
- "坐标" — 指录入到db的spawners表中的道具/怪物实体实际在地图位置的数据，包含x、y、z三个REAL字段
- "rotate" — 指模块(dungeon_module)在地图中的旋转角度，单位为度(0-359.9)，来自Layout JSON的LevelTransform.Rotation四元数
- "yaw" — 指单个spawner实体在模块内的自身旋转角度，单位为度(0-359.9)，来自模块地图JSON的RelativeRotation.Yaw
- "部署" — 删除db → 运行后端管道 → 构建前端 → 启动web服务到localhost:8080

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
