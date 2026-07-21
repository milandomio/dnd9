# 2026-07-22 会话修改记录

## ShipGraveyard_BladehandRefuge 旋转值修复
- **原因**：`ShipGraveyard_BladehandRefuge` 无 DungeonModule JSON 文件，通过 `extra_rows` 分支插入 DB 时旋转值硬编码为 270，而布局文件计算值为 0
- **变更文件**：`api/src/db/importers/modules.py`
- **关键逻辑**：`extra_rows.append` 第 9 个参数从 `270` 改为 `module_rotations.get(base_name, 270)`，使无 DungeonModule 文件的模块也能从布局文件中获取正确的旋转值
- **验证结果**：DB 中 `rotation` 从 `270.0` → `0.0`，`dungeon_modules.json` 中 `rotate` 同步为 `0.0`

## SW 更新检测修复
- **原因**：原有 `workbox-window` 库未安装导致动态 import 失败被 `.catch()` 吞掉 + `autoUpdate` 使 SW 跳过 waiting 状态，页面无法感知 SW 更新
- **变更文件**：`web/vite.config.ts`、`web/src/components/SWUpdateBanner.tsx`
- **关键逻辑**：
  - `registerType: 'autoUpdate'` → `'prompt'`：新 SW 安装后进入 waiting 状态等待用户确认，不再自动 skipWaiting
  - `SWUpdateBanner.tsx` 重写为原生 `navigator.serviceWorker` API（移除未安装的 `workbox-window` 依赖）
  - 监听 `updatefound` → `statechange` = `'installed'` 时弹出 banner（带有 controller 为更新，无 controller 为首次安装）
  - 点击"刷新以应用"→ `postMessage({ type: 'SKIP_WAITING' })` 激活等待中的新 SW
  - `controllerchange` 监听 + `refreshing` 引用防死循环

# 2026-07-18 会话修改记录

## Dungeon Module 页面 SSR 改造

**原因：** `/dungeon_modules/`（列表页）和 `/dungeon_modules/:group/:name`（详情页）是纯 CSR Shell，HTML 中 `<div id="root">` 为空，用户需等 JS 全量下载→执行→fetch 才能看到内容。参照 lootdrop 页面模式加入 SSR。

**变更文件：**
- `web/scripts/ssg.mjs` — 3 处修改
  - `routeDataKey()`: 详情页从 `return ""` 改为 `return \`dungeon_modules_detail/${group}/${name}\``
  - `SINGLE` 循环: 替换 `continue`，注入预计算的分组 summary 到 `ssrDataMap["dungeon_modules"]`
  - 新增 detail SSR 数据填充块: 完整模式注入 `{ module: DungeonModule, coords: ModuleCoordsData }`，quick 模式注入 `{ module: { name, translation }, coords: null }`
- `web/src/pages/DungeonModuleDetailPage.tsx` — SSR 数据消费
  - 添加模块级预加载 `_preloadedCoords`（同 lootdrop 的 `_preloadedLootdrop`）
  - 添加 `useSSRData`，guard 验证 `ssrData?.coords?.entities`
  - `useState` 初始值链: `_preloadedCoords ?? effectiveCoords ?? null`
  - `mod` 增加 SSR fallback: `modFromHook || effectiveModSsr`
  - `useEffect` 中若 SSR 数据齐全则跳过 fetch
- `web/src/pages/DungeonModulesPage.tsx` — SSR 数据消费
  - 添加 `useSSRData("dungeon_modules")`，初始 `groups` 状态使用 SSR 数据
  - `useEffect` 中若 SSR 数据已存在则跳过分组构建

**逻辑/映射关系：**
- 路由数据键：详情页 → `dungeon_modules_detail/:group/:name`（区别于 group 页的 `dungeon_modules/:group`）
- SSR 数据守卫：`ssrData?.coords?.entities`（同 lootdrop 的 `ssrData?.item?.monsters`）
- Quick 模式：`coords: null` → guard 失败 → 自动降级 CSR
- 列表页数据结构：`[{ group, group_display, module_count }, ...]`（8 个分组）
- 详情页 coords 数据：完整模式下 ~100KB 内联，含 37 个实体坐标

## /items 页面只显示地面掉落物

**原因：** 用户要求物品列表页只展示地面掉落物（从地面直接拾取的物品），从箱子或怪物爆出的物品应归类到掉落表（/lootdrops）。

**变更文件：**
- `api/src/entity_export.py:42-46` — 在 `export_items()` 中添加过滤逻辑

**逻辑/映射关系：**
- 保留条件：`monsters` 列表包含 `"Ground"`（地面掉落物）或 `monsters` 为空（装饰/任务物品）
- 排除条件：`monsters` 列表存在但不含 `"Ground"`（仅从怪物/箱子产出）
- 效果：items 从 517 降为 96 个物品
- 被排除的物品仍可在 /lootdrops 页面按怪物/箱子查询

## 超级金堆命名神器爆率计算验证

**验证结论：** 计算正确，`0.0018%` 即 `5/28/10000`。

**爆率公式：** `pool_weight / shared_count / rate_total`
- `pool_weight` = 该 luck_grade 的权重
- `shared_count` = 同 luck_grade 的物品数
- `rate_total` = 所有 luck_grade 正权重之和

**超级金堆 Inferno Lv1 (`ID_Droprate_Hoard_WeaponArmor_3001`)：**
| LuckGrade | 权重 | 物品数 | 说明 |
|:---:|---:|---:|---|
| 5 (魔法) | 7190 | 191 | 白色/蓝色武器 |
| 6 (稀有) | 2500 | 0 | 无 LG6 物品，权重闲置 |
| 7 (史诗) | 305 | 0 | 无 LG7 物品，权重闲置 |
| 8 (神器) | 5 | **28** | 28 件命名神器平分 LG8 权重 |

**关键点：**
- `5/10000 = 0.05%` — 超级金堆产出**任意**神器的概率
- `5/28/10000 = 0.0018%` — 超级金堆产出**某件特定**神器的概率
- 游戏机制：先按权重 roll 运气等级，再在同级内均匀随机挑选
- LG6(2500) 和 LG7(305) 无对应物品，相关权重闲置不参与分配

# 2026-07-17 会话修改记录

## 诊断：ShipGraveyard_BladehandRefuge 模块翻译丢失原因

**原因：** `ShipGraveyard_BladehandRefuge` 没有对应的 DungeonModule JSON 文件（`Data/Generated/V2/Dungeon/DungeonModule/` 下不存在），仅作为地图文件存在（`Maps/.../ShipGraveyard_BladehandRefuge_A.json`）。`ModulesImporter` 通过 `_build_path_group_map()` 将其添加为"extra row"，但：
- `translation_key` = `""`（没有源 DungeonModule JSON 继承 Name.Key）
- `sl_base_name` = `""`（没有 SubLevelAsset 引用）
- `NameResolver` 所有翻译策略均失败（无 Game.json key `Text_DesignData_Dungeon_DungeonModule_BladehandRefuge`、无 HARDCODED 条目、模糊匹配无效）

**影响：** 前端显示英文名 `ShipGraveyard_BladehandRefuge`，无中文翻译。

**修复方式：** 在 `config.py` 的 `HARDCODED_TRANSLATIONS` 中添加 `"ShipGraveyard_BladehandRefuge": "刃手避难所"`（沿用 HARDCODED 中 `Bladehand_` 前缀的"刃手"译法），确保第 140 行 `name in HARDCODED_TRANSLATIONS` 命中。

**变更文件：** `api/src/config.py`

## 修复：TearofHrimthurs 不显示爆率

**原因：** spawner keyword `TearofHrithurs` 比物品名 `TearofHrimthurs` 少一个 m，导致 `_spawner_ldg` 无 item_name 映射，enrichment 无法注入 `group_drop_info`。前端 `variant_count > 1` 条件又过滤了非变体物品。

**变更：**
- `api/src/drop_rate.py` — 预加载时从 `lootdrop_rate_items` 反向取 item base name → lootdrop_group_id 映射，处理 keyword 与 item_name 不一致的情况
- `web/src/pages/DetailPage.tsx` — 移除 `variant_count > 1` 条件，有 `group_drop_info` 就显示；variant 仅作爆率分摊和 "(N种选1)" 文字

**关键逻辑：**
- `TearofHrimthurs_5001`(lootdrop_rate_items) → 去后缀 `_5001` → `TearofHrimthurs` → 通过 `_ld_id_to_groups` 关联 `ID_LootdropGroup_TearofHrimthurs`
- 综合爆率：PVE 0.1%, 普通 0.35%, 豪客赛 0.5%, 逆袭赛 0.5%

## 回滚 _8001 变体继承基底怪物列表

- **原因**：`9ef1a483` 修复让 _8001 变体继承基底全量怪物列表，但 RondelDagger 跨越 8 个地图（Inferno/FireDeep/GoblinCave/Ruins/IceAbyss/ShipGraveyard/Crypt/IceCavern），`group_drop_info` 中继承这 8 个地图是正确的行为，无需变更
- **操作**：回滚 `e87446e2` + `9ef1a483`，`api/src/lootdrop_builder.py` 第 160/168 行回到 `loot_map.get(v8001, [])`
- **遗留问题**：ShipGraveyard 参考爆率缺失是前端渲染问题，非数据问题

