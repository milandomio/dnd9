"""Build loot_pools for monster and props detail JSON."""

from __future__ import annotations

import json
import re

from config import HARDCODED_TRANSLATIONS
from translator import ORE_QUALITY_RE, QUALITY_RE, VARIANT_RE

_LOOTDROP_PREFIXES = ("Id_Lootdrop_", "ID_Lootdrop_")
_LUCK_TO_SUFFIX = {n: f"{n}001" for n in range(1, 9)}
_CONSUMABLE_SUBTYPE = "Text_Code_DCDataBlueprintLibrary_Type_Item_Utility_Consumable"
_POOL_DROP_PREFIX_RE = re.compile(r"^(?:Drop|Spawn|Monster)_", re.IGNORECASE)
_POOL_QUEST_PREFIX_RE = re.compile(r"^Quest(?:Item|Special)_", re.IGNORECASE)
_POOL_SPOILS_SUFFIX_RE = re.compile(r"_Spoils$", re.IGNORECASE)

# Lootdrop pool names that name an item category rather than an entity.
# Their display text comes from the item-category translation keys.
_POOL_CATEGORY_KEYS = {
    "ChestArmors": "Text_Code_DCDataBlueprintLibrary_Type_Item_Category_Armor",
    "Cloak_All": "Text_DesignData_Item_Item_Cloak",
    "Cloak_Magic": "Text_DesignData_Item_Item_Cloak",
    "Cloak_Physical": "Text_DesignData_Item_Item_Cloak",
    "Coin": "Text_DesignData_Item_Item_GoldCoins",
    "Gems": "Text_Code_DCDataBlueprintLibrary_Type_Item_Misc_Gem",
    "Trinkets": "Text_Code_DCDataBlueprintLibrary_Type_Item_Category_Accessory",
    "Weapon": "Text_Code_DCDataBlueprintLibrary_Type_Item_Category_Weapon",
    "Consumables": "Text_Code_DCDataBlueprintLibrary_Type_Item_Utility_Consumable",
}

# Lootdrop pool names that name a container prop rather than an entity.
_POOL_PROP_KEYS = {
    "Barrels": "Text_DesignData_Props_Props_WoodBarrel",
    "Crates": "Text_DesignData_Props_Props_WoodenCrateSmall",
    "CommonCoffins": "Text_DesignData_Props_Props_Coffin_01",
    "Caskets": "Text_DesignData_Props_Props_SimpleChestLarge",
    "FlatChestLarge": "Text_DesignData_Props_Props_FlatChestLarge",
    "HoardTreasure": "Text_DesignData_Props_Props_Hoard",
}

