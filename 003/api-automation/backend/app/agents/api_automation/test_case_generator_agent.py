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
            logger.info(f"开始生成测试用例: document_id={message.document_id}, interface_id={getattr(message, 'interface_id', None)}, 端点数量: {len(message.endpoints)}")

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
                interface_id=getattr(message, 'interface_id', None),  # 传递interface_id
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
            await self._send_to_script_generator(output, message)

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

            # 清理和预处理响应内容
            cleaned_content = self._clean_json_content(result_content)

            # 解析JSON
            parsed_data = json.loads(cleaned_content)
            return parsed_data
            # if result_content:
            #     # 添加调试日志
            #     logger.info(f"AI返回内容长度: {len(result_content)}")
            #     logger.info(f"AI返回内容前200字符: {result_content[:200]}")
            #     logger.info(f"AI返回内容后200字符: {result_content[-200:]}")
            #
            #     # 首先尝试提取JSON结果
            #     parsed_data = self._extract_json_from_content(result_content)
            #     if parsed_data:
            #         logger.info(f"JSON提取成功，结果类型: {type(parsed_data)}")
            #         if isinstance(parsed_data, dict):
            #             logger.info(f"JSON顶级键: {list(parsed_data.keys())}")
            #             if "test_cases" in parsed_data:
            #                 logger.info(f"包含test_cases数组，长度: {len(parsed_data['test_cases'])}")
            #             else:
            #                 logger.warning("JSON结果中缺少test_cases键，可能只提取了部分内容")
            #         return parsed_data
            #     else:
            #         logger.warning("JSON提取失败，内容可能不是有效的JSON格式")
            #
            #     # 如果JSON提取失败，尝试智能解析文档格式
            #     logger.info("JSON提取失败，尝试智能解析文档格式")
            #     parsed_data = await self._parse_document_format_response(result_content, endpoints)
            #     if parsed_data:
            #         return parsed_data

        except Exception as e:
            logger.error(f"智能测试用例生成失败: {str(e)}")
            raise

    def _clean_json_content(self, content: str) -> str:
        """清理和预处理JSON内容，移除无效的JavaScript表达式"""
        try:
            import re

            # 移除markdown标记
            content = content.replace("```json\n", "").replace("```", "").strip()

            # 查找并替换JavaScript表达式模式
            # 匹配类似 "a".repeat(320) + "@example.com" 的模式
            js_repeat_pattern = r'"([a-zA-Z])"\s*\.\s*repeat\s*\(\s*(\d+)\s*\)\s*\+\s*"([^"]*)"'

            def replace_js_repeat(match):
                char = match.group(1)
                count = int(match.group(2))
                suffix = match.group(3)
                # 生成实际的字符串，但限制长度避免过长
                max_length = min(count, 500)  # 限制最大长度为500字符
                result = char * max_length + suffix
                return f'"{result}"'

            content = re.sub(js_repeat_pattern, replace_js_repeat, content)

            # 查找并替换其他可能的JavaScript表达式
            # 匹配类似 "string".repeat(n) 的模式
            simple_repeat_pattern = r'"([^"]+)"\s*\.\s*repeat\s*\(\s*(\d+)\s*\)'

            def replace_simple_repeat(match):
                string = match.group(1)
                count = int(match.group(2))
                # 限制重复次数避免过长
                max_count = min(count, 100)
                result = string * max_count
                return f'"{result}"'

            content = re.sub(simple_repeat_pattern, replace_simple_repeat, content)

            # 移除可能的函数调用
            function_call_pattern = r'[a-zA-Z_][a-zA-Z0-9_]*\s*\([^)]*\)'
            # 但要小心不要移除JSON中的正常内容，只在字符串值中查找

            logger.debug(f"JSON内容清理完成，长度: {len(content)}")
            return content

        except Exception as e:
            logger.warning(f"JSON内容清理失败: {str(e)}")
            # 如果清理失败，返回基本清理的内容
            return content.replace("```json\n", "").replace("```", "").strip()

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
        """生成增强的覆盖度报告"""
        total_endpoints = len(endpoints)
        covered_endpoint_ids = set(tc.endpoint_id for tc in test_cases)
        covered_endpoints = len(covered_endpoint_ids)

        # 按测试类型统计
        type_coverage = {}
        for test_type in TestCaseType:
            type_cases = [tc for tc in test_cases if tc.test_type == test_type]
            type_coverage[test_type.value] = {
                "count": len(type_cases),
                "endpoints_covered": len(set(tc.endpoint_id for tc in type_cases)),
                "percentage": (len(set(tc.endpoint_id for tc in type_cases)) / total_endpoints * 100) if total_endpoints > 0 else 0
            }

        # 按HTTP方法统计
        method_coverage = {}
        for endpoint in endpoints:
            method = endpoint.method.value
            if method not in method_coverage:
                method_coverage[method] = {"total": 0, "covered": 0}
            method_coverage[method]["total"] += 1
            if endpoint.endpoint_id in covered_endpoint_ids:
                method_coverage[method]["covered"] += 1

        # 计算每个方法的覆盖率
        for method in method_coverage:
            total = method_coverage[method]["total"]
            covered = method_coverage[method]["covered"]
            method_coverage[method]["percentage"] = (covered / total * 100) if total > 0 else 0

        # 未覆盖的端点详情
        uncovered_endpoints = []
        for ep in endpoints:
            if ep.endpoint_id not in covered_endpoint_ids:
                uncovered_endpoints.append({
                    "endpoint_id": ep.endpoint_id,
                    "method": ep.method.value,
                    "path": ep.path,
                    "summary": ep.summary
                })

        return {
            "total_endpoints": total_endpoints,
            "covered_endpoints": covered_endpoints,
            "coverage_percentage": (covered_endpoints / total_endpoints * 100) if total_endpoints > 0 else 0,
            "total_test_cases": len(test_cases),
            "test_cases_by_type": type_coverage,
            "method_coverage": method_coverage,
            "uncovered_endpoints": uncovered_endpoints,
            "quality_metrics": {
                "avg_test_cases_per_endpoint": len(test_cases) / total_endpoints if total_endpoints > 0 else 0,
                "avg_assertions_per_case": sum(len(tc.assertions) for tc in test_cases) / len(test_cases) if test_cases else 0,
                "endpoints_with_multiple_test_types": len([
                    ep_id for ep_id in covered_endpoint_ids
                    if len(set(tc.test_type for tc in test_cases if tc.endpoint_id == ep_id)) > 1
                ])
            }
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

    async def _parse_document_format_response(
        self,
        content: str,
        endpoints: List[ParsedEndpoint]
    ) -> Dict[str, Any]:
        """智能解析文档格式的响应内容"""
        try:
            import re

            test_cases = []

            # 解析测试用例标题和内容
            # 匹配类似 "**FT-001: 有效凭证登录成功**" 的模式
            test_case_pattern = r'\*\*([^*]+)\*\*\s*\n-\s*\*\*描述\*\*:\s*([^\n]+)'
            test_case_matches = re.findall(test_case_pattern, content)

            for i, (title, description) in enumerate(test_case_matches):
                # 提取测试用例ID和名称
                title_parts = title.split(':', 1)
                test_id = title_parts[0].strip() if len(title_parts) > 1 else f"TC_{i+1:03d}"
                test_name = title_parts[1].strip() if len(title_parts) > 1 else title.strip()

                # 确定测试类型
                test_type = self._determine_test_type_from_content(test_id, test_name, description)

                # 查找对应的端点
                endpoint_id = self._find_matching_endpoint(content, endpoints)

                # 提取测试数据
                test_data = self._extract_test_data_from_section(content, test_id)

                # 生成基本断言
                assertions = self._generate_basic_assertions(test_type)

                test_case = {
                    "test_name": test_name,
                    "endpoint_id": endpoint_id,
                    "test_type": test_type,
                    "description": description,
                    "test_data": test_data,
                    "assertions": assertions,
                    "setup_steps": [],
                    "cleanup_steps": [],
                    "priority": self._determine_priority_from_type(test_type),
                    "tags": self._generate_tags_from_type(test_type)
                }

                test_cases.append(test_case)

            # 如果没有找到结构化的测试用例，生成基础测试用例
            if not test_cases:
                test_cases = self._generate_basic_test_cases_from_content(content, endpoints)

            return {
                "test_cases": test_cases,
                "generation_method": "document_parsing",
                "confidence_score": 0.7
            }

        except Exception as e:
            logger.error(f"解析文档格式失败: {str(e)}")
            return None

    def _determine_test_type_from_content(self, test_id: str, test_name: str, description: str) -> str:
        """从内容确定测试类型"""
        content_lower = f"{test_id} {test_name} {description}".lower()

        if any(keyword in content_lower for keyword in ['错误', '异常', '失败', 'error', 'invalid', 'wrong']):
            return "negative"
        elif any(keyword in content_lower for keyword in ['边界', '最大', '最小', 'boundary', 'max', 'min', 'limit']):
            return "boundary"
        elif any(keyword in content_lower for keyword in ['安全', '注入', '攻击', 'security', 'injection', 'attack']):
            return "security"
        elif any(keyword in content_lower for keyword in ['性能', '并发', '负载', 'performance', 'load', 'concurrent']):
            return "performance"
        else:
            return "positive"

    def _find_matching_endpoint(self, content: str, endpoints: List[ParsedEndpoint]) -> str:
        """查找匹配的端点ID"""
        if not endpoints:
            return "unknown_endpoint"

        # 在内容中查找端点路径
        for endpoint in endpoints:
            if endpoint.path in content:
                return endpoint.endpoint_id

        # 默认返回第一个端点
        return endpoints[0].endpoint_id

    def _extract_test_data_from_section(self, content: str, test_id: str) -> List[Dict[str, Any]]:
        """从内容段落中提取测试数据"""
        import re

        test_data = []

        # 查找JSON格式的请求体
        json_pattern = r'"([^"]+)":\s*"([^"]+)"'
        json_matches = re.findall(json_pattern, content)

        for param_name, param_value in json_matches:
            if param_name in ['email', 'password', 'username', 'phone', 'name']:
                test_data.append({
                    "parameter_name": param_name,
                    "test_value": param_value,
                    "value_description": f"测试用例 {test_id} 的 {param_name} 参数"
                })

        return test_data

    def _generate_basic_assertions(self, test_type: str) -> List[Dict[str, Any]]:
        """生成基本断言"""
        assertions = [
            {
                "assertion_type": "status_code",
                "expected_value": "200" if test_type == "positive" else "400",
                "comparison_operator": "equals",
                "description": f"验证{test_type}测试的状态码"
            }
        ]

        if test_type == "positive":
            assertions.append({
                "assertion_type": "response_body",
                "expected_value": "success",
                "comparison_operator": "contains",
                "description": "验证响应包含成功标识"
            })

        return assertions

    def _determine_priority_from_type(self, test_type: str) -> int:
        """根据测试类型确定优先级"""
        priority_map = {
            "positive": 1,
            "negative": 2,
            "boundary": 3,
            "security": 2,
            "performance": 4
        }
        return priority_map.get(test_type, 3)

    def _generate_tags_from_type(self, test_type: str) -> List[str]:
        """根据测试类型生成标签"""
        base_tags = [test_type]

        if test_type == "positive":
            base_tags.append("smoke")
        elif test_type == "security":
            base_tags.extend(["security", "critical"])
        elif test_type == "performance":
            base_tags.extend(["performance", "load"])

        return base_tags

    def _generate_basic_test_cases_from_content(
        self,
        content: str,
        endpoints: List[ParsedEndpoint]
    ) -> List[Dict[str, Any]]:
        """从内容生成基础测试用例"""
        test_cases = []

        for endpoint in endpoints:
            # 为每个端点生成一个基本的正向测试用例
            test_case = {
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
            test_cases.append(test_case)

        return test_cases

    async def _send_to_script_generator(
        self,
        output: TestCaseGenerationOutput,
        original_input: TestCaseGenerationInput,
    ):
        """发送测试用例到脚本生成智能体"""
        try:
            from .schemas import ScriptGenerationInput

            # 构建增强的生成选项
            enhanced_generation_options = {
                **original_input.generation_options,
                "test_case_count": len(output.test_cases),
                "coverage_percentage": output.coverage_report.get("coverage_percentage", 0),
                "generation_method": output.generation_summary.get("generation_method", "intelligent"),
                "confidence_score": output.generation_summary.get("confidence_score", 0.8),
                "test_types_distribution": output.generation_summary.get("test_case_distribution", {}),
                "generation_config": self.generation_config
            }

            # 构建脚本生成输入 - 修复数据传输问题
            script_input = ScriptGenerationInput(
                session_id=output.session_id,
                document_id=output.document_id,
                interface_id=output.interface_id,  # 使用输出中的interface_id
                api_info=original_input.api_info,
                endpoints=original_input.endpoints,
                test_cases=output.test_cases,
                dependencies=original_input.dependencies,  # 修复：传递依赖关系
                execution_groups=original_input.execution_groups,
                generation_options=enhanced_generation_options  # 修复：传递增强的生成选项
            )

            # 发送到脚本生成智能体
            await self.runtime.publish_message(
                script_input,
                topic_id=TopicId(type=TopicTypes.TEST_SCRIPT_GENERATOR.value, source=self.agent_name)
            )

            logger.info(
                f"已发送测试用例到脚本生成智能体: {output.document_id}, "
                f"测试用例数: {len(output.test_cases)}, "
                f"覆盖率: {output.coverage_report.get('coverage_percentage', 0):.1f}%"
            )

        except Exception as e:
            logger.error(f"发送到脚本生成智能体失败: {str(e)}")
            # 记录详细错误信息用于调试
            logger.debug(f"发送失败的详细信息 - session_id: {output.session_id}, "
                        f"document_id: {output.document_id}, "
                        f"test_cases_count: {len(output.test_cases)}")

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
