# 多语言 (i18n) 重构计划

> 创建日期: 2026-07-24
> 版本: v0.10 (统一语言前缀路由, zh-Hans 也使用 /zh-Hans/ 前缀)
> 状态: 路径重构已完成验证; SSG 待重新构建测试

---

## 1. 背景与目标

### 1.1 现状

- 后端 DB 已有 **10 语言**翻译表: `translations_de` / `translations_en` / ... / `translations_zh_Hant` + `translations`(zh-Hans)。
- 每个实体详情 JSON (items/monsters/props/lootdrops/modules/npcs) 同时持有:
  - `translation` —— 中文真值 (SSG 默认渲染用)
  - `translation_EN` —— 后端按英文本地化提取的英文名
- 实体 JSON **缺少 `translation_key` 字段**，SSG 无法按语言查字典生成 `<title>`。
- 运行时 JSON 中 **唯一中文翻译字符串 = 1608 个** (grep 去重)。
- 前端 UI 硬编码中文 ~329 行 (页面标题、提示、Disclaimer、NavBar tab 等)。

### 1.2 目标

1. **语言路由**: 访问 `/en/lootdrops/HeaterShield_8001/` 直接展示英文页面，URL 自动决定语言。
2. **SSG 预生成多语言标题**: 每种语言的 SSG 页面 `<title>` 直接写入对应语言翻译，SEO 友好，搜索引擎收录各语言版本。
3. **复用既有 `translation_key`** 作为 i18n 主键，DB `translations_{lang}` 表天然对齐 10 种语言。
4. **前端加载对应语言字典**: 路由语言前缀 → 自动 fetch 版本化 `/data/{short}/json/locale/{lang}.json` → i18n 切换。
5. **PWA 缓存**: locale 字典纳入 Service Worker，语言切换瞬间加载。
6. **清理冗余字段**（次优先级）: 移除 `translation_EN` / `resolver_en`，详情 JSON 减 ~1.5 MB。

---

## 2. 关键设计决策

### 2.1 翻译键策略

| 实体类型 | i18n Key | 来源 |
|---|---|---|
| item/monster/props/lootdrop/module/quest_npc/explore/emote/action_skin | `translation_key` (如 `Text_DesignData_Item_Item_HeaterShield`) | DB `translation_key` 列,与 `Game.json` key 1:1 |
| UI 通用文案 (NavBar tab, Disclaimer, "未分组", "加载中" 等) | `ui.<feature>.<key>` (如 `ui.nav.items`, `ui.disclaimer`) | 单独 `web/src/i18n/locales/{lang}.json` 维护 |

> **理由**: `translation_key` 已覆盖所有实体类型 + 已在 DB / JSON 中,无需再造键体系。UI 文案量极小 (~15-30 条),单独字典更易维护。

### 2.2 字典文件结构

```
data/json/locale/
├── zh-Hans.json     # 实体字典 + UI 文案合并,键=translation_key|ui.*
├── en.json          # 同上
├── de.json
├── es.json
├── fr.json
├── ja.json
├── ko.json
├── pt-BR.json
├── ru.json
└── zh-Hant.json
```

- UI 文案 (`ui.*`) 合并到各语言的 locale JSON 中，不分文件，减少 fetch 次数。
- 所有语言字典**键集合一致**,缺失值前端自动回退: 先查 locale dict → zh 真值 → name → 空。
- 总条目 ≈ 1608 (实体) + 30 (UI) = ~1640 key / 语言,文件 ~200 KB, GZip 后 ~50 KB。

### 2.3 路由与 URL 架构

#### 2.3.1 统一语言前缀路由 (v0.10)

**所有语言（含 zh-Hans）统一使用 `/:lang/...` 前缀路由**，不再有非前缀和前缀两套路由树：

```
/                                     → zh-Hans 首页 (唯一非前缀路由)
/zh-Hans/                             → 简体中文首页
/zh-Hans/lootdrops/HeaterShield_8001/ → 简体中文详情
/en/lootdrops/HeaterShield_8001/      → English
/ja/items/Ale/                        → 日本語
/ko/monsters/Mimic_Large_Flat/        → 한국어
/zh-Hant/props/TreasureChest/         → 繁體中文
```

- **所有路由统一为 `/:lang/...` 模式**，消除两套路由树导致的参数缺失 bug。
- **`/` 根路径** 直接展示 zh-Hans 首页，LanguageProvider 自动推断默认语言。
- **旧路径自动重定向**: `LegacyRedirect` 组件 (`AppInner.tsx`) 将 `/lootdrops`、`/items/Torch` 等非前缀路径 302 跳转到 `/zh-Hans/...`。
- `withLangPrefix` 始终添加语言前缀（含 zh-Hans），不再为默认语言去前缀。
- 语言切换通过 `window.location.href` 整页导航。
- NavBar `visiblePath` 为当前路径，面包屑基于 `stripLangPrefix` 计算。

