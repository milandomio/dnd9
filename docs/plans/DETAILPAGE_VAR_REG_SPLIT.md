# DetailPage 固定点/变体点分离显示方案

## 问题

`/monsters/Mummy/` 的 EightToOne_01 模块显示 `(12点选2)`，但实际应为 `(4点)(8点选2)`：
- 4 个固定坐标（无 `group_parent`）
- 8 个变体坐标（`BP_GameSpawnerGroup_C_1`，`variant_count=2`）

## 根因

`DetailPage.tsx` 将所有坐标合并计算 `posCount`，未分离固定点和变体点。

## 改动

**文件**：`web/src/pages/DetailPage.tsx`

**第 758-948 行** — variant 显示 IIFE 内部：

### 1. 坐标分离（替代原 `forcedVc` / `posCount`）

- `varCoords = mapCoords.filter(c => c.group_parent)` — 有 group_parent 的变体坐标
- `regCoords = mapCoords.filter(c => !c.group_parent)` — 无 group_parent 的固定坐标
- `regPosCount = new Set(regCoords.map(c => \`${c.x},${c.y},${c.z}\`)).size`
- `varPosCount = new Set(varCoords.map(c => \`${c.x},${c.y},${c.z}\`)).size`
- `hasVariant = varCoords.length > 0`

### 2. 标签渲染（替代原 names / no-names 返回）

- 有 varCoords + variant_names：`(regPosCount点)(varPosCount点选{vc.variant_count})`
- 有 varCoords + 无 names：`(regPosCount点)(varPosCount点)`
- 无 varCoords：`(posCount点)`（原逻辑，仅 regCoords）

## 关键约束

- `mapCoords` 是 GDI 分组后的坐标子集，分离逻辑对其一一适用
- `adjRate` 公式不变，仍用 `forceVc` 的 `variant_count` 和 `groupCount`
- 不涉及数据层改动
