# 性能优化草案：管线 + 运行时

> 创建日期: 2026-07-27  
> 状态: **草案 / 待执行**（仅文档，未改代码）  
> 基线: `api/logs/pipeline_20260727_005114.log`（热 DB，总 **98.18s**）  
> 关联历史:
> - `docs/PERF_LOOTDROPS_OPTIMIZATION.md`（已完成：compact / fuzzy / 去 variant_suffixes；当时 loot ~25s，现状回升）
> - `docs/PERF_VARIANT_DROP_RATE_CACHE.md`（**废弃**，勿再按该文实施）
> - `docs/plans/P005_coord_reference.md`（坐标 ref 已部分落地，仍有 `MAX_COORDS_PER_PAGE` 内联）
> - `docs/CACHE_OPTIMIZATION_PLAN.md`（版本化路径 + SW 规则，大部分已实施）
> - `docs/MODULES_LOAD_PERF.md`（详情页 `_modules` 内联，已修复加载链）

---

## 1. 背景与目标

### 1.1 现状（热 DB 导出阶段）

| 步骤 | 耗时 | 占比 |
|------|------|------|
| **lootdrops** | **79.08s** | **80.5%** |
| **locale export** | **14.16s** | **14.4%** |
| deliver | 2.08s | 2.1% |
| dungeon_modules | 1.16s | 1.2% |
| 其余 export | <1s | <1% |
| **合计** | **98.18s** | 100% |

数据规模（约）:

| 产物 | 规模 |
|------|------|
| `data/json/lootdrops/` | ~664MB / ~2308 文件（均 ~295KB，大文件 ~660KB） |
| `web/dist` | ~728MB（多为 `dist/data/{ver}/` 版本化拷贝） |
| `search_index.json` | ~1.7MB |
| DB `darkfindv5.db` | ~40MB |

冷启动（源文件新于 DB）另有 map/spawner 全量 import，不在上表 98s 内。

### 1.2 目标（执行时再实测验收）

| 目标 | 指标建议 |
|------|----------|
| 热 DB 管线 | 总时长 **≤ 40s**（loot ≤ 30s，locale ≤ 1s） |
| 产物体积 | loot 外实体 JSON 全面 compact；dist 可观测下降 |
| 详情页交互 | 大掉落页筛选/图例切换无明显长任务（目标：主线程 <50ms 重组） |
| 不回归 | drop_rates / coords / locale key 集合与优化前一致（抽样 + 关键物品对比） |

### 1.3 非目标

- 不改业务掉落公式语义（仅缓存/索引/I/O）
- 不在本草案强制上 C 扩展 / 减变体数量
- 不强制全量 SSR 详情（已有 `--quick`）
- 日常 dev HMR 不跑全量管线，优化收益主要在 rebuild / 生产构建

---

## 2. 热点分级

### P0 — 高 ROI，优先做

#### P0-1 Locale 二次全盘 parse（I/O 冗余）

| | |
|---|---|
| **文件** | `api/src/locale_builder.py` → `_load_used_keys` |
| **现象** | loot 写完后对 `items/monsters/props/lootdrops` **再 `json.load` 一遍**（~670MB+）只为收集 `translation_key` |
| **实测** | locale export **14.16s** |
| **方案** | 导出/构建详情时维护全局 `used_translation_keys: set[str]`，写盘时顺带 `add`；`build_locale_files` 只读该 set（或落盘 `used_keys.json` 中间产物）。保留对 `search_index` / `dungeon_modules` 的轻量收集。 |
| **预期** | **~14s → 亚秒** |
| **风险** | 漏 key → 某语言缺译名；需用「优化前后 used_keys 集合 diff」验收 |
| **工作量** | S（半日级） |

#### P0-2 DropRateEngine 反向索引（CPU 易赢）

| | |
|---|---|
| **文件** | `api/src/drop_rate.py` → `get_base_item_spawners`（约 L283–297） |
| **现象** | 每个多变体物品 **线性扫** `_ld_rate_items`（~7867 行）再展开 group→spawner |
| **方案** | `preload()` 一次构建 `base_item → set[spawner_keyword]`（及可选 `base_item → set[ld_id]`）；`get_base_item_spawners` 改为 dict 查 |
| **预期** | 砍掉 loot 阶段重复 O(items×rate_rows) 扫描；具体秒数需 profile |
| **风险** | 低（纯索引，语义不变） |
| **工作量** | S |

#### P0-3 变体 GDI / 结构复用（loot 主路径）

