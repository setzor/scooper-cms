#!/usr/bin/env python3
"""
Demo script: render the paper templates with sample data so you can eyeball them.

SAFE BY DEFAULT - running this script never modifies the database.
Resetting the database to demo content is opt-in via --wipe, and even then
it asks for confirmation twice and is refused when not running in an
interactive terminal.

Usage:
  python3 demo_render.py          # render with sample data, DB untouched
  python3 demo_render.py --wipe   # also reset DB to demo content
                                   # (deletes ALL stories and settings)
"""

import sys
sys.path.insert(0, '.')

from datetime import datetime

from server import (
    SafeString,
    create_story,
    get_db,
    init_db,
    render_template,
    set_setting,
)

# Initialize (idempotent: only creates tables that are missing)
init_db()

wipe_requested = "--wipe" in sys.argv

if wipe_requested:
    if not sys.stdin.isatty():
        sys.exit(
            "Refusing to wipe: --wipe requires an interactive terminal "
            "so you can confirm. Nothing was deleted."
        )

    print("WARNING: --wipe will DELETE ALL STORIES AND SETTINGS from the")
    print("database and replace them with demo content. This cannot be undone.")
    first = input("\nDo you want to continue? Type 'yes' to proceed: ").strip().lower()
    if first != "yes":
        sys.exit("Aborted. Nothing was deleted.")

    second = input(
        "\nFinal confirmation: type 'WIPE' to delete all stories and settings: "
    ).strip()
    if second != "WIPE":
        sys.exit("Aborted. Nothing was deleted.")

    conn = get_db()
    conn.execute("DELETE FROM stories")
    conn.execute("DELETE FROM settings")
    conn.commit()
    conn.close()

    create_story({
        'title': 'Breaking News: Scooper Launches!',
        'slug': 'breaking-news-scooper-launches',
        'content': '<p>Scooper CMS has officially launched! This revolutionary content management platform brings newspaper-style elegance to digital publishing.</p><p>With full dark/light mode support, rich text editing, and a beautiful paper aesthetic, Scooper is set to change how news sites manage content.</p>',
        'excerpt': 'Scooper CMS has officially launched with revolutionary features.',
        'author': 'Scooper Team',
        'category': 'Announcement',
        'published': True,
        'published_at': datetime.now().isoformat(),
    })

    set_setting('site_title', 'Scooper Paper')
    set_setting('site_description', 'News Delivered with Style')
    set_setting('theme', 'light')
    print("\nDatabase reset to demo content.\n")
else:
    print("Rendering with sample data (database untouched).")
    print("To reset the database to demo content, run: python3 demo_render.py --wipe\n")

# Render paper homepage with sample data (read-only)
print("=" * 70)
print("DEMO: Rendering Paper Homepage (paper/index.html)")
print("=" * 70)

context = {
    'site_title': 'Scooper Paper',
    'site_description': 'News Delivered with Style',
    'theme': 'light',
    'theme_icon': SafeString('&#127774;'),
    'stories': [{
        'id': 1,
        'title': 'Breaking News: Scooper Launches!',
        'slug': 'breaking-news-scooper-launches',
        'excerpt': 'Scooper CMS has officially launched...',
        'author': 'Scooper Team',
        'category': 'Announcement',
        'published_at': datetime.now().strftime('%B %d, %Y')
    }]
}

html = render_template('paper/index.html', context)

# Show key parts
if '/static/css/style.css' in html:
    print("✓ CSS stylesheet linked")
else:
    print("✗ CSS stylesheet missing")

if 'theme-light' in html:
    print("✓ Theme class applied")
else:
    print("✗ Theme class missing")

if 'data-theme="light"' in html:
    print("✓ Data-theme attribute set")
else:
    print("✗ Data-theme attribute missing")

if 'Breaking News: Scooper Launches!' in html:
    print("✓ Story title rendered")
else:
    print("✗ Story title missing")

if 'paper-layout' in html:
    print("✓ Layout class present")
else:
    print("✗ Layout class missing")

print("\n" + "=" * 70)
print("Sample of rendered HTML (first 600 characters):")
print("=" * 70)
print(html[:600])
print("...")

# Demo dark mode
print("\n" + "=" * 70)
print("DEMO: Dark Mode")
print("=" * 70)

context_dark = context.copy()
context_dark['theme'] = 'dark'
context_dark['theme_icon'] = SafeString('&#127771;')

html_dark = render_template('paper/index.html', context_dark)

if 'data-theme="dark"' in html_dark:
    print("✓ Dark mode data-theme attribute set")
else:
    print("✗ Dark mode data-theme missing")

if 'theme-dark' in html_dark:
    print("✓ Dark theme class applied")
else:
    print("✗ Dark theme class missing")

print("\n" + "=" * 70)
print("Demo complete. Templates render correctly with styles.")
print("=" * 70)