## SW 图片缓存 maxEntries 250→300

- **原因**：游戏模块图片增加，`api/src/img/` 现已有 255 个 webp，原 250 上限不够用
- **变更文件**：`web/vite.config.ts` — `df5-data-img` 缓存上限 250 → 300

## 新增 PNG→WebP 自动转换流水线

- **原因**：V5 项目原本没有任何 PNG→WebP 转换代码，`api/src/img/` 中的 webp 文件被视为预存静态资产。新增游戏 PNG 时无法自动生成 webp。
- **变更文件**：
  - `api/src/image_utils.py` — 新增，导出 `sync_webp_images()` 和 `compress_and_save_image()`
  - `api/src/collector.py` — 在 JSON 导出阶段前调用 `sync_webp_images()`
- **⚠️ 重要规则**：`api/src/img/` 下的 .webp 文件是**不可再生资源**，禁止删除。这些文件从游戏解包 PNG 转换而来，一旦丢失无法从游戏重新提取。

## 修复 _8001 变体 group_drop_info 缺少参考爆率

- **原因**：`build_merged_loot_map()` 中 `_8001` 变体只使用自己的怪物列表（RondelDagger_8001 仅 3 个怪物），而非继承基底 RondelDagger 的合并全量列表（40 个怪物），导致 ShipGraveyard 参考爆率丢失。
- **变更文件**：
  - `api/src/lootdrop_builder.py` — `build_merged_loot_map()` 中 `_8001` 使用 `merged_loot[base]` 代替 `loot_map.get(v8001, [])`
- **验证**：RondelDagger_8001 group_drop_info.ShipGraveyard 从 1 条（宝藏堆 0%）恢复到 29 条完整参考爆率
- **剩余操作**：见 `docs/FIX_8001_VARIANT_GROUP_DROP_INFO.md`

## 新增 DwarvenLockWay.webp 地图图片

- **原因**：FireDeep 组模块 `DwarvenLockWay`（矮人闸道）的源 PNG 文件存在，但项目中无 PNG→WebP 自动转换流水线，webp 文件缺失，前端始终显示占位图 `RareModule_1x1`
- **操作**：
  - 使用 Pillow 将 `DwarvenLockway.png`（小写 w）转换为 `DwarvenLockway.webp`（quality=85, 50KB）
  - 存入 `api/src/img/DwarvenLockway.webp`
  - 重新运行管道 → `dungeon_modules.json` 中 `img_name` 从 `RareModule_1x1` 变为 `DwarvenLockway`，`has_img=true`
  - 前端构建 + 预览验证通过（HTTP 200, 图片可访问）
- **变更文件**：
  - `api/src/img/DwarvenLockway.webp` — 新增（50218 bytes）
  - `docs/SESSION_CHANGES.md` — 本记录
- **备注**：项目中不存在自动 PNG→WebP 转换机制，新增模块图片需手动转换后放入 `api/src/img/`

## 跨变体 Fallback 爆率 Bug（未修复，已记录暂存）

- **原因**：`compute_drop_rate` 和 `compute_variant_rate` 的 `_base` 跨变体 fallback 允许未注册变体借用同物品其他变体的爆率，产生虚假数据
- **关键发现**：`lootdrop_rate_items` 中仅注册了部分变体（如 `SurgicalKit_4001`、`HeaterShield_5001`/`8001`），其余变体均无直接绑定。fallback 通过 `_base` + `_VARIANT_SUFFIXES` 循环命中错误变体，算出不应存在的爆率
- **变更文件**：
  - `docs/CROSS_VARIANT_FALLBACK_ISSUE.md` — 问题文档（待解决）
- **操作**：回滚到 checkpoint `e7623d8`，恢复原始状态，问题延期处理

## 修复重复请求 + preload URL 对齐 + 空版本跳过

- **原因**：Playwright 网络追踪发现 `/lootdrops/EmberGem/` 页面打开时 `dungeon_modules.json` 被请求 3 次、`search_index.json` 被请求 2 次，页面卡顿约 1 秒。根因：
  1. `useDataVersion()` 初始返回空字符串 `''`，`useEffect` 在 meta.json 加载前就用空版本发起 fetch
  2. meta.json 到达后 `dataVersion` 更新，`cachedVersion !== dataVersion` 清空 in-flight 的 `cachedPromise`，触发第二次 fetch（真正的重复）
  3. preload URL 使用 base36 编码（`/data/{short}/json/`），但 fetch URL 使用原始十进制时间戳 `/data/{dataVersion}/json/` — 总是不匹配，preload 缓存浪费
- **变更文件**：
  - `web/src/hooks/useDungeonModules.ts`
    - `useEffect` 开头加 `if (!dataVersion) return;`，空版本时跳过，等待 meta.json 到达
    - fetch URL 改为 `/data/${Number(version).toString(36)}/json/dungeon_modules.json`，与 preload 的 base36 格式对齐
  - `web/src/hooks/useSearchIndex.ts` — `useEffect` 开头加 `if (!dataVersion) return;`
  - `web/src/pages/ListPage.tsx` — `useEffect` 开头加 `if (!dataVersion) return;`
  - `docs/REFERENCE.md` — 更新详情页 `_modules` 描述为当前共享 Map 架构，新增 preload 策略说明（版本化 URL、AppInner 主动预取、防重复机制）
- **效果验证**（Playwright 实测 localhost:8080）：
  - BEFORE：`dungeon_modules.json` 3 次（preload + 2 fetch，总计 1.1s），`search_index.json` 2 次（629ms）
  - AFTER：`dungeon_modules.json` **1 次**（preload cache hit，20ms），`search_index.json` **1 次**（19ms）
  - 重复请求完全消除，preload 缓存被正确复用

## 移除 fetch+blob 图片加载 + preload meta.json + 延迟 search_index

- **原因**：上一轮修复后 Playwright 追踪仍有三大问题：
  1. 每张模块图片被加载两次（`<img>` 降级 + `fetch`+blob），SW 无法消除首次访问的双重请求
  2. `search_index.json` 在首屏关键路径中 fetch，阻塞内容渲染
  3. `meta.json` 被 ESM 模块评估阻塞，等 JS 下载完才开始请求
- **变更文件**：
  - `web/src/pages/LootdropDetailPage.tsx` — 删除 `scheduleFetch`、`imageUrlsRef`、`controllersRef`、`timersRef` 等整个 fetch+blob+createObjectURL 机制；IntersectionObserver 只控制 `visibleMaps`，MapPanel 直传 `/data/img/*.webp` URL
  - `web/src/components/MapPanel.tsx` — 删除 `imgName` prop 和 `imageSrc || /data/img/...` 回退逻辑；`imageSrc` 改为必填
  - `web/src/pages/DetailPage.tsx` — MapPanel 传 `imageSrc` 直连 URL，去除 `imgName`
  - `web/src/pages/DungeonModuleDetailPage.tsx` — 同上
  - `web/src/pages/QuestItemGroupPage.tsx` — 同上
  - `web/src/hooks/useSearchIndex.ts` — useEffect 中 fetch 包裹 `setTimeout(0)`，让出首屏渲染
  - `web/vite.config.ts` — `inject-versioned-preload` 插件额外注入 `<link rel="preload" href="/data/json/meta.json">`
- **效果验证**（Playwright 实测 localhost:8080）：
  - meta.json 开始时间从 **+2689ms → +69ms**（提前 ~2.6s）
  - EmberGem.json 开始从 **+2857ms → +1266ms**（提前 ~1.6s）
  - 图片每张 **2 次 → 1 次**，无重复
  - 全页面总耗时从 **~4.6s → ~1.6s**（-3s）
  - 用户感知的"数据加载中→内容出现"从 ~2.8s 降到 ~1.2s

## 模块级数据预加载 — 消除详情页首条数据 fetch 的串行等待

### 原因

Chrome DevTools 网络面板追踪 `/lootdrops/GoldenKey/` 发现首条数据 fetch 到 +1041ms 才启动：

```
+0ms     HTML 到达 (18ms TTFB)
+38ms    meta.json / dungeon_modules.json preload 完成
+44ms    JS bundle 开始下载 (antd 415KB + react 180KB + index 119KB)
+130ms   JS 下载完毕
+130~400ms  浏览器解析 JS (~270ms，含 ESM 模块求值)
+400~1041ms React hydrateRoot 执行 (~640ms，含组件树对齐 SSR + Ant Design 复杂 DOM)
+1041ms  useEffect 中 fetch 启动
+1059ms  fetch 完成 (18ms，SW 缓存命中)
```

核心问题：**数据 fetch 被 React 水合串行阻塞**。虽然 `meta.json` 在模块级 fetch（ESM 求值时发起，数据在 hydration 前已就绪），但详情页的实体数据 fetch 放在 `useEffect` 里，必须等 React 水合完 → 组件 mount → effect 调度 → 才发出请求。这导致：

