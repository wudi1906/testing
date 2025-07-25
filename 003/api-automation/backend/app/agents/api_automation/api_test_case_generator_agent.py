"""
API测试用例生成智能体
专门负责基于接口分析结果生成专业化的测试用例
"""
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

from autogen_core import message_handler, type_subscription, MessageContext, TopicId
from loguru import logger
from pydantic import BaseModel, Field

from app.agents.api_automation.base_api_agent import BaseApiAutomationAgent
from app.core.types import AgentTypes, AGENT_NAMES, TopicTypes
from app.core.messages.api_automation import (
    DependencyAnalysisResponse, TestCaseGenerationRequest, TestCaseGenerationResponse,
    TestCaseInfo, ApiEndpointInfo, DependencyInfo, TestScriptGenerationRequest
)
from app.core.enums import TestType, Priority, TestLevel, HttpMethod, DependencyType


@type_subscription(topic_type=TopicTypes.API_TEST_CASE_GENERATOR.value)
class ApiTestCaseGeneratorAgent(BaseApiAutomationAgent):
    """
    API测试用例生成智能体

    核心功能：
    1. 基于接口分析结果生成专业化测试用例
    2. 智能分析业务场景并设计对应测试用例
    3. 生成多类型测试用例（功能、边界、异常、性能、安全）
    4. 智能优先级算法和覆盖度分析
    5. 生成高质量测试数据和断言规则
    6. 支持流式生成和实时反馈
    """

    def __init__(self, model_client_instance=None, agent_config=None, **kwargs):
        """初始化API测试用例生成智能体"""
        super().__init__(
            agent_type=AgentTypes.API_TEST_CASE_GENERATOR,
            model_client_instance=model_client_instance,
            **kwargs
        )

        # 存储智能体配置信息
        self.agent_config = agent_config or {}

        # 初始化AssistantAgent
        self._initialize_assistant_agent()

        # 测试用例生成统计（继承公共统计）
        self.test_case_metrics = {
            "total_requests": 0,
            "successful_generations": 0,
            "failed_generations": 0,
            "total_test_cases_generated": 0,
            "functional_cases": 0,
            "boundary_cases": 0,
            "exception_cases": 0,
            "performance_cases": 0,
            "security_cases": 0
        }

        # 测试用例生成配置
        self.generation_config = {
            "enable_functional_tests": True,
            "enable_boundary_tests": True,
            "enable_exception_tests": True,
            "enable_performance_tests": True,
            "enable_security_tests": True,
            "max_cases_per_endpoint": 20,
            "coverage_threshold": 0.8
        }

        logger.info(f"API测试用例生成智能体初始化完成: {self.agent_name}")

    @message_handler
    async def handle_dependency_analysis_response(
        self, 
        message: DependencyAnalysisResponse, 
        ctx: MessageContext
    ) -> None:
        """处理依赖分析响应，生成测试用例"""
        start_time = datetime.now()
        self.test_case_metrics["total_requests"] += 1
        
        try:
            logger.info(f"开始生成API测试用例: {message.doc_id}")
            
            # 使用大模型智能生成测试用例
            test_cases = await self._intelligent_generate_test_cases(
                message.endpoints,
                message.dependencies,
                message.analysis_result,
                message.session_id
            )

            # 分析测试覆盖度
            coverage_analysis = await self._analyze_test_coverage(
                test_cases,
                message.endpoints
            )

            # 优化测试用例优先级
            optimized_cases = await self._optimize_test_case_priority(
                test_cases,
                message.dependencies,
                coverage_analysis
            )

            # 构建响应
            response = TestCaseGenerationResponse(
                session_id=message.session_id,
                doc_id=message.doc_id,
                test_cases=optimized_cases,
                coverage_analysis=coverage_analysis,
                generation_summary={
                    "total_test_cases": len(optimized_cases),
                    "functional_cases": len([c for c in optimized_cases if c.test_type == TestType.FUNCTIONAL]),
                    "boundary_cases": len([c for c in optimized_cases if c.test_type == TestType.BOUNDARY]),
                    "exception_cases": len([c for c in optimized_cases if c.test_type == TestType.EXCEPTION]),
                    "performance_cases": len([c for c in optimized_cases if c.test_type == TestType.PERFORMANCE]),
                    "security_cases": len([c for c in optimized_cases if c.test_type == TestType.SECURITY]),
                    "coverage_score": coverage_analysis.get("overall_coverage", 0.0),
                    "generation_time": (datetime.now() - start_time).total_seconds()
                },
                processing_time=(datetime.now() - start_time).total_seconds()
            )
            
            # 更新统计
            self._update_generation_metrics(optimized_cases)
            
            logger.info(f"API测试用例生成完成: {message.doc_id}, 生成了 {len(optimized_cases)} 个测试用例")
            
            # 发送到测试脚本生成智能体
            await self._send_to_script_generator(response)
            
        except Exception as e:
            self.test_case_metrics["failed_generations"] += 1
            logger.error(f"API测试用例生成失败: {str(e)}")
            
            # 发送错误响应
            await self._send_error_response(message, str(e))

    async def _intelligent_generate_test_cases(
        self,
        endpoints: List[ApiEndpointInfo],
        dependencies: List[DependencyInfo],
        analysis_result: Dict[str, Any],
        session_id: str
    ) -> List[TestCaseInfo]:
        """使用大模型智能生成测试用例"""
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
                    "auth_required": endpoint.auth_required,
                    "security_level": getattr(endpoint, 'security_level', 'medium')
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

            # 构建测试用例生成任务
            endpoints_json = json.dumps(endpoints_data, ensure_ascii=False, indent=2)
            dependencies_json = json.dumps(dependencies_data, ensure_ascii=False, indent=2)
            analysis_json = json.dumps(analysis_result, ensure_ascii=False, indent=2)

            task = "请基于以下API分析结果生成专业化的测试用例：\n\n"
            task += "## API端点信息\n"
            task += endpoints_json + "\n\n"
            task += "## 依赖关系分析\n"
            task += dependencies_json + "\n\n"
            task += "## 接口分析结果\n"
            task += analysis_json + "\n\n"

            task += """## 测试用例生成要求

请为每个API端点生成以下类型的测试用例：

### 1. 功能测试用例 (Functional Tests)
- **正常场景**: 使用有效参数的标准业务流程测试
- **业务逻辑**: 基于API的实际业务场景设计测试
- **数据流转**: 验证数据的正确传递和处理

### 2. 边界值测试用例 (Boundary Tests)
- **参数边界**: 最大值、最小值、临界值测试
- **数据长度**: 字符串长度、数组大小的边界测试
- **数值范围**: 整数、浮点数的边界值测试

### 3. 异常测试用例 (Exception Tests)
- **无效参数**: 错误类型、格式不正确的参数
- **缺失参数**: 必需参数缺失的场景
- **权限测试**: 无权限访问、权限不足的场景
- **服务异常**: 模拟服务不可用、超时等异常

### 4. 性能测试用例 (Performance Tests)
- **响应时间**: 验证API响应时间在合理范围内
- **并发测试**: 多用户同时访问的场景
- **大数据量**: 处理大量数据时的性能表现

### 5. 安全测试用例 (Security Tests)
- **SQL注入**: 在参数中注入SQL代码
- **XSS攻击**: 跨站脚本攻击测试
- **认证绕过**: 尝试绕过认证机制
- **敏感数据**: 验证敏感信息不会泄露

## 输出格式要求

请严格按照JSON格式输出测试用例数据。

请确保：
1. 每个端点至少有5-10个不同类型的测试用例
2. 测试数据真实有效，符合业务逻辑
3. 断言规则完整准确
4. 优先级设置合理
5. 考虑接口间的依赖关系

严格按照JSON格式输出结果。"""

            # 使用AssistantAgent进行智能生成
            result_content = await self._run_assistant_agent(task)

            # 解析大模型返回的结果
            if result_content:
                generation_result = self._extract_json_from_content(result_content)
                if generation_result and "test_cases" in generation_result:
                    return self._convert_to_test_case_objects(generation_result["test_cases"])

            # 如果大模型生成失败，使用备用方法
            logger.warning("大模型生成失败，使用备用生成方法")
            return await self._fallback_generate_test_cases(endpoints, dependencies)

        except Exception as e:
            logger.error(f"智能生成测试用例失败: {str(e)}")
            return await self._fallback_generate_test_cases(endpoints, dependencies)

    def _convert_to_test_case_objects(self, test_cases_data: List[Dict[str, Any]]) -> List[TestCaseInfo]:
        """将生成的测试用例数据转换为TestCaseInfo对象"""
        test_cases = []

        try:
            for case_data in test_cases_data:
                # 创建端点信息
                endpoint = ApiEndpointInfo(
                    path=case_data.get("endpoint_path", "/unknown"),
                    method=HttpMethod(case_data.get("endpoint_method", "GET")),
                    summary=case_data.get("name", ""),
                    description=case_data.get("description", "")
                )

                # 转换测试类型
                test_type_map = {
                    "functional": TestType.FUNCTIONAL,
                    "boundary": TestType.BOUNDARY,
                    "exception": TestType.EXCEPTION,
                    "performance": TestType.PERFORMANCE,
                    "security": TestType.SECURITY
                }
                test_type = test_type_map.get(case_data.get("test_type", "functional"), TestType.FUNCTIONAL)

                # 转换测试级别
                test_level_map = {
                    "unit": TestLevel.UNIT,
                    "integration": TestLevel.INTEGRATION,
                    "api": TestLevel.API,
                    "system": TestLevel.SYSTEM
                }
                test_level = test_level_map.get(case_data.get("test_level", "api"), TestLevel.API)

                # 转换优先级
                priority_map = {
                    "high": Priority.HIGH,
                    "medium": Priority.MEDIUM,
                    "low": Priority.LOW
                }
                priority = priority_map.get(case_data.get("priority", "medium"), Priority.MEDIUM)

                # 创建测试用例对象
                test_case = TestCaseInfo(
                    test_id=str(uuid.uuid4()),
                    name=case_data.get("name", ""),
                    description=case_data.get("description", ""),
                    endpoint=endpoint,
                    test_type=test_type,
                    test_level=test_level,
                    priority=priority,
                    test_data=case_data.get("test_data", []),
                    assertions=case_data.get("assertions", []),
                    setup_steps=case_data.get("setup_steps", []),
                    teardown_steps=case_data.get("teardown_steps", []),
                    tags=case_data.get("tags", [])
                )
                test_cases.append(test_case)

        except Exception as e:
            logger.error(f"转换测试用例对象失败: {str(e)}")

        return test_cases

    async def _analyze_test_coverage(
        self,
        test_cases: List[TestCaseInfo],
        endpoints: List[ApiEndpointInfo]
    ) -> Dict[str, Any]:
        """分析测试覆盖度"""
        try:
            # 端点覆盖度分析
            covered_endpoints = set()
            for test_case in test_cases:
                covered_endpoints.add(f"{test_case.endpoint.method.value} {test_case.endpoint.path}")

            total_endpoints = len(endpoints)
            endpoint_coverage = len(covered_endpoints) / total_endpoints if total_endpoints > 0 else 0

            # 测试类型覆盖度分析
            test_type_counts = {}
            for test_case in test_cases:
                test_type = test_case.test_type.value
                test_type_counts[test_type] = test_type_counts.get(test_type, 0) + 1

            # HTTP方法覆盖度分析
            method_coverage = {}
            for endpoint in endpoints:
                method = endpoint.method.value
                method_coverage[method] = method_coverage.get(method, 0) + 1

            # 业务场景覆盖度分析
            business_scenarios = set()
            for test_case in test_cases:
                for tag in test_case.tags:
                    if tag.startswith("scenario:"):
                        business_scenarios.add(tag)

            # 计算整体覆盖度得分
            coverage_factors = [
                endpoint_coverage,
                min(len(test_type_counts) / 5, 1.0),  # 5种测试类型
                min(len(business_scenarios) / max(total_endpoints, 1), 1.0)
            ]
            overall_coverage = sum(coverage_factors) / len(coverage_factors)

            return {
                "overall_coverage": round(overall_coverage, 3),
                "endpoint_coverage": round(endpoint_coverage, 3),
                "covered_endpoints": len(covered_endpoints),
                "total_endpoints": total_endpoints,
                "test_type_distribution": test_type_counts,
                "method_coverage": method_coverage,
                "business_scenarios": list(business_scenarios),
                "coverage_details": {
                    "functional_coverage": test_type_counts.get("functional", 0) / len(test_cases) if test_cases else 0,
                    "boundary_coverage": test_type_counts.get("boundary", 0) / len(test_cases) if test_cases else 0,
                    "exception_coverage": test_type_counts.get("exception", 0) / len(test_cases) if test_cases else 0,
                    "performance_coverage": test_type_counts.get("performance", 0) / len(test_cases) if test_cases else 0,
                    "security_coverage": test_type_counts.get("security", 0) / len(test_cases) if test_cases else 0
                }
            }

        except Exception as e:
            logger.error(f"分析测试覆盖度失败: {str(e)}")
            return {
                "overall_coverage": 0.0,
                "endpoint_coverage": 0.0,
                "covered_endpoints": 0,
                "total_endpoints": len(endpoints),
                "test_type_distribution": {},
                "method_coverage": {},
                "business_scenarios": [],
                "coverage_details": {}
            }

    async def _optimize_test_case_priority(
        self,
        test_cases: List[TestCaseInfo],
        dependencies: List[DependencyInfo],
        coverage_analysis: Dict[str, Any]
    ) -> List[TestCaseInfo]:
        """优化测试用例优先级"""
        try:
            # 创建依赖图
            dependency_map = {}
            for dep in dependencies:
                if dep.target_test not in dependency_map:
                    dependency_map[dep.target_test] = []
                dependency_map[dep.target_test].append(dep.source_test)

            # 优先级评分算法
            for test_case in test_cases:
                score = 0

                # 基础优先级分数
                priority_scores = {
                    Priority.HIGH: 100,
                    Priority.MEDIUM: 50,
                    Priority.LOW: 25
                }
                score += priority_scores.get(test_case.priority, 50)

                # 测试类型权重
                type_weights = {
                    TestType.FUNCTIONAL: 30,
                    TestType.SECURITY: 25,
                    TestType.EXCEPTION: 20,
                    TestType.BOUNDARY: 15,
                    TestType.PERFORMANCE: 10
                }
                score += type_weights.get(test_case.test_type, 15)

                # 依赖关系权重（被依赖的测试用例优先级更高）
                endpoint_key = f"{test_case.endpoint.method.value} {test_case.endpoint.path}"
                if endpoint_key in dependency_map:
                    score += len(dependency_map[endpoint_key]) * 10

                # 业务重要性权重（基于标签）
                if "critical" in test_case.tags:
                    score += 50
                elif "important" in test_case.tags:
                    score += 25

                # 更新优先级
                if score >= 150:
                    test_case.priority = Priority.HIGH
                elif score >= 75:
                    test_case.priority = Priority.MEDIUM
                else:
                    test_case.priority = Priority.LOW

            # 按优先级排序
            priority_order = {Priority.HIGH: 3, Priority.MEDIUM: 2, Priority.LOW: 1}
            test_cases.sort(key=lambda x: priority_order.get(x.priority, 1), reverse=True)

            return test_cases

        except Exception as e:
            logger.error(f"优化测试用例优先级失败: {str(e)}")
            return test_cases

    async def _fallback_generate_test_cases(
        self,
        endpoints: List[ApiEndpointInfo],
        dependencies: List[DependencyInfo]
    ) -> List[TestCaseInfo]:
        """备用测试用例生成方法"""
        test_cases = []

        try:
            for endpoint in endpoints:
                # 为每个端点生成基础测试用例

                # 1. 功能测试用例
                functional_case = TestCaseInfo(
                    test_id=str(uuid.uuid4()),
                    name=f"test_{endpoint.path.replace('/', '_').replace('{', '').replace('}', '')}_success",
                    description=f"测试 {endpoint.method.value} {endpoint.path} 成功场景",
                    endpoint=endpoint,
                    test_type=TestType.FUNCTIONAL,
                    test_level=TestLevel.API,
                    priority=Priority.HIGH,
                    test_data=[{
                        "scenario": "正常请求",
                        "input": self._generate_valid_test_data(endpoint),
                        "expected_status": 200,
                        "expected_response": {"status": "success"}
                    }],
                    assertions=[{
                        "type": "status_code",
                        "field": "status_code",
                        "operator": "equals",
                        "expected": 200,
                        "description": "验证响应状态码为200"
                    }],
                    tags=["functional", "smoke"]
                )
                test_cases.append(functional_case)

                # 2. 异常测试用例
                exception_case = TestCaseInfo(
                    test_id=str(uuid.uuid4()),
                    name=f"test_{endpoint.path.replace('/', '_').replace('{', '').replace('}', '')}_invalid_params",
                    description=f"测试 {endpoint.method.value} {endpoint.path} 无效参数场景",
                    endpoint=endpoint,
                    test_type=TestType.EXCEPTION,
                    test_level=TestLevel.API,
                    priority=Priority.MEDIUM,
                    test_data=[{
                        "scenario": "无效参数",
                        "input": self._generate_invalid_test_data(endpoint),
                        "expected_status": 400,
                        "expected_response": {"error": "Invalid parameters"}
                    }],
                    assertions=[{
                        "type": "status_code",
                        "field": "status_code",
                        "operator": "equals",
                        "expected": 400,
                        "description": "验证响应状态码为400"
                    }],
                    tags=["exception", "negative"]
                )
                test_cases.append(exception_case)

                # 3. 边界值测试用例（如果有数值参数）
                if self._has_numeric_parameters(endpoint):
                    boundary_case = TestCaseInfo(
                        test_id=str(uuid.uuid4()),
                        name=f"test_{endpoint.path.replace('/', '_').replace('{', '').replace('}', '')}_boundary_values",
                        description=f"测试 {endpoint.method.value} {endpoint.path} 边界值场景",
                        endpoint=endpoint,
                        test_type=TestType.BOUNDARY,
                        test_level=TestLevel.API,
                        priority=Priority.MEDIUM,
                        test_data=[{
                            "scenario": "边界值测试",
                            "input": self._generate_boundary_test_data(endpoint),
                            "expected_status": 200,
                            "expected_response": {"status": "success"}
                        }],
                        assertions=[{
                            "type": "status_code",
                            "field": "status_code",
                            "operator": "equals",
                            "expected": 200,
                            "description": "验证边界值处理正确"
                        }],
                        tags=["boundary", "edge_case"]
                    )
                    test_cases.append(boundary_case)

        except Exception as e:
            logger.error(f"备用测试用例生成失败: {str(e)}")

        return test_cases

    def _generate_valid_test_data(self, endpoint: ApiEndpointInfo) -> Dict[str, Any]:
        """生成有效的测试数据"""
        test_data = {}

        # 基于参数生成测试数据
        for param in endpoint.parameters:
            param_name = param.get("name", "")
            param_type = param.get("type", "string")

            if param_type == "string":
                test_data[param_name] = "test_value"
            elif param_type == "integer":
                test_data[param_name] = 123
            elif param_type == "boolean":
                test_data[param_name] = True
            elif param_type == "array":
                test_data[param_name] = ["item1", "item2"]
            else:
                test_data[param_name] = "default_value"

        return test_data

    def _generate_invalid_test_data(self, endpoint: ApiEndpointInfo) -> Dict[str, Any]:
        """生成无效的测试数据"""
        test_data = {}

        # 基于参数生成无效测试数据
        for param in endpoint.parameters:
            param_name = param.get("name", "")
            param_type = param.get("type", "string")

            if param_type == "string":
                test_data[param_name] = 123  # 类型错误
            elif param_type == "integer":
                test_data[param_name] = "not_a_number"  # 类型错误
            elif param_type == "boolean":
                test_data[param_name] = "not_boolean"  # 类型错误
            elif param_type == "array":
                test_data[param_name] = "not_array"  # 类型错误
            else:
                test_data[param_name] = None  # 空值

        return test_data

    def _generate_boundary_test_data(self, endpoint: ApiEndpointInfo) -> Dict[str, Any]:
        """生成边界值测试数据"""
        test_data = {}

        # 基于参数生成边界值测试数据
        for param in endpoint.parameters:
            param_name = param.get("name", "")
            param_type = param.get("type", "string")

            if param_type == "integer":
                # 使用最大整数值
                test_data[param_name] = 2147483647
            elif param_type == "string":
                # 使用长字符串
                test_data[param_name] = "a" * 1000
            elif param_type == "array":
                # 使用大数组
                test_data[param_name] = ["item"] * 100
            else:
                test_data[param_name] = "boundary_value"

        return test_data

    def _has_numeric_parameters(self, endpoint: ApiEndpointInfo) -> bool:
        """检查端点是否有数值参数"""
        for param in endpoint.parameters:
            param_type = param.get("type", "")
            if param_type in ["integer", "number", "float"]:
                return True
        return False

    def _update_generation_metrics(self, test_cases: List[TestCaseInfo]):
        """更新生成统计指标"""
        self.test_case_metrics["successful_generations"] += 1
        self.test_case_metrics["total_test_cases_generated"] += len(test_cases)

        for test_case in test_cases:
            test_type = test_case.test_type.value
            if test_type == "functional":
                self.test_case_metrics["functional_cases"] += 1
            elif test_type == "boundary":
                self.test_case_metrics["boundary_cases"] += 1
            elif test_type == "exception":
                self.test_case_metrics["exception_cases"] += 1
            elif test_type == "performance":
                self.test_case_metrics["performance_cases"] += 1
            elif test_type == "security":
                self.test_case_metrics["security_cases"] += 1

    async def _send_to_script_generator(self, response: TestCaseGenerationResponse):
        """发送测试用例到脚本生成智能体"""
        try:
            # 构建测试脚本生成请求
            script_request = TestScriptGenerationRequest(
                session_id=response.session_id,
                doc_id=response.doc_id,
                endpoints=[case.endpoint for case in response.test_cases],
                dependencies=[],  # 依赖关系已在测试用例中处理
                test_config={
                    "framework": "pytest",
                    "include_allure": True,
                    "include_data_driven": True,
                    "test_cases": [case.dict() for case in response.test_cases]
                }
            )

            # 发送到测试脚本生成智能体
            await self.runtime.publish_message(
                script_request,
                topic_id=TopicId(type=TopicTypes.TEST_SCRIPT_GENERATOR.value, source=self.agent_name)
            )

            logger.info(f"已发送测试用例到脚本生成智能体: {response.session_id}")

        except Exception as e:
            logger.error(f"发送到脚本生成智能体失败: {str(e)}")

    async def _send_error_response(self, original_message, error_message: str):
        """发送错误响应"""
        try:
            error_response = TestCaseGenerationResponse(
                session_id=original_message.session_id,
                doc_id=original_message.doc_id,
                test_cases=[],
                coverage_analysis={"overall_coverage": 0.0},
                generation_summary={"error": error_message},
                processing_time=0.0
            )

            # 这里可以发送错误通知或记录日志
            logger.error(f"测试用例生成错误响应: {error_message}")

        except Exception as e:
            logger.error(f"发送错误响应失败: {str(e)}")

    def get_generation_statistics(self) -> Dict[str, Any]:
        """获取测试用例生成统计信息"""
        # 获取公共统计信息
        common_stats = super().get_common_statistics()

        # 计算成功率
        total_requests = self.test_case_metrics["total_requests"]
        success_rate = (
            (self.test_case_metrics["successful_generations"] / total_requests * 100)
            if total_requests > 0 else 0
        )

        # 计算平均每次生成的测试用例数
        successful_generations = self.test_case_metrics["successful_generations"]
        avg_cases_per_generation = (
            (self.test_case_metrics["total_test_cases_generated"] / successful_generations)
            if successful_generations > 0 else 0
        )

        # 合并统计信息
        return {
            **common_stats,
            "generation_metrics": self.test_case_metrics,
            "generation_success_rate": round(success_rate, 2),
            "avg_cases_per_generation": round(avg_cases_per_generation, 2),
            "generation_config": self.generation_config
        }
