# LocationStats / 地图模块名 i18n 缺口分析

> 创建日期: 2026-07-26  
> 状态: 待修复  
> 复现 URL: `http://localhost:8090/en/lootdrops/WarMaul_5001/`

---

## 1. 现象

英文详情页底部：

1. **公共组件文案仍为中文**：`位置统计：共 44 个位置点` / `包含地图：…`
2. **地图模块名列表未走 i18n**：`modules.get(k)?.translation` 直接取中文真值，未用 `t(translation_key, translation)`

地图卡片标题（h3）已正确：`t(mod?.translation_key, mod?.translation || …)`，仅底部统计区漏掉。

---

## 2. 根因

### 2.1 `LocationStats` 硬编码中文

`web/src/components/LocationStats.tsx`：

```tsx
<strong>位置统计：共 {count} 个位置点</strong>
<strong>包含地图：</strong>
{mapTranslations.join('、')}
```

- 未调用 `useLocale` / `ut`
- 分隔符固定为中文顿号 `、`（非中文语言应用 `, `）

### 2.2 调用方传入未本地化的模块名

| 文件 | 位置 | 问题 |
|------|------|------|
| `DetailPage.tsx` | ~1186–1190 | `modules.get(k)?.translation \|\| k` |
| `LootdropDetailPage.tsx` | ~1682–1686 | 同上 |
| `QuestItemGroupPage.tsx` | ~809–811 | UI 文案已 `ut`，地图名仍用 `.translation` |

对比同页已正确写法（Lootdrop 地图 h3 ~1153）：

```tsx
t(mod?.translation_key, mod?.translation || mod?.name || mapName)
```

### 2.3 调试表 `mapLabel` 同样未本地化

| 文件 | 字段 |
|------|------|
| `DetailPage.tsx` ~1211 | `mapLabel: mod?.translation \|\| c.map` |
| `LootdropDetailPage.tsx` ~1630 | 同上 |
| `QuestItemGroupPage.tsx` ~749 | 同上 |

### 2.4 UI 字典已有近似 key，未复用到公共组件

| key | 用途 | 现状 |
|-----|------|------|
| `ui.module_detail.pos_stat` | 「位置统计：共 {count} 个位置点」 | 仅 `DungeonModuleDetailPage` |
| `ui.quest_group.pos_stat` | 同上文案 | 仅 `QuestItemGroupPage` 内联 |
| `ui.quest_group.map_includes` | 「包含地图：」 | 仅 `QuestItemGroupPage` 内联 |

`LocationStats` 与详情页底部**未使用**上述 key，导致三处文案分裂。

---

## 3. 数据侧确认

`DungeonModule`（`web/src/types/data.ts`）含：

- `translation` — 中文真值（如「信徒会所」）
- `translation_key` — 如 `Text_DesignData_Dungeon_DungeonModule_Admirer_Room`

`data/json/dungeon_modules.json` 样本字段齐全；locale 字典可按 `translation_key` 采样。

---

## 4. 修复方案

### 4.1 统一 UI key（推荐）

在 `uiLocale.ts` 全语言增加（或复用并重命名语义）：

| key | zh-Hans 示例 |
|-----|----------------|
| `ui.location.pos_stat` | `位置统计：共 {count} 个位置点` |
| `ui.location.map_includes` | `包含地图：` |
| `ui.location.map_sep` | `、`（en: `, `） |

可选：让 `ui.module_detail.pos_stat` / `ui.quest_group.pos_stat` 与 `ui.location.pos_stat` 同值，或逐步收敛到 `ui.location.*`，避免再复制。

### 4.2 改造 `LocationStats`

```tsx
// 伪代码
const { t, ut } = useLocale();
const sep = ut('ui.location.map_sep'); // 或 lang === 'zh-Hans' ? '、' : ', '
return (
  <>
    <strong>{ut('ui.location.pos_stat').replace('{count}', String(count))}</strong>
    <br />
    <strong>{ut('ui.location.map_includes')}</strong>
    {mapKeys.map((k) => {
      const mod = modules?.get(k);
      return t(mod?.translation_key, mod?.translation || k);
    }).join(sep)}
  </>
);
```

**两种传参策略（二选一）：**

- **A（推荐）**：组件内 `useLocale` + 接收 `mapKeys: string[]` + `modules: Map<…>`，自行 `t(translation_key)`
- **B**：调用方已 `t` 后传入 `mapTranslations: string[]`，组件只做 UI 文案 i18n

选 A 可一次修掉所有调用方漏 `t`；选 B 改动面更小但调用方易再漏。

### 4.3 调用点修改清单

| 文件 | 改动 |
|------|------|
| `LocationStats.tsx` | i18n 文案 +（若 A）模块名采样 |
| `DetailPage.tsx` | 底部 LocationStats；debug `mapLabel` 用 `t` |
| `LootdropDetailPage.tsx` | 同上 |
| `QuestItemGroupPage.tsx` | 底部地图名 `t`；可改为复用 `LocationStats` 去重 |
| `uiLocale.ts` | 10 语言补 `ui.location.*`（若新增） |

### 4.4 不做 / 注意

- 不改 `data/` 生成物；modules JSON 已有 `translation_key`
- 分隔符：中文 `、`，其它语言 `, `
- Hydration：组件 CSR 用 `ut/t`，与现有详情页模式一致（SSR 中文 body + 客户端切语言）

---

## 5. 验收

1. 打开 `/en/lootdrops/WarMaul_5001/`  
   - 底部：`Total: N positions`（或 en 字典等价文案）  
   - 「包含地图」后为英文模块名（与地图 h3 一致）  
2. `/zh-Hans/lootdrops/WarMaul_5001/` 仍为中文 + `、`  
3. items/monsters/props 详情页底部同样本地化  
4. 任务物品分组页底部地图名同步  
5. format + tsc 通过  

---

## 6. 相关文件速查

```
web/src/components/LocationStats.tsx          # 硬编码中文
web/src/pages/DetailPage.tsx                  # 调用 + mapLabel
web/src/pages/LootdropDetailPage.tsx          # 调用 + mapLabel；h3 已正确 t()
web/src/pages/QuestItemGroupPage.tsx          # 内联 ut，地图名未 t
web/src/pages/DungeonModuleDetailPage.tsx     # 已用 ui.module_detail.pos_stat
web/src/i18n/uiLocale.ts                      # pos_stat / map_includes 已存在但未统一
web/src/i18n/useLocale.ts                     # t / ut
web/src/types/data.ts                         # DungeonModule.translation_key
```
