"""
数据库备份和恢复工具
支持API自动化系统的数据备份、恢复和迁移
"""
import asyncio
import json
import gzip
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from loguru import logger
from tortoise import Tortoise

from app.core.config import settings


class BackupRestoreManager:
    """数据库备份恢复管理器"""
    
    def __init__(self):
        self.backup_dir = Path("backups")
        self.backup_dir.mkdir(exist_ok=True)
        
    async def create_full_backup(self, backup_name: Optional[str] = None) -> str:
        """创建完整备份"""
        try:
            if not backup_name:
                backup_name = f"full_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            backup_path = self.backup_dir / f"{backup_name}.json.gz"
            
            await Tortoise.init(
                db_url=settings.DATABASE_URL,
                modules={'models': ['app.models.api_automation', 'app.models.admin']}
            )
            
            logger.info(f"开始创建完整备份: {backup_name}")
            
            backup_data = {
                'metadata': {
                    'backup_name': backup_name,
                    'backup_time': datetime.utcnow().isoformat(),
                    'backup_type': 'full',
                    'version': '1.0'
                },
                'data': {}
            }
            
            # 备份各个表的数据
            tables_to_backup = [
                'api_documents', 'api_endpoints', 'test_cases', 'test_results',
                'test_executions', 'agent_logs', 'system_metrics', 'alerts',
                'alert_rules', 'test_scripts', 'log_analyses', 'workflow_sessions',
                'api_analysis_results', 'test_generation_tasks', 'test_execution_sessions',
                'test_reports', 'agent_metrics', 'user_sessions', 'system_configurations',
                'operation_logs'
            ]
            
            for table_name in tables_to_backup:
                try:
                    model_class = self._get_model_class(table_name)
                    if model_class:
                        records = await model_class.all().values()
                        backup_data['data'][table_name] = self._serialize_records(records)
                        logger.info(f"备份表 {table_name}: {len(records)} 条记录")
                except Exception as e:
                    logger.warning(f"备份表 {table_name} 失败: {str(e)}")
                    backup_data['data'][table_name] = []
            
            # 压缩并保存备份文件
            json_data = json.dumps(backup_data, ensure_ascii=False, indent=2)
            
            with gzip.open(backup_path, 'wt', encoding='utf-8') as f:
                f.write(json_data)
            
            backup_size = backup_path.stat().st_size
            logger.info(f"备份完成: {backup_path} ({backup_size / 1024 / 1024:.2f} MB)")
            
            return str(backup_path)
            
        except Exception as e:
            logger.error(f"创建备份失败: {str(e)}")
            raise
        finally:
            await Tortoise.close_connections()
    
    async def create_incremental_backup(self, since: datetime, backup_name: Optional[str] = None) -> str:
        """创建增量备份"""
        try:
            if not backup_name:
                backup_name = f"incremental_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            backup_path = self.backup_dir / f"{backup_name}.json.gz"
            
            await Tortoise.init(
                db_url=settings.DATABASE_URL,
                modules={'models': ['app.models.api_automation']}
            )
            
            logger.info(f"开始创建增量备份: {backup_name} (自 {since})")
            
            backup_data = {
                'metadata': {
                    'backup_name': backup_name,
                    'backup_time': datetime.utcnow().isoformat(),
                    'backup_type': 'incremental',
                    'since': since.isoformat(),
                    'version': '1.0'
                },
                'data': {}
            }
            
            # 只备份指定时间之后的数据
            from app.models.api_automation import (
                ApiDocument, ApiEndpoint, TestCase, TestResult,
                AgentLog, Alert, OperationLog
            )
            
            incremental_tables = [
                (ApiDocument, 'api_documents'),
                (TestResult, 'test_results'),
                (AgentLog, 'agent_logs'),
                (Alert, 'alerts'),
                (OperationLog, 'operation_logs')
            ]
            
            for model_class, table_name in incremental_tables:
                try:
                    records = await model_class.filter(created_at__gte=since).values()
                    backup_data['data'][table_name] = self._serialize_records(records)
                    logger.info(f"增量备份表 {table_name}: {len(records)} 条记录")
                except Exception as e:
                    logger.warning(f"增量备份表 {table_name} 失败: {str(e)}")
                    backup_data['data'][table_name] = []
            
            # 压缩并保存备份文件
            json_data = json.dumps(backup_data, ensure_ascii=False, indent=2)
            
            with gzip.open(backup_path, 'wt', encoding='utf-8') as f:
                f.write(json_data)
            
            backup_size = backup_path.stat().st_size
            logger.info(f"增量备份完成: {backup_path} ({backup_size / 1024:.2f} KB)")
            
            return str(backup_path)
            
        except Exception as e:
            logger.error(f"创建增量备份失败: {str(e)}")
            raise
        finally:
            await Tortoise.close_connections()
    
    async def restore_backup(self, backup_path: str, restore_mode: str = "replace") -> bool:
        """恢复备份"""
        try:
            backup_file = Path(backup_path)
            if not backup_file.exists():
                raise FileNotFoundError(f"备份文件不存在: {backup_path}")
            
            logger.info(f"开始恢复备份: {backup_path} (模式: {restore_mode})")
            
            # 读取备份文件
            with gzip.open(backup_file, 'rt', encoding='utf-8') as f:
                backup_data = json.load(f)
            
            metadata = backup_data.get('metadata', {})
            logger.info(f"备份信息: {metadata}")
            
            await Tortoise.init(
                db_url=settings.DATABASE_URL,
                modules={'models': ['app.models.api_automation']}
            )
            
            # 根据恢复模式处理数据
            if restore_mode == "replace":
                await self._restore_replace_mode(backup_data['data'])
            elif restore_mode == "merge":
                await self._restore_merge_mode(backup_data['data'])
            elif restore_mode == "skip_existing":
                await self._restore_skip_mode(backup_data['data'])
            else:
                raise ValueError(f"不支持的恢复模式: {restore_mode}")
            
            logger.info("备份恢复完成")
            return True
            
        except Exception as e:
            logger.error(f"恢复备份失败: {str(e)}")
            return False
        finally:
            await Tortoise.close_connections()
    
    async def _restore_replace_mode(self, data: Dict[str, List[Dict]]):
        """替换模式恢复"""
        for table_name, records in data.items():
            try:
                model_class = self._get_model_class(table_name)
                if model_class and records:
                    # 清空表
                    await model_class.all().delete()
                    logger.info(f"清空表 {table_name}")
                    
                    # 插入备份数据
                    for record in records:
                        record = self._deserialize_record(record)
                        await model_class.create(**record)
                    
                    logger.info(f"恢复表 {table_name}: {len(records)} 条记录")
            except Exception as e:
                logger.error(f"恢复表 {table_name} 失败: {str(e)}")
    
    async def _restore_merge_mode(self, data: Dict[str, List[Dict]]):
        """合并模式恢复"""
        for table_name, records in data.items():
            try:
                model_class = self._get_model_class(table_name)
                if model_class and records:
                    for record in records:
                        record = self._deserialize_record(record)
                        # 尝试更新或创建
                        await model_class.update_or_create(
                            id=record.get('id'),
                            defaults=record
                        )
                    
                    logger.info(f"合并表 {table_name}: {len(records)} 条记录")
            except Exception as e:
                logger.error(f"合并表 {table_name} 失败: {str(e)}")
    
    async def _restore_skip_mode(self, data: Dict[str, List[Dict]]):
        """跳过已存在记录模式恢复"""
        for table_name, records in data.items():
            try:
                model_class = self._get_model_class(table_name)
                if model_class and records:
                    created_count = 0
                    for record in records:
                        record = self._deserialize_record(record)
                        # 检查记录是否已存在
                        existing = await model_class.filter(id=record.get('id')).first()
                        if not existing:
                            await model_class.create(**record)
                            created_count += 1
                    
                    logger.info(f"跳过模式恢复表 {table_name}: 新增 {created_count} 条记录")
            except Exception as e:
                logger.error(f"跳过模式恢复表 {table_name} 失败: {str(e)}")
    
    def _get_model_class(self, table_name: str):
        """根据表名获取模型类"""
        from app.models.api_automation import (
            ApiDocument, ApiEndpoint, TestCase, TestResult, TestExecution,
            AgentLog, SystemMetrics, Alert, AlertRule, TestScript,
            LogAnalysis, WorkflowSession, ApiAnalysisResult, TestGenerationTask,
            TestExecutionSession, TestReport, AgentMetrics, UserSession,
            SystemConfiguration, OperationLog, DependencyRelation
        )
        
        model_mapping = {
            'api_documents': ApiDocument,
            'api_endpoints': ApiEndpoint,
            'test_cases': TestCase,
            'test_results': TestResult,
            'test_executions': TestExecution,
            'agent_logs': AgentLog,
            'system_metrics': SystemMetrics,
            'alerts': Alert,
            'alert_rules': AlertRule,
            'test_scripts': TestScript,
            'log_analyses': LogAnalysis,
            'workflow_sessions': WorkflowSession,
            'api_analysis_results': ApiAnalysisResult,
            'test_generation_tasks': TestGenerationTask,
            'test_execution_sessions': TestExecutionSession,
            'test_reports': TestReport,
            'agent_metrics': AgentMetrics,
            'user_sessions': UserSession,
            'system_configurations': SystemConfiguration,
            'operation_logs': OperationLog,
            'dependency_relations': DependencyRelation
        }
        
        return model_mapping.get(table_name)
    
    def _serialize_records(self, records: List[Dict]) -> List[Dict]:
        """序列化记录"""
        serialized = []
        for record in records:
            serialized_record = {}
            for key, value in record.items():
                if isinstance(value, datetime):
                    serialized_record[key] = value.isoformat()
                else:
                    serialized_record[key] = value
            serialized.append(serialized_record)
        return serialized
    
    def _deserialize_record(self, record: Dict) -> Dict:
        """反序列化记录"""
        deserialized = {}
        for key, value in record.items():
            if isinstance(value, str) and 'T' in value and value.endswith('Z'):
                try:
                    deserialized[key] = datetime.fromisoformat(value.replace('Z', '+00:00'))
                except:
                    deserialized[key] = value
            else:
                deserialized[key] = value
        return deserialized
    
    async def list_backups(self) -> List[Dict[str, Any]]:
        """列出所有备份"""
        backups = []
        
        for backup_file in self.backup_dir.glob("*.json.gz"):
            try:
                with gzip.open(backup_file, 'rt', encoding='utf-8') as f:
                    backup_data = json.load(f)
                
                metadata = backup_data.get('metadata', {})
                file_size = backup_file.stat().st_size
                
                backups.append({
                    'file_name': backup_file.name,
                    'file_path': str(backup_file),
                    'backup_name': metadata.get('backup_name', 'Unknown'),
                    'backup_time': metadata.get('backup_time', 'Unknown'),
                    'backup_type': metadata.get('backup_type', 'Unknown'),
                    'file_size': file_size,
                    'file_size_mb': round(file_size / 1024 / 1024, 2)
                })
            except Exception as e:
                logger.warning(f"读取备份文件 {backup_file} 失败: {str(e)}")
        
        # 按时间排序
        backups.sort(key=lambda x: x['backup_time'], reverse=True)
        return backups
    
    async def delete_backup(self, backup_path: str) -> bool:
        """删除备份文件"""
        try:
            backup_file = Path(backup_path)
            if backup_file.exists():
                backup_file.unlink()
                logger.info(f"删除备份文件: {backup_path}")
                return True
            else:
                logger.warning(f"备份文件不存在: {backup_path}")
                return False
        except Exception as e:
            logger.error(f"删除备份文件失败: {str(e)}")
            return False