1. **无用串行等待**：数据请求不需要 `dataVersion`（URL 不含版本号），却放在 `useEffect` 里等组件 mount
2. **缓存利用不足**：SW 已经缓存了数据，但请求发得晚，缓存命中的 18ms 也被串行在后
3. **首次渲染缺数据**：`useState(null)` 先渲染空状态 → fetch 完成 → `setData` 再渲染；两次渲染浪费 CPU

### 方案

在 **ESM 模块求值阶段**（JS 解析时，比 hydrateRoot 早 ~300ms）就直接解析 URL 发起数据 fetch，结果存模块级变量。组件从模块级变量读取数据作为 `useState` 初始值，`useEffect` 只作为导航切换的兜底。

```
BEFORE (串行):
  ESM求值 → JS执行 → hydrateRoot → 组件mount → useEffect → fetch → setData → 渲染
                                                       └── wait 1041ms ──┘

AFTER (并行):
  ESM求值 → fetch ─┬─ 完成 ────┐
                    │           ↓
  JS执行 → hydrateRoot → 组件mount → useState(预加载数据) → 渲染
                                    └── useEffect: 命中跳过
```

### 变更文件

#### `web/src/pages/LootdropDetailPage.tsx`

**① 模块级变量 + 预加载 fetch**（行 70–83，组件函数之前）

```ts
let _preloadedLootdropUrl = '';
let _preloadedLootdrop: LootdropItem | null = null;
if (typeof window !== 'undefined') {
  const _m = window.location.pathname.match(/^\/lootdrops\/([^/]+)/);
  if (_m) {
    _preloadedLootdropUrl = `/data/json/lootdrops/${_m[1]}.json`;
    fetch(_preloadedLootdropUrl)
      .then((r) => r.json())
      .then((d) => { _preloadedLootdrop = d as LootdropItem; })
      .catch(() => {});
  }
}
```

- `typeof window !== 'undefined'`：SSR 构建时跳过（Node.js 无 window）
- URL 从 `location.pathname` 提取，与 React Router 的 `useParams` 同步
- fetch 结果异步写入 `_preloadedLootdrop`，组件 mount 时可能已就绪

**② useState 初始值优先使用预加载数据**（行 140–143）

```ts
const [data, setData] = useState<LootdropItem | null>(
  _preloadedLootdrop ??
    (effectiveSsrData?.item?.monsters ? effectiveSsrData.item : null)
);
```

数据优先级：**模块预加载 > SSR 内联数据 > null**

**③ useEffect URL 对齐检查 + 移除 dataVersion 依赖**（行 194–219）

```ts
useEffect(() => {
  if (!baseName) return;
  if (effectiveSsrData?.item?.monsters) { ... return; }
  const fetchName = currentSuffix && !isArtifact
    ? `${baseName}_${currentSuffix}` : baseName;
  const lootUrl = `/data/json/lootdrops/${fetchName}.json`;
  if (_preloadedLootdrop?.monsters && _preloadedLootdropUrl === lootUrl) return;
  if (lootFetchedRef.current) return;
  lootFetchedRef.current = true;
  // ...fallback fetch...
}, [baseName, currentSuffix, effectiveSsrData]); // ← 移除 dataVersion
```

关键变更：
- **`_preloadedLootdropUrl === lootUrl`**：精确比对预加载 URL 和当前组件需要的 URL，防止导航切换后误用旧预加载数据跳过新 fetch
- **移除 `dataVersion` 依赖**：因为 URL 不含版本号，不需要等 meta.json 信号
- **不变**：`lootFetchedRef.current` 兜底机制保留，导航切换时 `name` 的 effect 重置该 flag，确保新页面走 fallback fetch

#### `web/src/pages/DetailPage.tsx`

**① 模块级预加载**（行 30–45）

```ts
let _preloadedEntityUrl = '';
let _preloadedEntity: Entity | null = null;
if (typeof window !== 'undefined') {
  const _m = window.location.pathname.match(/^\/(items|monsters|props)\/([^/]+)/);
  if (_m) {
    _preloadedEntityUrl = `/data/json/${_m[1]}/${_m[2]}.json`;
    fetch(_preloadedEntityUrl)
      .then((r) => r.json())
      .then((d) => { _preloadedEntity = d as Entity; })
      .catch(() => {});
  }
}
```

正则 `/(items|monsters|props)/:name` 覆盖所有实体详情页。

**② useState + useEffect** 与 LootdropDetailPage 相同模式：

- `useState` 初始值：`_preloadedEntity ?? (ssrData?.entity?.coords ? ssrData.entity : null)`
- `useEffect` 开头：`if (_preloadedEntity?.coords && _preloadedEntityUrl === url) return;`
- `useEffect` deps：移除 `dataVersion`，改为 `[page, name, ssrData]`
- **删除 `useDataVersion()` 调用**（已无引用，`dataVersion` 在 DetailPage 无其他用途）

### 正确性保证

| 场景 | 预加载行为 | 预期结果 |
|------|-----------|---------|
| 首次加载（SSG 页面） | 模块级 fetch 在 hydration 前发起，可能已返回 | useState 带数据，useEffect 命中跳过 |
| 导航切换（同页不同 name） | 模块级变量未更新（ESM cache），URL 比对不匹配 | useEffect fallback fetch 接手 |
| SSR data 已注入（Quick mode 有数据） | 预加载数据覆盖 SSR（优先级更高） | ✅ 数据正确 |
| 预加载失败（网络错误） | `_preloadedLootdrop` 保持 null | useEffect fallback fetch 兜底 |
| 变体跳转（`/lootdrops/GoldenKey/` → `GoldenKey_5001/`） | 初始预加载 `GoldenKey.json` 与跳转后 `GoldenKey_5001.json` URL 不匹配 | fallback fetch 获取变体数据 |

### 效果

- 数据 fetch 从 +1041ms → **约 +200ms（ESM 求值阶段）**，提前 ~840ms 发起
- 首次渲染带数据（`useState` 预填充），减少一次因 `setData` 触发的重渲染
- 与 React 水合并行，消除无用的串行等待
- 剩余 ~800ms 瓶颈为 JS 解析 + React 水合 CPU 时间，属架构限制（Quick mode SSG）

## Decimal-化 spawners.py 生成概率浮点除法

- **原因**：lootdrops/SkullKey 页 CofferSmall(迷你宝盒组) spawn_rate=3.0001 应 3.0，根因是 ChestMedium spawner 中 ∑SpawnRate=999960（非 100万），`100*30000/999960` 产生 3.00012% 尾数
- **变更文件**：`api/src/db/importers/spawners.py`
  - 添加 `from decimal import Decimal` 导入
  - 三处除法 `100*raw_rate/X` 全部改用 `Decimal(str(100*raw_rate))/Decimal(str(X))` 后转 float，消除中间浮点精度损失
  - 排序：lint-fix 自动调整 import 顺序 + black 格式化
- **现状**：3.0001 仍存在（因游戏数据 SimpleChestSmall SpawnRate=519960 而非 520000 导致 pool=999960），但当游戏数据分母为整万时 Decimal 化会确保结果精确

# 2026-07-16 会话修改记录

## computeModuleScore 变体组综合爆率改用 selected_count / variant_count

- **原因**：骷髅双手剑士在沼泽等的综合爆率计算中，变体组（如 3种选1）贡献错误地加了完整 baseScore，应为 baseScore × 组内点数 / 变体总数
- **公式**：变体组贡献 = baseScore × count_in_group / variant_count（count_in_group 为同 group_parent 的坐标点数）
- **变更文件**：`web/src/pages/LootdropDetailPage.tsx` 的 `computeModuleScore()` 函数
  - `varGroups` 记录从 `{ translation }` 改为 `{ translation, count, vc }`
  - 遍历 dots 时递增 `existing.count` 而非去重后置 1
  - 最终累加时：`Math.round(baseScore)` → `Math.round(baseScore * g.count / g.vc)`

## 分类按钮数字 + 底部统计同步 hideZeroRate 过滤；抽离 LocationStats 组件

- **原因**：按钮数字（1080→163）在按钮熄灭时未更新（回退 `m.coords.length`）；底部"包含地图"列表未过滤已隐藏坐标
- **变更文件**：
  - `web/src/components/LocationStats.tsx` — 新建（共享底部统计行组件）
  - `web/src/pages/LootdropDetailPage.tsx` — `visibleCountByMonster` 从 `resolvedMonsters` 直接计算（不排除 hidden），按钮始终显示过滤数；底部用 `bottomCount`/`visibleMapsSet`（hidden + hideZeroRate 双重过滤）替换旧 `totalCoords`/`mapGroups.keys()`
  - `web/src/pages/DetailPage.tsx` — 底部统计同步覆盖 hideZeroRate 过滤；使用 LocationStats

## 坐标计数同步 hideZeroRate 过滤：迷你宝盒组 1080 不再显示错误数字

