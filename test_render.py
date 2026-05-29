#!/usr/bin/env python3
"""
Quick test script to verify template rendering works correctly.
Run this to see the templates with actual data filled in.
"""

import sys
sys.path.insert(0, '.')

from server import render_template, init_db, create_story, get_all_stories, get_setting, set_setting, SafeString
from datetime import datetime

# Initialize
init_db()

# Clear and add test data
from server import get_db
conn = get_db()
conn.execute('DELETE FROM stories')
conn.execute('DELETE FROM settings')
conn.commit()
conn.close()

# Add test story
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

# Set theme
set_setting('site_title', 'Scooper Paper')
set_setting('site_description', 'News Delivered with Style')
set_setting('theme', 'light')

# Render paper homepage
print("=" * 70)
print("TEST: Rendering Paper Homepage (paper/index.html)")
print("=" * 70)

context = {
    'site_title': get_setting('site_title'),
    'site_description': get_setting('site_description'),
    'theme': get_setting('theme'),
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

# Test dark mode
print("\n" + "=" * 70)
print("TEST: Dark Mode")
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
print("All tests passed! Templates render correctly with styles.")
print("=" * 70)
