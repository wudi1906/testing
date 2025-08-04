"""
脚本生成智能体 - 重新设计版本
专门负责将测试用例转换为可执行的自动化测试脚本

核心职责：
1. 将测试用例转换为高质量的pytest测试脚本
2. 生成完整的测试项目结构和配置文件
3. 集成测试框架和工具（pytest、requests、allure等）
4. 确保生成的脚本可以直接运行

数据流：ScriptGenerationInput -> 脚本生成 -> ScriptGenerationOutput
"""
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

from autogen_core import message_handler, type_subscription, MessageContext, TopicId
from loguru import logger

from app.agents.api_automation.base_api_agent import BaseApiAutomationAgent
from app.core.types import AgentTypes, TopicTypes

# 导入重新设计的数据模型
from .schemas import (
    ScriptGenerationInput, ScriptGenerationOutput, GeneratedScript,
    GeneratedTestCase, ParsedEndpoint, TestCaseType, AgentPrompts
)


@type_subscription(topic_type=TopicTypes.TEST_SCRIPT_GENERATOR.value)
class ScriptGeneratorAgent(BaseApiAutomationAgent):
    """
    脚本生成智能体 - 重新设计版本
    
    专注于生成高质量、可维护的自动化测试脚本，
    确保测试代码的专业性和可执行性。
    """

    def __init__(self, model_client_instance=None, agent_config=None, **kwargs):
        """初始化脚本生成智能体"""
        super().__init__(
            agent_type=AgentTypes.TEST_SCRIPT_GENERATOR,
            model_client_instance=model_client_instance,
            **kwargs
        )

        self.agent_config = agent_config or {}
        self._initialize_assistant_agent()

        # 生成统计指标
        self.generation_metrics = {
            "total_generations": 0,
            "successful_generations": 0,
            "failed_generations": 0,
            "total_scripts_generated": 0,
            "total_test_methods_generated": 0
        }

        # 脚本生成配置
        self.generation_config = {
            "framework": "pytest",
            "enable_allure": True,
            "enable_data_driven": True,
            "enable_parallel": True,
            "single_script_mode": True,  # 新增：单脚本模式
            "include_fixtures_inline": True,  # 新增：内联fixture
            "code_style": "pep8"
        }

        # 输出目录
        self.output_dir = Path("./generated_tests")
        self.output_dir.mkdir(exist_ok=True)

        logger.info(f"脚本生成智能体初始化完成: {self.agent_name}")

    @message_handler
    async def handle_script_generation_request(
        self,
        message: ScriptGenerationInput,
        ctx: MessageContext
    ) -> None:
        """处理脚本生成请求 - 主要入口点"""
        start_time = datetime.now()
        self.generation_metrics["total_generations"] += 1

        try:
            logger.info(
                f"开始生成测试脚本: document_id={message.document_id}, "
                f"interface_id={getattr(message, 'interface_id', None)}, "
                f"测试用例数量: {len(message.test_cases)}, "
                f"端点数量: {len(message.endpoints)}, "
                f"依赖关系数量: {len(getattr(message, 'dependencies', []))}"
            )

            # 记录开始生成脚本的日志
            await self._log_operation_start(
                message.session_id,
                "script_generation",
                {
                    "document_id": message.document_id,
                    "interface_id": getattr(message, 'interface_id', None),
                    "test_cases_count": len(message.test_cases),
                    "endpoints_count": len(message.endpoints),
                    "dependencies_count": len(getattr(message, 'dependencies', []))
                }
            )

            await self._log_operation_progress(
                message.session_id,
                "script_generation",
                "智能生成测试脚本"
            )

            # 1. 使用大模型智能生成测试脚本
            generation_result = await self._intelligent_generate_scripts(
                message.api_info,
                message.endpoints,
                message.test_cases,
                getattr(message, 'dependencies', []),  # 处理依赖关系
                message.execution_groups,
                message.generation_options  # 使用传递的生成选项
            )
            
            await self._log_operation_progress(
                message.session_id,
                "script_generation",
                "构建脚本对象",
                {"scripts_count": len(generation_result.get("scripts", []))}
            )

            # 2. 构建脚本对象（单脚本模式）
            scripts = self._build_script_objects(
                generation_result.get("scripts", []), message.test_cases
            )

            await self._log_operation_progress(
                message.session_id,
                "script_generation",
                "生成配置文件"
            )

            # 3. 简化配置（仅生成必要的配置信息）
            config_files = {}  # 不再生成额外的配置文件
            requirements_txt = self._generate_requirements_txt()
            readme_content = self._generate_simple_readme_content(message.api_info, scripts)
            
            # 6. 生成摘要信息
            generation_summary = self._generate_summary(scripts, generation_result)
            
            # 7. 构建输出结果
            output = ScriptGenerationOutput(
                session_id=message.session_id,
                document_id=message.document_id,
                interface_id=getattr(message, 'interface_id', None),  # 传递interface_id
                scripts=scripts,
                config_files=config_files,
                requirements_txt=requirements_txt,
                readme_content=readme_content,
                generation_summary=generation_summary,
                processing_time=(datetime.now() - start_time).total_seconds()
            )

            # 8. 更新统计指标
            self.generation_metrics["successful_generations"] += 1
            self.generation_metrics["total_scripts_generated"] += len(scripts)
            self.generation_metrics["total_test_methods_generated"] += sum(
                len(script.test_case_ids) for script in scripts
            )
            self._update_metrics("script_generation", True, output.processing_time)

            await self._log_operation_progress(
                message.session_id,
                "script_generation",
                "保存生成文件"
            )

            # 9. 保存生成的文件到磁盘
            await self._save_generated_files(output)

            await self._log_operation_progress(
                message.session_id,
                "script_generation",
                "发送到数据持久化智能体"
            )

            # 10. 发送脚本到数据持久化智能体
            await self._send_to_persistence_agent(output, message, ctx)

            await self._log_operation_complete(
                message.session_id,
                "script_generation",
                {
                    "scripts_count": len(scripts),
                    "processing_time": output.processing_time
                }
            )

            logger.info(f"脚本生成完成: {message.document_id}, 生成脚本数: {len(scripts)}")

        except Exception as e:
            self.generation_metrics["failed_generations"] += 1
            self._update_metrics("script_generation", False)
            error_info = self._handle_common_error(e, "script_generation")

            await self._log_operation_error(
                message.session_id,
                "script_generation",
                e
            )

            logger.error(f"脚本生成失败: {error_info}")

    async def _intelligent_generate_scripts(
        self,
        api_info,
        endpoints: List[ParsedEndpoint],
        test_cases: List[GeneratedTestCase],
        dependencies: List = None,
        execution_groups = None,
        generation_options: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """使用大模型智能生成测试脚本"""
        try:
            # 设置默认值
            dependencies = dependencies or []
            execution_groups = execution_groups or []
            generation_options = generation_options or {}

            # 构建生成任务提示词
            api_info_str = json.dumps({
                "title": api_info.title,
                "version": api_info.version,
                "description": api_info.description,
                "base_url": api_info.base_url
            }, indent=2, ensure_ascii=False)

            endpoints_info = self._format_endpoints_for_generation(endpoints)
            test_cases_info = self._format_test_cases_for_generation(test_cases)
            dependencies_info = self._format_dependencies_for_generation(dependencies)
            groups_info = self._format_execution_groups_for_generation(execution_groups)
            options_info = json.dumps(generation_options, indent=2, ensure_ascii=False)

            task_prompt = AgentPrompts.SCRIPT_GENERATOR_TASK_PROMPT.format(
                api_info=api_info_str,
                endpoints=endpoints_info,
                test_cases=test_cases_info,
                dependencies=dependencies_info,
                execution_groups=groups_info,
                generation_options=options_info
            )
            
            # 使用AssistantAgent进行智能生成
            result_content = await self._run_assistant_agent(task_prompt)
            
            if result_content:
                # 提取JSON结果
                parsed_data = self._extract_json_from_content(result_content)
                if parsed_data:
                    return parsed_data
            
            # 如果大模型生成失败，使用备用生成方法
            logger.warning("大模型生成失败，使用备用生成方法")
            return await self._fallback_generate_scripts(endpoints, test_cases, dependencies)

        except Exception as e:
            logger.error(f"智能脚本生成失败: {str(e)}")
            return await self._fallback_generate_scripts(endpoints, test_cases, dependencies)

    def _format_endpoints_for_generation(self, endpoints: List[ParsedEndpoint]) -> str:
        """格式化端点信息用于生成"""
        formatted_endpoints = []
        
        for endpoint in endpoints:
            endpoint_info = {
                "id": endpoint.endpoint_id,
                "path": endpoint.path,
                "method": endpoint.method.value,
                "summary": endpoint.summary,
                "auth_required": endpoint.auth_required,
                "parameters": [
                    {
                        "name": param.name,
                        "location": param.location.value,
                        "type": param.data_type.value,
                        "required": param.required
                    }
                    for param in endpoint.parameters
                ]
            }
            formatted_endpoints.append(endpoint_info)
        
        return json.dumps(formatted_endpoints, indent=2, ensure_ascii=False)

    def _format_test_cases_for_generation(self, test_cases: List[GeneratedTestCase]) -> str:
        """格式化测试用例信息用于生成"""
        formatted_cases = []
        
        for case in test_cases:
            case_info = {
                "test_id": case.test_case_id,
                "test_name": case.test_name,
                "endpoint_id": case.endpoint_id,
                "test_type": case.test_type.value,
                "description": case.description,
                "test_data": [
                    {
                        "parameter_name": data.parameter_name,
                        "test_value": data.test_value,
                        "value_description": data.value_description
                    }
                    for data in case.test_data
                ],
                "assertions": [
                    {
                        "assertion_type": assertion.assertion_type.value,
                        "expected_value": assertion.expected_value,
                        "comparison_operator": assertion.comparison_operator,
                        "description": assertion.description
                    }
                    for assertion in case.assertions
                ],
                "setup_steps": case.setup_steps,
                "cleanup_steps": case.cleanup_steps,
                "priority": case.priority,
                "tags": case.tags
            }
            formatted_cases.append(case_info)
        
        return json.dumps(formatted_cases, indent=2, ensure_ascii=False)

    def _format_dependencies_for_generation(self, dependencies) -> str:
        """格式化依赖关系信息用于生成"""
        if not dependencies:
            return "[]"

        formatted_deps = []
        for dep in dependencies:
            dep_info = {
                "source_endpoint_id": dep.source_endpoint_id,
                "target_endpoint_id": dep.target_endpoint_id,
                "dependency_type": dep.dependency_type.value if hasattr(dep.dependency_type, 'value') else str(dep.dependency_type),
                "description": dep.description,
                "data_mapping": dep.data_mapping
            }
            formatted_deps.append(dep_info)

        return json.dumps(formatted_deps, indent=2, ensure_ascii=False)

    def _format_execution_groups_for_generation(self, execution_groups) -> str:
        """格式化执行组信息用于生成"""
        formatted_groups = []
        
        for group in execution_groups:
            group_info = {
                "group_name": group.group_name,
                "endpoint_ids": group.endpoint_ids,
                "execution_order": group.execution_order,
                "parallel_execution": group.parallel_execution
            }
            formatted_groups.append(group_info)
        
        return json.dumps(formatted_groups, indent=2, ensure_ascii=False)

    def _build_script_objects(
        self, 
        scripts_data: List[Dict[str, Any]], 
        test_cases: List[GeneratedTestCase]
    ) -> List[GeneratedScript]:
        """构建脚本对象"""
        scripts = []
        
        for script_data in scripts_data:
            try:
                script = GeneratedScript(
                    script_name=script_data.get("script_name", "test_api.py"),
                    file_path=script_data.get("file_path", "test_api.py"),
                    script_content=script_data.get("script_content", ""),
                    test_case_ids=script_data.get("test_case_ids", []),
                    framework=script_data.get("framework", "pytest"),
                    dependencies=script_data.get("dependencies", []),
                    execution_order=script_data.get("execution_order", 1)
                )
                scripts.append(script)
                
            except Exception as e:
                logger.warning(f"构建脚本对象失败: {str(e)}")
                continue
        
        return scripts

    def _generate_config_files(self, api_info, scripts: List[GeneratedScript]) -> Dict[str, str]:
        """生成配置文件（已废弃 - 单脚本模式不需要额外配置文件）"""
        # 在单脚本模式下，不再生成额外的配置文件
        # 所有配置都内嵌在测试脚本中
        return {}

    def _generate_requirements_txt(self) -> str:
        """生成依赖文件"""
        requirements = [
            "pytest>=7.0.0",
            "requests>=2.28.0",
            "allure-pytest>=2.12.0",
            "pytest-html>=3.1.0",
            "pytest-xdist>=3.0.0",  # 并行执行
            "jsonschema>=4.0.0",    # JSON验证
            "pyyaml>=6.0",          # YAML支持
            "faker>=18.0.0",        # 测试数据生成
        ]
        return "\n".join(requirements)

    def _generate_readme_content(self, api_info, scripts: List[GeneratedScript]) -> str:
        """生成README文档"""
        return f"""# {api_info.title} API 自动化测试

## 项目描述
{api_info.description}

**API版本**: {api_info.version}
**基础URL**: {api_info.base_url}

## 项目结构
```
tests/
├── conftest.py          # pytest配置
├── api_utils.py         # API工具类
├── pytest.ini          # pytest配置文件
├── requirements.txt     # 依赖包
└── test_*.py           # 测试脚本
```

## 安装依赖
```bash
pip install -r requirements.txt
```

## 运行测试
```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest test_api.py

# 生成Allure报告
pytest --allure-dir=reports/allure-results
allure serve reports/allure-results
```

## 测试脚本说明
{chr(10).join(f"- **{script.script_name}**: 包含 {len(script.test_case_ids)} 个测试用例" for script in scripts)}

## 测试标记
- `positive`: 正向测试用例
- `negative`: 负向测试用例  
- `boundary`: 边界测试用例
- `security`: 安全测试用例
- `performance`: 性能测试用例

## 注意事项
1. 请确保API服务正在运行
2. 根据实际环境修改配置文件中的base_url
3. 如需认证，请在conftest.py中配置认证信息
"""

    def _generate_summary(
        self,
        scripts: List[GeneratedScript],
        generation_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成摘要信息"""
        return {
            "total_scripts": len(scripts),
            "total_test_methods": sum(len(script.test_case_ids) for script in scripts),
            "generation_method": generation_result.get("generation_method", "intelligent_single_script"),
            "confidence_score": generation_result.get("confidence_score", 0.8),
            "framework": self.generation_config["framework"],
            "script_mode": "single_script",  # 新增：标识单脚本模式
            "features_enabled": {
                "allure_reporting": self.generation_config["enable_allure"],
                "data_driven_testing": self.generation_config["enable_data_driven"],
                "parallel_execution": self.generation_config["enable_parallel"],
                "inline_fixtures": self.generation_config["include_fixtures_inline"],
                "self_contained": True  # 新增：自包含标识
            },
            "generation_config": self.generation_config,
            "optimization_notes": [
                "生成单一完整测试脚本",
                "所有fixture和工具函数内嵌在脚本中",
                "无需额外配置文件",
                "脚本可独立运行"
            ]
        }

    async def _fallback_generate_scripts(
        self,
        endpoints: List[ParsedEndpoint],
        test_cases: List[GeneratedTestCase],
        dependencies: List = None
    ) -> Dict[str, Any]:
        """备用脚本生成方法 - 生成单一完整脚本"""
        try:
            # 生成完整的自包含测试脚本
            script_content = self._generate_complete_script_template(endpoints, test_cases, dependencies)

            scripts = [{
                "script_name": "test_api_automation.py",
                "file_path": "test_api_automation.py",
                "script_content": script_content,
                "test_case_ids": [tc.test_case_id for tc in test_cases],
                "framework": "pytest",
                "dependencies": ["pytest", "requests", "allure-pytest"],
                "execution_order": 1
            }]

            return {
                "scripts": scripts,
                "confidence_score": 0.7,
                "generation_method": "fallback_single_script"
            }

        except Exception as e:
            logger.error(f"备用脚本生成失败: {str(e)}")
            return {"scripts": [], "confidence_score": 0.3}

    def _generate_complete_script_template(
        self,
        endpoints: List[ParsedEndpoint],
        test_cases: List[GeneratedTestCase],
        dependencies: List = None
    ) -> str:
        """生成完整的自包含脚本模板"""
        dependencies = dependencies or []

        # 获取API基础URL（从第一个端点推断）
        base_url = "http://localhost:8000"  # 默认值
        if endpoints:
            # 尝试从端点路径推断基础URL
            base_url = "http://localhost:8000"  # 可以根据实际情况调整

        return f'''"""
API自动化测试脚本 - 完整自包含版本
自动生成于 {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

此脚本包含所有必要的配置、工具函数和测试用例，可以独立运行。

运行方式：
    pytest test_api_automation.py -v
    pytest test_api_automation.py --allure-dir=reports
"""
import pytest
import requests
import json
import time
from typing import Dict, Any, Optional
from urllib.parse import urljoin

# ============================================================================
# 配置常量
# ============================================================================

API_BASE_URL = "{base_url}"
DEFAULT_TIMEOUT = 30
DEFAULT_HEADERS = {{
    "Content-Type": "application/json",
    "User-Agent": "API-Test-Automation/1.0"
}}

# ============================================================================
# 公共Fixture定义
# ============================================================================

@pytest.fixture(scope="session")
def api_config():
    """API配置信息"""
    return {{
        "base_url": API_BASE_URL,
        "timeout": DEFAULT_TIMEOUT,
        "headers": DEFAULT_HEADERS.copy()
    }}

@pytest.fixture(scope="session")
def api_client(api_config):
    """API客户端会话"""
    session = requests.Session()
    session.headers.update(api_config["headers"])
    return session

@pytest.fixture(scope="function")
def test_data():
    """测试数据"""
    return {{
        "timestamp": int(time.time()),
        "test_id": f"test_{{int(time.time())}}"
    }}

# ============================================================================
# 工具函数定义
# ============================================================================

def make_request(client: requests.Session, method: str, path: str,
                base_url: str = API_BASE_URL, **kwargs) -> requests.Response:
    """发送HTTP请求的统一方法"""
    url = urljoin(base_url.rstrip('/') + '/', path.lstrip('/'))

    # 设置默认超时
    if 'timeout' not in kwargs:
        kwargs['timeout'] = DEFAULT_TIMEOUT

    try:
        response = client.request(method.upper(), url, **kwargs)
        return response
    except requests.exceptions.RequestException as e:
        pytest.fail(f"请求失败: {{method}} {{url}} - {{str(e)}}")

def validate_response_status(response: requests.Response, expected_status: int = 200):
    """验证响应状态码"""
    assert response.status_code == expected_status, \\
        f"期望状态码 {{expected_status}}, 实际状态码 {{response.status_code}}, 响应内容: {{response.text[:200]}}"

def validate_response_json(response: requests.Response) -> Dict[str, Any]:
    """验证并返回JSON响应"""
    try:
        return response.json()
    except json.JSONDecodeError:
        pytest.fail(f"响应不是有效的JSON格式: {{response.text[:200]}}")

def validate_response_time(response: requests.Response, max_time: float = 5.0):
    """验证响应时间"""
    response_time = response.elapsed.total_seconds()
    assert response_time <= max_time, \\
        f"响应时间 {{response_time:.2f}}s 超过最大允许时间 {{max_time}}s"

def validate_json_structure(data: Dict[str, Any], required_fields: list):
    """验证JSON结构包含必需字段"""
    for field in required_fields:
        assert field in data, f"响应JSON缺少必需字段: {{field}}"

# ============================================================================
# 测试类定义
# ============================================================================

class TestAPIAutomation:
    """API自动化测试类"""

{self._generate_complete_test_methods(test_cases, endpoints)}
'''

    def _generate_complete_test_methods(self, test_cases: List[GeneratedTestCase], endpoints: List[ParsedEndpoint]) -> str:
        """生成完整的测试方法集合"""
        methods = []

        for test_case in test_cases:
            endpoint = next((ep for ep in endpoints if ep.endpoint_id == test_case.endpoint_id), None)
            if not endpoint:
                continue

            method_content = self._generate_single_test_method(test_case, endpoint)
            methods.append(method_content)

        return "\n".join(methods)

    def _generate_single_test_method(self, test_case: GeneratedTestCase, endpoint: ParsedEndpoint) -> str:
        """生成单个测试方法"""
        method_name = test_case.test_name.replace(" ", "_").replace("-", "_").lower()
        if not method_name.startswith("test_"):
            method_name = f"test_{method_name}"

        # 生成测试数据
        test_data_setup = self._generate_test_data_setup(test_case)

        # 生成请求参数
        request_params = self._generate_request_params(test_case, endpoint)

        # 生成断言
        assertions = self._generate_assertions(test_case)

        # 检查是否有状态码断言
        has_status_assertion = any(a.assertion_type.value == "status_code" for a in test_case.assertions)

        return f'''    def {method_name}(self, api_client, api_config, test_data):
        """
        {test_case.description}
        测试类型: {test_case.test_type.value}
        端点: {endpoint.method.value} {endpoint.path}
        """
        # 测试数据准备
{test_data_setup}

        # 发送请求
        response = make_request(
            api_client,
            "{endpoint.method.value}",
            "{endpoint.path}",
            api_config["base_url"],
{request_params}
        )

        # 基础验证
        {"# 状态码验证在自定义断言中进行" if has_status_assertion else "validate_response_status(response, 200)"}
        validate_response_time(response, 5.0)

{assertions}

        # 记录测试结果
        print(f"✅ {{test_data['test_id']}} - {test_case.test_name} 测试通过")
'''

    def _generate_test_data_setup(self, test_case: GeneratedTestCase) -> str:
        """生成测试数据设置代码"""
        if not test_case.test_data:
            return "        # 无需特殊测试数据"

        setup_lines = []
        for data_item in test_case.test_data:
            # 确保变量名符合Python命名规范
            var_name = data_item.parameter_name.replace("-", "_").replace(".", "_")
            # 确保变量名是有效的Python标识符
            if not var_name.isidentifier():
                var_name = f"param_{var_name}"

            setup_lines.append(f'        {var_name} = "{data_item.test_value}"  # {data_item.value_description}')

        return "\n".join(setup_lines)

    def _generate_request_params(self, test_case: GeneratedTestCase, endpoint: ParsedEndpoint) -> str:
        """生成请求参数代码"""
        params = []

        # 构建请求体数据
        if test_case.test_data and endpoint.method.value in ["POST", "PUT", "PATCH"]:
            json_fields = []
            header_fields = []

            for data_item in test_case.test_data:
                var_name = data_item.parameter_name.replace("-", "_").replace(".", "_")
                if not var_name.isidentifier():
                    var_name = f"param_{var_name}"

                # 区分请求体参数和header参数
                if data_item.parameter_name.lower() in ['access-token', 'fecshop-currency', 'fecshop-lang']:
                    # 这些是header参数
                    header_key = data_item.parameter_name
                    header_fields.append(f'"{header_key}": {var_name}')
                else:
                    # 这些是请求体参数
                    json_fields.append(f'"{data_item.parameter_name}": {var_name}')

            if json_fields:
                json_data = "{" + ", ".join(json_fields) + "}"
                params.append(f'            json={json_data},')

            if header_fields:
                headers_data = "{" + ", ".join(header_fields) + "}"
                params.append(f'            headers={headers_data}')

        # 根据端点参数类型生成其他参数
        has_query_params = any(p.location.value == "query" for p in endpoint.parameters)

        if has_query_params and not any("params=" in p for p in params):
            params.append('            # params={}  # 查询参数（如需要）')

        if not params:
            params.append('            # 无需额外参数')

        return "\n".join(params)

    def _generate_assertions(self, test_case: GeneratedTestCase) -> str:
        """生成断言代码"""
        if not test_case.assertions:
            return """        # 自定义断言验证
        response_data = validate_response_json(response)
        assert response_data is not None"""

        assertion_lines = ["        # 自定义断言验证"]
        assertion_lines.append("        response_data = validate_response_json(response)")

        # 检查是否有状态码断言，避免重复验证
        has_status_assertion = any(a.assertion_type.value == "status_code" for a in test_case.assertions)

        for assertion in test_case.assertions:
            if assertion.assertion_type.value == "status_code":
                # 只在这里验证状态码，不在基础验证中重复
                assertion_lines.append(f'        validate_response_status(response, {assertion.expected_value})')
            elif assertion.assertion_type.value == "json_field":
                assertion_lines.append(f'        assert "{assertion.expected_value}" in response_data  # {assertion.description}')
            elif assertion.assertion_type.value == "response_time":
                assertion_lines.append(f'        validate_response_time(response, {assertion.expected_value})')

        return "\n".join(assertion_lines)

    def _generate_simple_readme_content(self, api_info, scripts: List[GeneratedScript]) -> str:
        """生成简化的README文档"""
        script_name = scripts[0].script_name if scripts else "test_api_automation.py"
        total_tests = sum(len(script.test_case_ids) for script in scripts)

        return f"""# {api_info.title} API 自动化测试

## 项目描述
{api_info.description}

**API版本**: {api_info.version}
**基础URL**: {api_info.base_url}

## 测试脚本
- **{script_name}**: 包含 {total_tests} 个测试用例的完整自动化测试脚本

## 快速开始

### 1. 安装依赖
```bash
pip install pytest requests allure-pytest
```

### 2. 运行测试
```bash
# 运行所有测试
pytest {script_name} -v

# 生成详细报告
pytest {script_name} -v --tb=short

# 生成Allure报告
pytest {script_name} --allure-dir=reports
allure serve reports
```

### 3. 测试配置
测试脚本是完全自包含的，所有配置都在脚本内部定义。
如需修改API基础URL，请编辑脚本中的 `API_BASE_URL` 常量。

## 注意事项
1. 确保API服务正在运行
2. 根据实际环境修改脚本中的API_BASE_URL
3. 如需认证，请在脚本中的api_config fixture中添加认证信息

## 测试特性
- ✅ 完整的HTTP请求测试
- ✅ 响应状态码验证
- ✅ JSON响应结构验证
- ✅ 响应时间性能验证
- ✅ 详细的错误信息和日志
- ✅ 支持Allure测试报告
"""

    async def _save_generated_files(self, output: ScriptGenerationOutput):
        """保存生成的文件到磁盘（简化版本）"""
        try:
            # 创建项目目录
            project_dir = self.output_dir / f"api_test_{output.interface_id[:8]}"
            project_dir.mkdir(exist_ok=True)

            # 保存测试脚本（主要文件）
            for script in output.scripts:
                script_path = project_dir / script.file_path
                script_path.write_text(script.script_content, encoding='utf-8')
                logger.info(f"已保存测试脚本: {script_path}")

            # 保存依赖文件
            if output.requirements_txt:
                requirements_path = project_dir / "requirements.txt"
                requirements_path.write_text(output.requirements_txt, encoding='utf-8')
                logger.info(f"已保存依赖文件: {requirements_path}")

            # 保存README
            if output.readme_content:
                readme_path = project_dir / "README.md"
                readme_path.write_text(output.readme_content, encoding='utf-8')
                logger.info(f"已保存README文档: {readme_path}")

            logger.info(f"✅ 单脚本测试项目已保存到: {project_dir}")
            logger.info(f"📁 生成的文件: {len(output.scripts)} 个脚本文件")

        except Exception as e:
            logger.error(f"保存生成文件失败: {str(e)}")

    def get_generation_statistics(self) -> Dict[str, Any]:
        """获取生成统计信息"""
        base_stats = self.get_common_statistics()
        base_stats.update({
            "generation_metrics": self.generation_metrics,
            "generation_config": self.generation_config,
            "avg_scripts_per_generation": (
                self.generation_metrics["total_scripts_generated"] / 
                max(self.generation_metrics["successful_generations"], 1)
            ),
            "avg_methods_per_script": (
                self.generation_metrics["total_test_methods_generated"] / 
                max(self.generation_metrics["total_scripts_generated"], 1)
            )
        })
        return base_stats

    async def _send_to_persistence_agent(self, output: ScriptGenerationOutput, message: ScriptGenerationInput, ctx: MessageContext):
        """发送脚本到数据持久化智能体"""
        try:
            from .schemas import ScriptPersistenceInput

            # 构建脚本持久化输入
            persistence_input = ScriptPersistenceInput(
                session_id=output.session_id,
                document_id=output.document_id,
                interface_id=message.interface_id,
                scripts=output.scripts,
                config_files=output.config_files,
                requirements_txt=output.requirements_txt,
                readme_content=output.readme_content,
                generation_summary=output.generation_summary,
                processing_time=output.processing_time
            )

            # 发送到数据持久化智能体
            await self.runtime.publish_message(
                persistence_input,
                topic_id=TopicId(type=TopicTypes.API_DATA_PERSISTENCE.value, source=self.agent_name)
            )

            logger.info(f"已发送脚本到数据持久化智能体: {output.document_id}")

        except Exception as e:
            logger.error(f"发送脚本到数据持久化智能体失败: {str(e)}")
