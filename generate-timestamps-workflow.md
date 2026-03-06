# ElevenLabs Scribe STT — 批次產生 Word-Level Timestamps 流程文檔

> **目的：** 將現有 MP3 音檔透過 ElevenLabs Scribe v2 API 反推 word-level timestamps，產出 `timestamps.json` 供有聲繪本 Preview Tool 的逐字同步功能使用。  
> **適用範圍：** 三隻小豬故事的所有語言（EN / ZH-TW / JA）× 所有版本（standard / toddler）× 所有音檔變體（v1, v2, v3...）

---

## 一、環境準備

### 1.1 前提條件

- Python 3.9+
- ElevenLabs API key 已設定為環境變數

### 1.2 確認環境變數

```bash
# 確認 API key 已設定
echo $ELEVENLABS_API_KEY
# 應該要看到 sk_xxxxx... 開頭的字串
```

若尚未設定，加入你的 shell 設定檔（`~/.zshrc` 或 `~/.bash_profile`）：

```bash
export ELEVENLABS_API_KEY="你的API金鑰"
source ~/.zshrc
```

### 1.3 安裝依賴

```bash
pip install elevenlabs
```

僅需這一個套件，無其他依賴。

---

## 二、目標資料夾結構

### 2.1 資料夾 A — TTS 產出區（3_ttsGen）

```
3_ttsGen/output_tts/三隻小豬/
├── EN/
│   ├── standard/
│   │   ├── P01_v1.mp3
│   │   ├── P02_v4.mp3      ← 同一頁可能有多個版本
│   │   ├── P03_v2.mp3
│   │   ├── P03_v3.mp3
│   │   ├── P03_v4.mp3
│   │   └── ...
│   └── toddler/
│       └── ...
├── ZH-TW/
│   ├── standard/
│   └── toddler/
└── JA/
    ├── standard/
    └── toddler/
```

### 2.2 資料夾 B — Preview 定稿區（4_previewGen）

```
4_previewGen/final/three-little-pigs/
├── EN/
│   ├── standard/
│   │   ├── P01_v1.mp3
│   │   ├── P02_v1.mp3
│   │   └── ...
│   └── toddler/
│       └── ...
├── ZH-TW/
│   ├── standard/
│   └── toddler/
└── JA/
    ├── standard/
    └── toddler/
```

### 2.3 共通特徵

- 檔名格式：`P{NN}_v{N}.mp3`（如 `P01_v1.mp3`、`P03_v4.mp3`）
- 每個 MP3 都要產生對應的 timestamps
- 語言子資料夾：`EN`、`ZH-TW`、`JA`
- 版本子資料夾：`standard`、`toddler`

---

## 三、產出格式

### 3.1 timestamps 存放位置

腳本會在**每個 MP3 所在的同一資料夾**內產生同名的 `.json` 檔案：

```
EN/standard/
├── P01_v1.mp3
├── P01_v1.json    ← 新產生（與 MP3 同名，僅副檔名不同）
├── P03_v2.mp3
├── P03_v2.json    ← 新產生
├── P03_v3.mp3
├── P03_v3.json    ← 新產生
└── ...
```

> **命名規則：** `P01_v1.mp3` → `P01_v1.json`，一對一對應，放在同一資料夾。

### 3.2 單一 JSON 檔案格式

每個 `.json` 的內容：

```json
{
  "source_file": "P01_v1.mp3",
  "language": "EN",
  "version": "standard",
  "page": "P01",
  "variant": "v1",
  "generated_at": "2025-06-01T14:30:00Z",
  "words": [
    {
      "word": "Once",
      "start": 0.00,
      "end": 0.35,
      "type": "word"
    },
    {
      "word": "upon",
      "start": 0.38,
      "end": 0.58,
      "type": "word"
    },
    {
      "word": "a",
      "start": 0.60,
      "end": 0.65,
      "type": "word"
    },
    {
      "word": "time,",
      "start": 0.67,
      "end": 1.02,
      "type": "word"
    }
  ]
}
```

**欄位說明：**

| 欄位 | 說明 |
|------|------|
| `source_file` | 原始 MP3 檔名 |
| `language` | 從資料夾路徑推斷（EN / ZH-TW / JA） |
| `version` | 從資料夾路徑推斷（standard / toddler） |
| `page` | 從檔名解析（P01, P02...） |
| `variant` | 從檔名解析（v1, v2, v3...） |
| `words[].word` | 辨識出的文字 |
| `words[].start` | 該詞開始時間（秒） |
| `words[].end` | 該詞結束時間（秒） |
| `words[].type` | ElevenLabs 回傳的類型（`word` / `spacing`） |

