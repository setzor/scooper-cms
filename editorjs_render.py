"""Render Editor.js block JSON into trusted HTML for Scooper story pages.

Stories edited with the block editor store their content as an Editor.js
output document (JSON) with content_format = 'editorjs'. This module converts
that document into the HTML shown on public story pages and previews.

Design notes:
- Block content is authored by CMS admins (same trust model as the legacy
  Quill HTML), but inline markup is still filtered through a small whitelist
  so a compromised or mangled editor payload cannot smuggle script tags or
  event handlers into public pages.
- Image and embed sources are restricted to same-origin paths and http(s).
- Unknown block types are skipped rather than guessed at.
"""

import json
import re

from template_engine import SafeString, escape_html

CONTENT_FORMAT_HTML = "html"
CONTENT_FORMAT_EDITORJS = "editorjs"

# Inline tags produced by Editor.js inline tools (bold, italic, link, ...)
ALLOWED_INLINE_TAGS = {"b", "strong", "i", "em", "u", "s", "del", "code", "mark", "br", "a"}
ALLOWED_URL_SCHEMES = ("http://", "https://", "mailto:", "/", "#")

_TAG_RE = re.compile(r"<\s*(/?)\s*([a-zA-Z0-9-]+)((?:[^<>]*)?)>", re.DOTALL)
_HREF_RE = re.compile(r"""href\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))""", re.IGNORECASE)
_TAG_STRIP_RE = re.compile(r"<[^>]*>")


def _safe_url(url):
    """Return an attribute-safe URL if it uses an allowed scheme, else None."""
    if not url:
        return None
    url = url.strip()
    lowered = url.lower()
    if lowered.startswith(ALLOWED_URL_SCHEMES) and not lowered.startswith("//"):
        return url
    return None


def render_inline(text):
    """Filter Editor.js inline markup through a tag whitelist.

    Text between tags is HTML-escaped; only whitelisted tags survive, and
    anchors may keep only a scheme-checked href attribute.
    """
    out = []
    pos = 0
    for match in _TAG_RE.finditer(text or ""):
        out.append(escape_html(text[pos:match.start()]))
        pos = match.end()

        closing, name, attrs = match.group(1), match.group(2).lower(), match.group(3) or ""
        if name not in ALLOWED_INLINE_TAGS:
            continue
        if closing:
            if name != "br":
                out.append(f"</{name}>")
            continue
        if name == "br":
            out.append("<br>")
            continue
        if name == "a":
            href_match = _HREF_RE.search(attrs)
            href = _safe_url(href_match.group(1) or href_match.group(2) or href_match.group(3)) if href_match else ""
            if href:
                out.append(f'<a href="{escape_html(href)}" rel="noopener">')
            else:
                out.append("<a>")
        else:
            out.append(f"<{name}>")
    out.append(escape_html(text[pos:] if text else ""))
    return "".join(out)


def _render_list_items(items, ordered):
    tag = "ol" if ordered else "ul"
    parts = [f"<{tag}>"]
    for item in items:
        if not isinstance(item, dict):
            continue
        content = render_inline(item.get("content", ""))
        nested = item.get("items") or []
        if nested:
            parts.append(f"<li>{content}{_render_list_items(nested, ordered)}</li>")
        else:
            parts.append(f"<li>{content}</li>")
    parts.append(f"</{tag}>")
    return "".join(parts)


def _render_image(data):
    file_info = data.get("file") or {}
    url = _safe_url(file_info.get("url", ""))
    if not url:
        return ""
    caption = data.get("caption", "")
    classes = ["story-figure"]
    if data.get("stretched"):
        classes.append("story-figure--wide")
    alt = _TAG_STRIP_RE.sub("", caption).strip() or "Story image"
    html = f'<figure class="{" ".join(classes)}">'
    html += f'<img src="{escape_html(url)}" alt="{escape_html(alt)}" loading="lazy">'
    if caption:
        html += f"<figcaption>{render_inline(caption)}</figcaption>"
    html += "</figure>"
    return html


def _render_table(data):
    rows = data.get("content") or []
    if not rows:
        return ""
    with_headings = bool(data.get("withHeadings"))
    parts = ["<table>"]
    if with_headings:
        parts.append("<thead>")
        for cell in rows[0]:
            parts.append(f"<th>{render_inline(cell)}</th>")
        parts.append("</thead>")
        rows = rows[1:]
    parts.append("<tbody>")
    for row in rows:
        parts.append("<tr>")
        for cell in row:
            parts.append(f"<td>{render_inline(str(cell))}</td>")
        parts.append("</tr>")
    parts.append("</tbody></table>")
    return "".join(parts)


