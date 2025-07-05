"""
执行历史服务
提供脚本执行历史的查询和管理功能
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy import select, desc, func, and_, or_
from sqlalchemy.orm import selectinload

from app.database.connection import db_manager
from app.database.models.executions import ScriptExecution, BatchExecution
from app.database.models.scripts import TestScript
from app.core.logging import get_logger

logger = get_logger(__name__)


class ExecutionHistoryService:
    """执行历史服务类"""
    
    async def get_execution_history(self,
                                  limit: int = 50,
                                  script_type: Optional[str] = None,
                                  status: Optional[str] = None,
                                  script_id: Optional[str] = None,
                                  execution_id: Optional[str] = None) -> Dict[str, Any]:
        """获取执行历史记录

        Args:
            limit: 返回记录数量限制
            script_type: 脚本类型过滤 (yaml, playwright)
            status: 状态过滤
            script_id: 脚本ID过滤
            execution_id: 执行ID过滤

        Returns:
            Dict[str, Any]: 包含历史记录和统计信息的字典
        """
        try:
            async with db_manager.get_session() as session:
                # 构建基础查询
                stmt = (
                    select(ScriptExecution)
                    .order_by(desc(ScriptExecution.created_at))
                    .limit(limit)
                )
                
                # 添加过滤条件
                filters = []
                if script_type:
                    # 暂时不通过TestScript表过滤，因为可能没有对应记录
                    # 我们可以通过execution_config中的信息来过滤
                    # 或者先获取所有记录，然后在Python中过滤
                    pass  # 暂时跳过脚本类型过滤
                
                if status:
                    filters.append(ScriptExecution.status == status)
                    
                if script_id:
                    filters.append(ScriptExecution.script_id == script_id)

                if execution_id:
                    filters.append(ScriptExecution.execution_id == execution_id)

                if filters:
                    stmt = stmt.filter(and_(*filters))
                
                # 执行查询
                result = await session.execute(stmt)
                executions = result.scalars().all()
                
                # 转换为字典格式
                history = []
                for execution in executions:
                    # 从execution_config中获取脚本信息
                    config = execution.execution_config or {}
                    script_name = config.get("script_name", "未知脚本")
                    execution_script_type = config.get("script_type", "playwright")  # 默认为playwright

                    # 如果指定了script_type过滤，在这里进行过滤
                    if script_type and script_type.lower() != execution_script_type.lower():
                        continue

                    execution_dict = {
                        "id": execution.id,
                        "execution_id": execution.execution_id,
                        "script_id": execution.script_id,
                        "script_name": script_name,
                        "script_type": execution_script_type,
                        "status": execution.status,
                        "start_time": execution.start_time.isoformat() if execution.start_time else None,
                        "end_time": execution.end_time.isoformat() if execution.end_time else None,
                        "duration": execution.duration_seconds,
                        "error_message": execution.error_message,
                        "exit_code": execution.exit_code,
                        "execution_config": execution.execution_config or {},
                        "environment_info": execution.environment_info or {},
                        "performance_metrics": execution.performance_metrics or {},
                        "created_at": execution.created_at.isoformat() if execution.created_at else None,
                        "updated_at": execution.updated_at.isoformat() if execution.updated_at else None,
                    }
                    history.append(execution_dict)
                
                return {
                    "history": history,
                    "count": len(history),
                    "total_available": await self._get_total_executions_count(session, filters),
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"获取执行历史失败: {str(e)}")
            return {
                "history": [],
                "count": 0,
                "total_available": 0,
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
    
    async def get_active_executions(self, script_type: Optional[str] = None) -> Dict[str, Any]:
        """获取活跃的执行记录
        
        Args:
            script_type: 脚本类型过滤 (yaml, playwright)
            
        Returns:
            Dict[str, Any]: 包含活跃执行记录的字典
        """
        try:
            async with db_manager.get_session() as session:
                # 构建查询 - 查找状态为 pending 或 running 的执行
                stmt = (
                    select(ScriptExecution)
                    .filter(ScriptExecution.status.in_(['pending', 'running']))
                    .order_by(desc(ScriptExecution.created_at))
                )
                
                result = await session.execute(stmt)
                executions = result.scalars().all()
                
                # 转换为字典格式
                active_executions = []
                for execution in executions:
                    # 从execution_config中获取脚本信息
                    config = execution.execution_config or {}
                    script_name = config.get("script_name", "未知脚本")
                    execution_script_type = config.get("script_type", "playwright")

                    # 如果指定了script_type过滤，在这里进行过滤
                    if script_type and script_type.lower() != execution_script_type.lower():
                        continue

                    execution_dict = {
                        "id": execution.id,
                        "execution_id": execution.execution_id,
                        "script_id": execution.script_id,
                        "script_name": script_name,
                        "script_type": execution_script_type,
                        "status": execution.status,
                        "start_time": execution.start_time.isoformat() if execution.start_time else None,
                        "duration": execution.duration_seconds,
                        "execution_config": execution.execution_config or {},
                        "environment_info": execution.environment_info or {},
                        "created_at": execution.created_at.isoformat() if execution.created_at else None,
                    }
                    active_executions.append(execution_dict)
                
                return {
                    "active_executions": active_executions,
                    "count": len(active_executions),
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"获取活跃执行记录失败: {str(e)}")
            return {
                "active_executions": [],
                "count": 0,
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
    
    async def _get_total_executions_count(self, session, filters: List) -> int:
        """获取执行记录总数"""
        try:
            count_stmt = select(func.count(ScriptExecution.id))

            # 如果有脚本类型过滤，需要join TestScript表
            has_script_type_filter = any(
                hasattr(f.left, 'table') and f.left.table.name == 'test_scripts'
                for f in filters if hasattr(f, 'left')
            )

            if has_script_type_filter:
                count_stmt = count_stmt.join(TestScript)

            if filters:
                count_stmt = count_stmt.filter(and_(*filters))

            result = await session.execute(count_stmt)
            return result.scalar() or 0
        except Exception as e:
            logger.error(f"获取执行记录总数失败: {str(e)}")
            return 0

    async def delete_execution_record(self, execution_id: str) -> int:
        """删除指定的执行记录

        Args:
            execution_id: 执行ID

        Returns:
            int: 删除的记录数量
        """
        try:
            from sqlalchemy import text

            async with db_manager.get_session() as session:
                # 使用原生SQL直接删除，完全绕过ORM关系
                sql = text("DELETE FROM script_executions WHERE execution_id = :execution_id")
                result = await session.execute(sql, {"execution_id": execution_id})
                deleted_count = result.rowcount

                await session.commit()

                if deleted_count > 0:
                    logger.info(f"成功删除执行记录: {execution_id}")
                else:
                    logger.warning(f"未找到执行记录: {execution_id}")

                return deleted_count

        except Exception as e:
            logger.error(f"删除执行记录失败: {str(e)}")
            raise

    async def delete_multiple_execution_records(self, execution_ids: List[str]) -> int:
        """批量删除执行记录

        Args:
            execution_ids: 执行ID列表

        Returns:
            int: 删除的记录数量
        """
        try:
            from sqlalchemy import delete

            async with db_manager.get_session() as session:
                # 直接使用DELETE语句，避免触发关系查询
                stmt = delete(ScriptExecution).where(ScriptExecution.execution_id.in_(execution_ids))
                result = await session.execute(stmt)
                deleted_count = result.rowcount

                await session.commit()

                logger.info(f"成功批量删除 {deleted_count} 条执行记录")
                return deleted_count

        except Exception as e:
            logger.error(f"批量删除执行记录失败: {str(e)}")
            raise


# 创建全局服务实例
execution_history_service = ExecutionHistoryService()
