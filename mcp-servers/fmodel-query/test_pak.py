#!/usr/bin/env python3
"""Test script for pak parser."""

import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pak_parser import open_pak

PAK_DIR = "/mnt/e/soft/Steam/steamapps/common/Dark and Darker/DungeonCrawler/Content/Paks"

def test_pak_parser():
    """Test pak parser functionality."""
    pak_path = Path(PAK_DIR)
    
    # Find the first pak file
    pak_files = list(pak_path.glob("pakchunk0-Windows.pak"))
    if not pak_files:
        print("No pakchunk0-Windows.pak found")
        return
    
    pak_file = pak_files[0]
    print(f"Testing with: {pak_file.name}")
    print("=" * 60)
    
    try:
        with open_pak(pak_file) as pak:
            # Get version
            print(f"Version: {pak.get_version()}")
            
            # Get mount point
            print(f"Mount point: {pak.get_mount_point()}")
            
            # List files (first 20)
            files = pak.list_files()
            print(f"\nTotal files: {len(files)}")
            print("First 20 files:")
            for f in files[:20]:
                print(f"  {f}")
            
            # Search for JSON files
            json_files = pak.search_files("*.json")
            print(f"\nJSON files: {len(json_files)}")
            if json_files:
                print("First 10 JSON files:")
                for f in json_files[:10]:
                    print(f"  {f}")
            
            # Get stats
            stats = pak.get_stats()
            print(f"\nStats:")
            print(f"  Total size: {stats['total_size'] / (1024*1024):.1f} MB")
            print(f"  Encrypted: {stats['encrypted']}")
            
            # Show top extensions
            print("\nTop file types:")
            for ext, count in sorted(stats["extensions"].items(), key=lambda x: -x[1])[:10]:
                print(f"  {ext or '(no ext)'}: {count}")
    
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_pak_parser()
