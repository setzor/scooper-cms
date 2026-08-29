"""Story schemas"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime


class StoryBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    title: str
    slug: Optional[str] = None
    content: str
    excerpt: Optional[str] = None
    author: str = "Admin"
    category: str = "General"
    featured_image: Optional[str] = None
    published: bool = False


class StoryCreate(StoryBase):
    pass


class StoryUpdate(BaseModel):
    title: Optional[str] = None
    slug: Optional[str] = None
    content: Optional[str] = None
    excerpt: Optional[str] = None
    author: Optional[str] = None
    category: Optional[str] = None
    featured_image: Optional[str] = None
    published: Optional[bool] = None
    published_at: Optional[datetime] = None


class Story(StoryBase):
    id: int
    published_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class StoryListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    title: str
    slug: str
    excerpt: Optional[str] = None
    author: str
    category: str
    featured_image: Optional[str] = None
    published: bool
    published_at: Optional[str] = None


class StoryDetail(Story):
    pass
