# 会话修改记录

当前会话记录写在本文件；历史记录已移至 [`SESSION_CHANGES_ARCHIVE.md`](SESSION_CHANGES_ARCHIVE.md)，按日期保留原始内容。

## 2026-10-21

### feat: 搜索索引补全商店/工匠语义标签，并为合成原料建索引

- **改动原因**：用户反馈「黄金钥匙在搜索栏显示为『地穴』，实际是哥布林走私者卖的，应完整显示为『地牢商店-地穴』」；同时要求「像合成原料『生命之叶』也应该添加为『工匠合成-治疗药水』，即成品和原料都要索引」。
- **变更文件**：`api/src/index_export.py`、`api/tests/test_search_index_entries.py`、`web/src/hooks/useSearchIndex.ts`、`web/src/components/NavBar.tsx`、`web/src/i18n/uiLocale.ts`、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：
  1. **标签前缀键**：搜索条目新增可选字段 `tag_prefix_key`。前端渲染规则为 `tag_prefix_key ? ut(tag_prefix_key) + "-" + tag : tag`，因此同一个 `tag` 在不同页面可复用不同前缀，避免把展示文案写死进索引。
  2. **商店条目**：`_iter_shop_search_entries` 为每条商品加 `tag_prefix_key = "ui.nav.dungeon_shops"`（=「地牢商店」），页面显示为「地牢商店-地穴」；`tag` 仍取区域 `display`，`tag_translation_key` 不变，10 语言自动本地化。
  3. **工匠成品条目**：保持原逻辑（`tag` = 工匠名，如「炼金术师」）。
  4. **新增工匠原料条目**：`_iter_craft_search_entries` 在原「按 (merchant, item) 去重」之外，再遍历每份配方的 `requirements`，为每个原料生成一条 `page="crafts"` 的条目——`name/translation/translation_key` 取原料本身，`tag` 取成品名、`tag_translation_key` 取成品翻译键、`tag_prefix_key = "ui.search.tag.craft_group"`（=「工匠合成」），`url` 复用成品的 `/crafts/{slug}/?item={成品}`，点击后打开该工匠标签并高亮用到该原料的配方卡片（`CraftsPage` 的 `data-craft-item` 高亮逻辑无需改动）。去重键为 `(merchant, 成品, 原料)`，因此一个原料用于多个配方会各出现一条。
  5. **文案**：`uiLocale.ts` 的 `UI_EXTRA_LOCALE` 增补中英两条 `ui.search.tag.craft_group`（「工匠合成」/「Crafting」），其余语言回落英文。
- **结果**：`search_index.json` 2213 → 2837 条；`crafts` 条目 255 → 879，`dungeon_shops` 147 条带前缀；`search_index/{lang}.json` 同步重新生成。
- **验证**：`api/lint.sh` + `black --check` 通过；`cd api && python3 -m unittest discover -s tests` 163/163 OK（新增商店前缀断言、原料条目断言与素材，并同步 `pages.count("crafts")` 由 2 改 3）；`npm run check`（0 error / 20 既有 warning、Prettier、tsc）通过；`TMPDIR=<workspace>/.tmp python3 main.py` 导出 29.31s 无 error；`npm run build` 3125 页；8081 preview HTTP 200；Playwright 实测：
  - 搜「黄金钥匙」→ 第二行为「地牢商店-地穴」，点击进入 `/zh-Hans/dungeon_shops/Crypts/?item=GoldenKey`；
  - 搜「生命之叶」→ 出现「工匠合成-清晰药水 / 治疗药水 / 毒药瓶 / 手术包」四条（另有原掉落、实体、任务条目）；
  - 点击「工匠合成-治疗药水」→ `/zh-Hans/crafts/alchemist/?item=HealingPotion`，目标卡片带 2px accent 高亮；
  - `/en/` 搜 Lifeleaf → 「Crafting-Potion of Healing」等英文标签正确；全程无 pageerror。
- **附注**：`python3 main.py` 首次运行报 `sqlite3.OperationalError: unable to open database file`，原因是本机 `/tmp` 对 SQLite 排序临时文件不可写；用 `TMPDIR=<workspace>/.tmp` 重跑即通过（`.tmp/` 已由 gitignore 忽略）。

### feat: 容器宽度随视口线性缩放到 1400px + 导航栏品牌名居中

- **改动原因**：用户要求「把页面适配成 1920px 宽度，内容（比如导航栏组件总宽度）1400px，宽度变化时等比例缩放，页面宽度 1200 以下还是进入平板/手机模式（保持之前的样子）」；随后追加「越来越黑暗闪电指南 DarkFlashNav 这个组件能否居中显示」。
- **变更文件**：`web/index.html`、`web/src/AppInner.tsx`、`web/src/components/NavBar.tsx`、`web/scripts/ssg.mjs` 以及 14 个页面容器（`pages/*.tsx`）、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：
  1. **宽度变量**：`index.html` 的 `:root` 新增 `--shell-max: min(1400px, calc(1200px + (100vw - 1200px) * 0.27778))`。1200px 视口时 = 1200px，1920px 时 = 1400px，两点之间线性插值，>1920px 封顶 1400px；<1200px 时计算值大于视口，行为等同原先的满宽，既有 950/750/600 断点完全不变。
  2. **外层外壳**：`AppInner` 的根容器 `maxWidth` 改为 `calc(var(--shell-max) + 32px)`——它自身有 `padding: 16px` 且 `box-sizing: border-box`，加 32px 后**内容区**正好等于 `--shell-max`，从而与导航栏内宽对齐（1920 下导航栏 1400、内容区 1400）。
  3. **统一替换**：`NavBar` 的 `.navbar-shell` 与 14 个页面的 `maxWidth: 1200` 全部改为 `var(--shell-max)`；SSG 的详情占位页（`scripts/ssg.mjs`）同步改为 `calc(var(--shell-max) + 32px)`，避免首屏占位与 React 渲染后宽度跳变。
  4. **品牌名居中**：`.navbar-brand-slot` 由 `flex: 1 1 auto` 改为绝对定位 `left: 50%` + `translateX(-50%)`，在导航栏内水平居中（导航栏补 `position: relative`）；`max-width: 40%` 防止长语言名溢出。**≤1100px 时回退为静态流式布局**（此时居中会撞到搜索框/操作区），≤600px 仍按原移动端规则独占一行。
- **验证**：`npm run format` + `npm run check`（0 error / 20 既有 warning、Prettier、tsc）通过；`npm run build` 3125 页；8081 preview HTTP 200；`BASE_URL=http://localhost:8081 npm run test:i18n` Pass 29 / Fail 0；Playwright 逐宽度实测——
  - 导航栏宽度：1920→1400、1680→1333、1440→1267、1200→1168、1024→992、768→736、390→358，全部水平居中（`navCenterOffset=0`），无横向滚动；
  - 首页网格列数：≥1200 四列（4/4/2）、768 三列、390 两列，与改动前一致；
  - 品牌名居中误差：1920/1600/1440/1200 均为 **0px**，且与搜索框、操作区均无重叠；≤1100 自动回到流式布局；
  - 详情页 `/zh-Hans/items/Ale/` 在 1440 下内容区与导航栏同为 1267px。

## 2026-10-20

### feat: 站点名移入导航栏（搜索框右侧），全站可见

- **改动原因**：用户要求「把首页的 越来越黑暗闪电指南 DarkFlashNav 移动到导航栏上，放在搜索框右边，这样每个页面都能知道站点名字」。
- **变更文件**：`web/src/components/AppName.tsx`、`web/src/components/NavBar.tsx`、`web/src/pages/HomePage.tsx`、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：
  1. **位置**：`NavBar` 在搜索框 `.navbar-search-container` 与右侧操作区 `.navbar-actions` 之间新增 `.navbar-brand-slot` 包裹 `<AppName />`；桌面端品牌名紧贴搜索框右侧、操作区靠右，移动端（≤600px）导航栏竖向排列，品牌独占一行位于搜索框下方、操作区上方。
  2. **组件改造**：`AppName` 由首页居中大标题改为导航栏品牌链接——文字取 `ui.brand.name`，`Link` 指向当前语言首页（`zh-Hans` → `/`，其余 → `/{lang}/`），色值用 `tokens.accent`；仅在首页渲染为 `<h1 class="navbar-brand">`（首页原本无其他 h1），其余页面渲染为 `<div>`，避免与页面内容 h1 重复。
  3. **首页去重**：`HomePage` 删除 `<AppName />` 与该引入，首页大标题由导航栏品牌名承担；`<title>` / meta 的 `ui.brand.name` 逻辑不变。
  4. **响应式**：品牌单行 `nowrap + ellipsis`，小屏字号 17 → 15px，390px 视口下宽度 318px 不溢出、无横向滚动。
- **验证**：`npm run format` + `npm run check`（eslint 0 error / 20 既有 warning、Prettier、tsc）通过；`npm run build` 3125 页；8081 preview HTTP 200；SSR 产物校验：首页 `<h1 class="navbar-brand">` 且仅 1 个 h1，详情页品牌为 div、页面自身标题仍是唯一 h1；`BASE_URL=http://localhost:8081 npm run test:i18n` Pass 29 / Fail 0；Playwright 实测 `/zh-Hans/`、`/zh-Hans/items/Ale/`、`/zh-Hans/monsters/`、`/en/`、`/ja/crafts/` 均显示品牌且紧贴搜索框右侧（brand.x 444 > search.right 436），点击 `/ja/crafts/` 品牌跳 `/ja/`、`/en/items/Ale/` 跳 `/en/`，无 pageerror（仅云朵统计 CORS 噪音）。

### feat: 导航栏新增录屏用「自动滚动」播放按钮

- **改动原因**：用户要求「给导航栏增加一个播放按钮，点击播放按钮画面会慢慢滚动到最底部，用于页面录制视频使用」。
- **变更文件**：`web/src/components/AutoScrollButton.tsx`（新增）、`web/src/components/NavBar.tsx`、`web/src/i18n/uiLocale.ts`、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：
  1. **按钮挂载**：`NavBar` 的 `.navbar-actions` 内、语言选择器之前挂载 `<AutoScrollButton />`，与主题/语言控件同排；SSG 与客户端共用同一组件树，SSR 只输出停止态。
  2. **匀速滚动**：`requestAnimationFrame` 循环按 `SCROLL_SPEED = 60` CSS px/s（与屏幕刷新率无关，每帧用 `dt` 累加，`dt` 上限 50ms 防切标签页后跳变）写 `window.scrollTo`，到 `scrollHeight - innerHeight` 自动停止；再次在底部点击则先回到顶部重新播放。
  3. **交互中止**：运行中按钮切换为暂停图标（`aria-pressed` 同步），再点即暂停；用户 `wheel` / `touchstart` / 方向键、PageUp/PageDown、Home/End、空格会立即暂停自动滚动；路由 `pathname` 变化也会重置为停止态。
  4. **文案**：新增 `ui.autoscroll.play` / `ui.autoscroll.pause`，在 `UI_EXTRA_LOCALE` 的 `zh-Hans`、`en` 中提供，其余语言回落到英文（`extraUiDict` 既有回落逻辑）；中文含「（录屏用）」说明用途。
- **验证**：`npm run format` + `npm run check`（eslint 0 error / 20 既有 warning、Prettier、tsc）通过；`npm run build` 3125 页成功；8081 preview HTTP 200；Playwright 实测：`/zh-Hans/monsters/` 点击播放 2s 内滚动 120px 且按钮变为「暂停自动滚动」，滚轮介入立即暂停、按钮点击可暂停、`/zh-Hans/` 短页面滚动到 12px 底部后自动回到播放态、在底部再次点击从顶部重播，`/en/` 显示英文标签，路由切换后回到停止态；全过程无 pageerror。

## 2026-10-19

### chore: 补丁部署（跳过 FMOD 同步，删库重建并推送含 DB 的 main）

- **改动原因**：用户要求「进行补丁部署（不包括 ~ 的同步脚本）」，即按 `docs/BUILD_AND_DEPLOY.md` 的「更新部署」流程执行，但跳过第 1 步 `~/sync_fmod.sh`（沿用现有 `~/fmod/Output` 解包源）。
- **变更文件**：`docs/SESSION_CHANGES.md` + 临时跟踪的 `api/data/darkfindv5.db`（推送后立即 `reset` 并恢复 `skip-worktree`）。
- **关键逻辑/映射关系**：`rm -f api/data/darkfindv5.db` → `cd api && nohup python main.py > pipeline.log 2>&1 &` 全量重建（`[DB] state=REBUILD_REQUIRED: DB missing`，耗时 50.52s，`[VALIDATE] all module images OK`，日志 0 error/0 traceback）。本流程不跑 `npm run build` / `vite preview`，前端 SSG 交给 GitHub Actions。本次推送内容涵盖四个未推送提交：`3f44a95ead`【工匠】属性区间（含 DB 新表）、`dc5580b44b` 搜索纳入商店/工匠/任务目标物、`78f956d279` 归档【任务探索表】、`f98ca08a5b`【工匠】标签路由。
- **DB 校验**：新 DB 49,500,160 字节、md5 `43c7801756951a4e226ea7c94dd65bca`；`pipeline_meta.generator_version = db-lifecycle-v13-item-properties`、`import_complete=1`；47 张表（含新增 `item_properties` 1876 行、`item_property_pools` 14 行）；`spawners` 55147 / `spawner_entries` 2291 / `props_entities` 592 / `craft_recipes` 332 / `craft_merchants` 9 / `quest_npcs` 14 / `explore_targets` 9。
- **导出产物校验**：`data/json/crafts.json` 9 个标签 slug（含 `ores`）；`search_index.json` 255 条工匠条目全部为标签路由（`/crafts/alchemist/?item=…`）；`index.json` / `search_index.json` 均无 `explore` 条目、`data/json/explore.json` 已不再产出。
- **部署结果**：临时跟踪 DB 并以 `75b296cf57 chore: update DB`（Bin 48308224 → 49500160 bytes）推送成功（`7f0c5f5291..75b296cf57 main -> main`）；推送后按文档 `git reset HEAD~1` 去掉本地临时 DB 提交、删除 `/tmp/darkfindv5.db` 并恢复 `skip-worktree`。GitHub Actions「Build & Deploy」3 分钟内 `completed success`（run 39180291320，`75b296cf57`），前端 SSG 由 Actions 用新 DB 完成。
- **推送异常与处理**：本轮 github.com:443 长时间不可达——DNS 把 `github.com` 解析到 `20.205.243.166`，连续出现 123s `connect timeout`、`GnuTLS recv error (-110)`、`Failure when receiving data from the peer`；而 `140.82.112.3/113.3/121.3` 可达（`curl --resolve github.com:443:140.82.113.3` 返回 200）。本机无代理、`sudo` 需密码（无法改 `/etc/hosts`），故改用临时本机 CONNECT 代理 `/tmp/opencode/gh_proxy.py`（监听 `127.0.0.1:8899`，把 `github.com` 钉到 `140.82.113.3`，隧道内仍是端到端 TLS、SNI/Host 保持 github.com），`git -c http.proxy=http://127.0.0.1:8899 push` 一次成功。属本机 DNS/网络问题，与仓库配置无关。
- **线上抽查**（`https://dnd9.icetar.com`，带随机 `cb` 参数绕 Cloudflare 缓存）：`/zh-Hans/` 200 且主页已无「任务探索表」；`/zh-Hans/crafts/` 200；`/zh-Hans/crafts/goldsmith/` 200 且 SSR 直出「獾吊坠」（= 标签路由页命中珠宝匠标签）；`/zh-Hans/crafts/tailor/` 200 且含「属性」（= 新 DB 的 `item_properties` 已上线）；`/en/crafts/ores/` 200 含 `Brimstone Powder`；`/ja/crafts/weaponsmith/` 200 含「正義の刃」；`/zh-Hans/quest_npc/Goldsmith/` 200 含「物资常缺」；已下线的 `/zh-Hans/explore/` 返回 404。

### feat: 【工匠】分页标签改为路由（`/crafts/:merchant`），搜索直达标签页

- **改动原因**：用户要求「为 `zh-Hans/crafts/` 页面的不同分页标签添加路由，使搜索结果能直接跳到路由的标签页而不是自己翻找」。原实现里标签只是组件内 state（`activeTab`），搜索跳转只能落 `/crafts/?item=X` 再由 `useEffect` 猜测并切换标签。
- **变更文件**：`api/src/craft_builder.py`、`api/src/index_export.py`、`api/tests/test_craft_builder_properties.py`、`api/tests/test_search_index_entries.py`、`web/src/types/data.ts`、`web/src/AppInner.tsx`、`web/src/pages/CraftsPage.tsx`、`web/scripts/ssg.mjs`、`docs/AGENT_REFERENCE.md`、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：
  1. **商品标签 slug**：`craft_builder._merchant_slug()` 生成语言无关的稳定 slug——NPC 用 `merchant_name.lower()`（`Alchemist` → `alchemist`），合成矿石标签 `__ores__` 映射为 `ores`；`crafts.json` 的 `merchants[]` 新增 `slug` 字段（前端类型 `CraftMerchant.slug` 同步）。
  2. **搜索直达**：`_iter_craft_search_entries()` 的 url 由 `/crafts/?item=X` 改为 `/crafts/{slug}/?item=X`，搜索结果点击后直接命中该工匠标签路由，无需再猜标签。
  3. **路由与标签同源**：`AppInner` 新增 `/:lang/crafts/:merchant`；`CraftsPage` 用 `useParams` 取 `merchant` 并与 `merchant.slug` 匹配决定选中标签（找不到回落首个），删除 `activeTab` state；标签按钮由 `<button onClick>` 改为 `<Link to="/{lang}/crafts/{slug}/">`（带 `aria-current="page"`），可被爬虫跟随、支持新标签页打开，切换标签不再残留 `?item=`。
  4. **兼容旧链接**：`/crafts/?item=X`（无标签段）在 `?item=` 命中的配方所属工匠与当前标签不一致时，用 `navigate(..., { replace: true })` 重定向到 `/crafts/{slug}/?item=X`，随后照旧高亮 + 平滑滚动。
  5. **SSG**：`ssg.mjs` 按 `crafts.json` 的 `merchants[].slug` 为每个标签生成 `/{lang}/crafts/{slug}/` 页面（`routeDataKey` 让所有标签页共享 `crafts` 数据，SSR 阶段即渲染对应标签），sitemap 给 `/crafts/*` 提升为 `['0.5','weekly']`；非语言前缀 URL（`/crafts/weaponsmith`）由既有 step 5c/5d 机制自动生成 meta-refresh + `_redirects` 301。
