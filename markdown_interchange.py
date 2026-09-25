"""Markdown as an interchange format for Scooper stories.

Two directions:

- Import: Markdown files (with optional YAML-style front matter, as written
  by Grav, Obsidian, Bear, Jekyll, ...) are converted into Editor.js block
  JSON so they become native, fully editable Scooper stories.
- Export: stories (block format or legacy HTML) are converted back into
  Markdown with front matter, so a Scooper export can be imported into Grav
  or a notes app - and back into Scooper.

Design notes:
- No YAML/Markdown libraries: this parses the pragmatic subset that real
  Grav pages and notes apps actually emit. Anything unrecognised degrades
  gracefully: unknown front matter is ignored, unparsed Markdown becomes a
  plain paragraph, unknown blocks export as best-effort text.
- Import never throws away content: if block conversion fails, the story is
  imported with the raw Markdown preserved as a plain text paragraph.
"""

import json
import re
from datetime import datetime

EDITORJS_VERSION = "2.30.7"

_DATE_FORMATS = (
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d",
    "%d-%m-%Y %H:%M:%S",
    "%d-%m-%Y %H:%M",
    "%d-%m-%Y",
    "%m/%d/%Y %H:%M:%S",
    "%m/%d/%Y",
    "%d. %m. %Y",
)


# ===========================================================================
# Front matter
# ===========================================================================

def parse_front_matter(text):
    """Split optional YAML-ish front matter from a Markdown document.

    Returns (meta, body). Handles the common Grav/Obsidian/Jekyll shape:
    a document starting with a --- line, flat ``key: value`` pairs, and one
    level of nesting (e.g. taxonomy: category: blog).
    """
    if not text.startswith("---"):
        return {}, text

    lines = text.split("\n")
    if lines[0].strip() != "---":
        return {}, text

    end = None
    for idx in range(1, len(lines)):
        if lines[idx].strip() in ("---", "..."):
            end = idx
            break
    if end is None:
        # Unterminated front matter: treat the whole file as body
        return {}, text

    meta = {}
    parent_key = None
    for line in lines[1:end]:
        if not line.strip() or line.strip().startswith("#"):
            continue
        if line[:1].isspace():
            # Nested key (e.g. "    category: blog" under "taxonomy:")
            m = re.match(r"^\s+([A-Za-z0-9_-]+)\s*:\s*(.*)$", line)
            if m and parent_key:
                meta.setdefault(parent_key, {})[m.group(1)] = _clean_value(m.group(2))
            continue
        m = re.match(r"^([A-Za-z0-9_-]+)\s*:\s*(.*)$", line)
        if not m:
            parent_key = None
            continue
        key, value = m.group(1), m.group(2)
        if value.strip() == "":
            # Opens a nested mapping
            parent_key = key
            meta[key] = {}
        else:
            parent_key = None
            meta[key] = _clean_value(value)

    body = "\n".join(lines[end + 1:]).lstrip("\n")
    return meta, body


def _clean_value(value):
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        value = value[1:-1]
    lowered = value.lower()
    if lowered in ("true", "yes", "on"):
        return True
    if lowered in ("false", "no", "off"):
        return False
    return value


def meta_to_story_fields(meta, fallback_title):
    """Map parsed front matter onto Scooper story fields."""
    taxonomy = meta.get("taxonomy") if isinstance(meta.get("taxonomy"), dict) else {}
    title = meta.get("title") or fallback_title
    excerpt = meta.get("excerpt") or meta.get("summary") or ""
    if not isinstance(excerpt, str):
        excerpt = str(excerpt)

    published = None
    if "published" in meta:
        published = meta["published"] is True or meta["published"] == "true"

    return {
        "title": title,
        "slug": meta.get("slug") or "",
        "excerpt": excerpt,
        "category": taxonomy.get("category") or meta.get("category") or "",
        "author": meta.get("author") or "",
        "published": published,
        "published_at": parse_date(meta.get("date") or meta.get("published_date")),
    }


