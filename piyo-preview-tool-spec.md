# Piyo 有聲繪本 Preview Tool — 建置規格書

> **版本：** v2.0  
> **目的：** 供內部團隊審核有聲繪本資源品質（圖片／影片、音檔、字幕、逐字同步）  
> **技術方案：** 純 HTML5 + CSS3 + Vanilla JS，單一 `index.html`，零建構步驟  
> **部署方式：** 本機 `python3 -m http.server` 開發 → GitHub Pages 部署給同事

---

## 一、資料夾結構規範

### 1.1 總覽

```
4_previewGen/
├── index.html              ← 主程式（單一檔案）
├── build.py                ← 掃描腳本，產生 stories.json
├── README.md               ← 使用說明
└── final/                  ← 唯一資源來源（唯讀，不改動）
    └── {story-slug}/       ← 英文 slug，例如 three-little-pigs
        ├── meta.json       ← 故事層級 metadata
        ├── media/          ← 圖片 (.png) 與影片 (.mp4) 混放
        │   ├── P01.png
        │   ├── P02.png
        │   ├── P03.mp4     ← 影片頁（靜音，旁白由 MP3 提供）
        │   └── ...
        ├── EN/
        │   ├── standard/
        │   │   ├── pages.json       ← 字幕文字
        │   │   ├── timestamps.json  ← 逐字時間軸（可選，無則整句顯示）
        │   │   ├── P01.mp3
        │   │   └── ...
        │   └── toddler/
        │       ├── pages.json
        │       ├── timestamps.json
        │       └── ...
        ├── ZH-TW/
        │   ├── standard/
        │   └── toddler/
        └── JA/
            ├── standard/
            └── toddler/
```

### 1.2 命名規則

| 項目 | 規則 | 範例 |
|------|------|------|
| 故事資料夾 | 英文 slug，全小寫，`-` 分隔 | `three-little-pigs` |
| 媒體檔案 | `P{NN}.png` 或 `P{NN}.mp4` | `P01.png`、`P03.mp4` |
| 音檔 | `P{NN}.mp3` | `P01.mp3` |
| 語言代碼 | IETF BCP 47 標準 | `EN`、`ZH-TW`、`JA` |
| 版本代碼 | 全小寫英文 | `standard`、`toddler` |

### 1.3 `meta.json`（每個故事一份）

位於 `final/{story-slug}/meta.json`，提供故事的多語言標題與其他 metadata。

```json
{
  "id": "three-little-pigs",
  "title": {
    "EN": "The Three Little Pigs",
    "ZH-TW": "三隻小豬",
    "JA": "三匹の子ぶた"
  },
  "coverPage": "P01"
}
```

> **為何獨立 `meta.json`？**  
> 故事標題是多語言資料，不應由程式猜測或硬編碼。  
> 放在故事根目錄，新增故事時只需填一次。

### 1.4 `pages.json`（每個語言 × 版本一份）

位於 `final/{story-slug}/{lang}/{version}/pages.json`。

```json
[
  {
    "page": "P01",
    "text": "Once upon a time, three little pigs set off to build their own homes."
  },
  {
    "page": "P02",
    "text": "The first little pig built his house out of straw."
  }
]
```

### 1.5 `timestamps.json`（逐字同步用，可選）

位於 `final/{story-slug}/{lang}/{version}/timestamps.json`。

由 ElevenLabs API 的 `alignment` 回傳資料轉換而來。若此檔案不存在，前端自動 fallback 為整句顯示。

```json
[
  {
    "page": "P01",
    "words": [
      { "word": "Once",   "start": 0.00, "end": 0.35 },
      { "word": "upon",   "start": 0.35, "end": 0.58 },
      { "word": "a",      "start": 0.58, "end": 0.65 },
      { "word": "time,",  "start": 0.65, "end": 1.02 },
      { "word": "three",  "start": 1.10, "end": 1.38 }
    ]
  },
  {
    "page": "P02",
    "words": []
  }
]
```

> **中文 / 日文的處理：**  
> 中文以「詞」為單位（非單字），日文以「文節」為單位。  
> ElevenLabs 的 alignment 回傳會自動依語言分詞。  
> 前端不需要額外分詞邏輯。

---

## 二、`build.py` — 掃描腳本

