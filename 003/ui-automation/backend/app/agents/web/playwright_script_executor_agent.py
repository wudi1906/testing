"""
Playwright执行智能体 - 全新改造版本
负责执行基于MidScene.js + Playwright的测试脚本
执行环境：C:/Users/86134/Desktop/workspace/playwright-workspace
"""
import os
import json
import uuid
import asyncio
import subprocess
import re
import webbrowser
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

from autogen_core import message_handler, type_subscription, MessageContext
from loguru import logger

from app.core.messages.web import PlaywrightExecutionRequest
from app.core.agents.base import BaseAgent
from app.core.types import TopicTypes, AgentTypes, AGENT_NAMES
from app.services.test_report_service import test_report_service
from app.core.config import settings
from .playwright_script_executor_agent_enhancement import PlaywrightExecutorEnhancement


@type_subscription(topic_type=TopicTypes.PLAYWRIGHT_EXECUTOR.value)
class PlaywrightExecutorAgent(BaseAgent):
    """Playwright执行智能体，负责执行MidScene.js + Playwright测试脚本"""

    def __init__(self, model_client_instance=None, **kwargs):
        """初始化Playwright执行智能体"""
        super().__init__(
            agent_id=AgentTypes.PLAYWRIGHT_EXECUTOR.value,
            agent_name=AGENT_NAMES[AgentTypes.PLAYWRIGHT_EXECUTOR.value],
            model_client_instance=model_client_instance,
            **kwargs
        )
        self.execution_records: Dict[str, Dict[str, Any]] = {}
        # 解析并统一确定 Playwright 工作空间（环境变量/配置/示例目录/最终兜底）
        self.playwright_workspace = self._resolve_playwright_workspace()
        
        # 初始化增强执行器
        self.enhancer = PlaywrightExecutorEnhancement(self)

        logger.info(f"Playwright执行智能体初始化完成: {self.agent_name}")
        logger.info(f"执行环境路径: {self.playwright_workspace}")

    def _validate_workspace(self) -> bool:
        """验证Playwright工作空间是否存在且配置正确"""
        try:
            if not self.playwright_workspace.exists():
                logger.error(f"Playwright工作空间不存在: {self.playwright_workspace}")
                return False

            # 检查package.json是否存在
            package_json = self.playwright_workspace / "package.json"
            if not package_json.exists():
                logger.error(f"package.json不存在: {package_json}")
                return False

            # 检查e2e目录是否存在
            e2e_dir = self.playwright_workspace / "e2e"
            if not e2e_dir.exists():
                logger.warning(f"e2e目录不存在，将自动创建: {e2e_dir}")
                e2e_dir.mkdir(exist_ok=True)

            logger.info("Playwright工作空间验证通过")
            return True

        except Exception as e:
            logger.error(f"验证Playwright工作空间失败: {str(e)}")
            return False

    async def _get_existing_script_path(self, script_name: str) -> Path:
        """获取现有脚本文件路径"""
        try:
            # 如果script_name是绝对路径，直接使用
            if os.path.isabs(script_name):
                script_path = Path(script_name)
                if not script_path.exists():
                    raise FileNotFoundError(f"脚本文件不存在: {script_name}")
                logger.info(f"使用绝对路径脚本文件: {script_path}")
                return script_path

            # 否则在e2e目录中查找
            e2e_dir = self.playwright_workspace / "e2e"
            script_path = e2e_dir / script_name

            if not script_path.exists():
                raise FileNotFoundError(f"脚本文件不存在: {script_name}")

            logger.info(f"找到现有脚本文件: {script_path}")
            return script_path

        except Exception as e:
            logger.error(f"获取脚本文件路径失败: {str(e)}")
            raise

    def _resolve_playwright_workspace(self) -> Path:
        """解析 Playwright 工作空间路径。

        优先级：
        1) 环境变量 PLAYWRIGHT_WORKSPACE
        2) 配置 settings.MIDSCENE_SCRIPT_PATH
        3) 项目内示例目录 examples/midscene-playwright
        4) 兜底到历史固定路径 C:\\Users\\86134\\Desktop\\workspace\\playwright-workspace
        """
        try:
            # 1) 环境变量
            env_path = os.getenv("PLAYWRIGHT_WORKSPACE", "").strip()
            if env_path:
                p = Path(env_path)
                if p.exists():
                    return p

            # 2) 配置
            if getattr(settings, "MIDSCENE_SCRIPT_PATH", None):
                cfg = Path(settings.MIDSCENE_SCRIPT_PATH)
                if cfg.exists():
                    return cfg

            # 3) 项目内示例目录（相对定位到 ui-automation/examples/midscene-playwright）
            try:
                current = Path(__file__).resolve()
                ui_root = None
                for ancestor in current.parents:
                    if ancestor.name == "ui-automation":
                        ui_root = ancestor
                        break
                if ui_root is not None:
                    example = ui_root / "examples" / "midscene-playwright"
                    if example.exists():
                        return example
            except Exception:
                pass

            # 4) 兜底路径
            return Path(r"C:\\Users\\86134\\Desktop\\workspace\\playwright-workspace")
        except Exception as e:
            logger.warning(f"解析Playwright工作空间失败，使用兜底路径: {e}")
            return Path(r"C:\\Users\\86134\\Desktop\\workspace\\playwright-workspace")

    @message_handler
    async def handle_execution_request(self, message: PlaywrightExecutionRequest, ctx: MessageContext) -> None:
        """处理Playwright执行请求"""
        monitor_id = None
        execution_id = None
        try:
            monitor_id = self.start_performance_monitoring("playwright_execution")
            execution_id = str(uuid.uuid4())

            await self.send_response(f"🚀 开始执行Playwright测试脚本: {execution_id}")

            # 验证工作空间
            if not self._validate_workspace():
                await self.send_error("Playwright工作空间验证失败")
                return

            # 创建执行记录
            self.execution_records[execution_id] = {
                "execution_id": execution_id,
                "status": "running",
                "start_time": datetime.now().isoformat(),
                "script_name": message.script_name,
                "test_content": message.test_content,
                "config": message.execution_config.model_dump() if message.execution_config else {},
                "logs": [],
                "screenshots": [],
                "results": None,
                "error_message": None,
                "playwright_output": None,
                "report_path": None
            }

            # 执行Playwright测试
            execution_result = await self._execute_playwright_test(execution_id, message)

            # 更新执行记录
            self.execution_records[execution_id].update(execution_result)

            # 保存执行记录到数据库
            await self._save_execution_record_to_database(execution_id, message, execution_result)

            # 保存测试报告到数据库
            await self._save_test_report_to_database(execution_id, message, execution_result)

            # 如果有报告路径，尝试在浏览器中打开
            # if execution_result.get("report_path"):
            #     await self._open_report_in_browser(execution_result["report_path"])

            await self.send_response(
                f"✅ Playwright测试执行完成: {execution_result['status']}",
                is_final=True,
                result={
                    "execution_id": execution_id,
                    "execution_result": execution_result,
                    "performance_metrics": self.performance_metrics
                }
            )

            if monitor_id:
                self.end_performance_monitoring(monitor_id)

        except Exception as e:
            if monitor_id:
                self.end_performance_monitoring(monitor_id)
            await self.handle_exception("handle_execution_request", e)

    async def _execute_playwright_test(self, execution_id: str, message: PlaywrightExecutionRequest) -> Dict[str, Any]:
        """执行Playwright测试"""
        try:
            record = self.execution_records[execution_id]

            # 确定测试文件路径
            if message.script_name:
                # 使用指定的脚本文件
                test_file_path = await self._get_existing_script_path(message.script_name)
                logger.info(f"使用现有脚本文件: {test_file_path}")
            else:
                # 创建新的测试文件
                test_file_path = await self._create_test_file(execution_id, message.test_content, message.execution_config or {})
                logger.info(f"创建新测试文件: {test_file_path}")

            # 运行测试
            execution_result = await self._run_playwright_test(test_file_path, execution_id)

            # 解析结果和报告
            parsed_result = self._parse_playwright_result(execution_result)

            # 如果是临时创建的文件，清理它
            # if not message.script_name and message.test_content:
            #     await self._cleanup_test_file(test_file_path)

            return parsed_result

        except Exception as e:
            logger.error(f"执行Playwright测试失败: {str(e)}")
            return {
                "status": "error",
                "end_time": datetime.now().isoformat(),
                "error_message": str(e),
                "duration": 0.0
            }

    async def _create_test_file(self, execution_id: str, test_content: str,
                              config: Dict[str, Any]) -> Path:
        """在固定工作空间中创建测试文件"""
        try:
            # 确保e2e目录存在
            e2e_dir = self.playwright_workspace / "e2e"
            e2e_dir.mkdir(exist_ok=True)

            # 创建fixture.ts（如果不存在）
            fixture_path = e2e_dir / "fixture.ts"
            if not fixture_path.exists():
                fixture_content = self._generate_fixture_content(config)
                with open(fixture_path, "w", encoding="utf-8") as f:
                    f.write(fixture_content)
                logger.info(f"创建fixture文件: {fixture_path}")

            # 创建测试文件
            test_filename = f"test-{execution_id}.spec.ts"
            test_file_path = e2e_dir / test_filename

            test_file_content = self._generate_test_file(test_content, config)
            with open(test_file_path, "w", encoding="utf-8") as f:
                f.write(test_file_content)

            logger.info(f"创建测试文件: {test_file_path}")
            return test_file_path

        except Exception as e:
            logger.error(f"创建测试文件失败: {str(e)}")
            raise

    def _generate_fixture_content(self, config: Dict[str, Any]) -> str:
        """生成fixture.ts内容"""
        network_idle_timeout = config.get("network_idle_timeout", 2000) if isinstance(config, dict) else getattr(config, "network_idle_timeout", 2000)

        return f"""import {{ test as base }} from '@playwright/test';
import type {{ PlayWrightAiFixtureType }} from '@midscene/web/playwright';
import {{ PlaywrightAiFixture }} from '@midscene/web/playwright';

export const test = base.extend<PlayWrightAiFixtureType>(PlaywrightAiFixture({{
  waitForNetworkIdleTimeout: {network_idle_timeout},
}}));

export {{ expect }} from '@playwright/test';
"""

    def _generate_test_file(self, test_content: str, config: Dict[str, Any]) -> str:
        """生成测试文件内容"""
        base_url = config.get("base_url", "https://example.com") if isinstance(config, dict) else getattr(config, "base_url", "https://example.com")
        
        # 如果test_content是JavaScript代码，直接使用
        if test_content.strip().startswith("import") or "test(" in test_content:
            return test_content
        
        # 否则生成基础的测试模板
        return f"""import {{ expect }} from "@playwright/test";
import {{ test }} from "./fixture";

test.beforeEach(async ({{ page }}) => {{
  await page.goto("{base_url}");
  await page.waitForLoadState("networkidle");
}});

test("AI自动化测试", async ({{ 
  ai, 
  aiQuery, 
  aiAssert,
  aiInput,
  aiTap,
  aiScroll,
  aiWaitFor,
  aiHover,
  aiKeyboardPress
}}) => {{
  {test_content}
}});
"""

    async def _run_playwright_test(self, test_file_path: Path, execution_id: str) -> Dict[str, Any]:
        """运行Playwright测试"""
        try:
            record = self.execution_records[execution_id]
            start_time = datetime.now()

            record["logs"].append("开始执行Playwright测试...")
            await self.send_response("🎭 开始执行Playwright测试...")

            # 构建测试命令 - 使用相对路径，在Windows上转换路径分隔符
            relative_test_path = test_file_path.relative_to(self.playwright_workspace)
            # 在Windows上将反斜杠转换为正斜杠，因为npx playwright期望正斜杠
            import platform
            if platform.system() == "Windows":
                relative_path_str = str(relative_test_path).replace('\\', '/')
            else:
                relative_path_str = str(relative_test_path)
            command = ["npx", "playwright", "test", relative_path_str]

            # 检查是否需要添加 --headed 参数
            config = record.get("config", {})
            if config:
                # 处理不同类型的配置对象
                if hasattr(config, 'headed'):
                    headed = config.headed
                elif isinstance(config, dict):
                    headed = config.get('headed', False)
                else:
                    headed = False

                # 如果配置为有头模式，添加 --headed 参数
                if headed:
                    command.append("--headed")
                    record["logs"].append("启用有头模式（显示浏览器界面）")
                    await self.send_response("🖥️ 启用有头模式（显示浏览器界面）")
                    logger.info("添加 --headed 参数到Playwright命令")

            # 设置环境变量
            env = os.environ.copy()
            
            # 确保关键的AI API密钥被传递到子进程
            # 直接从settings中读取API密钥配置，添加异常处理
            ai_key_mappings = {}
            try:
                ai_key_mappings = {
                    'QWEN_VL_API_KEY': getattr(settings, 'QWEN_VL_API_KEY', ''),
                    'QWEN_API_KEY': getattr(settings, 'QWEN_API_KEY', ''),
                    'GLM_API_KEY': getattr(settings, 'GLM_API_KEY', ''),
                    'DEEPSEEK_API_KEY': getattr(settings, 'DEEPSEEK_API_KEY', ''),
                    'OPENAI_API_KEY': getattr(settings, 'OPENAI_API_KEY', ''),
                    'UI_TARS_API_KEY': getattr(settings, 'UI_TARS_API_KEY', ''),
                    'GEMINI_API_KEY': getattr(settings, 'GEMINI_API_KEY', ''),
                }
                logger.info("🔍 成功从settings读取API密钥配置")
            except Exception as e:
                logger.error(f"❌ 从settings读取API密钥配置失败: {e}")
                # 使用从环境变量获取的备用值
                ai_key_mappings = {
                    'QWEN_VL_API_KEY': os.getenv('QWEN_VL_API_KEY', ''),
                    'QWEN_API_KEY': os.getenv('QWEN_API_KEY', ''),
                    'GLM_API_KEY': os.getenv('GLM_API_KEY', ''),
                    'DEEPSEEK_API_KEY': os.getenv('DEEPSEEK_API_KEY', ''),
                    'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY', ''),
                    'UI_TARS_API_KEY': os.getenv('UI_TARS_API_KEY', ''),
                    'GEMINI_API_KEY': os.getenv('GEMINI_API_KEY', ''),
                }
                logger.info("🔄 使用环境变量备用API密钥配置")
            
            # 设置有效的API密钥到环境变量
            logger.info("🔍 开始设置AI API密钥到子进程环境变量...")
            for key, value in ai_key_mappings.items():
                try:
                    if value and value.strip() and not value.startswith('your-'):
                        env[key] = value
                        logger.info(f"🔑 设置AI密钥到子进程: {key} = {value[:10]}...")
                    elif key in os.environ and os.environ[key]:
                        env[key] = os.environ[key]
                        logger.info(f"🔑 从环境变量传递AI密钥到子进程: {key}")
                    else:
                        logger.warning(f"⚠️ API密钥未设置: {key}")
                except Exception as e:
                    logger.error(f"❌ 设置API密钥失败 {key}: {e}")
            
            logger.info(f"🔍 API密钥设置完成，共设置 {len([k for k, v in env.items() if k.endswith('_API_KEY')])} 个密钥")
            
            if config:
                # 处理不同类型的配置对象中的环境变量
                env_vars = None
                if hasattr(config, 'environment_variables'):
                    env_vars = config.environment_variables
                elif isinstance(config, dict):
                    env_vars = config.get('environment_variables')

                if env_vars:
                    env.update(env_vars)
                    logger.info(f"添加配置中的环境变量: {list(env_vars.keys())}")

            logger.info(f"执行命令: {' '.join(command)}")
            logger.info(f"工作目录: {self.playwright_workspace}")

            # 详细的环境变量调试日志
            logger.info("🔍 Playwright执行环境调试 - 环境变量检查:")
            env_keys_to_check = ['QWEN_VL_API_KEY', 'QWEN_API_KEY', 'GLM_API_KEY', 'DEEPSEEK_API_KEY', 'OPENAI_API_KEY']
            for key in env_keys_to_check:
                value = env.get(key)
                if value:
                    logger.info(f"  {key}: ✅ 存在 ({value[:10]}...)")
                else:
                    logger.info(f"  {key}: ❌ 未设置")
            
            logger.info(f"🔍 Playwright执行调试 - 环境变量总数: {len(env)}")

            # 使用增强执行器进行实时流式执行
            try:
                result = await self.enhancer.execute_with_enhanced_logging(command, execution_id, env)
                return_code = result["return_code"]
                stdout_lines = result["stdout"].splitlines() if result["stdout"] else []
                stderr_lines = result["stderr"].splitlines() if result["stderr"] else []
                
            except Exception as e:
                logger.error(f"增强执行器执行失败，回退到原方法: {e}")
                # 回退到原有的执行方式
                import platform
                if platform.system() == "Windows":
                    try:
                        command_str = ' '.join(command)
                        logger.info(f"Windows执行命令: {command_str}")

                        env_with_utf8 = env.copy()
                        env_with_utf8['PYTHONIOENCODING'] = 'utf-8'
                        env_with_utf8['CHCP'] = '65001'

                        # 在线程中执行以避免阻塞
                        result = await asyncio.to_thread(
                            subprocess.run,
                            command_str,
                            cwd=self.playwright_workspace,
                            capture_output=True,
                            text=True,
                            env=env_with_utf8,
                            timeout=300,
                            shell=True,
                            encoding='utf-8',
                            errors='replace'
                        )

                        return_code = result.returncode
                        stdout_lines = result.stdout.splitlines() if result.stdout else []
                        stderr_lines = result.stderr.splitlines() if result.stderr else []

                        for line in stdout_lines:
                            if line.strip():
                                record["logs"].append(f"[STDOUT] {line}")
                                await self.send_response(f"📝 {line}")
                                logger.info(f"[Playwright] {line}")

                        for line in stderr_lines:
                            if line.strip():
                                record["logs"].append(f"[STDERR] {line}")
                                await self.send_response(f"⚠️ {line}")
                                logger.warning(f"[Playwright Error] {line}")

                    except subprocess.TimeoutExpired:
                        logger.error("Playwright测试执行超时")
                        raise Exception("测试执行超时（5分钟）")
                    except UnicodeDecodeError as e:
                        logger.warning(f"编码错误，尝试使用字节模式: {str(e)}")
                        try:
                            result = await asyncio.to_thread(
                                subprocess.run,
                                command_str,
                                cwd=self.playwright_workspace,
                                capture_output=True,
                                text=False,
                                env=env_with_utf8,
                                timeout=300,
                                shell=True
                            )

                            return_code = result.returncode

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

                        except Exception as inner_e:
                            logger.error(f"字节模式执行也失败: {str(inner_e)}")
                            raise Exception(f"执行失败: {str(inner_e)}")

                    except Exception as e:
                        logger.error(f"Playwright测试执行出错：{str(e)}")
                        raise

            else:
                # 非Windows系统使用异步subprocess
                process = await asyncio.create_subprocess_exec(
                    *command,
                    cwd=self.playwright_workspace,
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
                            await self.send_response(f"📝 {line_text}")
                            logger.info(f"[Playwright] {line_text}")

                async def read_stderr():
                    async for line in process.stderr:
                        line_text = line.decode('utf-8').strip()
                        if line_text:
                            stderr_lines.append(line_text)
                            record["logs"].append(f"[STDERR] {line_text}")
                            await self.send_response(f"⚠️ {line_text}")
                            logger.warning(f"[Playwright Error] {line_text}")

                # 并发读取输出
                await asyncio.gather(read_stdout(), read_stderr())

                # 等待进程完成
                return_code = await process.wait()
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            return {
                "return_code": return_code,
                "stdout": stdout_lines,
                "stderr": stderr_lines,
                "duration": duration,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat()
            }

        except Exception as e:
            logger.error(f"运行Playwright测试失败: {str(e)}")
            raise

    def _extract_report_path(self, stdout_lines: List[str]) -> Optional[str]:
        """从stdout中提取报告文件路径"""
        try:
            for line in stdout_lines:
                # 查找 "Midscene - report file updated: ./current_cwd/midscene_run/report/some_id.html"
                if "Midscene - report file updated:" in line:
                    # 使用正则表达式提取路径
                    match = re.search(r'Midscene - report file updated:\s*(.+\.html)', line)
                    if match:
                        report_path = match.group(1).strip()
                        # 如果是相对路径，转换为绝对路径
                        if not os.path.isabs(report_path):
                            if report_path.startswith('./'):
                                report_path = report_path[2:]  # 移除 './'
                            report_path = self.playwright_workspace / report_path

                        logger.info(f"提取到报告路径: {report_path}")
                        return str(report_path)

            return None

        except Exception as e:
            logger.error(f"提取报告路径失败: {str(e)}")
            return None

    def _parse_playwright_result(self, execution_result: Dict[str, Any]) -> Dict[str, Any]:
        """解析Playwright执行结果"""
        try:
            # 基础结果信息
            parsed_result = {
                "status": execution_result.get("status", "failed"),
                "end_time": execution_result.get("end_time", datetime.now().isoformat()),
                "duration": execution_result.get("duration", 0.0),
                "return_code": execution_result.get("return_code", 1),
                "error_message": execution_result.get("error_message"),
                "stdout": execution_result.get("stdout", ""),
                "stderr": execution_result.get("stderr", "")
            }

            # 提取报告路径
            report_path = execution_result.get("report_path")
            if not report_path and execution_result.get("stdout"):
                stdout_data = execution_result["stdout"]
                # 确保传入的是列表格式
                if isinstance(stdout_data, str):
                    stdout_data = stdout_data.split('\n')
                elif not isinstance(stdout_data, list):
                    stdout_data = [str(stdout_data)]
                report_path = self._extract_report_path(stdout_data)

            if report_path:
                parsed_result["report_path"] = report_path
                logger.info(f"找到测试报告: {report_path}")
            else:
                logger.warning("未找到测试报告文件")

            # 解析测试统计信息
            stdout = execution_result.get("stdout", "")
            # 如果stdout是列表，转换为字符串
            if isinstance(stdout, list):
                stdout = "\n".join(str(line) for line in stdout)
            elif not isinstance(stdout, str):
                stdout = str(stdout)

            test_stats = self._extract_test_statistics(stdout)
            parsed_result.update(test_stats)

            return parsed_result

        except Exception as e:
            logger.error(f"解析Playwright结果失败: {str(e)}")
            return {
                "status": "error",
                "end_time": datetime.now().isoformat(),
                "duration": 0.0,
                "return_code": 1,
                "error_message": str(e)
            }

    def _extract_test_statistics(self, stdout: str) -> Dict[str, Any]:
        """从stdout中提取测试统计信息"""
        stats = {
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "skipped_tests": 0
        }

        try:
            # 查找测试结果统计
            # 例如: "1 failed", "2 passed", "Running 1 test using 1 worker"
            import re

            # 提取运行的测试数量
            running_match = re.search(r'Running (\d+) test', stdout)
            if running_match:
                stats["total_tests"] = int(running_match.group(1))

            # 提取失败的测试数量
            failed_match = re.search(r'(\d+) failed', stdout)
            if failed_match:
                stats["failed_tests"] = int(failed_match.group(1))

            # 提取通过的测试数量
            passed_match = re.search(r'(\d+) passed', stdout)
            if passed_match:
                stats["passed_tests"] = int(passed_match.group(1))

            # 如果没有明确的通过数量，计算通过数量
            if stats["passed_tests"] == 0 and stats["total_tests"] > 0:
                stats["passed_tests"] = stats["total_tests"] - stats["failed_tests"] - stats["skipped_tests"]

        except Exception as e:
            logger.warning(f"提取测试统计信息失败: {str(e)}")

        return stats

    async def _open_report_in_browser(self, report_path: str) -> None:
        """在浏览器中打开报告"""
        try:
            if os.path.exists(report_path):
                # 转换为file:// URL
                file_url = f"file:///{report_path.replace(os.sep, '/')}"
                webbrowser.open(file_url)
                await self.send_response(f"📊 已在浏览器中打开测试报告: {report_path}")
                logger.info(f"已在浏览器中打开报告: {file_url}")
            else:
                await self.send_warning(f"报告文件不存在: {report_path}")

        except Exception as e:
            logger.error(f"打开报告失败: {str(e)}")
            await self.send_warning(f"无法打开报告: {str(e)}")

    async def _collect_playwright_reports(self) -> List[str]:
        """收集Playwright报告文件"""
        try:
            reports = []

            # 查找HTML报告
            report_dirs = [
                self.playwright_workspace / "playwright-report",
                self.playwright_workspace / "test-results",
                self.playwright_workspace / "midscene_run" / "report"
            ]

            for report_dir in report_dirs:
                if report_dir.exists():
                    for file_path in report_dir.rglob("*.html"):
                        reports.append(str(file_path))
                    for file_path in report_dir.rglob("*.json"):
                        reports.append(str(file_path))

            return reports

        except Exception as e:
            logger.error(f"收集Playwright报告失败: {str(e)}")
            return []

    async def _collect_test_artifacts(self) -> Dict[str, List[str]]:
        """收集测试产物（截图、视频等）"""
        try:
            artifacts = {
                "screenshots": [],
                "videos": []
            }

            # 查找测试结果目录
            test_results_dir = self.playwright_workspace / "test-results"
            if test_results_dir.exists():
                # 收集截图
                for file_path in test_results_dir.rglob("*.png"):
                    artifacts["screenshots"].append(str(file_path))

                # 收集视频
                for file_path in test_results_dir.rglob("*.webm"):
                    artifacts["videos"].append(str(file_path))

            return artifacts

        except Exception as e:
            logger.error(f"收集测试产物失败: {str(e)}")
            return {"screenshots": [], "videos": []}

    async def _parse_test_results(self, stdout_lines: List[str]) -> Dict[str, Any]:
        """解析测试结果"""
        try:
            results = {
                "total_tests": 0,
                "passed_tests": 0,
                "failed_tests": 0,
                "skipped_tests": 0,
                "success_rate": 0.0,
                "test_details": []
            }

            # 解析Playwright输出
            for line in stdout_lines:
                # 解析测试总数
                if "Running" in line and "test" in line:
                    import re
                    match = re.search(r'(\d+)\s+test', line)
                    if match:
                        results["total_tests"] = int(match.group(1))

                # 解析通过的测试
                if "passed" in line.lower():
                    import re
                    match = re.search(r'(\d+)\s+passed', line)
                    if match:
                        results["passed_tests"] = int(match.group(1))

                # 解析失败的测试
                if "failed" in line.lower():
                    import re
                    match = re.search(r'(\d+)\s+failed', line)
                    if match:
                        results["failed_tests"] = int(match.group(1))

                # 解析跳过的测试
                if "skipped" in line.lower():
                    import re
                    match = re.search(r'(\d+)\s+skipped', line)
                    if match:
                        results["skipped_tests"] = int(match.group(1))

            # 计算成功率
            if results["total_tests"] > 0:
                results["success_rate"] = results["passed_tests"] / results["total_tests"]

            return results

        except Exception as e:
            logger.error(f"解析测试结果失败: {str(e)}")
            return {
                "total_tests": 0,
                "passed_tests": 0,
                "failed_tests": 0,
                "skipped_tests": 0,
                "success_rate": 0.0,
                "test_details": []
            }

    async def _cleanup_test_file(self, test_file_path: Path):
        """清理测试文件"""
        try:
            if test_file_path.exists():
                test_file_path.unlink()
                logger.info(f"清理测试文件: {test_file_path}")
        except Exception as e:
            logger.warning(f"清理测试文件失败: {str(e)}")

    async def _find_default_report_path(self, execution_id: str) -> Optional[str]:
        """查找默认位置的报告文件"""
        try:
            # 可能的报告路径
            possible_paths = [
                self.playwright_workspace / "midscene_run" / "report" / f"{execution_id}.html",
                self.playwright_workspace / "midscene_run" / "report" / "index.html",
                self.playwright_workspace / "playwright-report" / "index.html",
                self.playwright_workspace / "test-results" / "index.html",
            ]

            for path in possible_paths:
                if path.exists():
                    logger.info(f"在默认位置找到报告文件: {path}")
                    return str(path)

            # 如果没有找到，尝试搜索最新的HTML文件
            report_dirs = [
                self.playwright_workspace / "midscene_run" / "report",
                self.playwright_workspace / "playwright-report",
                self.playwright_workspace / "test-results",
            ]

            for report_dir in report_dirs:
                if report_dir.exists():
                    html_files = list(report_dir.glob("*.html"))
                    if html_files:
                        # 按修改时间排序，取最新的
                        latest_file = max(html_files, key=lambda f: f.stat().st_mtime)
                        logger.info(f"找到最新的报告文件: {latest_file}")
                        return str(latest_file)

            logger.warning(f"未找到执行 {execution_id} 的报告文件")
            return None

        except Exception as e:
            logger.error(f"查找默认报告路径失败: {str(e)}")
            return None

    def _get_report_extraction_util(self) -> str:
        """获取报告路径提取的Python代码示例"""
        return '''
# 报告路径提取示例代码
import re
import os
from pathlib import Path

def extract_report_path_from_output(stdout_lines):
    """从Playwright输出中提取报告路径"""
    for line in stdout_lines:
        if "Midscene - report file updated:" in line:
            match = re.search(r'Midscene - report file updated:\\s*(.+\\.html)', line)
            if match:
                report_path = match.group(1).strip()
                if not os.path.isabs(report_path):
                    if report_path.startswith('./'):
                        report_path = report_path[2:]
                    # 转换为绝对路径
                    workspace = Path(r"C:\\Users\\86134\\Desktop\\workspace\\playwright-workspace")
                    report_path = workspace / report_path
                return str(report_path)
    return None

# 使用示例
# report_path = extract_report_path_from_output(stdout_lines)
# if report_path:
#     import webbrowser
#     webbrowser.open(f"file:///{report_path.replace(os.sep, '/')}")
'''

    async def process_message(self, message: Any, ctx: MessageContext) -> None:
        """处理消息的统一入口"""
        if isinstance(message, PlaywrightExecutionRequest):
            await self.handle_execution_request(message, ctx)
        else:
            logger.warning(f"Playwright执行智能体收到未知消息类型: {type(message)}")

    def get_execution_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """获取执行状态"""
        return self.execution_records.get(execution_id)

    def list_executions(self) -> List[Dict[str, Any]]:
        """列出所有执行记录"""
        return list(self.execution_records.values())

    async def get_latest_report_path(self) -> Optional[str]:
        """获取最新的测试报告路径"""
        try:
            report_dir = self.playwright_workspace / "midscene_run" / "report"
            if not report_dir.exists():
                return None

            # 查找最新的HTML报告文件
            html_files = list(report_dir.glob("*.html"))
            if not html_files:
                return None

            # 按修改时间排序，获取最新的
            latest_file = max(html_files, key=lambda f: f.stat().st_mtime)
            return str(latest_file)

        except Exception as e:
            logger.error(f"获取最新报告路径失败: {str(e)}")
            return None

    async def open_latest_report(self) -> bool:
        """打开最新的测试报告"""
        try:
            report_path = await self.get_latest_report_path()
            if report_path:
                await self._open_report_in_browser(report_path)
                return True
            else:
                await self.send_warning("未找到测试报告文件")
                return False

        except Exception as e:
            logger.error(f"打开最新报告失败: {str(e)}")
            await self.send_error(f"打开报告失败: {str(e)}")
            return False

    def get_workspace_info(self) -> Dict[str, Any]:
        """获取工作空间信息"""
        try:
            workspace_info = {
                "workspace_path": str(self.playwright_workspace),
                "workspace_exists": self.playwright_workspace.exists(),
                "e2e_dir_exists": (self.playwright_workspace / "e2e").exists(),
                "package_json_exists": (self.playwright_workspace / "package.json").exists(),
                "recent_test_files": [],
                "recent_reports": []
            }

            # 获取最近的测试文件
            e2e_dir = self.playwright_workspace / "e2e"
            if e2e_dir.exists():
                test_files = list(e2e_dir.glob("*.spec.ts"))
                workspace_info["recent_test_files"] = [str(f) for f in test_files[-5:]]

            # 获取最近的报告
            report_dir = self.playwright_workspace / "midscene_run" / "report"
            if report_dir.exists():
                report_files = list(report_dir.glob("*.html"))
                workspace_info["recent_reports"] = [str(f) for f in report_files[-5:]]

            return workspace_info

        except Exception as e:
            logger.error(f"获取工作空间信息失败: {str(e)}")
            return {"error": str(e)}

    async def _save_execution_record_to_database(
        self,
        execution_id: str,
        message: PlaywrightExecutionRequest,
        execution_result: Dict[str, Any]
    ) -> None:
        """保存执行记录到数据库"""
        try:
            from app.database.connection import db_manager
            from app.database.models.executions import ScriptExecution
            from app.database.models.scripts import TestScript

            record = self.execution_records.get(execution_id, {})

            # 提取脚本信息
            script_id = getattr(message, 'script_id', None) or message.script_name or execution_id

            # 解析时间信息
            start_time = None
            end_time = None
            if record.get("start_time"):
                try:
                    start_time = datetime.fromisoformat(record["start_time"])
                except:
                    pass
            if execution_result.get("end_time"):
                try:
                    end_time = datetime.fromisoformat(execution_result["end_time"])
                except:
                    pass

            # 计算执行时长（秒）
            duration_seconds = None
            if start_time and end_time:
                duration_seconds = int((end_time - start_time).total_seconds())
            elif execution_result.get("duration"):
                duration_seconds = int(execution_result["duration"])

            # 确定执行状态 - 与TestReport保持一致的逻辑
            return_code = execution_result.get("return_code", 1)
            explicit_status = execution_result.get("status", "")

            logger.info(f"状态映射调试 - return_code: {return_code}, explicit_status: '{explicit_status}'")

            if return_code == 0:
                status = "completed"  # 成功执行
            else:
                status = "failed"     # 执行失败

            # 如果有明确的status字段，也考虑进去
            if explicit_status == "success":
                status = "completed"
            elif explicit_status in ["pending", "running", "cancelled"]:
                status = explicit_status

            logger.info(f"最终状态映射结果: {status}")

            # 安全序列化配置信息
            safe_execution_config = {}
            safe_environment_info = {}

            try:
                if record.get("config"):
                    config = record["config"]
                    # 如果是Pydantic模型，转换为字典
                    if hasattr(config, 'model_dump'):
                        safe_execution_config = config.model_dump()
                    elif hasattr(config, 'dict'):
                        safe_execution_config = config.dict()
                    elif isinstance(config, dict):
                        safe_execution_config = config
                    else:
                        safe_execution_config = {}

                # 添加脚本信息到配置中
                safe_execution_config["script_name"] = record.get("script_name", message.script_name)
                safe_execution_config["script_type"] = "playwright"  # 明确设置脚本类型

            except Exception as e:
                logger.warning(f"序列化执行配置失败: {str(e)}")

            try:
                if execution_result.get("environment"):
                    env = execution_result["environment"]
                    # 如果是Pydantic模型，转换为字典
                    if hasattr(env, 'model_dump'):
                        safe_environment_info = env.model_dump()
                    elif hasattr(env, 'dict'):
                        safe_environment_info = env.dict()
                    elif isinstance(env, dict):
                        safe_environment_info = env
                    else:
                        safe_environment_info = {}
            except Exception as e:
                logger.warning(f"序列化环境信息失败: {str(e)}")

            # 创建执行记录
            db_execution = ScriptExecution(
                script_id=script_id,
                execution_id=execution_id,
                status=status,
                execution_config=safe_execution_config,
                environment_info=safe_environment_info,
                start_time=start_time,
                end_time=end_time,
                duration_seconds=duration_seconds,
                error_message=execution_result.get("error_message") or record.get("error_message"),
                exit_code=execution_result.get("return_code", 0),
                performance_metrics={}
            )

            # 保存到MySQL数据库
            async with db_manager.get_session() as session:
                session.add(db_execution)
                await session.commit()
                await session.refresh(db_execution)
                logger.info(f"执行记录已保存到MySQL: {db_execution.id} - {script_id}")

        except Exception as e:
            logger.error(f"保存执行记录失败: {str(e)}")

    async def _save_test_report_to_database(self, execution_id: str, message: PlaywrightExecutionRequest, execution_result: Dict[str, Any]) -> None:
        """保存测试报告到数据库"""
        try:
            record = self.execution_records.get(execution_id, {})

            # 提取脚本信息
            script_id = getattr(message, 'script_id', None) or message.script_name or execution_id
            script_name = message.script_name or f"test-{execution_id}"
            session_id = getattr(message, 'session_id', execution_id)

            # 解析时间信息
            start_time = None
            end_time = None
            if record.get("start_time"):
                try:
                    start_time = datetime.fromisoformat(record["start_time"])
                except:
                    pass
            if execution_result.get("end_time"):
                try:
                    end_time = datetime.fromisoformat(execution_result["end_time"])
                except:
                    pass

            # 确定执行状态
            status = execution_result.get("status", "unknown")
            if execution_result.get("return_code") == 0:
                status = "passed"
            elif execution_result.get("return_code") != 0:
                status = "failed"

            # 提取报告路径和生成访问URL
            report_path = execution_result.get("report_path")
            report_url = None
            if report_path:
                # 生成报告访问URL
                report_url = f"/api/v1/web/reports/view/{execution_id}"
                logger.info(f"生成报告访问URL: {report_url} -> {report_path}")

            # 安全转换配置对象
            safe_execution_config = record.get("config", {})
            safe_environment_variables = {}

            # 安全提取环境变量
            if message.execution_config and hasattr(message.execution_config, 'environment_variables'):
                env_vars = message.execution_config.environment_variables
                if env_vars:
                    if isinstance(env_vars, dict):
                        safe_environment_variables = env_vars
                    elif hasattr(env_vars, 'dict'):
                        safe_environment_variables = env_vars.dict()
                    elif hasattr(env_vars, 'model_dump'):
                        safe_environment_variables = env_vars.model_dump()
                    else:
                        safe_environment_variables = {"raw_env_vars": str(env_vars)}

            # 保存报告
            saved_report = await test_report_service.save_test_report(
                script_id=script_id,
                script_name=script_name,
                session_id=session_id,
                execution_id=execution_id,
                status=status,
                return_code=execution_result.get("return_code", 0),
                start_time=start_time,
                end_time=end_time,
                duration=execution_result.get("duration", 0.0),
                logs=record.get("logs", []),
                execution_config=safe_execution_config,
                environment_variables=safe_environment_variables,
                # 传递报告路径和URL
                report_path=report_path,
                report_url=report_url
            )

            if saved_report:
                logger.info(f"测试报告已保存到数据库: {saved_report.id}")
                if report_url:
                    await self.send_response(f"📊 测试报告已保存: ID {saved_report.id}, 访问地址: {report_url}")
                else:
                    await self.send_response(f"📊 测试报告已保存: ID {saved_report.id}")
            else:
                logger.warning("保存测试报告到数据库失败")

        except Exception as e:
            logger.error(f"保存测试报告到数据库失败: {str(e)}")
            # 不抛出异常，避免影响主流程
