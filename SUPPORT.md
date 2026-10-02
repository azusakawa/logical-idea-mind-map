# 支援說明

本專案透過 [GitHub Issues](https://github.com/azusakawa/logical-idea-mind-map/issues) 提供公開、盡力而為的社群支援。

## 可回報的問題

- Skill 安裝、載入或觸發異常。
- 12 章報告契約或模型內嵌規則不清楚。
- `validate_report.py` 的檢查結果與文件不一致。
- `render_report.py` 發生錯誤、缺字、裁切、重疊、表格溢出或 PDF 文字無法搜尋。
- 在支援範圍內的文件錯誤、相容性問題或功能建議。

ChatGPT、Codex、GitHub 或作業系統本身的帳號、計費、服務中斷及平台權限問題，請使用相應平台的官方支援管道處理。

## 建立 Issue 前

1. 使用最新版本重現問題。
2. 先閱讀 `README.md`、`SKILL.md`、`references/framework-contract.md` 與 `references/report-template.md`。
3. 對報告問題先執行驗證器：

   ```bash
   python3 skills/structuring-logical-ideas/scripts/validate_report.py report.md
   ```

4. 對 PDF 問題確認 Markdown 已通過驗證，並記錄實際渲染命令。
5. 移除檔案、畫面與終端輸出中的個人資料、憑證、內部路徑、客戶資料及其他機密內容。

## Issue 應包含的資訊

請使用清楚的標題，並提供：

- 問題摘要。
- 預期行為與實際行為。
- 可穩定重現的最少步驟。
- 本專案的版本、commit 或下載日期。
- 使用環境：ChatGPT 或 Codex 版本／介面、作業系統、Python 版本。
- `reportlab` 版本；可執行：

  ```bash
  python3 -c "import reportlab; print(reportlab.Version)"
  ```

- 已去識別化的最小報告片段。
- 完整但已清除敏感資訊的驗證器或渲染器錯誤訊息。
- 若是版面問題，可附不含敏感內容的 PDF 頁面截圖。

請勿只貼整份私人報告；通常一份能重現問題的最小範例更容易定位原因。

## 安全與隱私問題

GitHub Issues 是公開管道。請勿在 Issue 中放入存取權杖、密碼、個人資料、專有資料或可直接利用的未公開漏洞細節。

若問題需要避免公開技術細節，先建立一個不含敏感資訊的 Issue，只說明受影響的元件、影響類型及希望取得非公開聯絡方式。維護者回覆前，不要公開可利用細節。

## 回覆與修復

問題會依影響範圍、可重現程度、安全性與維護資源評估。公開 Issue 不附帶服務水準承諾，也不保證回覆時間、接受功能建議或提供特定版本的修復。

為了讓討論可追蹤，請在原 Issue 補充資訊；除非問題不同，避免為同一件事重複建立多個 Issue。

