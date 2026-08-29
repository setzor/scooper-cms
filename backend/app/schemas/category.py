"""Category schemas"""

from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class CategoryBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    name: str


class CategoryCreate(CategoryBase):
    pass


class Category(CategoryBase):
    id: int
    created_at: datetime
