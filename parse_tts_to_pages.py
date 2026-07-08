#!/usr/bin/env python3
"""
Parse TTS script MD files and generate pages.json for each story/language/version.
Strips all [tag] markers and extracts pure text from code blocks.
"""

import re
import json
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TTS_DIR = os.path.join(SCRIPT_DIR, "..", "tts_gen", "tts_scripts")
FINAL_DIR = os.path.join(SCRIPT_DIR, "final")

# Mapping: filename prefix -> final/ folder language code
LANG_MAP = {
    "11_TTS_script_TC": "ZH-TW",
    "12_TTS_script_EN": "EN-US",
    "13_TTS_script_JP": "JA",
}

STORIES = ["三隻小豬", "金髮女孩與三隻熊", "龜兔賽跑"]


def strip_tags(text: str) -> str:
    """Remove all [tag] markers from text."""
    return re.sub(r'\[.*?\]', '', text)


def clean_line(line: str) -> str:
    """Strip tags and whitespace from a single line."""
    cleaned = strip_tags(line).strip()
    return cleaned


def extract_pages_from_md(md_content: str):
    """
    Extract standard and toddler pages from a TTS script MD file.
    Returns (standard_pages, toddler_pages) where each is a list of text strings.
    """
    # Split into lines
    lines = md_content.split('\n')

    # Find code blocks and their section context
    standard_pages = []
    toddler_pages = []

    in_code_block = False
    current_block_lines = []
    current_section = None  # 'standard' or 'toddler'

    for line in lines:
        # Detect section headers
        # Standard version markers (EN/TC/JP)
        if re.match(r'^#\s*(Standard Version|標準版|スタンダード版)', line):
            current_section = 'standard'
            continue
        # Toddler version markers (EN/TC/JP)
        if re.match(r'^#\s*(Toddler Version|幼幼版|よちよち版)', line):
            current_section = 'toddler'
            continue
        # Appendix markers - stop processing
        if re.match(r'^#\s*(Appendix|附錄|付録)', line):
            current_section = None
            continue

        # Handle code blocks
        if line.strip() == '```':
            if in_code_block:
                # End of code block - process it
                if current_section in ('standard', 'toddler'):
                    # Clean lines: strip tags, remove empty lines
                    cleaned = []
                    for bl in current_block_lines:
                        cl = clean_line(bl)
                        if cl:  # skip empty lines
                            cleaned.append(cl)
                    if cleaned:
                        page_text = '\n'.join(cleaned)
                        if current_section == 'standard':
                            standard_pages.append(page_text)
                        else:
                            toddler_pages.append(page_text)
                current_block_lines = []
                in_code_block = False
            else:
                # Start of code block
                in_code_block = True
                current_block_lines = []
            continue

        if in_code_block:
            current_block_lines.append(line)

    return standard_pages, toddler_pages


def build_pages_json(pages: list) -> list:
    """Build the pages.json structure.
    Bare list format — this is what build.py iterates and what shipped
    pages.json files use. Do not wrap in a metadata dict."""
    return [
        {
            "page": f"P{i+1:02d}",
            "text": text
        }
        for i, text in enumerate(pages)
    ]


def main():
    total_written = 0

    for story in STORIES:
        for prefix, folder_lang in LANG_MAP.items():
            filename = f"{prefix}_{story}.md"
            filepath = os.path.join(TTS_DIR, filename)

            if not os.path.exists(filepath):
                print(f"WARNING: File not found: {filepath}")
                continue

            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            standard_pages, toddler_pages = extract_pages_from_md(content)

            # Write standard pages.json
            std_json = build_pages_json(standard_pages)
            std_path = os.path.join(FINAL_DIR, story, folder_lang, "3-5", "pages.json")
            os.makedirs(os.path.dirname(std_path), exist_ok=True)
            with open(std_path, 'w', encoding='utf-8') as f:
                json.dump(std_json, f, ensure_ascii=False, indent=2)
            print(f"OK: {std_path} ({len(standard_pages)} pages)")
            total_written += 1

            # Write toddler pages.json
            tod_json = build_pages_json(toddler_pages)
            tod_path = os.path.join(FINAL_DIR, story, folder_lang, "2-3", "pages.json")
            os.makedirs(os.path.dirname(tod_path), exist_ok=True)
            with open(tod_path, 'w', encoding='utf-8') as f:
                json.dump(tod_json, f, ensure_ascii=False, indent=2)
            print(f"OK: {tod_path} ({len(toddler_pages)} pages)")
            total_written += 1

    print(f"\nDone! {total_written} pages.json files written.")


if __name__ == "__main__":
    main()
