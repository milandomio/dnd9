using CUE4Parse.Encryption.Aes;
using CUE4Parse.FileProvider;
using CUE4Parse.MappingsProvider.Usmap;
using CUE4Parse.UE4.Versions;
using CUE4Parse.UE4.VirtualFileSystem;
using Serilog;
using Serilog.Events;

const string defaultAsset = "DungeonCrawler/Content/Localization/Game/zh-Hans/Game.locres";

if (args.Contains("--help") || args.Contains("-h"))
{
    Console.WriteLine("""
        Usage: dotnet run -- [--paks DIRECTORY] [--asset PATH] [--output FILE]
                             [--usmap FILE] [--aes-file FILE] [--game GAME_UE5_8]
               dotnet run -- --manifest FILE --output-root DIRECTORY [--apply-to CONTENT_ROOT]
                             [--report FILE] [--usmap FILE] [--usmap-dir DIRECTORY]
               dotnet run -- --scan KEYWORD_OR_PATH [--output INVENTORY_JSON]
        All modes accept --config FILE (default: module config.json plus config.local.json).

        Reads game containers directly and exports .locres/.uasset/.umap as UTF-8 JSON.
        Defaults: configured Paks directory; zh-Hans/Game.locres;
                  output/<asset path with .json extension>, relative to working directory.
        --usmap optionally loads an explicit mapping file; .locres does not require one.
        UObject/batch exports default to the newest .usmap in configured keys/.
        --manifest accepts root/folders configuration and optional files from fmodel-query.
        Batch mode recursively exports all resources under the configured folders.
        --apply-to backs up/replaces folders, writes a diff, and prunes only compared backups next run.
        --aes-file reads a single hex AES key; defaults to configured keys/aes.txt if present.
        --game selects a CUE4Parse EGame name (default: GAME_UE5_8).
        """);
    return 0;
}

Log.Logger = new LoggerConfiguration()
    .MinimumLevel.Information()
    .WriteTo.Sink(new ExportDiagnostics())
    .WriteTo.Console(standardErrorFromLevel: LogEventLevel.Verbose)
    .CreateLogger();

