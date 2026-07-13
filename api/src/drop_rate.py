"""Drop rate computation engine extracted from collector.py."""

import json
from decimal import ROUND_HALF_UP, Decimal

from config import DUNGEON_MODE_NAMES, MODULE_GROUP_FLOOR_SUFFIXES
from translator import HARD_SUFFIX_RE, ORE_QUALITY_RE, QUALITY_RE, VARIANT_RE, base_monster_name

_VARIANT_SUFFIXES = ["_5001", "_6001", "_7001", "_8001", "_4001", "_3001", "_2001", "_1001"]
_VARIANT_RE = VARIANT_RE

_QUALITY_VARIANT_SUFFIXES = ["", "_Common", "_Elite", "_Nightmare", "_Unique"]


def _round_rate(v: float) -> float:
    d = Decimal(str(v)).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
    return float(d)


class DropRateEngine:
    """Preloads drop rate data from DB and provides O(1) computation methods."""

    def __init__(self):
        self._spawner_ldg: dict[str, str] = {}
        self._entity_ldg_all: dict[str, set[str]] = {}
        self._ore_ldg: dict[str, str] = {}
        self._ld_groups: dict[str, dict[int, list[tuple[str, str, int]]]] = {}
        self._ld_rate_items: dict[str, dict[str, tuple[int, int]]] = {}
        self._ld_luck_grade_count: dict[tuple[str, int], int] = {}
        self._ld_rate_weights: dict[str, dict[int, int]] = {}
        self._ld_rate_totals: dict[str, int] = {}
        self._map_base_to_group: dict[str, str] = {}
        self._group_spawner_keywords: dict[str, set[str]] = {}
        self._spawn_rate_cache: dict[str, float] = {}
        self._spawn_rate_detail: dict[tuple[str, str], float] = {}
        self._spawn_rate_by_mode: dict[tuple[str, str], dict[str, float]] = {}
        self._entity_spawners: dict[str, set[str]] = {}
        # group_id → set of spawner_keywords that belong to this group
        self._group_to_spawners: dict[str, set[str]] = {}
        # base_item_name → set of suffixes with actual drop data
        self._existing_variant_suffixes: dict[str, set[str]] = {}
        # lootdrop_id → set of group_ids
        self._ld_id_to_groups: dict[str, set[str]] = {}
        # base_entity_name → combined spawn rate across quality variants
        self._combined_spawn_rate_cache: dict[str, float] = {}
        self._item_to_ld_ids: dict[str, set[str]] = {}
        self._variant_rate_cache: dict[tuple, float] = {}
        self._candidate_ids_cache: dict[str, set[str]] = {}
        self._all_groups_cache: dict[tuple, dict[str, dict[str, float]]] = {}

    def preload(self, db, modules_data: list[dict]) -> None:
        """Preload all drop rate data from DB."""
        _c = db.connect().cursor()

        # Build map_base → group mapping
        for _m in modules_data:
            _g = _m.get("group", "") or ""
            if not _g:
                continue
            self._map_base_to_group[_m["name"]] = _g
            _sl = _m.get("sl_base_name", "")
            if _sl:
                self._map_base_to_group[_sl] = _g
            for _alias in _m.get("aliases") or []:
                self._map_base_to_group[_alias] = _g

        # spawner_keyword / entity_name → lootdrop_group_id
        for _row in _c.execute(
            "SELECT DISTINCT spawner_keyword, entity_name, lootdrop_group_id FROM spawner_entries WHERE lootdrop_group_id != ''"
        ):
            for _key in (_row["spawner_keyword"], _row["entity_name"]):
                if _key and _key not in self._spawner_ldg:
                    self._spawner_ldg[_key] = _row["lootdrop_group_id"]
            for _key in (_row["spawner_keyword"], _row["entity_name"]):
                if _key:
                    _base = HARD_SUFFIX_RE.sub("", _key)
                    _base = QUALITY_RE.sub("", _base)
                    self._entity_ldg_all.setdefault(_base, set()).add(_row["lootdrop_group_id"])
            for _key in (_row["spawner_keyword"], _row["entity_name"]):
                _m = ORE_QUALITY_RE.match(_key)
                if _m:
                    _stripped = _m.group(1)
                    if _stripped and _stripped not in self._ore_ldg:
                        self._ore_ldg[_stripped] = _row["lootdrop_group_id"]

        # lootdrop_groups
        for _row in _c.execute(
            "SELECT group_id, dungeon_grade, lootdrop_id, lootdrop_rate_id, drop_count FROM lootdrop_groups"
        ):
            self._ld_groups.setdefault(_row["group_id"], {}).setdefault(_row["dungeon_grade"], []).append(
                (_row["lootdrop_id"], _row["lootdrop_rate_id"], _row["drop_count"])
            )

        # lootdrop_rate_items
        for _row in _c.execute("SELECT lootdrop_id, item_name, luck_grade, drop_count FROM lootdrop_rate_items"):
            self._ld_rate_items.setdefault(_row["lootdrop_id"], {})[_row["item_name"]] = (
                _row["luck_grade"],
                _row["drop_count"],
            )
        for _ld_id, _items in self._ld_rate_items.items():
            _lg_counts: dict[int, int] = {}
            for _item_name, (_lg, _) in _items.items():
                _lg_counts[_lg] = _lg_counts.get(_lg, 0) + 1
                self._item_to_ld_ids.setdefault(_item_name, set()).add(_ld_id)
            for _lg, _cnt in _lg_counts.items():
                self._ld_luck_grade_count[(_ld_id, _lg)] = _cnt

        # lootdrop_rate_weights
        for _row in _c.execute(
            "SELECT rate_id, luck_grade, SUM(weight) as total FROM lootdrop_rate_weights GROUP BY rate_id, luck_grade"
        ):
            self._ld_rate_weights.setdefault(_row["rate_id"], {})[_row["luck_grade"]] = _row["total"]

        for _rid, _grades in self._ld_rate_weights.items():
            self._ld_rate_totals[_rid] = sum(_w for _w in _grades.values() if _w > 0) or 10000

        # Build group_id → spawner_keywords mapping
        for _row in _c.execute(
            "SELECT DISTINCT spawner_keyword, lootdrop_group_id FROM spawner_entries WHERE lootdrop_group_id != ''"
        ):
            self._group_to_spawners.setdefault(_row["lootdrop_group_id"], set()).add(_row["spawner_keyword"])

        # Build lootdrop_id → group_ids mapping (from _ld_groups)
        for _gid, _grades in self._ld_groups.items():
            for _grade_data in _grades.values():
                for _ld_id, _lr_id, _ in _grade_data:
                    self._ld_id_to_groups.setdefault(_ld_id, set()).add(_gid)

        # Build existing variant suffixes from _ld_rate_items
        for _items in self._ld_rate_items.values():
            for _item_name in _items:
                _m = _VARIANT_RE.match(_item_name)
                if _m:
                    _base = _m.group(1)
                    _suffix = _item_name[-4:]  # e.g. "5001" from "HeaterShield_5001"
                    self._existing_variant_suffixes.setdefault(_base, set()).add(_suffix)

        # group → spawner keywords mapping (for per-group filtering in enrichment)
        for _row in _c.execute("SELECT DISTINCT keyword, map_base FROM spawners WHERE map_base != ''"):
            _g = self._map_base_to_group.get(_row["map_base"], "")
            if _g:
                self._group_spawner_keywords.setdefault(_g, set()).add(_row["keyword"])

        # spawn_rate cache
        for _row in db.get_all_spawner_entries():
            sk = _row["spawner_keyword"]
            en = _row["entity_name"]
            sr = _row["spawn_rate"]
            _grades_raw = _row.get("dungeon_grades", "[]")
            try:
                _grades = json.loads(_grades_raw) if isinstance(_grades_raw, str) else (_grades_raw or [])
            except (json.JSONDecodeError, TypeError):
                _grades = []
            for _key in (sk, en):
                if _key and sr > self._spawn_rate_cache.get(_key, 0):
                    self._spawn_rate_cache[_key] = sr
            _om = ORE_QUALITY_RE.match(en)
            if _om:
                _oname = _om.group(1)
                if _oname and sr > self._spawn_rate_cache.get(_oname, 0):
                    self._spawn_rate_cache[_oname] = sr
            if sk and en:
                _pair = (sk, en)
                if sr > self._spawn_rate_detail.get(_pair, 0):
                    self._spawn_rate_detail[_pair] = sr
                _mode_rates: dict[str, float] = {}
                for _g in _grades:
                    _mode_id = _g // 1000 if _g >= 1000 else 1
                    _mode_name = DUNGEON_MODE_NAMES.get(_mode_id, "")
                    if _mode_name and (_mode_name not in _mode_rates or sr < _mode_rates[_mode_name]):
                        _mode_rates[_mode_name] = sr
                if _mode_rates:
                    _existing = self._spawn_rate_by_mode.get(_pair, {})
                    for _mn, _mr in _mode_rates.items():
                        if _mn not in _existing or _mr < _existing[_mn]:
                            _existing[_mn] = _mr
                    self._spawn_rate_by_mode[_pair] = _existing
                    _en_mode = self._spawn_rate_by_mode.get(("", en), {})
                    for _mn, _mr in _mode_rates.items():
                        if _mn not in _en_mode or _mr < _en_mode[_mn]:
                            _en_mode[_mn] = _mr
                    self._spawn_rate_by_mode[("", en)] = _en_mode
            if en and sk:
                self._entity_spawners.setdefault(en, set()).add(sk)

        # Build combined spawn rate cache: sum quality variant rates per keyword+grade
        _entries_by_sk: dict[str, list[tuple[str, float, str]]] = {}
        for _row in db.get_all_spawner_entries():
            _sk = _row["spawner_keyword"]
            _en = _row["entity_name"]
            _sr = _row["spawn_rate"]
            _grades_raw = _row.get("dungeon_grades", "[]")
            _gs = str(_grades_raw)
            _entries_by_sk.setdefault(_sk, []).append((_en, _sr, _gs))
        for _sk, _entries in _entries_by_sk.items():
            _by_grades: dict[str, list[tuple[str, float]]] = {}
            for _en, _sr, _gs in _entries:
                _by_grades.setdefault(_gs, []).append((_en, _sr))
            for _grade_entries in _by_grades.values():
                _combined_by_base: dict[str, float] = {}
                for _en, _sr in _grade_entries:
                    _base = base_monster_name(_en)
                    _combined_by_base[_base] = _combined_by_base.get(_base, 0.0) + _sr
                for _base, _combined in _combined_by_base.items():
                    _capped = min(_combined, 100.0)
                    if _capped > self._combined_spawn_rate_cache.get(_base, 0.0):
                        self._combined_spawn_rate_cache[_base] = _capped

    @property
    def spawner_ldg(self) -> dict[str, str]:
        return self._spawner_ldg

    @property
    def entity_ldg_all(self) -> dict[str, set[str]]:
        return self._entity_ldg_all

    @property
    def ore_ldg(self) -> dict[str, str]:
        return self._ore_ldg

    @property
    def spawn_rate_cache(self) -> dict[str, float]:
        return self._spawn_rate_cache

    @property
    def spawn_rate_detail(self) -> dict[tuple[str, str], float]:
        return self._spawn_rate_detail

    @property
    def spawn_rate_by_mode(self) -> dict[tuple[str, str], dict[str, float]]:
        return self._spawn_rate_by_mode

    @property
    def entity_spawners(self) -> dict[str, set[str]]:
        return self._entity_spawners

    @property
    def map_base_to_group(self) -> dict[str, str]:
        return self._map_base_to_group

    @property
    def group_spawner_keywords(self) -> dict[str, set[str]]:
        return self._group_spawner_keywords

    def get_existing_variant_suffixes(self, base_item_name: str) -> set[str]:
        """Return suffixes that actually exist in lootdrop_rate_items for a base item."""
        return self._existing_variant_suffixes.get(base_item_name, set())

    def get_variant_spawners(self, item_name: str) -> set[str]:
        """Get spawner_keywords that actually drop the given item variant.

        Traces: item_name → lootdrop_ids → group_ids → spawner_keywords.
        """
        result: set[str] = set()
        for _ld_id in self._item_to_ld_ids.get(item_name, set()):
            _groups = self._ld_id_to_groups.get(_ld_id, set())
            for _gid in _groups:
                result.update(self._group_to_spawners.get(_gid, set()))
        return result

    def get_base_item_spawners(self, base_item_name: str) -> set[str]:
        """Get spawner_keywords for ALL variants of a base item (union).

        Used as fallback when a specific variant has no spawner data.
        """
        result: set[str] = set()
        for _ld_id, _items in self._ld_rate_items.items():
            for _item_name in _items:
                _m = _VARIANT_RE.match(_item_name)
                _base = _m.group(1) if _m else _item_name
                if _base == base_item_name:
                    _groups = self._ld_id_to_groups.get(_ld_id, set())
                    for _gid in _groups:
                        result.update(self._group_to_spawners.get(_gid, set()))
        return result

    def get_quality_variants(self, entity_name: str) -> list[str]:
        """Generate all quality variant names for a given entity.
        E.g. 'Wraith' -> ['Wraith', 'Wraith_Common', 'Wraith_Elite', 'Wraith_Nightmare', 'Wraith_Unique']
        """
        base = base_monster_name(entity_name)
        return [base + s for s in _QUALITY_VARIANT_SUFFIXES]

    def get_combined_spawn_rate(self, entity_name: str) -> float:
        """Return pre-computed combined spawn rate across quality variants.

        Uses _combined_spawn_rate_cache built during preload (sums rates
        per keyword+grade across quality variants). Falls back to spawn_rate_cache.
        """
        base = base_monster_name(entity_name)
        cached = self._combined_spawn_rate_cache.get(base, 0.0)
        if cached > 0.0:
            return cached
        return self._spawn_rate_cache.get(entity_name, 0.0)

    def compute_drop_rate(self, ldg_id: str, item_name: str, full_grade: int) -> float:
        """Compute drop rate for an item in a specific group+grade (0~1)."""
        grade_data = self._ld_groups.get(ldg_id, {}).get(full_grade, [])
        if not grade_data:
            return 0.0
        total_weight = 0.0
        found = False
        # Pre-compute base name for variant fallback (e.g. Mitre_7001 -> Mitre)
        _base = _VARIANT_RE.sub(r"\1", item_name) if _VARIANT_RE.match(item_name) else None
        for ld_id, lr_id, _ in grade_data:
            rate_items = self._ld_rate_items.get(ld_id, {})
            item_info = rate_items.get(item_name)
            if item_info is None:
                for _suffix in _VARIANT_SUFFIXES:
                    item_info = rate_items.get(item_name + _suffix)
                    if item_info is not None:
                        break
            # Fallback: strip variant suffix and try base name
            if item_info is None and _base:
                item_info = rate_items.get(_base)
                if item_info is None:
                    for _suffix in _VARIANT_SUFFIXES:
                        item_info = rate_items.get(_base + _suffix)
                        if item_info is not None:
                            break
            if item_info is None:
                continue
            found = True
            luck_grade, item_count = item_info
            _pool_weight = self._ld_rate_weights.get(lr_id, {}).get(luck_grade, 0)
            _shared = self._ld_luck_grade_count.get((ld_id, luck_grade), 1)
            _rate_total = self._ld_rate_totals.get(lr_id, 10000)
            total_weight += _pool_weight / _shared / _rate_total
        if found:
            return total_weight
        return 0.0

    def get_group_drop_rates(self, item_name: str, monster_name: str, group_key: str) -> dict[str, float]:
        """Compute per-mode drop rates for an item/monster in a map group."""
        candidate_ids: set[str] = set()
        _primary = self._spawner_ldg.get(monster_name, "")
        if _primary:
            candidate_ids.add(_primary)
        for _suffix in ("_Unique", "_Elite", "_Nightmare", "_Common"):
            _v = self._spawner_ldg.get(monster_name + _suffix, "")
            if _v:
                candidate_ids.add(_v)
        if not candidate_ids:
            _lower = monster_name.lower()
            for _k, _v in self._spawner_ldg.items():
                if _k.lower() == _lower:
                    candidate_ids.add(_v)
                    break
        _all_groups = self._entity_ldg_all.get(monster_name, set())
        if not _all_groups:
            _all_groups = self._entity_ldg_all.get(QUALITY_RE.sub("", monster_name), set())
        candidate_ids.update(_all_groups)
        if not candidate_ids:
            return {}
        suffixes = MODULE_GROUP_FLOOR_SUFFIXES.get(group_key, [])
        if not suffixes:
            return {}
        mode_rates: dict[str, float] = {}
        for mode_id, mode_name in DUNGEON_MODE_NAMES.items():
            best_rate = 0.0
            for suffix in suffixes:
                full_grade = mode_id * 1000 + suffix
                for _ldg_id in candidate_ids:
                    rate = self.compute_drop_rate(_ldg_id, item_name, full_grade)
                    if rate > best_rate:
                        best_rate = rate
            mode_rates[mode_name] = _round_rate(best_rate * 100)
        return mode_rates

    def _get_candidate_ids(self, monster_name: str) -> set[str]:
        """Get candidate lootdrop_group_ids for a monster (cached)."""
        cached = self._candidate_ids_cache.get(monster_name)
        if cached is not None:
            return cached
        candidate_ids: set[str] = set()
        _primary = self._spawner_ldg.get(monster_name, "")
        if _primary:
            candidate_ids.add(_primary)
        for _suffix in ("_Unique", "_Elite", "_Nightmare", "_Common"):
            _v = self._spawner_ldg.get(monster_name + _suffix, "")
            if _v:
                candidate_ids.add(_v)
        if not candidate_ids:
            _lower = monster_name.lower()
            for _k, _v in self._spawner_ldg.items():
                if _k.lower() == _lower:
                    candidate_ids.add(_v)
                    break
        _all_groups = self._entity_ldg_all.get(monster_name, set())
        if not _all_groups:
            _all_groups = self._entity_ldg_all.get(QUALITY_RE.sub("", monster_name), set())
        candidate_ids.update(_all_groups)
        # Fuzzy fallback: try stripping FakeDeath/FromFakeDeath suffixes
        if not candidate_ids:
            for _fuzzy_suffix in ("FromFakeDeath", "FakeDeath"):
                if _fuzzy_suffix in monster_name:
                    _fuzzy_name = monster_name.replace(_fuzzy_suffix, "")
                    _fuzzy_groups = self._entity_ldg_all.get(_fuzzy_name, set())
                    if _fuzzy_groups:
                        candidate_ids.update(_fuzzy_groups)
                        break
        # Fuzzy fallback: try adding FakeDeath/FromFakeDeath suffixes
        if not candidate_ids:
            for _fuzzy_suffix in ("FakeDeath", "FromFakeDeath"):
                _fuzzy_name = monster_name + _fuzzy_suffix
                _fuzzy_groups = self._entity_ldg_all.get(_fuzzy_name, set())
                if _fuzzy_groups:
                    candidate_ids.update(_fuzzy_groups)
                    break
        # Fuzzy fallback: try base name without any suffix
        if not candidate_ids:
            _base = QUALITY_RE.sub("", HARD_SUFFIX_RE.sub("", monster_name))
            _base_groups = self._entity_ldg_all.get(_base, set())
            if _base_groups:
                candidate_ids.update(_base_groups)
        self._candidate_ids_cache[monster_name] = candidate_ids
        return candidate_ids

    def get_variant_group_drop_rates(
        self, luck_grade: int, monster_name: str, group_key: str, item_name: str = ""
    ) -> dict[str, float]:
        """Compute per-mode drop rates for a specific luck_grade (variant) in a map group."""
        candidate_ids = self._get_candidate_ids(monster_name)
        if not candidate_ids:
            return {}
        suffixes = MODULE_GROUP_FLOOR_SUFFIXES.get(group_key, [])
        if not suffixes:
            return {}
        mode_rates: dict[str, float] = {}
        _rt_cache: dict[str, int] = {}
        for mode_id, mode_name in DUNGEON_MODE_NAMES.items():
            best_rate = 0.0
            for suffix in suffixes:
                full_grade = mode_id * 1000 + suffix
                for _ldg_id in candidate_ids:
                    rate = self.compute_variant_rate(
                        _ldg_id, luck_grade, full_grade, item_name=item_name, _rt_cache=_rt_cache
                    )
                    if rate > best_rate:
                        best_rate = rate
            mode_rates[mode_name] = _round_rate(best_rate * 100)
        return mode_rates

    def get_variant_rates_all_groups(
        self, luck_grade: int, monster_name: str, group_keys: set[str], item_name: str = ""
    ) -> dict[str, dict[str, float]]:
        """Compute per-mode drop rates for ALL groups at once. Returns {group_key: mode_rates}."""
        candidate_ids = self._get_candidate_ids(monster_name)
        if not candidate_ids:
            return {}
        _rt_cache: dict[str, int] = {}
        result: dict[str, dict[str, float]] = {}
        for group_key in group_keys:
            suffixes = MODULE_GROUP_FLOOR_SUFFIXES.get(group_key, [])
            if not suffixes:
                continue
            mode_rates: dict[str, float] = {}
            for mode_id, mode_name in DUNGEON_MODE_NAMES.items():
                best_rate = 0.0
                for suffix in suffixes:
                    full_grade = mode_id * 1000 + suffix
                    for _ldg_id in candidate_ids:
                        rate = self.compute_variant_rate(
                            _ldg_id, luck_grade, full_grade, item_name=item_name, _rt_cache=_rt_cache
                        )
                        if rate > best_rate:
                            best_rate = rate
                mode_rates[mode_name] = _round_rate(best_rate * 100)
            result[group_key] = mode_rates
        return result

    def compute_group_drop_rates(self, ldg_id: str, group_key: str) -> dict[str, float]:
        """Compute aggregated drop rates for all items in a lootdrop group."""
        suffixes = MODULE_GROUP_FLOOR_SUFFIXES.get(group_key, [])
        if not suffixes:
            return {}
        mode_rates: dict[str, float] = {}
        for mode_id, mode_name in DUNGEON_MODE_NAMES.items():
            best_rate = 0.0
            for suffix in suffixes:
                full_grade = mode_id * 1000 + suffix
                grade_data = self._ld_groups.get(ldg_id, {}).get(full_grade, [])
                if not grade_data:
                    continue
                for ld_id, lr_id, _ in grade_data:
                    rate_items = self._ld_rate_items.get(ld_id, {})
                    if not rate_items:
                        continue
                    _lg_weights: dict[int, int] = {}
                    for _item_name, (lg, _) in rate_items.items():
                        _w = self._ld_rate_weights.get(lr_id, {}).get(lg, 0)
                        if _w > _lg_weights.get(lg, 0):
                            _lg_weights[lg] = _w
                    _rate_total = self._ld_rate_totals.get(lr_id, 10000)
                    for lg, w in _lg_weights.items():
                        _shared = self._ld_luck_grade_count.get((ld_id, lg), 1)
                        r = w / _shared / _rate_total
                        if r > best_rate:
                            best_rate = r
            mode_rates[mode_name] = _round_rate(best_rate * 100)
        return mode_rates

    def compute_container_drop_rates(self, ldg_id: str, group_key: str) -> dict[str, float]:
        """Compute container (chest etc.) aggregated drop rates."""
        suffixes = MODULE_GROUP_FLOOR_SUFFIXES.get(group_key, [])
        if not suffixes:
            return {}
        mode_rates: dict[str, float] = {}
        for mode_id, mode_name in DUNGEON_MODE_NAMES.items():
            best_total = 0.0
            for suffix in suffixes:
                full_grade = mode_id * 1000 + suffix
                grade_data = self._ld_groups.get(ldg_id, {}).get(full_grade, [])
                if not grade_data:
                    continue
                total_any_prob = 0.0
                for ld_id, lr_id, drop_count in grade_data:
                    rate_items = self._ld_rate_items.get(ld_id, {})
                    if not rate_items:
                        continue
                    rate_total = self._ld_rate_totals.get(lr_id, 10000)
                    _lg_set: set[int] = set()
                    for _item_name, (lg, _) in rate_items.items():
                        _lg_set.add(lg)
                    ld_prob = 0.0
                    for lg in _lg_set:
                        w = self._ld_rate_weights.get(lr_id, {}).get(lg, 0)
                        if w > 0:
                            ld_prob += w / rate_total
                    if ld_prob > 0:
                        any_prob_rolls = 1.0 - (1.0 - ld_prob) ** drop_count
                        total_any_prob = 1.0 - (1.0 - total_any_prob) * (1.0 - any_prob_rolls)
                if total_any_prob > best_total:
                    best_total = total_any_prob
            mode_rates[mode_name] = _round_rate(best_total * 100)
        return mode_rates

    def compute_variant_rate(
        self,
        ldg_id: str,
        luck_grade: int,
        full_grade: int,
        item_name: str = "",
        target_ld_id: str = "",
        _rt_cache: dict[str, int] | None = None,
    ) -> float:
        """Compute drop rate by luck_grade directly (for game JSON variants)."""
        if not target_ld_id:
            _ck = (ldg_id, luck_grade, full_grade, item_name)
            _cv = self._variant_rate_cache.get(_ck)
            if _cv is not None:
                return _cv
        grade_data = self._ld_groups.get(ldg_id, {}).get(full_grade, [])
        if not grade_data:
            if not target_ld_id:
                self._variant_rate_cache[(ldg_id, luck_grade, full_grade, item_name)] = 0.0
            return 0.0
        total_weight = 0.0
        found = False
        _base = _VARIANT_RE.sub(r"\1", item_name) if item_name and _VARIANT_RE.match(item_name) else None
        for ld_id, lr_id, _ in grade_data:
            if target_ld_id and ld_id != target_ld_id:
                continue
            _found_lg = None
            if item_name:
                rate_items = self._ld_rate_items.get(ld_id, {})
                item_info = rate_items.get(item_name)
                if item_info is None:
                    for _sfx in _VARIANT_SUFFIXES:
                        item_info = rate_items.get(item_name + _sfx)
                        if item_info is not None:
                            break
                if item_info is None and _base:
                    item_info = rate_items.get(_base)
                    if item_info is None:
                        for _sfx in _VARIANT_SUFFIXES:
                            item_info = rate_items.get(_base + _sfx)
                            if item_info is not None:
                                break
                if item_info is None:
                    continue
                # Use caller's luck_grade for weight (higher grade = rarer pool),
                # but found item's luck_grade for shared count (the item lives there).
                _found_lg = item_info[0]
            found = True
            _pool_weight = self._ld_rate_weights.get(lr_id, {}).get(luck_grade, 0)
            if _pool_weight == 0:
                continue
            _shared_lg = _found_lg if _found_lg is not None else luck_grade
            _shared = self._ld_luck_grade_count.get((ld_id, _shared_lg), 1)
            if _rt_cache is not None:
                _rate_total = _rt_cache.setdefault(lr_id, self._ld_rate_totals.get(lr_id, 10000))
            else:
                _rate_total = self._ld_rate_totals.get(lr_id, 10000)
            total_weight += _pool_weight / _shared / _rate_total
        if found:
            if not target_ld_id:
                self._variant_rate_cache[(ldg_id, luck_grade, full_grade, item_name)] = total_weight
            return total_weight
        if not target_ld_id:
            self._variant_rate_cache[(ldg_id, luck_grade, full_grade, item_name)] = 0.0
        return 0.0