### 2.1 職責

掃描 `final/` 資料夾，自動產生 `data/stories.json`。  
任何人都能跑，不依賴 Claude Code。

### 2.2 掃描邏輯

```
1. 列出 final/ 下所有子資料夾 → 故事列表
2. 每個故事：
   a. 讀取 meta.json → 取得 id、title
   b. 掃描 media/ → 列出所有 .png 和 .mp4，依頁碼排序
   c. 判斷每頁的媒體類型（image 或 video）
   d. 列出語言資料夾 → languages 陣列
   e. 每個語言下，列出版本資料夾 → versions 陣列
   f. 每個版本：
      - 讀取 pages.json → 文字內容
      - 嘗試讀取 timestamps.json → 逐字時間軸（不存在則 null）
      - 掃描 .mp3 檔案 → 音檔列表
   g. 以頁碼為 key，組合 media + audio + text + timestamps
   h. 缺少的欄位填 null，不報錯
```

### 2.3 產出 `data/stories.json` 格式

```json
{
  "generatedAt": "2025-06-01T14:30:00Z",
  "stories": [
    {
      "id": "three-little-pigs",
      "title": {
        "EN": "The Three Little Pigs",
        "ZH-TW": "三隻小豬",
        "JA": "三匹の子ぶた"
      },
      "languages": ["EN", "ZH-TW", "JA"],
      "versions": ["standard", "toddler"],
      "pages": {
        "EN": {
          "standard": [
            {
              "page": "P01",
              "mediaType": "image",
              "media": "final/three-little-pigs/media/P01.png",
              "audio": "final/three-little-pigs/EN/standard/P01.mp3",
              "text": "Once upon a time, three little pigs set off to build their own homes.",
              "timestamps": [
                { "word": "Once", "start": 0.00, "end": 0.35 },
                { "word": "upon", "start": 0.35, "end": 0.58 }
              ]
            },
            {
              "page": "P03",
              "mediaType": "video",
              "media": "final/three-little-pigs/media/P03.mp4",
              "audio": "final/three-little-pigs/EN/standard/P03.mp3",
              "text": "The wolf huffed and puffed and blew the house down!",
              "timestamps": null
            }
          ],
          "toddler": []
        },
        "ZH-TW": { "standard": [], "toddler": [] },
        "JA": { "standard": [], "toddler": [] }
      }
    }
  ]
}
```

> **路徑規則：** `media` 和 `audio` 使用**相對於 `4_previewGen/` 的路徑**。

### 2.4 執行方式

```bash
cd /Users/stacywang/Desktop/Piyo/AI_workflow/4_previewGen
python3 build.py
# → 輸出 data/stories.json
```

腳本應具備以下特性：

- **零依賴**：僅使用 Python 標準庫（`os`、`json`、`pathlib`）
- **冪等**：重複執行結果一致
- **友善輸出**：掃描過程印出摘要（找到幾個故事、幾種語言、幾頁）
- **容錯**：缺少 `meta.json` 時以資料夾名稱作為 fallback title

---

## 三、`index.html` — 前端播放器

### 3.1 功能總覽

| 功能區 | 說明 |
|--------|------|
| 選擇列 | 故事、語言、版本三個自訂下拉選單 |
| 主播放區 | 媒體顯示（圖片或影片）+ 字幕區 |
| 逐字同步 | 有 timestamps 時逐字 highlight，無則整句顯示 |
| 翻頁控制 | 左右箭頭按鈕 + 鍵盤方向鍵 + 滑動動畫 |
| 自動播放 | 開關切換；開啟時音檔結束 1.5 秒後自動翻頁 |
| 頁碼與進度 | 底部頁碼（3 / 12）+ 進度條 |
| 容錯顯示 | 音檔 null → 顯示 🔇 提示；媒體 null → 灰色佔位區塊 |

### 3.2 選擇介面（頁面頂部）

**三個自訂下拉選單，不使用原生 `<select>`：**

- **故事：** 依 `stories.json` 動態生成，顯示當前語言的標題
- **語言：** 顯示友善名稱對照

  | 代碼 | 顯示名稱 |
  |------|----------|
  | `EN` | English |
  | `ZH-TW` | 繁體中文 |
  | `JA` | 日本語 |

