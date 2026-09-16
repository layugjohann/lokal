from fastapi import APIRouter
from .endpoints import auth, health, reviews, shops

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(shops.router, prefix="/shops", tags=["Coffee Shops"])
api_router.include_router(reviews.router, prefix="/shops", tags=["Coffee Shop Reviews"])

