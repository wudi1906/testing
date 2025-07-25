"""
数据库初始化脚本
用于创建API自动化相关的数据库表和初始数据
"""
import asyncio
from pathlib import Path
from loguru import logger
from tortoise import Tortoise

from app.core.config import settings
from app.models.api_automation import (
    AgentLog, LogAnalysis, TestScript, AlertRule, Alert,
    ApiDocument, ApiEndpoint, TestCase, TestResult, TestExecution
)


async def init_database():
    """初始化数据库"""
    try:
        # 初始化Tortoise ORM
        await Tortoise.init(
            db_url=settings.DATABASE_URL,
            modules={'models': ['app.models.api_automation']}
        )
        
        # 生成数据库表
        await Tortoise.generate_schemas()
        
        logger.info("数据库表创建成功")
        
        # 创建默认告警规则
        await create_default_alert_rules()
        
        logger.info("数据库初始化完成")
        
    except Exception as e:
        logger.error(f"数据库初始化失败: {str(e)}")
        raise
    finally:
        await Tortoise.close_connections()


async def create_default_alert_rules():
    """创建默认告警规则"""
    try:
        default_rules = [
            {
                "rule_id": "default-error-rate",
                "name": "错误率告警",
                "description": "当错误率超过5%时触发告警",
                "rule_type": "ERROR_RATE",
                "threshold_value": 5.0,
                "comparison_operator": ">",
                "time_window": 10,
                "severity": "HIGH"
            },
            {
                "rule_id": "default-response-time",
                "name": "响应时间告警", 
                "description": "当平均响应时间超过5秒时触发告警",
                "rule_type": "RESPONSE_TIME",
                "threshold_value": 5.0,
                "comparison_operator": ">",
                "time_window": 5,
                "severity": "MEDIUM"
            },
            {
                "rule_id": "default-memory-usage",
                "name": "内存使用告警",
                "description": "当内存使用率超过80%时触发告警", 
                "rule_type": "MEMORY_USAGE",
                "threshold_value": 80.0,
                "comparison_operator": ">",
                "time_window": 5,
                "severity": "HIGH"
            },
            {
                "rule_id": "default-cpu-usage",
                "name": "CPU使用告警",
                "description": "当CPU使用率超过90%时触发告警",
                "rule_type": "CPU_USAGE", 
                "threshold_value": 90.0,
                "comparison_operator": ">",
                "time_window": 5,
                "severity": "CRITICAL"
            }
        ]
        
        for rule_data in default_rules:
            # 检查规则是否已存在
            existing_rule = await AlertRule.filter(rule_id=rule_data["rule_id"]).first()
            if not existing_rule:
                await AlertRule.create(**rule_data)
                logger.info(f"创建默认告警规则: {rule_data['name']}")
            else:
                logger.info(f"告警规则已存在: {rule_data['name']}")
                
    except Exception as e:
        logger.error(f"创建默认告警规则失败: {str(e)}")
        raise


async def drop_all_tables():
    """删除所有表（谨慎使用）"""
    try:
        await Tortoise.init(
            db_url=settings.DATABASE_URL,
            modules={'models': ['app.models.api_automation']}
        )
        
        # 删除所有表
        await Tortoise.generate_schemas(safe=False)
        
        logger.warning("所有数据库表已删除")
        
    except Exception as e:
        logger.error(f"删除数据库表失败: {str(e)}")
        raise
    finally:
        await Tortoise.close_connections()


async def reset_database():
    """重置数据库（删除并重新创建）"""
    try:
        logger.warning("开始重置数据库...")
        
        # 删除所有表
        await drop_all_tables()
        
        # 重新初始化
        await init_database()
        
        logger.info("数据库重置完成")
        
    except Exception as e:
        logger.error(f"数据库重置失败: {str(e)}")
        raise


async def check_database_connection():
    """检查数据库连接"""
    try:
        await Tortoise.init(
            db_url=settings.DATABASE_URL,
            modules={'models': ['app.models.api_automation']}
        )
        
        # 执行简单查询测试连接
        await AgentLog.all().limit(1)
        
        logger.info("数据库连接正常")
        return True
        
    except Exception as e:
        logger.error(f"数据库连接失败: {str(e)}")
        return False
    finally:
        await Tortoise.close_connections()


