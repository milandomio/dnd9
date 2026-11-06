# 游戏资源 JSON 导出

独立的 .NET 10 / CUE4Parse 命令行模块，直接读取 `.pak` 和 `.utoc/.ucas`，无需先用 repak、retoc 或 FModel 解包。可复制整个 `extractor/` 单独使用，不依赖 `api/`、`web/` 或 MCP 服务。

本项目的部署流程中，仅维护者更新游戏补丁数据时调用本模块。普通用户拉取仓库后通过随仓库 DB 进行本地部署，无需配置本模块；`deploy.sh`、API 入口和 Web 构建均不会自动调用解包。

支持容器索引扫描、单文件 JSON 导出、递归目录更新。`.locres` 输出命名空间字典，`.uasset` / `.umap` 输出 FModel 兼容的对象数组。当前尚未实现纹理转 PNG。

## 首次配置

运行环境为 Linux .NET SDK 10，已在 WSL Ubuntu 验证。完整保留 Paks 根目录中的 `.pak`、`.utoc`、配套 `.ucas`、分卷、global 和补丁容器。

```text
extractor/
├── config.json                 # 通用默认配置
├── config.local.json.example   # 本机配置示例
├── config.local.json           # 本机游戏路径，忽略提交
├── update-scope.json           # 本项目固定的 14 个递归目录
├── keys/
│   ├── aes.txt                 # 当前 AES，忽略提交
│   └── <游戏版本>.usmap        # 当前属性映射，忽略提交
└── output/                     # 导出、报告和备份，忽略提交
```

在模块目录中复制示例，将 `paksDirectory` 改成自己的游戏 Paks 路径：

```bash
cd extractor
cp config.local.json.example config.local.json
```

Windows 的 `E:\soft\Steam\steamapps\common\Dark and Darker\DungeonCrawler\Content\Paks`，在 WSL 中填写 `/mnt/e/soft/Steam/steamapps/common/Dark and Darker/DungeonCrawler/Content/Paks`。

将 AES 放到 `keys/aes.txt`，将匹配当前游戏版本的 usmap 放到 `keys/`。AES 文件是一条 64 位十六进制密钥，可带 `0x` 前缀。真实密钥、映射和本机配置均忽略 Git 提交；其他使用者自行提供。

配置优先级：命令行 > `config.local.json` > `config.json`。配置中的相对路径以配置文件所在目录为基准；命令行中的相对路径以工作目录为基准。`--config FILE` 选择另一份配置，并加载其同目录的 `config.local.json`。

| 配置字段 | 用途 |
| --- | --- |
| `paksDirectory` | 默认留空，需配置或传入 `--paks` |
| `aesFile` | 默认 `keys/aes.txt` |
| `usmapDirectory` | 默认 `keys`，UObject / 批量导出按修改时间选取最新 `.usmap` |
| `game` | Unreal 读取配置，可用 `--game` 覆盖，不是自动检测结果 |

日志记录采用的映射文件及 AES 文件路径，不打印密钥。需要固定版本时使用 `--usmap keys/文件名.usmap`。单独解析 `.locres` 或扫描索引无需 usmap，加密容器仍需 AES。

当前 Dark and Darker 配置为 `GAME_UE5_8`，与本机成功读取资源的 FModel 配置一致，并非自动检测引擎版本。`GAME_UE5_6` 能读取部分数据资产，但在本次全量导出中导致 1089 个 Blueprint / 地图资源失败；更换游戏或升级后需要核对 `game` 和 usmap。

## 安装和构建

若尚未安装 SDK：

```bash
curl -fsSL https://dot.net/v1/dotnet-install.sh -o /tmp/dotnet-install.sh
nohup setsid bash /tmp/dotnet-install.sh --channel 10.0 --install-dir "$HOME/.dotnet" > /tmp/dotnet-install.log 2>&1 < /dev/null &
```

日志确认安装成功后配置终端：

```bash
export PATH="$HOME/.dotnet:$PATH"
```

以下命令均在 `extractor/` 中执行。CUE4Parse 精确固定为 NuGet `1.2.2.202611`，依赖由 `packages.lock.json` 锁定。

```bash
nohup setsid dotnet restore --locked-mode > restore.log 2>&1 < /dev/null &
# restore.log 显示成功后：
nohup setsid dotnet build -c Release --no-restore > build.log 2>&1 < /dev/null &
```

`build.log` 显示 `Build succeeded`、0 Error(s) 后再运行导出。使用 `tail -n 30 <日志文件>` 查看进度，`dotnet bin/Release/net10.0/Extractor.dll --help` 查看参数。

## 单文件导出

默认导出简体中文 `Game.locres`：

```bash
nohup setsid dotnet bin/Release/net10.0/Extractor.dll > export.log 2>&1 < /dev/null &
```

输出为 `output/DungeonCrawler/Content/Localization/Game/zh-Hans/Game.json`。使用 UTF-8 无 BOM，保留全部命名空间、键、中文和换行。`DC` 字典兼容现有 Python 导入器。

导出单个物品：

```bash
nohup setsid dotnet bin/Release/net10.0/Extractor.dll \
  --asset 'DungeonCrawler/Content/DungeonCrawler/Data/Generated/V2/Item/Item/Id_Item_AdventurerBoots_1001.uasset' \
  --output output/item-probe.json > item-probe.log 2>&1 < /dev/null &
```

