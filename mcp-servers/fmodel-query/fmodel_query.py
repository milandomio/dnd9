"""MCP server for querying FModel extracted game data and .pak files."""

import os
import sys
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP
from pak_parser import PakFile, open_pak

# Initialize FastMCP server
mcp = FastMCP("fmodel-query")

# Default paths
DEFAULT_EXPORT_PATH = "/home/mio/fmod/Output/Exports/DungeonCrawler/Content/DungeonCrawler"
DEFAULT_PAK_DIR = "/mnt/e/soft/Steam/steamapps/common/Dark and Darker/DungeonCrawler/Content/Paks"

# Cache for opened pak files
_pak_cache: dict[str, PakFile] = {}


def get_pak_file(pak_path: str) -> PakFile:
    """Get or open a pak file."""
    if pak_path not in _pak_cache:
        _pak_cache[pak_path] = open_pak(pak_path)
    return _pak_cache[pak_path]


@mcp.tool()
def list_directory(path: str = "", custom_export_path: str = "") -> str:
    """List contents of a directory in the FModel export structure.
    
    Args:
        path: Relative path from export root (empty string for root)
        custom_export_path: Custom export path (optional, uses default if empty)
    """
    try:
        export_path = Path(custom_export_path) if custom_export_path else Path(DEFAULT_EXPORT_PATH)
        target_path = export_path / path if path else export_path
        
        if not target_path.exists():
            return f"Error: Path not found: {path}"
        
        if not target_path.is_dir():
            return f"Error: Path is not a directory: {path}"
        
        entries = []
        for entry in sorted(target_path.iterdir()):
            if entry.is_dir():
                entries.append(f"📁 {entry.name}/")
            else:
                size = entry.stat().st_size
                if size > 1024 * 1024:
                    size_str = f"{size / (1024 * 1024):.1f} MB"
                elif size > 1024:
                    size_str = f"{size / 1024:.1f} KB"
                else:
                    size_str = f"{size} B"
                entries.append(f"📄 {entry.name} ({size_str})")
        
        if not entries:
            return f"Directory is empty: {path}"
        
        return f"Contents of {path or 'root'}:\n" + "\n".join(entries)
    
    except Exception as e:
        return f"Error: {str(e)}"


@mcp.tool()
def search_files(
    pattern: str,
    path: str = "",
    custom_export_path: str = ""
) -> str:
    """Search for files matching a pattern in the FModel export structure.
    
    Args:
        pattern: Search pattern (supports wildcards like *.json)
        path: Relative path to search in (empty for root)
        custom_export_path: Custom export path (optional)
    """
    try:
        export_path = Path(custom_export_path) if custom_export_path else Path(DEFAULT_EXPORT_PATH)
        search_path = export_path / path if path else export_path
        
        if not search_path.exists():
            return f"Error: Path not found: {path}"
        
        matches = list(search_path.rglob(pattern))
        
        if not matches:
            return f"No files matching '{pattern}' found in {path or 'root'}"
        
        max_results = 50
        results = []
        for match in sorted(matches)[:max_results]:
            relative = match.relative_to(export_path)
            if match.is_file():
                size = match.stat().st_size
                results.append(f"📄 {relative} ({size} bytes)")
            else:
                results.append(f"📁 {relative}/")
        
        total = len(matches)
        if total > max_results:
            results.append(f"\n... and {total - max_results} more results")
        
        return f"Found {total} matches for '{pattern}':\n" + "\n".join(results)
    
    except Exception as e:
        return f"Error: {str(e)}"


@mcp.tool()
def read_file(
    file_path: str,
    custom_export_path: str = "",
    max_size: int = 10000
) -> str:
    """Read the contents of a file from the FModel export structure.
    
    Args:
        file_path: Relative path to the file
        custom_export_path: Custom export path (optional)
        max_size: Maximum file size to read in bytes (default 10KB)
    """
    try:
        export_path = Path(custom_export_path) if custom_export_path else Path(DEFAULT_EXPORT_PATH)
        target_file = export_path / file_path
        
        if not target_file.exists():
            return f"Error: File not found: {file_path}"
        
        if not target_file.is_file():
            return f"Error: Path is not a file: {file_path}"
        
        file_size = target_file.stat().st_size
        if file_size > max_size:
            return f"Error: File too large ({file_size} bytes). Use max_size parameter to read larger files."
        
        content = target_file.read_text(encoding="utf-8", errors="ignore")
        return f"Contents of {file_path} ({file_size} bytes):\n\n{content}"
    
    except Exception as e:
        return f"Error: {str(e)}"


