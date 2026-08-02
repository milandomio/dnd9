import re
from pathlib import Path

# api/src/
SRC_DIR = Path(__file__).parent
# api/
API_DIR = SRC_DIR.parent
# DarkFindV5/
PROJECT_DIR = API_DIR.parent

GAME_ROOT = PROJECT_DIR.parent / "Output" / "Exports" / "DungeonCrawler" / "Content" / "DungeonCrawler"
DATA_DIR = GAME_ROOT / "Data" / "Generated" / "V2"
MAPS_DIR = GAME_ROOT / "Maps" / "Dungeon" / "Modules"

LOCALIZATION_DIR = GAME_ROOT.parent / "Localization" / "Game" / "zh-Hans"
GAME_JSON = LOCALIZATION_DIR / "Game.json"

LOCALIZATION_ROOT = GAME_ROOT.parent / "Localization" / "Game"

ITEM_DIR = DATA_DIR / "Item" / "Item"
MONSTER_DIR = DATA_DIR / "Monster" / "Monster"
PROPS_DIR = DATA_DIR / "Props" / "Props"
LOOTDROP_DIR = DATA_DIR / "LootDrop" / "LootDrop"
LOOTDROP_GROUP_DIR = DATA_DIR / "LootDrop" / "LootDropGroup"
LOOTDROP_RATE_DIR = DATA_DIR / "LootDrop" / "LootDropRate"
DUNGEON_MODULE_DIR = DATA_DIR / "Dungeon" / "DungeonModule"
SPAWNER_DIR = DATA_DIR / "Spawner" / "Spawner"
ART_DIR = DATA_DIR / "Art"

# DB 文件
DB_PATH = API_DIR / "data" / "darkfindv5.db"
# JSON 输出（collector 写入到此）
OUTPUT_DIR = API_DIR / "output" / "json"
# 日志目录
LOG_DIR = API_DIR / "logs"
# 图片源目录
IMG_SRC = SRC_DIR / "img"
# 交付目标（前端构建时从此读取）
DATA_DELIVERY_DIR = PROJECT_DIR / "data"

SPAWNER_ALIAS_MAP = {
    "ReinforcedDungeonDoor02": "ReinforcedDungeonDoor01",
}

TRANSLATION_ALIAS_MAP = {
    "GoldChest": "GoldenChest",
    "Corpse": "SkeletonCorpse",
    "CrateSmall": "WoodenCrateSmall",
    "CrateMedium": "WoodenCrateMedium",
    "CandleHolder": "GoldCandleHolder",
    "Chalice": "GoldChaliceA",
    "Cloak": "AdventurerCloak",
    # Case mismatch between lootdrop_items and spawners
    "DreadSpine": "Dreadspine",
    "DwarfHandCannoneer": "DwarfHandcannoneer",
    "TideWalkerShaman": "TidewalkerShaman",
    "BlueMarlin": "Bluemarlin",
}

TRANSLATION_KEY_ALIAS_MAP = {
    "Text_DesignData_Props_Props_Ore_BrimstoneOre": "Text_DesignData_Item_Item_BrimstoneOres_5001",
}