def parse_date(value):
    """Best-effort date parsing; returns ISO string or None."""
    if not value or not isinstance(value, str):
        return None
    value = value.strip()
    try:
        return datetime.fromisoformat(value).isoformat()
    except ValueError:
        pass
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).isoformat()
        except ValueError:
            continue
    return None


def extract_leading_heading(body):
    """Return (title, body) using a leading '# Heading' as the title.

    Notes-app exports usually start with a heading instead of front matter.
    The heading line is consumed so the story does not repeat its title.
    Returns (None, body) when the document does not start with a heading.
    """
    lines = body.split("\n")
    for idx, line in enumerate(lines):
        if not line.strip():
            continue
        m = re.match(r"^#{1,6}\s+(.*)$", line.strip())
        if m:
            title = _md_inline_to_plain(m.group(1))
            rest = "\n".join(lines[idx + 1:]).lstrip("\n")
            return title, rest
        break
    return None, body


# ===========================================================================
# Import: Markdown -> Editor.js blocks
# ===========================================================================

_HEADER_RE = re.compile(r"^(#{1,6})\s+(.*)$")
_LIST_ITEM_RE = re.compile(r"^(\s*)(?:([-*+])|(\d+[.)]))\s+(.*)$")
_IMAGE_ONLY_RE = re.compile(r"^!\[(.*?)\]\((\S*?)(?:\s+[\"'](.*)[\"'])?\)$")
_CAPTION_RE = re.compile(r"^(?:--|-|—)\s+\S")
_TABLE_SEP_RE = re.compile(r"^\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?$")


def _is_table_separator(line):
    return bool(_TABLE_SEP_RE.match(line.strip()))


def _split_table_row(line):
    """'| a | b |' -> ['a', 'b'] (no inline conversion; done per cell later)."""
    cells = line.strip().strip("|").split("|")
    return [c.strip() for c in cells]


def _escape_text(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _inline_md_to_html(text):
    """Convert inline Markdown marks to the HTML Editor.js stores."""
    text = _escape_text(text)
    # Protect code spans first
    code_spans = []

    def _stash_code(m):
        code_spans.append(m.group(1))
        return f"\x00{len(code_spans) - 1}\x00"

    text = re.sub(r"`([^`]+)`", _stash_code, text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"__([^_]+)__", r"<b>\1</b>", text)
    text = re.sub(r"(?<!\w)_([^_\n]+)_(?!\w)", r"<i>\1</i>", text)
    text = re.sub(r"\*([^*\n]+)\*", r"<i>\1</i>", text)
    text = re.sub(r"==([^=]+)==", r"<mark>\1</mark>", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r'<a href="\2">\1</a>', text)
    for idx, code in enumerate(code_spans):
        text = text.replace(f"\x00{idx}\x00", f"<code>{code}</code>")
    return text


def _md_inline_to_plain(text):
    """Strip inline Markdown marks (for image captions, alt text)."""
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"__([^_]+)__", r"\1", text)
    text = re.sub(r"(?<!\w)_([^_\n]+)_(?!\w)", r"\1", text)
    text = re.sub(r"\*([^*\n]+)\*", r"\1", text)
    text = re.sub(r"==([^=]+)==", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r"\1", text)
    return text.strip()


def _parse_list(lines, i, indent=0):
    """Recursively parse a Markdown list starting at lines[i]."""
    items = []
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            break
        m = _LIST_ITEM_RE.match(line)
        if not m or len(m.group(1)) < indent:
            break
        if len(m.group(1)) > indent:
            # Deeper indentation than expected: treat as start of nested list
            nested, i = _parse_list(lines, i, len(m.group(1)))
            if items:
                items[-1]["items"] = nested
            continue
        i += 1
        nested = []
        if i < len(lines):
            nxt = _LIST_ITEM_RE.match(lines[i])
            if nxt and len(nxt.group(1)) > indent:
                nested, i = _parse_list(lines, i, len(nxt.group(1)))
        items.append({"content": _inline_md_to_html(m.group(4)), "items": nested})
    return items, i


