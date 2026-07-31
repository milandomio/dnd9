# 日语详情页实体 i18n 待翻译计划

## 当前审计基线

- **审计日期**：2026-08-01（基于完成本轮管道后的 `data/json` locale 与实体详情产物复核）。
- **审计范围**：日语 `items`、`monsters`、`props`、`lootdrops` 和 `dungeon_modules` 详情页的主实体标题；不把坐标中的地图文件名、页脚品牌和 `PvE`、`HR`、`EXP` 等固定缩写当作实体翻译问题。
- **候选总数**：105 个技术实体。
- **分类**：所有详情实体已具备官方或 `df5.hardcoded.*` key；五个怪物和五个场景实体已补十语言人工词条，`LittleToad_Poison`、`LivingArmor`、`LivingStatue`、`Morayeel`、`Rat`、`TrainingDummy_CharacterBase` 和 `Ruins_Chapel` 复用官方 key；其余 105 个技术实体的日语值仍等于英文。
- **排除项**：`EmptyModule_1F_09/13/14/15` 与 ShipGraveyard 的两个数字模块名是既定显示别名（如 `5-1`、`1-1`），不是待翻译 raw identifier。
- **数据依据**：`data/json/{items,monsters,props,lootdrops,dungeon_modules.json,locale/{ja,en}.json}`；所有当前使用的 172 个 `df5.hardcoded.*` 键已在十语言 locale 中存在。
- **清单说明**：下方逐项清单保留 2026-07-30 的人工核对记录，个别计数已被后续合成键落地改变；实施前先按上述当前基线重新导出候选，不以旧条目数量判断完成度。

## 处理顺序

### P0：人类可读实体

- 先处理 5 个怪物名称和明显的中文/中英混合地图模块名。
- 优先使用游戏官方 `translation_key`；没有官方键时新增稳定的 `df5.hardcoded.*` key。

### P1：已有 synthetic key

- 为现有 key 补齐十种语言，至少保证 `ja` 不再等于 `en`。
- 翻译集中维护在 `api/src/config.py` 的 `HARDCODED_LOCALE_OVERRIDES`，不直接修改生成的 `data/json`。

### P2：空 translation_key 技术实体

- 先确认是否存在可复用的 Game.json key。
- 没有官方 key 时，加入 `HARDCODED_TRANSLATIONS`、`hardcoded_translation_key()` 和十语言 locale 映射。
- 技术型 FX、触发器、体积和内部控制器允许保留英文技术名，但必须在计划中明确标记为“保留”或提供日语显示名，不能静默回退。

## 候选清单

### Monsters：5 个 synthetic key

- [ ] `ExpressmanOtto` — `df5.hardcoded.ExpressmanOtto`
- [ ] `GoblinMelee` — `df5.hardcoded.GoblinMelee`
- [ ] `GoblinRanged` — `df5.hardcoded.GoblinRanged`
- [ ] `SkeletonMelee` — `df5.hardcoded.SkeletonMelee`
- [ ] `SkeletonRanged` — `df5.hardcoded.SkeletonRanged`

### Props：83 个 synthetic key

