"""Unreal Engine 5.5 .pak file parser with AES decryption support."""

import struct
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend


class PakFile:
    """Parser for Unreal Engine .pak files (supports UE5.x with AES decryption)."""
    
    MAGIC = 0x5A6F12E1
    
    # Compression methods
    COMPRESSION_NONE = 0
    COMPRESSION_ZLIB = 1
    COMPRESSION_GZIP = 2
    COMPRESSION_OODLE = 3
    COMPRESSION_LZ4 = 4
    
    # Encryption block size (AES uses 16-byte blocks)
    AES_BLOCK_SIZE = 16
    
    def __init__(self, pak_path: str | Path, aes_key: bytes | None = None):
        self.path = Path(pak_path)
        self.file = None
        self.mount_point = ""
        self.entries: dict[str, dict[str, Any]] = {}
        self.version = 0
        self.index_offset = 0
        self.index_size = 0
        self.aes_key = aes_key
        self.encrypted = False
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
    
    def _decrypt_data(self, data: bytes, iv: bytes | None = None) -> bytes:
        """Decrypt data using AES-256-CBC."""
        if not self.aes_key:
            raise ValueError("AES key not provided")
        
        if iv is None:
            # Use default IV (16 bytes of zeros)
            iv = b'\x00' * 16
        
        cipher = Cipher(
            algorithms.AES(self.aes_key),
            modes.CBC(iv),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        
        # Ensure data is multiple of block size
        if len(data) % self.AES_BLOCK_SIZE != 0:
            padding = self.AES_BLOCK_SIZE - (len(data) % self.AES_BLOCK_SIZE)
            data = data + b'\x00' * padding
        
        decrypted = decryptor.update(data) + decryptor.finalize()
        
        # Remove PKCS7 padding if present
        if decrypted:
            pad_len = decrypted[-1]
            if 1 <= pad_len <= self.AES_BLOCK_SIZE:
                if all(b == pad_len for b in decrypted[-pad_len:]):
                    decrypted = decrypted[:-pad_len]
        
        return decrypted
    
    def _parse_index(self):
        """Parse the file index."""
        # If encrypted, we need to decrypt the index first
        if self.encrypted and self.aes_key:
            self._parse_encrypted_index()
        else:
            self._parse_plaintext_index()
    
    def _parse_plaintext_index(self):
        """Parse plaintext index."""
        self.file.seek(self.index_offset)
        
        # Read mount point
        mount_point = self._read_fstring()
        self.mount_point = mount_point
        
        # Read entry count
        entry_count = struct.unpack("<i", self.file.read(4))[0]
        
        # Read entries
        for _ in range(entry_count):
            self._read_entry()
    
    def _parse_encrypted_index(self):
        """Parse encrypted index."""
        # Read the encrypted index data
        self.file.seek(self.index_offset)
        encrypted_data = self.file.read(self.index_size)
        
        # For encrypted index, the first 16 bytes are the IV
        if len(encrypted_data) < 16:
            raise ValueError("Encrypted index too small")
        
        iv = encrypted_data[:16]
        encrypted_index = encrypted_data[16:]
        
        # Decrypt the index
        decrypted_index = self._decrypt_data(encrypted_index, iv)
        
        # Parse the decrypted index
        import io
        index_stream = io.BytesIO(decrypted_index)
        
        # Read mount point
        mount_point = self._read_fstring_from_stream(index_stream)
        self.mount_point = mount_point
        
        # Read entry count
        entry_count = struct.unpack("<i", index_stream.read(4))[0]
        
        # Read entries
        for _ in range(entry_count):
            self._read_entry_from_stream(index_stream)
    
    def _read_fstring_from_stream(self, stream) -> str:
        """Read an FString from a stream."""
        length = struct.unpack("<i", stream.read(4))[0]
        
        if length < 0:
            char_count = -length
            data = stream.read(char_count * 2)
            return data.decode("utf-16-le").rstrip("\x00")
        else:
            data = stream.read(length)
            return data.decode("utf-8", errors="replace").rstrip("\x00")
    
    def _read_entry_from_stream(self, stream):
        """Read a single index entry from a stream."""
        filename = self._read_fstring_from_stream(stream)
        
        offset = struct.unpack("<q", stream.read(8))[0]
        size = struct.unpack("<q", stream.read(8))[0]
        raw_offset = struct.unpack("<q", stream.read(8))[0]
        raw_size = struct.unpack("<q", stream.read(8))[0]
        compressed_size = struct.unpack("<q", stream.read(8))[0]
        sha1 = stream.read(20)
        flags = struct.unpack("<B", stream.read(1))[0]
        
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
        length = struct.unpack("<i", self.file.read(4))[0]
        
        if length < 0:
            char_count = -length
            data = self.file.read(char_count * 2)
            return data.decode("utf-16-le").rstrip("\x00")
        else:
            data = self.file.read(length)
            return data.decode("utf-8", errors="replace").rstrip("\x00")
    
    def _read_entry(self):
        """Read a single index entry."""
        filename = self._read_fstring()
        
        offset = struct.unpack("<q", self.file.read(8))[0]
        size = struct.unpack("<q", self.file.read(8))[0]
        raw_offset = struct.unpack("<q", self.file.read(8))[0]
        raw_size = struct.unpack("<q", self.file.read(8))[0]
        compressed_size = struct.unpack("<q", self.file.read(8))[0]
        sha1 = self.file.read(20)
        flags = struct.unpack("<B", self.file.read(1))[0]
        
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
        
        # Handle encrypted file data
        if entry["encrypted"] and self.aes_key:
            return self._extract_encrypted_file(entry)
        else:
            return self._extract_plaintext_file(entry)
    
    def _extract_plaintext_file(self, entry: dict) -> bytes:
        """Extract a plaintext file."""
        self.file.seek(entry["offset"])
        data = self.file.read(entry["size"])
        return data
    
    def _extract_encrypted_file(self, entry: dict) -> bytes:
        """Extract an encrypted file."""
        self.file.seek(entry["offset"])
        encrypted_data = self.file.read(entry["size"])
        
        # For encrypted files, the first 16 bytes are the IV
        if len(encrypted_data) < 16:
            return encrypted_data
        
        iv = encrypted_data[:16]
        encrypted_content = encrypted_data[16:]
        
        decrypted = self._decrypt_data(encrypted_content, iv)
        return decrypted
    
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


def open_pak(pak_path: str | Path, aes_key: bytes | None = None) -> PakFile:
    """Open a pak file and return a PakFile object."""
    pak = PakFile(pak_path, aes_key)
    pak.open()
    return pak


def list_pak_files(pak_path: str | Path, aes_key: bytes | None = None) -> list[str]:
    """List all files in a pak file."""
    with open_pak(pak_path, aes_key) as pak:
        return pak.list_files()


def extract_pak_file(pak_path: str | Path, filename: str, aes_key: bytes | None = None) -> bytes | None:
    """Extract a single file from a pak file."""
    with open_pak(pak_path, aes_key) as pak:
        return pak.extract_file(filename)