def markdown_to_blocks(markdown_text):
    """Convert a Markdown document into a list of Editor.js block dicts."""
    lines = (markdown_text or "").replace("\r\n", "\n").split("\n")
    blocks = []
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()

        if not stripped:
            i += 1
            continue

        # Fenced code
        if stripped.startswith("```") or stripped.startswith("~~~"):
            fence = stripped[:3]
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith(fence):
                code_lines.append(lines[i])
                i += 1
            i += 1  # closing fence
            blocks.append({"type": "code", "data": {"code": "\n".join(code_lines)}})
            continue

        # Delimiter
        if stripped in ("---", "***", "___"):
            blocks.append({"type": "delimiter", "data": {}})
            i += 1
            continue

        # Header
        m = _HEADER_RE.match(stripped)
        if m:
            blocks.append({
                "type": "header",
                "data": {"text": _inline_md_to_html(m.group(2)), "level": min(len(m.group(1)), 6)},
            })
            i += 1
            continue

        # Quote (consecutive > lines, optional "-- caption" last line)
        if stripped.startswith(">"):
            quote_lines = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                quote_lines.append(lines[i].strip().lstrip(">").strip())
                i += 1
            caption = ""
            if len(quote_lines) > 1 and _CAPTION_RE.match(quote_lines[-1]):
                caption = re.sub(r"^(?:--|-|—)\s*", "", quote_lines.pop()).strip()
            blocks.append({
                "type": "quote",
                "data": {"text": _inline_md_to_html(" ".join(quote_lines)), "caption": caption},
            })
            continue

        # Standalone image
        m = _IMAGE_ONLY_RE.match(stripped)
        if m:
            blocks.append({
                "type": "image",
                "data": {
                    "file": {"url": m.group(2)},
                    "caption": _md_inline_to_plain(m.group(1)),
                },
            })
            i += 1
            continue

        # List
        m = _LIST_ITEM_RE.match(lines[i])
        if m and not stripped.startswith(("#",)):
            ordered = bool(m.group(3))
            items, i = _parse_list(lines, i, len(m.group(1)))
            if items:
                blocks.append({
                    "type": "list",
                    "data": {"style": "ordered" if ordered else "unordered", "items": items},
                })
            continue

        # GFM table: header row + |---|---| separator + body rows
        if stripped.startswith("|") and i + 1 < len(lines) and _is_table_separator(lines[i + 1]):
            header = _split_table_row(stripped)
            i += 2
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(_split_table_row(lines[i].strip()))
                i += 1
            content = [
                [_inline_md_to_html(cell) for cell in row]
                for row in [header] + rows
            ]
            blocks.append({
                "type": "table",
                "data": {"withHeadings": True, "content": content},
            })
            continue

        # Paragraph: join lines until blank line or next block construct
        para = [stripped]
        i += 1
        while i < len(lines):
            nxt = lines[i].strip()
            if (
                not nxt
                or nxt.startswith(("#", ">", "```", "~~~", "|"))
                or nxt in ("---", "***", "___")
                or _LIST_ITEM_RE.match(lines[i])
                or _IMAGE_ONLY_RE.match(nxt)
            ):
                break
            para.append(nxt)
            i += 1
        blocks.append({"type": "paragraph", "data": {"text": _inline_md_to_html(" ".join(para))}})

    return blocks


def markdown_to_editorjs(markdown_text, fallback_paragraph=None):
    """Markdown to a full Editor.js document JSON string.

    Never raises on conversion trouble: falls back to a single paragraph
    block so imported content is never lost.
    """
    try:
        blocks = markdown_to_blocks(markdown_text)
    except Exception:
        blocks = []
    if not blocks and fallback_paragraph is not None:
        blocks = [{"type": "paragraph", "data": {"text": _escape_text(fallback_paragraph)}}]
    return json.dumps({"time": 0, "blocks": blocks, "version": EDITORJS_VERSION})


# ===========================================================================
# Export: Editor.js blocks / legacy HTML -> Markdown
# ===========================================================================

