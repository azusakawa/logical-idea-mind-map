import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = REPO_ROOT / "skills" / "structuring-logical-ideas"
VALIDATOR = SKILL_DIR / "scripts" / "validate_report.py"
RENDERER = SKILL_DIR / "scripts" / "render_report.py"


def report_text(*, nested: bool = True) -> str:
    summary = "本構想以可逆的小規模驗證作為起點，先盤點決策背景、利害關係人、時程與資源，再把未知條件轉成可量測假設。核心主張是先用明確範圍與停止門檻驗證價值，不以展示效果取代真實成果。執行時由單一決策者負責取捨，跨部門角色分別提供資料、風險與操作證據。推論鏈從投入、機制、中介結果一路連到最終成效，並同步記錄反向因果與外部干擾。方案用互斥且完整的理由拆解，再以試點案例驗證。若品質、成本與風險同時達標才擴大；任一底線失守便回退修正。對決策層強調價值與風險，對執行層說明責任與步驟，最後用領先指標、結果指標與固定檢查點持續校正。"
    if nested:
        mindmap = """- SCQA
  - S｜Situation（情境）：[已知] 使用者輸入顯示目前需要作出試點選擇。
  - C｜Complication（衝突）：[未知] 效益與風險可能並存，基準尚未取得。
  - Q｜Question（問題）：如何用可逆方式驗證？
  - A｜Answer（解答）：[假設] 先試點再決定擴大。
    - PREP
      - P1｜Point（主張）：[假設] 採分階段試點。
      - R｜Reason（理由）：[假設] 可把不確定性轉成證據。
        - 金字塔原理（MECE；分類準則：決策條件）
          - 核心結論：[待驗證] 只有價值、可行性與風險條件皆達標才擴大。
            - 次級論點 1｜價值：[待驗證] 完成率達標才能支持擴大。
              - 底層事實：[待驗證] 以完成率檢驗試點是否有價值。
            - 次級論點 2｜可行性：[待驗證] 記錄完整且流程時間可接受才能擴大。
              - 底層事實：[待驗證] 以流程時間與記錄完整度檢驗可行性。
            - 次級論點 3｜風險：[待驗證] 重大事件為零且能及時回退才能擴大。
              - 底層事實：[待驗證] 以重大事件與回退時間檢驗風險。
      - E｜Example（案例）
        - STAR｜驗證設計
          - S｜Situation（情境）：[未知] 代表性流程尚未取得基準。
          - T｜Task（任務）：[待驗證] 在四週內取得完成率與風險證據。
          - A｜Action（行動）：[假設] 執行對照試點並逐週記錄資料。
          - R｜Result（結果）：[待驗證] 第四週完成率至少 80% 且重大風險為 0 才擴大，否則停止。
      - P2｜Point（重申）：[假設] 以四週證據決定停止或擴大。"""
    else:
        mindmap = """- SCQA
  - S｜Situation（情境）：目前需要作出選擇。
  - C｜Complication（衝突）：效益與風險並存。
  - Q｜Question（問題）：如何驗證？
  - A｜Answer（解答）：先試點。
- PREP
  - P1｜Point（主張）：採分階段試點。
  - R｜Reason（理由）：降低風險。
- 金字塔原理（MECE）
  - 核心結論：達標才擴大。
- STAR｜驗證設計
  - S｜Situation（情境）：尚未驗證。
  - T｜Task（任務）：取得證據。
  - A｜Action（行動）：執行試點。
  - R｜Result（結果）：預期達標。"""
    return f"""# 邏輯構想測試報告

## 1. 主題相關資訊

### 主題識別

- 主題／專案名稱：測試構想
- 背景：[已知] 使用者於 2026-10-02 的本次輸入要求評估一項構想。
- 觸發事件：[已知] 使用者提出是否啟動試點的決策需求；來源為本次輸入。
- 目前狀態：[未知] 尚未啟動，現況基線亦未取得。

### 決策題與分析範圍

- 核心決策題：專案贊助人是否應核准四週可逆試點，並依門檻決定是否擴大？
- 分析目的：支援試點啟動、停止或擴大的決策。
- 納入範圍：單一代表性流程、參與團隊及四週試點結果。
- 排除範圍：永久上線、全面推廣及試點以外的流程。
- 時間尺度：啟動前至第四週結案決策。
- 適用情境：流程可回退且能取得一致紀錄時。

### 條件限制

- 關鍵時點／期限：[假設] 核准後四週完成試點並決策。
- 可用資源：[假設] 專案經理、參與團隊、流程紀錄與風險通報權限。
- 硬限制：[假設] 重大風險事件必須為零，且方案可立即回退。
- 可調整條件：[假設] 試點樣本、紀錄頻率與擴大節奏可依證據調整。

### 利害關係人概況

| 主要角色 | 關切 | 影響 | 初步權責 |
|---|---|---|---|
| 專案贊助人 | 價值與風險 | 承擔預算與決策責任 | 核准、停止或擴大 |
| 專案經理 | 可執行性與證據品質 | 承擔排程與資料品質 | 執行、量測與通報 |

### 資料來源清單

| 來源 ID | 資訊／主張 | 證據狀態 | 來源／輸入位置 | 日期／版本 | 與決策的關聯 |
|---|---|---|---|---|---|
| SRC-01 | 需要評估測試構想 | [已知] | 使用者本次輸入 | 2026-10-02 | 定義主題與決策需求 |

### 資訊缺口

| 缺口問題 | 證據狀態 | 對決策的影響 | 補證方式 | 責任角色 | 期限／觸發點 |
|---|---|---|---|---|---|
| 現況完成率與重大事件基準為何？ | [未知] | 影響門檻比較與擴大決定 | 第一週建立一致基準 | 專案經理 | 試點第一週結束前 |

## 2. 300 字邏輯構想摘要

{summary}

## 3. 重要關鍵字與變數

| 統一名稱 | 操作型定義 | 近義詞／易混淆詞 | 本分析採用的用法 | 證據狀態／來源 |
|---|---|---|---|---|
| 可逆試點 | 可在停止門檻觸發後回復原狀的限時驗證 | 正式上線、全面推廣 | 僅指四週且可停止的驗證 | [假設] 本次分析定義 |

#### 變數 V1｜完成率

- 角色：結果
- 定義／單位或尺度：成功完成數除以總數，百分比。
- 已知值或範圍：[未知] 第一週建立。
- 預期方向：越高越好。
- 可觀測方式：每週由流程紀錄計算。
- 證據狀態／來源：[待驗證] 由 A1 取得。

## 4. 核心決策者或主體

- 最終決策者／共同決策機制：[假設] 專案贊助人，擁有試點啟停權。
- 待決事項：是否核准四週試點，以及達標後是否擴大。
- 核心目標：以可控風險取得足以決策的完成率證據。
- 決策權限：可核准、停止或擴大試點。
- 可支配資源：[假設] 四週工時、流程紀錄與風險通報權限。
- 限制：[未知] 現況基準尚未取得。
- 誘因：擴大有效方案，同時避免放大風險。
- 決策時點：第 0 日核准試點，第 4 週核准停止或擴大。
- 不可逆程度：低，因試點可回退。

| 角色 | 與決策的關係 | 權限與責任 | 受益 | 成本／風險承擔 | 參與時點／方式 |
|---|---|---|---|---|---|
| 專案經理 | 執行 | 排程、收集資料與升級風險 | 取得清楚決策 | 執行與品質風險 | 全程週會 |

- 主要受益者：使用者，因有效流程會得到擴大。
- 主要成本／風險承擔者：專案贊助人承擔預算，營運單位承擔品質風險。

## 5. 核心論點（Thesis）

**[假設] 專案贊助人應核准四週可逆試點，只在完成率與風險門檻同時達標時擴大。**

| 論證欄位 | 內容 | 證據狀態／來源 |
|---|---|---|
| 主要理由 | 可逆試點能以有限暴險取得真實流程證據 | [假設] 本次推論 |
| 必要條件 | 團隊能持續紀錄分母、風險事件與成本 | [待驗證] A1 |
| 適用邊界 | 只適用於四週、可回退的單一流程試點 | [假設] 本次範圍 |
| 反轉／失效條件 | 試點不可回退或無法取得可比基準時不啟動 | [待驗證] 啟動前確認 |

- 信心水準：[假設] 中等，因基準值尚未取得。
- 信心依據／證據狀態／來源：[未知] 基準值未取得，由 A1 補齊。

## 6. 關鍵概念、定義與前提邊界

#### 概念 C1｜試點

- 操作型定義／判定標準：受控範圍內的四週驗證。
- 定義來源或本次假設：[假設] 本次分析採用。
- 納入範圍：單一代表性流程與參與團隊。
- 排除範圍：永久上線與全面擴大。
- 依賴項：流程可回退且資料可取得。
- 失效條件：無法回退或無法建立分母。
- 證據狀態／來源：[假設] 本次分析定義。

| 項目 | 採用慣例 | 來源／理由 | 證據狀態 |
|---|---|---|---|
| 完成率 | 成功完成數除以應完成總數 | 保持分母一致 | [假設] |

## 7. 因果關係與推論路徑

整體路徑：四週試點 → 統一紀錄機制 → 可比紀錄 → 機制判斷 → 擴大決策

### 連結 L1｜四週試點 → 統一紀錄機制

- 原因 → 結果與方向：四週試點執行增加 → 統一紀錄機制形成。
- 時序／延遲：啟動後逐週產生紀錄。
- 作用機制：統一分母與欄位後可比較。
- 證據狀態／來源：[待驗證] A1 逐週紀錄。
- 成立條件／依賴：分母一致且無重大流程變更。
- 替代解釋／干擾變數：人力與需求波動也會影響記錄。
- 反證觀察：試點完成但記錄缺失時削弱連結。
- 驗證方法／責任角色／時點：檢查欄位完整率；專案經理；每週。

### 連結 L2｜統一紀錄機制 → 可比紀錄

- 原因 → 結果與方向：統一紀錄機制穩定 → 可比紀錄增加。
- 時序／延遲：累積至第四週後判斷。
- 作用機制：紀錄使結果可與基準比較。
- 證據狀態／來源：[待驗證] A1 結案報告。
- 成立條件／依賴：基準可比且指標定義一致。
- 替代解釋／干擾變數：外部需求變化可同時改變結果。
- 反證觀察：調整後與基準無差異會削弱機制。
- 驗證方法／責任角色／時點：比較基準與試點；專案經理；第四週。

### 連結 L3｜可比紀錄 → 機制判斷

- 原因 → 結果與方向：可比紀錄增加 → 有效機制可辨識性提高。
- 時序／延遲：累積至第四週後判斷。
- 作用機制：紀錄使結果可與基準比較。
- 證據狀態／來源：[待驗證] A1 結案報告。
- 成立條件／依賴：基準可比且指標定義一致。
- 替代解釋／干擾變數：外部需求變化可同時改變結果。
- 反證觀察：調整後與基準無差異會削弱機制。
- 驗證方法／責任角色／時點：比較基準與試點；專案經理；第四週。

### 連結 L4｜機制判斷 → 擴大決策

- 原因 → 結果與方向：機制判斷的信心提高 → 擴大決策可行性提高。
- 時序／延遲：第四週完成判斷後才決策。
- 作用機制：達標證據降低擴大的下行風險。
- 證據狀態／來源：[待驗證] A1 決策包。
- 成立條件／依賴：價值與風險門檻同時達標。
- 替代解釋／干擾變數：贊助人的風險偏好可改變決策。
- 反證觀察：證據達標但仍無法回退時不應擴大。
- 驗證方法／責任角色／時點：門檻審查；專案贊助人；第四週。

## 8. 重複考量與潛在衝突

| 考量點 | 重複位置／衝突雙方 | 影響 | 目前狀態 | 處理原則／所需證據 | 責任角色與時點 |
|---|---|---|---|---|---|
| 速度與品質 | 快速擴大 vs. 先驗證風險 | 過早擴大可能放大錯誤 | 未解 | 以 M1 與停止門檻取得證據 | 專案贊助人；第 4 週 |

## 9. 一句話總結

用可逆試點把構想轉成可檢驗的決策。

## 10. 分眾解釋

| 受眾 | 應回答的問題 | 表達重點 | 建議說法 |
|---|---|---|---|
| 決策層 | 是否值得批准 | 價值、成本、期限與主要風險 | 先批准四週可逆試點，只在完成率與風險門檻同時達標時擴大。 |
| 管理／專業層 | 如何取捨與治理 | 機制、證據、依賴、指標與例外 | 統一分母並逐週審查干擾因素，關鍵紀錄缺失時不做擴大決定。 |
| 執行層 | 誰何時做什麼 | 任務、順序、交付物、驗收與升級 | 專案經理逐週收集記錄，第四週交付可複核的基準、結果與風險清單。 |
| 一般受眾 | 這與我有何關係 | 問題、做法、影響與成效 | 先像試用新路線一樣小範圍測試，確認有用又安全後才讓更多人使用。 |

## 11. 行動方案與驗證指標

### 行動 A1｜執行四週可逆試點

- 行動內容：建立基準後執行四週可回退試點並形成決策包。
- 依據：連到 Thesis 與因果鏈的試點投入節點。
- 責任人：[假設] 專案經理，由贊助人在第 0 日指定姓名。
- 期限／優先序：核准後四週內完成；最高，因後續決策需要這些證據。
- 依賴／資源：流程紀錄、團隊工時與風險通報權限。
- 交付物／驗收：交付基準、週報與結案報告，欄位完整率達 95%。
- 領先指標：L1 紀錄完整率；完整欄位數除以應有欄位數，百分比；越高越好；來源為流程系統紀錄。
- 結果指標：R1 完成率；成功完成數除以應完成總數，百分比；越高越好；來源為流程系統紀錄。
- 基準值：[未知] L1 與 R1 由 A1 在第一週建立。
- 目標／護欄門檻：[待驗證] 第四週 L1 至少 95%、R1 至少 80%，重大風險為 0。
- 量測頻率／檢查點：每週匯總；第四週結案會議。
- 決策規則：專案贊助人判讀；全數達標時擴大，未達或護欄失守時停止並修正。

## 12. 複合模型思維導圖

{mindmap}
"""


