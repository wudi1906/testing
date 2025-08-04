"""
日志记录智能体
基于公共基类实现，智能收集、分析和管理系统日志
"""
import os
import json
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path

from autogen_core import message_handler, type_subscription, MessageContext, TopicId
from loguru import logger
from pydantic import BaseModel, Field

from app.agents.api_automation.base_api_agent import BaseApiAutomationAgent
from app.core.types import AgentTypes, AGENT_NAMES, TopicTypes
from .schemas import (
    LogRecordRequest, LogRecordResponse, LogLevel
)
from app.services.log_service import LogService


@type_subscription(topic_type=TopicTypes.LOG_RECORDER.value)
class LogRecorderAgent(BaseApiAutomationAgent):
    """
    日志记录智能体

    核心功能：
    1. 智能收集和存储系统日志
    2. 实时监控系统健康状态
    3. 使用大模型分析日志模式和异常
    4. 生成智能告警和建议
    5. 提供日志查询和导出功能
    6. 支持流式分析和实时反馈
    """

    def __init__(self, model_client_instance=None, agent_config=None, **kwargs):
        """初始化日志记录智能体"""
        super().__init__(
            agent_type=AgentTypes.LOG_RECORDER,
            model_client_instance=model_client_instance,
            **kwargs
        )

        # 存储智能体配置信息
        self.agent_config = agent_config or {}

        # 初始化AssistantAgent
        self._initialize_assistant_agent()

        # 日志统计（继承公共统计）
        self.log_metrics = {
            "total_logs_collected": 0,
            "error_logs": 0,
            "warning_logs": 0,
            "info_logs": 0,
            "debug_logs": 0,
            "alerts_generated": 0,
            "analysis_performed": 0
        }

        # 日志存储目录
        self.logs_dir = Path("./logs")
        self.logs_dir.mkdir(exist_ok=True)

        # 会话日志存储
        self.session_logs = {}

        # 告警规则
        self.alert_rules = {
            "error_rate_threshold": 5.0,  # 错误率超过5%
            "response_time_threshold": 5.0,  # 响应时间超过5秒
            "memory_usage_threshold": 0.8,  # 内存使用超过80%
            "disk_usage_threshold": 0.9   # 磁盘使用超过90%
        }

        logger.info(f"日志记录智能体初始化完成: {self.agent_name}")



    @message_handler
    async def handle_log_record_request(
        self, 
        message: LogRecordRequest, 
        ctx: MessageContext
    ) -> None:
        """处理日志记录请求"""
        try:
            # 记录日志
            await self._record_log(message)
            return None
            # 分析日志（如果需要）
            if self._should_analyze_logs(message):
                await self._analyze_logs(message.session_id)
            
            # 构建响应
            response = LogRecordResponse(
                session_id=message.session_id,
                log_id=str(uuid.uuid4()),
                status="recorded",
                timestamp=datetime.now()
            )
            
            # 更新统计
            self._update_metrics(message)
            
        except Exception as e:
            logger.error(f"日志记录失败: {str(e)}")

    async def _record_log(self, message: LogRecordRequest):
        """记录日志"""
        try:
            # 保存到数据库
            log_id = await LogService.save_agent_log(
                session_id=message.session_id,
                agent_type=message.source,  # 使用source作为agent_type
                agent_name=message.source,
                log_level=message.level.value,
                message=message.message,
                log_data=message.metadata,
                request_id=getattr(message, 'request_id', None),
                user_id=getattr(message, 'user_id', None),
                operation=getattr(message, 'operation', None),
                execution_time=getattr(message, 'execution_time', None),
                memory_usage=getattr(message, 'memory_usage', None),
                cpu_usage=getattr(message, 'cpu_usage', None),
                error_code=getattr(message, 'error_code', None),
                error_type=getattr(message, 'error_type', None),
                stack_trace=getattr(message, 'stack_trace', None),
                tags=getattr(message, 'tags', []),
                category=getattr(message, 'category', None)
            )

            # 存储到会话日志（内存缓存）
            if message.session_id not in self.session_logs:
                self.session_logs[message.session_id] = []

            log_entry = {
                "log_id": log_id,
                "timestamp": message.timestamp.isoformat(),
                "level": message.level.value,
                "source": message.source,
                "message": message.message,
                "metadata": message.metadata
            }

            self.session_logs[message.session_id].append(log_entry)

            # 写入文件（备份）
            log_file = self.logs_dir / f"session_{message.session_id}.log"
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"{json.dumps(log_entry, ensure_ascii=False)}\n")

            # 写入全局日志
            global_log_file = self.logs_dir / f"api_automation_{datetime.now().strftime('%Y-%m-%d')}.log"
            with open(global_log_file, 'a', encoding='utf-8') as f:
                f.write(f"{json.dumps(log_entry, ensure_ascii=False)}\n")

            self.log_metrics["total_logs_collected"] += 1

            logger.debug(f"日志记录成功: {log_id}")
            
        except Exception as e:
            logger.error(f"记录日志失败: {str(e)}")

    def _should_analyze_logs(self, message: LogRecordRequest) -> bool:
        """判断是否需要分析日志"""
        # 错误日志立即分析
        if message.level in [LogLevel.ERROR, LogLevel.CRITICAL]:
            return True
        
        # 会话日志达到一定数量时分析
        session_log_count = len(self.session_logs.get(message.session_id, []))
        if session_log_count > 0 and session_log_count % 50 == 0:
            return True
        
        return False

    async def _analyze_logs(self, session_id: str):
        """分析日志"""
        try:
            # 使用数据库服务进行日志分析
            analysis_result = await LogService.analyze_session_logs(session_id)

            if "error" in analysis_result:
                logger.warning(f"会话 {session_id} 没有日志可分析")
                return

            # 使用大模型进行智能分析
            ai_analysis = await self._intelligent_log_analysis(session_id)

            # 检查告警规则
            alerts = await LogService.check_alert_rules(session_id)
            if alerts:
                logger.warning(f"会话 {session_id} 触发了 {len(alerts)} 个告警")
                self.log_metrics["alerts_generated"] += len(alerts)

            self.log_metrics["analysis_performed"] += 1

            logger.info(f"日志分析完成: {session_id}, 分析ID: {analysis_result.get('analysis_id')}")

        except Exception as e:
            logger.error(f"日志分析失败: {str(e)}")

    async def _intelligent_log_analysis(self, session_id: str) -> Dict[str, Any]:
        """使用大模型进行智能日志分析"""
        try:
            # 从数据库获取日志
            logs = await LogService.get_session_logs(session_id, limit=100)

            if not logs:
                return {"error": "没有日志可分析"}

            # 转换为分析格式
            log_data = []
            for log in logs:
                log_data.append({
                    "timestamp": log.timestamp.isoformat(),
                    "level": log.log_level,
                    "agent": log.agent_name,
                    "message": log.log_message,
                    "data": log.log_data,
                    "execution_time": log.execution_time,
                    "error_type": log.error_type
                })

            # 构建分析任务
            task = f"""请分析以下系统日志，提供专业的分析和洞察：

## 日志数据
{json.dumps(log_data, ensure_ascii=False, indent=2)}

## 分析要求
请从以下维度进行深度分析：

1. **日志摘要统计**
   - 日志总数和级别分布
   - 时间范围和频率分析
   - 主要智能体统计

2. **错误分析**
   - 错误类型分类和统计
   - 错误模式识别
   - 根因分析
   - 影响评估

3. **性能洞察**
   - 响应时间分析
   - 资源使用模式
   - 性能瓶颈识别
   - 优化建议

4. **趋势分析**
   - 错误趋势变化
   - 性能趋势分析
   - 使用量趋势
   - 预测分析

5. **告警检测**
   - 异常情况识别
   - 告警级别评估
   - 影响范围分析

请严格按照系统提示中的JSON格式输出详细的分析结果。"""

            # 使用AssistantAgent进行智能分析
            result_content = await self._run_assistant_agent(task)

            # 解析大模型返回的结果
            if result_content:
                analysis_result = self._extract_json_from_content(result_content)
                if analysis_result:
                    return analysis_result

            # 如果大模型分析失败，使用备用方法
            logger.warning("大模型分析失败，使用备用分析方法")
            return await self._fallback_log_analysis(logs)

        except Exception as e:
            logger.error(f"智能日志分析失败: {str(e)}")
            return await self._fallback_log_analysis(logs)



    async def _fallback_log_analysis(self, logs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """备用日志分析方法"""
        try:
            # 基础统计
            total_logs = len(logs)
            error_count = sum(1 for log in logs if log.get("level") == "ERROR")
            warning_count = sum(1 for log in logs if log.get("level") == "WARNING")
            info_count = sum(1 for log in logs if log.get("level") == "INFO")

            error_rate = (error_count / total_logs * 100) if total_logs > 0 else 0

            # 时间范围
            timestamps = [log.get("timestamp") for log in logs if log.get("timestamp")]
            time_range = f"{min(timestamps)} to {max(timestamps)}" if timestamps else "unknown"

            return {
                "log_summary": {
                    "total_logs": total_logs,
                    "error_count": error_count,
                    "warning_count": warning_count,
                    "info_count": info_count,
                    "time_range": time_range,
                    "error_rate": round(error_rate, 2)
                },
                "error_analysis": {
                    "error_categories": {"general": error_count},
                    "critical_errors": [log for log in logs if log.get("level") == "ERROR"][:5],
                    "error_trends": {"trend": "stable"},
                    "root_causes": ["需要详细分析"]
                },
                "performance_insights": {
                    "avg_response_time": 1.0,
                    "slow_operations": [],
                    "resource_usage": {"memory": "normal", "cpu": "normal"},
                    "bottlenecks": []
                },
                "trend_analysis": {
                    "error_trend": "stable",
                    "performance_trend": "stable",
                    "usage_trend": "stable",
                    "predictions": []
                },
                "alerts": [],
                "recommendations": [
                    "监控错误日志" if error_count > 0 else "系统运行正常",
                    "定期清理日志文件",
                    "增加详细的日志记录"
                ]
            }

        except Exception as e:
            logger.error(f"备用日志分析失败: {str(e)}")
            return {
                "log_summary": {},
                "error_analysis": {},
                "performance_insights": {},
                "trend_analysis": {},
                "alerts": [],
                "recommendations": []
            }

    async def _generate_alerts(self, analysis_result: Dict[str, Any]):
        """生成告警"""
        try:
            alerts = analysis_result.get("alerts", [])

            for alert in alerts:
                if alert.get("level") in ["critical", "high"]:
                    await self._send_alert(alert)
                    self.log_metrics["alerts_generated"] += 1

        except Exception as e:
            logger.error(f"生成告警失败: {str(e)}")

    async def _send_alert(self, alert: Dict[str, Any]):
        """发送告警"""
        try:
            # 这里可以实现告警发送逻辑（邮件、短信、webhook等）
            logger.warning(f"系统告警: {alert}")

        except Exception as e:
            logger.error(f"发送告警失败: {str(e)}")

    def _basic_log_analysis(self, logs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """基础日志分析"""
        try:
            total_logs = len(logs)
            error_count = sum(1 for log in logs if log.get("level") == "ERROR")
            warning_count = sum(1 for log in logs if log.get("level") == "WARNING")
            info_count = sum(1 for log in logs if log.get("level") == "INFO")
            debug_count = sum(1 for log in logs if log.get("level") == "DEBUG")
            
            # 时间范围
            timestamps = [log.get("timestamp") for log in logs if log.get("timestamp")]
            time_range = f"{min(timestamps)} to {max(timestamps)}" if timestamps else "unknown"
            
            # 错误率
            error_rate = (error_count / total_logs * 100) if total_logs > 0 else 0
            
            # 日志源统计
            sources = {}
            for log in logs:
                source = log.get("source", "unknown")
                sources[source] = sources.get(source, 0) + 1
            
            # 最近错误
            recent_errors = [log for log in logs if log.get("level") == "ERROR"][-5:]
            
            return {
                "summary": {
                    "total_logs": total_logs,
                    "error_count": error_count,
                    "warning_count": warning_count,
                    "info_count": info_count,
                    "debug_count": debug_count,
                    "time_range": time_range,
                    "error_rate": round(error_rate, 2)
                },
                "sources": sources,
                "recent_errors": recent_errors,
                "analysis_time": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"基础日志分析失败: {str(e)}")
            return {}

    async def _save_analysis_result(self, session_id: str, analysis_result: Dict[str, Any]):
        """保存分析结果"""
        try:
            analysis_file = self.logs_dir / f"analysis_{session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(analysis_file, 'w', encoding='utf-8') as f:
                json.dump(analysis_result, f, indent=2, ensure_ascii=False)
            
            logger.info(f"日志分析结果已保存: {analysis_file}")
            
        except Exception as e:
            logger.error(f"保存分析结果失败: {str(e)}")

    def _update_metrics(self, message: LogRecordRequest):
        """更新统计指标"""
        level = message.level
        
        if level == LogLevel.ERROR:
            self.log_metrics["error_logs"] += 1
        elif level == LogLevel.WARNING:
            self.log_metrics["warning_logs"] += 1
        elif level == LogLevel.INFO:
            self.log_metrics["info_logs"] += 1
        elif level == LogLevel.DEBUG:
            self.log_metrics["debug_logs"] += 1

    async def get_session_logs(self, session_id: str) -> List[Dict[str, Any]]:
        """获取会话日志"""
        return self.session_logs.get(session_id, [])

    async def get_logs_by_level(self, session_id: str, level: LogLevel) -> List[Dict[str, Any]]:
        """按级别获取日志"""
        session_logs = self.session_logs.get(session_id, [])
        return [log for log in session_logs if log.get("level") == level.value]

    async def get_logs_by_source(self, session_id: str, source: str) -> List[Dict[str, Any]]:
        """按来源获取日志"""
        session_logs = self.session_logs.get(session_id, [])
        return [log for log in session_logs if log.get("source") == source]

    async def get_logs_by_time_range(
        self, 
        session_id: str, 
        start_time: datetime, 
        end_time: datetime
    ) -> List[Dict[str, Any]]:
        """按时间范围获取日志"""
        session_logs = self.session_logs.get(session_id, [])
        filtered_logs = []
        
        for log in session_logs:
            try:
                log_time = datetime.fromisoformat(log.get("timestamp", ""))
                if start_time <= log_time <= end_time:
                    filtered_logs.append(log)
            except Exception:
                continue
        
        return filtered_logs

    async def export_logs(self, session_id: str, format: str = "json") -> str:
        """导出日志"""
        try:
            logs = self.session_logs.get(session_id, [])
            
            if format == "json":
                export_file = self.logs_dir / f"export_{session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(export_file, 'w', encoding='utf-8') as f:
                    json.dump(logs, f, indent=2, ensure_ascii=False)
            elif format == "csv":
                import csv
                export_file = self.logs_dir / f"export_{session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                with open(export_file, 'w', newline='', encoding='utf-8') as f:
                    if logs:
                        writer = csv.DictWriter(f, fieldnames=logs[0].keys())
                        writer.writeheader()
                        writer.writerows(logs)
            
            return str(export_file)
            
        except Exception as e:
            logger.error(f"导出日志失败: {str(e)}")
            return ""

    async def get_log_statistics(self) -> Dict[str, Any]:
        """获取日志统计信息"""
        try:
            # 获取基类的公共统计
            common_stats = self.get_common_statistics()

            # 获取数据库统计
            db_stats = await LogService.get_log_statistics()

            # 计算日志特定的统计
            total_logs = self.log_metrics["total_logs_collected"]
            error_rate = 0.0
            if total_logs > 0:
                error_rate = (self.log_metrics["error_logs"] / total_logs) * 100

            # 合并统计信息
            return {
                **common_stats,
                "log_metrics": self.log_metrics,
                "database_stats": db_stats,
                "error_rate": round(error_rate, 2),
                "active_sessions": len(self.session_logs),
                "logs_directory": str(self.logs_dir)
            }

        except Exception as e:
            logger.error(f"获取日志统计失败: {str(e)}")
            # 返回基本统计
            common_stats = self.get_common_statistics()
            return {
                **common_stats,
                "log_metrics": self.log_metrics,
                "active_sessions": len(self.session_logs),
                "logs_directory": str(self.logs_dir)
            }

    async def cleanup_old_logs(self, days: int = 30):
        """清理旧日志"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            for log_file in self.logs_dir.glob("*.log"):
                if log_file.stat().st_mtime < cutoff_date.timestamp():
                    log_file.unlink()
                    logger.info(f"已删除旧日志文件: {log_file}")
            
            # 清理内存中的旧会话日志
            sessions_to_remove = []
            for session_id, logs in self.session_logs.items():
                if logs:
                    try:
                        last_log_time = datetime.fromisoformat(logs[-1].get("timestamp", ""))
                        if last_log_time < cutoff_date:
                            sessions_to_remove.append(session_id)
                    except Exception:
                        continue
            
            for session_id in sessions_to_remove:
                del self.session_logs[session_id]
                logger.info(f"已清理会话日志: {session_id}")
            
        except Exception as e:
            logger.error(f"清理旧日志失败: {str(e)}")

    async def get_session_logs_from_db(self, session_id: str, limit: int = 1000) -> List[Dict[str, Any]]:
        """从数据库获取会话日志"""
        try:
            logs = await LogService.get_session_logs(session_id, limit=limit)

            return [
                {
                    "log_id": log.log_id,
                    "timestamp": log.timestamp.isoformat(),
                    "agent_type": log.agent_type,
                    "agent_name": log.agent_name,
                    "log_level": log.log_level,
                    "message": log.log_message,
                    "data": log.log_data,
                    "execution_time": log.execution_time,
                    "memory_usage": log.memory_usage,
                    "cpu_usage": log.cpu_usage,
                    "error_type": log.error_type,
                    "error_code": log.error_code
                }
                for log in logs
            ]

        except Exception as e:
            logger.error(f"从数据库获取会话日志失败: {str(e)}")
            return []

    async def create_alert_rule(self, rule_data: Dict[str, Any]) -> str:
        """创建告警规则"""
        try:
            from app.models.api_automation import AlertRule

            rule_id = str(uuid.uuid4())

            rule = await AlertRule.create(
                rule_id=rule_id,
                name=rule_data["name"],
                description=rule_data.get("description", ""),
                rule_type=rule_data["rule_type"],
                threshold_value=rule_data["threshold_value"],
                comparison_operator=rule_data["comparison_operator"],
                time_window=rule_data["time_window"],
                trigger_count=rule_data.get("trigger_count", 1),
                severity=rule_data["severity"],
                is_active=rule_data.get("is_active", True)
            )

            logger.info(f"创建告警规则成功: {rule_id}")
            return rule_id

        except Exception as e:
            logger.error(f"创建告警规则失败: {str(e)}")
            raise

    async def get_active_alerts(self, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取活跃告警"""
        try:
            from app.models.api_automation import Alert

            query = Alert.filter(status="OPEN")
            if session_id:
                query = query.filter(session_id=session_id)

            alerts = await query.prefetch_related("rule").all()

            return [
                {
                    "alert_id": alert.alert_id,
                    "rule_name": alert.rule.name,
                    "title": alert.title,
                    "message": alert.message,
                    "severity": alert.severity,
                    "status": alert.status,
                    "triggered_at": alert.triggered_at.isoformat(),
                    "session_id": alert.session_id
                }
                for alert in alerts
            ]

        except Exception as e:
            logger.error(f"获取活跃告警失败: {str(e)}")
            return []

    async def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """确认告警"""
        try:
            from app.models.api_automation import Alert

            alert = await Alert.get(alert_id=alert_id)
            alert.status = "ACKNOWLEDGED"
            alert.acknowledged_by = acknowledged_by
            alert.acknowledged_at = datetime.utcnow()
            await alert.save()

            logger.info(f"告警确认成功: {alert_id}")
            return True

        except Exception as e:
            logger.error(f"告警确认失败: {str(e)}")
            return False