- **结果**：每语言新增 9 个标签页（10 语言共 +90 页，另 +9 个无语言前缀重定向页）；SSG 3116 → 3125 页、dist 17148 → 17247 文件、sitemap 13400 → 13490 URL；`crafts.json` 9 个 slug（`alchemist/surgeon/armourer/weaponsmith/woodsman/tailor/leathersmith/goldsmith/ores`），`search_index.json` 255 条工匠条目的 url 全部改为标签路由（`/crafts/ores/?item=BrimstonePowder` 等，无 `__ores__` 残留）。
- **验证**：`api/lint.sh` + `black --check src tests` 通过；`cd api && python3 -m unittest discover -s tests` 163/163 OK（新增 slug 与「无 slug 回落」用例，并更新工匠 url 断言）；`npm run check`（eslint 0 error / 20 既有 warning、Prettier、tsc）通过；`python main.py` 走导出态（`[DB] state=DB_READY`，DB 未变）；`npm run build` 3125 页；`BASE_URL=http://localhost:8081 npm run test:i18n` Pass 29 / Fail 0；8081 各标签页 HTTP 200；Playwright 实测 zh-Hans 搜「獾吊坠」点工匠结果 → `/zh-Hans/crafts/goldsmith/?item=BadgerPendant` 且珠宝匠标签选中、卡片高亮（`box-shadow` 命中）；搜「清晰药水」→ `/crafts/alchemist/?item=ClarityPotion`；直接访问 `/zh-Hans/crafts/goldsmith/` 首个卡片为 `BadgerPendant`（SSR 直出对应标签）；点击「矿石」标签 → `/crafts/ores/` 客户端切换并渲染 `BrimstonePowder`；旧链接 `/crafts/?item=BladeOfRighteousness` → 自动 replace 到 `/crafts/weaponsmith/?item=BladeOfRighteousness` 并高亮；`/en/crafts/tailor/` 正常（首卡 `CobaltFrock`）、`/crafts/` 无标签时回落首个标签；全过程无 pageerror、无 hydration 报错。

### chore: 归档【任务探索表】（下线 `/explore` 并从主页移除入口）

- **改动原因**：用户要求「把【任务探索表】的代码做归档，并从主页中移除【任务探索表】」。确认范围为「前端页面 + 后端导出一起归档，DB 表保留」，归档位置沿用仓库既有约定 `web/src/_archived/` 与 `api/src/_archived/`。
- **变更文件**：`web/src/_archived/ExplorePage.tsx`（由 `web/src/pages/ExplorePage.tsx` 移入）、`web/src/AppInner.tsx`、`web/src/pages/HomePage.tsx`、`web/src/components/NavBar.tsx`、`web/scripts/ssg.mjs`、`api/src/_archived/explore_export.py`（新增）、`api/src/index_export.py`、`api/src/collector.py`、`api/tests/test_search_index_entries.py`、`docs/AGENT_REFERENCE.md`、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：
  1. **前端下线**：`AppInner` 删除 `ExplorePage` 引入与 `/:lang/explore` 路由；`HomePage` 删除 `CARD_THEME.explore` 与 `ui.home.view_explore` 那行；`NavBar` 删除 `NAV_LABEL_KEYS.explore`（面包屑）与 `PAGE_TAG_KEYS.explore`（搜索结果标签）；`ssg.mjs` 删除 `SINGLE` 中的 `'explore'`、`ssrDataMap['explore']` / `['explore-modules']`、`routeDataKey` 的 `/explore` 分支、sitemap 中 `/explore` 的 `['0.7','weekly']` 优先级。
  2. **后端归档**：`save_quest_data()` 不再导出 `explore.json`，返回值由 4 元组变 3 元组 `(quest_items_count, quest_npc_count, quest_npcs_data)`；`build_and_save_indexes()` 删除 `explore_count` 形参与 `index.json` 的 `{"page":"explore"}` 卡片条目；`search_index.json` 的 `LIST_PAGES` 删除 `{"name":"explore","url":"/explore/"}` 导航条目；`collector.py` 同步调整解包/打印/传参（`ctx.set_result` 改为 `items=…, npcs=…`）。被摘除的代码完整保存在 `api/src/_archived/explore_export.py`（含恢复步骤），前端恢复步骤写在归档页文件头。
  3. **明确不归档（仍活跃）**：`explore_targets` 表与 `db.import_explore_targets()`／`get_explore_targets()`、`quest_collector` 的探索目标提取、`db_freshness` 的 `REQUIRED_TABLES`；`Explore` 任务内容类型（`ui.content.explore`，`QuestNPCDetailPage` 的内容类型映射）；i18n 文案（`ui.explore.*` / `ui.nav.explore` / `ui.search.tag.explore` / `ui.home.card_labels.explore` / `ui.home.view_explore`）与 `seoTemplate` 的 `explore` 模板，均保留以便日后恢复，不影响构建。
- **结果**：主页卡片 11 → 10 项（`index.json` 无 `explore`）；`search_index.json` 2214 → 2213 条（`_nav` 10 → 9）；管道不再产出 `data/json/explore.json`；SSG 3117 → 3116 页、dist 17160 → 17148 文件，`dist/**/explore/` 目录消失，sitemap 与 `_redirects` 均无 `explore`。
- **验证**：`api/lint.sh` + `black --check src tests` 通过；`cd api && python3 -m unittest discover -s tests` 全绿（`test_search_index_entries` 增补「`index.json`/`search_index.json` 不含 explore」断言，并同步去掉位置参数）；`npm run check`（eslint 0 error / 20 既有 warning、Prettier、tsc）通过；`python main.py` 走导出态（`[DB] state=DB_READY: DB and source manifest are current`，DB md5 不变）；`npm run build` 3116 页、`data/json/explore.json` 不存在、`index.json` 10 张卡片、`search_index.json` 无 `explore`；8081 preview HTTP 200；Playwright 实测主页卡片 10 个且无「任务探索表」、en 主页无 Explore 卡片，导航搜索「探索」只返回任务/工匠条目（无 `_nav` 探索入口）、「风箱」「灯」原有结果不受影响，直接访问 `/zh-Hans/explore/` 无 pageerror（回落到 ListPage 空列表）。

### feat: 导航栏搜索纳入【地牢商店】商品、【工匠】成品与「任务目标物」

- **改动原因**：用户要求把【地牢商店】【工匠】的目标产物，以及「某物品可提交给谁的任务」（如风箱）一并纳入导航栏搜索，即把 `quest_npc` 页的独立搜索能力合并进全局搜索框。约定候选池只按同一坐标实体判定，不按 `group_parent` 泛化。
- **变更文件**：`api/src/index_export.py`、`api/src/search_index_builder.py`、`api/src/collector.py`、`api/tests/test_search_index_entries.py`（新增）、`web/src/hooks/useSearchIndex.ts`、`web/src/components/NavBar.tsx`、`web/src/pages/CraftsPage.tsx`、`web/src/pages/DungeonShopDetailPage.tsx`、`web/src/pages/QuestNPCDetailPage.tsx`、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：
  1. `index_export` 新增三类 entry：`dungeon_shops`（每 region × 折叠物品名，url `/dungeon_shops/{region}/?item={foldedName}`）、`crafts`（每 merchant × `recipe.name`，url `/crafts/?item={name}`）、任务目标（`page=quest_npc`，`name`=quest.id、`translation`=任务标题、新增 `subtitle`=目标物、`tag`=NPC 名，url `/quest_npc/{npc}/?quest={number}`）；`Damage`/`Hold` 类型目标无实际可寻物，跳过。
  2. 品质档位折叠：商店按 `item.page` 去重（同 page 译名一致），工匠按 `(merchant, name)` 去重（`name` 只属一个 merchant）。`build_and_save_indexes` 签名改为接收 `shop_index` / `crafts_payload`，count 内部推导。
  3. `search_index_builder` 新增 `subtitle` 按语言本地化，并把 `subtitle_key` 计入 `used_keys`。
  4. 前端：`useSearchIndex` 的 `SearchEntry` 加 `subtitle?`；`NavBar` 匹配范围含 `subtitle`，渲染为「任务标题 (目标物) [NPC]」（有 `subtitle` 时不再重复显示 `(name)`），结果 key 改 `${page}::${url}::${i}` 避免同 url 重复；三个目标页用 `useSearchParams` + `useEffect` 写入 focus state（不在 render 期读 query，避免预渲染 HTML 与注水不一致），`?item=` / `?quest=` 触发高亮 + 滚动，工匠页会先切到该配方所属标签。
- **结果**：`search_index.json` 2214 条（quest_npc 532 / lootdrops 523 / dungeon_modules 268 / props 255 / crafts 255 / monsters 152 / dungeon_shops 147 / items 72 / `_nav` 10）；每语言 `search_index/{lang}.json` 由 1.05MB 增至约 1.36MB（gzip ≈98–109KB）。该文件同时是 items/monsters/props/lootdrops 列表页的 SSR 数据源，新增三类 entry 不影响这些列表页。
- **验证**：`api/lint.sh` 通过；`cd api && python3 -m unittest discover -s tests` 160/160 OK（新增 7 例）；`npm run check`（eslint 0 error / 20 既有 warning、Prettier、tsc）通过；`python main.py` 走导出态不改 DB（`[DB] state=DB_READY`，DB md5 与改动前一致）；`npm run build` 3117 页 / 17160 文件，8081 preview HTTP 200；Playwright 实测 zh-Hans 搜「风箱」得到「物资常缺 (风箱) 珠宝匠」并跳 `/quest_npc/Goldsmith/?quest=6` 且目标卡片高亮（`box-shadow` 命中 `[data-quest-num="6"]`）；搜「清晰药水」点工匠结果跳 `/crafts/?item=ClarityPotion` 并高亮 `[data-craft-item]`；搜「幸运药水」得 3 条带 地穴／哥布林洞穴／寒冰洞穴 标签，点第一条跳 `/dungeon_shops/Crypts/?item=LuckPotion` 并高亮；en 搜 `Bellows` 得 `Always in Short Supply (Bellows) Goldsmith`、ja 搜 `ふいご` 得 `いつも品薄 (ふいご) 金細工師`，均跳 `/en|/ja/quest_npc/Goldsmith/?quest=6`；全过程无 pageerror。

### docs: 预览端口统一更正为 8081

- **改动原因**：本机 `8080` 被本地 WordPress/nginx 占用（Playwright 访问会命中无关站点），项目预览实际固定使用 `8081`，文档仍写 `8080`。
- **变更文件**：`AGENTS.md`（「我看到」、其他分支启动命令、端口表）、`docs/BUILD_AND_DEPLOY.md`（完整构建/仅前端改动的预览命令、端口占用排查说明）、`docs/DEVELOPMENT_WORKFLOW.md`（`BASE_URL` 示例）、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：仅文档端口替换，无代码行为变更；dev 分支 `8090` 规则不变。

### feat: 【工匠】制作物品展示属性区间（护甲值／武器伤害／随机词条池）

- **改动原因**：用户要求「【工匠】制作的物品（如寒光布面甲）应显示对应属性，列在材料下面，并确认能否检出属性区间」。确认可行：物品资产的数值全部在独立 `ItemProperty` 资产里（主属性 `MinValue~MaxValue` + 随机池权重），且每种属性类型资产带 `ValueRatio` 可区分百分比与固定值。
- **变更文件**：`api/src/item_properties.py`（新增）、`api/src/db/importers/item_properties.py`（新增）、`api/src/config.py`、`api/src/db/schema.py`、`api/src/db/importers/__init__.py`、`api/src/db/__init__.py`、`api/src/db/repositories/items.py`、`api/src/craft_builder.py`、`api/src/collector.py`、`api/src/db_freshness.py`、`api/tests/test_item_properties.py`（新增）、`api/tests/test_craft_builder_properties.py`（新增）、`web/src/types/data.ts`、`web/src/pages/CraftsPage.tsx`、`web/src/i18n/uiLocale.ts`、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：
  1. `item_properties.py`：`Id_Item_{raw}` → `PrimaryProperty`（固定属性）+ `SecondaryProperties`（N 个随机词条槽，通常指向同一个池资产）→ `ItemProperty` 资产的 `ItemPropertyItemArray`（`MinValue`/`MaxValue`/`PropertyRate`）→ 属性类型资产 `Id_ItemPropertyType_*` 的 `PropertyType.TagName` 翻译键（`Type.Item.Property.Effect.ArmorRating` → `Text_Code_DCDataBlueprintLibrary_Type_Item_Property_Effect_ArmorRating`）+ `ValueRatio`。
  2. **属性区间与百分比换算**：`ValueRatio=0.001` 的是百分比属性（原始值 × 0.001 即比例，如动作速度 20 → `2%`、对不死生物伤害加成 150 → `15%`），其余为固定值（护甲值 19~20、移动速度 -30、武器伤害 38~41）。该口径同时与游戏内 tooltip、维基（Frostlight Crystal Sword「Action Speed 2%」）和正义之刃（「武器伤害 38~41 / 移动速度 -33 / 对不死生物伤害加成 15%」）对齐。
  3. 新增表 `item_properties(raw_name, primary_json, secondary_pool, secondary_rolls)` 与 `item_property_pools(pool_name, entries_json)`：随机池按槽位资产只存一份（14 个池），物品只引用池名，避免每件装备重复 46 条词条；导入阶段读游戏源，导出阶段（含 CI 无源）只读 DB。
  4. `craft_builder`：为每条配方附 `properties.primary[]` 与 `properties.random{rolls, pool}`，顶层新增 `property_pools`（仅导出被引用的池，含 `chance`）；属性名带 `translation`（zh-Hans）+ `translation_key`，10 语言由 `locale_builder` 自动收录（每种语言 52 个属性键）。
  5. 前端 `CraftsPage`：卡片材料行下新增「属性」行（固定属性 + 「随机属性 ×N」标签，悬停显示整池区间与概率），新增 `ui.crafts.properties`／`random_properties`／`random_hint`（zh-Hans/en/ja/zh-Hant，与既有 `ui.crafts.*` 一致）。
  6. `collector.py` 导入阶段新增 `import_item_properties`（11 → 12 步）；`db_freshness.GENERATOR_VERSION` 提升为 `db-lifecycle-v13-item-properties`，两张新表加入 `REQUIRED_TABLES`。
- **验证**：`api/lint.sh`（ruff + black）通过；`python -m unittest discover -s tests` 全绿（新增 5 + 6 个用例）；`npm run check` 0 error；删库重建 51.37s → `import_item_properties DONE -> 1876 items, 14 random pools`（1293 件带随机池）；`data/json/crafts.json` 340 配方 / 315 条带属性 / 13 个池；寒光布面甲 = 护甲值 19~20、最大生命值 3、魔法抗性 41、移动速度 -9、动作速度 1%、随机属性 ×3（池 46 条）；SSG 3117 页，SSR HTML 直出「属性 移动速度 -10」；8081 预览 HTTP 200，Playwright 实测 zh-Hans 裁缝页卡片「材料 … | 属性 | 护甲值 19~20 | … | 动作速度 1% | 随机属性 ×3」、en 页「Stats | Armor Rating 19~20 | … | Random ×3」及悬停池文案；`test:i18n` Pass 29 / Fail 0。

### chore: 补丁部署（跳过 FMOD 同步，重建 DB 并推送 main）

- **改动原因**：用户要求「按补丁流程（不执行 ~ 同步）进行补丁部署」，即走 `docs/BUILD_AND_DEPLOY.md` 的「更新部署」，但跳过第 1 步 `~/sync_fmod.sh`（不重新同步游戏解包，沿用现有 `~/fmod/Output`）。
- **变更文件**：`docs/SESSION_CHANGES.md` + 临时跟踪的 `api/data/darkfindv5.db`（推送后立即 `reset` 并恢复 `skip-worktree`）。
- **关键逻辑/映射关系**：删库 `rm -f api/data/darkfindv5.db` → `python main.py` 全量重建（`REBUILD_REQUIRED: DB missing`，耗时 46.49s，`[VALIDATE] all module images OK`）→ 新 DB 含本日两项改动（生成器真身解析 + 同坐标候选池、掉落表稀有分组修正）。本流程不跑 `npm run build` / `vite preview`，前端 SSG 交给 GitHub Actions。
- **验证**：重建后 DB 45 张表，`spawners` 55147 / `spawner_entries` 2291 / `props_entities` 592 / `item_entities` 816 / `monster_entities` 735；`props/StatueCursedPower.json` 8 点（2 个同点候选）、`props.json` 255 条含 `StatueCursedPower`、`dungeon_modules_coords/Ruins_Square_01.json` 15 个带候选池实体；管道日志无 error/traceback。
- **部署结果**：`main` 推送前远端已多出 `8d2fbf1728 chore: update DB`（10-16 的 DB 提交），先 `git reset --hard` 去掉本地临时 DB 提交、`git rebase origin/main` 后再提交 DB；`2fed5f8fdf` 推送成功（含新 DB 48308224 字节）。GitHub Actions「Build & Deploy」4 分钟内 success。
- **线上抽查**：`https://dnd9.icetar.com/zh-Hans/props/StatueCursedPower/`、`/en/props/StatueCursedPower/` HTTP 200 且含「受诅咒的伤害神坛」；部署数据 `data/tn4bib/json/props.json` 255 条（无 `CursedStatue01`）；`Ruins_Square_01` 模块数据含同点候选池；Playwright 打开线上 `/zh-Hans/lootdrops/` 显示「稀有掉落(4)、项链(12)、戒指(7)、消耗品(15)、金币容器(4)」。（首轮抽查命中 Cloudflare 边缘缓存的旧版本 `tmzy71`，加缓存绕过后确认为新版本。）

### fix: 【掉落表】稀有掉落分组不再吞掉已分类物品（饰品行恢复）

- **改动原因**：用户反馈 `zh-Hans/lootdrops/` 的「✨稀有掉落」分组里混进了「装备饰品」分组的物品（例：公牛吊坠），且页面连「💍饰品：」整行都不显示。根因是 `groupLootdrops()` 里 `max_score` 稀有判定（`0 < max_score < 1`）排在类型元数据分组之前并 `continue`，而全部 19 件饰品（项链 12／戒指 7）的 `max_score` 都是 0.4211，于是被整包吞进稀有组，类型行永远建不出来。
- **变更文件**：`web/src/pages/ListPage.tsx`、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：稀有判定收紧为「`0 < max_score < 1` **且**（无 `item_category_key` **或** 该物品 subtype 命中 `Type_Item_Misc_HuntingLoot`〔战利品〕）」——即按用户要求「移出已有分类的掉落，保留战利品分类符合原判定稀有条件的物品」。判断用翻译键后缀而非中文译名，避免随语言失效。
- **结果**：稀有掉落 29 → **4**（午夜雄鹿之冠、午夜雄鹿之首、腐化之心、蜜悦梨，均为战利品）；「💍饰品：项链(12)、戒指(7)」行恢复，公牛吊坠归入项链；护甲 布甲 61→62、皮甲 43→44，辅助道具 消耗品 13→15，杂项 金币容器 2→4。
- **验证**：`npm run check`（eslint + prettier + tsc）通过；SSG 重建 3117 页；Playwright 实测分组按钮与稀有组 4 件内容、项链组含「公牛吊坠」，zh-Hans/en HTTP 200；`test:i18n` Pass 29 / Fail 0。

### feat: 生成器实体解析（真身补录）+ 同坐标候选池标记