- [ ] `AkPostEventSequencerSection` — `df5.hardcoded.AkPostEventSequencerSection`
- [ ] `AkPostEventSequencerTrack` — `df5.hardcoded.AkPostEventSequencerTrack`
- [ ] `AmbientLight_Crypt_Strong` — `df5.hardcoded.AmbientLight_Crypt_Strong`
- [ ] `AmbientLight_Firedeep_Strong` — `df5.hardcoded.AmbientLight_Firedeep_Strong`
- [ ] `AmbientLight_Firedeep_Weak` — `df5.hardcoded.AmbientLight_Firedeep_Weak`
- [ ] `AmbientLight_Ice_Strong` — `df5.hardcoded.AmbientLight_Ice_Strong`
- [ ] `AmbientLight_Ice_Weak` — `df5.hardcoded.AmbientLight_Ice_Weak`
- [ ] `AmbientLight_Ocean_Strong` — `df5.hardcoded.AmbientLight_Ocean_Strong`
- [ ] `AmbientLight_Ocean_Weak` — `df5.hardcoded.AmbientLight_Ocean_Weak`
- [ ] `AntiFireDeppModuleVolume` — `df5.hardcoded.AntiFireDeppModuleVolume`
- [ ] `ArcheryTarget` — `df5.hardcoded.ArcheryTarget`
- [ ] `BlackDespairBanner` — `df5.hardcoded.BlackDespairBanner`
- [ ] `BossTriggerBase` — `df5.hardcoded.BossTriggerBase`
- [ ] `CandleHolder_Bronze` — `df5.hardcoded.CandleHolder_Bronze`
- [ ] `Chain` — `df5.hardcoded.Chain`
- [ ] `CustomFogVolume_DCWaterExclusionVolume` — `df5.hardcoded.CustomFogVolume_DCWaterExclusionVolume`
- [ ] `CustomFogVolume_Sphere` — `df5.hardcoded.CustomFogVolume_Sphere`
- [ ] `DirtyWater` — `df5.hardcoded.DirtyWater`
- [ ] `DownIndicatorTorch` — `df5.hardcoded.DownIndicatorTorch`
- [ ] `DungeonDown` — `df5.hardcoded.DungeonDown`
- [ ] `DungeonEscape_IndicatorTidewalker` — `df5.hardcoded.DungeonEscape_IndicatorTidewalker`
- [ ] `DungeonEscape_IndicatorTorch` — `df5.hardcoded.DungeonEscape_IndicatorTorch`
- [ ] `DungeonEscapeBoss` — `df5.hardcoded.DungeonEscapeBoss`
- [ ] `DungeonInfiniteExitBase` — `df5.hardcoded.DungeonInfiniteExitBase`
- [ ] `DungeonModule` — `df5.hardcoded.DungeonModule`
- [ ] `EasyFog` — `df5.hardcoded.EasyFog`
- [ ] `FallingDebrisActor_Crypt` — `df5.hardcoded.FallingDebrisActor_Crypt`
- [ ] `FallingIcicleActor` — `df5.hardcoded.FallingIcicleActor`
- [ ] `FallingIcicleArea` — `df5.hardcoded.FallingIcicleArea`
- [ ] `FireColossus_ArenaFloorManager` — `df5.hardcoded.FireColossus_ArenaFloorManager`
- [ ] `FiredeepMagmaVolume` — `df5.hardcoded.FiredeepMagmaVolume`
- [ ] `FiredeepRoaster_01ON` — `df5.hardcoded.FiredeepRoaster_01ON`
- [ ] `Fireflies` — `df5.hardcoded.Fireflies`
- [ ] `FixedStairDown` — `df5.hardcoded.FixedStairDown`
- [ ] `FixedStairEscape` — `df5.hardcoded.FixedStairEscape`
- [ ] `FogSheet` — `df5.hardcoded.FogSheet`
- [ ] `Food_Set_02` — `df5.hardcoded.Food_Set_02`
- [ ] `GameObjectLinker` — `df5.hardcoded.GameObjectLinker`
- [ ] `GameSpawnerGroup` — `df5.hardcoded.GameSpawnerGroup`
- [ ] `GroundLamp_Lit_01` — `df5.hardcoded.GroundLamp_Lit_01`
- [ ] `IceFloorWyvernLair` — `df5.hardcoded.IceFloorWyvernLair`
- [ ] `IceSecretWallDoor02` — `df5.hardcoded.IceSecretWallDoor02`
- [ ] `JailDoor02_Unlocked` — `df5.hardcoded.JailDoor02_Unlocked`
- [ ] `LadderBase` — `df5.hardcoded.LadderBase`
- [ ] `LevelSequenceActor` — `df5.hardcoded.LevelSequenceActor`
- [ ] `LevelSequenceAlwaysRelevantActor` — `df5.hardcoded.LevelSequenceAlwaysRelevantActor`
- [ ] `LevelSequenceSoundActor` — `df5.hardcoded.LevelSequenceSoundActor`
- [ ] `LightBeam` — `df5.hardcoded.LightBeam`
- [ ] `LivingStatue` — `df5.hardcoded.LivingStatue`
- [ ] `LivingStatue_Elite_Dummy` — `df5.hardcoded.LivingStatue_Elite_Dummy`
- [ ] `MapIconDrawbridge` — `df5.hardcoded.MapIconDrawbridge`
- [ ] `MapIconElevatorEscape` — `df5.hardcoded.MapIconElevatorEscape`
- [ ] `MapIconFixedStairDown` — `df5.hardcoded.MapIconFixedStairDown`
- [ ] `MapIconFixedStairEscape` — `df5.hardcoded.MapIconFixedStairEscape`
- [ ] `MeshParticle_Fog_Icy_001` — `df5.hardcoded.MeshParticle_Fog_Icy_001`
- [ ] `ObjectLinkWithTriggerBox` — `df5.hardcoded.ObjectLinkWithTriggerBox`
- [ ] `OceanCurrent` — `df5.hardcoded.OceanCurrent`
- [ ] `Path_01` — `df5.hardcoded.Path_01`
- [ ] `Placer_Fog_IceCavern` — `df5.hardcoded.Placer_Fog_IceCavern`
- [ ] `Portcullis_Down_Infinite` — `df5.hardcoded.Portcullis_Down_Infinite`
- [ ] `Portcullis_Escape_Infinite` — `df5.hardcoded.Portcullis_Escape_Infinite`
- [ ] `Portcullis_FixedStairs_Small_OnlyActivate` — `df5.hardcoded.Portcullis_FixedStairs_Small_OnlyActivate`
- [ ] `PressurePlate_OnlyActivate_IceAbyss` — `df5.hardcoded.PressurePlate_OnlyActivate_IceAbyss`
- [ ] `PressurePlate_OnlyActivate_Inferno` — `df5.hardcoded.PressurePlate_OnlyActivate_Inferno`
- [ ] `PushingBlock` — `df5.hardcoded.PushingBlock`
- [ ] `RandomTimerSwitch` — `df5.hardcoded.RandomTimerSwitch`
- [ ] `ShipLamp01On1` — `df5.hardcoded.ShipLamp01On1`
- [ ] `SkeletonWoodenBarrel` — `df5.hardcoded.SkeletonWoodenBarrel`
- [ ] `SpikeLogEjectorB` — `df5.hardcoded.SpikeLogEjectorB`
- [ ] `SplineMesh_Ladder` — `df5.hardcoded.SplineMesh_Ladder`
- [ ] `SplineMesh_Lava` — `df5.hardcoded.SplineMesh_Lava`
- [ ] `StaticMeshItemHolder` — `df5.hardcoded.StaticMeshItemHolder`
- [ ] `StatueLever_ice` — `df5.hardcoded.StatueLever_ice`
- [ ] `SubGroup` — `df5.hardcoded.SubGroup`
- [ ] `SulfurRoaster_01` — `df5.hardcoded.SulfurRoaster_01`
- [ ] `TidewalkerPortcullis_Deactivate` — `df5.hardcoded.TidewalkerPortcullis_Deactivate`
- [ ] `TorchBold02_On` — `df5.hardcoded.TorchBold02_On`
- [ ] `UnderSeaCave_Deactivate` — `df5.hardcoded.UnderSeaCave_Deactivate`
- [ ] `UnderWater` — `df5.hardcoded.UnderWater`
- [ ] `UnlockingFloorLeverByMonsterKill` — `df5.hardcoded.UnlockingFloorLeverByMonsterKill`
- [ ] `Updraft` — `df5.hardcoded.Updraft`
- [ ] `WoodenBarricateLarge` — `df5.hardcoded.WoodenBarricateLarge`
- [ ] `WoodenBarricateSmall` — `df5.hardcoded.WoodenBarricateSmall`

