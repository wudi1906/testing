#!/usr/bin/env python3
"""
AI模型测试启动脚本
快速验证所有配置的AI模型是否可用
"""
import sys
import os
import asyncio
from pathlib import Path

# 添加项目路径
current_dir = Path(__file__).parent.absolute()
backend_dir = current_dir / "backend"
sys.path.insert(0, str(backend_dir))

from app.tests.test_ai_models import run_ai_model_tests
from loguru import logger

def setup_logging():
    """设置日志配置"""
    logger.remove()  # 移除默认handler
    logger.add(
        sys.stdout,
        level="INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
        colorize=True
    )

async def main():
    """主函数"""
    setup_logging()
    
    logger.info("🚀 启动AI模型可用性测试...")
    logger.info(f"📂 项目目录: {current_dir}")
    
    try:
        # 运行测试
        results = await run_ai_model_tests()
        
        # 统计结果
        total_models = len(results)
        successful_count = sum(1 for r in results.values() if r["success"])
        failed_count = total_models - successful_count
        
        logger.info(f"\n📊 测试完成统计:")
        logger.info(f"   总模型数: {total_models}")
        logger.info(f"   成功: {successful_count} 个")
        logger.info(f"   失败: {failed_count} 个")
        logger.info(f"   成功率: {(successful_count/total_models*100):.1f}%")
        
        if successful_count > 0:
            logger.info("\n🎉 系统可以正常运行！")
            return True
        else:
            logger.error("\n⚠️ 所有模型都不可用，请检查API密钥配置！")
            return False
            
    except Exception as e:
        logger.error(f"❌ 测试过程中发生错误: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
