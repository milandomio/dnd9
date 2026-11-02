using System.Text.Json;

internal sealed record ExtractorSettings(string PaksDirectory, string AesFile, string UsmapDirectory, string Game)
{
    public static ExtractorSettings Load(string? configurationPath)
    {
        var directory = new DirectoryInfo(AppContext.BaseDirectory);
        while (directory.Parent is not null && !File.Exists(Path.Combine(directory.FullName, "Extractor.csproj")))
            directory = directory.Parent;
        var moduleDirectory = File.Exists(Path.Combine(directory.FullName, "Extractor.csproj"))
            ? directory.FullName : AppContext.BaseDirectory;
        var configPath = configurationPath is null ? Path.Combine(moduleDirectory, "config.json") : Path.GetFullPath(configurationPath);
        var configDirectory = Path.GetDirectoryName(configPath)!;
        var values = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        foreach (var file in new[] { configPath, Path.Combine(configDirectory, "config.local.json") }.Distinct())
        {
            if (!File.Exists(file))
            {
                if (configurationPath is not null && file == configPath)
                    throw new FileNotFoundException($"Configuration not found: {file}");
                continue;
            }
            var parsed = JsonSerializer.Deserialize<Dictionary<string, string>>(File.ReadAllText(file))
                ?? throw new InvalidDataException($"Empty configuration: {file}");
            foreach (var (key, value) in parsed)
                values[key] = value;
        }
        string Resolve(string value) => string.IsNullOrWhiteSpace(value) ? "" : Path.GetFullPath(value, configDirectory);
        return new ExtractorSettings(
            Resolve(values.GetValueOrDefault("paksDirectory", "")),
            Resolve(values.GetValueOrDefault("aesFile", "keys/aes.txt")),
            Resolve(values.GetValueOrDefault("usmapDirectory", "keys")),
            values.GetValueOrDefault("game", "GAME_UE5_8"));
    }
}
