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
            "include_utils": True,
            "include_config": True,
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
            logger.info(f"开始生成测试脚本: {message.document_id}, 测试用例数量: {len(message.test_cases)}")

            # 1. 使用大模型智能生成测试脚本
            generation_result = await self._intelligent_generate_scripts(
                message.api_info, message.endpoints, message.test_cases, message.execution_groups
            )
            
            # 2. 构建脚本对象
            scripts = self._build_script_objects(
                generation_result.get("scripts", []), message.test_cases
            )
            
            # 3. 生成配置文件
            config_files = self._generate_config_files(message.api_info, scripts)
            
            # 4. 生成依赖文件
            requirements_txt = self._generate_requirements_txt()
            
            # 5. 生成README文档
            readme_content = self._generate_readme_content(message.api_info, scripts)
            
            # 6. 生成摘要信息
            generation_summary = self._generate_summary(scripts, generation_result)
            
            # 7. 构建输出结果
            output = ScriptGenerationOutput(
                session_id=message.session_id,
                document_id=message.document_id,
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

            # 9. 保存生成的文件到磁盘
            await self._save_generated_files(output)

            # 10. 发送脚本到数据持久化智能体
            await self._send_to_persistence_agent(output, message, ctx)

            logger.info(f"脚本生成完成: {message.document_id}, 生成脚本数: {len(scripts)}")

        except Exception as e:
            self.generation_metrics["failed_generations"] += 1
            self._update_metrics("script_generation", False)
            error_info = self._handle_common_error(e, "script_generation")
            logger.error(f"脚本生成失败: {error_info}")

    async def _intelligent_generate_scripts(
        self, 
        api_info, 
        endpoints: List[ParsedEndpoint],
        test_cases: List[GeneratedTestCase],
        execution_groups
    ) -> Dict[str, Any]:
        """使用大模型智能生成测试脚本"""
        try:
            # 构建生成任务提示词
            api_info_str = json.dumps({
                "title": api_info.title,
                "version": api_info.version,
                "description": api_info.description,
                "base_url": api_info.base_url
            }, indent=2, ensure_ascii=False)
            
            endpoints_info = self._format_endpoints_for_generation(endpoints)
            test_cases_info = self._format_test_cases_for_generation(test_cases)
            groups_info = self._format_execution_groups_for_generation(execution_groups)
            
            task_prompt = AgentPrompts.SCRIPT_GENERATOR_TASK_PROMPT.format(
                api_info=api_info_str,
                endpoints=endpoints_info,
                test_cases=test_cases_info,
                execution_groups=groups_info
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
            return await self._fallback_generate_scripts(endpoints, test_cases)
            
        except Exception as e:
            logger.error(f"智能脚本生成失败: {str(e)}")
            return await self._fallback_generate_scripts(endpoints, test_cases)

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
        """生成配置文件"""
        config_files = {}
        
        # pytest.ini配置
        config_files["pytest.ini"] = f"""[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short --allure-dir=reports/allure-results
markers =
    positive: 正向测试用例
    negative: 负向测试用例
    boundary: 边界测试用例
    security: 安全测试用例
    performance: 性能测试用例
"""

        # conftest.py配置
        config_files["conftest.py"] = f'''"""
pytest配置文件
"""
import pytest
import requests
from typing import Dict, Any

@pytest.fixture(scope="session")
def api_config():
    """API配置"""
    return {{
        "base_url": "{api_info.base_url}",
        "timeout": 30,
        "headers": {{
            "Content-Type": "application/json",
            "User-Agent": "API-Test-Agent/1.0"
        }}
    }}

@pytest.fixture(scope="session")
def api_client(api_config):
    """API客户端"""
    session = requests.Session()
    session.headers.update(api_config["headers"])
    return session

@pytest.fixture(scope="function")
def test_data():
    """测试数据"""
    return {{}}
'''

        # API工具类
        config_files["api_utils.py"] = '''"""
API测试工具类
"""
import json
import requests
from typing import Dict, Any, Optional

class APIClient:
    """API客户端封装"""
    
    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "API-Test-Client/1.0"
        })
    
    def request(self, method: str, path: str, **kwargs) -> requests.Response:
        """发送HTTP请求"""
        url = f"{self.base_url}{path}"
        return self.session.request(method, url, timeout=self.timeout, **kwargs)
    
    def get(self, path: str, **kwargs) -> requests.Response:
        """GET请求"""
        return self.request("GET", path, **kwargs)
    
    def post(self, path: str, **kwargs) -> requests.Response:
        """POST请求"""
        return self.request("POST", path, **kwargs)
    
    def put(self, path: str, **kwargs) -> requests.Response:
        """PUT请求"""
        return self.request("PUT", path, **kwargs)
    
    def delete(self, path: str, **kwargs) -> requests.Response:
        """DELETE请求"""
        return self.request("DELETE", path, **kwargs)

class ResponseValidator:
    """响应验证器"""
    
    @staticmethod
    def validate_status_code(response: requests.Response, expected: int):
        """验证状态码"""
        assert response.status_code == expected, f"期望状态码 {expected}, 实际 {response.status_code}"
    
    @staticmethod
    def validate_json_schema(response: requests.Response, schema: Dict[str, Any]):
        """验证JSON结构"""
        try:
            data = response.json()
            # 这里可以集成jsonschema库进行验证
            assert isinstance(data, dict), "响应不是有效的JSON对象"
        except json.JSONDecodeError:
            assert False, "响应不是有效的JSON格式"
    
    @staticmethod
    def validate_response_time(response: requests.Response, max_time: float):
        """验证响应时间"""
        assert response.elapsed.total_seconds() <= max_time, f"响应时间超过 {max_time} 秒"
'''

        return config_files

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
            "generation_method": generation_result.get("generation_method", "intelligent"),
            "confidence_score": generation_result.get("confidence_score", 0.8),
            "framework": self.generation_config["framework"],
            "features_enabled": {
                "allure_reporting": self.generation_config["enable_allure"],
                "data_driven_testing": self.generation_config["enable_data_driven"],
                "parallel_execution": self.generation_config["enable_parallel"]
            },
            "generation_config": self.generation_config
        }

    async def _fallback_generate_scripts(
        self, 
        endpoints: List[ParsedEndpoint],
        test_cases: List[GeneratedTestCase]
    ) -> Dict[str, Any]:
        """备用脚本生成方法"""
        try:
            # 生成基础测试脚本
            script_content = self._generate_basic_script_template(endpoints, test_cases)
            
            scripts = [{
                "script_name": "test_api_basic.py",
                "file_path": "test_api_basic.py",
                "script_content": script_content,
                "test_case_ids": [tc.test_case_id for tc in test_cases],
                "framework": "pytest",
                "dependencies": ["pytest", "requests"],
                "execution_order": 1
            }]
            
            return {
                "scripts": scripts,
                "confidence_score": 0.6,
                "generation_method": "fallback_basic"
            }
            
        except Exception as e:
            logger.error(f"备用脚本生成失败: {str(e)}")
            return {"scripts": [], "confidence_score": 0.3}

    def _generate_basic_script_template(
        self, 
        endpoints: List[ParsedEndpoint],
        test_cases: List[GeneratedTestCase]
    ) -> str:
        """生成基础脚本模板"""
        return f'''"""
API自动化测试脚本 - 基础版本
自动生成于 {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""
import pytest
import requests
import json
from api_utils import APIClient, ResponseValidator

class TestAPI:
    """API测试类"""
    
    @pytest.fixture(autouse=True)
    def setup(self, api_config):
        """测试初始化"""
        self.client = APIClient(api_config["base_url"])
        self.validator = ResponseValidator()
    
{chr(10).join(self._generate_test_method(tc, endpoints) for tc in test_cases)}
'''

    def _generate_test_method(self, test_case: GeneratedTestCase, endpoints: List[ParsedEndpoint]) -> str:
        """生成测试方法"""
        endpoint = next((ep for ep in endpoints if ep.endpoint_id == test_case.endpoint_id), None)
        if not endpoint:
            return ""
        
        method_name = test_case.test_name.replace(" ", "_").replace("-", "_").lower()
        if not method_name.startswith("test_"):
            method_name = f"test_{method_name}"
        
        return f'''    def {method_name}(self):
        """
        {test_case.description}
        测试类型: {test_case.test_type.value}
        """
        # 发送请求
        response = self.client.{endpoint.method.value.lower()}(
            "{endpoint.path}",
            # 这里需要根据实际测试数据填充参数
        )
        
        # 验证响应
        self.validator.validate_status_code(response, 200)
        
        # 其他断言
        assert response.json() is not None
'''

    async def _save_generated_files(self, output: ScriptGenerationOutput):
        """保存生成的文件到磁盘"""
        try:
            # 创建项目目录
            project_dir = self.output_dir / f"api_test_{output.document_id[:8]}"
            project_dir.mkdir(exist_ok=True)
            
            # 保存测试脚本
            for script in output.scripts:
                script_path = project_dir / script.file_path
                script_path.write_text(script.script_content, encoding='utf-8')
            
            # 保存配置文件
            for filename, content in output.config_files.items():
                config_path = project_dir / filename
                config_path.write_text(content, encoding='utf-8')
            
            # 保存依赖文件
            requirements_path = project_dir / "requirements.txt"
            requirements_path.write_text(output.requirements_txt, encoding='utf-8')
            
            # 保存README
            readme_path = project_dir / "README.md"
            readme_path.write_text(output.readme_content, encoding='utf-8')
            
            logger.info(f"测试项目已保存到: {project_dir}")
            
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
                interface_id=message.interface_id or output.document_id,  # 使用传入的interface_id
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