- **原因**：`hideZeroRate` 过滤后，怪物切换按钮和底部统计仍显示原始未过滤的坐标总数（如迷你宝盒组 1080），未反映过滤后的实际可见坐标数
- **变更文件**：`web/src/pages/LootdropDetailPage.tsx`
- **变更逻辑**：新增 `visibleCountByMonster` 遍历 `sortedGroups` 同步应用 `hideZeroRate`/`modeFilter` 过滤逻辑，统计每个怪物翻译的实际可见坐标数；`filteredTotalCoords` 汇总为底部统计总数；切换按钮和 `Helmet` meta 描述均使用过滤后的数字
- **注意**：此功能是核心筛选机制，除非用户要求否则不能移除

## 零爆率坐标过滤修复：modeFilter=全部时检测所有模式

- **原因**：`hideZeroRate` 在 `modeFilter=""`（全部）时跳过过滤，导致 OldRustyKey 等全模式爆率为 0 的坐标/地图分组错误显示
- **变更文件**：`web/src/pages/LootdropDetailPage.tsx`、`web/src/pages/DetailPage.tsx`
- **核心逻辑**：新增 `hasAnyRate()` 辅助函数；当 `hideZeroRate=true` 且 `modeFilter=""` 时，检查 `drop_rates` 中 PVE/普通/豪客赛/逆袭赛 是否任一 > 0，全 0 才隐藏。选中具体模式时保持原行为（只检查该模式）
- **效果**：Billet（PVE=65%、豪客赛=0%）选"全部"时 AshTree 坐标保留；OldRustyKey 沉船墓场1层（全模式=0%）在"全部"时也被隐藏

## PWA 图标内容改为 "DND" + 去掉白色边框 + iPhone 风格圆角

- **原因**：原图标仅显示字母"D"，用户要求改为"DND"；边缘有白色半透明环状边框需移除
- **变更**：`web/public/icons/icon-192-v2.png`、`web/public/icons/icon-512-v2.png` — 内容从蓝色字母"D"改为粗体"DND"（DejaVuSans-Bold，字号 ≈ 尺寸 × 30%，RGB(200,220,255)）；移除白色边框像素；应用 iPhone 风格 squircle 圆角（半径 ≈ 尺寸 × 22%）
- **变更文件**：
  - `web/public/icons/icon-192-v2.png`
  - `web/public/icons/icon-512-v2.png`
  - `web/public/favicon.ico` — 同步更新为 "DND" 图标（含 16/32/48/64 多尺寸）

# 2026-07-15 会话修改记录

## 稀有掉落阈值调整 2.5→1.5 + 零豪客赛掉落显示修复

- **原因**：用户反馈列表页「稀有掉落」分组过严（2.5 阈值），且 Billet（小木块）等只有 PVE 爆率的掉落详情页无数据
- **阈值修改**：`web/src/pages/ListPage.tsx:57` 列表页稀有掉落分组阈值 2.5 → 1.5
- **零豪客赛修复**：`api/src/lootdrop_builder.py:525-548` 移除对 `豪客赛=0` 条目的过滤。原逻辑只保留豪客赛爆率 > 0 的怪物，但 Billet（木材掉落）的 AshTree 在 PVE 模式有爆率（65%）而豪客赛权重为 0，导致所有怪物被过滤、JSON 文件未生成。修改后所有有坐标的怪物均保留
- **变更文件**：
  - `web/src/pages/ListPage.tsx` — `2.5 → 1.5`
  - `web/src/pages/LootdropDetailPage.tsx` — 阈值回滚（用户要求只改列表页）

### 小型神器分类恢复

- **原因**：提交 `0f29744` 修复水合错误时重构 `groupLootdrops()`，无意中移除了 `hr100`（小型神器）分类逻辑。后端一直正常生成 `hr100` 标记，仅前端不消费
- **变更**：`web/src/pages/ListPage.tsx` — `IndexEntry` 补回 `hr100?: boolean` 类型定义，`groupLootdrops()` 恢复 `hr100` 数组、分类判断、和"🪙 小型神器"分组

### 提交 0f29744 误删功能批量恢复

- **原因**：审计发现提交 `0f29744` 在删 `dataUrl` 导入时，同一文件中的不相关代码被整体回退到旧版本
- **恢复内容**：
  - 阈值 2.5 → 1.0（用户要求 1.0）
  - `NavBar.tsx` search bar 恢复 `scrollIntoView` 自动滚动到搜索框
  - `NavBar.tsx` 搜索框宽度恢复 `flex: 0 0 360px`（被改为 `flex: 1 1 280px`）
  - 删除死代码 `web/src/utils/dataUrl.ts`（无人引用的残留文件）

### 列表页数据源统一 + search_index 补 hr100

- **原因**：列表页有两个数据源——SSR 用 `{page}.json`、运行时用 `search_index.json`，加 `hr100` 时只改了前者，导致客户端导航无小型神器分组。详情页只有一个数据源没有此问题
- **变更**：
  - `api/src/index_export.py:264` — `search_index` 的 lootdrop 条目补上 `hr100` 字段
  - `web/scripts/ssg.mjs:149` — 列表页 SSR 数据改为从 `search_index.json` 提取（过滤 `page`），不再读 `{page}.json`，消除两套数据源不一致的隐患

## 掉落详情页 spawn_rate 修正：使用原始生成器关键词 + 允许 0 值入缓存

- **原因**：用户反馈 `WanderlightLantern` 掉落页面中「中型诡污(特殊)」显示 100% 生成概率，实际应为 0%（该实体在 ChestLarge 中的权值为 0）。错误地使用了容器实体（ChestLarge=100%）的生成概率
- **根因**：
  1. `lootdrop_builder.py:414-416` 在 `keyword != original_keyword` 时使用 `_c["keyword"]`（如 "Mimic_Medium_MidLevel"）查 `spawn_rate_detail`，但 `spawner_entries` 表的 key 是 `original_keyword`（如 "ChestLarge"），导致查不到时返回默认值 100
  2. `drop_rate.py:155,161,164` 中缓存条件 `sr > 0` 排除了 spawn_rate=0.0 的合法值，该条目根本未入缓存
- **变更**：
  - `api/src/lootdrop_builder.py:415` — 查 `spawn_rate_detail` 时用 `original_keyword` 替代 `keyword`
  - `api/src/lootdrop_builder.py:416,418` — `.get()` 默认值 100 → 0
  - `api/src/drop_rate.py:155,161` — `spawn_rate_cache` 条件 `sr > 0` → `sr > -1`（允许 0 值存储）
  - `api/src/drop_rate.py:164` — `spawn_rate_detail` 条件 `sr > 0` → `sr > -1`（允许 0 值存储）
- **验证**：WanderlightLantern 掉落详情中「中型诡污(特殊)」spawn_rate 100% → 0.0%，「巨型诡污(特殊)」保持 0.01%

## spawn_rate 精度 2→4 位 + 公式 100 前置

- **原因**：`round(40/1000040*100, 2)` = 0.0，0.004%被吞掉。文档要求 4 位精度但实际代码用 `round(x, 2)`
- **变更**：
  - `api/src/db/importers/spawners.py` — `round(x, 2)` → `_round_rate(x)`，公式 `x/总池*100` → `100*x/总池`
  - `api/src/search_engine.py` — 同上
  - `docs/REFERENCE.md:264` — 更新公式示例
- **验证**：ChestLarge 中 Unique 宝箱怪 `40/1000040*100` 从 0.0 → 0.004%
  - `api/src/lootdrop_builder.py` — 移除豪客赛=0 过滤

## 彻底修复 React #418/#423 hydration 错误（全站 1235 页面 0 错误）

- **原因**：React 18 `hydrateRoot` 对无 SSR 内容的空容器会导致双重渲染（hydration → CSR fallback），期间模块级 `meta.json` fetch 可能完成并突变 `cachedDate`，造成 hook 数量不匹配。受影响页面为所有无 SSR 渲染的页面（`dungeon_modules` 列表页 + 详情页，共 244 个）。
- **变更文件**：`web/src/main.tsx`
- **改动**：检查 `root.hasChildNodes()` — 有 SSR 内容时用 `hydrateRoot`，无 SSR 内容时用 `createRoot` 避免 hydration 失败
- **验证**：Playwright 全站 1235 页测试，0 个 #418/#423 错误；剩余的 `Timeout` 是测试 100 并发造成的性能问题，非应用错误

## OfflineDetector SSR 不匹配修复

- **原因**：OfflineDetector 在 SSR 时 `useState(typeof navigator !== 'undefined' && !navigator.onLine)` 返回 `false`，但客户端 hydrate 时 `navigator.onLine` 为 `true`，导致返回 `null`，引发 #418
- **变更文件**：`web/src/components/OfflineDetector.tsx`
- **改动**：`useState(false)` 固定初始值，`useEffect` 在客户端才设置正确状态

## 数据版本预加载修复 + Playwright 调试文档

