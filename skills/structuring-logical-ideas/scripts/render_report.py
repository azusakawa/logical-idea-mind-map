#!/usr/bin/env python3
"""Render a UTF-8 Markdown report as a polished, searchable A4 PDF."""

from __future__ import annotations

import argparse
import html
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable,
    LayoutError,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


_HEADING_RE = re.compile(r"^\s{0,3}(#{1,4})[ \t]+(.+?)\s*$")
_LIST_RE = re.compile(
    r"^(?P<indent>[ \t]*)(?P<marker>[-+*]|\d+[.)])[ \t]+(?P<text>.*)$"
)
_RULE_RE = re.compile(r"^\s{0,3}(?:(?:\*\s*){3,}|(?:-\s*){3,}|(?:_\s*){3,})\s*$")
_TABLE_SEPARATOR_RE = re.compile(r"^:?-{3,}:?$")
_INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")

_INK = colors.HexColor("#243447")
_MUTED = colors.HexColor("#667085")
_ACCENT = colors.HexColor("#176B67")
_ACCENT_DARK = colors.HexColor("#174A5B")
_PALE = colors.HexColor("#F2F7F7")
_LINE = colors.HexColor("#D6DEE3")
_TABLE_ALT = colors.HexColor("#F7F9FA")
_CODE = colors.HexColor("#8A3B12")
_CODE_BG = colors.HexColor("#F4F1ED")


@dataclass(frozen=True)
class FontChoice:
    """A registered ReportLab font and its optional source file."""

    name: str
    source: Path | None


@dataclass
class ListEntry:
    indent: int
    marker: str
    lines: list[str]


class MissingGlyphError(ValueError):
    """Raised when a font would silently render one or more characters as .notdef."""

    def __init__(self, missing: Sequence[str]):
        self.missing = tuple(missing)
        super().__init__(_format_missing_glyphs(self.missing))


def _font_missing_glyphs(font_name: str, rendered_text: str) -> list[str]:
    """Return every input character that maps to the font's .notdef glyph."""

    font = pdfmetrics.getFont(font_name)
    char_to_glyph = getattr(getattr(font, "face", None), "charToGlyph", {})
    required = sorted(
        {char for char in rendered_text if char not in {"\n", "\r", "\t"}},
        key=ord,
    )
    return [char for char in required if not char_to_glyph.get(ord(char), 0)]


def _format_missing_glyphs(missing: Sequence[str], limit: int = 12) -> str:
    shown: list[str] = []
    for character in missing[:limit]:
        name = unicodedata.name(character, "UNNAMED CHARACTER")
        shown.append(f"{character!r} (U+{ord(character):04X} {name})")
    suffix = f"; and {len(missing) - limit} more" if len(missing) > limit else ""
    return ", ".join(shown) + suffix


def _layout_unsafe_characters(rendered_text: str) -> list[str]:
    """Reject text this lightweight renderer cannot reliably shape or order."""

    unsafe: set[str] = set()
    for character in rendered_text:
        category = unicodedata.category(character)
        bidi = unicodedata.bidirectional(character)
        if category.startswith("M") or category == "Cf" or bidi in {"R", "AL", "AN"}:
            unsafe.add(character)
    return sorted(unsafe, key=ord)


def _validate_layout_safety(rendered_text: str) -> None:
    unsafe = _layout_unsafe_characters(rendered_text)
    if unsafe:
        raise ValueError(
            "this renderer cannot faithfully shape combining, format-control, or "
            "right-to-left text; unsupported characters: "
            f"{_format_missing_glyphs(unsafe)}. Use precomposed left-to-right text "
            "or a PDF renderer with complex-script shaping and bidirectional layout"
        )


def _font_roots() -> list[Path]:
    skill_root = Path(__file__).resolve().parent.parent
    roots = [
        skill_root,
        Path("/usr/share/fonts"),
        Path("/usr/local/share/fonts"),
        Path.home() / ".fonts",
        Path.home() / ".local/share/fonts",
        Path("/Library/Fonts"),
        Path("/System/Library/Fonts"),
        Path("C:/Windows/Fonts"),
    ]
    return [root for root in roots if root.is_dir()]


