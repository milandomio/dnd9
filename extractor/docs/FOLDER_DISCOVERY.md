# 扫描定位其他目录

先按 [`README.md`](../README.md) 配置并构建。以下命令均在独立 `extractor/` 根目录运行。

## 扫描索引

```bash
nohup setsid dotnet bin/Release/net10.0/Extractor.dll \
  --scan DungeonModuleMapImage \
  --output output/map-image-inventory.json > scan-map-images.log 2>&1 < /dev/null &
```

扫描无需预先解包，也无需 usmap；加密索引仍需 AES。日志显示匹配数量、目录及前 50 个文件，JSON 清单包含完整 `Folders`、`Files`、扩展名和来源容器。无匹配时返回失败。

本次定位到 `DungeonCrawler/Content/DungeonCrawler/Data/Art/DungeonModuleMapImage` 及其子目录，共 226 个资源、9 个目录。数量随补丁变化，以实时扫描为准。注意该位置是 `Data/Art`，不是 `Data/Generated/V2/Art`。

没有结果时缩短为 `ModuleMap`、`MapImage`、`DungeonModule` 或 `Data/Art` 逐级定位，再用完整路径缩小范围。同名资源使用容器优先级选取当前版本。

## 区分路径

| 类型 | 示例 |
| --- | --- |
| 容器虚拟路径，供 `--asset` 使用 | `DungeonCrawler/Content/DungeonCrawler/Data/Art/DungeonModuleMapImage/Crypt/CorridorofDarkPriests.uasset` |
| 范围配置的相对目录 | `DungeonCrawler/Data/Art/DungeonModuleMapImage` |
| 本地文件系统路径 | `/home/mio/fmod/Output/Exports/DungeonCrawler/Content/DungeonCrawler/Data/Art/DungeonModuleMapImage/...` |

WSL UNC 路径是本地访问入口，不能作为资源虚拟路径。单文件输入保留 `.uasset` / `.umap` 后缀，输出改为 `.json`。

## 单文件试导出

从当前扫描结果中选取存在的文件：

```bash
nohup setsid dotnet bin/Release/net10.0/Extractor.dll \
  --asset 'DungeonCrawler/Content/DungeonCrawler/Data/Art/DungeonModuleMapImage/Crypt/CorridorofDarkPriests.uasset' \
  --output output/module-map-image-probe.json > module-map-image-probe.log 2>&1 < /dev/null &
```

检查 `Type`、`Name` 及需要的字段是否符合用途。纹理通常为 `Texture2D`，JSON 描述纹理资源；当前工具尚未提供 Texture2D → PNG 解码，因此不能用该 JSON 替换地图图片源。

上述 `CorridorofDarkPriests.uasset` 已用当前映射和 `GAME_UE5_8` 成功导出 JSON；其他目录仍需逐个确认资源类型与解析结果。

## 建立独立批量配置

在模块根目录新建 `map-image-scope.json`：

```json
{
  "root": "output/map-images/Content",
  "folders": ["DungeonCrawler/Data/Art/DungeonModuleMapImage"]
}
```

`folders` 相对 `DungeonCrawler/Content/`，包含所有子目录；`root` 相对范围文件。固定 14 个目录继续由 `update-scope.json` 维护。

```bash
nohup setsid dotnet bin/Release/net10.0/Extractor.dll \
  --manifest map-image-scope.json \
  --output-root output/map-images-staging/Content \
  --report output/map-images-staging/report.json > map-images.log 2>&1 < /dev/null &
```

`Completed=true`、`Failed=0` 表示暂存完成。核对数量、资源类型、字段及用途后，再决定是否对选定的 Content 根目录使用 `--apply-to`。

## 更新及恢复

`--apply-to` 在全部资源解析成功后，备份并整体替换配置目录，清理旧文件；目录内的手工文件也会进入备份。试验输出使用独立目录，避免混入需要保留的手工产物。

解析失败时原目录保持原状。替换失败时工具尝试回滚，报告记录 `ApplyError`。手动恢复时先停止后续导入、另存当前对应目录，再按 `BackupRoot` 和 `Folders` 将备份目录移回原位置；保留范围外目录。未成功导出的暂存结果不能作为新数据源。
