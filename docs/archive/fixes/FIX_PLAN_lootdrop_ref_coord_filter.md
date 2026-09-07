# 修复计划：Lootdrop 详情页 ref 坐标未按模块过滤

## 问题

### 现象

`/lootdrops/FrozenIronKey/` 页面中，迷你宝盒组（CofferSmall）的坐标将本不该显示的非 IceAbyss 地图的坐标点也渲染了出来，导致：

1. **模块分组丢失** — 非 IceAbyss 地图的坐标没有对应模块数据（`mod: undefined`），出现在无分组的区域
2. **翻译丢失** — 无模块数据的坐标显示原始英文地图名（如 `"Cistern"`、`"Armory"`）而非中文
3. **显示异常** — 这些地图位置不含模块图片、无分组标题，显示为空白占位

### 根因

数据管道 `lootdrop_builder.py` 在 P005 优化（第 567-577 行）中，将怪物坐标替换为 `ref` 引用以减小 JSON 体积。坐标被正确过滤（仅保留 IceAbyss 组）后移除了具体坐标数组，用 `ref: "props/CofferSmall"` 和 `coord_count: 106` 替代。

**前端** fetch `props/CofferSmall.json` 后获取了全部 1080 个坐标，*没有*按 `_modules` 中的地图集合过滤，导致非 IceAbyss 地图（974 个坐标点）也被渲染。

### 受影响范围

| 怪物 | 实体总坐标 | IceAbyss 坐标 | 多余坐标 |
|------|-----------|--------------|---------|
| CofferSmall | 1080 | 106 | **974** |
| GoldChest | 87 | 7 | 80 |
| OrnateChestLarge | 312 | 31 | 281 |
| OrnateChestMedium | 579 | 49 | 530 |
| OrnateChestSmall | 1098 | 106 | 992 |
| FrostWyvern | 1 | 1 | 0 |

所有含 `ref` 的 lootdrop 详情页理论上都可能受此影响，但目前仅限于特定组别（非全组通用的）掉落较为明显。

## 修复方案

### 方案：前端过滤 `refCoords`

在 `LootdropDetailPage.tsx` 的 `resolvedMonsters` useMemo 中，对通过 `ref` 加载的坐标按 `modules` map 过滤：

**位置**：`web/src/pages/LootdropDetailPage.tsx`，第 407-413 行

```tsx
const resolvedMonsters = useMemo(
    () =>
      monsters.map((m) => ({
        ...m,
        coords: (m.coords ?? refCoords.get(m.ref!) ?? [])  // 仅保留坐标中 map 存在于 modules 的
          .filter(c => !m.ref || modules.size === 0 || modules.has(c.map)),
      })),
    [monsters, refCoords, modules]
);
```

### 过滤逻辑

- `m.coords` 有值？→ 直接使用（已经过管道过滤的内联坐标，跳过过滤）
- `m.ref` 存在且 `modules.size > 0`？→ 过滤 `c.map ∈ modules.keys()`
- `modules` 为空（如 SSR quick 模式无模块数据）？→ 不过滤，显示全部

### 影响评估

- **正面**：
  - 迷你宝盒组只显示 IceAbyss 的 106 个坐标点，不再有孤立无分组的非 IceAbyss 地图
  - 所有地图正确显示中文模块名（`mod?.translation`）
  - 坐标点数量与 `coord_count` 一致，用户感知正确
  - 不影响 inline coords 的怪物（数据管道已预先过滤）

- **负面**：
  - 微小性能开销：每次 `resolvedMonsters` 重新计算时需遍历坐标数组进行过滤（O(n)，n ≤ 1080，极微）
  - 不影响 SSR 内容：SSR 预加载的 refCoords 同样会经过此过滤

### 不涉及的修改

- 不改动数据管道（`_modules` 和 `coord_count` 已经正确）
- 不改动 SSG 脚本（SSR 数据缓存的 refCoords 会被前端的过滤逻辑处理）
- 不改动其他页面组件

## 验证方式

1. 构建前端：`cd web && npm run build`
2. 启动预览：`cd web && npx vite preview --port 8080 --host 0.0.0.0`
3. 打开 `http://localhost:8080/lootdrops/FrozenIronKey/`
4. 确认迷你宝盒组的坐标点只出现在 IceAbyss 模块地图上
5. 所有地图区块应显示中文名称（倒金字塔、冰迷宫、石柱廊等）
6. 调试模式下查看总数应为 106（与 coord_count 一致）