def _font_score(path: Path) -> tuple[int, str]:
    compact = re.sub(r"[^a-z0-9]", "", path.name.lower())
    priorities = (
        "notosanstc",
        "notosanscjktc",
        "notoseriftc",
        "notoserifcjktc",
        "sourcehansanstc",
        "sourcehanseriftc",
        "sourcehansans",
        "sourcehanserif",
        "notosanscjk",
        "notoserifcjk",
        "droidsansfallback",
        "wenquanyi",
        "uming",
        "ukai",
        "sarasa",
        "ipaex",
    )
    for rank, hint in enumerate(priorities):
        if hint in compact:
            return rank, str(path).lower()
    return len(priorities), str(path).lower()


def _discover_font_files() -> Iterable[Path]:
    """Yield likely CJK TrueType/OpenType files from conventional locations."""

    preferred = Path(__file__).resolve().parent.parent / "assets" / "NotoSansTC-Regular.ttf"
    if preferred.is_file():
        yield preferred.resolve()

    candidates: set[Path] = set()
    for root in _font_roots():
        for pattern in ("*.ttf", "*.otf", "*.TTF", "*.OTF"):
            try:
                paths = root.rglob(pattern)
                for path in paths:
                    candidates.add(path.resolve())
            except OSError:
                continue
    candidates.discard(preferred.resolve())
    yield from sorted(candidates, key=_font_score)


def _register_font(font_path: Path, alias: str, rendered_text: str) -> FontChoice:
    pdfmetrics.registerFont(TTFont(alias, str(font_path)))
    pdfmetrics.registerFontFamily(
        alias,
        normal=alias,
        bold=alias,
        italic=alias,
        boldItalic=alias,
    )
    missing = _font_missing_glyphs(alias, rendered_text)
    if missing:
        raise MissingGlyphError(missing)
    return FontChoice(alias, font_path)


def choose_font(rendered_text: str, requested: str | None = None) -> FontChoice:
    """Choose one embeddable font that covers every character that will be drawn."""

    if requested:
        requested_path = Path(requested).expanduser().resolve()
        if not requested_path.is_file():
            raise ValueError(f"font file does not exist: {requested_path}")
        if requested_path.suffix.lower() not in {".ttf", ".otf"}:
            raise ValueError("--font must name a .ttf or .otf file")
        try:
            return _register_font(requested_path, "ReportCJKUser", rendered_text)
        except MissingGlyphError as exc:
            raise ValueError(
                f"font {requested_path} is missing required glyphs: {exc}"
            ) from exc
        except Exception as exc:
            raise ValueError(f"cannot use font {requested_path}: {exc}") from exc

    coverage_failures: list[tuple[Path, tuple[str, ...]]] = []
    for index, candidate in enumerate(_discover_font_files()):
        try:
            return _register_font(candidate, f"ReportCJK{index}", rendered_text)
        except MissingGlyphError as exc:
            coverage_failures.append((candidate, exc.missing))
        except Exception:
            # Some CJK-named OTF files contain CFF outlines, which TTFont cannot use.
            continue

    if coverage_failures:
        candidate, missing = min(coverage_failures, key=lambda item: len(item[1]))
        raise ValueError(
            "no single embeddable TTF/OTF font covers every rendered character; "
            f"closest candidate {candidate} is missing: {_format_missing_glyphs(missing)}. "
            "Remove or replace those characters, or pass --font with a font that covers all of them"
        )
    raise ValueError(
        "no usable embeddable TTF/OTF font found; "
        "restore assets/NotoSansTC-Regular.ttf or pass --font PATH"
    )


def _inline_markup(text: str, font_name: str) -> str:
    """Escape arbitrary source text and retain simple bold/code formatting."""

    output: list[str] = []
    cursor = 0
    for match in _INLINE_CODE_RE.finditer(text):
        output.append(_bold_markup(text[cursor : match.start()]))
        code = html.escape(match.group(1), quote=False)
        output.append(
            f'<font name="{font_name}" color="{_CODE.hexval()}" '
            f'backColor="{_CODE_BG.hexval()}">{code}</font>'
        )
        cursor = match.end()
    output.append(_bold_markup(text[cursor:]))
    return "".join(output)


