#!/usr/bin/env python3
"""
Tests for Markdown interchange (import + export).

Covers front matter parsing (Grav/Obsidian style), Markdown -> Editor.js
blocks, blocks -> Markdown, legacy HTML -> Markdown, the never-lose-content
fallback, and full round trips. Run with: python3 test_markdown_interchange.py
"""

import json

from markdown_interchange import (
    blocks_to_markdown,
    extract_leading_heading,
    html_to_markdown,
    markdown_to_blocks,
    markdown_to_editorjs,
    meta_to_story_fields,
    parse_date,
    parse_front_matter,
    story_to_markdown,
)


def block(kind, **data):
    return {"type": kind, "data": data}


# ---------------------------------------------------------------------------
# Front matter
# ---------------------------------------------------------------------------

def test_front_matter_grav():
    text = (
        "---\n"
        "title: My Page\n"
        "taxonomy:\n"
        "    category: blog\n"
        "published: false\n"
        "date: 2024-01-15 10:30\n"
        "---\n\nBody here"
    )
    meta, body = parse_front_matter(text)
    assert meta["title"] == "My Page", meta
    assert meta["taxonomy"]["category"] == "blog", meta
    assert meta["published"] is False
    assert body == "Body here", body


def test_front_matter_plain_and_quoted():
    meta, body = parse_front_matter('---\ntitle: "Quoted"\nauthor: Jane\nexcerpt: plain\n---\nX')
    assert meta["title"] == "Quoted" and meta["author"] == "Jane"
    assert body == "X"


def test_no_front_matter():
    meta, body = parse_front_matter("# Just a note\n\nBody")
    assert meta == {}
    assert body.startswith("# Just a note")


def test_unterminated_front_matter_is_body():
    meta, body = parse_front_matter("---\ntitle: broken\nno end marker\n")
    assert meta == {}
    assert "title: broken" in body


def test_meta_to_story_fields():
    fields = meta_to_story_fields(
        {"title": "T", "taxonomy": {"category": "blog"}, "published": False}, "fb"
    )
    assert fields["title"] == "T" and fields["category"] == "blog"
    assert fields["published"] is False
    fields = meta_to_story_fields({"slug": "custom"}, "Fallback")
    assert fields["title"] == "Fallback" and fields["slug"] == "custom"
    assert fields["published"] is None  # unspecified: caller decides


def test_parse_date_formats():
    assert parse_date("2024-01-15 10:30") == "2024-01-15T10:30:00"
    assert parse_date("2024-01-15") == "2024-01-15T00:00:00"
    assert parse_date("15-01-2024 10:30") is not None
    assert parse_date("nonsense") is None
    assert parse_date(None) is None


def test_extract_leading_heading():
    title, rest = extract_leading_heading("# Note Title\n\nBody **here**")
    assert title == "Note Title"
    assert rest == "Body **here**"
    title, rest = extract_leading_heading("### Deep Heading\nbody follows")
    assert title == "Deep Heading" and rest == "body follows"
    # No leading heading: nothing consumed
    title, rest = extract_leading_heading("Just a paragraph\n\n# later heading")
    assert title is None and rest.startswith("Just a paragraph")
    # Blank lines before the heading are fine
    title, rest = extract_leading_heading("\n\n# After blanks\nbody")
    assert title == "After blanks"


# ---------------------------------------------------------------------------
# Import: Markdown -> blocks
# ---------------------------------------------------------------------------

def test_import_headers_and_paragraph():
    blocks = markdown_to_blocks("# Title\n\nSome **bold** text")
    assert blocks[0] == block("header", text="Title", level=1)
    assert blocks[1] == block("paragraph", text="Some <b>bold</b> text")


def test_import_inline_marks():
    text = "a *it* **bd** `cd` [lk](https://x.co) ==mk== _ul_"
    out = markdown_to_blocks(text)[0]["data"]["text"]
    assert "<i>it</i>" in out and "<b>bd</b>" in out and "<code>cd</code>" in out
    assert '<a href="https://x.co">lk</a>' in out
    assert "<mark>mk</mark>" in out and "<i>ul</i>" in out