_TAG_RE = re.compile(r"<\s*(/?)\s*([a-zA-Z0-9-]+)((?:[^<>]*)?)>", re.DOTALL)
_HREF_RE = re.compile(r"""href\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))""", re.IGNORECASE)


def _md_text(chunk):
    return chunk.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")


def _tags_to_md(text):
    """Inline HTML -> inline Markdown, ignoring anchors (handled upstream)."""
    parts = []
    pos = 0
    for match in _TAG_RE.finditer(text):
        parts.append(_md_text(text[pos:match.start()]))
        pos = match.end()
        closing, name = match.group(1), match.group(2).lower()
        if name == "br" and not closing:
            parts.append("  \n")
            continue
        marker = {
            "b": "**", "strong": "**",
            "i": "*", "em": "*",
            "code": "`", "mark": "==",
        }.get(name)
        if marker:
            parts.append(marker)
        # Unknown tags are dropped; their text content survives
    parts.append(_md_text(text[pos:]))
    return "".join(parts)


def _inline_to_md(html_text):
    """Inline HTML -> inline Markdown.

    <a href>text</a> needs reordering into [text](href), so anchors get a
    targeted pass first; everything else goes through the generic converter.
    """
    if not html_text:
        return ""

    def _link(m):
        return f"[{_tags_to_md(m.group(2))}]({m.group(1)})"

    text = re.sub(
        r'<a\s+(?:[^>]*?)*?href\s*=\s*["\']([^"\']*)["\'][^>]*>(.*?)</a>',
        _link,
        html_text,
        flags=re.DOTALL,
    )
    return _tags_to_md(text)


def _list_items_to_md(items, ordered, depth=0):
    lines = []
    for idx, item in enumerate(items):
        marker = f"{idx + 1}." if ordered else "-"
        prefix = "    " * depth
        lines.append(f"{prefix}{marker} {_inline_to_md(item.get('content', ''))}")
        nested = item.get("items") or []
        if nested:
            lines.append(_list_items_to_md(nested, ordered, depth + 1))
    return "\n".join(lines)


def blocks_to_markdown(content):
    """Editor.js document (JSON string or dict) -> Markdown body."""
    if isinstance(content, str):
        try:
            doc = json.loads(content)
        except ValueError:
            return content
    else:
        doc = content
    if not isinstance(doc, dict) or not isinstance(doc.get("blocks"), list):
        return ""

    out = []
    for block in doc.get("blocks") or []:
        if not isinstance(block, dict):
            continue
        data = block.get("data") or {}
        kind = block.get("type")

        if kind == "paragraph":
            out.append(_inline_to_md(data.get("text", "")))
        elif kind == "header":
            level = max(1, min(int(data.get("level", 2) or 2), 6))
            out.append("#" * level + " " + _inline_to_md(data.get("text", "")))
        elif kind == "list":
            out.append(_list_items_to_md(data.get("items") or [], data.get("style") == "ordered"))
        elif kind == "quote":
            quote = "> " + _inline_to_md(data.get("text", ""))
            caption = data.get("caption", "")
            if caption:
                quote += "\n>\n> -- " + _inline_to_md(caption)
            out.append(quote)
        elif kind == "code":
            out.append("```\n" + (data.get("code", "") or "") + "\n```")
        elif kind == "delimiter":
            out.append("---")
        elif kind == "image":
            url = (data.get("file") or {}).get("url", "")
            alt = data.get("caption", "") or "image"
            out.append(f"![{_inline_to_md(alt)}]({url})")
        elif kind == "table":
            out.append(_table_to_md(data))
        elif kind == "warning":
            title = _inline_to_md(data.get("title", ""))
            message = _inline_to_md(data.get("message", ""))
            lines = ["> **" + title + "**"] if title else []
            if message:
                lines.append("> " + message)
            if lines:
                out.append("\n".join(lines))
        elif kind == "embed":
            # No universal Markdown embed: fall back to a link
            caption = _inline_to_md(data.get("caption", "")) or "Embedded video"
            url = data.get("source") or data.get("embed") or ""
            out.append(f"[{caption}]({url})")
        # Unknown block types are skipped (same policy as the renderer)

    return "\n\n".join(part for part in out if part is not None)


