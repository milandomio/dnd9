# 变体标签修复方案

## 问题

`(N点选M组)` 格式误导。当多个 GameSpawnerGroup 共存于同一模块且产生同一种实体时，"选M组" 暗示只生成 M 个物品，实际上每个位置独立产出 1 个。

## 修复目标

| 条件 | 旧格式 | 新格式 | 示例 |
|------|--------|--------|------|
| 无 `variant_names`（cnt=1，同实体） | `(N点选M组)` | `(N点)` | `(16点)` |
| 有 `variant_names`（cnt>1，混合实体） | `(名称N种选M)` | `(N点选{variant_count})` | `(8点选2)` |

## 改动文件

### 1. `web/src/pages/LootdropDetailPage.tsx`

- names case（~1532 行）：`(${localeNames}${vc}种选${groupCount})` → `(${totalVarPos}点选${varDots[0].variant_count})`
- no-names case（~1540 行）：`(${totalVarPos}点选${groupCount})` → `(${totalVarPos}点)`

### 2. `web/src/pages/DetailPage.tsx`

- names case（~929 行）：`({localeNames}{vc}种选{groupCount} · {posCount}点选{groupCount})` → `({posCount}点选{vc.variant_count})`
- no-names case（~943 行）：`({posCount}点选{groupCount})` → `({posCount}点)`

## 验证

- `npx prettier --check`
- `npx tsc --noEmit`
- 人工查看 GiantBatEar 页面确认 ForsakenCloister 显示 `(16点)` 而非 `(16点选2组)`
