from fastapi import APIRouter

from app.api.v1 import auth, chat, diagnosis, escalations, farm_images, farms, health, users
from app.api.v1 import intelligence, knowledge, news
from app.api.v1 import notifications
from app.api.v1 import recommendations
from app.api.v1 import stage_advisory
from app.api.v1 import timeline
from app.api.v1 import weather


api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(chat.router)
api_router.include_router(diagnosis.router)
api_router.include_router(escalations.router)
api_router.include_router(farm_images.router)
api_router.include_router(farms.router)
api_router.include_router(health.router)
api_router.include_router(intelligence.router)
api_router.include_router(knowledge.router)
api_router.include_router(news.router)
api_router.include_router(notifications.router)
api_router.include_router(recommendations.router)
api_router.include_router(stage_advisory.router)
api_router.include_router(timeline.router)
api_router.include_router(users.router)
api_router.include_router(weather.router)
