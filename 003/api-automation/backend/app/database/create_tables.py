"""
创建API自动化数据库表结构
优化版本 - 支持完整的前端功能
"""
import asyncio
from pathlib import Path
from loguru import logger
from tortoise import Tortoise

from app.core.config import settings


async def create_api_automation_tables():
    """创建API自动化相关表"""
    try:
        # 初始化Tortoise ORM
        await Tortoise.init(
            db_url=settings.DATABASE_URL,
            modules={'models': ['app.models.api_automation', 'app.models.admin']}
        )
        
        # 生成数据库表
        await Tortoise.generate_schemas()
        
        logger.info("API自动化数据库表创建成功")
        
        # 创建索引
        await create_custom_indexes()
        
        # 插入初始数据
        await insert_initial_data()
        
        logger.info("数据库初始化完成")
        
    except Exception as e:
        logger.error(f"数据库表创建失败: {str(e)}")
        raise
    finally:
        await Tortoise.close_connections()


async def create_custom_indexes():
    """创建自定义索引"""
    try:
        from tortoise import connections
        
        db = connections.get("default")
        
        # 创建复合索引
        indexes = [
            # API文档表索引
            "CREATE INDEX IF NOT EXISTS idx_api_documents_status_time ON api_documents(parse_status, created_at)",
            "CREATE INDEX IF NOT EXISTS idx_api_documents_user_active ON api_documents(uploaded_by, is_active)",
            "CREATE INDEX IF NOT EXISTS idx_api_documents_format_status ON api_documents(doc_format, parse_status)",
            
            # API端点表索引
            "CREATE INDEX IF NOT EXISTS idx_api_endpoints_path_method ON api_endpoints(path, method)",
            "CREATE INDEX IF NOT EXISTS idx_api_endpoints_complexity ON api_endpoints(complexity_score, security_level)",
            "CREATE INDEX IF NOT EXISTS idx_api_endpoints_test_stats ON api_endpoints(test_success_rate, last_test_time)",
            
            # 测试用例表索引
            "CREATE INDEX IF NOT EXISTS idx_test_cases_type_priority ON test_cases(test_type, priority)",
            "CREATE INDEX IF NOT EXISTS idx_test_cases_active_time ON test_cases(is_active, created_at)",
            
            # 测试执行表索引
            "CREATE INDEX IF NOT EXISTS idx_test_executions_env_status ON test_executions(environment, status)",
            "CREATE INDEX IF NOT EXISTS idx_test_executions_time_range ON test_executions(start_time, end_time)",
            
            # 智能体日志表索引
            "CREATE INDEX IF NOT EXISTS idx_agent_logs_level_time ON agent_logs(log_level, timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_agent_logs_agent_session ON agent_logs(agent_type, session_id)",
            "CREATE INDEX IF NOT EXISTS idx_agent_logs_user_operation ON agent_logs(user_id, operation)",
            
            # 系统指标表索引
            "CREATE INDEX IF NOT EXISTS idx_system_metrics_type_time ON system_metrics(metric_type, timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_system_metrics_name_time ON system_metrics(metric_name, timestamp)",
            
            # 告警表索引
            "CREATE INDEX IF NOT EXISTS idx_alerts_status_time ON alerts(status, triggered_at)",
            "CREATE INDEX IF NOT EXISTS idx_alerts_severity_time ON alerts(severity, triggered_at)",
            
            # 操作日志表索引
            "CREATE INDEX IF NOT EXISTS idx_operation_logs_user_type ON operation_logs(user_id, operation_type)",
            "CREATE INDEX IF NOT EXISTS idx_operation_logs_target_time ON operation_logs(operation_target, created_at)",
            
            # 用户会话表索引
            "CREATE INDEX IF NOT EXISTS idx_user_sessions_user_active ON user_sessions(user_id, is_active)",
            "CREATE INDEX IF NOT EXISTS idx_user_sessions_activity_time ON user_sessions(last_activity, is_active)"
        ]
        
        for index_sql in indexes:
            try:
                await db.execute_query(index_sql)
                logger.debug(f"创建索引: {index_sql}")
            except Exception as e:
                logger.warning(f"索引创建失败: {index_sql}, 错误: {str(e)}")
        
        logger.info("自定义索引创建完成")
        
    except Exception as e:
        logger.error(f"创建自定义索引失败: {str(e)}")


