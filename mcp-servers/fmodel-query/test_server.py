#!/usr/bin/env python3
"""Test script for fmodel-query MCP server."""

import sys
import os

# Add the current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fmodel_query import list_directory, search_files, read_file, get_file_info

def test_list_directory():
    """Test listing directory contents."""
    print("Testing list_directory...")
    result = list_directory("")
    print(result[:500])
    print()

def test_search_files():
    """Test searching files."""
    print("Testing search_files...")
    result = search_files("*.json", "Data")
    print(result[:500])
    print()

def test_get_file_info():
    """Test getting file info."""
    print("Testing get_file_info...")
    result = get_file_info("Data")
    print(result)
    print()

if __name__ == "__main__":
    test_list_directory()
    test_search_files()
    test_get_file_info()