HARDCODED_TRANSLATIONS = {
    "Barrel": "木桶",
    "Bones": "骸骨",
    "Coin": "金币",
    "Ground": "地面",
    "Accessory_OldRustRoom": "旧锈房-饰品",
    "AntiquatedCoin": "古钱币",
    "Armor_Armory": "军械库-护甲",
    "Armor_DualBoss": "双Boss-护甲",
    "Armor_GoldenRoom": "黄金房-护甲",
    "BlackRose": "黑玫瑰",
    "Coffin": "棺材",
    "Coffin_Poor": "破旧棺材",
    "Coffin_Royal": "皇家棺材",
    "Gems": "宝石",
    "SuperHoard": "超级宝藏堆",
    "SuperHoardChest": "超级宝藏堆",
    "SuperHoardChest01": "超级宝藏堆",
    "SuperHoard01_9": "超级宝藏堆",
    "SuperHoardChest01_9": "超级宝藏堆",
    "Trinkets": "小饰品",
    "Weapon": "武器",
    "Weapon_DualBoss": "双Boss-武器",
    "Weapon_FrozenRoom": "冰封房-武器",
    "Weapon_GoldenRoom": "黄金房-武器",
    "Weapon_MysticalTreasureRoom": "神秘宝藏房-武器",
    "Weapon_SkullRoom": "骷髅房-武器",
    "DwarfSecretWeapon": "矮人秘密武器",
    "WoodenBarrel_UnderSea": "海底木桶",
    "BlueMarlin": "蓝枪鱼",
    "CandleHolder": "烛台",
    "Chalice": "圣杯",
    "Cloak": "披风",
    "CobaltOre": "钴矿",
    "CopperOre": "铜矿",
    "CryptSkeletonChampion": "地穴骷髅冠军",
    "DwarfHandCannoneer": "矮人火枪手",
    "FrostSkeletonChampion": "冰霜骷髅冠军",
    "FrostStoneOre": "霜石矿",
    "GoblinSkeletonChampion": "哥布林骷髅冠军",
    "GoldOre": "金矿",
    "InfernoSkeletonChampion": "炼狱骷髅冠军",
    "InfernoWraith": "炼狱幽魂",
    "IronOre": "铁矿",
    "Lumber": "木材",
    "MaelstromSkeletonChampion": "漩涡骷髅冠军",
    "MermaidCoffin": "人鱼棺材",
    "MimicLarge": "大宝箱怪",
    "MimicMedium": "中宝箱怪",
    "MimicSmall": "小宝箱怪",
    "ObsidianOre": "黑曜石矿",
    "PhantomFlower": "幻影花",
    "PirateCrossbow": "海盗弩",
    "Potion": "药水",
    "RubysilverOre": "红宝石银矿",
    "StingrayEgg": "刺鳐蛋",
    "StoneTomb": "石棺",
    "TideWalkerShaman": "踏潮者萨满",
    "TidestoneOre": "潮汐石矿",
    "Wardweed": "护符草",
    "Lifeleaf": "生命之叶",
    # 环境实体兜底翻译（源文件无 Name 属性，系统自动剥离后缀匹配基名）
    "AquaPrison": "水牢",
    "Bladehand_Ballista": "刃手弩炮",
    "CaveModuleWall": "洞穴墙壁",
    "DownCrevice": "下裂隙",
    "DownIndicatorTorch": "下行指示火把",
    "EscapeIndicatorTorch": "逃生指示火把",
    "EscapeShipExternalCrane": "逃生船外部吊车",
    "FrostSkeletonWoodenBarrer": "冰霜骷髅木栅栏",
    "FrostWyvern_IcePillar": "冰霜飞龙冰柱",
    "IceFloor": "冰面",
    "IceFloorWyvernLair": "冰面（飞龙巢穴）",
    "IceWall": "冰墙",
    "IciclesWall": "冰柱墙",
    "OceanCurrent": "洋流",
    "RandomTimerSwitch": "随机定时开关",
    "SkeletonWoodenBarrel": "骷髅木桶",
    "Updraft": "上升气流",
    "WoodenBarricateLarge": "大型木路障",
    "WoodenBarricateSmall": "小型木路障",
    # 直接放置实体兜底翻译（非 spawner，extract_spawners 未提取）
    "Statue01": "生命神坛",
    "Statue02": "保护神坛",
    "Statue03": "伤害神坛",
    "Statue04": "速度之泉",
    "StatueLever": "隐蔽雕像拉杆",
    "AltarOfSacrifice": "献祭神坛",
    "FloorPortal": "传送门",
    "Drawbridge": "撤离吊桥",
    "FloorLever": "拉杆",
    "WallLever": "拉杆",
    "Bloodfreeze": "极寒",
    "SulfurThrowerTrap": "硫磺喷射陷阱",
    "FlameThrowerTrap": "喷火机关",
    "GiantClam_Trap": "巨蚌",
    "SpikeLogEjector": "尖刺滚木弹射口",
    "Banshee_Soulflame": "狺女的哀伤灵焰",
    "SpectralKnight_Soulflame": "鬼灵骑士的魂焰",
    "Ladder": "梯子",
    "FallingIcicleArea": "坠冰区域",
    "FallingIcicleActor": "坠冰",
    "FallingDebrisActor_Crypt": "坠落碎石",
    "WoodenDoorWithLock": "带锁木门",
    "InfernoSecretWallDoor": "炼狱暗门",
    "IceSecretWallDoor02": "冰暗门",
    "FogSheet": "雾幕",
    "DungeonEscape": "地牢逃脱门",
    "DungeonDown": "地牢下方门",
    "DungeonEscapeBoss": "Boss逃脱门",
    "PushingBlock": "推动方块",
    "Rat": "老鼠",
    "ArcheryTarget": "射箭靶",
    "Chess": "棋盘",
    # 实体变体硬编码翻译（剥离后缀后无法自动匹配翻译前缀）
    "LivingStatue": "石像鬼",
    # ── AI 汉化新增 ──────────────────────────────────────────────
    # 怪物变体（entity_index 无法匹配，Game.json 前缀也找不到）
    "Expressman": "快递员",
    "ExpressmanOtto": "快递员奥托",
    "GoblinMelee": "哥布林近战",
    "GoblinRanged": "哥布林远程",
    "PirateSwiftBlade": "海盗快刀手",
    "SkeletonFootmanFakeDeath": "骷髅步兵（装死）",
    "SkeletonGuardsmanFromFakeDeath": "骷髅卫兵（装死）",
    "SkeletonMelee": "骷髅近战",
    "SkeletonRanged": "骷髅远程",
    "TideWalkerClubFighter": "踏潮者棍战士",
    "TideWalkerSpearer": "踏潮者矛兵",
    "ifrit": "火元素",
    "LivingStatue_Elite_Dummy": "精英石像鬼（假）",
    # Type.Character 杀怪目标
    "Undead": "亡灵",
    "Skeleton": "骷髅",
    "Goblin": "哥布林",
    "Mimic": "宝箱怪",
    "Kobold": "狗头人",
    "Demon": "恶魔",
    "Giant": "巨人",
    # 宝箱容器（无 Game.json 前缀匹配）
    "ChestLarge": "大宝箱",
    "ChestLarge_UnderSea": "海底大宝箱",
    "ChestMedium": "中宝箱",
    "ChestMedium_UnderSea": "海底中宝箱",
    "ChestSmall": "小宝箱",
    "ChestSpecial": "特殊宝箱",
    "ChestSpecial_UnderSea": "海底特殊宝箱",
    # 战利品类别
    "Armor": "护甲",
    "Weapon_Rare": "稀有武器",
    "LockPick": "开锁器",
    # 棺材（裸名 Coffin 无 Game.json 匹配，需保留兜底）
    "Coffin_R": "棺材",
    # 随机变体（无法通过 fuzzy 剥离匹配 Game.json 的才保留）
    "FrostSkeletonWoodenBarrelRandom": "冰霜骷髅木桶",
    "SkeletonWoodenBarrelRandom": "骷髅木桶",
    "OrnateChestLargeRandom_UnderSea": "海底华丽大宝箱",
    "SkeletonCorpseRandom_UnderSea": "海底骷髅尸体",
    "SkeletonCorpse_01_UnderSea": "海底骷髅尸体",
    "SkeletonCorpse_02_UnderSea": "海底骷髅尸体",
    "SkeletonCorpse_03_UnderSea": "海底骷髅尸体",
    # 环境/装饰（Game.json 无匹配）
    "BlackDespairBanner": "黑色绝望旗帜",
    "CandleHolder_Bronze": "青铜烛台",
    "Candles02": "蜡烛",
    "Candles08": "蜡烛",
    "Chain": "锁链",
    "DirtyWater": "脏水",
    "Fireflies": "萤火虫",
    "Fireflies2": "萤火虫",
    "Food_Set_02": "食物",
    "GroundLamp_Lit_01": "地面灯",
    "Lamp02Random": "灯",
    "LightBeam": "光束",
    "Path_01": "小径",
    "ShipLamp01On1": "船灯",
    "Statue_Dwarven": "矮人雕像",
    "SulfurRoaster_01": "硫磺灯架",
    "SulfurRoaster_02": "硫磺灯架",
    "SulfurRoaster_03": "硫磺灯架",
    "TorchBold02_On": "粗火把",
    "FiredeepRoaster_01ON": "熔岩灯架",
    "FiredeepRoaster_02ON": "熔岩灯架",
    "FiredeepTorch_01": "熔岩火把",
    # 门/机关/地图图标
    "DungeonDown_IndicatorTorch": "下行指示火把",
    "DungeonEscape_IndicatorTidewalker": "踏潮者逃脱指示",
    "DungeonEscape_IndicatorTorch": "逃生指示火把",
    "FixedStairDown": "固定下楼楼梯",
    "FixedStairEscape": "固定逃生楼梯",
    "JailDoor02_Unlocked": "未锁牢门",
    "LadderBase": "梯子底部",
    "MapIconDrawbridge": "地图图标-吊桥",
    "MapIconElevatorEscape": "地图图标-逃生电梯",
    "MapIconFixedStairDown": "地图图标-下行楼梯",
    "MapIconFixedStairEscape": "地图图标-逃生楼梯",
    "Portcullis_Down_Infinite": "下行吊桥（无限）",
    "Portcullis_Escape_Infinite": "逃生吊桥（无限）",
    "Portcullis_FixedStairs_Small_OnlyActivate": "小楼梯吊桥",
    "PressurePlate_OnlyActivate_IceAbyss": "压力板（冰渊）",
    "PressurePlate_OnlyActivate_Inferno": "压力板（炼狱）",
    "SpikeLogEjectorB": "尖刺滚木弹射口B",
    "StatueLever_ice": "冰雕拉杆",
    "TidewalkerPortcullis_Deactivate": "踏潮者吊桥",
    "UnderSeaCave_Deactivate": "海底洞穴门",
    "UnlockingFloorLeverByMonsterKill": "击杀怪物解锁拉杆",
    # 其他实体
    "BalistaShip": "弩炮船",
    "FireColossus_ArenaFloorManager": "火焰巨人竞技场",
    # 引擎/框架内部
    "AkPostEventSequencerSection": "音效序列器",
    "AkPostEventSequencerTrack": "音效序列轨道",
    "AmbientLight_Crypt_Strong": "环境光（地牢-强）",
    "AmbientLight_Firedeep_Strong": "环境光（熔岩-强）",
    "AmbientLight_Firedeep_Weak": "环境光（熔岩-弱）",
    "AmbientLight_Ice_Strong": "环境光（冰-强）",
    "AmbientLight_Ice_Weak": "环境光（冰-弱）",
    "AmbientLight_Ocean_Strong": "环境光（海洋-强）",
    "AmbientLight_Ocean_Weak": "环境光（海洋-弱）",
    "AntiFireDeppModuleVolume": "防火区域",
    "FiredeepMagmaVolume": "熔岩岩浆区域",
    "UnderWater": "水下区域",
    "BossTriggerBase": "Boss触发器",
    "CustomFogVolume_DCWaterExclusionVolume": "水排除区域",
    "CustomFogVolume_Sphere": "球形雾",
    "EasyFog": "简易雾",
    "PlaneFog": "平面雾",
    "DCHitBox": "碰撞箱",
    "GameObjectLinker": "对象链接器",
    "GameSpawnerGroup": "生成器组",
    "ObjectLinkWithTriggerBox": "触发器链接",
    "SubGroup": "子组",
    "LevelSequenceActor": "过场动画",
    "LevelSequenceAlwaysRelevantActor": "过场动画（始终相关）",
    "LevelSequenceSoundActor": "过场音效",
    "MeshParticle_Fog_Icy_001": "冰雾粒子",
    "Placer_Fog_IceCavern": "冰洞雾气",
    "SplineMesh_Ladder": "梯子（样条）",
    "SplineMesh_Lava": "岩浆（样条）",
    "StaticMeshItemHolder": "物品持有器",
    "DungeonModule": "地牢模块",
    "DungeonInfiniteExitBase": "无限出口",
    "Ruins_DualBossTreasureRoom": "双boss宝藏室",
    "ShipGraveyard_BladehandRefuge": "1-1",
    "ShipGraveyard_ElephantIsland": "3-6",
    "AmbientLight_Ice": "环境光（冰）",
    "AmbientLight_Ruins_Strong": "环境光（废墟-强）",
    "AmbientLight_Ruins_Weak": "环境光（废墟-弱）",
    "BallistaShip": "弩炮船",
    "CandleWall": "壁烛台",
    "Candle_Noframe": "无框蜡烛",
    "Candle_Wall": "墙壁蜡烛",
    "Candles02a": "蜡烛",
    "DCAkAmbient_Sound": "环境音",
    "DarkChain": "暗影锁链",
    "FX_Env_IcyFog_Linear_001": "冰雾特效",
    "FX_Placer_FlyingBook": "飞行书特效",
    "FX_SulfurFalls": "硫磺瀑布特效",
    "FireDeepMagmaWall": "熔岩墙",
    "FiredeepMagmaVolume_Strong": "熔岩区域（强）",
    "FiredeepRoaster01": "熔岩灯架",
    "FiredeepRoaster02": "熔岩灯架",
    "FloatingIce": "浮冰",
    "Inferno_SplineMeshParticle_Fog": "炼狱雾气粒子",
    "LivingArmor": "铠甲傀儡",
    "MapIconRaft": "地图图标-木筏",
    "MeshParticle_Fog_Icy_002": "冰雾粒子",
    "MeshParticle_Snow_001": "雪粒子",
    "MeshParticle_Snow_002": "雪粒子",
    "Morayeel": "海鳗",
    "Raft": "木筏",
    "Sack_Stack": "麻袋堆",
    "SceneRender": "场景渲染",
    "SceneRenderInterior": "室内场景渲染",
    "StaticChain": "静态锁链",
    "StoneLantern_On": "石灯笼",
    "TrainingDummy_CharacterBase": "训练假人",
    "UnderBlood": "血水区域",
    "WindmillWheel_01": "风车轮",
    "WoodenBarricadeLarge": "大型木路障",
    "WoodenBarricadeSmall": "小型木路障",
    "chess": "棋盘",
}

