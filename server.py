#!/usr/bin/env python3
"""
Scooper CMS - Content Management Platform for News Site
A lightweight, modern CMS with paper-style frontend and backend management.
Uses only Python standard library - no external dependencies required.

Features:
- SQLite database for stories
- Paper-style frontend with modern design
- Full CMS backend for story management
- Dark and light mode support
- Preview functionality
- Rich text editing support (HTML content)
"""

import os
import sys
import sqlite3
import json
import base64
import cgi
import uuid
import secrets
from io import BytesIO
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, unquote
from datetime import datetime
import re

from template_engine import TemplateEngine, SafeString, get_engine as get_template_engine

# HELPERS
# ============================================================================

# ============================================================================
# HELPERS
# ============================================================================

def save_uploaded_file(field, upload_dir=None):
    """Save an uploaded file to the uploads directory and return the relative path."""
    if upload_dir is None:
        upload_dir = UPLOADS_DIR
    if not field or not field.filename:
        return None
    
    # Generate a unique filename to prevent conflicts
    ext = os.path.splitext(field.filename)[1].lower()
    # Clean extension - only allow common image types
    allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg'}
    if ext not in allowed_extensions:
        return None
    
    unique_name = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(upload_dir, unique_name)
    
    try:
        file_content = field.file.read()
        with open(file_path, 'wb') as f:
            f.write(file_content)
        field.file.close()
        # Return relative path from static directory
        return os.path.join('/static/uploads', unique_name)
    except Exception as e:
        print(f"Error saving file: {e}")
        return None



# For production with reverse proxy, change HOST to "0.0.0.0"
HOST = "localhost"
PORT = 8000
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "db", "scooper.db")
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
UPLOADS_DIR = os.path.join(STATIC_DIR, "uploads")

# Authentication configuration for CMS access
CMS_USERNAME = "admin"
CMS_PASSWORD = "admin"

# CSRF configuration
CSRF_COOKIE_NAME = "csrf_token"
CSRF_TOKEN_LENGTH = 32

# Ensure directories exist
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)

# ============================================================================
# CSRF PROTECTION
# ============================================================================

def generate_csrf_token():
    """Generate a cryptographically secure random CSRF token."""
    return secrets.token_hex(CSRF_TOKEN_LENGTH)


def validate_csrf_token(request_cookie_token, request_form_token):
    """Validate CSRF token using double-submit cookie pattern."""
    if not request_cookie_token or not request_form_token:
        return False
    return secrets.compare_digest(request_cookie_token, request_form_token)


# ============================================================================
# HELPERS
# ============================================================================

def get_theme_icon(theme):
    """Get the appropriate icon for a theme (sun for light, moon for dark)."""
    light_themes = ['light', 'rose-pine-dawn', 'catpuccin-latte']
    icon = '&#127774;' if theme in light_themes else '&#127771;'
    return SafeString(icon)


# ============================================================================
# DATABASE
# ============================================================================

def init_db():
    """Initialize the SQLite database with required tables."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Stories table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            slug TEXT NOT NULL UNIQUE,
            content TEXT NOT NULL,
            excerpt TEXT,
            author TEXT DEFAULT 'Admin',
            category TEXT DEFAULT 'General',
            featured_image TEXT,
            published BOOLEAN DEFAULT 0,
            published_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Settings table (for site title, theme, etc.)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    
    # Categories table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Insert default settings if not exists
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('site_title', 'Scooper Paper')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('site_description', 'Your News, Delivered')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('theme', 'light')")
    
    conn.commit()
    conn.close()


def get_db():
    """Get a database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ============================================================================
# MODELS
# ============================================================================

def get_all_stories(published_only=False, search=None, category=None, status=None, month=None, page=1, per_page=10):
    """Get all stories with optional filtering and pagination.
    
    Args:
        published_only: Only return published stories
        search: Search term to match against title and content
        category: Filter by category name
        status: Filter by status ('published', 'draft', or None for all)
        month: Filter by month (YYYY-MM format)
        page: Page number for pagination (1-based)
        per_page: Number of stories per page
    
    Returns:
        tuple: (stories, total_count) - list of stories and total count for pagination
    """
    conn = get_db()
    
    # Build WHERE clause
    conditions = []
    params = []
    
    if published_only:
        conditions.append("published = 1")
    
    if search:
        conditions.append("(title LIKE ? OR content LIKE ? OR excerpt LIKE ?)")
        search_param = f"%{search}%"
        params.extend([search_param, search_param, search_param])
    
    if category:
        conditions.append("category = ?")
        params.append(category)
    
    if status == 'published':
        conditions.append("published = 1")
    elif status == 'draft':
        conditions.append("published = 0")
    
    if month:
        # Filter by month - check both published_at and created_at
        conditions.append("(strftime('%Y-%m', published_at) = ? OR strftime('%Y-%m', created_at) = ?)")
        params.extend([month, month])
    
    # Build query for counting total
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    
    # Get total count
    count_cursor = conn.execute(f"SELECT COUNT(*) FROM stories WHERE {where_clause}", params)
    total_count = count_cursor.fetchone()[0]
    
    # Build query with pagination
    order_clause = "ORDER BY published_at DESC, created_at DESC"
    offset = (page - 1) * per_page
    
    cursor = conn.execute(
        f"SELECT * FROM stories WHERE {where_clause} {order_clause} LIMIT ? OFFSET ?",
        params + [per_page, offset]
    )
    stories = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return stories, total_count


