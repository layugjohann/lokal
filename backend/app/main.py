from fastapi import FastAPI
from .api.v1.router import api_router
from .core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API for LOKAL coffee shop discovery platform",
    version="0.1.0",
)

# Include API v1 router (includes /health)
app.include_router(api_router, prefix="/api/v1")


# Direct /health endpoint for convenience
@app.get("/health", summary="Health Check", tags=["Health"])
async def health_check():
    """Return operational status of the FastAPI backend."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
