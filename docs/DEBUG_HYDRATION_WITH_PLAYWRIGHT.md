# 前端水合错误排错方案

## 方案一：使用 Playwright/Puppeteer 自动抓取控制台报错（最推荐）

前端的水合错误（#418/#423）发生在浏览器端，服务端日志看不到。你可以让 Agent 运行一个 Node.js 脚本，用无头浏览器打开 http://localhost:5173，监听并收集控制台的报错。

### 步骤

1. 安装依赖：

```bash
npm install playwright
npx playwright install chromium
```

2. 编写排错脚本：

```js
import { chromium } from 'playwright';

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage();

const errors = [];
page.on('pageerror', err => errors.push(err.message));
page.on('console', msg => {
  if (msg.type() === 'error') errors.push(msg.text());
});

await page.goto('http://localhost:5173/', { waitUntil: 'networkidle' });
console.log('Errors:', errors);

await browser.close();
```

3. 执行脚本即可获得浏览器端完整错误列表。

---

## 方案二：检查 Vite / Node 服务端终端日志

如果是 React SSR（如 Next.js、Vite SSR、Remix），水合失败的警告或错误有时也会在运行 5173 服务的终端控制台打印出来。

让 Agent 执行以下操作：

```bash
# 找到进程 PID
lsof -i :5173

# 或直接重新启动服务并捕获输出
npm run dev 2>&1 | tee server-log.txt
# 然后读取 server-log.txt
```

---

## 方案三：利用 Vite 的 SSR 错误叠加层

Vite 在开发环境下自带错误叠加层。如果是 SSR 阶段的报错，Vite 会在返回的 HTML 中包含特定的错误结构。

通过 `curl` 获取首页 HTML 快速判断：

```bash
curl http://localhost:5173
```

- 如果是纯客户端渲染（CSR）的水合错误，`curl` 拿到的 HTML 是正常的，错误发生在 JS 执行时，必须用方案一的浏览器自动化方案。
- 如果是 SSR 报错，`curl` 返回的 HTML 里会直接带有报错堆栈。