try
{
    var options = new Dictionary<string, string>(StringComparer.Ordinal);
    string[] knownOptions = ["--paks", "--asset", "--output", "--usmap", "--usmap-dir", "--aes-file", "--game",
        "--manifest", "--output-root", "--apply-to", "--report", "--scan", "--config"];
    for (var i = 0; i < args.Length; i += 2)
    {
        if (!knownOptions.Contains(args[i]))
            throw new ArgumentException($"Unknown option: {args[i]}. Use --help.");
        if (i + 1 == args.Length || args[i + 1].StartsWith("--", StringComparison.Ordinal))
            throw new ArgumentException($"Missing value for {args[i]}.");
        if (!options.TryAdd(args[i], args[i + 1]))
            throw new ArgumentException($"Repeated option: {args[i]}.");
    }

    var batch = options.ContainsKey("--manifest");
    var scan = options.ContainsKey("--scan");
    if (scan && (batch || options.ContainsKey("--asset")))
        throw new ArgumentException("Use --scan separately from --manifest/--asset.");
    if (batch && (options.ContainsKey("--asset") || options.ContainsKey("--output")))
        throw new ArgumentException("Use --output-root in batch mode, without --asset/--output.");
    if (!batch && new[] { "--output-root", "--apply-to", "--report" }.Any(options.ContainsKey))
        throw new ArgumentException("--output-root/--apply-to/--report require --manifest.");

    var settings = ExtractorSettings.Load(options.GetValueOrDefault("--config"));
    var configuredPaks = options.GetValueOrDefault("--paks", settings.PaksDirectory);
    if (string.IsNullOrWhiteSpace(configuredPaks))
        throw new ArgumentException("Set paksDirectory in config.local.json or pass --paks DIRECTORY.");
    var paks = Path.GetFullPath(configuredPaks);
    if (!Directory.Exists(paks))
        throw new DirectoryNotFoundException($"Paks directory not found: {paks}");

    var asset = options.GetValueOrDefault("--asset", defaultAsset).Replace('\\', '/');
    if (Path.IsPathRooted(asset) || asset.Split('/').Any(part => part is ".." or "." or ""))
        throw new ArgumentException("--asset must be a relative virtual resource path.");
    if (!AssetExporter.Supports(asset))
        throw new ArgumentException("Supported resources: .locres, .uasset and .umap.");

    var output = Path.GetFullPath(options.GetValueOrDefault("--output",
        Path.Combine("output", Path.ChangeExtension(asset, ".json"))));
    var gameName = options.GetValueOrDefault("--game", settings.Game);
    if (!Enum.TryParse<EGame>(gameName, out var game) || !Enum.IsDefined(game)
        || !gameName.StartsWith("GAME_", StringComparison.Ordinal))
        throw new ArgumentException($"Unknown CUE4Parse game version: {gameName}.");

    using var provider = new DefaultFileProvider(paks, SearchOption.TopDirectoryOnly,
        new VersionContainer(game), StringComparer.OrdinalIgnoreCase);
    var usmap = options.GetValueOrDefault("--usmap");
    if (usmap is null && (batch || !asset.EndsWith(".locres", StringComparison.OrdinalIgnoreCase)))
    {
        var mappingsDirectory = options.GetValueOrDefault("--usmap-dir", settings.UsmapDirectory);
        usmap = Directory.Exists(mappingsDirectory)
            ? Directory.EnumerateFiles(mappingsDirectory, "*.usmap")
                .OrderByDescending(File.GetLastWriteTimeUtc).ThenBy(path => path, StringComparer.Ordinal).FirstOrDefault()
            : null;
        if (usmap is null)
            throw new FileNotFoundException("UObject exports require a .usmap. Set --usmap or --usmap-dir.");
    }
    if (usmap is not null)
    {
        usmap = Path.GetFullPath(usmap);
        if (!File.Exists(usmap))
            throw new FileNotFoundException($"Mapping file not found: {usmap}");
        provider.MappingsContainer = new FileUsmapTypeMappingsProvider(usmap);
        Console.WriteLine($"Mappings: {usmap} (optional for .locres)");
    }

    FAesKey? aesKey = null;
    var aesFile = options.GetValueOrDefault("--aes-file", settings.AesFile);
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
    provider.PostMount();
    Console.WriteLine($"Containers: {provider.MountedVfs.Count} mounted, {provider.UnloadedVfs.Count} unmounted");
    var failedContainers = provider.UnloadedVfs.Where(reader => reader.HasDirectoryIndex).ToArray();
    if (failedContainers.Length > 0)
        throw new InvalidOperationException("Some indexed containers could not be mounted: "
            + string.Join(", ", failedContainers.Select(reader => reader.Name)) + ". Check the AES file and container errors. "
            + "Export stopped to avoid silently using an older resource.");

    CUE4Parse.Globals.FatalObjectSerializationErrors = true;
    if (scan)
        return await ContainerScan.RunAsync(provider, options["--scan"], options.GetValueOrDefault("--output"));
    if (batch || !asset.EndsWith(".locres", StringComparison.OrdinalIgnoreCase))
    {
        provider.LoadVirtualPaths();
        provider.ChangeCulture("en");
    }
    if (batch)
        return await BatchExport.RunAsync(provider, options);

    if (!provider.TryGetGameFile(asset, out var file))
        throw new FileNotFoundException($"Resource not found in mounted containers: {asset}");

    Console.WriteLine($"Asset: {file.Path}");
    Console.WriteLine($"Source: {(file is VfsEntry entry ? entry.Vfs.Path : "loose file")}");

    var json = await AssetExporter.SerializeAsync(provider, file);
    await AssetExporter.WriteAtomicAsync(output, json);
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
