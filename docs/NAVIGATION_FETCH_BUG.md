# 搜索导航后页面不更新问题

## 现象

线上搜索后点击条目跳转，URL 已变（如 `/monsters/BabyTurtle/`），但页面内容未更新，仍显示前一个实体。

## 原因

**`web/src/pages/DetailPage.tsx`** 使用 `fetchedRef`（`useRef(false)`）控制只 fetch 一次。当从条目 A 导航到条目 B 时，组件实例复用，`fetchedRef.current` 仍为 `true`，导致 `useEffect` 中 `if (fetchedRef.current) return;` 跳过 fetch。

```tsx
const fetchedRef = useRef(false);

useEffect(() => {
  if (!page || !name) return;
  if (ssrData?.entity?.coords) { setEntity(ssrData.entity); return; }
  if (fetchedRef.current) return;  // ← 导航后永远为 true，跳过 fetch
  fetchedRef.current = true;
  fetch(...).then(setEntity)
    .catch(console.error);
}, [page, name, ssrData, dataVersion]);
```

## 修复

新增 `useEffect` 在 `page`/`name` 变化时重置 `fetchedRef`：

```tsx
// Reset fetch guard when navigating between entities
useEffect(() => {
  fetchedRef.current = false;
}, [page, name]);
```

## 参考

`LootdropDetailPage.tsx:200-203` 已有相同修复：

```tsx
// Reset fetch guard when name changes (e.g. navigation between lootdrops)
useEffect(() => {
  lootFetchedRef.current = false;
}, [name]);
```

## 涉及文件

- `web/src/pages/DetailPage.tsx` — 新增第 77-80 行
- `web/src/pages/LootdropDetailPage.tsx` — 已有修复（第 200-203 行）
