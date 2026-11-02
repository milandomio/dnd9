using System.Text;
using System.Text.Encodings.Web;
using System.Text.Json;
using CUE4Parse.Compression;
using CUE4Parse.FileProvider;
using CUE4Parse.FileProvider.Objects;
using CUE4Parse.UE4.Assets;
using CUE4Parse.UE4.Localization;
using Newtonsoft.Json;

internal static class AssetExporter
{
    public static bool Supports(string path) => Path.GetExtension(path).ToLowerInvariant() is ".locres" or ".uasset" or ".umap";

    public static async Task<string> SerializeAsync(DefaultFileProvider provider, GameFile file)
    {
        var errorsBefore = ExportDiagnostics.Errors;
        string json;
        try
        {
            json = Serialize(provider, file);
        }
        catch (FileLoadException error) when (OodleHelper.Instance is null
            && error.Message.StartsWith("Failed to decompress Oodle data", StringComparison.Ordinal))
        {
            Console.WriteLine("Initializing Linux-compatible Oodle decompression...");
            await OodleHelper.InitializeAsync();
            if (OodleHelper.Instance is null)
                throw new InvalidOperationException("Oodle initialization failed; see the decompression errors above.");
            json = Serialize(provider, file);
        }
        if (ExportDiagnostics.Errors != errorsBefore)
            throw new InvalidDataException($"CUE4Parse reported serialization errors for {file.Path}; see the log.");
        using var document = JsonDocument.Parse(json);
        return json;
    }

    private static string Serialize(DefaultFileProvider provider, GameFile file)
    {
        if (!file.Path.EndsWith(".locres", StringComparison.OrdinalIgnoreCase))
        {
            var package = provider.LoadPackage(file);
            if (!package.CanDeserialize)
                throw new InvalidDataException($"Cannot deserialize package: {file.Path}");
            var exports = package.GetExports().ToArray();
            if (exports.Length != package.ExportMapLength || exports.Length == 0)
                throw new InvalidDataException($"Incomplete or empty package: {file.Path}");
            return JsonConvert.SerializeObject(exports, Formatting.Indented) + "\n";
        }

        using var reader = file.CreateReader();
        var resource = new FTextLocalizationResource(reader);
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
        Console.WriteLine($"Namespaces: {data.Count}; translations: {count}");
        return System.Text.Json.JsonSerializer.Serialize(data, new JsonSerializerOptions
        {
            WriteIndented = true,
            Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping,
        }) + "\n";
    }

    public static async Task WriteAtomicAsync(string output, string text)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(output)!);
        var temporary = output + "." + Guid.NewGuid().ToString("N") + ".tmp";
        try
        {
            await File.WriteAllTextAsync(temporary, text, new UTF8Encoding(false));
            File.Move(temporary, output, overwrite: true);
        }
        finally
        {
            if (File.Exists(temporary))
                File.Delete(temporary);
        }
    }
}
