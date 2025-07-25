"""
日志服务
处理智能体日志的存储、查询和分析
"""
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from loguru import logger

from app.models.api_automation import AgentLog, LogAnalysis, AlertRule, Alert
from app.core.enums import LogLevel


class LogService:
    """日志服务类"""
    
    @staticmethod
    async def save_agent_log(
        session_id: str,
        agent_type: str,
        agent_name: str,
        log_level: str,
        message: str,
        log_data: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
        user_id: Optional[str] = None,
        operation: Optional[str] = None,
        execution_time: Optional[float] = None,
        memory_usage: Optional[float] = None,
        cpu_usage: Optional[float] = None,
        error_code: Optional[str] = None,
        error_type: Optional[str] = None,
        stack_trace: Optional[str] = None,
        tags: Optional[List[str]] = None,
        category: Optional[str] = None
    ) -> str:
        """保存智能体日志"""
        try:
            log_id = str(uuid.uuid4())
            
            agent_log = await AgentLog.create(
                log_id=log_id,
                session_id=session_id,
                agent_type=agent_type,
                agent_name=agent_name,
                log_level=log_level,
                log_message=message,
                log_data=log_data or {},
                request_id=request_id,
                user_id=user_id,
                operation=operation,
                execution_time=execution_time,
                memory_usage=memory_usage,
                cpu_usage=cpu_usage,
                error_code=error_code,
                error_type=error_type,
                stack_trace=stack_trace,
                tags=tags or [],
                category=category,
                timestamp=datetime.utcnow()
            )
            
            logger.debug(f"保存智能体日志成功: {log_id}")
            return log_id
            
        except Exception as e:
            logger.error(f"保存智能体日志失败: {str(e)}")
            raise
    
    @staticmethod
    async def get_session_logs(
        session_id: str,
        log_level: Optional[str] = None,
        agent_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[AgentLog]:
        """获取会话日志"""
        try:
            query = AgentLog.filter(session_id=session_id)
            
            if log_level:
                query = query.filter(log_level=log_level)
            
            if agent_type:
                query = query.filter(agent_type=agent_type)
            
            if start_time:
                query = query.filter(timestamp__gte=start_time)
            
            if end_time:
                query = query.filter(timestamp__lte=end_time)
            
            logs = await query.order_by('-timestamp').limit(limit)
            return logs
            
        except Exception as e:
            logger.error(f"获取会话日志失败: {str(e)}")
            raise
    
    @staticmethod
    async def get_agent_logs(
        agent_type: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        log_level: Optional[str] = None,
        limit: int = 1000
    ) -> List[AgentLog]:
        """获取智能体日志"""
        try:
            query = AgentLog.filter(agent_type=agent_type)
            
            if start_time:
                query = query.filter(timestamp__gte=start_time)
            
            if end_time:
                query = query.filter(timestamp__lte=end_time)
            
            if log_level:
                query = query.filter(log_level=log_level)
            
            logs = await query.order_by('-timestamp').limit(limit)
            return logs
            
        except Exception as e:
            logger.error(f"获取智能体日志失败: {str(e)}")
            raise
    
    @staticmethod
    async def analyze_session_logs(session_id: str) -> Dict[str, Any]:
        """分析会话日志"""
        try:
            # 获取会话的所有日志
            logs = await AgentLog.filter(session_id=session_id).all()
            
            if not logs:
                return {"error": "没有找到日志"}
            
            # 统计分析
            total_logs = len(logs)
            error_logs = len([log for log in logs if log.log_level == "ERROR"])
            warning_logs = len([log for log in logs if log.log_level == "WARNING"])
            
            error_rate = (error_logs / total_logs) * 100 if total_logs > 0 else 0
            warning_rate = (warning_logs / total_logs) * 100 if total_logs > 0 else 0
            
            # 计算平均响应时间
            execution_times = [log.execution_time for log in logs if log.execution_time is not None]
            avg_response_time = sum(execution_times) / len(execution_times) if execution_times else None
            
            # 检测异常
            anomalies = []
            for log in logs:
                if log.log_level == "ERROR" and log.error_type:
                    anomalies.append({
                        "log_id": log.log_id,
                        "error_type": log.error_type,
                        "error_code": log.error_code,
                        "message": log.log_message,
                        "timestamp": log.timestamp.isoformat()
                    })
            
            # 保存分析结果
            analysis_id = str(uuid.uuid4())
            analysis = await LogAnalysis.create(
                analysis_id=analysis_id,
                session_id=session_id,
                log_count=total_logs,
                analysis_start_time=min(log.timestamp for log in logs),
                analysis_end_time=max(log.timestamp for log in logs),
                error_rate=error_rate,
                warning_rate=warning_rate,
                avg_response_time=avg_response_time,
                anomalies_detected=len(anomalies),
                anomaly_details=anomalies
            )
            
            return {
                "analysis_id": analysis_id,
                "total_logs": total_logs,
                "error_rate": error_rate,
                "warning_rate": warning_rate,
                "avg_response_time": avg_response_time,
                "anomalies_detected": len(anomalies),
                "anomalies": anomalies
            }
            
        except Exception as e:
            logger.error(f"分析会话日志失败: {str(e)}")
            raise
    
    @staticmethod
    async def check_alert_rules(session_id: str) -> List[Dict[str, Any]]:
        """检查告警规则"""
        try:
            # 获取活跃的告警规则
            rules = await AlertRule.filter(is_active=True).all()
            triggered_alerts = []
            
            for rule in rules:
                # 根据规则类型检查条件
                if rule.rule_type == "ERROR_RATE":
                    # 检查错误率
                    end_time = datetime.utcnow()
                    start_time = end_time - timedelta(minutes=rule.time_window)
                    
                    logs = await AgentLog.filter(
                        session_id=session_id,
                        timestamp__gte=start_time,
                        timestamp__lte=end_time
                    ).all()
                    
                    if logs:
                        error_logs = [log for log in logs if log.log_level == "ERROR"]
                        error_rate = (len(error_logs) / len(logs)) * 100
                        
                        if LogService._check_threshold(error_rate, rule.threshold_value, rule.comparison_operator):
                            alert = await LogService._create_alert(rule, session_id, {
                                "error_rate": error_rate,
                                "total_logs": len(logs),
                                "error_logs": len(error_logs)
                            })
                            triggered_alerts.append(alert)
                
                elif rule.rule_type == "RESPONSE_TIME":
                    # 检查响应时间
                    end_time = datetime.utcnow()
                    start_time = end_time - timedelta(minutes=rule.time_window)
                    
                    logs = await AgentLog.filter(
                        session_id=session_id,
                        timestamp__gte=start_time,
                        timestamp__lte=end_time,
                        execution_time__isnull=False
                    ).all()
                    
                    if logs:
                        avg_response_time = sum(log.execution_time for log in logs) / len(logs)
                        
                        if LogService._check_threshold(avg_response_time, rule.threshold_value, rule.comparison_operator):
                            alert = await LogService._create_alert(rule, session_id, {
                                "avg_response_time": avg_response_time,
                                "sample_count": len(logs)
                            })
                            triggered_alerts.append(alert)
            
            return triggered_alerts
            
        except Exception as e:
            logger.error(f"检查告警规则失败: {str(e)}")
            raise
    
    @staticmethod
    def _check_threshold(value: float, threshold: float, operator: str) -> bool:
        """检查阈值条件"""
        if operator == ">":
            return value > threshold
        elif operator == ">=":
            return value >= threshold
        elif operator == "<":
            return value < threshold
        elif operator == "<=":
            return value <= threshold
        elif operator == "==":
            return value == threshold
        return False
    
    @staticmethod
    async def _create_alert(rule: AlertRule, session_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """创建告警"""
        alert_id = str(uuid.uuid4())
        
        alert = await Alert.create(
            alert_id=alert_id,
            rule=rule,
            session_id=session_id,
            title=f"告警: {rule.name}",
            message=f"规则 {rule.name} 被触发，阈值: {rule.threshold_value}，当前值: {data}",
            severity=rule.severity,
            status="OPEN"
        )
        
        return {
            "alert_id": alert_id,
            "rule_name": rule.name,
            "severity": rule.severity,
            "message": alert.message,
            "data": data
        }
    
    @staticmethod
    async def get_log_statistics(
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        agent_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """获取日志统计信息"""
        try:
            query = AgentLog.all()
            
            if start_time:
                query = query.filter(timestamp__gte=start_time)
            
            if end_time:
                query = query.filter(timestamp__lte=end_time)
            
            if agent_type:
                query = query.filter(agent_type=agent_type)
            
            logs = await query
            
            # 统计各级别日志数量
            level_counts = {}
            agent_counts = {}
            
            for log in logs:
                # 按级别统计
                level_counts[log.log_level] = level_counts.get(log.log_level, 0) + 1
                # 按智能体统计
                agent_counts[log.agent_type] = agent_counts.get(log.agent_type, 0) + 1
            
            return {
                "total_logs": len(logs),
                "level_distribution": level_counts,
                "agent_distribution": agent_counts,
                "time_range": {
                    "start": start_time.isoformat() if start_time else None,
                    "end": end_time.isoformat() if end_time else None
                }
            }
            
        except Exception as e:
            logger.error(f"获取日志统计失败: {str(e)}")
            raise
