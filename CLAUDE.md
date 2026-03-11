# 4_previewGen — Preview Player & Build Pipeline

Single-page vanilla JS app (`index.html`, 1215 lines) + Python build script (`build.py`, 222 lines).
Zero external dependencies. Server: `python3 -m http.server 8080`.

## final/ Directory Schema (Source of Truth)

```
final/{story-slug}/
├── meta.json                           ← Story metadata
├── media/P{NN}.{png|mp4}              ← Visual assets (shared across all languages)
└── {EN|ZH-TW|JA}/
    └── {standard|toddler}/
        ├── pages.json                  ← Text content per page
        ├── P{NN}_v{N}.mp3             ← Audio narration (versioned)
        └── P{NN}_v{N}.json            ← Word-level timestamps (same stem as MP3)
```

### meta.json

```json
{
  "id": "three-little-pigs",
  "title": { "EN": "The Three Little Pigs", "ZH-TW": "三隻小豬", "JA": "三匹の子ぶた" },
  "coverPage": "P01",
  "mediaMapping": {
    "toddler": { "P03": "P05", "P04": "P07" }
  }
}
```

`mediaMapping`: Toddler versions reuse standard media. Key = toddler page ID, Value = standard media page ID.

### pages.json

```json
[{ "page": "P01", "text": "Story text with\nnewlines for line breaks." }]
```

### Timestamp JSON (per-MP3, e.g. P01_v1.json)

```json
{
  "source_file": "P01_v1.mp3",
  "words": [{ "word": "Once", "start": 0.299, "end": 1.059, "type": "word" }]
}
```

## build.py Behavior

1. Scans `final/` for story directories (alphabetical order)
2. Per story: reads `meta.json`, scans `media/` for PNG/MP4
3. Discovers languages (`EN`, `ZH-TW`, `JA`) and versions (`standard`, `toddler`)
4. Per language/version: loads `pages.json`, scans MP3 audio (versioned: `P01_v2.mp3` beats `P01_v1.mp3`), scans timestamp JSONs
5. Applies `mediaMapping` to resolve which media file each page uses
6. Writes `data/stories.json` with `generatedAt` timestamp

### stories.json Page Object (consumed by index.html)

```json
{
  "page": "P01",
  "mediaType": "video",
  "media": "final/three-little-pigs/media/P01.mp4",
  "audio": "final/three-little-pigs/EN/standard/P01_v1.mp3",
  "text": "Biggie, Woody, and Bricky were three little pig brothers.",
  "timestamps": [{ "word": "Biggie,", "start": 0.299, "end": 1.059, "type": "word" }]
}
```

## index.html Code Map

| Lines | Section | Key Functions |
|---|---|---|
| 1-415 | HTML + CSS | Styles, layout, responsive breakpoints |
| 14-45 | CSS: Reset & base | CSS custom properties (--bg, --accent, --font-*) |
| 47-83 | CSS: Welcome overlay | Start button, fade transition |
| 85-178 | CSS: Header + dropdowns | Custom dropdown component styles |
| 180-230 | CSS: Auto-play toggle | Switch component |
| 232-316 | CSS: Player card + media | 3:2 aspect ratio container, nav arrows |
| 318-367 | CSS: Subtitle + karaoke | `.word`, `.word.spoken`, `.word.active` styles |
| 369-401 | CSS: Progress bar | Footer progress track |
| 404-414 | CSS: Responsive | @media max-width 768px adjustments |
| 416-472 | HTML body | DOM structure (overlay, header, player, progress, audio) |
| 474-524 | JS: App state + data loader | `state` object, `loadData()` |
| 526-653 | JS: Dropdown controller | `setupDropdown()`, `initDropdowns()`, `updateDropdowns()` |
| 655-668 | JS: Page data helpers | `getCurrentPages()`, `getCurrentPage()` |
| 670-719 | JS: Page renderer | `renderPage()` — main render orchestrator |
| 721-743 | JS: Media renderer | `renderMedia()` — image/video display |
| 745-902 | JS: CJK karaoke engine | `isCJKContent()`, `normalizeKana()`, `buildAnchorMapping()`, `renderCJKKaraoke()` |
| 904-972 | JS: EN karaoke engine | `renderENKaraoke()` — fuzzy word matching + lookahead |
| 974-989 | JS: Subtitle dispatcher | `renderSubtitle()` — routes to CJK or EN karaoke |
| 991-1036 | JS: Audio controller | `playAudio()`, `stopAudio()`, auto-advance on ended (1.5s delay) |
| 1038-1110 | JS: Karaoke timing engine | `startKaraoke()` — requestAnimationFrame loop, gap bridging |
| 1112-1163 | JS: Navigation | `goPrev()`, `goNext()`, keyboard arrows, progress bar click |
| 1165-1179 | JS: Selection change | `onSelectionChange()` — validates lang/version, re-renders |
| 1181-1215 | JS: Welcome + init | Welcome overlay handler, `init()` entry point |

