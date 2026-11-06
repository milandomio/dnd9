using System.Text;

var root = Path.Combine(Path.GetTempPath(), "extractor-backup-retention-" + Guid.NewGuid().ToString("N"));
var projectRoot = Path.Combine(root, "project", "Content");
var otherProjectRoot = Path.Combine(root, "other-project", "Content");
Directory.CreateDirectory(root);
try
{
    CreateBackup(root, "20261101T100000-00000001", projectRoot, compared: true, diffDocument: true);
    CreateBackup(root, "20261102T100000-00000002", projectRoot, compared: true, diffDocument: false);
    CreateBackup(root, "20261103T100000-00000003", projectRoot, compared: false, diffDocument: true);
    CreateBackup(root, "20261104T100000-00000004", projectRoot, compared: true, diffDocument: true);
    CreateBackup(root, "20261105T100000-00000005", otherProjectRoot, compared: true, diffDocument: true);
    Directory.CreateDirectory(Path.Combine(root, "other-output", "Content"));

    var removed = BackupRetention.RemoveComparedBackups(root, projectRoot);
    Require(removed.Count == 2, $"Expected 2 compared backups removed, got {removed.Count}.");
    Require(!Directory.Exists(BackupPath(root, "20261101T100000-00000001")), "Old compared backup should be removed.");
    Require(!Directory.Exists(BackupPath(root, "20261104T100000-00000004")), "Latest completed comparison backup should be removed on the next cycle.");
    Require(Directory.Exists(BackupPath(root, "20261102T100000-00000002")), "Backup without a diff document must be retained.");
    Require(Directory.Exists(BackupPath(root, "20261103T100000-00000003")), "Backup without a completion marker must be retained.");
    Require(Directory.Exists(BackupPath(root, "20261105T100000-00000005")), "Backups for another project root must be retained.");
    Require(Directory.Exists(Path.Combine(root, "other-output", "Content")), "Non-backup directories must be untouched.");

    var preservedBackups = Directory.GetDirectories(root, "backup-*", SearchOption.TopDirectoryOnly).Length;
    Require(preservedBackups == 3, $"Expected 3 unverified or unrelated backups preserved, got {preservedBackups}.");
    Console.WriteLine("PASS cleanup requires a retained diff, completion marker, and matching project root");
}
finally
{
    Directory.Delete(root, recursive: true);
}

static void CreateBackup(string root, string runId, string projectRoot, bool compared, bool diffDocument)
{
    var runDirectory = Path.Combine(root, "backup-" + runId);
    Directory.CreateDirectory(Path.Combine(runDirectory, "Content", "DungeonCrawler"));
    File.WriteAllText(Path.Combine(runDirectory, "Content", "DungeonCrawler", "snapshot.json"), runId, Encoding.UTF8);
    if (compared)
        File.WriteAllText(BackupRetention.CompletionMarkerPath(Path.Combine(runDirectory, "Content")), projectRoot, Encoding.UTF8);
    if (diffDocument)
        File.WriteAllText(Path.Combine(root, "update-diff-" + runId + ".md"), "# Diff", Encoding.UTF8);
}

static string BackupPath(string root, string runId) => Path.Combine(root, "backup-" + runId);

static void Require(bool condition, string message)
{
    if (!condition)
        throw new InvalidOperationException(message);
}
