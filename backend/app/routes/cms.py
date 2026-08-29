"""CMS routes"""

from fastapi import APIRouter, Depends, HTTPException, Request, Query, File, UploadFile, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.database import Story, Setting, Category, User, get_db
from app.utils.helpers import slugify, format_date, save_uploaded_file, get_excerpt
from app.utils.security import get_current_user, require_admin_user, generate_csrf_token, validate_csrf_token
from app.schemas.story import StoryCreate, StoryUpdate, StoryListItem
from app.schemas.settings import Setting
from app.config import settings

router = APIRouter()
security = HTTPBasic()


@router.get("/", response_class=HTMLResponse)
async def cms_root(request: Request):
    """Redirect to CMS dashboard"""
    return RedirectResponse(url="/cms/dashboard")


@router.get("/dashboard", response_class=HTMLResponse)
async def cms_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get CMS dashboard data"""
    # Get statistics
    total_stories = db.query(Story).count()
    published_count = db.query(Story).filter_by(published=True).count()
    draft_count = db.query(Story).filter_by(published=False).count()
    categories_count = db.query(Category).count()
    
    # Get recent stories
    recent_stories = db.query(Story).order_by(Story.created_at.desc()).limit(5).all()
    
    formatted_recent = []
    for story in recent_stories:
        formatted_recent.append({
            "id": story.id,
            "title": story.title,
            "slug": story.slug,
            "published": story.published,
            "published_at": format_date(story.published_at) or format_date(story.created_at),
        })
    
    # Get site settings
    site_title = db.query(Setting).filter_by(key="site_title").first()
    theme = db.query(Setting).filter_by(key="theme").first()
    font_family = db.query(Setting).filter_by(key="font_family").first()
    
    data = {
        "site_title": site_title.value if site_title else "Scooper Paper",
        "theme": theme.value if theme else "light",
        "font_family": font_family.value if font_family else "serif",
        "stats": {
            "total_stories": total_stories,
            "published_count": published_count,
            "draft_count": draft_count,
            "categories_count": categories_count,
        },
        "recent_stories": formatted_recent,
        "user": {
            "username": current_user.username,
            "full_name": current_user.full_name,
            "is_admin": current_user.is_admin,
        },
    }
    
    return data


@router.get("/stories", response_class=HTMLResponse)
async def cms_stories(
    request: Request,
    page: int = Query(1, ge=1),
    status: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get stories list"""
    from sqlalchemy import or_, and_
    
    offset = (page - 1) * 10
    
    # Build query
    query = db.query(Story)
    
    if status == "published":
        query = query.filter_by(published=True)
    elif status == "draft":
        query = query.filter_by(published=False)
    
    if category:
        query = query.filter_by(category=category)
    
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                Story.title.ilike(search_pattern),
                Story.content.ilike(search_pattern),
                Story.author.ilike(search_pattern),
            )
        )
    
    stories = query.order_by(Story.updated_at.desc()).offset(offset).limit(10).all()
    total_count = query.count()
    total_pages = (total_count + 9) // 10
    
    # Get all categories for filter
    all_categories = db.query(Category).order_by(Category.name).all()
    
    # Get site settings
    site_title = db.query(Setting).filter_by(key="site_title").first()
    theme = db.query(Setting).filter_by(key="theme").first()
    
    formatted_stories = []
    for story in stories:
        formatted_stories.append({
            "id": story.id,
            "title": story.title,
            "slug": story.slug,
            "author": story.author,
            "category": story.category,
            "published": story.published,
            "featured_image": story.featured_image,
            "published_at": format_date(story.published_at) or format_date(story.created_at),
            "updated_at": format_date(story.updated_at),
        })
    
    data = {
        "site_title": site_title.value if site_title else "Scooper Paper",
        "theme": theme.value if theme else "light",
        "stories": formatted_stories,
        "pagination": {
            "current_page": page,
            "total_pages": total_pages,
            "total_count": total_count,
            "has_previous": page > 1,
            "has_next": page < total_pages,
        },
        "filters": {
            "status": status,
            "category": category,
            "search": search,
        },
        "categories": [{"id": c.id, "name": c.name} for c in all_categories],
        "user": {
            "username": current_user.username,
            "is_admin": current_user.is_admin,
        },
    }
    
    return data


