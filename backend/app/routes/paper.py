"""Paper (frontend) routes"""

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.database import Story, Setting, Category, get_db
from app.utils.helpers import format_date, get_excerpt
from app.config import settings

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serve React frontend for paper homepage"""
    # In production, serve the built React index.html
    # For development, proxy to Vite
    return RedirectResponse(url="/paper")


@router.get("/paper", response_class=HTMLResponse)
async def paper_home(
    request: Request,
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db),
):
    """Get paper homepage data"""
    # Get site settings
    site_title = db.query(Setting).filter_by(key="site_title").first()
    site_description = db.query(Setting).filter_by(key="site_description").first()
    theme = db.query(Setting).filter_by(key="theme").first()
    font_family = db.query(Setting).filter_by(key="font_family").first()
    
    # Get published stories with pagination
    offset = (page - 1) * 10
    stories = db.query(Story).filter_by(published=True).order_by(Story.published_at.desc()).offset(offset).limit(10).all()
    total_count = db.query(Story).filter_by(published=True).count()
    total_pages = (total_count + 9) // 10
    
    # Format stories
    formatted_stories = []
    for story in stories:
        formatted_stories.append({
            "id": story.id,
            "title": story.title,
            "slug": story.slug,
            "excerpt": story.excerpt or get_excerpt(story.content, 150),
            "author": story.author,
            "category": story.category,
            "featured_image": story.featured_image,
            "published_at": format_date(story.published_at) or format_date(story.created_at),
        })
    
    data = {
        "site_title": site_title.value if site_title else "Scooper Paper",
        "site_description": site_description.value if site_description else "Your News, Delivered",
        "theme": theme.value if theme else "light",
        "font_family": font_family.value if font_family else "serif",
        "stories": formatted_stories,
        "pagination": {
            "current_page": page,
            "total_pages": total_pages,
            "total_count": total_count,
            "has_previous": page > 1,
            "has_next": page < total_pages,
        },
    }
    
    return data


@router.get("/story/{slug}", response_class=HTMLResponse)
async def paper_story(
    request: Request,
    slug: str,
    db: Session = Depends(get_db),
):
    """Get single story data"""
    story = db.query(Story).filter_by(slug=slug, published=True).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    # Get site settings
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
            "excerpt": story.excerpt or get_excerpt(story.content, 150),
            "author": story.author,
            "category": story.category,
            "featured_image": story.featured_image,
            "published_at": format_date(story.published_at) or format_date(story.created_at),
        },
    }
    
    return data


@router.get("/categories")
async def get_categories(db: Session = Depends(get_db)):
    """Get all categories"""
    categories = db.query(Category).order_by(Category.name).all()
    return {"categories": [{"id": c.id, "name": c.name} for c in categories]}


@router.get("/search")
async def search_stories(
    q: str = Query(..., min_length=2),
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db),
):
    """Search stories"""
    from sqlalchemy import or_, text
    
    offset = (page - 1) * 10
    search_pattern = f"%{q}%"
    
    stories = db.query(Story).filter(
        or_(
            Story.title.ilike(search_pattern),
            Story.content.ilike(search_pattern),
            Story.excerpt.ilike(search_pattern),
        ),
        Story.published == True,
    ).order_by(Story.published_at.desc()).offset(offset).limit(10).all()
    
    total_count = db.query(Story).filter(
        or_(
            Story.title.ilike(search_pattern),
            Story.content.ilike(search_pattern),
            Story.excerpt.ilike(search_pattern),
        ),
        Story.published == True,
    ).count()
    
    total_pages = (total_count + 9) // 10
    
    formatted_stories = []
    for story in stories:
        formatted_stories.append({
            "id": story.id,
            "title": story.title,
            "slug": story.slug,
            "excerpt": story.excerpt or get_excerpt(story.content, 150),
            "author": story.author,
            "category": story.category,
            "featured_image": story.featured_image,
            "published_at": format_date(story.published_at) or format_date(story.created_at),
        })
    
    return {
        "query": q,
        "stories": formatted_stories,
        "pagination": {
            "current_page": page,
            "total_pages": total_pages,
            "total_count": total_count,
        },
    }
