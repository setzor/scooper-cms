#!/usr/bin/env python3
"""
Migration script to convert SQLite database to markdown file storage.

This script will:
1. Read all stories from the SQLite database
2. Convert them to markdown files with frontmatter
3. Save them in the content/stories/ directory
4. Migrate settings to content/settings/settings.json

Usage:
    python3 scripts/migrate_to_markdown.py

Note: This is a one-time migration. The server will automatically use
file-based storage after this migration.
"""

import os
import sys
import sqlite3
from pathlib import Path
from datetime import datetime

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from md_storage import (
    FrontmatterParser,
    STORIES_DIR,
    SETTINGS_FILE,
    ensure_directories,
)


def main():
    print("Scooper CMS - SQLite to Markdown Migration")
    print("=" * 50)
    
    # Get database path
    db_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "db",
        "scooper.db"
    )
    
    print(f"\nLooking for SQLite database at: {db_path}")
    
    if not os.path.exists(db_path):
        print("ERROR: SQLite database not found!")
        print("This script requires an existing scooper.db file.")
        print("If you're starting fresh, you can just run the server - it will create")
        print("sample stories in markdown format automatically.")
        sys.exit(1)
    
    # Ensure directories exist
    ensure_directories()
    
    # Connect to SQLite database
    print(f"\nConnecting to SQLite database: {db_path}")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Migrate settings
    print("\nMigrating settings...")
    cursor.execute("SELECT key, value FROM settings")
    settings_rows = cursor.fetchall()
    settings = {}
    for row in settings_rows:
        settings[row['key']] = row['value']
    
    # Add defaults if missing
    if 'site_title' not in settings:
        settings['site_title'] = 'Scooper Paper'
    if 'site_description' not in settings:
        settings['site_description'] = 'Your News, Delivered'
    if 'theme' not in settings:
        settings['theme'] = 'light'
    if 'font_family' not in settings:
        settings['font_family'] = 'serif'
    
    # Save settings
    import json
    with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)
    
    print(f"  ✓ Migrated {len(settings)} settings to {SETTINGS_FILE}")
    
    # Migrate stories
    print("\nMigrating stories...")
    cursor.execute("SELECT * FROM stories ORDER BY id")
    stories = cursor.fetchall()
    
    migrated_count = 0
    skipped_count = 0
    
    for story in stories:
        # Build metadata
        metadata = {
            'title': story['title'],
            'slug': story['slug'],
        }
        
        # Add optional fields if they exist
        if story.get('excerpt'):
            metadata['excerpt'] = story['excerpt']
        if story.get('author'):
            metadata['author'] = story['author']
        if story.get('category'):
            metadata['category'] = story['category']
        if story.get('featured_image'):
            metadata['featured_image'] = story['featured_image']
        if story.get('published') is not None:
            metadata['published'] = bool(story['published'])
        if story.get('published_at'):
            metadata['published_at'] = story['published_at']
        if story.get('created_at'):
            metadata['created_at'] = story['created_at']
        if story.get('updated_at'):
            metadata['updated_at'] = story['updated_at']
        
        # Get content
        content = story['content']
        
        # Create markdown file
        filename = f"{story['slug']}.md"
        md_file = STORIES_DIR / filename
        
        # Check for duplicate slugs
        if md_file.exists():
            # Append a suffix to make it unique
            counter = 1
            while True:
                new_filename = f"{story['slug']}-{counter}.md"
                new_md_file = STORIES_DIR / new_filename
                if not new_md_file.exists():
                    md_file = new_md_file
                    metadata['slug'] = f"{story['slug']}-{counter}"
                    break
                counter += 1
        
        # Create the markdown content
        md_content = FrontmatterParser.create(metadata, content)
        
        # Write the file
        md_file.write_text(md_content, encoding='utf-8')
        migrated_count += 1
        print(f"  ✓ Migrated story: {story['title']} ({story['id']})")
    
    conn.close()
    
    print(f"\n✅ Migration complete!")
    print(f"   - Settings: {len(settings)} migrated")
    print(f"   - Stories: {migrated_count} migrated")
    print(f"\nYour data is now stored in:")
    print(f"   - Settings: {SETTINGS_FILE}")
    print(f"   - Stories: {STORIES_DIR}/")
    print(f"\nYou can now run the server with:")
    print(f"   SCOOPER_ADMIN_USER=your_user SCOOPER_ADMIN_PASS=your_pass python3 server.py")
    print(f"\nNote: The old SQLite database at {db_path} is still intact.")
    print(f"      You can delete it if the migration was successful.")


if __name__ == "__main__":
    main()