# Lootdrop pool names with no Game.json key at all. These are display labels
# only (never entity names), so they get a synthetic locale key plus the
# 10-language phrases used elsewhere for hardcoded entities.
POOL_LABEL_I18N_PREFIX = "df5.lootpool."
POOL_LABEL_TRANSLATIONS: dict[str, dict[str, str]] = {
    "Cloak_All": {
        "zh-Hans": "披风",
        "zh-Hant": "披風",
        "en": "Cloaks",
        "de": "Umhänge",
        "es": "Capas",
        "fr": "Capes",
        "ja": "クローク",
        "ko": "망토",
        "pt-BR": "Capas",
        "ru": "Плащи",
    },
    "Cloak_Magic": {
        "zh-Hans": "魔法披风",
        "zh-Hant": "魔法披風",
        "en": "Magic Cloaks",
        "de": "Magische Umhänge",
        "es": "Capas mágicas",
        "fr": "Capes magiques",
        "ja": "魔法のクローク",
        "ko": "마법 망토",
        "pt-BR": "Capas mágicas",
        "ru": "Магические плащи",
    },
    "Cloak_Physical": {
        "zh-Hans": "物理披风",
        "zh-Hant": "物理披風",
        "en": "Physical Cloaks",
        "de": "Physische Umhänge",
        "es": "Capas físicas",
        "fr": "Capes physiques",
        "ja": "物理のクローク",
        "ko": "물리 망토",
        "pt-BR": "Capas físicas",
        "ru": "Физические плащи",
    },
    "Treasure": {
        "zh-Hans": "宝藏",
        "zh-Hant": "寶藏",
        "en": "Treasure",
        "de": "Schatz",
        "es": "Tesoro",
        "fr": "Trésor",
        "ja": "宝",
        "ko": "보물",
        "pt-BR": "Tesouro",
        "ru": "Сокровище",
    },
    "Treasure_Both": {
        "zh-Hans": "宝藏",
        "zh-Hant": "寶藏",
        "en": "Treasure",
        "de": "Schatz",
        "es": "Tesoro",
        "fr": "Trésor",
        "ja": "宝",
        "ko": "보물",
        "pt-BR": "Tesouro",
        "ru": "Сокровище",
    },
    "Treasure_Large": {
        "zh-Hans": "大型宝藏",
        "zh-Hant": "大型寶藏",
        "en": "Large Treasure",
        "de": "Großer Schatz",
        "es": "Tesoro grande",
        "fr": "Grand trésor",
        "ja": "大きな宝",
        "ko": "대형 보물",
        "pt-BR": "Tesouro grande",
        "ru": "Большое сокровище",
    },
    "Utility": {
        "zh-Hans": "工具",
        "zh-Hant": "工具",
        "en": "Utility",
        "de": "Werkzeuge",
        "es": "Utilidad",
        "fr": "Utilitaires",
        "ja": "道具",
        "ko": "도구",
        "pt-BR": "Utilidade",
        "ru": "Инструменты",
    },
    "LootGoblin_StolenGoods": {
        "zh-Hans": "赃物",
        "zh-Hant": "贓物",
        "en": "Stolen Goods",
        "de": "Diebesgut",
        "es": "Bienes robados",
        "fr": "Biens volés",
        "ja": "盗品",
        "ko": "도난품",
        "pt-BR": "Bens roubados",
        "ru": "Краденое",
    },
    "LootGoblin_GoldContainer": {
        "zh-Hans": "金币容器",
        "zh-Hant": "金幣容器",
        "en": "Gold Container",
        "de": "Goldbehälter",
        "es": "Contenedor de oro",
        "fr": "Conteneur d'or",
        "ja": "金貨容器",
        "ko": "금화 용기",
        "pt-BR": "Contenedor de ouro",
        "ru": "Контейнер с золотом",
    },
    "GradedRoll_Ruby": {
        "zh-Hans": "红宝石",
        "zh-Hant": "紅寶石",
        "en": "Ruby",
        "de": "Rubin",
        "es": "Rubí",
        "fr": "Rubis",
        "ja": "ルビー",
        "ko": "루비",
        "pt-BR": "Rubi",
        "ru": "Рубин",
    },
    "GradedRoll_Emerald": {
        "zh-Hans": "绿宝石",
        "zh-Hant": "綠寶石",
        "en": "Emerald",
        "de": "Smaragd",
        "es": "Esmeralda",
        "fr": "Émeraude",
        "ja": "エメラルド",
        "ko": "에메랄드",
        "pt-BR": "Esmeralda",
        "ru": "Изумруд",
    },
    "GradedRoll_BlueSapphire": {
        "zh-Hans": "蓝宝石",
        "zh-Hant": "藍寶石",
        "en": "Blue Sapphire",
        "de": "Blauer Saphir",
        "es": "Zafiro azul",
        "fr": "Saphir bleu",
        "ja": "ブルーサファイア",
        "ko": "블루 사파이어",
        "pt-BR": "Safira azul",
        "ru": "Синий сапфир",
    },
    "GradedRoll_Diamond": {
        "zh-Hans": "钻石",
        "zh-Hant": "鑽石",
        "en": "Diamond",
        "de": "Diamant",
        "es": "Diamante",
        "fr": "Diamant",
        "ja": "ダイヤモンド",
        "ko": "다이아몬드",
        "pt-BR": "Diamante",
        "ru": "Алмаз",
    },
    "GradedRoll_ArcaneEssence": {
        "zh-Hans": "秘术精华",
        "zh-Hant": "秘術精華",
        "en": "Arcane Essence",
        "de": "Arkane Essenz",
        "es": "Esencia arcana",
        "fr": "Essence arcanique",
        "ja": "秘術のエッセンス",
        "ko": "비전의 정수",
        "pt-BR": "Essência arcana",
        "ru": "Тайная эссенция",
    },
    "GradedRoll_CrackedTrinkets": {
        "zh-Hans": "裂开的饰品",
        "zh-Hant": "裂開的飾品",
        "en": "Cracked Trinkets",
        "de": "Rissige Schmuckstücke",
        "es": "Abalorios agrietados",
        "fr": "Bijoux fissurés",
        "ja": "割れたアクセサリー",
        "ko": "금간 장신구",
        "pt-BR": "Berloques rachados",
        "ru": "Треснувшие безделушки",
    },
    "Accessory_Rare": {
        "zh-Hans": "稀有饰品",
        "zh-Hant": "稀有飾品",
        "en": "Rare Accessories",
        "de": "Seltene Accessoires",
        "es": "Accesorios raros",
        "fr": "Accessoires rares",
        "ja": "レアアクセサリー",
        "ko": "희귀 장신구",
        "pt-BR": "Acessórios raros",
        "ru": "Редкие аксессуары",
    },
    "Quiver": {
        "zh-Hans": "箭袋",
        "zh-Hant": "箭袋",
        "en": "Quiver",
        "de": "Köcher",
        "es": "Carcaj",
        "fr": "Carquois",
        "ja": "矢筒",
        "ko": "화살통",
        "pt-BR": "Aljava",
        "ru": "Колчан",
    },
    "SkeletonSwordsman": {
        "zh-Hans": "骷髅剑士",
        "zh-Hant": "骷髏劍士",
        "en": "Skeleton Swordsman",
        "de": "Skelett-Schwertkämpfer",
        "es": "Espadachín esqueleto",
        "fr": "Squelette escrimeur",
        "ja": "スケルトン剣士",
        "ko": "해골 검사",
        "pt-BR": "Esqueleto espadachim",
        "ru": "Скелет-мечник",
    },
    "SkeletonCorpses": {
        "zh-Hans": "骷髅尸骸",
        "zh-Hant": "骷髏屍骸",
        "en": "Skeleton Corpses",
        "de": "Skelett-Leichen",
        "es": "Cadáveres esqueleto",
        "fr": "Cadavres de squelette",
        "ja": "スケルトンの死体",
        "ko": "해골 시체",
        "pt-BR": "Corpos de esqueleto",
        "ru": "Скелеты-трупы",
    },
    "SkeletonBones": {
        "zh-Hans": "骸骨",
        "zh-Hant": "骸骨",
        "en": "Bones",
        "de": "Knochen",
        "es": "Huesos",
        "fr": "Os",
        "ja": "骨",
        "ko": "뼈",
        "pt-BR": "Ossos",
        "ru": "Кости",
    },
    "Crate_Supplies": {
        "zh-Hans": "木箱补给",
        "zh-Hant": "木箱補給",
        "en": "Supply Crates",
        "de": "Vorratskisten",
        "es": "Cajas de suministros",
        "fr": "Caisses de ravitaillement",
        "ja": "補給木箱",
        "ko": "보급 상자",
        "pt-BR": "Caixas de suprimentos",
        "ru": "Ящики с припасами",
    },
    "Barrel_Junk": {
        "zh-Hans": "杂物桶",
        "zh-Hant": "雜物桶",
        "en": "Junk Barrels",
        "de": "Trümmerfässer",
        "es": "Barriles de chatarra",
        "fr": "Tonneaux de rebuts",
        "ja": "がらくた樽",
        "ko": "잡동사니 통",
        "pt-BR": "Barris de sucata",
        "ru": "Бочки с хламом",
    },
    "Barrel_Stores": {
        "zh-Hans": "储物桶",
        "zh-Hant": "儲物桶",
        "en": "Storage Barrels",
        "de": "Vorratsfässer",
        "es": "Barriles de almacenamiento",
        "fr": "Tonneaux de stockage",
        "ja": "貯蔵樽",
        "ko": "저장 통",
        "pt-BR": "Barris de armazenamento",
        "ru": "Бочки с запасами",
    },
    "PoorCoffins": {
        "zh-Hans": "简陋棺材",
        "zh-Hant": "簡陋棺材",
        "en": "Poor Coffins",
        "de": "Armselige Särge",
        "es": "Ataúdes pobres",
        "fr": "Cercueils modestes",
        "ja": "粗末な棺",
        "ko": "조잡한 관",
        "pt-BR": "Caixões pobres",
        "ru": "Убогие гробы",
    },
    "Stonetombs": {
        "zh-Hans": "石墓",
        "zh-Hant": "石墓",
        "en": "Stone Tombs",
        "de": "Steingräber",
        "es": "Tumbas de piedra",
        "fr": "Tombeaux de pierre",
        "ja": "石の墓",
        "ko": "석묘",
        "pt-BR": "Túmulos de pedra",
        "ru": "Каменные гробницы",
    },
    "Herbs": {
        "zh-Hans": "草药",
        "zh-Hant": "草藥",
        "en": "Herbs",
        "de": "Kräuter",
        "es": "Hierbas",
        "fr": "Herbes",
        "ja": "薬草",
        "ko": "약초",
        "pt-BR": "Ervas",
        "ru": "Травы",
    },
    "Pants": {
        "zh-Hans": "裤子",
        "zh-Hant": "褲子",
        "en": "Pants",
        "de": "Hosen",
        "es": "Pantalones",
        "fr": "Pantalons",
        "ja": "ズボン",
        "ko": "바지",
        "pt-BR": "Calças",
        "ru": "Штаны",
    },
    "Pots": {
        "zh-Hans": "罐子",
        "zh-Hant": "罐子",
        "en": "Pots",
        "de": "Töpfe",
        "es": "Ollas",
        "fr": "Pots",
        "ja": "壺",
        "ko": "항아리",
        "pt-BR": "Vasos",
        "ru": "Горшки",
    },
    "Utility_CrateMedium": {
        "zh-Hans": "中型木箱道具",
        "zh-Hant": "中型木箱道具",
        "en": "Medium Crate Utility",
        "de": "Mittlere Kisten-Werkzeuge",
        "es": "Utilidad de caja mediana",
        "fr": "Utilitaires de caisse moyenne",
        "ja": "中型木箱の道具",
        "ko": "중형 상자 도구",
        "pt-BR": "Utilidades de caixa média",
        "ru": "Инструменты среднего ящика",
    },
    "Trinkets_NoCoin": {
        "zh-Hans": "饰品（不含金币）",
        "zh-Hant": "飾品（不含金幣）",
        "en": "Trinkets (No Coin)",
        "de": "Schmuckstücke (ohne Münzen)",
        "es": "Abalorios (sin monedas)",
        "fr": "Bijoux (sans pièces)",
        "ja": "アクセサリー（金貨なし）",
        "ko": "장신구 (동전 없음)",
        "pt-BR": "Berloques (sem moedas)",
        "ru": "Безделушки (без монет)",
    },
    "HoardWeaponArmor": {
        "zh-Hans": "宝藏武器护甲",
        "zh-Hant": "寶藏武器護甲",
        "en": "Hoard Weapon & Armor",
        "de": "Hort-Waffen & Rüstung",
        "es": "Armas y armadura del tesoro",
        "fr": "Armes et armure du trésor",
        "ja": "宝物の武器と鎧",
        "ko": "보물 무기 및 방어구",
        "pt-BR": "Armas e armaduras do tesouro",
        "ru": "Оружие и броня из клада",
    },
    "Spawn_GoldCoinChest": {
        "zh-Hans": "金币宝箱",
        "zh-Hant": "金幣寶箱",
        "en": "Gold Coin Chest",
        "de": "Goldmünzen-Truhe",
        "es": "Cofre de monedas de oro",
        "fr": "Coffre de pièces d'or",
        "ja": "金貨の宝箱",
        "ko": "금화 보물상자",
        "pt-BR": "Baú de moedas de ouro",
        "ru": "Сундук с золотыми монетами",
    },
    "Cyclops_TrollBlood": {
        "zh-Hans": "独眼巨人之血",
        "zh-Hant": "獨眼巨人之血",
        "en": "Cyclops Troll Blood",
        "de": "Zyklopen-Trollblut",
        "es": "Sangre de trol cíclope",
        "fr": "Sang de troll cyclope",
        "ja": "サイクロプスのトロールの血",
        "ko": "키클롭스 트롤의 피",
        "pt-BR": "Sangue de troll ciclope",
        "ru": "Кровь тролля-циклопа",
    },
    "IceKoboldBowman": {
        "zh-Hans": "冰霜狗头人弓手",
        "zh-Hant": "冰霜狗頭人弓手",
        "en": "Ice Kobold Bowman",
        "de": "Eiskobold-Bogenschütze",
        "es": "Arquero kobold de hielo",
        "fr": "Archer kobold des glaces",
        "ja": "氷のコボルド弓兵",
        "ko": "얼음 코볼드 궁수",
        "pt-BR": "Arqueiro kobold de gelo",
        "ru": "Ледяной кобольд-лучник",
    },
    "IceHarpy_Jewelry": {
        "zh-Hans": "冰霜鹰身女妖首饰",
        "zh-Hant": "冰霜鷹身女妖首飾",
        "en": "Ice Harpy Jewelry",
        "de": "Eisharpyen-Schmuck",
        "es": "Joyas de arpía de hielo",
        "fr": "Bijoux de harpie des glaces",
        "ja": "氷のハーピーの宝飾品",
        "ko": "얼음 하피 장신구",
        "pt-BR": "Joias de harpia de gelo",
        "ru": "Украшения ледяной гарпии",
    },
    "Whitewalker": {
        "zh-Hans": "白行者",
        "zh-Hant": "白行者",
        "en": "Whitewalker",
        "de": "Weißwandler",
        "es": "Caminante blanco",
        "fr": "Marcheur blanc",
        "ja": "ホワイトウォーカー",
        "ko": "화이트워커",
        "pt-BR": "Caminhante branco",
        "ru": "Белый ходок",
    },
    "WebSpider": {
        "zh-Hans": "网蛛",
        "zh-Hant": "網蛛",
        "en": "Web Spider",
        "de": "Netzspinne",
        "es": "Araña de telaraña",
        "fr": "Araignée des toiles",
        "ja": "ウェブスパイダー",
        "ko": "거미줄 거미",
        "pt-BR": "Aranha-teia",
        "ru": "Паук-тенётник",
    },
    "Banshee2": {
        "zh-Hans": "报丧女妖",
        "zh-Hant": "報喪女妖",
        "en": "Banshee",
        "de": "Banshee",
        "es": "Banshee",
        "fr": "Banshee",
        "ja": "バンシー",
        "ko": "밴시",
        "pt-BR": "Banshee",
        "ru": "Банши",
    },
    "FlameButterflyUnique": {
        "zh-Hans": "赤焰蝶（独特）",
        "zh-Hant": "赤焰蝶（獨特）",
        "en": "Flame Butterfly (Unique)",
        "de": "Flammenschmetterling (Einzigartig)",
        "es": "Mariposa de llama (única)",
        "fr": "Papillon de flamme (unique)",
        "ja": "炎の蝶（ユニーク）",
        "ko": "불꽃 나비 (고유)",
        "pt-BR": "Borboleta de chama (única)",
        "ru": "Пламенная бабочка (уникальная)",
    },
    "Slime_Quest": {
        "zh-Hans": "史莱姆任务",
        "zh-Hant": "史萊姆任務",
        "en": "Slime Quest",
        "de": "Schleim-Quest",
        "es": "Misión de slime",
        "fr": "Quête de slime",
        "ja": "スライムクエスト",
        "ko": "슬라임 퀘스트",
        "pt-BR": "Missão de slime",
        "ru": "Задание слизи",
    },
    "Spoils": {
        "zh-Hans": "战利品",
        "zh-Hant": "戰利品",
        "en": "Loot",
        "de": "Beute",
        "es": "Botín",
        "fr": "Butin",
        "ja": "戦利品",
        "ko": "전리품",
        "pt-BR": "Saque",
        "ru": "Добыча",
    },
    "Gear": {
        "zh-Hans": "装备",
        "zh-Hant": "裝備",
        "en": "Gear",
        "de": "Ausrüstung",
        "es": "Equipo",
        "fr": "Équipement",
        "ja": "装備",
        "ko": "장비",
        "pt-BR": "Equipamento",
        "ru": "Снаряжение",
    },
    "Jewelry": {
        "zh-Hans": "首饰",
        "zh-Hant": "首飾",
        "en": "Jewelry",
        "de": "Schmuck",
        "es": "Joyería",
        "fr": "Bijoux",
        "ja": "宝飾品",
        "ko": "장신구",
        "pt-BR": "Joias",
        "ru": "Украшения",
    },
    "Ore": {
        "zh-Hans": "矿石",
        "zh-Hant": "礦石",
        "en": "Ore",
        "de": "Erz",
        "es": "Mineral",
        "fr": "Minerai",
        "ja": "鉱石",
        "ko": "광석",
        "pt-BR": "Minério",
        "ru": "Руда",
    },
    "Misc": {
        "zh-Hans": "杂项",
        "zh-Hant": "雜項",
        "en": "Misc",
        "de": "Sonstiges",
        "es": "Varios",
        "fr": "Divers",
        "ja": "その他",
        "ko": "기타",
        "pt-BR": "Diversos",
        "ru": "Разное",
    },
}


