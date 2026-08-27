#!/usr/bin/env python3
"""
Markdown File Storage Backend for Scooper CMS
A file-based storage system that uses markdown files with frontmatter for stories
and JSON files for settings.

This replaces the SQLite database with a file-based approach:
- Stories are stored as individual .md files with YAML frontmatter
- Settings are stored in a JSON file
- Categories are derived from story metadata

Dependencies:
- frontmatter (for parsing YAML frontmatter)
- markdown (optional, for rendering markdown to HTML)
"""

import html
import json
import os
import re
import secrets
import sys
from datetime import datetime
from pathlib import Path

# Required dependency
try:
    import frontmatter
    HAS_FRONTMATTER = True
except ImportError:
    print("ERROR: 'frontmatter' package is required. Install it with:")
    print("  pip install python-frontmatter")
    sys.exit(1)

# Optional dependency for markdown rendering
try:
    import markdown
    HAS_MARKDOWN = True
except ImportError:
    HAS_MARKDOWN = False


# ============================================================================
# CONFIGURATION
# ============================================================================

CONTENT_DIR = Path(__file__).parent / "content"
STORIES_DIR = CONTENT_DIR / "stories"
SETTINGS_DIR = CONTENT_DIR / "settings"
SETTINGS_FILE = SETTINGS_DIR / "settings.json"

# Default categories
DEFAULT_CATEGORIES = ['General', 'Local News', 'Technology', 'Business', 'Sports', 'Entertainment', 'Announcement']

# Ensure directories exist
def ensure_directories():
    """Ensure all required directories exist."""
    CONTENT_DIR.mkdir(exist_ok=True)
    STORIES_DIR.mkdir(exist_ok=True)
    SETTINGS_DIR.mkdir(exist_ok=True)


# ============================================================================
# SETTINGS MANAGEMENT
# ============================================================================

def init_settings():
    """Initialize default settings if they don't exist."""
    ensure_directories()
    if not SETTINGS_FILE.exists():
        default_settings = {
            'site_title': 'Scooper Paper',
            'site_description': 'Your News, Delivered',
            'theme': 'light',
            'font_family': 'serif'
        }
        save_settings(default_settings)


def get_settings():
    """Get all settings as a dictionary."""
    ensure_directories()
    if not SETTINGS_FILE.exists():
        init_settings()
    try:
        with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def get_setting(key, default=None):
    """Get a single setting value."""
    settings = get_settings()
    return settings.get(key, default)


def set_setting(key, value):
    """Set a single setting value."""
    ensure_directories()
    settings = get_settings()
    settings[key] = value
    save_settings(settings)


def save_settings(settings):
    """Save all settings to the settings file."""
    ensure_directories()
    with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)


# ============================================================================
# STORY MANAGEMENT
# ============================================================================

def slugify(text):
    """Simple slugify function."""
    if not text:
        return ""
    slug = text.lower()
    slug = re.sub(r"[^\w\s-]", "", slug)  # Remove special chars
    slug = re.sub(r"[\s_]+", "-", slug)  # Replace spaces with -
    slug = re.sub(r"-+", "-", slug)  # Remove duplicate -
    slug = slug.strip("-")
    return slug


def generate_unique_slug(title, existing_slugs=None):
    """Generate a unique slug for a story."""
    if existing_slugs is None:
        existing_slugs = get_all_story_slugs()
    
    slug = slugify(title)
    if not slug:
        slug = "untitled"
    
    base_slug = slug
    counter = 1
    while slug in existing_slugs:
        slug = f"{base_slug}-{secrets.token_hex(2)}"
        counter += 1
    
    return slug


def get_all_story_slugs():
    """Get all existing story slugs."""
    ensure_directories()
    slugs = []
    for md_file in STORIES_DIR.glob("*.md"):
        try:
            post = frontmatter.load(md_file)
            if post.get('slug'):
                slugs.append(post['slug'])
        except Exception:
            continue
    return slugs


