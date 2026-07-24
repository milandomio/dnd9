# 多语言 (i18n) 重构计划

> 创建日期: 2026-07-24
> 版本: v0.3 (路由版·轻量SSG)
> 状态: 核心链路已落地 — UI/回归/清理仍待收尾

> 执行进度（2026-07-24）：P0-P7 核心链路已完成并提交；P8-P12 仍需继续执行。当前实现未引入 `react-i18next`，采用轻量 `LanguageProvider` + `useLocale()`。

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

#### 2.3.1 语言前缀路由

```
/                                     → zh-Hans (默认,向后兼容)
/en/lootdrops/HeaterShield_8001/      → English
/ja/items/Ale/                        → 日本語
/ko/monsters/Mimic_Large_Flat/        → 한국어
/zh-Hant/props/TreasureChest/         → 繁體中文
...
```

- **无前缀路径** (如 `/items/Ale/`) 固定保持简体中文，避免破坏现有外链；只有用户主动切换语言才进入 `/{lang}/...`。
- 语言代码与 locale 文件名一致（`en`、`ja`、`ko`、`zh-Hant`、`zh-Hans` 等）。

#### 2.3.2 支持的语言范围

| 语言 | 代码 | 路由前缀 |
|---|---|---|
| 简体中文 (默认) | zh-Hans | `/` |
| English | en | `/en/` |
| Deutsch | de | `/de/` |
| Español | es | `/es/` |
| Français | fr | `/fr/` |
| 日本語 | ja | `/ja/` |
| 한국어 | ko | `/ko/` |
| Português (BR) | pt-BR | `/pt-BR/` |
| Русский | ru | `/ru/` |
| 繁體中文 | zh-Hant | `/zh-Hant/` |

> 简体中文保留在根路径 `/`，其余 9 语言前缀路由。避免破坏现有外链。SSG 总页面数 = 3,096 × 10 = ~30,960。

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

```bash
npm i react-i18next i18next
npm i -D @types/i18next   # 如需
```

### 4.2 目录结构

```
web/src/i18n/
├── I18nProvider.tsx      # 根 Provider, SSR 安全,从路由提取 lang
├── useI18n.ts            # Hook 返回 {t, lang, setLang, ready}
├── config.ts             # 支持语言列表、字典懒加载、namespace
├── locales/              # UI 文案字典 (TS 直写)
│   ├── zh-Hans.json
│   ├── en.json
│   └── ...
└── index.ts              # 导出
```

### 4.3 路由改造 (`AppInner.tsx`)

所有路由添加 `:lang` 前缀，同时保留无前缀路径（自动重定向）：

```tsx
// AppInner.tsx
<Routes>
  {/* 有语言前缀的路由 */}
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

  {/* 无前缀 → zh-Hans，保持现有 URL */}
  <Route path="/" element={<HomePage />} />
  <Route path="/explore" element={<ExplorePage />} />
  <Route path="/quest_items" element={<QuestItemsPage />} />
  <Route path="/quest_items/:group" element={<QuestItemGroupPage />} />
  <Route path="/quest_npc" element={<QuestNPCPage />} />
  <Route path="/quest_npc/:npc_name" element={<QuestNPCDetailPage />} />
  <Route path="/dungeon_modules" element={<DungeonModulesPage />} />
  <Route path="/dungeon_modules/:group" element={<DungeonModuleGroupPage />} />
  <Route path="/dungeon_modules/:group/:name" element={<DungeonModuleDetailPage />} />
  <Route path="/lootdrops/:name" element={<LootdropDetailPage />} />
  <Route path="/:page" element={<ListPage />} />
  <Route path="/:page/:name" element={<DetailPage />} />
</Routes>
```

**SSR 路由生成**: SSG 分别输出 `/{lang}/lootdrops/HeaterShield_8001/index.html` 等，HTML 中 `<title>` 已为对应语言。

**无前缀访问**: 固定作为 `zh-Hans` 渲染，不按浏览器语言自动跳转。

### 4.4 `I18nProvider` 关键点

- URL 路径提取 `lang` 参数 → 验证是否在支持列表中 → 不在则 fallback 到 zh-Hans。
- SSR 阶段: `i18n.init({ lng: 'zh-Hans', resources: {} })`，不预注入任何 locale dict。HTML 中的 `<title>` 已由后处理替换为目标语言，body 保留中文。
- 客户端 hydration 后: 读取 `__SSR_DATA__.lang`，非 zh-Hans 时通过 `dataUrl(dataVersion, '/data/json/locale/{lang}.json')` 获取版本化字典 → 切换语言。
- 字典加载: `fetch(dataUrl(dataVersion, '/data/json/locale/{lang}.json'))`。

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

### 4.7 UI 文案 i18n

