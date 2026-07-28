# 地图模块参考

本文集中说明 DungeonModule、Layout、旋转和无资产模块。Spawner 坐标解析规则见 [`REFERENCE_DATA_PIPELINE.md`](REFERENCE_DATA_PIPELINE.md)；完整历史表格见 [`REFERENCE_ARCHIVE.md`](REFERENCE_ARCHIVE.md) 的地图模块章节。

## 模块数据来源

`DCDungeonModuleDataAsset` 位于游戏导出目录的 DungeonModule 数据目录，关键字段为：

- `ModuleType`：区域分组。
- `Name.Key` / `Name.LocalizedString`：翻译键和显示名。
- `SubLevelAssetA`：逻辑层，含实体 Spawner。
- `SubLevelAssetD` / `SubLevelAssetD_HR`：普通/豪客地图布局。
- `SubLevelAssetS`：音频层。
- `MapImage`：地图预览图。

Layout 文件通过 `LevelStreamingAlwaysLoaded.WorldAsset` 引用子模块，并携带 `LevelTransform.Translation` 和四元数 `Rotation`。

## 图片匹配

图片优先级为 `SubLevelAsset(sl_base) -> module name -> MapImage`。`RareModule_1x1` 和 `UnderConstruction_1x1` 是占位图，不能作为最终匹配结果。`module_builder.py:_resolve_img()` 应区分：

- `found`：找到匹配图片。
- `not_found`：有 Art 目录但没有匹配，继续按模块名尝试。
- `no_art`：没有 Art 目录，回退到 sl_base 名称。

## 旋转值

ShipGraveyard 从 Layout 四元数计算：

```text
yaw_rad = 2 * atan2(Z, W)
yaw_deg = degrees(yaw_rad)
js_rotate = (yaw_deg - 90) % 360
```

其他地图组通常使用 DB `dungeon_modules.rotation`，默认值为 270。优先级是模块名精确匹配、sl_base 匹配、270 默认值。

前端链路为：

```text
dungeon_modules.rotation
  -> build_modules_map().rotate
  -> dungeon_modules.json
  -> useDungeonModules()
  -> getAdj()/applyTransform()
```

## extra_rows

没有 DungeonModule JSON、但在地图目录中出现的模块由 `ModulesImporter._build_path_group_map()` 发现，并通过 `extra_rows` 插入。此类记录默认 `size_x=1`、`size_y=1`、空 `sl_base_name`、空 `map_image_name`、旋转 270。

`MODULE_DISPLAY_OVERRIDE` 只在生成 `dungeon_modules.json` 时修正已知模块的展示尺寸；不要把展示覆写误当成 DB 原始资产数据。ShipGraveyard 的特殊偏移使用 `MODULE_OFFSET_MAP`，其中人工偏移是坐标换算后的前端值，不一定等于 Layout 原始 Translation。

## 地图模块 V2

Layout 文件命名一般为 `{区域}_{尺寸}_{序号}_{版本}_{后缀}.json`。子模块层级含义：`_A` 逻辑、`_D` 装饰、`_S` 音频、`_HR_D` 豪客版装饰。采集输出为 `data/json/dungeon_modules_v2.json`，主要用于保留资产层级、尺寸、布局引用和图片来源。

`ModuleType` 为空时先通过 `SubLevelAsset` 的 sl_base 反查已知分组，再使用模块名前缀推断。通用未使用模块应在导入清理阶段移除，不能为了填分组而虚构地图数据。