- **原因**：SSG 构建时序问题 — 版本号在 Vite 构建后才计算，导致 `VITE_DATA_VERSION` 为空
- **变更文件**：`web/scripts/ssg.mjs`、`web/vite.config.ts`
- **改动**：版本号计算移至构建前（step 0），`process.env.VITE_DATA_VERSION` 提前设置
- **文档**：新增 `docs/DEBUG_HYDRATION_WITH_PLAYWRIGHT.md`（调试指南）

# 2026-07-14 会话修改记录

## fix: variant 详情页综合爆率使用 variant_gdi 重算

- **原因**：variant 详情页（如 LargeScroll_7001）的 `coords[].score` 继承自 base 物品的 `_hk_lookup`（`get_group_drop_rates`），而 `group_drop_info` 用 `get_variant_group_drop_rates(luck_grade=7)` 计算，两者不一致。表现为 group_drop_info 显示 0.1111% 但综合爆率显示 2.4815%。
- **变更文件**：`api/src/lootdrop_builder.py` — variant 分支新增 per-coord score 从 `variant_gdi` 重算
- **关键映射**：variant 分支的 `coords[].score` 现在用 variant_gdi 的 `豪客赛` 值重算，score = `spawn_rate * 豪客赛 / 100`，与 group_drop_info 对齐

## 新增"小型神器"分类 — 豪客赛 100% 爆率 + 低生成率装备

- **原因**：用户需要从掉落表页面快速筛选豪客赛模式下必定掉落但生成率低的稀有装备
- **筛选条件**：`drop_rates.豪客赛 >= 100`（怪物必定掉落）AND `spawn_rate < 5`（生成率低于 5%）
- **变更文件**：
  - `api/src/lootdrop_builder.py` — 构建索引时扫描 `group_drop_info` 中两个条件同时满足的条目，标记 `hr100: true` 写入 `lootdrops.json`
  - `web/src/pages/ListPage.tsx` — `groupLootdrops()` 增加 `hr100` 分类逻辑，新增"🪙 小型神器"分类（位于"🏺 神器"之后）
- **数据流**：后端管道计算 → lootdrops.json 索引含 `hr100` 字段 → 前端 CSR 加载后按分类渲染
- **共 7 个物品**被标记：吸血之刃、迷乱之刃、荆棘之盾、缠丝长裤、静谧长靴、流光灯笼、盗法者权杖

## 导航栏搜索框点击放大镜后滚动到可视区域

- **原因**：手机端任务详情页底部点击放大镜搜索后，`inputRef.current?.focus()` 不会自动滚动页面，用户看不到搜索框被填充
- **变更文件**：`web/src/components/NavBar.tsx:79-85`
- **改动**：`NavBar.useEffect`（消费 `searchQuery`）中在 `focus()` 后添加 `scrollIntoView({ behavior: 'smooth', block: 'center' })`

## 导航栏搜索框宽度改为 8 字符

- **原因**：搜索框默认 `flex: 1 1 280px` 过长，经尝试后改为 `flex: 0 0 360px`
- **变更文件**：`web/src/components/NavBar.tsx:208`

## 修复 apple-touch-icon 指向旧图标

- **原因**：`index.html` 中 `<link rel="apple-touch-icon">` 仍指向 `/icons/icon-192.png`（旧版无圆角），iOS 添加到主屏幕时显示方形图标
- **修复**：改为 `/icons/icon-192-v2.png`（圆角版）
- **变更文件**：`web/index.html:12`

## 修复 webp 图片在 iOS 14 不显示

- **原因**：上次修复只改了 `MapPanel.tsx` 的 `aspect-ratio` → `paddingBottom`，但 `DungeonModuleGroupPage.tsx` 和 `ExplorePage.tsx` 仍直接使用 CSS `aspect-ratio` 属性。iOS Safari < 15 不支持 `aspect-ratio`，div 高度为 0 → `backgroundImage` 不可见
- **修复**：两个页面改为 `paddingBottom` 占位 + `position: absolute` 内层 div 渲染背景图（与 MapPanel 相同模式）
- **变更文件**：
  - `web/src/pages/DungeonModuleGroupPage.tsx:172` — 模块卡片缩略图
  - `web/src/pages/ExplorePage.tsx:157` — 探索页模块缩略图

## 移动端排版换行修复

- **原因**：手机屏幕窄，多处 flex 容器未设置 `flexWrap: 'wrap'`，导致内容溢出或强制同行显示
- **变更文件**：
  - `web/src/components/NavBar.tsx` — 导航栏容器 + 右侧按钮区加 `flexWrap: 'wrap'`，搜索框 `flex: '1 1 280px'`
  - `web/src/pages/DetailPage.tsx` — "参考爆率" 容器 + 变体图例内层 flex 加 `flexWrap: 'wrap'`
  - `web/src/pages/LootdropDetailPage.tsx` — "参考爆率" 容器 + 怪物图例内层 flex 加 `flexWrap: 'wrap'`
  - `web/src/pages/QuestNPCPage.tsx` — 搜索框包装为 `width: 100%` 独立一行；NPC 卡片名+任务数改用 `display: flex; flexWrap: wrap`
  - `web/src/pages/QuestNPCDetailPage.tsx` — 搜索框 `width: 100%` 独立一行；h1 标题加 `flexWrap: 'wrap'`

## 修复 SW runtime caching urlPattern 正则不匹配问题

- **原因**：`vite.config.ts` 中 Workbox runtime caching 的 `urlPattern` 使用了 `^` 锚定正则（`/^\/data\/json\//`），Workbox 用 `regex.test(request.url)` 匹配完整 URL（含协议/域名），导致 `df5-data-json` 和 `df5-data-img` 缓存池**永远不会被写入**
- **后果**：离线时 HTML（NetworkFirst）可正常加载，但数据 JSON fetch 全部失败 → 详情页显示"数据加载中"
- **修复**：改为函数式 `({ url }) => url.pathname.startsWith(...)` 匹配 pathname
- **变更文件**：`web/vite.config.ts`（data-json、data-img、meta 三个缓存规则）

## 站点描述全面更新

- **原因：** 原描述"游戏数据导航"不够明确，用户要求改为功能标签式描述
- **新描述：** `游戏地图·任务攻略·BOSS掉落·资源点位·寻找宝箱`
- **变更文件：**
  - `web/vite.config.ts` — manifest.description
  - `web/src/pages/HomePage.tsx` — title/meta description/heading 标签栏
  - `web/src/pages/ListPage.tsx` — title
  - `web/src/pages/DetailPage.tsx` — title/og:title
  - `web/src/pages/LootdropDetailPage.tsx` — title/og:title
  - `web/src/pages/DungeonModulesPage.tsx` — title
  - `web/src/pages/DungeonModuleGroupPage.tsx` — title
  - `web/src/pages/DungeonModuleDetailPage.tsx` — title
  - `web/src/pages/QuestItemsPage.tsx` — title
  - `web/src/pages/QuestItemGroupPage.tsx` — title
  - `web/src/pages/QuestNPCPage.tsx` — title
  - `web/src/pages/QuestNPCDetailPage.tsx` — title
  - `web/src/pages/ExplorePage.tsx` — title
- **bili.bi/map 对比：** 该站是多游戏地图导航门户（链接到采蘑菇/游民星空等第三方地图），我们聚焦 Dark and Darker 单一游戏，功能标签已覆盖其核心维度

## PWA 图标优化

- **原因：** PWA 图标上 "dnd" 文字过大，小尺寸看不清；新版图标缺少圆角
- **变更文件：**
  - `web/public/icons/icon-192-v2.png` — 新图标（文字缩小，增加蓝光效果，圆角矩形）
  - `web/public/icons/icon-512-v2.png` — 新图标（同上）
  - `web/public/favicon.ico` — 同步更新
  - `web/vite.config.ts` — manifest 图标引用改为 `-v2` 版本
- **缓存策略：** 文件名带 `v2` 后缀绕过浏览器/OS 图标缓存

# 2026-07-12 会话修改记录

## 性能优化

### lootdrops 模块优化（85s → 28s，省 67%）

| 优化                       | commit    | 效果             |
| -------------------------- | --------- | ---------------- |
| compact JSON               | `4109ee1` | 省 15s           |
| fuzzy candidate_ids 匹配   | `764acc7` | 省 1s            |
| 移除 variant_suffixes 冗余 | `ec15e98` | 省 44s           |
| 修复 variant 后缀计算      | `3be3910` | 恢复正确后缀     |
| 修复 _8001 变体显示        | `e2f3e6a` | 恢复神器变体切换 |

### 其他优化

- `drop_rate.py`: 添加 `_get_candidate_ids` 缓存
- `drop_rate.py`: 添加 fuzzy matching（FakeDeath/FromFakeDeath 后缀）

## Bug 修复

### 坐标标签翻译问题

- **commit**: `858cc54`
- **问题**: 坐标标签被 HARDCODED_TRANSLATIONS 翻译为中文（如 "ChestMedium" → "中宝箱"）
- **修复**: `build_coord_out` 中移除翻译，直接使用 `original_keyword`

### 双下划线变体分类

- **commit**: `f137cd5`
- **问题**: `GoldChest__UnderSea`（双下划线）被错误分类为 "other" 类型，添加 "组" 后缀
- **修复**: `_classify_label` 中将 `__` 视为 `_` 进行匹配