def get_all_stories(
    published_only=False,
    search=None,
    category=None,
    status=None,
    month=None,
    page=1,
    per_page=10,
):
    """Get all stories with optional filtering and pagination.
    
    Returns:
        tuple: (stories, total_count) - list of story dicts and total count
    """
    ensure_directories()
    all_stories = []
    
    for md_file in STORIES_DIR.glob("*.md"):
        try:
            post = frontmatter.load(md_file)
            
            # Build story dict
            story = {
                'id': md_file.stem,  # Use filename as ID
                'title': post.get('title', 'Untitled'),
                'slug': post.get('slug', md_file.stem),
                'content': post.content,
                'excerpt': post.get('excerpt', ''),
                'author': post.get('author', 'Admin'),
                'category': post.get('category', 'General'),
                'featured_image': post.get('featured_image', ''),
                'published': post.get('published', False),
                'published_at': post.get('published_at', ''),
                'created_at': post.get('created_at', md_file.stat().st_ctime),
                'updated_at': post.get('updated_at', md_file.stat().st_mtime),
                'file_path': str(md_file),
            }
            all_stories.append(story)
        except Exception:
            continue
    
    # Apply filters
    filtered_stories = []
    for story in all_stories:
        # Published only filter
        if published_only and not story.get('published', False):
            continue
        
        # Search filter
        if search:
            search_lower = search.lower()
            title_match = search_lower in story.get('title', '').lower()
            content_match = search_lower in story.get('content', '').lower()
            excerpt_match = search_lower in story.get('excerpt', '').lower()
            if not (title_match or content_match or excerpt_match):
                continue
        
        # Category filter
        if category and story.get('category') != category:
            continue
        
        # Status filter
        if status == 'published' and not story.get('published', False):
            continue
        if status == 'draft' and story.get('published', False):
            continue
        
        # Month filter
        if month:
            published_at = story.get('published_at', '')
            created_at = story.get('created_at', '')
            pub_month = published_at[:7] if isinstance(published_at, str) and len(published_at) >= 7 else ''
            create_month = created_at[:7] if isinstance(created_at, str) and len(created_at) >= 7 else ''
            if pub_month != month and create_month != month:
                continue
        
        filtered_stories.append(story)
    
    # Sort by published_at DESC, then created_at DESC
    filtered_stories.sort(key=lambda s: (
        s.get('published_at', '') or '',
        s.get('created_at', '') or ''
    ), reverse=True)
    
    total_count = len(filtered_stories)
    
    # Apply pagination
    offset = (page - 1) * per_page
    paginated_stories = filtered_stories[offset:offset + per_page]
    
    # Convert timestamps to ISO format strings if they're datetime objects
    for story in paginated_stories:
        for key in ['published_at', 'created_at', 'updated_at']:
            value = story.get(key)
            if isinstance(value, (int, float)):
                story[key] = datetime.fromtimestamp(value).isoformat()
            elif hasattr(value, 'isoformat'):
                story[key] = value.isoformat()
    
    return paginated_stories, total_count


def get_story_by_id(story_id):
    """Get a single story by ID (filename)."""
    ensure_directories()
    md_file = STORIES_DIR / f"{story_id}.md"
    if not md_file.exists():
        return None
    
    try:
        post = frontmatter.load(md_file)
        
        story = {
            'id': story_id,
            'title': post.get('title', 'Untitled'),
            'slug': post.get('slug', story_id),
            'content': post.content,
            'excerpt': post.get('excerpt', ''),
            'author': post.get('author', 'Admin'),
            'category': post.get('category', 'General'),
            'featured_image': post.get('featured_image', ''),
            'published': post.get('published', False),
            'published_at': post.get('published_at', ''),
            'created_at': post.get('created_at', md_file.stat().st_ctime),
            'updated_at': post.get('updated_at', md_file.stat().st_mtime),
            'file_path': str(md_file),
        }
        
        # Convert timestamps
        for key in ['published_at', 'created_at', 'updated_at']:
            value = story.get(key)
            if isinstance(value, (int, float)):
                story[key] = datetime.fromtimestamp(value).isoformat()
            elif hasattr(value, 'isoformat'):
                story[key] = value.isoformat()
        
        return story
    except Exception:
        return None


