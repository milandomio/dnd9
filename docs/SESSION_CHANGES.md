# 会话修改记录

当前会话记录写在本文件；历史记录已移至 [`SESSION_CHANGES_ARCHIVE.md`](SESSION_CHANGES_ARCHIVE.md)，按日期保留原始内容。

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