- **改动原因**：
  1. 用户核对 `Ruins_Square_01_HR_D.json` 中 Statue04 同一坐标是否「有概率生成其他实体」→ 结论：是（该点 2 选 1）。
  2. 用户指出【实体表】缺少「受诅咒的神坛」这类实体，要求清查未录入原因并补录。
- **根因**：地图里的生成器**资产名**不等于它实际生成的**实体**。`CursedStatue01` 生成器无 `LootDropGroupId`，旧 `import_spawner_entries` 直接丢弃该类条目 → `search_engine` 的 `multi_entity` 只能覆盖带掉落组的生成器 → `spawners.keyword` 停在生成器名 `CursedStatue01`，真身 `StatueCursedPower` 一个坐标都没有 → `export_props` 对无坐标 props 直接 `continue` → 实体表／详情页／搜索索引全部缺失。
- **变更文件**：`api/src/db/schema.py`、`api/src/db/__init__.py`、`api/src/db/repositories/coordinates.py`、`api/src/db/importers/spawners.py`、`api/src/db/importers/spawner_coordinates.py`、`api/src/search_engine.py`、`api/src/translator.py`、`api/src/collector.py`、`api/src/entity_export.py`、`api/src/lootdrop_builder.py`、`api/src/module_builder.py`、`api/src/db_freshness.py`、`web/src/types/data.ts`、`web/src/i18n/uiLocale.ts`、`web/src/pages/DetailPage.tsx`、`web/src/pages/LootdropDetailPage.tsx`、`web/src/pages/DungeonModuleDetailPage.tsx`、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：
  1. `spawners.py::import_spawner_entries`：无掉落组但有 `PropsId`/`MonsterId` 的条目也写入 `spawner_entries`（新增 192 条无掉落组条目），速率计算提前统一（NPC 保留历史固定 100.0）。
  2. `search_engine.load_all_spawner_data`：无掉落组条目只要目标命中 props/monster 实体表就参与 `grouped`（`Id_NPC_*` 一类被过滤），展开条目携带自身 `has_lootdrop`；`ldg_to_monsters` 仍只统计带掉落组条目。于是 `CursedStatue01 → StatueCursedPower`、`CursedStatue02 → StatueCursedLuck` 等重定向生效。
  3. `spawner_coordinates.py::extract_spawners`：展开行改用 `entity_info["has_lootdrop"]`（不再硬编码 True）；`BP_*` actor 行标记 `is_container=True`；`schema.py` 的 `spawners` 新增 `is_container` 列（含 `_migrate_spawners_table` 迁移），容器行 7233 条。
  4. `coordinates.get_point_pool_info()`：按 `(map_base, json_filename, x, y, z)` 聚合非容器生成器，不同 keyword > 1 即同点候选池。
  5. `collector._point_pools`：先按 `RESOLVE_STRIP_RE` 去品质/地形后缀，再按**译名**去重（否则 `OrnateChestLarge`/`_Locked` 会重复计 4），计数与展示名同源；`translator.build_coord_out` 输出 `point_pool_size` / `point_pool_entries`（容器行不输出）。
  6. `module_builder`：每个坐标附池信息，并按实体聚合 `point_pool_size` / `point_pool_entries`（排除自身） / `point_pool_count`。
  7. 前端：`Coord`、模块 `CoordEntity` 增加上述字段；`DetailPage` / `DungeonModuleDetailPage` / `LootdropDetailPage` 显示「N选1（候选：A、B）」，新增 i18n `ui.pool.point_pool`（10 语言）。详情页对已有分组候选池（`variant_count > 1`）的坐标不再重复显示，避免双重「选1」。
- **结果**：
  - 实体表补录 **受诅咒的伤害神坛**（`StatueCursedPower`，8 点）与 **被诅咒的命运神坛**（`StatueCursedLuck`，16 点），伪实体 `CursedStatue01/02` 消失。
  - 用户核对点：`Ruins_Square_01 / 广场A` 同点 `(-1378, 203, 0.314065)` → 「速度之泉／受诅咒的伤害神坛 2 选 1」；Statue04 全库共 14 个同点候选坐标（另有生命神坛／保护神坛等 3 选 1）。
  - 同点候选池原始分组 3626 组；宝箱点位显示 3 选 1（受诅咒的箱子／黄金宝箱／狮头宝箱），矿点按矿种 2 选 1（如 铜矿／铁矿）。
- **验证**：`api/lint.sh`（ruff + black）通过；`npm run check`（eslint + prettier + tsc）通过；DB 全量重建（`GENERATOR_VERSION` → `db-lifecycle-v12-spawner-entity-resolution`）后 `spawner_entries` 2291 条、`spawners` 55147 行；SSG 构建 3117 页 / 15281 HTML；`npm run test:i18n` Pass 29 / Fail 0；Playwright 校验 zh-Hans/en/ja/ru 目标页 HTTP 200，并实际渲染「2选1（候选：受诅咒的伤害神坛）」等文案。

### feat: 【工匠】装备类标签改按「护甲部位／武器子类」分类（武器锻造师一并纳入）

- **改动原因**：用户要求「武器要分子类，装备要分部件，比如头 手 身体 裤子（检查 item 文件是否有部位属性）」。上一版只把制甲匠／裁缝／皮革匠按【掉落表】的子类分组（护甲：板甲／链甲／布甲／皮甲），既没有部位概念，武器锻造师也仍按原料分组（银粉／铁锭）。经查游戏 Item 资产确实带部位属性 `Properties.SlotType`（`Type.Item.Slot.*`）。
- **变更文件**：`api/src/db/schema.py`、`api/src/db/importers/items.py`、`api/src/db/repositories/items.py`、`api/src/db_freshness.py`、`api/src/craft_builder.py`、`web/src/i18n/uiLocale.ts`、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：
  1. **部位数据入库**：`item_entities` 新增 `item_slot_key`（建表语句 + `_migrate_item_entities_table` 迁移 + `ItemsRepository` 的可选列回退），导入时把 `Properties.SlotType.TagName`（`Type.Item.Slot.Head`）按既有 `_tag_translation_key` 规则转成翻译键；`GENERATOR_VERSION` 提升为 `db-lifecycle-v11-item-slots` 触发 DB 全量重建。实际取到的部位键：`Head` 头部／`Hands` 手部／`Chest` 胸部／`Legs` 腿部／`Foot` 脚部／`Back` 背部／`Sash` 装饰。
  2. **分类规则**：`_CATEGORY_MERCHANTS` → `_EQUIPMENT_MERCHANTS = {Armourer, Tailor, Leathersmith, Weaponsmith}`；新增 `_part_keys()`：物品类型为 Armor 且有 `item_slot_key` 时用部位键，其余（武器／辅助道具／杂项）用 `item_subtype_keys`。原因是武器的 `SlotType` 只有 `Primary`／`Secondary`（不含武器种类），只能靠 `WeaponTypes` 子类区分，正是「武器分子类」。
  3. **多武器类型**：游戏把法杖同时登记为 `Mace + Staff` 等，若按子类集合成组会切出「锤 + 杖」这类碎片组，故与【掉落表】一致地把该物品在每个子类下各列一次（`group` 逐子类克隆）。`item_count`（255）／`recipe_count`（332）改为按去重配方统计，重复卡片不影响统计口径。
  4. **无翻译的深层标签**：`..._Type_Item_Utility_Installable_Trap` 在游戏里没有独立译文，`_key_label` 改为逐级回退到最近有译文的祖级键（`..._Type_Item_Utility_Installable` → zh 部署品／en Installable／ja 設置可能），且 `translation_key` 也指向祖级键，否则非默认语言会直接显示原始键。
  5. **分节顺序**：装备类标签按「物品数降序 → 【掉落表】类别顺序 → 分组键」排序，让主要部位／子类排在最前（制甲匠「护甲：头部(12)」在前、武器锻造师「武器：剑(16)」在首、皮革匠「杂项：金币容器(3)」在末）。
  6. **结果**：分组数 79 → 53。制甲匠＝护甲：头部12／胸部8／手部8／脚部7／腿部7；裁缝＝护甲：胸部18／头部15／背部6／腿部6／手部2／脚部1；皮革匠＝护甲：脚部14／手部13／腿部9／胸部5／头部5 + 杂项：金币容器3；武器锻造师＝武器：剑16／锤13／魔法物品8／匕首6／斧5／杖5／弓4／长柄4 + 辅助道具：消耗品2／投掷物2／部署品1／照明物1／挖掘工具1 + 杂项：弹丸1 + 武器：盾1（62 物品／65 配方／73 张卡）。炼金术师、樵夫、医师、珠宝匠、矿类维持不变。
  7. **i18n**：`ui.crafts.hint` 四语言同步说明「装备类 NPC 按【掉落表】分类——护甲按部位、武器按子类」；统计行分组数 79 → 53。
- **验证**：`python main.py` 全量重建（`state=REBUILD_REQUIRED`，`import_items DONE -> 816`）后两次 `DB_READY` 仅重跑导出，`crafts export DONE -> 9 merchants, 53 groups, 332 recipes`；`api/lint.sh`（ruff + black）通过；`cd web && npm run check` 通过（Prettier + `tsc --noEmit`）；`npm run build` 3114 页 / 17121 文件（mode=quick）；`BASE_URL=http://localhost:8081 node tests/i18n.mjs` → Pass 29 / Fail 0；Playwright 逐标签核对 zh-Hans／en／ja：武器锻造师 15 段标题如上（en `Weapon:Sword(16) … Utility:Installable(1)`、ja `武器：剣(16) … ユーティリティー：設置可能(1)`），制甲匠／裁缝／皮革匠按部位（en `Armor:Head`），炼金术师与矿类未变，页面无 hydration／page error（仅既有 Cloudflare RUM CORS 报错）。
- **备注**：`api/data/darkfindv5.db` 与 `data/` 下产物均为本地生成，未纳入提交。

## 2026-10-18

### feat: 【工匠】装备类 NPC（制甲匠／裁缝／皮革匠）改用【掉落表】物品分类分组

- **改动原因**：用户指出「没有把这三个装备类 NPC 分类，他们合成的物品参考 lootdrops 中的武器/护甲分组」。上一版对这三个标签按原料分组时，每个原料集合只对应 1 件物品（制甲匠 42 条、裁缝 48 条、皮革匠 49 条几乎一物品一配方），回退物品名后又等于没有分类。
- **变更文件**：`api/src/craft_builder.py`、`web/src/types/data.ts`、`web/src/pages/CraftsPage.tsx`、`web/src/i18n/uiLocale.ts`、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：
  1. `craft_builder` 新增 `_CATEGORY_MERCHANTS = {Armourer, Tailor, Leathersmith}`：这些标签的配方改为按「物品类别 + 子类」分组，取 `item_entities.item_category_key` / `item_subtype_keys`（与【掉落表】页面同一套 `Text_Code_DCDataBlueprintLibrary_Type_Item_*` 键）：`group = "{类别序号}\u001f{category_key}\u001f{subtype_keys}"`，排序沿用【掉落表】的类别顺序 `Utility, Misc, Accessory, Armor, Weapon`，再按子类键排序；无类别/子类的物品回退「物品名」分组。
  2. 导出新增字段 `group_kind`（`ores`/`item`/`material`/`category`）与 `group_category`（类别标签，仅 category 类有），`group_parts` 在 category 类下存放子类标签。`group` 仍为分组/排序键。
  3. 前端 `groupLabel` 按 `group_kind` 渲染：category 类拼成「{类别}：{子类}」（复用【掉落表】的 `ui.list.item_group_prefix` 与语言分隔符 、/, ），其余仍为「材料 + 材料」或物品名；矿石标签仍为「矿类」。section 标题追加「(N)」＝该分组内不同物品数。
  4. 【掉落表】的分类结果：制甲匠＝护甲：链甲(3)/板甲(39)；裁缝＝护甲：布甲(47)/皮甲(1)；皮革匠＝杂项：金币容器(3)/护甲：链甲(5)/皮甲(41)。武器锻造师、珠宝匠、炼金术师等保持原有的原料分组／物品名分组（武器锻造师的「银粉」「铁锭」保留）。全局分组数 207 → 79。
  5. i18n：hint 说明装备类 NPC 按【掉落表】分类，其余按原料/物品名；统计行「79 个分组」。
- **验证**：`python main.py`（`DB_READY`，仅重跑导出）`crafts export DONE -> 9 merchants, 79 groups, 332 recipes`；`api/lint.sh`、`npm run build`（3114 页）、`node tests/i18n.mjs`（Pass 29 / Fail 0）通过；Playwright：制甲匠／裁缝／皮革匠标题为「护甲：链甲(3)」「护甲：板甲(39)」「护甲：布甲(47)」「护甲：皮甲(1)」「杂项：金币容器(3)」「护甲：链甲(5)」「护甲：皮甲(41)」，皮革匠三段卡片数 3/5/41，武器锻造师仍含「银粉(7)」「铁锭(6)」，珠宝匠 4 个宝石原料组，矿类 1 段 19 卡；en 页 `Armor:Chain` / `Armor:Plate` / `Misc:Gold Container` 正确；无 console/page error。

### fix: 【工匠】分组细化——「原料组」只在能合并多件物品时生效，否则回退物品名

- **改动原因**：用户反馈「制甲匠／裁缝／皮革匠不应该用原料分类，这样分成的分组都是 1 个物品，不符合分组初衷」。上一版对所有配方一律用原料集合当标题，导致这三个标签（制甲匠 42 条、裁缝 48 条、皮革匠 49 条几乎全是一物品一配方）出现「钴蓝锭 + 锅盔」这类无意义原料标题，分组数却没变。
- **变更文件**：`api/src/craft_builder.py`、`web/src/i18n/uiLocale.ts`、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：
  1. `craft_builder` 新增 `family_items` 统计：按 `(标签, 原料集合)` 收集物品名。**只有该原料集合能合并 ≥2 件不同物品时**，组标题才用原料名；否则该组回退为「物品名」分组（`group = 输出物品折叠名`、`group_parts = [该物品]`）。矿类标签与「同物品不同品质原料不同」的安全网逻辑不变。
  2. 分组总数不变（207）：回退后的单物品组原本也是各占一组；变化只在标题文案与排序键。
  3. 结果：制甲匠 42 组全部为物品名；炼金术师 7 组全部为物品名（清晰药水／治疗药水…）；裁缝 46 组中仅「附魔暗布 + 蜘蛛丝」（暗影兜帽／长袍／鞋 3 件）保留原料标题；皮革匠 47 组中仅「坟墓精华 + 狼皮」（2 件）、「巨魔之皮 + 狼皮」（2 件）保留；武器锻造师仍保留「银粉」（7 件）与「铁锭」（6 件）；珠宝匠仍保留 4 个宝石原料组。
  4. i18n：统计行「207 类配方」→「207 个分组」（`{groups} groups` / グループ / 個分組），hint 补充「能合并多件物品时归为一组，否则按物品名显示」。
- **验证**：`python main.py`（`DB_READY`，仅重跑导出）`crafts export DONE -> 9 merchants, 207 groups, 332 recipes`；隔离重放与 `data/json/crafts.json` 对比 `identical: True`；`api/lint.sh`、`npm run build`（3114 页）通过；Playwright 逐标签核对：制甲匠 42 个物品标题、裁缝 46 段、皮革匠 47 段（仅 2 段原料标题）、樵夫 3 段、炼金术师 7 个物品标题、矿类 1 段 19 卡、武器锻造师「银粉」7 卡；en 页标题与 `Ores` 正常；无 hydration/page error。

### fix: 【灯】页在数据到达前误显示「0 种灯具」，改为保持加载态并自动重试

- **改动原因**：用户反馈网络延迟时【灯】页显示「共 0 种灯具 | 0 个品质变体」，误判为线上没有数据。根因有二：① `useLights` 在 `fetch` 失败时把 `loading` 置为 `false` 而 `data` 仍为 `null`，页面随后渲染 `data?.count ?? 0`，计数字串直接变成 0；② 失败的 promise 被写入模块级缓存，即使网络恢复，重新挂载仍复用同一个已 reject 的 promise，页面永久卡在 0。
- **变更文件**：`web/src/hooks/useLights.ts`、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：
  1. `loading` 改由数据推导（`!data`）：payload 未到达前页面始终停留在 `ui.common.loading`（加载中...），不再渲染 0 计数；只有服务端确实返回空 payload 时才显示 0（此时页面确实为空，属正确结果）。
  2. `fetchLights` 增加 `r.ok` 校验，避免把 404/错误页 HTML 当 JSON 解析；`.catch` 中执行 `cache.delete(version)`，失败 promise 不再被缓存。
  3. 新增 `error` 状态与 5 秒自动重试（由 `attempt` 计数驱动 effect 重跑），网络恢复后自动拉取并渲染，无需用户手动刷新。
- **验证**：`cd web && npm run check` 通过（lint 0 error / 20 既有 warning、Prettier、`tsc --noEmit`）；`npm run build` 退出码 0（3113 页 / 17109 文件，mode=quick）；`npx vite preview`（8080 被占用 → 回落 8081）HTTP 200；Playwright 三轮验证：正常路径渲染「共 8 种灯具 | 45 个品质变体」且「环境」标签存在；用 CDP `Network.setBlockedURLs` 阻断 `lights.json` 时页面显示「加载中...」且**不含**「共 0 种灯具」；解除阻断后 ≤2.5s 自动恢复为 8/45。

### feat: 【工匠】栏目——按制作 NPC 分标签页展示配方与原料

