# Preview Player — Lessons Learned

> 本文件記錄 Preview player (index.html) 和 build pipeline 的已知問題及設計決策。
> 修改 karaoke / build / rendering 相關程式碼前，先查閱此文件。

---

## 目錄

| # | Lesson | 關鍵字 |
|---|--------|--------|
| L1 | [顯示文字必須來自 pages.json](#l1) | Scribe 簡體、display vs timing |
| L2 | [JA karaoke anchor mapping](#l2) | M ≠ N、漢字→平假名、buildAnchorMapping |
| L3 | [標點符號不應有 active highlight](#l3) | data-punct、spoken only |
| L4 | [Gap bridging 防閃爍](#l4) | extendedEnds、flicker |

---

## L1: 顯示文字必須來自 pages.json，不是 timestamps {#l1}

**問題**
如果直接用 timestamp 的 `word` 欄位作為顯示文字，ZH-TW 的字幕會變成簡體字。

**根因**
ElevenLabs Scribe STT 處理中文音檔時，會自動輸出簡體中文，不保留繁體原文。
Timestamp JSON 的 `word` 欄位是 STT 產出，不是原始文本。

**解法**
Display text 永遠從 `page.text`（來自 `pages.json`）取得。
Timestamps 只用於計算每個字/詞的 start/end 時間。
這個原則在 `renderCJKKaraoke()` 和 `renderENKaraoke()` 中都有體現。

**位置**: `index.html` lines 841-902 (CJK), lines 908-972 (EN)

---

## L2: JA karaoke anchor mapping 處理 M ≠ N {#l2}

**問題**
日文 timestamps 的字元數 (M) 經常和 page.text 的內容字元數 (N) 不同，因為 STT 會把漢字轉成平假名。
例如：原文「三匹の子ぶた」有 6 個內容字，但 STT 可能回傳「さんびきのこぶた」7 個字。

**根因**
ElevenLabs Scribe 對日文做語音辨識時，傾向將漢字展開為假名讀音。

**解法**
`buildAnchorMapping()` (line 772) 使用雙指針找到匹配的錨點字元（透過 `normalizeKana()` 將片假名轉平假名比較），然後在錨點之間做等比分配。
只在 `state.lang === 'JA'` 且 `M !== N` 時啟用此模式。

**位置**: `index.html` lines 765-833

---

## L3: 標點符號不應有 active highlight {#l3}

**問題**
標點符號如果像一般字元一樣獲得 `.active` class（反白背景），視覺上會很突兀。

**解法**
標點符號元素加上 `data-punct="1"` 標記。
Karaoke timing engine 中，標點只套用 `.spoken`（顏色變化），永不套用 `.active`（背景 highlight）。
標點繼承前一個內容字元的 timing。

**位置**: `index.html` lines 1079-1087 (timing engine punctuation handling)

---

## L4: Gap bridging 防止 karaoke 閃爍 {#l4}

**問題**
當一個詞的 end time 和下一個詞的 start time 之間有空隙時，會有短暫時刻沒有任何字元被 highlight，造成視覺閃爍。

**解法**
`startKaraoke()` 中計算 `extendedEnds` 陣列：如果下一個 content element 的 start > 當前的 end，就延長當前的有效 end time 到下一個的 start。
這樣確保永遠有一個字元處於 active 狀態。

**位置**: `index.html` lines 1051-1058

<!-- 後續 session 解決新問題時，請在此追加 L5, L6... -->
