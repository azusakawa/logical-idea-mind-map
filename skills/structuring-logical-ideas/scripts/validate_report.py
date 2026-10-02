#!/usr/bin/env python3
"""Validate the Markdown contract for a structured logical-ideas report."""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable


EXPECTED_SECTIONS = tuple(range(1, 13))
EXPECTED_TITLES = {
    1: "主題相關資訊",
    2: "300 字邏輯構想摘要",
    3: "重要關鍵字與變數",
    4: "核心決策者或主體",
    5: "核心論點（Thesis）",
    6: "關鍵概念、定義與前提邊界",
    7: "因果關係與推論路徑",
    8: "重複考量與潛在衝突",
    9: "一句話總結",
    10: "分眾解釋",
    11: "行動方案與驗證指標",
    12: "複合模型思維導圖",
}

SECTION_HEADING_RE = re.compile(
    r"^[ \t]{0,3}##(?!#)[ \t]+(?P<number>\d{1,2})"
    r"(?:(?:[.．、:：)）])[ \t]*|[ \t]+)"
    r"(?P<title>.*?)[ \t]*#*[ \t]*$"
)
FENCE_RE = re.compile(
    r"^[ \t]{0,3}(?P<fence>`{3,}|~{3,})(?P<info>.*)$"
)
BULLET_RE = re.compile(
    r"^(?P<indent>[ \t]*)(?P<marker>[-+*])[ \t]+(?P<text>.+?)\s*$"
)
H3_RE = re.compile(r"^[ \t]{0,3}###(?!#)[ \t]+(?P<title>.+?)[ \t]*#*[ \t]*$")
H4_RE = re.compile(r"^[ \t]{0,3}####(?!#)[ \t]+(?P<title>.+?)[ \t]*#*[ \t]*$")
EVIDENCE_LABEL_RE = re.compile(r"\[(?:已知|假設|未知|待驗證)\]")
SOURCE_ID_RE = re.compile(r"\bSRC[-_ ]?(?P<number>\d+)\b", flags=re.IGNORECASE)
SOURCE_CUE_RE = re.compile(
    r"(?:使用者(?:提供|輸入|說明)|本次(?:分析)?輸入|原始題目|"
    r"\bSRC[-_ ]?\d+\b|https?://|訪談(?:逐字稿|紀錄)?|會議紀錄|"
    r"系統紀錄|稽核紀錄|實驗紀錄|帳單|合約|資料集|公開資料|"
    r"(?:研究|財務|年度|月度|測試|結案)報告|來源文件|[\w./-]+\.(?:md|pdf|docx?|xlsx?|csv)|"
    r"\bsource\b|\bprovided by\b)",
    flags=re.IGNORECASE,
)
INVALID_SOURCE_RE = re.compile(
    r"(?:(?:來源|依據|引用)(?:文件)?\s*(?:為|[:：])?\s*"
    r"(?:不存在|虛構|杜撰|捏造|不明|未知|未提供|未記錄|未查核|"
    r"無|none|unknown|fictional|fabricated|made[ -]?up)|"
    r"(?:無來源|沒有來源|source unknown|source unavailable)|"
    r"(?:本次輸入|原始題目|紀錄|記錄|報告|文件|資料|來源|證據)"
    r"[^。；;]{0,20}(?:從未存在|並不存在|不存在|無法查核)|"
    r"(?:從未|從來沒有|沒有任何)[^。；;]{0,20}"
    r"(?:可查核)?(?:紀錄|記錄|報告|文件|資料|來源|證據)|"
    r"(?:沒有|並無|查無|找不到)\s*(?:這|該|此)?\s*(?:份|筆|項)?\s*"
    r"(?:結案|測試|研究|財務|年度|月度)?\s*"
    r"(?:紀錄|記錄|報告|文件|資料|來源|證據)|"
    r"(?:這|該|此)?\s*(?:份|筆|項)?\s*"
    r"(?:結案|測試|研究|財務|年度|月度)?\s*"
    r"(?:紀錄|記錄|報告|文件|資料|來源|證據)"
    r"[^。；;]{0,12}(?:尚未|還沒|未曾)\s*"
    r"(?:產生|建立|完成|取得|提供|發布|出爐))",
    flags=re.IGNORECASE,
)
FABRICATION_RE = re.compile(
    r"(?:虛構|杜撰|捏造|假造|不存在的?(?:公司|資料|測試|案例|來源)|"
    r"fictional|fabricated|made[ -]?up)",
    flags=re.IGNORECASE,
)
SUMMARY_CONTENT_CUES: tuple[tuple[str, str], ...] = (
    ("context", r"(?:背景|情境|目前|現況|起點|既有|本題|分析對象|已知|current|context|situation|today)"),
    ("tension", r"(?:但|然而|衝突|風險|限制|缺口|未知|不確定|尚無|不足|不能|未提供|but|yet|risk|constraint|gap|uncertain)"),
    ("decision question", r"(?:是否|如何|決策|決定|問題|whether|how|decision|question)"),
    ("Thesis", r"(?:建議|應|主張|採取|核准|先|recommend|should|propose|approve)"),
    ("reason", r"(?:因為|理由|因此|基於|所以|使得|使|能以|可讓|藉由|透過|because|reason|therefore|so that)"),
    ("action", r"(?:行動|執行|試點|建立|盤點|啟動|實施|校準|量測|分批|action|pilot|implement|launch)"),
    ("verification", r"(?:驗證|指標|門檻|量測|達標|停止|verify|metric|threshold|measure|pass|stop)"),
)


@dataclass(frozen=True)
class Heading:
    number: int
    line_index: int
    title: str

    @property
    def line_number(self) -> int:
        return self.line_index + 1


@dataclass
class Bullet:
    line_number: int
    indent: int
    text: str
    normalized: str
    parent: Bullet | None = None
    children: list[Bullet] = field(default_factory=list)


@dataclass(frozen=True)
class TableRow:
    line_number: int
    cells: tuple[str, ...]


@dataclass(frozen=True)
class MarkdownTable:
    line_number: int
    headers: tuple[str, ...]
    rows: tuple[TableRow, ...]


@dataclass(frozen=True)
class Subsection:
    line_number: int
    title: str
    body: tuple[str, ...]


@dataclass
class ValidationResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def error(self, message: str, line_number: int | None = None) -> None:
        if line_number is None:
            rendered = f"ERROR: {message}"
        else:
            rendered = f"ERROR line {line_number}: {message}"
        if rendered not in self.errors:
            self.errors.append(rendered)

    def warning(self, message: str, line_number: int | None = None) -> None:
        if line_number is None:
            rendered = f"WARNING: {message}"
        else:
            rendered = f"WARNING line {line_number}: {message}"
        if rendered not in self.warnings:
            self.warnings.append(rendered)


def _closing_fence(line: str, fence: str) -> bool:
    char = re.escape(fence[0])
    return bool(
        re.match(
            rf"^[ \t]{{0,3}}{char}{{{len(fence)},}}[ \t]*$",
            line,
        )
    )


def _scan_headings(lines: list[str]) -> list[Heading]:
    """Return numbered H2 headings, ignoring anything inside code fences."""
    headings: list[Heading] = []
    open_fence: str | None = None

    for index, line in enumerate(lines):
        if open_fence is not None:
            if _closing_fence(line, open_fence):
                open_fence = None
            continue

        fence_match = FENCE_RE.match(line)
        if fence_match:
            open_fence = fence_match.group("fence")
            continue

        heading_match = SECTION_HEADING_RE.match(line)
        if heading_match:
            headings.append(
                Heading(
                    number=int(heading_match.group("number")),
                    line_index=index,
                    title=heading_match.group("title").strip(),
                )
            )

    return headings


def _section_bodies(
    lines: list[str], headings: list[Heading]
) -> dict[int, tuple[Heading, list[str]]]:
    """Map the first occurrence of each section number to its body."""
    sections: dict[int, tuple[Heading, list[str]]] = {}
    for index, heading in enumerate(headings):
        if heading.number in sections:
            continue
        end = headings[index + 1].line_index if index + 1 < len(headings) else len(lines)
        sections[heading.number] = (
            heading,
            lines[heading.line_index + 1 : end],
        )
    return sections


