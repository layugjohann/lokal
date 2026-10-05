from fastapi import APIRouter
from .endpoints import auth, claims, curation, favorites, health, owner, recommendations, reviews, shops

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(recommendations.router, prefix="/shops/recommendations", tags=["Personalized Recommendations"])
api_router.include_router(shops.router, prefix="/shops", tags=["Coffee Shops"])
api_router.include_router(reviews.router, prefix="/shops", tags=["Coffee Shop Reviews"])
api_router.include_router(curation.router, prefix="/shops", tags=["Coffee Shop Curation"])
api_router.include_router(favorites.user_favorites_router, prefix="/favorites", tags=["Favorites"])
api_router.include_router(favorites.router, prefix="/shops", tags=["Coffee Shop Favorites"])
api_router.include_router(claims.claims_router, prefix="/claims", tags=["Ownership Claims"])
api_router.include_router(claims.shop_claims_router, prefix="/shops", tags=["Coffee Shop Claims"])
api_router.include_router(owner.router, prefix="/owner/shops", tags=["Coffee Shop Owner Dashboard"])



