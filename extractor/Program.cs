using System.Text;
using System.Text.Encodings.Web;
using System.Text.Json;
using CUE4Parse.Compression;
using CUE4Parse.Encryption.Aes;
using CUE4Parse.FileProvider;
using CUE4Parse.MappingsProvider.Usmap;
using CUE4Parse.UE4.Localization;
using CUE4Parse.UE4.Versions;
using CUE4Parse.UE4.VirtualFileSystem;
using Serilog;
using Serilog.Events;

const string defaultPaks = "/mnt/e/soft/Steam/steamapps/common/Dark and Darker/DungeonCrawler/Content/Paks";
const string defaultAsset = "DungeonCrawler/Content/Localization/Game/zh-Hans/Game.locres";
const string defaultAesFile = "/mnt/e/Game/fmod/aes.txt";

if (args.Contains("--help") || args.Contains("-h"))
{
    Console.WriteLine("""
        Usage: dotnet run -- [--paks DIRECTORY] [--asset PATH] [--output FILE]
                             [--usmap FILE] [--aes-file FILE] [--game GAME_UE5_6]

        Reads game containers directly and exports a .locres as UTF-8 JSON.
        Defaults: installed Dark and Darker Paks; zh-Hans/Game.locres;
                  output/<asset path with .json extension>, relative to working directory.
        --usmap optionally loads an explicit mapping file; .locres does not require one.
        --aes-file reads a single hex AES key; defaults to /mnt/e/Game/fmod/aes.txt if present.
        --game selects a CUE4Parse EGame name (default: GAME_UE5_6).
        """);
    return 0;
}

Log.Logger = new LoggerConfiguration()
    .MinimumLevel.Information()
    .WriteTo.Console(standardErrorFromLevel: LogEventLevel.Verbose)
    .CreateLogger();

