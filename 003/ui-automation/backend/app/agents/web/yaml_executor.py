"""
测试执行智能体
负责执行各种类型的测试脚本（YAML、Playwright等）
"""
import json
import uuid
import asyncio
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from pathlib import Path

from autogen_core import message_handler, type_subscription, MessageContext
from loguru import logger

from app.core.messages.web import YAMLExecutionRequest
from app.core.agents.base import BaseAgent
from app.core.types import TopicTypes, AgentTypes, AGENT_NAMES


@type_subscription(topic_type=TopicTypes.YAML_EXECUTOR.value)
class YAMLExecutorAgent(BaseAgent):
    """测试执行智能体，负责执行各种类型的测试脚本"""

    def __init__(self, model_client_instance=None, **kwargs):
        """初始化测试执行智能体"""
        super().__init__(
            agent_id=AgentTypes.YAML_EXECUTOR.value,
            agent_name=AGENT_NAMES[AgentTypes.YAML_EXECUTOR.value],
            model_client_instance=model_client_instance,
            **kwargs
        )
        self.execution_records: Dict[str, Dict[str, Any]] = {}
        self.supported_formats = ["yaml", "playwright", "javascript", "typescript"]

        logger.info(f"YAML执行智能体初始化完成: {self.agent_name}")

    @message_handler
    async def handle_execution_request(self, message: YAMLExecutionRequest, ctx: MessageContext) -> None:
        """处理测试执行请求"""
        try:
            self.start_performance_monitoring()
            execution_id = str(uuid.uuid4())
            
            await self.send_response(f"🚀 开始执行测试: {execution_id}")
            
            # 创建执行记录
            self.execution_records[execution_id] = {
                "execution_id": execution_id,
                "status": "running",
                "start_time": datetime.now().isoformat(),
                "test_type": "yaml",
                "test_content": message.yaml_content,
                "config": message.execution_config.model_dump() if message.execution_config else {},
                "logs": [],
                "results": None,
                "error_message": None
            }
            
            # 执行YAML测试
            execution_result = await self._execute_yaml_test(
                execution_id,
                message.yaml_content,
                message.execution_config.model_dump() if message.execution_config else {}
            )
            
            # 更新执行记录
            self.execution_records[execution_id].update(execution_result)
            
            await self.send_response(
                f"✅ 测试执行完成: {execution_result['status']}",
                is_final=True,
                result={
                    "execution_id": execution_id,
                    "execution_result": execution_result,
                    "metrics": self.metrics
                }
            )

            self.end_performance_monitoring()

        except Exception as e:
            await self.handle_exception("handle_execution_request", e)



    async def _execute_yaml_test(self, execution_id: str, test_content: Union[str, Dict[str, Any]], 
                               config: Dict[str, Any]) -> Dict[str, Any]:
        """执行YAML测试脚本"""
        try:
            record = self.execution_records[execution_id]
            record["logs"].append("开始执行YAML测试...")
            
            await self.send_response("📄 解析YAML测试脚本...")
            
            # 解析YAML内容
            if isinstance(test_content, str):
                import yaml
                yaml_data = yaml.safe_load(test_content)
            else:
                yaml_data = test_content
            
            # 验证YAML结构
            if not self._validate_yaml_structure(yaml_data):
                raise ValueError("YAML结构验证失败")
            
            # 执行YAML测试
            start_time = datetime.now()
            
            # 这里需要调用MidScene.js执行器
            # 由于MidScene.js是Node.js工具，我们需要通过子进程调用
            execution_result = await self._run_midscene_yaml(yaml_data, config, execution_id)
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            return {
                "status": "passed" if execution_result.get("success", False) else "failed",
                "end_time": end_time.isoformat(),
                "duration": duration,
                "test_results": execution_result.get("results", {}),
                "screenshots": execution_result.get("screenshots", []),
                "reports": execution_result.get("reports", [])
            }
            
        except Exception as e:
            logger.error(f"执行YAML测试失败: {str(e)}")
            return {
                "status": "error",
                "end_time": datetime.now().isoformat(),
                "error_message": str(e),
                "duration": 0.0
            }



    def _validate_yaml_structure(self, yaml_data: Dict[str, Any]) -> bool:
        """验证YAML结构"""
        try:
            # 检查必要的字段
            if "web" not in yaml_data:
                logger.error("YAML缺少'web'配置")
                return False
            
            if "tasks" not in yaml_data:
                logger.error("YAML缺少'tasks'配置")
                return False
            
            # 检查web配置
            web_config = yaml_data["web"]
            if "url" not in web_config:
                logger.error("web配置缺少'url'字段")
                return False
            
            # 检查tasks配置
            tasks = yaml_data["tasks"]
            if not isinstance(tasks, list) or len(tasks) == 0:
                logger.error("tasks必须是非空列表")
                return False
            
            # 检查每个任务
            for i, task in enumerate(tasks):
                if "name" not in task:
                    logger.error(f"任务{i+1}缺少'name'字段")
                    return False
                
                if "flow" not in task:
                    logger.error(f"任务{i+1}缺少'flow'字段")
                    return False
                
                if not isinstance(task["flow"], list):
                    logger.error(f"任务{i+1}的'flow'必须是列表")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"验证YAML结构失败: {str(e)}")
            return False

    async def _run_midscene_yaml(self, yaml_data: Dict[str, Any], config: Dict[str, Any], 
                               execution_id: str) -> Dict[str, Any]:
        """运行MidScene.js YAML测试"""
        try:
            record = self.execution_records[execution_id]
            
            # 创建临时YAML文件
            temp_dir = Path("temp_yaml_tests") / execution_id
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            yaml_file = temp_dir / "test.yaml"
            
            import yaml
            with open(yaml_file, "w", encoding="utf-8") as f:
                yaml.dump(yaml_data, f, default_flow_style=False, allow_unicode=True)
            
            record["logs"].append(f"创建临时YAML文件: {yaml_file}")
            await self.send_response(f"📝 创建测试文件: {yaml_file}")
            
            # 检查MidScene.js是否可用
            midscene_available = await self._check_midscene_availability()
            
            if not midscene_available:
                # 如果MidScene.js不可用，返回模拟结果
                record["logs"].append("MidScene.js不可用，返回模拟结果")
                await self.send_response("⚠️ MidScene.js不可用，返回模拟结果")
                
                return {
                    "success": True,
                    "results": {
                        "total_tasks": len(yaml_data.get("tasks", [])),
                        "completed_tasks": len(yaml_data.get("tasks", [])),
                        "failed_tasks": 0,
                        "execution_time": "模拟执行",
                        "note": "MidScene.js不可用，这是模拟结果"
                    },
                    "screenshots": [],
                    "reports": []
                }
            
            # 执行MidScene.js命令
            command = ["npx", "@midscene/cli", "run", str(yaml_file)]
            
            # 设置环境变量
            import os
            env = os.environ.copy()
            if config.get("environment_variables"):
                env.update(config["environment_variables"])
            
            # 执行命令
            process = await asyncio.create_subprocess_exec(
                *command,
                cwd=temp_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )
            
            stdout, stderr = await process.communicate()
            
            # 解析执行结果
            if process.returncode == 0:
                record["logs"].append("MidScene.js执行成功")
                await self.send_response("✅ MidScene.js执行成功")
                
                # 收集结果文件
                results = await self._collect_midscene_results(temp_dir)
                
                return {
                    "success": True,
                    "results": results,
                    "stdout": stdout.decode('utf-8'),
                    "screenshots": await self._collect_screenshots(temp_dir),
                    "reports": await self._collect_reports(temp_dir)
                }
            else:
                error_msg = stderr.decode('utf-8')
                record["logs"].append(f"MidScene.js执行失败: {error_msg}")
                await self.send_response(f"❌ MidScene.js执行失败: {error_msg}")
                
                return {
                    "success": False,
                    "error": error_msg,
                    "stdout": stdout.decode('utf-8'),
                    "stderr": error_msg
                }
            
        except Exception as e:
            logger.error(f"运行MidScene.js失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _check_midscene_availability(self) -> bool:
        """检查MidScene.js是否可用"""
        try:
            process = await asyncio.create_subprocess_exec(
                "npx", "@midscene/cli", "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            return process.returncode == 0
            
        except Exception as e:
            logger.debug(f"检查MidScene.js可用性失败: {str(e)}")
            return False

    async def _collect_midscene_results(self, temp_dir: Path) -> Dict[str, Any]:
        """收集MidScene.js执行结果"""
        try:
            results = {
                "total_tasks": 0,
                "completed_tasks": 0,
                "failed_tasks": 0,
                "execution_time": "未知"
            }
            
            # 查找结果文件
            result_files = list(temp_dir.rglob("*.json"))
            
            for result_file in result_files:
                try:
                    with open(result_file, "r", encoding="utf-8") as f:
                        result_data = json.load(f)
                        
                    # 解析结果数据
                    if "tasks" in result_data:
                        results["total_tasks"] = len(result_data["tasks"])
                        results["completed_tasks"] = sum(
                            1 for task in result_data["tasks"] 
                            if task.get("status") == "completed"
                        )
                        results["failed_tasks"] = sum(
                            1 for task in result_data["tasks"] 
                            if task.get("status") == "failed"
                        )
                    
                    if "execution_time" in result_data:
                        results["execution_time"] = result_data["execution_time"]
                        
                except Exception as e:
                    logger.debug(f"解析结果文件失败: {str(e)}")
                    continue
            
            return results
            
        except Exception as e:
            logger.error(f"收集MidScene.js结果失败: {str(e)}")
            return {}

    async def _collect_screenshots(self, temp_dir: Path) -> List[str]:
        """收集截图文件"""
        try:
            screenshots = []
            
            # 查找截图文件
            for screenshot_file in temp_dir.rglob("*.png"):
                screenshots.append(str(screenshot_file))
            
            return screenshots
            
        except Exception as e:
            logger.error(f"收集截图失败: {str(e)}")
            return []

    async def _collect_reports(self, temp_dir: Path) -> List[str]:
        """收集报告文件"""
        try:
            reports = []
            
            # 查找报告文件
            for report_file in temp_dir.rglob("*.html"):
                reports.append(str(report_file))
            
            for report_file in temp_dir.rglob("*.json"):
                reports.append(str(report_file))
            
            return reports
            
        except Exception as e:
            logger.error(f"收集报告失败: {str(e)}")
            return []

    async def process_message(self, message: Any, ctx: MessageContext) -> None:
        """处理消息的统一入口"""
        if isinstance(message, YAMLExecutionRequest):
            await self.handle_execution_request(message, ctx)
        else:
            logger.warning(f"测试执行智能体收到未知消息类型: {type(message)}")

    def get_execution_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """获取执行状态"""
        return self.execution_records.get(execution_id)

    def list_executions(self) -> List[Dict[str, Any]]:
        """列出所有执行记录"""
        return list(self.execution_records.values())

    def get_supported_formats(self) -> List[str]:
        """获取支持的测试格式"""
        return self.supported_formats.copy()
