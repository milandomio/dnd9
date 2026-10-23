# 地牢商店装备槽分组改进计划

> 状态：**已实施**（后端类别/稀有度键 + 两级分组 + 汇总行渲染）。
> 实施中按用户要求调整了最终形态：装备槽不再渲染任何物品卡片，改为「标签 ×件数 · 累计概率 + 共同价格」的汇总行；小型神器组同样只显示一行。详见「四、前端改动」的最终实现与「八、实施记录」。
> 关联：`docs/plans/LOOTDROP_ITEM_TYPE_GROUPING.md`（lootdrops 列表页的类型分组，已完成）。
> 相关提交：`fdca4cb8` 地牢商店新增装备槽（Equip 共享库存按 Schedule 归属展开）。

## 一、目标

装备槽（slot 90）当前只按「稀有度 × 件数 · 累计爆率」分一层组，需要改成三层信息：

```
独特 ×207 · 累计 1.9799%
  ├─ 饰品 ×19 · 累计 0.1817%
  ├─ 护甲 ×144 · 累计 1.3773%
  └─ 武器 ×44 · 累计 0.4209%
小型神器 ×10 · 累计 1.0043%
  ├─ 护甲 ×3 · 累计 0.3013%      ← 组内每张卡显示自身概率 0.1004%
  └─ 武器 ×7 · 累计 0.7030%
```

三条需求：

1. **组内按类别细分**：在每个稀有度组内继续按 lootdrops 的「饰品 / 护甲 / 武器」分类合并显示，并给出该分类的累计爆率。
2. **稀有度词汉化**：分组标题里的 `Unique` 等英文串改为游戏 i18n（`独特` / `传奇` / `史诗`）。
3. **小型神器组**：含「血缚」（Bloodbound）的 10 件分组不再叫 `Epic ×10`，改名为「小型神器」；组内每张物品卡补充显示自身实际概率，与其他槽位的卡片一致。

## 二、现状与实测数据

### 数据文件

`data/json/dungeon_shops/{Crypts,Goblin,IceCavern}.json` → `difficulties[].slots[]`，装备槽 `slot === 90`，每难度 **631** 项，三地区共用同一个池（`InGameMerchantStockBuy_GoblinSmuggler_Equip_{N,HR}_{01,02,03}` 三份资产内容完全相同，由所有 Schedule 引用）。

### 每项现有字段（`web/src/types/data.ts: ShopItem`）

`name` `page` `translation` `translation_key` `price` `currency` `count` `stock` `rate` `slot_total` `chance` `rarity` `map_exclusive` `effect`

**缺少**：物品类别（饰品/护甲/武器）、稀有度翻译键。这两项是本次需求的阻塞点。

### 分组实测（N / HR 同池，稀有度整体差一档）

`slot_total = 104550`（N 与 HR 相同）。

| rate | 件数 | 单件 chance | 组累计 | 稀有度 N / HR |
|------|------|-------------|--------|----------------|
| 300 | 207 | 0.286940% | 59.3974% | Rare / Epic |
| 190 | 207 | 0.181731% | 37.6184% | Epic / Legend |
| 10 | 207 | 0.009565% | 1.9799% | Legend / **Unique** |
| **105** | **10** | **0.100430%** | **1.0043%** | Epic / Epic（小型神器池） |

三档 207 件组的类别构成相同：**饰品 19 / 护甲 144 / 武器 44**。

各组合计（用 `item_entities` 类别实测）：

```
Unique ×207 累计 1.9799% | 饰品×19 (0.1817%), 护甲×144 (1.3773%), 武器×44 (0.4209%)
Legend ×207 累计 37.6184% | 饰品×19 (3.4529%), 护甲×144 (26.1693%), 武器×44 (7.9962%)
Epic   ×207 累计 59.3974% | 饰品×19 (5.4519%), 护甲×144 (41.3199%), 武器×44 (12.6255%)
Epic   × 10 累计 1.0043% | 护甲×3 (0.3013%), 武器×7 (0.7030%)   ← 小型神器
```

### 小型神器 10 件清单

`Bloodbound`(血缚, 武器/剑) `BloodsapBlade`(武器/剑) `BowofEndlessThirst`(武器/弓) `GrimveilCloak`(护甲/布) `HazeBlade`(武器/匕首) `SoulDevotedFolio`(武器/魔法书) `SpellplunderRod`(武器/魔杖·法杖) `StillmendBoots`(护甲/皮甲) `TanglethreadTrousers`(护甲/皮甲) `ThornShield`(武器/盾)