- **版本：** 顯示友善名稱

  | 代碼 | 顯示名稱 |
  |------|----------|
  | `standard` | Standard（4-6y） |
  | `toddler` | Toddler（2-4y） |

**行為：** 切換任一選單後，立即載入對應內容，從第一頁開始播放。

### 3.3 主播放區

#### 媒體顯示

- **容器：** 固定 3:2 比例（對應 1536×1024px 原圖），最大寬度 860px，置中
- **圖片頁（`mediaType: "image"`）：** `<img>` 標籤，`object-fit: cover`
- **影片頁（`mediaType: "video"`）：** `<video>` 標籤，靜音（`muted`），自動播放，不顯示控制列
  - 影片播放與 MP3 旁白同步啟動
  - 影片長度可能與音檔不同；以音檔結束為準決定是否翻頁
  - 影片播完若音檔未結束，停在最後一幀
  - 音檔播完若影片未結束，依自動翻頁設定決定行為
- **媒體為 null：** 顯示灰色佔位區塊，中間顯示「🖼️ 媒體未就緒」

#### 字幕區

- 位於媒體下方，固定高度區域，文字垂直置中
- 有適當內距（padding: 20px 32px）

**逐字同步模式（有 timestamps 時）：**
- 所有文字預先渲染，初始為淺灰色（`#CCCCCC`）
- 隨音檔播放進度，已唸過的字轉為主文字色（`#2C2C2C`）
- 當前正在唸的字加上強調色底色（`#8B6F47` 的淡化版，約 20% opacity）
- 使用 `requestAnimationFrame` + `audio.currentTime` 驅動，確保流暢
- 過渡效果：顏色變化用 CSS transition（`color 0.15s ease`）

**整句顯示模式（無 timestamps 時）：**
- 整句文字直接以主文字色顯示
- 無動畫效果

**文字為 null：** 字幕區保留，顯示空白。

#### 音檔播放

- 使用 `<audio>` 元素，不顯示原生控制列
- 翻頁時自動播放當前頁音檔
- 音檔為 null 時：字幕區上方顯示小字提示「🔇 音檔未就緒」，不報錯

### 3.4 翻頁控制

- **箭頭按鈕：** 媒體區左右兩側，半透明圓形按鈕，hover 時完全顯示
- **鍵盤：** `←` `→` 方向鍵支援翻頁
- **翻頁動畫：** 水平滑動（CSS `transform: translateX` + `transition 0.3s ease`）
- **邊界：** 第一頁隱藏左箭頭，最後一頁隱藏右箭頭
- **翻頁時重置：** 停止當前音檔 → 載入新頁媒體與字幕 → 播放新頁音檔

### 3.5 自動播放開關

- UI：頁面右上角或控制列區域，Toggle Switch 樣式
- 標籤：「Auto ▶」
- **開啟時：** 音檔播放結束後等待 1.5 秒，自動翻到下一頁
- **關閉時：** 音檔播完停留在當前頁，需手動翻頁
- **最後一頁：** 不論開關狀態，播完不做動作（不循環）
- **預設：** 開啟

### 3.6 底部控制列

- **頁碼顯示：** `3 / 12` 格式
- **進度條：** 細長條，填充色為強調色，寬度 = 當前頁 / 總頁數
- **可點擊：** 點擊進度條可跳轉到對應頁面

---

## 四、視覺設計規格

### 4.1 色彩系統

| 用途 | 色碼 | 說明 |
|------|------|------|
| 背景 | `#FAF7F2` | 米白奶油色 |
| 卡片背景 | `#FFFFFF` | 純白，搭配輕微陰影 |
| 主文字 | `#2C2C2C` | 深灰近黑 |
| 次要文字 | `#8C8C8C` | 中灰 |
| 強調色 | `#8B6F47` | 溫暖棕金 |
| 強調色淡化 | `rgba(139, 111, 71, 0.15)` | 用於逐字 highlight 底色 |
| 未讀字色 | `#CCCCCC` | 淺灰，逐字同步的未唸字 |
| 錯誤/提示 | `#B8A080` | 柔和提示色 |

### 4.2 字型

