from fastapi import APIRouter

from app.api.v1 import auth, chat, diagnosis, farm_images, farms, health, users


api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(chat.router)
api_router.include_router(diagnosis.router)
api_router.include_router(farm_images.router)
api_router.include_router(farms.router)
api_router.include_router(health.router)
api_router.include_router(users.router)