@router.get("/create", response_class=HTMLResponse)
async def cms_create(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get create story form"""
    categories = db.query(Category).order_by(Category.name).all()
    
    site_title = db.query(Setting).filter_by(key="site_title").first()
    theme = db.query(Setting).filter_by(key="theme").first()
    
    csrf_token = generate_csrf_token()
    
    data = {
        "site_title": site_title.value if site_title else "Scooper Paper",
        "theme": theme.value if theme else "light",
        "categories": [{"id": c.id, "name": c.name} for c in categories],
        "user": {
            "username": current_user.username,
            "full_name": current_user.full_name,
            "is_admin": current_user.is_admin,
        },
        "csrf_token": csrf_token,
    }
    
    return data


@router.post("/create")
async def cms_create_story(
    request: Request,
    title: str = Form(...),
    content: str = Form(...),
    excerpt: Optional[str] = Form(None),
    author: Optional[str] = Form(None),
    category: str = Form(...),
    featured_image: Optional[UploadFile] = File(None),
    published: bool = Form(False),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create new story"""
    # Validate CSRF
    # In production, store CSRF token in session or cookie
    # For now, we'll skip strict validation in API mode
    
    # Generate slug
    slug = slugify(title)
    
    # Check for duplicate slug
    existing = db.query(Story).filter_by(slug=slug).first()
    if existing:
        slug = f"{slug}-{datetime.now().strftime('%Y%m%d%H%M')}"
    
    # Handle featured image upload
    image_path = None
    if featured_image:
        image_path = await save_uploaded_file(featured_image)
    
    # Create story
    story = Story(
        title=title,
        slug=slug,
        content=content,
        excerpt=excerpt or get_excerpt(content, 150),
        author=author or current_user.full_name or current_user.username,
        category=category,
        featured_image=image_path,
        published=published,
        published_at=datetime.now() if published else None,
    )
    
    db.add(story)
    db.commit()
    db.refresh(story)
    
    return {
        "success": True,
        "message": "Story created successfully",
        "story": {
            "id": story.id,
            "slug": story.slug,
        },
    }


@router.get("/edit/{story_id}", response_class=HTMLResponse)
async def cms_edit(
    request: Request,
    story_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get edit story form"""
    story = db.query(Story).filter_by(id=story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    categories = db.query(Category).order_by(Category.name).all()
    
    site_title = db.query(Setting).filter_by(key="site_title").first()
    theme = db.query(Setting).filter_by(key="theme").first()
    
    csrf_token = generate_csrf_token()
    
    data = {
        "site_title": site_title.value if site_title else "Scooper Paper",
        "theme": theme.value if theme else "light",
        "story": {
            "id": story.id,
            "title": story.title,
            "slug": story.slug,
            "content": story.content,
            "excerpt": story.excerpt,
            "author": story.author,
            "category": story.category,
            "featured_image": story.featured_image,
            "published": story.published,
            "published_at": format_date(story.published_at),
        },
        "categories": [{"id": c.id, "name": c.name} for c in categories],
        "user": {
            "username": current_user.username,
            "full_name": current_user.full_name,
            "is_admin": current_user.is_admin,
        },
        "csrf_token": csrf_token,
    }
    
    return data


@router.post("/edit/{story_id}")
async def cms_update_story(
    request: Request,
    story_id: int,
    title: str = Form(...),
    content: str = Form(...),
    excerpt: Optional[str] = Form(None),
    author: Optional[str] = Form(None),
    category: str = Form(...),
    featured_image: Optional[UploadFile] = File(None),
    published: bool = Form(False),
    publish_now: bool = Form(False),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update story"""
    story = db.query(Story).filter_by(id=story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    # Update fields
    story.title = title
    story.content = content
    story.excerpt = excerpt or get_excerpt(content, 150)
    story.author = author or current_user.full_name or current_user.username
    story.category = category
    story.published = published
    
    # Handle featured image upload
    if featured_image:
        image_path = await save_uploaded_file(featured_image)
        if image_path:
            story.featured_image = image_path
    
    # Handle publish now
    if publish_now and not story.published:
        story.published = True
        story.published_at = datetime.now()
    elif not published:
        story.published = False
        story.published_at = None
    
    story.updated_at = datetime.now()
    
    db.commit()
    db.refresh(story)
    
    return {
        "success": True,
        "message": "Story updated successfully",
        "story": {
            "id": story.id,
            "slug": story.slug,
            "published": story.published,
        },
    }


@router.post("/delete/{story_id}")
async def cms_delete_story(
    request: Request,
    story_id: int,
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete story"""
    story = db.query(Story).filter_by(id=story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    db.delete(story)
    db.commit()
    
    return {
        "success": True,
        "message": "Story deleted successfully",
    }


@router.get("/settings", response_class=HTMLResponse)
async def cms_settings(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get settings page"""
    settings_list = db.query(Setting).all()
    
    site_title = db.query(Setting).filter_by(key="site_title").first()
    theme = db.query(Setting).filter_by(key="theme").first()
    
    csrf_token = generate_csrf_token()
    
    settings_data = {}
    for s in settings_list:
        settings_data[s.key] = s.value
    
    data = {
        "site_title": site_title.value if site_title else "Scooper Paper",
        "theme": theme.value if theme else "light",
        "settings": settings_data,
        "user": {
            "username": current_user.username,
            "full_name": current_user.full_name,
            "is_admin": current_user.is_admin,
        },
        "csrf_token": csrf_token,
    }
    
    return data


@router.post("/settings")
async def cms_update_settings(
    request: Request,
    site_title: str = Form(...),
    site_description: str = Form(...),
    theme: str = Form(...),
    font_family: str = Form(...),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update site settings"""
    # Update settings
    db.query(Setting).filter_by(key="site_title").update({"value": site_title})
    db.query(Setting).filter_by(key="site_description").update({"value": site_description})
    db.query(Setting).filter_by(key="theme").update({"value": theme})
    db.query(Setting).filter_by(key="font_family").update({"value": font_family})
    
    # Insert if not exists
    if not db.query(Setting).filter_by(key="site_title").first():
        db.add(Setting(key="site_title", value=site_title))
    if not db.query(Setting).filter_by(key="site_description").first():
        db.add(Setting(key="site_description", value=site_description))
    if not db.query(Setting).filter_by(key="theme").first():
        db.add(Setting(key="theme", value=theme))
    if not db.query(Setting).filter_by(key="font_family").first():
        db.add(Setting(key="font_family", value=font_family))
    
    db.commit()
    
    return {
        "success": True,
        "message": "Settings updated successfully",
    }


@router.post("/preview/{story_id}", response_class=HTMLResponse)
async def cms_preview_story(
    request: Request,
    story_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Preview story"""
    story = db.query(Story).filter_by(id=story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    site_title = db.query(Setting).filter_by(key="site_title").first()
    theme = db.query(Setting).filter_by(key="theme").first()
    font_family = db.query(Setting).filter_by(key="font_family").first()
    
    data = {
        "site_title": site_title.value if site_title else "Scooper Paper",
        "theme": theme.value if theme else "light",
        "font_family": font_family.value if font_family else "serif",
        "story": {
            "id": story.id,
            "title": story.title,
            "slug": story.slug,
            "content": story.content,
            "excerpt": story.excerpt,
            "author": story.author,
            "category": story.category,
            "featured_image": story.featured_image,
            "published_at": format_date(story.published_at) or format_date(story.created_at),
        },
        "is_preview": True,
    }
    
    return data