> **中文與日文注意事項：**  
> ElevenLabs Scribe 對不使用空格的語言（中文、日文）會自動分詞。  
> 中文會以「詞」為單位，日文以「文節」為單位。  
> `spacing` 類型的元素在這些語言中不會出現，腳本會自動過濾。

---

## 四、腳本：`generate_timestamps.py`

### 4.1 存放位置

```
/Users/stacywang/Desktop/Piyo/AI_workflow/generate_timestamps.py
```

放在 `AI_workflow/` 根目錄，方便同時處理兩個子資料夾。

### 4.2 完整腳本

```python
#!/usr/bin/env python3
"""
ElevenLabs Scribe STT — 批次產生 word-level timestamps

用法：
  python3 generate_timestamps.py [--dry-run] [--skip-existing] [--folder FOLDER]

範例：
  # 處理所有目標資料夾
  python3 generate_timestamps.py

  # 只掃描不呼叫 API（預覽會處理哪些檔案）
  python3 generate_timestamps.py --dry-run

  # 跳過已有 timestamps 的檔案
  python3 generate_timestamps.py --skip-existing

  # 只處理特定資料夾
  python3 generate_timestamps.py --folder /path/to/folder
"""

import os
import json
import re
import sys
import time
import argparse
from pathlib import Path
from datetime import datetime, timezone

# ─── 設定區 ───────────────────────────────────────────────

# 目標資料夾（可包含多個）
TARGET_FOLDERS = [
    Path("/Users/stacywang/Desktop/Piyo/AI_workflow/3_ttsGen/output_tts/三隻小豬"),
    Path("/Users/stacywang/Desktop/Piyo/AI_workflow/4_previewGen/final/three-little-pigs"),
]

# 語言代碼 → ElevenLabs language_code 對照
LANG_MAP = {
    "EN":    "en",
    "ZH-TW": "zh",
    "JA":    "ja",
}

# 支援的版本資料夾
VERSIONS = {"standard", "toddler"}

# MP3 檔名格式：P01_v1.mp3
MP3_PATTERN = re.compile(r"^(P\d{2})_(v\d+)\.mp3$")

# API 呼叫間隔（秒），避免 rate limit
API_DELAY = 1.0

# ─── 核心函式 ──────────────────────────────────────────────

def find_all_mp3s(base_folder: Path) -> list[dict]:
    """掃描資料夾，找出所有符合格式的 MP3 檔案。"""
    results = []

    for lang_code in LANG_MAP:
        lang_dir = base_folder / lang_code
        if not lang_dir.is_dir():
            continue

        for version in VERSIONS:
            version_dir = lang_dir / version
            if not version_dir.is_dir():
                continue

            for mp3_file in sorted(version_dir.glob("*.mp3")):
                match = MP3_PATTERN.match(mp3_file.name)
                if not match:
                    print(f"  ⚠️  略過不符格式的檔案：{mp3_file.name}")
                    continue

                page, variant = match.groups()
                results.append({
                    "path": mp3_file,
                    "language": lang_code,
                    "version": version,
                    "page": page,
                    "variant": variant,
                    "timestamps_path": mp3_file.with_suffix(".json"),
                })

    return results


def call_scribe_api(mp3_path: Path, language: str) -> list[dict]:
    """呼叫 ElevenLabs Scribe v2 API，取得 word-level timestamps。"""
    from elevenlabs import ElevenLabs

    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        print("❌ 錯誤：找不到環境變數 ELEVENLABS_API_KEY")
        print("   請執行：export ELEVENLABS_API_KEY=\"你的API金鑰\"")
        sys.exit(1)

    client = ElevenLabs(api_key=api_key)

    el_lang = LANG_MAP.get(language)

    with open(mp3_path, "rb") as f:
        result = client.speech_to_text.convert(
            file=f,
            model_id="scribe_v2",
            tag_audio_events=False,
            timestamps_granularity="word",
            language_code=el_lang,
        )

    # 從回傳結果中提取 word-level timestamps
    words = []
    if hasattr(result, "words") and result.words:
        for w in result.words:
            # 只保留 word 類型，過濾掉 spacing
            if w.type == "word":
                words.append({
                    "word": w.text,
                    "start": round(w.start, 3),
                    "end": round(w.end, 3),
                    "type": w.type,
                })

    return words


def save_timestamps(info: dict, words: list[dict]):
    """儲存 timestamps JSON 檔案。"""
    output = {
        "source_file": info["path"].name,
        "language": info["language"],
        "version": info["version"],
        "page": info["page"],
        "variant": info["variant"],
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "words": words,
    }

    output_path = info["timestamps_path"]
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    return output_path


# ─── 主流程 ────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="批次產生 word-level timestamps")
    parser.add_argument("--dry-run", action="store_true", help="只掃描不呼叫 API")
    parser.add_argument("--skip-existing", action="store_true", help="跳過已有 timestamps 的檔案")
    parser.add_argument("--folder", type=str, help="只處理特定資料夾")
    args = parser.parse_args()

    folders = [Path(args.folder)] if args.folder else TARGET_FOLDERS

    # 1. 掃描所有 MP3
    all_mp3s = []
    for folder in folders:
        if not folder.is_dir():
            print(f"⚠️  資料夾不存在，略過：{folder}")
            continue
        print(f"\n📂 掃描：{folder}")
        mp3s = find_all_mp3s(folder)
        print(f"   找到 {len(mp3s)} 個 MP3 檔案")
        all_mp3s.extend(mp3s)

    if not all_mp3s:
        print("\n❌ 沒有找到任何 MP3 檔案")
        return

    # 2. 過濾已存在的 timestamps
    if args.skip_existing:
        before = len(all_mp3s)
        all_mp3s = [m for m in all_mp3s if not m["timestamps_path"].exists()]
        skipped = before - len(all_mp3s)
        if skipped:
            print(f"\n⏭️  跳過 {skipped} 個已有 timestamps 的檔案")

    # 3. 印出摘要
    print(f"\n{'='*60}")
    print(f"📊 待處理摘要")
    print(f"{'='*60}")
    print(f"   總檔案數：{len(all_mp3s)}")

    # 依語言統計
    by_lang = {}
    for m in all_mp3s:
        key = f"{m['language']}/{m['version']}"
        by_lang[key] = by_lang.get(key, 0) + 1
    for key, count in sorted(by_lang.items()):
        print(f"   {key}：{count} 個檔案")

    # 估算費用
    # 假設每頁平均 10 秒，ElevenLabs STT 計費 $0.40/小時
    est_minutes = len(all_mp3s) * 10 / 60
    est_cost = est_minutes / 60 * 0.40
    print(f"\n   預估音檔總長：約 {est_minutes:.1f} 分鐘")
    print(f"   預估 API 費用：約 ${est_cost:.2f} USD")
    print(f"{'='*60}")

    if args.dry_run:
        print("\n🔍 Dry-run 模式，以下是會處理的檔案清單：\n")
        for m in all_mp3s:
            status = "✅ 已存在" if m["timestamps_path"].exists() else "⬜ 待產生"
            print(f"   {status}  {m['path'].relative_to(m['path'].parents[4])}")
        print(f"\n💡 移除 --dry-run 參數以正式執行")
        return

    # 4. 確認執行
    print(f"\n⚡ 即將呼叫 ElevenLabs Scribe API {len(all_mp3s)} 次")
    confirm = input("   確認執行？(y/N) ").strip().lower()
    if confirm != "y":
        print("   已取消")
        return

    # 5. 逐一處理
    success = 0
    failed = 0
    failed_files = []

    for i, mp3_info in enumerate(all_mp3s, 1):
        relative = mp3_info["path"].name
        lang = mp3_info["language"]
        ver = mp3_info["version"]

        print(f"\n[{i}/{len(all_mp3s)}] 🎙️  {lang}/{ver}/{relative}")

        try:
            words = call_scribe_api(mp3_info["path"], lang)
            output_path = save_timestamps(mp3_info, words)
            print(f"         ✅ {len(words)} 個詞 → {output_path.name}")
            success += 1
        except Exception as e:
            print(f"         ❌ 失敗：{e}")
            failed += 1
            failed_files.append(str(mp3_info["path"]))

        # API 節流
        if i < len(all_mp3s):
            time.sleep(API_DELAY)

    # 6. 完成摘要
    print(f"\n{'='*60}")
    print(f"🏁 完成！")
    print(f"   ✅ 成功：{success}")
    print(f"   ❌ 失敗：{failed}")
    if failed_files:
        print(f"\n   失敗的檔案：")
        for f in failed_files:
            print(f"   - {f}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
```