- **改动原因**：用户要求新增【工匠】栏目：顶部标签页为制作 NPC 名字（替换【灯】页的 常用/不常用/环境），内容为「制作的物品 + 所需原料」，同一物品的不同稀有度归为一组，UI 仿造【灯】，数据来源限定 `V2/Merchant`。侦察发现 9 条「矿石→锭」配方在游戏数据里没有任何 NPC 归属（`MerchantSchedule` 只引用 `StockSellBack`，全库无 `StockCraft` 引用），经用户确认：单独开一个【锭制作】标签页收拢这些无归属配方。
- **变更文件**：`api/src/db/importers/crafts.py`（新增）、`api/src/db/repositories/crafts.py`（新增）、`api/src/craft_builder.py`（新增）、`api/src/db/schema.py`、`api/src/db/__init__.py`、`api/src/db/importers/__init__.py`、`api/src/db/repositories/__init__.py`、`api/src/config.py`、`api/src/collector.py`、`api/src/index_export.py`、`api/src/db_freshness.py`、`api/src/locale_builder.py`、`web/src/hooks/useCrafts.ts`（新增）、`web/src/pages/CraftsPage.tsx`（新增）、`web/src/types/data.ts`、`web/src/AppInner.tsx`、`web/src/components/NavBar.tsx`、`web/src/pages/HomePage.tsx`、`web/src/i18n/uiLocale.ts`、`web/src/i18n/seoTemplate.mjs`、`web/src/i18n/seoTemplate.d.mts`、`web/scripts/ssg.mjs`、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：
  1. 数据源：`V2/Merchant/StockCraft`（一个文件一条配方，共 **332** 条）+ `V2/Merchant/Merchant`（取有 Craft 服务的商人：显示名 `Properties.Name.Key`、酒馆顺序 `Properties.Order`）。新增 DB 表 `craft_recipes`（`recipe_id`=资产名`#索引`、产物裸名+折叠名+品质、`requirements_json`、话术 key）与 `craft_merchants`（`kind` = `npc` / `ingot`，含 `sort_order`），并加 `idx_craft_recipes_merchant` 索引。
  2. NPC 归属三级判定（`CraftsImporter._owner`）：① 文件名 `Id_StockCraft_<商人>_NN` 且该商人在 Craft 商人表内（Alchemist/Armourer/Goldsmith/Leathersmith/Surgeon/Tailor/Weaponsmith/Woodsman）；② 配方的 conversation key `..._StockCraft_Conversation_<商人>_...`（3 个钱袋 GoldBag/GoldPouch/SpectralCoinbag → **Leathersmith**，故皮革匠 49 条 = 46 + 3）；③ 其余无归属者（9 条矿石→锭）归入合成标签 `__ingots__`，`sort_order=1000` 排在最后，前端用 `ui.crafts.tab.ingots`＝「锭制作」渲染。
  3. 品质由物品名 `_1001~_8001` 后缀映射（Poor→Artifact，与地牢商店/掉落页同表）；产物与原料统一存**折叠名**（`VoidBlade_5001` → `VoidBlade`），导出时按「商人 → 折叠物品名 → 品质 → UniqueID」排序，前端单趟扫描即可把同一物品的不同稀有度归为一组。
  4. 导出阶段只读 DB：`craft_builder.build_and_save_crafts()` 产出 `data/json/crafts.json`（`count`=9 个标签、`item_count`=255 组、`recipe_count`=332）。NPC 显示名走 `Text_DesignData_Merchant_Merchant_<Name>` 翻译键，因此 `locale_builder` 把 `crafts.json` 纳入 `_collect_keys` 收集（否则非 zh-Hans 语言只有中文回退值）。
  5. 前端：`useCrafts` 与修好的 `useLights` 同构（数据未到前保持加载态、失败 5s 自动重试、失败 promise 不入缓存）；`CraftsPage` 顶部标签＝NPC 名（附组数），卡片＝品质色 + 「材料：名称×数量」（原料按各自品质着色），点击卡片注入搜索框查询该物品。
  6. 接线：`index.json` 新增 `{page: crafts, label: 工匠, count: 9}` 与 `_nav` 搜索项、HomePage 卡片主题/文案、路由 `/:lang/crafts`、NavBar 面包屑与搜索标签、`db_freshness` `REQUIRED_TABLES` 增表并把 `GENERATOR_VERSION` 提升为 `db-lifecycle-v9-craft-recipes`（触发 DB 全量重建）、SSG `SINGLE`/`routeDataKey` 新增 `crafts`（每语言生成 `/{lang}/crafts/`）。
- **验证**：
  - 管道全量重建（`[DB] state=REBUILD_REQUIRED`）：`import_craft_recipes DONE -> 9 merchants, 332 recipes`、`crafts export DONE -> 9 merchants, 255 items, 332 recipes`，管道总耗时 47.05s，无 error/traceback。
  - 隔离重放：用真实 DB 跑 `build_and_save_crafts` 与已交付的 `data/json/crafts.json` 对比 `identical: True`。
  - `api/lint.sh`（ruff + black）通过；`cd web && npm run check` 通过（lint 0 error / 20 既有 warning、Prettier、`tsc --noEmit`）。
  - `npm run build` 退出码 0（3114 页 / 17121 文件，mode=quick；10 语言 sitemap 各 1338 URL）；`npx vite preview`（8080 被占用 → 落 8081）`/zh-Hans/crafts/`、`/en/crafts/`、`/ja/crafts/` 均 HTTP 200。
  - Playwright：zh-Hans 渲染 9 个标签（炼金术师17/医师1/制甲匠42/武器锻造师62/樵夫3/裁缝48/皮革匠49/珠宝匠24/锭制作9）与统计行「共 9 位工匠 | 255 种可制作物品 | 332 条配方」；「清晰药水」的优秀/罕见两条配方归入同一组；「锭制作」标签显示 9 种锭（钴锭/铜锭/霜石锭/金锭/铁锭/黑曜石锭/红宝石银锭/银锭/潮汐石锭）；en 页标签与材料正确（Ingots、Materials、Brimstone Ore×2）；无 hydration/page error（仅既有的 Cloudflare insights CORS 报错）。`BASE_URL=http://localhost:8081 node tests/i18n.mjs` → Pass 29 / Fail 0。
- **备注**：`api/data/darkfindv5.db` 为 skip-worktree 跟踪文件，本次未纳入提交；`data/json/crafts.json` 已由本次管道生成。

### feat: 【工匠】按「共用原料」归组，矿石／银币精炼配方并入「矿类」标签

- **改动原因**：用户要求「把原料比较相同的配方归到一个分组（如银粉），矿类也归到一个分组（如铜矿做铜粉、金矿做金粉）」。确认后落为两条规则：① **用到同一种原料的配方合成一组**，组标题＝该原料（如「银粉」组＝7 把纯银武器、「铁锭」组）；② 所有**纯矿石／银币精炼**配方（粉末 + 锭）合并为一个「矿类」组，并把炼金术师里的矿石→粉末配方移入原【锭制作】标签，标签改名为「矿类」。
- **变更文件**：`api/src/db/importers/crafts.py`、`api/src/craft_builder.py`、`api/src/db/schema.py`、`api/src/db_freshness.py`、`api/src/collector.py`、`web/src/types/data.ts`、`web/src/pages/CraftsPage.tsx`、`web/src/i18n/uiLocale.ts`、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：
  1. 归属规则新增最高优先级：原料**全部**是矿石（`*Ores`）或银币/金币的配方视为「纯精炼」，一律归属合成标签 `__ores__`（`kind='ores'`、`sort_order=1000`），改名前为 `__ingots__`/`ingot`；因此炼金术师的 10 条矿石→粉末配方移入该标签，与原【锭制作】的 9 条合成 19 条。
  2. 导出新增分组字段：`group`（分组键）+ `group_parts`（标题片段，前端按当前语言拼接成「A + B」）。分组键＝配方的原料名集合，**去掉银币/金币这类通用货币**（它们被 95/78 条无关配方共用，会导致跨类合并），仅当货币是唯一原料时才保留；组内按「分组键 → 物品 → 品质」排序，前端单趟扫描即可分组。`__ores__` 标签只有一个分组，其 `group_parts` 为空，标题回退到 `ui.crafts.tab.ores`。
  3. 安全网：某物品的不同品质若用到**不同**原料（手术包／镐／营火工具包／樵夫斧），该物品仍按物品单独成组，保证「同一物品不同品质归为一组」不被拆散（其余多品质物品因原料一致自然同组）。
  4. 标签页徽标由「物品数」改为「配方数」（矿类 19、珠宝匠 81…）；统计行改为「共 9 位工匠 | 207 类配方 | 255 种可制作物品 | 332 条配方」。`GENERATOR_VERSION` 升为 `db-lifecycle-v10-craft-ores` 以触发 DB 重建。
  5. 前端 `CraftsPage` 改为按 `recipe.group` 单趟分组、标题用 `group_parts` 拼接；i18n 把 `ui.crafts.tab.ingots` 改为 `ui.crafts.tab.ores`（矿类 / Ores / 鉱石 / 礦類），并更新 `ui.crafts.stat`（新增 `{groups}`）与 `ui.crafts.hint`。`craft_builder` 重命名 `_resolve_item` → `_ItemLabel` 并新增 `_signature()`。
- **验证**：管道全量重建（`REBUILD_REQUIRED`）`import_craft_recipes DONE -> 9 merchants, 332 recipes`、`crafts export DONE -> 9 merchants, 207 groups, 332 recipes`；隔离重放 `build_and_save_crafts` 与 `data/json/crafts.json` 对比 `identical: True`；`api/lint.sh`、`cd web && npm run check`（0 error / 20 既有 warning）、`npm run build`（3114 页）均通过；Playwright：标签「炼金术师20／医师2／制甲匠42／武器锻造师65／樵夫6／裁缝48／皮革匠49／珠宝匠81／矿类19」，炼金术师 7 个原料分组（生命之叶／幻影花／盐藤／护符草／生命之叶 + 护符草…），矿类 1 组 19 张卡（硫磺粉／钴锭／钴粉／铜锭…），珠宝匠 9 组（「奥术精华 + 蓝宝石」24 条 6 物品…），武器锻造师含「银粉」组（7 张）与「铁锭」组，医师「手术包」2 张同组；en 页 Ores／Goldsmith 标题正确；无 hydration/page error（仅既有 Cloudflare insights CORS 报错）。
- **备注**：材料名（如 en 的「Ruby (Cracked)」）沿用折叠物品名的既有翻译键约定，与站点其他页面一致；如需按品质后缀显示精确名称可后续单独调整。

## 2026-10-16

### chore: 补丁部署——同步游戏数据并全量重建 DB

- **改动原因**：按请求执行 `docs/BUILD_AND_DEPLOY.md`「更新部署」流程，游戏更新后同步 FMOD 解包数据并全量重建 SQLite，随后把含新 DB 的 `main` 推到 `origin/main` 供 Actions 导出 JSON。
- **变更文件**：`api/data/darkfindv5.db`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：`~/sync_fmod.sh` 已完成（跳过）；删除 `api/data/darkfindv5.db` 后重跑 `python main.py`，从同步后的游戏 JSON 全量重建数据库与 JSON 导出。
- **验证**：`api/pipeline.log` 无 error/traceback，管道总耗时 51.57s；sqlite-debug 确认 DB 可读、43 张表，关键表 `spawners=54298`、`monster_entities=739`、`lootdrop_groups=69771`、`item_entities=816`、`props_entities=598`。

### docs: 备份「旧版灯持续时间」参数表

- **改动原因**：游戏更新（0.18.156）后火把燃烧时间由 60/75/90/105/120/150/180 调整为 90/115/135/160/180/225/270。为便于更新后做新旧对比（视频解说），先备份更新前的【灯】页面参数。
- **变更文件**：`docs/旧版灯持续时间.md`（新增）、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：数据取自 `data/json/lights.json`（更新前），按页面结构分为「常用」（火把/灯笼/机关盾）与「不常用」两组；列为 `原始 ID | 灯具 | 品质 | 燃烧时间（秒） | 照明范围`，共 8 种灯具 / 45 个品质变体，`原始 ID` 作为后续新旧合并的连接键。照明范围本次未变（火把/灯笼=300，其余=120）。
- **备注**：【灯】页面功能代码（后端 `light_items`/`light_builder`、前端 `LightsPage`/`useLights`、SSG 路由）已在工作区完成并通过 lint/tsc/实机验证，待新数据同步后与前端一并提交；本次仅本地提交该备份文档。

### feat: 【灯】页面新增「环境」分类（Props 光源）

- **改动原因**：用户要求把 Props 目录中带 `FuelSeconds` 的发光场景道具（火把/灯架/灯/蜡烛等）也纳入【灯】页面，作为第三个分类标签「环境」。此前页面只收录同时具备 `FuelSeconds` 与 `LightAreaRadius` 的物品，而场景 Props 有燃料时长却无照明范围字段，被过滤掉；经全库搜索确认 `FuelSeconds` 分布在 59 个 Props 文件与 45 个 Item 文件，`LightAreaRadius` 仅存在于 Item。
- **变更文件**：`api/src/db/schema.py`、`api/src/db/importers/props.py`、`api/src/db/repositories/props.py`、`api/src/db/__init__.py`、`api/src/collector.py`、`api/src/light_builder.py`、`api/src/db_freshness.py`、`web/src/types/data.ts`、`web/src/pages/LightsPage.tsx`、`web/src/i18n/uiLocale.ts`、`docs/SESSION_CHANGES.md`；前端特性其余文件（`nav`/`home`/`AppInner`/`ssg`/`seoTemplate`/`useLights`）随【灯】页面本体一并纳入本次提交。
- **关键逻辑/映射关系**：
  1. 新增 `environment_lights(raw_name PK, item_name, translation_key, fuel_seconds, fuel_seconds_max, only_in_swarm)` 表；`PropsImporter.import_environment_lights()` 扫描 `PROPS_DIR`，只保留 `FuelSeconds > 0` 的 Props（共 59 个），`Name.Key` 经 `TRANSLATION_KEY_ALIAS_MAP` 作分组键，`FuelSecondsMax` 非数值时回退 `FuelSeconds`，`FuelBurnsOnlyInSwarm` 归一为 `only_in_swarm`。
  2. `PropsRepository.get_environment_lights()` 读回、`DatabaseManager.get_environment_lights()` 透出；`light_builder.build_and_save_lights()` 增加 `environment` 参数，`lights.json` 新增 `environment`（59 条）与 `environment_count`（6 组：火把/灯架子/灯/蜡烛/冰渊灯架/水晶灯架），导出阶段仍只读 DB。
  3. `collector.py` 新增 `import_environment_lights` 导入阶段并把行集传入导出；`db_freshness.py` 版本升到 `db-lifecycle-v8-environment-lights`，`REQUIRED_TABLES` 增加 `environment_lights`。
  4. 前端 `LightsPayload` 增加可选 `environment`/`environment_count` 与 `EnvironmentLight` 类型（兼容旧数据）；`LightsPage.tsx` 新增第三个标签「环境」，按 `translation_key` 分组成同族，卡片显示燃烧时间区间（`fuel_seconds~fuel_seconds_max`，如 `45~112秒`，两者相等时只显示单值）与「仅虫潮」标记；标签页提示文案随 tab 切换为环境专用说明。
  5. i18n 新增 `ui.lights.tab.environment` / `ui.lights.swarm` / `ui.lights.env_hint`（zh-Hans/en/ja/zh-Hant 四语言）。
- **验证**：隔离测试（内存 DB 直连游戏源）导入 `59` 行 / `6` 组，`build_and_save_lights` 输出 `environment` 59 条、`environment_count` 6；`web/npm run check` 通过（0 error）；`api/lint.sh`（ruff + black）通过；Playwright 在 8081 实机点击「环境」标签，渲染 6 组 59 张卡片，中文标签正确（蜡烛/水晶灯架/冰渊灯架/灯/灯架子/火把），燃烧时间显示 `20~60秒`、`45~112秒`，无 page error；测试后已还原被临时改写的 `data/json/lights.json`（md5 校验一致）。
- **备注**：`data/json/lights.json` 需重跑管道后才会带上 `environment` 段（由另一进程负责同步/重跑）；本次仅本地提交代码与文档。

## 2026-10-15

### fix: 商店效果区间改由 DB 承载，修复 Actions 无游戏源导致的 CI 失败

- **改动原因**：推送前做 CI 等价仿真（把项目复制到 `/tmp` 使 `PROJECT_DIR` 指向无游戏解包目录的位置）发现两处必然失败，证明当前 HEAD 一旦推送 CI 必红：1) `267635be3` 的幸运药水效果区间在**导出阶段**读游戏资产（`ActorStatusEffect`/`GameplayAbility`/`ItemAbility`），而仓库与 DB 里都没有这些文件，Actions 无游戏源时 `effect` 全部落为 `null`，线上商店页不显示区间；2) `api/tests/test_consumable_effects.py` 直接读源目录并断言 `ACTOR_STATUS_EFFECT_DIR`/`POTION_ABILITY_DIR` 存在，`test_merchant_builder.py` 也调用 `build_effect_index()` 读源，无游戏源时 3 failures + 7 errors。该问题违反项目规则「解包 JSON 只能用于导入阶段，导出只能从 DB 读取」。
- **变更文件**：`api/src/db/schema.py`、`api/src/db/importers/effects.py`（新增）、`api/src/db/importers/__init__.py`、`api/src/db/repositories/merchants.py`、`api/src/db/__init__.py`、`api/src/collector.py`、`api/src/merchant_builder.py`、`api/tests/test_consumable_effects.py`、`api/tests/test_merchant_builder.py`、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：
  1. 新增 `item_effects(item_name TEXT PRIMARY KEY, effect_json TEXT)` 表：把 `{values, rolls}` 摘要按商品名持久化，使导出阶段无需再接触解包目录。
  2. 新增 `ItemEffectsImporter`：从 `ingame_merchant_stock` 取出在售商品名，经 `resolve_item_effects(build_effect_index(), ITEM_ABILITY_DIR)` 解析后写库，仅导入阶段读游戏源。
  3. `InGameMerchantRepository.get_item_effects()` 读回摘要（表缺失时返回 `{}`，兼容旧 DB）；`DatabaseManager.get_ingame_merchants()` 增加 `effects` 字段。
  4. `build_shop_data()` 删除 `effect_index` / `item_ability_dir` 参数，改为直接消费 `merchant_data["effects"]`；`collector.py` 移除 `ITEM_ABILITY_DIR` 与 `build_effect_index` 引用（满足 `test_runtime_io_guard` 的运行时禁止解包路径约束），并在导入阶段插入 `import_item_effects` 步骤。
  5. 测试改为**夹具驱动**而非跳过：`test_consumable_effects.py` 内联真实资产结构（8 档 Luck 数值、4 张蓝图权重表、能力映射）写入临时目录，保留原有全部解析断言并新增 `MissingSourceTest`（缺源时返回空且不抛错）；`test_merchant_builder.py` 改为通过 `merchant_data["effects"]` 传入，并新增 `ItemEffectsImporterTest` 覆盖「导入→仓储读回」与缺表兜底。
- **验证**：CI 等价仿真（`/tmp` 无游戏源）后端 `Ran 142 tests ... OK`（修复前为 3 failures + 7 errors）；本地含游戏源同样 142/142、`api/lint.sh`（ruff + black）通过；删库全量重建 41.74s，`import_item_effects DONE -> 2 items`，新 DB 41 表 / integrity ok / `item_effects` 两行（5001 → `[100,200]`、6001 → `[200,300]`）；在无游戏源副本中以 DB-only 模式重跑管道成功，导出 `dungeon_shops/Crypts.json` 的 4 处 `effect` 与本地有源结果完全一致；前端 `npm test` 通过（0 errors / 20 既有 warnings、Prettier、tsc），`npm run build` 退出码 0（3111 页 / 17106 文件）；8084 预览 HTTP 200，Playwright 多语言回归 29/29，实机确认 zh-Hans/en/ja 商店详情页分别显示 `幸运 +100~200`、`Luck +100~200`、`幸運 +100~200` 及 `幸运 +200~300`，无 page error。
- **备注**：本次为补丁部署前的必要前置修复，修复后按补丁流程随新 DB 一并推送 `main`。

## 2026-10-13

### feat: 展示 GoblinSmuggler 每局刷新上限