### Props：39 个空 translation_key

- [ ] `AmbientLight_Ice`
- [ ] `AmbientLight_Ruins_Strong`
- [ ] `AmbientLight_Ruins_Weak`
- [ ] `BallistaShip`
- [ ] `Candle_Noframe`
- [ ] `Candle_Wall`
- [ ] `Candles02a`
- [ ] `CandleWall`
- [ ] `chess`
- [ ] `DCAkAmbient_Sound`
- [ ] `DarkChain`
- [ ] `FireDeepMagmaWall`
- [ ] `FiredeepMagmaVolume_Strong`
- [ ] `FiredeepRoaster01`
- [ ] `FiredeepRoaster02`
- [ ] `FloatingIce`
- [ ] `FX_Env_IcyFog_Linear_001`
- [ ] `FX_Placer_FlyingBook`
- [ ] `FX_SulfurFalls`
- [ ] `Inferno_SplineMeshParticle_Fog`
- [ ] `LivingArmor` — 当前 ja：`铠甲傀儡`
- [ ] `LivingArmor_Elite` — 当前 ja：`铠甲傀儡`
- [ ] `LivingStatue_Elite` — 当前 ja：`石像鬼`
- [ ] `MapIconRaft`
- [ ] `MeshParticle_Fog_Icy_002`
- [ ] `MeshParticle_Snow_001`
- [ ] `MeshParticle_Snow_002`
- [ ] `Morayeel` — 当前 ja：`海鳗`
- [ ] `Raft`
- [ ] `Sack_Stack`
- [ ] `SceneRender`
- [ ] `SceneRenderInterior`
- [ ] `StaticChain`
- [ ] `StoneLantern_On`
- [ ] `TrainingDummy_CharacterBase`
- [ ] `UnderBlood`
- [ ] `WindmillWheel_01`
- [ ] `WoodenBarricadeLarge`
- [ ] `WoodenBarricadeSmall`

### Dungeon modules：3 个空 translation_key

- [ ] `EmptyModule_1F_02` — 当前 ja：`EmptyModule_1F_02`
- [ ] `Ruins_Chapel` — 当前 ja：`教堂`
- [ ] `Ruins_DualBossTreasureRoom` — 当前 ja：`双boss宝藏室`

## 实施步骤

1. 逐项确认实体是否有官方 Game.json key；有则回填 `translation_key`，没有则建立稳定 synthetic key。
2. 为 synthetic key 添加十种语言文案，避免只补日语后其他语言继续回退英文。
3. 对模块实体同步检查 `dungeon_modules.json`、坐标实体 JSON、搜索索引和详情页消费端。
4. 每批完成后运行数据管道和 SSG，禁止直接编辑 `data/json` 生成文件。
5. 为每批新增实体增加产物断言，确认 `ja` 不再显示英文/中文兜底，其他语言 key 集合一致。

## 验收标准

- 候选清单全部勾选，或明确标注“保留技术名”及原因。
- 10 个 locale 文件包含相同的新增 key 集合。
- 日语详情页主标题不再显示 raw identifier、中文兜底或与英文相同的 synthetic value。
- `python main.py`、`npm run build`、`npm run test:i18n` 通过。
- 抽查 items、monsters、props、lootdrops、dungeon_modules 五类日语详情页 HTTP 200，且无 hydration 错误。
