"""
测试脚本仓库
提供脚本相关的数据访问操作
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from app.database.models.scripts import TestScript, ScriptTag, ScriptRelationship
from app.models.test_scripts import ScriptSearchRequest, ScriptStatistics
from .base import BaseRepository
from app.core.logging import get_logger

logger = get_logger(__name__)


class ScriptRepository(BaseRepository[TestScript]):
    """测试脚本仓库"""
    
    def __init__(self):
        super().__init__(TestScript)
    
    async def get_by_id_with_tags(self, session: AsyncSession, script_id: str) -> Optional[TestScript]:
        """获取脚本及其标签"""
        try:
            result = await session.execute(
                select(TestScript)
                .options(selectinload(TestScript.tags))
                .where(TestScript.id == script_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"获取脚本及标签失败: {e}")
            raise
    
    async def search_scripts(
        self, 
        session: AsyncSession, 
        request: ScriptSearchRequest
    ) -> tuple[List[TestScript], int]:
        """搜索脚本"""
        try:
            # 构建基础查询
            query = select(TestScript).options(selectinload(TestScript.tags))
            count_query = select(func.count(TestScript.id))
            
            # 应用过滤条件
            conditions = []
            
            # 关键词搜索
            if request.query:
                keyword = f"%{request.query}%"
                conditions.append(
                    or_(
                        TestScript.name.like(keyword),
                        TestScript.description.like(keyword),
                        TestScript.test_description.like(keyword),
                        TestScript.additional_context.like(keyword)
                    )
                )
            
            # 格式过滤
            if request.script_format:
                conditions.append(TestScript.script_format == request.script_format)
            
            # 类型过滤
            if request.script_type:
                conditions.append(TestScript.script_type == request.script_type)
            
            # 分类过滤
            if request.category:
                conditions.append(TestScript.category == request.category)
            
            # 日期过滤
            if request.date_from:
                conditions.append(TestScript.created_at >= request.date_from)
            
            if request.date_to:
                conditions.append(TestScript.created_at <= request.date_to)
            
            # 标签过滤
            if request.tags:
                # 子查询：查找包含指定标签的脚本ID
                tag_subquery = (
                    select(ScriptTag.script_id)
                    .where(ScriptTag.tag_name.in_(request.tags))
                    .group_by(ScriptTag.script_id)
                    .having(func.count(ScriptTag.tag_name) >= len(request.tags))
                )
                conditions.append(TestScript.id.in_(tag_subquery))
            
            # 应用所有条件
            if conditions:
                where_clause = and_(*conditions)
                query = query.where(where_clause)
                count_query = count_query.where(where_clause)
            
            # 获取总数
            total_result = await session.execute(count_query)
            total_count = total_result.scalar()
            
            # 排序和分页
            query = query.order_by(TestScript.updated_at.desc())
            query = query.limit(request.limit).offset(request.offset)
            
            # 执行查询
            result = await session.execute(query)
            scripts = result.scalars().all()
            
            return scripts, total_count
            
        except Exception as e:
            logger.error(f"搜索脚本失败: {e}")
            raise
    
    async def get_statistics(self, session: AsyncSession) -> ScriptStatistics:
        """获取脚本统计信息"""
        try:
            # 基础统计
            total_scripts_result = await session.execute(
                select(func.count(TestScript.id))
            )
            total_scripts = total_scripts_result.scalar()
            
            # 按格式统计
            yaml_scripts_result = await session.execute(
                select(func.count(TestScript.id))
                .where(TestScript.script_format == 'yaml')
            )
            yaml_scripts = yaml_scripts_result.scalar()
            
            playwright_scripts_result = await session.execute(
                select(func.count(TestScript.id))
                .where(TestScript.script_format == 'playwright')
            )
            playwright_scripts = playwright_scripts_result.scalar()
            
            # 执行统计
            execution_stats_result = await session.execute(
                select(
                    func.sum(TestScript.execution_count).label('total_executions'),
                    func.avg(TestScript.execution_count).label('avg_executions')
                )
            )
            execution_stats = execution_stats_result.first()
            total_executions = execution_stats.total_executions or 0
            
            # 最常用脚本
            most_used_result = await session.execute(
                select(TestScript)
                .order_by(TestScript.execution_count.desc())
                .limit(5)
            )
            most_used_scripts = [
                {
                    "id": script.id,
                    "name": script.name,
                    "execution_count": script.execution_count,
                    "script_format": script.script_format
                }
                for script in most_used_result.scalars().all()
            ]
            
            # 最近创建脚本
            recent_result = await session.execute(
                select(TestScript)
                .order_by(TestScript.created_at.desc())
                .limit(5)
            )
            recent_scripts = [
                {
                    "id": script.id,
                    "name": script.name,
                    "created_at": script.created_at.isoformat(),
                    "script_format": script.script_format
                }
                for script in recent_result.scalars().all()
            ]
            
            # 构建统计结果
            stats = ScriptStatistics(
                total_scripts=total_scripts,
                yaml_scripts=yaml_scripts,
                playwright_scripts=playwright_scripts,
                total_executions=total_executions,
                successful_executions=int(total_executions * 0.85),  # 模拟数据
                failed_executions=int(total_executions * 0.15),  # 模拟数据
                success_rate=0.85,  # 模拟数据
                average_execution_time=45.5,  # 模拟数据
                most_used_scripts=most_used_scripts,
                recent_scripts=recent_scripts
            )
            
            return stats
            
        except Exception as e:
            logger.error(f"获取脚本统计失败: {e}")
            raise
    
    async def add_tag(self, session: AsyncSession, script_id: str, tag_name: str) -> bool:
        """为脚本添加标签"""
        try:
            # 检查标签是否已存在
            existing = await session.execute(
                select(ScriptTag)
                .where(and_(ScriptTag.script_id == script_id, ScriptTag.tag_name == tag_name))
            )
            if existing.scalar_one_or_none():
                return True  # 标签已存在
            
            # 添加新标签
            tag = ScriptTag(script_id=script_id, tag_name=tag_name)
            session.add(tag)
            await session.flush()
            return True
            
        except Exception as e:
            logger.error(f"添加脚本标签失败: {e}")
            raise
    
    async def remove_tag(self, session: AsyncSession, script_id: str, tag_name: str) -> bool:
        """移除脚本标签"""
        try:
            result = await session.execute(
                select(ScriptTag)
                .where(and_(ScriptTag.script_id == script_id, ScriptTag.tag_name == tag_name))
            )
            tag = result.scalar_one_or_none()
            if tag:
                await session.delete(tag)
                await session.flush()
                return True
            return False
            
        except Exception as e:
            logger.error(f"移除脚本标签失败: {e}")
            raise
    
    async def get_by_session_id(self, session: AsyncSession, session_id: str) -> List[TestScript]:
        """根据会话ID获取脚本"""
        try:
            result = await session.execute(
                select(TestScript)
                .options(selectinload(TestScript.tags))
                .where(TestScript.session_id == session_id)
                .order_by(TestScript.created_at.desc())
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"根据会话ID获取脚本失败: {e}")
            raise
