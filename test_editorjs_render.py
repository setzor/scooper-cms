#!/usr/bin/env python3
"""
Tests for the Editor.js block renderer.

Covers every block type the editor can produce, the inline markup
whitelist, URL scheme checks, and the plain-text excerpt extraction for
both content formats. Run with: python3 test_editorjs_render.py
"""

import json

from editorjs_render import (
    is_editorjs_content,
    plain_text_excerpt,
    render_editorjs,
    render_inline,
    render_story_content,
)
from template_engine import SafeString


def doc(blocks):
    return json.dumps({"time": 0, "blocks": blocks, "version": "2.30.7"})


def block(block_type, **data):
    return {"type": block_type, "data": data}


# ---------------------------------------------------------------------------
# Inline whitelist
# ---------------------------------------------------------------------------

def test_inline_keeps_allowed_tags():
    out = render_inline('Hello <b>bold</b> <i>it</i> <a href="https://example.com">link</a>')
    assert out == 'Hello <b>bold</b> <i>it</i> <a href="https://example.com" rel="noopener">link</a>', out


def test_inline_escapes_text():
    out = render_inline("a < b & c")
    assert out == "a &lt; b &amp; c", out


def test_inline_strips_script_and_event_handlers():
    out = render_inline('x <script>alert(1)</script> <img src=x onerror="alert(1)"> y')
    assert "<script" not in out and "onerror" not in out, out


def test_inline_drops_dangerous_href_schemes():
    out = render_inline('<a href="javascript:alert(1)">bad</a>')
    assert "javascript:" not in out, out
    assert out == "<a>bad</a>", out


def test_inline_allows_relative_and_https_hrefs():
    assert '<a href="/static/uploads/a.png"' in render_inline('<a href="/static/uploads/a.png">img</a>')
    assert 'rel="noopener"' in render_inline('<a href="https://s.co">x</a>')


def test_inline_scheme_check_is_case_insensitive():
    out = render_inline('<a href="HTTPS://EXAMPLE.COM/PATH">caps</a>')
    assert 'href="HTTPS://EXAMPLE.COM/PATH"' in out, out


# ---------------------------------------------------------------------------
# Blocks
# ---------------------------------------------------------------------------

def test_paragraph():
    out = render_editorjs(doc([block("paragraph", text="Plain <b>story</b>")]))
    assert out == "<p>Plain <b>story</b></p>", out


def test_header_clamps_level_into_outline():
    out = render_editorjs(
        doc([block("header", text="Big", level=1), block("header", text="Deep", level=9)])
    )
    assert "<h2>Big</h2>" in out and "<h6>Deep</h6>" in out, out


def test_list_ordered_and_nested():
    out = render_editorjs(
        doc(
            [
                block(
                    "list",
                    style="ordered",
                    items=[
                        {"content": "one", "items": [{"content": "nested"}]},
                        {"content": "two", "items": []},
                    ],
                )
            ]
        )
    )
    assert out == "<ol><li>one<ol><li>nested</li></ol></li><li>two</li></ol>", out


def test_list_unordered():
    out = render_editorjs(doc([block("list", style="unordered", items=[{"content": "a"}])]))
    assert out == "<ul><li>a</li></ul>", out


def test_quote_with_caption():
    out = render_editorjs(doc([block("quote", text="Words of wisdom", caption="Sage")]))
    assert out == "<blockquote><p>Words of wisdom</p><footer>Sage</footer></blockquote>", out


def test_code_block_escapes_html():
    out = render_editorjs(doc([block("code", code="<script>hi</script>")]))
    assert out == "<pre><code>&lt;script&gt;hi&lt;/script&gt;</code></pre>", out


def test_delimiter():
    assert render_editorjs(doc([block("delimiter")])) == "<hr>"


def test_image_with_caption():
    out = render_editorjs(
        doc([block("image", file={"url": "/static/uploads/a.png"}, caption="A cat")])
    )
    assert '<img src="/static/uploads/a.png" alt="A cat" loading="lazy">' in out, out
    assert "<figcaption>A cat</figcaption>" in out, out


def test_image_rejects_non_http_schemes():
    out = render_editorjs(doc([block("image", file={"url": "javascript:alert(1)"})]))
    assert out == "", out


def test_image_rejects_protocol_relative_url():
    out = render_editorjs(doc([block("image", file={"url": "//evil.com/a.png"})]))
    assert out == "", out


def test_table_with_headings():
    out = render_editorjs(
        doc(
            [
                block(
                    "table",
                    withHeadings=True,
                    content=[["h1", "h2"], ["a", "b"]],
                )
            ]
        )
    )
    assert "<thead><th>h1</th><th>h2</th></thead>" in out, out
    assert "<tbody><tr><td>a</td><td>b</td></tr></tbody>" in out, out


def test_embed_only_known_services():
    ok = render_editorjs(
        doc([block("embed", service="youtube", embed="https://www.youtube.com/embed/x", caption=None)])
    )
    assert 'src="https://www.youtube.com/embed/x"' in ok, ok
    assert render_editorjs(
        doc([block("embed", service="evil", embed="https://evil.com/x")])
    ) == ""


def test_warning_block():
    out = render_editorjs(doc([block("warning", title="Note", message="Warm words")]))
    assert '<aside class="story-warning"><strong>Note</strong><p>Warm words</p></aside>' == out, out


def test_unknown_block_is_skipped():
    out = render_editorjs(doc([block("mystery", magic=True)]))
    assert out == "", out


def test_malformed_json_falls_back_to_escaped_text():
    out = render_editorjs("not json at <all>")
    assert out == "<p>not json at &lt;all&gt;</p>", out


# ---------------------------------------------------------------------------
# Validation and excerpts
# ---------------------------------------------------------------------------

def test_is_editorjs_content():
    assert is_editorjs_content(doc([block("paragraph", text="hi")]))
    assert not is_editorjs_content("<p>html</p>")
    assert not is_editorjs_content("{broken")
    assert not is_editorjs_content(json.dumps({"no": "blocks"}))


def test_render_story_content_dispatch():
    html = render_story_content("<p>legacy</p>", "html")
    assert isinstance(html, SafeString) and html == "<p>legacy</p>"
    blocks = render_story_content(doc([block("paragraph", text="new")]), "editorjs")
    assert blocks == "<p>new</p>"
    assert isinstance(blocks, SafeString)


def test_plain_text_excerpt_editorjs():
    content = doc(
        [
            block("header", text="Heading <b>bold</b>"),
            block("paragraph", text="First words of the story. " + "x" * 200),
            block("code", code="ignored"),
        ]
    )
    text = plain_text_excerpt(content, "editorjs", limit=60)
    assert text.startswith("Heading bold First words"), text
    assert len(text) <= 64 and text.endswith("..."), text


def test_plain_text_excerpt_html():
    text = plain_text_excerpt("<p>Hello <b>world</b> again</p>", "html", limit=12)
    assert text == "Hello world...", text


def test_plain_text_excerpt_empty():
    assert plain_text_excerpt("", "html") == "Untitled story"


if __name__ == "__main__":
    tests = [(name, fn) for name, fn in sorted(globals().items()) if name.startswith("test_")]
    passed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"PASS {name}")
            passed += 1
        except AssertionError as e:
            print(f"FAIL {name}: {e}")
    print(f"\n{passed}/{len(tests)} passed")
    if passed != len(tests):
        raise SystemExit(1)
