from fastapi import APIRouter
from .endpoints import auth, curation, favorites, health, reviews, shops

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(shops.router, prefix="/shops", tags=["Coffee Shops"])
api_router.include_router(reviews.router, prefix="/shops", tags=["Coffee Shop Reviews"])
api_router.include_router(curation.router, prefix="/shops", tags=["Coffee Shop Curation"])
api_router.include_router(favorites.user_favorites_router, prefix="/favorites", tags=["Favorites"])
api_router.include_router(favorites.router, prefix="/shops", tags=["Coffee Shop Favorites"])