**变更文件**:
- `web/src/i18n/LanguageContext.tsx` — `withLangPrefix` 移除 `DEFAULT_LANG` 去前缀逻辑
- `web/src/AppInner.tsx` — 仅保留 `/:lang/...` 路由树 + `<Route path="*">` LegacyRedirect
- `web/scripts/ssg.mjs` — 默认语言也生成 `/zh-Hans/` 路径; 本地化循环剥离源路径前缀
- `web/src/pages/ListPage.tsx` — `useParams<{ page: string }>()` 从 `/:lang/:page` 获取 page

#### 2.3.2 支持的语言范围

| 语言 | 代码 | 路由前缀 |
|---|---|---|
| 简体中文 (默认) | zh-Hans | `/zh-Hans/` |
| English | en | `/en/` |
| Deutsch | de | `/de/` |
| Español | es | `/es/` |
| Français | fr | `/fr/` |
| 日本語 | ja | `/ja/` |
| 한국어 | ko | `/ko/` |
| Português (BR) | pt-BR | `/pt-BR/` |
| Русский | ru | `/ru/` |
| 繁體中文 | zh-Hant | `/zh-Hant/` |

> **v0.10**: zh-Hans 现在也使用 `/zh-Hans/` 前缀路径，与其他 9 种语言统一。旧外链通过 `LegacyRedirect` 组件（`AppInner.tsx` `*` catch-all）自动跳转到 `/zh-Hans/...`。`/` 根路径仍然直接展示 zh-Hans 首页。SSG 总页面数 = 3,096 × 10 + 1(root) = ~30,961。

### 2.4 SSG / SEO 策略 (轻量方案)

**核心思路: SSR 只跑一次(中文全量)，非中文页面通过文本后处理生成，不做二次 React 渲染。**

| 阶段 | 内容 |
|---|---|
| **zh-Hans SSG** | 现有全量渲染流程不变，`dist/*.html` 含完整 SSR 数据和中文 `<title>` |
| **`/{lang}/` SSG** | 读取中文 HTML，**不做 `renderToString`**，文本替换 `<title>` + `__SSR_DATA__` 注入 `lang`; 写到 `dist/{lang}/.../index.html` |
| **路由** | `/{lang}/items/Ale/` → 提供的 HTML 中 `<title>` 已为对应语言 |
| **标题** | 后处理阶段用 `localeDict[entity.translation_key]` 替换 `<title>` 内容 |
| **hreflang** | 后处理阶段在 `<head>` 注入 9 条 `<link rel="alternate" hreflang="..." href="...">` |
| **sitemap** | 每条 URL 出 10 个语言版本，标注 hreflang |
| **Hydration** | SSR/CSR 共用同一套中文 body DOM，hydration 天然一致；客户端检测 `__SSR_DATA__.lang` 后加载 locale dict 切换 UI 文字 |
| **回退** | `localeDict[translation_key]` 未命中 → 显示 `entity.translation` (中文真值) |

> **关键**: 9 种非中文页面 = 中文 HTML + 文本替换，**不需要额外的 React 渲染**。构建时间几乎不变，dist 增量仅为 HTML 副本开销 (每语言 ~62 MB，9 语言共 ~560 MB)。

---

## 3. 后端改造 (API / Collector)

### 3.1 新增/变更文件

| 文件 | 变更 |
|---|---|
| `api/src/locale_builder.py` **(新)** | 导出所有语言字典到 `/data/json/locale/{lang}.json` |
| `api/src/collector.py` | 加 `translation_key` 到 entity JSON; 加管道步骤 `build_locale_files`; `_SOURCE_PATHS` 加 `LOCALIZATION_ROOT` |
| `api/src/entity_export.py` | 加 `translation_key` 写入; 可选删 `resolve_en_name` / `translation_EN` |
| `api/src/lootdrop_builder.py` | 同上 |
| `api/src/module_builder.py` | 同上 |
| `api/src/index_export.py` | 加 `translation_key` 到索引 |
| `api/src/config.py` | 加 `LOCALE_OUTPUT_DIR` |
| `api/src/db/_helpers.py` | 保持 `load_game_json` / `discover_languages`; `load_en_game_json` 保留或清理 |
| `api/src/db/__init__.py` | 保持 `get_translations_map(lang)` (已支持 10 语言) |

### 3.1a translation_key 注入

