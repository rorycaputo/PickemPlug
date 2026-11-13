#!/usr/bin/env python3
"""
Render comma-delimited CSV rows as a self-contained HTML table.

Handles ANSI SGR color codes embedded in cell values (e.g. from terminal
output that was captured verbatim into the CSV), such as:

    173.47\x1b[92m \x1b[00m

...and renders them as colored <span> elements instead of raw escape
sequences.

Uses only the standard library (re) plus lxml.
"""

import re

from lxml import etree
from lxml.html.builder import E
from lxml.html import tostring

import time_util


# --------------------------------------------------------------------------
# ANSI -> CSS color mapping (standard 16-color SGR foreground/background codes)
# --------------------------------------------------------------------------

ANSI_ESCAPE_RE = re.compile(r'\x1b\[([0-9;]*)m')

FG_COLORS = {
    30: '#000000', 31: '#cc0000', 32: '#4e9a06', 33: '#c4a000',
    34: '#3465a4', 35: '#75507b', 36: '#06989a', 37: '#d3d7cf',
    90: '#555753', 91: '#ef2929', 92: '#8ae234', 93: '#fce94f',
    94: '#729fcf', 95: '#ad7fa8', 96: '#34e2e2', 97: '#eeeeec',
}

BG_COLORS = {
    40: '#000000', 41: '#cc0000', 42: '#4e9a06', 43: '#c4a000',
    44: '#3465a4', 45: '#75507b', 46: '#06989a', 47: '#d3d7cf',
    100: '#555753', 101: '#ef2929', 102: '#8ae234', 103: '#fce94f',
    104: '#729fcf', 105: '#ad7fa8', 106: '#34e2e2', 107: '#eeeeec',
}


class AnsiState:
    """Tracks the current SGR styling as ANSI codes are applied."""

    def __init__(self):
        self.fg = None
        self.bg = None
        self.bold = False

    def apply(self, codes):
        for code in codes:
            if code == 0:
                self.fg = self.bg = None
                self.bold = False
            elif code == 1:
                self.bold = True
            elif code == 22:
                self.bold = False
            elif code == 39:
                self.fg = None
            elif code == 49:
                self.bg = None
            elif code in FG_COLORS:
                self.fg = FG_COLORS[code]
            elif code in BG_COLORS:
                self.bg = BG_COLORS[code]
            # Unsupported codes (underline, italic, 256-color, etc.) are
            # silently ignored rather than raising.

    def css(self):
        parts = []
        if self.fg:
            parts.append(f'color:{self.fg}')
        if self.bg:
            parts.append(f'background-color:{self.bg}')
        if self.bold:
            parts.append('font-weight:bold')
        return ';'.join(parts)

    def is_default(self):
        return not (self.fg or self.bg or self.bold)


def append_inline(parent, node_or_text):
    """
    Append a text node or an element to `parent`, correctly handling
    lxml's text/tail model (text before the first child goes on
    parent.text; text after a child goes on that child's .tail).
    """
    if isinstance(node_or_text, str):
        if len(parent) == 0:
            parent.text = (parent.text or '') + node_or_text
        else:
            last = parent[-1]
            last.tail = (last.tail or '') + node_or_text
    else:
        parent.append(node_or_text)


def cell_to_element(tag, raw_text):
    """
    Build a <td> or <th> element from raw cell text, converting any
    embedded ANSI escape sequences into styled <span> elements.
    """
    el = E(tag)

    if '\x1b[' not in raw_text:
        el.text = raw_text
        return el

    state = AnsiState()
    pos = 0
    for match in ANSI_ESCAPE_RE.finditer(raw_text):
        chunk = raw_text[pos:match.start()]
        if chunk:
            if state.is_default():
                append_inline(el, chunk)
            else:
                span = E.span(chunk, style=state.css())
                append_inline(el, span)

        code_str = match.group(1)
        codes = [int(c) for c in code_str.split(';') if c != ''] or [0]
        state.apply(codes)

        pos = match.end()

    tail = raw_text[pos:]
    if tail:
        if state.is_default():
            append_inline(el, tail)
        else:
            append_inline(el, E.span(tail, style=state.css()))

    return el


# --------------------------------------------------------------------------
# CSV -> HTML
# --------------------------------------------------------------------------

