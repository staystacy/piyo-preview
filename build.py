#!/usr/bin/env python3
"""
Piyo Preview Tool — build.py
Scans final/ directory and generates data/stories.json for the preview player.
Zero dependencies — uses only Python standard library.
"""

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
FINAL_DIR = SCRIPT_DIR / "final"
OUTPUT_DIR = SCRIPT_DIR / "data"
OUTPUT_FILE = OUTPUT_DIR / "stories.json"

# Known language folders
KNOWN_LANGUAGES = {"EN", "ZH-TW", "JA"}
# Known version folders
KNOWN_VERSIONS = {"standard", "toddler"}
# Page number patterns
PAGE_PATTERN = re.compile(r"^P(\d+)$")
# Audio files may have version suffix: P01.mp3, P01_v1.mp3, P01_v2.mp3
AUDIO_PATTERN = re.compile(r"^(P\d+)(?:_v\d+)?$")


def scan_media(media_dir: Path) -> dict:
    """Scan media/ folder and return {page_id: {mediaType, path}}."""
    media_map = {}
    if not media_dir.is_dir():
        return media_map
    for f in sorted(media_dir.iterdir()):
        if not f.is_file():
            continue
        stem = f.stem  # e.g. "P01"
        ext = f.suffix.lower()  # e.g. ".png"
        if not PAGE_PATTERN.match(stem):
            continue
        if ext == ".png":
            media_map[stem] = {"mediaType": "image", "path": str(f.relative_to(SCRIPT_DIR))}
        elif ext == ".mp4":
            media_map[stem] = {"mediaType": "video", "path": str(f.relative_to(SCRIPT_DIR))}
    return media_map


def scan_audio(version_dir: Path) -> dict:
    """Scan a version folder for .mp3 files. Return {page_id: relative_path}.
    Supports versioned filenames like P01_v1.mp3, P02_v4.mp3.
    If multiple versions exist for the same page, keeps the last (sorted) one.
    """
    audio_map = {}
    if not version_dir.is_dir():
        return audio_map
    for f in sorted(version_dir.iterdir()):
        if not (f.is_file() and f.suffix.lower() == ".mp3"):
            continue
        m = AUDIO_PATTERN.match(f.stem)
        if m:
            page_id = m.group(1)  # e.g. "P01"
            audio_map[page_id] = str(f.relative_to(SCRIPT_DIR))
    return audio_map


def load_json(filepath: Path):
    """Load a JSON file, return None if not found."""
    if not filepath.is_file():
        return None
    with open(filepath, "r", encoding="utf-8") as fh:
        return json.load(fh)


def build_story(story_dir: Path) -> dict:
    """Build a single story entry."""
    story_slug = story_dir.name

    # Read meta.json
    meta = load_json(story_dir / "meta.json")
    if meta:
        story_id = meta.get("id", story_slug)
        title = meta.get("title", {})
    else:
        story_id = story_slug
        title = {"EN": story_slug}
        print(f"  WARNING: No meta.json, using folder name as title")

    # Scan media
    media_map = scan_media(story_dir / "media")

    # Discover languages and versions
    languages = sorted(
        d.name for d in story_dir.iterdir()
        if d.is_dir() and d.name in KNOWN_LANGUAGES
    )
    # Collect all versions across languages
    all_versions = set()
    for lang in languages:
        lang_dir = story_dir / lang
        for d in lang_dir.iterdir():
            if d.is_dir() and d.name in KNOWN_VERSIONS:
                all_versions.add(d.name)
    versions = sorted(all_versions)

    # Build pages per language/version
    pages = {}
    total_pages = 0
    for lang in languages:
        pages[lang] = {}
        for version in versions:
            version_dir = story_dir / lang / version
            if not version_dir.is_dir():
                pages[lang][version] = []
                continue

            # Load text
            pages_json = load_json(version_dir / "pages.json")
            if pages_json is None:
                pages[lang][version] = []
                continue

            # Load timestamps (optional)
            timestamps_json = load_json(version_dir / "timestamps.json")
            timestamps_map = {}
            if timestamps_json and isinstance(timestamps_json, list):
                for entry in timestamps_json:
                    page_id = entry.get("page")
                    if page_id:
                        timestamps_map[page_id] = entry.get("words")

            # Scan audio
            audio_map = scan_audio(version_dir)

            # Combine per page
            page_list = []
            for page_entry in pages_json:
                page_id = page_entry.get("page")
                if not page_id:
                    continue
                media_info = media_map.get(page_id)
                page_data = {
                    "page": page_id,
                    "mediaType": media_info["mediaType"] if media_info else None,
                    "media": media_info["path"] if media_info else None,
                    "audio": audio_map.get(page_id),
                    "text": page_entry.get("text"),
                    "timestamps": timestamps_map.get(page_id),
                }
                page_list.append(page_data)

            pages[lang][version] = page_list
            total_pages += len(page_list)

    print(f"  {story_id}: {len(languages)} languages, {len(versions)} versions, {total_pages} total page entries")

    return {
        "id": story_id,
        "title": title,
        "languages": languages,
        "versions": versions,
        "pages": pages,
    }


def main():
    print("Piyo Preview Tool — build.py")
    print(f"Scanning: {FINAL_DIR}")
    print()

    if not FINAL_DIR.is_dir():
        print(f"ERROR: {FINAL_DIR} not found")
        return

    # Discover stories
    story_dirs = sorted(
        d for d in FINAL_DIR.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    )

    if not story_dirs:
        print("No stories found in final/")
        return

    print(f"Found {len(story_dirs)} stories:")
    stories = []
    for story_dir in story_dirs:
        story = build_story(story_dir)
        stories.append(story)

    # Write output
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output = {
        "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "stories": stories,
    }
    with open(OUTPUT_FILE, "w", encoding="utf-8") as fh:
        json.dump(output, fh, ensure_ascii=False, indent=2)

    print()
    print(f"Output: {OUTPUT_FILE}")
    print(f"Stories: {len(stories)}")
    print("Done!")


if __name__ == "__main__":
    main()