def _visible_character_count(lines: Iterable[str]) -> int:
    """Approximate rendered prose length, including visible inter-word spaces."""
    text = "\n".join(lines)
    text = re.sub(r"<!--[\s\S]*?-->", "", text)
    text = re.sub(r"^[ \t]{0,3}(?:`{3,}|~{3,}).*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"!\[([^]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"\[([^]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(
        r"^[ \t]{0,3}(?:[-+*]|\d+[.)])[ \t]+",
        "",
        text,
        flags=re.MULTILINE,
    )
    text = re.sub(r"[*_~`#>|]", "", text)
    return len(re.sub(r"\s+", " ", text).strip())


def _summary_diversity_ratio(text: str) -> float:
    """Measure repeated-token stuffing without assuming one output language."""
    plain = _plain_text(text, remove_evidence=True).lower()
    cjk = "".join(re.findall(r"[\u3400-\u9fff]", plain))
    if len(cjk) >= 40:
        grams = [cjk[index : index + 2] for index in range(len(cjk) - 1)]
    else:
        words = re.findall(r"[a-z0-9]+", plain)
        grams = [f"{words[index]} {words[index + 1]}" for index in range(len(words) - 1)]
    if not grams:
        return 0.0
    return len(set(grams)) / len(grams)


def _summary_long_ngram_diversity_ratio(text: str, width: int = 12) -> float:
    """Detect long copied cycles that short-token diversity can miss."""
    plain = _plain_text(text, remove_evidence=True).lower()
    compact = "".join(re.findall(r"[a-z0-9\u3400-\u9fff]", plain))
    if len(compact) < width:
        return 0.0
    grams = [
        compact[index : index + width]
        for index in range(len(compact) - width + 1)
    ]
    return len(set(grams)) / len(grams)


def _normalize_bullet_text(text: str) -> str:
    text = re.sub(r"^\[[ xX]\]\s*", "", text.strip())
    text = re.sub(r"[*_~`]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def _plain_text(text: str, *, remove_evidence: bool = False) -> str:
    """Return visible inline text suitable for semantic-presence checks."""
    text = re.sub(r"!\[([^]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"\[([^]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"[*_~`]", "", text)
    if remove_evidence:
        text = EVIDENCE_LABEL_RE.sub("", text)
    return re.sub(r"\s+", " ", text).strip()


def _has_substantive_content(text: str, minimum: int = 4) -> bool:
    visible = _plain_text(text, remove_evidence=True)
    visible = visible.strip(" \t:：;；,，.。—–-|｜/／()（）[]【】")
    if not visible:
        return False
    if re.fullmatch(r"(?:N/?A|TBD|TODO|待補|待填|待定|同上)", visible, flags=re.IGNORECASE):
        return False
    if re.search(r"[A-Za-z\u3400-\u9fff]", visible):
        return len(visible) >= minimum
    return bool(re.search(r"\d", visible))


def _payload_after_colon(text: str) -> str:
    normalized = _plain_text(text)
    parts = re.split(r"[:：]", normalized, maxsplit=1)
    return parts[1].strip() if len(parts) == 2 else ""


def _contains_evidence_label(text: str) -> bool:
    return EVIDENCE_LABEL_RE.search(text) is not None


def _contains_source_cue(text: str) -> bool:
    plain = _plain_text(text)
    if INVALID_SOURCE_RE.search(plain) or FABRICATION_RE.search(plain):
        return False
    if SOURCE_CUE_RE.search(plain):
        return True
    attribution = re.search(
        r"(?:來源(?:文件)?|依據|引用)\s*(?:為|[:：])\s*(.{4,})$",
        plain,
        flags=re.IGNORECASE,
    )
    if attribution is None:
        return False
    value = attribution.group(1).strip()
    return _has_substantive_content(value) and not INVALID_SOURCE_RE.search(value)


def _source_ids(text: str) -> set[str]:
    return {f"SRC-{match.group('number')}" for match in SOURCE_ID_RE.finditer(text)}


def _defined_source_ids(
    section: tuple[Heading, list[str]] | None,
) -> set[str]:
    if section is None:
        return set()
    heading, body = section
    tables = _scan_tables(body, heading.line_number + 1)
    match = _find_table_with_fields(tables, [("來源 ID", r"來源\s*ID")])
    if match is None:
        return set()
    table, indexes = match
    source_index = indexes["來源 ID"]
    defined: set[str] = set()
    for row in table.rows:
        if source_index < len(row.cells):
            defined.update(_source_ids(row.cells[source_index]))
    return defined


def _validate_source_integrity(
    result: ValidationResult,
    lines: list[str],
    defined_sources: set[str],
) -> None:
    """Reject broken source references and explicit non-evidence globally."""
    for line_number, line in enumerate(lines, start=1):
        referenced = _source_ids(line)
        undefined = sorted(referenced - defined_sources)
        if undefined:
            result.error(
                "report references undefined source ID(s): "
                + ", ".join(undefined),
                line_number,
            )
        labels = list(EVIDENCE_LABEL_RE.finditer(line))
        for index, label_match in enumerate(labels):
            if label_match.group(0) != "[已知]":
                continue
            segment_end = labels[index + 1].start() if index + 1 < len(labels) else len(line)
            known_segment = _plain_text(line[label_match.start() : segment_end])
            if INVALID_SOURCE_RE.search(known_segment) or FABRICATION_RE.search(known_segment):
                result.error(
                    "[已知] statement cannot rely on an explicitly missing or fabricated source",
                    line_number,
                )
                break


def _split_table_row(line: str) -> tuple[str, ...] | None:
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return None
    inner = stripped[1:-1]
    cells = re.split(r"(?<!\\)\|", inner)
    return tuple(cell.replace(r"\|", "|").strip() for cell in cells)


def _is_table_separator(cells: tuple[str, ...]) -> bool:
    return bool(cells) and all(
        re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) is not None
        for cell in cells
    )


def _scan_tables(body: list[str], first_body_line_number: int) -> list[MarkdownTable]:
    tables: list[MarkdownTable] = []
    index = 0
    open_fence: str | None = None
    while index < len(body):
        line = body[index]
        if open_fence is not None:
            if _closing_fence(line, open_fence):
                open_fence = None
            index += 1
            continue
        fence_match = FENCE_RE.match(line)
        if fence_match:
            open_fence = fence_match.group("fence")
            index += 1
            continue

        headers = _split_table_row(line)
        if headers is None or index + 1 >= len(body):
            index += 1
            continue
        separator = _split_table_row(body[index + 1])
        if separator is None or not _is_table_separator(separator):
            index += 1
            continue

        rows: list[TableRow] = []
        cursor = index + 2
        while cursor < len(body):
            cells = _split_table_row(body[cursor])
            if cells is None:
                break
            rows.append(
                TableRow(
                    line_number=first_body_line_number + cursor,
                    cells=cells,
                )
            )
            cursor += 1
        tables.append(
            MarkdownTable(
                line_number=first_body_line_number + index,
                headers=headers,
                rows=tuple(rows),
            )
        )
        index = cursor
    return tables


def _header_matches(header: str, pattern: str) -> bool:
    return re.search(pattern, _plain_text(header), flags=re.IGNORECASE) is not None


def _find_table_with_fields(
    tables: list[MarkdownTable],
    fields: list[tuple[str, str]],
) -> tuple[MarkdownTable, dict[str, int]] | None:
    for table in tables:
        indexes: dict[str, int] = {}
        used: set[int] = set()
        for name, pattern in fields:
            match = next(
                (
                    index
                    for index, header in enumerate(table.headers)
                    if index not in used and _header_matches(header, pattern)
                ),
                None,
            )
            if match is None:
                break
            indexes[name] = match
            used.add(match)
        if len(indexes) == len(fields):
            return table, indexes
    return None


def _validate_required_table(
    result: ValidationResult,
    section: tuple[Heading, list[str]] | None,
    section_number: int,
    fields: list[tuple[str, str]],
) -> tuple[MarkdownTable, dict[str, int]] | None:
    if section is None:
        return None
    heading, body = section
    tables = _scan_tables(body, heading.line_number + 1)
    match = _find_table_with_fields(tables, fields)
    field_names = "、".join(name for name, _ in fields)
    if match is None:
        result.error(
            f"section {section_number} is missing a table with fields: {field_names}",
            heading.line_number,
        )
        return None
    table, indexes = match
    if not table.rows:
        result.error(
            f"section {section_number} table must contain at least one data row",
            table.line_number,
        )
        return match
    for row in table.rows:
        for name, index in indexes.items():
            value = row.cells[index] if index < len(row.cells) else ""
            evidence_only = "證據狀態" in name and _contains_evidence_label(value)
            if not evidence_only and not _has_substantive_content(value, minimum=1):
                result.error(
                    f"section {section_number} row has empty field {name}",
                    row.line_number,
                )
    return match


def _scan_subsections(
    body: list[str], first_body_line_number: int
) -> list[Subsection]:
    starts: list[tuple[int, str]] = []
    open_fence: str | None = None
    for index, line in enumerate(body):
        if open_fence is not None:
            if _closing_fence(line, open_fence):
                open_fence = None
            continue
        fence_match = FENCE_RE.match(line)
        if fence_match:
            open_fence = fence_match.group("fence")
            continue
        match = H3_RE.match(line)
        if match:
            starts.append((index, _plain_text(match.group("title"))))

    subsections: list[Subsection] = []
    for position, (index, title) in enumerate(starts):
        end = starts[position + 1][0] if position + 1 < len(starts) else len(body)
        subsections.append(
            Subsection(
                line_number=first_body_line_number + index,
                title=title,
                body=tuple(body[index + 1 : end]),
            )
        )
    return subsections


def _scan_h4_blocks(body: list[str], first_body_line_number: int) -> list[Subsection]:
    starts: list[tuple[int, str]] = []
    for index, line in enumerate(body):
        match = H4_RE.match(line)
        if match:
            starts.append((index, _plain_text(match.group("title"))))
    blocks: list[Subsection] = []
    for position, (index, title) in enumerate(starts):
        end = starts[position + 1][0] if position + 1 < len(starts) else len(body)
        blocks.append(
            Subsection(
                line_number=first_body_line_number + index,
                title=title,
                body=tuple(body[index + 1 : end]),
            )
        )
    return blocks


def _find_labeled_value(
    body: Iterable[str], patterns: Iterable[str]
) -> tuple[str, int] | None:
    for offset, line in enumerate(body):
        visible = _plain_text(line)
        visible = re.sub(r"^\s*(?:[-+*]|\d+[.)])\s*", "", visible)
        for pattern in patterns:
            match = re.match(rf"^(?:{pattern})\s*[:：]\s*(.*)$", visible)
            if match:
                return match.group(1).strip(), offset
    return None


def _scan_bullets(
    body: list[str], first_body_line_number: int
) -> list[Bullet]:
    """Build a bullet tree from indentation, ignoring fenced code blocks."""
    bullets: list[Bullet] = []
    stack: list[Bullet] = []
    open_fence: str | None = None

    for offset, line in enumerate(body):
        if open_fence is not None:
            if _closing_fence(line, open_fence):
                open_fence = None
            continue

        fence_match = FENCE_RE.match(line)
        if fence_match:
            open_fence = fence_match.group("fence")
            continue

        bullet_match = BULLET_RE.match(line.expandtabs(4))
        if not bullet_match:
            continue

        indent = len(bullet_match.group("indent"))
        while stack and indent <= stack[-1].indent:
            stack.pop()

        node = Bullet(
            line_number=first_body_line_number + offset,
            indent=indent,
            text=bullet_match.group("text").strip(),
            normalized=_normalize_bullet_text(bullet_match.group("text")),
            parent=stack[-1] if stack else None,
        )
        if node.parent is not None:
            node.parent.children.append(node)
        bullets.append(node)
        stack.append(node)

    return bullets


def _starts_with_code(text: str, code: str) -> bool:
    return bool(
        re.match(
            rf"^{re.escape(code)}(?=$|[\s｜|:：—–\-（(])",
            text,
            flags=re.IGNORECASE,
        )
    )


def _is_scqa(node: Bullet) -> bool:
    return _starts_with_code(node.normalized, "SCQA")


def _is_prep(node: Bullet) -> bool:
    return _starts_with_code(node.normalized, "PREP")


def _is_pyramid_candidate(node: Bullet) -> bool:
    text = node.normalized
    return (
        text.startswith("金字塔原理")
        or _starts_with_code(text, "Pyramid")
        or _starts_with_code(text, "MECE")
    )


def _is_complete_pyramid(node: Bullet) -> bool:
    return "金字塔原理" in node.normalized and "MECE" in node.normalized.upper()


def _is_core_conclusion(node: Bullet) -> bool:
    return node.normalized.startswith("核心結論")


def _is_secondary_argument(node: Bullet) -> bool:
    return node.normalized.startswith("次級論點")


def _is_bottom_fact(node: Bullet) -> bool:
    return node.normalized.startswith("底層事實")


def _is_star_candidate(node: Bullet) -> bool:
    return _starts_with_code(node.normalized, "STAR")


def _is_valid_star_label(node: Bullet) -> bool:
    return bool(
        re.match(
            r"^STAR\s*[｜|]\s*(?:實證案例|驗證設計)"
            r"(?=$|[\s:：—–\-（(])",
            node.normalized,
            flags=re.IGNORECASE,
        )
    )


def _check_exact_children(
    result: ValidationResult,
    parent: Bullet,
    expected: list[tuple[str, Callable[[Bullet], bool]]],
    group_name: str,
) -> dict[str, Bullet]:
    """Require one direct child per label, in order, with no extra children."""
    found: dict[str, Bullet] = {}
    positions: dict[str, int] = {}

    for position, child in enumerate(parent.children):
        matches = [name for name, predicate in expected if predicate(child)]
        if not matches:
            result.error(
                f"unexpected direct child under {group_name}: {child.normalized}",
                child.line_number,
            )
            continue

        name = matches[0]
        if name in found:
            result.error(
                f"duplicate {name} child under {group_name}", child.line_number
            )
            continue
        found[name] = child
        positions[name] = position

    for name, _ in expected:
        if name not in found:
            result.error(
                f"missing {name} as a direct child of {group_name}",
                parent.line_number,
            )

    present_in_expected_order = [
        name for name, _ in expected if name in positions
    ]
    actual_order = sorted(present_in_expected_order, key=positions.__getitem__)
    if actual_order != present_in_expected_order:
        bad_name = next(
            (
                name
                for index, name in enumerate(actual_order)
                if name != present_in_expected_order[index]
            ),
            actual_order[0],
        )
        result.error(
            f"{group_name} children must be ordered "
            + "/".join(name for name, _ in expected),
            found[bad_name].line_number,
        )

    return found


def _validate_sections(
    result: ValidationResult, headings: list[Heading]
) -> None:
    counts: dict[int, int] = {}
    for heading in headings:
        counts[heading.number] = counts.get(heading.number, 0) + 1
        if heading.number not in EXPECTED_SECTIONS:
            result.error(
                f"unexpected numbered section {heading.number}; expected only 1-12",
                heading.line_number,
            )
        elif counts[heading.number] > 1:
            result.error(
                f"duplicate section {heading.number} heading",
                heading.line_number,
            )

    for number in EXPECTED_SECTIONS:
        if counts.get(number, 0) == 0:
            result.error(f"missing section {number} heading")

    for heading in headings:
        expected_title = EXPECTED_TITLES.get(heading.number)
        if expected_title is None:
            continue
        actual_title = re.sub(r"[*_`~]", "", heading.title).strip()
        actual_title = re.sub(r"\s+", " ", actual_title)
        if actual_title != expected_title:
            result.error(
                f"section {heading.number} title must be {expected_title}",
                heading.line_number,
            )

    observed = [
        heading for heading in headings if heading.number in EXPECTED_SECTIONS
    ]
    if (
        len(observed) == len(EXPECTED_SECTIONS)
        and all(counts.get(number) == 1 for number in EXPECTED_SECTIONS)
    ):
        for expected_number, heading in zip(EXPECTED_SECTIONS, observed):
            if heading.number != expected_number:
                result.error(
                    f"section {heading.number} is out of order; "
                    f"expected section {expected_number} here",
                    heading.line_number,
                )


def _validate_epistemic_labels(
    result: ValidationResult,
    section: tuple[Heading, list[str]] | None,
) -> None:
    if section is None:
        return
    heading, body = section
    text = "\n".join(body)
    labels = ("[已知]", "[假設]", "[未知]", "[待驗證]")
    if not any(label in text for label in labels):
        result.error(
            "section 1 must include at least one epistemic label: "
            "[已知], [假設], [未知], or [待驗證]",
            heading.line_number,
        )
    for offset, line in enumerate(body):
        if "[已知]" not in line:
            continue
        if _contains_source_cue(line) or re.search(r"\bSRC[-_ ]?\d+\b", line, re.IGNORECASE):
            continue
        result.error(
            "section 1 [已知] statement must cite a recognizable source, "
            "input location, or source ID on the same line",
            heading.line_number + 1 + offset,
        )


def _validate_section_one(
    result: ValidationResult,
    section: tuple[Heading, list[str]] | None,
) -> None:
    """Require the decision context promised by report section 1."""
    if section is None:
        return

    heading, body = section
    required_fields = [
        ("主題／專案名稱", (r"主題.*專案名稱", r"主題", r"專案名稱")),
        ("背景", (r"背景",)),
        ("觸發事件", (r"觸發事件",)),
        ("目前狀態", (r"目前狀態",)),
        ("核心決策題", (r"核心決策題", r"決策題")),
        ("分析目的", (r"分析目的",)),
        ("納入範圍", (r"納入範圍",)),
        ("排除範圍", (r"排除範圍",)),
        ("時間尺度", (r"時間尺度",)),
        ("適用情境", (r"適用情境",)),
        ("關鍵時點／期限", (r"關鍵時點.*期限", r"時點.*期限")),
        ("可用資源", (r"可用資源",)),
        ("硬限制", (r"硬限制",)),
        ("可調整條件", (r"可調整條件",)),
    ]
    _validate_labeled_fields(result, section, 1, required_fields)

    labeled_context_fields = {
        "背景",
        "觸發事件",
        "目前狀態",
        "關鍵時點／期限",
        "可用資源",
        "硬限制",
        "可調整條件",
    }
    for field_name, patterns in required_fields:
        if field_name not in labeled_context_fields:
            continue
        found = _find_labeled_value(body, patterns)
        if found is None:
            continue
        value, offset = found
        if not _contains_evidence_label(value):
            result.error(
                f"section 1 field {field_name} must include an evidence status label",
                heading.line_number + 1 + offset,
            )

    stakeholder_fields = [
        ("主要角色", r"主要角色"),
        ("關切", r"^關切$"),
        ("影響", r"^影響$"),
        ("初步權責", r"初步權責"),
    ]
    _validate_required_table(result, section, 1, stakeholder_fields)

    source_fields = [
        ("來源 ID", r"來源\s*ID"),
        ("資訊／主張", r"資訊.*主張"),
        ("證據狀態", r"^證據狀態$"),
        ("來源／輸入位置", r"來源.*輸入位置"),
        ("日期／版本", r"日期.*版本"),
        ("與決策的關聯", r"與決策.*關聯"),
    ]
    source_match = _validate_required_table(result, section, 1, source_fields)
    if source_match is not None:
        table, indexes = source_match
        for row in table.rows:
            status = row.cells[indexes["證據狀態"]]
            source = row.cells[indexes["來源／輸入位置"]]
            if not _contains_evidence_label(status):
                result.error(
                    "section 1 source row 證據狀態 must include a valid label",
                    row.line_number,
                )
            if not _contains_source_cue(source):
                result.error(
                    "section 1 source row must identify a recognizable source or input location",
                    row.line_number,
                )

    gap_fields = [
        ("缺口問題", r"缺口問題"),
        ("證據狀態", r"^證據狀態$"),
        ("對決策的影響", r"對決策.*影響"),
        ("補證方式", r"補證方式"),
        ("責任角色", r"責任角色"),
        ("期限／觸發點", r"期限.*觸發點"),
    ]
    tables = _scan_tables(body, heading.line_number + 1)
    gap_match = _find_table_with_fields(tables, gap_fields)
    if gap_match is None:
        no_gap_statement = next(
            (
                (offset, _plain_text(line))
                for offset, line in enumerate(body)
                if re.search(r"無.*(?:重大|關鍵).*資訊缺口", _plain_text(line))
            ),
            None,
        )
        if no_gap_statement is None or not _has_substantive_content(
            no_gap_statement[1], minimum=12
        ):
            result.error(
                "section 1 must include an information-gap table or a substantive "
                "statement explaining why no material gap remains",
                heading.line_number,
            )
    else:
        table, indexes = gap_match
        if not table.rows:
            result.error("section 1 information-gap table must contain at least one row", table.line_number)
        for row in table.rows:
            for name, index in indexes.items():
                value = row.cells[index] if index < len(row.cells) else ""
                evidence_only = name == "證據狀態" and _contains_evidence_label(value)
                if not evidence_only and not _has_substantive_content(value, minimum=1):
                    result.error(f"section 1 gap row has empty field {name}", row.line_number)
            status = row.cells[indexes["證據狀態"]] if indexes["證據狀態"] < len(row.cells) else ""
            if not any(label in status for label in ("[未知]", "[待驗證]")):
                result.error(
                    "section 1 information gap must be labeled [未知] or [待驗證]",
                    row.line_number,
                )


def _validate_summary(
    result: ValidationResult,
    section: tuple[Heading, list[str]] | None,
) -> None:
    if section is None:
        return
    heading, body = section
    body_text = "\n".join(body).strip()
    blocks = [block for block in re.split(r"\n\s*\n", body_text) if block.strip()]
    if len(blocks) != 1:
        result.error(
            "section 2 must contain exactly one paragraph",
            heading.line_number,
        )
    for offset, line in enumerate(body):
        if not line.strip():
            continue
        if (
            re.match(r"^\s{0,3}(?:#{1,6}|>|[-+*]\s|\d+[.)]\s)", line)
            or "|" in line
        ):
            result.error(
                "section 2 must be prose, not headings, lists, quotes, or tables",
                heading.line_number + 1 + offset,
            )
    count = _visible_character_count(body)
    if count < 250 or count > 350:
        result.error(
            f"section 2 summary is {count} characters; required range is 250-350",
            heading.line_number,
        )
    plain = _plain_text(body_text)
    for label, pattern in SUMMARY_CONTENT_CUES:
        if re.search(pattern, plain, flags=re.IGNORECASE) is None:
            result.error(
                f"section 2 summary must cover {label}",
                heading.line_number,
            )
    if _summary_diversity_ratio(plain) < 0.22:
        result.error(
            "section 2 summary is excessively repetitive or keyword-stuffed",
            heading.line_number,
        )
    if _summary_long_ngram_diversity_ratio(plain) < 0.75:
        result.error(
            "section 2 summary contains a repeated long cycle or copied passage",
            heading.line_number,
        )
    if len(re.findall(r"[，,；;。.!?！？]", plain)) < 4:
        result.error(
            "section 2 summary must form a connected argument with multiple clauses",
            heading.line_number,
        )


def _validate_labeled_fields(
    result: ValidationResult,
    section: tuple[Heading, list[str]] | None,
    section_number: int,
    fields: list[tuple[str, tuple[str, ...]]],
) -> None:
    if section is None:
        return
    heading, body = section
    for name, patterns in fields:
        found = _find_labeled_value(body, patterns)
        if found is None:
            result.error(
                f"section {section_number} is missing field {name}",
                heading.line_number,
            )
            continue
        value, offset = found
        if not _has_substantive_content(value):
            result.error(
                f"section {section_number} field {name} must contain substantive content",
                heading.line_number + 1 + offset,
            )


def _validate_sections_three_to_eight(
    result: ValidationResult,
    sections: dict[int, tuple[Heading, list[str]]],
) -> None:
    keyword_fields = [
        ("統一名稱", r"(?:統一名稱|關鍵字)"),
        ("操作型定義", r"操作(?:型)?定義"),
        ("近義詞／易混淆詞", r"近義詞.*易混淆詞"),
        ("本分析採用的用法", r"本分析.*用法"),
        ("證據狀態／來源", r"證據狀態.*來源"),
    ]
    keyword_match = _validate_required_table(result, sections.get(3), 3, keyword_fields)
    if keyword_match is not None:
        table, indexes = keyword_match
        evidence_index = indexes["證據狀態／來源"]
        for row in table.rows:
            value = row.cells[evidence_index] if evidence_index < len(row.cells) else ""
            if value and not _contains_evidence_label(value):
                result.error("section 3 keyword 證據狀態／來源 must include a valid label", row.line_number)

    section3 = sections.get(3)
    if section3 is not None:
        heading3, body3 = section3
        variable_blocks = []
        for block in _scan_h4_blocks(body3, heading3.line_number + 1):
            match = re.match(r"^變數\s+([A-Za-z][A-Za-z0-9_.-]*)\s*[｜|:：—–-]\s*(.+)$", block.title)
            if match:
                variable_blocks.append((match.group(1).upper(), match.group(2), block))
        if not variable_blocks:
            result.error("section 3 must contain at least one #### 變數 <ID>｜<名稱> block", heading3.line_number)
        variable_fields = [
            ("角色", (r"角色",)),
            ("定義／單位或尺度", (r"定義.*(?:單位|尺度)",)),
            ("已知值或範圍", (r"已知值.*範圍",)),
            ("預期方向", (r"預期方向",)),
            ("可觀測方式", (r"可觀測.*(?:方式|方法)",)),
            ("證據狀態／來源", (r"證據狀態.*來源",)),
        ]
        seen: set[str] = set()
        for variable_id, name, block in variable_blocks:
            if variable_id in seen:
                result.error(f"section 3 has duplicate variable ID {variable_id}", block.line_number)
            seen.add(variable_id)
            if not _has_substantive_content(name, minimum=2):
                result.error(f"section 3 variable {variable_id} must have a substantive name", block.line_number)
            for field_name, patterns in variable_fields:
                found = _find_labeled_value(block.body, patterns)
                if found is None:
                    result.error(f"section 3 variable {variable_id} is missing field {field_name}", block.line_number)
                    continue
                value, offset = found
                minimum = 2 if field_name == "角色" else 4
                if not _has_substantive_content(value, minimum=minimum):
                    result.error(f"section 3 variable {variable_id} field {field_name} must contain substantive content", block.line_number + 1 + offset)
                if field_name == "證據狀態／來源" and not _contains_evidence_label(value):
                    result.error(f"section 3 variable {variable_id} 證據狀態／來源 must include a valid label", block.line_number + 1 + offset)

    _validate_labeled_fields(
        result, sections.get(4), 4,
        [
            ("最終決策者／共同決策機制", (r"最終決策者.*共同決策機制", r"最終決策者")),
            ("待決事項", (r"待決事項",)),
            ("核心目標", (r"核心目標",)),
            ("決策權限", (r"決策權限",)),
            ("可支配資源", (r"可支配資源",)),
            ("限制", (r"限制",)),
            ("誘因", (r"誘因",)),
            ("決策時點", (r"決策時點",)),
            ("不可逆程度", (r"不可逆程度",)),
            ("主要受益者", (r"主要受益者",)),
            ("主要成本／風險承擔者", (r"主要成本.*風險承擔者",)),
        ],
    )
    role_fields = [
        ("角色", r"^角色$"), ("與決策的關係", r"與決策.*關係"),
        ("權限與責任", r"權限.*責任"), ("受益", r"^受益$"),
        ("成本／風險承擔", r"成本.*風險承擔"), ("參與時點／方式", r"參與時點.*方式"),
    ]
    _validate_required_table(result, sections.get(4), 4, role_fields)

    section5 = sections.get(5)
    if section5 is not None:
        heading5, body5 = section5
        thesis_line = next((line for line in body5 if line.strip() and not re.match(r"^\s*(?:#{1,6}|[-+*]\s|\|)", line)), "")
        if not _has_substantive_content(thesis_line, minimum=12):
            result.error("section 5 must contain a substantive, falsifiable Thesis", heading5.line_number)
        elif not _contains_evidence_label(thesis_line):
            result.error("section 5 Thesis must include an evidence status label", heading5.line_number)
        argument_fields = [("論證欄位", r"論證欄位"), ("內容", r"^內容$"), ("證據狀態／來源", r"證據狀態.*來源")]
        argument_match = _validate_required_table(result, section5, 5, argument_fields)
        required_rows = {
            "主要理由": r"主要理由", "必要條件": r"必要條件", "適用邊界": r"適用邊界", "反轉／失效條件": r"反轉.*失效條件",
        }
        if argument_match is not None:
            table, indexes = argument_match
            for name, pattern in required_rows.items():
                row = next((row for row in table.rows if row.cells and re.search(pattern, _plain_text(row.cells[indexes["論證欄位"]]))), None)
                if row is None:
                    result.error(f"section 5 argument table is missing row {name}", table.line_number)
                elif not _contains_evidence_label(row.cells[indexes["證據狀態／來源"]]):
                    result.error(f"section 5 row {name} 證據狀態／來源 must include a valid label", row.line_number)
        _validate_labeled_fields(result, section5, 5, [
            ("信心水準", (r"信心水準",)),
            ("信心依據／證據狀態／來源", (r"信心依據.*證據狀態.*來源",)),
        ])

    section6 = sections.get(6)
    if section6 is not None:
        heading6, body6 = section6
        concept_blocks = []
        for block in _scan_h4_blocks(body6, heading6.line_number + 1):
            match = re.match(r"^概念\s+([A-Za-z][A-Za-z0-9_.-]*)\s*[｜|:：—–-]\s*(.+)$", block.title)
            if match:
                concept_blocks.append((match.group(1).upper(), match.group(2), block))
        if not concept_blocks:
            result.error("section 6 must contain at least one #### 概念 <ID>｜<名稱> block", heading6.line_number)
        concept_fields = [
            ("操作型定義／判定標準", (r"操作型定義.*判定標準",)),
            ("定義來源或本次假設", (r"定義來源.*本次假設",)),
            ("納入範圍", (r"納入範圍",)), ("排除範圍", (r"排除範圍",)),
            ("依賴項", (r"依賴項",)), ("失效條件", (r"失效條件",)),
            ("證據狀態／來源", (r"證據狀態.*來源",)),
        ]
        for concept_id, name, block in concept_blocks:
            if not _has_substantive_content(name, minimum=2):
                result.error(f"section 6 concept {concept_id} must have a substantive name", block.line_number)
            for field_name, patterns in concept_fields:
                found = _find_labeled_value(block.body, patterns)
                if found is None:
                    result.error(f"section 6 concept {concept_id} is missing field {field_name}", block.line_number)
                    continue
                value, offset = found
                if not _has_substantive_content(value):
                    result.error(f"section 6 concept {concept_id} field {field_name} must contain substantive content", block.line_number + 1 + offset)
                if field_name == "證據狀態／來源" and not _contains_evidence_label(value):
                    result.error(f"section 6 concept {concept_id} 證據狀態／來源 must include a valid label", block.line_number + 1 + offset)
        convention_fields = [("項目", r"^項目$"), ("採用慣例", r"採用慣例"), ("來源／理由", r"來源.*理由"), ("證據狀態", r"^證據狀態$")]
        convention_match = _validate_required_table(result, section6, 6, convention_fields)
        if convention_match is not None:
            table, indexes = convention_match
            for row in table.rows:
                if not _contains_evidence_label(row.cells[indexes["證據狀態"]]):
                    result.error("section 6 numeric/version convention must include a valid evidence label", row.line_number)

    section7 = sections.get(7)
    if section7 is not None:
        heading7, body7 = section7
        path = _find_labeled_value(body7, (r"整體路徑",))
        arrow_count = 0
        path_nodes: list[str] = []
        if path is None or not _has_substantive_content(path[0], minimum=12):
            result.error("section 7 is missing a substantive 整體路徑", heading7.line_number)
        else:
            path_nodes = [part.strip() for part in path[0].split("→")]
            arrow_count = len(re.findall(r"→", path[0]))
            if arrow_count < 4 or len(path_nodes) < 5:
                result.error(
                    "section 7 整體路徑 must contain at least five stages "
                    "(input/intervention → mechanism → direct output → intermediate result → final result)",
                    heading7.line_number + 1 + path[1],
                )
        links = []
        for block in _scan_subsections(body7, heading7.line_number + 1):
            match = re.match(r"^連結\s+([A-Za-z][A-Za-z0-9_.-]*)\s*[｜|:：—–-]\s*(.+)$", block.title)
            if match:
                links.append((match.group(1).upper(), match.group(2), block))
        if not links:
            result.error("section 7 must contain at least one ### 連結 <ID>｜<原因 → 結果> block", heading7.line_number)
        elif arrow_count and len(links) != arrow_count:
            result.error(f"section 7 has {arrow_count} arrows in 整體路徑 but {len(links)} 連結 blocks; each arrow needs its own block", heading7.line_number)
        link_fields = [
            ("原因 → 結果與方向", (r"原因.*結果.*方向",)), ("時序／延遲", (r"時序.*延遲",)),
            ("作用機制", (r"作用機制",)), ("證據狀態／來源", (r"證據狀態.*來源",)),
            ("成立條件／依賴", (r"成立條件.*依賴",)), ("替代解釋／干擾變數", (r"替代解釋.*干擾變數",)),
            ("反證觀察", (r"反證觀察",)), ("驗證方法／責任角色／時點", (r"驗證方法.*責任角色.*時點",)),
        ]

        def normalize_endpoint(value: str) -> str:
            value = EVIDENCE_LABEL_RE.sub("", _plain_text(value)).lower()
            return re.sub(r"[^a-z0-9\u3400-\u9fff]", "", value)

        def endpoint_matches(
            actual: str,
            expected: str,
            *,
            loose: bool = False,
            minimum_tokens: int = 1,
        ) -> bool:
            negative_change = re.compile(
                r"(?:取消|刪除|移除|停止|終止|中止|放棄|禁止|廢除|撤銷|"
                r"停辦|停用|關閉|凍結|排除|拒絕|不使用|不執行|不建立|"
                r"cancel|delete|remove|stop|abandon)",
                flags=re.IGNORECASE,
            )
            if bool(negative_change.search(actual)) != bool(negative_change.search(expected)):
                return False
            actual_norm = normalize_endpoint(actual)
            expected_norm = normalize_endpoint(expected)
            if not actual_norm or not expected_norm:
                return False
            if (
                actual_norm == expected_norm
                or actual_norm in expected_norm
                or expected_norm in actual_norm
            ):
                return True
            if loose:
                def semantic_tokens(value: str) -> set[str]:
                    visible = EVIDENCE_LABEL_RE.sub("", _plain_text(value)).lower()
                    tokens: set[str] = set()
                    for run in re.findall(r"[\u3400-\u9fff]+", visible):
                        if len(run) == 1:
                            tokens.add(run)
                        else:
                            tokens.update(
                                run[index : index + 2]
                                for index in range(len(run) - 1)
                            )
                    tokens.update(
                        word
                        for word in re.findall(r"[a-z0-9]+", visible)
                        if len(word) >= 3
                    )
                    return tokens

                # Link bodies commonly paraphrase their concise titles.  One
                # shared meaningful bigram (or Latin token) per endpoint is a
                # stronger semantic anchor than raw character overlap, while
                # still rejecting unrelated substitutions such as weather and
                # coffee price.
                return (
                    len(semantic_tokens(actual) & semantic_tokens(expected))
                    >= minimum_tokens
                )
            shorter = set(min((actual_norm, expected_norm), key=len))
            longer = set(max((actual_norm, expected_norm), key=len))
            shared = shorter & longer
            minimum_shared = 4
            minimum_ratio = 0.7
            return len(shared) >= minimum_shared and len(shared) / len(shorter) >= minimum_ratio

        seen: set[str] = set()
        for link_id, title, block in links:
            if link_id in seen:
                result.error(f"section 7 has duplicate link ID {link_id}", block.line_number)
            seen.add(link_id)
            if "→" not in title:
                result.error(f"section 7 link {link_id} title must name 原因 → 結果", block.line_number)
            field_values: dict[str, str] = {}
            for field_name, patterns in link_fields:
                found = _find_labeled_value(block.body, patterns)
                if found is None:
                    result.error(f"section 7 link {link_id} is missing field {field_name}", block.line_number)
                    continue
                value, offset = found
                field_values[field_name] = value
                if not _has_substantive_content(value):
                    result.error(f"section 7 link {link_id} field {field_name} must contain substantive content", block.line_number + 1 + offset)
                if field_name == "證據狀態／來源" and not _contains_evidence_label(value):
                    result.error(f"section 7 link {link_id} 證據狀態／來源 must include a valid label", block.line_number + 1 + offset)
            direction = field_values.get("原因 → 結果與方向", "")
            title_endpoints = [part.strip() for part in title.split("→")]
            if direction and len(title_endpoints) == 2:
                if "→" in direction:
                    direction_endpoints = [part.strip() for part in direction.split("→", maxsplit=1)]
                    matches_body = all(
                        endpoint_matches(actual, expected, loose=True)
                        for actual, expected in zip(direction_endpoints, title_endpoints)
                    )
                else:
                    matches_body = endpoint_matches(
                        direction,
                        title,
                        loose=True,
                        minimum_tokens=2,
                    )
                if not matches_body:
                    result.error(
                        f"section 7 link {link_id} 原因 → 結果與方向 does not match its link title",
                        block.line_number,
                    )

        if path_nodes and len(links) == arrow_count:
            for index, (_, title, block) in enumerate(links):
                endpoints = [part.strip() for part in title.split("→")]
                if len(endpoints) != 2:
                    result.error(
                        "section 7 link title must contain exactly one cause → result pair",
                        block.line_number,
                    )
                    continue
                expected = (path_nodes[index], path_nodes[index + 1])
                for actual_value, expected_value, role in zip(
                    endpoints, expected, ("cause", "result")
                ):
                    if not endpoint_matches(actual_value, expected_value):
                        result.error(
                            f"section 7 link {links[index][0]} {role} does not match "
                            "the corresponding adjacent node in 整體路徑",
                            block.line_number,
                        )

    conflict_fields = [
        ("考量點", r"考量點"), ("重複位置／衝突雙方", r"重複位置.*衝突雙方"),
        ("影響", r"^影響$"), ("目前狀態", r"目前狀態"),
        ("處理原則／所需證據", r"處理原則.*所需證據"), ("責任角色與時點", r"責任角色.*時點"),
    ]
    _validate_required_table(result, sections.get(8), 8, conflict_fields)

def _validate_one_sentence(
    result: ValidationResult,
    section: tuple[Heading, list[str]] | None,
) -> None:
    if section is None:
        return
    heading, body = section
    nonempty = [line for line in body if line.strip()]
    if not nonempty:
        result.error("section 9 must contain one sentence", heading.line_number)
        return
    if any(
        re.match(r"^\s{0,3}(?:#{1,6}|>|[-+*]\s|\d+[.)]\s)", line)
        or "|" in line
        for line in nonempty
    ):
        result.error(
            "section 9 must be one prose sentence, not a list or table",
            heading.line_number,
        )
    plain = _plain_text(" ".join(nonempty))
    terminal_core = plain.rstrip(" \t\"'”’」』）)]》】")
    if not re.search(r"[。！？.!?]$", terminal_core):
        result.error(
            "section 9 must end with sentence-ending punctuation",
            heading.line_number,
        )
    boundary_re = re.compile(
        r"[。！？!?]+|(?<!\d)\.(?!\d)(?=(?:[\"'”’」』）)\]]*)"
        r"(?:\s+[A-Z\u3400-\u9fff]|\s*$))"
    )
    if len(boundary_re.findall(plain)) != 1:
        result.error(
            "section 9 must contain exactly one sentence",
            heading.line_number,
        )


def _validate_no_placeholders(result: ValidationResult, lines: list[str]) -> None:
    open_fence: str | None = None
    for index, line in enumerate(lines):
        if open_fence is not None:
            if _closing_fence(line, open_fence):
                open_fence = None
            continue
        fence_match = FENCE_RE.match(line)
        if fence_match:
            open_fence = fence_match.group("fence")
            continue
        if re.search(r"<[^>\n]+>", line):
            result.error(
                "unresolved angle-bracket placeholder or unsupported HTML",
                index + 1,
            )


def _validate_audiences(
    result: ValidationResult,
    section: tuple[Heading, list[str]] | None,
) -> None:
    if section is None:
        return
    heading, body = section
    required: list[tuple[str, str]] = [
        ("決策層", r"^決策層$"),
        ("管理／專業層", r"^管理(?:層)?\s*[／/、]\s*專業層$"),
        ("執行層", r"^執行層$"),
        ("一般受眾", r"^一般受眾$"),
    ]
    tables = _scan_tables(body, heading.line_number + 1)
    audience_table = next(
        (
            table
            for table in tables
            if any(_header_matches(header, r"^受眾$") for header in table.headers)
        ),
        None,
    )
    seen_explanations: dict[str, str] = {}
    for label, pattern in required:
        row_match: TableRow | None = None
        if audience_table is not None:
            row_match = next(
                (
                    row
                    for row in audience_table.rows
                    if row.cells
                    and re.match(pattern, _plain_text(row.cells[0])) is not None
                ),
                None,
            )
        if row_match is not None:
            meaningful_cells = [
                cell
                for cell in row_match.cells[1:]
                if _has_substantive_content(cell)
            ]
            explanation = row_match.cells[-1] if row_match.cells else ""
            if len(meaningful_cells) < 3 or not _has_substantive_content(
                explanation, minimum=12
            ):
                result.error(
                    f"section 10 audience {label} must contain substantive explanation",
                    row_match.line_number,
                )
            else:
                seen_explanations[label] = _plain_text(explanation)
            continue

        bullet_entry = _find_labeled_value(body, (pattern.strip("^$"),))
        if bullet_entry is None:
            result.error(
                f"section 10 is missing audience label {label}",
                heading.line_number,
            )
            continue
        explanation, offset = bullet_entry
        if not _has_substantive_content(explanation, minimum=20):
            result.error(
                f"section 10 audience {label} must contain substantive explanation",
                heading.line_number + 1 + offset,
            )
        else:
            seen_explanations[label] = _plain_text(explanation)

    reverse: dict[str, list[str]] = {}
    for label, explanation in seen_explanations.items():
        normalized = re.sub(r"\W+", "", explanation, flags=re.UNICODE).lower()
        reverse.setdefault(normalized, []).append(label)
    for duplicate_labels in reverse.values():
        if len(duplicate_labels) > 1:
            result.error(
                "section 10 audience explanations must be tailored; duplicate "
                + "/".join(duplicate_labels),
                heading.line_number,
            )


def _validate_actions(
    result: ValidationResult,
    section: tuple[Heading, list[str]] | None,
) -> None:
    if section is None:
        return
    heading, body = section
    subsections = _scan_subsections(body, heading.line_number + 1)
    actions: list[tuple[str, Subsection, str]] = []
    for subsection in subsections:
        action_match = re.match(r"^行動\s+([A-Za-z][A-Za-z0-9_.-]*)\s*[｜|:：—–-]\s*(.*)$", subsection.title, flags=re.IGNORECASE)
        if action_match:
            actions.append((action_match.group(1).upper(), subsection, action_match.group(2)))
        elif re.match(r"^指標\s+", subsection.title):
            result.error("section 11 must embed indicators inside each action; separate 指標 blocks are not allowed", subsection.line_number)
    if not actions:
        result.error("section 11 must contain at least one ### 行動 <ID>｜<名稱> block", heading.line_number)
        return
    fields: list[tuple[str, tuple[str, ...]]] = [
        ("行動內容", (r"行動內容",)), ("依據", (r"依據",)),
        ("責任人", (r"責任人", r"負責角色")), ("期限／優先序", (r"期限.*優先序",)),
        ("依賴／資源", (r"依賴.*資源",)), ("交付物／驗收", (r"交付物.*驗收",)),
        ("領先指標", (r"領先指標",)), ("結果指標", (r"結果指標",)),
        ("基準值", (r"基準值",)), ("目標／護欄門檻", (r"目標.*護欄門檻",)),
        ("量測頻率／檢查點", (r"量測頻率.*檢查點",)), ("決策規則", (r"決策規則",)),
    ]
    seen: set[str] = set()
    for action_id, subsection, name in actions:
        if action_id in seen:
            result.error(f"section 11 has duplicate action ID {action_id}", subsection.line_number)
        seen.add(action_id)
        if not _has_substantive_content(name, minimum=2):
            result.error(f"section 11 action {action_id} must have a substantive name", subsection.line_number)
        values: dict[str, str] = {}
        for field_name, patterns in fields:
            found = _find_labeled_value(subsection.body, patterns)
            if found is None:
                result.error(f"section 11 action {action_id} is missing field {field_name}", subsection.line_number)
                continue
            value, offset = found
            values[field_name] = value
            if not _has_substantive_content(value):
                result.error(f"section 11 action {action_id} field {field_name} must contain substantive content", subsection.line_number + 1 + offset)
        for indicator_name in ("領先指標", "結果指標"):
            indicator = values.get(indicator_name, "")
            if indicator and not (
                re.search(r"\b[A-Za-z][A-Za-z0-9_.-]*\b", indicator)
                and re.search(r"(?:公式|除以|百分比|%|件|元|日|小時|分鐘|分|數|率|時間)", indicator)
                and re.search(r"(?:越|增加|降低|提高|減少|維持|方向)", indicator)
                and re.search(r"(?:來源|系統|紀錄|問卷|帳單|日誌|台帳|量測)", indicator)
            ):
                result.error(f"section 11 action {action_id} {indicator_name} must include ID, definition/unit, direction, and data source", subsection.line_number)
        baseline = values.get("基準值", "")
        target = values.get("目標／護欄門檻", "")
        frequency = values.get("量測頻率／檢查點", "")
        rule = values.get("決策規則", "")
        if baseline and not _contains_evidence_label(baseline):
            result.error(f"section 11 action {action_id} 基準值 must include an evidence status label", subsection.line_number)
        if baseline and "[已知]" in baseline and not _contains_source_cue(baseline):
            result.error(f"section 11 action {action_id} known baseline must cite its source", subsection.line_number)
        if target and not _contains_evidence_label(target):
            result.error(f"section 11 action {action_id} 目標／護欄門檻 must include an evidence status label", subsection.line_number)
        if target and not re.search(r"(?:\d|至少|至多|不高於|不低於|通過|符合|維持|門檻)", target):
            result.error(f"section 11 action {action_id} 目標／護欄門檻 must state a measurable criterion", subsection.line_number)
        if target and not re.search(r"(?:日|週|月|季|年|期間|前|後|內|時|每|連續|批次|觸發)", target):
            result.error(f"section 11 action {action_id} 目標／護欄門檻 must state a timeframe or trigger", subsection.line_number)
        if frequency and not re.search(r"(?:每|逐|即時|定期|日|週|月|季|年|批|事件發生|一次)", frequency):
            result.error(f"section 11 action {action_id} 量測頻率／檢查點 must state a measurement frequency", subsection.line_number)
        if rule and not (
            re.search(r"(?:達標|達\s*\d|通過|符合|高於|低於|至少|至多)", rule)
            and re.search(r"(?:未達|否則|失守|超過|不符合|低於)", rule)
            and re.search(r"(?:判讀|決定|核准|負責)", rule)
        ):
            result.error(f"section 11 action {action_id} 決策規則 must name the decision role and cover passing and failing outcomes", subsection.line_number)
        if rule:
            clauses = [
                clause.strip()
                for clause in re.split(r"[，,；;。]", rule)
                if clause.strip()
            ]
            fail_cue = re.compile(r"(?:未達|否則|失守|超過|不符合|低於|失敗)")
            pass_cue = re.compile(r"(?:全數達標|達標|通過|符合|不低於|不高於|至少|至多)")
            pass_action = re.compile(r"(?:繼續|擴大|核准|批准|推動|常態化|進入下一|保留|採用|同意|啟用)")
            safe_fail_action = re.compile(r"(?:停止|暫停|調整|修正|回退|縮減|終止|不擴大|重做|補證|延後|凍結|停用|補救|不啟動|不得啟動)")
            unsafe_fail_action = re.compile(r"(?:直接|立即|全面)?\s*(?:擴大|常態化|正式導入|全面導入)")
            blocked_pass_state = re.compile(
                r"(?:維持|保持|繼續)[^，,；;。]{0,12}"
                r"(?:暫停|停止|凍結|停用|不啟用|不核准|不擴大)"
            )
            unsafe_fail_outcome = re.compile(
                r"(?:向所有(?:單位|使用者)?|直接|立即|全面|正式)?\s*"
                r"(?:擴大|常態化|導入|採用|啟用|推動|核准|批准)"
            )
            negation_scope = re.compile(
                r"(?:不|不得|不可|禁止|避免|拒絕)[^，,；;。]{0,12}$"
            )
            requalified = re.compile(
                r"(?:重新|再次)(?:達標|通過)|複驗通過|補證通過|修正後通過"
            )
            passing = [
                clause for clause in clauses
                if pass_cue.search(clause) and not fail_cue.search(clause)
            ]
            failing = [clause for clause in clauses if fail_cue.search(clause)]
            if passing and not any(pass_action.search(clause) for clause in passing):
                result.error(
                    f"section 11 action {action_id} decision rule must continue or advance after passing",
                    subsection.line_number,
                )
            if any(blocked_pass_state.search(clause) for clause in passing):
                result.error(
                    f"section 11 action {action_id} decision rule must not remain stopped or paused after passing",
                    subsection.line_number,
                )
            if failing and not any(safe_fail_action.search(clause) for clause in failing):
                result.error(
                    f"section 11 action {action_id} decision rule must stop, adjust, or obtain more evidence after failing",
                    subsection.line_number,
                )
            if any(
                unsafe_fail_action.search(clause)
                and not re.search(r"(?:不|不得|不可|停止|暫停)", clause)
                for clause in failing
            ):
                result.error(
                    f"section 11 action {action_id} decision rule must not expand after a failed threshold or guardrail",
                    subsection.line_number,
                )
            first_failure = fail_cue.search(rule)
            if first_failure is not None:
                failure_tail = rule[first_failure.start() :]
                for unsafe_match in unsafe_fail_outcome.finditer(failure_tail):
                    prefix = failure_tail[max(0, unsafe_match.start() - 20) : unsafe_match.start()]
                    prior_failure_context = failure_tail[: unsafe_match.start()]
                    if negation_scope.search(prefix) or requalified.search(prior_failure_context):
                        continue
                    result.error(
                        f"section 11 action {action_id} decision rule must not adopt, enable, or expand after a failed threshold or guardrail",
                        subsection.line_number,
                    )
                    break

def _contains_mermaid_fence(body: list[str]) -> tuple[bool, int | None]:
    for offset, line in enumerate(body):
        match = FENCE_RE.match(line)
        if not match:
            continue
        info = match.group("info").strip().lower()
        if re.match(r"^(?:\{?\.)?mermaid(?:\b|\})", info):
            return True, offset
    return False, None


def _node_payload(node: Bullet) -> str:
    text = node.normalized
    if re.search(r"[:：]", text):
        return re.split(r"[:：]", text, maxsplit=1)[1].strip()
    if "｜" in text or "|" in text:
        return re.split(r"[｜|]", text, maxsplit=1)[1].strip()
    return ""


def _require_node_content(
    result: ValidationResult,
    node: Bullet | None,
    name: str,
    *,
    minimum: int = 4,
    evidence: bool = False,
) -> None:
    if node is None:
        return
    payload = _node_payload(node)
    if not _has_substantive_content(payload, minimum=minimum):
        result.error(f"{name} must contain substantive content", node.line_number)
    if evidence and not _contains_evidence_label(payload):
        result.error(
            f"{name} must include an evidence status label",
            node.line_number,
        )


def _require_leaf_node(
    result: ValidationResult,
    node: Bullet | None,
    name: str,
) -> None:
    if node is None:
        return
    for child in node.children:
        result.error(f"{name} must not contain child nodes", child.line_number)


def _validate_pyramid(
    result: ValidationResult,
    pyramid: Bullet,
) -> list[Bullet]:
    core_nodes = [child for child in pyramid.children if _is_core_conclusion(child)]
    for child in pyramid.children:
        if not _is_core_conclusion(child):
            result.error(
                "Pyramid direct children must be 核心結論",
                child.line_number,
            )

    if not core_nodes:
        result.error(
            "Pyramid is missing 核心結論 as a direct child",
            pyramid.line_number,
        )
    for duplicate in core_nodes[1:]:
        result.error("duplicate 核心結論 under Pyramid", duplicate.line_number)

    bottom_facts: list[Bullet] = []
    if not core_nodes:
        return bottom_facts

    core = core_nodes[0]
    _require_node_content(
        result, core, "Pyramid 核心結論", minimum=10, evidence=True
    )
    secondary_nodes = [
        child for child in core.children if _is_secondary_argument(child)
    ]
    for child in core.children:
        if not _is_secondary_argument(child):
            result.error(
                "核心結論 direct children must be 次級論點",
                child.line_number,
            )
    if not secondary_nodes:
        result.error(
            "核心結論 is missing 次級論點 as a direct child",
            core.line_number,
        )
    elif len(secondary_nodes) < 2:
        result.error(
            "Pyramid must contain at least two sibling 次級論點 to demonstrate a MECE split",
            core.line_number,
        )

    category_names: dict[str, Bullet] = {}
    claim_texts: dict[str, Bullet] = {}
    for secondary in secondary_nodes:
        _require_node_content(
            result, secondary, "Pyramid 次級論點", minimum=6, evidence=True
        )
        category_match = re.search(r"[｜|]\s*([^:：]+)", secondary.normalized)
        category = re.sub(
            r"\W+",
            "",
            category_match.group(1) if category_match else "",
            flags=re.UNICODE,
        ).lower()
        if category and category in category_names:
            result.error(
                "Pyramid sibling 次級論點 must use distinct MECE categories",
                secondary.line_number,
            )
        elif category:
            category_names[category] = secondary
        claim = re.sub(
            r"\W+",
            "",
            _plain_text(_node_payload(secondary), remove_evidence=True),
            flags=re.UNICODE,
        ).lower()
        if claim and claim in claim_texts:
            result.error(
                "Pyramid sibling 次級論點 must not repeat the same substantive claim",
                secondary.line_number,
            )
        elif claim:
            claim_texts[claim] = secondary

    fact_texts: dict[str, Bullet] = {}
    for secondary in secondary_nodes:
        facts = [child for child in secondary.children if _is_bottom_fact(child)]
        for child in secondary.children:
            if not _is_bottom_fact(child):
                result.error(
                    "次級論點 direct children must be 底層事實",
                    child.line_number,
                )
        if not facts:
            result.error(
                "次級論點 is missing 底層事實 as a direct child",
                secondary.line_number,
            )
        for fact in facts:
            _require_node_content(
                result,
                fact,
                "Pyramid bottom fact",
                minimum=6,
                evidence=True,
            )
            fact_claim = re.sub(
                r"\W+",
                "",
                _plain_text(_node_payload(fact), remove_evidence=True),
                flags=re.UNICODE,
            ).lower()
            if fact_claim and fact_claim in fact_texts:
                result.error(
                    "Pyramid bottom facts must not duplicate the same evidence claim",
                    fact.line_number,
                )
            elif fact_claim:
                fact_texts[fact_claim] = fact
        bottom_facts.extend(facts)

    return bottom_facts


def _validate_star(
    result: ValidationResult,
    star: Bullet,
    defined_sources: set[str],
) -> None:
    children = _check_exact_children(
        result,
        star,
        [
            ("S", lambda node: _starts_with_code(node.normalized, "S")),
            ("T", lambda node: _starts_with_code(node.normalized, "T")),
            ("A", lambda node: _starts_with_code(node.normalized, "A")),
            ("R", lambda node: _starts_with_code(node.normalized, "R")),
        ],
        "STAR",
    )
    for code, label in (
        ("S", "STAR Situation"),
        ("T", "STAR Task"),
        ("A", "STAR Action"),
        ("R", "STAR Result"),
    ):
        _require_node_content(
            result,
            children.get(code),
            label,
            minimum=6,
            evidence=True,
        )
        _require_leaf_node(result, children.get(code), label)

    is_empirical = "實證案例" in star.normalized
    result_node = children.get("R")
    if is_empirical:
        if FABRICATION_RE.search(star.normalized):
            result.error(
                "STAR｜實證案例 contains an explicit fabrication marker",
                star.line_number,
            )
        for code, node in children.items():
            payload = _node_payload(node)
            if "[已知]" not in payload:
                result.error(
                    f"STAR｜實證案例 {code} must be grounded as [已知]",
                    node.line_number,
                )
            if FABRICATION_RE.search(payload):
                result.error(
                    f"STAR｜實證案例 {code} contains an explicit fabrication marker",
                    node.line_number,
                )
            if not _contains_source_cue(payload):
                result.error(
                    f"STAR｜實證案例 {code} must include a recognizable source or source ID",
                    node.line_number,
                )
            referenced = _source_ids(payload)
            undefined = sorted(referenced - defined_sources)
            if undefined:
                result.error(
                    f"STAR｜實證案例 {code} references undefined source ID(s): "
                    + ", ".join(undefined),
                    node.line_number,
                )
    elif result_node is not None:
        result_payload = _node_payload(result_node)
        if not any(label in result_payload for label in ("[假設]", "[待驗證]")):
            result.error(
                "STAR｜驗證設計 Result must be [假設] or [待驗證], "
                "not an observed outcome",
                result_node.line_number,
            )
        if not (
            re.search(
                r"(?:\d|門檻|至少|至多|不高於|不低於|通過|達標)",
                result_payload,
            )
            and re.search(
                r"(?:若|否則|才|達標|未達|停止|擴大|繼續|回退|調整)",
                result_payload,
            )
        ):
            result.error(
                "STAR｜驗證設計 Result must state a target threshold "
                "and decision rule",
                result_node.line_number,
            )


def _validate_model_tree(
    result: ValidationResult,
    section: tuple[Heading, list[str]] | None,
    defined_sources: set[str],
) -> None:
    if section is None:
        return
    heading, body = section

    has_mermaid, mermaid_offset = _contains_mermaid_fence(body)
    if has_mermaid:
        assert mermaid_offset is not None
        result.error(
            "Mermaid is not allowed in section 12; use nested Markdown bullets",
            heading.line_number + 1 + mermaid_offset,
        )

    bullets = _scan_bullets(body, heading.line_number + 1)
    roots = [node for node in bullets if node.parent is None]
    scqa_nodes = [node for node in bullets if _is_scqa(node)]
    root_scqa = next(
        (node for node in scqa_nodes if node.parent is None), None
    )

    if root_scqa is None:
        if scqa_nodes:
            result.error(
                "SCQA must be the root bullet in section 12",
                scqa_nodes[0].line_number,
            )
        else:
            result.error(
                "section 12 is missing the SCQA root bullet",
                heading.line_number,
            )
        return

    for duplicate in scqa_nodes:
        if duplicate is not root_scqa:
            result.error("duplicate SCQA node", duplicate.line_number)
    for root in roots:
        if root is not root_scqa:
            result.error(
                "SCQA must be the only root bullet in section 12",
                root.line_number,
            )

    scqa_children = _check_exact_children(
        result,
        root_scqa,
        [
            ("S", lambda node: _starts_with_code(node.normalized, "S")),
            ("C", lambda node: _starts_with_code(node.normalized, "C")),
            ("Q", lambda node: _starts_with_code(node.normalized, "Q")),
            ("A", lambda node: _starts_with_code(node.normalized, "A")),
        ],
        "SCQA",
    )
    for code, label, evidence in (
        ("S", "SCQA Situation", True),
        ("C", "SCQA Complication", True),
        ("Q", "SCQA Question", False),
        ("A", "SCQA Answer", True),
    ):
        _require_node_content(
            result,
            scqa_children.get(code),
            label,
            minimum=6,
            evidence=evidence,
        )
        if code in {"S", "C", "Q"}:
            _require_leaf_node(result, scqa_children.get(code), label)
    question = scqa_children.get("Q")
    if question is not None and not re.search(r"[?？]", _node_payload(question)):
        result.error(
            "SCQA Question must be written as a question",
            question.line_number,
        )

    answer = scqa_children.get("A")
    all_prep = [node for node in bullets if _is_prep(node)]
    prep = None
    if answer is not None:
        answer_children = _check_exact_children(
            result,
            answer,
            [("PREP", _is_prep)],
            "SCQA Answer",
        )
        prep = answer_children.get("PREP")

    if prep is None:
        if all_prep:
            result.error(
                "PREP must be nested under SCQA Answer",
                all_prep[0].line_number,
            )
        else:
            anchor = answer.line_number if answer else root_scqa.line_number
            result.error("missing PREP under SCQA Answer", anchor)
        return

    for other in all_prep:
        if other is not prep and other.parent is not answer:
            result.error(
                "PREP must be nested under SCQA Answer",
                other.line_number,
            )

    prep_children = _check_exact_children(
        result,
        prep,
        [
            ("P1", lambda node: _starts_with_code(node.normalized, "P1")),
            ("R", lambda node: _starts_with_code(node.normalized, "R")),
            ("E", lambda node: _starts_with_code(node.normalized, "E")),
            ("P2", lambda node: _starts_with_code(node.normalized, "P2")),
        ],
        "PREP",
    )
    for code, label in (
        ("P1", "PREP Point P1"),
        ("R", "PREP Reason"),
        ("P2", "PREP Point P2"),
    ):
        _require_node_content(
            result,
            prep_children.get(code),
            label,
            minimum=6,
            evidence=True,
        )
        if code in {"P1", "P2"}:
            _require_leaf_node(result, prep_children.get(code), label)

    reason = prep_children.get("R")
    example = prep_children.get("E")
    pyramid_candidates = [node for node in bullets if _is_pyramid_candidate(node)]
    pyramid = None
    if reason is not None:
        reason_children = _check_exact_children(
            result,
            reason,
            [("Pyramid", _is_pyramid_candidate)],
            "PREP Reason",
        )
        pyramid = reason_children.get("Pyramid")

    if pyramid is None:
        if pyramid_candidates:
            result.error(
                "Pyramid (金字塔原理 + MECE) must be nested under PREP Reason",
                pyramid_candidates[0].line_number,
            )
        elif reason is not None:
            result.error(
                "missing Pyramid (金字塔原理 + MECE) under PREP Reason",
                reason.line_number,
            )
        bottom_facts: list[Bullet] = []
    else:
        if not _is_complete_pyramid(pyramid):
            result.error(
                "Pyramid label must include both 金字塔原理 and MECE",
                pyramid.line_number,
            )
        if re.search(r"分類準則\s*[:：]\s*[^)）\s][^)）]*", pyramid.normalized) is None:
            result.error(
                "Pyramid label must state a non-empty 分類準則",
                pyramid.line_number,
            )
        for other in pyramid_candidates:
            if other is not pyramid and other.parent is not reason:
                result.error(
                    "Pyramid (金字塔原理 + MECE) must be nested under PREP Reason",
                    other.line_number,
                )
        bottom_facts = _validate_pyramid(result, pyramid)

    star_candidates = [node for node in bullets if _is_star_candidate(node)]
    valid_stars: list[Bullet] = []
    for candidate in star_candidates:
        if not _is_valid_star_label(candidate):
            result.error(
                "STAR label must be STAR｜實證案例 or STAR｜驗證設計",
                candidate.line_number,
            )
        else:
            valid_stars.append(candidate)

    if not valid_stars:
        result.error(
            "missing STAR｜實證案例 or STAR｜驗證設計 in section 12",
            example.line_number if example else prep.line_number,
        )
    elif len(valid_stars) > 1:
        for duplicate in valid_stars[1:]:
            result.error(
                "section 12 must contain exactly one STAR block",
                duplicate.line_number,
            )

    stars_under_example = [
        star for star in valid_stars if star.parent is example
    ] if example is not None else []
    if example is not None and not stars_under_example:
        _require_node_content(
            result, example, "PREP Example", minimum=6, evidence=False
        )
        example_payload = _node_payload(example)
        example_meaning = _plain_text(example_payload, remove_evidence=True)
        if not re.search(
            r"(?:案例|實證|過往|經驗|驗證|試點|測試|實驗|對照|演練|量測|證據)",
            example_meaning,
        ):
            result.error(
                "PREP Example must explain an example or validation design",
                example.line_number,
            )


    allowed_parents = ({id(example)} if example is not None else set()) | {
        id(node) for node in bottom_facts
    }
    if example is not None:
        allowed_example_children = {
            id(star) for star in valid_stars if star.parent is example
        }
        for child in example.children:
            if id(child) not in allowed_example_children:
                result.error(
                    "PREP Example may contain only the single STAR block as a child",
                    child.line_number,
                )
    valid_star_ids = {id(star) for star in valid_stars}
    for fact in bottom_facts:
        for child in fact.children:
            if id(child) not in valid_star_ids:
                result.error(
                    "Pyramid bottom fact may contain only the single STAR block as a child",
                    child.line_number,
                )
    for star in valid_stars:
        if star.parent is None or id(star.parent) not in allowed_parents:
            result.error(
                "STAR must be nested under PREP Example or a Pyramid bottom fact",
                star.line_number,
            )
        _validate_star(result, star, defined_sources)


def _recommendation_polarity(text: str) -> int:
    """Return -1 for explicit rejection, +1 for explicit adoption, else 0."""
    plain = _plain_text(text, remove_evidence=True).lower()
    adoption_verbs = r"(?:核准|批准|採用|啟動|導入|擴大|推動|開始|實施)"
    negative_pattern = re.compile(
        rf"(?:不應|不得|不宜|不能|未予|不予|不要|毋須|無須|避免)"
        rf"[^，,。；;]{{0,20}}{adoption_verbs}"
        rf"|(?:不核准|不批准|不採用|不啟動|不導入|不擴大|"
        r"禁止|拒絕|取消|終止|中止|永久停止|暫緩|放棄|must not|should not|"
        r"do not|ban|reject|prohibit|cancel|terminate)",
        flags=re.IGNORECASE,
    )
    negative = negative_pattern.search(plain)
    positive_text = negative_pattern.sub(" ", plain)
    positive = re.search(
        r"(?:核准|批准|採用|啟動|導入|擴大|推動|開始|實施|"
        r"approve|adopt|launch|implement|expand|proceed)",
        positive_text,
        flags=re.IGNORECASE,
    )
    if negative and not positive:
        return -1
    if positive and not negative:
        return 1
    return 0


def _validate_core_consistency(
    result: ValidationResult,
    sections: dict[int, tuple[Heading, list[str]]],
) -> None:
    """Catch explicit approve/reject contradictions across core claim surfaces."""
    section5 = sections.get(5)
    if section5 is None:
        return
    heading5, body5 = section5
    thesis = next(
        (
            _plain_text(line)
            for line in body5
            if line.strip()
            and not re.match(r"^\s*(?:#{1,6}|[-+*]\s|\|)", line)
        ),
        "",
    )
    thesis_polarity = _recommendation_polarity(thesis)
    if thesis_polarity == 0:
        return

    comparisons: list[tuple[str, str, int]] = []
    section9 = sections.get(9)
    if section9 is not None:
        heading9, body9 = section9
        comparisons.append(("section 9 one-sentence summary", " ".join(body9), heading9.line_number))

    section10 = sections.get(10)
    if section10 is not None:
        heading10, body10 = section10
        for table in _scan_tables(body10, heading10.line_number + 1):
            if not any(_header_matches(header, r"^受眾$") for header in table.headers):
                continue
            for row in table.rows:
                if row.cells:
                    comparisons.append((f"section 10 audience {row.cells[0]}", row.cells[-1], row.line_number))

    section12 = sections.get(12)
    if section12 is not None:
        heading12, body12 = section12
        for node in _scan_bullets(body12, heading12.line_number + 1):
            if (
                _starts_with_code(node.normalized, "P1")
                or _starts_with_code(node.normalized, "P2")
                or (
                    _starts_with_code(node.normalized, "A")
                    and node.parent is not None
                    and _is_scqa(node.parent)
                )
            ):
                comparisons.append(("section 12 core claim", _node_payload(node), node.line_number))

    for label, text, line_number in comparisons:
        polarity = _recommendation_polarity(text)
        if polarity and polarity != thesis_polarity:
            result.error(
                f"{label} explicitly contradicts the adoption/rejection direction of the Thesis",
                line_number,
            )


def validate_text(text: str) -> ValidationResult:
    result = ValidationResult()
    lines = text.splitlines()
    _validate_no_placeholders(result, lines)
    headings = _scan_headings(lines)
    _validate_sections(result, headings)
    sections = _section_bodies(lines, headings)
    defined_sources = _defined_source_ids(sections.get(1))

    _validate_epistemic_labels(result, sections.get(1))
    _validate_section_one(result, sections.get(1))
    _validate_source_integrity(result, lines, defined_sources)
    _validate_summary(result, sections.get(2))
    _validate_sections_three_to_eight(result, sections)
    _validate_one_sentence(result, sections.get(9))
    _validate_audiences(result, sections.get(10))
    _validate_actions(result, sections.get(11))
    _validate_model_tree(
        result,
        sections.get(12),
        defined_sources,
    )
    _validate_core_consistency(result, sections)
    return result


def _read_utf8(path: Path) -> tuple[str | None, str | None]:
    try:
        data = path.read_bytes()
    except OSError as exc:
        return None, f"cannot read {path}: {exc}"

    try:
        return data.decode("utf-8-sig"), None
    except UnicodeDecodeError as exc:
        return None, f"{path} is not valid UTF-8 (byte {exc.start})"


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print("ERROR: usage: python validate_report.py report.md")
        return 2

    text, read_error = _read_utf8(Path(args[0]))
    if read_error is not None:
        print(f"ERROR: {read_error}")
        return 2
    assert text is not None

    result = validate_text(text)
    for warning in result.warnings:
        print(warning)
    if result.ok:
        print("PASS")
        return 0

    for error in result.errors:
        print(error)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