def get_story_by_slug(slug):
    """Get a single story by slug."""
    ensure_directories()
    for md_file in STORIES_DIR.glob("*.md"):
        try:
            post = frontmatter.load(md_file)
            if post.get('slug') == slug:
                story = {
                    'id': md_file.stem,
                    'title': post.get('title', 'Untitled'),
                    'slug': slug,
                    'content': post.content,
                    'excerpt': post.get('excerpt', ''),
                    'author': post.get('author', 'Admin'),
                    'category': post.get('category', 'General'),
                    'featured_image': post.get('featured_image', ''),
                    'published': post.get('published', False),
                    'published_at': post.get('published_at', ''),
                    'created_at': post.get('created_at', md_file.stat().st_ctime),
                    'updated_at': post.get('updated_at', md_file.stat().st_mtime),
                    'file_path': str(md_file),
                }
                
                # Convert timestamps
                for key in ['published_at', 'created_at', 'updated_at']:
                    value = story.get(key)
                    if isinstance(value, (int, float)):
                        story[key] = datetime.fromtimestamp(value).isoformat()
                    elif hasattr(value, 'isoformat'):
                        story[key] = value.isoformat()
                
                return story
        except Exception:
            continue
    return None


def create_story(data):
    """Create a new story as a markdown file."""
    ensure_directories()
    
    # Generate slug if not provided
    slug = data.get('slug')
    if not slug:
        slug = generate_unique_slug(data.get('title', 'Untitled'))
    else:
        # Ensure slug is unique
        existing_slugs = get_all_story_slugs()
        if slug in existing_slugs:
            slug = generate_unique_slug(data.get('title', 'Untitled'), existing_slugs)
    
    # Use slug as filename
    filename = f"{slug}.md"
    md_file = STORIES_DIR / filename
    
    # Prepare metadata
    metadata = {
        'title': data.get('title', 'Untitled'),
        'slug': slug,
    }
    
    # Add optional fields if they exist
    if data.get('excerpt'):
        metadata['excerpt'] = data['excerpt']
    if data.get('author'):
        metadata['author'] = data['author']
    if data.get('category'):
        metadata['category'] = data['category']
    if data.get('featured_image'):
        metadata['featured_image'] = data['featured_image']
    if data.get('published') is not None:
        metadata['published'] = data['published']
    if data.get('published_at'):
        metadata['published_at'] = data['published_at']
    if data.get('created_at'):
        metadata['created_at'] = data['created_at']
    if data.get('updated_at'):
        metadata['updated_at'] = data['updated_at']
    
    # Get content
    content = data.get('content', '')
    
    # Create the markdown file
    post = frontmatter.Post(content, **metadata)
    with open(md_file, 'w', encoding='utf-8') as f:
        frontmatter.dump(post, f)
    
    return md_file.stem  # Return the ID (filename without extension)


def update_story(story_id, data):
    """Update an existing story."""
    ensure_directories()
    md_file = STORIES_DIR / f"{story_id}.md"
    
    if not md_file.exists():
        return False
    
    try:
        # Load existing post
        post = frontmatter.load(md_file)
        
        # Update metadata
        if 'title' in data:
            post['title'] = data['title']
        if 'slug' in data:
            post['slug'] = data['slug']
        if 'excerpt' in data:
            post['excerpt'] = data['excerpt']
        if 'author' in data:
            post['author'] = data['author']
        if 'category' in data:
            post['category'] = data['category']
        if 'featured_image' in data:
            post['featured_image'] = data['featured_image']
        if 'published' in data:
            post['published'] = data['published']
        if 'published_at' in data:
            post['published_at'] = data['published_at']
        post['updated_at'] = datetime.now().isoformat()
        
        # Update content
        if 'content' in data:
            post.content = data['content']
        
        # Write updated file
        with open(md_file, 'w', encoding='utf-8') as f:
            frontmatter.dump(post, f)
        
        return True
    except Exception:
        return False


