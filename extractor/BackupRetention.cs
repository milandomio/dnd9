using System.Globalization;

internal static class BackupRetention
{
    private const string BackupPrefix = "backup-";
    private const string DiffPrefix = "update-diff-";
    private const string CompletionMarker = "comparison-complete";

    public static IReadOnlyList<string> RemoveComparedBackups(string backupCollectionRoot, string originalRoot, Action<string>? log = null)
    {
        var root = Path.GetFullPath(backupCollectionRoot);
        var expectedRoot = Path.GetFullPath(originalRoot);
        var pathComparison = OperatingSystem.IsWindows() ? StringComparison.OrdinalIgnoreCase : StringComparison.Ordinal;
        if (!Directory.Exists(root))
            return [];

        var removed = new List<string>();
        foreach (var runDirectory in Directory.EnumerateDirectories(root, BackupPrefix + "*", SearchOption.TopDirectoryOnly))
        {
            var runName = Path.GetFileName(runDirectory);
            if (!TryGetRunId(runName, out var runId) || IsReparsePoint(runDirectory))
                continue;

            var content = Path.Combine(runDirectory, "Content");
            var marker = Path.Combine(runDirectory, CompletionMarker);
            var diffDocument = Path.Combine(root, DiffPrefix + runId + ".md");
            if (!Directory.Exists(content) || !File.Exists(marker) || !File.Exists(diffDocument)
                || IsReparsePoint(marker) || IsReparsePoint(diffDocument))
                continue;

            try
            {
                var markedRoot = File.ReadAllText(marker).Trim();
                if (!Path.IsPathRooted(markedRoot)
                    || !Path.GetFullPath(markedRoot).Equals(expectedRoot, pathComparison))
                    continue;
                Directory.Delete(runDirectory, recursive: true);
                removed.Add(runDirectory);
                log?.Invoke($"Removed compared backup: {runDirectory}");
            }
            catch (Exception error)
            {
                log?.Invoke($"Could not remove compared backup {runDirectory}: {error.Message}");
            }
        }
        return removed;
    }

    public static string CompletionMarkerPath(string backupRoot)
    {
        var runDirectory = Directory.GetParent(Path.GetFullPath(backupRoot))?.FullName
            ?? throw new ArgumentException("Backup root must be nested inside a run directory.", nameof(backupRoot));
        return Path.Combine(runDirectory, CompletionMarker);
    }

    private static bool TryGetRunId(string runName, out string runId)
    {
        runId = string.Empty;
        if (!runName.StartsWith(BackupPrefix, StringComparison.Ordinal))
            return false;

        var suffix = runName[BackupPrefix.Length..];
        if (suffix.Length != 24 || suffix[15] != '-'
            || !DateTime.TryParseExact(suffix[..15], "yyyyMMdd'T'HHmmss", CultureInfo.InvariantCulture,
                DateTimeStyles.AssumeUniversal | DateTimeStyles.AdjustToUniversal, out _)
            || !suffix[16..].All(Uri.IsHexDigit))
            return false;

        runId = suffix;
        return true;
    }

    private static bool IsReparsePoint(string path)
    {
        try
        {
            return (File.GetAttributes(path) & FileAttributes.ReparsePoint) != 0;
        }
        catch
        {
            return true;
        }
    }
}
