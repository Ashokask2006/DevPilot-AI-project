import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn

from app.core.config import settings
from app.services.gemini_service import gemini_service
from app.api.router import api_router
from app.database.init_db import init_db

# Ensure database tables exist
init_db()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="DevPilot AI - Autonomous AI Coding Agent"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount REST API Router
app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "gemini_ready": settings.is_gemini_configured,
        "model": settings.GEMINI_MODEL
    }


@app.get("/api/v1/ai/status")
def gemini_status():
    """
    Test and report status of Google Gemini API connection securely.
    """
    return gemini_service.test_connection()


# Serve UI Static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/")
    def serve_dashboard():
        return FileResponse(os.path.join(static_dir, "index.html"))


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