- **改动原因**：用户反馈 GoblinSmuggler 页面没有生成率显示。排查发现该 NPC 的 24 个坐标全部为固定刷怪点（无 `sub_group_parent`、无 ObjectLinker 子池），但游戏资产 `Id_Spawner_New_NPC_GoblinSmuggler.json` 中 6 个区域变体（Crypts/Goblin/IceCavern × N/HR）均带 `SessionSpawnLimit: 1`，表示一次对局全局最多出现 1 个、从 24 个点位中随机择一。此前管道完全丢弃该字段，页面因此无法解释"为什么有时遇不到"。
- **变更文件**：`api/src/db/schema.py`、`api/src/db/importers/spawners.py`、`api/src/db/repositories/lootdrops.py`、`api/src/db/__init__.py`、`api/src/collector.py`、`api/src/entity_export.py`、`api/tests/test_session_spawn_limit.py`、`web/src/types/data.ts`、`web/src/pages/DetailPage.tsx`、`web/src/i18n/uiLocale.ts`、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：
  1. `spawner_entries` 表新增 `session_spawn_limit INTEGER NOT NULL DEFAULT 0` 列；`spawners.py:import_spawner_entries()` 从 `SpawnerItemArray[].SessionSpawnLimit` 取值（非 int 归一为 0）。
  2. 原先 `if not ldg_path: continue` 会丢弃无掉落组的 NPC spawner；改为仅在 `session_spawn_limit > 0` 且能解析 `entity_name` 时保留该行（`spawn_rate=100.0`、`lootdrop_group_id=''`），使上限能到达实体导出。
  3. 新增 `LootdropsRepository.get_session_spawn_limits()`：按 `entity_name` 取 `MAX(session_spawn_limit)`，仅返回 >0 的实体；`DatabaseManager.get_session_spawn_limits()` 透出，`collector.py` 在实体导出前一次性读取。
  4. `entity_export.py:export_monsters()` 新增 `session_spawn_limits` 参数，按翻译键分组后取组内最大值写入详情 JSON 顶层 `session_spawn_limit`（0/缺失则不写）。
  5. 前端 `MonsterEntity` 增加可选 `session_spawn_limit`；`DetailPage.tsx` 在 `<h1>` 标题之后、`<Disclaimer />` 之前渲染提示条。**不放在分组爆率行或单个模块图底下**：该属性是全局约束，而 GoblinSmuggler 横跨 8 个区域分组和 24 个模块卡片，放在任一副标题位置都会只出现一次或在每个卡片重复 24 次，且易被误读为区域/模块级限制。
  6. `uiLocale.ts` 为 10 种语言新增 `ui.detail.session_spawn_limit`（`一次对局最多出现 {count} 个` 等）。UI 文案不走 locale 字典（`locale_builder.py:139` 显式过滤 `ui.` 前缀），故无需重建 locale 产物。
- **数据范围**：全量扫描 541 个 Spawner 资产，`SessionSpawnLimit` 仅 6 项非零，全部属于 GoblinSmuggler 的 6 个区域变体且均为 1；其余 2303 项为 0（不限制）。导出产物中仅 `Id_NPC_GoblinSmuggler.json` 含该字段，验证无其他实体被误标。
- **验证**：`python3 -m unittest discover -s tests` 73/73 通过（新增 `test_session_spawn_limit.py` 5 例，覆盖 NPC 无掉落组保留上限、普通 spawner 记录上限、缺省归零、按实体聚合、0 值被过滤）；`api/lint.sh` 通过（ruff + black）；`cd web && npm test` 通过（lint 0 errors / 20 既有 warnings、Prettier、tsc）；`python main.py` 全量重建（删库后 43.25s）确认 `data/json/monsters/Id_NPC_GoblinSmuggler.json` 含 `session_spawn_limit: 1`、`translation_key: Text_DesignData_Monster_NPC_GoblinSmuggler`、24 坐标；`npm run build` 退出码 0（3107 页 / 17058 文件），`dist/data/{ver}/json/monsters/Id_NPC_GoblinSmuggler.json` 含新字段；Playwright 实机验证 10 种语言文案全部正确渲染，CaveTroll/Abomination/LootGoblin 三个无限制实体页无泄漏、无 page error。
- **环境备注**：本机 `npm` 不在默认 PATH，需使用 `~/.nvm/versions/node/v22.22.0/bin`；`python main.py` 只读查询大表时报 `unable to open database file`，需设置 `SQLITE_TMPDIR=/tmp`（sqlite 在同目录创建排序临时文件被沙箱拦截）。端口 8080 被本机 nginx 上的 WordPress（HBOT1 A4 Local）占用，本次预览服务改用 8081。

### feat: 掉落池标签全量 i18n（修复 SpectralKnight 等页面显示原始 id）

- **改动原因**：`http://localhost:8081/zh-Hans/monsters/SpectralKnight/` 的掉落物分页标签显示未翻译的原始 token：`Bloodbound_5001`、`Cloak_Physical`、`SpectralKnight`、`QuestItem_SpectralFabric`、`QuestItem_SpectralHilt`。根因是 `MonsterDropSwitch.tsx` 的 `poolLabel()` 硬编码只查 `ui.monster_drops.pool.{stem}`（仅 12 个通用池有覆盖），其余 364 个掉落池全部回退到原始 id。
- **变更文件**：`api/src/monster_drops_builder.py`、`api/src/locale_builder.py`、`api/tests/test_monster_drops_builder.py`、`web/src/types/data.ts`、`web/src/components/MonsterDropSwitch.tsx`、`web/src/i18n/uiLocale.ts`、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：`resolve_pool_text(lootdrop_id, translations, entity_index) -> (text, key, sub_label)` 六级解析：
  1. **纯标签池**（`Cloak_Physical`、`Treasure`、`Utility`、`GradedRoll_Ruby` 等无 Game.json 键）→ 合成键 `df5.lootpool.{core}`，10 语言值定义在 `POOL_LABEL_TRANSLATIONS`。
  2. **物品分类池** → `_POOL_CATEGORY_KEYS`（`ChestArmors`→`...Type_Item_Category_Armor`、`Consumables`、`Gems`、`Trinkets`）。
  3. **容器实体池** → `_POOL_PROP_KEYS`（`Barrels`→`Props_WoodBarrel`、`Crates`→`Props_WoodenCrateSmall`、`CommonCoffins`、`FlatChestLarge`、`HoardTreasure`→`Props_Hoard`）。
  4. **实体同名池** → 官方 `Text_DesignData_{Item_Item|Monster_Monster|Props_Props|Props_Props_Ore}_{name}` 键。
  5. **项目硬编码名**（`Lumber`→木材、`Bones`→骸骨）。
  6. **兜底**：技术名可读化为英文（`Drop_Barrel_Junk`→`Barrel Junk`），保证永不显示原始 id。
- **名称归一化规则**（`_lookup_entity_key`）：按候选顺序尝试，命中即返回 `(key, borrowed)`：
  - 剥离 `Drop_/Spawn_/Monster_/QuestItem_/QuestSpecial_` 前缀；
  - 剥离 `_Spoils` 后缀（`CaveTroll_Spoils`→`CaveTroll`）；
  - 剥离子池标记 `_Misc/_Gear/_Jewelry/_Ore`（`Yeti_Gear`→`Yeti`、`LavaGolem_Ore`→`LavaGolem`），此类回退记 `borrowed=True`；
  - 拼写别名 `_POOL_ENTITY_NAME_ALIASES`（`FrostGiantSheilder`→`FrostGiantShielder`、`PirateCrossbow`→`PirateCrossbowman`、`GoldChest`→`GoldenChest` 等 10 条）；
  - 大小写不敏感索引 `_build_entity_key_index`（`BlueMarlin`/`Bluemarlin`、`TideWalkerShaman`/`TidewalkerShaman`），预计算小写映射避免每次全表扫描。
- **同名消歧**：子池复用宿主实体名会与宿主主池重名（页面上原本 66 处）。改用 `sub_label` 字段（合成键 `df5.lootpool.{Spoils|Gear|Jewelry|Ore|Misc}`），前端拼 `宿主名 · 后缀`。前端渲染后重名归零。注意该后缀**不能**用中文硬编码（此前误写 `f"{base} 战利品"` 会导致 10 语言页出现中文）。
- **默认语言 locale 不加载的坑**：`useLocale()` 对 `DEFAULT_LANG`（zh-Hans）执行 `setDict(null)`、不 fetch locale 文件，只返回 UI 字典。因此 `df5.lootpool.*` 后缀键必须**同时**写入 `web/src/i18n/uiLocale.ts`（10 语言 × 5 键），否则仅中文页丢后缀而英文页正常。池主体名不受影响（中文走 `pool.translation` 兜底）。

### fix: 补齐剩余掉落池标签（SkeletonWarlord 等 59 处英文残留）

- **改动原因**：上一条提交后全站仍有 59 个池标签落到英文兜底（去重 26 个），用户反馈 `SkeletonWarlord` 页面显示 `Warlord` 而实际应为「骷髅督军」。根因有三：① `GradedRoll_CrackedTrinkets` 标签条目在先前编辑中被误删；② 池名只是宿主实体名的缩写（`SkeletonWarlord` → `Warlord`）时无从得知宿主；③ `_Spoils` 变体（`IceKoboldBowman_Spoils`）用未剥离后缀的 core 去查标签表，查不到。
- **变更文件**：`api/src/monster_drops_builder.py`、`api/tests/test_monster_drops_builder.py`、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：
  1. `resolve_pool_text()` 新增 `host_entity` 参数：`build_loot_pools` 传入页面实体名 `monster`；当池名是宿主名的后缀且池名自身无官方键时（`host.lower().endswith(spoils.lower())` 且两者不等），回退到宿主的官方键。该分支位于硬编码名之后、英文兜底之前，避免抢先覆盖官方键。全站仅 `SkeletonWarlord` 的 `Drop_Warlord` / `Drop_Warlord_Spoils` 命中，无误伤。
  2. 标签表查找改为依次尝试 `core` 与剥离 `_Spoils` 后的 `spoils` 两个候选，使 `X_Spoils` 能复用 `X` 的标签并保留 spoils 后缀。
  3. `_lookup_entity_key()` 候选列表追加「剥离尾部数字」的变体（`Banshee2` → `Banshee`），命中官方键 `Text_DesignData_Monster_Monster_Banshee`=报丧女妖。
  4. 补回 `GradedRoll_CrackedTrinkets`，并新增 25 个标签（10 语言）：`Accessory_Rare` 稀有饰品、`Quiver` 箭袋、`SkeletonSwordsman` 骷髅剑士、`SkeletonCorpses` 骷髅尸骸、`SkeletonBones` 骸骨、`Crate_Supplies` 木箱补给、`Barrel_Junk` 杂物桶、`Barrel_Stores` 储物桶、`PoorCoffins` 简陋棺材、`Stonetombs` 石墓、`Herbs` 草药、`Pants` 裤子、`Pots` 罐子、`Utility_CrateMedium`、`Trinkets_NoCoin`、`HoardWeaponArmor`、`Spawn_GoldCoinChest`、`Cyclops_TrollBlood`、`IceKoboldBowman`、`IceHarpy_Jewelry`、`Whitewalker` 白行者、`WebSpider` 网蛛、`Banshee2`、`FlameButterflyUnique`、`Slime_Quest`。
- **验证**：`python3 -m unittest discover -s tests` 91/91 通过（新增 3 例：已知标签池被翻译、真正未知池走英文兜底、`_Spoils` 变体复用基础标签；原 `Barrel_Junk` 兜底用例改为断言其标签已生效）；`api/lint.sh` 通过；`python main.py` 全量重建后**全站纯英文池标签归零**；`npm run build` 退出码 0；Playwright 实机验证 zh-Hans/en：SkeletonWarlord 显示 `物理披风 / 骷髅督军 / 骷髅督军 · 战利品 / 坟墓精华 / …`（英文 `Skeleton Warlord / Skeleton Warlord · Loot`），FrostWalker 显示 `白行者 / 白行者 · 战利品`，IceKoboldArcher 与 SkeletonSwordman 同理，无 page error。
- **locale 导出**：`locale_builder._collect_keys()` 的键名白名单新增 `sub_label`，否则 `df5.lootpool.*` 后缀键不会被收集、不会进入 `data/json/locale/*.json`。`build_locale_files()` 将这些合成键从 DB 查询中剥离并按语言注入（共 19 个键 × 10 语言）。
- **前端渲染**：`MonsterLootPool` 新增 `translation`/`translation_key`/`sub_label`；`poolLabel(pool, ut, t)` 优先 `translation_key` → `translation` → 旧 `ui.monster_drops.pool.{stem}` → 去前缀 stem。保留旧 fallback，已生效的 12 个通用池不受影响。
- **验证**：`python3 -m unittest discover -s tests` 87/87 通过（新增 `PoolLabelTest` 14 例：物品/怪物/任务物品/`_Spoils`/大小写变体/拼写别名/分类/容器/矿石/合成键/硬编码/可读英文兜底/子池借名/`Monster_` 前缀）；`api/lint.sh` 通过；`cd web && npm test` 通过（lint 0 errors / 20 既有 warnings、Prettier、tsc）；`python main.py` 全量重建（29.55s，0 错误）；全站扫描 686 个 pool 标签，**残留原始技术名 0 个**、前端渲染后页内重名 0 处；`npm run build` 退出码 0（3107 页 / 17058 文件）；Playwright 实机验证 zh-Hans/en/ja/de 四个语言页：SpectralKnight 显示 `血缚 / 物理披风 / 鬼灵骑士 / 冥界织物 / 幽冥剑柄`（英文 `Physical Cloaks / Spectral Knight`），CaveTroll 显示 `洞穴巨魔 / 洞穴巨魔·战利品 / 洞穴巨魔·杂项`（英文 `Cave Troll / Cave Troll · Loot / Cave Troll · Misc`），无 page error。

### feat: 单物品掉落池合并为【杂项】标签页

- **改动原因**：用户反馈掉落物表被大量「一个池只装一个物品」的标签割裂——例如 `SkeletonWarlord` 页有 `坟墓精华 / 蛆虫 / 旧布 / 督军的铠甲残片 / 督军的断剑` 等独立标签，每个标签内容与标签名完全重复，既占满标签栏又无信息量。全站扫描确认共 340 个单物品池分布在 148 个页面上，其中 216 个是 `QuestItem_*` 池（**全部**恰好只有 1 个物品）。
- **变更文件**：`api/src/monster_drops_builder.py`、`api/tests/test_monster_drops_builder.py`、`web/src/types/data.ts`、`web/src/components/MonsterDropSwitch.tsx`、`web/src/i18n/uiLocale.ts`、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：
  1. `build_loot_pools()` 新增 `misc_items` 收集容器。在既有的「单物品消耗品并入 consumable」判定**之后**追加分支：`len(remaining_deduped) == 1` 的池不再独立成 tab，而是并入 `misc_items`。顺序很重要——消耗品优先，保持原有 `consumable` 行为不变。
  2. 合并后的杂项池以 `{"id": "misc", "kind": "misc", "lootdrop_id": None, "items": _dedupe_items(misc_items)}` 形式**追加到池列表末尾**，使具名池（金币、宝藏、披风等）继续保持前置标签位。物品按 `page` 去重（`_dedupe_items`），与既有合并池一致。
  3. 前端 `MonsterLootPool.kind` 联合类型新增 `'misc'`；`poolLabel()` 增加 `pool.kind === 'misc'` → `ut('ui.monster_drops.misc')` 分支，与 `quest`/`artifact`/`consumable` 走同一套渲染路径（无需改动渲染与事件逻辑）。
  4. `uiLocale.ts` 为 10 种语言新增 `ui.monster_drops.misc`（杂项/Misc/Sonstiges/Varios/Divers/その他/기타/Diversos/Разное/雜項）。UI 文案不走 locale 字典（`locale_builder.py` 过滤 `ui.` 前缀），故无需重建 locale 产物。
- **不误伤重要池的验证**：具名通用池在真实数据中均为多物品，不受影响——`Drop_Gems` 4 项、`Spawn_Treasure` 15 项、`Drop_Trinkets` 17 项、`Drop_Utility` 17 项、`Drop_HoardTreasure` 26 项、`Drop_Crates` 166 项、`Drop_Coin` 2 项、`LootGoblin_StolenGoods` 14 项。`RuinsGolem` 的 `_Ore` 子池有 4 项，保留独立标签「废墟魔像 · 矿石」；其单物品 `_Spoils` 池才并入 misc。
- **验证**：`python3 -m unittest discover -s tests` 95/95 通过（新增 `MiscPoolMergeTest` 4 例：多个单物品池合并为单一 misc、多物品池保留独立标签且 misc 置尾、misc 内按 page 去重、无单物品池时不生成 misc；另更新 4 个以单物品池为夹具的既有用例，其核心断言意图保持不变）；`api/lint.sh` 通过；`cd web && npm run lint` 0 errors / 20 既有 warnings、`npx tsc --noEmit` 通过；`python main.py` 全量重建后 `data/json/monsters/SkeletonWarlord.json` 由 11 个池变为 5 个（`artifact / consumable / 物理披风 / 骷髅督军 / misc`），misc 内 6 个物品与合并前逐一对应、无丢失；全站标签总数 **745 → 554（减少 191，约 25%）**，148 个页面获得杂项标签；`npm run build` 退出码 0（3107 页 / 17058 文件）；Playwright 实机验证 zh-Hans/en/ja：SkeletonWarlord 标签栏为 `神器 / 消耗品 / 物理披风 / 骷髅督军 / 杂项`（英文 `Artifact / Consumable / Physical Cloaks / Skeleton Warlord / Misc`，日文 `その他`），点击杂项后正确列出 6 个物品，RuinsGolem 保留 `废墟魔像 · 矿石` 独立标签且 misc 仅含 `小碎石 / 萤火虫之腹`，无 page error。

### feat: 新增【地牢商店】页面（哥布林走私者商品表）