def test_import_escapes_html_in_markdown():
    out = markdown_to_blocks("Text with <script>alert(1)</script> & amp")[0]["data"]["text"]
    assert "<script" not in out and "&lt;script&gt;" in out and "&amp;" in out


def test_import_lists_nested():
    blocks = markdown_to_blocks("- one\n- two\n    - nested\n- three")
    items = blocks[0]["data"]["items"]
    assert blocks[0]["type"] == "list"
    assert items[0]["content"] == "one"
    assert items[1]["items"][0]["content"] == "nested"


def test_import_ordered_list():
    blocks = markdown_to_blocks("1. a\n2. b")
    assert blocks[0]["data"]["style"] == "ordered"
    assert len(blocks[0]["data"]["items"]) == 2


def test_import_quote_with_caption():
    blocks = markdown_to_blocks("> Words of wisdom\n> -- The Sage")
    assert blocks[0] == block("quote", text="Words of wisdom", caption="The Sage")


def test_import_code_fence():
    blocks = markdown_to_blocks("```\nprint('hi')\n<a>not html</a>\n```")
    assert blocks[0] == block("code", code="print('hi')\n<a>not html</a>")


def test_import_delimiter_and_image():
    blocks = markdown_to_blocks("---\n\n![A cat](cat.jpg)\n")
    assert blocks[0] == block("delimiter")
    assert blocks[1] == block("image", file={"url": "cat.jpg"}, caption="A cat")


def test_import_gfm_table():
    blocks = markdown_to_blocks("| a | b |\n|---|---|\n| 1 | 2 |")
    data = blocks[0]["data"]
    assert blocks[0]["type"] == "table"
    assert data["withHeadings"] is True
    assert data["content"] == [["a", "b"], ["1", "2"]]


def test_import_never_loses_content():
    doc = json.loads(markdown_to_editorjs("", fallback_paragraph="raw **text**"))
    blocks = doc["blocks"]
    assert len(blocks) == 1
    assert blocks[0]["type"] == "paragraph"
    assert "raw **text**" in blocks[0]["data"]["text"]


def test_import_paragraph_lines_join():
    blocks = markdown_to_blocks("line one\nline two continues\n\nnew para")
    assert len(blocks) == 2
    assert blocks[0]["data"]["text"] == "line one line two continues"


# ---------------------------------------------------------------------------
# Export: blocks -> Markdown
# ---------------------------------------------------------------------------

def test_export_blocks_basic():
    doc = json.dumps({"blocks": [
        block("header", text="Head", level=2),
        block("paragraph", text="Some <b>bold</b> and <i>it</i> and <code>x</code> and <a href=\"https://e.co\">lnk</a>"),
    ]})
    out = blocks_to_markdown(doc)
    assert "## Head" in out
    assert "**bold**" in out and "*it*" in out and "`x`" in out
    assert "[lnk](https://e.co)" in out


def test_export_list_nested():
    doc = json.dumps({"blocks": [block("list", style="ordered", items=[
        {"content": "first", "items": []},
        {"content": "second", "items": [{"content": "nested", "items": []}]},
    ])]})
    out = blocks_to_markdown(doc)
    assert "1. first" in out and "2. second" in out
    assert "    1. nested" in out


def test_export_quote_and_code():
    doc = json.dumps({"blocks": [
        block("quote", text="Wisdom", caption="Sage"),
        block("code", code="x = 1"),
    ]})
    out = blocks_to_markdown(doc)
    assert "> Wisdom" in out and "> -- Sage" in out
    assert "```\nx = 1\n```" in out


def test_export_table():
    doc = json.dumps({"blocks": [block("table", withHeadings=True, content=[["h1", "h2"], ["a", "b"]])]})
    out = blocks_to_markdown(doc)
    assert "| h1 | h2 |" in out and "| --- | --- |" in out and "| a | b |" in out


def test_export_image_delimiter_embed_warning():
    doc = json.dumps({"blocks": [
        block("image", file={"url": "/static/uploads/x.png"}, caption="pic"),
        block("delimiter"),
        block("embed", service="youtube", source="https://youtu.be/x", caption="vid"),
        block("warning", title="Note", message="Stay cozy"),
    ]})
    out = blocks_to_markdown(doc)
    assert "![pic](/static/uploads/x.png)" in out
    assert "\n---\n" in out
    assert "[vid](https://youtu.be/x)" in out
    assert "> **Note**" in out and "> Stay cozy" in out