class SkillToolTests(unittest.TestCase):
    def run_validator(self, content: str):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "report.md"
            path.write_text(content, encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(VALIDATOR), str(path)],
                text=True,
                capture_output=True,
                check=False,
            )

    def test_validator_accepts_complete_nested_report(self):
        result = self.run_validator(report_text(nested=True))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PASS", result.stdout)

    def test_validator_rejects_sibling_models(self):
        result = self.run_validator(report_text(nested=False))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("PREP must be nested under SCQA Answer", result.stdout + result.stderr)

    def test_validator_rejects_changed_fixed_title(self):
        content = report_text(nested=True).replace(
            "## 5. 核心論點（Thesis）", "## 5. 我的建議"
        )
        result = self.run_validator(content)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("section 5 title must be", result.stdout + result.stderr)

    def test_validator_rejects_unresolved_template_placeholder(self):
        content = report_text(nested=True).replace(
            "[假設] 專案贊助人應核准四週可逆試點，只在完成率與風險門檻同時達標時擴大。",
            "<填入核心主張>",
        )
        result = self.run_validator(content)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unresolved angle-bracket placeholder", result.stdout + result.stderr)

    def test_validator_rejects_multiple_sentence_summary_line(self):
        content = report_text(nested=True).replace(
            "用可逆試點把構想轉成可檢驗的決策。",
            "用可逆試點把構想轉成可檢驗的決策。達標後再擴大。",
        )
        result = self.run_validator(content)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("section 9 must contain exactly one sentence", result.stdout + result.stderr)

    def test_validator_counts_spaces_in_english_summary(self):
        english_summary = (
            "Current context is clear. But risk and a gap matter. The decision "
            "question is whether we should approve a pilot. We recommend it "
            "because a test gives evidence. The action is to implement it. "
            "Verification uses a metric, a threshold, and a stop rule. We act "
            "on data. We act on data. We act on data."
        )
        self.assertGreaterEqual(len(english_summary), 250)
        self.assertLessEqual(len(english_summary), 350)
        self.assertLess(len(english_summary.replace(" ", "")), 250)
        content = report_text(nested=True)
        start = content.index("## 2. 300 字邏輯構想摘要")
        paragraph_start = content.index("\n\n", start) + 2
        section_end = content.index("\n\n## 3.", paragraph_start)
        content = content[:paragraph_start] + english_summary + content[section_end:]
        result = self.run_validator(content)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_validator_rejects_sentence_without_terminal_punctuation(self):
        content = report_text(nested=True).replace(
            "用可逆試點把構想轉成可檢驗的決策。",
            "Use a reversible pilot to turn the idea into a testable decision",
        )
        result = self.run_validator(content)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "section 9 must end with sentence-ending punctuation",
            result.stdout + result.stderr,
        )

    def test_validator_rejects_empty_required_fields_in_sections_3_to_8(self):
        mutations = [
            (
                "- 角色：結果",
                "- 角色：",
                "section 3 variable V1 field 角色 must contain substantive content",
            ),
            (
                "- 決策權限：可核准、停止或擴大試點。",
                "- 決策權限：",
                "section 4 field 決策權限 must contain substantive content",
            ),
            (
                "| 反轉／失效條件 | 試點不可回退或無法取得可比基準時不啟動 |",
                "| 反轉／失效條件 |  |",
                "section 5 row has empty field 內容",
            ),
            (
                "- 操作型定義／判定標準：受控範圍內的四週驗證。",
                "- 操作型定義／判定標準：",
                "section 6 concept C1 field 操作型定義／判定標準 must contain substantive content",
            ),
            (
                "- 作用機制：統一分母與欄位後可比較。",
                "- 作用機制：",
                "section 7 link L1 field 作用機制 must contain substantive content",
            ),
            (
                "| 速度與品質 | 快速擴大 vs. 先驗證風險 |",
                "| 速度與品質 |  |",
                "section 8 row has empty field 重複位置／衝突雙方",
            ),
        ]
        for old, new, expected in mutations:
            with self.subTest(expected=expected):
                result = self.run_validator(report_text(nested=True).replace(old, new))
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected, result.stdout + result.stderr)

    def test_validator_rejects_audience_without_explanation(self):
        content = report_text(nested=True).replace(
            "| 決策層 | 是否值得批准 | 價值、成本、期限與主要風險 | 先批准四週可逆試點，只在完成率與風險門檻同時達標時擴大。 |",
            "| 決策層 | 是否值得批准 | 價值、成本、期限與主要風險 |  |",
        )
        result = self.run_validator(content)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "section 10 audience 決策層 must contain substantive explanation",
            result.stdout + result.stderr,
        )

    def test_validator_checks_every_action_and_metric(self):
        content = report_text(nested=True).replace(
            "- 期限／優先序：核准後四週內完成；最高，因後續決策需要這些證據。\n", ""
        ).replace(
            "- 量測頻率／檢查點：每週匯總；第四週結案會議。\n",
            "",
        )
        result = self.run_validator(content)
        self.assertNotEqual(result.returncode, 0)
        output = result.stdout + result.stderr
        self.assertIn("section 11 action A1 is missing field 期限／優先序", output)
        self.assertIn("section 11 action A1 is missing field 量測頻率／檢查點", output)

    def test_validator_rejects_known_information_without_source(self):
        content = report_text(nested=True).replace(
            "| SRC-01 | 需要評估測試構想 | [已知] | 使用者本次輸入 | 2026-10-02 | 定義主題與決策需求 |",
            "| SRC-01 | 需要評估測試構想 | [已知] | 未記錄 | 2026-10-02 | 定義主題與決策需求 |",
        )
        result = self.run_validator(content)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "section 1 source row must identify a recognizable source or input location",
            result.stdout + result.stderr,
        )

    def test_validator_rejects_explicitly_nonexistent_source(self):
        content = report_text(nested=True).replace(
            "| SRC-01 | 需要評估測試構想 | [已知] | 使用者本次輸入 | 2026-10-02 | 定義主題與決策需求 |",
            "| SRC-01 | 需要評估測試構想 | [已知] | 本次輸入從未存在，也沒有任何可查核紀錄 | 2026-10-02 | 定義主題與決策需求 |",
        )
        result = self.run_validator(content)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "section 1 source row must identify a recognizable source or input location",
            result.stdout + result.stderr,
        )

    def test_validator_rejects_missing_named_report_as_source(self):
        content = report_text(nested=True).replace(
            "| SRC-01 | 需要評估測試構想 | [已知] | 使用者本次輸入 | 2026-10-02 | 定義主題與決策需求 |",
            "| SRC-01 | 需要評估測試構想 | [已知] | 沒有這份結案報告可供查核 | 2026-10-02 | 定義主題與決策需求 |",
        )
        result = self.run_validator(content)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "section 1 source row must identify a recognizable source or input location",
            result.stdout + result.stderr,
        )

    def test_validator_rejects_content_free_summary(self):
        content = report_text(nested=True)
        start = content.index("## 2. 300 字邏輯構想摘要")
        paragraph_start = content.index("\n\n", start) + 2
        section_end = content.index("\n\n## 3.", paragraph_start)
        content = content[:paragraph_start] + ("甲" * 260) + content[section_end:]
        result = self.run_validator(content)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("section 2 summary must cover context", result.stdout + result.stderr)

    def test_validator_rejects_keyword_stuffed_summary(self):
        content = report_text(nested=True)
        stuffed = ("背景但風險是否決策應建議因為行動驗證指標門檻，" * 13)[:300]
        self.assertGreaterEqual(len(stuffed), 250)
        self.assertLessEqual(len(stuffed), 350)
        start = content.index("## 2. 300 字邏輯構想摘要")
        paragraph_start = content.index("\n\n", start) + 2
        section_end = content.index("\n\n## 3.", paragraph_start)
        content = content[:paragraph_start] + stuffed + content[section_end:]
        result = self.run_validator(content)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("excessively repetitive or keyword-stuffed", result.stdout + result.stderr)

    def test_validator_rejects_repeated_long_summary_cycle(self):
        cycle = (
            "背景目前團隊面臨資源限制，但風險與效益仍有缺口；核心決策問題是是否核准試點？"
            "建議先啟動可逆試點，因為分階段行動能降低暴險並取得證據。行動包括建立基準、"
            "指定責任人與逐週量測，驗證使用完成率、成本、重大事件與停止門檻；全部達標才擴大，"
            "未達則停止修正後再複驗。"
        )
        stuffed = cycle * 2
        self.assertGreaterEqual(len(stuffed), 250)
        self.assertLessEqual(len(stuffed), 350)
        content = report_text(nested=True)
        start = content.index("## 2. 300 字邏輯構想摘要")
        paragraph_start = content.index("\n\n", start) + 2
        section_end = content.index("\n\n## 3.", paragraph_start)
        content = content[:paragraph_start] + stuffed + content[section_end:]
        result = self.run_validator(content)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("repeated long cycle or copied passage", result.stdout + result.stderr)

    def test_validator_rejects_cross_section_direction_conflict(self):
        content = report_text(nested=True).replace(
            "**[假設] 專案贊助人應核准四週可逆試點，只在完成率與風險門檻同時達標時擴大。**",
            "**[假設] 專案贊助人不應核准四週可逆試點，也不應在門檻達標時擴大。**",
        )
        result = self.run_validator(content)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "explicitly contradicts the adoption/rejection direction of the Thesis",
            result.stdout + result.stderr,
        )

    def test_validator_rejects_buyao_negated_direction_conflict(self):
        content = report_text(nested=True).replace(
            "用可逆試點把構想轉成可檢驗的決策。",
            "專案贊助人不要核准四週可逆試點，應直接停止整個計畫。",
        )
        result = self.run_validator(content)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "explicitly contradicts the adoption/rejection direction of the Thesis",
            result.stdout + result.stderr,
        )

    def test_validator_rejects_undefined_source_id_outside_star(self):
        content = report_text(nested=True).replace(
            "| 主要理由 | 可逆試點能以有限暴險取得真實流程證據 | [假設] 本次推論 |",
            "| 主要理由 | 可逆試點能以有限暴險取得真實流程證據 | [已知] 依據 SRC-99 |",
        )
        result = self.run_validator(content)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("report references undefined source ID(s): SRC-99", result.stdout + result.stderr)

    def test_validator_rejects_incomplete_section_one(self):
        content = report_text(nested=True).replace(
            "- 可用資源：[假設] 專案經理、參與團隊、流程紀錄與風險通報權限。\n",
            "",
        )
        result = self.run_validator(content)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("section 1 is missing field 可用資源", result.stdout + result.stderr)

    def test_validator_rejects_unlabeled_section_one_context(self):
        content = report_text(nested=True).replace(
            "- 硬限制：[假設] 重大風險事件必須為零，且方案可立即回退。",
            "- 硬限制：重大風險事件必須為零，且方案可立即回退。",
        )
        result = self.run_validator(content)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "section 1 field 硬限制 must include an evidence status label",
            result.stdout + result.stderr,
        )

    def test_validator_rejects_empirical_star_result_without_source(self):
        content = report_text(nested=True)
        replacements = {
            "STAR｜驗證設計": "STAR｜實證案例",
            "[未知] 代表性流程尚未取得基準": "[已知] 過往案例有完整基準",
            "[待驗證] 在四週內取得完成率與風險證據": "[已知] 團隊的任務是取得完成率與風險證據",
            "[假設] 執行對照試點並逐週記錄資料": "[已知] 團隊執行對照試點並逐週記錄資料",
            "[待驗證] 第四週完成率至少 80% 且重大風險為 0 才擴大，否則停止": "[已知] 第四週完成率為 82% 且重大風險為 0",
        }
        for old, new in replacements.items():
            content = content.replace(old, new)
        result = self.run_validator(content)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "STAR｜實證案例 S must include a recognizable source or source ID",
            result.stdout + result.stderr,
        )

    def test_validator_rejects_fabricated_empirical_star(self):
        content = report_text(nested=True)
        replacements = {
            "STAR｜驗證設計": "STAR｜實證案例",
            "[未知] 代表性流程尚未取得基準": "[已知] 過往基準完整，來源 SRC-99",
            "[待驗證] 在四週內取得完成率與風險證據": "[已知] 團隊負責取得證據，來源 SRC-99",
            "[假設] 執行對照試點並逐週記錄資料": "[已知] 團隊完成對照試點，來源 SRC-99",
            "[待驗證] 第四週完成率至少 80% 且重大風險為 0 才擴大，否則停止": "[已知] 虛構公司營收提高 999%，來源不存在",
        }
        for old, new in replacements.items():
            content = content.replace(old, new)
        result = self.run_validator(content)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "STAR｜實證案例 R contains an explicit fabrication marker",
            result.stdout + result.stderr,
        )

    def test_validator_rejects_empirical_star_with_ghost_source_id(self):
        content = report_text(nested=True)
        replacements = {
            "STAR｜驗證設計": "STAR｜實證案例",
            "[未知] 代表性流程尚未取得基準": "[已知] 過往基準完整，來源 SRC-99；該紀錄從未存在",
            "[待驗證] 在四週內取得完成率與風險證據": "[已知] 團隊接受任務，來源 SRC-99；該紀錄從未存在",
            "[假設] 執行對照試點並逐週記錄資料": "[已知] 團隊完成試點，來源 SRC-99；該紀錄從未存在",
            "[待驗證] 第四週完成率至少 80% 且重大風險為 0 才擴大，否則停止": "[已知] 完成率為 82%，來源 SRC-99；該紀錄從未存在",
        }
        for old, new in replacements.items():
            content = content.replace(old, new)
        result = self.run_validator(content)
        self.assertNotEqual(result.returncode, 0)
        output = result.stdout + result.stderr
        self.assertIn("must include a recognizable source or source ID", output)
        self.assertIn("references undefined source ID(s): SRC-99", output)

    def test_validator_rejects_empirical_star_citing_unproduced_defined_source(self):
        content = report_text(nested=True)
        replacements = {
            "STAR｜驗證設計": "STAR｜實證案例",
            "[未知] 代表性流程尚未取得基準": "[已知] 過往基準完整，依據 SRC-01，但該結案報告尚未產生",
            "[待驗證] 在四週內取得完成率與風險證據": "[已知] 團隊接受任務，依據 SRC-01，但該結案報告尚未產生",
            "[假設] 執行對照試點並逐週記錄資料": "[已知] 團隊完成試點，依據 SRC-01，但該結案報告尚未產生",
            "[待驗證] 第四週完成率至少 80% 且重大風險為 0 才擴大，否則停止": "[已知] 完成率為 82%，依據 SRC-01，但該結案報告尚未產生",
        }
        for old, new in replacements.items():
            content = content.replace(old, new)
        result = self.run_validator(content)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "[已知] statement cannot rely on an explicitly missing or fabricated source",
            result.stdout + result.stderr,
        )

    def test_validator_rejects_semantically_empty_model_nodes(self):
        content = report_text(nested=True).replace(
            "S｜Situation（情境）：[已知] 使用者輸入顯示目前需要作出試點選擇。",
            "S｜Situation（情境）：",
        )
        result = self.run_validator(content)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "SCQA Situation must contain substantive content",
            result.stdout + result.stderr,
        )

    def test_validator_requires_model_evidence_labels(self):
        content = report_text(nested=True).replace(
            "底層事實：[待驗證] 以完成率檢驗試點是否有價值。",
            "底層事實：以完成率檢驗試點是否有價值。",
        )
        result = self.run_validator(content)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "Pyramid bottom fact must include an evidence status label",
            result.stdout + result.stderr,
        )

    def test_validator_rejects_one_block_for_an_entire_causal_chain(self):
        content = report_text(nested=True)
        start = content.index("## 7. 因果關係與推論路徑")
        body_start = content.index("\n\n", start) + 2
        end = content.index("\n\n## 8.", body_start)
        old_style = """整體路徑：投入 → 機制 → 輸出 → 結果

| 前提／投入 | 作用機制 | 直接輸出 | 中介結果 | 最終結果 | 證據狀態 |
|---|---|---|---|---|---|
| 試點 | 統一流程 | 可比記錄 | 機制判斷 | 擴大決策 | [待驗證] |"""
        content = content[:body_start] + old_style + content[end:]
        result = self.run_validator(content)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "section 7 must contain at least one ### 連結",
            result.stdout + result.stderr,
        )

    def test_validator_rejects_causal_link_unrelated_to_path(self):
        content = report_text(nested=True).replace(
            "### 連結 L2｜統一紀錄機制 → 可比紀錄",
            "### 連結 L2｜天氣變化 → 咖啡價格",
        )
        result = self.run_validator(content)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "does not match the corresponding adjacent node in 整體路徑",
            result.stdout + result.stderr,
        )

    def test_validator_rejects_causal_body_unrelated_to_title(self):
        content = report_text(nested=True).replace(
            "- 原因 → 結果與方向：統一紀錄機制穩定 → 可比紀錄增加。",
            "- 原因 → 結果與方向：氣溫提高 → 咖啡售價降低。",
        )
        result = self.run_validator(content)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "原因 → 結果與方向 does not match its link title",
            result.stdout + result.stderr,
        )

    def test_validator_rejects_negated_causal_body(self):
        content = report_text(nested=True).replace(
            "- 原因 → 結果與方向：四週試點執行增加 → 統一紀錄機制形成。",
            "- 原因 → 結果與方向：取消四週試點 → 刪除統一紀錄機制。",
        )
        result = self.run_validator(content)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "原因 → 結果與方向 does not match its link title",
            result.stdout + result.stderr,
        )

    def test_validator_rejects_prohibited_causal_title_and_body(self):
        content = report_text(nested=True).replace(
            "### 連結 L1｜四週試點 → 統一紀錄機制",
            "### 連結 L1｜禁止四週試點 → 廢除統一紀錄機制",
        ).replace(
            "- 原因 → 結果與方向：四週試點執行增加 → 統一紀錄機制形成。",
            "- 原因 → 結果與方向：禁止四週試點 → 廢除統一紀錄機制。",
        )
        result = self.run_validator(content)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "does not match the corresponding adjacent node in 整體路徑",
            result.stdout + result.stderr,
        )

    def test_validator_rejects_separate_metric_block(self):
        content = report_text(nested=True).replace(
            "\n\n## 12. 複合模型思維導圖",
            "\n\n### 指標 M9｜舊式獨立指標\n\n- 定義：不應獨立。\n\n## 12. 複合模型思維導圖",
        )
        result = self.run_validator(content)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "separate 指標 blocks are not allowed",
            result.stdout + result.stderr,
        )

    def test_validator_rejects_inverted_guardrail_decision_rule(self):
        content = report_text(nested=True).replace(
            "專案贊助人判讀；全數達標時擴大，未達或護欄失守時停止並修正。",
            "專案贊助人判讀；全數達標時停止並修正，未達或護欄失守時直接全面擴大。",
        )
        result = self.run_validator(content)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "decision rule must not expand after a failed threshold or guardrail",
            result.stdout + result.stderr,
        )

    def test_validator_rejects_delayed_enablement_after_guardrail_failure(self):
        content = report_text(nested=True).replace(
            "專案贊助人判讀；全數達標時擴大，未達或護欄失守時停止並修正。",
            "專案贊助人判讀；全數達標時繼續維持暫停狀態，未達或護欄失守時先調整文案，隨即向所有單位啟用。",
        )
        result = self.run_validator(content)
        self.assertNotEqual(result.returncode, 0)
        output = result.stdout + result.stderr
        self.assertIn("must not remain stopped or paused after passing", output)
        self.assertIn("must not adopt, enable, or expand after a failed threshold or guardrail", output)

    def test_validator_rejects_bare_secondary_category(self):
        content = report_text(nested=True).replace(
            "次級論點 1｜價值：[待驗證] 完成率達標才能支持擴大。",
            "次級論點 1｜價值",
        )
        result = self.run_validator(content)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "Pyramid 次級論點 must contain substantive content",
            result.stdout + result.stderr,
        )

    def test_validator_rejects_duplicate_mece_claims(self):
        content = report_text(nested=True).replace(
            "次級論點 2｜可行性：[待驗證] 記錄完整且流程時間可接受才能擴大。",
            "次級論點 2｜可行性：[待驗證] 完成率達標才能支持擴大。",
        ).replace(
            "底層事實：[待驗證] 以流程時間與記錄完整度檢驗可行性。",
            "底層事實：[待驗證] 以完成率檢驗試點是否有價值。",
        )
        result = self.run_validator(content)
        self.assertNotEqual(result.returncode, 0)
        output = result.stdout + result.stderr
        self.assertIn("must not repeat the same substantive claim", output)
        self.assertIn("must not duplicate the same evidence claim", output)

    def test_validator_rejects_child_under_prep_point(self):
        content = report_text(nested=True).replace(
            "      - R｜Reason（理由）：[假設] 可把不確定性轉成證據。",
            "        - 獨立替代方案：[已知] 無須進行任何驗證便可全面上線。\n"
            "      - R｜Reason（理由）：[假設] 可把不確定性轉成證據。",
        )
        result = self.run_validator(content)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("PREP Point P1 must not contain child nodes", result.stdout + result.stderr)

    def test_validator_requires_mece_classification_criterion(self):
        content = report_text(nested=True).replace(
            "金字塔原理（MECE；分類準則：決策條件）",
            "金字塔原理（MECE）",
        )
        result = self.run_validator(content)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "Pyramid label must state a non-empty 分類準則",
            result.stdout + result.stderr,
        )

    def test_validator_requires_example_semantics(self):
        content = report_text(nested=True).replace(
            "[待驗證] 第四週完成率至少 80% 且重大風險為 0 才擴大，否則停止",
            "[待驗證] 結果待觀察",
        )
        result = self.run_validator(content)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "STAR｜驗證設計 Result must state a target threshold and decision rule",
            result.stdout + result.stderr,
        )

    def test_validator_rejects_duplicate_star(self):
        star = """        - STAR｜驗證設計
          - S｜Situation（情境）：[未知] 代表性流程尚未取得基準。
          - T｜Task（任務）：[待驗證] 在四週內取得完成率與風險證據。
          - A｜Action（行動）：[假設] 執行對照試點並逐週記錄資料。
          - R｜Result（結果）：[待驗證] 第四週完成率至少 80% 且重大風險為 0 才擴大，否則停止。"""
        content = report_text(nested=True).replace(star, star + "\n" + star)
        result = self.run_validator(content)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("section 12 must contain exactly one STAR block", result.stdout + result.stderr)

    def test_validator_rejects_extra_example_child(self):
        content = report_text(nested=True).replace(
            "      - E｜Example（案例）\n        - STAR｜驗證設計",
            "      - E｜Example（案例）\n        - 額外框架：不應出現在此層。\n        - STAR｜驗證設計",
        )
        result = self.run_validator(content)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "PREP Example may contain only the single STAR block as a child",
            result.stdout + result.stderr,
        )

    def test_validator_rejects_extra_answer_child(self):
        content = report_text(nested=True).replace(
            "    - PREP\n", "    - 額外模型：不應與 PREP 並列。\n    - PREP\n"
        )
        result = self.run_validator(content)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unexpected direct child under SCQA Answer", result.stdout + result.stderr)

    def test_renderer_creates_searchable_pdf(self):
        self.assertIsNotNone(importlib.util.find_spec("pypdf"))
        from pypdf import PdfReader

        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "report.md"
            output = Path(tmp) / "report.pdf"
            source.write_text(report_text(nested=True), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(RENDERER), str(source), str(output)],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue(output.exists())
            self.assertGreater(output.stat().st_size, 5_000)
            extracted = "\n".join(page.extract_text() or "" for page in PdfReader(output).pages)
            self.assertIn("邏輯構想測試報告", extracted)
            self.assertIn("SCQA", extracted)

    def test_validator_and_renderer_accept_utf8_bom_consistently(self):
        self.assertIsNotNone(importlib.util.find_spec("pypdf"))
        from pypdf import PdfReader

        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "report.md"
            output = Path(tmp) / "report.pdf"
            source.write_bytes(b"\xef\xbb\xbf" + report_text(nested=True).encode("utf-8"))
            validation = subprocess.run(
                [sys.executable, str(VALIDATOR), str(source)],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(validation.returncode, 0, validation.stdout + validation.stderr)
            rendering = subprocess.run(
                [sys.executable, str(RENDERER), str(source), str(output)],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(rendering.returncode, 0, rendering.stdout + rendering.stderr)
            extracted = "\n".join(page.extract_text() or "" for page in PdfReader(output).pages)
            self.assertIn("邏輯構想測試報告", extracted)


if __name__ == "__main__":
    unittest.main()