def fold_item_page(item_name: str) -> tuple[str, str | None]:
    """Map a rate-table item name to the lootdrop JSON filename and suffix."""
    match = VARIANT_RE.match(item_name)
    if not match:
        return item_name, None
    suffix = match.group(0).rsplit("_", 1)[-1]
    if suffix == "8001":
        return item_name, suffix
    return match.group(1), suffix


def lootdrop_stem(lootdrop_id: str) -> str:
    lower = lootdrop_id.lower()
    for prefix in _LOOTDROP_PREFIXES:
        if lower.startswith(prefix.lower()):
            return lootdrop_id[len(prefix) :]
    return lootdrop_id


def is_quest_pool(lootdrop_id: str) -> bool:
    stem = lootdrop_stem(lootdrop_id)
    return stem.startswith("Quest_") or stem.startswith("QuestSpecial_")


def is_event_currency_pool(lootdrop_id: str) -> bool:
    stem = lootdrop_stem(lootdrop_id)
    return "EventCurrency" in stem


def pool_core_name(lootdrop_id: str) -> str:
    """Pool name without the Lootdrop prefix and the Drop_/Spawn_ marker."""
    stem = lootdrop_stem(lootdrop_id)
    return _POOL_DROP_PREFIX_RE.sub("", _POOL_QUEST_PREFIX_RE.sub("", stem))


