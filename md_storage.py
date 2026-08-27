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
- markdown (for rendering markdown to HTML)
- python-frontmatter or ruamel.yaml (for parsing frontmatter)
"""

import html
import json
import os
import re
import secrets
from datetime import datetime
from pathlib import Path

# Try to import markdown and frontmatter libraries
try:
    import markdown
    HAS_MARKDOWN = True
except ImportError:
    HAS_MARKDOWN = False

try:
    import frontmatter
    HAS_FRONTMATTER = True
except ImportError:
    try:
        import ruamel.yaml
        HAS_YAML = True
        HAS_FRONTMATTER = False
    except ImportError:
        HAS_FRONTMATTER = False
        HAS_YAML = False

# Fallback: simple frontmatter parser if libraries not available
class SimpleFrontmatter:
    """Simple frontmatter parser that doesn't require external dependencies."""
    
    @staticmethod
    def parse(content):
        """Parse markdown content with frontmatter into metadata and content."""
        if not content or not content.strip():
            return {'content': content, 'metadata': {}}
        
        lines = content.split('\n')
        
        # Check for frontmatter delimiter
        if lines[0].strip() != '---':
            return {'content': content, 'metadata': {}}
        
        # Find the closing delimiter
        metadata_lines = []
        content_start = None
        for i, line in enumerate(lines[1:], 1):
            if line.strip() == '---':
                content_start = i + 1
                break
            metadata_lines.append(line)
        
        if content_start is None:
            return {'content': content, 'metadata': {}}
        
        # Parse metadata (simple YAML-like parsing)
        metadata = {}
        current_key = None
        for line in metadata_lines:
            line = line.strip()
            if not line:
                continue
            # Check for key: value pattern
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                
                # Handle quoted strings
                if (value.startswith('"') and value.endswith('"')) or \
                   (value.startswith("'") and value.endswith("'")):
                    value = value[1:-1]
                
                # Handle boolean values
                if isinstance(value, str) and value.lower() == 'true':
                    value = True
                elif isinstance(value, str) and value.lower() == 'false':
                    value = False
                
                # Handle null/None
                if isinstance(value, str) and value.lower() in ['null', 'none', '']:
                    value = None
                
                # Handle numbers
                try:
                    if '.' in value:
                        value = float(value)
                    else:
                        value = int(value)
                except (ValueError, TypeError):
                    pass
                
                metadata[key] = value
                current_key = key
            elif current_key:
                # Continuation of previous value
                if current_key in metadata:
                    existing = metadata[current_key]
                    if isinstance(existing, str):
                        metadata[current_key] = existing + '\n' + line
                    else:
                        metadata[current_key] = str(existing) + '\n' + line
        
        # Get the content after frontmatter
        content_text = '\n'.join(lines[content_start:])
        
        return {'content': content_text, 'metadata': metadata}
    
    @staticmethod
    def create(metadata, content):
        """Create markdown content with frontmatter from metadata and content."""
        frontmatter_lines = ['---']
        for key, value in metadata.items():
            if value is None:
                frontmatter_lines.append(f"{key}:")
            elif isinstance(value, bool):
                frontmatter_lines.append(f"{key}: {str(value).lower()}")
            elif isinstance(value, (int, float)):
                frontmatter_lines.append(f"{key}: {value}")
            elif isinstance(value, str):
                # Escape quotes and handle multiline
                if '\n' in value:
                    # Use folded block style
                    frontmatter_lines.append(f"{key}: >")
                    for line in value.split('\n'):
                        frontmatter_lines.append(f"  {line}")
                else:
                    # Use quoted string if contains special chars
                    if any(c in value for c in [':', '#', '[', ']', '{', '}', '!', '*']) or value.strip() != value:
                        frontmatter_lines.append(f"{key}: \"{value}\"")
                    else:
                        frontmatter_lines.append(f"{key}: {value}")
            else:
                frontmatter_lines.append(f"{key}: {value}")
        frontmatter_lines.append('---')
        frontmatter_lines.append('')
        frontmatter_lines.append(content)
        return '\n'.join(frontmatter_lines)


# Use the appropriate parser
if HAS_FRONTMATTER:
    FrontmatterParser = frontmatter
elif HAS_YAML:
    # Simple wrapper for ruamel.yaml
    class YamlFrontmatter:
        @staticmethod
        def parse(content):
            yaml = ruamel.yaml.YAML(typ='safe')
            if not content or not content.strip():
                return {'content': content, 'metadata': {}}
            lines = content.split('\n')
            if lines[0].strip() != '---':
                return {'content': content, 'metadata': {}}
            
            metadata_lines = []
            content_start = None
            for i, line in enumerate(lines[1:], 1):
                if line.strip() == '---':
                    content_start = i + 1
                    break
                metadata_lines.append(line)
            
            if content_start is None:
                return {'content': content, 'metadata': {}}
            
            from io import StringIO
            metadata = yaml.load('\n'.join(metadata_lines))
            content_text = '\n'.join(lines[content_start:])
            return {'content': content_text, 'metadata': metadata or {}}
        
        @staticmethod
        def create(metadata, content):
            yaml = ruamel.yaml.YAML(typ='safe')
            from io import StringIO
            stream = StringIO()
            yaml.dump(metadata, stream)
            return f"---\n{stream.getvalue()}---\n\n{content}"
    
    FrontmatterParser = YamlFrontmatter
