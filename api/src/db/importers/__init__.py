from .items import ItemsImporter
from .lootdrops import LootdropsImporter
from .modules import ModulesImporter
from .monsters import MonstersImporter
from .props import PropsImporter
from .quests import QuestsImporter
from .spawners import SpawnersImporter


class ImporterRegistry:
    def __init__(self, conn):
        self.items = ItemsImporter(conn)
        self.monsters = MonstersImporter(conn)
        self.props = PropsImporter(conn)
        self.modules = ModulesImporter(conn)
        self.lootdrops = LootdropsImporter(conn)
        self.quests = QuestsImporter(conn)
        self.spawners = SpawnersImporter(conn)