_ENTITY_KEY_PREFIXES = (
    "Text_DesignData_Item_Item_",
    "Text_DesignData_Monster_Monster_",
    "Text_DesignData_Props_Props_",
)


def _build_entity_key_index(translations: dict[str, str]) -> dict[str, str]:
    """Map lowercased entity name -> translation key for one-time lookups."""
    index: dict[str, str] = {}
    for key in translations:
        for prefix in _ENTITY_KEY_PREFIXES:
            if key.startswith(prefix):
                index.setdefault(key[len(prefix) :].lower(), key)
                break
    return index


# Lootdrop ids occasionally misspell or shorten the entity asset name. Map them
# to the canonical name that owns the official translation key.
_POOL_ENTITY_NAME_ALIASES = {
    "FrostGiantSheilder": "FrostGiantShielder",
    "FrostSkeletonGuardsman": "FrostSkeletonGuardman",
    "PirateCrossbow": "PirateCrossbowman",
    "PirateSwiftBlade": "PirateSwiftblade",
    "TideWalkerClubFighter": "TidewalkerClubfighter",
    "TideWalkerShaman": "TidewalkerShaman",
    "TideWalkerSpearer": "TidewalkerSpearer",
    "TidewalkerSlinger": "TidewalkerSlinger",
    "DwarfHandCannoneer": "DwarfHandcannoneer",
    "GoldChest": "GoldenChest",
}