**当前实体 JSON 缺少 `translation_key` 字段**，SSG 无法用该 key 去查各语言字典。需在 entity_export / lootdrop_builder / module_builder 中添加：

```python
# entity_export.py: export_items()
entity_data = {
    "name": name,
    "translation": translation,
    "translation_key": r["translation_key"],  # 新增
    "translation_EN": translation_en,          # 保留(过渡期)
    ...
}
```

对所有实体类型（items/monsters/props/lootdrops/modules/quest_npc）同步添加。

> **兼容**: 旧 HTML 页面（未重建）访问时，`translation_key` 不存在也不影响，回退到 `entity.translation`。

### 3.2 `locale_builder.py` 核心逻辑

```python
def build_locale_files(db: DatabaseManager, output_dir: Path):
    langs = discover_languages()  # 10 个
    for lang in langs:
        data = db.get_translations_map(lang)
        # data: {translation_key: localized_text}
        dest = output_dir / "locale" / f"{lang}.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
```

- 输出到 `api/output/json/locale/{lang}.json`，前端经版本化路径 `/data/{short}/json/locale/{lang}.json` 读取。
- 每条 key 对应一个 `translation_key`（如 `Text_DesignData_Item_Item_Ale_1001`），值是该语言的翻译文本。
- 实体 JSON 的 `translation_key` 字段直接作为 locale dict 的查找键。

### 3.3 清理 `translation_EN`（次优先级）

- 可在路由功能稳定后做，与路由改造解耦。
- 详情 JSON 保留 `translation_key` + `translation`(zh)，移除 `translation_EN` 可减 ~1.5 MB。

---

## 4. 前端改造 (Web / React)

### 4.1 新增依赖

**未引入 `react-i18next`**。采用轻量自建方案：`LanguageProvider` + `useLocale()` + `ut()`。无需额外 npm 包。

### 4.2 目录结构（实际落地）

```
web/src/i18n/
├── locale.ts               # 语言列表、loadLocale、translate()
├── LanguageContext.tsx      # LanguageProvider + useLanguage + 路径工具
├── useLocale.ts             # Hook: t(translation_key, fallback) + ut(ui_key)
├── uiLocale.ts              # UI 文案字典 (10 语言 × ~60 key/语言)
├── antdLocale.ts            # useAntdLocale hook (懒加载 Ant Design locale 模块)
└── index.ts                 # 导出
```

- 实体字典：运行时 fetch `/data/{short}/json/locale/{lang}.json`（后端 locale_builder.py 生成）
- UI 字典：静态 import `uiLocale.ts`（TypeScript const 对象，~60 key/语言）
- AntD locale：`useAntdLocale()` 按语言懒加载 `antd/locale/{lang}` 模块

### 4.3 路由改造 (`AppInner.tsx`) — v0.10 已落地

统一 `/:lang/...` 前缀（含 zh-Hans），非前缀旧路径自动跳转：

```tsx
// AppInner.tsx (v0.10 实际代码)
<Routes>
  <Route path="/" element={<HomePage />} />                    {/* 唯一非前缀路由 */}
  <Route path="/:lang" element={<HomePage />} />
  <Route path="/:lang/explore" element={<ExplorePage />} />
  <Route path="/:lang/quest_items" element={<QuestItemsPage />} />
  <Route path="/:lang/quest_items/:group" element={<QuestItemGroupPage />} />
  <Route path="/:lang/quest_npc" element={<QuestNPCPage />} />
  <Route path="/:lang/quest_npc/:npc_name" element={<QuestNPCDetailPage />} />
  <Route path="/:lang/dungeon_modules" element={<DungeonModulesPage />} />
  <Route path="/:lang/dungeon_modules/:group" element={<DungeonModuleGroupPage />} />
  <Route path="/:lang/dungeon_modules/:group/:name" element={<DungeonModuleDetailPage />} />
  <Route path="/:lang/lootdrops/:name" element={<LootdropDetailPage />} />
  <Route path="/:lang/:page" element={<ListPage />} />
  <Route path="/:lang/:page/:name" element={<DetailPage />} />
  <Route path="*" element={<LegacyRedirect />} />              {/* 旧路径 → /zh-Hans/... */}
</Routes>
```

**旧路径处理**: `LegacyRedirect` 组件检查 `location.pathname` 首段，若非 `isSupportedLang` 则 `window.location.replace('/zh-Hans' + path)` 跳转。

**关键差异 vs v0.9**:
- 移除全部非前缀显式路由（`/items`、`/lootdrops/:name` 等），消除 `useParams().page` 缺失 bug。
- `withLangPrefix` 不再为 zh-Hans 去前缀。
- SSG 生成路径从 `dist/items/...` 改为 `dist/zh-Hans/items/...`。