### 4.3 腳本特性

| 特性 | 說明 |
|------|------|
| `--dry-run` | 只掃描、不呼叫 API，預覽會處理哪些檔案 |
| `--skip-existing` | 跳過已有 `.json` 的檔案，避免重複處理 |
| `--folder` | 只處理指定資料夾，不處理全部 |
| 執行前確認 | 顯示摘要和預估費用，需輸入 `y` 才正式執行 |
| 錯誤容忍 | 單一檔案失敗不中斷，結束時統一報告 |
| API 節流 | 每次呼叫間隔 1 秒，避免 rate limit |
| spacing 過濾 | 自動過濾 ElevenLabs 回傳的 `spacing` 類型，只保留 `word` |

---

## 五、執行步驟

### Step 1：預覽（Dry Run）

先確認腳本能正確掃描到所有檔案：

```bash
cd /Users/stacywang/Desktop/Piyo/AI_workflow
python3 generate_timestamps.py --dry-run
```

預期輸出：

```
📂 掃描：/Users/stacywang/Desktop/Piyo/AI_workflow/3_ttsGen/output_tts/三隻小豬
   找到 48 個 MP3 檔案

📂 掃描：/Users/stacywang/Desktop/Piyo/AI_workflow/4_previewGen/final/three-little-pigs
   找到 36 個 MP3 檔案

============================================================
📊 待處理摘要
============================================================
   總檔案數：84
   EN/standard：28 個檔案
   EN/toddler：14 個檔案
   JA/standard：14 個檔案
   ...

🔍 Dry-run 模式，以下是會處理的檔案清單：
   ⬜ 待產生  EN/standard/P01_v1.mp3
   ⬜ 待產生  EN/standard/P02_v4.mp3
   ...
```

