"""API routes for JSON responses"""

from fastapi import APIRouter, Depends, HTTPException, Query, File, UploadFile, Form
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.database import Story, Setting, Category, User, get_db
from app.utils.helpers import slugify, format_date, save_uploaded_file, get_excerpt
from app.utils.security import get_current_user, require_admin_user, generate_csrf_token
from app.schemas.story import StoryCreate, StoryUpdate, StoryListItem, StoryDetail
from app.schemas.settings import Setting as SettingSchema
from app.schemas.category import Category as CategorySchema
from app.config import settings

router = APIRouter(prefix="/api")


@router.get("/stories", response_model=List[StoryListItem])
async def api_get_stories(
    published_only: bool = Query(True),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Get list of stories"""
    offset = (page - 1) * per_page
    
    query = db.query(Story)
    if published_only:
        query = query.filter_by(published=True)
    
    stories = query.order_by(Story.published_at.desc()).offset(offset).limit(per_page).all()
    
    return [
        StoryListItem(
            id=s.id,
            title=s.title,
            slug=s.slug,
            excerpt=s.excerpt,
            author=s.author,
            category=s.category,
            featured_image=s.featured_image,
            published=s.published,
            published_at=format_date(s.published_at) or format_date(s.created_at),
        )
        for s in stories
    ]


@router.get("/stories/{slug}", response_model=StoryDetail)
async def api_get_story(
    slug: str,
    db: Session = Depends(get_db),
):
    """Get single story by slug"""
    story = db.query(Story).filter_by(slug=slug).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    return StoryDetail(
        id=story.id,
        title=story.title,
        slug=story.slug,
        content=story.content,
        excerpt=story.excerpt,
        author=story.author,
        category=story.category,
        featured_image=story.featured_image,
        published=story.published,
        published_at=story.published_at,
        created_at=story.created_at,
        updated_at=story.updated_at,
    )


@router.post("/stories", response_model=StoryDetail)
async def api_create_story(
    story: StoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create new story"""
    # Generate slug
    slug = slugify(story.title)
    
    # Check for duplicate slug
    existing = db.query(Story).filter_by(slug=slug).first()
    if existing:
        slug = f"{slug}-{datetime.now().strftime('%Y%m%d%H%M')}"
    
    db_story = Story(
        title=story.title,
        slug=slug,
        content=story.content,
        excerpt=story.excerpt or get_excerpt(story.content, 150),
        author=story.author or current_user.full_name or current_user.username,
        category=story.category,
        featured_image=story.featured_image,
        published=story.published,
        published_at=datetime.now() if story.published else None,
    )
    
    db.add(db_story)
    db.commit()
    db.refresh(db_story)
    
    return db_story


@router.put("/stories/{story_id}", response_model=StoryDetail)
async def api_update_story(
    story_id: int,
    story: StoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update story"""
    db_story = db.query(Story).filter_by(id=story_id).first()
    if not db_story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    update_data = story.model_dump(exclude_unset=True)
    
    if "title" in update_data:
        db_story.title = update_data["title"]
        if not update_data.get("slug"):
            db_story.slug = slugify(update_data["title"])
    
    if "slug" in update_data:
        db_story.slug = update_data["slug"]
    
    if "content" in update_data:
        db_story.content = update_data["content"]
    
    if "excerpt" in update_data:
        db_story.excerpt = update_data["excerpt"]
    
    if "author" in update_data:
        db_story.author = update_data["author"]
    
    if "category" in update_data:
        db_story.category = update_data["category"]
    
    if "featured_image" in update_data:
        db_story.featured_image = update_data["featured_image"]
    
    if "published" in update_data:
        db_story.published = update_data["published"]
        if update_data["published"]:
            db_story.published_at = datetime.now()
        else:
            db_story.published_at = None
    
    if "published_at" in update_data:
        db_story.published_at = update_data["published_at"]
    
    db_story.updated_at = datetime.now()
    
    db.commit()
    db.refresh(db_story)
    
    return db_story


@router.delete("/stories/{story_id}")
async def api_delete_story(
    story_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete story"""
    db_story = db.query(Story).filter_by(id=story_id).first()
    if not db_story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    db.delete(db_story)
    db.commit()
    
    return {"message": "Story deleted successfully"}


@router.get("/categories", response_model=List[CategorySchema])
async def api_get_categories(db: Session = Depends(get_db)):
    """Get all categories"""
    categories = db.query(Category).order_by(Category.name).all()
    return categories


@router.post("/categories", response_model=CategorySchema)
async def api_create_category(
    category: CategorySchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
):
    """Create new category"""
    db_category = Category(name=category.name)
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category


@router.get("/settings")
async def api_get_settings(db: Session = Depends(get_db)):
    """Get all settings"""
    settings_list = db.query(Setting).all()
    return {s.key: s.value for s in settings_list}


@router.put("/settings/{key}")
async def api_update_setting(
    key: str,
    value: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
):
    """Update setting"""
    db_setting = db.query(Setting).filter_by(key=key).first()
    if db_setting:
        db_setting.value = value
    else:
        db_setting = Setting(key=key, value=value)
        db.add(db_setting)
    
    db.commit()
    db.refresh(db_setting)
    return {"key": key, "value": value}


@router.post("/upload")
async def api_upload_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload file"""
    image_path = await save_uploaded_file(file)
    if not image_path:
        raise HTTPException(status_code=400, detail="Invalid file type")
    
    return {"url": image_path}


@router.get("/csrf-token")
async def api_get_csrf_token():
    """Get CSRF token"""
    return {"csrf_token": generate_csrf_token()}
