"""
Aerich数据库迁移配置
"""
from app.core.config import settings

TORTOISE_ORM = {
    "connections": {"default": settings.DATABASE_URL},
    "apps": {
        "models": {
            "models": ["app.models.api_automation", "aerich.models"],
            "default_connection": "default",
        }
    },
}
