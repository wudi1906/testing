from contextlib import asynccontextmanager

from fastapi import FastAPI
from tortoise import Tortoise

from app.core.exceptions import SettingNotFound
from app.core.init_app import (
    init_data,
    make_middlewares,
    register_exceptions,
    register_routers,
)

try:
    from app.settings.config import settings
except ImportError:
    raise SettingNotFound("Can not import settings")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 初始化数据库和基础数据
    await init_data()

    # 初始化API自动化编排器
    try:
        from app.api.v1.endpoints.api_automation import initialize_orchestrator
        await initialize_orchestrator()
    except Exception as e:
        from loguru import logger
        logger.error(f"初始化API自动化编排器失败: {str(e)}")
        # 不阻止应用启动，但记录错误

    yield
    await Tortoise.close_connections()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_TITLE,
        description=settings.APP_DESCRIPTION,
        version=settings.VERSION,
        openapi_url="/openapi.json",
        middleware=make_middlewares(),
        lifespan=lifespan,
    )
    register_exceptions(app)
    register_routers(app, prefix="/api")
    return app


app = create_app()