识别依据：这批在 `Equip_*` 库存里 `ItemRate = 105`，与三档 300/190/10 并列，是游戏独立的一档权重池。

**不要**用下面两种标记判定，均不完整：

- `lootdrops.json` 的 `hr100`（豪客赛掉率 ≥100% 且 spawn_rate <5%）：10 件里只有 7 件为真（Bloodbound、BowofEndlessThirst 不是，GrimveilCloak 根本不在 lootdrops 索引里）。
- 物品能力名含 `MinorArtifact`：10 件里只有 4 件（Bloodbound、BowofEndlessThirst、GrimveilCloak、SoulDevotedFolio）。

也不要复用列表页的「小型神器」分组（那是 `hr100` 语义），两处判定不同，需在代码注释里点明。

### 已落地（未提交，工作区 WIP）

第一层分组已经实现，后续会话不要重复做：

- `web/src/utils/shopEquipment.ts`（新文件）：`EquipmentGroup`、`groupEquipmentByChance()`（按 `Math.round(chance*1e9)` 量化聚合、按 `cumulative` 升序）、`formatChancePercent()`。
- `web/src/pages/DungeonShopDetailPage.tsx`：slot 90 改为按组渲染 `{rarity} ×{n} · 累计 {x}`，组内卡片 `showChance={false}`。
- `web/src/i18n/uiLocale.ts`：新增 `ui.shops.cumulative_rate`（10 语言）、`ui.shops.slot.equipment`、`ui.module.suffix.edge/corner`。

本计划是在此基础上的增量：类别二级分组、稀有度 i18n、小型神器组。

## 三、数据层改动

### 1. 类别来源

唯一可靠来源是 DB `item_entities`：`item_type`(Armor/Accessory/Weapon/…) + `item_category_key`(游戏翻译键) + `item_subtype_keys`，由 `api/src/db/importers/items.py` 从物品资产 `ItemType` 解析，787 行，**631 件商店装备全部命中**（含 GrimveilCloak）。

反例：`api/src/collector.py` 现在构造 `shop_item_index` 时用的是 `loot_index`（即 `data/json/lootdrops.json` 的 524 条），GrimveilCloak 不在其中 → 必须改成并入 `item_entities`。

### 2. `api/src/merchant_builder.py`

- `build_shop_data()` 新增参数 `item_categories: dict[str, dict]`（`page` → `{"item_type", "category_key"}`）。
- 每项输出追加：
  - `item_type`：`Armor` / `Accessory` / `Weapon`（缺失时空串）
  - `item_category_key`：`Text_Code_DCDataBlueprintLibrary_Type_Item_Category_*`（前端直接用游戏 locale 渲染）
  - `rarity_key`：`Text_Code_DCDataBlueprintLibrary_Type_Item_Rarity_{Rarity}` ← 由现有 `SUFFIX_RARITY` 拼出，无需新增映射表；`8001` 已对应 `Artifact`（`命名神器`）
  - `pool`：`"mini_artifact"` 当 `item_rate == MINI_ARTIFACT_RATE`，否则 `"tier"`
- 常量：`MINI_ARTIFACT_RATE = 105`，注释写明是 `Equip_*` 库存里与 300/190/10 并列的独立权重组（10 件，含血缚）。

### 3. `api/src/collector.py`

`shop_item_index` 里补类别字段（`db.get_item_entities()` 已加载为 `items`），保持「导出阶段不读游戏资产」的边界。

### 4. 不需要动的部分

- DB schema 不改（`item_entities` 已有全部字段）。
- 概率计算不改（`chance = item_rate / slot_total` 已经正确）。

## 四、前端改动

### 1. `web/src/types/data.ts`

`ShopItem` 追加 `item_type?` `item_category_key?` `rarity_key?` `pool?`（可选，兼容旧数据）。

### 2. `web/src/utils/shopEquipment.ts`

现在：

```ts
interface EquipmentGroup { chance: number; cumulative: number; items: ShopItem[] }
groupEquipmentByChance(items): EquipmentGroup[]   // 按 chance 量化分组，按 cumulative 升序
formatChancePercent(chance): string               // 0.002869 -> "0.2869%"
```

改成：

```ts
interface EquipmentCategoryGroup {
  category_key: string;      // 游戏翻译键，空串表示未分类
  cumulative: number;
  items: ShopItem[];
}
interface EquipmentGroup {
  pool: 'tier' | 'mini_artifact';
  rarity: string;            // 原始枚举，用于配色（RARITY_COLORS）
  rarity_key: string;        // 游戏翻译键，用于显示
  chance: number;
  cumulative: number;
  categories: EquipmentCategoryGroup[];
  items: ShopItem[];         // 仍保留扁平列表，便于 focus/scroll
}
```

