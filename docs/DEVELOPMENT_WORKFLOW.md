# Development Workflow

本文件保存日常改动、预检、提交相关细节。触发条件：准备改代码、提交、本地质量检查、遇到 pre-commit / TypeScript / Prettier 问题时阅读。

**适用范围**：`dev` 与任意功能分支一视同仁。默认工作分支是 `dev`，**dev 上的改动同样必须及时本地 commit**，不得以「还在 dev / 未合 main」为由堆未提交 diff。

## 强制提交节奏（dev 同样适用）

| 时机 | 动作 |
|------|------|
| **改动前** | 若工作区已有未提交改动：只处理本任务相关文件；与本任务无关的脏文件先单独 `wip:` commit 或留给用户，**禁止**混进本任务、禁止回退他人改动 |
| **一个逻辑任务完成时** | 立刻本地 commit（含 `docs/SESSION_CHANGES.md`），不要等「改天再提」 |
| **中断 / 换任务前** | 必须 commit 当前进度（可用 `wip:`），保证 `git status` 干净或仅剩明确无关的用户 WIP |
| **发现 `git status` 有脏文件** | **先判定「改完 vs 改一半」再决定**：已完成的逻辑必须马上单独 commit；仅确认是未完成 WIP 才可暂时留下，并在 `SESSION_CHANGES` 写清单与原因 |
| **推送远程** | 仅当用户明确要求 push；平时只做本地 checkpoint |

禁止：

- 在 `dev` 上连续多轮改动却长期不 commit，导致 `git status` 堆积无关文件
- 用 `git add -A` 把无关 WIP 和本任务绑成一次提交（应只 stage 本任务文件）
- 未跑预检就 commit 赌 hook
- **把「已完成」的改动长期留在工作区**：禁止因「不是当前任务」就默认当半成品搁置；应拆 commit。历史教训：列表 `monster_translation_keys` / 首页 i18n 曾做完未提，干净 checkout 会丢字段

## 脏文件验收（避免「做完没提交」）

换任务或会话结束前执行 `git status`，对每个脏/未跟踪文件判定：

| 判定 | 条件 | 动作 |
|------|------|------|
| **改完** | 逻辑闭环（生产端+消费端齐全）、无 TODO/FIXME、预检可通过、SESSION 或计划已写完成 | **立即** `feat:`/`docs:` 单独 commit |
| **改一半** | 缺对端、缺文案 key、管道未验证、或明确 wip | `wip:` commit，或 SESSION 记清单+原因（禁止无记录地堆着） |
| **无关用户改动** | 非本 agent 任务 | 不碰；可提醒用户 |

判定方法（快速）：`git diff` 看是否有完整读写链路；`grep` 对端是否已用；产物/类型是否对齐。
## 改动前 checkpoint

```bash
# 仅 stage 本任务相关文件（勿 git add -A 除非确认全是本任务）
git add <本任务文件...>
git commit -m "wip: <改动摘要>"
```

## 提交前质量预检

项目 pre-commit hook 会自动运行 eslint + prettier + tsc，如果代码不过关会拒绝提交。禁止直接 git commit 赌运气，每次提交前必须手动预检，确保全绿：

```bash
# 在 web/ 下
npm run format
npm run format:check
npx tsc --noEmit

# 仅 add 本任务文件后提交
git add <本任务文件...> && git commit -m "feat: ..."
```

## 常见问题

- **TS6133 unused variable**：删除 `?v=` 参数后，很多地方 `dataVersion` 变量不再使用。每次改动后跑 `npx tsc --noEmit` 自检，发现 unused 变量主动删掉，不要等 hook 报错。
- **Prettier 失败**：`vite.config.ts` 等配置文件也可能格式不符，在编辑后手动 `npm run format`。
- **dev 上 status 很脏**：先把已完成任务拆成独立 commit；剩余用户/其他任务文件不要强行塞进当前 commit。

## 重要警告

- 不要直接改 `data/` 下的自动生成文件，修改 `api/src/collector.py` 中的生成逻辑。
- 解包 JSON 只能用于批量导入 DB；导出、构建与部署代码只能从 DB 读取，不能因本地存在解包目录而增加 JSON 回退读取。
- `python main.py` 必须在 `npm run build` 之前运行。
- TypeScript 类型检查：`npx tsc --noEmit`（构建中自动执行）。
