# DarkFindV5 多人协作工作流建立计划

## 目标
建立成熟的工作流，使未来的多人协同成为可能，提升代码质量、协作效率和项目可维护性。

## 项目现状分析

### 优势
- 详细的 `CLAUDE.md` 开发规范（157行）
- CI/CD 流水线已存在（GitHub Actions）
- TypeScript 严格模式已配置
- MIT 许可证已就绪

### 主要缺失
1. **协作基础设施** - 无 README、CONTRIBUTING、Issue/PR 模板
2. **代码质量工具** - 无 ESLint、Prettier、Ruff 等
3. **测试框架** - 无 Python 测试，前端无测试
4. **Git 工作流** - 无 hooks、提交规范、分支保护
5. **依赖管理** - Python 依赖未声明，无自动化更新
6. **文档** - 缺少项目介绍、架构说明、API 文档

---

## 分阶段实施计划

### 第一阶段：基础协作设施（1-2天）
**目标：** 建立基本的协作环境

#### 1.1 配置远程仓库
```bash
git remote add origin <github-repo-url>
git push -u origin main
```

#### 1.2 创建协作文档
- [ ] `README.md` - 项目介绍、快速开始、架构说明
- [ ] `CONTRIBUTING.md` - 贡献指南（从 CLAUDE.md 转化）
- [ ] `.github/ISSUE_TEMPLATE/bug_report.md` - Bug 报告模板
- [ ] `.github/ISSUE_TEMPLATE/feature_request.md` - 功能请求模板
- [ ] `.github/PULL_REQUEST_TEMPLATE.md` - PR 描述模板

#### 1.3 分支策略
```
main      - 稳定版本，仅通过 PR 合并
develop   - 开发主分支
feature/* - 功能分支
hotfix/*  - 紧急修复
```

#### 1.4 基础 Git 配置
```bash
# 设置 .gitattributes 处理换行符
echo "* text=auto" > .gitattributes

# 设置默认分支名
git config --global init.defaultBranch main
```

---

### 第二阶段：代码质量工具（2-3天）
**目标：** 自动化代码质量保证

#### 2.1 前端代码质量
```bash
# 安装 ESLint + Prettier
npm install -D eslint prettier eslint-config-prettier eslint-plugin-react
npx eslint --init

# 配置 .prettierrc
{
  "semi": true,
  "singleQuote": true,
  "tabWidth": 2,
  "trailingComma": "es5"
}
```

#### 2.2 Python 代码质量
更新 `api/pyproject.toml`：
```toml
[tool.ruff]
line-length = 88
select = ["E", "F", "I", "N", "W", "UP"]
ignore = ["E501"]

[tool.black]
line-length = 88
target-version = ["py310"]

[tool.isort]
profile = "black"
```

#### 2.3 Git Hooks
```bash
# 安装 husky + lint-staged
npm install -D husky lint-staged
npx husky init

# 创建 pre-commit hook
cat > .husky/pre-commit << 'EOF'
npm run lint
npm run typecheck
EOF

# 配置 lint-staged (package.json)
"lint-staged": {
  "*.{js,jsx,ts,tsx}": ["eslint --fix", "prettier --write"],
  "*.py": ["ruff check --fix", "black"]
}
```

#### 2.4 提交规范化
```bash
# 安装 commitlint
npm install -D @commitlint/cli @commitlint/config-conventional

# 创建 commitlint.config.js
module.exports = {
  extends: ['@commitlint/config-conventional'],
  rules: {
    'type-enum': [2, 'always', [
      'feat', 'fix', 'docs', 'style', 'refactor', 
      'test', 'chore', 'revert', 'ci', 'perf'
    ]],
    'subject-max-length': [2, 'always', 100]
  }
};
```

---

### 第三阶段：测试框架（3-5天）
**目标：** 建立自动化测试体系

#### 3.1 前端测试
```bash
# 安装测试依赖
npm install -D vitest @testing-library/react @testing-library/jest-dom

# 更新 package.json scripts
"test": "vitest",
"test:coverage": "vitest run --coverage"
```

#### 3.2 Python 测试
更新 `api/pyproject.toml`：
```toml
[project.optional-dependencies]
test = [
  "pytest>=7.0",
  "pytest-cov>=4.0",
  "pytest-asyncio>=0.21"
]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_functions = ["test_*"]
addopts = "-v --tb=short"
```

