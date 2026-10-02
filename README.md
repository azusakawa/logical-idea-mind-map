# 邏輯構想與思維導圖

`structuring-logical-ideas` 是一個供 ChatGPT 與 Codex 使用的 Skill，將「特定主題、問題情境或專案構想」整理成可追溯、可驗證、可執行的邏輯分析。它會產生固定 12 章的 Markdown 報告、嚴格內嵌的思維導圖，以及可搜尋文字的 PDF。

## 核心特色

- 先辨識決策題、決策主體、利害關係人、時間與資源限制，再提出論點。
- 用 `[已知]`、`[假設]`、`[未知]`、`[待驗證]` 區分證據狀態，避免把推測寫成事實。
- 讓摘要、Thesis、一句話總結與最終建議維持同一主張。
- 將因果鏈拆成可檢驗的前提、機制、結果、干擾因素與反證條件。
- 把行動連到責任人、期限、資源、領先指標、結果指標與決策門檻。
- 內附報告驗證器與繁體中文 PDF 渲染器。

## 框架的內嵌關係

四個模型不是平行羅列，而是依固定語意相互內嵌：

- SCQA
  - S｜Situation（情境）
  - C｜Complication（衝突）
  - Q｜Question（問題）
  - A｜Answer（解答）
    - PREP
      - P1｜Point（主張）
      - R｜Reason（理由）
        - 金字塔原理（MECE）
          - 核心結論
            - 次級論點
              - 底層事實
      - E｜Example（案例）
        - STAR｜實證案例或驗證設計
          - S｜Situation
          - T｜Task
          - A｜Action
          - R｜Result
      - P2｜Point（重申）

STAR 也可放在金字塔的底層事實之下，但整份思維導圖只保留一個有實質內容的 STAR 節點。

## 輸入與輸出

| 項目 | 內容 |
|---|---|
| 輸入 | 一個主題、問題情境或專案構想；可另附決策者、受眾、期限、資源及證據 |
| 主要輸出 | 固定 12 章的繁體中文 Markdown 分析報告 |
| 視覺結構 | Markdown 階層列表格式的複合模型思維導圖 |
| 文件輸出 | 可搜尋文字、內嵌繁體中文字型的 A4 PDF |
| 驗證 | 章節、字數、證據標籤、模型內嵌位置與內容完整性檢查 |

12 章依序涵蓋：主題相關資訊、300 字摘要、關鍵字與變數、核心決策者、Thesis、定義與前提邊界、因果路徑、重複考量與衝突、一句話總結、分眾解釋、行動與指標、複合模型思維導圖。PDF 是相同內容的交付格式，不另設第 13 章。

## 使用方式

在已安裝本 Skill 的 ChatGPT 或 Codex 中輸入：

```text
使用 $structuring-logical-ideas 分析這個主題，建立巢狀思維導圖並產生 PDF：
<貼上主題、問題情境或專案構想>
```

若輸入資訊不足但仍可分析，Skill 會繼續推演，並明確標示假設、未知與待驗證項目；只有連主題或決策問題都無法辨認時才需要補充資訊。

## 從原始碼使用

需求：Python 3.10 以上與 `reportlab`。

```bash
git clone https://github.com/azusakawa/logical-idea-mind-map.git
cd logical-idea-mind-map
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

將 `skills/structuring-logical-ideas` 目錄安裝到執行環境所支援的 Skill 位置。各版本的 ChatGPT 與 Codex 安裝方式可能不同，請以當前官方 Skill 文件為準。

本專案的 Python 工具不會自行產生分析內容；它們負責驗證已完成的 Markdown 報告並將其渲染為 PDF：

```bash
export SKILL_ROOT="$PWD/skills/structuring-logical-ideas"

python3 "$SKILL_ROOT/scripts/validate_report.py" report.md
python3 "$SKILL_ROOT/scripts/render_report.py" report.md report.pdf
```

如需使用其他可內嵌且完整涵蓋報告字元的 TTF／OTF 字型：

```bash
python3 "$SKILL_ROOT/scripts/render_report.py" report.md report.pdf --font /path/to/font.ttf
```

驗證器輸出 `PASS` 後再產生 PDF。交付前仍應抽取 PDF 文字並檢查所有頁面的缺字、裁切、重疊、表格溢出與層級縮排。

## 專案結構

```text
plugin.json
README.md / PRIVACY.md / TERMS.md / SUPPORT.md
assets/
  logo.png
  composer-icon.png
skills/
  structuring-logical-ideas/
    SKILL.md
    agents/openai.yaml
    assets/
      NotoSansTC-Regular.ttf
      OFL.txt
      icon.svg
    references/
      framework-contract.md
      report-template.md
    scripts/
      validate_report.py
      render_report.py
tests/
scripts/
  check_package.py
  build_plugin.py
```

## 重要限制

- 驗證契約要求 12 個固定的繁體中文章節標題；即使正文使用其他語言，也需保留這些標題與模型標籤。
- 內建 PDF 渲染器支援 H1–H4、段落、引言、階層列表、簡單表格、粗體與行內程式碼。
- 內建渲染器不適合需要複雜文字塑形、組合字形或雙向排版的文字。
- `STAR｜實證案例` 必須來自可查核的過往事件；未發生的方案應使用 `STAR｜驗證設計`。
- 產出品質仍取決於輸入資料與模型推論，重要決策應由適任人員複核。

## 隱私與支援

本 Skill 沒有 MCP、外部 API、帳號系統、付款功能或遙測。詳情請見 [隱私政策](PRIVACY.md)。遇到安裝、驗證或 PDF 渲染問題，請依 [支援說明](SUPPORT.md) 在 [GitHub Issues](https://github.com/azusakawa/logical-idea-mind-map/issues) 回報。

## 授權

專案原始碼的使用條件以儲存庫根目錄的 `LICENSE` 為準。內附的 Noto Sans TC 字型依其 [SIL Open Font License](skills/structuring-logical-ideas/assets/OFL.txt) 提供，字型授權不會改變專案其他檔案的授權條件。

