"""
测试报告服务
"""
import os
import re
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from sqlalchemy import desc, func

from app.database.connection import db_manager
from app.database.models.reports import TestReport
from app.core.logging import get_logger

logger = get_logger(__name__)


class TestReportService:
    """测试报告服务"""
    
    def __init__(self):
        self.playwright_workspace = Path(r"C:\Users\86134\Desktop\workspace\playwright-workspace")
        self.report_base_dir = self.playwright_workspace / "midscene_run" / "report"
    
    async def save_test_report(self,
                             script_id: str,
                             script_name: str,
                             session_id: str,
                             execution_id: str,
                             status: str,
                             return_code: int,
                             start_time: Optional[datetime] = None,
                             end_time: Optional[datetime] = None,
                             duration: float = 0.0,
                             logs: List[str] = None,
                             execution_config: Dict[str, Any] = None,
                             environment_variables: Dict[str, Any] = None,
                             report_path: Optional[str] = None,
                             report_url: Optional[str] = None) -> Optional[TestReport]:
        """保存测试报告到数据库"""
        try:
            # 如果没有传入报告路径，尝试查找报告文件
            if not report_path:
                report_info = self._find_report_files(execution_id, script_name)
                report_path = report_info.get("report_path")
                if not report_url and report_path:
                    report_url = f"/api/v1/web/reports/view/{execution_id}"

            # 获取报告文件大小
            report_size = 0
            if report_path and os.path.exists(report_path):
                try:
                    report_size = os.path.getsize(report_path)
                except:
                    pass

            # 解析测试结果统计
            test_stats = self._parse_test_results(logs or [])

            # 计算成功率
            success_rate = 0.0
            if test_stats["total_tests"] > 0:
                success_rate = (test_stats["passed_tests"] / test_stats["total_tests"]) * 100
            
            # 安全转换配置对象为字典
            safe_execution_config = self._safe_serialize_config(execution_config)
            safe_environment_variables = self._safe_serialize_config(environment_variables)

            # 创建报告记录
            db_report = TestReport(
                script_id=script_id,
                script_name=script_name,
                session_id=session_id,
                execution_id=execution_id,
                status=status,
                return_code=return_code,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                total_tests=test_stats["total_tests"],
                passed_tests=test_stats["passed_tests"],
                failed_tests=test_stats["failed_tests"],
                skipped_tests=test_stats["skipped_tests"],
                success_rate=success_rate,
                report_path=report_path,  # 使用传入的报告路径
                report_url=report_url,    # 使用传入的报告URL
                report_size=report_size,  # 使用计算的文件大小
                screenshots=[],  # 暂时为空，后续可以扩展
                videos=[],       # 暂时为空，后续可以扩展
                artifacts=[],    # 暂时为空，后续可以扩展
                error_message=self._extract_error_message(logs or []),
                logs=self._safe_serialize_logs(logs or []),
                execution_config=safe_execution_config,      # 使用安全序列化的配置
                environment_variables=safe_environment_variables  # 使用安全序列化的环境变量
            )

            # 保存到MySQL数据库
            async with db_manager.get_session() as session:
                session.add(db_report)
                await session.commit()
                await session.refresh(db_report)
                logger.info(f"测试报告已保存到MySQL: {db_report.id} - {script_name}")
                return db_report
                
        except Exception as e:
            logger.error(f"保存测试报告失败: {str(e)}")
            return None
    
    def _find_report_files(self, execution_id: str, script_name: str) -> Dict[str, Any]:
        """查找报告文件"""
        report_info = {
            "report_path": None,
            "report_url": None,
            "report_size": 0,
            "screenshots": [],
            "videos": [],
            "artifacts": []
        }
        
        try:
            # 查找HTML报告文件
            if self.report_base_dir.exists():
                # 查找index.html文件
                index_html = self.report_base_dir / "index.html"
                if index_html.exists():
                    report_info["report_path"] = str(index_html)
                    report_info["report_url"] = f"/api/v1/web/reports/view/{execution_id}"
                    report_info["report_size"] = index_html.stat().st_size
                
                # 查找截图文件
                screenshots = []
                for ext in ["*.png", "*.jpg", "*.jpeg"]:
                    screenshots.extend(self.report_base_dir.rglob(ext))
                report_info["screenshots"] = [str(f) for f in screenshots]
                
                # 查找视频文件
                videos = []
                for ext in ["*.mp4", "*.webm", "*.avi"]:
                    videos.extend(self.report_base_dir.rglob(ext))
                report_info["videos"] = [str(f) for f in videos]
                
                # 查找其他产物
                artifacts = []
                for ext in ["*.json", "*.xml", "*.log"]:
                    artifacts.extend(self.report_base_dir.rglob(ext))
                report_info["artifacts"] = [str(f) for f in artifacts]
                
        except Exception as e:
            logger.warning(f"查找报告文件失败: {str(e)}")
        
        return report_info
    
    def _parse_test_results(self, logs: List[str]) -> Dict[str, int]:
        """解析测试结果统计"""
        stats = {
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "skipped_tests": 0
        }
        
        try:
            # 合并所有日志
            log_text = "\n".join(logs)
            
            # 解析Playwright输出格式
            # 例如: "1 passed (3.2s)" 或 "2 failed, 1 passed (5.1s)"
            patterns = [
                r"(\d+)\s+passed",
                r"(\d+)\s+failed",
                r"(\d+)\s+skipped",
                r"Running\s+(\d+)\s+test"
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, log_text, re.IGNORECASE)
                if matches:
                    if "passed" in pattern:
                        stats["passed_tests"] = int(matches[-1])
                    elif "failed" in pattern:
                        stats["failed_tests"] = int(matches[-1])
                    elif "skipped" in pattern:
                        stats["skipped_tests"] = int(matches[-1])
                    elif "Running" in pattern:
                        stats["total_tests"] = int(matches[-1])
            
            # 如果没有找到总数，计算总数
            if stats["total_tests"] == 0:
                stats["total_tests"] = stats["passed_tests"] + stats["failed_tests"] + stats["skipped_tests"]
                
        except Exception as e:
            logger.warning(f"解析测试结果失败: {str(e)}")
        
        return stats
    
    def _extract_error_message(self, logs: List[str]) -> Optional[str]:
        """提取错误信息"""
        try:
            error_lines = []
            for log in logs:
                if any(keyword in log.lower() for keyword in ["error", "failed", "exception"]):
                    error_lines.append(log)
            
            if error_lines:
                return "\n".join(error_lines[:5])  # 只保留前5行错误信息
                
        except Exception as e:
            logger.warning(f"提取错误信息失败: {str(e)}")
        
        return None
    
    async def get_report_by_script_id(self, script_id: str) -> Optional[TestReport]:
        """根据脚本ID获取最新的测试报告"""
        try:
            async with db_manager.get_session() as session:
                from sqlalchemy import select
                stmt = select(TestReport).filter(
                    TestReport.script_id == script_id
                ).order_by(desc(TestReport.created_at))
                result = await session.execute(stmt)
                return result.scalars().first()  # 使用first()而不是scalar_one_or_none()
        except Exception as e:
            logger.error(f"获取测试报告失败: {str(e)}")
            return None
    
    async def get_report_by_execution_id(self, execution_id: str) -> Optional[TestReport]:
        """根据执行ID获取测试报告"""
        try:
            async with db_manager.get_session() as session:
                from sqlalchemy import select
                stmt = select(TestReport).filter(
                    TestReport.execution_id == execution_id
                )
                result = await session.execute(stmt)
                return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"获取测试报告失败: {str(e)}")
            return None
    
    async def get_reports_by_session_id(self, session_id: str) -> List[TestReport]:
        """根据会话ID获取所有测试报告"""
        try:
            async with db_manager.get_session() as session:
                from sqlalchemy import select
                stmt = select(TestReport).filter(
                    TestReport.session_id == session_id
                ).order_by(desc(TestReport.created_at))
                result = await session.execute(stmt)
                return list(result.scalars().all())
        except Exception as e:
            logger.error(f"获取测试报告失败: {str(e)}")
            return []
    
    async def get_report_file_path(self, execution_id: str) -> Optional[str]:
        """获取报告文件路径"""
        try:
            # 首先尝试从MySQL数据库获取报告路径
            async with db_manager.get_session() as session:
                from sqlalchemy import select
                stmt = select(TestReport).filter(
                    TestReport.execution_id == execution_id
                )
                result = await session.execute(stmt)
                report = result.scalar_one_or_none()

                if report and report.report_path:
                    # 验证文件是否存在
                    if os.path.exists(report.report_path):
                        logger.info(f"从MySQL获取报告路径: {report.report_path}")
                        return report.report_path
                    else:
                        logger.warning(f"MySQL中的报告文件不存在: {report.report_path}")

            # 如果数据库中没有或文件不存在，尝试默认路径
            index_html = self.report_base_dir / "index.html"
            if index_html.exists():
                logger.info(f"使用默认报告路径: {index_html}")
                return str(index_html)

        except Exception as e:
            logger.warning(f"获取报告文件路径失败: {str(e)}")

        return None

    async def get_report_file_path_by_script_id(self, script_id: str) -> Optional[str]:
        """根据脚本ID获取最新报告文件路径"""
        try:
            async with db_manager.get_session() as session:
                from sqlalchemy import select
                stmt = select(TestReport).filter(
                    TestReport.script_id == script_id
                ).order_by(desc(TestReport.created_at))
                result = await session.execute(stmt)
                report = result.scalars().first()  # 使用first()而不是scalar_one_or_none()

                if report and report.report_path:
                    # 验证文件是否存在
                    if os.path.exists(report.report_path):
                        logger.info(f"从MySQL获取脚本 {script_id} 的报告路径: {report.report_path}")
                        return report.report_path
                    else:
                        logger.warning(f"MySQL中的报告文件不存在: {report.report_path}")

        except Exception as e:
            logger.warning(f"根据脚本ID获取报告文件路径失败: {str(e)}")

        return None

    def _safe_serialize_config(self, config: Any) -> Dict[str, Any]:
        """安全序列化配置对象为字典"""
        if config is None:
            return {}

        try:
            # 如果是字典，直接返回
            if isinstance(config, dict):
                return config

            # 如果是Pydantic模型，转换为字典
            if hasattr(config, 'dict'):
                return config.dict()

            # 如果是Pydantic模型（新版本），转换为字典
            if hasattr(config, 'model_dump'):
                return config.model_dump()

            # 如果有__dict__属性，转换为字典
            if hasattr(config, '__dict__'):
                result = {}
                for key, value in config.__dict__.items():
                    if not key.startswith('_'):  # 跳过私有属性
                        try:
                            # 尝试JSON序列化测试
                            json.dumps(value)
                            result[key] = value
                        except (TypeError, ValueError):
                            # 如果不能序列化，转换为字符串
                            result[key] = str(value)
                return result

            # 如果都不行，尝试转换为字符串然后解析
            if hasattr(config, '__str__'):
                config_str = str(config)
                try:
                    # 尝试解析为JSON
                    return json.loads(config_str)
                except (json.JSONDecodeError, ValueError):
                    # 如果解析失败，返回字符串形式
                    return {"raw_config": config_str}

            # 最后的备选方案
            return {"config_type": str(type(config)), "config_value": str(config)}

        except Exception as e:
            logger.warning(f"序列化配置对象失败: {str(e)}, 配置类型: {type(config)}")
            return {"error": f"序列化失败: {str(e)}", "config_type": str(type(config))}

    def _safe_serialize_logs(self, logs: List[Any]) -> List[str]:
        """安全序列化日志列表"""
        if not logs:
            return []

        safe_logs = []
        for log in logs:
            try:
                if isinstance(log, str):
                    safe_logs.append(log)
                else:
                    # 尝试转换为字符串
                    safe_logs.append(str(log))
            except Exception as e:
                safe_logs.append(f"日志序列化失败: {str(e)}")

        return safe_logs


# 创建全局服务实例
test_report_service = TestReportService()
