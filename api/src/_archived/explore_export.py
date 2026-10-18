"""归档：【任务探索表】后端导出逻辑。

迁移日期：2026-10-19
迁移原因：用户要求把【任务探索表】从站点下线（主页入口移除、路由取消），
         前端页面已归档到 `web/src/_archived/ExplorePage.tsx`，此处保存随之
         从活跃管道中摘除的导出逻辑，以便日后恢复。

被摘除的内容（原位置 → 本文件对应函数）：
  1. `index_export.save_quest_data()` 中的 `explore.json` 导出
     → `save_explore_json()`
  2. `index_export.build_and_save_indexes()` 中 `index.json` 的
     `{"page": "explore", "label": "任务探索表", "count": explore_count}` 条目
     → `explore_index_entry()`
  3. `index_export.build_and_save_indexes()` 中 `search_index.json` 的
     `LIST_PAGES` 条目 `{"name": "explore", ...}`
     → `explore_nav_entry()`

未归档（仍在活跃使用，禁止删除）：
  - `explore_targets` 表、`db.import_explore_targets()`、`db.get_explore_targets()`、
    `quest_collector` 的探索目标提取、`db_freshness.REQUIRED_TABLES` 中的该表；
  - `Explore` 任务内容类型（`ui.content.explore`）相关渲染。

恢复方式：
  1. 在 `index_export.save_quest_data()` 中重新调用 `save_explore_json()` 并把
     `explore_count` 加回返回值；
  2. 在 `index_export.build_and_save_indexes()` 中加回 `explore_count` 参数、
     `explore_index_entry(explore_count)` 与 `explore_nav_entry()`；
  3. `collector.py` 中恢复 `explore_count` 的解包、打印与传参；
  4. 前端按 `web/src/_archived/ExplorePage.tsx` 头部说明恢复路由与 SSG。
"""

from __future__ import annotations

import json
from pathlib import Path


def save_explore_json(db, output_dir: Path) -> int:
    """导出 `explore.json`（任务探索目标汇总），返回条目数。

    原为 `save_quest_data()` 的一部分。
    """
    explore_data = db.get_explore_targets()
    path = output_dir / "explore.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(explore_data, f, ensure_ascii=False, indent=2)
    return len(explore_data)


def explore_index_entry(explore_count: int) -> dict:
    """`index.json` 中的【任务探索表】卡片条目（主页入口）。"""
    return {"page": "explore", "label": "任务探索表", "count": explore_count}


def explore_nav_entry() -> dict:
    """`search_index.json` 中的【任务探索表】导航条目（`page` 为 `_nav`）。"""
    return {"name": "explore", "translation": "任务探索表", "page": "_nav", "url": "/explore/"}
