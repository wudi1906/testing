"""
日志配置模块
"""
import sys
import os
from pathlib import Path
from loguru import logger

from app.core.config import settings


def setup_logging():
    """设置日志配置"""
    
    # 移除默认的日志处理器
    logger.remove()
    
    # 创建日志目录
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # 控制台日志格式
    console_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )
    
    # 文件日志格式
    file_format = (
        "{time:YYYY-MM-DD HH:mm:ss} | "
        "{level: <8} | "
        "{name}:{function}:{line} | "
        "{message}"
    )
    
    # 添加控制台处理器
    logger.add(
        sys.stdout,
        format=console_format,
        level=settings.LOG_LEVEL,
        colorize=True,
        backtrace=True,
        diagnose=True
    )
    
    # 添加文件处理器 - 所有日志
    logger.add(
        settings.LOG_FILE,
        format=file_format,
        level="DEBUG",
        rotation=settings.LOG_ROTATION,
        retention=settings.LOG_RETENTION,
        compression="zip",
        backtrace=True,
        diagnose=True
    )
    
    # 添加错误日志文件
    logger.add(
        "logs/error.log",
        format=file_format,
        level="ERROR",
        rotation="1 day",
        retention="30 days",
        compression="zip",
        backtrace=True,
        diagnose=True
    )
    
    # 添加智能体专用日志
    logger.add(
        "logs/agents.log",
        format=file_format,
        level="INFO",
        rotation="1 day",
        retention="7 days",
        filter=lambda record: "agent" in record["name"].lower(),
        backtrace=True,
        diagnose=True
    )
    
    # 添加API请求日志
    logger.add(
        "logs/api.log",
        format=file_format,
        level="INFO",
        rotation="1 day",
        retention="7 days",
        filter=lambda record: "api" in record["name"].lower() or "endpoint" in record["name"].lower(),
        backtrace=True,
        diagnose=True
    )
    
    logger.info("日志系统初始化完成")


def get_logger(name: str):
    """获取指定名称的日志器"""
    return logger.bind(name=name)