| | |
|---|---|
| **文件** | `api/src/lootdrop_builder.py`、`api/src/drop_rate.py` |
| **现象** | 物品 × 实体 × map 组 × mode × 楼层 × LDG × rate 的嵌套；多稀有度变体重复算 base 结构 |
| **方案** | 1）优先批量 API：`get_variant_rates_all_groups`（若已有）替代 per-group 循环；2）跨变体复用 monsters/coords 骨架，仅替换 GDI + 过滤后 coords；3）`(item, entity, group) → drop_rates` 结果缓存（注意与已废弃的「内层 grade_data 微缓存」区分：这里是**外层结果/结构复用**） |
| **预期** | loot 79s 的主要下降来源；目标 loot **≤ 30s**（与 P0-2 叠加） |
| **风险** | 中 — 变体过滤 coords / 零爆率清理易回归；需固定样例对比 JSON |
| **工作量** | M |

### P1 — 体积与写盘

#### P1-1 全实体 compact JSON

| | |
|---|---|
| **文件** | `entity_export.py`、`enrichment.py`、module/quest 写出路径 |
| **现象** | loot 已 compact；其它实体仍 `indent=2`，体积与 parse 浪费 |
| **方案** | 统一 `separators=(",", ":")`；dev 调试可读性用可选 env `DF5_JSON_PRETTY=1` |
| **预期** | 单文件可再降 ~30%；dist/deliver 略快 |
| **风险** | 低；若有依赖 pretty 的外部脚本需知会 |
| **工作量** | S |

#### P1-2 enrichment 合并写

| | |
|---|---|
| **文件** | `api/src/enrichment.py` |
| **现象** | 多遍 load+dump 实体 JSON |
| **方案** | 尽量在首次 export 注入 `group_drop_info` 等字段，减少二次读写 |
| **预期** | 数秒级 + 更少磁盘抖动 |
| **风险** | 中 — 依赖 collector 阶段数据是否已齐 |
| **工作量** | M |

#### P1-3 详情写盘并行

| | |
|---|---|
| **文件** | `lootdrop_builder.py` |
| **方案** | preload 与纯计算单进程完成后，`ProcessPool`/`ThreadPool` 并行 `json.dump`（GIL：dump 偏 I/O 可用线程；重 CPU 段需进程） |
| **预期** | 视磁盘；SSD 上中等收益 |
| **风险** | 中 — 内存峰值、错误传播 |
| **工作量** | M |

### P2 — 运行时 UX

#### P2-1 LootdropDetail 重组 memo 化

| | |
|---|---|
| **文件** | `web/src/pages/LootdropDetailPage.tsx` |
| **现象** | 最多 ~3000 coords：按 map/module 分组、打分、排序、质量/隐藏过滤；筛选切换易重算整树 |
| **方案** | `useMemo` 绑定 `data + hidden + qualityFilter + …`；拆纯函数便于测 |
| **预期** | 筛选交互流畅 |
| **风险** | 低 |
| **工作量** | S–M |

#### P2-2 MapPanel 密集点渲染

| | |
|---|---|
| **文件** | `web/src/components/MapPanel.tsx`（及 MapDebug 相关） |
| **现象** | `dots.map` → 每点一 DOM，模块多时 React 树膨胀 |
| **方案** | 阈值以上改 **单层 canvas / 单 SVG path**；或虚拟化仅渲染可见模块 |
| **预期** | 大图滚动/缩放不再卡 |
| **风险** | 中 — 点击命中、高亮、SSR/hydration 需对齐 |
| **工作量** | M–L |

#### P2-3 搜索索引（按需）

| | |
|---|---|
| **文件** | `useSearchIndex.ts`、`NavBar.tsx` |
| **现象** | 1.7MB 全量 filter + `includes` |
| **方案** | 确认 debounce；pipeline 预写 lowercase 字段；仅当中低端机卡顿再上前缀索引 |
| **预期** | 通常可跳过 |
| **工作量** | S |

### P3 — 冷启动 import / PWA 存储

#### P3-1 源指纹替代全树 walk

| | |
|---|---|
| **文件** | stale 检测（`main` / collector / search_engine 路径） |
| **现象** | `_is_db_stale` 对大型 Exports 树 `os.walk` mtime |
| **方案** | 持久化 mtime/hash manifest，只比对变更子树 |
| **场景** | 仅冷 rebuild 频繁时做 |
| **工作量** | M |

#### P3-2 HR/D 去重空间索引

| | |
|---|---|
| **文件** | spawner 提取路径 |
| **现象** | 坐标线性距离去重 |
| **方案** | 网格桶 / 空间 hash（列表变大时） |
| **工作量** | M |

#### P3-3 Workbox 大 JSON 策略

| | |
|---|---|
| **文件** | `web/vite.config.ts`（`df5-data-json` maxEntries ~3300，无 maxAge） |
| **现象** | 条目数淘汰、不按字节；缓存大量 ~300KB loot → 存储压力 |
| **方案** | 版本化 URL 可用 CacheFirst；最大 loot 可不进 SW / 仅 summary；评估 size 插件 |
| **工作量** | S–M |

---

## 3. 建议执行顺序