else:
    FrontmatterParser = SimpleFrontmatter


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
            result = FrontmatterParser.parse(md_file.read_text(encoding='utf-8'))
            metadata = result.get('metadata', {})
            if metadata.get('slug'):
                slugs.append(metadata['slug'])
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
            content = md_file.read_text(encoding='utf-8')
            result = FrontmatterParser.parse(content)
            metadata = result.get('metadata', {})
            
            # Build story dict
            story = {
                'id': md_file.stem,  # Use filename as ID
                'title': metadata.get('title', 'Untitled'),
                'slug': metadata.get('slug', md_file.stem),
                'content': result.get('content', ''),
                'excerpt': metadata.get('excerpt', ''),
                'author': metadata.get('author', 'Admin'),
                'category': metadata.get('category', 'General'),
                'featured_image': metadata.get('featured_image', ''),
                'published': metadata.get('published', False),
                'published_at': metadata.get('published_at', ''),
                'created_at': metadata.get('created_at', md_file.stat().st_ctime),
                'updated_at': metadata.get('updated_at', md_file.stat().st_mtime),
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
            pub_month = published_at[:7] if isinstance(published_at, str) else ''
            create_month = created_at[:7] if isinstance(created_at, str) else ''
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
        content = md_file.read_text(encoding='utf-8')
        result = FrontmatterParser.parse(content)
        metadata = result.get('metadata', {})
        
        story = {
            'id': story_id,
            'title': metadata.get('title', 'Untitled'),
            'slug': metadata.get('slug', story_id),
            'content': result.get('content', ''),
            'excerpt': metadata.get('excerpt', ''),
            'author': metadata.get('author', 'Admin'),
            'category': metadata.get('category', 'General'),
            'featured_image': metadata.get('featured_image', ''),
            'published': metadata.get('published', False),
            'published_at': metadata.get('published_at', ''),
            'created_at': metadata.get('created_at', md_file.stat().st_ctime),
            'updated_at': metadata.get('updated_at', md_file.stat().st_mtime),
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
            content = md_file.read_text(encoding='utf-8')
            result = FrontmatterParser.parse(content)
            metadata = result.get('metadata', {})
            if metadata.get('slug') == slug:
                story = {
                    'id': md_file.stem,
                    'title': metadata.get('title', 'Untitled'),
                    'slug': slug,
                    'content': result.get('content', ''),
                    'excerpt': metadata.get('excerpt', ''),
                    'author': metadata.get('author', 'Admin'),
                    'category': metadata.get('category', 'General'),
                    'featured_image': metadata.get('featured_image', ''),
                    'published': metadata.get('published', False),
                    'published_at': metadata.get('published_at', ''),
                    'created_at': metadata.get('created_at', md_file.stat().st_ctime),
                    'updated_at': metadata.get('updated_at', md_file.stat().st_mtime),
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
        'excerpt': data.get('excerpt', ''),
        'author': data.get('author', 'Admin'),
        'category': data.get('category', 'General'),
        'featured_image': data.get('featured_image', ''),
        'published': data.get('published', False),
        'published_at': data.get('published_at', datetime.now().isoformat()),
        'created_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat(),
    }
    
    # Handle HTML content - store as markdown
    # For now, we'll store HTML as-is in the content field
    # In a full migration, you'd convert HTML to markdown
    content = data.get('content', '')
    
    # Create the markdown file
    md_content = FrontmatterParser.create(metadata, content)
    md_file.write_text(md_content, encoding='utf-8')
    
    return md_file.stem  # Return the ID (filename without extension)


def update_story(story_id, data):
    """Update an existing story."""
    ensure_directories()
    md_file = STORIES_DIR / f"{story_id}.md"
    
    if not md_file.exists():
        return False
    
    try:
        # Get existing metadata to preserve unchanged fields
        existing_content = md_file.read_text(encoding='utf-8')
        result = FrontmatterParser.parse(existing_content)
        existing_metadata = result.get('metadata', {})
        
        # Update metadata with new data
        metadata = existing_metadata.copy()
        metadata.update({
            'title': data.get('title', metadata.get('title', 'Untitled')),
            'slug': data.get('slug', metadata.get('slug', story_id)),
            'excerpt': data.get('excerpt', metadata.get('excerpt', '')),
            'author': data.get('author', metadata.get('author', 'Admin')),
            'category': data.get('category', metadata.get('category', 'General')),
            'featured_image': data.get('featured_image', metadata.get('featured_image', '')),
            'published': data.get('published', metadata.get('published', False)),
            'published_at': data.get('published_at', metadata.get('published_at', '')),
            'updated_at': datetime.now().isoformat(),
        })
        
        # Update content
        content = data.get('content', result.get('content', ''))
        
        # Write updated file
        md_content = FrontmatterParser.create(metadata, content)
        md_file.write_text(md_content, encoding='utf-8')
        
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
            content = md_file.read_text(encoding='utf-8')
            result = FrontmatterParser.parse(content)
            metadata = result.get('metadata', {})
            category = metadata.get('category', 'General')
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
            'excerpt': story['excerpt'] or '',
            'author': story['author'],
            'category': story['category'],
            'featured_image': story['featured_image'] or '',
            'published': bool(story['published']),
            'published_at': story['published_at'] or '',
            'created_at': story['created_at'] or '',
            'updated_at': story['updated_at'] or '',
        }
        
        content = story['content']
        
        # Create markdown file
        filename = f"{story['slug']}.md"
        md_file = STORIES_DIR / filename
        
        # Check for duplicate slugs
        if md_file.exists():
            filename = f"{story['slug']}-{secrets.token_hex(2)}.md"
            md_file = STORIES_DIR / filename
            metadata['slug'] = story['slug'] + '-' + secrets.token_hex(2)
        
        md_content = FrontmatterParser.create(metadata, content)
        md_file.write_text(md_content, encoding='utf-8')
    
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