### 神器变体切换

- **commit**: `6a89a1b`, `e2f3e6a`
- **问题**: `_8001` 物品没有变体切换按钮
- **修复**: 包含 8001 在 variant_rarity 中，所有变体页面显示完整 8 个按钮

### 变体后缀计算

- **commit**: `3be3910`
- **问题**: 移除 variant_suffixes 后，后缀计算从 1001 开始，但部分物品从 3001 开始
- **修复**: 使用 `raw_name` 中的数字作为起始后缀

### lootdrop 列表页变体前缀

- **commit**: `98265d2`
- **问题**: 列表页显示 "[8变体]" 前缀
- **修复**: 移除变体数量显示

## UI/SEO 改进

### 站名改名

- **commit**: `066194b`
- **修改**: DarkFindV5游戏导航 → 越来越黑暗光速指南 DarkFlashNav

### 标题样式

- **commit**: `453e5c2`, `01fd9f3`
- **修改**: 中文名 26px，DarkFlashNav 16px，分两行显示

### SEO 关键词

- **commit**: `2da772a`, `52d9a2f`
- **关键词**: 越来越黑暗, 越来越黑暗玩家指南, 越来越黑暗光速指南, DarkFlashNav, Dark and Darker, 暗黑地牢, ...

## 2026-07-13 会话修改记录

### 多实体刷怪器坐标误扩展修复

- **commit**: `dfffe3d`
- **问题**: GoblinWarrior 的 DCSpawnerDataAsset 包含 LavaGolem_Nightmare 条目，`load_all_spawner_data` 剥离后缀后得到 2 个不同实体名（GoblinWarrior、LavaGolem），触发多实体展开。所有 GoblinWarrior 地图刷怪点都生成了 keyword="LavaGolem" 的坐标，导致 LavaGolem 页面多了 104 个虚假坐标
- **修复**: `search_engine.py:extract_spawners` 中，展开前判断 spawner 基名是否匹配任一实体基名。若匹配，只保留基名一致的实体；若不匹配（如 Random/Special 生成器），保留全部
- **效果**: LavaGolem 坐标从 105 降为 1（真实坐标）；GoblinMelee_Random、ChestSpecial 等不受影响

### lootdrop score 未乘实体生成概率修复

- **commit**: `7703899`
- **问题**: `lootdrop_builder.py:556` 中 per-coord score 使用 `coord.spawn_rate`（未命中 cache 时默认回退 100），未使用实体级 `entity.spawn_rate`。如迷你宝盒组 group_drop_info 中 spawn_rate=3.0，但每个 coord score = 100×25/100=25.0，模块合计 512.5%。实际应为 3.0×25/100=0.75 per coord
- **修复**: 新增 `_sr_lookup` 从 `_group_drop_info` 提取实体级 spawn_rate，score 公式改为 `entity_spawn_rate × 豪客赛 / 100`
- **效果**: 迷你宝盒组 per-coord score 从 25.0 → 0.75，模块合计 ≈15.375%（512.5%×3%）

### 文案修正

- **commit**: `7703899`, `a5afb3e`
- **问题**: 模块卡片显示"单点综合爆率"，应为"综合爆率"
- **修复**: `LootdropDetailPage.tsx:1359` 模块卡片 + `:844` 调试面板标签，去掉了"单点"前缀

## 待处理问题

### 黄金宝箱(特殊) 缺失

- **问题**: "黄金宝箱(特殊)" 在 group_drop_info 中但不在 monsters 列表中
- **当前状态**: 未修复
- **根因**: ChestSpecial_UnderSea 生成器的坐标没有正确关联

### 容器生成器子分类

- **问题**: 容器生成器（如 ChestSpecial_UnderSea）的子分类按钮（如 "黄金宝箱(特殊)"）没有对应的实体详情页
- **当前状态**: 未修复
- **计划**: 在 `docs/PLAN_CONTAINER_GENERATOR_ENTITIES.md` 中记录

## 2026-07-14 会话修改记录（2）

### 重构：完全移除内联 `_modules`，统一走 `dungeon_modules.json`

**问题**：`_modules` 包含全部模块字段（rotate/offset/size/group/img_name/sl_base_name），与 `dungeon_modules.json` 完全重复。上次只去掉了翻译字段，剩余字段仍是冗余。

**方案**：

1. `build_coord_out` 通过 `map_to_module` 将 coords 的 `map` 字段解析为模块名，前端直接 `globalModules.get(c.map)` 查模块数据
2. 后端 `_build_inline_modules` 整个删除，实体 JSON 不再有 `_modules`
3. 前端 `DetailPage` / `LootdropDetailPage` 改直接使用 `useDungeonModules()` 的 `globalModules`
4. 类型 `InlineModuleData` 删除，实体接口删除 `_modules` 字段

**涉及文件**：

- `api/src/translator.py:build_coord_out` — 新增 `map_to_module` 参数，解析 map 字段
- `api/src/entity_export.py` — 删除 `_build_inline_modules` 及所有 `_modules` 注入，签名简化去掉 `modules_map`
- `api/src/lootdrop_builder.py` — 删除 `_modules` 注入及 `modules_map` 参数
- `api/src/collector.py` — 更新函数调用签名
- `web/src/types/data.ts` — 删除 `InlineModuleData`，实体接口删除 `_modules`
- `web/src/pages/DetailPage.tsx` — 模块 Map 直接来自 `globalModules.get(c.map)`
- `web/src/pages/LootdropDetailPage.tsx` — 同上

### 重构：移除内联 `_modules` 中的翻译数据，改由共享文件提供

**问题**：每个实体 JSON 的 `_modules` 内联了 `translation`/`group_display`，全站重复存储这些字段（1000+ 实体 × 5-15 模块），浪费带宽。

**改动**：

1. **后端**：`entity_export.py` / `lootdrop_builder.py` — 从内联 `_modules` 移除 `translation`、`group_display`
2. **类型**：`InlineModuleData` 移除这两个字段
3. **前端**：`DetailPage.tsx` / `LootdropDetailPage.tsx` — `translation`/`group_display` 改为从 `useDungeonModules()` 查询共享的 `dungeon_modules.json`
4. **预加载**：`index.html` 加 `<link rel="preload">`，`AppInner.tsx` 调用 `useDungeonModules()` 主动提前 fetch，确保模块数据优先于实体 JSON 加载

**涉及文件**：

- `api/src/entity_export.py:33-45` — 移除 `translation`/`group_display`
- `api/src/lootdrop_builder.py:698-710` — 同上
- `web/src/types/data.ts:75-87` — `InlineModuleData` 移除两个字段
- `web/src/pages/DetailPage.tsx:53-78` — `globalModules.get(mapName)` 获取翻译
- `web/src/pages/LootdropDetailPage.tsx:162-187` — 同上
- `web/index.html:12` — `<link rel="preload">`
- `web/src/AppInner.tsx:24,30` — 主动预取模块数据

### Bug 修复：内联 `_modules` 未提取 `group_display`

**问题**：`DetailPage.tsx` 和 `LootdropDetailPage.tsx` 从实体 JSON 内联 `_modules` 构建模块 Map 时，漏掉了 `group_display` 字段。导致 `mod?.group_display` 始终为 `undefined`，fallback 显示英文字段名（"Crypt"）。

**修复**：两文件在构造 `DungeonModule` 对象时添加 `group_display: data.group_display`。

**涉及文件**：

- `web/src/pages/DetailPage.tsx:63` — 新增 `group_display: data.group_display`
- `web/src/pages/LootdropDetailPage.tsx:171` — 新增 `group_display: modData.group_display`

**不受影响**：`QuestItemGroupPage` / `DungeonModulesPage` / `DungeonModuleGroupPage` / `DungeonModuleDetailPage` 使用 `useDungeonModules()`（直接从 `dungeon_modules.json` 加载 Map），`group_display` 正常。

---

## 2026-07-14 会话修改记录（先前）

### 修复：地图分组翻译不显示（data/ 交付遗漏）

**问题**：上一次管道运行时 `_deliver()` 可能被中断，`data/json/` 为空。前端 fetch 不到 `dungeon_modules.json`，fallback 显示英文 `group` 名（如 "Crypt"）。

**修复**：重新运行 `python main.py`，确保完整交付到 `data/json/`。

**涉及文件**：无代码改动，仅重新执行管道 + 前端构建

---

## 2026-07-14 会话修改记录

### PWA 图标改为 DND + 圆角

- **修改**: PWA 图标从纯蓝正方形改为圆角蓝底白字 "DND"
- **favicon**: 新增 `web/public/favicon.ico`（16/32/48 三尺寸），`index.html` 添加 `<link rel="icon">`

---

# 2026-07-14 会话修改记录

## 分组名动态化：移除全部硬编码 GROUP_LABELS

**目标**：用 Game.json 的 `Text_UI_WB_DungeonSlot_*_NthFloor` / `Text_WB_DungeonSlot_*_1stFloor` 翻译键动态推导分组显示名，替换后端和前端共 8 处硬编码。