async def get_database_stats():
    """获取数据库统计信息"""
    try:
        await Tortoise.init(
            db_url=settings.DATABASE_URL,
            modules={'models': ['app.models.api_automation']}
        )
        
        stats = {
            "agent_logs": await AgentLog.all().count(),
            "log_analyses": await LogAnalysis.all().count(),
            "test_scripts": await TestScript.all().count(),
            "alert_rules": await AlertRule.all().count(),
            "alerts": await Alert.all().count(),
            "api_documents": await ApiDocument.all().count(),
            "api_endpoints": await ApiEndpoint.all().count(),
            "test_cases": await TestCase.all().count(),
            "test_results": await TestResult.all().count()
        }
        
        logger.info(f"数据库统计: {stats}")
        return stats
        
    except Exception as e:
        logger.error(f"获取数据库统计失败: {str(e)}")
        return {}
    finally:
        await Tortoise.close_connections()


async def cleanup_old_data(days: int = 30):
    """清理旧数据"""
    try:
        from datetime import datetime, timedelta
        
        await Tortoise.init(
            db_url=settings.DATABASE_URL,
            modules={'models': ['app.models.api_automation']}
        )
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # 清理旧日志
        deleted_logs = await AgentLog.filter(created_at__lt=cutoff_date).delete()
        logger.info(f"清理了 {deleted_logs} 条旧日志")
        
        # 清理旧分析结果
        deleted_analyses = await LogAnalysis.filter(created_at__lt=cutoff_date).delete()
        logger.info(f"清理了 {deleted_analyses} 条旧分析结果")
        
        # 清理已解决的旧告警
        deleted_alerts = await Alert.filter(
            status="RESOLVED",
            resolved_at__lt=cutoff_date
        ).delete()
        logger.info(f"清理了 {deleted_alerts} 条已解决的旧告警")
        
        return {
            "deleted_logs": deleted_logs,
            "deleted_analyses": deleted_analyses, 
            "deleted_alerts": deleted_alerts
        }
        
    except Exception as e:
        logger.error(f"清理旧数据失败: {str(e)}")
        return {}
    finally:
        await Tortoise.close_connections()


async def backup_database(backup_path: str):
    """备份数据库（导出为JSON）"""
    try:
        await Tortoise.init(
            db_url=settings.DATABASE_URL,
            modules={'models': ['app.models.api_automation']}
        )
        
        import json
        from datetime import datetime
        
        backup_data = {
            "backup_time": datetime.utcnow().isoformat(),
            "agent_logs": [],
            "log_analyses": [],
            "test_scripts": [],
            "alert_rules": [],
            "alerts": []
        }
        
        # 导出各表数据
        for log in await AgentLog.all():
            backup_data["agent_logs"].append({
                "log_id": log.log_id,
                "session_id": log.session_id,
                "agent_type": log.agent_type,
                "agent_name": log.agent_name,
                "log_level": log.log_level,
                "log_message": log.log_message,
                "log_data": log.log_data,
                "timestamp": log.timestamp.isoformat(),
                "created_at": log.created_at.isoformat()
            })
        
        # 保存备份文件
        backup_file = Path(backup_path)
        backup_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"数据库备份完成: {backup_path}")
        return True
        
    except Exception as e:
        logger.error(f"数据库备份失败: {str(e)}")
        return False
    finally:
        await Tortoise.close_connections()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "init":
            asyncio.run(init_database())
        elif command == "reset":
            asyncio.run(reset_database())
        elif command == "check":
            asyncio.run(check_database_connection())
        elif command == "stats":
            asyncio.run(get_database_stats())
        elif command == "cleanup":
            days = int(sys.argv[2]) if len(sys.argv) > 2 else 30
            asyncio.run(cleanup_old_data(days))
        elif command == "backup":
            backup_path = sys.argv[2] if len(sys.argv) > 2 else f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            asyncio.run(backup_database(backup_path))
        else:
            print("可用命令: init, reset, check, stats, cleanup, backup")
    else:
        print("用法: python init_db.py <command>")
        print("命令:")
        print("  init    - 初始化数据库")
        print("  reset   - 重置数据库")
        print("  check   - 检查数据库连接")
        print("  stats   - 获取数据库统计")
        print("  cleanup - 清理旧数据")
        print("  backup  - 备份数据库")