| 文案示例 | 键名 |
|---|---|
| "物品表" | `ui.nav.items` |
| "怪物表" | `ui.nav.monsters` |
| "数据有误差,以实际游戏内为准" | `ui.disclaimer` |
| "未分组" | `ui.common.ungrouped` |
| "加载中..." | `ui.common.loading` |

- 存入 `web/src/i18n/locales/{lang}.json` (TS 直写或 JSON import),约 15-30 条/语言。
- **实体名翻译**: 非 zh-Hans 时，列表页卡片、详情页标题、关联实体名等所有展示 entity `translation` 的地方，统一通过 `localeDict[entity.translation_key]` 替换。组件内用 `t(entity.translation_key, { fallback: entity.translation })` 模式。
- **UI 文案翻译必须人工维护**：前端硬编码 UI 文案不能机械套 Game.json，也不能自动机翻后直接落库。每条 UI key 需要手动写入各语言文案；为保证措辞贴近游戏，翻译时优先查对应语言 `Game.json` 中相同/相近功能的官方表达，再手动改写到 UI 语境。
- **调试字段默认不翻译**：坐标 `label`、`original_keyword`、`keyword`、文件名、内部 entity name 等主要用于调试和溯源，默认保留原始值。只有当这些字段已经作为用户可见文案渲染，或现有中文逻辑已明确翻译给用户看时，才纳入 i18n。
- **rarity 翻译来源**：`variant_rarity` 本来就由后端从对应语言/翻译表的 Game.json key 提取，不应在前端二次手写或重复映射；后续多语言 rarity 只需确保后端按目标语言输出或前端按 rarity key 查 locale。

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
| `/items/Ale/` (无前缀) | 自动重定向到浏览器语言版本 |
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
| **hydration mismatch** | React warning | 非中文页 body 与中文版完全一致，仅叠加 `__SSR_DATA__.lang`;hydration 安全 |
| **无前缀页 404** | 旧链接失效 | 保留无前缀路由;客户端检测浏览器语言后重定向 |
| **locale dict 首屏加载** | 非中文页首屏 body 为中文，闪变为目标语言 | 切换前显示 loading 骨架屏;locale dict 小 (~200 KB GZip ~50 KB)，加载快 |

---

## 9. 实施里程碑

### 9.0 当前完成情况（2026-07-24）

已完成：

- P0：修复 `ssg.mjs` 版本化数据目录顺序，保留 `/data/json/meta.json`，大 JSON 进入 `/data/{short}/json/`。
- P1：items/monsters/props/lootdrops/dungeon_modules/search_index 输出 `translation_key`。
- P2：新增 `api/src/locale_builder.py`，导出 10 语言 `data/json/locale/{lang}.json`。
- P3：新增语言前缀路由，`/en/...` 等路径可访问；无前缀路径固定 `zh-Hans`，不自动重定向。
- P4：新增 `LanguageProvider` / `useLocale()`，按 URL 语言和 data version 加载版本化 locale 字典。
- P5：`ssg.mjs` 生成非中文 HTML 副本，注入 localized title、canonical、hreflang、`window.__SSR_DATA__.__lang`。
- P6：NavBar 语言下拉、搜索结果、列表页、items/monsters/props 详情页、lootdrop 详情页主实体名已接入 locale。
- P7：sitemap 已输出 10 语言 URL，并带 `xhtml:link rel="alternate"`。

待完成：

- P8：全量 UI 文案 i18n。当前大量页面文案仍为中文，包括 Disclaimer、按钮、筛选项、统计说明、分组名、爆率提示、加载/空状态等。UI 文案和前端硬编码必须手动翻译，翻译时参考对应语言 Game.json 的官方表达。
- P8：任务页、探索页、地图模块页、Quest NPC 页仍未系统接入 locale；部分页面只继承 NavBar 语言切换。
- P8：lootdrop 详情页内嵌怪物名、`group_drop_info`、地图模块名等仍未全量按 `translation_key` 翻译；坐标 label 属调试/溯源字段，默认不翻译，除非它已作为用户可见文案渲染；variant rarity 已由 Game.json 翻译链路提供，不做前端硬编码映射。
- P8：后端尚未给 lootdrop `monsters` 内嵌项、`group_drop_info` 条目、quest/export 结构补齐 `translation_key`，因此前端无法稳定翻译所有嵌套名称。
- P9：locale 字典当前导出完整 Game.json，体积大于原计划估算；需过滤到实际使用 key + UI key，或明确接受完整字典体积。
- P9：Ant Design locale 仍固定 `zh_CN`，语言切换后组件内置文案不会变。
- P10：尚未执行 Playwright 多语言 hydration/console 全站回归；只验证了构建通过和 `/`、`/en/items/Ale/` HTTP 200。
- P11：尚未清理 `translation_EN` / `resolver_en`，仍作为 SEO/回退字段保留。
- P12：需在完成 P8-P11 后再次同步文档、更新验收标准和计划状态。

### 9.1 原始里程碑

