from pathlib import Path

# api/src/
SRC_DIR = Path(__file__).parent
# api/
API_DIR = SRC_DIR.parent
# DarkFindV5/
PROJECT_DIR = API_DIR.parent

GAME_ROOT = (
    PROJECT_DIR.parent
    / "Output"
    / "Exports"
    / "DungeonCrawler"
    / "Content"
    / "DungeonCrawler"
)
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
    "PushingBlock": "推块",
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
    "LivingStatue_Elite": "精英石像鬼",
    "LivingStatue_Nightmare": "噩梦石像鬼",
}

MODULE_NAME_OVERRIDE = {
    "EmptyModule_1F_14": "3-1模块",
    "EmptyModule_1F_09": "5-1模块",
    "EmptyModule_1F_15": "7-4模块",
    "EmptyModule_1F_13": "6-5模块",
}

MODULE_DISPLAY_OVERRIDE = {
    "ShipGraveyard_Hole": {"size_x": 2, "size_y": 2, "range": 4800},
    "ShipGraveyard_HangingShip": {"size_x": 2, "size_y": 1},
}

MODULE_OFFSET_MAP = {
    "ShipGraveyard_PiratePrison": (-3200, 3200),
    "ShipGraveyard_BladehandRefuge": (-1600, -1600),
    "ShipGraveyard_HangingShip": (1600, 0),
    "Inferno_Hellcrossbridge": (-600, 300),
    "Inferno_Judgementroad": (-1000, -1000),
    "Inferno_Painfulsteps": (-800, 0),
    "IceAbyss_WyvernLair": (1600, -2400),
    "CenterTower": (-1600, -1600),
    "IceCave_Watchtower": (-150, 900),
    "IceCave_Hive_03": (-1600, -1600),
    "IceAbyss_IceMaze": (-1150, 0),
    "Firedeep_BlazeTunnel": (0, -500),
    "Ruins_TowerBridge_Destroyed": (-1600, -1600),
    "ShipGraveyard_SkullIsland": (1600, 1600),
    "ShipGraveyard_AbandonedShip_01": (-1600, -1600),
    "ShipGraveyard_ElephantIsland": (-1600, 1600),
    "ShipGraveyard_FloatingVillage": (-1600, 1600),
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
