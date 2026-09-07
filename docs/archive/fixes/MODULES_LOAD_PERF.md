# 地图模块加载性能 & 详情页 JSON 依赖分析

## 问题描述（已修复）

详情页（/items/:name、/monsters/:name、/props/:name）需要加载多个 JSON 文件后才显示坐标地图。在慢服务器下延迟明显。用户报告在浏览器 Network 中未看到 `dungeon_modules.json` 的加载请求。

## 修复方案：内联模块数据

将模块旋转/偏移/尺寸信息直接嵌入实体 JSON 的 `_modules` 字段，详情页不再依赖 `dungeon_modules.json`。

### 后端改动

- `entity_export.py`：`export_items`、`export_monsters`、`export_props` 新增 `modules_map`、`map_to_module` 参数，为每个实体 JSON 注入 `_modules` 字段
- `lootdrop_builder.py`：`build_and_save_lootdrop_details` 新增同样参数，为每个掉落详情 JSON 注入 `_modules` 字段
- `collector.py`：将 `modules_map` 构建提前到实体导出之前

### 前端改动

- `types/data.ts`：新增 `InlineModuleData` 接口，实体类型新增 `_modules` 字段
- `DetailPage.tsx`：从 `entity._modules` 构建本地 modules Map，移除 `modulesLoading` 阻塞守卫
- `LootdropDetailPage.tsx`：同样处理，优先使用 `_modules` 数据

### 数据流变化

```
旧流程：meta.json → dungeon_modules.json → entity.json（三文件串行依赖）
新流程：meta.json → entity.json（含 _modules，二文件串行依赖）
```

## 详情页加载的 JSON 列表

| 文件 | 大小 | 加载来源 | 用途 |
|------|------|----------|------|
| `meta.json` | 25B | `useDataVersion()` | 获取数据版本号，用于缓存 bust |
| `items/Shackles.json` | ~6K+ | `DetailPage` useEffect | 实体的坐标、爆率、模块旋转等完整数据 |

**二文件串行依赖：** `meta.json` → `entity.json`（通过 `dataVersion` 实现缓存 bust）

## useDungeonModules 加载流程（保留，但详情页不再依赖）

```tsx
// useDungeonModules.ts — 仍被 dungeon_modules 列表页/详情页使用
const dataVersion = useDataVersion();
useEffect(() => { /* 空 deps []，只运行一次 */ }, []);
```

## DetailPage 新流程

```tsx
// 优先使用内联 _modules 数据
const modules = useMemo(() => {
  if (entity?._modules) {
    // 从 _modules 构建本地 Map
    return localMap;
  }
  return globalModules; // 降级到 useDungeonModules()
}, [entity?._modules, globalModules]);

useEffect(() => {
  // 不再等待 modulesLoading，直接 fetch 实体数据
  fetch(`/data/json/${page}/${name}.json`);
}, [page, name, ssrData, dataVersion]);
```

## _modules 字段结构

```json
{
  "_modules": {
    "Catacomb": {
      "rotate": 270,
      "offset_x": 0,
      "offset_y": 0,
      "size_x": 1,
      "size_y": 1,
      "range": 0,
      "group": "Crypt",
      "translation": "地下墓穴",
      "img_name": "Catacomb",
      "sl_base_name": "Catacomb"
    }
  }
}
```