@mcp.tool()
def get_file_info(
    file_path: str,
    custom_export_path: str = ""
) -> str:
    """Get detailed information about a file or directory.
    
    Args:
        file_path: Relative path to the file or directory
        custom_export_path: Custom export path (optional)
    """
    try:
        export_path = Path(custom_export_path) if custom_export_path else Path(DEFAULT_EXPORT_PATH)
        target_path = export_path / file_path
        
        if not target_path.exists():
            return f"Error: Path not found: {file_path}"
        
        stat = target_path.stat()
        
        info = [
            f"Path: {file_path}",
            f"Type: {'Directory' if target_path.is_dir() else 'File'}",
            f"Size: {stat.st_size} bytes",
            f"Modified: {stat.st_mtime}",
        ]
        
        if target_path.is_file():
            suffix = target_path.suffix.lower()
            type_map = {
                ".json": "JSON data",
                ".uasset": "Unreal Engine asset",
                ".umap": "Unreal Engine map",
                ".png": "PNG image",
                ".jpg": "JPEG image",
                ".tga": "TGA image",
                ".wav": "WAV audio",
                ".ogg": "OGG audio",
            }
            if suffix in type_map:
                info.append(f"Type hint: {type_map[suffix]}")
        
        return "\n".join(info)
    
    except Exception as e:
        return f"Error: {str(e)}"


@mcp.tool()
def list_pak_files(
    pak_dir: str = ""
) -> str:
    """List all .pak files in the game directory.
    
    Args:
        pak_dir: Custom pak directory (optional, uses default if empty)
    """
    try:
        pak_path = Path(pak_dir) if pak_dir else Path(DEFAULT_PAK_DIR)
        
        if not pak_path.exists():
            return f"Error: Pak directory not found: {pak_path}"
        
        pak_files = sorted(pak_path.glob("*.pak"))
        
        if not pak_files:
            return f"No .pak files found in {pak_path}"
        
        results = []
        for pak in pak_files:
            size = pak.stat().st_size
            if size > 1024 * 1024 * 1024:
                size_str = f"{size / (1024 * 1024 * 1024):.2f} GB"
            elif size > 1024 * 1024:
                size_str = f"{size / (1024 * 1024):.1f} MB"
            else:
                size_str = f"{size / 1024:.1f} KB"
            results.append(f"📦 {pak.name} ({size_str})")
        
        return f"Found {len(pak_files)} .pak files:\n" + "\n".join(results)
    
    except Exception as e:
        return f"Error: {str(e)}"


@mcp.tool()
def list_pak_contents(
    pak_file: str,
    prefix: str = "",
    pak_dir: str = "",
    max_results: int = 100
) -> str:
    """List files inside a .pak file.
    
    Args:
        pak_file: Name of the pak file (e.g., pakchunk0-Windows.pak)
        prefix: Optional prefix filter (e.g., /Game/Data/)
        pak_dir: Custom pak directory (optional)
        max_results: Maximum results to return (default 100)
    """
    try:
        pak_path = Path(pak_dir) if pak_dir else Path(DEFAULT_PAK_DIR)
        full_path = pak_path / pak_file
        
        if not full_path.exists():
            return f"Error: Pak file not found: {full_path}"
        
        with open_pak(full_path) as pak:
            files = pak.list_files(prefix)
            
            if not files:
                return f"No files found with prefix '{prefix}' in {pak_file}"
            
            results = []
            for f in files[:max_results]:
                results.append(f"📄 {f}")
            
            total = len(files)
            if total > max_results:
                results.append(f"\n... and {total - max_results} more files")
            
            return f"Files in {pak_file}" + (f" (prefix: {prefix})" if prefix else "") + f":\n" + "\n".join(results)
    
    except Exception as e:
        return f"Error: {str(e)}"


@mcp.tool()
def search_pak_files(
    pak_file: str,
    pattern: str,
    pak_dir: str = ""
) -> str:
    """Search for files matching a pattern inside a .pak file.
    
    Args:
        pak_file: Name of the pak file
        pattern: Search pattern (supports * and ? wildcards, e.g., *.json, *sword*)
        pak_dir: Custom pak directory (optional)
    """
    try:
        pak_path = Path(pak_dir) if pak_dir else Path(DEFAULT_PAK_DIR)
        full_path = pak_path / pak_file
        
        if not full_path.exists():
            return f"Error: Pak file not found: {full_path}"
        
        with open_pak(full_path) as pak:
            files = pak.search_files(pattern)
            
            if not files:
                return f"No files matching '{pattern}' found in {pak_file}"
            
            max_results = 50
            results = []
            for f in files[:max_results]:
                results.append(f"📄 {f}")
            
            total = len(files)
            if total > max_results:
                results.append(f"\n... and {total - max_results} more files")
            
            return f"Found {total} files matching '{pattern}' in {pak_file}:\n" + "\n".join(results)
    
    except Exception as e:
        return f"Error: {str(e)}"