async def insert_initial_data():
    """插入初始数据"""
    try:
        from app.models.api_automation import (
            AlertRule, SystemConfiguration, AgentMetrics
        )
        from datetime import datetime
        import uuid
        
        # 创建默认告警规则
        default_alert_rules = [
            {
                "rule_id": "rule-error-rate-high",
                "name": "高错误率告警",
                "description": "当错误率超过5%时触发告警",
                "rule_type": "ERROR_RATE",
                "threshold_value": 5.0,
                "comparison_operator": ">",
                "time_window": 10,
                "trigger_count": 3,
                "severity": "HIGH"
            },
            {
                "rule_id": "rule-response-time-slow",
                "name": "响应时间过慢告警",
                "description": "当平均响应时间超过5秒时触发告警",
                "rule_type": "RESPONSE_TIME",
                "threshold_value": 5000.0,
                "comparison_operator": ">",
                "time_window": 5,
                "trigger_count": 2,
                "severity": "MEDIUM"
            },
            {
                "rule_id": "rule-memory-usage-high",
                "name": "内存使用率过高告警",
                "description": "当内存使用率超过80%时触发告警",
                "rule_type": "MEMORY_USAGE",
                "threshold_value": 80.0,
                "comparison_operator": ">",
                "time_window": 5,
                "trigger_count": 3,
                "severity": "HIGH"
            },
            {
                "rule_id": "rule-cpu-usage-critical",
                "name": "CPU使用率危险告警",
                "description": "当CPU使用率超过90%时触发告警",
                "rule_type": "CPU_USAGE",
                "threshold_value": 90.0,
                "comparison_operator": ">",
                "time_window": 3,
                "trigger_count": 2,
                "severity": "CRITICAL"
            },
            {
                "rule_id": "rule-test-failure-rate",
                "name": "测试失败率告警",
                "description": "当测试失败率超过10%时触发告警",
                "rule_type": "TEST_FAILURE_RATE",
                "threshold_value": 10.0,
                "comparison_operator": ">",
                "time_window": 15,
                "trigger_count": 1,
                "severity": "MEDIUM"
            }
        ]
        
        for rule_data in default_alert_rules:
            existing_rule = await AlertRule.filter(rule_id=rule_data["rule_id"]).first()
            if not existing_rule:
                await AlertRule.create(**rule_data)
                logger.info(f"创建默认告警规则: {rule_data['name']}")
        
        # 创建默认系统配置
        default_configs = [
            {
                "config_id": "config-max-file-size",
                "config_key": "MAX_UPLOAD_FILE_SIZE",
                "config_value": "10485760",  # 10MB
                "config_type": "INTEGER",
                "category": "UPLOAD",
                "description": "最大上传文件大小(字节)",
                "is_system": True
            },
            {
                "config_id": "config-supported-formats",
                "config_key": "SUPPORTED_DOC_FORMATS",
                "config_value": '["openapi", "swagger", "postman"]',
                "config_type": "JSON",
                "category": "PARSER",
                "description": "支持的文档格式",
                "is_system": True
            },
            {
                "config_id": "config-default-timeout",
                "config_key": "DEFAULT_TEST_TIMEOUT",
                "config_value": "300",
                "config_type": "INTEGER",
                "category": "EXECUTION",
                "description": "默认测试超时时间(秒)",
                "is_system": False
            },
            {
                "config_id": "config-max-parallel-workers",
                "config_key": "MAX_PARALLEL_WORKERS",
                "config_value": "5",
                "config_type": "INTEGER",
                "category": "EXECUTION",
                "description": "最大并行工作线程数",
                "is_system": False
            },
            {
                "config_id": "config-log-retention-days",
                "config_key": "LOG_RETENTION_DAYS",
                "config_value": "30",
                "config_type": "INTEGER",
                "category": "LOGGING",
                "description": "日志保留天数",
                "is_system": False
            },
            {
                "config_id": "config-report-formats",
                "config_key": "DEFAULT_REPORT_FORMATS",
                "config_value": '["html", "json"]',
                "config_type": "JSON",
                "category": "REPORTING",
                "description": "默认报告格式",
                "is_system": False
            }
        ]
        
        for config_data in default_configs:
            existing_config = await SystemConfiguration.filter(config_id=config_data["config_id"]).first()
            if not existing_config:
                await SystemConfiguration.create(**config_data)
                logger.info(f"创建默认系统配置: {config_data['config_key']}")
        
        # 初始化智能体指标记录
        agent_types = [
            "api_doc_parser",
            "api_analyzer", 
            "test_generator",
            "test_executor",
            "log_recorder"
        ]
        
        for agent_type in agent_types:
            metric_id = f"metric-{agent_type}-{uuid.uuid4().hex[:8]}"
            existing_metric = await AgentMetrics.filter(agent_type=agent_type).first()
            if not existing_metric:
                await AgentMetrics.create(
                    metric_id=metric_id,
                    agent_type=agent_type,
                    agent_name=f"{agent_type.replace('_', ' ').title()} Agent",
                    status="ONLINE",
                    timestamp=datetime.utcnow(),
                    last_heartbeat=datetime.utcnow()
                )
                logger.info(f"初始化智能体指标: {agent_type}")
        
        logger.info("初始数据插入完成")
        
    except Exception as e:
        logger.error(f"插入初始数据失败: {str(e)}")


async def drop_all_tables():
    """删除所有表（谨慎使用）"""
    try:
        await Tortoise.init(
            db_url=settings.DATABASE_URL,
            modules={'models': ['app.models.api_automation', 'app.models.admin']}
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
        
        # 重新创建表
        await create_api_automation_tables()
        
        logger.info("数据库重置完成")
        
    except Exception as e:
        logger.error(f"数据库重置失败: {str(e)}")
        raise


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "create":
            asyncio.run(create_api_automation_tables())
        elif command == "reset":
            asyncio.run(reset_database())
        elif command == "drop":
            asyncio.run(drop_all_tables())
        else:
            print("可用命令: create, reset, drop")
    else:
        print("用法: python create_tables.py <command>")
        print("命令:")
        print("  create - 创建数据库表")
        print("  reset  - 重置数据库")
        print("  drop   - 删除所有表")
