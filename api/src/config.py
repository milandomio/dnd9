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

ITEM_DIR = DATA_DIR / "Item" / "Item"
MONSTER_DIR = DATA_DIR / "Monster" / "Monster"
PROPS_DIR = DATA_DIR / "Props" / "Props"
LOOTDROP_DIR = DATA_DIR / "LootDrop" / "LootDrop"
LOOTDROP_GROUP_DIR = DATA_DIR / "LootDrop" / "LootDropGroup"
DUNGEON_MODULE_DIR = DATA_DIR / "Dungeon" / "DungeonModule"
SPAWNER_DIR = DATA_DIR / "Spawner" / "Spawner"
ART_DIR = DATA_DIR / "Art"

# DB 文件
DB_PATH = API_DIR / "data" / "darkfindv5.db"
# JSON 输出（collector 写入到此）
OUTPUT_DIR = API_DIR / "output" / "json"
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
    "SuperHoard": "超级宝藏",
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
    "SuperHoard01_9": "超级宝藏",
    "SuperHoardChest01_9": "超级宝藏箱",
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
}

MODULE_NAME_OVERRIDE = {
    "EmptyModule_1F_14": "3-1模块",
    "EmptyModule_1F_09": "5-1模块",
    "EmptyModule_1F_15": "7-4模块",
    "EmptyModule_1F_13": "6-5模块",
}

MODULE_DISPLAY_OVERRIDE = {
    "ShipGraveyard_BladehandRefuge": {"size_x": 2, "size_y": 2, "range": 3200},
    "ShipGraveyard_Hole": {"size_x": 2, "size_y": 2, "range": 4800},
    "ShipGraveyard_HangingShip": {"size_x": 2, "size_y": 1},
}

MODULE_OFFSET_MAP = {
    # 2x2 modules
    "CenterTower": (-1600, -1600),
    "IceAbyss_WyvernLair": (1600, -1600),
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

LAYOUT_DIR = GAME_ROOT / "Maps" / "Dungeon" / "Layouts"
