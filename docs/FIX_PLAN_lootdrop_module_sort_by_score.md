# 修复计划：Lootdrop 详情页地图模块按综合爆率排序

## 目标

将 `LootdropDetailPage` 中模块的排列逻辑从"按尺寸+点数"改为"按综合爆率总分"降序排列，实现：

- 高价值（高 spawn_rate × 高豪客赛率 × 多坐标点）的模块排前面
- 点击怪物分类按钮切换显隐时自动重算排序

## 总分计算公式

```
模块总分 = Σ ( spawn_rate × 豪客赛_rate × coords_count )
          对模块上每个可见的怪物类型求和
```

数据来源：`data.group_drop_info[groupName]` → 按 `translation` 匹配怪物 → `spawn_rate` × `drop_rates.豪客赛`

### 示例（伪王座，仅显示黄金宝箱 + 狮头宝箱 + 迷你宝盒组）

| 怪物 | spawn_rate | 豪客赛率 | 该模块上点数 | 贡献 |
|------|-----------|---------|------------|------|
| 黄金宝箱 | 100 | 25 | 1 | 2500 |
| 狮头宝箱(特殊)(可能上锁) | 50 | 3 | 2 | 300 |
| 迷你宝盒组 | 3 | 25 | 7 | 525 |
| **模块总分** | | | | **3325** |

## 修改位置

`web/src/pages/LootdropDetailPage.tsx`

### 1. 新增 useMemo：构建 group_drop_info 查找表

```typescript
const groupDropRateLookup = useMemo(() => {
  const lookup = new Map<string, Map<string, { sr: number; dr: number }>>();
  if (!data?.group_drop_info) return lookup;
  for (const [g, entries] of Object.entries(data.group_drop_info)) {
    const m = new Map<string, { sr: number; dr: number }>();
    for (const e of entries) {
      m.set(e.translation, { sr: e.spawn_rate, dr: e.drop_rates["豪客赛"] ?? 0 });
    }
    lookup.set(g, m);
  }
  return lookup;
}, [data?.group_drop_info]);
```

### 2. 修改组内排序（原第 525-534 行）

**当前**：`size_y → size_x → dots.length`

**改为**：倒序排列，**一级 `模块总分` 降序，二级 `dots.length` 降序，三级 `size_y → size_x`**

```typescript
for (const group of groupedByType.values()) {
  const _gName = group[0]?.mod?.group || '';
  const _rl = groupDropRateLookup.get(_gName) ?? new Map();
  group.sort((a, b) => {
    const scoreA = computeModuleScore(a, _rl);
    const scoreB = computeModuleScore(b, _rl);
    if (scoreA !== scoreB) return scoreB - scoreA;
    if (a.dots.length !== b.dots.length) return b.dots.length - a.dots.length;
    const sy_a = a.mod?.size_y ?? 1;
    const sy_b = b.mod?.size_y ?? 1;
    if (sy_a !== sy_b) return sy_a - sy_b;
    const sx_a = a.mod?.size_x ?? 1;
    const sx_b = b.mod?.size_x ?? 1;
    return sx_a - sx_b;
  });
}
```

### 3. 修改分组间排序（原第 538-548 行）

**当前**：总 `dots.length` 降序

**改为**：组内所有模块总分之和降序 → 总 dots.length 降序 → groupOrder

```typescript
const sortedGroups = [...groupedByType.entries()].sort(
  ([a, aItems], [b, bItems]) => {
    const _gA = aItems[0]?.mod?.group || '';
    const _gB = bItems[0]?.mod?.group || '';
    const _rlA = groupDropRateLookup.get(_gA) ?? new Map();
    const _rlB = groupDropRateLookup.get(_gB) ?? new Map();
    const totalA = aItems.reduce((s, item) => s + computeModuleScore(item, _rlA), 0);
    const totalB = bItems.reduce((s, item) => s + computeModuleScore(item, _rlB), 0);
    if (totalA !== totalB) return totalB - totalA;
    const dotA = aItems.reduce((s, item) => s + item.dots.length, 0);
    const dotB = bItems.reduce((s, item) => s + item.dots.length, 0);
    if (dotA !== dotB) return dotB - dotA;
    if (!a && !b) return 0;
    if (!a) return 1;
    if (!b) return -1;
    return groupOrder.indexOf(a) - groupOrder.indexOf(b);
  }
);
```

### 4. 辅助函数

```typescript
function computeModuleScore(
  item: { mod?: DungeonModule; dots: { monster: LootdropMonster }[] },
  rateLookup: Map<string, { sr: number; dr: number }>
): number {
  const counts = new Map<string, number>();
  for (const d of item.dots) {
    counts.set(d.monster.translation, (counts.get(d.monster.translation) ?? 0) + 1);
  }
  let total = 0;
  for (const [trans, cnt] of counts) {
    const r = rateLookup.get(trans);
    if (r) {
      total += r.sr * r.dr * cnt;
    }
  }
  return total;
}
```

## 重算触发

`group.sort()` 和 `sortedGroups` 位于 render 函数体（非 useMemo），每次 state 变化（如 `setHidden`）都会重新执行。`mapGroups` 已在构建时跳过隐藏怪物，排序因此自动反映当前可见状态。**无需额外触发机制**。

## 验证步骤

1. 打开 `/lootdrops/FrozenIronKey/`
2. 只点击三个分类按钮：黄金宝箱、狮头宝箱(特殊)(可能上锁)、迷你宝盒组
3. 观察伪王座（及其他模块）的排列顺序与计算出的总分一致
4. 切换显示其他怪物，确认排序自动重算
5. 调试模式下确认总分与人工计算一致

## 不涉及的修改

- 不改动数据管道 / 后端
- 不改动 SSG 脚本
- 不改动其他页面组件
- 不改动怪物显隐/阈值逻辑