#### 3.3 测试目录结构
```
api/
├── tests/
│   ├── __init__.py
│   ├── test_collector.py
│   ├── test_db_manager.py
│   └── conftest.py
web/
├── src/
│   ├── __tests__/
│   │   ├── components/
│   │   └── pages/
│   └── test-utils.tsx
```

#### 3.4 CI 集成
更新 `.github/workflows/deploy.yml` 添加测试步骤：
```yaml
- name: Run Python tests
  run: |
    cd api
    pip install -e ".[test]"
    pytest --cov=. --cov-report=xml

- name: Run frontend tests
  run: |
    cd web
    npm run test:coverage
```

---

### 第四阶段：分支保护和审查（1天）
**目标：** 建立代码审查流程

#### 4.1 GitHub 分支保护规则
- 要求 PR 审查（至少1人批准）
- 要求状态检查通过（CI 构建 + 测试）
- 要求分支最新代码
- 要求线性提交历史（squash 或 rebase）

#### 4.2 CODEOWNERS 文件
```
# 默认代码所有者
* @your-github-username

# 前端代码
/web/ @frontend-team

# 后端代码
/api/ @backend-team

# 文档
*.md @docs-team
```

#### 4.3 PR 自动化
```yaml
# .github/workflows/pr-checks.yml
name: PR Checks
on: pull_request

jobs:
  auto-assign:
    runs-on: ubuntu-latest
    steps:
      - uses: kentaro-m/auto-assign-action@v2
        with:
          assignees: ${{ github.actor }}
          
  request-review:
    runs-on: ubuntu-latest
    steps:
      - uses: kentaro-m/auto-request-review-action@v0
        with:
          review-policy: MINIMAL
          users: '[ "user1", "user2" ]'
```

---

## 高级功能（可选）

### 5.1 依赖自动化
```yaml
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: "npm"
    directory: "/web"
    schedule:
      interval: "weekly"
      
  - package-ecosystem: "pip"
    directory: "/api"
    schedule:
      interval: "weekly"
```

### 5.2 发布自动化
```yaml
# .github/workflows/release.yml
on:
  push:
    tags:
      - 'v*'

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Create Release
        uses: actions/create-release@v1
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### 5.3 文档自动化
```bash
# 前端文档
npm install -D typedoc
npx typedoc --out docs/web src/

# Python 文档
pip install sphinx
sphinx-quickstart api/docs
```

---

## 风险与注意事项

### 1. 历史重写风险
- 如需清理 WIP 提交，建议在新分支上 squash 合并
- 重写前备份当前 main 分支
- 使用 `git filter-branch` 或 BFG 清理敏感信息

### 2. 团队适应期
- 提供培训文档和示例
- 设置1-2周的过渡期
- 收集反馈并调整规则

### 3. 渐进式采用
- 可先实施核心工具（ESLint + Prettier）
- 逐步添加测试要求
- 根据团队需求调整 hooks

### 4. 性能考虑
- Git hooks 可能增加提交时间
- 使用 `lint-staged` 只检查暂存文件
- 考虑使用 `--no-verify` 跳过紧急情况

---

## 实施时间表

| 阶段 | 主要任务 | 预计时间 | 依赖 |
|------|----------|----------|------|
| 第一阶段 | 基础协作设施 | 1-2天 | 远程仓库 |
| 第二阶段 | 代码质量工具 | 2-3天 | 第一阶段完成 |
| 第三阶段 | 测试框架 | 3-5天 | 第二阶段完成 |
| 第四阶段 | 分支保护 | 1天 | 第二阶段完成 |
| 第五阶段 | 高级功能 | 2-3天 | 第三阶段完成 |

**总计：** 约9-14天（可根据优先级调整）

---

## 成功指标

1. **代码质量** - Lint 错误减少 90%+
2. **测试覆盖** - 核心模块测试覆盖 > 70%
3. **协作效率** - PR 审查时间 < 24小时
4. **文档完整性** - 所有模块有 API 文档
5. **自动化程度** - 80%+ 的质量检查自动化

---

## 下一步行动

1. **确认远程仓库** - 创建 GitHub 仓库并配置 origin
2. **选择优先级** - 确定先实施哪个阶段
3. **团队组建** - 确定协作者和角色分工
4. **开始实施** - 按照计划逐步执行

---

*最后更新：2026-06-10*