- 分组键：`pool` + `chance`（小型神器池单独成组，不参与稀有度聚合）。
- 组内按 `item_category_key` 再聚合，双键排序：组按 `cumulative` 升序（现状保留），类别组也按 `cumulative` 升序。
- 缺 `item_category_key` 的条目落到该组一个「未分类」子块（category_key 为空串），不丢弃。

### 3. `web/src/pages/DungeonShopDetailPage.tsx`（最终实现）

装备槽**不渲染物品卡片**，改为汇总行（`EquipmentSummaryRow`），三列布局：标签 · 累计概率 · 价格（右对齐）。

- 稀有度行：`{t(group.rarity_key) || group.rarity_label} ×{n} · 累计 {x}`，价格加粗底色
- 小型神器行：`{ut('ui.shops.mini_artifact')} ×{n} · 累计 {x}`（不显示 Epic，不拆类别），下方渲染 10 张 `ShopItemCard`，`showChance` + `preciseChance` 同时开启
- 类别行：`{t(category_key) || label} ×{m} · 累计 {y}`，缩进、无底色；空键用 `ut('ui.list.item_group_unknown')`
- 价格：组内所有条目同价（实测 N: 罕见50/史诗200/传奇300、HR: 史诗200/传奇300/独特500、小型神器 500），`uniform()` 取共同值；不一致则返回 0 并隐藏该列

实测渲染（zh-Hans，Crypts · 普通）：

```
小型神器 ×10 · 累计 1.0043%        500金
  [血缚 史诗 0.1004%概率 500金] [吸血之刃 ...] ... （10 张卡）
独特 ×207 · 累计 1.9799%           500金
  饰品 ×19 · 累计 0.1817%          500金
  武器 ×44 · 累计 0.4209%          500金
  护甲 ×144 · 累计 1.3773%         500金
传奇 ×207 · 累计 37.6184%          300金
  ...
```

### 4. i18n 键

- 稀有度、类别：**不新增**，直接用游戏 locale（`data/json/locale/*.json` 已含 10 语言，`useLocale().t(key)` 可渲染）：

```
Text_Code_DCDataBlueprintLibrary_Type_Item_Rarity_{Poor,Common,Uncommon,Rare,Epic,Legend,Unique,Artifact}
   → 粗糙 普通 优秀 罕见 史诗 传奇 独特 命名神器
Text_Code_DCDataBlueprintLibrary_Type_Item_Category_{Utility,Misc,Accessory,Armor,Weapon}
   → 辅助道具 杂项 饰品 护甲 武器
```

- 只新增 `ui.shops.mini_artifact`（10 语言，中文「小型神器」）。`ui.shops.cumulative_rate` 已存在（`累计 {rate}`）。

## 五、已决定的实现口径

1. **三档常规稀有度不显示具体物品名**：饰品/护甲/武器只显示「类别 ×件数 · 累计概率 · 价格」，具体条目（獾吊坠、熊吊坠等）一律不渲染。物品名仍保留在 JSON 与搜索索引里，页面只是不再罗列。
2. **小型神器显示物品卡片**：这一组必须保留 10 张卡（血缚、吸血之刃、永饮弓……），每张卡标注自身爆率 `0.1004%`（四位小数，两位有效数字会显示成 `0.1%` 看不出是同一权重）。该组不拆 饰品/护甲/武器。
3. **次级行按累计概率升序**：饰品 → 武器 → 护甲（0.1817% → 0.4209% → 1.3773%），与分组排序口径一致。
4. **价格来源于组内共同值**：`uniform()` 校验；将来若游戏改成同档不同价，会自动隐藏价格列而不是显示错值。
5. ~~未分类兜底键是否覆盖 10 语言~~（已确认：`ui.list.item_group_unknown` 10 语言齐备）。

### 概率口径校验（为何 10 × 0.1% = 1.0043% 而不是 1.0%）

```
slot_total = 104550 = 300×207 + 190×207 + 10×207 + 105×10
单件 chance = 105 / 104550 = 0.0010043041606886...
            = 0.10043041606886...%   ← 卡片显示 0.1004%
10 件累计   = 1050 / 104550 = 0.010043041606888...
            = 1.0043041606888...%    ← 标题显示 1.0043%
```