### 4.4 `LanguageProvider` / `useLocale()` 关键点（已落地）

- `LanguageProvider`：从 URL 第一段提取 lang → 验证 SUPPORTED_LANGS → fallback zh-Hans。
- `useLocale()`：返回 `{ lang, dict, t, ut }`。
  - `t(key, fallback)`：先查合并字典（UI locale + 运行时实体 locale），再 fallback。
  - `ut(uiKey)`：直接查 UI locale，用于纯 UI 标签（如 `ut('ui.common.loading')`）。
- SSR 阶段：只渲染中文，不加载任何 locale dict。非中文页的 `<title>` 由 SSG 后处理替换。
- 客户端 hydration 后：`useEffect` → `fetch(dataUrl(version, '/data/json/locale/{lang}.json'))` → 合并 UI+实体字典。
- `uiLocale.ts`：10 语言静态字典（TypeScript const），直接 import，无需 fetch。

### 4.5 字典加载策略

| 场景 | 行为 |
|---|---|
| 后处理写入 `/en/lootdrops/.../` | 文本替换 `__SSR_DATA__` 注入 `lang: 'en'` + 替换 `<title>` 为翻译后标题 |
| 客户端 hydration | SSR/CSR 语言一致（从 URL 确定），直接 hydrate，无 mismatch |
| 客户端切换语言 | `localStorage.setItem('lang', 'en')` → `window.location.href = '/en/当前路径'` → 加载 SSG 页 |
| 无前缀访问 | 固定 `zh-Hans`，不自动重定向 |

### 4.6 详情页标题 (SSG 后处理 + 客户端 i18n)

**标题通过 SSG 后处理写入，body 文字通过客户端 i18n 切换。**

| 页面 | 改造点 |
|---|---|
| `DetailPage.tsx` | 从 `__SSR_DATA__.lang` 读取语言；非 zh-Hans 时加载 locale dict → i18next 翻译 UI 文案；Helmet 同步更新 `<title>` (与 SSG 后处理已写入的一致，无闪烁) |
| `LootdropDetailPage.tsx` | 同上 |
| `DungeonModuleDetailPage.tsx` | 同上 |
| `QuestNPCDetailPage.tsx` | 同上 |
| `QuestItemGroupPage.tsx` | 组名保持英文 URL group，暂不做 i18n |
| `NavBar.tsx` | 下拉选择语言 → `/{newLang}/当前路径` 整页导航 |

**SSG 后处理伪代码** (ssg.mjs):

```js
// 1. 中文全量渲染 (现有流程)
renderAllRoutes('zh-Hans')  // dist/*.html

// 2. 非中文后处理 (无 renderToString)
for (lang of ['en', 'de', 'es', 'fr', 'ja', 'ko', 'pt-BR', 'ru', 'zh-Hant']) {
  localeDict = readJSON(`data/locale/${lang}.json`)
  for (route of routes) {
    zhHtml = readFile(`dist${route.path}/index.html`)
    title = localeDict[entity.translation_key] || entity.translation
    langHtml = zhHtml
      .replace(/<title>[^<]*<\/title>/, `<title>${title}</title>`)
      .replace('window.__SSR_DATA__', `window.__SSR_DATA__={...originData,lang:'${lang}'}`)
    writeFile(`dist/${lang}${route.path}/index.html`, langHtml)
  }
}
```

**客户端行为**:

1. HTML 解析 → `__SSR_DATA__.lang` 非 zh-Hans
2. Hydrate 中文 body (SSR/CSR 完全一致，安全)
3. `useEffect` → fetch `/data/{short}/json/locale/{lang}.json` → 加载 locale dict
4. i18next 替换 UI 文案 (NavBar、列表、卡片等)
5. Helmet `<title>` 更新为目标语言 (与 SSG 已写入的一致，无闪烁)

### 4.7 UI 文案 i18n 完成度

**已接入 `ut()` 的页面/组件：**

| 页面/组件 | 已翻译内容 |
|---|---|
| `NavBar.tsx` | 标签名/面包屑、搜索 placeholder/标签/最近搜索/搜索按钮、主题切换 aria-label、返回首页 |
| `Disclaimer.tsx` | 免责声明、反馈链接 |
| `ListPage.tsx` | 页面标题（NavBar 标签复用）、lootdrop 分组名（神器/小型神器等）、调试按钮 |
| `DetailPage.tsx` | 加载文字、调试按钮、爆率显示/模式筛选/隐藏零爆率标签 |
| `LootdropDetailPage.tsx` | 同上 + 爆率品质标签（极低/低/中/高） |