# Prefer a verified official key when an exported name is a gameplay or module
# alias rather than the canonical data asset name.
EXPLICIT_TRANSLATION_KEY_OVERRIDES = {
    "LittleToad_Poison": "Text_DesignData_Monster_Monster_LittleToad",
    "Ruins_Chapel": "Text_DesignData_Dungeon_DungeonModule_Abandoned_Sanctuary",
    "LivingArmor": "Text_DesignData_Monster_Monster_LivingArmor",
    "LivingStatue": "Text_DesignData_Monster_Monster_LivingStatue",
    "Morayeel": "Text_DesignData_Monster_Monster_Morayeel",
    "Rat": "Text_DesignData_ShapeShift_ShapeShift_Rat",
    "TrainingDummy_CharacterBase": "Text_DesignData_Props_Props_TrainingDummy",
}

# Module spawners use numbered or dungeon-prefixed names while their display
# names resolve to these base hardcoded entities.
HARDCODED_TRANSLATION_KEY_ALIASES = {
    "Ladder_01": "Ladder",
    "Ladder_02": "Ladder",
    "Ladder_03": "Ladder",
    "Ladder_04": "Ladder",
    "Inferno_PlaneFog": "PlaneFog",
    "IceWall_01": "IceWall",
    "IceWall_02": "IceWall",
    "IceWall_05": "IceWall",
    "IceWall_06": "IceWall",
    "IceWall_08": "IceWall",
    "IceWall_09": "IceWall",
    "IceFloor_01": "IceFloor",
    "IciclesWall_01": "IciclesWall",
}

