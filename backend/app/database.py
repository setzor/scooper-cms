"""Database configuration and models"""

from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, func
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from app.config import settings
import os

# Create engine
SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False} if "sqlite" in SQLALCHEMY_DATABASE_URL else {},
    echo=settings.DEBUG,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Models
class Story(Base):
    """Story model for news articles"""
    __tablename__ = "stories"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    slug = Column(String(200), unique=True, index=True, nullable=False)
    content = Column(Text, nullable=False)
    excerpt = Column(Text)
    author = Column(String(100), default="Admin")
    category = Column(String(100), default="General")
    featured_image = Column(String(500))
    published = Column(Boolean, default=False)
    published_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Setting(Base):
    """Site settings model"""
    __tablename__ = "settings"
    
    key = Column(String(100), primary_key=True, index=True)
    value = Column(Text)


class Category(Base):
    """Category model"""
    __tablename__ = "categories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class User(Base):
    """User model for CMS authentication"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(200))
    email = Column(String(200))
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())


def init_db():
    """Initialize database with default data"""
    from sqlalchemy.orm import Session
    
    db = Session(engine)
    
    # Check if settings exist
    if not db.query(Setting).filter_by(key="site_title").first():
        db.add(Setting(key="site_title", value="Scooper Paper"))
        db.add(Setting(key="site_description", value="Your News, Delivered"))
        db.add(Setting(key="theme", value="light"))
        db.add(Setting(key="font_family", value="serif"))
    
    # Check if default categories exist
    categories = ["General", "Local News", "Technology", "Business", "Sports", "Entertainment", "Announcement"]
    for cat in categories:
        if not db.query(Category).filter_by(name=cat).first():
            db.add(Category(name=cat))
    
    # Check if admin user exists
    if not db.query(User).filter_by(username=settings.CMS_USERNAME).first():
        from app.utils.security import get_password_hash
        # Ensure password is not too long for bcrypt
        password = settings.CMS_PASSWORD[:72] if len(settings.CMS_PASSWORD) > 72 else settings.CMS_PASSWORD
        hashed_password = get_password_hash(password)
        db.add(User(
            username=settings.CMS_USERNAME,
            password_hash=hashed_password,
            full_name="Administrator",
            is_admin=True,
        ))
    
    db.commit()
    db.close()
