# Development Workflow

本文件保存日常改动、预检、功能验证和本地提交规则。触发条件：准备改代码、提交、本地质量检查、遇到 pre-commit / TypeScript / Prettier 问题时阅读。

**适用范围**：所有分支一视同仁。默认工作分支是 `main`；除非用户明确要求切换分支，不要自行切换，新增功能直接在 `main` 开发。

## 核心原则：测试通过后提交

正式提交必须满足：实现已完成、适用的静态预检和功能测试通过、`SESSION_CHANGES` 已更新，然后才创建正式 `feat:`/`fix:`/`docs:` 等 commit。

提交前后的标准顺序：

```text
检查 git status → 分类已有改动 → 实现功能 → 静态预检 → 功能测试
→ 追加 docs/SESSION_CHANGES.md → 精确 stage → 正式 commit → git status
```

### 改动前：只检查，不强制空 checkpoint

```bash
git status --short
```

按以下规则处理工作区：

| 状态 | 动作 |
|------|------|
| 工作区干净 | 直接开始实现，不创建空 checkpoint |
| 有无关用户改动 | 不回退、不覆盖、不 stage；本任务只提交自己的文件 |
| 有本任务已有 WIP | 先确认文件范围；必要时单独提交 `wip: <描述>` 保护进度 |
| 有已完成但未提交的本任务改动 | 不继续堆积，先按本流程完成测试并正式提交 |

`wip:` 只表示“保存未完成进度”，不表示功能已验证或可交付。只有已有本任务 WIP 需要保护、测试失败后必须保存现场、或会话中断时，才使用 `wip:` commit。

## 实现后的验证流程

### 1. 静态预检

提交前必须手动运行适用的静态检查；不要只依赖 commit hook：

```bash
# 前端（在 web/ 下）
npm run format              # 仅在需要修正格式时运行，会修改文件
npm run format:check
npm run lint
npx tsc --noEmit
# 或直接运行：npm test

# 后端（在 api/ 下）
./lint.sh
```

`pre-commit` 是静态质量安全网，不替代功能测试。它可能只检查 staged 的部分文件，不能证明数据、页面、浏览器交互或部署行为正确。

### 2. 按改动范围运行功能测试

根据实际改动选择，不要用“静态检查通过”代替功能验证：

| 改动范围 | 最低功能验证 |
|----------|--------------|
| 前端组件/页面 | `cd web && npm run build`；需要页面回归时启动 preview 并验证 HTTP 200 |
| 多语言/SSG/页面输出 | 构建后运行 `BASE_URL=http://localhost:8080 npm run test:i18n` |
| 地图识别或浏览器交互 | 构建并启动 preview 后运行对应 Playwright 测试，如 `npm run test:map-recognition` |
| 后端逻辑 | `cd api && python3 -m unittest discover -s tests -p 'test_*.py'`，或针对改动运行相关 pytest |
| 数据管道/导出数据 | 先运行 `cd api && python main.py`，再运行前端 build；必要时检查产物和页面 HTTP 200 |
| 完整发布/部署 | 按 `docs/BUILD_AND_DEPLOY.md` 完成管道、构建、preview HTTP 200 及适用回归 |

长流程必须按 `docs/BUILD_AND_DEPLOY.md` 使用 `nohup <command> > <log> 2>&1 &` 后台运行，再读取日志和检查进程；不得以命令已启动代替命令成功。连续两次测试失败时停止并报告，不要盲目重复修改。

## 测试通过后的正式提交

测试和预检都通过后，先更新 `docs/SESSION_CHANGES.md`。它是正式 commit 前的最后一个文档步骤，每条记录至少包含：改动原因、变更文件、关键逻辑/映射关系、验证结果。然后只 stage 本任务文件：

```bash
git diff --check
git add <本任务文件...> docs/SESSION_CHANGES.md
git diff --cached --stat
git commit -m "<type>: <description>"
git status --short
```

禁止使用 `git add -A` 或 `git commit -am` 混入无关用户改动、生成文件或其他任务 WIP。正式 commit 只在适用功能测试通过后创建；不要为了满足“不能有脏文件”而提前提交未验证功能。

## 测试失败或中断时的保存

如果功能测试失败：先保留失败日志和当前差异，按项目失败熔断规则处理；需要切换任务、结束会话或避免现场丢失时，再精确 stage 当前任务文件和 `SESSION_CHANGES.md`，提交：

```bash
git add <当前任务文件...> docs/SESSION_CHANGES.md
git commit -m "wip: <说明未完成原因>"
```

`wip:` 记录中必须说明失败测试、未完成项或阻塞原因。若只是一次临时失败且仍在当前会话继续排查，可以暂不提交，但不能把它误报为完成；离开任务前必须保存或明确报告现场。

## 脏文件验收

换任务或会话结束前执行 `git status`，对每个脏/未跟踪文件判定：

| 判定 | 条件 | 动作 |
|------|------|------|
| 改完且已验证 | 逻辑闭环、适用测试通过、SESSION 已写 | 立即正式 commit |
| 改一半或测试失败 | 缺对端、缺文案 key、管道未验证、或明确 WIP | 记录失败/阻塞原因，必要时 `wip:` commit |
| 无关用户改动 | 非本任务 | 不碰、不混提，并向用户说明 |

## 常见问题

- **TS6133 unused variable**：删除 `?v=` 参数后，很多地方 `dataVersion` 变量不再使用。每次改动后跑 `npx tsc --noEmit` 自检，发现 unused 变量主动删掉，不要等 hook 报错。
- **Prettier 失败**：`vite.config.ts` 等配置文件也可能格式不符，在编辑后手动 `npm run format`，然后重新执行 `format:check`。
- **Hook 通过但功能不正确**：hook 只覆盖静态质量；补跑与改动对应的单测、构建、preview、HTTP 或 Playwright 回归。
- **当前分支 status 很脏**：先按上面的分类表拆分无关改动、已有 WIP 和本任务改动，禁止 `git add -A`。

## 重要警告

- 不要直接改 `data/` 下的自动生成文件，修改 `api/src/collector.py` 等生成逻辑。
- 解包 JSON 只能用于批量导入 DB；导出、构建与部署代码只能从 DB 读取，不能因本地存在解包目录而增加 JSON 回退读取。
- `python main.py` 必须在 `npm run build` 之前运行。
- TypeScript 类型检查：`npx tsc --noEmit`（构建中自动执行）。
