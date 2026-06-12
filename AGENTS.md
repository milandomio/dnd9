# DarkFindV5 Agent Instructions

## 术语约定

- "我看到" — 部署后 http://localhost:8080/ 上的内容
- "前端" — `web/`，"后端" — `api/`，"db" — `api/data/darkfindv5.db`
- "坐标" — spawners 表中 x/y/z 三个 REAL 字段
- "启动web" — `cd web && kill $(lsof -t -i:8080) 2>/dev/null; sleep 0.5; (npx vite preview --port 8080 --host 0.0.0.0 &>/dev/null &) && echo "web started"`

## V4 参考

符号链接 `v4_reference/` 提供只读参考（不要修改）：
- `group_config.json` — 分组翻译配置
- `src/config.py` — MODULE_OFFSET_MAP、HARDCODED_TRANSLATIONS

## MCP Tools

### fmodel-query
查询游戏解包数据（`/home/mio/fmod/Output/Exports/DungeonCrawler/...`）。
工具：`list_directory`、`search_files`、`read_file`、`get_file_info`、`search_json_keys`

### sqlite-debug
直接读写 `api/data/darkfindv5.db`。
工具：`query`、`execute`、`list_tables`、`describe_table`、`export_table`
