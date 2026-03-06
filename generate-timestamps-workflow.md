# ElevenLabs Scribe STT — Word-Level Timestamps 流程文檔

> **目的：** 將 `4_previewGen/final/` 中所有故事的 MP3 音檔，透過 ElevenLabs Scribe v2 API 反推 word-level timestamps，供 Preview Tool 的逐字同步 (karaoke) 功能使用。
> **腳本位置：** `AI_workflow/generate_timestamps.py`
> **適用範圍：** 所有故事 × 所有語言（EN / ZH-TW / JA）× 所有版本（standard / toddler）

---

## 日常維護速查

```bash
cd /Users/stacywang/Desktop/Piyo/AI_workflow

# 盤點覆蓋率（不呼叫 API）
python3 generate_timestamps.py --audit

# 補齊缺失的 timestamps
python3 generate_timestamps.py --skip-existing --yes

# 強制重建全部（覆蓋已存在的 JSON）
python3 generate_timestamps.py --force --yes

# 只處理特定故事
python3 generate_timestamps.py --folder 4_previewGen/final/故事名稱 --force --yes

# 產生完後重建 stories.json
python3 4_previewGen/build.py
```

---

## 一、環境準備

### 1.1 前提條件

- Python 3.9+
- ElevenLabs API key（需有 `speech_to_text` 權限）
- `pip install elevenlabs`

### 1.2 環境變數

```bash
export ELEVENLABS_API_KEY="sk_..."
# 建議加入 ~/.zshrc 持久化
```

---

## 二、資料夾結構

腳本自動掃描 `4_previewGen/final/` 下所有故事子資料夾：

```
4_previewGen/final/
├── three-little-pigs/
│   ├── EN/standard/    ← P01_v1.mp3 + P01_v1.json
│   ├── EN/toddler/
│   ├── ZH-TW/standard/
│   ├── ZH-TW/toddler/
│   ├── JA/standard/
│   └── JA/toddler/
├── goldilocks-and-the-three-bears/
│   └── ...（同上結構）
└── the-tortoise-and-the-hare/
    └── ...
```

**命名規則：** `P01_v1.mp3` → `P01_v1.json`（同名同目錄，一對一對應）
也支援不含版本號：`P01.mp3` → `P01.json`

---

## 三、JSON 格式

```json
{
  "source_file": "P01_v1.mp3",
  "language": "EN",
  "version": "standard",
  "page": "P01",
  "variant": "v1",
  "generated_at": "2026-03-06T05:32:20Z",
  "words": [
    { "word": "Once", "start": 0.00, "end": 0.35, "type": "word" },
    { "word": "upon", "start": 0.38, "end": 0.58, "type": "word" }
  ]
}
```

> **重要設計原則：**
> - timestamps 的 `word` 欄位**僅用於時間對齊**，不用於畫面顯示
> - 前端 karaoke 的**顯示文字永遠來自 `page.text`**（pages.json → build.py → stories.json）
> - 這避免了 ElevenLabs Scribe 對 CJK 語言可能回傳簡體中文的問題

---

## 四、腳本功能

| 參數 | 說明 |
|------|------|
| `--audit` | 盤點所有故事的 timestamps 覆蓋率（表格式摘要） |
| `--dry-run` | 列出會處理的檔案清單（不呼叫 API） |
| `--skip-existing` | 跳過已有有效 `words` 格式 JSON 的檔案 |
| `--force` | 強制覆蓋已存在的 JSON（修復格式不符等問題） |
| `--folder PATH` | 只處理指定資料夾（支援相對路徑） |
| `--yes`, `-y` | 跳過確認直接執行 |

**格式驗證：** `--audit` 和 `--skip-existing` 都會檢查 JSON 是否包含有效的 `"words"` 陣列，而非僅檢查檔案是否存在。這能正確識別舊的 TTS alignment 格式（`{"alignment":...}`）為「格式不符」。

---

## 五、注意事項

### 5.1 CJK 語言（ZH-TW、JA）

- ElevenLabs Scribe API 不區分繁體/簡體中文（`language_code="zh"`）
- Scribe 回傳的 `word` 欄位可能是簡體中文
- **前端已處理此問題**：karaoke 引擎使用 `page.text` 作為顯示文字，timestamps 僅提供時間軸

### 5.2 費用

- ElevenLabs Scribe 定價：$0.40 / 小時
- 一個故事（3 語言 × 2 版本 × ~13 頁）約 $0.05-0.15 USD

### 5.3 API Key 權限

API key 必須有 `speech_to_text` 權限，可在 [ElevenLabs Dashboard](https://elevenlabs.io/app/settings/api-keys) 設定。

---

## 六、系統架構

```
generate_timestamps.py   →  產生 per-MP3 的 .json（words 格式）
        ↓
build.py                 →  掃描 .json，整合進 stories.json
        ↓
index.html               →  讀取 stories.json，驅動 karaoke 引擎
                             顯示文字 = page.text
                             時間軸 = timestamps[].{start, end}
```

三個系統完全解耦，各自負責單一職責。
