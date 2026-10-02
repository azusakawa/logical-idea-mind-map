---
name: structuring-logical-ideas
description: "Use when a topic, problem, or project concept needs rigorous reasoning with SCQA, PREP, Pyramid MECE, and STAR strictly nested inside their required parent modules, plus a Markdown mind map and searchable PDF."
---

# 邏輯構想與思維導圖

## 核心原則

把輸入轉成一條可追溯的決策論證。所有章節共用同一個決策主體、Thesis、前提與證據狀態；思維導圖必須呈現模型的真正包含關係。

## 工作流程

1. **界定輸入。** 擷取主題、要解決的問題、決策主體、時點、受眾、限制與可用證據。資料不足但仍可分析時直接繼續，以 `[假設]`、`[未知]`、`[待驗證]` 標示；只有連主題或決策問題都無法辨認時才詢問。
2. **建立推論骨架。** 先寫一句 Thesis，再整理背景、利害關係人、時間、資源、概念邊界、變數、因果鏈與衝突。因果鏈須包含條件、反向路徑或干擾因素。
3. **套用完整契約。** 讀取 [references/framework-contract.md](references/framework-contract.md) 與 [references/report-template.md](references/report-template.md)。依範本完成 1–12 節，不省略空缺；無資料的欄位寫明未知及驗證方式。
4. **建立嚴格內嵌圖。** 固定使用此包含關係：

   `SCQA > Answer > PREP > Reason > 金字塔（MECE）`

   `SCQA > Answer > PREP > Example > STAR`

   STAR 也可放在金字塔的底層事實下。PREP、金字塔、STAR 不得與 SCQA 並列。思維導圖使用 Markdown 階層列表，不用 Mermaid 取代。
5. **保護證據完整性。** 只有使用者提供或可驗證的過往資料可標為 `STAR｜實證案例`。其餘一律使用 `STAR｜驗證設計`，Result 寫成待觀察的目標、門檻或決策規則，不得寫成已發生成果。
6. **驗證報告。** 將完整內容存為 UTF-8 Markdown。先把載入本 Skill 時取得的 `skill_root` 絕對路徑設為 `SKILL_ROOT`；不得用 `pwd`、報告所在目錄或目前工作目錄推測 Skill 位置。確認 `$SKILL_ROOT/SKILL.md` 存在後執行：

   ```bash
   test -f "$SKILL_ROOT/SKILL.md"
   python3 "$SKILL_ROOT/scripts/validate_report.py" <report.md>
   ```

   修正所有 `ERROR`，直到輸出 `PASS`。若工具輸出 `WARNING`，先人工處理後再進入 PDF 階段。
7. **產生 PDF。** 驗證通過後執行：

   ```bash
   python3 "$SKILL_ROOT/scripts/render_report.py" <report.md> <report.pdf>
   ```

   報告只使用渲染器支援的 H1–H4、段落、引言、階層列表、簡單表格、粗體與行內程式碼。每個表格的標題列、分隔列與資料列必須有相同欄數，否則渲染會明確失敗。內建字型以繁體中文為主要保真範圍；渲染器會在寫檔前逐字檢查所有內文、檔名及自動加入的符號，缺少任一字形便以非零狀態結束，不得忽略錯誤或交付 tofu 方框。此輕量渲染器只接受不需複雜塑形與雙向排版的文字，會拒絕組合記號、格式控制字元及由右至左文字。若其他由左至右的語言或特殊符號不需複雜塑形，但超出內建字型範圍，改傳入一個涵蓋報告全部字元且可內嵌的 TTF/OTF：

   ```bash
   python3 "$SKILL_ROOT/scripts/render_report.py" <report.md> <report.pdf> --font <font.ttf>
   ```

   若語言需要組合字形或雙向排版，改用具備複雜文字塑形能力的 PDF 工具，不得只更換字型後繼續使用本腳本。

   重新開啟 PDF、抽取文字並把全部頁面渲染成 PNG；先看縮圖總覽，再以原尺寸檢查第一頁、中間頁、最後一頁及每種特殊版型。五頁以內逐頁原尺寸檢查。修正缺字、裁切、重疊、表格溢出、層級不清或孤立標題後重新驗證。

## 交付契約

- 預設使用繁體中文與台灣常用詞。使用者指定其他語言時可翻譯內文，但保留 12 個繁體中文固定章節標題與模型標籤，以維持驗證契約。
- 在對話中提供一句話總結與完整 Markdown 思維導圖；長篇正文可由 Markdown 檔承載。
- 一定交付經檢查的 PDF。檔名使用可辨識的主題名稱。
- 清楚列出重大假設、未知、待驗證事項及可能反轉 Thesis 的條件；不存在的狀態類別不用虛構。
- 每項行動至少包含責任人、期限、資源、領先指標、結果指標、門檻與檢查點。
- 整份思維導圖只保留一個有意義的 STAR 節點；多個證據情境應合併成一個代表性案例或驗證設計，避免重複框架。

## 完成前檢查

| 檢查 | 合格條件 |
|---|---|
| 一致性 | 300 字摘要、一句話、Thesis、SCQA Answer 與 PREP Point 指向同一主張 |
| MECE | 次級論點採同一分類軸，互不重複，合計足以支撐結論 |
| 因果 | 每條路徑能指出前提、機制、結果及可能失效原因 |
| STAR | 實證與未來驗證清楚區分，Result 可量測 |
| 可行動 | 每個重要未知至少連到一項驗證行動或指標 |
| PDF | 可搜尋、繁體中文正常、頁碼完整、階層列表跨頁可讀 |