```
阶段 A（快赢，可单独 commit）
  A1  P0-1 locale 顺带收集 keys
  A2  P0-2 base_item→spawners 索引
  A3  P1-1 全量 compact JSON

阶段 B（loot 主降耗）
  B1  P0-3 变体批量 rates + 结构复用 + 外层结果缓存
  B2  固定样例 JSON diff / drop_rates 抽样
  B3  （可选）P1-3 并行写盘

阶段 C（前端体感）
  C1  P2-1 useMemo 重组
  C2  P2-2 密集点 canvas/SVG（阈值触发）

阶段 D（按需）
  D1  P1-2 enrichment 合并
  D2  P3-1~3 冷启动 / PWA
```

每阶段完成后：热 DB 跑一次 `python main.py`（日志重定向），对比 `pipeline_*.log` 分步耗时；前端阶段跑 format / tsc，大页手测。

---

## 4. 验收清单

### 4.1 管线

- [ ] 热 DB 总时长 vs 基线 98s（记新 log 路径）
- [ ] lootdrops / locale 分步秒数
- [ ] `used_keys` 或 locale 文件：key 集合无减少（允许新增）
- [ ] 抽样对比（建议固定）:
  - 多变体装备（如 `HeaterShield_8001` 及 rarity 变体）
  - 大坐标物品（helm 类 ~660KB 级）
  - props 参考爆率（`GoldChest` / `FlatChestLarge` 结构化标签仍在）

### 4.2 前端

- [ ] `npm run format` / `format:check` / `npx tsc --noEmit`
- [ ] 大 loot 详情：质量筛选、隐藏模块、地图切换无长卡顿
- [ ] Map 点击/高亮行为与优化前一致

### 4.3 流程纪律

- [ ] 改代码前按 `docs/DEVELOPMENT_WORKFLOW.md` checkpoint
- [ ] 每逻辑任务本地 commit；禁止只写 SESSION 不 commit
- [ ] 完成后追加 `docs/SESSION_CHANGES.md`
- [ ] **禁止** 未要求时 `git push`

---

## 5. 关键代码锚点（便于执行时跳转）

| 区域 | 路径 | 备注 |
|------|------|------|
| 管线入口 / 计时 | `api/main.py`、`api/src/pipeline_timer.py`、`api/logs/pipeline_*.log` |
| 掉落详情 | `api/src/lootdrop_builder.py` | 主 79s |
| 爆率引擎 | `api/src/drop_rate.py` | `get_base_item_spawners`、`compute_*`、`preload` |
| Locale | `api/src/locale_builder.py` | `_load_used_keys` |
| 富化多遍写 | `api/src/enrichment.py` | |
| 实体导出 | `api/src/entity_export.py` | indent |
| 冷 import | `api/src/search_engine.py`、`api/src/collector.py`、`api/src/db/importers/` | |
| 详情页 | `web/src/pages/LootdropDetailPage.tsx` | |
| 地图点 | `web/src/components/MapPanel.tsx` | |
| SSG / 版本拷贝 | `web/scripts/ssg.mjs` | |
| PWA | `web/vite.config.ts` | Workbox runtimeCaching |

---

## 6. 复杂度与模式备忘

| 模式 | 位置 | 说明 |
|------|------|------|
| 多层嵌套 drop 循环 | drop_rate + lootdrop_builder | 主导 CPU |
| 全目录 JSON 再 parse | locale_builder | 主导 I/O（热路径） |
| 线性扫 rate items | `get_base_item_spawners` | 易改 O(1) |
| indent=2 写出 | entity / enrichment | 体积 |
| 客户端 3000 点重组 | LootdropDetailPage | 交互 |
| DOM-per-dot | MapPanel | 密集图 |
| SW 按条目数淘汰 | vite.config | 存储 |

---

## 7. 明确不做 / 已废弃

| 项 | 说明 |
|----|------|
| `PERF_VARIANT_DROP_RATE_CACHE.md` 内层 grade_data 微缓存 | 已废弃；结果级 `_variant_rate_cache` 已存在 |
| 为省时间改掉落公式 / 砍变体 | 属产品决策，不在本草案 |
| 每次 dev 都全量管线压测 | dev 用 8090 HMR；验收用日志重定向的 `python main.py` |

---

## 8. 执行时备注（给未来的 agent）

1. 先读本文件 + 最新 `api/logs/pipeline_*.log`，更新基线数字若已漂移。  
2. **阶段 A 可独立合入**；阶段 B 必须带 JSON 抽样 diff。  
3. 改 `drop_rate` / loot 写出后勿只信「更快」——用同一物品变体前后 `group_drop_info` 对比。  
4. 文档规则：每完成子阶段更新本文件状态（`草案` → `进行中 A` → `A 完成` …）并写 `SESSION_CHANGES.md`。  
5. 运行环境为 **WSL Ubuntu**；长命令重定向日志，勿阻塞 TUI。

---

## 9. 变更记录（文档本身）

| 日期 | 说明 |
|------|------|
| 2026-07-27 | 初稿：基于热 DB 98s 剖析；分 P0–P3 与阶段 A–D；待执行 |
