# SSR 字段完整性验证问题

## 问题现象

Quick 模式 SSG 构建下，DetailPage 详情页（items/monsters/props）在 SSR 渲染时，地图模块显示异常（旋转/偏移数据错误）。用户手动点击范围放大缩小后，页面才正常显示。

## 根因

Quick 模式 SSG 构建时，SSR 只注入 `{ name, translation }` 最小字段集（见 `ssg.mjs:201`）。但 `DetailPage.tsx` 第 46 行使用：

```tsx
const [entity, setEntity] = useState<Entity | null>(ssrData?.entity || null);
```

不完整对象 `{ name, translation }` 是 truthy，组件将其当作完整实体数据渲染。此时：
- `entity._modules` 为 `undefined` → `modules` 是空 Map
- `entity.coords` 为 `undefined` → 坐标数组为空
- MapPanel 接收到的 `mod` 全是 `undefined`，所有模块属性用默认值（占位图 RareModule_1x1、旋转 0、范围默认值等）

客户端 fetch 完成后返回完整数据 → 正确渲染。用户手动交互恰好触发了重渲染，所以看起来手动调整后"好了"。

## 修复方法

在 `web/src/pages/DetailPage.tsx:46-48` 验证 SSR 数据的字段完整性：

```tsx
const [entity, setEntity] = useState<Entity | null>(
    ssrData?.entity?._modules ? ssrData.entity : null
);
```

验证 `_modules` 存在才使用 SSR 数据，否则设为 `null`，让组件显示"数据加载中..."等待 fetch 完成。

## 参考

- `LootdropDetailPage.tsx:110-117` 已有相同的验证模式（`ssrData?.item?.monsters`）
- `CLAUDE.md` "React Hydration 规则"第 3 条：Quick 模式下 SSR 数据不完整，必须验证必要字段
- `ssg.mjs:201` Quick 模式注入的 SSR 数据格式