_POOL_MISC_SUFFIX_RE = re.compile(r"_(?:Misc|Gear|Jewelry|Ore|Spoils)$", re.IGNORECASE)
_POOL_TRAILING_DIGITS_RE = re.compile(r"\d+$")

# Sub-pool markers -> synthetic locale key for the suffix the UI appends to the
# owning entity's name. Keeps "Yeti" / "Yeti_Gear" / "Yeti_Spoils" apart.
_POOL_SUBPOOL_SUFFIXES = {
    "spoils": "df5.lootpool.Spoils",
    "gear": "df5.lootpool.Gear",
    "jewelry": "df5.lootpool.Jewelry",
    "ore": "df5.lootpool.Ore",
    "misc": "df5.lootpool.Misc",
}


def _english_pool_name(name: str) -> str:
    """Readable English reading of a technical lootdrop pool name."""
    spaced = name.replace("_", " ")
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", spaced)
    spaced = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", " ", spaced)
    spaced = re.sub(r"\d+$", "", spaced)
    return re.sub(r"\s+", " ", spaced).strip()


def _lookup_entity_key(
    core: str, translations: dict[str, str], index: dict[str, str] | None = None
) -> tuple[str, bool]:
    """Find the Text_DesignData_* key for a pool's entity name.

    Returns (key, borrowed) where ``borrowed`` means the key came from a
    fallback candidate (the owning entity of a `_Gear`/`_Ore` sub-pool, or a
    case/spelling variant) rather than the pool name itself, so callers can keep
    the rendered label distinguishable from the entity's own pool.
    """
    spoils = _POOL_SPOILS_SUFFIX_RE.sub("", core)
    names = [spoils]
    # Sub-pools carry a marker (Cyclops_TrollBlood, Yeti_Gear, LavaGolem_Ore);
    # fall back to the owning entity name before giving up.
    generic = _POOL_MISC_SUFFIX_RE.sub("", spoils)
    if generic != spoils and generic != core:
        names.append(generic)
    alias = _POOL_ENTITY_NAME_ALIASES.get(spoils)
    if alias and alias not in names:
        names.append(alias)
    # Variant pools append an index (Banshee2 -> Banshee).
    digits = _POOL_TRAILING_DIGITS_RE.sub("", spoils)
    if digits != spoils and digits not in names:
        names.append(digits)
    for position, name in enumerate(names):
        for key in (
            f"Text_DesignData_Item_Item_{name}",
            f"Text_DesignData_Monster_Monster_{name}",
            f"Text_DesignData_Props_Props_{name}",
            f"Text_DesignData_Props_Props_Ore_{name}",
        ):
            if key in translations:
                return key, position > 0
        # Case-insensitive fallback: lootdrop ids and entity tables disagree on
        # casing (BlueMarlin/Bluemarlin, TideWalkerShaman/TidewalkerShaman).
        if index is not None:
            hit = index.get(name.lower())
            if hit:
                return hit, position > 0
    return "", False