**未接入 `ut()` 的页面/组件（下次会话继续）：**

| 页面 | 待翻译内容 |
|---|---|
| `HomePage.tsx` | 页面描述文字、导航卡片标签、SEO tagline |
| `DungeonModulesPage.tsx` | 标题、统计、"未分组"回退 |
| `DungeonModuleGroupPage.tsx` | 标题、调试按钮 |
| `DungeonModuleDetailPage.tsx` | 标题、稀有度标签、实体类型标签、统计 |
| `ExplorePage.tsx` | 标题 |
| `QuestItemsPage.tsx` | 标题、统计 |
| `QuestItemGroupPage.tsx` | 标题、实体图例、位置统计 |
| `QuestNPCPage.tsx` | 标题、NPC 分类标签 |
| `QuestNPCDetailPage.tsx` | 奖励类型、任务目标、稀有度、统计、NPC 名 |

**UI locale 键命名规范：**
```
ui.nav.items         → 物品表 / Items / ...
ui.search.placeholder → 搜索物品/怪物/实体... / Search...
ui.common.loading    → 加载中... / Loading...
ui.filter.drop_rate  → 爆率显示 / Drop Rate
ui.rate.very_low     → 极低(PVE100%) / Very Low (PVE 100%)
ui.list.artifact     → 神器 / Artifact
ui.detail.position   → 位置 / Position
ui.disclaimer.warning → 数据有误差...
```

---

## 5. PWA / Service Worker 缓存

| 资源 | 缓存策略 |
|---|---|
| `/data/{short}/json/locale/*.json` | 复用现有 `df5-data-json` `StaleWhileRevalidate` 缓存 |
| `/*.html` (多语言 SSG) | 现有策略不变。用户同一时间只使用一种语言，不会被其他语言 HTML 驱逐 |
| 现有 JSON / img | 保持原策略 |

- `vite.config.ts` 不需要新增 locale 专用规则；现有 `/^\/data\/(?:[a-z0-9]+\/)?json\//` 已覆盖版本化 locale 字典。
- `df5-html` `maxEntries` **保持 1300 不变** — 用户不会同时浏览多语言页面，单语言 HTML 数量未变。

---

## 6. 构建 / 部署流程变更

```bash
# 完整构建 (新增 locale 导出 + 多语言 SSG)
cd api && python main.py          # 生成 api/output/json/locale/{lang}.json + 实体 JSON
cd web && npm run build           # SSG 生成所有语言版本页面
./deploy.sh                       # 交付 + 提交
```

### 6.1 `ssg.mjs` 改造 (轻量)

**改造原则: 不与现有中文 SSG 流程竞争，只在其输出上做文本后处理。**

两步走:

**Step 1 — 中文全量渲染 (现有流程，不改动)**
```
所有路由 × full SSR data → dist/*.html
```

**Step 2 — 非中文后处理 (新增，无 renderToString)**
```
for each lang in [en, de, es, fr, ja, ko, pt-BR, ru, zh-Hant]:
    localeDict = readJSON(`data/locale/${lang}.json`)
    for each route:
        zhHtml = readFile(`dist${route.path}/index.html`)
        entity = extractEntityFromSSRData(zhHtml)
        title = localeDict[entity.translation_key] || entity.translation
        langHtml = zhHtml
            .replace('<title>...</title>', `<title>${title}</title>`)
            .injectSSRDataField('lang', lang)
            .injectAlternateLinks(allLangUrls)
        writeFile(`dist/${lang}${route.path}/index.html`, langHtml)
```

核心操作是字符串替换，不需要 React 参与。详情页的 `__SSR_DATA__` 保留完整的 entity 数据（与中文版相同），仅叠加 `lang` 字段。

**lootdrop SEO 标题限制**：SSG 生成 lootdrop 详情页 `<title>` 时只包含 lootdrop 物品名，不包含嵌套怪物名/来源名。嵌套来源可能非常多，纳入标题会增加后处理计算、字符串长度和 SEO 噪声；来源列表留给页面正文和客户端渲染。

**hreflang 注入**: 每页 `<head>` 中写入 10 条 alternate 链接（指向自身及其他语言版本的 URL），SSG 阶段 URL 已知，纯文本拼接。

### 6.2 构建时间预估

| 阶段 | 当前 | 多语言后 (10 语言) |
|---|---|---|
| renderToString 调用 | 3,096 次 | **3,096 次** (不变) |
| 文本后处理页面数 | 0 | ~27,864 (9 lang × 3,096) |
| 构建时间 | ~2-3 min | **~3-4 min** (+ 文本替换约 30s) |
| dist 大小 (单语言) | ~720 MB | **~1.28 GB** (+ 9 × ~62 MB HTML 副本) |

