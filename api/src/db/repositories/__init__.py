from .coordinates import CoordinatesRepository
from .items import ItemsRepository
from .lootdrops import LootdropsRepository
from .modules import ModulesRepository
from .monsters import MonstersRepository
from .props import PropsRepository
from .quests import QuestsRepository


class RepositoryRegistry:
    def __init__(self, conn):
        self.items = ItemsRepository(conn)
        self.monsters = MonstersRepository(conn)
        self.props = PropsRepository(conn)
        self.modules = ModulesRepository(conn)
        self.coordinates = CoordinatesRepository(conn)
        self.lootdrops = LootdropsRepository(conn)
        self.quests = QuestsRepository(conn)
