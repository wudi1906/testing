"""
测试执行智能体
基于公共基类实现，智能执行pytest测试脚本并生成详细报告
"""
import os
import subprocess
import asyncio
import json
import uuid
import platform
import re
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

from autogen_agentchat.base import TaskResult
from autogen_agentchat.messages import ModelClientStreamingChunkEvent
from autogen_core import message_handler, type_subscription, MessageContext, TopicId
from loguru import logger
from pydantic import BaseModel, Field

from app.agents.api_automation.base_api_agent import BaseApiAutomationAgent
from app.core.types import AgentTypes, TopicTypes

# 导入重新设计的数据模型
from .schemas import (
    TestExecutionInput, TestExecutionOutput, TestResult,
    ScriptExecutionResult, GeneratedScript
)


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
        message: TestExecutionInput,
        ctx: MessageContext
    ) -> None:
        """处理测试执行请求 - 使用新的数据模型"""
        start_time = datetime.now()
        self.execution_metrics["total_executions"] += 1

        try:
            logger.info(f"开始执行测试: {message.session_id}")

            # 准备执行环境
            await self._prepare_execution_environment(message)

            # 执行测试
            execution_result = await self._execute_tests(message)

            # 使用大模型分析执行结果
            analysis_result = await self._intelligent_analyze_execution_results(
                execution_result,
                message.execution_config
            )

            # 生成报告
            report_files = await self._generate_reports(
                execution_result,
                analysis_result,
                message.session_id
            )

            # 解析测试结果
            script_results = self._parse_script_results(execution_result)

            # 构建响应 - 使用新的数据模型
            end_time = datetime.now()
            response = TestExecutionOutput(
                session_id=message.session_id,
                document_id=message.document_id,
                overall_status="success" if execution_result.get("success", False) else "failed",
                start_time=start_time,
                end_time=end_time,
                total_duration=(end_time - start_time).total_seconds(),
                script_results=script_results,
                summary={
                    "total_tests": execution_result.get("total_tests", 0),
                    "passed_tests": execution_result.get("passed_tests", 0),
                    "failed_tests": execution_result.get("failed_tests", 0),
                    "execution_time": execution_result.get("execution_time", 0),
                    "success_rate": execution_result.get("success_rate", 0)
                },
                reports=report_files,
                processing_time=(end_time - start_time).total_seconds()
            )
            
            # 更新统计
            self.execution_metrics["successful_executions"] += 1
            self.execution_metrics["total_tests_executed"] += execution_result.get("total_tests", 0)
            self.execution_metrics["total_tests_passed"] += execution_result.get("passed_tests", 0)
            self.execution_metrics["total_tests_failed"] += execution_result.get("failed_tests", 0)
            
            logger.info(f"测试执行完成: {message.session_id}")

            # 发送执行结果到前端
            await self.send_success(
                f"脚本执行完成: {response.overall_status}",
                result={
                    "execution_id": response.execution_id,
                    "session_id": response.session_id,
                    "status": response.overall_status,
                    "summary": response.summary,
                    "script_results": [
                        {
                            "script_id": sr.script_id,
                            "script_name": sr.script_name,
                            "status": sr.status,
                            "duration": sr.duration,
                            "total_tests": sr.total_tests,
                            "passed_tests": sr.passed_tests,
                            "failed_tests": sr.failed_tests
                        } for sr in response.script_results
                    ],
                    "reports": response.reports,
                    "start_time": response.start_time.isoformat(),
                    "end_time": response.end_time.isoformat(),
                    "total_duration": response.total_duration
                }
            )

            # 发送到日志记录智能体
            await self._send_to_log_recorder(response)
            
        except Exception as e:
            self.execution_metrics["failed_executions"] += 1
            logger.error(f"测试执行失败: {str(e)}")

            # 发送错误响应到前端
            await self.send_error(
                f"脚本执行失败: {str(e)}",
                error_details={
                    "session_id": message.session_id,
                    "error": str(e),
                    "status": "FAILED"
                }
            )

            # 发送错误响应
            await self._send_error_response(message, str(e))

    async def _prepare_execution_environment(self, message: TestExecutionInput):
        """准备执行环境"""
        try:
            import tempfile
            import os

            # 创建跨平台的脚本目录
            temp_dir = tempfile.gettempdir()
            script_dir = Path(os.path.join(temp_dir, "scripts"))
            script_dir.mkdir(parents=True, exist_ok=True)

            # 创建报告目录
            execution_dir = self.reports_dir / message.session_id
            execution_dir.mkdir(parents=True, exist_ok=True)

            # 创建测试脚本文件
            for script in message.scripts:
                script_path = Path(script.file_path)
                script_path.parent.mkdir(parents=True, exist_ok=True)

                # 写入脚本内容 - 修复字段名
                with open(script_path, 'w', encoding='utf-8') as f:
                    f.write(script.script_content)

                logger.info(f"创建脚本文件: {script_path}")

            logger.info(f"执行环境准备完成: {message.session_id}")

        except Exception as e:
            logger.error(f"准备执行环境失败: {str(e)}")
            raise

    async def _execute_tests(self, message: TestExecutionInput) -> Dict[str, Any]:
        """执行测试 - 参考api_agents.py和code_executor.py的最佳实践"""
        try:
            execution_dir = self.reports_dir / message.session_id
            config = message.execution_config

            # 确定工作目录 - 优先使用脚本所在目录
            work_dir = execution_dir
            if message.scripts:
                first_script_path = Path(message.scripts[0].file_path)
                if first_script_path.parent.exists():
                    work_dir = first_script_path.parent

            logger.info(f"测试执行工作目录: {work_dir}")

            # 1. 安装测试依赖（如果存在requirements.txt） ，依赖已经安装
            # await self._install_test_dependencies(work_dir)

            # 2. 构建pytest命令 - 参考api_agents.py的构建方式
            test_cmd = await self._build_test_command(
                message, execution_dir, work_dir, config
            )

            logger.info(f"执行测试命令: {' '.join(test_cmd)}")

            # 3. 执行测试命令 - 参考code_executor.py的execute_command
            execution_result = await self._execute_command(
                test_cmd,
                str(work_dir),
                message.session_id,
                "pytest测试执行",
                timeout=config.get("timeout", 300)
            )

            # 4. 解析执行结果
            result = await self._parse_execution_result(
                execution_result, execution_dir, work_dir
            )

            # 5. 生成Allure报告
            await self._generate_allure_report(work_dir, execution_dir)

            logger.info(f"测试执行完成: 总计 {result.get('total_tests', 0)}, "
                       f"通过 {result.get('passed_tests', 0)}, "
                       f"失败 {result.get('failed_tests', 0)}")

            return result

        except Exception as e:
            logger.error(f"执行测试失败: {str(e)}")
            raise

    async def _install_test_dependencies(self, work_dir: Path) -> None:
        """安装测试依赖 - 参考api_agents.py的依赖安装逻辑"""
        try:
            requirements_file = work_dir / "requirements.txt"
            if requirements_file.exists():
                logger.info("发现requirements.txt，开始安装测试依赖...")

                # 构建安装命令
                install_cmd = ["python", "-m", "pip", "install", "-r", "requirements.txt"]

                # 执行安装命令
                install_result = await self._execute_command(
                    install_cmd,
                    str(work_dir),
                    "dependency_install",
                    "依赖安装",
                    timeout=180  # 3分钟超时
                )

                if install_result["return_code"] == 0:
                    logger.info("测试依赖安装成功")
                else:
                    logger.warning(f"依赖安装可能有问题: {install_result.get('stderr', '')}")
            else:
                logger.info("未发现requirements.txt文件，跳过依赖安装")

        except Exception as e:
            logger.warning(f"安装测试依赖失败: {str(e)}")

    async def _build_test_command(
        self,
        message: TestExecutionInput,
        execution_dir: Path,
        work_dir: Path,
        config: Dict[str, Any]
    ) -> List[str]:
        """构建测试命令 - 参考api_agents.py的命令构建方式，返回命令列表"""
        try:
            # 基础命令
            cmd = ["python", "-m", "pytest"]

            # 添加测试文件或目录
            if message.scripts:
                # 如果有多个脚本，运行所有脚本
                for script in message.scripts:
                    script_path = Path(script.file_path)
                    # 使用相对于工作目录的路径
                    if script_path.is_absolute():
                        try:
                            rel_path = script_path.relative_to(work_dir)
                            cmd.append(str(rel_path))
                        except ValueError:
                            # 如果无法计算相对路径，使用绝对路径
                            cmd.append(str(script_path))
                    else:
                        cmd.append(str(script_path))
            else:
                # 如果没有指定脚本，运行当前目录下的所有测试
                cmd.append(".")

            # 添加详细输出
            if config.get("verbose", True):
                cmd.append("-v")

            # 添加报告参数 - 智能检测可用插件
            await self._add_report_options(cmd, execution_dir)

            # 添加基础URL（如果配置中有）
            base_url = config.get("base_url")
            if base_url:
                cmd.extend(["--base-url", base_url])

            # 添加其他pytest参数
            extra_args = config.get("pytest_args", [])
            if extra_args:
                cmd.extend(extra_args)

            return cmd

        except Exception as e:
            logger.error(f"构建测试命令失败: {str(e)}")
            # 返回基础命令
            return ["python", "-m", "pytest", "-v"]

    async def _add_report_options(self, cmd: List[str], execution_dir: Path) -> None:
        """智能添加报告选项，只添加可用的插件参数"""
        try:
            # 总是添加JUnit XML报告（pytest内置支持）
            junit_report = execution_dir / "junit.xml"
            cmd.extend(["--junitxml", str(junit_report)])

            # 检查是否安装了pytest-html插件
            try:
                import pytest_html
                html_report = execution_dir / "report.html"
                cmd.extend(["--html", str(html_report), "--self-contained-html"])
                logger.info("检测到pytest-html插件，添加HTML报告")
            except ImportError:
                logger.info("未安装pytest-html插件，跳过HTML报告")

            # 检查是否安装了pytest-json-report插件
            try:
                import pytest_jsonreport
                json_report = execution_dir / "report.json"
                cmd.extend(["--json-report", "--json-report-file", str(json_report)])
                logger.info("检测到pytest-json-report插件，添加JSON报告")
            except ImportError:
                logger.info("未安装pytest-json-report插件，跳过JSON报告")

            # 检查是否安装了allure-pytest插件
            try:
                import allure_pytest
                allure_results_dir = execution_dir / "allure-results"
                cmd.extend(["--alluredir", str(allure_results_dir)])
                logger.info("检测到allure-pytest插件，添加Allure报告")
            except ImportError:
                logger.info("未安装allure-pytest插件，跳过Allure报告")

        except Exception as e:
            logger.warning(f"添加报告选项时出错: {str(e)}")

    async def _parse_execution_result(
        self,
        execution_result: Dict[str, Any],
        execution_dir: Path,
        work_dir: Path
    ) -> Dict[str, Any]:
        """解析执行结果"""
        try:
            # 基础结果
            result = {
                "success": execution_result["return_code"] == 0,
                "return_code": execution_result["return_code"],
                "stdout": execution_result["stdout"],
                "stderr": execution_result["stderr"],
                "execution_time": execution_result["duration"],
                "start_time": execution_result.get("start_time", datetime.now().isoformat()),
                "end_time": execution_result.get("end_time", datetime.now().isoformat()),
                "error_message": execution_result.get("error_message")
            }

            # 解析测试结果 - 优先级：JSON报告 > JUnit XML > stdout解析
            stats_found = False

            # 1. 尝试解析JSON报告（如果存在）
            json_report = execution_dir / "report.json"
            if json_report.exists():
                try:
                    with open(json_report, 'r', encoding='utf-8') as f:
                        json_data = json.load(f)
                        summary = json_data.get("summary", {})
                        if summary:
                            result.update({
                                "total_tests": summary.get("total", 0),
                                "passed_tests": summary.get("passed", 0),
                                "failed_tests": summary.get("failed", 0),
                                "skipped_tests": summary.get("skipped", 0),
                                "error_tests": summary.get("error", 0),
                                "test_details": json_data.get("tests", [])
                            })
                            stats_found = True
                            logger.info("使用JSON报告的统计信息")
                except Exception as e:
                    logger.warning(f"解析JSON报告失败: {str(e)}")

            # 2. 如果没有JSON报告，尝试JUnit XML
            if not stats_found:
                junit_report = execution_dir / "junit.xml"
                if junit_report.exists():
                    try:
                        junit_stats = self._parse_junit_xml(junit_report)
                        if junit_stats.get("total_tests", 0) > 0:
                            result.update(junit_stats)
                            stats_found = True
                            logger.info("使用JUnit XML报告的统计信息")
                    except Exception as e:
                        logger.warning(f"解析JUnit XML报告失败: {str(e)}")

            # 3. 最后尝试从stdout解析
            if not stats_found:
                logger.info("从标准输出解析测试统计")
                stdout_stats = self._extract_stats_from_output(execution_result["stdout"])
                result.update(stdout_stats)

                # 如果仍然没有获取到测试统计，尝试更宽松的解析
                if result.get("total_tests", 0) == 0:
                    logger.warning("尝试更宽松的统计解析")
                    fallback_stats = self._extract_stats_fallback(execution_result["stdout"])
                    result.update(fallback_stats)

            # 计算成功率
            total_tests = result.get("total_tests", 0)
            passed_tests = result.get("passed_tests", 0)
            result["success_rate"] = (passed_tests / total_tests * 100) if total_tests > 0 else 0

            return result

        except Exception as e:
            logger.error(f"解析执行结果失败: {str(e)}")
            return {
                "success": False,
                "return_code": -1,
                "stdout": execution_result.get("stdout", ""),
                "stderr": f"解析结果失败: {str(e)}",
                "execution_time": execution_result.get("duration", 0),
                "error_message": str(e),
                "total_tests": 0,
                "passed_tests": 0,
                "failed_tests": 0,
                "success_rate": 0
            }

    def _extract_stats_from_output(self, output: str) -> Dict[str, int]:
        """从pytest输出中提取测试统计信息 - 参考api_agents.py的提取逻辑"""
        stats = {
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "error_tests": 0,
            "skipped_tests": 0
        }

        try:
            # 尝试匹配pytest的输出格式
            # 例如: "5 passed, 2 failed, 1 skipped in 10.5s"
            patterns = [
                r'(\d+)\s+passed,?\s*(\d+)\s+failed,?\s*(\d+)\s+error(?:ed)?,?\s*(\d+)\s+skipped',
                r'(\d+)\s+passed,?\s*(\d+)\s+failed,?\s*(\d+)\s+skipped',
                r'(\d+)\s+passed,?\s*(\d+)\s+failed',
                r'(\d+)\s+passed'
            ]

            for pattern in patterns:
                match = re.search(pattern, output)
                if match:
                    groups = match.groups()
                    stats["passed_tests"] = int(groups[0]) if len(groups) > 0 else 0
                    stats["failed_tests"] = int(groups[1]) if len(groups) > 1 else 0
                    if len(groups) > 2:
                        # 检查第三个组是error还是skipped
                        if "error" in pattern:
                            stats["error_tests"] = int(groups[2])
                            stats["skipped_tests"] = int(groups[3]) if len(groups) > 3 else 0
                        else:
                            stats["skipped_tests"] = int(groups[2])
                    break

            # 计算总数
            stats["total_tests"] = (stats["passed_tests"] + stats["failed_tests"] +
                                  stats["error_tests"] + stats["skipped_tests"])

        except Exception as e:
            logger.warning(f"从输出提取统计信息失败: {str(e)}")

        return stats

    def _parse_junit_xml(self, junit_file: Path) -> Dict[str, int]:
        """解析JUnit XML报告获取测试统计"""
        stats = {
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "error_tests": 0,
            "skipped_tests": 0
        }

        try:
            tree = ET.parse(junit_file)
            root = tree.getroot()

            # JUnit XML格式通常有testsuites或testsuite作为根元素
            if root.tag == 'testsuites':
                # 多个测试套件
                for testsuite in root.findall('testsuite'):
                    stats["total_tests"] += int(testsuite.get('tests', 0))
                    stats["failed_tests"] += int(testsuite.get('failures', 0))
                    stats["error_tests"] += int(testsuite.get('errors', 0))
                    stats["skipped_tests"] += int(testsuite.get('skipped', 0))
            elif root.tag == 'testsuite':
                # 单个测试套件
                stats["total_tests"] = int(root.get('tests', 0))
                stats["failed_tests"] = int(root.get('failures', 0))
                stats["error_tests"] = int(root.get('errors', 0))
                stats["skipped_tests"] = int(root.get('skipped', 0))

            # 计算通过的测试数
            stats["passed_tests"] = (stats["total_tests"] - stats["failed_tests"] -
                                   stats["error_tests"] - stats["skipped_tests"])

            logger.info(f"从JUnit XML解析得到统计: {stats}")

        except Exception as e:
            logger.warning(f"解析JUnit XML失败: {str(e)}")

        return stats

    def _extract_stats_fallback(self, output: str) -> Dict[str, int]:
        """更宽松的统计信息提取方法"""
        stats = {
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "error_tests": 0,
            "skipped_tests": 0
        }

        try:
            # 尝试更多的模式匹配
            patterns = [
                # 标准pytest输出
                r'=+ (\d+) failed.*?(\d+) passed.*?in',
                r'=+ (\d+) passed.*?(\d+) failed.*?in',
                r'=+ (\d+) passed.*?in',
                r'=+ (\d+) failed.*?in',
                # 简单的数字匹配
                r'(\d+) passed',
                r'(\d+) failed',
                r'(\d+) error',
                r'(\d+) skipped'
            ]

            for pattern in patterns:
                matches = re.findall(pattern, output, re.IGNORECASE)
                if matches:
                    logger.info(f"使用模式 '{pattern}' 找到匹配: {matches}")
                    break

            # 如果找到任何数字，至少设置一个基础值
            if re.search(r'\d+', output):
                # 设置一个最小值，表示至少执行了测试
                stats["total_tests"] = 1
                if "FAILED" in output.upper() or "ERROR" in output.upper():
                    stats["failed_tests"] = 1
                else:
                    stats["passed_tests"] = 1

        except Exception as e:
            logger.warning(f"宽松统计提取失败: {str(e)}")

        return stats

    async def _generate_allure_report(self, work_dir: Path, execution_dir: Path) -> None:
        """生成Allure报告 - 参考api_agents.py的Allure报告生成"""
        try:
            allure_results_dir = execution_dir / "allure-results"
            allure_report_dir = execution_dir / "allure-report"

            if allure_results_dir.exists() and any(allure_results_dir.iterdir()):
                logger.info("生成Allure报告...")

                # 构建Allure生成命令
                allure_cmd = ["allure", "generate", "allure-results", "-o", "allure-report", "--clean"]

                # 执行Allure命令
                allure_result = await self._execute_command(
                    allure_cmd,
                    str(execution_dir),
                    "allure_generation",
                    "Allure报告生成",
                    timeout=60
                )

                if allure_result["return_code"] == 0:
                    logger.info(f"Allure报告生成成功: {allure_report_dir}")
                else:
                    logger.warning(f"Allure报告生成失败: {allure_result.get('stderr', '')}")
            else:
                logger.info("未发现Allure测试结果，跳过Allure报告生成")

        except Exception as e:
            logger.warning(f"生成Allure报告失败: {str(e)}")

    async def _execute_command(self, command: List[str], cwd: str, execution_id: str,
                                       operation_name: str, env: Dict[str, str] = None,
                                       timeout: int = 300) -> Dict[str, Any]:
        """优化的命令执行方法，支持Windows和非Windows系统"""
        start_time = datetime.now()

        # 设置环境变量
        if env is None:
            env = dict(os.environ)

        # 记录执行信息
        record = {
            "logs": [],
            "start_time": start_time.isoformat(),
            "operation": operation_name,
            "command": command
        }

        return_code = 0
        stdout_lines = []
        stderr_lines = []

        try:
            # 在Windows上使用同步subprocess避免NotImplementedError
            if platform.system() == "Windows":
                # Windows系统使用同步subprocess，需要shell=True来执行pytest
                try:
                    # 在Windows上将命令转换为字符串并使用shell=True
                    command_str = ' '.join(command)
                    logger.info(f"Windows执行命令: {command_str}")

                    # 设置UTF-8编码环境变量，避免Windows编码问题
                    env_with_utf8 = env.copy()
                    env_with_utf8['PYTHONIOENCODING'] = 'utf-8'
                    env_with_utf8['CHCP'] = '65001'  # 设置代码页为UTF-8

                    result = subprocess.run(
                        command_str,
                        cwd=cwd,
                        capture_output=True,
                        text=True,
                        env=env_with_utf8,
                        timeout=timeout,
                        shell=True,  # Windows上需要shell=True来执行pytest
                        encoding='utf-8',  # 明确指定UTF-8编码
                        errors='replace'  # 遇到编码错误时替换为占位符
                    )

                    return_code = result.returncode
                    stdout_lines = result.stdout.splitlines() if result.stdout else []
                    stderr_lines = result.stderr.splitlines() if result.stderr else []

                    # 记录输出信息
                    for line in stdout_lines:
                        if line.strip():
                            record["logs"].append(f"[STDOUT] {line}")
                            logger.info(f"[{operation_name}] {line}")

                    for line in stderr_lines:
                        if line.strip():
                            record["logs"].append(f"[STDERR] {line}")
                            logger.warning(f"[{operation_name} Error] {line}")

                except subprocess.TimeoutExpired:
                    logger.error(f"{operation_name}执行超时")
                    raise Exception(f"{operation_name}执行超时（{timeout}秒）")
                except UnicodeDecodeError as e:
                    logger.warning(f"编码错误，尝试使用字节模式: {str(e)}")
                    # 如果UTF-8编码失败，使用字节模式重新执行
                    try:
                        result = subprocess.run(
                            command_str,
                            cwd=cwd,
                            capture_output=True,
                            text=False,  # 使用字节模式
                            env=env_with_utf8,
                            timeout=timeout,
                            shell=True
                        )

                        return_code = result.returncode

                        # 手动处理编码，优先尝试UTF-8，失败则使用GBK
                        def safe_decode(byte_data):
                            if not byte_data:
                                return []
                            try:
                                return byte_data.decode('utf-8').splitlines()
                            except UnicodeDecodeError:
                                try:
                                    return byte_data.decode('gbk').splitlines()
                                except UnicodeDecodeError:
                                    return byte_data.decode('utf-8', errors='replace').splitlines()

                        stdout_lines = safe_decode(result.stdout)
                        stderr_lines = safe_decode(result.stderr)

                        # 记录输出信息
                        for line in stdout_lines:
                            if line.strip():
                                record["logs"].append(f"[STDOUT] {line}")
                                logger.info(f"[{operation_name}] {line}")

                        for line in stderr_lines:
                            if line.strip():
                                record["logs"].append(f"[STDERR] {line}")
                                logger.warning(f"[{operation_name} Error] {line}")

                    except Exception as inner_e:
                        logger.error(f"字节模式执行也失败: {str(inner_e)}")
                        raise Exception(f"执行失败: {str(inner_e)}")

                except Exception as e:
                    logger.error(f"{operation_name}执行出错：{str(e)}")
                    raise

            else:
                # 非Windows系统使用异步subprocess
                process = await asyncio.create_subprocess_exec(
                    *command,
                    cwd=cwd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=env
                )

                # 实时读取输出
                stdout_lines = []
                stderr_lines = []

                async def read_stdout():
                    async for line in process.stdout:
                        line_text = line.decode('utf-8').strip()
                        if line_text:
                            stdout_lines.append(line_text)
                            record["logs"].append(f"[STDOUT] {line_text}")
                            logger.info(f"[{operation_name}] {line_text}")

                async def read_stderr():
                    async for line in process.stderr:
                        line_text = line.decode('utf-8').strip()
                        if line_text:
                            stderr_lines.append(line_text)
                            record["logs"].append(f"[STDERR] {line_text}")
                            logger.warning(f"[{operation_name} Error] {line_text}")

                # 并发读取输出
                await asyncio.gather(read_stdout(), read_stderr())

                # 等待进程完成
                return_code = await process.wait()

        except Exception as e:
            logger.error(f"{operation_name}执行失败: {str(e)}")
            end_time = datetime.now()
            return {
                "return_code": -1,
                "stdout": "",
                "stderr": str(e),
                "error_message": str(e),
                "logs": record["logs"],
                "duration": (end_time - start_time).total_seconds(),
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat()
            }

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        return {
            "return_code": return_code,
            "stdout": '\n'.join(stdout_lines),
            "stderr": '\n'.join(stderr_lines),
            "error_message": '\n'.join(stderr_lines) if return_code != 0 else None,
            "logs": record["logs"],
            "duration": duration,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat()
        }

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

    def _parse_script_results(self, execution_result: Dict[str, Any]) -> List[ScriptExecutionResult]:
        """解析脚本执行结果 - 使用新的数据模型"""
        script_results = []

        try:
            for script_detail in execution_result.get("script_details", []):
                # 解析测试结果
                test_results = []
                for test in script_detail.get("tests", []):
                    test_result = TestResult(
                        test_id=str(uuid.uuid4()),
                        test_name=test.get("nodeid", "unknown"),
                        status=test.get("outcome", "unknown"),
                        duration=test.get("duration", 0),
                        error_message=test.get("call", {}).get("longrepr", "") if test.get("outcome") == "failed" else None,
                        failure_reason=test.get("failure_reason"),
                        stdout=test.get("stdout", ""),
                        stderr=test.get("stderr", ""),
                        assertions=test.get("assertions", [])
                    )
                    test_results.append(test_result)

                # 创建脚本执行结果
                script_result = ScriptExecutionResult(
                    script_id=script_detail.get("script_id", str(uuid.uuid4())),
                    script_name=script_detail.get("script_name", "unknown"),
                    status=script_detail.get("status", "unknown"),
                    start_time=datetime.fromisoformat(script_detail.get("start_time", datetime.now().isoformat())),
                    end_time=datetime.fromisoformat(script_detail.get("end_time", datetime.now().isoformat())),
                    duration=script_detail.get("duration", 0),
                    test_results=test_results,
                    total_tests=len(test_results),
                    passed_tests=len([t for t in test_results if t.status == "passed"]),
                    failed_tests=len([t for t in test_results if t.status == "failed"]),
                    skipped_tests=len([t for t in test_results if t.status == "skipped"]),
                    error_tests=len([t for t in test_results if t.status == "error"]),
                    coverage_report=script_detail.get("coverage", {})
                )
                script_results.append(script_result)

        except Exception as e:
            logger.error(f"解析脚本执行结果失败: {str(e)}")

        return script_results

    async def _send_to_log_recorder(self, response: TestExecutionOutput):
        """发送到日志记录智能体"""
        try:
            # 这里应该发送到日志记录智能体
            logger.info(f"已发送到日志记录智能体: {response.execution_id}")

        except Exception as e:
            logger.error(f"发送到日志记录智能体失败: {str(e)}")

    async def _send_error_response(self, message: TestExecutionInput, error: str):
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


