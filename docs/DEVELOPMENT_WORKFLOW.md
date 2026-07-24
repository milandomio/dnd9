# Development Workflow

本文件保存日常改动、预检、提交相关细节。触发条件：准备改代码、提交、本地质量检查、遇到 pre-commit / TypeScript / Prettier 问题时阅读。

## 前置规则：改动前先提交

每次改动前必须先 git commit 作为 checkpoint：

```bash
git commit -am "WIP: <改动摘要>"
# 有新文件时先 git add
git add <新文件> && git commit -am "WIP: <改动摘要>"
```

## 提交前质量预检

项目 pre-commit hook 会自动运行 eslint + prettier + tsc，如果代码不过关会拒绝提交。禁止直接 git commit 赌运气，每次提交前必须手动预检，确保全绿：

```bash
# 1. 格式化（修复所有 prettier 问题）
npm run format

# 2. 格式化检查（确认无残留）
npm run format:check

# 3. TypeScript 类型检查（确认无 unused 变量/类型错误）
npx tsc --noEmit

# 4. 全部通过后，再提交
git add -A && git commit -m "..."
```

## 常见问题

- **TS6133 unused variable**：删除 `?v=` 参数后，很多地方 `dataVersion` 变量不再使用。每次改动后跑 `npx tsc --noEmit` 自检，发现 unused 变量主动删掉，不要等 hook 报错。
- **Prettier 失败**：`vite.config.ts` 等配置文件也可能格式不符，在编辑后手动 `npm run format`。

## 关键警告

- 不要直接改 `data/` 下的自动生成文件，修改 `api/src/collector.py` 中的生成逻辑。
- `python main.py` 必须在 `npm run build` 之前运行。
- TypeScript 类型检查：`npx tsc --noEmit`（构建中自动执行）。