def resolve_pool_text(
    lootdrop_id: str,
    translations: dict[str, str],
    entity_index: dict[str, str] | None = None,
    host_entity: str = "",
) -> tuple[str, str, str]:
    """Resolve a lootdrop pool id to (display text, translation key, sub_label).

    Resolution order:
    1. Label-only pools with no Game.json key (Cloak_Physical, ...) via the
       synthetic df5.lootpool.* locale entries.
    2. Item-category pools (ChestArmors, Consumables, ...) via category keys.
    3. Container-prop pools (Barrels, Crates, ...) via prop keys.
    4. Entity-named pools (Drop_CaveTroll, Drop_Bloodbound_5001) via the
       canonical Text_DesignData_* key for that entity.
    5. The project's hardcoded entity names (Lumber, Bones, ...).
    6. A readable English reading of the technical pool name.

    ``sub_label`` is the synthetic locale key of a suffix the UI appends to the
    owning entity's name for sub-pools (`_Spoils`, `_Gear`, `_Ore`, ...), so
    "Yeti" / "Yeti_Gear" / "Yeti_Spoils" stay distinguishable. Empty when the
    pool name stands on its own.

    ``host_entity`` is the page's entity name. When the pool merely abbreviates
    it (`SkeletonWarlord` -> `Warlord`) and no official key exists under the
    short name, the host's own name is used instead of an English fallback.
    """
    core = pool_core_name(lootdrop_id)
    spoils = _POOL_SPOILS_SUFFIX_RE.sub("", core)
    sub_label = _POOL_SUBPOOL_SUFFIXES["spoils"] if spoils != core else ""

    # Label-only pools with no Game.json key. Try the bare name too so a
    # `_Spoils` variant reuses the base pool's label (IceKoboldBowman_Spoils).
    for candidate in (core, spoils):
        label_key = f"{POOL_LABEL_I18N_PREFIX}{candidate}"
        label_value = translations.get(label_key) or POOL_LABEL_TRANSLATIONS.get(candidate, {}).get("zh-Hans")
        if label_value:
            return label_value, label_key, sub_label

    category_key = _POOL_CATEGORY_KEYS.get(core)
    if category_key:
        value = translations.get(category_key)
        if value:
            return value, category_key, ""

    prop_key = _POOL_PROP_KEYS.get(core)
    if prop_key:
        value = translations.get(prop_key)
        if value:
            return value, prop_key, ""

    entity_key, borrowed = _lookup_entity_key(spoils, translations, entity_index)
    if entity_key:
        return translations[entity_key], entity_key, sub_label or _sub_label_of(spoils, borrowed)

    # Fall back to the project's hardcoded entity names (Lumber, Bones, ...).
    hardcoded = HARDCODED_TRANSLATIONS.get(spoils)
    if hardcoded:
        return hardcoded, "", sub_label

    # The pool may just abbreviate the host (SkeletonWarlord -> Warlord); reuse
    # the host's name rather than showing an English fallback on its own page.
    if host_entity and host_entity.lower().endswith(spoils.lower()) and spoils.lower() != host_entity.lower():
        host_key, _ = _lookup_entity_key(host_entity, translations, entity_index)
        if host_key:
            return translations[host_key], host_key, sub_label

    # Last resort: a readable English reading of the technical pool name so the
    # UI never shows a raw id such as "Drop_Barrel_Junk".
    return _english_pool_name(spoils), "", sub_label


def _sub_label_of(core: str, borrowed: bool) -> str:
    """Suffix key for a sub-pool resolved through its owning entity."""
    if not borrowed:
        return ""
    match = _POOL_MISC_SUFFIX_RE.search(core)
    if not match:
        return ""
    marker = match.group(0)[1:].lower()
    return _POOL_SUBPOOL_SUFFIXES.get(marker, "")


