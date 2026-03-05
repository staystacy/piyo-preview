# Claude Code 任務 Prompt-1：建立定稿文字資源

## 背景說明
這是 JOJO Math 有聲繪本的定稿資源區。
所有「最終確認」的圖片、音檔、文字都放在這裡，供 Preview 工具使用。
**不要碰其他任何 AI_workflow 子資料夾。**

---

## 定稿區完整資料夾結構

```
/Users/stacywang/Desktop/Piyo/AI_workflow/4_previewGen/
└── final/
    └── {故事名稱}/
        ├── images/              ← 圖片三語共用，直接放
        │   ├── P01.png
        │   ├── P02.png
        │   └── ...
        ├── EN/
        │   ├── standard/
        │   │   ├── pages.json   ← 所有頁的字幕文字
        │   │   ├── P01.mp3
        │   │   ├── P02.mp3
        │   │   └── ...
        │   └── toddler/
        │       ├── pages.json
        │       ├── P01.mp3
        │       └── ...
        ├── ZH-TW/
        │   ├── standard/
        │   │   ├── pages.json
        │   │   └── ...
        │   └── toddler/
        │       ├── pages.json
        │       └── ...
        └── JA/
            ├── standard/
            │   ├── pages.json
            │   └── ...
            └── toddler/
                ├── pages.json
                └── ...
```

---

## pages.json 格式

```json
{
  "story": "三隻小豬",
  "language": "EN",
  "version": "standard",
  "pages": [
    {
      "page": "P01",
      "text": "Once upon a time, three little pigs set off to build their own homes."
    },
    {
      "page": "P02",
      "text": "The first little pig built his house out of straw. It was quick and easy!"
    },
    {
      "page": "P03",
      "text": "The second pig chose sticks for his house. A little stronger, he thought."
    }
  ]
}
```

| 欄位 | 說明 |
|------|------|
| `story` | 故事名稱，與資料夾名稱一致 |
| `language` | `EN` / `ZH-TW` / `JA` |
| `version` | `standard`（4-6歲）或 `toddler`（2-4歲） |
| `page` | 與圖片、音檔命名前綴一致（`P01`、`P02`⋯⋯） |
| `text` | 該頁顯示在畫面上的字幕文字 |

---

## 你的任務

**建立資料夾結構 + 示範 pages.json**，共 3 故事 × 3 語言 × 2 版本 = **18 個 pages.json**。

音檔（.mp3）和圖片（.png）資料夾先建好但留空，之後人工拖入。

### 故事一：三隻小豬（The Three Little Pigs）
| 路徑 | 語氣說明 |
|------|---------|
| `三隻小豬/EN/standard/pages.json` | 英文，4-6歲，完整敘述 |
| `三隻小豬/EN/toddler/pages.json` | 英文，2-4歲，句子極短極簡單 |
| `三隻小豬/ZH-TW/standard/pages.json` | 繁體中文，4-6歲 |
| `三隻小豬/ZH-TW/toddler/pages.json` | 繁體中文，2-4歲 |
| `三隻小豬/JA/standard/pages.json` | 日文，4-6歲 |
| `三隻小豬/JA/toddler/pages.json` | 日文，2-4歲 |

### 故事二：金髮女孩與三隻熊（Goldilocks and the Three Bears）
| 路徑 | 語氣說明 |
|------|---------|
| `金髮女孩與三隻熊/EN/standard/pages.json` | 英文，4-6歲 |
| `金髮女孩與三隻熊/EN/toddler/pages.json` | 英文，2-4歲 |
| `金髮女孩與三隻熊/ZH-TW/standard/pages.json` | 繁體中文，4-6歲 |
| `金髮女孩與三隻熊/ZH-TW/toddler/pages.json` | 繁體中文，2-4歲 |
| `金髮女孩與三隻熊/JA/standard/pages.json` | 日文，4-6歲 |
| `金髮女孩與三隻熊/JA/toddler/pages.json` | 日文，2-4歲 |

### 故事三：龜兔賽跑（The Tortoise and the Hare）
| 路徑 | 語氣說明 |
|------|---------|
| `龜兔賽跑/EN/standard/pages.json` | 英文，4-6歲 |
| `龜兔賽跑/EN/toddler/pages.json` | 英文，2-4歲 |
| `龜兔賽跑/ZH-TW/standard/pages.json` | 繁體中文，4-6歲 |
| `龜兔賽跑/ZH-TW/toddler/pages.json` | 繁體中文，2-4歲 |
| `龜兔賽跑/JA/standard/pages.json` | 日文，4-6歲 |
| `龜兔賽跑/JA/toddler/pages.json` | 日文，2-4歲 |

每個 pages.json 請填入合理的示範文字（10頁），之後我會替換成真實內容。

---

## 更新資源的方式（日常操作說明）

| 想做的事 | 操作 |
|---------|------|
| 換某頁圖片 | 拖入新 `P03.png` 到 `images/` 覆蓋舊檔 |
| 換某頁音檔 | 拖入新 `P03.mp3` 到對應語言版本資料夾覆蓋 |
| 改某頁字幕 | 打開 `pages.json`，找到對應 `page`，修改 `text` 欄位 |
| 新增一頁 | 放 `P11.png` 到 `images/`，各語言版本放 `P11.mp3`，`pages.json` 新增一筆 |
| 新增一個故事 | 複製任一故事資料夾結構，改資料夾名稱和 JSON 內容 |

---

## 重要限制
- 只在 `4_previewGen/final/` 內操作
- 不要碰 `2_sceneGen/`、`3_ttsGen/` 或其他任何資料夾
