"""
数据库性能监控脚本
实时监控数据库性能指标，生成性能报告和告警
"""
import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from loguru import logger
from tortoise import Tortoise, connections

from app.core.config import settings


class DatabaseMonitor:
    """数据库性能监控器"""
    
    def __init__(self):
        self.monitoring = False
        self.metrics_history = []
        self.alert_thresholds = {
            'slow_query_threshold': 1000,  # 毫秒
            'connection_threshold': 80,     # 连接数百分比
            'lock_wait_threshold': 5000,    # 毫秒
            'table_size_threshold': 1024,   # MB
            'index_usage_threshold': 0.1    # 使用率
        }
    
    async def start_monitoring(self, interval: int = 60):
        """开始监控"""
        try:
            await Tortoise.init(
                db_url=settings.DATABASE_URL,
                modules={'models': ['app.models.api_automation']}
            )
            
            self.monitoring = True
            logger.info(f"开始数据库性能监控，间隔: {interval}秒")
            
            while self.monitoring:
                try:
                    metrics = await self.collect_metrics()
                    await self.analyze_metrics(metrics)
                    await self.check_alerts(metrics)
                    
                    # 保存指标历史
                    self.metrics_history.append({
                        'timestamp': datetime.utcnow(),
                        'metrics': metrics
                    })
                    
                    # 保持最近24小时的数据
                    cutoff_time = datetime.utcnow() - timedelta(hours=24)
                    self.metrics_history = [
                        h for h in self.metrics_history 
                        if h['timestamp'] > cutoff_time
                    ]
                    
                    await asyncio.sleep(interval)
                    
                except Exception as e:
                    logger.error(f"监控过程中出错: {str(e)}")
                    await asyncio.sleep(interval)
            
        except Exception as e:
            logger.error(f"启动监控失败: {str(e)}")
        finally:
            await Tortoise.close_connections()
    
    async def collect_metrics(self) -> Dict[str, Any]:
        """收集性能指标"""
        try:
            db = connections.get("default")
            metrics = {
                'timestamp': datetime.utcnow().isoformat(),
                'database_size': await self._get_database_size(),
                'table_sizes': await self._get_table_sizes(),
                'connection_stats': await self._get_connection_stats(),
                'query_stats': await self._get_query_stats(),
                'index_usage': await self._get_index_usage(),
                'lock_stats': await self._get_lock_stats(),
                'cache_stats': await self._get_cache_stats()
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"收集指标失败: {str(e)}")
            return {}
    
    async def _get_database_size(self) -> Dict[str, Any]:
        """获取数据库大小"""
        try:
            db = connections.get("default")
            
            # PostgreSQL查询
            if 'postgresql' in settings.DATABASE_URL:
                query = """
                SELECT 
                    pg_size_pretty(pg_database_size(current_database())) as size,
                    pg_database_size(current_database()) as size_bytes
                """
                result = await db.execute_query(query)
                if result:
                    return {
                        'size': result[0].get('size', '0 bytes'),
                        'size_bytes': result[0].get('size_bytes', 0)
                    }
            
            return {'size': 'Unknown', 'size_bytes': 0}
            
        except Exception as e:
            logger.warning(f"获取数据库大小失败: {str(e)}")
            return {'size': 'Error', 'size_bytes': 0}
    
    async def _get_table_sizes(self) -> List[Dict[str, Any]]:
        """获取表大小"""
        try:
            db = connections.get("default")
            
            if 'postgresql' in settings.DATABASE_URL:
                query = """
                SELECT 
                    schemaname,
                    tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
                    pg_total_relation_size(schemaname||'.'||tablename) as size_bytes,
                    pg_stat_get_tuples_returned(c.oid) as tuples_returned,
                    pg_stat_get_tuples_fetched(c.oid) as tuples_fetched
                FROM pg_tables pt
                JOIN pg_class c ON c.relname = pt.tablename
                WHERE schemaname = 'public'
                ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
                LIMIT 20
                """
                
                result = await db.execute_query(query)
                return [dict(row) for row in result] if result else []
            
            return []
            
        except Exception as e:
            logger.warning(f"获取表大小失败: {str(e)}")
            return []
    
    async def _get_connection_stats(self) -> Dict[str, Any]:
        """获取连接统计"""
        try:
            db = connections.get("default")
            
            if 'postgresql' in settings.DATABASE_URL:
                query = """
                SELECT 
                    count(*) as total_connections,
                    count(*) FILTER (WHERE state = 'active') as active_connections,
                    count(*) FILTER (WHERE state = 'idle') as idle_connections,
                    count(*) FILTER (WHERE state = 'idle in transaction') as idle_in_transaction
                FROM pg_stat_activity
                WHERE datname = current_database()
                """
                
                result = await db.execute_query(query)
                if result:
                    return dict(result[0])
            
            return {}
            
        except Exception as e:
            logger.warning(f"获取连接统计失败: {str(e)}")
            return {}
    
    async def _get_query_stats(self) -> List[Dict[str, Any]]:
        """获取查询统计"""
        try:
            db = connections.get("default")
            
            if 'postgresql' in settings.DATABASE_URL:
                # 需要pg_stat_statements扩展
                query = """
                SELECT 
                    query,
                    calls,
                    total_time,
                    mean_time,
                    rows,
                    100.0 * shared_blks_hit / nullif(shared_blks_hit + shared_blks_read, 0) AS hit_percent
                FROM pg_stat_statements
                WHERE query NOT LIKE '%pg_stat_statements%'
                ORDER BY total_time DESC
                LIMIT 10
                """
                
                try:
                    result = await db.execute_query(query)
                    return [dict(row) for row in result] if result else []
                except:
                    # pg_stat_statements可能未启用
                    return []
            
            return []
            
        except Exception as e:
            logger.warning(f"获取查询统计失败: {str(e)}")
            return []
    
    async def _get_index_usage(self) -> List[Dict[str, Any]]:
        """获取索引使用情况"""
        try:
            db = connections.get("default")
            
            if 'postgresql' in settings.DATABASE_URL:
                query = """
                SELECT 
                    schemaname,
                    tablename,
                    indexname,
                    idx_scan,
                    idx_tup_read,
                    idx_tup_fetch
                FROM pg_stat_user_indexes
                WHERE schemaname = 'public'
                ORDER BY idx_scan DESC
                """
                
                result = await db.execute_query(query)
                return [dict(row) for row in result] if result else []
            
            return []
            
        except Exception as e:
            logger.warning(f"获取索引使用情况失败: {str(e)}")
            return []
    
    async def _get_lock_stats(self) -> Dict[str, Any]:
        """获取锁统计"""
        try:
            db = connections.get("default")
            
            if 'postgresql' in settings.DATABASE_URL:
                query = """
                SELECT 
                    mode,
                    count(*) as count
                FROM pg_locks
                WHERE database = (SELECT oid FROM pg_database WHERE datname = current_database())
                GROUP BY mode
                """
                
                result = await db.execute_query(query)
                lock_stats = {}
                if result:
                    for row in result:
                        lock_stats[row['mode']] = row['count']
                
                return lock_stats
            
            return {}
            
        except Exception as e:
            logger.warning(f"获取锁统计失败: {str(e)}")
            return {}
    
    async def _get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        try:
            db = connections.get("default")
            
            if 'postgresql' in settings.DATABASE_URL:
                query = """
                SELECT 
                    sum(heap_blks_read) as heap_read,
                    sum(heap_blks_hit) as heap_hit,
                    sum(heap_blks_hit) / (sum(heap_blks_hit) + sum(heap_blks_read)) as cache_hit_ratio
                FROM pg_statio_user_tables
                """
                
                result = await db.execute_query(query)
                if result:
                    return dict(result[0])
            
            return {}
            
        except Exception as e:
            logger.warning(f"获取缓存统计失败: {str(e)}")
            return {}
    
    async def analyze_metrics(self, metrics: Dict[str, Any]):
        """分析指标"""
        try:
            analysis = {
                'timestamp': metrics['timestamp'],
                'health_score': 100,
                'issues': [],
                'recommendations': []
            }
            
            # 分析表大小
            table_sizes = metrics.get('table_sizes', [])
            for table in table_sizes:
                size_mb = table.get('size_bytes', 0) / 1024 / 1024
                if size_mb > self.alert_thresholds['table_size_threshold']:
                    analysis['issues'].append(f"表 {table['tablename']} 过大: {table['size']}")
                    analysis['health_score'] -= 5
            
            # 分析连接数
            conn_stats = metrics.get('connection_stats', {})
            total_conn = conn_stats.get('total_connections', 0)
            if total_conn > 50:  # 假设最大连接数为100
                analysis['issues'].append(f"连接数过多: {total_conn}")
                analysis['health_score'] -= 10
            
            # 分析索引使用
            index_usage = metrics.get('index_usage', [])
            unused_indexes = [idx for idx in index_usage if idx.get('idx_scan', 0) == 0]
            if unused_indexes:
                analysis['recommendations'].append(f"发现 {len(unused_indexes)} 个未使用的索引")
            
            # 分析缓存命中率
            cache_stats = metrics.get('cache_stats', {})
            hit_ratio = cache_stats.get('cache_hit_ratio', 1.0)
            if hit_ratio < 0.9:
                analysis['issues'].append(f"缓存命中率过低: {hit_ratio:.2%}")
                analysis['health_score'] -= 15
            
            logger.info(f"性能分析完成，健康评分: {analysis['health_score']}")
            
            return analysis
            
        except Exception as e:
            logger.error(f"分析指标失败: {str(e)}")
            return {}
    
    async def check_alerts(self, metrics: Dict[str, Any]):
        """检查告警"""
        try:
            alerts = []
            
            # 检查慢查询
            query_stats = metrics.get('query_stats', [])
            for query in query_stats:
                mean_time = query.get('mean_time', 0)
                if mean_time > self.alert_thresholds['slow_query_threshold']:
                    alerts.append({
                        'type': 'SLOW_QUERY',
                        'severity': 'WARNING',
                        'message': f"慢查询检测: 平均执行时间 {mean_time:.2f}ms",
                        'details': query
                    })
            
            # 检查表大小
            table_sizes = metrics.get('table_sizes', [])
            for table in table_sizes:
                size_mb = table.get('size_bytes', 0) / 1024 / 1024
                if size_mb > self.alert_thresholds['table_size_threshold']:
                    alerts.append({
                        'type': 'LARGE_TABLE',
                        'severity': 'INFO',
                        'message': f"大表检测: {table['tablename']} ({table['size']})",
                        'details': table
                    })
            
            # 记录告警
            for alert in alerts:
                logger.warning(f"数据库告警: {alert['message']}")
            
            return alerts
            
        except Exception as e:
            logger.error(f"检查告警失败: {str(e)}")
            return []
    
    async def generate_performance_report(self) -> Dict[str, Any]:
        """生成性能报告"""
        try:
            if not self.metrics_history:
                return {'error': '没有可用的监控数据'}
            
            latest_metrics = self.metrics_history[-1]['metrics']
            
            # 计算趋势
            trends = {}
            if len(self.metrics_history) > 1:
                prev_metrics = self.metrics_history[-2]['metrics']
                
                # 数据库大小趋势
                current_size = latest_metrics.get('database_size', {}).get('size_bytes', 0)
                prev_size = prev_metrics.get('database_size', {}).get('size_bytes', 0)
                if prev_size > 0:
                    size_growth = ((current_size - prev_size) / prev_size) * 100
                    trends['database_size_growth'] = f"{size_growth:.2f}%"
            
            report = {
                'generated_at': datetime.utcnow().isoformat(),
                'monitoring_period': {
                    'start': self.metrics_history[0]['timestamp'].isoformat(),
                    'end': self.metrics_history[-1]['timestamp'].isoformat(),
                    'data_points': len(self.metrics_history)
                },
                'current_metrics': latest_metrics,
                'trends': trends,
                'summary': {
                    'database_size': latest_metrics.get('database_size', {}),
                    'total_tables': len(latest_metrics.get('table_sizes', [])),
                    'active_connections': latest_metrics.get('connection_stats', {}).get('active_connections', 0),
                    'cache_hit_ratio': latest_metrics.get('cache_stats', {}).get('cache_hit_ratio', 0)
                }
            }
            
            return report
            
        except Exception as e:
            logger.error(f"生成性能报告失败: {str(e)}")
            return {'error': str(e)}
    
    def stop_monitoring(self):
        """停止监控"""
        self.monitoring = False
        logger.info("数据库监控已停止")


