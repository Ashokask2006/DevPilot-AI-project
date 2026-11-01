from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from app.core.config import settings
from app.services.gemini_service import gemini_service

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="DevPilot AI - Autonomous AI Coding Agent Backend"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "status": "online",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "gemini_configured": settings.is_gemini_configured,
        "model": settings.GEMINI_MODEL
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "gemini_ready": settings.is_gemini_configured
    }


@app.get("/api/v1/ai/status")
def gemini_status():
    """
    Test and report the status of the Google Gemini API connection.
    Safe endpoint that never reveals the raw API key.
    """
    status = gemini_service.test_connection()
    return status


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