> 单语言 720 MB 含 681 MB JSON + ~39 MB HTML。9 语言 HTML 副本 ~560 MB，总 dist ~1.28 GB。

### 6.3 sitemap.xml

- sitemap 包含所有语言版本的 URL。
- 每个 URL 附加 `<xhtml:link rel="alternate" hreflang="lang" href="...">`。

---

## 7. 测试 / 验收标准

### 7.1 单元 / 冒烟

| 测试项 | 通过标准 |
|---|---|
| 后端导出 locale | `api/output/json/locale/*.json` 共 10 文件,键数 ≈ 1600+,非空值率 > 95% |
| 实体 JSON 含 translation_key | `grep -c '"translation_key"' data/json/lootdrops/HeaterShield_8001.json` ≥ 1 |
| collector 正常跑通 | `python main.py` 无报错 |

### 7.2 前端回归 (Playwright)

| 页面 | 测试点 |
|---|---|
| `/en/lootdrops/HeaterShield_8001/` | `<title>` 为英文名 "Immortal Shield" |
| `/ja/lootdrops/HeaterShield_8001/` | `<title>` 为日文名 |
| `/items/Ale/` (无前缀) | 固定简体中文，不按浏览器语言自动跳转 |
| `/en/items/Ale/` | 列表页卡片名为 "Ale" |
| `curl /en/monsters/Mimic_Large_Flat/ \| grep '<title'` | 英文名,非空 |

### 7.3 Hydration / SSR

- `curl /en/items/Ale/ | grep '<title'` → 英文,非空。
- `npm run build` 无 `Hydration failed` / `#418` / `#423` 错误。
- 中文页面 (`/items/Ale/`) 行为不变,向后兼容。

### 7.4 性能

| 指标 | 目标 |
|---|---|
| 首屏 FCP (zh) | < 1.2s (与现状持平) |
| 首屏 FCP (en,url 进入) | < 1.5s (SSG 直出中文 body + locale dict fetch,~50KB GZip 不影响 FCP) |
| 语言切换 | 整页导航到新 URL,SSG 页面直出,locale dict 已在 SW 缓存中 |
| locale 字典总大小 | < 500 KB / 语言 (GZip < 150 KB) |

---

## 8. 风险与缓解

| 风险 | 影响 | 缓解 |
|---|---|---|
| **HTML 文件倍增** | dist 增 ~560 MB | 9 语言 × ~62 MB HTML 副本;SW df5-html maxEntries 保持 1300 (用户单语言浏览) |
| **翻译键缺失** | 标题为中文回退 | `localeDict[translation_key] || entity.translation` 兜底 |
| **hydration mismatch** | React warning / 白屏风险 | 当前 v0.8 未解决；采用 10.1 推荐方案，确保 Helmet 首轮标题与 SSG head 一致 |
| **无前缀页 404** | 旧链接失效 | 保留无前缀路由；无前缀固定 zh-Hans，不按浏览器语言重定向 |
| **locale dict 首屏加载** | 非中文页首屏 body 为中文，闪变为目标语言 | 切换前显示 loading 骨架屏;locale dict 小 (~200 KB GZip ~50 KB)，加载快 |

---

## 9. 实施里程碑

### 9.0 当前完成情况（2026-07-25，最后更新）

**已完成：**

| Phase | 内容 | 产出 |
|---|---|---|
| P0 | 修复 ssg.mjs 版本化数据目录顺序 | meta.json 保留，大 JSON 进版本化路径 |
| P1 | items/monsters/props/lootdrops/modules/search_index 输出 `translation_key` | 实体 JSON 含 translation_key |
| P2 | 新建 `locale_builder.py` | 10 语言 `data/json/locale/{lang}.json` |
| P3 | 语言前缀路由 `/:lang/...` | `/en/...` 等路径可访问；无前缀固定 zh-Hans |
| P4 | `LanguageProvider` + `useLocale()` | URL 提取 lang → 加载版本化 locale dict |
| P5 | ssg.mjs 多语言 HTML 后处理 | 9 种非中文 HTML 副本，含 localized title/canonical/hreflang/`__lang` |
| P6 | NavBar 语言下拉 + 搜索结果翻译 | 语言选择 → 整页导航；搜索结果实体名按 locale 翻译 |
| P7 | sitemap 多语言 URL | 10 语言 URL + `xhtml:link rel="alternate"` |
| P8 | lootdrop 嵌套 monsters + group_drop_info 补 `translation_key` | 前端可翻译 lootdrop 内嵌实体名 |
| P8 部分 | 新建 `uiLocale.ts`（10 语言 × ~60 key） | NavBar/Disclaimer/ListPage/DetailPage/LootdropDetailPage 核心 UI 接入 `ut()` |
| **P8d** | **剩余 9 页面 UI i18n + LootdropDetail 嵌套实体名翻译** | **HomePage/DungeonModules(Group/Detail)/Explore/QuestItems(Group)/QuestNPC(List/Detail) 全量接入 `ut()`；GDI/模块名改用 `t(translation_key)`** |
| P9 部分 | Ant Design locale 切换 | `useAntdLocale` + `AntdLocaleProvider`，按语言懒加载 antd locale 模块 |
| **P10** | **统一语言前缀 v0.10** | zh-Hans 也用 `/zh-Hans/` 前缀；移除双路由树；`*` catch-all → `LegacyRedirect` 跳转旧路径；`withLangPrefix` 始终加前缀；SSG 默认语言生成至 `/zh-Hans/` 目录 |

