"""
数据库优化脚本
包含性能优化、数据清理、统计分析等功能
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any
from loguru import logger
from tortoise import Tortoise, connections

from app.core.config import settings


async def analyze_table_performance():
    """分析表性能"""
    try:
        await Tortoise.init(
            db_url=settings.DATABASE_URL,
            modules={'models': ['app.models.api_automation', 'app.models.admin']}
        )
        
        db = connections.get("default")
        
        # 获取表统计信息
        tables = [
            'api_documents', 'api_endpoints', 'test_cases', 'test_results',
            'test_executions', 'agent_logs', 'system_metrics', 'alerts',
            'test_reports', 'operation_logs', 'user_sessions'
        ]
        
        performance_stats = {}
        
        for table in tables:
            try:
                # 获取表大小和行数
                size_query = f"""
                SELECT 
                    COUNT(*) as row_count,
                    pg_size_pretty(pg_total_relation_size('{table}')) as table_size,
                    pg_total_relation_size('{table}') as size_bytes
                FROM {table}
                """
                
                result = await db.execute_query(size_query)
                if result:
                    row = result[0]
                    performance_stats[table] = {
                        'row_count': row.get('row_count', 0),
                        'table_size': row.get('table_size', '0 bytes'),
                        'size_bytes': row.get('size_bytes', 0)
                    }
                
                # 检查索引使用情况
                index_query = f"""
                SELECT 
                    schemaname,
                    tablename,
                    indexname,
                    idx_scan,
                    idx_tup_read,
                    idx_tup_fetch
                FROM pg_stat_user_indexes 
                WHERE tablename = '{table}'
                """
                
                index_result = await db.execute_query(index_query)
                performance_stats[table]['indexes'] = []
                
                if index_result:
                    for idx_row in index_result:
                        performance_stats[table]['indexes'].append({
                            'name': idx_row.get('indexname'),
                            'scans': idx_row.get('idx_scan', 0),
                            'tuples_read': idx_row.get('idx_tup_read', 0),
                            'tuples_fetched': idx_row.get('idx_tup_fetch', 0)
                        })
                
            except Exception as e:
                logger.warning(f"分析表 {table} 失败: {str(e)}")
                performance_stats[table] = {'error': str(e)}
        
        # 输出分析结果
        logger.info("=== 数据库性能分析报告 ===")
        total_size = 0
        total_rows = 0
        
        for table, stats in performance_stats.items():
            if 'error' not in stats:
                logger.info(f"表 {table}:")
                logger.info(f"  行数: {stats['row_count']:,}")
                logger.info(f"  大小: {stats['table_size']}")
                logger.info(f"  索引数量: {len(stats['indexes'])}")
                
                total_size += stats['size_bytes']
                total_rows += stats['row_count']
                
                # 检查未使用的索引
                unused_indexes = [idx for idx in stats['indexes'] if idx['scans'] == 0]
                if unused_indexes:
                    logger.warning(f"  未使用的索引: {[idx['name'] for idx in unused_indexes]}")
        
        logger.info(f"总计: {total_rows:,} 行, {total_size / 1024 / 1024:.2f} MB")
        
        return performance_stats
        
    except Exception as e:
        logger.error(f"性能分析失败: {str(e)}")
        return {}
    finally:
        await Tortoise.close_connections()


async def cleanup_old_data(days: int = 30, dry_run: bool = True):
    """清理旧数据"""
    try:
        from app.models.api_automation import (
            AgentLog, LogAnalysis, Alert, OperationLog, 
            UserSession, TestResult, TestExecution
        )
        
        await Tortoise.init(
            db_url=settings.DATABASE_URL,
            modules={'models': ['app.models.api_automation']}
        )
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        cleanup_stats = {}
        
        logger.info(f"{'[DRY RUN] ' if dry_run else ''}开始清理 {days} 天前的数据...")
        
        # 清理智能体日志
        old_logs = await AgentLog.filter(created_at__lt=cutoff_date)
        cleanup_stats['agent_logs'] = len(old_logs)
        if not dry_run:
            await AgentLog.filter(created_at__lt=cutoff_date).delete()
        
        # 清理日志分析结果
        old_analyses = await LogAnalysis.filter(created_at__lt=cutoff_date)
        cleanup_stats['log_analyses'] = len(old_analyses)
        if not dry_run:
            await LogAnalysis.filter(created_at__lt=cutoff_date).delete()
        
        # 清理已解决的告警
        old_alerts = await Alert.filter(
            status="RESOLVED",
            resolved_at__lt=cutoff_date
        )
        cleanup_stats['resolved_alerts'] = len(old_alerts)
        if not dry_run:
            await Alert.filter(
                status="RESOLVED",
                resolved_at__lt=cutoff_date
            ).delete()
        
        # 清理操作日志
        old_operation_logs = await OperationLog.filter(created_at__lt=cutoff_date)
        cleanup_stats['operation_logs'] = len(old_operation_logs)
        if not dry_run:
            await OperationLog.filter(created_at__lt=cutoff_date).delete()
        
        # 清理过期用户会话
        old_sessions = await UserSession.filter(
            is_active=False,
            logout_time__lt=cutoff_date
        )
        cleanup_stats['user_sessions'] = len(old_sessions)
        if not dry_run:
            await UserSession.filter(
                is_active=False,
                logout_time__lt=cutoff_date
            ).delete()
        
        # 清理旧的测试结果（保留最近的执行结果）
        old_test_results = await TestResult.filter(created_at__lt=cutoff_date)
        cleanup_stats['test_results'] = len(old_test_results)
        if not dry_run:
            await TestResult.filter(created_at__lt=cutoff_date).delete()
        
        # 输出清理统计
        logger.info(f"{'[DRY RUN] ' if dry_run else ''}清理统计:")
        for table, count in cleanup_stats.items():
            logger.info(f"  {table}: {count:,} 条记录")
        
        total_cleaned = sum(cleanup_stats.values())
        logger.info(f"{'预计清理' if dry_run else '已清理'} 总计: {total_cleaned:,} 条记录")
        
        return cleanup_stats
        
    except Exception as e:
        logger.error(f"数据清理失败: {str(e)}")
        return {}
    finally:
        await Tortoise.close_connections()


async def optimize_indexes():
    """优化索引"""
    try:
        await Tortoise.init(
            db_url=settings.DATABASE_URL,
            modules={'models': ['app.models.api_automation']}
        )
        
        db = connections.get("default")
        
        # 重建索引
        logger.info("开始重建索引...")
        
        # 获取所有索引
        index_query = """
        SELECT 
            schemaname,
            tablename,
            indexname
        FROM pg_indexes 
        WHERE schemaname = 'public'
        AND tablename IN (
            'api_documents', 'api_endpoints', 'test_cases', 
            'test_results', 'agent_logs', 'system_metrics'
        )
        """
        
        indexes = await db.execute_query(index_query)
        
        for index in indexes:
            try:
                index_name = index['indexname']
                # 跳过主键索引
                if '_pkey' not in index_name:
                    reindex_sql = f"REINDEX INDEX {index_name}"
                    await db.execute_query(reindex_sql)
                    logger.debug(f"重建索引: {index_name}")
            except Exception as e:
                logger.warning(f"重建索引 {index_name} 失败: {str(e)}")
        
        # 更新表统计信息
        logger.info("更新表统计信息...")
        
        tables = [
            'api_documents', 'api_endpoints', 'test_cases', 
            'test_results', 'agent_logs', 'system_metrics'
        ]
        
        for table in tables:
            try:
                analyze_sql = f"ANALYZE {table}"
                await db.execute_query(analyze_sql)
                logger.debug(f"分析表: {table}")
            except Exception as e:
                logger.warning(f"分析表 {table} 失败: {str(e)}")
        
        logger.info("索引优化完成")
        
    except Exception as e:
        logger.error(f"索引优化失败: {str(e)}")
    finally:
        await Tortoise.close_connections()


async def vacuum_database():
    """清理数据库"""
    try:
        await Tortoise.init(
            db_url=settings.DATABASE_URL,
            modules={'models': ['app.models.api_automation']}
        )
        
        db = connections.get("default")
        
        logger.info("开始数据库清理...")
        
        # 执行 VACUUM ANALYZE
        tables = [
            'api_documents', 'api_endpoints', 'test_cases', 
            'test_results', 'agent_logs', 'system_metrics',
            'alerts', 'test_reports', 'operation_logs'
        ]
        
        for table in tables:
            try:
                vacuum_sql = f"VACUUM ANALYZE {table}"
                await db.execute_query(vacuum_sql)
                logger.debug(f"清理表: {table}")
            except Exception as e:
                logger.warning(f"清理表 {table} 失败: {str(e)}")
        
        logger.info("数据库清理完成")
        
    except Exception as e:
        logger.error(f"数据库清理失败: {str(e)}")
    finally:
        await Tortoise.close_connections()


async def generate_database_report():
    """生成数据库报告"""
    try:
        from app.models.api_automation import (
            ApiDocument, ApiEndpoint, TestCase, TestResult,
            AgentLog, Alert, TestExecution
        )
        
        await Tortoise.init(
            db_url=settings.DATABASE_URL,
            modules={'models': ['app.models.api_automation']}
        )
        
        report = {
            'generated_at': datetime.utcnow().isoformat(),
            'statistics': {},
            'health_metrics': {},
            'recommendations': []
        }
        
        # 基础统计
        report['statistics'] = {
            'total_documents': await ApiDocument.all().count(),
            'total_endpoints': await ApiEndpoint.all().count(),
            'total_test_cases': await TestCase.all().count(),
            'total_test_results': await TestResult.all().count(),
            'total_executions': await TestExecution.all().count(),
            'total_logs': await AgentLog.all().count(),
            'active_alerts': await Alert.filter(status="OPEN").count()
        }
        
        # 最近7天的活动
        week_ago = datetime.utcnow() - timedelta(days=7)
        report['recent_activity'] = {
            'documents_uploaded': await ApiDocument.filter(created_at__gte=week_ago).count(),
            'tests_executed': await TestExecution.filter(created_at__gte=week_ago).count(),
            'errors_logged': await AgentLog.filter(
                log_level="ERROR",
                created_at__gte=week_ago
            ).count()
        }
        
        # 健康指标
        total_executions = await TestExecution.all().count()
        successful_executions = await TestExecution.filter(
            status="SUCCESS"
        ).count()
        
        if total_executions > 0:
            success_rate = (successful_executions / total_executions) * 100
            report['health_metrics']['overall_success_rate'] = round(success_rate, 2)
        else:
            report['health_metrics']['overall_success_rate'] = 0
        
        # 生成建议
        if report['statistics']['total_logs'] > 100000:
            report['recommendations'].append("建议清理旧日志以提高性能")
        
        if report['health_metrics']['overall_success_rate'] < 80:
            report['recommendations'].append("测试成功率较低，建议检查测试配置")
        
        if report['statistics']['active_alerts'] > 10:
            report['recommendations'].append("存在较多未处理告警，建议及时处理")
        
        logger.info("=== 数据库健康报告 ===")
        logger.info(f"文档总数: {report['statistics']['total_documents']:,}")
        logger.info(f"接口总数: {report['statistics']['total_endpoints']:,}")
        logger.info(f"测试用例: {report['statistics']['total_test_cases']:,}")
        logger.info(f"执行记录: {report['statistics']['total_executions']:,}")
        logger.info(f"成功率: {report['health_metrics']['overall_success_rate']}%")
        logger.info(f"活跃告警: {report['statistics']['active_alerts']}")
        
        if report['recommendations']:
            logger.info("建议:")
            for rec in report['recommendations']:
                logger.info(f"  - {rec}")
        
        return report
        
    except Exception as e:
        logger.error(f"生成数据库报告失败: {str(e)}")
        return {}
    finally:
        await Tortoise.close_connections()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "analyze":
            asyncio.run(analyze_table_performance())
        elif command == "cleanup":
            days = int(sys.argv[2]) if len(sys.argv) > 2 else 30
            dry_run = sys.argv[3].lower() != "execute" if len(sys.argv) > 3 else True
            asyncio.run(cleanup_old_data(days, dry_run))
        elif command == "optimize":
            asyncio.run(optimize_indexes())
        elif command == "vacuum":
            asyncio.run(vacuum_database())
        elif command == "report":
            asyncio.run(generate_database_report())
        else:
            print("可用命令: analyze, cleanup, optimize, vacuum, report")
    else:
        print("用法: python optimize_database.py <command> [args]")
        print("命令:")
        print("  analyze              - 分析表性能")
        print("  cleanup <days> [execute] - 清理旧数据 (默认30天，dry-run)")
        print("  optimize             - 优化索引")
        print("  vacuum               - 清理数据库")
        print("  report               - 生成健康报告")
