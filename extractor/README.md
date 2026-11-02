# 游戏资源 JSON 导出

独立的 C# / CUE4Parse 命令行模块，直接读取游戏 Paks 目录中的 `.pak` 和 `.utoc/.ucas`，导出原始资源 JSON。当前支持 `.locres` 本地化资源；后续可在此模块扩展 UObject 导出。

## 环境

- WSL Ubuntu，Linux .NET SDK 10；不调用 Windows 程序。
- CUE4Parse 固定为 NuGet `1.2.2.202611`，依赖由 `packages.lock.json` 锁定。
- 完整的游戏 Paks 目录，包括配套 `.ucas`、分卷、`global` 和补丁容器。

若尚未安装 .NET，可使用官方安装脚本安装到用户目录：

```bash
curl -fsSL https://dot.net/v1/dotnet-install.sh -o /tmp/dotnet-install.sh
nohup bash /tmp/dotnet-install.sh --channel 10.0 --install-dir "$HOME/.dotnet" > /tmp/dotnet-install.log 2>&1 < /dev/null &
```

查看安装日志确认成功，然后在使用工具的终端配置：

```bash
export PATH="$HOME/.dotnet:$PATH"
```

## 构建和运行

以下命令均在项目根目录下的 `extractor/` 中执行。长流程后台运行，读取日志确认完成后再执行下一步。

```bash
cd extractor
nohup dotnet restore --locked-mode > restore.log 2>&1 < /dev/null &
# restore.log 成功后：
nohup dotnet build -c Release --no-restore > build.log 2>&1 < /dev/null &
# build.log 显示构建成功后：
nohup dotnet bin/Release/net10.0/Extractor.dll > export.log 2>&1 < /dev/null &
```

用 `tail -n 30 restore.log`、`tail -n 30 build.log`、`tail -n 30 export.log` 查看结果；导出成功会打印来源容器、命名空间数量、翻译条目数及绝对输出路径。

默认输入与输出：

| 参数 | 默认值 |
| --- | --- |
| `--paks` | `/mnt/e/soft/Steam/steamapps/common/Dark and Darker/DungeonCrawler/Content/Paks` |
| `--asset` | `DungeonCrawler/Content/Localization/Game/zh-Hans/Game.locres` |
| `--output` | `output/DungeonCrawler/Content/Localization/Game/zh-Hans/Game.json` |
| `--aes-file` | `/mnt/e/Game/fmod/aes.txt`，存在时自动读取 |
| `--usmap` | 不加载；可显式指定映射文件 |
| `--game` | `GAME_UE5_6`，可指定 CUE4Parse 的其他 `EGame` 名称 |

`--game` 是当前容器读取的默认配置，不表示工具自动检测出了游戏引擎版本。相对输出路径以运行目录为基准；`--output` 接收完整的目标文件路径。

自定义参数示例：

```bash
nohup dotnet bin/Release/net10.0/Extractor.dll \
  --paks '/mnt/e/soft/Steam/steamapps/common/Dark and Darker/DungeonCrawler/Content/Paks' \
  --asset 'DungeonCrawler/Content/Localization/Game/zh-Hans/Game.locres' \
  --aes-file '/mnt/e/Game/fmod/aes.txt' \
  --output 'output/DungeonCrawler/Content/Localization/Game/zh-Hans/Game.json' \
  > export.log 2>&1 < /dev/null &
```

AES 文件仅包含一条 64 位十六进制密钥，可带 `0x` 前缀。工具读取本地文件，不打印密钥；不要把密钥放进源码或提交到仓库。指定的 AES 文件不存在或格式不正确时返回失败。

`.locres` 自身包含本地化索引和文本，解析不依赖 usmap。如需显式加载映射，可添加 `--usmap '/mnt/e/Game/fmod/usmap/season11hotfix130.usmap'`；该文件用于属性映射，不用于解密容器。

## 输出约定

```json
{
  "DC": {
    "ExampleKey": "示例文本"
  }
}
```

保留全部命名空间、翻译键与原始文本，使用 UTF-8 无 BOM，按命名空间和键排序，保留中文及文本中的换行。此结构与 `api/` 当前读取 `Game.json` 的方式兼容；导出阶段不移除文本后缀或执行 Python 清洗。

使用 CUE4Parse 的容器读取优先级选择补丁资源。仅扫描 Paks 根目录，避免读取子目录中的备份和模组。存在未能挂载的带目录索引容器时停止，防止静默导出旧版本；无目录索引的 `global` 容器不因此判为失败。

Oodle 优先使用依赖内置的解压实现；若所选资源解压失败，尝试通过 CUE4Parse 初始化本机平台的 Oodle 库。该步骤可能联网下载 Linux 库，失败信息写入导出日志。

完整解析和序列化成功后才原子替换输出；失败返回非零退出码。`output/`、`bin/`、`obj/`、日志和本地解压库不提交。此模块独立运行，后续再接入 `api/` 的导入流程。