```css
/* 英文標題 */
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;600&display=swap');

/* 英文內文 / UI */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');

/* 中文字型 */
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+TC:wght@400;600&display=swap');

/* 日文字型 */
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+JP:wght@400;600&display=swap');
```

| 場景 | 字型 | 備註 |
|------|------|------|
| 頁面標題 | `Cormorant Garamond` | 英文大標 |
| UI 元素（按鈕、標籤） | `Inter` | 清晰易讀 |
| 英文字幕 | `Inter`, 18px | — |
| 中文字幕 | `Noto Serif TC`, 20px | 中文稍大以平衡視覺 |
| 日文字幕 | `Noto Serif JP`, 20px | 同上 |

> **字型切換邏輯：** 根據當前選擇的語言，動態切換字幕區的 `font-family`。

### 4.3 版面

- 整體風格：高級歐美繪本出版社官網感，大方留白
- 主內容區最大寬度：`960px`，置中
- 媒體區最大寬度：`860px`
- 卡片圓角：`12px`
- 卡片陰影：`0 2px 16px rgba(0, 0, 0, 0.06)`
- 自訂下拉選單：圓角、border、hover 漸變效果
- 響應式：MacBook 13" 到 27" 大螢幕都好看

---

## 五、技術規格

### 5.1 架構

- **單一 `index.html`**：HTML + CSS + JS 全部內嵌
- **資料驅動**：`fetch('./data/stories.json')` 載入設定
- **零依賴**：不使用任何框架或 build 工具
- **響應式**：純 CSS media query

### 5.2 JavaScript 架構建議

```
App
├── DataLoader          ← fetch stories.json，解析資料
├── DropdownController  ← 三個自訂下拉選單的狀態與事件
├── PageRenderer        ← 渲染媒體 + 字幕 + 翻頁動畫
├── AudioController     ← 音檔播放、結束事件、自動翻頁計時
├── KaraokeEngine       ← 逐字同步邏輯（requestAnimationFrame）
├── NavigationController← 翻頁（按鈕 + 鍵盤 + 進度條點擊）
└── AutoPlayToggle      ← 自動播放開關狀態
```

### 5.3 關鍵實作細節

**逐字同步（KaraokeEngine）：**
```javascript
// 核心邏輯
function updateKaraoke() {
  const currentTime = audioElement.currentTime;
  words.forEach((wordEl, i) => {
    const ts = timestamps[i];
    if (currentTime >= ts.end) {
      wordEl.classList.add('spoken');
      wordEl.classList.remove('active');
    } else if (currentTime >= ts.start) {
      wordEl.classList.add('active');
    }
  });
  if (!audioElement.paused) {
    requestAnimationFrame(updateKaraoke);
  }
}
```

**影片頁同步播放：**
```javascript
// 影片與音檔同步啟動
async function playPage(pageData) {
  if (pageData.mediaType === 'video') {
    videoEl.currentTime = 0;
    videoEl.play();
  }
  if (pageData.audio) {
    audioEl.src = pageData.audio;
    await audioEl.play();
  }
}
```

### 5.4 瀏覽器相容性

- Chrome 90+、Safari 15+、Firefox 90+
- 注意：Chrome 的 autoplay 政策要求用戶至少互動一次才能播放音檔
  - 解法：首次載入時顯示一個「▶ 開始體驗」按鈕，點擊後解鎖 audio context

---

## 六、`README.md` 內容

### 6.1 本機預覽

```bash
cd /Users/stacywang/Desktop/Piyo/AI_workflow/4_previewGen
python3 -m http.server 8080
# 瀏覽器開啟 http://localhost:8080
```

### 6.2 重新產生 stories.json

替換或新增 `final/` 內的資源後：

```bash
python3 build.py
```

### 6.3 日常更新對照表