### 映射规则

| 代码库 group  | 基础键                                       | 公式                        | 结果示例                  |
| ------------- | -------------------------------------------- | --------------------------- | ------------------------- |
| GoblinCave    | `Slot_GoblinCave_1stFloor`                   | base + "1层"                | 哥布林洞穴1层             |
| FireDeep      | `Slot_GoblinCave_1stFloor`                   | base + "2层（`_2ndFloor`）" | 哥布林洞穴2层（赤焰深窟） |
| IceCavern     | `Slot_IceCavern_1stFloor`                    | base + "1层"                | 寒冰洞穴1层               |
| IceAbyss      | `Slot_IceCavern_1stFloor`                    | base + "2层（`_2ndFloor`）" | 寒冰洞穴2层（寒冰深渊）   |
| Ruins         | `Slot_TheCrypts_1stFloor`                    | base + "1层"                | 废墟1层                   |
| Crypt         | `Slot_TheCrypts_1stFloor`                    | base + "2层（`_2ndFloor`）" | 废墟2层（地穴）           |
| Inferno       | `Slot_TheCrypts_1stFloor`                    | base + "3层（`_3rdFloor`）" | 废墟3层（炼狱）           |
| ShipGraveyard | `Text_WB_DungeonSlot_ShipGraveyard_1stFloor` | base + "1层"                | 沉船墓场1层               |

### 后端改动

- `translator.py` — 新增 `resolve_group_label()` + `DUNGEON_SLOT_KEY_MAP` / `DUNGEON_SUBFLOOR_SLOT_KEY` / `DUNGEON_FLOOR_NUMBER`
- `config.py` — `DUNGEON_GROUP_GRADES` label 改为 1stFloor slot 基础值
- `collector.py` — `modules_map` 注入 `group_display`；传给 `generate_quest_items_groups` 和 `build_and_save_indexes`
- `entity_export.py` / `lootdrop_builder.py` — inline `_modules` 包含 `group_display`
- `index_export.py` — 移除全局 `GROUP_LABELS`，改用 `group_label_resolver` 回调

### 前端改动

7 个页面移除硬编码 `GROUP_LABELS`，改用 `mod.group_display`：

- `DetailPage.tsx`、`LootdropDetailPage.tsx`、`DungeonModuleDetailPage.tsx`
- `DungeonModulesPage.tsx`、`DungeonModuleGroupPage.tsx`
- `QuestItemGroupPage.tsx`、`ExplorePage.tsx`

`types/data.ts` — `DungeonModule` + `InlineModuleData` 添加 `group_display?: string`

### 验证

- 后端 pipeline 输出全部 8 个分组名正确
- `search_index.json` 中 tag 字段已更新为新格式
- 前端 tsc + SSG 构建全通过

## 清理死代码：DungeonGrade 分组代码表归档

**问题**：`dungeon_mode.py`（`parse_grade` 等 7 个函数）、`GRADE_DISPLAY_NAMES`、`_BASE_TO_GROUP`、`DUNGEON_GROUP_GRADES`、`DUNGEON_MODE_PVE~REVERSAL` 常量、`LOOTDROP_RATE_REFERENCE` 均无外部调用，属于 v4 参考项目遗留死代码。

**处理**：移入 `api/src/_archived/dungeon_grades.py`，从 `config.py` 中删除。

**保留**：`MODULE_GROUP_FLOOR_SUFFIXES`（仍被 `drop_rate.py`、`enrichment.py` 使用）、`DUNGEON_MODE_NAMES`（改为内联整数键 `{1: "PVE", 2: "普通", ...}`）。

## 文档更新

- `docs/FIX_ARTIFACT_VARIANT_SWITCH.md` - 神器变体切换修复文档
- `docs/PERF_LOOTDROPS_OPTIMIZATION.md` - lootdrops 性能优化记录
- `docs/PLAN_CONTAINER_GENERATOR_ENTITIES.md` - 容器生成器实体页计划

# 2026-07-14 会话修改记录

## Bug 修复

### Coffin_06 爆率重复显示（"皇家棺材" + "皇家棺材组"）

**原因**：`_classify_label('Coffin_R', 'Coffin_06')` 返回 `"other"`，因为 `Coffin_R` 不以 `Coffin_06_` 开头，错误归类为"组"，导致同一个实体产生两种标签（`皇家棺材` + `皇家棺材组`）。

**修复**：在 `api/src/lootdrop_builder.py:_classify_label` 中添加兜底匹配——当实体名含尾部数字后缀（如 `Coffin_06`）时，剥离后缀为 `Coffin`，检查标签是否以 `Coffin_` 开头。`Coffin_R` → `"direct"`，正确合并到唯一入口。

**变更文件**：`api/src/lootdrop_builder.py`（`_classify_label` 函数）

### Coffin_06 变体系数导致 spawn_rate 虚高

**问题**：`Ruins_ForsakenCloister` 模块的坐标 `variant_count=3`（3 种选 1），但 group_drop_info 中 spawn_rate=100% 未除以 3，页面显示 `100% (3种选1)` 应为 `33.3333%`。

**修复**：

1. **前端** `DetailPage.tsx:720-724` — 变体模块显示区域新增 `adjRate()`，将 `info.spawn_rate` 除以 `forcedVc.variant_count`，保留 4 位小数。
2. **精度规范** — `drop_rate.py:_round_rate` 从 3 位改为 4 位小数；`enrichment.py` 中 `round(x, 2)` 替换为 `_round_rate(x)`。
3. **文档** — `docs/REFERENCE.md` 添加精度要求说明。

**变更文件**：

- `web/src/pages/DetailPage.tsx`（变体 spawn_rate 除以 variant_count）
- `api/src/drop_rate.py`（`_round_rate` 3 位→4 位）
- `api/src/enrichment.py`（`round(x,2)` → `_round_rate(x)`）
- `docs/REFERENCE.md`（Decimal 精度规范说明）

## InstallPrompt 增加关闭按钮

- **原因**：安装 DND闪电指南 提示无法关闭，用户不需要时只能等待浏览器自动隐藏
- **变更文件**：`web/src/components/InstallPrompt.tsx`
- **改动**：新增 `dismissed` 状态 + ✕ 关闭按钮，点击后隐藏 prompt；关闭按钮绝对定位在卡片右上角

## MapPanel 兼容 iOS 14（不支持 aspect-ratio）

- **原因**：iOS 14.6 不支持 CSS `aspect-ratio` 属性（iOS 15+ 才支持），MapPanel div 高度为 0 导致背景地图图片不可见
- **变更文件**：`web/src/components/MapPanel.tsx`
- **改动**：将 `aspectRatio` 改为 `padding-bottom` 百分比 hack + 内层 `position: absolute` 容器，兼容所有浏览器；现代浏览器性能无差异

## CDN 缓存破坏 — 数据路径版本化

- **原因**：Cloudflare Pages CDN 和 SW 缓存无法在游戏更新时自动失效，用户看到旧版本数据。查询参数（`?_v=`）不可靠（CF 默认忽略 query string 作为缓存键）
- **方案**：构建时将数据版本（Unix 时间戳）通过 Vite `define` 注入为全局常量 `__DATA_VERSION__`，`dataUrl()` 将请求路径从 `/data/json/foo` 变换为 `/data/<base36>/json/foo`（base36 缩短时间戳，如 `1784008247` → `ti5hp2`）→ 版本变化时路径完全不同 → CDN 无歧义视为新资源
- **不版本化的资源**：图片（很少变化）、meta.json（固定路径用于版本检测）
- **构建流程**：
  1. `ssg.mjs` 在 `vite build` **之前**扫描所有 JSON 文件 mtime 计算 `dataDate`，设置 `VITE_DATA_VERSION` 环境变量
  2. `vite build` 时 Vite `define` 将 `__DATA_VERSION__` 替换为时间戳字符串，嵌入 JS bundle
  3. `vite build` 后 `ssg.mjs` 复制 `dist/data/json/` → `dist/data/<base36>/json/`（移除 versioned 副本中的 `meta.json`）
  4. `meta.json` 保持固定路径 `dist/data/json/meta.json`
- **SW 兼容**：`vite.config.ts` 中 SW 路由正则 `/^\/data\/\w+\/json\//` 匹配 base36 版本化路径
- **关键函数** `dataUrl()`：`/data/json/foo` → `path.slice(5)` 截断 `/data` 后插入 `/data/<base36>` → `/data/ti5hp2/json/foo`
- **版本更新机制**：`useDataVersion` 从 `/data/json/meta.json` 获取最新时间戳 → `setDataVersion()` 数值仅升不降，长会话能自动切到新版本 URL
- **`_headers` 最终状态**：仅 `meta.json` 设 10 分钟缓存（`/data/json/* → max-age=600`），其他全走 Cloudflare Pages 默认缓存策略
- **变更文件**：`dataUrl.ts`（新建）、`vite.config.ts`、`ssg.mjs`、`vite-env.d.ts`、`_headers`、`index.html`、`useDataVersion.ts`、`useDungeonModules.ts`、`useSearchIndex.ts`、`MapPanel.tsx`、所有 11 个页面