# Synthetic keys make fallback entity names available to the locale exporter.
HARDCODED_I18N_PREFIX = "df5.hardcoded."

# Assets without a player-facing game name remain technically identifiable while
# each locale still signals that the following readable asset name is technical.
TECHNICAL_LOCALE_PREFIXES = {
    "de": "Technisches Objekt: ",
    "es": "Objeto técnico: ",
    "fr": "Objet technique : ",
    "ja": "技術オブジェクト: ",
    "ko": "기술 오브젝트: ",
    "pt-BR": "Objeto técnico: ",
    "ru": "Технический объект: ",
    "zh-Hant": "技術物件：",
}

HARDCODED_LOCALE_OVERRIDES: dict[str, dict[str, str]] = {
    "ArcheryTarget": {
        "zh-Hans": "射箭靶",
        "en": "Archery Target",
        "de": "Bogenschießziel",
        "es": "Blanco de tiro con arco",
        "fr": "Cible de tir à l'arc",
        "ja": "アーチェリーの的",
        "ko": "양궁 과녁",
        "pt-BR": "Alvo de arco e flecha",
        "ru": "Мишень для стрельбы из лука",
        "zh-Hant": "射箭靶",
    },
    "BlackDespairBanner": {
        "zh-Hans": "绝厄海寇战旗",
        "en": "Black Despair Banner",
        "de": "Banner der Schwarzen Verzweiflung",
        "es": "Estandarte de la Desesperación Negra",
        "fr": "Bannière du Désespoir noir",
        "ja": "ブラック・デスペアの旗",
        "ko": "블랙 디스페어 깃발",
        "pt-BR": "Estandarte do Desespero Negro",
        "ru": "Знамя Чёрного Отчаяния",
        "zh-Hant": "絕厄海寇戰旗",
    },
    "CandleHolder_Bronze": {
        "zh-Hans": "青铜烛台",
        "en": "Bronze Candle Holder",
        "de": "Bronzener Kerzenhalter",
        "es": "Candelabro de bronce",
        "fr": "Bougeoir en bronze",
        "ja": "青銅の燭台",
        "ko": "청동 촛대",
        "pt-BR": "Castical de bronze",
        "ru": "Бронзовый подсвечник",
        "zh-Hant": "青銅燭台",
    },
    "Fireflies": {
        "zh-Hans": "萤火虫",
        "en": "Fireflies",
        "de": "Glühwürmchen",
        "es": "Luciérnagas",
        "fr": "Luciole",
        "ja": "ホタル",
        "ko": "반딧불이",
        "pt-BR": "Vagalumes",
        "ru": "Светлячки",
        "zh-Hant": "螢火蟲",
    },
    "GroundLamp_Lit_01": {
        "zh-Hans": "地面灯",
        "en": "Ground Lamp",
        "de": "Bodenlampe",
        "es": "Lámpara de suelo",
        "fr": "Lampe au sol",
        "ja": "地面のランプ",
        "ko": "바닥 램프",
        "pt-BR": "Luminária de chão",
        "ru": "Напольный светильник",
        "zh-Hant": "地面燈",
    },
    "ExpressmanOtto": {
        "zh-Hans": "快递员奥托",
        "en": "Expressman Otto",
        "de": "Kurier Otto",
        "es": "Mensajero Otto",
        "fr": "Otto le Messager",
        "ja": "配達人オットー",
        "ko": "배달부 오토",
        "pt-BR": "Entregador Otto",
        "ru": "Курьер Отто",
        "zh-Hant": "快遞員奧托",
    },
    "GoblinMelee": {
        "zh-Hans": "哥布林近战",
        "en": "Melee Goblin",
        "de": "Nahkampf-Goblin",
        "es": "Goblin cuerpo a cuerpo",
        "fr": "Gobelin de mêlée",
        "ja": "近接ゴブリン",
        "ko": "근접 고블린",
        "pt-BR": "Goblin corpo a corpo",
        "ru": "Гоблин ближнего боя",
        "zh-Hant": "近戰哥布林",
    },
    "GoblinRanged": {
        "zh-Hans": "哥布林远程",
        "en": "Ranged Goblin",
        "de": "Fernkampf-Goblin",
        "es": "Goblin a distancia",
        "fr": "Gobelin à distance",
        "ja": "遠距離ゴブリン",
        "ko": "원거리 고블린",
        "pt-BR": "Goblin à distância",
        "ru": "Гоблин дальнего боя",
        "zh-Hant": "遠程哥布林",
    },
    "SkeletonMelee": {
        "zh-Hans": "骷髅近战",
        "en": "Melee Skeleton",
        "de": "Nahkampf-Skelett",
        "es": "Esqueleto cuerpo a cuerpo",
        "fr": "Squelette de mêlée",
        "ja": "近接スケルトン",
        "ko": "근접 스켈레톤",
        "pt-BR": "Esqueleto corpo a corpo",
        "ru": "Скелет ближнего боя",
        "zh-Hant": "近戰骷髏",
    },
    "SkeletonRanged": {
        "zh-Hans": "骷髅远程",
        "en": "Ranged Skeleton",
        "de": "Fernkampf-Skelett",
        "es": "Esqueleto a distancia",
        "fr": "Squelette à distance",
        "ja": "遠距離スケルトン",
        "ko": "원거리 스켈레톤",
        "pt-BR": "Esqueleto à distância",
        "ru": "Скелет дальнего боя",
        "zh-Hant": "遠程骷髏",
    },
    "Ruins_DualBossTreasureRoom": {
        "zh-Hans": "双Boss宝藏室",
        "en": "Dual Boss Treasure Room",
        "de": "Schatzkammer der Doppelbosse",
        "es": "Sala del tesoro de doble jefe",
        "fr": "Salle au trésor des deux boss",
        "ja": "双ボスの宝物庫",
        "ko": "이중 보스 보물방",
        "pt-BR": "Sala do tesouro dos dois chefes",
        "ru": "Сокровищница двух боссов",
        "zh-Hant": "雙Boss寶藏室",
    },
    "Ladder": {
        "zh-Hans": "梯子",
        "en": "Ladder",
        "de": "Leiter",
        "es": "Escalera",
        "fr": "Échelle",
        "ja": "はしご",
        "ko": "사다리",
        "pt-BR": "Escada",
        "ru": "Лестница",
        "zh-Hant": "梯子",
    },
    "PlaneFog": {
        "zh-Hans": "平面雾",
        "en": "Plane Fog",
        "de": "Flächennebel",
        "es": "Niebla plana",
        "fr": "Brouillard plan",
        "ja": "平面フォグ",
        "ko": "평면 안개",
        "pt-BR": "Névoa plana",
        "ru": "Плоский туман",
        "zh-Hant": "平面霧",
    },
    "IceWall": {
        "zh-Hans": "冰墙",
        "en": "Ice Wall",
        "de": "Eiswand",
        "es": "Pared de hielo",
        "fr": "Mur de glace",
        "ja": "氷の壁",
        "ko": "얼음벽",
        "pt-BR": "Parede de gelo",
        "ru": "Ледяная стена",
        "zh-Hant": "冰牆",
    },
    "IceFloor": {
        "zh-Hans": "冰面",
        "en": "Ice Floor",
        "de": "Eisfläche",
        "es": "Suelo de hielo",
        "fr": "Sol de glace",
        "ja": "氷の床",
        "ko": "얼음 바닥",
        "pt-BR": "Piso de gelo",
        "ru": "Ледяной пол",
        "zh-Hant": "冰面",
    },
    "IciclesWall": {
        "zh-Hans": "冰柱墙",
        "en": "Icicle Wall",
        "de": "Eiszapfenwand",
        "es": "Pared de carámbanos",
        "fr": "Mur de stalactites de glace",
        "ja": "つららの壁",
        "ko": "고드름 벽",
        "pt-BR": "Parede de estalactites de gelo",
        "ru": "Стена с сосульками",
        "zh-Hant": "冰柱牆",
    },
    "DwarfHandCannoneer": {
        "zh-Hans": "矮人火铳手",
        "en": "Dwarf Hand Cannoneer",
        "de": "Zwergen-Handkanonier",
        "es": "Artillero de mano enano",
        "fr": "Canonnier nain",
        "ja": "ドワーフ・ハンドキャノニア",
        "ko": "드워프 핸드 캐노니어",
        "pt-BR": "Canhoneiro de mão anão",
        "ru": "Ручной канонир-дворф",
        "zh-Hant": "矮人火銃手",
    },
    "Armor_DualBoss": {
        "zh-Hans": "双Boss-护甲",
        "en": "Dual Boss Armor",
        "de": "Doppelboss-Rüstung",
        "es": "Armadura de jefes dobles",
        "fr": "Armure des deux boss",
        "ja": "双ボスの防具",
        "ko": "더블 보스 방어구",
        "pt-BR": "Armadura dos chefes duplos",
        "ru": "Доспехи двух боссов",
        "zh-Hant": "雙Boss-護甲",
    },
    "Armor_Armory": {
        "zh-Hans": "军械库-护甲",
        "en": "Armory Armor",
        "de": "Rüstung der Waffenkammer",
        "es": "Armadura de la armería",
        "fr": "Armure de l'armurerie",
        "ja": "武器庫の防具",
        "ko": "무기고 방어구",
        "pt-BR": "Armadura do arsenal",
        "ru": "Доспехи оружейной",
        "zh-Hant": "軍械庫-護甲",
    },
    "Armor_GoldenRoom": {
        "zh-Hans": "黄金房-护甲",
        "en": "Golden Room Armor",
        "de": "Rüstung der Goldkammer",
        "es": "Armadura de la sala dorada",
        "fr": "Armure de la salle dorée",
        "ja": "黄金部屋の防具",
        "ko": "황금 방 방어구",
        "pt-BR": "Armadura da sala dourada",
        "ru": "Доспехи золотой комнаты",
        "zh-Hant": "黃金房-護甲",
    },
    "Weapon_DualBoss": {
        "zh-Hans": "双Boss-武器",
        "en": "Dual Boss Weapon",
        "de": "Doppelboss-Waffe",
        "es": "Arma de jefes dobles",
        "fr": "Arme des deux boss",
        "ja": "双ボス部屋の武器",
        "ko": "쌍둥이 보스 방 무기",
        "pt-BR": "Arma dos chefes duplos",
        "ru": "Оружие двух боссов",
        "zh-Hant": "雙Boss-武器",
    },
    "Weapon_MysticalTreasureRoom": {
        "zh-Hans": "神秘宝藏房-武器",
        "en": "Mystical Treasure Room Weapon",
        "de": "Waffe der mystischen Schatzkammer",
        "es": "Arma de la sala del tesoro místico",
        "fr": "Arme de la salle au trésor mystique",
        "ja": "神秘の宝物庫の武器",
        "ko": "신비한 보물방 무기",
        "pt-BR": "Arma da sala do tesouro místico",
        "ru": "Оружие мистической сокровищницы",
        "zh-Hant": "神秘寶藏房-武器",
    },
    "Weapon": {
        "zh-Hans": "武器",
        "en": "Weapon",
        "de": "Waffe",
        "es": "Arma",
        "fr": "Arme",
        "ja": "武器",
        "ko": "무기",
        "pt-BR": "Arma",
        "ru": "Оружие",
        "zh-Hant": "武器",
    },
    "Weapon_GoldenRoom": {
        "zh-Hans": "黄金房-武器",
        "en": "Golden Room Weapon",
        "de": "Waffe der goldenen Kammer",
        "es": "Arma de la sala dorada",
        "fr": "Arme de la salle dorée",
        "ja": "黄金部屋の武器",
        "ko": "황금 방 무기",
        "pt-BR": "Arma da sala dourada",
        "ru": "Оружие золотой комнаты",
        "zh-Hant": "黃金房-武器",
    },
    "DwarfSecretWeapon": {
        "zh-Hans": "矮人秘密武器",
        "en": "Dwarven Secret Weapon",
        "de": "Geheime Zwergenwaffe",
        "es": "Arma secreta enana",
        "fr": "Arme secrète naine",
        "ja": "ドワーフの秘密兵器",
        "ko": "드워프 비밀 무기",
        "pt-BR": "Arma secreta anã",
        "ru": "Секретное оружие дворфов",
        "zh-Hant": "矮人秘密武器",
    },
    "Weapon_FrozenRoom": {
        "zh-Hans": "冰封房-武器",
        "en": "Frozen Room Weapon",
        "de": "Waffe der gefrorenen Kammer",
        "es": "Arma de la sala helada",
        "fr": "Arme de la salle gelée",
        "ja": "氷結部屋の武器",
        "ko": "얼어붙은 방 무기",
        "pt-BR": "Arma da sala congelada",
        "ru": "Оружие ледяной комнаты",
        "zh-Hant": "冰封房-武器",
    },
    "Weapon_SkullRoom": {
        "zh-Hans": "骷髅房-武器",
        "en": "Skull Room Weapon",
        "de": "Waffe der Schädelkammer",
        "es": "Arma de la sala de calaveras",
        "fr": "Arme de la salle des crânes",
        "ja": "頭蓋骨部屋の武器",
        "ko": "해골 방 무기",
        "pt-BR": "Arma da sala de caveiras",
        "ru": "Оружие комнаты черепов",
        "zh-Hant": "骷髏房-武器",
    },
    "Weapon_Rare": {
        "zh-Hans": "稀有武器",
        "en": "Rare Weapon",
        "de": "Seltene Waffe",
        "es": "Arma rara",
        "fr": "Arme rare",
        "ja": "レア武器",
        "ko": "희귀 무기",
        "pt-BR": "Arma rara",
        "ru": "Редкое оружие",
        "zh-Hant": "稀有武器",
    },
}


