from pathlib import Path

BACKEND_DIR = Path(__file__).parent
PROJECT_DIR = BACKEND_DIR.parent
OUTPUT_DIR = BACKEND_DIR / "output"

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