卡片上的 0.1% 是四位小数 `0.1004%` 的显示值，四舍五入到一位就是 0.1%，**不是 0.1**。10 × 0.100430% = 1.00430%，与标题完全一致。自检脚本：`sum(item.rate) == slot_total`（实测 104550 == 104550），`sum(10 件 chance) == 1050/104550`。

## 六、验证结果（已全部通过）

1. 后端单测 39 项通过（`api/tests/test_merchant_builder.py`，新增 `EquipmentCategoryTest` 5 项：类别映射、`rarity_key`、`mini_artifact` 识别、缺失兜底、已翻译标签）。`./api/lint.sh` 通过。
2. 全量管道 `python main.py` 后复核 `data/json/dungeon_shops/Crypts.json`：631 项 **0 项缺类别**；`pool` 计数 `tier 621 / mini_artifact 10`；类别计数 护甲 435 / 武器 139 / 饰品 57；N 与 HR 完全一致。
3. `npx tsc --noEmit` 无错，`npm run lint` 0 error（20 条既有 warning），Prettier 通过。
4. SSG 构建成功（2980 页 / 15407 文件），`vite preview` 8081 三地区 + 多语言全部 HTTP 200。
5. 静态 HTML 与截图核对：zh-Hans 显示「小型神器 ×10 · 累计 1.0043%」「独特 ×207 · 累计 1.9799%」「饰品 ×19 · 累计 0.1817%」，物品名（血缚等）**不再出现**，价格列 500/300/200 正确。
6. 多语言核对：en `Minor Artifact / Unique / Accessory`、ja `小型神器 / ユニーク / アクセサリー`、ru `Малый артефакт / Уникальное / Аксессуар`，均随游戏 i18n 变化。

## 七、风险

- 稀有度随难度整体偏移一档（N: Legend/Epic/Rare，HR: Unique/Legend/Epic），同一池两套标签。组标题必须按**当前难度**的 rarity 显示，不能写死 HR 的 Unique。
- 未分类兜底：新增类别字段后，若某次导入 `item_entities` 为空（DB-only 模式），全部条目会落到单一「未分类」子块；需要保证 `get_item_entities()` 在 DB-only 下仍可用（它是 DB 表，不读游戏目录，安全）。
- 概率口径：组内类别累计是「抽到该类别任一物品」的合计，不要与单件概率混排在同一视觉层级，靠标题区分。

## 八、实施记录

| 文件 | 改动 |
|------|------|
| `api/src/merchant_builder.py` | 新增 `EQUIPMENT_SLOT = 90`、`MINI_ARTIFACT_RATE = 105`、`RARITY_KEY_PREFIX`；`build_shop_data()` 新增 `item_categories` 参数；每项输出 `rarity_key` / `rarity_label` / `item_type` / `item_category_key` / `item_category_label` / `pool` |
| `api/src/collector.py` | 从 `item_entities` 构造 `shop_item_categories`（按 `item_name` 折叠键）传入 `build_shop_data` |
| `api/tests/test_merchant_builder.py` | 新增 `EquipmentCategoryTest`（5 项） |
| `web/src/types/data.ts` | `ShopItem` 追加 `rarity_key?` / `rarity_label?` / `item_type?` / `item_category_key?` / `item_category_label?` / `pool?` |
| `web/src/utils/shopEquipment.ts` | 两级分组 + `uniform()` 共同值 + `formatChancePercent()` |
| `web/src/pages/DungeonShopDetailPage.tsx` | slot 90 改渲染 `EquipmentSummaryRow`；新增 `groupHeadline()` / `categoryName()` |
| `web/src/i18n/uiLocale.ts` | 新增 `ui.shops.mini_artifact`（10 语言） |

### 关键坑（勿重犯）

1. **默认语言不加载游戏字典**：zh-Hans 走 `lang === DEFAULT_LANG → dict = null` 分支，`t(gameKey)` 直接回落。所以组标题必须用后端下发的 `rarity_label` / `item_category_label`，只用 `t(key)` 会渲染出英文 `Unique` 和「未分类」。
2. **`item_entities` 用的是折叠名**：key 是 `GrimveilCloak` 而非 `GrimveilCloak_5001`，查表要 `fold_item_page()` 兜底。
3. **价格唯一性必须校验**：直接取 `items[0].price` 会在未来游戏改价时静默显示错值，`uniform()` 不一致返回 0 并隐藏。
4. **小型神器判定用 `item_rate == 105`**，不要用 `hr100` 或能力名 `MinorArtifact`（覆盖度 7/10、4/10）。