if __name__ == "__main__":
    import sys
    
    manager = BackupRestoreManager()
    
    if len(sys.argv) < 2:
        print("用法: python backup_restore.py <command> [args]")
        print("命令:")
        print("  backup [name]           - 创建完整备份")
        print("  incremental <since>     - 创建增量备份")
        print("  restore <path> [mode]   - 恢复备份")
        print("  list                    - 列出所有备份")
        print("  delete <path>           - 删除备份")
        sys.exit(1)
    
    command = sys.argv[1]
    
    async def main():
        try:
            if command == "backup":
                name = sys.argv[2] if len(sys.argv) > 2 else None
                result = await manager.create_full_backup(name)
                print(f"备份创建成功: {result}")
            
            elif command == "incremental":
                if len(sys.argv) < 3:
                    print("请提供起始时间 (YYYY-MM-DD HH:MM:SS)")
                    return
                since_str = sys.argv[2]
                since = datetime.fromisoformat(since_str)
                result = await manager.create_incremental_backup(since)
                print(f"增量备份创建成功: {result}")
            
            elif command == "restore":
                if len(sys.argv) < 3:
                    print("请提供备份文件路径")
                    return
                backup_path = sys.argv[2]
                mode = sys.argv[3] if len(sys.argv) > 3 else "replace"
                result = await manager.restore_backup(backup_path, mode)
                print(f"备份恢复{'成功' if result else '失败'}")
            
            elif command == "list":
                backups = await manager.list_backups()
                print("备份列表:")
                for backup in backups:
                    print(f"  {backup['backup_name']} - {backup['backup_time']} ({backup['file_size_mb']} MB)")
            
            elif command == "delete":
                if len(sys.argv) < 3:
                    print("请提供备份文件路径")
                    return
                backup_path = sys.argv[2]
                result = await manager.delete_backup(backup_path)
                print(f"备份删除{'成功' if result else '失败'}")
            
            else:
                print(f"未知命令: {command}")
        
        except Exception as e:
            logger.error(f"执行命令失败: {str(e)}")
            sys.exit(1)
    
    asyncio.run(main())
