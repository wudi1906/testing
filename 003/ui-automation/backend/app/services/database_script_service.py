"""
基于数据库的脚本管理服务
替换原有的文件存储系统
"""
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.database.connection import db_manager
from app.database.repositories.script_repository import ScriptRepository
from app.database.models.scripts import TestScript as DBTestScript
from app.models.test_scripts import (
    TestScript, ScriptFormat, ScriptType, ScriptExecutionRecord,
    ScriptSearchRequest, ScriptSearchResponse, ScriptStatistics
)
from app.core.logging import get_logger

logger = get_logger(__name__)


class DatabaseScriptService:
    """基于数据库的脚本管理服务"""
    
    def __init__(self):
        self.script_repo = ScriptRepository()
    
    def _db_to_pydantic(self, db_script: DBTestScript) -> TestScript:
        """将数据库模型转换为Pydantic模型"""
        tags = [tag.tag_name for tag in db_script.tags] if db_script.tags else []
        
        return TestScript(
            id=db_script.id,
            session_id=db_script.session_id or "",
            name=db_script.name,
            description=db_script.description or "",
            script_format=ScriptFormat(db_script.script_format),
            script_type=ScriptType(db_script.script_type),
            content=db_script.content,
            file_path=db_script.file_path or "",
            test_description=db_script.test_description,
            additional_context=db_script.additional_context,
            source_url=db_script.source_url,
            source_image_path=db_script.source_image_path,
            execution_count=db_script.execution_count,
            last_execution_time=db_script.last_execution_time.isoformat() if db_script.last_execution_time else None,
            last_execution_status=db_script.last_execution_status,
            created_at=db_script.created_at.isoformat(),
            updated_at=db_script.updated_at.isoformat(),
            tags=tags,
            category=db_script.category,
            priority=db_script.priority,
            analysis_result_id=db_script.analysis_result_id
        )
    
    def _pydantic_to_db_dict(self, script: TestScript) -> Dict[str, Any]:
        """将Pydantic模型转换为数据库字典"""
        return {
            "id": script.id,
            "session_id": script.session_id,
            "name": script.name,
            "description": script.description,
            "script_format": script.script_format.value,
            "script_type": script.script_type.value,
            "content": script.content,
            "file_path": script.file_path,
            "test_description": script.test_description,
            "additional_context": script.additional_context,
            "source_url": script.source_url,
            "source_image_path": script.source_image_path,
            "execution_count": script.execution_count,
            "last_execution_time": datetime.fromisoformat(script.last_execution_time) if script.last_execution_time else None,
            "last_execution_status": script.last_execution_status,
            "category": script.category,
            "priority": script.priority,
            "analysis_result_id": script.analysis_result_id
        }
    
    async def save_script(self, script: TestScript) -> TestScript:
        """保存脚本到数据库"""
        try:
            async with db_manager.get_session() as session:
                # 检查脚本是否已存在
                existing = await self.script_repo.get_by_id(session, script.id)
                
                if existing:
                    # 更新现有脚本
                    script_data = self._pydantic_to_db_dict(script)
                    script_data.pop('id')  # 移除ID，避免更新主键
                    
                    updated = await self.script_repo.update(session, script.id, **script_data)
                    if not updated:
                        raise Exception(f"更新脚本失败: {script.id}")
                    
                    # 更新标签
                    await self._update_script_tags(session, script.id, script.tags)
                    
                    # 重新获取完整数据
                    result = await self.script_repo.get_by_id_with_tags(session, script.id)
                    updated_script = self._db_to_pydantic(result)

                    # 同步到文件系统
                    await self._sync_script_to_filesystem(updated_script)

                    return updated_script
                else:
                    # 创建新脚本
                    if not script.id:
                        script.id = str(uuid.uuid4())
                    
                    script_data = self._pydantic_to_db_dict(script)
                    created = await self.script_repo.create(session, **script_data)
                    
                    # 添加标签
                    await self._update_script_tags(session, created.id, script.tags)
                    
                    # 重新获取完整数据
                    result = await self.script_repo.get_by_id_with_tags(session, created.id)
                    new_script = self._db_to_pydantic(result)

                    # 同步到文件系统
                    await self._sync_script_to_filesystem(new_script)

                    return new_script
                    
        except Exception as e:
            logger.error(f"保存脚本失败: {e}")
            raise
    
    async def get_script(self, script_id: str) -> Optional[TestScript]:
        """根据ID获取脚本"""
        try:
            async with db_manager.get_session() as session:
                db_script = await self.script_repo.get_by_id_with_tags(session, script_id)
                if db_script:
                    return self._db_to_pydantic(db_script)
                return None
        except Exception as e:
            logger.error(f"获取脚本失败: {script_id} - {e}")
            raise
    
    async def update_script(self, script_id: str, updates: Dict[str, Any]) -> Optional[TestScript]:
        """更新脚本（同时更新数据库和文件系统）"""
        try:
            updated_script = None
            content_updated = 'content' in updates

            # 数据库操作 - 使用较短的事务
            async with db_manager.get_session() as session:
                # 获取原始脚本信息
                original_script = await self.script_repo.get_by_id_with_tags(session, script_id)
                if not original_script:
                    return None

                # 处理标签更新
                tags = updates.pop('tags', None)

                # 更新脚本基本信息
                if updates:
                    updated = await self.script_repo.update(session, script_id, **updates)
                    if not updated:
                        return None

                # 更新标签
                if tags is not None:
                    await self._update_script_tags(session, script_id, tags)

                # 获取更新后的脚本
                result = await self.script_repo.get_by_id_with_tags(session, script_id)
                updated_script = self._db_to_pydantic(result) if result else None

            # 文件系统同步操作 - 在事务外执行，避免长时间锁定
            if updated_script and content_updated:
                try:
                    await self._sync_script_to_filesystem(updated_script)
                except Exception as sync_error:
                    logger.error(f"文件系统同步失败，但数据库更新成功: {script_id} - {sync_error}")
                    # 不抛出异常，因为数据库更新已成功

            return updated_script

        except Exception as e:
            logger.error(f"更新脚本失败: {script_id} - {e}")
            raise
    
    async def delete_script(self, script_id: str) -> bool:
        """删除脚本"""
        try:
            async with db_manager.get_session() as session:
                return await self.script_repo.delete(session, script_id)
        except Exception as e:
            logger.error(f"删除脚本失败: {script_id} - {e}")
            raise
    
    async def search_scripts(self, request: ScriptSearchRequest) -> ScriptSearchResponse:
        """搜索脚本"""
        try:
            async with db_manager.get_session() as session:
                scripts, total_count = await self.script_repo.search_scripts(session, request)
                
                pydantic_scripts = [self._db_to_pydantic(script) for script in scripts]
                has_more = (request.offset + len(pydantic_scripts)) < total_count
                
                return ScriptSearchResponse(
                    scripts=pydantic_scripts,
                    total_count=total_count,
                    has_more=has_more
                )
        except Exception as e:
            logger.error(f"搜索脚本失败: {e}")
            raise
    
    async def get_script_statistics(self) -> ScriptStatistics:
        """获取脚本统计信息"""
        try:
            async with db_manager.get_session() as session:
                return await self.script_repo.get_statistics(session)
        except Exception as e:
            logger.error(f"获取脚本统计失败: {e}")
            raise
    
    async def _update_script_tags(self, session, script_id: str, tags: List[str]):
        """更新脚本标签"""
        # 获取现有标签
        existing_script = await self.script_repo.get_by_id_with_tags(session, script_id)
        if not existing_script:
            return
        
        existing_tags = {tag.tag_name for tag in existing_script.tags}
        new_tags = set(tags)
        
        # 添加新标签
        for tag in new_tags - existing_tags:
            await self.script_repo.add_tag(session, script_id, tag)
        
        # 移除不需要的标签
        for tag in existing_tags - new_tags:
            await self.script_repo.remove_tag(session, script_id, tag)
    
    async def create_script_from_analysis(
        self,
        session_id: str,
        name: str,
        description: str,
        content: str,
        script_format: ScriptFormat,
        script_type: ScriptType,
        test_description: str,
        file_path: str,
        additional_context: Optional[str] = None,
        source_url: Optional[str] = None,
        source_image_path: Optional[str] = None,
        analysis_result_id: Optional[str] = None,

    ) -> TestScript:
        """从分析结果创建脚本"""
        # 确保会话存在，如果不存在则创建
        await self._ensure_session_exists(session_id)

        script = TestScript(
            id=str(uuid.uuid4()),
            session_id=session_id,
            name=name,
            description=description,
            script_format=script_format,
            script_type=script_type,
            content=content,
            file_path=file_path,
            test_description=test_description,
            additional_context=additional_context,
            source_url=source_url,
            source_image_path=source_image_path,
            analysis_result_id=analysis_result_id
        )

        return await self.save_script(script)

    async def _ensure_session_exists(self, session_id: str) -> None:
        """确保会话存在，如果不存在则创建"""
        try:
            from app.database.models.sessions import Session
            from app.database.connection import db_manager

            async with db_manager.get_session() as db_session:
                # 检查会话是否存在
                existing_session = await db_session.get(Session, session_id)

                if not existing_session:
                    # 创建新会话
                    new_session = Session(
                        id=session_id,
                        project_id=None,
                        session_type="image_analysis",  # 使用正确的枚举值
                        status="pending",  # 使用正确的枚举值
                        platform="web",
                        request_data={"auto_created": True, "created_by": "script_database_saver"}
                    )

                    db_session.add(new_session)
                    await db_session.commit()
                    logger.info(f"自动创建会话: {session_id}")

        except Exception as e:
            logger.warning(f"确保会话存在时发生错误: {e}")

    async def _sync_script_to_filesystem(self, script: TestScript):
        """同步脚本到文件系统和工作空间（异步执行，不阻塞数据库事务）"""
        try:
            from app.utils.file_utils import sync_script_to_workspace

            # 使用工具函数同步脚本到工作空间和存储目录
            storage_file_path, workspace_file_path = await sync_script_to_workspace(
                script_name=script.name,
                script_content=script.content,
                script_format=script.script_format.value,
                old_file_path=script.file_path if script.file_path != "" else None
            )

            # 异步更新数据库中的文件路径（如果路径发生变化）
            if script.file_path != storage_file_path:
                # 使用独立的数据库会话，避免影响主事务
                try:
                    async with db_manager.get_session() as session:
                        await self.script_repo.update(session, script.id, file_path=storage_file_path)
                    logger.info(f"更新数据库文件路径: {script.id} -> {storage_file_path}")
                except Exception as e:
                    logger.error(f"更新数据库文件路径失败: {script.id} - {e}")

        except Exception as e:
            logger.error(f"同步脚本到文件系统失败: {script.id} - {e}")
            # 不抛出异常，避免影响主要的数据库更新操作

    async def get_script_executions(self, script_id: str, limit: int = 20) -> List[ScriptExecutionRecord]:
        """获取脚本执行记录（暂时返回空列表，待实现执行记录功能）"""
        # TODO: 实现执行记录查询
        return []

    async def execute_script(self, script_id: str, execution_config: Dict[str, Any] = None,
                           environment_variables: Dict[str, str] = None) -> Dict[str, Any]:
        """执行脚本

        Args:
            script_id: 脚本ID
            execution_config: 执行配置
            environment_variables: 环境变量

        Returns:
            执行结果信息
        """
        try:
            # 获取脚本
            script = await self.get_script(script_id)
            if not script:
                raise ValueError(f"脚本不存在: {script_id}")

            # 调用脚本执行服务
            from app.api.v1.endpoints.web.test_script_execution import create_script_execution_session

            # 创建执行会话
            session_id = await create_script_execution_session(
                script_content=script.content,
                script_name=script.name,
                execution_config=execution_config or {},
                environment_variables=environment_variables or {}
            )

            logger.info(f"脚本执行启动: {script_id} - {session_id}")
            return {
                "execution_id": session_id,
                "session_id": session_id,
                "script_id": script_id,
                "status": "started",
                "message": "脚本执行已启动",
                "sse_endpoint": f"/api/v1/web/execution/stream/{session_id}"
            }

        except Exception as e:
            logger.error(f"执行脚本失败: {script_id} - {e}")
            raise


# 全局数据库脚本服务实例
database_script_service = DatabaseScriptService()