| Phase | 任务 | 产出 | 预估工时 |
|---|---|---|---|---|
| **P0 准备** | 确认计划、分支切分；修改 ssg.mjs 版本化数据目录为"移动而非复制"（省 681 MB） | `feat/multilang` 分支; ssg.mjs 改 rmSync 冗余 JSON | 0.5h |
| **P1 translation_key 注入** | entity_export/lootdrop_builder/module_builder/index_export 加 `translation_key` 字段 | 实体 JSON 含 translation_key,管道跑通 | 1.5h |
| **P2 locale_builder** | 新建 `locale_builder.py`,集成 collector 管道 | `api/output/json/locale/*.json` 生成 (10 语言) | 1.5h |
| **P3 前端路由改造** | AppInner 添加 `/:lang` 前缀路由 + 无前缀重定向逻辑 | `/en/items/...` 可访问 | 2h |
| **P4 I18nProvider + URL 检测** | 从 URL 提取 lang、验证列表、加载 locale dict、注入 i18next | `I18nProvider` 按 URL 自动选语言 | 2h |
| **P5 SSG 文本后处理** | ssg.mjs 新增后处理阶段:读中文 HTML → locale dict 替换 `<title>` → 注入 lang+hreflang → 写 `dist/{lang}/.../index.html` | 9 语言 HTML 生成 | 1.5h |
| **P6 NavBar 语言切换** | 下拉选择语言 → `/{newLang}/当前路径` 整页导航 | 导航栏语言切换 | 1.5h |
| **P7 hreflang + sitemap** | 每个页面注入 alternate 链接 + 多语言 sitemap | SEO 完整 | 1.5h |
| **P8 UI 文案 i18n** | 15-30 条常用文案迁移 + Disclaimer/NavBar/列表页 | 导航/提示切语言 | 1.5h |
| **P9 PWA 缓存调整** | workbox 新增 locale 缓存规则 (maxEntries:15) | locale dict SW 缓存正常 | 0.5h |
| **P10 回归测试** | Playwright 5 页 (home/items/Ale/lootdrops/HeaterShield_8001/monsters/Mimic_Large_Flat/dungeon_modules/Crypt/AdmirerRoom) × 3 语言 (zh-Hans/en/ja) × 标题验证 + Hydration 检查 | 全绿 | 2h |
| **P11 后端清理 (可选)** | 删 `translation_EN`/`resolver_en`/`load_en_game_json` | 代码减 ~120 行 | 1.5h |
| **P12 文档 & 收尾** | 更新 CLAUDE.md 流程说明 | 文档同步 | 0.5h |

**总计约 16.5h (2.5-3 天)。全部 10 语言同步推出。**

---

## 10. 附录: 关键文件变更清单

### 后端 (新增/修改)

```
api/src/locale_builder.py          (新建)
api/src/collector.py               (加 build_locale_files 步骤)
api/src/entity_export.py           (加 translation_key 写入)
api/src/lootdrop_builder.py        (加 translation_key 写入)
api/src/module_builder.py          (加 translation_key 写入)
api/src/index_export.py            (加 translation_key 写入)
api/src/config.py                  (加 LOCALE_OUTPUT_DIR)
api/src/db/__init__.py             (保持 get_translations_map(lang))
```

### 前端 (新增/修改)

```
web/package.json                   (+ react-i18next, i18next)
web/src/i18n/I18nProvider.tsx      (新建 — 从路由提取 lang,加载 locale dict)
web/src/i18n/useI18n.ts            (新建)
web/src/i18n/config.ts             (新建 — 语言列表 / 检测逻辑)
web/src/i18n/locales/*.json        (新建, 10 语言 × UI 文案)
web/src/i18n/index.ts              (新建)
web/src/AppInner.tsx               (+ /:lang 前缀路由 + 无前缀重定向)
web/src/ssr.tsx                    (+ lang 参数透传)
web/src/components/NavBar.tsx      (+ 语言切换下拉,导航到 /{lang}/当前路径)
web/src/pages/DetailPage.tsx       (title 从 SSG locale dict 注入)
web/src/pages/LootdropDetailPage.tsx (同上)
web/src/pages/DungeonModuleDetailPage.tsx (同上)
web/src/pages/QuestNPCDetailPage.tsx (同上)
web/src/pages/QuestItemGroupPage.tsx (group 名保留现状)
web/src/pages/ListPage.tsx         (列表页标题同步)
web/scripts/ssg.mjs                (新增后处理阶段 — 文本替换 `<title>` + 注入 lang/hreflang)
web/vite.config.ts                 (+ workbox locale 缓存, df5-html maxEntries 保持 1300)
```

---

## 11. 确认执行

> **本文档为计划草案,尚未执行任何代码变更。**
> 请核对后回复 **"确认执行"**,我将按上述里程碑分阶段落地。
> 如需调整 (例如先不做 UI 文案、改键策略、或保留 translation_EN),请直接在文档上标注或告知。