## 删除 SWUpdateBanner — SW 更新静默化，不再打扰用户

- **原因**：`SWUpdateBanner.tsx` 用 `workbox-window` 额外注册 SW，弹横幅让用户点"刷新以应用"。但 vite.config.ts 已设 `registerType: 'autoUpdate'`，Workbox 生成的 SW 自带 `skipWaiting()`，新 SW 安装后自动激活，完全不需要用户干预。且双注册（`registerSW.js` + `workbox-window`）竞争，用户要点两次才生效
- **教训**：此文件上次被删后又因"用户会看到旧内容"的理由被加回。错。`autoUpdate` + `skipWaiting()` 激活后，`StaleWhileRevalidate` / `NetworkFirst` 策略自动用新数据更新缓存，用户不刷新也会在后台同步。**客户不需要知道 SW 更新了，更不需要手动确认**
- **变更文件**：
  - 删除 `web/src/components/SWUpdateBanner.tsx`
  - `web/src/AppInner.tsx` — 移除 import 和 `<SWUpdateBanner />` 标签

## 坐标位置去重 + 矿石品质提取与前端的品质切换

- **原因**：钴矿类掉落数据中同一物理点位因品质等级（VeryLow/Low/Med/High）被导出为多条记录，导致计数膨胀（5点位 × 4品质 = 20条）。前端按 (x,y,z) 去重后显示正确点位；同时提取品质字段支持切换查看
- **公式**：
  - 品质概率：豪客赛→High 100%，普通赛→Low 90%+Med 10%，PVE→VeryLow 100%
  - 钴矿组在洞坑大厅展现：默认"高品质(豪客赛100%)"去重后 5 点位
- **变更文件**：
  - `api/src/translator.py` — `build_coord_out()` 从 keyword/original_keyword 提取品质后缀
  - `api/src/lootdrop_builder.py` — inline coord 生成同样提取 quality 字段
  - `web/src/pages/LootdropDetailPage.tsx`：
    - `LootdropCoord` 接口新增 `quality?: string`
    - mapGroups 循环中按 `qualityFilter` 过滤坐标
    - `computeModuleScore` 支持 `quality` 字段
    - `visibleCountByMonster` / `bottomCount` 按 (translation,x,y,z) 去重计数
    - 新增品质切换 UI（默认 High，点击切换品质/显示全部）
- **CobaltOres 数据**：重新运行管道后每组品质各 5 坐标（钴矿组）/ 13 坐标（钴矿随机）

## 新增物品坐标链式反查（lootdrop chain）

- **原因**：`TearofHrimthurs`（霜巨人之泪）虽然存在于 DB 中，但因 spawner 文件名缺 m（`TearofHrithurs` vs `TearofHrimthurs`）导致坐标匹配失败，物品表不显示。更深层问题是管道缺少 lootdrop 容器→坐标→物品的链式反查机制
- **变更文件**：
  - `api/src/collector.py` — 通过 `lootdrop_rate_items→lootdrop_groups→spawner_entries` 三表 JOIN 构建 `item_coord_chain_map`（529 个物品 → spawner keyword 映射）
  - `api/src/entity_export.py` — `export_items()` 新增 `item_coord_chain_map` 参数，直接坐标查找失败时作为回退（跳过 `filter_coords`，因为 spawner keyword 不是物品名）
  - `docs/REFERENCE.md` — 新增"物品坐标链式反查"章节
- **关键映射**：`TearofHrimthurs` → 链式反查到 spawner `TearofHrithurs` → 坐标 `IceAbyss_HoundVale` (x=-40, y=1430, z=-1187.73)
- **影响**：物品索引从 94 增至 517 个（新增 423 个 lootdrop 容器坐标物品）

## 2025-07-17 会话修改记录

### 变体切换组件提取 + 导航刷新修复

**原因：** `/lootdrops/WarMaul_6001/` 导航到 `/lootdrops/WarMaul_8001/` 时页面不刷新，需 F5 才能显示正确标题和分类按钮。

**变更文件：**
- `web/src/components/VariantSwitch.tsx` — 新建变体稀有度切换组件，从 LootdropDetailPage 提取
- `web/src/pages/LootdropDetailPage.tsx` — 内联变体按钮替换为 `<VariantSwitch>`；导航时清除 `_preloadedLootdrop` 缓存

**关键修复：**
- 模块级 `_preloadedLootdrop` 缓存在客户端导航后仍保留旧页面数据，干扰 useEffect 数据拉取逻辑
- 在 `name` 变化的 useEffect 中同时清除 `_preloadedLootdrop` 和 `_preloadedLootdropUrl`，确保下次 fetch 不被跳过

### 宝藏堆神器爆率缺失修复

**原因：** `build_and_save_lootdrop_details` 中 `monsters_out` 的每个怪物条目未填充 `drop_rates` 字段，导致前端地图卡片中不显示爆率。此问题在 _8001 神器变体页面（继承基础物品的完整怪物列表后）尤为明显。

**变更文件：**
- `api/src/lootdrop_builder.py` — 在 `max_score` 计算后，聚合 `group_drop_info` 中各模式的最高爆率，注入到每个怪物条目的 `drop_rates` 字段

**修复效果：**
- 所有 lootdrop 详情页的怪物现在都有 `drop_rates`（各模式下跨组取最大值）
- 前端地图卡片中怪物名称旁正确显示 `[豪客赛:X%]` 等爆率信息
- WarMaul_8001 页面：宝藏堆 显示 `[豪客赛:0.0107%][逆袭赛:0.0107%]`

### 宝藏堆神器爆率调查与 compute_drop_rate 修复

**调查结论：** 宝藏堆在 RondelDagger_8001 页面显示的神器爆率 `[豪客赛:0.0107%]` 是**正确的**。

**数据链路：**
- `Hoard01_3` 的候选 LDG 包含 `ID_LootDropGroup_SuperHoard`
- SuperHoard 在 mode=3(豪客赛) floor=23 绑定 `ID_Lootdrop_Drop_HoardWeaponArmor`
- 该 LootDrop 直接包含 `WarMaul_8001` 条目（LuckGrade=8）
- 对应的 `ID_Droprate_Hoard_WeaponArmor_3023` 有 LuckGrade 8 weight=30（非零）

用户检查的 `ID_Droprate_Hoard_Treasure_*` 的 LG8=0，但 **SuperHoard 走的是 WeaponArmor 通道**，该通道的 droprate 文件有 LG8 数据。

**bug：** `compute_drop_rate` 在 item fallback 时使用基础物品的 luck_grade（如 WarMaul→5）计算 pool weight，而非使用变体后缀的 luck_grade（如 8001→8）。导致某些场景下神器爆率使用了非神器的权重。

**修复：** 从 item_name 的 `_\d{4}` 后缀提取 luck_grade，用于 pool weight 查询；shared count 仍使用物品本身的 luck_grade（与 `compute_variant_rate` 的行为一致）。

**变更文件：**
- `api/src/drop_rate.py` — `compute_drop_rate` 新增 `_variant_luck_grade` 提取逻辑

### get_group_drop_rates 分离主/备 LDG 修复

**原因：** `_get_candidate_ids` 的 `_no_num` fallback（去尾数后缀）导致 `Hoard01_3`（宝藏堆）继承 `Hoard01_9`（超级宝藏堆）的 `ID_LootDropGroup_SuperHoard` LDG，进而拿到非法的 LuckGrade 8 神器爆率。

**修复：** `get_group_drop_rates` 将候选 LDG 分为 `_primary_set`（spawner_ldg 直连）和 `_fallback_set`（entity_ldg_all + 去尾数聚合）。对于 `luck_grade >= 8` 的变体物品，仅使用 `_primary_set` 计算爆率，不使用 fallback LDGs。

**影响：**
- 宝藏堆（Hoard01_3）→ 神器爆率 = 0 ✓
- 超级宝藏堆（SuperHoard01_9）→ 神器爆率正确（Primary 直连 SuperHoard LDG）✓
- 其他实体（AncientStingray 等）→ 不变 ✓
- 基础物品爆率（非变体）→ 不变（走原有 primary+fallback 逻辑）

**变更文件：**
- `api/src/drop_rate.py` — `get_group_drop_rates` 分离 primary/fallback LDGs，LG≥8 仅用 primary

### 回退怪物级 drop_rates 注入

**原因：** 前端地图分组头部"参考爆率"已展示完整爆率信息，无需在每个地图卡片怪物名旁重复显示 `[豪客赛:X%]`。`N种选M`/`N点选1` 等变体展示不受影响（数据在 coords 的 variant_count 字段）。

**操作：** 删除 `lootdrop_builder.py` 中 `max_score` 计算后聚合 `group_drop_info` 注入 `monsters[]` 每个条目的 `drop_rates` 字段的代码块。

**变更文件：**
- `api/src/lootdrop_builder.py` — 移除 `_agg_drop_rates` 聚合与注入逻辑
