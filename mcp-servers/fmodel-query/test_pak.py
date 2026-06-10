#!/usr/bin/env python3
"""Test script for pak parser with AES decryption."""

import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pak_parser import open_pak

PAK_DIR = "/mnt/e/soft/Steam/steamapps/common/Dark and Darker/DungeonCrawler/Content/Paks"
AES_KEY_FILE = "/mnt/e/Game/fmod/aes.txt"

def load_aes_key() -> bytes:
    """Load AES key from file."""
    key_hex = Path(AES_KEY_FILE).read_text().strip()
    if key_hex.startswith("0x"):
        key_hex = key_hex[2:]
    return bytes.fromhex(key_hex)

def test_pak_parser():
    """Test pak parser functionality."""
    aes_key = load_aes_key()
    print(f"AES key loaded: {aes_key.hex()[:32]}...")
    
    pak_path = Path(PAK_DIR)
    
    # Find a smaller pak file first
    pak_files = sorted(pak_path.glob("pakchunk304-Windows.pak"))
    if not pak_files:
        print("No pakchunk304-Windows.pak found")
        return
    
    pak_file = pak_files[0]
    print(f"\nTesting with: {pak_file.name}")
    print("=" * 60)
    
    try:
        with open_pak(pak_file, aes_key) as pak:
            print(f"Version: {pak.get_version()}")
            print(f"Mount point: {pak.get_mount_point()}")
            print(f"Encrypted: {pak.encrypted}")
            
            files = pak.list_files()
            print(f"\nTotal files: {len(files)}")
            print("Files:")
            for f in files[:20]:
                info = pak.get_file_info(f)
                print(f"  {f} ({info['size']} bytes)")
            
            # Try to extract a file
            if files:
                print(f"\nExtracting first file: {files[0]}")
                data = pak.extract_file(files[0])
                if data:
                    print(f"Extracted {len(data)} bytes")
                    try:
                        text = data.decode("utf-8", errors="ignore")
                        print(f"Content preview: {text[:200]}")
                    except:
                        print("Binary data")
    
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_pak_parser()