def _table_to_md(data):
    rows = data.get("content") or []
    if not rows:
        return ""
    rows = [[_inline_to_md(str(cell)).replace("|", "\\|") for cell in row] for row in rows]
    if data.get("withHeadings") and len(rows) > 1:
        head, body = rows[0], rows[1:]
    else:
        head, body = rows[0], rows[1:]
        head = head if data.get("withHeadings") else None
    lines = []
    if head is not None:
        lines.append("| " + " | ".join(head) + " |")
        lines.append("| " + " | ".join(["---"] * len(head)) + " |")
        body_rows = body
    else:
        body_rows = rows
    for row in body_rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def story_to_markdown(story):
    """A full story dict -> a Markdown document with front matter.

    Works for both block-format and legacy HTML stories.
    """
    from editorjs_render import plain_text_excerpt

    if story.get("content_format") == "editorjs":
        body = blocks_to_markdown(story.get("content", ""))
    else:
        body = html_to_markdown(story.get("content", ""))

    excerpt = story.get("excerpt") or ""
    if not excerpt.strip():
        excerpt = plain_text_excerpt(
            story.get("content", ""), story.get("content_format", "html")
        )
    excerpt = " ".join(excerpt.split())

    published = bool(story.get("published"))
    date = story.get("published_at") or story.get("created_at") or ""
    try:
        date = datetime.fromisoformat(date).strftime("%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        pass

    front = [
        "---",
        f"title: {story.get('title', '')}",
        f"slug: {story.get('slug', '')}",
        f"author: {story.get('author', 'Admin')}",
        f"category: {story.get('category', 'General')}",
        f"published: {str(published).lower()}",
    ]
    if date:
        front.append(f"date: {date}")
    if excerpt:
        front.append(f"excerpt: {excerpt}")
    front.append("---")

    return "\n".join(front) + "\n\n" + body.strip() + "\n"


# ===========================================================================
# Export fallback: legacy HTML -> Markdown
# ===========================================================================

from html.parser import HTMLParser


class _HTMLToMarkdown(HTMLParser):
    """Best-effort conversion of legacy (Quill) HTML to Markdown."""

    BLOCK_TAGS = {"p", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote",
                  "pre", "ul", "ol", "table", "figure", "hr", "aside"}
    INLINE_MAP = {
        "b": "**", "strong": "**",
        "i": "*", "em": "*",
        "code": "`", "mark": "==", "kbd": "`",
    }

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self._list_stack = []  # [ordered, counter]
        self._quote_depth = 0
        self._in_pre = False
        self._in_table = False
        self._row_cells = None   # current row: list of cell strings
        self._cell_buffer = None  # current cell parts
        self._table_rows = []

    # -- helpers -------------------------------------------------------
    def _newline(self, count=2):
        if self.parts and not self.parts[-1].endswith("\n"):
            self.parts.append("\n" * count)
        elif self.parts:
            # collapse to at most one blank line
            stripped = self.parts[-1].rstrip("\n")
            self.parts[-1] = stripped + "\n" * count

    def result(self):
        text = "".join(self.parts)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    # -- block handlers ------------------------------------------------
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if self._in_table:
            if tag == "tr":
                self._row_cells = []
            elif tag in ("td", "th"):
                if self._row_cells is None:
                    self._row_cells = []
                self._cell_buffer = []
            elif tag in self.INLINE_MAP and self._cell_buffer is not None:
                self._cell_buffer.append(self.INLINE_MAP[tag])
            elif tag == "br" and self._cell_buffer is not None:
                self._cell_buffer.append(" ")
            return
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self._newline()
            self.parts.append("#" * int(tag[1]) + " ")
        elif tag == "p":
            self._newline()
        elif tag == "br":
            self.parts.append("  \n")
        elif tag == "blockquote":
            self._quote_depth += 1
            self._newline()
        elif tag == "pre":
            self._in_pre = True
            self._newline()
            self.parts.append("```\n")
        elif tag in ("ul", "ol"):
            self._list_stack.append([tag == "ol", 0])
            self._newline()
        elif tag == "li":
            ordered, counter = (self._list_stack[-1] if self._list_stack else [False, 0])
            counter += 1
            if self._list_stack:
                self._list_stack[-1][1] = counter
            depth = max(0, len(self._list_stack) - 1)
            marker = f"{counter}." if ordered else "-"
            self.parts.append("    " * depth + marker + " ")
        elif tag == "hr":
            self._newline(2)
            self.parts.append("---\n\n")
        elif tag == "img":
            alt = attrs.get("alt", "image")
            src = attrs.get("src", "")
            self._newline()
            self.parts.append(f"![{alt}]({src})")
            self._newline()
        elif tag == "a":
            href = attrs.get("href", "")
            self.parts.append("\x01" + href)
        elif tag == "table":
            self._in_table = True
            self._table_rows = []
        elif tag in self.INLINE_MAP and not self._in_pre:
            self.parts.append(self.INLINE_MAP[tag])

    def handle_endtag(self, tag):
        if self._in_table:
            if tag in ("td", "th") and self._cell_buffer is not None:
                self._row_cells.append("".join(self._cell_buffer).strip())
                self._cell_buffer = None
            elif tag == "tr":
                if self._row_cells:
                    self._table_rows.append(self._row_cells)
                self._row_cells = None
            elif tag == "table":
                self._in_table = False
                self._flush_table()
            elif tag in self.INLINE_MAP and self._cell_buffer is not None:
                self._cell_buffer.append(self.INLINE_MAP[tag])
            return
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6", "p"):
            self._newline()
        elif tag == "blockquote":
            self._quote_depth = max(0, self._quote_depth - 1)
            self._newline()
        elif tag == "pre":
            self._in_pre = False
            self.parts.append("\n```")
            self._newline()
        elif tag in ("ul", "ol"):
            if self._list_stack:
                self._list_stack.pop()
            self._newline()
        elif tag == "li":
            self.parts.append("\n")
        elif tag == "a":
            self._close_link()
        elif tag in self.INLINE_MAP and not self._in_pre:
            self.parts.append(self.INLINE_MAP[tag])

    def handle_data(self, data):
        if self._cell_buffer is not None:
            self._cell_buffer.append(data)
            return
        if self._in_pre:
            self.parts.append(data)
            return
        if self._quote_depth:
            for line in data.split("\n"):
                if line.strip():
                    self.parts.append("> " + line.strip())
                elif line:
                    self.parts.append(">\n")
                else:
                    self.parts.append("\n")
        else:
            self.parts.append(data)

    # -- link/table plumbing -------------------------------------------
    def _close_link(self):
        # Links are stashed as \x01 + href, followed by their inner text
        for idx in range(len(self.parts) - 1, -1, -1):
            if self.parts[idx].startswith("\x01"):
                href = self.parts[idx][1:]
                inner = "".join(self.parts[idx + 1:])
                del self.parts[idx:]
                self.parts.append(f"[{inner.strip()}]({href})")
                return
        self.parts.append("")

    def _flush_table(self):
        rows = self._table_rows
        self._table_rows = []
        if not rows:
            return
        lines = []
        for r_idx, row in enumerate(rows):
            lines.append("| " + " | ".join(c.replace("|", "\\|") for c in row) + " |")
            if r_idx == 0:
                lines.append("| " + " | ".join(["---"] * len(row)) + " |")
        self._newline()
        self.parts.append("\n".join(lines))
        self._newline(1)


def html_to_markdown(html_text):
    """Convert legacy HTML content to Markdown (best effort)."""
    if not html_text:
        return ""
    converter = _HTMLToMarkdown()
    try:
        converter.feed(html_text)
        converter.close()
    except Exception:
        # Absolute fallback: strip tags, keep text
        return re.sub(r"<[^>]*>", "", html_text).strip()
    return converter.result()
