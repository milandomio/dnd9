# Development Workflow

本文件保存日常改动、预检、提交相关细节。触发条件：准备改代码、提交、本地质量检查、遇到 pre-commit / TypeScript / Prettier 问题时阅读。

**适用范围**：`dev` 与任意功能分支一视同仁。默认工作分支是 `dev`，**dev 上的改动同样必须及时本地 commit**，不得以「还在 dev / 未合 main」为由堆未提交 diff。

## 强制提交节奏（dev 同样适用）

| 时机 | 动作 |
|------|------|
| **改动前** | 若工作区已有未提交改动：只处理本任务相关文件；与本任务无关的脏文件先单独 `wip:` commit 或留给用户，**禁止**混进本任务、禁止回退他人改动 |
| **一个逻辑任务完成时** | 立刻本地 commit（含 `docs/SESSION_CHANGES.md`），不要等「改天再提」 |
| **中断 / 换任务前** | 必须 commit 当前进度（可用 `wip:`），保证 `git status` 干净或仅剩明确无关的用户 WIP |
| **推送远程** | 仅当用户明确要求 push；平时只做本地 checkpoint |

禁止：

- 在 `dev` 上连续多轮改动却长期不 commit，导致 `git status` 堆积无关文件
- 用 `git add -A` 把无关 WIP 和本任务绑成一次提交（应只 stage 本任务文件）
- 未跑预检就 commit 赌 hook

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
- `python main.py` 必须在 `npm run build` 之前运行。
- TypeScript 类型检查：`npx tsc --noEmit`（构建中自动执行）。