### Step 2：正式執行

```bash
python3 generate_timestamps.py
```

腳本會顯示摘要並要求確認，輸入 `y` 後開始逐一處理。

### Step 3：驗證結果

```bash
# 檢查產生了多少 timestamps 檔案（排除 pages.json 等其他 JSON）
find 3_ttsGen/output_tts/三隻小豬 -name "P*_v*.json" | wc -l
find 4_previewGen/final/three-little-pigs -name "P*_v*.json" | wc -l

# 抽查一個看內容
cat 4_previewGen/final/three-little-pigs/EN/standard/P01_v1.json | python3 -m json.tool
```

### Step 4：增量更新（日後新增音檔時）

```bash
# 只處理還沒有 timestamps 的新檔案
python3 generate_timestamps.py --skip-existing
```

---

## 六、費用估算

| 項目 | 數量 |
|------|------|
| 故事數 | 1（三隻小豬） |
| 語言 × 版本 | 3 × 2 = 6 組 |
| 每組約 10-15 頁 | 約 60-90 頁 |
| 每頁 MP3 約 5-15 秒 | — |
| 每頁多個 variant（v1-v4） | 估計平均 2 個 variant/頁 |
| **估計總檔案數** | **~120-180 個 MP3** |
| **估計總音檔長度** | **~20-45 分鐘** |
| **ElevenLabs Scribe 定價** | **$0.40 / 小時** |
| **預估總費用** | **< $0.50 USD** |

---

## 七、疑難排解

### 7.1 常見錯誤

| 錯誤訊息 | 原因 | 解法 |
|---------|------|------|
| `找不到環境變數 ELEVENLABS_API_KEY` | 環境變數未設定 | `export ELEVENLABS_API_KEY="sk_..."` |
| `rate limit exceeded` | API 呼叫太頻繁 | 調高腳本中的 `API_DELAY`（如改為 2.0） |
| `略過不符格式的檔案` | 檔名不符合 `P{NN}_v{N}.mp3` | 確認檔名格式正確 |
| `words 列表為空` | 音檔太短或靜音 | 手動檢查該 MP3 是否有內容 |

### 7.2 中文 / 日文分詞結果不理想

ElevenLabs Scribe 的分詞是自動的，如果某些詞的切分不符合預期：

- 這不影響 karaoke 功能的整體體驗（前端是逐詞 highlight，不是逐字）
- 若需更精確的切分，可考慮後處理腳本調整 `.json` 內的 words 陣列

### 7.3 如何重新處理特定檔案

```bash
# 刪除該檔案的 timestamps，再重新跑（搭配 --skip-existing）
rm 4_previewGen/final/three-little-pigs/EN/standard/P01_v1.json
python3 generate_timestamps.py --skip-existing
```

---

## 八、後續整合：Preview Tool 使用 timestamps

產生完 `.json` 後，`build.py`（Preview Tool 的掃描腳本）會：

1. 掃描每個 MP3 旁邊是否有同名的 `.json`（如 `P01_v1.mp3` → 找 `P01_v1.json`）
2. 有 → 讀取 `words` 陣列，寫入 `stories.json` 的 `timestamps` 欄位
3. 無 → `timestamps` 欄位填 `null`，前端 fallback 為整句顯示

這樣兩個系統完全解耦：
- `generate_timestamps.py` 負責產生 timestamps
- `build.py` 負責組裝 stories.json
- `index.html` 負責播放與逐字同步
