from pathlib import Path

BACKEND_DIR = Path(__file__).parent
PROJECT_DIR = BACKEND_DIR.parent
OUTPUT_DIR = BACKEND_DIR / "data"

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

DB_PATH = BACKEND_DIR / "darkfind.db"

TRANSLATION_ALIAS_MAP = {
    "GoldChest": "GoldenChest",
    "Corpse": "SkeletonCorpse",
    "CrateSmall": "WoodenCrateSmall",
    "CrateMedium": "WoodenCrateMedium",
    "CandleHolder": "GoldCandleHolder",
    "Chalice": "GoldChaliceA",
    "Coin": "AntiquatedCoin",
    "Cloak": "AdventurerCloak",
}

HARDCODED_TRANSLATIONS = {
    "Barrel": "木桶",
    "Bones": "骸骨",
    "Ground": "地面",
    "Accessory_OldRustRoom": "旧锈房-饰品",
    "AntiquatedCoin_01": "古钱币01",
    "AntiquatedCoin_02": "古钱币02",
    "AntiquatedCoin_03": "古钱币03",
    "AntiquatedCoin_04": "古钱币04",
    "Armor_Armory": "军械库-护甲",
    "Armor_DualBoss": "双Boss-护甲",
    "Armor_GoldenRoom": "黄金房-护甲",
    "BlackRose_N": "黑玫瑰",
    "Coffin_Casket": "棺材",
    "Coffin_Common": "普通棺材",
    "Coffin_Poor": "破旧棺材",
    "Coffin_Royal": "皇家棺材",
    "Gems": "宝石",
    "SuperHoard": "超级宝藏",
    "Trinkets": "小饰品",
    "Weapon": "武器",
    "Weapon_Common": "普通武器",
    "Weapon_DualBoss": "双Boss-武器",
    "Weapon_FrozenRoom": "冰封房-武器",
    "Weapon_GoldenRoom": "黄金房-武器",
    "Weapon_MysticalTreasureRoom": "神秘宝藏房-武器",
    "Weapon_Rare": "稀有武器",
    "Weapon_SkullRoom": "骷髅房-武器",
    "DwarfSecretWeapon": "矮人秘密武器",
    "WoodenBarrel_UnderSea": "海底木桶",
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

LAYOUT_DIR = GAME_ROOT / "Maps" / "Dungeon" / "Layouts"
