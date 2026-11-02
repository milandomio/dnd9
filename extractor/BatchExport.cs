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
        var backupRoot = applyRoot is null ? null : Path.Combine(Path.GetDirectoryName(outputRoot)!,
            "backup-" + DateTime.UtcNow.ToString("yyyyMMddTHHmmss") + "-" + Guid.NewGuid().ToString("N")[..8], "Content");

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
        report.Completed = true;
        await SaveReportAsync(reportPath, report);
        Console.WriteLine($"Batch complete: total={report.Results.Count}, failed={report.Failed}, "
            + $"updated={report.Results.Count(r => r.Status == "updated")}, added={report.Results.Count(r => r.Status == "added")}, "
            + $"unchanged={report.Results.Count(r => r.Status == "unchanged")}");
        Console.WriteLine($"Report: {reportPath}");
        if (backupRoot is not null)
            Console.WriteLine($"Backup: {backupRoot}");
        return report.Failed == 0 ? 0 : 1;
    }

    private static async Task ApplyFoldersAsync(UpdateReport report, string applyRoot, string outputRoot,
        string backupRoot, string[] folders)
    {
        var swaps = new List<FolderSwap>();
        var statuses = new Dictionary<ExportResult, string>();
        try
        {
            // Prepare and verify every replacement before moving any original directory.
            foreach (var folder in folders)
            {
                var target = Path.Combine(applyRoot, folder);
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
        public List<ExportResult> Results { get; } = [];
        public string[] UnmatchedExisting { get; set; } = [];
        public int Failed => Results.Count(result => result.Status == "failed");
    }
}