- **改动原因**：用户要求把 `InGameMerchant` 解包数据做成类似【地图模块表】的页面——第一层列出各地图（Crypts / Goblin / IceCavern），点进去看该地图哥布林走私者的商品表，每件商品标明价格，跨区域独有的商品标注【地图限定】，页面内用标签切换 N（普通）/ HR（豪客赛）两套货品。
- **变更文件**：`api/src/config.py`、`api/src/db/schema.py`、`api/src/db/importers/merchants.py`（新增）、`api/src/db/importers/__init__.py`、`api/src/db/repositories/merchants.py`（新增）、`api/src/db/repositories/__init__.py`、`api/src/db/__init__.py`、`api/src/merchant_builder.py`（新增）、`api/src/collector.py`、`api/src/index_export.py`、`api/src/locale_builder.py`、`api/tests/test_merchant_builder.py`（新增）、`web/src/types/data.ts`、`web/src/hooks/useDungeonShops.ts`（新增）、`web/src/pages/DungeonShopsPage.tsx`（新增）、`web/src/pages/DungeonShopDetailPage.tsx`（新增）、`web/src/AppInner.tsx`、`web/src/components/NavBar.tsx`、`web/src/pages/HomePage.tsx`、`web/src/i18n/uiLocale.ts`、`web/src/i18n/seoTemplate.mjs`、`web/src/i18n/seoTemplate.d.mts`、`web/scripts/ssg.mjs`、`docs/SESSION_CHANGES.md`。
- **数据来源与结构**：`V2/InGameMerchant/` 下三个子目录构成三层——`InGameMerchant/`（NPC 身份 + 问候语）、`InGameMerchantSchedule/`（每变体挂 12 个 StockBuy）、`InGameMerchantStockBuy/`（实际商品池，含 `ItemId`/`ItemCount`/`ItemRate`权重/`Stock`库存/`RequiredItemId_01`+`RequiredAmount01` 价格）。该目录**只有哥布林走私者**一个商人，6 个变体 = 3 区域 × 2 难度；另有 `V2/Merchant/`（据点炼金术士等）属另一套系统，本次未涉及。
- **关键逻辑/映射关系**：
  1. **解析**（`merchants.py`）：`parse_asset_name()` 用统一正则剥离 `Id_InGameMerchant{Schedule|StockBuy}?` 前缀，把三类资源归一到同一个 `variant_id`（`GoblinSmuggler_Crypts_N`），StockBuy 额外取出 `slot`。物品名经 `_asset_item_name()` 去掉 `Id_Item_` 前缀（`ue_asset_base_name` 会返回带前缀的 asset 名）。
  2. **三张表**：`ingame_merchants`（商人身份）、`ingame_merchant_variants`（变体）、`ingame_merchant_stock`（商品行，主键 `variant_id+slot_index+item_name`）。入库 1 商人 / 6 变体 / 579 行，与源文件逐条一致。
  3. **槽位 8/9 合并**：数据验证发现每个变体的槽位 08 与 09 **内容逐字节相同**（游戏对同一张材料表掷两次），合并为一个显示槽位并按物品名去重，否则会出现 78 项的重复清单。
  4. **地图限定判定**：按**折叠后的物品基础名**跨区域比较（`fold_item_page`），区域独有才标 `map_exclusive`。这样 `Ruby_4001`（某区）与 `Ruby_7001`（另一区）视为同一物品，品质档位差异不误报限定。
  5. **物品链接与翻译**：商店行带品质后缀（`HealingPotion_5001`），而详情页用折叠名（`HealingPotion`），故用 `fold_item_page` 取页面名；翻译来自 `loot_index`（521 条）。**商店专属物品不在掉落索引**（`LuckPotion` 从不出现在 `lootdrops.json`），追加 `Text_DesignData_Item_Item_{page}` 兜底查询，最终全站商店物品 0 个未翻译。
  6. **区域标签**：复用官方 `Text_UI_WB_DungeonSlot_*` 楼层键（Crypts→`TheCrypts_2ndFloor`「地穴」、Goblin→`GoblinCave_1stFloor`「哥布林洞穴」、IceCavern→`IceCavern_1stFloor`「寒冰洞穴」），比模块页的合成标签（如「废墟2层（地穴）」）更贴合商店所在地图。
  7. **默认语言兜底**：`useLocale()` 对 zh-Hans 不加载 locale 字典，因此 `merchant.display` / `merchant.greeting` 由后端直接写入 JSON（与 `region.display` 同款做法），否则中文页会显示英文 ID `GoblinSmuggler` 和空的 `「」`。
  8. **前端**：`useDungeonShops` 提供 `useShopIndex`/`useShopDetail`（按版本缓存）；列表页渲染区域卡片（商品数 + 限定数），详情页用 `useState` 切换 N/HR 并分组渲染槽位，限定商品以粉色边框 + 【地图限定】标注。
  9. **SSG**：`dungeon_shops` 加入 `SINGLE` 列表、`routeDataKey()`、`templateDescription()`（新增 `shops`/`shopRegion` SEO 类型），路由为用户可见的 `/:lang/dungeon_shops/:region`；区域详情在 quick/full 两种模式下都整体注入 `ssrDataMap`。
- **验证**：`python3 -m unittest discover -s tests` 115/115 通过（新增 `test_merchant_builder.py` 20 例：资源名解析 5 例、区域顺序、N/HR 双难度、8/9 槽位合并、价格降序、限定标记与计数、物品链接元数据、品质后缀折叠、`_8001` 神器不折叠、品质档位差异不算限定、商人 display/greeting 解析与兜底、商店专属物品回退 Game.json 键、落盘文件校验）；`api/lint.sh` 通过；`cd web && npm run lint` 0 errors / 20 既有 warnings、Prettier 与 `npx tsc --noEmit` 通过；`python main.py --rebuild-db` 全量重建，导出 3 区域 / 57·46·44 种商品（含 12·7·6 种地图限定）；`npm run build` 退出码 0（3111 页 / 17106 文件，新增 4 个商店路由）；Playwright 实机验证 zh-Hans/en/ja：列表页标题「【地牢商店】哥布林走私者」并显示商人名与问候语，Crypts 详情页显示 `治疗药水 / 绷带与手术包 / 幸运药水 / 邪水 / 十字镐 / 营火工具 / 宝石 / 怪物材料 / 钥匙与开锁器 / 金币 / 油灯笼` 共 11 个分组，普通↔豪客赛切换正常（HR 出现巨魔之血、宝石升为传说档），限定商品带【地图限定】标记，三语言均无原始 token、无 page error。

### feat: 地牢商店展示刷出概率与稀有度，并按设计审查修正

- **改动原因**：用户询问「黄金钥匙是固定价格吗，刷出概率也标一下」「稀有度也标一下，因为有相同名字的东西」（如"治疗药水"有 100 金与 250 金两档），随后要求对新增的列表页/详情页做设计优化。经实机审查发现 6 类问题：① 头部标语「共 57 种商品」与实际渲染的 73 张卡片矛盾；② 概率说明文案在每个槽位重复，全文出现 84 次"概率"；③ 单品槽位显示无意义的"100% 概率"；④ 概率精度在 1/2/3 位小数间跳变；⑤ 宝石区 12 张卡片按 5 列排布导致品质分组中途断裂；⑥ 列表页固定 3 列在 390px 窄屏把卡片压到约 110px。
- **变更文件**：`api/src/merchant_builder.py`、`api/tests/test_merchant_builder.py`、`web/src/types/data.ts`、`web/src/pages/DungeonShopDetailPage.tsx`、`web/src/pages/DungeonShopsPage.tsx`、`web/src/i18n/uiLocale.ts`、`docs/SESSION_CHANGES.md`。
- **黄金钥匙价格结论**：**固定 1000 金**。三个地图 × N/HR 两档均为 1000（Crypts-N 权重 435、Crypts-HR 权重 1305，价格不变）；概率则随难度变化（N 0.435% → HR 1.3%）。
- **概率算法**：`ItemRate` 是槽位内的相对权重，某商品概率 = `rate ÷ 该槽位权重和`。槽位权重和高度规律（槽位 1-6/11/12 = 1000，槽位 7 = 4000，槽位 10 = 100000，槽位 8/9 随区域物品数在 20000/21800/27200 间变化）。**槽位 8/9 是同一张表掷两次**，故合并展示时概率按 `1-(1-p)²` 折叠（如 `rate=1000/27200` 单次 3.676% → 两次 7.218%），`chance_total` 因此约等于 2 而非 1。
- **关键逻辑/映射关系**：
  1. `merchant_builder` 新增 `SUFFIX_RARITY`（1001 粗糙 → 8001 命名神器），由 `fold_item_page` 返回的品质后缀推导 `rarity`；每项同时输出 `slot_total` 与 `chance`。
  2. 每个难度新增 `base_item_count`（折叠品质后的去重数）与 `exclusive_count`；区域层 `item_count` / `total_items` 改为**各难度的最大值**，使列表页与详情页头部数字一致（57→73、46→62、44→60）。
  3. 前端 `ShopItemCard` 新增 `showChance` 参数，单物品槽位（邪水/金币/油灯笼）不再渲染 `100%`。
  4. `formatChance` 统一为 2 位有效数字（`Number(pct.toPrecision(2))`），消除 `99.0%` 与 `0.435%` 并存的不一致。
  5. 概率说明文案改为整页**只出现一次**（位于难度切换下方），并合并单抽/双抽两种规则说明；删除已无用的 `ui.shops.chance_hint_double`（10 语言 × 1 条）。
  6. 宝石槽（slot 7）用 `repeat(auto-fit, minmax(170px, 1fr))`、其余槽位 `minmax(230px, 1fr)`；列表页改 `repeat(auto-fit, minmax(220px, 1fr))`（390px 单列、768px+ 三列）。
  7. 详情页字号整体上调一档（h1 32→34、槽位标题 16→17、物品名与价格 14→15、辅助信息 11→12）。
- **验证**：`python3 -m unittest discover -s tests` 123/123 通过（新增 2 例：区域计数等于详情页实际渲染卡片数、区域计数取各难度最大值）；`api/lint.sh` 通过；`cd web && npm run lint` 0 errors / 20 既有 warnings、Prettier 与 `npx tsc --noEmit` 通过；`python main.py` 重建后列表页 3 区域计数为 73/62/60（含 12/7/6 限定）；`npm run build` 退出码 0（3111 页）；Playwright 实机验证：头部「共 73 种商品」与实际 73 张卡片一致、列表页 Crypts 73 = 详情页 73、说明文案全文仅 1 次、`100%` 已消失、概率统一为 2 位有效数字、390px 单列且卡片满宽、无 page error。

### fix: 地牢商店商品点击改为触发搜索，避免死链

- **改动原因**：用户反馈 `zh-Hans/dungeon_shops/IceCavern` 详情页点击幸运药水不一定能跳转。排查确认 `LuckPotion` **从不出现在掉落表中**（`lootdrops.json` 521 条页面里没有它），而商店商品卡片此前统一 `Link` 到 `/${lang}/lootdrops/${item.page}/`，因此是一枚死链。全站扫描 387 条商品条目、70 个不重复物品，其中仅 `LuckPotion` 缺页面（12 条条目受影响）。
- **变更文件**：`web/src/pages/DungeonShopDetailPage.tsx`、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：`ShopItemCard` 由 `<Link>` 改为 `<div role="button" tabIndex={0}>`，点击与回车/空格均执行 `navigate(location.pathname, { state: { searchQuery: label } })`，复用 NavBar 已有的 `location.state.searchQuery` 机制把物品名灌进顶部搜索框（与商人名、任务目标放大镜同一套通路）。保留键盘可达性（`onKeyDown` 处理 Enter/Space 并 `preventDefault`），并加 `title` 提示。移除不再使用的 `Link` 导入。
- **已知限制**：`LuckPotion` 本身也不在 `search_index` 中，因此搜"幸运药水"仍无结果——用户已确认接受此权衡。若后续要让它可搜，需把商店商品补进 `index_export.build_and_save_indexes()` 的搜索索引。
- **验证**：`npx tsc --noEmit` 通过、`npm run lint` 0 errors / 20 既有 warnings、Prettier 通过；`npm run build` 退出码 0（3111 页）；Playwright 实机验证 IceCavern 详情页：指向 `/lootdrops/LuckPotion` 的链接数 **0**（死链已移除），点击幸运药水后搜索框内容为 `幸运药水`，点击治疗药水后为 `治疗药水`，卡片 `tabindex=0`，无 page error。

### feat: 商店消耗品展示真实效果区间（幸运药水 +100~200 等）

- **改动原因**：用户要求「详情页的幸运药卡片上写上具体幸运区间 比如200-300」。此前卡片只能显示名字，而两档幸运药水**游戏内名称完全相同**（都叫"大型幸运药水"），玩家无法判断差异。数值不在物品 JSON 里，需要新解一条数据链。
- **变更文件**：`api/src/consumable_effects.py`（新增）、`api/src/config.py`、`api/src/merchant_builder.py`、`api/src/collector.py`、`api/tests/test_consumable_effects.py`（新增）、`api/tests/test_merchant_builder.py`、`web/src/types/data.ts`、`web/src/pages/DungeonShopDetailPage.tsx`、`web/src/i18n/uiLocale.ts`、`docs/SESSION_CHANGES.md`。
- **数据链（三段，此前完全未接入管道）**：
  1. `Item/Item/Id_Item_LuckPotion_5001` → `Abilities` 指向 `Id_ItemAbility_LuckPotion_5001`
  2. `V2/Item/ItemAbility/Id_ItemAbility_LuckPotion_5001` 的 `Class` 指向蓝图 `GA_LuckPotion_5001_Consume`
  3. `Item/Utility/Potion/GameplayAbility/GA_LuckPotion_5001_Consume` 的 **`RandomEffectDataArray`** 给出三档权重，每档指向 `Id_ActorStatusEffect_Luck{N}`
  4. `Data/Generated/V2/ActorStatus/StatusEffect/Id_ActorStatusEffect_Luck{N}` 的 **`Luck` 字段**才是真实数值
- **关键坑：资产后缀是缩放 10 倍的简称**。`Id_ActorStatusEffect_Luck10` 里的 `Luck` 值是 **100**，不是 10（`Luck02`=20、`Luck30`=300）。最初误以为「区间均匀随机」，实际是三档**加权抽取**。
- **四档真实数据**：3001 = +20/50/80（45/35/20%，期望 +42.5）；4001 = +50/100/150（25/50/25%，期望 +100）；**5001 = +100/150/200（20/40/40%，期望 +160）**；**6001 = +200/250/300（各 33.3%，期望 +250）**。哥布林走私者卖的是 5001（100 金）与 6001（250 金），6001 保底值 = 5001 中位档，两者区间**完全不重叠**。
- **实现**：`consumable_effects.py` 提供 `build_effect_index()`（解析蓝图权重 + 状态效果数值，算出各档概率）、`resolve_item_effects()`（按 `Id_ItemAbility_{item}` → `Class` 名反查蓝图）。`merchant_builder` 新增 `effect_index` / `item_ability_dir` 参数，为每个商品写入 `effect: {values: {Luck: [min,max]}, rolls: [{effect, rate, chance, Luck}]}`；未命中时为 `null`。`config.py` 新增 `ITEM_ABILITY_DIR`、`ACTOR_STATUS_EFFECT_DIR`、`POTION_ABILITY_DIR`。
- **前端**：`ShopItemCard` 在稀有度后渲染 `幸运 +100~200`（`title` 悬停显示完整分布「随机获得以下效果之一：+100 (20%) / +150 (40%) / +200 (40%)」）；`uiLocale` 新增 `ui.shops.effect.luck|range|hint` 三键 × 10 语言。
- **验证**：`python3 -m unittest discover -s tests` 140/140 通过（新增 `test_consumable_effects.py` 13 例：状态效果数值读取、8 档后缀×10 关系、缺目录返回空、蓝图权重解析、四档区间断言、概率和为 1、6001 三档等概率、物品名经能力资产映射、无效果物品被跳过、源目录存在性；`test_merchant_builder.py` 新增 4 例：区间附加、各档数值与概率、无效果物品为 null、不传索引时字段为空）；`api/lint.sh` 通过；`npm run lint` 0 errors / 20 既有 warnings、Prettier 与 `npx tsc --noEmit` 通过；`python main.py` 重建后 3 个区域内共 2 个物品带 `effect`（5001/6001），无「有 effect 但缺 Luck」的异常；`npm run build` 退出码 0（3111 页）；Playwright 实机验证 zh-Hans/en/ja/zh-Hant：卡片显示 `幸运 +200~300`（传奇 250 金）与 `幸运 +100~200`（史诗 100 金），英文 `Luck +200~300`、日文 `幸運 +200~300`，悬停提示含三档概率，无 page error。

## 2026-10-12

### docs: 同步性能计划与本地化文档计数

- **改动原因**：`b9bb1bf76`（2026-10-10）已把 P2-1 LootdropDetail 优化发布，但 `docs/plans/PERF_PIPELINE_AND_RUNTIME.md` 仍把 P2-1 标为「待处理样本」；`MULTILANG_STATUS.md`、`HARDCODED_I18N.md`、`JA_DETAIL_I18N_BACKLOG.md` 仍写「当前输出使用 172 个 `df5.hardcoded.*` 键」，与最新 locale 产物不符，会误导后续本地化工作量判断。
- **变更文件**：`docs/plans/PERF_PIPELINE_AND_RUNTIME.md`、`docs/plans/MULTILANG_STATUS.md`、`docs/plans/HARDCODED_I18N.md`、`docs/plans/JA_DETAIL_I18N_BACKLOG.md`、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：性能计划 P2-1 改为已完成并引用提交 `b9bb1bf76`、记录引用批量 4 与 memo 化范围、`GemNecklace_5001` 回归方式；头部状态与阶段清单 C2、文档变更记录同步。本地化三份文档改用 2026-10-10 03:14 locale 产物实测：10 个 locale 各 2,426 键、无缺失/空值；`df5.hardcoded.*` 定义 150 个、产物实际引用 135 个、未引用 15 个；`HARDCODED_LOCALE_OVERRIDES` 38 条（36 条进入当前 locale）、自动技术词条 114 个；`HARDCODED_TRANSLATIONS` 由旧 230 改为实测 267 条。历史快照数字保留并标注复核值。
- **验证**：只读统计脚本核对 locale 键数、空值、`df5.hardcoded.*` 定义/引用/未使用、覆盖条目与十语言完整度；`git status` 确认仅改动上述四份计划文档。

### fix: 修正 GoblinSmuggler 翻译映射到官方 NPC 键

- **改动原因**：用户发现游戏本地化中存在 `Text_DesignData_Monster_NPC_GoblinSmuggler: "哥布林走私者"` 官方翻译键，而非之前认为的 Merchant 商人键；GoblinSmuggler 页面未正确显示翻译，需要建立正确的兜底映射。
- **变更文件**：`api/src/config.py`、`api/src/translator.py`、`api/tests/test_hardcoded_i18n.py`、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：
  1. 在 `EXPLICIT_TRANSLATION_KEY_OVERRIDES` 添加 `GoblinSmuggler → Text_DesignData_Monster_NPC_GoblinSmuggler` 官方键映射。
  2. 调整 `NameResolver._resolve_inner()` 逻辑：资产自带 `translation_key` > 显式官方键覆盖 > 别名前缀匹配 > 硬编码回退，确保未来游戏文件补充 `translation_key` 后自动优先使用。
  3. 补充测试用例：`test_name_resolver_prefers_explicit_key_over_hardcoded` 验证 `NameResolver` 在游戏翻译字典中正确查找显式键；`test_verified_aliases_keep_official_game_keys` 和 `test_map_source_aliases_use_official_translation_keys` 加入 GoblinSmuggler 回归断言。
- **验证**：`python3 -m unittest tests.test_hardcoded_i18n` 6/6 通过；`./lint.sh` 通过（ruff + black）。

## 2026-10-10

### fix: 按 CI 锁定 Prettier 修复格式并重新发布