## Karaoke Engine Design

### Critical Rule
Display text ALWAYS comes from `page.text` (via `pages.json` → `build.py` → `stories.json`).
Timestamps are ONLY used for timing alignment, never for display.
Reason: ElevenLabs Scribe STT may return simplified Chinese for ZH-TW content.

### EN Karaoke (lines 904-972)
- Splits `page.text` by whitespace into display words
- Matches each display word to timestamp words using fuzzy matching:
  - `norm()`: strips non-alphanumeric, lowercases
  - Prefix match (first 3 chars) for spelling differences
  - Lookahead: one display word can consume multiple timestamp words (e.g., "AAAH!" ← ["Ah,", "ah,", "ah!"])
- Pure punctuation tokens ("——", "......") get `data-punct="1"`, inherit previous word's timing

### CJK Karaoke (lines 745-902)
- Extracts CJK content chars from both `page.text` and `timestamps`
- Two mapping strategies:
  - **Proportional** (default, ZH-TW): When M (timestamp chars) = N (text chars), maps 1:1
  - **Anchor-based** (JA when M != N): `buildAnchorMapping()` uses dual-pointer matching with `normalizeKana()` (katakana→hiragana, offset -0x60), then interpolates between anchors
- Punctuation: inherits timing from preceding content char, gets `data-punct="1"`

### Karaoke Timing Engine (lines 1038-1110)
- Uses `requestAnimationFrame` synced to `audioPlayer.currentTime`
- **Gap bridging**: extends each word's end time to next word's start, preventing flicker
- CSS classes: `.word` (unspoken, #D2C4AD) → `.word.spoken` (accent color) → `.word.active` (inverted, white on accent bg)
- Punctuation: only gets `.spoken` class, never `.active` (no background highlight)
- Color transitions: 0.25s CSS ease

## CSS Design Tokens

```
--bg: #FAF7F2          (cream background)
--accent: #8B6F47      (warm brown, primary action color)
--text-primary: #2C2C2C
--unspoken: #CCCCCC
--font-en: 'Lora'
--font-zh: 'LXGW WenKai TC'
--font-ja: 'Noto Serif JP'
--font-title: 'Cormorant Garamond'
--font-ui: 'Inter'
```

Media container: 3:2 aspect ratio, max 860px wide, centered within 960px content area.

## Common Operations

| Task | Command |
|---|---|
| Rebuild after resource change | `python3 build.py` |
| Preview locally | `python3 -m http.server 8080` |
| Add timestamps for new audio | `cd .. && python3 generate_timestamps.py --skip-existing --yes && cd 4_previewGen && python3 build.py` |
| Audit timestamp coverage | `cd .. && python3 generate_timestamps.py --audit` |

<!-- Last verified: 2026-03-11. Key staleness indicators:
     - index.html line count changed (currently 1215)
     - New CSS sections or JS functions added
     - build.py behavior changed -->
