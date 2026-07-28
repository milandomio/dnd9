# DarkFindV5 技术参考索引

本目录按主题保存数据管道、爆率、地图模块和前端数据加载规范。日常先读对应的小文档；历史细节和已完成修复保留在 [`REFERENCE_ARCHIVE.md`](REFERENCE_ARCHIVE.md)。

> 术语约定：如无特别说明，“详情页”/“列表页”默认指 lootdrops、monsters、props、items 四类实体页面。

## 按任务查阅

| 任务 | 文档 |
|------|------|
| 管道顺序、Spawner、坐标提取、实体分类 | [`REFERENCE_DATA_PIPELINE.md`](REFERENCE_DATA_PIPELINE.md) |
| SpawnRate、DropRate、变体和掉落详情显示 | [`REFERENCE_DROP_RATES.md`](REFERENCE_DROP_RATES.md) |
| 地图模块、旋转、Layout、extra_rows、图片 | [`REFERENCE_MAP_MODULES.md`](REFERENCE_MAP_MODULES.md) |
| SSR、SSG、JSON fetch、共享 Hook、Hydration | [`REFERENCE_FRONTEND_DATA.md`](REFERENCE_FRONTEND_DATA.md) |
| 历史问题、旧方案、完整原始技术记录 | [`REFERENCE_ARCHIVE.md`](REFERENCE_ARCHIVE.md) |

## 相关入口

- [构建与部署](BUILD_AND_DEPLOY.md)：运行管道、构建 SSG、启动预览和 HTTP 验证。
- [开发工作流](DEVELOPMENT_WORKFLOW.md)：改动前 checkpoint、预检和提交纪律。
- [Agent 项目参考](AGENT_REFERENCE.md)：项目结构、页面/组件职责、PWA 和排障索引。
- [多语言架构](plans/MULTILANG_PLAN.md)：语言路由、locale 和 SSG 多语言入口。

## 维护规则

- 新增可执行规则写入对应主题文档，不要继续堆入本索引。
- 已完成但仍需追溯的调查、旧实现和历史修复写入 `REFERENCE_ARCHIVE.md`，并在主题文档保留当前结论。
- 代码路径变化时，优先更新主题文档中的“实现位置”和本索引，不在多个文档复制完整方案。
