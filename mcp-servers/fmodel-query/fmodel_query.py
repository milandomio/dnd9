"""MCP server for querying FModel extracted game data."""

import os
import sys
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("fmodel-query")

# Default export path (FModel extracted data)
DEFAULT_EXPORT_PATH = "/home/mio/fmod/Output/Exports/DungeonCrawler/Content/DungeonCrawler"


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
    max_size: int = 50000
) -> str:
    """Read the contents of a file from the FModel export structure.
    
    Args:
        file_path: Relative path to the file
        custom_export_path: Custom export path (optional)
        max_size: Maximum file size to read in bytes (default 50KB)
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
def search_json_keys(
    key_name: str,
    path: str = "",
    custom_export_path: str = ""
) -> str:
    """Search for JSON files containing a specific key.
    
    Args:
        key_name: The JSON key to search for
        path: Relative path to search in (empty for root)
        custom_export_path: Custom export path (optional)
    """
    try:
        import json
        
        export_path = Path(custom_export_path) if custom_export_path else Path(DEFAULT_EXPORT_PATH)
        search_path = export_path / path if path else export_path
        
        if not search_path.exists():
            return f"Error: Path not found: {path}"
        
        matches = []
        max_results = 20
        
        for json_file in search_path.rglob("*.json"):
            if len(matches) >= max_results:
                break
            
            try:
                content = json_file.read_text(encoding="utf-8", errors="ignore")
                data = json.loads(content)
                
                if isinstance(data, dict) and key_name in data:
                    relative = json_file.relative_to(export_path)
                    matches.append(f"📄 {relative}")
            except (json.JSONDecodeError, Exception):
                continue
        
        if not matches:
            return f"No JSON files containing key '{key_name}' found in {path or 'root'}"
        
        result = f"JSON files containing key '{key_name}':\n" + "\n".join(matches)
        if len(matches) >= max_results:
            result += f"\n\n(Results limited to {max_results} files)"
        
        return result
    
    except Exception as e:
        return f"Error: {str(e)}"


def main():
    """Run the MCP server."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
