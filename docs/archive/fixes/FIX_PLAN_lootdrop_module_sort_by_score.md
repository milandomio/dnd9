# 修复记录：Lootdrop 详情页地图模块按综合爆率排序

## 修改清单

本文件记录了 `LootdropDetailPage.tsx` 的一批关联修改。

### 1. 模块排序改为按综合爆率总分

组件：`LootdropDetailPage.tsx`

**组内排序**：模块总分降序 → `dots.length` 降序 → `size_y → size_x`

**分组间排序**：该组总模块总分降序 → 总 `dots.length` 降序 → `groupOrder`

总分公式：

```
模块总分 = Σ ( spawn_rate × 豪客赛率 × effectiveCount )
          对模块上每个可见的怪物类型求和
```

数据来源：`data.group_drop_info[groupName]` → 按 `translation` 匹配怪物 → `spawn_rate` × `drop_rates.豪客赛`

### 2. 变体坐标计分修正

新增 `effectiveCount(dots)` 函数，逐点计算有效坐标数：

- 普通点 → +1
- 有名变体点（`variant_names` 存在，如 `狮头宝箱、中宝箱2种选1`）→ `+1/variant_count`
- 无名变体点（`variant_count > 1` 但无名，如 `4点选1`）→ `+1`

之前错误地使用 `dots.find` 找到第一个变体点后，对所有点统一处理，导致混合普通+变体点时严重低估有效数。

### 3. 变体/普通点显示分离

模块卡片底部怪物摘要中的点数显示，原来混在一起只显示一种标签。现在分离显示：

- 普通点 → `(N点)`
- 有名变体点 → `(names N种选<count>)`（`<count>` 是该类型变体点数量，不再硬编码为 `1`）
- 无名变体点 → `(N点选1)`

### 4. hidden/toggle key 改为 translation

**根因**：同一个实体名（如 `OrnateChestMedium`）在 lootdrop 中可能出现多次（不同翻译后缀如 `(特殊)`、`(随机)`），`hidden` Set 以 `m.name` 为键导致分类按钮联动显隐。

**修复**：将组件内所有 `hidden`/`toggle`/`grouping` 的 key 从 `m.name` 改为 `m.translation`（翻译名在条目间唯一）。涉及：

- `defaultHidden` 初始隐藏阈值判断
- `mapGroups` 构建循环的显隐过滤
- `hiddenRows` 的 rowKey
- 分类按钮（含全显/全隐）
- 模块卡片底部怪物标签分组 key
- `group_drop_info` 参考爆率过滤
- 调试表格的显隐判断/toggle

### 5. 综合爆率显示

- 默认可见（非调试模式）
- 显示在模块卡片底部怪物摘要下方
- 格式：`parseFloat((sc / 100).toFixed(4))`，去除多余尾随零
- 示例：`综合爆率 0.03%`、`综合爆率 33.25%`

## 不涉及的修改

- 不改动数据管道 / 后端
- 不改动 SSG 脚本
- 不改动其他页面组件
- 不改动怪物显隐/阈值逻辑