async def main():
    """主函数"""
    import sys
    
    monitor = DatabaseMonitor()
    
    if len(sys.argv) < 2:
        print("用法: python monitor_performance.py <command> [args]")
        print("命令:")
        print("  start [interval]  - 开始监控 (默认间隔60秒)")
        print("  report           - 生成性能报告")
        print("  metrics          - 收集当前指标")
        return
    
    command = sys.argv[1]
    
    try:
        if command == "start":
            interval = int(sys.argv[2]) if len(sys.argv) > 2 else 60
            await monitor.start_monitoring(interval)
        
        elif command == "report":
            # 先收集一些数据
            await Tortoise.init(
                db_url=settings.DATABASE_URL,
                modules={'models': ['app.models.api_automation']}
            )
            
            metrics = await monitor.collect_metrics()
            monitor.metrics_history.append({
                'timestamp': datetime.utcnow(),
                'metrics': metrics
            })
            
            report = await monitor.generate_performance_report()
            print(json.dumps(report, indent=2, ensure_ascii=False))
            
            await Tortoise.close_connections()
        
        elif command == "metrics":
            await Tortoise.init(
                db_url=settings.DATABASE_URL,
                modules={'models': ['app.models.api_automation']}
            )
            
            metrics = await monitor.collect_metrics()
            print(json.dumps(metrics, indent=2, ensure_ascii=False))
            
            await Tortoise.close_connections()
        
        else:
            print(f"未知命令: {command}")
    
    except KeyboardInterrupt:
        monitor.stop_monitoring()
        logger.info("监控被用户中断")
    except Exception as e:
        logger.error(f"执行失败: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