def parse_header_groups(header, words):
    """
    Walk `header` left to right and group consecutive columns whose names
    follow the pattern "<GROUP> <word>" for every word in `words`, in
    order, all sharing the same <GROUP>. A group is only recognized when
    all len(words) columns are present and match; otherwise each column
    is left as a standalone (single) header.

    Returns a list of items, each either:
        ('single', header_text)
        ('group', group_name, words)
    """
    if not words:
        return [('single', h) for h in header]

    groups = []
    i = 0
    n = len(header)
    while i < n:
        matched = False
        if i + len(words) <= n:
            candidate_group = None
            ok = True
            for j, word in enumerate(words):
                cell = header[i + j]
                suffix = f' {word}'
                if not cell.endswith(suffix):
                    ok = False
                    break
                group = cell[: -len(suffix)]
                if not group:
                    ok = False
                    break
                if candidate_group is None:
                    candidate_group = group
                elif group != candidate_group:
                    ok = False
                    break
            if ok:
                groups.append(('group', candidate_group, words))
                i += len(words)
                matched = True
        if not matched:
            groups.append(('single', header[i]))
            i += 1
    return groups


def add_class(el, cls):
    existing = el.get('class')
    el.set('class', f'{existing} {cls}' if existing else cls)


def group_column_starts(groups):
    """
    Return the set of body-column indices at which a new top-level
    header column (a 'single' header or a 'group') begins, excluding
    column 0 (there's nothing to the left of the first column to
    separate it from).
    """
    starts = set()
    col = 0
    for i, item in enumerate(groups):
        width = 1 if item[0] == 'single' else len(item[2])
        if i > 0:
            starts.add(col)
        col += width
    return starts


def build_thead(groups, boundary_cols):
    top_row_cells = []
    sub_row_cells = []
    col = 0
    for item in groups:
        if item[0] == 'single':
            th = cell_to_element('th', item[1])
            th.set('rowspan', '2')
            if col in boundary_cols:
                add_class(th, 'col-boundary')
            top_row_cells.append(th)
            col += 1
        else:
            _, group_name, words = item
            group_th = cell_to_element('th', group_name)
            group_th.set('colspan', str(len(words)))
            add_class(group_th, 'group-header')
            if col in boundary_cols:
                add_class(group_th, 'col-boundary')
            top_row_cells.append(group_th)
            for j, word in enumerate(words):
                sub_th = cell_to_element('th', word)
                if j == 0 and col in boundary_cols:
                    add_class(sub_th, 'col-boundary')
                sub_row_cells.append(sub_th)
            col += len(words)

    rows = [E.tr(*top_row_cells)]
    if sub_row_cells:
        rows.append(E.tr(*sub_row_cells))
    return E.thead(*rows)


def build_body_row(row, boundary_cols):
    cells = []
    for j, cell in enumerate(row):
        td = cell_to_element('td', cell)
        if j in boundary_cols:
            add_class(td, 'col-boundary')
        cells.append(td)
    return E.tr(*cells)


