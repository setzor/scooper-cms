"""Main FastAPI application for Scooper CMS"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.database import Base, engine, init_db
from app.routes import paper, cms, api
from app.config import settings

# Create database tables
Base.metadata.create_all(bind=engine)
init_db()

app = FastAPI(
    title="Scooper CMS API",
    description="Modern CMS API for Scooper News Platform",
    version="1.0.0",
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url="/api/redoc" if settings.DEBUG else None,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000"] + settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(api.router, prefix="/api")
app.include_router(paper.router, prefix="")
app.include_router(cms.router, prefix="/cms")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}
