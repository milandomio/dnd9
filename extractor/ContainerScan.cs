using System.Text.Json;
using CUE4Parse.FileProvider;
using CUE4Parse.UE4.VirtualFileSystem;

internal static class ContainerScan
{
    public static async Task<int> RunAsync(DefaultFileProvider provider, string query, string? output)
    {
        query = query.Replace('\\', '/').Trim();
        if (query.Length == 0)
            throw new ArgumentException("--scan requires a keyword or a virtual resource path.");
        var matches = provider.Files.Keys.Distinct(StringComparer.OrdinalIgnoreCase)
            .Where(path => path.Contains(query, StringComparison.OrdinalIgnoreCase))
            .OrderBy(path => path, StringComparer.Ordinal)
            .Select(path => provider[path])
            .Select(file => new
            {
                file.Path,
                Extension = Path.GetExtension(file.Path),
                Source = (file as VfsEntry)?.Vfs.Path,
            }).ToArray();
        var folders = matches.GroupBy(file => file.Path[..file.Path.LastIndexOf('/')])
            .Select(group => new { Path = group.Key, Files = group.Count() }).ToArray();
        Console.WriteLine($"Scan: {query}; files={matches.Length}; folders={folders.Length}");
        foreach (var folder in folders.Take(50))
            Console.WriteLine($"Folder: {folder.Path} ({folder.Files} files)");
        foreach (var file in matches.Take(50))
            Console.WriteLine($"File: {file.Path}");
        if (matches.Length > 50 || folders.Length > 50)
            Console.WriteLine("Showing the first 50 entries. Use --output FILE for the complete inventory.");
        if (output is not null)
        {
            output = Path.GetFullPath(output);
            await AssetExporter.WriteAtomicAsync(output, JsonSerializer.Serialize(new
            {
                Query = query,
                Folders = folders,
                Files = matches,
            }, new JsonSerializerOptions { WriteIndented = true }) + "\n");
            Console.WriteLine($"Inventory: {output}");
        }
        return matches.Length == 0 ? 1 : 0;
    }
}
