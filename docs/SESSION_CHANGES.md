# 会话修改记录

当前会话记录写在本文件；历史记录已移至 [`SESSION_CHANGES_ARCHIVE.md`](SESSION_CHANGES_ARCHIVE.md)，按日期保留原始内容。

## 2026-07-29

### docs: 拆分大型项目文档

- **改动原因**：`REFERENCE.md`、`SESSION_CHANGES.md` 和 `MULTILANG_PLAN.md` 过长，日常查阅需要加载大量历史内容，主题边界不清。
- **变更文件**：`docs/REFERENCE.md`；`docs/REFERENCE_DATA_PIPELINE.md`；`docs/REFERENCE_DROP_RATES.md`；`docs/REFERENCE_MAP_MODULES.md`；`docs/REFERENCE_FRONTEND_DATA.md`；`docs/REFERENCE_ARCHIVE.md`；`docs/plans/MULTILANG_PLAN.md`；`docs/plans/MULTILANG_ARCHITECTURE.md`；`docs/plans/MULTILANG_BUILD_AND_TEST.md`；`docs/plans/MULTILANG_STATUS.md`；`docs/plans/MULTILANG_PLAN_ARCHIVE.md`；`docs/SESSION_CHANGES.md`；`docs/SESSION_CHANGES_ARCHIVE.md`；`docs/AGENT_REFERENCE.md`；`CLAUDE.md`。
- **关键逻辑/映射关系**：主题文档承载当前可执行规则，`*_ARCHIVE.md` 只读保存完整历史；`CLAUDE.md` 与 `AGENT_REFERENCE.md` 指向小文档入口。后续会话仍追加本文件，历史不再混入日常入口。
- **验证**：Markdown 链接目标、差异空白和文件体量检查通过；日常入口均不超过 62 行，完整历史内容保留在三个 archive 文件中；`npm run format`、`npm run format:check`、`npx tsc --noEmit` 通过。

## 追加规则

- 每次改动完成后在当天日期下追加一条记录，至少写明原因、变更文件和关键逻辑/映射关系。
- 不把完整排障过程或旧方案复制到本文件；需要长期保留时写入对应主题文档或 archive，并在此处链接。