def get_story_by_id(story_id):
    """Get a single story by ID."""
    try:
        story_id = int(story_id)
    except:
        return None
    conn = get_db()
    cursor = conn.execute("SELECT * FROM stories WHERE id = ?", (story_id,))
    story = cursor.fetchone()
    conn.close()
    return dict(story) if story else None


def get_story_by_slug(slug):
    """Get a single story by slug."""
    conn = get_db()
    cursor = conn.execute("SELECT * FROM stories WHERE slug = ?", (slug,))
    story = cursor.fetchone()
    conn.close()
    return dict(story) if story else None


def create_story(data):
    """Create a new story."""
    conn = get_db()
    cursor = conn.execute(
        """INSERT INTO stories (title, slug, content, excerpt, author, category, featured_image, published, published_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (data.get('title'), data.get('slug'), data.get('content'), 
         data.get('excerpt'), data.get('author', 'Admin'), 
         data.get('category', 'General'), data.get('featured_image'),
         data.get('published', False), data.get('published_at'))
    )
    story_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return story_id


def update_story(story_id, data):
    """Update an existing story."""
    conn = get_db()
    conn.execute(
        """UPDATE stories SET title = ?, slug = ?, content = ?, excerpt = ?, 
           author = ?, category = ?, featured_image = ?, published = ?, 
           published_at = ?, updated_at = CURRENT_TIMESTAMP
           WHERE id = ?""",
        (data.get('title'), data.get('slug'), data.get('content'),
         data.get('excerpt'), data.get('author', 'Admin'),
         data.get('category', 'General'), data.get('featured_image'),
         data.get('published', False), data.get('published_at'), story_id)
    )
    conn.commit()
    conn.close()


def delete_story(story_id):
    """Delete a story."""
    conn = get_db()
    conn.execute("DELETE FROM stories WHERE id = ?", (story_id,))
    conn.commit()
    conn.close()


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def set_setting(key, value):
    """Set a setting value."""
    conn = get_db()
    conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()


def get_setting(key, default=None):
    """Get a setting value."""
    conn = get_db()
    cursor = conn.execute("SELECT value FROM settings WHERE key = ?", (key,))
    result = cursor.fetchone()
    conn.close()
    return result['value'] if result else default


def slugify(text):
    """Simple slugify function."""
    if not text:
        return ''
    slug = text.lower()
    slug = re.sub(r'[^\w\s-]', '', slug)  # Remove special chars
    slug = re.sub(r'[\s_]+', '-', slug)   # Replace spaces with -
    slug = re.sub(r'-+', '-', slug)      # Remove duplicate -
    slug = slug.strip('-')
    return slug


def format_date(timestamp):
    """Format a timestamp for display."""
    if not timestamp:
        return ''
    try:
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        return dt.strftime('%B %d, %Y')
    except:
        return timestamp


def escape_html(text):
    """Escape HTML special characters."""
    if not text:
        return ''
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')


# ============================================================================
# CATEGORY FUNCTIONS
# ============================================================================

def get_all_categories():
    """Get all categories."""
    conn = get_db()
    cursor = conn.execute("SELECT id, name FROM categories ORDER BY name")
    rows = cursor.fetchall()
    conn.close()
    # Ensure we return a list of proper dicts
    return [{'id': row['id'], 'name': row['name']} for row in rows]


def get_category_by_id(category_id):
    """Get a single category by ID."""
    try:
        category_id = int(category_id)
    except:
        return None
    conn = get_db()
    cursor = conn.execute("SELECT id, name FROM categories WHERE id = ?", (category_id,))
    category = cursor.fetchone()
    conn.close()
    return {'id': category['id'], 'name': category['name']} if category else None


def get_category_by_name(name):
    """Get a category by name."""
    conn = get_db()
    cursor = conn.execute("SELECT id, name FROM categories WHERE name = ?", (name,))
    category = cursor.fetchone()
    conn.close()
    return {'id': category['id'], 'name': category['name']} if category else None


def create_category(name):
    """Create a new category."""
    conn = get_db()
    try:
        cursor = conn.execute("INSERT INTO categories (name) VALUES (?)", (name,))
        category_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return category_id
    except sqlite3.IntegrityError:
        conn.close()
        return None


def update_category(category_id, name):
    """Update a category."""
    conn = get_db()
    conn.execute("UPDATE categories SET name = ? WHERE id = ?", (name, category_id))
    conn.commit()
    conn.close()


def delete_category(category_id):
    """Delete a category."""
    conn = get_db()
    conn.execute("DELETE FROM categories WHERE id = ?", (category_id,))
    conn.commit()
    conn.close()


# ============================================================================
# TEMPLATE RENDERING
# ============================================================================

def render_template(name, context=None):
    """Render a template with variable substitution using the lexer/parser engine.
    
    This function uses a proper lexer/parser-based template engine that:
    - Auto-escapes HTML special characters to prevent XSS vulnerabilities
    - Properly parses template syntax (variables, comments, includes, loops, conditionals)
    - Supports nested variable access via dot notation
    
    To mark content as safe HTML (e.g., rich text from the database), wrap it in SafeString:
        context = {'content': SafeString(html_content)}
    
    Args:
        name: Template file name (relative to TEMPLATES_DIR)
        context: Dictionary of variables for the template
    
    Returns:
        Rendered HTML string
    """
    if context is None:
        context = {}
    
    engine = get_template_engine(TEMPLATES_DIR)
    return engine.render_template(name, context)


# ============================================================================
# URL ROUTING
# ============================================================================

class ScooperHandler(BaseHTTPRequestHandler):
    """HTTP request handler with routing for Scooper CMS."""
    
    # Class-level route mappings
    routes = {
        'GET': {},
        'POST': {},
    }
    
    @classmethod
    def add_route(cls, method, path, handler):
        """Add a route (for dynamic registration)."""
        if method not in cls.routes:
            cls.routes[method] = {}
        cls.routes[method][path] = handler
    
    def do_GET(self):
        self.handle_request('GET')
    
    def do_POST(self):
        self.handle_request('POST')

    def authenticate(self):
        """Check if request has valid Basic Authentication for CMS access."""
        auth_header = self.headers.get('Authorization')
        if not auth_header:
            return False
        
        # Check for Basic auth
        if not auth_header.startswith('Basic '):
            return False
        
        # Decode the base64 encoded credentials
        encoded_credentials = auth_header[6:]  # Remove 'Basic ' prefix
        try:
            decoded = base64.b64decode(encoded_credentials).decode('utf-8')
        except (base64.binascii.Error, UnicodeDecodeError):
            return False
        
        # Expected format: username:password
        parts = decoded.split(':', 1)
        if len(parts) != 2:
            return False
        
        username, password = parts
        return username == CMS_USERNAME and password == CMS_PASSWORD
    
    def get_csrf_cookie(self):
        """Get the CSRF token from the Cookie header."""
        cookie_header = self.headers.get('Cookie', '')
        for part in cookie_header.split(';'):
            part = part.strip()
            if part.startswith(CSRF_COOKIE_NAME + '='):
                return part.split('=', 1)[1]
        return None
    
    def set_csrf_cookie(self, token):
        """Set the CSRF token as a cookie in the response."""
        cookie_value = f"{CSRF_COOKIE_NAME}={token}; Path=/; SameSite=Lax; Max-Age=3600"
        self.send_header('Set-Cookie', cookie_value)
    
    def validate_cms_csrf(self, path, form_data):
        """Validate CSRF token for CMS POST requests."""
        if not path.startswith('/cms'):
            return True
        cookie_token = self.get_csrf_cookie()
        form_token = form_data.get('csrf_token', '')
        return validate_csrf_token(cookie_token, form_token)
    
    def handle_request(self, method):
        """Handle HTTP request with routing."""
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        
        # Remove trailing slash for consistency
        if path.endswith('/') and path != '/':
            path = path.rstrip('/')
        
        # Track if this is a CMS request for CSRF handling
        is_cms_request = path.startswith('/cms')
        
        # Check if request targets CMS - requires authentication
        if is_cms_request:
            if not self.authenticate():
                self.send_response(401)
                self.send_header('WWW-Authenticate', 'Basic realm="Scooper CMS"')
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(b'Authentication required')
                return
        
        # Check static files
        if path.startswith('/static/'):
            self.serve_static(path)
            return
        
        # Route to appropriate handler
        routes = self.routes.get(method, {})
        handler = routes.get(path)
        
        # If no exact match, try prefix matching for path parameters
        # e.g., /cms/edit/123 should match /cms/edit
        # Sort routes by number of segments descending, then by length descending for stability
        if handler is None:
            def route_sort_key(item):
                route_path = item[0]
                segments = [s for s in route_path.split('/') if s]
                return (len(segments), len(route_path))
            sorted_routes = sorted(routes.items(), key=route_sort_key, reverse=True)
            for route_path, route_handler in sorted_routes:
                # Normalize route path by removing trailing slash
                normalized_route = route_path.rstrip('/')
                # Check if path starts with this route followed by /
                if path.startswith(normalized_route + '/'):
                    handler = route_handler
                    break
        
        if handler:
            # Parse query string
            query_params = parse_qs(parsed.query)
            simple_params = {}
            for k, v in query_params.items():
                simple_params[k] = v[0] if len(v) == 1 else v
            
            # Parse form data for POST
            form_data = {}
            files = {}
            if method == 'POST':
                content_type = self.headers.get('Content-Type', '')
                content_length = int(self.headers.get('Content-Length', 0))
                
                if content_length > 0:
                    if 'multipart/form-data' in content_type:
                        # Parse multipart form data
                        try:
                            form = cgi.FieldStorage(
                                fp=self.rfile,
                                headers=self.headers,
                                environ={'REQUEST_METHOD': method}
                            )
                            for field in form.list:
                                if field.filename:
                                    # File upload field
                                    files[field.name] = field
                                else:
                                    # Regular form field
                                    form_data[field.name] = field.value
                        except Exception as e:
                            print(f"Error parsing multipart: {e}")
                            form_data = {}
                    else:
                        # Parse regular form data
                        post_data = self.rfile.read(content_length).decode('utf-8')
                        form_data = parse_qs(post_data)
                        simple_form = {}
                        for k, v in form_data.items():
                            simple_form[k] = v[0] if len(v) == 1 else v
                        form_data = simple_form
            
            # Store files on handler instance for access in handlers
            self.files = files
            
            # CSRF Validation for POST requests to CMS
            if method == 'POST' and is_cms_request:
                if not self.validate_cms_csrf(path, form_data):
                    self.send_response(403)
                    self.send_header('Content-Type', 'text/html; charset=utf-8')
                    self.end_headers()
                    self.wfile.write(b'CSRF validation failed')
                    return
            
            # Generate CSRF token for GET requests to CMS forms
            csrf_token = None
            if method == 'GET' and is_cms_request:
                existing_token = self.get_csrf_cookie()
                if existing_token:
                    csrf_token = existing_token
                else:
                    csrf_token = generate_csrf_token()
            
            # Call handler - pass csrf_token only to CMS handlers
            try:
                if is_cms_request:
                    response = handler(path, simple_params, form_data, self, csrf_token=csrf_token)
                else:
                    response = handler(path, simple_params, form_data, self)
                if isinstance(response, tuple):
                    content = response[0]
                    status_code = response[1] if len(response) > 1 else 200
                    custom_headers = response[2] if len(response) > 2 and isinstance(response[2], dict) else {}
                else:
                    content = response
                    status_code = 200
                    custom_headers = {}
                
                self.send_response(status_code)
                for h_name, h_value in custom_headers.items():
                    self.send_header(h_name, h_value)
                if 'Content-Type' not in custom_headers:
                    content_type = 'application/json' if isinstance(content, (dict, list)) else 'text/html; charset=utf-8'
                    self.send_header('Content-Type', content_type)
                
                # Set CSRF cookie for CMS GET requests
                if csrf_token and method == 'GET' and is_cms_request:
                    self.set_csrf_cookie(csrf_token)
                
                self.end_headers()
                
                if isinstance(content, (dict, list)):
                    self.wfile.write(json.dumps(content).encode('utf-8'))
                else:
                    self.wfile.write(content.encode('utf-8'))
            except Exception as e:
                import traceback
                traceback.print_exc()
                self.send_error(500, str(e))
            return
        
        # Default 404
        self.send_error(404, f"Page not found: {path}")
    
    def serve_static(self, path):
        """Serve static files."""
        # Remove the /static/ prefix properly
        if path.startswith('/static/'):
            file_path = os.path.join(STATIC_DIR, path[8:])  # Remove '/static/' (8 chars)
        else:
            file_path = os.path.join(STATIC_DIR, path)
        
        if '..' in path or not path.startswith('/static/'):
            self.send_error(403)
            return
        
        if os.path.exists(file_path) and os.path.isfile(file_path):
            try:
                with open(file_path, 'rb') as f:
                    content = f.read()
                
                ext = os.path.splitext(file_path)[1].lower()
                content_types = {
                    '.css': 'text/css',
                    '.js': 'application/javascript',
                    '.png': 'image/png',
                    '.jpg': 'image/jpeg',
                    '.jpeg': 'image/jpeg',
                    '.gif': 'image/gif',
                    '.svg': 'image/svg+xml',
                    '.woff': 'font/woff',
                    '.woff2': 'font/woff2',
                }
                content_type = content_types.get(ext, 'application/octet-stream')
                
                self.send_response(200)
                self.send_header('Content-Type', content_type)
                self.send_header('Content-Length', str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            except Exception as e:
                self.send_error(500, str(e))
        else:
            self.send_error(404)
    
    def log_message(self, format, *args):
        """Override to suppress default logging."""
        pass


# ============================================================================
# ROUTE HANDLERS
# ============================================================================

def paper_home_handler(path, params, form_data, handler):
    """Handle the paper homepage."""
    theme = get_setting('theme', 'light')
    # Get page from query params, default to 1
    page = int(params.get('page', 1))
    stories, total_count = get_all_stories(published_only=True, page=page, per_page=10)
    
    site_title = get_setting('site_title', 'Scooper Paper')
    site_description = get_setting('site_description', 'Your News, Delivered')
    
    # Format stories
    formatted_stories = []
    for story in stories:
        excerpt = story.get('excerpt', story['content'][:150] + '...')
        formatted_stories.append({
            'id': story['id'],
            'title': story['title'],
            'slug': story['slug'],
            'excerpt': SafeString(excerpt),
            'author': story.get('author', 'Admin'),
            'category': story.get('category', 'General'),
            'published_at': format_date(story.get('published_at')) or format_date(story.get('created_at')),
        })
    
    theme_icon = get_theme_icon(theme)
    
    # Pagination info
    total_pages = (total_count + 9) // 10  # Ceiling division
    
    context = {
        'site_title': site_title,
        'site_description': site_description,
        'theme': theme,
        'theme_icon': theme_icon,
        'stories': formatted_stories,
        'pagination': {
            'current_page': page,
            'total_pages': total_pages,
            'total_count': total_count,
            'has_previous': page > 1,
            'has_next': page < total_pages,
        },
    }
    
    return render_template('paper/index.html', context)


def paper_story_handler(path, params, form_data, handler):
    """Handle individual story page."""
    parts = [p for p in path.split('/') if p]
    slug = parts[-1] if parts else ''
    
    story = get_story_by_slug(slug)
    if not story:
        return "<h1>404 - Story not found</h1>", 404
    
    theme = get_setting('theme', 'light')
    site_title = get_setting('site_title', 'Scooper Paper')
    site_description = get_setting('site_description', 'Your News, Delivered')
    theme_icon = get_theme_icon(theme)
    
    context = {
        'site_title': site_title,
        'site_description': site_description,
        'theme': theme,
        'theme_icon': theme_icon,
        'is_preview': params.get('preview', False),
        'story': {
            'id': story['id'],
            'title': story['title'],
            'slug': story['slug'],
            'content': SafeString(story['content']),
            'excerpt': SafeString(story.get('excerpt', '')),
            'author': story.get('author', 'Admin'),
            'category': story.get('category', 'General'),
            'published_at': format_date(story.get('published_at')) or format_date(story.get('created_at')),
        },
    }
    
    return render_template('paper/story.html', context)


def cms_dashboard_handler(path, params, form_data, handler, csrf_token=None):
    """Handle CMS dashboard."""
    theme = get_setting('theme', 'light')
    # Get first page for dashboard (shows recent stories)
    stories, total_count = get_all_stories(page=1, per_page=5)
    
    published_count = sum(1 for s in stories if s.get('published', False))
    
    formatted_stories = []
    for story in stories:
        formatted_stories.append({
            'id': story['id'],
            'title': story['title'],
            'published': story.get('published', False),
        })
    
    context = {
        'site_title': get_setting('site_title', 'Scooper'),
        'page_title': 'Dashboard',
        'theme': theme,
        'theme_icon': get_theme_icon(theme),
        'stories': stories,
        'total_stories': total_count,
        'published_count': published_count,
        'recent_stories': formatted_stories,
        'csrf_token': csrf_token or '',
    }
    
    return render_template('cms/dashboard.html', context)


def cms_stories_handler(path, params, form_data, handler, csrf_token=None):
    """Handle CMS stories list with filtering support."""
    theme = get_setting('theme', 'light')
    
    # Parse filter parameters from query string
    search_query = params.get('q', '').strip()
    category_filter = params.get('category', '').strip()
    status_filter = params.get('status', '').strip()  # 'published', 'draft', or empty
    month_filter = params.get('month', '').strip()
    page = int(params.get('page', 1))
    per_page = 10
    
    # Get stories with filters and pagination
    stories, total_count = get_all_stories(
        published_only=False,
        search=search_query if search_query else None,
        category=category_filter if category_filter else None,
        status=status_filter if status_filter in ('published', 'draft') else None,
        month=month_filter if month_filter else None,
        page=page,
        per_page=per_page
    )
    
    # Get all available categories for filter dropdown
    all_categories = get_all_categories()
    category_names = sorted(set([c['name'] for c in all_categories]))
    # Ensure we have at least General
    if 'General' not in category_names:
        category_names.insert(0, 'General')
    
    # Format categories with selected state for dropdown
    formatted_categories = []
    for cat_name in category_names:
        formatted_categories.append({
            'name': cat_name,
            'selected': cat_name == category_filter,
        })
    
    # Get all available months for filter dropdown
    conn = get_db()
    cursor = conn.execute("""
        SELECT DISTINCT strftime('%Y-%m', published_at) as month 
        FROM stories 
        WHERE published_at IS NOT NULL 
        UNION 
        SELECT DISTINCT strftime('%Y-%m', created_at) as month 
        FROM stories 
        WHERE published_at IS NULL
        ORDER BY month DESC
    """)
    available_months = [row['month'] for row in cursor.fetchall()]
    conn.close()
    
    # Format month names for display
    month_display_names = {}
    formatted_months = []
    for m in available_months:
        try:
            year, month_num = m.split('-')
            from datetime import datetime
            dt = datetime(int(year), int(month_num), 1)
            display_name = dt.strftime('%B %Y')
            month_display_names[m] = display_name
            formatted_months.append({
                'value': m,
                'display': display_name,
                'selected': m == month_filter,
            })
        except:
            month_display_names[m] = m
            formatted_months.append({
                'value': m,
                'display': m,
                'selected': m == month_filter,
            })
    
    # Format stories with raw dates for grouping
    formatted_stories = []
    for story in stories:
        raw_published_at = story.get('published_at')
        raw_created_at = story.get('created_at')
        display_date = format_date(raw_published_at) or format_date(raw_created_at)
        
        # Get month for grouping (YYYY-MM format)
        story_month = None
        if raw_published_at:
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(raw_published_at.replace('Z', '+00:00'))
                story_month = dt.strftime('%Y-%m')
            except:
                pass
        if not story_month and raw_created_at:
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(raw_created_at.replace('Z', '+00:00'))
                story_month = dt.strftime('%Y-%m')
            except:
                pass
        
        formatted_stories.append({
            'id': story['id'],
            'title': story['title'],
            'category': story.get('category', 'General'),
            'author': story.get('author', 'Admin'),
            'published': story.get('published', False),
            'published_at': display_date,
            'raw_date': raw_published_at or raw_created_at,
            'month': story_month,
        })
    
    theme_icon = get_theme_icon(theme)
    
    # Build active filter tags for display
    active_filter_tags = []
    if search_query:
        active_filter_tags.append({
            'label': f'Search: "{search_query}"',
            'param': 'q',
        })
    if category_filter:
        active_filter_tags.append({
            'label': f'Category: {category_filter}',
            'param': 'category',
        })
    if status_filter:
        active_filter_tags.append({
            'label': f'Status: {status_filter}',
            'param': 'status',
        })
    if month_filter:
        active_filter_tags.append({
            'label': f'Month: {month_display_names.get(month_filter, month_filter)}',
            'param': 'month',
        })
    # Build query string for active filters (to preserve them in links)
    def build_filter_query(exclude_param=None):
        filter_params = []
        if search_query and exclude_param != 'q':
            filter_params.append(f'q={search_query}')
        if category_filter and exclude_param != 'category':
            filter_params.append(f'category={category_filter}')
        if status_filter and exclude_param != 'status':
            filter_params.append(f'status={status_filter}')
        if month_filter and exclude_param != 'month':
            filter_params.append(f'month={month_filter}')
        return '&'.join(filter_params)
    
    active_filter_query = build_filter_query()
    
    # Pagination info
    total_pages = (total_count + per_page - 1) // per_page  # Ceiling division
    
    context = {
        'site_title': get_setting('site_title', 'Scooper'),
        'page_title': 'All Stories',
        'theme': theme,
        'theme_icon': theme_icon,
        'stories': formatted_stories,
        'search_query': search_query,
        'category_filter': category_filter,
        'status_filter': status_filter,
        'month_filter': month_filter,
        'categories': formatted_categories,
        'all_categories': category_names,
        'months': formatted_months,
        'available_months': available_months,
        'month_display_names': month_display_names,
        'active_filter_query': active_filter_query,
        'has_filters': bool(search_query or category_filter or status_filter or month_filter),
        'active_filter_tags': active_filter_tags,
        'total_count': total_count,
        'csrf_token': csrf_token or '',
        'pagination': {
            'current_page': page,
            'per_page': per_page,
            'total_pages': total_pages,
            'total_count': total_count,
            'has_previous': page > 1,
            'has_next': page < total_pages,
        },
    }
    
    return render_template('cms/stories.html', context)


def cms_create_handler(path, params, form_data, handler, csrf_token=None):
    """Handle story creation form."""
    theme = get_setting('theme', 'light')
    
    if form_data and 'title' in form_data:
        # Process form submission
        # Handle file upload for featured_image
        featured_image_path = form_data.get('featured_image', '')
        if 'featured_image' in handler.files:
            file_field = handler.files['featured_image']
            if file_field.filename:
                saved_path = save_uploaded_file(file_field)
                if saved_path:
                    featured_image_path = saved_path
        
        story_data = {
            'title': form_data['title'],
            'slug': slugify(form_data['title']),
            'content': form_data.get('content', ''),
            'excerpt': form_data.get('excerpt', ''),
            'author': form_data.get('author', 'Admin'),
            'category': form_data.get('category', 'General'),
            'featured_image': featured_image_path,
            'published': form_data.get('published') == 'on',
            'published_at': datetime.now().isoformat() if form_data.get('published') == 'on' else None,
        }
        
        create_story(story_data)
        # Redirect to stories list
        return '', 302, {'Location': '/cms/stories'}
    
    # Get categories from DB and merge with defaults
    db_categories = get_all_categories()
    default_categories = ['General', 'Local News', 'Technology', 'Business', 'Sports', 'Entertainment', 'Announcement']
    
    # Create list of unique category names (defaults + custom)
    all_category_names = list(set(default_categories + [c['name'] for c in db_categories]))
    all_category_names.sort()
    
    # Build categories list with DB IDs where available
    categories = []
    for cat_name in all_category_names:
        matching = [c for c in db_categories if c['name'] == cat_name]
        if matching:
            categories.append(matching[0])
        else:
            categories.append({'id': None, 'name': cat_name})
    
    theme_icon = get_theme_icon(theme)
    
    context = {
        'site_title': get_setting('site_title', 'Scooper'),
        'page_title': 'Create New Story',
        'theme': theme,
        'theme_icon': theme_icon,
        'categories': categories,
        'csrf_token': csrf_token or '',
    }
    
    return render_template('cms/create.html', context)


def cms_edit_handler(path, params, form_data, handler, csrf_token=None):
    """Handle story editing form."""
    theme = get_setting('theme', 'light')
    
    # Extract story ID
    parts = [p for p in path.split('/') if p]
    story_id = parts[-1] if parts else ''
    
    story = get_story_by_id(story_id)
    if not story:
        return "<h1>404 - Story not found</h1>", 404
    
    if form_data and 'title' in form_data:
        # Process form submission
        # Handle file upload for featured_image
        featured_image_path = form_data.get('featured_image', story.get('featured_image', ''))
        if 'featured_image' in handler.files:
            file_field = handler.files['featured_image']
            if file_field.filename:
                saved_path = save_uploaded_file(file_field)
                if saved_path:
                    featured_image_path = saved_path
        
        story_data = {
            'title': form_data['title'],
            'slug': slugify(form_data['title']),
            'content': form_data.get('content', ''),
            'excerpt': form_data.get('excerpt', ''),
            'author': form_data.get('author', story.get('author', 'Admin')),
            'category': form_data.get('category', story.get('category', 'General')),
            'featured_image': featured_image_path,
            'published': form_data.get('published') == 'on',
            'published_at': datetime.now().isoformat() if form_data.get('published') == 'on' else story.get('published_at'),
        }
        
        update_story(story_id, story_data)
        # Redirect to stories list
        return '', 302, {'Location': '/cms/stories'}
    
    categories = get_all_categories()
    theme_icon = get_theme_icon(theme)
    
    # If no categories exist, use defaults
    if not categories:
        categories = [{'id': None, 'name': 'General'}, {'id': None, 'name': 'Local News'}, 
                      {'id': None, 'name': 'Technology'}, {'id': None, 'name': 'Business'},
                      {'id': None, 'name': 'Sports'}, {'id': None, 'name': 'Entertainment'},
                      {'id': None, 'name': 'Announcement'}]
    
    context = {
        'site_title': get_setting('site_title', 'Scooper'),
        'page_title': f'Edit: {story["title"]}',
        'theme': theme,
        'theme_icon': theme_icon,
        'story': {
            'id': story['id'],
            'title': story['title'],
            'slug': story['slug'],
            'content': SafeString(story['content']),
            'excerpt': SafeString(story.get('excerpt', '')),
            'author': story.get('author', 'Admin'),
            'category': story.get('category', 'General'),
            'featured_image': story.get('featured_image', ''),
            'published': story.get('published', False),
        },
        'categories': categories,
        'csrf_token': csrf_token or '',
    }
    
    return render_template('cms/edit.html', context)


def cms_delete_handler(path, params, form_data, handler, csrf_token=None):
    """Handle story deletion."""
    parts = [p for p in path.split('/') if p]
    story_id = parts[-1] if parts else ''
    
    delete_story(story_id)
    return '', 302, {'Location': '/cms/stories'}


def cms_preview_handler(path, params, form_data, handler, csrf_token=None):
    """Handle story preview."""
    parts = [p for p in path.split('/') if p]
    story_id = parts[-1] if parts else ''
    
    story = get_story_by_id(story_id)
    if not story:
        return "<h1>404 - Story not found</h1>", 404
    
    theme = get_setting('theme', 'light')
    site_title = get_setting('site_title', 'Scooper Paper')
    site_description = get_setting('site_description', 'Your News, Delivered')
    theme_icon = get_theme_icon(theme)
    
    context = {
        'site_title': site_title,
        'site_description': site_description,
        'theme': theme,
        'theme_icon': theme_icon,
        'is_preview': True,
        'story': {
            'id': story['id'],
            'title': story['title'],
            'slug': story['slug'],
            'content': SafeString(story['content']),
            'excerpt': SafeString(story.get('excerpt', '')),
            'author': story.get('author', 'Admin'),
            'category': story.get('category', 'General'),
            'published_at': format_date(story.get('published_at')) or format_date(story.get('created_at')),
        },
    }
    
    return render_template('paper/story.html', context)


def cms_settings_handler(path, params, form_data, handler, csrf_token=None):
    """Handle CMS settings."""
    theme = get_setting('theme', 'light')
    
    if form_data:
        # Update settings
        if 'site_title' in form_data:
            set_setting('site_title', form_data['site_title'])
        if 'site_description' in form_data:
            set_setting('site_description', form_data['site_description'])
        if 'theme' in form_data:
            set_setting('theme', form_data['theme'])
        
        # Handle category operations
        # Add new category
        if 'new_category' in form_data and form_data['new_category'].strip():
            create_category(form_data['new_category'].strip())
        
        # Edit category
        if 'edit_category_id' in form_data and 'edit_category_name' in form_data:
            category_id = form_data['edit_category_id']
            new_name = form_data['edit_category_name'].strip()
            if new_name:
                update_category(category_id, new_name)
        
        # Delete category
        if 'delete_category_id' in form_data:
            category_id = form_data['delete_category_id']
            delete_category(category_id)
        
        return '', 302, {'Location': '/cms/settings'}
    
    theme_icon = get_theme_icon(theme)
    
    # Get categories from DB and merge with defaults
    db_categories = get_all_categories()
    
    # Start with default categories
    default_categories = ['General', 'Local News', 'Technology', 'Business', 'Sports', 'Entertainment', 'Announcement']
    categories = [{'id': None, 'name': name} for name in default_categories]
    
    # Add or merge DB categories
    for db_cat in db_categories:
        # Check if this category already exists in defaults
        found = False
        for i, cat in enumerate(categories):
            if cat['name'] == db_cat['name']:
                # Replace default with DB category (which has an ID)
                categories[i] = db_cat
                found = True
                break
        if not found:
            # Add new category from DB
            categories.append(db_cat)
    
    # Sort categories by name
    categories.sort(key=lambda c: c['name'])
    
    context = {
        'site_title': get_setting('site_title', 'Scooper'),
        'page_title': 'Settings',
        'theme': theme,
        'theme_icon': theme_icon,
        'site_title_value': get_setting('site_title', 'Scooper Paper'),
        'site_description_value': get_setting('site_description', 'Your News, Delivered'),
        'categories': categories,
        'csrf_token': csrf_token or '',
    }
    
    return render_template('cms/settings.html', context)


def toggle_theme_handler(path, params, form_data, handler, csrf_token=None):
    """Handle theme toggle via AJAX."""
    current = get_setting('theme', 'light')
    # Use the requested theme, fallback to a simple toggle if none provided
    new_theme = form_data.get('theme', 'dark' if current == 'light' else 'light')
    set_setting('theme', new_theme)
    return {'theme': new_theme, 'success': True}


# ============================================================================
# REGISTER ROUTES
# ============================================================================

# Paper routes
ScooperHandler.add_route('GET', '/', paper_home_handler)
ScooperHandler.add_route('GET', '/index.html', paper_home_handler)
ScooperHandler.add_route('GET', '/paper', paper_home_handler)
ScooperHandler.add_route('GET', '/paper/', paper_home_handler)

# Story routes
ScooperHandler.add_route('GET', '/story', paper_story_handler)

# CMS routes
ScooperHandler.add_route('GET', '/cms', cms_dashboard_handler)
ScooperHandler.add_route('GET', '/cms/', cms_dashboard_handler)
ScooperHandler.add_route('GET', '/cms/dashboard', cms_dashboard_handler)
ScooperHandler.add_route('GET', '/cms/stories', cms_stories_handler)
ScooperHandler.add_route('GET', '/cms/stories/', cms_stories_handler)
ScooperHandler.add_route('GET', '/cms/create', cms_create_handler)
ScooperHandler.add_route('GET', '/cms/create/', cms_create_handler)
ScooperHandler.add_route('POST', '/cms/create', cms_create_handler)
ScooperHandler.add_route('POST', '/cms/create/', cms_create_handler)
ScooperHandler.add_route('GET', '/cms/edit', cms_edit_handler)
ScooperHandler.add_route('GET', '/cms/edit/', cms_edit_handler)
ScooperHandler.add_route('POST', '/cms/edit', cms_edit_handler)
ScooperHandler.add_route('POST', '/cms/edit/', cms_edit_handler)
ScooperHandler.add_route('GET', '/cms/delete', cms_delete_handler)
ScooperHandler.add_route('GET', '/cms/delete/', cms_delete_handler)
ScooperHandler.add_route('GET', '/cms/preview', cms_preview_handler)
ScooperHandler.add_route('GET', '/cms/preview/', cms_preview_handler)
ScooperHandler.add_route('GET', '/cms/settings', cms_settings_handler)
ScooperHandler.add_route('GET', '/cms/settings/', cms_settings_handler)
ScooperHandler.add_route('POST', '/cms/settings', cms_settings_handler)
ScooperHandler.add_route('POST', '/cms/settings/', cms_settings_handler)
ScooperHandler.add_route('POST', '/api/toggle-theme', toggle_theme_handler)


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main entry point."""
    # Initialize database
    init_db()
    
    # Add sample data if empty
    conn = get_db()
    count = conn.execute("SELECT COUNT(*) FROM stories").fetchone()[0]
    conn.close()
    
    if count == 0:
        sample_stories = [
            {
                'title': 'Welcome to Scooper Paper',
                'slug': 'welcome-to-scooper-paper',
                'content': '<p>Welcome to our brand new news platform! Scooper Paper brings you the latest news from around the world, delivered with clarity and precision.</p><p>Our mission is to provide unbiased, timely news coverage that keeps you informed about what matters most.</p><p>Stay tuned as we continue to grow and bring you more stories that matter.</p>',
                'excerpt': 'Welcome to our brand new news platform!',
                'author': 'Editor-in-Chief',
                'category': 'Announcement',
                'published': True,
                'published_at': datetime.now().isoformat(),
            },
            {
                'title': 'Local Community Rallies for Park Cleanup',
                'slug': 'local-community-rallies-for-park-cleanup',
                'content': '<p>Last weekend, over 200 volunteers gathered at Central Park to participate in the largest community cleanup event of the year. Organized by local environmental group Green Future, the event saw families, students, and business owners working together to remove litter and restore the park to its former beauty.</p><p>"It was incredible to see so many people come together for a common cause," said Sarah Johnson, event organizer. "We collected over 50 bags of trash and recycled materials."</p><p>The park, which had been neglected for several months, now looks better than ever. Local residents have expressed their gratitude and many have pledged to participate in future cleanup events.</p>',
                'excerpt': 'Over 200 volunteers gathered for the largest community cleanup event.',
                'author': 'Jane Doe',
                'category': 'Local News',
                'published': True,
                'published_at': datetime.now().isoformat(),
            },
            {
                'title': 'Tech Innovations to Watch in 2024',
                'slug': 'tech-innovations-to-watch-in-2024',
                'content': '<p>The year 2024 promises to be an exciting one for technology enthusiasts. From advancements in artificial intelligence to breakthroughs in renewable energy, innovators are pushing the boundaries of what is possible.</p><p>One of the most anticipated developments is the release of quantum computing chips that can perform calculations previously thought impossible. Major tech companies are also investing heavily in augmented reality applications that could transform how we work, learn, and entertain ourselves.</p><p>Experts predict that these technologies will begin to enter the mainstream within the next 2-3 years, potentially revolutionizing multiple industries.</p>',
                'excerpt': 'From AI to quantum computing, 2024 promises exciting tech developments.',
                'author': 'John Smith',
                'category': 'Technology',
                'published': True,
                'published_at': datetime.now().isoformat(),
            },
        ]
        
        for story_data in sample_stories:
            create_story(story_data)
        
        print("Added sample stories to database.")
    
    # Always ensure default categories exist
    conn = get_db()
    cat_count = conn.execute("SELECT COUNT(*) FROM categories").fetchone()[0]
    conn.close()
    
    if cat_count == 0:
        default_categories = ['General', 'Local News', 'Technology', 'Business', 'Sports', 'Entertainment', 'Announcement']
        for cat_name in default_categories:
            create_category(cat_name)
        print("Added default categories to database.")
    
    # Start server
    server_address = (HOST, PORT)
    httpd = ThreadingHTTPServer(server_address, ScooperHandler)
    
    print(f"\n{'='*60}")
    print(f"  Scooper CMS - Content Management Platform")
    print(f"{'='*60}")
    print(f"\n  Paper site:  http://{HOST}:{PORT}/")
    print(f"  CMS backend: http://{HOST}:{PORT}/cms")
    print(f"\n  Press Ctrl+C to stop the server")
    print(f"{'='*60}\n")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        httpd.server_close()


if __name__ == '__main__':
    main()
