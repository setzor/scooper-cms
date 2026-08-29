"""Helper utilities"""

import re
from datetime import datetime
from typing import Optional
import os
from app.config import settings


def slugify(text: str) -> str:
    """Convert text to URL slug"""
    text = str(text).lower()
    text = re.sub(r'[^\w\s-]', '', text)  # Remove special chars
    text = re.sub(r'[\s_]+', '-', text)  # Replace spaces with hyphens
    text = re.sub(r'-+', '-', text)  # Remove duplicate hyphens
    text = text.strip('-')
    return text or 'untitled'


def format_date(date: Optional[datetime]) -> str:
    """Format date for display"""
    if not date:
        return ""
    return date.strftime("%B %d, %Y")


def format_datetime(date: Optional[datetime]) -> str:
    """Format datetime for display"""
    if not date:
        return ""
    return date.strftime("%B %d, %Y %I:%M %p")


def save_uploaded_file(file, upload_dir: Optional[str] = None) -> Optional[str]:
    """Save uploaded file and return relative path"""
    if upload_dir is None:
        upload_dir = settings.UPLOADS_DIR
    
    if not file:
        return None
    
    # Ensure upload directory exists
    os.makedirs(upload_dir, exist_ok=True)
    
    # Get file extension
    filename = file.filename
    ext = os.path.splitext(filename)[1].lower()
    
    # Allowed extensions
    allowed_extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
    if ext not in allowed_extensions:
        return None
    
    # Generate unique filename
    import uuid
    unique_name = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(upload_dir, unique_name)
    
    try:
        # Read file content
        contents = await file.read()
        
        # Save file
        with open(file_path, "wb") as f:
            f.write(contents)
        
        # Return relative path
        return f"/static/uploads/{unique_name}"
    except Exception as e:
        print(f"Error saving file: {e}")
        return None


def get_excerpt(content: str, length: int = 150) -> str:
    """Extract excerpt from content"""
    if not content:
        return ""
    
    # Remove HTML tags
    clean_content = re.sub(r'<[^>]+>', '', content)
    
    if len(clean_content) <= length:
        return clean_content
    
    return clean_content[:length] + "..."


def get_theme_icon(theme: str) -> str:
    """Get theme icon (sun or moon)"""
    light_themes = ["light", "rose-pine-dawn", "catpuccin-latte", "glass"]
    return "☀️" if theme in light_themes else "🌙"
