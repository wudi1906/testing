"""
会话仓库
管理用户会话数据的数据访问层
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session as SQLSession
from sqlalchemy import and_, or_, desc

from .base import BaseRepository
from app.database.models.sessions import Session as SessionModel
from app.core.types import SessionStatus


class SessionRepository(BaseRepository[SessionModel]):
    """会话数据仓库"""

    def __init__(self, db_session: SQLSession):
        super().__init__(db_session, SessionModel)

    def create_session(self, 
                      session_id: str,
                      user_id: Optional[str] = None,
                      session_type: str = "web_test",
                      metadata: Optional[Dict[str, Any]] = None) -> SessionModel:
        """创建新会话
        
        Args:
            session_id: 会话ID
            user_id: 用户ID
            session_type: 会话类型
            metadata: 会话元数据
            
        Returns:
            SessionModel: 创建的会话模型
        """
        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "session_type": session_type,
            "status": SessionStatus.ACTIVE.value,
            "metadata": metadata or {},
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        return self.create(session_data)

    def get_by_session_id(self, session_id: str) -> Optional[SessionModel]:
        """根据会话ID获取会话
        
        Args:
            session_id: 会话ID
            
        Returns:
            Optional[SessionModel]: 会话模型，如果不存在返回None
        """
        return self.db_session.query(SessionModel).filter(
            SessionModel.session_id == session_id
        ).first()

    def get_active_sessions(self, user_id: Optional[str] = None) -> List[SessionModel]:
        """获取活跃会话列表
        
        Args:
            user_id: 用户ID，如果提供则只返回该用户的会话
            
        Returns:
            List[SessionModel]: 活跃会话列表
        """
        query = self.db_session.query(SessionModel).filter(
            SessionModel.status == SessionStatus.ACTIVE.value
        )
        
        if user_id:
            query = query.filter(SessionModel.user_id == user_id)
            
        return query.order_by(desc(SessionModel.updated_at)).all()

    def update_session_status(self, 
                             session_id: str, 
                             status: SessionStatus) -> Optional[SessionModel]:
        """更新会话状态
        
        Args:
            session_id: 会话ID
            status: 新状态
            
        Returns:
            Optional[SessionModel]: 更新后的会话模型
        """
        session = self.get_by_session_id(session_id)
        if session:
            update_data = {
                "status": status.value,
                "updated_at": datetime.utcnow()
            }
            return self.update(session.id, update_data)
        return None

    def update_session_metadata(self, 
                               session_id: str, 
                               metadata: Dict[str, Any]) -> Optional[SessionModel]:
        """更新会话元数据
        
        Args:
            session_id: 会话ID
            metadata: 新的元数据
            
        Returns:
            Optional[SessionModel]: 更新后的会话模型
        """
        session = self.get_by_session_id(session_id)
        if session:
            # 合并现有元数据和新元数据
            current_metadata = session.metadata or {}
            current_metadata.update(metadata)
            
            update_data = {
                "metadata": current_metadata,
                "updated_at": datetime.utcnow()
            }
            return self.update(session.id, update_data)
        return None

    def close_session(self, session_id: str) -> Optional[SessionModel]:
        """关闭会话
        
        Args:
            session_id: 会话ID
            
        Returns:
            Optional[SessionModel]: 更新后的会话模型
        """
        return self.update_session_status(session_id, SessionStatus.CLOSED)

    def get_sessions_by_type(self, 
                           session_type: str, 
                           limit: int = 50) -> List[SessionModel]:
        """根据类型获取会话列表
        
        Args:
            session_type: 会话类型
            limit: 返回数量限制
            
        Returns:
            List[SessionModel]: 会话列表
        """
        return self.db_session.query(SessionModel).filter(
            SessionModel.session_type == session_type
        ).order_by(desc(SessionModel.created_at)).limit(limit).all()

    def cleanup_expired_sessions(self, 
                                expire_hours: int = 24) -> int:
        """清理过期会话
        
        Args:
            expire_hours: 过期时间（小时）
            
        Returns:
            int: 清理的会话数量
        """
        from datetime import timedelta
        
        expire_time = datetime.utcnow() - timedelta(hours=expire_hours)
        
        expired_sessions = self.db_session.query(SessionModel).filter(
            and_(
                SessionModel.status == SessionStatus.ACTIVE.value,
                SessionModel.updated_at < expire_time
            )
        ).all()
        
        count = 0
        for session in expired_sessions:
            self.update(session.id, {
                "status": SessionStatus.EXPIRED.value,
                "updated_at": datetime.utcnow()
            })
            count += 1
            
        return count

    def get_session_statistics(self) -> Dict[str, Any]:
        """获取会话统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        total_sessions = self.db_session.query(SessionModel).count()
        
        active_sessions = self.db_session.query(SessionModel).filter(
            SessionModel.status == SessionStatus.ACTIVE.value
        ).count()
        
        closed_sessions = self.db_session.query(SessionModel).filter(
            SessionModel.status == SessionStatus.CLOSED.value
        ).count()
        
        expired_sessions = self.db_session.query(SessionModel).filter(
            SessionModel.status == SessionStatus.EXPIRED.value
        ).count()
        
        # 按类型统计
        type_stats = {}
        session_types = self.db_session.query(SessionModel.session_type).distinct().all()
        for (session_type,) in session_types:
            count = self.db_session.query(SessionModel).filter(
                SessionModel.session_type == session_type
            ).count()
            type_stats[session_type] = count
        
        return {
            "total_sessions": total_sessions,
            "active_sessions": active_sessions,
            "closed_sessions": closed_sessions,
            "expired_sessions": expired_sessions,
            "session_types": type_stats
        }

    def search_sessions(self, 
                       query: str, 
                       session_type: Optional[str] = None,
                       status: Optional[SessionStatus] = None,
                       limit: int = 50) -> List[SessionModel]:
        """搜索会话
        
        Args:
            query: 搜索关键词
            session_type: 会话类型过滤
            status: 状态过滤
            limit: 返回数量限制
            
        Returns:
            List[SessionModel]: 搜索结果
        """
        db_query = self.db_session.query(SessionModel)
        
        # 关键词搜索（在session_id和metadata中搜索）
        if query:
            db_query = db_query.filter(
                or_(
                    SessionModel.session_id.contains(query),
                    SessionModel.metadata.contains(query)
                )
            )
        
        # 类型过滤
        if session_type:
            db_query = db_query.filter(SessionModel.session_type == session_type)
        
        # 状态过滤
        if status:
            db_query = db_query.filter(SessionModel.status == status.value)
        
        return db_query.order_by(desc(SessionModel.updated_at)).limit(limit).all()