def _render_embed(data):
    service = data.get("service", "")
    if service not in ("youtube", "vimeo"):
        return ""
    url = _safe_url(data.get("embed", ""))
    if not url:
        return ""
    html = (
        f'<figure class="story-embed">'
        f'<iframe src="{escape_html(url)}" loading="lazy" '
        f'allowfullscreen title="Embedded video"></iframe>'
    )
    caption = data.get("caption", "")
    if caption:
        html += f"<figcaption>{render_inline(caption)}</figcaption>"
    html += "</figure>"
    return html


def _render_warning(data):
    title = data.get("title", "")
    message = data.get("message", "")
    if not title and not message:
        return ""
    html = '<aside class="story-warning">'
    if title:
        html += f"<strong>{render_inline(title)}</strong>"
    if message:
        html += f"<p>{render_inline(message)}</p>"
    html += "</aside>"
    return html


def _render_block(block):
    block_type = block.get("type", "")
    data = block.get("data") or {}

    if block_type == "paragraph":
        return f"<p>{render_inline(data.get('text', ''))}</p>"
    if block_type == "header":
        level = data.get("level", 2)
        try:
            level = int(level)
        except (TypeError, ValueError):
            level = 2
        # The story title is the page's h1; keep the outline clean.
        level = min(max(level, 2), 6)
        return f"<h{level}>{render_inline(data.get('text', ''))}</h{level}>"
    if block_type == "list":
        ordered = data.get("style") == "ordered"
        return _render_list_items(data.get("items") or [], ordered)
    if block_type == "quote":
        text = render_inline(data.get("text", ""))
        caption = data.get("caption", "")
        html = f"<blockquote><p>{text}</p>"
        if caption:
            html += f"<footer>{render_inline(caption)}</footer>"
        return html + "</blockquote>"
    if block_type == "code":
        code = data.get("code", "")
        return f"<pre><code>{escape_html(code)}</code></pre>"
    if block_type == "delimiter":
        return "<hr>"
    if block_type == "image":
        return _render_image(data)
    if block_type == "table":
        return _render_table(data)
    if block_type == "embed":
        return _render_embed(data)
    if block_type == "warning":
        return _render_warning(data)
    return ""


def is_editorjs_content(content):
    """True when content parses as an Editor.js document with a blocks list."""
    try:
        doc = json.loads(content)
    except (TypeError, ValueError):
        return False
    return isinstance(doc, dict) and isinstance(doc.get("blocks"), list)


def render_blocks(doc):
    """Render a parsed Editor.js document to an HTML string."""
    blocks = doc.get("blocks") or []
    html = []
    for block in blocks:
        if isinstance(block, dict):
            html.append(_render_block(block))
    return "".join(html)


def render_editorjs(content):
    """Render Editor.js JSON content to HTML, escaping on parse failure."""
    if not is_editorjs_content(content):
        return f"<p>{escape_html(str(content))}</p>"
    return render_blocks(json.loads(content))


def render_story_content(content, content_format):
    """Render stored story content for display on public pages/previews."""
    if content_format == CONTENT_FORMAT_EDITORJS:
        return SafeString(render_editorjs(content))
    # Legacy Quill HTML is authored by admins and rendered as before.
    return SafeString(content or "")


def plain_text_excerpt(content, content_format, limit=150):
    """Extract a plain-text excerpt from stored content in either format."""
    if content_format == CONTENT_FORMAT_EDITORJS and is_editorjs_content(content):
        doc = json.loads(content)
        texts = []
        for block in doc.get("blocks") or []:
            if not isinstance(block, dict):
                continue
            data = block.get("data") or {}
            if block.get("type") == "paragraph":
                texts.append(_TAG_STRIP_RE.sub("", data.get("text", "")))
            elif block.get("type") == "header":
                texts.append(_TAG_STRIP_RE.sub("", data.get("text", "")))
        text = " ".join(t for t in texts if t).strip()
    else:
        text = _TAG_STRIP_RE.sub("", str(content or ""))

    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > limit:
        return text[:limit].rstrip() + "..."
    return text or "Untitled story"
