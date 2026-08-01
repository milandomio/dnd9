# Lootdrop 物品类型分组计划

## 目标

将 `/zh-Hans/lootdrops/` 中目前依赖 `variant_count`、`max_score` 的“物品 / 饰品 / 武器装备”粗略分类，改为读取游戏物品资产的真实 `ItemType` 和子类型属性，并在分类标签中显示多语言名称。

目标显示形式：

- `辅助道具：消耗品`
- `杂项：宝藏`
- `饰品：戒指`
- `护甲：皮甲`
- `武器：剑`

`神器`、`小型神器`、`稀有掉落` 仍保留现有特殊分组优先级，不参与普通类型拆分。

## 数据链路

```text
游戏 Item JSON
  -> ItemsImporter
  -> item_entities
  -> build_loot_index()
  -> lootdrops.json / search_index.json
  -> ListPage 分组标签
```

当前 `ItemsImporter` 只保存物品名称翻译键，必须在入库阶段保存类型元数据。导出阶段禁止直接读取游戏 JSON，继续遵守“游戏 JSON 只由 importer 读取”的边界。

## 类型解析

### 一级分类

根据 `Properties.ItemType` 解析枚举值：

```text
EItemType::Armor     -> Text_Code_DCDataBlueprintLibrary_Type_Item_Category_Armor
EItemType::Accessory -> Text_Code_DCDataBlueprintLibrary_Type_Item_Category_Accessory
EItemType::Weapon    -> Text_Code_DCDataBlueprintLibrary_Type_Item_Category_Weapon
EItemType::Utility   -> Text_Code_DCDataBlueprintLibrary_Type_Item_Category_Utility
EItemType::Misc      -> Text_Code_DCDataBlueprintLibrary_Type_Item_Category_Misc
```

### 子分类

将 Gameplay Tag `Type.Item.<Category>.<Subtype...>` 转成对应翻译键：

```text
Type.Item.Armor.Leather       -> ..._Type_Item_Armor_Leather
Type.Item.Utility.Consumable  -> ..._Type_Item_Utility_Consumable
Type.Item.Misc.Treasure       -> ..._Type_Item_Misc_Treasure
Type.Item.Accessory.Ring       -> ..._Type_Item_Accessory_Ring
Type.Item.Weapon.Sword         -> ..._Type_Item_Weapon_Sword
```

`ArmorType`、`MiscType`、`UtilityType`、`AccessoryType` 读取单个 `TagName`；`WeaponTypes` 读取数组并保留全部键，避免丢失多标签武器信息。没有子类型时只显示一级分类，无法解析时进入未分类兜底组。

## 后端改动

1. `api/src/db/schema.py`
   - 为 `item_entities` 增加 `item_type`、`item_category_key`、`item_subtype_keys` 字段。
   - 增加旧数据库迁移字段。

2. `api/src/db/importers/items.py`
   - 读取首个可用物品变体的类型属性。
   - 同一物品各品质变体类型不一致时记录警告，并使用确定性的首个有效值。

3. `api/src/db/repositories/items.py`
   - 返回新增字段。
   - 旧 DB-only 数据库缺少字段时返回空默认值，避免源目录不可用时运行失败。

4. `api/src/db_freshness.py`
   - 提升生成器版本，使旧数据库在源数据可用时自动重建。
   - 保留现有 `.building` 数据库原子替换机制。

5. `api/src/lootdrop_builder.py`
   - 将类型键和简体中文 fallback 翻译写入 `lootdrops.json`。
   - `_8001` 物品继续复用基础物品的类型元数据。

6. `api/src/index_export.py`、`api/src/search_index_builder.py`
   - 将类型元数据同步到 SSR 使用的 `search_index.json` 及各语言搜索索引。

7. `api/src/locale_builder.py` / `api/src/collector.py`
   - 将一级、子类型翻译键加入 locale 使用键集合，确保 10 种语言的 locale 文件包含这些键。

## 前端改动

1. `web/src/pages/ListPage.tsx`
   - 特殊分组保持原逻辑。
   - 其余掉落项按 `item_category_key + item_subtype_keys` 的稳定键分组，不按本地化文本分组。
   - 标签名通过游戏翻译键渲染，使用 UI 模板拼接一级分类和子分类。
   - 保持当前“只渲染一个选中分类”的标签交互。
   - 新数据缺少类型字段时暂时回退旧的三组规则。

2. `web/src/i18n/uiLocale.ts`
   - 为 10 种语言增加类型分组模板和未分类文案。
   - 中文使用 `：`，英文等语言使用各自自然的分隔格式。

## 验证计划

1. 后端单元测试覆盖 Armor、Accessory、Weapon、Utility、Misc、缺失子类型及多 WeaponTypes。
2. 验证重建前后 lootdrop 总数不减少，特殊分组数量保持可追踪。
3. 验证示例键在所有语言中有值，缺失翻译可回退简体中文。
4. 执行 `python main.py` 生成 DB、JSON 和 locale 文件。
5. 执行前端格式检查、ESLint、TypeScript 和 quick SSG。
6. 使用 Playwright 验证 `/zh-Hans/lootdrops/` 标签数量、标签文本和单分类显示。
7. 验证 `http://localhost:8080/zh-Hans/lootdrops/` 返回 HTTP 200。

## 完成标准

- 普通分组名称不再依赖 `variant_count` 猜测。
- 分类键在不同语言下保持一致，显示文本随语言切换。
- 页面每次只显示一个分类内容。
- 旧数据库和源不可用的 DB-only 模式不崩溃。
- 数据管道、SSG、页面交互和现有测试全部通过。

## 实施结果

- 已完成 DB 字段、导入解析、lootdrop/search index 输出、locale 使用键和前端标签切换。
- 完整管道生成 787 条带物品类型的 DB 记录、478 个 lootdrop 条目和 10 种 locale 文件；普通掉落条目无缺失类型元数据。
- 当前列表生成 46 个标签；默认 `神器（28）`，`辅助道具：消耗品（15）` 可正常切换。
- 分类按钮按一级 `ItemType` 分行，同一大类的子分类保持同一行；例如饰品行结束后，护甲分类从下一行开始。
- 按钮使用内容宽度排列，不会因一行按钮数量不足而拉伸填满整行。
- 标签使用紧凑格式：大类行首为 `⚔️【武器：】`，子类按钮为 `【斧(5)】`，特殊分组为 `🏺【神器(28)】`，不在标签文本中插入空格。
- 多个有效子类型的物品分别加入每个子类型组；例如同时属于锤和杖的物品会分别出现在 `锤`、`杖`，不创建 `锤、杖` 组合组。无有效翻译的子类型统一合并到该大类的一个未分类组。
- 英文等语言遇到游戏翻译表缺失的类型键时，前端将键名视为无效翻译并回退到对应语言的 `Uncategorized`，不展示内部键名。
- 验证通过：31 个后端测试、Ruff、Black、Prettier、TypeScript、quick SSG、HTTP 200 和中英文 Playwright 标签切换。
