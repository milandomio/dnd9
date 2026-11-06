using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using CUE4Parse.FileProvider;
using CUE4Parse.UE4.VirtualFileSystem;

internal static class BatchExport
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNameCaseInsensitive = true,
        WriteIndented = true,
    };

    public static async Task<int> RunAsync(DefaultFileProvider provider, Dictionary<string, string> options)
    {
        var manifestPath = Path.GetFullPath(options["--manifest"]);
        var inventory = JsonSerializer.Deserialize<Inventory>(await File.ReadAllTextAsync(manifestPath), JsonOptions)
            ?? throw new InvalidDataException("Empty update manifest.");
        if (string.IsNullOrWhiteSpace(inventory.Root) || inventory.Folders is not { Length: > 0 })
            throw new InvalidDataException("The manifest must specify root and nonempty folders.");
        var originalRoot = Path.GetFullPath(inventory.Root, Path.GetDirectoryName(manifestPath)!);
        var folders = inventory.Folders.Select(NormalizeRelative).Distinct(StringComparer.OrdinalIgnoreCase).ToArray();
        if (folders.Any(folder => folders.Any(other => folder != other && folder.StartsWith(other + "/", StringComparison.OrdinalIgnoreCase))))
            throw new InvalidDataException("Manifest folders must not overlap.");
        var outputRoot = Path.GetFullPath(options.GetValueOrDefault("--output-root", "output/update/Content"));
        var reportPath = Path.GetFullPath(options.GetValueOrDefault("--report", Path.Combine(Path.GetDirectoryName(outputRoot)!, "update-report.json")));
        var applyRoot = options.TryGetValue("--apply-to", out var applyTo) ? Path.GetFullPath(applyTo) : null;
        if (applyRoot is not null)
            originalRoot = applyRoot;
        if (outputRoot == originalRoot || outputRoot.StartsWith(originalRoot + Path.DirectorySeparatorChar, StringComparison.Ordinal))
            throw new ArgumentException("Stage exports outside the original Content directory.");
        var backupCollectionRoot = Path.GetDirectoryName(outputRoot)!;
        var updateId = DateTime.UtcNow.ToString("yyyyMMddTHHmmss") + "-" + Guid.NewGuid().ToString("N")[..8];
        var backupRunDirectory = applyRoot is null ? null : Path.Combine(backupCollectionRoot, "backup-" + updateId);
        var backupRoot = backupRunDirectory is null ? null : Path.Combine(backupRunDirectory, "Content");
        var diffDocumentPath = applyRoot is null ? null : Path.Combine(backupCollectionRoot, "update-diff-" + updateId + ".md");

        const string prefix = "DungeonCrawler/Content/";
        var jobs = provider.Files.Keys.Distinct(StringComparer.OrdinalIgnoreCase)
            .Where(path => path.StartsWith(prefix, StringComparison.OrdinalIgnoreCase) && AssetExporter.Supports(path))
            .Select(path => new { Asset = path, Relative = path[prefix.Length..] })
            .Where(file => folders.Any(folder => file.Relative.StartsWith(folder + "/", StringComparison.OrdinalIgnoreCase)))
            .Select(file => new Job(file.Asset, Path.ChangeExtension(file.Relative, ".json").Replace('\\', '/')))
            .OrderBy(job => job.Relative, StringComparer.Ordinal).ToArray();
        if (jobs.Length == 0)
            throw new InvalidDataException("No resources match the update folders.");
        if (jobs.Select(job => job.Relative).Distinct(StringComparer.OrdinalIgnoreCase).Count() != jobs.Length)
            throw new InvalidDataException("Multiple resources would write the same JSON path.");
        if (folders.Any(folder => !jobs.Any(job => job.Relative.StartsWith(folder + "/", StringComparison.OrdinalIgnoreCase))))
            throw new InvalidDataException("Every configured folder must match resources before any folder can be replaced.");

        if (backupRoot is not null)
        {
            var removedBackups = BackupRetention.RemoveComparedBackups(backupCollectionRoot, applyRoot!, Console.WriteLine);
            if (removedBackups.Count > 0)
                Console.WriteLine($"Removed {removedBackups.Count} previously compared backup(s); their diff documents remain.");
        }

        var report = new UpdateReport(originalRoot, outputRoot, backupRoot, folders);
        var selected = jobs.Select(job => job.Relative).ToHashSet(StringComparer.OrdinalIgnoreCase);
        report.UnmatchedExisting = (inventory.Files ?? []).Where(path => !selected.Contains(path)).ToArray();
        Console.WriteLine($"Batch: {folders.Length} recursive folders, {jobs.Length} resources; staging: {outputRoot}");
        for (var index = 0; index < jobs.Length; index++)
        {
            var job = jobs[index];
            var file = provider[job.Asset];
            var result = new ExportResult(job.Relative, file.Path, (file as VfsEntry)?.Vfs.Path);
            report.Results.Add(result);
            try
            {
                var json = await AssetExporter.SerializeAsync(provider, file);
                result.Sha256 = Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(json))).ToLowerInvariant();
                await AssetExporter.WriteAtomicAsync(Path.Combine(outputRoot, job.Relative), json);
                result.Status = "exported";
            }
            catch (Exception error)
            {
                result.Status = "failed";
                result.Error = error.ToString();
                Console.Error.WriteLine($"FAILED {job.Relative}: {error.Message}");
            }
            if ((index + 1) % 100 == 0 || index + 1 == jobs.Length)
            {
                Console.WriteLine($"Progress: {index + 1}/{jobs.Length}; failed: {report.Failed}");
                await SaveReportAsync(reportPath, report);
            }
        }

        if (applyRoot is not null && report.Failed == 0)
        {
            try
            {
                await ApplyFoldersAsync(report, applyRoot, outputRoot, backupRoot!, folders);
                report.Applied = true;
            }
            catch (Exception error)
            {
                report.ApplyError = error.ToString();
                await SaveReportAsync(reportPath, report);
                throw;
            }
        }
        else if (applyRoot is not null)
            Console.Error.WriteLine("Apply skipped: some exports failed. Original folders have not been changed.");

        if (report.Applied && diffDocumentPath is not null)
        {
            try
            {
                await SaveDiffDocumentAsync(diffDocumentPath, report);
                report.DiffDocument = diffDocumentPath;
                if (backupRoot is not null && Directory.Exists(backupRoot))
                    await AssetExporter.WriteAtomicAsync(BackupRetention.CompletionMarkerPath(backupRoot), applyRoot + "\n");
            }
            catch (Exception error)
            {
                report.DiffError = error.ToString();
                await SaveReportAsync(reportPath, report);
                throw new IOException($"Resources were applied, but the difference document could not be completed. Backup retained at {backupRoot}.", error);
            }
        }

        report.Completed = true;
        await SaveReportAsync(reportPath, report);
        Console.WriteLine($"Batch complete: total={report.Results.Count}, failed={report.Failed}, "
            + $"updated={report.Results.Count(r => r.Status == "updated")}, added={report.Results.Count(r => r.Status == "added")}, "
            + $"removed={report.Removed.Length}, unchanged={report.Results.Count(r => r.Status == "unchanged")}");
        Console.WriteLine($"Report: {reportPath}");
        if (backupRoot is not null)
            Console.WriteLine($"Backup: {backupRoot}");
        if (diffDocumentPath is not null && report.Applied)
            Console.WriteLine($"Difference: {diffDocumentPath}");
        return report.Failed == 0 ? 0 : 1;
    }

    private static async Task ApplyFoldersAsync(UpdateReport report, string applyRoot, string outputRoot,
        string backupRoot, string[] folders)
    {
        var swaps = new List<FolderSwap>();
        var statuses = new Dictionary<ExportResult, string>();
        var oldFiles = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        var newFiles = report.Results.Select(result => result.Relative).ToHashSet(StringComparer.OrdinalIgnoreCase);
        try
        {
            // Prepare and verify every replacement before moving any original directory.
            foreach (var folder in folders)
            {
                var target = Path.Combine(applyRoot, folder);
                if (Directory.Exists(target))
                {
                    foreach (var file in Directory.EnumerateFiles(target, "*", SearchOption.AllDirectories))
                    {
                        var relative = Path.GetRelativePath(applyRoot, file).Replace('\\', '/');
                        oldFiles.Add(relative);
                    }
                }
                var temporary = target + ".extractor-" + Guid.NewGuid().ToString("N");
                var swap = new FolderSwap(target, temporary, Path.Combine(backupRoot, folder));
                swaps.Add(swap);
                Directory.CreateDirectory(temporary);
                foreach (var result in report.Results.Where(result => result.Relative.StartsWith(folder + "/", StringComparison.OrdinalIgnoreCase)))
                {
                    var bytes = await File.ReadAllBytesAsync(Path.Combine(outputRoot, result.Relative));
                    if (Convert.ToHexString(SHA256.HashData(bytes)).ToLowerInvariant() != result.Sha256)
                        throw new InvalidDataException($"Staged output changed before apply: {result.Relative}");
                    var originalPath = Path.Combine(applyRoot, result.Relative);
                    statuses[result] = !File.Exists(originalPath) ? "added"
                        : (await File.ReadAllBytesAsync(originalPath)).AsSpan().SequenceEqual(bytes) ? "unchanged" : "updated";
                    var destination = Path.Combine(temporary, result.Relative[(folder.Length + 1)..]);
                    Directory.CreateDirectory(Path.GetDirectoryName(destination)!);
                    await File.WriteAllBytesAsync(destination, bytes);
                }
            }

            foreach (var swap in swaps)
            {
                if (Directory.Exists(swap.Target))
                {
                    Directory.CreateDirectory(Path.GetDirectoryName(swap.Backup)!);
                    Directory.Move(swap.Target, swap.Backup);
                    swap.OriginalMoved = true;
                }
                Directory.Move(swap.Temporary, swap.Target);
                swap.ReplacementMoved = true;
            }
            foreach (var (result, status) in statuses)
                result.Status = status;
            report.Removed = oldFiles.Where(path => !newFiles.Contains(path)).OrderBy(path => path, StringComparer.Ordinal).ToArray();
        }
        catch (Exception applyError)
        {
            var errors = new List<Exception> { applyError };
            foreach (var swap in swaps.AsEnumerable().Reverse())
            {
                try
                {
                    if (swap.ReplacementMoved)
                        Directory.Delete(swap.Target, recursive: true);
                    if (swap.OriginalMoved)
                        Directory.Move(swap.Backup, swap.Target);
                }
                catch (Exception rollbackError)
                {
                    errors.Add(rollbackError);
                }
            }
            throw new AggregateException("Folder update failed; rollback attempted. Check the backup paths before retrying.", errors);
        }
        finally
        {
            foreach (var swap in swaps)
                if (Directory.Exists(swap.Temporary))
                    Directory.Delete(swap.Temporary, recursive: true);
        }
    }

    private static Task SaveDiffDocumentAsync(string path, UpdateReport report)
    {
        var updated = report.Results.Where(result => result.Status == "updated").Select(result => result.Relative).ToArray();
        var added = report.Results.Where(result => result.Status == "added").Select(result => result.Relative).ToArray();
        var unchanged = report.Results.Count(result => result.Status == "unchanged");
        var document = new StringBuilder()
            .AppendLine("# 游戏资源更新差异")
            .AppendLine()
            .AppendLine($"- 完成时间 (UTC)：{DateTime.UtcNow:yyyy-MM-dd HH:mm:ss}")
            .AppendLine($"- 项目资源目录：`{report.OriginalRoot}`")
            .AppendLine($"- 旧资源快照：`{report.BackupRoot ?? "无"}`")
            .AppendLine()
            .AppendLine("## 摘要")
            .AppendLine()
            .AppendLine($"- 更新：{updated.Length}")
            .AppendLine($"- 新增：{added.Length}")
            .AppendLine($"- 删除：{report.Removed.Length}")
            .AppendLine($"- 未变：{unchanged}")
            .AppendLine();

        AppendDiffSection(document, "更新文件", updated);
        AppendDiffSection(document, "新增文件", added);
        AppendDiffSection(document, "删除文件", report.Removed);
        return AssetExporter.WriteAtomicAsync(path, document.ToString());
    }

    private static void AppendDiffSection(StringBuilder document, string title, IEnumerable<string> paths)
    {
        var orderedPaths = paths.OrderBy(value => value, StringComparer.Ordinal).ToArray();
        document.AppendLine($"## {title} ({orderedPaths.Length})").AppendLine();
        if (orderedPaths.Length == 0)
            document.AppendLine("- 无");
        else
            foreach (var item in orderedPaths)
                document.AppendLine($"- `{item}`");
        document.AppendLine();
    }

    private static string NormalizeRelative(string path)
    {
        path = path.Replace('\\', '/').TrimEnd('/');
        if (Path.IsPathRooted(path) || path.Split('/').Any(part => part is ".." or "." or ""))
            throw new InvalidDataException("Manifest folders must be relative paths under Content.");
        return path;
    }

    private static Task SaveReportAsync(string path, UpdateReport report) =>
        AssetExporter.WriteAtomicAsync(path, JsonSerializer.Serialize(report, JsonOptions) + "\n");

    private sealed record Inventory(string Root, string[] Folders, string[]? Files);
    private sealed record Job(string Asset, string Relative);
    private sealed record FolderSwap(string Target, string Temporary, string Backup)
    {
        public bool OriginalMoved { get; set; }
        public bool ReplacementMoved { get; set; }
    }
    private sealed record ExportResult(string Relative, string Asset, string? Source)
    {
        public string Status { get; set; } = "pending";
        public string? Sha256 { get; set; }
        public string? Error { get; set; }
    }
    private sealed record UpdateReport(string OriginalRoot, string OutputRoot, string? BackupRoot, string[] Folders)
    {
        public bool Completed { get; set; }
        public bool Applied { get; set; }
        public string? ApplyError { get; set; }
        public string? DiffDocument { get; set; }
        public string? DiffError { get; set; }
        public List<ExportResult> Results { get; } = [];
        public string[] Removed { get; set; } = [];
        public string[] UnmatchedExisting { get; set; } = [];
        public int Failed => Results.Count(result => result.Status == "failed");
    }
}