UObject 使用 CUE4Parse 原生 JSON 转换器，保留 `Type`、`Name`、`Properties`、对象路径与引用，属性内的本地化文本使用英文。整个包完成解析且没有记录解析错误后才写入输出，失败返回非零退出码。

## 递归目录更新及清理

[`update-scope.json`](update-scope.json) 保存固定 14 个目录；`folders` 相对于 `DungeonCrawler/Content/`，包含全部子目录及新增资源。`root` 相对于配置文件，是默认目标位置，`--apply-to` 可覆盖目标。

只导出到暂存区检查：

```bash
nohup setsid dotnet bin/Release/net10.0/Extractor.dll \
  --manifest update-scope.json \
  --output-root output/update/Content \
  --report output/update/update-report.json > update.log 2>&1 < /dev/null &
```

更新本项目解包源时增加：

```bash
nohup setsid dotnet bin/Release/net10.0/Extractor.dll \
  --manifest update-scope.json \
  --output-root output/update/Content \
  --apply-to /home/mio/fmod/Output/Exports/DungeonCrawler/Content \
  --report output/update/update-report.json > update.log 2>&1 < /dev/null &
```

独立使用时修改 `--apply-to` 为自己的 Content 目录，省略该参数仅暂存。补丁更新采用「当前项目资源 + 上一轮旧资源 + 持久差异文档」循环：

1. 校验本轮资源范围后，先删除上一轮已经完成对比的旧资源快照；只有快照带有 `comparison-complete` 标记且对应的差异 Markdown 仍存在时才会清理。未完成对比的备份不会删除。
2. 挂载容器并按补丁优先级导出新资源到暂存区，校验 JSON 与 SHA-256。
3. 所有资源成功后，将项目 Content 目录整体移入 `BackupRoot`，再用新资源目录替换项目 Content。应用失败会回滚，旧项目资源保留。
4. 对比旧项目资源和新项目资源，生成 `update-diff-<批次>.md`，列出更新、新增、删除文件及未变数量。差异文档保留在暂存目录旁；报告 JSON 同时记录 `Removed` 与 `DiffDocument`。
5. 差异文档写入成功后才给旧快照写入完成标记。下次批次开始时才清理这份已对比旧资源，因此每轮保留项目当前资源和上一轮旧资源用于比较。

任一解析失败时跳过目录替换；替换失败时尝试反向回滚，异常记录在 `ApplyError`。差异文档写入失败时不标记旧备份，保留旧资源并报告错误。备份与原目录需位于支持目录重命名的同一文件系统。

正式更新成功判据：进程结束、日志出现 `Batch complete`，报告为 `Completed=true`、`Applied=true`、`Failed=0`、`ApplyError=null` 且存在 `DiffDocument`。仅暂存时应为 `Applied=false`。进度行或进程启动不代表成功。

报告包含所有文件的 `Asset`、`Source`、`Sha256`、`Status`、`Removed` 和差异文档路径。传入带 `files` 的 fmodel-query 清单时额外记录 `UnmatchedExisting`。复用暂存目录时仅应用本次报告列出的文件，旧暂存产物不会混入新项目资源。

运行备份轮换回归测试：`dotnet run --project tests/BackupRetention.Tests.csproj`（在 `extractor/` 目录执行）。

### 本体与补丁如何合并

CUE4Parse 同时挂载所有容器，按 `ReadOrder` 降序查找同一个虚拟路径。本次安装的本体容器为 `3`，`_0_P` 补丁容器为 `103`，因此补丁中的同路径资源优先；补丁未包含的资源继续从本体读取。导出器对路径去重，再通过 `provider[path]` 取得最终资源，不依赖容器枚举顺序或文件修改时间，也不会逐包解压后相互覆盖。

例如简体中文 `DungeonCrawler/Content/Localization/Game/zh-Hans/Game.locres` 的 `Source` 为 `pakchunk0-Windows_0_P.pak`，复杂地图 `Cave_BaseCamp_A.umap` 来自 `pakchunk2002-Windows_0_P.utoc`。可用报告中的逐文件 `Source` 和挂载日志中的 `order` 复核。若有带目录索引的容器挂载失败，导出器直接停止，避免退回旧本体资源。需保留 Steam 当前安装的完整容器集合；此规则不能弥补缺失的补丁文件。

## 扫描其他目录

`--scan KEYWORD_OR_PATH` 显示真实虚拟路径、目录、资源扩展名和来源容器。具体操作及模块地图图片示例见 [`docs/FOLDER_DISCOVERY.md`](docs/FOLDER_DISCOVERY.md)。新试验使用独立范围配置，固定 14 个目录保持在 `update-scope.json` 中维护。

## 本项目补丁流程

提供最新 usmap → 更新 `keys/` → 从游戏容器更新并清理 14 个目录 → 重建 DB、运行 API 清洗 → Web 构建 → preview HTTP 200 及适用测试 → 记录并本地提交。解包步骤替代 `~/sync_fmod.sh`，推送仍需用户明确要求。站点步骤见主仓库 [`docs/BUILD_AND_DEPLOY.md`](../docs/BUILD_AND_DEPLOY.md) 的「更新部署」。

常见失败包括 AES、usmap 或引擎配置不匹配，配套容器缺失，资源类型不支持。先检查第一个具体错误，保留旧源及备份，修正后再运行。Oodle 优先使用内置实现，必要时尝试通过 CUE4Parse 下载并初始化当前平台的本机库。