try
{
    var options = new Dictionary<string, string>(StringComparer.Ordinal);
    string[] knownOptions = ["--paks", "--asset", "--output", "--usmap", "--aes-file", "--game"];
    for (var i = 0; i < args.Length; i += 2)
    {
        if (!knownOptions.Contains(args[i]))
            throw new ArgumentException($"Unknown option: {args[i]}. Use --help.");
        if (i + 1 == args.Length || args[i + 1].StartsWith("--", StringComparison.Ordinal))
            throw new ArgumentException($"Missing value for {args[i]}.");
        if (!options.TryAdd(args[i], args[i + 1]))
            throw new ArgumentException($"Repeated option: {args[i]}.");
    }

    var paks = Path.GetFullPath(options.GetValueOrDefault("--paks", defaultPaks));
    if (!Directory.Exists(paks))
        throw new DirectoryNotFoundException($"Paks directory not found: {paks}");

    var asset = options.GetValueOrDefault("--asset", defaultAsset).Replace('\\', '/');
    if (Path.IsPathRooted(asset) || asset.Split('/').Any(part => part is ".." or "." or ""))
        throw new ArgumentException("--asset must be a relative virtual resource path.");
    if (!asset.EndsWith(".locres", StringComparison.OrdinalIgnoreCase))
        throw new ArgumentException("This version exports .locres resources only.");

    var output = Path.GetFullPath(options.GetValueOrDefault("--output",
        Path.Combine("output", Path.ChangeExtension(asset, ".json"))));
    var gameName = options.GetValueOrDefault("--game", "GAME_UE5_6");
    if (!Enum.TryParse<EGame>(gameName, out var game) || !Enum.IsDefined(game)
        || !gameName.StartsWith("GAME_", StringComparison.Ordinal))
        throw new ArgumentException($"Unknown CUE4Parse game version: {gameName}.");

    using var provider = new DefaultFileProvider(paks, SearchOption.TopDirectoryOnly,
        new VersionContainer(game), StringComparer.OrdinalIgnoreCase);
    if (options.TryGetValue("--usmap", out var usmap))
    {
        usmap = Path.GetFullPath(usmap);
        if (!File.Exists(usmap))
            throw new FileNotFoundException($"Mapping file not found: {usmap}");
        provider.MappingsContainer = new FileUsmapTypeMappingsProvider(usmap);
        Console.WriteLine($"Mappings: {usmap} (optional for .locres)");
    }

    FAesKey? aesKey = null;
    var aesFile = options.GetValueOrDefault("--aes-file", defaultAesFile);
    if (File.Exists(aesFile))
    {
        var keyText = (await File.ReadAllTextAsync(aesFile)).Trim();
        if (keyText.StartsWith("0x", StringComparison.OrdinalIgnoreCase))
            keyText = keyText[2..];
        if (keyText.Length != 64 || !keyText.All(Uri.IsHexDigit))
            throw new ArgumentException("AES file must contain one 64-digit hexadecimal key.");
        aesKey = new FAesKey(Convert.FromHexString(keyText));
        Console.WriteLine($"AES file: {Path.GetFullPath(aesFile)} (key not logged)");
    }
    else if (options.ContainsKey("--aes-file"))
        throw new FileNotFoundException($"AES file not found: {aesFile}");

    provider.Initialize();
    if (aesKey is not null)
    {
        var keys = provider.UnloadedVfs.Select(reader => reader.EncryptionKeyGuid).Distinct()
            .Select(guid => new KeyValuePair<CUE4Parse.UE4.Objects.Core.Misc.FGuid, FAesKey>(guid, aesKey));
        await provider.SubmitKeysAsync(keys);
    }
    provider.Mount();
    Console.WriteLine($"Containers: {provider.MountedVfs.Count} mounted, {provider.UnloadedVfs.Count} unmounted");
    var failedContainers = provider.UnloadedVfs.Where(reader => reader.HasDirectoryIndex).ToArray();
    if (failedContainers.Length > 0)
        throw new InvalidOperationException("Some indexed containers could not be mounted: "
            + string.Join(", ", failedContainers.Select(reader => reader.Name)) + ". Check the AES file and container errors. "
            + "Export stopped to avoid silently using an older resource.");
    if (!provider.TryGetGameFile(asset, out var file))
        throw new FileNotFoundException($"Resource not found in mounted containers: {asset}");

    Console.WriteLine($"Asset: {file.Path}");
    Console.WriteLine($"Source: {(file is VfsEntry entry ? entry.Vfs.Path : "loose file")}");

    // Only initialize Oodle when the selected resource actually needs it.
    FTextLocalizationResource resource;
    try
    {
        using var reader = file.CreateReader();
        resource = new FTextLocalizationResource(reader);
    }
    catch (FileLoadException error) when (OodleHelper.Instance is null
        && error.Message.StartsWith("Failed to decompress Oodle data", StringComparison.Ordinal))
    {
        Console.WriteLine("Initializing Linux-compatible Oodle decompression...");
        await OodleHelper.InitializeAsync();
        if (OodleHelper.Instance is null)
            throw new InvalidOperationException("Oodle initialization failed; see the download/decompression errors above.");
        using var reader = file.CreateReader();
        resource = new FTextLocalizationResource(reader);
    }

    var data = new SortedDictionary<string, SortedDictionary<string, string>>(StringComparer.Ordinal);
    foreach (var (ns, entries) in resource.Entries)
    {
        var translations = new SortedDictionary<string, string>(StringComparer.Ordinal);
        foreach (var (key, value) in entries)
        {
            if (value.LocalizedString is null)
                throw new InvalidDataException($"Missing localized text for {ns.Str}/{key.Str}.");
            translations.Add(key.Str, value.LocalizedString);
        }
        data.Add(ns.Str, translations);
    }

    var count = data.Values.Sum(entries => entries.Count);
    if (count == 0)
        throw new InvalidDataException("The localization resource contains no translations.");

    var json = JsonSerializer.Serialize(data, new JsonSerializerOptions
    {
        WriteIndented = true,
        Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping,
    }) + "\n";
    Directory.CreateDirectory(Path.GetDirectoryName(output)!);
    // Replace only after the full resource has parsed and serialized successfully.
    var temporary = output + "." + Guid.NewGuid().ToString("N") + ".tmp";
    try
    {
        await File.WriteAllTextAsync(temporary, json, new UTF8Encoding(false));
        File.Move(temporary, output, overwrite: true);
    }
    finally
    {
        if (File.Exists(temporary))
            File.Delete(temporary);
    }

    Console.WriteLine($"Namespaces: {data.Count}; translations: {count}");
    Console.WriteLine($"Output: {output}");
    return 0;
}
catch (Exception error)
{
    Console.Error.WriteLine($"Export failed: {error}");
    return 1;
}
finally
{
    Log.CloseAndFlush();
}