def _english_hardcoded_name(name: str) -> str:
    """Produce a readable non-Chinese fallback when the game has no locale key."""
    spaced = name.replace("_", " ")
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", spaced)
    spaced = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", " ", spaced)
    return re.sub(r"\s+", " ", spaced).strip().title()


def hardcoded_translation_key(name: str) -> str | None:
    """Return a stable synthetic locale key for an entity without a Game.json key."""
    canonical_name = HARDCODED_TRANSLATION_KEY_ALIASES.get(name, name)
    if canonical_name in HARDCODED_TRANSLATIONS:
        return f"{HARDCODED_I18N_PREFIX}{canonical_name}"
    return None


def hardcoded_locale_entries(lang: str, used_keys: set[str]) -> dict[str, str]:
    """Build synthetic locale entries only for hardcoded entities present in output."""
    return {
        key: HARDCODED_LOCALE_OVERRIDES.get(name, {}).get(lang)
        or (value if lang == "zh-Hans" else TECHNICAL_LOCALE_PREFIXES.get(lang, "") + _english_hardcoded_name(name))
        for name, value in HARDCODED_TRANSLATIONS.items()
        if (key := hardcoded_translation_key(name)) in used_keys
    }


# SuperHoard* has no Game.json key — synthetic i18n key + 10-lang full phrases
SUPERHOARD_I18N_KEY = "df5.hardcoded.SuperHoard"
SUPERHOARD_ENTITY_NAMES = frozenset(
    {
        "SuperHoard",
        "SuperHoardChest",
        "SuperHoardChest01",
        "SuperHoard01_9",
        "SuperHoardChest01_9",
    }
)
SUPERHOARD_I18N: dict[str, str] = {
    "zh-Hans": "超级宝藏堆",
    "zh-Hant": "超級寶藏堆",
    "en": "Super Treasure Hoard",
    "de": "Super-Schatzhort",
    "es": "Super Pila del Tesoro",
    "fr": "Super Pile de Trésors",
    "ja": "スーパー財宝の山",
    "ko": "슈퍼 보물 더미",
    "pt-BR": "Super Pilha de Tesouros",
    "ru": "Супер Гора Сокровищ",
}


