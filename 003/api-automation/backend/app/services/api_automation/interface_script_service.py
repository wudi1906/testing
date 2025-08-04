"""
接口脚本管理服务
专门处理接口和测试脚本的关联管理

核心功能：
1. 接口脚本查询和管理
2. 脚本生成状态跟踪
3. 脚本执行统计
4. 接口测试覆盖率分析
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from loguru import logger
import uuid
import asyncio
import json
from pathlib import Path

from tortoise.transactions import in_transaction
from tortoise.expressions import Q

from app.models.api_automation import (
    ApiInterface, TestScript, ApiDocument,
    ScriptGenerationTask, WorkflowSession
)
from app.core.enums import SessionStatus


class InterfaceScriptService:
    """接口脚本管理服务"""
    
    def __init__(self):
        self.service_name = "InterfaceScriptService"
    
    async def get_all_scripts(
        self,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        status: Optional[str] = None,
        framework: Optional[str] = None,
        interface_id: Optional[str] = None,
        document_id: Optional[str] = None,
        include_inactive: bool = False
    ) -> Dict[str, Any]:
        """获取所有脚本列表，支持分页和筛选"""
        try:
            # 构建查询条件
            query_filter = Q()

            if not include_inactive:
                query_filter &= Q(is_active=True)

            if search:
                query_filter &= (
                    Q(name__icontains=search) |
                    Q(description__icontains=search) |
                    Q(script_id__icontains=search)
                )

            if status:
                query_filter &= Q(status=status)

            if framework:
                query_filter &= Q(framework=framework)

            if interface_id:
                interface = await ApiInterface.filter(interface_id=interface_id).first()
                if interface:
                    query_filter &= Q(interface=interface)

            if document_id:
                document = await ApiDocument.filter(doc_id=document_id).first()
                if document:
                    query_filter &= Q(document=document)

            # 获取总数
            total = await TestScript.filter(query_filter).count()

            # 分页查询
            offset = (page - 1) * page_size
            scripts = await TestScript.filter(query_filter).select_related(
                'interface', 'document'
            ).offset(offset).limit(page_size).order_by('-created_at')

            # 格式化脚本数据
            script_list = []
            for script in scripts:
                script_data = {
                    "script_id": script.script_id,
                    "name": script.name,
                    "description": script.description,
                    "file_name": script.file_name,
                    "framework": script.framework,
                    "language": script.language,
                    "version": script.version,
                    "status": script.status,
                    "is_executable": script.is_executable,
                    "execution_count": script.execution_count,
                    "success_count": script.success_count,
                    "last_execution_time": script.last_execution_time,
                    "generated_by": script.generated_by,
                    "generation_session_id": script.generation_session_id,
                    "code_quality_score": script.code_quality_score,
                    "test_coverage_score": script.test_coverage_score,
                    "complexity_score": script.complexity_score,
                    "interface_info": {
                        "interface_id": script.interface.interface_id if script.interface else None,
                        "name": script.interface.name if script.interface else None,
                        "path": script.interface.path if script.interface else None,
                        "method": script.interface.method.value if script.interface else None
                    } if script.interface else None,
                    "document_info": {
                        "doc_id": script.document.doc_id if script.document else None,
                        "file_name": script.document.file_name if script.document else None
                    } if script.document else None,
                    "created_at": script.created_at,
                    "updated_at": script.updated_at
                }
                script_list.append(script_data)

            return {
                "scripts": script_list,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size
            }

        except Exception as e:
            logger.error(f"获取脚本列表失败: {e}")
            raise

    async def get_interface_scripts(
        self,
        interface_id: str,
        include_inactive: bool = False
    ) -> Dict[str, Any]:
        """获取接口的所有脚本"""
        try:
            # 获取接口信息
            interface = await ApiInterface.filter(interface_id=interface_id).first()
            if not interface:
                raise ValueError(f"接口不存在: {interface_id}")
            
            # 构建查询条件
            query_filter = Q(interface=interface)
            if not include_inactive:
                query_filter &= Q(is_active=True)
            
            # 获取脚本列表
            scripts = await TestScript.filter(query_filter).order_by('-created_at')
            
            # 构建返回数据
            script_list = []
            for script in scripts:
                script_data = {
                    "script_id": script.script_id,
                    "name": script.name,
                    "description": script.description,
                    "file_name": script.file_name,
                    "framework": script.framework,
                    "language": script.language,
                    "version": script.version,
                    "status": script.status,
                    "is_executable": script.is_executable,
                    "execution_count": script.execution_count,
                    "success_count": script.success_count,
                    "last_execution_time": script.last_execution_time,
                    "generated_by": script.generated_by,
                    "generation_session_id": script.generation_session_id,
                    "code_quality_score": script.code_quality_score,
                    "test_coverage_score": script.test_coverage_score,
                    "complexity_score": script.complexity_score,
                    "created_at": script.created_at,
                    "updated_at": script.updated_at
                }
                script_list.append(script_data)
            
            return {
                "interface_id": interface_id,
                "interface_name": interface.name,
                "interface_path": interface.path,
                "interface_method": interface.method,
                "total_scripts": len(script_list),
                "active_scripts": len([s for s in script_list if s["status"] == "ACTIVE"]),
                "scripts": script_list
            }
            
        except Exception as e:
            logger.error(f"获取接口脚本失败: {e}")
            raise
    
    async def get_script_detail(self, script_id: str) -> Dict[str, Any]:
        """获取脚本详细信息"""
        try:
            script = await TestScript.filter(script_id=script_id).select_related(
                'interface', 'document'
            ).first()
            
            if not script:
                raise ValueError(f"脚本不存在: {script_id}")
            
            return {
                "script_id": script.script_id,
                "name": script.name,
                "description": script.description,
                "file_name": script.file_name,
                "content": script.content,
                "file_path": script.file_path,
                "framework": script.framework,
                "language": script.language,
                "version": script.version,
                "dependencies": script.dependencies,
                "requirements": script.requirements,
                "timeout": script.timeout,
                "retry_count": script.retry_count,
                "parallel_execution": script.parallel_execution,
                "status": script.status,
                "is_executable": script.is_executable,
                "execution_count": script.execution_count,
                "success_count": script.success_count,
                "last_execution_time": script.last_execution_time,
                "generated_by": script.generated_by,
                "generation_session_id": script.generation_session_id,
                "code_quality_score": script.code_quality_score,
                "test_coverage_score": script.test_coverage_score,
                "complexity_score": script.complexity_score,
                "interface": {
                    "interface_id": script.interface.interface_id,
                    "name": script.interface.name,
                    "path": script.interface.path,
                    "method": script.interface.method
                } if script.interface else None,
                "document": {
                    "doc_id": script.document.doc_id,
                    "file_name": script.document.file_name,
                    "api_title": script.document.api_info.get("title", "")
                } if script.document else None,
                "created_at": script.created_at,
                "updated_at": script.updated_at
            }
            
        except Exception as e:
            logger.error(f"获取脚本详情失败: {e}")
            raise
    
    async def update_script_status(
        self, 
        script_id: str, 
        status: str, 
        is_executable: Optional[bool] = None
    ) -> bool:
        """更新脚本状态"""
        try:
            async with in_transaction():
                script = await TestScript.filter(script_id=script_id).select_related('interface').first()
                if not script:
                    raise ValueError(f"脚本不存在: {script_id}")

                script.status = status
                if is_executable is not None:
                    script.is_executable = is_executable
                script.updated_at = datetime.now()

                await script.save()

                # 更新接口统计
                await self._update_interface_script_count(script.interface.id)
                
                logger.info(f"脚本状态更新成功: {script_id} -> {status}")
                return True
                
        except Exception as e:
            logger.error(f"更新脚本状态失败: {e}")
            raise
    
    async def delete_script(self, script_id: str, soft_delete: bool = True) -> bool:
        """删除脚本"""
        try:
            async with in_transaction():
                script = await TestScript.filter(script_id=script_id).first()
                if not script:
                    raise ValueError(f"脚本不存在: {script_id}")
                
                interface_id = script.interface_id
                
                if soft_delete:
                    # 软删除：标记为非活跃
                    script.is_active = False
                    script.status = "DELETED"
                    script.updated_at = datetime.now()
                    await script.save()
                else:
                    # 硬删除：直接删除记录
                    await script.delete()
                
                # 更新接口统计
                await self._update_interface_script_count(interface_id)
                
                logger.info(f"脚本删除成功: {script_id} (软删除: {soft_delete})")
                return True
                
        except Exception as e:
            logger.error(f"删除脚本失败: {e}")
            raise

    async def batch_update_script_status(
        self,
        script_ids: List[str],
        status: str,
        is_executable: Optional[bool] = None
    ) -> Dict[str, Any]:
        """批量更新脚本状态"""
        try:
            success_count = 0
            failed_count = 0
            failed_scripts = []

            async with in_transaction():
                for script_id in script_ids:
                    try:
                        script = await TestScript.filter(script_id=script_id).first()
                        if script:
                            script.status = status
                            if is_executable is not None:
                                script.is_executable = is_executable
                            script.updated_at = datetime.now()
                            await script.save()
                            success_count += 1
                        else:
                            failed_count += 1
                            failed_scripts.append({"script_id": script_id, "reason": "脚本不存在"})
                    except Exception as e:
                        failed_count += 1
                        failed_scripts.append({"script_id": script_id, "reason": str(e)})

            logger.info(f"批量更新脚本状态完成: 成功 {success_count} 个, 失败 {failed_count} 个")

            return {
                "total": len(script_ids),
                "success_count": success_count,
                "failed_count": failed_count,
                "failed_scripts": failed_scripts,
                "status": status,
                "is_executable": is_executable
            }

        except Exception as e:
            logger.error(f"批量更新脚本状态失败: {e}")
            raise
    
    async def get_interface_script_statistics(self, interface_id: str) -> Dict[str, Any]:
        """获取接口脚本统计信息"""
        try:
            interface = await ApiInterface.filter(interface_id=interface_id).first()
            if not interface:
                raise ValueError(f"接口不存在: {interface_id}")
            
            # 获取脚本统计
            total_scripts = await TestScript.filter(interface=interface).count()
            active_scripts = await TestScript.filter(
                interface=interface, is_active=True
            ).count()
            executable_scripts = await TestScript.filter(
                interface=interface, is_active=True, is_executable=True
            ).count()
            
            # 按框架分组统计
            framework_stats = {}
            scripts = await TestScript.filter(interface=interface, is_active=True)
            for script in scripts:
                framework = script.framework
                if framework not in framework_stats:
                    framework_stats[framework] = {
                        "count": 0,
                        "executable": 0,
                        "total_executions": 0,
                        "total_successes": 0
                    }
                framework_stats[framework]["count"] += 1
                if script.is_executable:
                    framework_stats[framework]["executable"] += 1
                framework_stats[framework]["total_executions"] += script.execution_count
                framework_stats[framework]["total_successes"] += script.success_count
            
            # 计算成功率
            for framework, stats in framework_stats.items():
                if stats["total_executions"] > 0:
                    stats["success_rate"] = stats["total_successes"] / stats["total_executions"]
                else:
                    stats["success_rate"] = 0.0
            
            # 最近生成的脚本
            recent_scripts = await TestScript.filter(
                interface=interface, is_active=True
            ).order_by('-created_at').limit(5)
            
            recent_script_list = [
                {
                    "script_id": script.script_id,
                    "name": script.name,
                    "framework": script.framework,
                    "created_at": script.created_at
                }
                for script in recent_scripts
            ]
            
            return {
                "interface_id": interface_id,
                "interface_name": interface.name,
                "total_scripts": total_scripts,
                "active_scripts": active_scripts,
                "executable_scripts": executable_scripts,
                "framework_statistics": framework_stats,
                "recent_scripts": recent_script_list,
                "last_script_generation_time": interface.last_script_generation_time
            }
            
        except Exception as e:
            logger.error(f"获取接口脚本统计失败: {e}")
            raise
    
    async def get_script_generation_history(
        self, 
        interface_id: str, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """获取脚本生成历史"""
        try:
            # 获取接口信息
            interface = await ApiInterface.filter(interface_id=interface_id).first()
            if not interface:
                raise ValueError(f"接口不存在: {interface_id}")
            
            # 获取该接口的脚本创建历史（按生成会话分组）
            scripts = await TestScript.filter(
                interface=interface
            ).order_by('-created_at').limit(limit * 3)  # 获取更多记录用于分组
            
            # 按生成会话分组
            session_groups = {}
            for script in scripts:
                session_id = script.generation_session_id or "manual"
                if session_id not in session_groups:
                    session_groups[session_id] = {
                        "session_id": session_id,
                        "scripts": [],
                        "created_at": script.created_at,
                        "generated_by": script.generated_by
                    }
                session_groups[session_id]["scripts"].append({
                    "script_id": script.script_id,
                    "name": script.name,
                    "framework": script.framework,
                    "status": script.status
                })
            
            # 转换为历史记录格式
            history = []
            for session_data in sorted(session_groups.values(), 
                                     key=lambda x: x["created_at"], reverse=True)[:limit]:
                history_item = {
                    "session_id": session_data["session_id"],
                    "generated_by": session_data["generated_by"],
                    "script_count": len(session_data["scripts"]),
                    "scripts": session_data["scripts"],
                    "created_at": session_data["created_at"]
                }
                history.append(history_item)
            
            return history
            
        except Exception as e:
            logger.error(f"获取脚本生成历史失败: {e}")
            raise
    
    async def _update_interface_script_count(self, interface_id: int) -> None:
        """更新接口的脚本数量统计"""
        try:
            interface = await ApiInterface.filter(id=interface_id).first()
            if interface:
                script_count = await TestScript.filter(
                    interface=interface, is_active=True
                ).count()
                
                interface.test_script_count = script_count
                await interface.save()
                
        except Exception as e:
            logger.error(f"更新接口脚本统计失败: {e}")
    
    async def batch_update_script_status(
        self, 
        script_ids: List[str], 
        status: str
    ) -> Dict[str, Any]:
        """批量更新脚本状态"""
        try:
            async with in_transaction():
                updated_count = 0
                failed_scripts = []
                
                for script_id in script_ids:
                    try:
                        script = await TestScript.filter(script_id=script_id).first()
                        if script:
                            script.status = status
                            script.updated_at = datetime.now()
                            await script.save()
                            updated_count += 1
                        else:
                            failed_scripts.append(script_id)
                    except Exception as e:
                        logger.error(f"更新脚本 {script_id} 失败: {e}")
                        failed_scripts.append(script_id)
                
                return {
                    "total_requested": len(script_ids),
                    "updated_count": updated_count,
                    "failed_count": len(failed_scripts),
                    "failed_scripts": failed_scripts
                }
                
        except Exception as e:
            logger.error(f"批量更新脚本状态失败: {e}")
            raise
    
    async def get_document_script_overview(self, document_id: str) -> Dict[str, Any]:
        """获取文档的脚本概览"""
        try:
            document = await ApiDocument.filter(doc_id=document_id).first()
            if not document:
                raise ValueError(f"文档不存在: {document_id}")
            
            # 获取文档下的所有接口
            interfaces = await ApiInterface.filter(document=document)
            
            # 统计脚本信息
            total_interfaces = len(interfaces)
            interfaces_with_scripts = 0
            total_scripts = 0
            
            interface_script_map = {}
            
            for interface in interfaces:
                script_count = await TestScript.filter(
                    interface=interface, is_active=True
                ).count()
                
                if script_count > 0:
                    interfaces_with_scripts += 1
                
                total_scripts += script_count
                
                interface_script_map[interface.interface_id] = {
                    "interface_name": interface.name,
                    "path": interface.path,
                    "method": interface.method,
                    "script_count": script_count
                }
            
            # 计算覆盖率
            coverage_rate = (interfaces_with_scripts / total_interfaces * 100) if total_interfaces > 0 else 0
            
            return {
                "document_id": document_id,
                "document_name": document.file_name,
                "total_interfaces": total_interfaces,
                "interfaces_with_scripts": interfaces_with_scripts,
                "total_scripts": total_scripts,
                "coverage_rate": round(coverage_rate, 2),
                "interface_script_map": interface_script_map
            }
            
        except Exception as e:
            logger.error(f"获取文档脚本概览失败: {e}")
            raise

    # ==================== 脚本执行相关方法 ====================

    async def execute_scripts(
        self,
        script_ids: List[str],
        execution_config: Dict[str, Any],
        environment: str = "test",
        timeout: int = 300,
        parallel: bool = False,
        max_workers: int = 1
    ) -> Dict[str, Any]:
        """执行多个脚本"""
        try:
            # 验证脚本存在性和可执行性
            scripts = []
            for script_id in script_ids:
                script = await TestScript.filter(
                    script_id=script_id,
                    is_active=True,
                    is_executable=True
                ).select_related('interface', 'document').first()

                if not script:
                    raise ValueError(f"脚本不存在或不可执行: {script_id}")

                scripts.append(script)

            # 生成执行ID和会话ID
            execution_id = str(uuid.uuid4())
            session_id = str(uuid.uuid4())

            # 创建执行记录
            execution_record = await self._create_execution_record(
                execution_id=execution_id,
                session_id=session_id,
                scripts=scripts,
                execution_config=execution_config,
                environment=environment,
                timeout=timeout,
                parallel=parallel,
                max_workers=max_workers
            )

            # 启动后台执行任务
            from app.core.bgtask import BgTasks
            await BgTasks.add_task(
                self._execute_scripts_background,
                execution_id,
                scripts,
                execution_config,
                environment,
                timeout,
                parallel,
                max_workers
            )

            logger.info(f"脚本执行任务已启动: execution_id={execution_id}, script_count={len(scripts)}")

            return {
                "execution_id": execution_id,
                "session_id": session_id,
                "script_count": len(scripts),
                "message": "脚本执行任务已启动",
                "status": "CREATED"
            }

        except Exception as e:
            logger.error(f"启动脚本执行失败: {e}")
            raise

    async def execute_single_script(
        self,
        script_id: str,
        execution_config: Dict[str, Any],
        environment: str = "test",
        timeout: int = 300
    ) -> Dict[str, Any]:
        """执行单个脚本"""
        return await self.execute_scripts(
            script_ids=[script_id],
            execution_config=execution_config,
            environment=environment,
            timeout=timeout,
            parallel=False,
            max_workers=1
        )

    async def get_script_execution_history(
        self,
        script_id: str,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """获取脚本执行历史"""
        try:
            # 验证脚本存在
            script = await TestScript.filter(script_id=script_id).first()
            if not script:
                raise ValueError(f"脚本不存在: {script_id}")

            # 这里需要从执行记录表中查询，暂时返回模拟数据
            # TODO: 实现真实的执行历史查询
            offset = (page - 1) * page_size

            # 模拟执行历史数据
            executions = [
                {
                    "execution_id": f"exec_{i}",
                    "session_id": f"session_{i}",
                    "status": "COMPLETED" if i % 3 != 0 else "FAILED",
                    "start_time": datetime.now() - timedelta(days=i),
                    "end_time": datetime.now() - timedelta(days=i, hours=-1),
                    "duration": 3600,
                    "environment": "test",
                    "success_rate": 85.5 if i % 3 != 0 else 0.0
                }
                for i in range(offset, min(offset + page_size, 50))
            ]

            return {
                "script_id": script_id,
                "script_name": script.name,
                "executions": executions,
                "total": 50,  # 模拟总数
                "page": page,
                "page_size": page_size
            }

        except Exception as e:
            logger.error(f"获取脚本执行历史失败: {e}")
            raise

    async def get_execution_detail(self, execution_id: str) -> Dict[str, Any]:
        """获取执行详情"""
        try:
            # TODO: 从真实的执行记录表中查询
            # 暂时返回模拟数据
            return {
                "execution_id": execution_id,
                "session_id": f"session_{execution_id}",
                "status": "COMPLETED",
                "start_time": datetime.now() - timedelta(hours=1),
                "end_time": datetime.now(),
                "duration": 3600,
                "environment": "test",
                "script_count": 3,
                "success_count": 2,
                "failed_count": 1,
                "success_rate": 66.7,
                "execution_config": {
                    "framework": "pytest",
                    "parallel": False,
                    "timeout": 300
                },
                "scripts": [
                    {
                        "script_id": "script_1",
                        "script_name": "用户登录测试",
                        "status": "PASSED",
                        "duration": 1200,
                        "error_message": None
                    },
                    {
                        "script_id": "script_2",
                        "script_name": "用户注册测试",
                        "status": "PASSED",
                        "duration": 1500,
                        "error_message": None
                    },
                    {
                        "script_id": "script_3",
                        "script_name": "密码重置测试",
                        "status": "FAILED",
                        "duration": 300,
                        "error_message": "连接超时"
                    }
                ]
            }

        except Exception as e:
            logger.error(f"获取执行详情失败: {e}")
            raise

    async def get_execution_logs(
        self,
        execution_id: str,
        page: int = 1,
        page_size: int = 100
    ) -> Dict[str, Any]:
        """获取执行日志"""
        try:
            # TODO: 从真实的日志表中查询
            # 暂时返回模拟数据
            offset = (page - 1) * page_size

            logs = [
                {
                    "log_id": f"log_{i}",
                    "timestamp": datetime.now() - timedelta(minutes=i),
                    "level": "INFO" if i % 4 != 0 else "ERROR",
                    "message": f"执行步骤 {i}: 测试用例运行中..." if i % 4 != 0 else f"执行步骤 {i}: 发生错误",
                    "source": "script_executor",
                    "script_id": f"script_{i % 3 + 1}"
                }
                for i in range(offset, min(offset + page_size, 200))
            ]

            return {
                "execution_id": execution_id,
                "logs": logs,
                "total": 200,  # 模拟总数
                "page": page,
                "page_size": page_size
            }

        except Exception as e:
            logger.error(f"获取执行日志失败: {e}")
            raise

    async def stop_execution(self, execution_id: str) -> Dict[str, Any]:
        """停止执行"""
        try:
            # TODO: 实现真实的执行停止逻辑
            logger.info(f"停止执行: {execution_id}")

            return {
                "execution_id": execution_id,
                "status": "STOPPED",
                "message": "执行已停止",
                "stopped_at": datetime.now()
            }

        except Exception as e:
            logger.error(f"停止执行失败: {e}")
            raise

    # ==================== 私有辅助方法 ====================

    async def _create_execution_record(
        self,
        execution_id: str,
        session_id: str,
        scripts: List,
        execution_config: Dict[str, Any],
        environment: str,
        timeout: int,
        parallel: bool,
        max_workers: int
    ) -> Dict[str, Any]:
        """创建执行记录"""
        try:
            # TODO: 创建真实的执行记录到数据库
            # 这里暂时只记录日志
            logger.info(f"创建执行记录: execution_id={execution_id}, script_count={len(scripts)}")

            return {
                "execution_id": execution_id,
                "session_id": session_id,
                "script_ids": [script.script_id for script in scripts],
                "status": "CREATED",
                "created_at": datetime.now()
            }

        except Exception as e:
            logger.error(f"创建执行记录失败: {e}")
            raise

    async def _execute_scripts_background(
        self,
        execution_id: str,
        scripts: List,
        execution_config: Dict[str, Any],
        environment: str,
        timeout: int,
        parallel: bool,
        max_workers: int
    ):
        """后台执行脚本的任务函数"""
        try:
            logger.info(f"开始后台执行脚本: execution_id={execution_id}")

            # 更新执行状态为处理中
            await self._update_execution_status(execution_id, "PROCESSING")

            # 准备执行环境
            execution_dir = await self._prepare_execution_environment(execution_id, scripts)

            # 执行脚本
            if parallel and len(scripts) > 1:
                results = await self._execute_scripts_parallel(
                    execution_id, scripts, execution_config, execution_dir, timeout, max_workers
                )
            else:
                results = await self._execute_scripts_sequential(
                    execution_id, scripts, execution_config, execution_dir, timeout
                )

            # 分析结果
            analysis = await self._analyze_execution_results(execution_id, results)

            # 生成报告
            await self._generate_execution_report(execution_id, results, analysis)

            # 更新执行状态为完成
            await self._update_execution_status(execution_id, "COMPLETED")

            logger.info(f"脚本执行完成: execution_id={execution_id}")

        except Exception as e:
            logger.error(f"后台执行脚本失败: execution_id={execution_id}, error={str(e)}")
            await self._update_execution_status(execution_id, "FAILED", str(e))

    async def _update_execution_status(
        self,
        execution_id: str,
        status: str,
        error_message: str = None
    ):
        """更新执行状态"""
        try:
            # TODO: 更新真实的执行记录状态
            logger.info(f"更新执行状态: execution_id={execution_id}, status={status}")
            if error_message:
                logger.error(f"执行错误: {error_message}")

        except Exception as e:
            logger.error(f"更新执行状态失败: {e}")

    async def _prepare_execution_environment(
        self,
        execution_id: str,
        scripts: List
    ) -> Path:
        """准备执行环境"""
        try:
            # 创建执行目录
            execution_dir = Path(f"./generated_tests/execution_{execution_id}")
            execution_dir.mkdir(parents=True, exist_ok=True)

            # 写入脚本文件
            for script in scripts:
                script_file = execution_dir / f"{script.script_id}.py"
                script_file.write_text(script.content, encoding='utf-8')

            logger.info(f"执行环境准备完成: {execution_dir}")
            return execution_dir

        except Exception as e:
            logger.error(f"准备执行环境失败: {e}")
            raise

    async def _execute_scripts_sequential(
        self,
        execution_id: str,
        scripts: List,
        execution_config: Dict[str, Any],
        execution_dir: Path,
        timeout: int
    ) -> List[Dict[str, Any]]:
        """顺序执行脚本"""
        try:
            results = []

            for script in scripts:
                logger.info(f"执行脚本: {script.script_id}")

                script_file = execution_dir / f"{script.script_id}.py"

                # 构建pytest命令
                cmd = [
                    "python", "-m", "pytest",
                    str(script_file),
                    "-v",
                    "--tb=short"
                ]

                start_time = datetime.now()

                try:
                    # 执行脚本
                    process = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                        cwd=execution_dir
                    )

                    stdout, stderr = await asyncio.wait_for(
                        process.communicate(),
                        timeout=timeout
                    )

                    end_time = datetime.now()
                    duration = (end_time - start_time).total_seconds()

                    # 解析结果
                    success = process.returncode == 0

                    result = {
                        "script_id": script.script_id,
                        "script_name": script.name,
                        "status": "PASSED" if success else "FAILED",
                        "start_time": start_time,
                        "end_time": end_time,
                        "duration": duration,
                        "stdout": stdout.decode('utf-8') if stdout else "",
                        "stderr": stderr.decode('utf-8') if stderr else "",
                        "return_code": process.returncode
                    }

                    results.append(result)

                    # 更新脚本执行统计
                    await self._update_script_execution_stats(script.script_id, success)

                except asyncio.TimeoutError:
                    end_time = datetime.now()
                    duration = (end_time - start_time).total_seconds()

                    result = {
                        "script_id": script.script_id,
                        "script_name": script.name,
                        "status": "TIMEOUT",
                        "start_time": start_time,
                        "end_time": end_time,
                        "duration": duration,
                        "stdout": "",
                        "stderr": "执行超时",
                        "return_code": -1
                    }

                    results.append(result)
                    await self._update_script_execution_stats(script.script_id, False)

                except Exception as e:
                    end_time = datetime.now()
                    duration = (end_time - start_time).total_seconds()

                    result = {
                        "script_id": script.script_id,
                        "script_name": script.name,
                        "status": "ERROR",
                        "start_time": start_time,
                        "end_time": end_time,
                        "duration": duration,
                        "stdout": "",
                        "stderr": str(e),
                        "return_code": -1
                    }

                    results.append(result)
                    await self._update_script_execution_stats(script.script_id, False)

            return results

        except Exception as e:
            logger.error(f"顺序执行脚本失败: {e}")
            raise

    async def _execute_scripts_parallel(
        self,
        execution_id: str,
        scripts: List,
        execution_config: Dict[str, Any],
        execution_dir: Path,
        timeout: int,
        max_workers: int
    ) -> List[Dict[str, Any]]:
        """并行执行脚本"""
        try:
            # TODO: 实现真正的并行执行
            # 暂时使用顺序执行
            logger.info(f"并行执行功能开发中，暂时使用顺序执行")
            return await self._execute_scripts_sequential(
                execution_id, scripts, execution_config, execution_dir, timeout
            )

        except Exception as e:
            logger.error(f"并行执行脚本失败: {e}")
            raise

    async def _update_script_execution_stats(self, script_id: str, success: bool):
        """更新脚本执行统计"""
        try:
            async with in_transaction():
                script = await TestScript.filter(script_id=script_id).first()
                if script:
                    script.execution_count += 1
                    if success:
                        script.success_count += 1
                    script.last_execution_time = datetime.now()
                    await script.save()

        except Exception as e:
            logger.error(f"更新脚本执行统计失败: {e}")

    async def _analyze_execution_results(
        self,
        execution_id: str,
        results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """分析执行结果"""
        try:
            total_scripts = len(results)
            passed_scripts = len([r for r in results if r["status"] == "PASSED"])
            failed_scripts = len([r for r in results if r["status"] == "FAILED"])
            timeout_scripts = len([r for r in results if r["status"] == "TIMEOUT"])
            error_scripts = len([r for r in results if r["status"] == "ERROR"])

            success_rate = (passed_scripts / total_scripts * 100) if total_scripts > 0 else 0

            total_duration = sum(r["duration"] for r in results)
            avg_duration = total_duration / total_scripts if total_scripts > 0 else 0

            analysis = {
                "execution_id": execution_id,
                "total_scripts": total_scripts,
                "passed_scripts": passed_scripts,
                "failed_scripts": failed_scripts,
                "timeout_scripts": timeout_scripts,
                "error_scripts": error_scripts,
                "success_rate": round(success_rate, 2),
                "total_duration": round(total_duration, 2),
                "average_duration": round(avg_duration, 2),
                "analysis_time": datetime.now()
            }

            logger.info(f"执行结果分析完成: {analysis}")
            return analysis

        except Exception as e:
            logger.error(f"分析执行结果失败: {e}")
            raise

    async def _generate_execution_report(
        self,
        execution_id: str,
        results: List[Dict[str, Any]],
        analysis: Dict[str, Any]
    ):
        """生成执行报告"""
        try:
            # 生成简单的JSON报告
            report_dir = Path(f"./reports/execution_{execution_id}")
            report_dir.mkdir(parents=True, exist_ok=True)

            report_data = {
                "execution_id": execution_id,
                "analysis": analysis,
                "results": results,
                "generated_at": datetime.now().isoformat()
            }

            report_file = report_dir / "execution_report.json"
            report_file.write_text(
                json.dumps(report_data, indent=2, ensure_ascii=False, default=str),
                encoding='utf-8'
            )

            logger.info(f"执行报告生成完成: {report_file}")

        except Exception as e:
            logger.error(f"生成执行报告失败: {e}")
            # 不抛出异常，避免影响主流程
