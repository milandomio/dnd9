"""
DarkFindV5 Backend
Reads raw JSON files, cleans/transforms data,
and outputs backend JSON data files for the frontend.
"""

import json
import sys
from pathlib import Path

from config import DATA_DIR, OUTPUT_DIR


def load_json_files(data_dir: Path) -> list[dict]:
    files = sorted(data_dir.glob("**/*.json"))
    if not files:
        print(f"[WARN] No JSON files found in {data_dir}")
        return []
    data = []
    for fp in files:
        try:
            with open(fp, "r", encoding="utf-8") as f:
                data.append(json.load(f))
        except Exception as e:
            print(f"[ERROR] Failed to load {fp}: {e}")
    print(f"[INFO] Loaded {len(data)} JSON files from {data_dir}")
    return data


def clean_data(raw: list[dict]) -> list[dict]:
    return raw


def save_json(data: list[dict], filename: str):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[INFO] Saved {len(data)} records to {path}")


def main():
    print("=" * 50)
    print("  DarkFindV5 Backend - Data Pipeline")
    print("=" * 50)
    raw = load_json_files(DATA_DIR)
    cleaned = clean_data(raw)
    save_json(cleaned, "data.json")
    print("[DONE] Backend processing complete.")


if __name__ == "__main__":
    main()