def superhoard_translation_key(name: str) -> str | None:
    """Return synthetic i18n key if name is a SuperHoard* entity."""
    if name in SUPERHOARD_ENTITY_NAMES or name.startswith("SuperHoard"):
        return SUPERHOARD_I18N_KEY
    return None


MODULE_NAME_OVERRIDE = {
    "EmptyModule_1F_14": "3-1",
    "EmptyModule_1F_09": "5-1",
    "EmptyModule_1F_15": "7-4",
    "EmptyModule_1F_13": "6-5",
}

MODULE_DISPLAY_OVERRIDE = {
    "ShipGraveyard_BladehandRefuge": {"size_x": 2, "size_y": 2, "range": 3200},
    "ShipGraveyard_ElephantIsland": {"size_x": 1, "size_y": 2},
    "ShipGraveyard_Hole": {"size_x": 2, "size_y": 2, "range": 4800},
    "ShipGraveyard_HangingShip": {"size_x": 2, "size_y": 1},
}

MODULE_OFFSET_MAP = {
    # 2x2 modules
    "CenterTower": (-1600, -1600),
    "IceAbyss_WyvernLair": (-1600, -1600),
    "ShipGraveyard_BladehandRefuge": (-1600, -1600),
    "ShipGraveyard_Hole": (0, 0),
    "ShipGraveyard_PiratePrison": (-3200, 3200),
    "ShipGraveyard_SkullIsland": (1600, 1600),
    # 1x2 modules
    "IceCave_Hive_03": (-1600, -1600),
    "Ruins_TowerBridge_Destroyed": (-1600, -1600),
    "ShipGraveyard_AbandonedShip_01": (-1600, -1600),
    "ShipGraveyard_ElephantIsland": (-1600, 1600),
    "ShipGraveyard_FloatingVillage": (-1600, 1600),
    "ShipGraveyard_HangingShip": (1600, 0),
}

GROUP_TO_ART_DIR = {
    "GoblinCave": "Cave",
    "IceCavern": "IceCave",
    "FireDeep": "FireDeep",
    "Crypt": "Crypt",
    "IceAbyss": "IceAbyss",
    "Inferno": "Inferno",
    "Ruins": "Ruins",
    "ShipGraveyard": "ShipGraveyard",
}

# module_group → 楼层后缀列表（用于爆率查询）
# 后缀 = base_code + floor - 1，如 FireDeep 的 base_code=1, floor=2 → 后缀=2
# base_code 编码规则参见 _archived/dungeon_grades.py
MODULE_GROUP_FLOOR_SUFFIXES: dict[str, list[int]] = {
    "GoblinCave": [1],
    "FireDeep": [2],
    "IceCavern": [11],
    "IceAbyss": [12],
    "Ruins": [21],
    "Crypt": [22],
    "Inferno": [23],
    "ShipGraveyard": [31, 32],
}

DUNGEON_MODE_NAMES = {
    1: "PVE",
    2: "普通",
    3: "豪客赛",
    4: "逆袭赛",
}

LAYOUT_DIR = GAME_ROOT / "Maps" / "Dungeon" / "Layouts"