def test_export_garbage_is_safe():
    assert blocks_to_markdown("not json") == "not json"
    assert blocks_to_markdown("{broken") == "{broken"
    assert blocks_to_markdown({"blocks": "nope"}) == ""
    assert blocks_to_markdown({"blocks": [block("mystery", x=1)]}) == ""


# ---------------------------------------------------------------------------
# Export: legacy HTML -> Markdown
# ---------------------------------------------------------------------------

def test_html_to_markdown_common_tags():
    html = (
        "<h2>Head</h2>"
        "<p>Some <strong>bold</strong> <em>text</em> <a href='https://x.co'>link</a></p>"
        "<ul><li>one</li><li>two</li></ul>"
        "<blockquote><p>wise words</p></blockquote>"
        "<pre><code>x = 1</code></pre>"
        "<hr>"
        "<p>end</p>"
    )
    md = html_to_markdown(html)
    assert "## Head" in md
    assert "**bold** *text* [link](https://x.co)" in md
    assert "- one" in md and "- two" in md
    assert "> wise words" in md
    assert "```\nx = 1\n```" in md
    assert "---" in md and md.rstrip().endswith("end")


def test_html_to_markdown_table():
    md = html_to_markdown("<table><tr><th>H</th><th>H2</th></tr><tr><td>1</td><td>2</td></tr></table>")
    assert "| H | H2 |" in md and "| --- | --- |" in md and "| 1 | 2 |" in md


def test_html_to_markdown_fallback_on_error():
    # Malformed input must not crash and must preserve text
    md = html_to_markdown("<p>keep <b>this</b></p>")
    assert "keep **this**" in md


# ---------------------------------------------------------------------------
# Story export shape (front matter + body)
# ---------------------------------------------------------------------------

def test_story_to_markdown_round_trip():
    doc = markdown_to_editorjs("# Round Trip\n\nSome **text** with [link](https://e.co).")
    story = {
        "id": 1,
        "title": "Round Trip",
        "slug": "round-trip",
        "author": "Scoop",
        "category": "General",
        "published": True,
        "published_at": "2026-09-25T10:00:00",
        "excerpt": "",
        "content": doc,
        "content_format": "editorjs",
    }
    md = story_to_markdown(story)
    assert md.startswith("---\n")
    assert "title: Round Trip" in md
    assert "slug: round-trip" in md
    assert "published: true" in md
    assert "date: 2026-09-25 10:00" in md

    # And it imports back to the same story fields
    meta, body = parse_front_matter(md)
    fields = meta_to_story_fields(meta, "x")
    assert fields["title"] == "Round Trip"
    assert fields["slug"] == "round-trip"
    assert fields["published"] is True
    assert "Some **text** with [link](https://e.co)" in body


def test_story_to_markdown_legacy_html():
    story = {
        "title": "Legacy",
        "slug": "legacy",
        "author": "A",
        "category": "C",
        "published": False,
        "content": "<p>hello <strong>world</strong></p>",
        "content_format": "html",
        "excerpt": "",
    }
    md = story_to_markdown(story)
    assert "published: false" in md
    assert "hello **world**" in md


# ---------------------------------------------------------------------------
# Full round trip: markdown -> blocks -> markdown
# ---------------------------------------------------------------------------

def test_full_round_trip():
    src = (
        "# Heading One\n\n"
        "A paragraph with **bold**, *italic* and [a link](https://example.com).\n\n"
        "- one\n- two\n\n"
        "> Quote text\n>\n> -- Captor\n\n"
        "```\ncode line\n```\n\n"
        "![alt text](/static/uploads/img.png)\n\n"
        "---\n\n"
        "Tail paragraph."
    )
    doc = markdown_to_editorjs(src)
    back = blocks_to_markdown(doc)
    assert "# Heading One" in back
    assert "**bold**" in back and "*italic*" in back and "[a link](https://example.com)" in back
    assert "- one" in back and "- two" in back
    assert "> Quote text" in back and "> -- Captor" in back
    assert "code line" in back
    assert "![alt text](/static/uploads/img.png)" in back
    assert "Tail paragraph." in back


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