def canonical_monster_name(entity_name: str, monster_names: set[str]) -> str:
    stripped = QUALITY_RE.sub("", entity_name)
    if stripped in monster_names:
        return stripped
    if entity_name in monster_names:
        return entity_name
    lower_map = {name.lower(): name for name in monster_names}
    return lower_map.get(stripped.lower()) or lower_map.get(entity_name.lower()) or stripped


def canonical_entity_name(entity_name: str, entity_names: set[str], *, fold_quality: bool) -> str:
    if fold_quality:
        return canonical_monster_name(entity_name, entity_names)
    lower_map = {name.lower(): name for name in entity_names}
    candidates: list[str] = [entity_name]
    stripped = QUALITY_RE.sub("", entity_name)
    if stripped != entity_name:
        candidates.append(stripped)
    ore = ORE_QUALITY_RE.match(entity_name)
    if ore:
        base = ore.group(1)
        candidates.extend([base, f"Ore_{base}"])
    for cand in candidates:
        if cand in entity_names:
            return cand
        hit = lower_map.get(cand.lower())
        if hit:
            return hit
    return entity_name


def _item_sort_key(item: dict) -> tuple[int, str]:
    suffix = item.get("suffix")
    if suffix and suffix.isdigit():
        rank = int(suffix)
    else:
        luck = int(item.get("luck_grade") or 0)
        rank = int(_LUCK_TO_SUFFIX.get(luck, "0"))
    return (-rank, item.get("translation") or item.get("page") or "")


def _resolve_item_text(
    item_name: str, page: str, translations: dict[str, str], item_keys: dict[str, str]
) -> tuple[str, str]:
    direct_key = f"Text_DesignData_Item_Item_{item_name}"
    if direct_key in translations:
        return translations[direct_key], direct_key
    for lookup in (page, VARIANT_RE.sub(r"\1", page) if VARIANT_RE.match(page) else None):
        if not lookup:
            continue
        key = item_keys.get(lookup, "")
        if key:
            return translations.get(key, lookup), key
    return page, ""


def _dedupe_items(items: list[dict]) -> list[dict]:
    by_page: dict[str, dict] = {}
    for item in items:
        existing = by_page.get(item["page"])
        if existing is None or int(item.get("luck_grade") or 0) > int(existing.get("luck_grade") or 0):
            by_page[item["page"]] = item
    return sorted(by_page.values(), key=_item_sort_key)


def monster_map_groups(entity: dict, map_base_to_group: dict[str, str]) -> set[str]:
    groups: set[str] = set()
    for coord in entity.get("coords") or []:
        map_name = coord.get("map") or ""
        group = map_base_to_group.get(map_name, "")
        if group:
            groups.add(group)
    return groups


def item_is_consumable(item: dict, item_subtypes: dict[str, set[str]]) -> bool:
    for key in (item.get("name"), item.get("page")):
        if key and _CONSUMABLE_SUBTYPE in item_subtypes.get(key, set()):
            return True
    return False


def item_has_positive_rate(drop_engine, item_name: str, monster_name: str, group_keys: set[str]) -> bool:
    """True if any mode on any of the monster's map groups has drop rate > 0."""
    if not group_keys:
        return True
    has_positive_rate = getattr(drop_engine, "has_positive_group_drop_rate", None)
    if callable(has_positive_rate):
        return any(has_positive_rate(item_name, monster_name, group_key) for group_key in group_keys)
    for group_key in group_keys:
        rates = drop_engine.get_group_drop_rates(item_name, monster_name, group_key) or {}
        if any(value > 0 for value in rates.values()):
            return True
    return False


