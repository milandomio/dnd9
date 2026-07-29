# DB-Only Runtime I/O Plan

目标：除 `api/src/db/importers/*` 的预载入阶段外，后端、前端和 SSG 运行时都不能再直接读取 `Output/Exports/...`、`Localization/Game/...` 或其他解包目录；运行时只允许读 `api/data/darkfindv5.db` 和由它生成的派生产物。

## 允许范围

- `api/src/db/importers/*`：只在 `python main.py` 预载入阶段使用，用解包文件批量写入 DB。
- `api/src/db/repositories/*`：所有运行时查询统一走这里。
- `data/json/*`：仅作为 DB 导出的静态派生数据，前端和 SSG 可以读取。

## 修复顺序

1. `api/src/db/_helpers.py` 和 `api/src/db/__init__.py`
   - 移除共享层里的 `load_game_json()`、`discover_languages()` 等解包目录访问。
   - 只保留 DB 连接、仓库入口和表结构相关逻辑。

2. `api/src/quest_extractor/*`
   - 停止在运行时读取 `Quest`、`QuestContent`、`QuestReward`、`Localization/Game`。
   - 任务、奖励、模块目标和 props 目标必须先写入 DB，再从 DB 查询。

3. `api/src/search_engine.py` 和 `api/src/layout_utils.py`
   - 停止扫描 `SPAWNER_DIR`、`MAPS_DIR`、`LAYOUT_DIR`。
   - 改为读取 DB 中已经导入的 spawner / map / rotation 数据。

4. `api/src/module_builder.py` 和 `api/src/image_utils.py`
   - 停止读取 `DungeonModuleMapImage` 目录。
   - 图片名、旋转、模块关联等元数据必须由 DB 提供，静态资源只作为已交付产物使用。

5. `api/src/locale_builder.py`、`api/src/search_index_builder.py`、`api/src/enrichment.py`、`api/src/collector.py`
   - 清理任何对游戏解包目录的二次读取。
   - 仅消费 DB 查询结果和已有导出产物，不再回退到解包文件。

6. 运行时守卫
   - 增加测试或检查，禁止 `api/src` 的运行时模块引用 `Output/Exports`、`Localization/Game`、`MAPS_DIR`、`LAYOUT_DIR`、`SPAWNER_DIR` 这类解包路径。

## 验收

- `grep`/测试检查不到 runtime 模块对解包目录的直接读取。
- 预载入阶段仍能把游戏数据写入 DB。
- 前端和 SSG 只消费 `data/json` 与 DB 派生产物。