- **改动原因**：远端 `6fd55dde8` 和 `b9bb1bf76` 都在 Web quality checks 的 Prettier 步骤失败；本地旧 `node_modules` 使用 3.9.6，但 Actions 的 `npm ci` 按锁文件安装 3.8.4，因此此前本地通过不能代表 CI 通过。
- **变更文件**：`web/src/components/MapImageRecognitionPanel.tsx`、`web/src/main.tsx`、`docs/DEVELOPMENT_WORKFLOW.md`、`docs/SESSION_CHANGES.md`。保留已有最新 DB，未修改依赖锁文件或业务逻辑。
- **关键逻辑/映射关系**：先执行 `npm ci` 恢复锁定依赖，再用 Prettier 3.8.4 将 RecognitionStatus 联合类型、SSR 数据类型断言改为该版本要求的多行前导 `|` 格式；开发规范增加发布前按锁文件安装依赖及与 Actions Node 20 对照验证的要求，防止 formatter 漂移导致误判。
- **验证**：Node 20.20.0 + 锁定依赖下 `npm test` 通过（lint 0 errors / 20 条既有 warnings、Prettier 3.8.4、TypeScript）；`npm run build` 退出码 0（3,107 routes / 15,193 HTML / 17,057 files）；独立 8083 预览 HTTP 200，Playwright 多语言页面 29/29、截图识别同意弹窗回归通过；`git diff --check` 通过。本地 DB 与 HEAD blob 均为 `a9cce69a23a6941c6f69e6fb301c4fd77066bcb1`。

### perf: 提交本地掉落详情优化并重新发布当前版本

- **改动原因**：用户确认发布当前本地代码及最新 DB，而非仅推送已有提交；先核对 `b2d213009`（2026-10-09 21:09:34 +0800）之后的已提交内容只有部署文档与 DB，本次将此前未提交的前端优化纳入发布。
- **变更文件**：`web/src/pages/LootdropDetailPage.tsx`、`web/tests/i18n.mjs`、`docs/SESSION_CHANGES.md`；发布提交树继续保留 `api/data/darkfindv5.db` 最新快照（47,255,552 bytes）。
- **关键逻辑/映射关系**：引用坐标加载批量从 1 改为 4；地图分组、排序、识别模板和位置统计使用 memoization，相关 hooks 放在 loading return 之前；IntersectionObserver 状态未变化时复用原 Set；有隐藏来源时“显示全部”清空隐藏状态。新增大量引用加载及显隐切换回归。最新 DB 已加入史诗绷带掉落，因此无掉落变体测试从 `Bandage_5001` 改为缺失的 `Bandage_6001`，保留 0% 文案、无位置统计、有效品质链接及无无效品质链接的断言，不改业务输出。
- **验证**：`npm test` 通过（lint 0 errors / 20 条既有 warnings、Prettier、TypeScript）；`npm run build` 退出码 0（3,107 routes、15,193 HTML、17,057 dist files）；8082 预览 HTTP 200；Playwright 首次 28/29（史诗绷带旧数据断言失效），更新测试后 29/29，通过 45 个引用加载及显隐切换；测试文件 Prettier 和 `git diff --check` 通过。DB 的本地及远端 blob 均为 `a9cce69a23a6941c6f69e6fb301c4fd77066bcb1`。
- **发布策略**：按用户确认采用当前工作区代码，不回退到旧版 DB 或丢弃前端改动；仅暂存上述三份源码/文档，使用指定远端 SHA 的 `--force-with-lease` 推送 `main`，不混入未跟踪文件。

### chore: 执行补丁部署并重建数据库快照

- **改动原因**：按用户确认的补丁部署流程同步最新 FMOD Output，删除旧数据库后全量重建，准备将新 DB 随 `main` 推送到远程。
- **变更文件**：`api/data/darkfindv5.db`（远程 DB 提交；本地恢复 `skip-worktree`）；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：
  1. `~/sync_fmod.sh` 把 `/mnt/e/Game/fmod/Output/` 同步到 `~/fmod/Output/`，对应数据管道 `GAME_ROOT` 的输入。
  2. 删除 `api/data/darkfindv5.db` 后运行 `api/main.py`，从同步源全量导入并生成 DB、JSON 和 10 种语言的 locale/search index。
  3. 按 `docs/BUILD_AND_DEPLOY.md` 临时提交更新后的 DB 和本次会话记录；Actions 负责后续 SSG 构建，补丁流程不做本地 `npm run build`。
- **验证**：FMOD rsync 完成（total size 1,688,019,723 bytes）；数据管道退出码 0、总耗时 37.32s，导出 items 72、monsters 152、props 253、lootdrops 521、dungeon_modules 260，10 个 locale；项目 `inspect_database()` 返回 `DB_READY`（source manifest current），DB 大小 47,255,552 bytes。

## 2026-10-09

### ci: 将测试加入发布门禁

- **改动原因**：main 发布流程原先只做静态质量检查，未运行 API 单测或浏览器行为回归，功能错误可能直接发布。
- **变更文件**：`.github/workflows/deploy.yml`、`.github/workflows/deploy-dev.yml`、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：main/dev 在数据管道前运行 `api/tests` 全量 unittest；main 构建后安装 Chromium、启动 preview，并复用 dev 已有的 `test:i18n` Playwright 回归后才部署。
- **验证**：API 58 项 unittest 通过；两个工作流 Prettier 检查通过；当前构建在独立端口 HTTP 200，`BASE_URL=http://127.0.0.1:8081 npm run test:i18n` 27/27 通过；`git diff --check` 通过。

### fix: 修复前端格式检查

- **改动原因**：`npm test` 中的 Prettier 检查因两个既有文件格式不符而失败，会阻断 main/dev 工作流。
- **变更文件**：`web/src/components/MapImageRecognitionPanel.tsx`、`web/src/main.tsx`、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：仅由 Prettier 规范类型联合和类型断言换行，不改变运行逻辑。
- **验证**：`npm test` 通过（ESLint 0 error、20 条 warning）；`npm run build` 成功，Quick SSG 生成 3,091 routes、15,466 HTML、17,302 个 dist 文件；现有 8080 预览 HTTP 200；`git diff --check` 通过。

### perf: 用掉率预加载索引生成实体掉落池行

- **改动原因**：profile 和计时日志确认 `load_drop_rows()` 的 `spawner_entries → lootdrop_groups → lootdrop_rate_items` JOIN/GROUP BY 被 monster、props 分别执行；仅共享查询后仍要 21.09s。`DropRateEngine.preload()` 已把相同关系载入内存，可直接重建相同行集。
- **变更文件**：`api/src/collector.py`、`api/src/drop_rate.py`、`api/src/monster_drops_builder.py`、`api/tests/test_drop_rate.py`、`api/tests/test_monster_drops_builder.py`、`docs/plans/PERF_PIPELINE_AND_RUNTIME.md`、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：
  1. 预加载保留原始 `entity_name → lootdrop_group_id`，结合已有 `group_id → lootdrop_id`、`lootdrop_id → item/luck_grade` 索引，按 `(entity_name, lootdrop_id, item_name)` 去重并取最大 luck grade，与原 SQL GROUP BY 等价；缺少新接口的调用方仍可走 SQL fallback。
  2. collector 只构造一次共用 rows，并传给 monster / props 池构造，避免第二遍关系扫描。
  3. 掉率计算增加 `(ldg_id,item_name,full_grade)` 结果缓存和「是否存在可显示正爆率」短路；显示边界仍与 4 位小数输出一致。
- **验证**：API 全量 67 项 unittest、Ruff、Black 通过；完整 `python main.py` 热 DB 管线 **28.68s**（先前基线 74.12s；低于 40s 目标），167,335 行内存构造耗时 0.150s；151 monster / 249 props 的 `loot_pools` 与稳定产物逐文件无语义差异。日志：`/tmp/darkfindv5-engine-rows-pipeline.log`、`api/logs/pipeline_20261009_125654.log`。未 push。

### fix: SSG 地图模块描述补入实体与坐标数量

- **改动原因**：Quick SSG 为减小客户端首屏注入把模块 `coords` 置为 `null`，但静态 SEO 描述也因此丢掉模块实体/位置事实；客户端 `DungeonModuleDetailPage` 已有这些计数。
- **变更文件**：`web/scripts/ssg.mjs`、`web/tests/i18n.mjs`、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：从模块坐标 JSON 汇总 `entities.length` 和所有 `entity.coords.length`，仅把两个计数写入 `seoFacts`；Quick 模式仍保持 `coords: null`，Full 模式继续注入完整坐标。模块模板描述使用 `seoFacts`，并保留无法读取坐标时的空值 fallback。Playwright 增加中文、英文、日文原始静态 HTML 计数断言。另把 sitemap 构建日志的 URL 数改为从实际生成的 sitemap entries 统计，排除未静态生成的 variant 路由。
- **验证**：`npm run format:check`、`npm run lint`（0 errors，20 条既有 warnings）、`npm run typecheck` 通过；Quick SSG 生成 3,091 routes / 15,466 HTML / 17,302 dist files，10 个 sitemap 各 1,358 URL、合计 13,580；全量 HTML audit 的 title/description/OG/canonical/lang/重复 URL 均 0 错误，根页 title 1 个且 canonical 保持 `/zh-Hans/`；Playwright 27/27 通过；预览 8081 首页、语言页、目标模块页 HTTP 200。未占用/终止被其他 WordPress 服务使用的 8080，未 push。

### perf: Canvas 阈值渲染密集地图点位

- **改动原因**：PiratePrison 模块“显示全部”会一次挂载 812 个点，旧版生成 2,436 个逐点 DOM 节点并触发 59ms Long Task，超过交互预算。
- **变更文件**：`web/src/components/MapPanel.tsx`、`web/tests/i18n.mjs`、`docs/plans/PERF_PIPELINE_AND_RUNTIME.md`、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：`dots.length > 300` 时按既有 `applyTransform` / `computePixel` 映射到单个高 DPI canvas，保留点色、z 标签和 11px 标记尺寸；通过最近点命中恢复实体名悬停提示及 aria 标签。≤300 点仍用原 DOM 路径。
- **验证**：改动前显示耗时 195ms、2,436 节点、59ms Long Task；改后显示耗时 131ms、仅新增 1 个 canvas 节点、该窗口无 >50ms Long Task，脚本/布局/样式耗时约 29.4/1.4/3.8ms。`npm run format:check`、lint（0 errors / 20 条既有 warnings）、`npm run typecheck` 通过；Quick SSG 3,091 routes / 15,466 HTML；Playwright 28/28（含 812 点 Canvas、正确 tooltip 与 ResizeObserver 高 DPI 缩放）；≤300 点详情页仍为 DOM。未 push。

## 2026-09-21

### feat: 实体详情复用掉落芯片，并隐藏活动货币池

- **改动原因**：`MonsterDropSwitch` 只挂在怪物详情；箱子/桶/矿等 props 也有 `lootdrop_group_id`，详情页看不到掉落芯片。活动货币池 `Spawn_EventCurrency` 内容是金币/银币，干扰阅读。
- **变更文件**：`api/src/monster_drops_builder.py`、`api/src/collector.py`、`api/tests/test_monster_drops_builder.py`、`web/src/components/MonsterDropSwitch.tsx`、`web/src/pages/DetailPage.tsx`、`web/src/types/data.ts`、`web/src/i18n/uiLocale.ts`、`docs/REFERENCE_DROP_RATES.md`、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：
  1. `is_event_currency_pool`：`EventCurrency` 池不进 `loot_pools`；前端再滤一次。
  2. `build_loot_pools(..., fold_quality=)`：怪物默认 True，剥 `Common/Elite/Nightmare/Unique`。实体 False，仍对齐导出页：`LivingArmor_Elite` → `LivingArmor`，`Ore_CopperOre_Med` → `CopperOre`。
  3. collector 在 enrich 写 JSON 前给 monsters 和 props 都 `attach_loot_pools`。
  4. `DetailPage`：`page === 'monsters' || page === 'props'` 且有 `loot_pools` 时渲染同一组件。
  5. 补常见池 i18n：Trinkets / Utility / Barrels / Treasure。
  6. 单物品且子类 `Utility_Consumable` 的池并成 `kind=consumable`（消耗品），与掉落表消耗品分组一致。
  7. `MonsterDropSwitch` 页签贴在内容框上沿，选中页签去掉底边框盖住面板上沿。
- **验证**：`python3 -m unittest tests.test_monster_drops_builder` 通过；`./lint.sh`、`npx tsc --noEmit` 通过。管道后 `WoodenBarrel`/`GoldChest`/`LivingArmor` 有芯片无活动货币；`OrnateChestLarge` 钥匙/宝石单物品池并入「消耗品」。页签贴在内容框上沿。

## 2026-09-19

### chore: 推送 main 并更新远程数据库快照

- **改动原因**：本地 `main` 有未推送的怪物列表分组/种族标签提交，且重建后的 `darkfindv5.db` 新于远程快照；按文档把含最新 DB 的 `main` 推到 `origin/main`。
- **变更文件**：`api/data/darkfindv5.db`（远程临时跟踪）；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：按 `docs/BUILD_AND_DEPLOY.md` 强制加入 DB、推送 `origin/main`，随后本地 `reset HEAD~1` 并恢复 `skip-worktree`。
- **验证**：sqlite-debug 可读。本次不跑本地 SSG；前端由 Actions 在拿到新 DB 后构建。本地 Vite 8080/8090 已关闭。

### feat: 怪物列表种族改卡片标签，组内仍按种族排序

- **改动原因**：DemonOverseer 同时有 `Type.Character.Demon.Demon` 与 `Type.Character.Humanoid.Human`，不能再按单一种族独占分组。列表仍按 Boss / 小Boss / 一般 / 杂项，去掉种族小标题；同种族仍排在一起；全部叶子种族写在卡片名下方，字更小、颜色更淡。
- **变更文件**：`api/src/db/_helpers.py`、`api/src/db/schema.py`、`api/src/db/importers/monsters.py`、`api/src/db/repositories/monsters.py`、`api/src/entity_export.py`、`api/src/index_export.py`、`api/src/db_freshness.py`、`api/tests/test_monster_class.py`、`web/src/pages/ListPage.tsx`、`docs/REFERENCE_DATA_PIPELINE.md`、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：
  1. `race` 仍取最长 `Type.Character.*` 后缀，只作组内排序键。
  2. `races` 取叶子后缀（被更具体子标签覆盖的父标签去掉）：DemonOverseer → `Demon`、`Human`。写入 `monster_entities.races`，导出 `monsters.json` / search_index。
  3. 变体合并时 `races` 只取最高 Class 那条，避免 Banshee Boss 卡片带上 FogMissile 变体的 `Undead`。
  4. 列表卡片：`races` 用 `ui.list.monster_race.*`，12px、`tokens.muted`，中日文用顿号。
  5. `GENERATOR_VERSION` 升到 `db-lifecycle-v6-monster-race-tags`。
- **验证**：`python3 -m unittest tests.test_monster_class` 5 项通过；`./lint.sh`、`npx tsc --noEmit`、prettier 通过；eslint 仅既有 `ssrData` warning。管道 `--rebuild-db` TOTAL 65.20s，再导出 50.21s。DemonOverseer `boss` + `races: [Demon, Human]`；Banshee `[Ghost]`；CaveTroll `[Troll, Beast]`。8090 `/zh-Hans/monsters/` HTTP 200。本次不跑全站 SSG，不 push。

### feat: 怪物列表一级 Class、二级种族嵌套，无攻击性归入杂项

- **改动原因**：鲑鱼、快递员等无攻击性实体与一般怪物共用 `ClassType.Normal`。列表需要先按 Boss / 小Boss / 一般 / 杂项，再按 `CharacterTypes` 种族拆开，避免一般怪物过长、Boss 仍一眼可见。`CharacterTypes` 是种族不是敌对性，不能单独用来分杂项。
- **变更文件**：`api/src/db/_helpers.py`、`api/src/db/schema.py`、`api/src/db/importers/monsters.py`、`api/src/db/repositories/monsters.py`、`api/src/entity_export.py`、`api/src/index_export.py`、`api/src/db_freshness.py`、`api/tests/test_monster_class.py`、`web/src/pages/ListPage.tsx`、`web/src/i18n/uiLocale.ts`、`docs/REFERENCE_DATA_PIPELINE.md`、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：
  1. 杂项：`Id.NPC.*`，或 Normal 且技能全是死亡/逃跑/闲置（无 Attack/Melee/Bite 等战斗词）。空技能不算被动（训练假人靠 NPC 标签）。LootGoblin 的 Surprised/Provocation/GoldDrop 不算被动。
  2. 种族：`CharacterTypes` 里最长的 `Type.Character.*` 后缀（`Undead.Ghost` → `Ghost`）。写入 `monster_entities.race`，导出 `monsters.json` / search_index 的 `race`。
  3. 列表：一级 `boss/miniboss/normal/misc`，二级按 `race`；未知种族走 `ui.list.item_group_unknown`。
  4. `GENERATOR_VERSION` 升到 `db-lifecycle-v5-monster-race-nest`。
- **验证**：`python3 -m unittest tests.test_monster_class` 5 项通过；`./lint.sh`、`npx tsc --noEmit`、prettier 通过；eslint 仅既有 `ssrData` warning。管道 `--rebuild-db` TOTAL 63.34s。列表 151：Boss 13 / 小Boss 23 / 一般 101 / 杂项 14。鲑鱼 `misc+Aquatic`，快递员 `misc+Human`，LootGoblin `normal+Goblin`，Banshee `boss+Ghost`。本次不跑全站 SSG，不 push。

### feat: 怪物列表按 Boss / 小Boss / 一般怪物分组

- **改动原因**：`/zh-Hans/monsters/` 原先平铺卡片。按 `/zh-Hans/props/` 的全宽分组标题 + 三列卡片样式，用游戏 `DCMonsterDataAsset.ClassType` 分成 Boss、小Boss、一般怪物。
- **变更文件**：`api/src/db/_helpers.py`、`api/src/db/schema.py`、`api/src/db/importers/monsters.py`、`api/src/db/repositories/monsters.py`、`api/src/entity_export.py`、`api/src/index_export.py`、`api/src/db_freshness.py`、`api/tests/test_monster_class.py`、`web/src/pages/ListPage.tsx`、`web/src/i18n/uiLocale.ts`、`docs/REFERENCE_DATA_PIPELINE.md`、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：
  1. `ClassType.TagName`：`Type.Monster.Class.Boss` → `boss`，`SubBoss` → `miniboss`，其余/缺失 → `normal`。
  2. `monster_entities.class_type`；质量变体合并时保留最高级（Boss > SubBoss > Normal）。
  3. `export_monsters` 把 `type` 写入 `monsters.json`，`search_index` 原样拷贝；列表 CSR 读 search_index。
  4. `GENERATOR_VERSION` 升到 `db-lifecycle-v3-monster-class-type`，强制重建导入。
- **验证**：`python3 -m unittest tests.test_monster_class` 3 项通过；`./lint.sh`、`npx tsc --noEmit`、目标文件 prettier 通过；eslint 仅既有 `ssrData` warning。管道 `--rebuild-db` TOTAL 62.88s。列表 151：Boss 13 / 小Boss 23 / 一般 115。Playwright 8090：`👑 Boss（13）`、`⚔️ 小Boss（23）`、`💀 一般怪物（115）`。本次不跑全站 SSG，不 push。

### fix: 怪物掉落芯片过滤实际爆率为 0 的条目

