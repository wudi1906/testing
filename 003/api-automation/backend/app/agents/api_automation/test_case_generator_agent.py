"""
测试用例生成智能体 - 重新设计版本
专门负责基于API端点和依赖关系生成全面的测试用例

核心职责：
1. 基于API端点信息生成多种类型的测试用例
2. 处理端点间的依赖关系，生成合适的测试数据
3. 设计准确的测试断言和验证逻辑
4. 生成测试覆盖度报告和质量评估

数据流：TestCaseGenerationInput -> 测试用例生成 -> TestCaseGenerationOutput
"""
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional

from autogen_core import message_handler, type_subscription, MessageContext, TopicId
from loguru import logger

from app.agents.api_automation.base_api_agent import BaseApiAutomationAgent
from app.core.types import AgentTypes, TopicTypes

# 导入重新设计的数据模型
from .schemas import (
    TestCaseGenerationInput, TestCaseGenerationOutput, GeneratedTestCase,
    TestDataItem, TestAssertion, ParsedEndpoint, EndpointDependency,
    TestCaseType, AssertionType, AgentPrompts
)


@type_subscription(topic_type=TopicTypes.API_TEST_CASE_GENERATOR.value)
class TestCaseGeneratorAgent(BaseApiAutomationAgent):
    """
    测试用例生成智能体 - 重新设计版本
    
    专注于生成高质量、全覆盖的API测试用例，
    为脚本生成智能体提供详细的测试规范。
    """

    def __init__(self, model_client_instance=None, agent_config=None, **kwargs):
        """初始化测试用例生成智能体"""
        super().__init__(
            agent_type=AgentTypes.API_TEST_CASE_GENERATOR,
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
            "total_test_cases_generated": 0,
            "test_cases_by_type": {
                "positive": 0,
                "negative": 0,
                "boundary": 0,
                "security": 0,
                "performance": 0
            }
        }

        # 测试用例生成配置
        self.generation_config = {
            "enable_positive_tests": True,
            "enable_negative_tests": True,
            "enable_boundary_tests": True,
            "enable_security_tests": True,
            "enable_performance_tests": False,  # 默认关闭性能测试
            "max_cases_per_endpoint": 10,
            "coverage_threshold": 0.8
        }

        logger.info(f"测试用例生成智能体初始化完成: {self.agent_name}")

    @message_handler
    async def handle_test_case_generation_request(
        self,
        message: TestCaseGenerationInput,
        ctx: MessageContext
    ) -> None:
        """处理测试用例生成请求 - 主要入口点"""
        start_time = datetime.now()
        self.generation_metrics["total_generations"] += 1

        try:
            logger.info(f"开始生成测试用例: {message.document_id}, 端点数量: {len(message.endpoints)}")

            # 1. 使用大模型智能生成测试用例
            generation_result = await self._intelligent_generate_test_cases(
                message.api_info, message.endpoints, message.dependencies, message.execution_groups
            )
            
            # 2. 构建测试用例对象
            test_cases = self._build_test_case_objects(
                generation_result.get("test_cases", []), message.endpoints
            )
            
            # 3. 生成覆盖度报告
            coverage_report = self._generate_coverage_report(test_cases, message.endpoints)
            
            # 4. 生成摘要信息
            generation_summary = self._generate_summary(test_cases, generation_result)
            
            # 5. 构建输出结果
            output = TestCaseGenerationOutput(
                session_id=message.session_id,
                document_id=message.document_id,
                test_cases=test_cases,
                coverage_report=coverage_report,
                generation_summary=generation_summary,
                processing_time=(datetime.now() - start_time).total_seconds()
            )

            # 6. 更新统计指标
            self.generation_metrics["successful_generations"] += 1
            self.generation_metrics["total_test_cases_generated"] += len(test_cases)
            self._update_test_case_type_metrics(test_cases)
            self._update_metrics("test_case_generation", True, output.processing_time)

            # 7. 发送结果到脚本生成智能体
            await self._send_to_script_generator(output, message, ctx)

            logger.info(f"测试用例生成完成: {message.document_id}, 生成用例数: {len(test_cases)}")

        except Exception as e:
            self.generation_metrics["failed_generations"] += 1
            self._update_metrics("test_case_generation", False)
            error_info = self._handle_common_error(e, "test_case_generation")
            logger.error(f"测试用例生成失败: {error_info}")

    async def _intelligent_generate_test_cases(
        self, 
        api_info, 
        endpoints: List[ParsedEndpoint],
        dependencies: List[EndpointDependency],
        execution_groups
    ) -> Dict[str, Any]:
        """使用大模型智能生成测试用例"""
        try:
            # 构建生成任务提示词
            endpoints_info = self._format_endpoints_for_generation(endpoints)
            dependencies_info = self._format_dependencies_for_generation(dependencies)
            groups_info = self._format_execution_groups_for_generation(execution_groups)
            api_info_str = json.dumps({
                "title": api_info.title,
                "version": api_info.version,
                "description": api_info.description,
                "base_url": api_info.base_url
            }, indent=2, ensure_ascii=False)
            
            task_prompt = AgentPrompts.TEST_CASE_GENERATOR_TASK_PROMPT.format(
                api_info=api_info_str,
                endpoints=endpoints_info,
                dependencies=dependencies_info,
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
            return await self._fallback_generate_test_cases(endpoints, dependencies)
            
        except Exception as e:
            logger.error(f"智能测试用例生成失败: {str(e)}")
            return await self._fallback_generate_test_cases(endpoints, dependencies)

    def _format_endpoints_for_generation(self, endpoints: List[ParsedEndpoint]) -> str:
        """格式化端点信息用于生成"""
        formatted_endpoints = []
        
        for endpoint in endpoints:
            endpoint_info = {
                "id": endpoint.endpoint_id,
                "path": endpoint.path,
                "method": endpoint.method.value,
                "summary": endpoint.summary,
                "description": endpoint.description,
                "auth_required": endpoint.auth_required,
                "parameters": [
                    {
                        "name": param.name,
                        "location": param.location.value,
                        "type": param.data_type.value,
                        "required": param.required,
                        "description": param.description,
                        "example": param.example,
                        "constraints": param.constraints
                    }
                    for param in endpoint.parameters
                ],
                "responses": [
                    {
                        "status_code": resp.status_code,
                        "description": resp.description,
                        "content_type": resp.content_type
                    }
                    for resp in endpoint.responses
                ]
            }
            formatted_endpoints.append(endpoint_info)
        
        return json.dumps(formatted_endpoints, indent=2, ensure_ascii=False)

    def _format_dependencies_for_generation(self, dependencies: List[EndpointDependency]) -> str:
        """格式化依赖关系信息用于生成"""
        formatted_deps = []
        
        for dep in dependencies:
            dep_info = {
                "source_endpoint_id": dep.source_endpoint_id,
                "target_endpoint_id": dep.target_endpoint_id,
                "dependency_type": dep.dependency_type.value,
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

    def _build_test_case_objects(
        self, 
        test_cases_data: List[Dict[str, Any]], 
        endpoints: List[ParsedEndpoint]
    ) -> List[GeneratedTestCase]:
        """构建测试用例对象"""
        test_cases = []
        endpoint_id_map = {ep.endpoint_id: ep for ep in endpoints}
        
        for case_data in test_cases_data:
            try:
                # 验证端点ID存在
                endpoint_id = case_data.get("endpoint_id")
                if endpoint_id not in endpoint_id_map:
                    continue
                
                # 构建测试数据
                test_data = []
                for data_item in case_data.get("test_data", []):
                    test_data.append(TestDataItem(
                        parameter_name=data_item.get("parameter_name", ""),
                        test_value=data_item.get("test_value"),
                        value_description=data_item.get("value_description", "")
                    ))
                
                # 构建断言
                assertions = []
                for assertion_item in case_data.get("assertions", []):
                    assertions.append(TestAssertion(
                        assertion_type=AssertionType(assertion_item.get("assertion_type", "status_code")),
                        expected_value=assertion_item.get("expected_value"),
                        comparison_operator=assertion_item.get("comparison_operator", "equals"),
                        description=assertion_item.get("description", "")
                    ))
                
                # 创建测试用例对象
                test_case = GeneratedTestCase(
                    test_name=case_data.get("test_name", ""),
                    endpoint_id=endpoint_id,
                    test_type=TestCaseType(case_data.get("test_type", "positive")),
                    description=case_data.get("description", ""),
                    test_data=test_data,
                    assertions=assertions,
                    setup_steps=case_data.get("setup_steps", []),
                    cleanup_steps=case_data.get("cleanup_steps", []),
                    priority=case_data.get("priority", 1),
                    tags=case_data.get("tags", [])
                )
                
                test_cases.append(test_case)
                
            except Exception as e:
                logger.warning(f"构建测试用例对象失败: {str(e)}")
                continue
        
        return test_cases

    def _generate_coverage_report(
        self, 
        test_cases: List[GeneratedTestCase], 
        endpoints: List[ParsedEndpoint]
    ) -> Dict[str, Any]:
        """生成覆盖度报告"""
        total_endpoints = len(endpoints)
        covered_endpoints = len(set(tc.endpoint_id for tc in test_cases))
        
        # 按测试类型统计
        type_coverage = {}
        for test_type in TestCaseType:
            type_cases = [tc for tc in test_cases if tc.test_type == test_type]
            type_coverage[test_type.value] = {
                "count": len(type_cases),
                "endpoints_covered": len(set(tc.endpoint_id for tc in type_cases))
            }
        
        return {
            "total_endpoints": total_endpoints,
            "covered_endpoints": covered_endpoints,
            "coverage_percentage": (covered_endpoints / total_endpoints * 100) if total_endpoints > 0 else 0,
            "total_test_cases": len(test_cases),
            "test_cases_by_type": type_coverage,
            "uncovered_endpoints": [
                ep.endpoint_id for ep in endpoints 
                if ep.endpoint_id not in set(tc.endpoint_id for tc in test_cases)
            ]
        }

    def _generate_summary(
        self, 
        test_cases: List[GeneratedTestCase], 
        generation_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成摘要信息"""
        return {
            "total_test_cases": len(test_cases),
            "generation_method": generation_result.get("generation_method", "intelligent"),
            "confidence_score": generation_result.get("confidence_score", 0.8),
            "test_case_distribution": {
                test_type.value: len([tc for tc in test_cases if tc.test_type == test_type])
                for test_type in TestCaseType
            },
            "avg_assertions_per_case": (
                sum(len(tc.assertions) for tc in test_cases) / len(test_cases)
                if test_cases else 0
            ),
            "generation_config": self.generation_config
        }

    def _update_test_case_type_metrics(self, test_cases: List[GeneratedTestCase]):
        """更新测试用例类型统计"""
        for test_case in test_cases:
            test_type = test_case.test_type.value
            if test_type in self.generation_metrics["test_cases_by_type"]:
                self.generation_metrics["test_cases_by_type"][test_type] += 1

    async def _fallback_generate_test_cases(
        self, 
        endpoints: List[ParsedEndpoint],
        dependencies: List[EndpointDependency]
    ) -> Dict[str, Any]:
        """备用测试用例生成方法"""
        try:
            test_cases = []
            
            for endpoint in endpoints:
                # 为每个端点生成基本的正向测试用例
                basic_case = {
                    "test_name": f"test_{endpoint.method.value.lower()}_{endpoint.path.replace('/', '_').replace('{', '').replace('}', '')}",
                    "endpoint_id": endpoint.endpoint_id,
                    "test_type": "positive",
                    "description": f"测试 {endpoint.method.value} {endpoint.path} 的基本功能",
                    "test_data": [
                        {
                            "parameter_name": param.name,
                            "test_value": self._generate_default_test_value(param),
                            "value_description": f"默认测试值"
                        }
                        for param in endpoint.parameters if param.required
                    ],
                    "assertions": [
                        {
                            "assertion_type": "status_code",
                            "expected_value": "200",
                            "comparison_operator": "equals",
                            "description": "验证响应状态码为200"
                        }
                    ],
                    "setup_steps": [],
                    "cleanup_steps": [],
                    "priority": 1,
                    "tags": ["basic", "positive"]
                }
                test_cases.append(basic_case)
            
            return {
                "test_cases": test_cases,
                "confidence_score": 0.6,
                "generation_method": "fallback_basic"
            }
            
        except Exception as e:
            logger.error(f"备用测试用例生成失败: {str(e)}")
            return {"test_cases": [], "confidence_score": 0.3}

    def _generate_default_test_value(self, parameter):
        """生成默认测试值"""
        if parameter.example is not None:
            return parameter.example
        
        # 根据数据类型生成默认值
        type_defaults = {
            "string": "test_string",
            "integer": 1,
            "number": 1.0,
            "boolean": True,
            "array": [],
            "object": {}
        }
        
        return type_defaults.get(parameter.data_type.value, "test_value")

    async def _send_to_script_generator(
        self, 
        output: TestCaseGenerationOutput, 
        original_input: TestCaseGenerationInput,
        ctx: MessageContext
    ):
        """发送测试用例到脚本生成智能体"""
        try:
            from .schemas import ScriptGenerationInput
            
            # 构建脚本生成输入
            script_input = ScriptGenerationInput(
                session_id=output.session_id,
                document_id=output.document_id,
                api_info=original_input.api_info,
                endpoints=original_input.endpoints,
                test_cases=output.test_cases,
                execution_groups=original_input.execution_groups,
                generation_options={}
            )
            
            # 发送到脚本生成智能体
            await self.runtime.publish_message(
                script_input,
                topic_id=TopicId(type=TopicTypes.TEST_SCRIPT_GENERATOR.value, source=self.agent_name)
            )
            
            logger.info(f"已发送测试用例到脚本生成智能体: {output.document_id}")
            
        except Exception as e:
            logger.error(f"发送到脚本生成智能体失败: {str(e)}")

    def get_generation_statistics(self) -> Dict[str, Any]:
        """获取生成统计信息"""
        base_stats = self.get_common_statistics()
        base_stats.update({
            "generation_metrics": self.generation_metrics,
            "generation_config": self.generation_config,
            "avg_test_cases_per_generation": (
                self.generation_metrics["total_test_cases_generated"] / 
                max(self.generation_metrics["successful_generations"], 1)
            )
        })
        return base_stats
