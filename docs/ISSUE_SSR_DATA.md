# SSG Quick 模式下 LootdropDetailPage 渲染错误

## 症状

访问 `/lootdrops/CeremonialStaff/` 时报 React error #310:
"Objects are not valid as a React child"

F5 刷新可正常显示，客户端导航时崩溃。

## 根因

SSG quick 模式下，`ssg.mjs` 只为 lootdrop 详情页注入最小 SSR 数据：

```js
ssrDataMap[`lootdrops/${name}`] = { item: { name: e.name, translation: e.translation } };
```

缺少 `monsters`、`group_drop_info` 等完整字段。

`LootdropDetailPage.tsx` 的 `useState` 初始化：

```tsx
const [data, setData] = useState<LootdropItem | null>(ssrData?.item || null);
```

`ssrData.item` 是 `{ name, translation }`，不是完整的 `LootdropItem`。`data` 是 truthy 对象，通过了 `if (!data)` 检查，但缺少 `monsters`、`group_drop_info` 等字段。后续渲染路径中访问这些字段时，某些分支返回了非 React 元素（对象/undefined），触发 #310 错误。

## 修复方案

在 `useState` 初始化或 `useEffect` 中，判断 SSR 数据是否完整（是否包含 `monsters` 字段）。如果不完整，应将 `data` 设为 `null`，走 fetch 流程获取完整数据后再渲染。

相关文件：`web/src/pages/LootdropDetailPage.tsx`