def _bold_markup(text: str) -> str:
    escaped = html.escape(text, quote=False)
    escaped = re.sub(r"\*\*(?=\S)(.+?)(?<=\S)\*\*", r"<b>\1</b>", escaped)
    escaped = re.sub(r"__(?=\S)(.+?)(?<=\S)__", r"<b>\1</b>", escaped)
    return escaped


def _paragraph_markup(lines: Sequence[str], font_name: str) -> str:
    chunks: list[str] = []
    for index, raw_line in enumerate(lines):
        hard_break = raw_line.endswith("  ")
        chunks.append(_inline_markup(raw_line.rstrip(), font_name))
        if index + 1 < len(lines):
            chunks.append("<br/>" if hard_break else " ")
    return "".join(chunks)


def _plain_markdown(text: str) -> str:
    text = re.sub(r"!\[([^]]*)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\[([^]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"[`*_~]", "", text)
    return html.unescape(text).strip()


def _split_table_row(line: str) -> list[str]:
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|") and not line.endswith(r"\|"):
        line = line[:-1]

    cells: list[str] = []
    current: list[str] = []
    escaped = False
    in_code = False
    for character in line:
        if escaped:
            current.append(character)
            escaped = False
        elif character == "\\":
            escaped = True
        elif character == "`":
            in_code = not in_code
            current.append(character)
        elif character == "|" and not in_code:
            cells.append("".join(current).strip())
            current = []
        else:
            current.append(character)
    if escaped:
        current.append("\\")
    cells.append("".join(current).strip())
    return cells


def _table_separator(line: str) -> list[str] | None:
    if "|" not in line:
        return None
    cells = _split_table_row(line)
    if cells and all(_TABLE_SEPARATOR_RE.fullmatch(cell) for cell in cells):
        return cells
    return None


def _display_width(text: str) -> int:
    plain = _plain_markdown(text)
    return sum(2 if unicodedata.east_asian_width(char) in {"W", "F"} else 1 for char in plain)


def _column_widths(rows: Sequence[Sequence[str]], available: float) -> list[float]:
    column_count = len(rows[0])
    weights = []
    for column in range(column_count):
        longest = max(_display_width(row[column]) for row in rows)
        weights.append(max(5.0, min(float(longest), 32.0)))

    floor = min(44.0, available / column_count * 0.58)
    widths = [available * weight / sum(weights) for weight in weights]
    fixed: set[int] = set()
    while True:
        newly_fixed = {index for index, width in enumerate(widths) if width < floor}
        newly_fixed -= fixed
        if not newly_fixed:
            break
        fixed |= newly_fixed
        remaining_width = available - floor * len(fixed)
        flexible = [index for index in range(column_count) if index not in fixed]
        if not flexible or remaining_width <= 0:
            return [available / column_count] * column_count
        remaining_weight = sum(weights[index] for index in flexible)
        widths = [
            floor if index in fixed else remaining_width * weights[index] / remaining_weight
            for index in range(column_count)
        ]
    return widths


def _make_styles(font_name: str) -> dict[str, ParagraphStyle]:
    sample = getSampleStyleSheet()
    body = ParagraphStyle(
        "ReportBody",
        parent=sample["BodyText"],
        fontName=font_name,
        fontSize=10.4,
        leading=16.2,
        textColor=_INK,
        alignment=TA_LEFT,
        wordWrap="CJK",
        splitLongWords=True,
        spaceAfter=6.5,
        allowWidows=0,
        allowOrphans=0,
    )
    return {
        "body": body,
        "h1": ParagraphStyle(
            "ReportH1",
            parent=body,
            fontSize=22,
            leading=29,
            textColor=_ACCENT_DARK,
            spaceBefore=0,
            spaceAfter=14,
            keepWithNext=True,
        ),
        "h2": ParagraphStyle(
            "ReportH2",
            parent=body,
            fontSize=16,
            leading=22,
            textColor=_ACCENT_DARK,
            spaceBefore=15,
            spaceAfter=7,
            keepWithNext=True,
        ),
        "h3": ParagraphStyle(
            "ReportH3",
            parent=body,
            fontSize=13,
            leading=18,
            textColor=_ACCENT,
            spaceBefore=11,
            spaceAfter=5,
            keepWithNext=True,
        ),
        "h4": ParagraphStyle(
            "ReportH4",
            parent=body,
            fontSize=11.2,
            leading=16,
            textColor=_ACCENT,
            spaceBefore=8,
            spaceAfter=4,
            keepWithNext=True,
        ),
        "quote": ParagraphStyle(
            "ReportQuote",
            parent=body,
            leftIndent=10,
            rightIndent=5,
            textColor=colors.HexColor("#3E5660"),
            backColor=_PALE,
            borderColor=_ACCENT,
            borderWidth=0.7,
            borderPadding=(7, 9, 7, 9),
            spaceBefore=5,
            spaceAfter=9,
        ),
        "table": ParagraphStyle(
            "ReportTableCell",
            parent=body,
            fontSize=8.7,
            leading=12.2,
            spaceAfter=0,
        ),
        "table_header": ParagraphStyle(
            "ReportTableHeader",
            parent=body,
            fontSize=9,
            leading=12.5,
            textColor=colors.white,
            spaceAfter=0,
        ),
    }


class MarkdownRenderer:
    def __init__(self, markdown: str, font: FontChoice, available_width: float):
        self.lines = markdown.expandtabs(4).splitlines()
        self.font = font
        self.styles = _make_styles(font.name)
        self.available_width = available_width

    def render(self) -> list[object]:
        story: list[object] = []
        index = 0
        while index < len(self.lines):
            line = self.lines[index]
            if not line.strip():
                index += 1
                continue

            heading = _HEADING_RE.match(line)
            if heading:
                level = len(heading.group(1))
                heading_text = re.sub(r"\s+#+\s*$", "", heading.group(2))
                story.append(
                    Paragraph(
                        f"<b>{_inline_markup(heading_text, self.font.name)}</b>",
                        self.styles[f"h{level}"],
                    )
                )
                index += 1
                continue

            if _RULE_RE.match(line):
                story.append(
                    HRFlowable(
                        width="100%",
                        thickness=0.7,
                        color=_LINE,
                        spaceBefore=7,
                        spaceAfter=9,
                    )
                )
                index += 1
                continue

            if self._starts_table(index):
                table, index = self._render_table(index)
                story.extend((table, Spacer(1, 3.5 * mm)))
                continue

            if re.match(r"^\s{0,3}>", line):
                quote_lines: list[str] = []
                while index < len(self.lines):
                    quote = re.match(r"^\s{0,3}>[ \t]?(.*)$", self.lines[index])
                    if not quote:
                        break
                    quote_lines.append(quote.group(1))
                    index += 1
                quote_markup = "<br/>".join(
                    _inline_markup(quote_line, self.font.name) if quote_line else "&#160;"
                    for quote_line in quote_lines
                )
                story.append(Paragraph(quote_markup, self.styles["quote"]))
                continue

            if _LIST_RE.match(line):
                entries, index = self._collect_list(index)
                story.extend(self._render_list(entries))
                story.append(Spacer(1, 2.5 * mm))
                continue

            # Preserve trailing double spaces, which Markdown defines as a hard break.
            paragraph_lines = [line.lstrip()]
            index += 1
            while index < len(self.lines) and self.lines[index].strip():
                if self._starts_block(index):
                    break
                paragraph_lines.append(self.lines[index].lstrip())
                index += 1
            story.append(
                Paragraph(
                    _paragraph_markup(paragraph_lines, self.font.name),
                    self.styles["body"],
                )
            )

        if not story:
            story.append(Paragraph("&#160;", self.styles["body"]))
        return story

    def _starts_table(self, index: int) -> bool:
        if index + 1 >= len(self.lines) or "|" not in self.lines[index]:
            return False
        separators = _table_separator(self.lines[index + 1])
        if separators is None:
            return False
        header = _split_table_row(self.lines[index])
        if len(header) != len(separators):
            raise ValueError(
                "malformed Markdown table at lines "
                f"{index + 1}-{index + 2}: header has {len(header)} columns but "
                f"separator has {len(separators)}"
            )
        return True

    def _starts_block(self, index: int) -> bool:
        line = self.lines[index]
        return bool(
            _HEADING_RE.match(line)
            or _RULE_RE.match(line)
            or _LIST_RE.match(line)
            or re.match(r"^\s{0,3}>", line)
            or self._starts_table(index)
        )

    def _collect_list(self, index: int) -> tuple[list[ListEntry], int]:
        entries: list[ListEntry] = []
        while index < len(self.lines):
            match = _LIST_RE.match(self.lines[index])
            if not match:
                break
            indent = len(match.group("indent"))
            entry = ListEntry(indent, match.group("marker"), [match.group("text")])
            entries.append(entry)
            index += 1

            while index < len(self.lines) and self.lines[index].strip():
                if _LIST_RE.match(self.lines[index]) or self._starts_block(index):
                    break
                continuation = self.lines[index]
                continuation_indent = len(continuation) - len(continuation.lstrip(" "))
                if continuation_indent <= indent:
                    break
                entry.lines.append(continuation.lstrip())
                index += 1
        return entries, index

    def _render_list(self, entries: Sequence[ListEntry]) -> list[Paragraph]:
        rendered: list[Paragraph] = []
        indent_stack: list[int] = []
        unordered_bullets = ("•", "◦", "▪")
        for position, entry in enumerate(entries):
            if not indent_stack:
                indent_stack.append(entry.indent)
            elif entry.indent > indent_stack[-1]:
                indent_stack.append(entry.indent)
            else:
                while len(indent_stack) > 1 and entry.indent < indent_stack[-1]:
                    indent_stack.pop()
                if entry.indent > indent_stack[-1]:
                    indent_stack.append(entry.indent)

            level = len(indent_stack) - 1
            left_indent = 13 + level * 13
            marker = (
                unordered_bullets[level % len(unordered_bullets)]
                if entry.marker in {"-", "+", "*"}
                else entry.marker
            )
            style = ParagraphStyle(
                f"ReportList{level}",
                parent=self.styles["body"],
                leftIndent=left_indent,
                firstLineIndent=0,
                bulletIndent=max(0, left_indent - 11),
                bulletFontName=self.font.name,
                bulletFontSize=9.5,
                bulletColor=_ACCENT_DARK,
                spaceAfter=2.2,
                keepWithNext=(
                    position + 1 < len(entries)
                    and entries[position + 1].indent > entry.indent
                ),
            )
            rendered.append(
                Paragraph(
                    _paragraph_markup(entry.lines, self.font.name),
                    style,
                    bulletText=html.escape(marker),
                )
            )
        return rendered

    def _render_table(self, index: int) -> tuple[Table, int]:
        header_line = index + 1
        header = _split_table_row(self.lines[index])
        separators = _split_table_row(self.lines[index + 1])
        raw_rows: list[list[str]] = [header]
        index += 2
        while index < len(self.lines) and self.lines[index].strip() and "|" in self.lines[index]:
            row = _split_table_row(self.lines[index])
            if len(row) != len(header):
                raise ValueError(
                    f"malformed Markdown table starting at line {header_line}: "
                    f"row {index + 1} has {len(row)} columns; expected {len(header)}"
                )
            raw_rows.append(row)
            index += 1

        data: list[list[Paragraph]] = []
        for row_index, row in enumerate(raw_rows):
            cell_style = self.styles["table_header"] if row_index == 0 else self.styles["table"]
            data.append(
                [Paragraph(_inline_markup(cell, self.font.name) or "&#160;", cell_style) for cell in row]
            )

        commands: list[tuple] = [
            ("BACKGROUND", (0, 0), (-1, 0), _ACCENT_DARK),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("GRID", (0, 0), (-1, -1), 0.35, _LINE),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]
        for row_index in range(1, len(raw_rows)):
            if row_index % 2 == 0:
                commands.append(("BACKGROUND", (0, row_index), (-1, row_index), _TABLE_ALT))
        for column, separator in enumerate(separators):
            alignment = "CENTER" if separator.startswith(":") and separator.endswith(":") else (
                "RIGHT" if separator.endswith(":") else "LEFT"
            )
            commands.append(("ALIGN", (column, 1), (column, -1), alignment))

        table = Table(
            data,
            colWidths=_column_widths(raw_rows, self.available_width),
            repeatRows=1,
            hAlign="LEFT",
            splitByRow=1,
            splitInRow=1,
        )
        table.setStyle(TableStyle(commands))
        return table, index


def _document_title(markdown: str, source: Path) -> str:
    for line in markdown.splitlines():
        heading = _HEADING_RE.match(line)
        if heading:
            title = _plain_markdown(re.sub(r"\s+#+\s*$", "", heading.group(2)))
            if title:
                return title
    return source.stem.replace("_", " ").replace("-", " ").strip() or "Markdown Report"


def _ellipsize(text: str, font_name: str, font_size: float, max_width: float) -> str:
    if pdfmetrics.stringWidth(text, font_name, font_size) <= max_width:
        return text
    suffix = "…"
    shortened = text
    while shortened and pdfmetrics.stringWidth(shortened + suffix, font_name, font_size) > max_width:
        shortened = shortened[:-1]
    return shortened + suffix


def render_pdf(source: Path, output: Path, font_path: str | None = None) -> FontChoice:
    # Match validate_report.py: accept an optional UTF-8 BOM without exposing
    # U+FEFF to layout/font preflight.
    markdown = source.read_text(encoding="utf-8-sig")
    title = _document_title(markdown, source)
    # Cover source content plus every string/symbol the renderer itself draws. This
    # preflight prevents ReportLab from silently substituting a .notdef/tofu glyph.
    rendered_text = "\n".join(
        (markdown, title, source.name, "Page 0123456789", "\u00a0•◦▪…")
    )
    _validate_layout_safety(rendered_text)
    font = choose_font(rendered_text, font_path)

    output.parent.mkdir(parents=True, exist_ok=True)
    page_width, page_height = A4
    left_margin = 18 * mm
    right_margin = 18 * mm
    top_margin = 23 * mm
    bottom_margin = 20 * mm
    available_width = page_width - left_margin - right_margin

    document = SimpleDocTemplate(
        str(output),
        pagesize=A4,
        leftMargin=left_margin,
        rightMargin=right_margin,
        topMargin=top_margin,
        bottomMargin=bottom_margin,
        title=title,
        author="",
        subject="Markdown report",
        creator="render_report.py",
    )
    story = MarkdownRenderer(markdown, font, available_width).render()

    def decorate_page(canvas, doc) -> None:
        canvas.saveState()
        canvas.setTitle(title)
        canvas.setSubject("Markdown report")
        canvas.setCreator("render_report.py")
        canvas.setStrokeColor(_LINE)
        canvas.setLineWidth(0.45)
        canvas.line(left_margin, page_height - 15.5 * mm, page_width - right_margin, page_height - 15.5 * mm)
        canvas.line(left_margin, 13.5 * mm, page_width - right_margin, 13.5 * mm)

        canvas.setFont(font.name, 8.2)
        canvas.setFillColor(_MUTED)
        header = _ellipsize(title, font.name, 8.2, available_width)
        canvas.drawString(left_margin, page_height - 12.5 * mm, header)
        source_label = _ellipsize(source.name, font.name, 8.2, available_width * 0.7)
        canvas.drawString(left_margin, 9.3 * mm, source_label)
        canvas.drawRightString(page_width - right_margin, 9.3 * mm, f"Page {doc.page}")
        canvas.restoreState()

    document.build(story, onFirstPage=decorate_page, onLaterPages=decorate_page)
    return font


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render UTF-8 Markdown, including Traditional Chinese, to an A4 PDF."
    )
    parser.add_argument("input", type=Path, help="UTF-8 Markdown source file")
    parser.add_argument("output", type=Path, help="destination PDF file")
    parser.add_argument(
        "--font",
        metavar="PATH",
        help="CJK-capable TTF/OTF to embed (auto-detected when omitted)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        font = render_pdf(args.input, args.output, args.font)
    except (OSError, UnicodeError, ValueError, LayoutError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    font_note = str(font.source) if font.source else font.name
    print(f"Wrote {args.output} using {font_note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