def build_html(rows, generated_at, title='CSV Export', sub_headers=None, preface_lines=None, header_text=None):
    """
    Args:
        rows: list of CSV rows (first row is the header).
        generated_at: aware datetime shown as the "generated" time, converted to
            the display zone.
        title: page title (used in <title>, and as the subtitle line
            above the table unless overridden by header_text below).
        sub_headers: optional list of exactly 3 words (e.g. ['word0',
            'word1', 'word2']). When present, any run of 3 consecutive
            header columns named "<GROUP> word0", "<GROUP> word1",
            "<GROUP> word2" (same GROUP, in that order) is rendered as a
            spanning group header over a sub-header row. Columns that
            don't match this pattern render as normal single headers.
        preface_lines: optional list of strings, printed in order as
            separate lines above the table. Supports the same embedded
            ANSI color codes as table cells.
        header_text: optional string printed as a bold heading at the
            very top of the page, above the "title — generated ..."
            subtitle line.
    """
    if not rows:
        raise ValueError('No rows found in CSV.')

    header, *body = rows

    groups = parse_header_groups(header, sub_headers)
    boundary_cols = group_column_starts(groups)

    thead = build_thead(groups, boundary_cols)
    tbody = E.tbody(*[build_body_row(row, boundary_cols) for row in body])
    table = E.table(thead, tbody, {'class': 'data-table'})

    preface_elements = [cell_to_element('p', line) for line in (preface_lines or [])]

    style = E.style("""
        :root { --gutter: 2rem; }
        body {
            font-family: 'Courier New', Consolas, monospace;
            background: #1e1e1e;
            color: #d3d7cf;
            padding: var(--gutter) 0 var(--gutter) var(--gutter);
        }
        h1, h2, .preface { padding-right: var(--gutter); }
        .table-inner {
            width: max-content;
            min-width: 100%;
            box-sizing: border-box;
            padding-right: var(--gutter);
        }
        h1 { font-size: 1.4rem; font-weight: bold; color: #eee; margin: 0 0 0.2rem 0; }
        h2 { font-size: 1.1rem; font-weight: normal; color: #888; margin: 0 0 0.6rem 0; }
        .preface p {
            margin: 0 0 0.4rem 0;
        }
        .preface {
            margin-bottom: 1.2rem;
        }
        .table-scroll {
            overflow-x: auto;
            max-width: 100%;
        }
        table.data-table {
            border-collapse: collapse;
            width: 100%;
            font-size: 0.9rem;
            border: 3px solid #777;
        }
        table.data-table th, table.data-table td {
            border: 1px solid #444;
            padding: 6px 10px;
            text-align: left;
            white-space: pre;
        }
        table.data-table th {
            background: #2d2d2d;
            color: #eee;
            position: sticky;
            top: 0;
            text-align: center;
        }
        table.data-table th.group-header {
            background: #383838;
            border-bottom: 1px solid #555;
        }
        table.data-table tr:nth-child(even) td {
            background: #252525;
        }
        table.data-table tbody tr {
            cursor: pointer;
        }
        table.data-table tbody tr:hover td {
            background: #3a3a1e !important;
        }
        table.data-table tbody tr.pinned td {
            background: #55510f !important;
        }
        table.data-table .col-boundary {
            border-left: 3px solid #777;
        }
        @media (max-width: 600px) {
            :root { --gutter: 0.75rem; }
            h1 { font-size: 1.2rem; }
            h2 { font-size: 0.95rem; }
            table.data-table { font-size: 0.85rem; }
            table.data-table th, table.data-table td { padding: 4px 6px; }        }
    """)

    table_wrapper = E.div(E.div(table, {'class': 'table-inner'}), {'class': 'table-scroll'})

    subtitle = cell_to_element(
        'h2', f'{title} — generated {time_util.to_display(generated_at).strftime("%d_%m_%y_%H_%M %Z")}'
    )

    body_children = []
    if header_text:
        body_children.append(cell_to_element('h1', header_text))
    body_children.append(subtitle)
    if preface_elements:
        body_children.append(E.div(*preface_elements, {'class': 'preface'}))
    body_children.append(table_wrapper)
    body_children.append(E.script("""
        document.querySelector('table.data-table tbody').addEventListener('click', function (event) {
            var row = event.target.closest('tr');
            if (row) {
                row.classList.toggle('pinned');
            }
        });
    """))

    doc = E.html(
        E.head(
            E.meta(charset='utf-8'),
            E.meta(name='viewport', content='width=device-width, initial-scale=1'),
            E.title(title),
            style,
        ),
        E.body(*body_children),
    )
    return doc


DAGGER = '\u2020'


def superscript_daggers(html_str):
    """
    Wrap every literal dagger character (U+2020, '†') in <sup> tags.

    Applied to the fully serialized HTML string (not per-cell), so it
    catches every dagger in the document regardless of where the text
    came from -- table cells, the title, the h1, or any section added
    to build_html() in the future. There's no way to type an actual
    superscript dagger glyph, so this is done with the <sup> tag instead.
    """
    return html_str.replace(DAGGER, f'<sup>{DAGGER}</sup>')


def render_html(
    rows,
    generated_at,
    title=None,
    sub_headers=None,
    preface_lines=None,
    header_text=None,
):
    """
    Render CSV rows (header row first) as a styled, ANSI-color-aware HTML page.

    Args:
        rows: list of rows, each a list of cell strings; the first row is the header.
        generated_at: aware datetime for the "generated" time in the subtitle
            (the CSV's creation time); shown in the display zone.
        title: Optional page title. Defaults to 'CSV Export'.
        sub_headers: optional list of exactly 3 words (e.g. ['word0',
            'word1', 'word2']). When provided, header columns named
            "<GROUP> word0", "<GROUP> word1", "<GROUP> word2" (all 3,
            same GROUP, consecutive, in that order) are rendered as a
            2-level header: a spanning "<GROUP>" cell over the 3 words.
            Columns that don't match the pattern are left as-is.
        preface_lines: optional list of strings, printed in order as
            separate lines above the table.
        header_text: optional string printed as a bold heading at the
            very top of the page, above the title/timestamp subtitle.

    Returns:
        The HTML document as a string.
    """
    doc = build_html(
        rows,
        title=title or 'CSV Export',
        sub_headers=sub_headers,
        preface_lines=preface_lines,
        header_text=header_text,
        generated_at=generated_at,
    )
    html_str = tostring(doc, doctype='<!DOCTYPE html>', pretty_print=True, encoding='unicode')
    return superscript_daggers(html_str)