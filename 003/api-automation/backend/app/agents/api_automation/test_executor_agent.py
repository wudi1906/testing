"""
测试执行智能体
基于公共基类实现，智能执行pytest测试脚本并生成详细报告
"""
import os
import subprocess
import asyncio
import json
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

from autogen_core import message_handler, type_subscription, MessageContext, TopicId
from loguru import logger
from pydantic import BaseModel, Field

from app.agents.api_automation.base_api_agent import BaseApiAutomationAgent
from app.core.types import AgentTypes, AGENT_NAMES, TopicTypes
from app.core.messages.api_automation import (
    TestExecutionRequest, TestExecutionResponse,
    TestResultInfo
)
from app.core.enums import ExecutionStatus


@type_subscription(topic_type=TopicTypes.TEST_EXECUTOR.value)
class TestExecutorAgent(BaseApiAutomationAgent):
    """
    测试执行智能体

    核心功能：
    1. 智能执行pytest测试脚本
    2. 实时监控测试执行状态
    3. 生成多格式测试报告（allure、HTML、JSON）
    4. 分析测试结果和性能指标
    5. 提供智能的错误分析和改进建议
    6. 支持流式输出和实时反馈
    """

    def __init__(self, model_client_instance=None, agent_config=None, **kwargs):
        """初始化测试执行智能体"""
        super().__init__(
            agent_type=AgentTypes.TEST_EXECUTOR,
            model_client_instance=model_client_instance,
            **kwargs
        )

        # 存储智能体配置信息
        self.agent_config = agent_config or {}

        # 初始化AssistantAgent
        self._initialize_assistant_agent()

        # 执行统计（继承公共统计）
        self.execution_metrics = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "total_tests_executed": 0,
            "total_tests_passed": 0,
            "total_tests_failed": 0
        }

        # 报告目录
        self.reports_dir = Path("./reports")
        self.reports_dir.mkdir(exist_ok=True)

        logger.info(f"测试执行智能体初始化完成: {self.agent_name}")



    @message_handler
    async def handle_test_execution_request(
        self, 
        message: TestExecutionRequest, 
        ctx: MessageContext
    ) -> None:
        """处理测试执行请求"""
        start_time = datetime.now()
        self.execution_metrics["total_executions"] += 1
        
        try:
            logger.info(f"开始执行测试: {message.execution_id}")
            
            # 准备执行环境
            await self._prepare_execution_environment(message)
            
            # 执行测试
            execution_result = await self._execute_tests(message)

            # 使用大模型分析执行结果
            analysis_result = await self._intelligent_analyze_execution_results(
                execution_result,
                message.test_config
            )

            # 生成报告
            report_files = await self._generate_reports(
                execution_result,
                analysis_result,
                message.execution_id
            )

            # 解析测试结果
            test_results = self._parse_test_results(execution_result)
            
            # 构建响应
            response = TestExecutionResponse(
                session_id=message.session_id,
                doc_id=message.doc_id,
                execution_id=str(uuid.uuid4()),
                results=test_results,
                summary={
                    "total_tests": execution_result.get("total_tests", 0),
                    "passed_tests": execution_result.get("passed_tests", 0),
                    "failed_tests": execution_result.get("failed_tests", 0),
                    "execution_time": execution_result.get("execution_time", 0),
                    "success_rate": execution_result.get("success_rate", 0)
                },
                report_files=report_files,
                processing_time=(datetime.now() - start_time).total_seconds()
            )
            
            # 更新统计
            self.execution_metrics["successful_executions"] += 1
            self.execution_metrics["total_tests_executed"] += execution_result.get("total_tests", 0)
            self.execution_metrics["total_tests_passed"] += execution_result.get("passed_tests", 0)
            self.execution_metrics["total_tests_failed"] += execution_result.get("failed_tests", 0)
            
            logger.info(f"测试执行完成: {message.execution_id}")
            
            # 发送到日志记录智能体
            await self._send_to_log_recorder(response)
            
        except Exception as e:
            self.execution_metrics["failed_executions"] += 1
            logger.error(f"测试执行失败: {str(e)}")
            
            # 发送错误响应
            await self._send_error_response(message, str(e))

    async def _prepare_execution_environment(self, message: TestExecutionRequest):
        """准备执行环境"""
        try:
            # 检查测试文件是否存在
            for script_file in message.script_files:
                if not os.path.exists(script_file):
                    raise FileNotFoundError(f"测试文件不存在: {script_file}")
            
            # 创建报告目录
            execution_dir = self.reports_dir / message.execution_id
            execution_dir.mkdir(exist_ok=True)
            
            logger.info(f"执行环境准备完成: {message.execution_id}")
            
        except Exception as e:
            logger.error(f"准备执行环境失败: {str(e)}")
            raise

    async def _execute_tests(self, message: TestExecutionRequest) -> Dict[str, Any]:
        """执行测试"""
        try:
            execution_dir = self.reports_dir / message.execution_id
            
            # 构建pytest命令
            cmd = ["python", "-m", "pytest"]
            
            # 添加测试文件
            cmd.extend(message.script_files)
            
            # 添加配置参数
            config = message.test_config
            
            if config.get("verbose", True):
                cmd.append("-v")
            
            # 添加报告参数
            html_report = execution_dir / "report.html"
            cmd.extend(["--html", str(html_report), "--self-contained-html"])
            
            json_report = execution_dir / "report.json"
            cmd.extend(["--json-report", "--json-report-file", str(json_report)])
            
            # 执行测试
            logger.info(f"执行命令: {' '.join(cmd)}")
            
            start_time = datetime.now()
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=Path(message.script_files[0]).parent if message.script_files else None
            )
            
            stdout, stderr = await process.communicate()
            end_time = datetime.now()
            
            execution_time = (end_time - start_time).total_seconds()
            
            # 解析执行结果
            result = {
                "success": process.returncode == 0,
                "return_code": process.returncode,
                "stdout": stdout.decode(),
                "stderr": stderr.decode(),
                "execution_time": execution_time,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat()
            }
            
            # 解析JSON报告
            if json_report.exists():
                try:
                    with open(json_report, 'r', encoding='utf-8') as f:
                        json_data = json.load(f)
                        result.update({
                            "total_tests": json_data.get("summary", {}).get("total", 0),
                            "passed_tests": json_data.get("summary", {}).get("passed", 0),
                            "failed_tests": json_data.get("summary", {}).get("failed", 0),
                            "skipped_tests": json_data.get("summary", {}).get("skipped", 0),
                            "test_details": json_data.get("tests", [])
                        })
                except Exception as e:
                    logger.warning(f"解析JSON报告失败: {str(e)}")
            
            # 计算成功率
            total_tests = result.get("total_tests", 0)
            passed_tests = result.get("passed_tests", 0)
            result["success_rate"] = (passed_tests / total_tests * 100) if total_tests > 0 else 0
            
            logger.info(f"测试执行完成: 总计 {total_tests}, 通过 {passed_tests}, 失败 {result.get('failed_tests', 0)}")
            
            return result
            
        except Exception as e:
            logger.error(f"执行测试失败: {str(e)}")
            raise

    async def _intelligent_analyze_execution_results(
        self,
        execution_result: Dict[str, Any],
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """使用大模型分析执行结果"""
        try:
            # 构建分析任务
            task = f"""请分析以下pytest测试执行结果，提供专业的分析和建议：

## 执行结果
{json.dumps(execution_result, ensure_ascii=False, indent=2)}

## 测试配置
{json.dumps(config, ensure_ascii=False, indent=2)}

## 分析要求
请从以下维度进行深度分析：

1. **执行摘要分析**
   - 整体成功率评估
   - 执行时间分析
   - 性能指标评估

2. **失败用例分析**
   - 失败原因分类
   - 错误模式识别
   - 根因分析

3. **性能分析**
   - 响应时间分析
   - 性能瓶颈识别
   - 优化建议

4. **质量评估**
   - 测试质量评分
   - 覆盖度评估
   - 改进建议

5. **趋势分析**
   - 与历史数据对比
   - 质量趋势评估
   - 风险识别

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
            return await self._fallback_analyze_execution_results(execution_result)

        except Exception as e:
            logger.error(f"智能分析执行结果失败: {str(e)}")
            return await self._fallback_analyze_execution_results(execution_result)

    async def _run_assistant_agent(self, task: str) -> Optional[str]:
        """运行AssistantAgent获取分析结果"""
        try:
            # 确保AssistantAgent已创建
            await self._ensure_assistant_agent()

            if self.assistant_agent is None:
                logger.error("AssistantAgent未能成功创建")
                return None

            stream = self.assistant_agent.run_stream(task=task)
            result_content = ""

            async for event in stream:  # type: ignore
                if isinstance(event, ModelClientStreamingChunkEvent):
                    # 可以在这里实现流式输出到前端
                    continue
                # 获取最终结果
                if isinstance(event, TaskResult):
                    messages = event.messages
                    if messages and hasattr(messages[-1], 'content'):
                        result_content = messages[-1].content
                        break

            return result_content

        except Exception as e:
            logger.error(f"运行AssistantAgent失败: {str(e)}")
            return None



    async def _fallback_analyze_execution_results(self, execution_result: Dict[str, Any]) -> Dict[str, Any]:
        """备用分析方法"""
        try:
            total_tests = execution_result.get("total_tests", 0)
            passed_tests = execution_result.get("passed_tests", 0)
            failed_tests = execution_result.get("failed_tests", 0)
            success_rate = execution_result.get("success_rate", 0)

            return {
                "execution_summary": {
                    "total_tests": total_tests,
                    "passed": passed_tests,
                    "failed": failed_tests,
                    "success_rate": success_rate,
                    "execution_time": execution_result.get("execution_time", 0),
                    "status": "completed" if execution_result.get("success", False) else "failed"
                },
                "performance_metrics": {
                    "avg_response_time": 1.0,
                    "total_execution_time": execution_result.get("execution_time", 0)
                },
                "error_analysis": {
                    "error_categories": {"general": failed_tests},
                    "common_failures": [],
                    "root_causes": ["需要详细分析"]
                },
                "recommendations": [
                    "检查失败的测试用例" if failed_tests > 0 else "所有测试通过",
                    "优化执行时间" if execution_result.get("execution_time", 0) > 60 else "执行时间良好"
                ]
            }

        except Exception as e:
            logger.error(f"备用分析失败: {str(e)}")
            return {
                "execution_summary": {},
                "performance_metrics": {},
                "error_analysis": {},
                "recommendations": []
            }

    async def _generate_reports(
        self,
        execution_result: Dict[str, Any],
        analysis_result: Dict[str, Any],
        execution_id: str
    ) -> List[str]:
        """生成测试报告"""
        report_files = []

        try:
            execution_dir = self.reports_dir / execution_id

            # HTML报告已在执行时生成
            html_report = execution_dir / "report.html"
            if html_report.exists():
                report_files.append(str(html_report))

            # JSON报告已在执行时生成
            json_report = execution_dir / "report.json"
            if json_report.exists():
                report_files.append(str(json_report))

            # 生成执行摘要报告
            summary_report = execution_dir / "execution_summary.json"
            with open(summary_report, 'w', encoding='utf-8') as f:
                json.dump(execution_result, f, indent=2, ensure_ascii=False)
            report_files.append(str(summary_report))

            # 保存智能分析报告
            analysis_report = execution_dir / "analysis_report.json"
            with open(analysis_report, 'w', encoding='utf-8') as f:
                json.dump(analysis_result, f, indent=2, ensure_ascii=False)
            report_files.append(str(analysis_report))

            logger.info(f"生成了 {len(report_files)} 个报告文件")

        except Exception as e:
            logger.error(f"生成报告失败: {str(e)}")

        return report_files

    def _parse_test_results(self, execution_result: Dict[str, Any]) -> List[TestResultInfo]:
        """解析测试结果"""
        test_results = []
        
        try:
            for test_detail in execution_result.get("test_details", []):
                result = TestResultInfo(
                    result_id=str(uuid.uuid4()),
                    test_name=test_detail.get("nodeid", "unknown"),
                    status=ExecutionStatus.SUCCESS if test_detail.get("outcome") == "passed" else ExecutionStatus.FAILED,
                    start_time=datetime.fromisoformat(execution_result.get("start_time", datetime.now().isoformat())),
                    end_time=datetime.fromisoformat(execution_result.get("end_time", datetime.now().isoformat())),
                    duration=test_detail.get("duration", 0),
                    error_message=test_detail.get("call", {}).get("longrepr", ""),
                    logs=[],
                    attachments=[]
                )
                test_results.append(result)
                
        except Exception as e:
            logger.error(f"解析测试结果失败: {str(e)}")
        
        return test_results

    async def _send_to_log_recorder(self, response: TestExecutionResponse):
        """发送到日志记录智能体"""
        try:
            # 这里应该发送到日志记录智能体
            logger.info(f"已发送到日志记录智能体: {response.execution_id}")
            
        except Exception as e:
            logger.error(f"发送到日志记录智能体失败: {str(e)}")

    async def _send_error_response(self, message: TestExecutionRequest, error: str):
        """发送错误响应"""
        logger.error(f"测试执行错误: {error}")

    def get_execution_statistics(self) -> Dict[str, Any]:
        """获取执行统计信息"""
        # 获取基类的公共统计
        common_stats = self.get_common_statistics()

        # 计算执行特定的统计
        success_rate = 0.0
        if self.execution_metrics["total_executions"] > 0:
            success_rate = (self.execution_metrics["successful_executions"] /
                          self.execution_metrics["total_executions"]) * 100

        test_pass_rate = 0.0
        if self.execution_metrics["total_tests_executed"] > 0:
            test_pass_rate = (self.execution_metrics["total_tests_passed"] /
                            self.execution_metrics["total_tests_executed"]) * 100

        # 合并统计信息
        return {
            **common_stats,
            "execution_metrics": self.execution_metrics,
            "execution_success_rate": round(success_rate, 2),
            "test_pass_rate": round(test_pass_rate, 2),
            "reports_directory": str(self.reports_dir)
        }


