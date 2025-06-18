"""
UI自动化测试系统主应用
FastAPI应用入口
"""
import asyncio
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger
import uvicorn

from app.core.config import settings
from app.api.v1.api import api_router
from app.core.logging import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    logger.info("🚀 UI自动化测试系统启动中...")

    # 设置日志
    setup_logging()

    # 确保目录结构
    from app.utils import ensure_directories
    ensure_directories()

    # 验证配置
    await validate_system_config()

    # 初始化数据库连接
    await init_databases()

    # 预热AI模型
    await warmup_ai_models()

    logger.info("✅ 系统启动完成")
    
    yield
    
    # 关闭时执行
    logger.info("🔄 系统关闭中...")
    
    # 清理资源
    await cleanup_resources()
    
    logger.info("✅ 系统关闭完成")


# 创建FastAPI应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="基于多模态大模型与多智能体协作的自动化测试系统",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan
)

# 添加中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

# 包含API路由
app.include_router(api_router, prefix=settings.API_V1_STR)

# 静态文件服务（确保目录存在）
from pathlib import Path
static_dir = Path("static")
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "UI自动化测试系统",
        "version": settings.APP_VERSION,
        "docs": f"{settings.API_V1_STR}/docs",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    try:
        # 检查系统状态
        system_status = await check_system_health()
        
        return {
            "status": "healthy" if system_status["overall"] else "unhealthy",
            "timestamp": system_status["timestamp"],
            "components": system_status["components"],
            "version": settings.APP_VERSION
        }
    except Exception as e:
        logger.error(f"健康检查失败: {str(e)}")
        raise HTTPException(status_code=503, detail="系统不健康")


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """全局异常处理"""
    logger.error(f"未处理的异常: {str(exc)}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "内部服务器错误",
            "message": str(exc) if settings.DEBUG else "系统发生错误，请稍后重试",
            "type": type(exc).__name__
        }
    )


async def validate_system_config():
    """验证系统配置"""
    try:
        logger.info("验证系统配置...")
        
        # 验证AI模型配置
        from app.core.llms import get_model_config_status
        model_config = get_model_config_status()

        if not any(model_config.values()):
            logger.warning("⚠️  没有配置任何AI模型API密钥")
        else:
            logger.info(f"✅ AI模型配置: {model_config}")

        
        logger.info("✅ 多模态服务验证完成")
        
    except Exception as e:
        logger.error(f"配置验证失败: {str(e)}")
        raise


async def init_databases():
    """初始化数据库连接"""
    try:
        logger.info("初始化数据库连接...")

        # 初始化主数据库（MySQL/PostgreSQL）
        from app.core.database_startup import app_database_manager
        database_initialized = await app_database_manager.startup()

        if database_initialized:
            logger.info("✅ 主数据库连接初始化完成")
        else:
            logger.warning("⚠️ 主数据库初始化失败，将使用文件存储")

        # TODO: 初始化Neo4j连接
        # TODO: 初始化Milvus连接
        # TODO: 初始化Redis连接

        logger.info("✅ 数据库连接初始化完成")

    except Exception as e:
        logger.error(f"数据库初始化失败: {str(e)}")
        # 非关键错误，不阻止启动
        pass


async def warmup_ai_models():
    """预热AI模型"""
    try:
        logger.info("预热AI模型...")
        
        # 预热LLM客户端
        from app.core.llms import get_deepseek_model_client, get_uitars_model_client
        from autogen_core.models import UserMessage
        llm_client = get_deepseek_model_client()
        get_uitars_model_client()
        # 发送一个简单的测试请求
        # await llm_client.create(
        #     [UserMessage(content="Hello, this is a warmup test.", source="user")])

        logger.info("✅ AI模型预热完成")
        
    except Exception as e:
        logger.warning(f"AI模型预热失败: {str(e)}")
        # 非关键错误，不阻止启动
        pass


async def check_system_health() -> Dict[str, Any]:
    """检查系统健康状态"""
    from datetime import datetime
    
    components = {}
    overall_healthy = True
    
    # 检查AI模型
    try:
        from app.core.llms import get_deepseek_model_client
        get_deepseek_model_client()
        components["llm"] = {"status": "healthy", "message": "LLM客户端正常"}
    except Exception as e:
        components["llm"] = {"status": "unhealthy", "message": str(e)}
        overall_healthy = False
    
    # 检查多模态模型
    try:
        from app.core.llms import get_uitars_model_client
        get_uitars_model_client()
        components["multimodal"] = {"status": "healthy", "message": "多模态客户端正常"}
    except Exception as e:
        components["multimodal"] = {"status": "unhealthy", "message": str(e)}
        overall_healthy = False
    
    # 检查数据库连接
    try:
        from app.core.database_startup import app_database_manager
        db_healthy = await app_database_manager.health_check()
        db_status = app_database_manager.get_status()

        if db_healthy:
            components["database"] = {"status": "healthy", "message": "数据库连接正常"}
        else:
            components["database"] = {"status": "unhealthy", "message": db_status.get("message", "数据库连接异常")}
            overall_healthy = False
    except Exception as e:
        components["database"] = {"status": "error", "message": f"数据库检查失败: {str(e)}"}
        overall_healthy = False
    
    return {
        "overall": overall_healthy,
        "timestamp": datetime.now().isoformat(),
        "components": components
    }


async def cleanup_resources():
    """清理资源"""
    try:
        # 清理数据库连接
        from app.core.database_startup import app_database_manager
        await app_database_manager.shutdown()

        # 清理AI模型客户端
        from app.core.llms import get_uitars_model_client,get_deepseek_model_client
        uitars_client = get_uitars_model_client()
        deepseek_client = get_deepseek_model_client()
        await deepseek_client.close()
        await uitars_client.close()

        logger.info("✅ 资源清理完成")

    except Exception as e:
        logger.error(f"资源清理失败: {str(e)}")


if __name__ == "__main__":
    # 开发环境直接运行
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD,
        log_level=settings.LOG_LEVEL.lower()
    )