@mcp.tool()
def extract_from_pak(
    pak_file: str,
    file_path: str,
    pak_dir: str = ""
) -> str:
    """Extract and read a file from a .pak file.
    
    Args:
        pak_file: Name of the pak file
        file_path: Path of the file inside the pak
        pak_dir: Custom pak directory (optional)
    """
    try:
        pak_path = Path(pak_dir) if pak_dir else Path(DEFAULT_PAK_DIR)
        full_path = pak_path / pak_file
        
        if not full_path.exists():
            return f"Error: Pak file not found: {full_path}"
        
        with open_pak(full_path) as pak:
            info = pak.get_file_info(file_path)
            if not info:
                return f"Error: File not found in pak: {file_path}"
            
            data = pak.extract_file(file_path)
            if data is None:
                return f"Error: Failed to extract file: {file_path}"
            
            # Try to decode as text
            try:
                content = data.decode("utf-8", errors="strict")
                return f"Contents of {file_path} from {pak_file} ({len(data)} bytes):\n\n{content}"
            except UnicodeDecodeError:
                return f"Binary file {file_path} from {pak_file} ({len(data)} bytes)"
    
    except Exception as e:
        return f"Error: {str(e)}"


@mcp.tool()
def get_pak_stats(
    pak_file: str,
    pak_dir: str = ""
) -> str:
    """Get statistics about a .pak file.
    
    Args:
        pak_file: Name of the pak file
        pak_dir: Custom pak directory (optional)
    """
    try:
        pak_path = Path(pak_dir) if pak_dir else Path(DEFAULT_PAK_DIR)
        full_path = pak_path / pak_file
        
        if not full_path.exists():
            return f"Error: Pak file not found: {full_path}"
        
        with open_pak(full_path) as pak:
            stats = pak.get_stats()
            
            total_size = stats["total_size"]
            if total_size > 1024 * 1024 * 1024:
                size_str = f"{total_size / (1024 * 1024 * 1024):.2f} GB"
            elif total_size > 1024 * 1024:
                size_str = f"{total_size / (1024 * 1024):.1f} MB"
            else:
                size_str = f"{total_size / 1024:.1f} KB"
            
            results = [
                f"Pak file: {pak_file}",
                f"Version: {stats['version']}",
                f"Mount point: {stats['mount_point']}",
                f"Total files: {stats['total_files']}",
                f"Total size: {size_str}",
                f"Encrypted: {'Yes' if stats['encrypted'] else 'No'}",
                "",
                "File types:"
            ]
            
            for ext, count in sorted(stats["extensions"].items(), key=lambda x: -x[1])[:20]:
                results.append(f"  {ext or '(no ext)'}: {count}")
            
            return "\n".join(results)
    
    except Exception as e:
        return f"Error: {str(e)}"


@mcp.tool()
def get_pak_file_info(
    pak_file: str,
    file_path: str,
    pak_dir: str = ""
) -> str:
    """Get information about a specific file inside a .pak file.
    
    Args:
        pak_file: Name of the pak file
        file_path: Path of the file inside the pak
        pak_dir: Custom pak directory (optional)
    """
    try:
        pak_path = Path(pak_dir) if pak_dir else Path(DEFAULT_PAK_DIR)
        full_path = pak_path / pak_file
        
        if not full_path.exists():
            return f"Error: Pak file not found: {full_path}"
        
        with open_pak(full_path) as pak:
            info = pak.get_file_info(file_path)
            
            if not info:
                return f"Error: File not found in pak: {file_path}"
            
            results = [
                f"File: {info['filename']}",
                f"Size: {info['size']} bytes",
                f"Offset: {info['offset']}",
                f"Compressed: {'Yes' if info['compressed'] else 'No'}",
            ]
            
            if info['compressed']:
                results.append(f"Compressed size: {info['compressed_size']} bytes")
            
            return "\n".join(results)
    
    except Exception as e:
        return f"Error: {str(e)}"


def main():
    """Run the MCP server."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
