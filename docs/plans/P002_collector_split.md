# P002: collector.py 按职责拆分

## 目标

将 2265 行单体 collector.py 拆分为职责清晰的小模块。

## 拆分方案

| 模块 | 职责 | `api/src/` 路径 |
|------|------|----------------|
| `collector.py` | 入口协调，调用各模块 | 保留为入口文件，大幅精简 |
| `importer.py` | DB 导入（translations/items/monsters/props/dungeon_modules/lootdrops） | 新建 |
| `exporter.py` | JSON 输出（search_index + index/list/detail 导出） | 新建 |
| `rate_calculator.py` | 爆率预加载 + 计算 + group_drop_info 合并 | 新建 |
| `coord_builder.py` | 坐标过滤、变体合并、dungeon_modules_coords 构建 | 新建 |
| `translator.py` | translate 解析（resolve_name + 全部模糊匹配） | 新建 |

## 不做的事

- 不改数据流架构（Python → 静态 JSON → React SSG）
- 不改 DB schema
- 不改 JSON 输出格式

## 验证

1. `cd api && python main.py` 返回码 0
2. `cd api && ruff check src/` 通过
3. 与拆分前输出 diff（`api/output/json/` 下全部 JSON 一致）
