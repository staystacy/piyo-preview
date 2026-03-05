# Piyo Preview Tool

Internal preview player for JOJO Math audio picture books. Review images, videos, audio narration, subtitles, and word-level synchronization — all in one browser page.

## Quick Start

```bash
cd /Users/stacywang/Desktop/Piyo/AI_workflow/4_previewGen
python3 -m http.server 8080
# Open http://localhost:8080
```

## Regenerate stories.json

After adding or updating resources in `final/`:

```bash
python3 build.py
```

## Daily Operations

| Task | How |
|------|-----|
| Replace an image | Drop new `P03.png` into `final/{story}/media/` → `python3 build.py` |
| Replace a video | Drop new `P03.mp4` into `final/{story}/media/` → `python3 build.py` |
| Image → Video | Delete `P03.png`, add `P03.mp4` → `python3 build.py` |
| Replace audio | Drop new `P03.mp3` into the language/version folder → `python3 build.py` |
| Edit subtitles | Edit `pages.json`, modify the `text` field → `python3 build.py` |
| Add timestamps | Create/update `timestamps.json` → `python3 build.py` |
| Add a page | Add media + audio + update `pages.json` → `python3 build.py` |
| Add a story | Create new folder with `meta.json` → add resources → `python3 build.py` |
| Add a language | Add language subfolder (e.g. `KO/`) → add resources → `python3 build.py` |

## Add a New Story

```bash
# 1. Create folder structure
mkdir -p final/new-story/{media,EN/{standard,toddler},ZH-TW/{standard,toddler},JA/{standard,toddler}}

# 2. Create meta.json
cat > final/new-story/meta.json << 'EOF'
{
  "id": "new-story",
  "title": { "EN": "New Story", "ZH-TW": "新故事", "JA": "新しい物語" },
  "coverPage": "P01"
}
EOF

# 3. Add media, audio, and pages.json files

# 4. Rebuild
python3 build.py
```

## Deploy to GitHub Pages

```bash
git add .
git commit -m "update preview resources"
git push

# GitHub Settings → Pages → set root directory
# For large media files, enable Git LFS:
git lfs track "*.mp3" "*.mp4" "*.png"
```

## ElevenLabs Timestamps

Add `alignment` parameter when calling ElevenLabs API to get word-level timing data. Convert the alignment output to `timestamps.json` format:

```json
[
  {
    "page": "P01",
    "words": [
      { "word": "Once", "start": 0.00, "end": 0.35 },
      { "word": "upon", "start": 0.35, "end": 0.58 }
    ]
  }
]
```

Place `timestamps.json` in the same folder as `pages.json`. The player automatically enables karaoke mode when timestamps are available.