**当前架构速览：**
- 语言检测：URL 前缀 → `LanguageProvider.lang` → `useLocale()`
- 实体翻译：`entity.translation_key` → `loadLocale()` 运行时 fetch → `t(key, fallback)`
- UI 翻译：`ut('ui.nav.items')` → 静态 `uiLocale.ts` 字典 → 合并入 `useLocale().t()`
- AntD 翻译：`useAntdLocale()` → 懒加载 antd locale 模块 → `ConfigProvider locale`
- SSG 多语言：中文 renderToString 一次 → 文本后处理生成 9 非中文副本
- 路由统一：所有语言 `/:lang/...`（含 zh-Hans）；旧路径 302 → `/zh-Hans/...`

---

### 9.1 完成项回顾

所有 P0-P11 计划项已完成。

| Phase | 内容 | 完成度 |
|---|---|---|
| P0-P8d | 翻译键注入、locale 导出、语言路由、SSG 多语言、UI i18n 全量接入 | ✅ |
| P9 | AntD locale 切换 + locale 字典体积优化（1056 key/语言，↓34%） | ✅ |
| P10 | Playwright 回归测试框架搭建（5 页面 × 3 语言 × 标题验证 + Hydration 检查） | ✅ |
| P11 | 移除 `translation_EN` / `resolver_en`（16 文件，~50 处引用） | ✅ |

---

### 9.2 文件变更清单（已实际修改）

**新增：**
```
api/src/locale_builder.py          # locale 字典导出
web/src/i18n/locale.ts             # 语言列表 / loadLocale()
web/src/i18n/LanguageContext.tsx    # LanguageProvider + 路径工具
web/src/i18n/useLocale.ts          # useLocale() hook
web/src/i18n/uiLocale.ts           # UI 文案字典 (10 语言 × ~60 key → 已扩展至 ~135 key)
web/src/i18n/antdLocale.ts         # AntD locale 懒加载 hook
```

**修改：**
```
api/src/collector.py               # + build_locale_files 管道步骤
api/src/entity_export.py            # + translation_key 写入
api/src/lootdrop_builder.py         # + translation_key (顶层 + 嵌套 monsters + gdi)
api/src/module_builder.py           # + translation_key 写入
api/src/index_export.py             # + translation_key 到索引
api/src/config.py                   # + LOCALE_OUTPUT_DIR
web/src/App.tsx                     # 移除硬编码 zhCN
web/src/AppInner.tsx                # + 语言前缀路由 + AntdLocaleProvider
web/src/components/NavBar.tsx       # + 语言下拉 + UI i18n
web/src/components/Disclaimer.tsx   # + UI i18n
web/src/pages/ListPage.tsx          # + 实体名翻译 + UI i18n
web/src/pages/DetailPage.tsx        # + 实体名翻译 + UI i18n
web/src/pages/LootdropDetailPage.tsx # + 实体名翻译 + UI i18n + 嵌套实体名 t() 翻译 + GroupDropInfo translation_key
web/src/pages/HomePage.tsx          # P8d: 卡片描述/tagline/计数全部 ut()
web/src/pages/DungeonModulesPage.tsx # P8d: 标题/统计/模块计数 ut()
web/src/pages/DungeonModuleGroupPage.tsx # P8d: 标题/隐藏计数/调试按钮 ut()
web/src/pages/ExplorePage.tsx       # P8d: 标题/统计/任务标签 ut()
web/src/pages/QuestItemsPage.tsx     # P8d: 标题/统计/实体位置计数 ut()
web/src/pages/QuestItemGroupPage.tsx # P8d: 标题/图例/位置统计 ut()
web/src/pages/QuestNPCPage.tsx      # P8d: 统计/NPC分类标签/CATEGORY_KEYS ut()
web/src/pages/DungeonModuleDetailPage.tsx # P8d: 标题/实体类型标签/位置统计 ut()
web/src/pages/QuestNPCDetailPage.tsx # P8d: CONTENT_TYPE_KEY/REWARD_TYPE_KEY → ut(); 全部中文标签替换
web/src/hooks/useSearchIndex.ts     # + translation_key 类型
web/src/types/data.ts               # + translation_key 字段
web/scripts/ssg.mjs                 # + 多语言 HTML 后处理 + hreflang + sitemap
CLAUDE.md                           # + 多语言文档映射
docs/BUILD_AND_DEPLOY.md            # + locale 导出流程说明
```