def delete_story(story_id):
    """Delete a story file."""
    ensure_directories()
    md_file = STORIES_DIR / f"{story_id}.md"
    
    if md_file.exists():
        md_file.unlink()
        return True
    return False


# ============================================================================
# CATEGORY MANAGEMENT
# ============================================================================

def get_all_categories():
    """Get all unique categories from stories."""
    ensure_directories()
    categories = set()
    
    # Always include default categories
    for cat in DEFAULT_CATEGORIES:
        categories.add(cat)
    
    # Get categories from existing stories
    for md_file in STORIES_DIR.glob("*.md"):
        try:
            post = frontmatter.load(md_file)
            category = post.get('category', 'General')
            categories.add(category)
        except Exception:
            continue
    
    # Return as list of dicts
    return [{'id': i + 1, 'name': cat} for i, cat in enumerate(sorted(categories))]


def get_valid_category(name):
    """Get a valid category name. Always returns the provided name."""
    if not name:
        return "General"
    return name


def get_category_by_id(category_id):
    """Get a category by ID."""
    categories = get_all_categories()
    for cat in categories:
        if cat['id'] == category_id:
            return cat
    return None


def get_category_by_name(name):
    """Get a category by name."""
    categories = get_all_categories()
    for cat in categories:
        if cat['name'] == name:
            return cat
    return None


# ============================================================================
# MARKDOWN RENDERING
# ============================================================================

def render_markdown_to_html(markdown_content):
    """Render markdown content to HTML.
    
    If markdown library is not available, returns the content as-is
    (assuming it might already be HTML).
    """
    if not markdown_content:
        return ""
    
    # If it looks like HTML already, return as-is
    if markdown_content.strip().startswith('<') and markdown_content.strip().endswith('>'):
        return markdown_content
    
    if HAS_MARKDOWN:
        try:
            html_content = markdown.markdown(markdown_content)
            return html_content
        except Exception:
            # Fallback: escape and return as plain text
            return html.escape(markdown_content)
    else:
        # No markdown library - return as-is (might be HTML already)
        return markdown_content


def render_story_content(story):
    """Render a story's content to HTML.
    
    This handles both markdown and HTML content.
    """
    content = story.get('content', '')
    
    # Check if content looks like HTML
    if content.strip().startswith('<') and '<' in content and '>' in content:
        return content
    
    # Otherwise, try to render as markdown
    return render_markdown_to_html(content)


# ============================================================================
# MIGRATION UTILITIES
# ============================================================================

def migrate_from_sqlite(sqlite_db_path):
    """Migrate stories and settings from SQLite to markdown files.
    
    This is a one-time migration utility.
    """
    import sqlite3
    
    ensure_directories()
    
    # Connect to SQLite database
    conn = sqlite3.connect(sqlite_db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Migrate settings
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
    
    save_settings(settings)
    print(f"Migrated {len(settings)} settings")
    
    # Migrate stories
    cursor.execute("SELECT * FROM stories")
    stories = cursor.fetchall()
    
    for story in stories:
        metadata = {
            'title': story['title'],
            'slug': story['slug'],
        }
        
        # Add optional fields
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
        
        content = story['content']
        
        # Create markdown file
        filename = f"{story['slug']}.md"
        md_file = STORIES_DIR / filename
        
        # Check for duplicate slugs
        if md_file.exists():
            filename = f"{story['slug']}-{secrets.token_hex(2)}.md"
            md_file = STORIES_DIR / filename
            metadata['slug'] = story['slug'] + '-' + secrets.token_hex(2)
        
        post = frontmatter.Post(content, **metadata)
        with open(md_file, 'w', encoding='utf-8') as f:
            frontmatter.dump(post, f)
    
    conn.close()
    print(f"Migrated {len(stories)} stories")
    
    return True


# ============================================================================
# INITIALIZATION
# ============================================================================

def init_storage():
    """Initialize the file-based storage."""
    ensure_directories()
    init_settings()


# Initialize on import
init_storage()
