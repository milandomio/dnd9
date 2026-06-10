"""Unreal Engine 5.5 .pak file parser."""

import struct
from pathlib import Path
from typing import Any


class PakFile:
    """Parser for Unreal Engine .pak files (supports UE5.x)."""
    
    MAGIC = 0x5A6F12E1
    
    # Compression methods
    COMPRESSION_NONE = 0
    COMPRESSION_ZLIB = 1
    COMPRESSION_GZIP = 2
    COMPRESSION_OODLE = 3
    COMPRESSION_LZ4 = 4
    
    def __init__(self, pak_path: str | Path):
        self.path = Path(pak_path)
        self.file = None
        self.mount_point = ""
        self.entries: dict[str, dict[str, Any]] = {}
        self.version = 0
        self.index_offset = 0
        self.index_size = 0
        self._parsed = False
    
    def __enter__(self):
        self.open()
        return self
    
    def __exit__(self, *args):
        self.close()
    
    def open(self):
        """Open the pak file and parse the index."""
        if self.file:
            return
        
        self.file = open(self.path, "rb")
        self._parse_header()
        self._parse_index()
        self._parsed = True
    
    def close(self):
        """Close the pak file."""
        if self.file:
            self.file.close()
            self.file = None
    
    def _parse_header(self):
        """Parse the pak file header."""
        # Read magic number
        magic_bytes = self.file.read(4)
        if len(magic_bytes) < 4:
            raise ValueError("File too small to be a pak file")
        
        magic = struct.unpack("<I", magic_bytes)[0]
        if magic != self.MAGIC:
            raise ValueError(f"Invalid pak file: wrong magic number (0x{magic:08X})")
        
        # Read version
        self.version = struct.unpack("<i", self.file.read(4))[0]
        
        # Read index offset and size
        self.index_offset = struct.unpack("<q", self.file.read(8))[0]
        self.index_size = struct.unpack("<q", self.file.read(8))[0]
        
        # Read SHA1 hash (20 bytes)
        sha1 = self.file.read(20)
        
        # Read encrypted flag
        encrypted = struct.unpack("<b", self.file.read(1))[0]
        self.encrypted = bool(encrypted)
        
        # For version >= 11 (UE5.x), there's a compression method field
        if self.version >= 11:
            self.compression_method = struct.unpack("<i", self.file.read(4))[0]
        else:
            self.compression_method = self.COMPRESSION_NONE
    
    def _parse_index(self):
        """Parse the file index."""
        self.file.seek(self.index_offset)
        
        # Read mount point
        mount_point = self._read_fstring()
        self.mount_point = mount_point
        
        # Read entry count
        entry_count = struct.unpack("<i", self.file.read(4))[0]
        
        # Read entries
        for _ in range(entry_count):
            self._read_entry()
    
    def _read_entry(self):
        """Read a single index entry."""
        # Read filename
        filename = self._read_fstring()
        
        # Read offset and size
        offset = struct.unpack("<q", self.file.read(8))[0]
        size = struct.unpack("<q", self.file.read(8))[0]
        
        # Read raw offset and size (for compressed files)
        raw_offset = struct.unpack("<q", self.file.read(8))[0]
        raw_size = struct.unpack("<q", self.file.read(8))[0]
        
        # Read compressed size
        compressed_size = struct.unpack("<q", self.file.read(8))[0]
        
        # Read SHA1
        sha1 = self.file.read(20)
        
        # Read flags
        flags = struct.unpack("<B", self.file.read(1))[0]
        
        # Store entry with metadata
        self.entries[filename] = {
            "offset": offset,
            "size": size,
            "raw_offset": raw_offset,
            "raw_size": raw_size,
            "compressed_size": compressed_size,
            "flags": flags,
            "compressed": (flags & 0x01) != 0,
            "encrypted": (flags & 0x02) != 0,
        }
    
    def _read_fstring(self) -> str:
        """Read an FString from the file."""
        # Read length
        length = struct.unpack("<i", self.file.read(4))[0]
        
        if length < 0:
            # Unicode string
            char_count = -length
            data = self.file.read(char_count * 2)
            return data.decode("utf-16-le").rstrip("\x00")
        else:
            # ANSI string
            data = self.file.read(length)
            return data.decode("utf-8", errors="replace").rstrip("\x00")
    
    def list_files(self, prefix: str = "") -> list[str]:
        """List all files in the pak, optionally filtered by prefix."""
        if not self._parsed:
            self.open()
        
        files = []
        for filename in sorted(self.entries.keys()):
            if prefix and not filename.startswith(prefix):
                continue
            files.append(filename)
        
        return files
    
    def search_files(self, pattern: str) -> list[str]:
        """Search for files matching a pattern (supports * and ? wildcards)."""
        if not self._parsed:
            self.open()
        
        import fnmatch
        files = []
        for filename in sorted(self.entries.keys()):
            if fnmatch.fnmatch(filename.lower(), pattern.lower()):
                files.append(filename)
        
        return files
    
    def get_file_info(self, filename: str) -> dict[str, Any] | None:
        """Get information about a file."""
        if not self._parsed:
            self.open()
        
        entry = self.entries.get(filename)
        if entry:
            return {
                "filename": filename,
                "offset": entry["offset"],
                "size": entry["size"],
                "raw_size": entry["raw_size"],
                "compressed_size": entry["compressed_size"],
                "compressed": entry["compressed"],
                "encrypted": entry["encrypted"],
            }
        return None
    
    def extract_file(self, filename: str) -> bytes | None:
        """Extract a file's contents from the pak."""
        if not self._parsed:
            self.open()
        
        entry = self.entries.get(filename)
        if not entry:
            return None
        
        # Seek to the file data
        self.file.seek(entry["offset"])
        
        # Read the data
        data = self.file.read(entry["size"])
        
        # If compressed, we would need to decompress here
        # For now, return raw data
        return data
    
    def get_mount_point(self) -> str:
        """Get the mount point of the pak file."""
        if not self._parsed:
            self.open()
        
        return self.mount_point
    
    def get_version(self) -> int:
        """Get the pak file version."""
        if not self._parsed:
            self.open()
        
        return self.version
    
    def get_stats(self) -> dict[str, Any]:
        """Get statistics about the pak file."""
        if not self._parsed:
            self.open()
        
        total_size = sum(e["size"] for e in self.entries.values())
        
        # Count by extension
        ext_counts: dict[str, int] = {}
        for filename in self.entries.keys():
            ext = Path(filename).suffix.lower()
            ext_counts[ext] = ext_counts.get(ext, 0) + 1
        
        return {
            "version": self.version,
            "mount_point": self.mount_point,
            "total_files": len(self.entries),
            "total_size": total_size,
            "encrypted": self.encrypted,
            "extensions": ext_counts,
        }


def open_pak(pak_path: str | Path) -> PakFile:
    """Open a pak file and return a PakFile object."""
    pak = PakFile(pak_path)
    pak.open()
    return pak


def list_pak_files(pak_path: str | Path) -> list[str]:
    """List all files in a pak file."""
    with open_pak(pak_path) as pak:
        return pak.list_files()


def extract_pak_file(pak_path: str | Path, filename: str) -> bytes | None:
    """Extract a single file from a pak file."""
    with open_pak(pak_path) as pak:
        return pak.extract_file(filename)