---

> **本文档将持续更新**。P0-P11 全部完成。

---

## 10. 问题追踪 (v0.8 → v0.9)

### 10.1 ✅ 非中文 SSG 页标题 hydration 崩溃 — 已修复

**修复方案**：采用"B 精简版"——SSG 后处理仅注入当前路由实体的 `__localizedTitle` 到 `window.__SSR_DATA__`，不 inline 整份 locale JSON。

**变更文件**：
- `web/scripts/ssg.mjs` — `injectLang()` 替换为 `injectLocalizedData(page, lang, title)`，同时注入 `__lang` 和 `__localizedTitle`
- `web/src/i18n/ssrTitle.ts` — 新建，导出 `ssrLocalizedTitle()` 读取 `window.__SSR_DATA__.__localizedTitle`
- `web/src/pages/DetailPage.tsx` — Helmet `<title>` / `og:title` 使用 `ssrLocalizedTitle() ?? 原中文标题`
- `web/src/pages/LootdropDetailPage.tsx` — 同上
- `web/src/pages/DungeonModuleDetailPage.tsx` — 同上
- `web/src/pages/QuestNPCDetailPage.tsx` — 同上

**验证结果**：
- `curl /en/lootdrops/HeaterShield_8001/ | grep title` → `Heater Shield | DarkFlashNav` ✓
- `curl /ja/items/Ale/ | grep title` → `エール | DarkFlashNav` ✓
- `curl /ja/lootdrops/HeaterShield_8001/ | grep title` → `ヒーターシールド | DarkFlashNav` ✓
- Playwright: en/ja lootdrop 页 hydro 错误从 **8 → 7**（-1，标题错误消除）；模块详情页 hydro 仍 8（NavBar 标签占全部）

### 10.2 ✅ ModuleDetail 标题重复 — 已修复

**修复方案**：引入 `moduleDisplayName = m.translation || m.name`，Helmet title / description / H1 统一使用。

**变更文件**：`web/src/pages/DungeonModuleDetailPage.tsx`

**验证结果**：
- Playwright zh-Hans ModuleDetail: title 从 `钉手岛钉手岛 地图模块Module` → `钉手岛 地图模块Module` ✓

### 10.3 ⚠️ NavBar 标签 hydration mismatch — 已知残留

**现象**：Playwright 回归测试中 en/ja 所有页面仍有 7-8 个 #418/#423 错误，全部来自 NavBar。

**根因**：`NavBar` 使用 `ut(NAV_LABEL_KEYS[p])` 渲染标签，`ut()` 在 `lang='en'` 时直接返回静态英文标签（Item/Monster 等），但 SSG HTML body 是中文版（物品表/怪物等）。React hydration 发现 NavBar DOM 与客户端渲染不一致 → 报错。

**与标题问题的区别**：
- 标题：单点失配，现已通过 `__localizedTitle` 解决
- NavBar：多点失配（~8 个 tab），涉及 10 个 60+ key 的 UI locale 字典

**备选方案**（待评估）：
| 方案 | 描述 | 副作用 |
|------|------|--------|
| `useState(false)` 门控 | hydration 首轮强制回退到中文标签，`useEffect` 后再切英文 | 非中文用户看到短暂中文闪烁 |
| SSG body 后处理 | 后处理替换 body 中的 NavBar 中文→英文 | 需精确匹配所有中文字符串，维护成本极高，且语言越多越不可维护 |
| 纯 CSR NavBar | 非中文页 NavBar 设为 `visibility:hidden`，hydration 后再显示 | FOUC（无样式内容闪烁），UX 差 |

**推荐方向**：暂时接受该残留。（不阻塞发布；用户通常单语言使用，不会频繁刷新非中文页；控制台错误不影响功能。）

> **注**：NavBar 标签语言切换是运行时行为，不属于 SSG head 范畴；完整解决需架构级改造，留待 v1.0 评估。