def build_loot_pools(
    *,
    monster_names: set[str],
    rows: list[tuple[str, str, str, int]],
    translations: dict[str, str],
    item_keys: dict[str, str],
    drop_engine=None,
    monster_groups: dict[str, set[str]] | None = None,
    fold_quality: bool = True,
    item_subtypes: dict[str, set[str]] | None = None,
) -> dict[str, list[dict]]:
    """rows: (entity_name, lootdrop_id, item_name, luck_grade)."""
    subtypes = item_subtypes or {}
    entity_index = _build_entity_key_index(translations)
    grouped: dict[str, dict[str, list[dict]]] = {}
    rate_ok: dict[tuple[str, str], bool] = {}
    for entity_name, lootdrop_id, item_name, luck_grade in rows:
        if not entity_name or not lootdrop_id or not item_name:
            continue
        canonical = canonical_entity_name(entity_name, monster_names, fold_quality=fold_quality)
        if canonical not in monster_names:
            continue
        if drop_engine is not None:
            cache_key = (item_name, entity_name)
            ok = rate_ok.get(cache_key)
            if ok is None:
                groups = (monster_groups or {}).get(canonical, set())
                ok = item_has_positive_rate(drop_engine, item_name, entity_name, groups)
                rate_ok[cache_key] = ok
            if not ok:
                continue
        page, suffix = fold_item_page(item_name)
        translation, translation_key = _resolve_item_text(item_name, page, translations, item_keys)
        grouped.setdefault(canonical, {}).setdefault(lootdrop_id, []).append(
            {
                "name": item_name,
                "page": page,
                "translation": translation,
                "translation_key": translation_key,
                "suffix": suffix,
                "luck_grade": int(luck_grade or 0),
            }
        )

    result: dict[str, list[dict]] = {}
    for monster, pools in grouped.items():
        quest_items: list[dict] = []
        artifact_items: list[dict] = []
        consumable_items: list[dict] = []
        other: list[tuple[str, list[dict]]] = []
        for lootdrop_id, items in pools.items():
            if is_event_currency_pool(lootdrop_id):
                continue
            if is_quest_pool(lootdrop_id):
                quest_items.extend(items)
                continue
            remaining = []
            for item in items:
                if item.get("suffix") == "8001" or (item.get("page") or "").endswith("_8001"):
                    artifact_items.append(item)
                else:
                    remaining.append(item)
            if not remaining:
                continue
            remaining_deduped = _dedupe_items(remaining)
            if len(remaining_deduped) == 1 and item_is_consumable(remaining_deduped[0], subtypes):
                consumable_items.extend(remaining)
                continue
            other.append((lootdrop_id, remaining))

        loot_pools: list[dict] = []
        quest_deduped = _dedupe_items(quest_items)
        if quest_deduped:
            loot_pools.append({"id": "quest", "kind": "quest", "lootdrop_id": None, "items": quest_deduped})
        artifact_deduped = _dedupe_items(artifact_items)
        if artifact_deduped:
            loot_pools.append({"id": "artifact", "kind": "artifact", "lootdrop_id": None, "items": artifact_deduped})
        consumable_deduped = _dedupe_items(consumable_items)
        if consumable_deduped:
            loot_pools.append(
                {"id": "consumable", "kind": "consumable", "lootdrop_id": None, "items": consumable_deduped}
            )
        other.sort(key=lambda pair: lootdrop_stem(pair[0]).lower())
        for lootdrop_id, items in other:
            pool_translation, pool_key, pool_sub_label = resolve_pool_text(
                lootdrop_id, translations, entity_index, host_entity=monster
            )
            loot_pools.append(
                {
                    "id": lootdrop_id,
                    "kind": "pool",
                    "lootdrop_id": lootdrop_id,
                    "translation": pool_translation,
                    "translation_key": pool_key,
                    "sub_label": pool_sub_label,
                    "items": _dedupe_items(items),
                }
            )
        if loot_pools:
            result[monster] = loot_pools
    return result


def load_drop_rows(db, drop_engine=None) -> list[tuple[str, str, str, int]]:
    if drop_engine is not None:
        get_rows = getattr(drop_engine, "get_entity_drop_rows", None)
        if callable(get_rows):
            return get_rows()
    cursor = db.connect().execute("""
        SELECT se.entity_name, lg.lootdrop_id, r.item_name, MAX(r.luck_grade) AS luck_grade
        FROM spawner_entries se
        JOIN lootdrop_groups lg ON lg.group_id = se.lootdrop_group_id
        JOIN lootdrop_rate_items r ON r.lootdrop_id = lg.lootdrop_id
        WHERE se.entity_name != '' AND se.lootdrop_group_id != ''
        GROUP BY se.entity_name, lg.lootdrop_id, r.item_name
        """)
    return [(row["entity_name"], row["lootdrop_id"], row["item_name"], int(row["luck_grade"] or 0)) for row in cursor]


def load_item_keys(db) -> dict[str, str]:
    return {
        row["item_name"]: row["translation_key"]
        for row in db.connect().execute("SELECT item_name, translation_key FROM item_entities")
    }


def load_item_subtypes(db) -> dict[str, set[str]]:
    subtypes: dict[str, set[str]] = {}
    for row in db.connect().execute("SELECT item_name, item_subtype_keys FROM item_entities"):
        raw = row["item_subtype_keys"] or "[]"
        try:
            keys = json.loads(raw)
        except json.JSONDecodeError:
            keys = []
        subtypes[row["item_name"]] = {str(key) for key in keys if key}
    return subtypes


def attach_loot_pools(
    monster_data: dict[str, dict],
    db,
    translations: dict[str, str],
    drop_engine=None,
    *,
    fold_quality: bool = True,
    rows: list[tuple[str, str, str, int]] | None = None,
) -> int:
    """Inject loot_pools onto in-memory detail dicts. Returns entity count updated."""
    if not monster_data:
        return 0
    map_base_to_group = drop_engine.map_base_to_group if drop_engine is not None else {}
    monster_groups = {name: monster_map_groups(entity, map_base_to_group) for name, entity in monster_data.items()}
    if rows is None:
        rows = load_drop_rows(db, drop_engine)
    pools = build_loot_pools(
        monster_names=set(monster_data),
        rows=rows,
        translations=translations,
        item_keys=load_item_keys(db),
        item_subtypes=load_item_subtypes(db),
        drop_engine=drop_engine,
        monster_groups=monster_groups,
        fold_quality=fold_quality,
    )
    updated = 0
    for name, entity in monster_data.items():
        loot_pools = pools.get(name)
        if loot_pools:
            entity["loot_pools"] = loot_pools
            updated += 1
        else:
            entity.pop("loot_pools", None)
    return updated
