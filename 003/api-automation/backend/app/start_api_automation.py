#!/usr/bin/env python3
"""
接口自动化智能体系统启动脚本
"""
import asyncio
import uvicorn
from pathlib import Path

from loguru import logger


def setup_directories():
    """创建必要的目录"""
    directories = [
        "./uploads",
        "./reports", 
        "./reports/allure-results",
        "./reports/allure-report",
        "./logs",
        "./generated_tests",
        "./generated_tests/tests",
        "./generated_tests/tests/api",
        "./generated_tests/tests/data",
        "./generated_tests/tests/config",
        "./generated_tests/tests/utils"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        logger.info(f"创建目录: {directory}")


def setup_logging():
    """配置日志"""
    logger.add(
        "./logs/api_automation_{time:YYYY-MM-DD}.log",
        rotation="1 day",
        retention="30 days",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}"
    )
    logger.info("日志配置完成")


async def test_system():
    """测试系统基本功能"""
    try:
        logger.info("开始系统功能测试...")
        
        # 测试智能体工厂
        from app.agents.factory import agent_factory
        
        logger.info("测试智能体工厂...")
        factory_status = agent_factory.get_factory_status()
        logger.info(f"工厂状态: {factory_status}")
        
        # 测试编排器
        from app.services.api_automation import ApiAutomationOrchestrator
        
        logger.info("测试编排器...")
        orchestrator = ApiAutomationOrchestrator()
        await orchestrator.initialize()
        
        metrics = await orchestrator.get_orchestrator_metrics()
        logger.info(f"编排器指标: {metrics}")
        
        await orchestrator.cleanup()
        
        logger.info("✅ 系统功能测试完成")
        
    except Exception as e:
        logger.error(f"❌ 系统功能测试失败: {str(e)}")
        raise


def main():
    """主函数"""
    logger.info("🚀 启动接口自动化智能体系统")
    
    # 设置目录
    setup_directories()
    
    # 设置日志
    setup_logging()
    
    # 测试系统
    try:
        asyncio.run(test_system())
    except Exception as e:
        logger.error(f"系统测试失败: {str(e)}")
        return
    
    # 启动FastAPI服务器
    logger.info("🌐 启动FastAPI服务器...")
    
    uvicorn.run(
        "run:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
        access_log=True
    )


if __name__ == "__main__":
    main()
