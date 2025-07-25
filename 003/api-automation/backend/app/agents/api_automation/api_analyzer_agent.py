"""
接口分析智能体
基于公共基类实现，使用大模型进行全面的API接口分析
"""
import uuid
import json
from typing import Dict, List, Any, Optional
from datetime import datetime

from autogen_core import message_handler, type_subscription, MessageContext, TopicId
from loguru import logger
from pydantic import BaseModel, Field

from app.agents.api_automation.base_api_agent import BaseApiAutomationAgent
from app.core.types import AgentTypes, TopicTypes
from app.core.messages.api_automation import (
    DependencyAnalysisRequest, DependencyAnalysisResponse,
    ApiEndpointInfo, DependencyInfo
)
from app.core.enums import DependencyType, HttpMethod


@type_subscription(topic_type=TopicTypes.API_ANALYZER.value)
class ApiAnalyzerAgent(BaseApiAutomationAgent):
    """
    接口分析智能体

    核心功能：
    1. 使用大模型深度分析API接口的参数和响应
    2. 智能识别接口之间的依赖关系
    3. 评估安全性和性能
    4. 生成专业的测试策略建议
    5. 支持流式分析和实时反馈
    """

    def __init__(self, model_client_instance=None, agent_config=None, **kwargs):
        """初始化接口分析智能体"""
        super().__init__(
            agent_type=AgentTypes.API_ANALYZER,
            model_client_instance=model_client_instance,
            **kwargs
        )

        # 存储智能体配置信息
        self.agent_config = agent_config or {}

        # 初始化AssistantAgent
        self._initialize_assistant_agent()

        # 分析统计（继承公共统计）
        self.analysis_metrics = {
            "total_requests": 0,
            "successful_analyses": 0,
            "failed_analyses": 0,
            "total_endpoints_analyzed": 0,
            "dependencies_identified": 0
        }

        logger.info(f"接口分析智能体初始化完成: {self.agent_name}")



    @message_handler
    async def handle_dependency_analysis_request(
        self, 
        message: DependencyAnalysisRequest, 
        ctx: MessageContext
    ) -> None:
        """处理接口分析请求"""
        start_time = datetime.now()
        self.analysis_metrics["total_requests"] += 1
        
        try:
            logger.info(f"开始分析API接口: {message.doc_id}")
            
            # 使用大模型智能分析接口依赖关系
            analysis_result = await self._intelligent_analyze_dependencies(message.endpoints)

            # 提取依赖关系
            dependencies = self._extract_dependencies_from_analysis(analysis_result)

            # 确定执行顺序
            execution_order = analysis_result.get("execution_order", [])

            # 构建依赖图
            dependency_graph = self._build_dependency_graph(dependencies)
            
            # 构建响应
            response = DependencyAnalysisResponse(
                session_id=message.session_id,
                doc_id=message.doc_id,
                dependencies=dependencies,
                execution_order=execution_order,
                dependency_graph=dependency_graph,
                analysis_summary={
                    "total_endpoints": len(message.endpoints),
                    "dependencies_found": len(dependencies),
                    "analysis_time": (datetime.now() - start_time).total_seconds()
                },
                processing_time=(datetime.now() - start_time).total_seconds()
            )
            
            # 更新统计
            self.analysis_metrics["successful_analyses"] += 1
            self.analysis_metrics["total_endpoints_analyzed"] += len(message.endpoints)
            self.analysis_metrics["dependencies_identified"] += len(dependencies)
            
            logger.info(f"接口分析完成: {message.doc_id}, 发现 {len(dependencies)} 个依赖关系")
            
            # 发送到测试脚本生成智能体
            await self._send_to_test_generator(response)
            
        except Exception as e:
            self.analysis_metrics["failed_analyses"] += 1
            logger.error(f"接口分析失败: {str(e)}")
            
            # 发送错误响应
            await self._send_error_response(message, str(e))

    async def _intelligent_analyze_dependencies(self, endpoints: List[ApiEndpointInfo]) -> Dict[str, Any]:
        """使用大模型智能分析接口依赖关系"""
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

            # 构建分析任务
            task = f"""请对以下API接口进行全面的专业分析：

## API接口列表
{json.dumps(endpoints_data, ensure_ascii=False, indent=2)}

## 分析要求
请从以下维度进行深度分析：

1. **依赖关系识别**
   - 数据依赖：哪些接口需要其他接口的数据
   - 认证依赖：哪些接口需要先进行认证
   - 业务流程依赖：接口的调用顺序
   - 循环依赖检测

2. **执行顺序确定**
   - 基于依赖关系确定最优的测试执行顺序
   - 考虑并行执行的可能性
   - 识别关键路径

3. **质量评估**
   - 接口设计质量
   - 安全性评估
   - 性能考虑
   - 改进建议

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
            return await self._fallback_analyze_dependencies(endpoints)

        except Exception as e:
            logger.error(f"智能分析依赖关系失败: {str(e)}")
            return await self._fallback_analyze_dependencies(endpoints)



    def _extract_dependencies_from_analysis(self, analysis_result: Dict[str, Any]) -> List[DependencyInfo]:
        """从分析结果中提取依赖关系"""
        dependencies = []

        try:
            for dep_data in analysis_result.get("dependencies", []):
                dependency = DependencyInfo(
                    dependency_id=str(uuid.uuid4()),
                    dependency_type=DependencyType.DATA_DEPENDENCY,  # 默认类型，可以根据type字段调整
                    source_test=dep_data.get("source", ""),
                    target_test=dep_data.get("target", ""),
                    is_required=dep_data.get("required", True),
                    description=dep_data.get("description", ""),
                    dependency_data={
                        "confidence": dep_data.get("confidence", 0.8),
                        "type": dep_data.get("type", "data_dependency")
                    }
                )
                dependencies.append(dependency)

        except Exception as e:
            logger.error(f"提取依赖关系失败: {str(e)}")

        return dependencies

    async def _fallback_analyze_dependencies(self, endpoints: List[ApiEndpointInfo]) -> Dict[str, Any]:
        """备用分析方法"""
        try:
            dependencies = []

            # 按HTTP方法分组
            create_endpoints = [ep for ep in endpoints if ep.method == HttpMethod.POST]
            read_endpoints = [ep for ep in endpoints if ep.method == HttpMethod.GET]
            update_endpoints = [ep for ep in endpoints if ep.method in [HttpMethod.PUT, HttpMethod.PATCH]]
            delete_endpoints = [ep for ep in endpoints if ep.method == HttpMethod.DELETE]

            # 分析CRUD依赖关系
            dependencies.extend(self._analyze_crud_dependencies(create_endpoints, read_endpoints))
            dependencies.extend(self._analyze_crud_dependencies(create_endpoints, update_endpoints))
            dependencies.extend(self._analyze_crud_dependencies(create_endpoints, delete_endpoints))

            # 分析认证依赖
            dependencies.extend(self._analyze_auth_dependencies(endpoints))

            # 简单的执行顺序
            execution_order = []
            for ep in create_endpoints + read_endpoints + update_endpoints + delete_endpoints:
                execution_order.append(f"{ep.method.value} {ep.path}")

            return {
                "dependencies": [
                    {
                        "source": dep["source"],
                        "target": dep["target"],
                        "type": "data_dependency",
                        "description": dep["description"],
                        "required": dep["required"]
                    }
                    for dep in dependencies
                ],
                "execution_order": execution_order,
                "analysis_summary": {
                    "total_endpoints": len(endpoints),
                    "dependencies_found": len(dependencies),
                    "security_issues": 0,
                    "performance_concerns": 0,
                    "recommendations": ["使用大模型进行更详细的分析"]
                }
            }

        except Exception as e:
            logger.error(f"备用分析失败: {str(e)}")
            return {
                "dependencies": [],
                "execution_order": [],
                "analysis_summary": {
                    "total_endpoints": len(endpoints),
                    "dependencies_found": 0,
                    "recommendations": []
                }
            }

    def _analyze_crud_dependencies(
        self, 
        source_endpoints: List[ApiEndpointInfo], 
        target_endpoints: List[ApiEndpointInfo]
    ) -> List[DependencyInfo]:
        """分析CRUD操作依赖"""
        dependencies = []
        
        for source_ep in source_endpoints:
            for target_ep in target_endpoints:
                # 检查路径相似性
                if self._paths_related(source_ep.path, target_ep.path):
                    dependency = DependencyInfo(
                        dependency_id=str(uuid.uuid4()),
                        dependency_type=DependencyType.DATA_DEPENDENCY,
                        source_test=f"{source_ep.method.value} {source_ep.path}",
                        target_test=f"{target_ep.method.value} {target_ep.path}",
                        is_required=True,
                        description=f"数据依赖: {source_ep.summary} -> {target_ep.summary}",
                        dependency_data={
                            "source_endpoint": source_ep.path,
                            "target_endpoint": target_ep.path,
                            "relationship_type": "crud"
                        }
                    )
                    dependencies.append(dependency)
        
        return dependencies

    def _analyze_auth_dependencies(self, endpoints: List[ApiEndpointInfo]) -> List[DependencyInfo]:
        """分析认证依赖"""
        dependencies = []
        
        # 查找认证端点
        auth_endpoints = [ep for ep in endpoints if self._is_auth_endpoint(ep)]
        protected_endpoints = [ep for ep in endpoints if ep.auth_required and not self._is_auth_endpoint(ep)]
        
        for auth_ep in auth_endpoints:
            for protected_ep in protected_endpoints:
                dependency = DependencyInfo(
                    dependency_id=str(uuid.uuid4()),
                    dependency_type=DependencyType.AUTH_DEPENDENCY,
                    source_test=f"{auth_ep.method.value} {auth_ep.path}",
                    target_test=f"{protected_ep.method.value} {protected_ep.path}",
                    is_required=True,
                    description=f"认证依赖: 需要先登录才能访问 {protected_ep.path}",
                    dependency_data={
                        "auth_endpoint": auth_ep.path,
                        "protected_endpoint": protected_ep.path
                    }
                )
                dependencies.append(dependency)
        
        return dependencies

    def _analyze_data_dependencies(self, endpoints: List[ApiEndpointInfo]) -> List[DependencyInfo]:
        """分析数据依赖"""
        dependencies = []
        
        # 简单的数据依赖分析：检查路径参数
        for i, ep1 in enumerate(endpoints):
            for j, ep2 in enumerate(endpoints):
                if i != j and self._has_data_dependency(ep1, ep2):
                    dependency = DependencyInfo(
                        dependency_id=str(uuid.uuid4()),
                        dependency_type=DependencyType.DATA_DEPENDENCY,
                        source_test=f"{ep1.method.value} {ep1.path}",
                        target_test=f"{ep2.method.value} {ep2.path}",
                        is_required=True,
                        description=f"数据依赖: {ep2.path} 需要 {ep1.path} 的数据",
                        dependency_data={
                            "source_endpoint": ep1.path,
                            "target_endpoint": ep2.path
                        }
                    )
                    dependencies.append(dependency)
        
        return dependencies

    def _paths_related(self, path1: str, path2: str) -> bool:
        """判断两个路径是否相关"""
        # 移除路径参数进行比较
        base1 = path1.split('/{')[0]
        base2 = path2.split('/{')[0]
        return base1 == base2

    def _is_auth_endpoint(self, endpoint: ApiEndpointInfo) -> bool:
        """判断是否为认证端点"""
        auth_keywords = ["login", "auth", "signin", "token", "oauth"]
        path_lower = endpoint.path.lower()
        summary_lower = (endpoint.summary or "").lower()
        
        return any(keyword in path_lower or keyword in summary_lower for keyword in auth_keywords)

    def _has_data_dependency(self, ep1: ApiEndpointInfo, ep2: ApiEndpointInfo) -> bool:
        """判断是否存在数据依赖"""
        # 简单规则：如果ep1是POST，ep2是GET且路径相关，则存在依赖
        if ep1.method == HttpMethod.POST and ep2.method == HttpMethod.GET:
            return self._paths_related(ep1.path, ep2.path)
        return False

    def _determine_execution_order(self, dependencies: List[DependencyInfo]) -> List[str]:
        """确定执行顺序"""
        try:
            # 简单的拓扑排序
            nodes = set()
            edges = []
            
            for dep in dependencies:
                nodes.add(dep.source_test)
                nodes.add(dep.target_test)
                edges.append((dep.source_test, dep.target_test))
            
            # 拓扑排序算法
            in_degree = {node: 0 for node in nodes}
            for source, target in edges:
                in_degree[target] += 1
            
            queue = [node for node in nodes if in_degree[node] == 0]
            result = []
            
            while queue:
                node = queue.pop(0)
                result.append(node)
                
                for source, target in edges:
                    if source == node:
                        in_degree[target] -= 1
                        if in_degree[target] == 0:
                            queue.append(target)
            
            return result
            
        except Exception as e:
            logger.error(f"确定执行顺序失败: {str(e)}")
            return []

    def _build_dependency_graph(self, dependencies: List[DependencyInfo]) -> Dict[str, Any]:
        """构建依赖图"""
        try:
            nodes = set()
            edges = []
            
            for dep in dependencies:
                nodes.add(dep.source_test)
                nodes.add(dep.target_test)
                edges.append((dep.source_test, dep.target_test))
            
            return {
                "nodes": list(nodes),
                "edges": edges,
                "dependency_count": len(dependencies)
            }
            
        except Exception as e:
            logger.error(f"构建依赖图失败: {str(e)}")
            return {"nodes": [], "edges": [], "dependency_count": 0}

    async def _send_to_test_generator(self, response: DependencyAnalysisResponse):
        """发送到测试用例生成智能体"""
        try:
            # 发送到新的测试用例生成智能体
            await self.runtime.publish_message(
                response,
                topic_id=TopicId(type=TopicTypes.API_TEST_CASE_GENERATOR.value, source=self.agent_name)
            )
            logger.info(f"已发送到测试用例生成智能体: {response.doc_id}")

        except Exception as e:
            logger.error(f"发送到测试用例生成智能体失败: {str(e)}")

    async def _send_error_response(self, message: DependencyAnalysisRequest, error: str):
        """发送错误响应"""
        logger.error(f"接口分析错误: {error}")

    def get_analysis_statistics(self) -> Dict[str, Any]:
        """获取分析统计信息"""
        # 获取基类的公共统计
        common_stats = self.get_common_statistics()

        # 计算分析特定的统计
        success_rate = 0.0
        if self.analysis_metrics["total_requests"] > 0:
            success_rate = (self.analysis_metrics["successful_analyses"] /
                          self.analysis_metrics["total_requests"]) * 100

        # 合并统计信息
        return {
            **common_stats,
            "analysis_metrics": self.analysis_metrics,
            "analysis_success_rate": round(success_rate, 2)
        }