| 想做的事 | 操作 |
|---------|------|
| 換某頁圖片 | 新 `P03.png` 放入 `final/{story}/media/` 覆蓋 → `python3 build.py` |
| 換某頁影片 | 新 `P03.mp4` 放入 `final/{story}/media/` 覆蓋 → `python3 build.py` |
| 圖片頁改成影片頁 | 刪除 `P03.png`，放入 `P03.mp4` → `python3 build.py` |
| 換某頁音檔 | 新 `P03.mp3` 放入對應語言版本資料夾覆蓋 → `python3 build.py` |
| 改某頁字幕 | 編輯 `pages.json`，修改對應 `text` → `python3 build.py` |
| 新增逐字時間軸 | 建立或更新 `timestamps.json` → `python3 build.py` |
| 新增一頁 | 放媒體 + 音檔 + 更新 `pages.json`（+ 可選 `timestamps.json`）→ `python3 build.py` |
| 新增故事 | 建立新資料夾（含 `meta.json`）→ 依結構放入資源 → `python3 build.py` |
| 新增語言 | 在故事資料夾下新增語言子資料夾（如 `KO/`）→ 放入資源 → `python3 build.py` |

### 6.4 新增故事快速指南

```bash
# 1. 建立資料夾結構
mkdir -p final/new-story/{media,EN/{standard,toddler},ZH-TW/{standard,toddler},JA/{standard,toddler}}

# 2. 建立 meta.json
echo '{
  "id": "new-story",
  "title": { "EN": "New Story", "ZH-TW": "新故事", "JA": "新しい物語" },
  "coverPage": "P01"
}' > final/new-story/meta.json

# 3. 放入媒體、音檔、pages.json

# 4. 重新掃描
python3 build.py
```

### 6.5 部署到 GitHub Pages

```bash
# 將整個 4_previewGen/ 推上 GitHub repo
git add .
git commit -m "update preview resources"
git push

# GitHub Settings → Pages → 設定根目錄
# 注意：媒體檔案較大，建議啟用 Git LFS
git lfs track "*.mp3" "*.mp4" "*.png"
```

### 6.6 ElevenLabs Timestamps 取得方式

在 ElevenLabs API 呼叫時加入 `alignment` 參數，即可取得逐字時間軸：

```python
# 呼叫 ElevenLabs API 時加入 with_timestamps
result = client.text_to_speech.convert(
    voice_id="your_voice_id",
    text="Once upon a time...",
    model_id="eleven_multilingual_v2",
    output_format="mp3_44100_128"
)

# alignment 資料會包含每個字的 start/end 時間
# 將其轉換為 timestamps.json 格式
```

> 具體轉換腳本可另建 `scripts/convert_timestamps.py`，  
> 從 ElevenLabs alignment 輸出轉為本專案的 `timestamps.json` 格式。

---

## 七、重要限制與原則

1. **唯讀原則：** `build.py` 和 `index.html` 只讀取 `final/` 內的資源，永不改動
2. **隔離原則：** 不碰 `AI_workflow/` 下的其他子資料夾
3. **容錯原則：** 任何欄位缺失都以 `null` 處理，前端優雅降級，不報錯
4. **獨立原則：** `build.py` 使用 Python 標準庫，任何人都能跑
5. **單一原則：** `index.html` 是自包含的單一檔案，零依賴零建構

---

## 八、舊版 → 新版改動摘要

| 項目 | 舊版（Prompt-2） | 新版（本文檔） |
|------|------------------|----------------|
| 故事資料夾命名 | 中文（`三隻小豬`） | 英文 slug（`three-little-pigs`） |
| 標題來源 | 硬編碼在 stories.json | `meta.json` 動態讀取 |
| 媒體資料夾 | `images/`（僅圖片） | `media/`（圖片 + 影片混放） |
| 影片支援 | 無 | `.mp4`，靜音播放，MP3 旁白 |
| 逐字同步 | 無 | `timestamps.json` 驅動 karaoke |
| 掃描方式 | 請 Claude Code 手動掃描 | 獨立 `build.py` 腳本 |
| 自動翻頁 | 寫死 1.5 秒 | Toggle 開關，可切換自動/手動 |
| `pages.json` schema | 未定義 | 明確定義 |
| 日文字型 | 未考慮 | `Noto Serif JP` |
| Autoplay 政策 | 未處理 | 首次互動解鎖 audio context |
| `stories.json` 產生時間 | 無 | `generatedAt` 欄位 |

---

## 九、執行順序（給 Claude Code）

```
Step 1 → 建立 build.py（掃描腳本）
Step 2 → 執行 build.py，產生 data/stories.json
Step 3 → 建立 index.html（前端播放器）
Step 4 → 建立 README.md
Step 5 → 本機測試：python3 -m http.server 8080
```