- **改动原因**：`/zh-Hans/monsters/Banshee/` 掉落芯片列出了神器（如 `CrystalBall_8001`），但打开对应 lootdrop 页没有 Banshee 来源按钮。芯片原先只反映掉落表成员关系；物品页来源按钮用 `get_group_drop_rates`，任一模式均为 0 则隐藏。Banshee 只在 Ruins HR_D，实际 grade 的 luck-8 权重为 0。
- **变更文件**：`api/src/monster_drops_builder.py`、`api/src/collector.py`、`api/tests/test_monster_drops_builder.py`、`docs/REFERENCE_DROP_RATES.md`、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：
  1. `monster_map_groups` 从怪物坐标 `map` 经 `drop_engine.map_base_to_group` 取实际地图组。
  2. `item_has_positive_rate` 与物品页一致：任一地图组任一模式 `> 0` 才保留；无地图组时不过滤。
  3. `build_loot_pools` 在 `fold_item_page` 之前按 `(item_name, canonical)` 缓存过滤，避免 `_8001` 被丢掉后把同页 `_5001` 一并折叠掉。
  4. `attach_loot_pools` 传入 `drop_engine`。
- **验证**：`python3 -m unittest tests.test_monster_drops_builder` 10 项通过；`./lint.sh` 通过。管道 TOTAL 52.61s。Banshee 无神器 tab、无 `_8001`；`CrystalBall_8001.json` 的 `monsters` 不含 Banshee。SkeletonMage / LootGoblin 同样无神器 tab 与 `_8001` 残留。本次不跑全站 SSG，不 push。

## 2026-09-18

### chore: 推送 main 并更新远程数据库快照

- **改动原因**：本地 `main` 有未推送的怪物掉落池芯片提交，且本地 `darkfindv5.db`（管道重建后）新于远程快照；按文档把含最新 DB 的 `main` 推到 `origin/main`。
- **变更文件**：`api/data/darkfindv5.db`（远程临时跟踪）；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：先 rebase 到远程 `chore: update DB`（`7723617b3`），再按 `docs/BUILD_AND_DEPLOY.md` 强制加入 DB、推送 `origin/main`，随后本地 `reset HEAD~1` 并恢复 `skip-worktree`。远程 DB 约 44 MiB、37 张表。
- **验证**：rebase 无冲突；SQLite 可读且表数量为 37。本次不跑本地 SSG；前端由 Actions 在拿到新 DB 后构建。

### feat: 怪物详情按掉落池显示掉落物芯片

- **改动原因**：怪物详情页只有坐标和自身聚合爆率，无法从 `/zh-Hans/monsters/LootGoblin/` 直接跳到掉落表。需要类似稀有度切换的芯片，按掉落池分页、按品质着色排序，点击进入对应 lootdrop 页。
- **变更文件**：`api/src/monster_drops_builder.py`、`api/src/collector.py`、`api/tests/test_monster_drops_builder.py`、`web/src/components/MonsterDropSwitch.tsx`、`web/src/pages/DetailPage.tsx`、`web/src/types/data.ts`、`web/src/i18n/uiLocale.ts`、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：
  1. `spawner_entries.entity_name` 剥品质后缀后对齐 canonical 怪物页；经 `lootdrop_groups` → `lootdrop_rate_items` 聚合物品。
  2. 新键 `loot_pools` 写入 `monsters/{name}.json`，不改 `group_drop_info`。tab 顺序：任务（合并 `Quest*`/`QuestSpecial*`，默认）→ 神器（全池 `*_8001` 合成）→ 其余每个 `lootdrop_id`。神器只出现在神器 tab。
  3. 物品名折叠与掉落页一致：非 `_8001` 去掉 `_\d{4}`；`GoldCoinPouch` → `/lootdrops/GoldCoinPouch/`，`CrystalBall_8001` 独立页。
  4. 前端 `MonsterDropSwitch` 挂在 `DetailPage` 免责声明之后；池标签走 `ui.monster_drops.*`（十语言）。
- **验证**：`python3 -m unittest tests.test_monster_drops_builder` 7 项通过；`./lint.sh`、`npx tsc --noEmit`、目标文件 prettier/eslint 通过。管道 TOTAL 50.69s，`[VALIDATE] all module images OK`。LootGoblin：任务 GoblinEars、金币容器 3、赃物 14、无神器 tab。SkeletonMage：神器 5 件且 `Drop_SkeletonMage` 不含 `_8001`。Playwright（8090）：默认任务「哥布林耳朵」；切金币容器点「小型金币袋」→ `/zh-Hans/lootdrops/GoldCoinPouch/`；SkeletonMage 神器「茨戈奇之眼」→ `/zh-Hans/lootdrops/CrystalBall_8001/`。本次不跑全站 SSG，不 push。

### chore: 更新部署（修复 FModel GameSpawner 后重建 DB 并推送）

- **改动原因**：上一轮更新部署用的地图 JSON 缺 `BP_GameSpawner_C.Properties`（FModel unversioned 反序列化失败），坐标无法绑定 `Id_Spawner_*`，物品/实体/怪物表数量崩掉。用户重新导出后再跑独立「更新部署」。
- **变更文件**：`docs/SESSION_CHANGES.md`；`api/data/darkfindv5.db`（远程临时跟踪）。
- **关键逻辑/映射关系**：
  1. `~/sync_fmod.sh` 增量同步；Chapel `Crypt_Chapel_HR_D.json` 363KB→506KB，64/64 GameSpawner 恢复 `SpawnerDataAsset`/`PreviewData`。
  2. `Chapel01_Spawner_SkeletonArcher_11` → `Id_Spawner_New_Monster_SkeletonMage`；`BP_WoodenBarrel_C_*` → `WoodenBarrel01`。
  3. 删除 `api/data/darkfindv5.db` 后 `python main.py` 全量重建。现有 `extract_spawners` 无需改解析逻辑。
- **验证**：管道 TOTAL 39.60s，`[VALIDATE] all module images OK`；DB 约 44 MiB、37 张表、59473 spawners。index：物品 96、实体 249、怪物 151、掉落 493。HoneyblissPear：木桶 678、矮人木桶 `coord_count` 130、木桶(随机) 12。Chapel 14×WoodenBarrel01 + 1×SkeletonMage。本次不跑本地 SSG。

### chore: 更新部署（同步 FMOD、全量重建 DB 并推送）

- **改动原因**：执行独立于完整构建的「更新部署」：同步最新游戏解包、删库全量重建 SQLite，并把含新 DB 的 `main` 推到 `origin/main`。同时把该流程写入主文档，避免再误走完整构建/仅前端构建。
- **变更文件**：`docs/BUILD_AND_DEPLOY.md`、`AGENTS.md`、`docs/SESSION_CHANGES.md`；`api/data/darkfindv5.db`（远程临时跟踪）。
- **关键逻辑/映射关系**：
  1. `~/sync_fmod.sh`：`rsync -avu /mnt/e/Game/fmod/Output/ ~/fmod/Output/`，约 2.08 GB，含 2026-09-18 FModel 日志。
  2. 删除 `api/data/darkfindv5.db` 后 `python main.py` 全量重建。
  3. 推送前将「更新部署」写入 `docs/BUILD_AND_DEPLOY.md`，并在 `AGENTS.md` 查阅表增加对应入口。
  4. 本地 `main` 已 rebase 到远程 `chore: update DB`，其上还有未推送的 GA4 gtag 修复。
- **验证**：管道 TOTAL 44.02s，`[VALIDATE] all module images OK`；新 DB 约 38 MiB、37 张表，sqlite-debug 可读。本次不跑本地 SSG；前端由 Actions 在拿到新 DB 后构建。

## 2026-09-12

### fix: 修正 gtag stub，使 GA4 能发出 collect

- **改动原因**：线上 `https://dnd9.icetar.com/zh-Hans/` 已加载 `gtag/js?id=G-0SHM5GPXYN` 且 dataLayer 有 `js`/`config`，但实时报表无用户。根因是 Footer stub 用 rest 参数 `push(args)`，把真正的 Array 推进 dataLayer；官方 snippet 必须 `push(arguments)`。GA4 只处理 Arguments 对象，Array 形态的 `config` 被静默丢弃，因此不发 `/g/collect`。
- **变更文件**：`web/src/components/Footer.tsx`、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：`gtag` stub 改回无 rest 参数、`dataLayer.push(arguments)`；对该行关闭 `prefer-rest-params`。测量 ID 仍为 `G-0SHM5GPXYN`。
- **验证**：`npx tsc --noEmit`、`eslint src/components/Footer.tsx`、`prettier --check` 通过。线上实测 dataLayer 前两条为 `Array`（`callee` 为 undefined），对照官方 stub 为 Arguments 对象。本次未跑全站 SSG（仅 stub 三行）。部署后需再看 GA4 实时。

## 2026-09-07

### chore: 推送 main 并更新远程数据库快照

- **改动原因**：本地 `main` 相对 `origin/main` 有 3 个未推送提交（共享生成组修复、页尾统计脚本、文档归档），且本地 `darkfindv5.db` 新于远程快照。
- **变更文件**：`api/data/darkfindv5.db`（远程临时跟踪）；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：先 rebase 到远程 `chore: update DB`，再按 `docs/BUILD_AND_DEPLOY.md` 强制加入 DB、推送 `origin/main`，随后本地 `reset HEAD~1` 并恢复 `skip-worktree`。远程 DB 为 43,294,720 字节、37 张表。
- **验证**：rebase 无冲突；SQLite 可读且表数量为 37。

### docs: 归档历史修复与计划文档

- **改动原因**：活跃 `docs/` 中堆积大量已完成修复记录、废弃方案和旧计划，索引与交叉引用难以维护；同时 `SESSION_CHANGES.md` 仍包含 2026-08 及更早的完整历史，当前会话文件过长。
- **变更文件**：删除 `agent.md`（规范源已是 `AGENTS.md`）；将历史文档移至 `docs/archive/{fixes,plans,investigations}/`；更新 `docs/AGENT_REFERENCE.md`、`docs/PWA_ROADMAP.md`、`docs/BLINDFALL_PIT_PROBABILITY_RECORD.md`、`docs/BLINDFALL_PIT_PROBABILITY_RECORD_EN.md`、`docs/plans/HARDCODED_I18N.md`、`docs/plans/PERF_PIPELINE_AND_RUNTIME.md` 中的路径；将 2026-08-17 及更早的会话记录前置写入 `docs/SESSION_CHANGES_ARCHIVE.md`。
- **关键逻辑/映射关系**：活跃文档索引只保留当前计划与参考；历史修复/计划通过 `docs/archive/` 保留可检索原文；会话日志当前文件仅保留 2026-09 记录。
- **验证**：已删除文档均能在 `docs/archive/` 对应文件名找到（含中文文件名计划文档）；`git diff --check` 通过。本次仅文档搬迁，不改生产代码。

### feat: 将全站统计脚本集中到页尾

- **改动原因**：统一由所有路由共用的 `Footer` 管理 Google Analytics 和 Cloudflare Web Analytics，避免模板与组件双重加载；Bing 统计因未提供 Clarity/验证 ID，本次不接入。
- **变更文件**：`web/src/components/Footer.tsx`、`web/index.html`、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：Footer 客户端 `useEffect` 以固定 DOM ID 为 Google gtag (`G-0SHM5GPXYN`) 与 Cloudflare beacon 注入异步脚本；`window.gtagInitialized` 防止 StrictMode 或重复挂载重复执行 Google 配置；`index.html` 移除旧 Cloudflare head 脚本，确保每次页面加载各统计脚本只存在一个。
- **验证**：`npx tsc --noEmit` 通过；ESLint 无 error（保留既有 warning）；`npm run build` 成功生成 3,089 路由和 17,278 个文件；生产预览首页及 `/en/monsters/DeathSkull/` 均 HTTP 200；Playwright 确认两个统计 script 各一个、Footer 存在且 head 无旧 Cloudflare script。`npm run format:check` 仅剩 `MapImageRecognitionPanel.tsx` 与 `main.tsx` 两个既有格式问题；浏览器仅报已知的 localhost Cloudflare Insights CORS 噪声。

## 2026-09-04

### fix: 修复生成组候选池显示与概率折算

- **改动原因**：`Firedeep_StonepillarHall_D.json` 中的 BlazeToad 与 FlameBoar 通过缺少显式 `RootComponent` 的 `BP_GameSpawnerGroup_C_3` 共享生成组，旧解析无法建立 `group_parent`，导致页面不显示“2种选1”；同时多物理位置的具名候选池被错误显示为“点选”。
- **变更文件**：`api/src/db/importers/spawner_coordinates.py`、`api/tests/test_spawner_coordinates.py`、`web/src/pages/DetailPage.tsx`、`web/src/pages/LootdropDetailPage.tsx`、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：
  1. 当生成组 actor 没有 `Properties.RootComponent` 时，通过 `DefaultSceneRoot.Outer.ObjectName` 回填根索引；继续识别 `BP_SubGroup_C` 父级并沿 AttachParent 链累计坐标与旋转。
  2. 共享 `group_parent` 的 BlazeToad/FlameBoar 聚合为 `variant_count=2` 和 `variant_names` 候选池，复用 Wraith 已有的具名候选池显示分支。
  3. 具名候选池统一显示候选名称、`2种选1`，多物理点追加 `(2点)`；当前详情实体按 `translation_key` 置于候选列表第一位。
  4. 现有 `variant_count` 概率折算保持按候选种类数均分，本例每个候选关联概率为 50%。
- **验证**：删除旧 DB 后全量重建成功；API 38 项单测、后端 lint、前端 TypeScript 检查、目标文件 Prettier 和 `git diff --check` 通过；SSG 成功生成 3,089 个页面；本地预览中 BlazeToad 与 SearingSlime 均 HTTP 200，并显示 `(烈焰蛤蟆、烈焰野猪2种选1) (2点)`。

## 2026-09-03

### chore: 记录补丁部署流程

- **改动原因**：记录标准化的补丁部署流程，以便未来重复使用。流程包括：同步FMOD数据、删除本地数据库、运行数据管道生成新数据库、推送包含新数据库的main分支到远程。
- **变更文件**：`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：
  1. 运行~目录下的同步脚本：`~/sync_fmod.sh`（同步FMOD Output文件夹到项目所需的游戏数据）
  2. 删除项目的db文件：`rm -f api/data/darkfindv5.db`（移除旧数据库以确保全量重建）
  3. 运行项目的数据管道生成新的db文件：`cd api && python main.py`（从游戏JSON数据重新生成完整的SQLite数据库和前端JSON数据）
  4. 推送main分支包含新的db文件到远程：按照`docs/BUILD_AND_DEPLOY.md`中的推送流程，使用git update-index临时跟踪数据库文件，提交并推送到origin/main，然后恢复本地skip-worktree状态
- **验证**：此流程已记录供未来使用。实际执行时需要确保：
  - FMOD同步脚本有权限访问源目录和目标目录
  - 数据管道能够成功读取同步的游戏数据并生成完整的数据库
  - 生成的数据库通过has_usable_database验证
  - 推送过程中正确处理.gitignore中的数据库文件

## 2026-09-03

### feat: 部署环境无游戏源时保留数据库数据

- **改动原因**：`main` 部署的 Actions 工作区没有游戏解包目录，但 collector 将源数据可用性硬编码为真，导致导入器清空已提交 DB 后导出空 JSON，站点无数据。
- **变更文件**：`api/src/collector.py`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：仅在 `GAME_ROOT` 存在时执行解包 JSON → DB 的导入链；Actions 无游戏源时直接以已跟踪的 `api/data/darkfindv5.db` 导出 `data/json`，本地有游戏源时维持原有导入行为。
- **验证**：`python3 -m py_compile api/src/collector.py`、运行时 I/O 守卫、Prettier、TypeScript 与 `git diff --check` 通过；本地未安装 `pytest`，守卫测试以标准 Python 直接执行。

## 2026-09-03

### chore: 同步 main 数据库快照

- **改动原因**：按请求将本地已更新的运行时 SQLite 数据库快照提交并推送至 `main`。
- **变更文件**：`api/data/darkfindv5.db`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：远端 `main` 追踪与本地一致的 `darkfindv5.db` 二进制快照；该库保留实体、生成点、掉落率和十语言翻译等 36 张数据表，前端与构建管道继续从该 DB 读取数据。
- **验证**：SQLite 表结构可读取，确认包含 36 张表。

### feat: 掉落详情页来源筛选写入可分享路由参数 `?sources=`

- **改动原因**：用户要求 `zh-Hans/lootdrops/HeaterShield_8001/` 等掉落详情页的怪物/来源选中状态「提供参数路由」，例如只显示「洞穴巨魔」时更新 URL，别人打开链接即可看到同样的筛选结果。
- **变更文件**：`web/src/pages/LootdropDetailPage.tsx`、`web/src/components/VariantSwitch.tsx`、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：
  1. **参数格式**：URL 查询参数 `?sources=`，值为仍处于显示状态的来源 id（`source_id ?? name`，如 `CaveTroll`、`Lich`、`SuperHoard01_9`），逗号分隔；`?sources=`（空值）表示全部隐藏；无该参数表示沿用原有阈值默认可见性（不变）。
  2. **点击即写 URL**：`toggle`、「显示全部 / 隐藏全部」按钮在更新 `hidden` 的同一步调用 `updateSourcesParam()`，用 `setSearchParams(..., { replace: true })` 写回，避免每次点选都堆积历史记录；全部可见时删除参数，URL 回到干净状态。
  3. **打开即还原**：`useSearchParams()` 读取 `sources`，`hiddenForSources()` 把未列出的来源加入 `hidden`；效果只在挂载后/参数变化时应用，首帧仍用阈值默认值，保证与 SSG 静态 HTML 一致（无水合差异）；`skipSelectionApplyRef` 用于跳过自身写 URL 的回声。
  4. **容错**：来源匹配同时接受 `source_id`、`name` 与 `translation`（中文翻译也可手写）；未知 id 不报错，表现为该来源隐藏。
  5. **阈值联动**：`threshold` 变化（调试面板）在存在显式 `?sources=` 时不再覆盖选择。
  6. **变体切换**：`VariantSwitch` 新增可选 `sources` 属性，切品质（1001–7001 等）时把当前选择带进新 URL，避免筛选丢失。
- **验证**：`npm run check`（eslint 0 error / 20 既有 warning、Prettier、`tsc --noEmit`）通过；`npm run build` 生成 3125 页、dist 17247 文件；8081 `vite preview` HTTP 200；Playwright 实测 `/zh-Hans/lootdrops/HeaterShield_8001/` 默认 H1 显示「洞穴巨魔、巫妖、熔岩飞龙、超级宝藏堆 (+1)」，点「隐藏全部」再点「洞穴巨魔」后 URL 变为 `?sources=CaveTroll`，H1 只剩「洞穴巨魔 (+4)」且地图区仅渲染 `哥布林小镇 B` 1 个位置点；新开页面加载该分享 URL 得到同样的按钮透明度（熔岩飞龙/巫妖/鬼灵骑士 0.3）与 H1，无 pageerror / 无水合报错；`?sources=` 空值链接打开后 5 个来源全部隐藏；无参数与未知 id 均不破坏原有默认展示。
