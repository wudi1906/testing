"""
测试脚本生成智能体
基于公共基类实现，使用大模型生成高质量的pytest测试脚本
"""
import os
import uuid
import json
from typing import Dict, List, Any
from datetime import datetime
from pathlib import Path

from autogen_core import message_handler, type_subscription, MessageContext
from loguru import logger

from app.agents.api_automation.base_api_agent import BaseApiAutomationAgent
from app.core.types import AgentTypes, TopicTypes
from app.core.messages.api_automation import (
    TestScriptGenerationRequest, TestScriptGenerationResponse,
    TestCaseInfo, TestScriptInfo, ApiEndpointInfo
)
from app.core.enums import TestType, Priority, TestLevel, HttpMethod


@type_subscription(topic_type=TopicTypes.TEST_SCRIPT_GENERATOR.value)
class TestScriptGeneratorAgent(BaseApiAutomationAgent):
    """
    测试脚本生成智能体

    核心功能：
    1. 使用大模型基于API分析结果生成高质量pytest测试脚本
    2. 智能生成测试用例和测试数据
    3. 生成完整的测试配置文件
    4. 支持多种测试类型和测试策略
    5. 支持流式生成和实时反馈
    """

    def __init__(self, model_client_instance=None, agent_config=None, **kwargs):
        """初始化测试脚本生成智能体"""
        super().__init__(
            agent_type=AgentTypes.TEST_SCRIPT_GENERATOR,
            model_client_instance=model_client_instance,
            **kwargs
        )

        # 存储智能体配置信息
        self.agent_config = agent_config or {}

        # 初始化AssistantAgent
        self._initialize_assistant_agent()

        # 生成统计（继承公共统计）
        self.generation_metrics = {
            "total_requests": 0,
            "successful_generations": 0,
            "failed_generations": 0,
            "total_test_files_generated": 0,
            "total_test_cases_generated": 0
        }

        # 输出目录
        self.output_dir = Path("./generated_tests")
        self.output_dir.mkdir(exist_ok=True)

        logger.info(f"测试脚本生成智能体初始化完成: {self.agent_name}")

    @message_handler
    async def handle_test_script_generation_request(
        self, 
        message: TestScriptGenerationRequest, 
        ctx: MessageContext
    ) -> None:
        """处理测试脚本生成请求"""
        start_time = datetime.now()
        self.generation_metrics["total_requests"] += 1
        
        try:
            logger.info(f"开始生成测试脚本: {message.doc_id}")
            
            # 使用大模型智能生成测试脚本
            generation_result = await self._intelligent_generate_test_scripts(
                message.endpoints,
                message.dependencies,
                message.session_id
            )

            # 提取测试用例和脚本
            test_cases = self._extract_test_cases_from_generation(generation_result)
            test_scripts = await self._save_and_create_test_scripts(generation_result, message.session_id)
            
            # 构建响应
            response = TestScriptGenerationResponse(
                session_id=message.session_id,
                doc_id=message.doc_id,
                test_cases=test_cases,
                test_scripts=test_scripts,
                generation_summary={
                    "total_test_files": len(test_scripts),
                    "total_test_cases": len(test_cases),
                    "generation_time": (datetime.now() - start_time).total_seconds()
                },
                processing_time=(datetime.now() - start_time).total_seconds()
            )
            
            # 更新统计
            self.generation_metrics["successful_generations"] += 1
            self.generation_metrics["total_test_files_generated"] += len(test_scripts)
            self.generation_metrics["total_test_cases_generated"] += len(test_cases)
            
            logger.info(f"测试脚本生成完成: {message.doc_id}, 生成了 {len(test_scripts)} 个测试文件")
            
            # 发送到测试执行智能体
            await self._send_to_test_executor(response)
            
        except Exception as e:
            self.generation_metrics["failed_generations"] += 1
            logger.error(f"测试脚本生成失败: {str(e)}")
            
            # 发送错误响应
            await self._send_error_response(message, str(e))

    async def _intelligent_generate_test_scripts(
        self,
        endpoints,
        dependencies,
        session_id: str
    ) -> Dict[str, Any]:
        """使用大模型智能生成测试脚本"""
        try:
            # 准备端点数据
            endpoints_data = []
            for endpoint in endpoints:
                endpoint_data = {
                    "path": endpoint.path,
                    "method": endpoint.method.value,
                    "summary": endpoint.summary,
                    "description": endpoint.description,
                    "parameters": endpoint.parameters,
                    "request_body": endpoint.request_body,
                    "responses": endpoint.responses,
                    "tags": endpoint.tags,
                    "auth_required": endpoint.auth_required
                }
                endpoints_data.append(endpoint_data)

            # 准备依赖数据
            dependencies_data = []
            for dependency in dependencies:
                dep_data = {
                    "source": dependency.source_test,
                    "target": dependency.target_test,
                    "type": dependency.dependency_type.value,
                    "required": dependency.is_required,
                    "description": dependency.description
                }
                dependencies_data.append(dep_data)

            # 构建生成任务
            task = f"""请基于以下API分析结果生成完整的pytest测试脚本：

## API端点信息
{json.dumps(endpoints_data, ensure_ascii=False, indent=2)}

## 依赖关系
{json.dumps(dependencies_data, ensure_ascii=False, indent=2)}

## 生成要求
请生成以下内容：

1. **完整的pytest测试文件**
   - 包含所有API端点的测试用例
   - 覆盖正常、异常、边界值场景
   - 使用allure装饰器增强报告
   - 实现参数化和数据驱动测试

2. **测试配置文件**
   - conftest.py（pytest配置和fixture）
   - pytest.ini（pytest设置）
   - requirements.txt（依赖包）

3. **测试数据文件**
   - 有效测试数据
   - 无效测试数据
   - 边界值数据

4. **辅助工具**
   - API客户端封装
   - 通用断言函数
   - 测试工具类

请确保生成的代码：
- 可以直接执行
- 遵循最佳实践
- 包含详细注释
- 具有良好的可维护性

严格按照系统提示中的JSON格式输出结果。"""

            # 使用AssistantAgent进行智能生成
            result_content = await self._run_assistant_agent(task)

            # 解析大模型返回的结果
            if result_content:
                generation_result = self._extract_json_from_content(result_content)
                if generation_result:
                    return generation_result

            # 如果大模型生成失败，使用备用方法
            logger.warning("大模型生成失败，使用备用生成方法")
            return await self._fallback_generate_test_scripts(endpoints, dependencies)

        except Exception as e:
            logger.error(f"智能生成测试脚本失败: {str(e)}")
            return await self._fallback_generate_test_scripts(endpoints, dependencies)

    def _extract_test_cases_from_generation(self, generation_result: Dict[str, Any]) -> List[TestCaseInfo]:
        """从生成结果中提取测试用例"""
        test_cases = []

        try:
            for case_data in generation_result.get("test_cases", []):
                # 创建一个默认的端点信息
                default_endpoint = ApiEndpointInfo(
                    path=case_data.get("path", "/unknown"),
                    method=HttpMethod.GET,
                    summary=case_data.get("name", ""),
                    description=case_data.get("description", "")
                )

                test_case = TestCaseInfo(
                    test_id=str(uuid.uuid4()),
                    name=case_data.get("name", ""),
                    description=case_data.get("description", ""),
                    endpoint=default_endpoint,
                    test_type=TestType.FUNCTIONAL,  # 默认类型
                    test_level=TestLevel.API,
                    priority=Priority.MEDIUM,
                    test_data=case_data.get("test_data", []),
                    assertions=case_data.get("assertions", []),
                    setup_steps=case_data.get("setup_steps", []),
                    teardown_steps=case_data.get("teardown_steps", []),
                    tags=case_data.get("tags", [])
                )
                test_cases.append(test_case)

        except Exception as e:
            logger.error(f"提取测试用例失败: {str(e)}")

        return test_cases

    async def _save_and_create_test_scripts(
        self,
        generation_result: Dict[str, Any],
        session_id: str
    ) -> List[TestScriptInfo]:
        """保存并创建测试脚本信息"""
        test_scripts = []

        try:
            # 创建会话目录
            session_dir = self.output_dir / session_id
            session_dir.mkdir(exist_ok=True)

            # 保存测试文件
            for test_file in generation_result.get("test_files", []):
                file_path = session_dir / test_file["filename"]
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(test_file["content"])

                script_info = TestScriptInfo(
                    script_id=str(uuid.uuid4()),
                    name=test_file["filename"],
                    file_path=str(file_path),
                    content=test_file["content"],
                    description=test_file.get("description", ""),
                    framework="pytest",
                    dependencies=generation_result.get("dependencies", [])
                )
                test_scripts.append(script_info)

            # 保存配置文件
            for config_file in generation_result.get("config_files", []):
                file_path = session_dir / config_file["filename"]
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(config_file["content"])

            logger.info(f"已保存 {len(test_scripts)} 个测试脚本到 {session_dir}")

        except Exception as e:
            logger.error(f"保存测试脚本失败: {str(e)}")

        return test_scripts

    async def _fallback_generate_test_scripts(self, endpoints, dependencies) -> Dict[str, Any]:
        """备用生成方法"""
        try:
            test_files = []
            test_cases = []

            for endpoint in endpoints:
                # 生成基础测试文件内容
                test_content = self._generate_basic_test_file(endpoint)

                test_files.append({
                    "filename": f"test_{endpoint.method.value.lower()}_{self._path_to_name(endpoint.path)}.py",
                    "content": test_content,
                    "description": f"{endpoint.method.value} {endpoint.path} 测试",
                    "test_count": 3
                })

                # 生成基础测试用例
                test_cases.append({
                    "name": f"test_{endpoint.method.value.lower()}_{self._path_to_name(endpoint.path)}_success",
                    "description": f"测试 {endpoint.method.value} {endpoint.path} 成功场景",
                    "type": "functional",
                    "priority": "high",
                    "tags": ["api", "functional"]
                })

            return {
                "test_files": test_files,
                "test_cases": test_cases,
                "config_files": [
                    {
                        "filename": "conftest.py",
                        "content": self._generate_basic_conftest()
                    }
                ],
                "dependencies": ["pytest", "requests", "allure-pytest"],
                "execution_instructions": [
                    "pip install pytest requests allure-pytest",
                    "pytest tests/ -v --alluredir=reports"
                ]
            }

        except Exception as e:
            logger.error(f"备用生成失败: {str(e)}")
            return {
                "test_files": [],
                "test_cases": [],
                "config_files": [],
                "dependencies": [],
                "execution_instructions": []
            }

    def _generate_endpoint_test_cases(self, endpoint) -> List[TestCaseInfo]:
        """为单个端点生成测试用例"""
        test_cases = []
        
        try:
            # 成功场景测试
            success_case = TestCaseInfo(
                test_id=str(uuid.uuid4()),
                name=f"test_{endpoint.method.value.lower()}_{self._path_to_name(endpoint.path)}_success",
                description=f"测试 {endpoint.method.value} {endpoint.path} 成功场景",
                endpoint=endpoint,
                test_type=TestType.FUNCTIONAL,
                test_level=TestLevel.API,
                priority=Priority.HIGH,
                test_data=[{
                    "endpoint": endpoint.path,
                    "method": endpoint.method.value,
                    "expected_status": 200
                }],
                assertions=[{
                    "type": "status_code",
                    "expected": 200,
                    "description": "response.status_code == 200"
                }, {
                    "type": "response_body",
                    "expected": "not_null",
                    "description": "response.json() is not None"
                }],
                setup_steps=[
                    "准备测试数据",
                    "设置请求头"
                ],
                teardown_steps=[
                    "清理测试数据"
                ],
                tags=["api", "functional", endpoint.method.value.lower()]
            )
            test_cases.append(success_case)
            
            # 错误场景测试
            error_case = TestCaseInfo(
                test_id=str(uuid.uuid4()),
                name=f"test_{endpoint.method.value.lower()}_{self._path_to_name(endpoint.path)}_error",
                description=f"测试 {endpoint.method.value} {endpoint.path} 错误场景",
                endpoint=endpoint,
                test_type=TestType.FUNCTIONAL,
                test_level=TestLevel.API,
                priority=Priority.MEDIUM,
                test_data=[{
                    "endpoint": endpoint.path,
                    "method": endpoint.method.value,
                    "expected_status": 400
                }],
                assertions=[{
                    "type": "status_code",
                    "expected": ">=400",
                    "description": "response.status_code >= 400"
                }, {
                    "type": "response_body",
                    "expected": "contains_error",
                    "description": "'error' in response.json()"
                }],
                setup_steps=[
                    "准备无效测试数据"
                ],
                teardown_steps=[],
                tags=["api", "functional", "error", endpoint.method.value.lower()]
            )
            test_cases.append(error_case)
            
        except Exception as e:
            logger.error(f"生成端点测试用例失败: {str(e)}")
        
        return test_cases

    def _generate_integration_test_cases(self, dependencies) -> List[TestCaseInfo]:
        """生成集成测试用例"""
        test_cases = []
        
        try:
            for dependency in dependencies:
                # 创建一个默认的端点信息用于集成测试
                integration_endpoint = ApiEndpointInfo(
                    path=f"/integration/{dependency.source_test}",
                    method=HttpMethod.POST,
                    summary=f"Integration test for {dependency.source_test}",
                    description=f"测试依赖关系: {dependency.source_test} -> {dependency.target_test}"
                )

                integration_case = TestCaseInfo(
                    test_id=str(uuid.uuid4()),
                    name=f"test_integration_{self._dependency_to_name(dependency)}",
                    description=f"测试依赖关系: {dependency.source_test} -> {dependency.target_test}",
                    endpoint=integration_endpoint,
                    test_type=TestType.INTEGRATION,
                    test_level=TestLevel.API,
                    priority=Priority.HIGH,
                    test_data=[{
                        "source_test": dependency.source_test,
                        "target_test": dependency.target_test,
                        "dependency_type": dependency.dependency_type.value
                    }],
                    assertions=[{
                        "type": "status_code",
                        "expected": 200,
                        "description": "source_response.status_code == 200"
                    }, {
                        "type": "status_code",
                        "expected": 200,
                        "description": "target_response.status_code == 200"
                    }, {
                        "type": "custom",
                        "expected": "exists",
                        "description": "dependency_data_exists"
                    }],
                    setup_steps=[
                        "执行前置依赖测试",
                        "提取依赖数据"
                    ],
                    teardown_steps=[
                        "清理依赖数据"
                    ],
                    tags=["api", "integration", "dependency"]
                )
                test_cases.append(integration_case)
                
        except Exception as e:
            logger.error(f"生成集成测试用例失败: {str(e)}")
        
        return test_cases

    async def _generate_test_scripts(self, test_cases: List[TestCaseInfo], session_id: str) -> List[TestScriptInfo]:
        """生成测试脚本文件"""
        test_scripts = []
        
        try:
            # 按测试类型分组
            functional_cases = [tc for tc in test_cases if tc.test_type == TestType.FUNCTIONAL]
            integration_cases = [tc for tc in test_cases if tc.test_type == TestType.INTEGRATION]
            
            # 生成功能测试脚本
            if functional_cases:
                functional_script = await self._create_test_script(
                    "test_functional_api.py",
                    functional_cases,
                    session_id,
                    "功能测试"
                )
                test_scripts.append(functional_script)
            
            # 生成集成测试脚本
            if integration_cases:
                integration_script = await self._create_test_script(
                    "test_integration_api.py",
                    integration_cases,
                    session_id,
                    "集成测试"
                )
                test_scripts.append(integration_script)
            
        except Exception as e:
            logger.error(f"生成测试脚本失败: {str(e)}")
        
        return test_scripts

    async def _create_test_script(
        self, 
        filename: str, 
        test_cases: List[TestCaseInfo], 
        session_id: str,
        description: str
    ) -> TestScriptInfo:
        """创建单个测试脚本文件"""
        try:
            # 生成测试代码
            test_code = self._generate_test_code(test_cases, description)
            
            # 保存文件
            session_dir = self.output_dir / session_id
            session_dir.mkdir(exist_ok=True)
            
            file_path = session_dir / filename
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(test_code)
            
            # 创建脚本信息
            script_info = TestScriptInfo(
                script_id=str(uuid.uuid4()),
                name=filename,
                file_path=str(file_path),
                content=test_code,
                description=description,
                framework="pytest",
                dependencies=["pytest", "requests", "allure-pytest"]
            )
            
            return script_info
            
        except Exception as e:
            logger.error(f"创建测试脚本失败: {str(e)}")
            raise

    def _generate_test_code(self, test_cases: List[TestCaseInfo], description: str) -> str:
        """生成测试代码"""
        code_lines = [
            f'"""',
            f'{description}',
            f'自动生成的API测试脚本',
            f'"""',
            f'import pytest',
            f'import requests',
            f'import allure',
            f'from typing import Dict, Any',
            f'',
            f'',
            f'class TestAPI:',
            f'    """API测试类"""',
            f'    ',
            f'    def setup_method(self):',
            f'        """测试方法初始化"""',
            f'        self.base_url = os.getenv("API_BASE_URL", "http://localhost:8000")',
            f'        self.headers = {{"Content-Type": "application/json"}}',
            f'    ',
        ]
        
        for test_case in test_cases:
            code_lines.extend(self._generate_test_method(test_case))
            code_lines.append('')
        
        return '\n'.join(code_lines)

    def _generate_test_method(self, test_case: TestCaseInfo) -> List[str]:
        """生成单个测试方法"""
        lines = [
            f'    @allure.story("{test_case.description}")',
            f'    @pytest.mark.{test_case.test_type.value}',
            f'    def {test_case.name}(self):',
            f'        """',
            f'        {test_case.description}',
            f'        """',
            f'        # 测试数据',
            f'        test_data = {json.dumps(test_case.test_data, indent=8)}',
            f'        ',
            f'        # 执行请求',
            f'        endpoint = test_data.get("endpoint", "/")',
            f'        method = test_data.get("method", "GET")',
            f'        url = f"{{self.base_url}}{{endpoint}}"',
            f'        ',
            f'        response = requests.request(method, url, headers=self.headers)',
            f'        ',
            f'        # 断言验证',
        ]
        
        for assertion in test_case.assertions:
            lines.append(f'        assert {assertion}')
        
        return lines

    def _path_to_name(self, path: str) -> str:
        """将路径转换为方法名"""
        return path.replace('/', '_').replace('{', '').replace('}', '').strip('_')

    def _dependency_to_name(self, dependency) -> str:
        """将依赖关系转换为方法名"""
        source_name = self._path_to_name(dependency.source_test.split(' ')[-1])
        target_name = self._path_to_name(dependency.target_test.split(' ')[-1])
        return f"{source_name}_to_{target_name}"

    async def _send_to_test_executor(self, response: TestScriptGenerationResponse):
        """发送到测试执行智能体"""
        try:
            # 这里应该发送到测试执行智能体
            logger.info(f"已发送到测试执行智能体: {response.doc_id}")
            
        except Exception as e:
            logger.error(f"发送到测试执行智能体失败: {str(e)}")

    async def _send_error_response(self, message: TestScriptGenerationRequest, error: str):
        """发送错误响应"""
        logger.error(f"测试脚本生成错误: {error}")

    def get_generation_statistics(self) -> Dict[str, Any]:
        """获取生成统计信息"""
        # 获取基类的公共统计
        common_stats = self.get_common_statistics()

        # 计算生成特定的统计
        success_rate = 0.0
        if self.generation_metrics["total_requests"] > 0:
            success_rate = (self.generation_metrics["successful_generations"] /
                          self.generation_metrics["total_requests"]) * 100

        # 合并统计信息
        return {
            **common_stats,
            "generation_metrics": self.generation_metrics,
            "generation_success_rate": round(success_rate, 2),
            "output_directory": str(self.output_dir)
        }


