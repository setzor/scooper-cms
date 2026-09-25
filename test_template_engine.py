#!/usr/bin/env python3
"""
Regression tests for the template engine parser.

Focuses on tag nesting, which was historically broken: {% if %} blocks
inside {% for %} loops were rendered unconditionally, and nested loops
inside conditionals were flattened. Run with: python3 test_template_engine.py
"""

from template_engine import TemplateEngine


def render(source, context=None):
    engine = TemplateEngine(templates_dir="templates")
    ast = engine._parse_template("inline", source)
    return "".join(node.render(context or {}, engine) for node in ast)


def test_if_inside_for():
    # The condition must be evaluated per item, not dropped
    out = render(
        "{% for item in items %}"
        "{% if item.show %}[on]{% else %}[off]{% endif %}"
        "{% endfor %}",
        {"items": [{"show": True}, {"show": False}]},
    )
    assert out == "[on][off]", f"got {out!r}"


def test_nested_if_inside_if():
    out = render(
        "{% if outer %}A{% if inner %}B{% endif %}C{% endif %}",
        {"outer": True, "inner": True},
    )
    assert out == "ABC", f"got {out!r}"
    out = render(
        "{% if outer %}A{% if inner %}B{% endif %}C{% endif %}",
        {"outer": True, "inner": False},
    )
    assert out == "AC", f"got {out!r}"


def test_for_inside_if():
    out = render(
        "{% if show %}{% for x in xs %}{{ x }}{% endfor %}{% endif %}",
        {"show": True, "xs": ["1", "2", "3"]},
    )
    assert out == "123", f"got {out!r}"
    out = render(
        "{% if show %}{% for x in xs %}{{ x }}{% endfor %}{% endif %}",
        {"show": False, "xs": ["1", "2", "3"]},
    )
    assert out == "", f"got {out!r}"


def test_elif_branches():
    out = render(
        "{% if n == 1 %}one{% elif n == 2 %}two{% elif n == 3 %}three{% else %}many{% endif %}",
        {"n": 2},
    )
    assert out == "two", f"got {out!r}"
    out = render(
        "{% if n == 1 %}one{% elif n == 2 %}two{% else %}many{% endif %}",
        {"n": 9},
    )
    assert out == "many", f"got {out!r}"


def test_else_branch():
    out = render("{% if ok %}yes{% else %}no{% endif %}", {"ok": False})
    assert out == "no", f"got {out!r}"


def test_not_operator():
    out = render("{% if not stories %}empty{% else %}full{% endif %}", {"stories": []})
    assert out == "empty", f"got {out!r}"
    out = render(
        "{% if not stories %}empty{% else %}full{% endif %}",
        {"stories": [{"id": 1}]},
    )
    assert out == "full", f"got {out!r}"


def test_for_else():
    out = render("{% for x in xs %}{{ x }}{% else %}none{% endfor %}", {"xs": []})
    assert out == "none", f"got {out!r}"
    out = render("{% for x in xs %}{{ x }}{% else %}none{% endfor %}", {"xs": ["a"]})
    assert out == "a", f"got {out!r}"


def test_nested_for():
    out = render(
        "{% for row in rows %}{% for cell in row %}{{ cell }},{% endfor %}{% endfor %}",
        {"rows": [["a", "b"], ["c"]]},
    )
    assert out == "a,b,c,", f"got {out!r}"


def test_comparison_inside_for():
    # e.g. pagination: {% if p == pagination.current_page %}
    out = render(
        "{% for p in pages %}"
        "{% if p == current %}({{ p }}){% else %}{{ p }}{% endif %}"
        "{% endfor %}",
        {"pages": [1, 2, 3], "current": 2},
    )
    assert out == "1(2)3", f"got {out!r}"


def test_dotted_iterable_in_for():
    # e.g. {% for p in pagination.pages %}
    out = render(
        "{% for p in pagination.pages %}{{ p }}{% endfor %}",
        {"pagination": {"pages": [1, 2, 3]}},
    )
    assert out == "123", f"got {out!r}"
    # A non-list dotted value renders the else body, not the loop body
    out = render(
        "{% for p in pagination.pages %}{{ p }}{% else %}none{% endfor %}",
        {"pagination": {"pages": []}},
    )
    assert out == "none", f"got {out!r}"


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failures = 0
    for test in tests:
        try:
            test()
            print(f"PASS {test.__name__}")
        except AssertionError as e:
            failures += 1
            print(f"FAIL {test.__name__}: {e}")
    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    return failures


if __name__ == "__main__":
    raise SystemExit(main())
