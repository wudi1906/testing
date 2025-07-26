"""
接口分析智能体 - 重新设计版本
专门负责分析API端点之间的依赖关系，确定测试执行顺序

核心职责：
1. 分析API端点之间的数据流依赖关系
2. 识别认证依赖和序列依赖
3. 制定最优的测试执行计划
4. 进行风险评估和测试策略建议

数据流：AnalysisInput -> 依赖分析 -> AnalysisOutput
"""
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional, Set, Tuple

from autogen_core import message_handler, type_subscription, MessageContext, TopicId
from loguru import logger

from app.agents.api_automation.base_api_agent import BaseApiAutomationAgent
from app.core.types import AgentTypes, TopicTypes

# 导入重新设计的数据模型
from .schemas import (
    AnalysisInput, AnalysisOutput, EndpointDependency, ExecutionGroup,
    ParsedEndpoint, DependencyType, AgentPrompts
)

# 导入 R2R 客户端用于 RAG 搜索
try:
    from r2r import R2RClient
    R2R_AVAILABLE = True
except ImportError:
    logger.warning("R2R模块未安装，RAG检索功能将使用模拟模式")
    R2R_AVAILABLE = False


@type_subscription(topic_type=TopicTypes.API_ANALYZER.value)
class ApiAnalyzerAgent(BaseApiAutomationAgent):
    """
    接口分析智能体 - 重新设计版本
    
    专注于分析API端点之间的复杂依赖关系，
    为测试用例生成智能体提供清晰的执行计划和依赖信息。
    """

    def __init__(self, model_client_instance=None, agent_config=None, **kwargs):
        """初始化接口分析智能体"""
        super().__init__(
            agent_type=AgentTypes.API_ANALYZER,
            model_client_instance=model_client_instance,
            **kwargs
        )

        self.agent_config = agent_config or {}
        self._initialize_assistant_agent()

        # 分析统计指标
        self.analysis_metrics = {
            "total_analyses": 0,
            "successful_analyses": 0,
            "failed_analyses": 0,
            "total_dependencies_identified": 0,
            "total_execution_groups_created": 0
        }

        # 初始化 RAG 配置 - 基于R2R官方文档优化
        self.rag_config = {
            'base_url': "http://155.138.220.75:7272",
            'superuser_email': "65132090@qq.com",
            'superuser_password': "65132090",

            # 搜索模式配置
            'default_search_mode': "advanced",  # 使用advanced模式获得更好的混合搜索结果
            'enable_web_search': False,  # 是否启用网络搜索

            # 搜索设置
            'search_settings': {
                'use_semantic_search': True,
                'use_fulltext_search': True,
                'use_hybrid_search': True,
                'limit': 3,  # 增加结果数量以获得更好的上下文
                'include_scores': True,
                'include_metadatas': True,

                # 混合搜索配置
                'hybrid_settings': {
                    'full_text_weight': 1.0,
                    'semantic_weight': 5.0,  # 语义搜索权重更高
                    'full_text_limit': 200,
                    'rrf_k': 50  # Reciprocal Rank Fusion参数
                },

                # 向量搜索配置
                'chunk_settings': {
                    'index_measure': 'cosine_distance',  # 推荐用于文本嵌入
                    'probes': 10,
                    'ef_search': 40
                },

                # 搜索策略
                'search_strategy': 'vanilla',  # 可选: 'hyde', 'rag_fusion'
            },

            # RAG生成配置
            'rag_generation_config': {
                'model': 'openai/gpt-4o-mini',  # 可配置模型
                'stream': False,
                'temperature': 0.3,  # 较低温度确保准确性
                'max_tokens': 1000,
                'top_p': 0.9
            },

            # 过滤和质量控制
            'default_confidence_threshold': 0.6,  # 降低阈值获得更多结果
            'enable_advanced_filtering': True,
            'enable_citation_tracking': True
        }

        # 初始化 R2R 客户端
        self.r2r_client = None
        self._initialize_r2r_client()

        logger.info(f"接口分析智能体初始化完成: {self.agent_name}")

    def _initialize_r2r_client(self):
        """初始化R2R客户端"""
        try:
            if R2R_AVAILABLE:
                self.r2r_client = R2RClient(self.rag_config['base_url'])
                # 登录
                self.r2r_client.users.login(
                    self.rag_config['superuser_email'],
                    self.rag_config['superuser_password']
                )
                logger.info("R2R客户端初始化成功")
            else:
                logger.warning("R2R模块未安装，RAG检索功能将使用模拟模式")
                self.r2r_client = None
        except Exception as e:
            logger.error(f"R2R客户端初始化失败: {str(e)}")
            self.r2r_client = None

    @message_handler
    async def handle_analysis_request(
        self,
        message: AnalysisInput,
        ctx: MessageContext
    ) -> None:
        """处理接口分析请求 - 主要入口点"""
        start_time = datetime.now()
        self.analysis_metrics["total_analyses"] += 1

        try:
            logger.info(f"开始分析API依赖关系: {message.document_id}, 端点数量: {len(message.endpoints)}")

            # 1. 构建专业提示词并执行 RAG 搜索
            rag_context = await self._perform_rag_search_for_api_analysis(message)

            # 2. 使用大模型智能分析依赖关系（结合 RAG 上下文）
            analysis_result = await self._intelligent_analyze_dependencies(
                message.api_info, message.endpoints, rag_context
            )
            
            # 3. 构建依赖关系对象 - 修复数据路径
            dependencies = self._build_dependency_objects_from_analysis(
                analysis_result, message.endpoints
            )

            # 4. 创建执行组 - 使用分析结果中的执行顺序
            execution_groups = self._create_execution_groups_from_analysis(
                analysis_result, dependencies, message.endpoints
            )

            # 5. 进行风险评估
            risk_assessment = self._assess_testing_risks(dependencies, message.endpoints)

            # 6. 生成测试策略建议（结合 RAG 上下文）
            test_strategy = self._generate_test_strategy_with_rag_context(
                dependencies, execution_groups, rag_context
            )
            
            # 7. 构建输出结果（包含 RAG 上下文信息）
            output = AnalysisOutput(
                session_id=message.session_id,
                document_id=message.document_id,
                dependencies=dependencies,
                execution_groups=execution_groups,
                test_strategy=test_strategy,
                risk_assessment=risk_assessment,
                processing_time=(datetime.now() - start_time).total_seconds()
            )

            # 将 RAG 上下文信息添加到风险评估中
            if rag_context:
                output.risk_assessment["rag_context"] = rag_context

            # 8. 更新统计指标
            self.analysis_metrics["successful_analyses"] += 1
            self.analysis_metrics["total_dependencies_identified"] += len(dependencies)
            self.analysis_metrics["total_execution_groups_created"] += len(execution_groups)
            self._update_metrics("dependency_analysis", True, output.processing_time)

            # 9. 发送结果到脚本生成智能体（跳过测试用例生成步骤）
            await self._send_to_script_generator(output, message, ctx)

            logger.info(f"依赖分析完成: {message.document_id}, 识别依赖: {len(dependencies)}, 执行组: {len(execution_groups)}")

        except Exception as e:
            self.analysis_metrics["failed_analyses"] += 1
            self._update_metrics("dependency_analysis", False)
            error_info = self._handle_common_error(e, "dependency_analysis")
            logger.error(f"依赖分析失败: {error_info}")

    async def _intelligent_analyze_dependencies(
        self,
        api_info,
        endpoints: List[ParsedEndpoint],
        rag_context: Optional[Dict[str, Any]] = None
    ):
        """使用大模型智能分析依赖关系（结合RAG上下文）"""
        try:
            # 构建分析任务提示词
            endpoints_info = self._format_endpoints_for_analysis(endpoints)
            api_info_str = json.dumps({
                "title": api_info.title,
                "version": api_info.version,
                "description": api_info.description,
                "base_url": api_info.base_url
            }, indent=2, ensure_ascii=False)

            # 构建增强的提示词（包含RAG上下文）
            task_prompt = self._build_enhanced_analysis_prompt(
                api_info_str, endpoints_info, rag_context
            )
            
            # 使用AssistantAgent进行智能分析
            result_content = await self._run_assistant_agent(task_prompt)
            
            if result_content:
                # 提取JSON结果
                parsed_data = self._extract_json_from_content(result_content)
                if parsed_data:
                    return parsed_data
            

        except Exception as e:
            logger.error(f"智能依赖分析失败: {str(e)}")
            return {}

    def _format_endpoints_for_analysis(self, endpoints: List[ParsedEndpoint]) -> str:
        """格式化端点信息用于分析"""
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
                        "description": param.description
                    }
                    for param in endpoint.parameters
                ],
                "responses": [
                    {
                        "status_code": resp.status_code,
                        "description": resp.description
                    }
                    for resp in endpoint.responses
                ]
            }
            formatted_endpoints.append(endpoint_info)
        
        return json.dumps(formatted_endpoints, indent=2, ensure_ascii=False)

    def _build_dependency_objects_from_analysis(
        self,
        analysis_result: Dict[str, Any],
        endpoints: List[ParsedEndpoint]
    ) -> List[EndpointDependency]:
        """从分析结果构建依赖关系对象 - 适配新的数据结构"""
        dependencies = []

        try:
            # 从正确的路径提取依赖数据
            dependency_analysis = analysis_result.get("dependency_analysis", {})
            dependency_graph = dependency_analysis.get("dependency_graph", {})
            edges = dependency_graph.get("edges", [])
            nodes = dependency_graph.get("nodes", [])

            logger.info(f"开始构建依赖关系对象，发现 {len(edges)} 个依赖边，{len(nodes)} 个节点")

            # 创建端点ID到端点对象的映射
            endpoint_map = {}
            for endpoint in endpoints:
                # 尝试多种方式匹配端点
                endpoint_key = f"{endpoint.method.value}:{endpoint.path}"
                endpoint_map[endpoint_key] = endpoint

                # 如果端点有ID，也加入映射
                if hasattr(endpoint, 'endpoint_id'):
                    endpoint_map[endpoint.endpoint_id] = endpoint

            # 创建节点ID到端点的映射
            node_to_endpoint_map = {}
            for node in nodes:
                node_id = node.get("endpoint_id")
                method = node.get("method", "").upper()
                path = node.get("path", "")

                # 尝试通过路径和方法匹配端点
                endpoint_key = f"{method}:{path}"
                if endpoint_key in endpoint_map:
                    node_to_endpoint_map[node_id] = endpoint_map[endpoint_key]
                    logger.debug(f"映射节点 {node_id} 到端点 {method} {path}")
                else:
                    logger.warning(f"无法找到匹配的端点: {method} {path}")

            # 构建依赖关系对象
            for edge in edges:
                try:
                    from_id = edge.get("from")
                    to_id = edge.get("to")
                    dependency_type = edge.get("dependency_type", "unknown")
                    description = edge.get("description", "")
                    strength = edge.get("strength", "medium")

                    # 查找源端点和目标端点
                    source_endpoint = node_to_endpoint_map.get(from_id)
                    target_endpoint = node_to_endpoint_map.get(to_id)

                    if source_endpoint and target_endpoint:
                        # 映射依赖类型
                        dep_type_mapping = {
                            "sequence": DependencyType.SEQUENCE,
                            "auth": DependencyType.AUTH,
                            "business": DependencyType.BUSINESS,
                            "data": DependencyType.DATA,
                            "functional": DependencyType.FUNCTIONAL
                        }

                        mapped_type = dep_type_mapping.get(dependency_type.lower(), DependencyType.FUNCTIONAL)

                        # 映射强度
                        strength_mapping = {
                            "weak": 1,
                            "medium": 2,
                            "strong": 3,
                            "critical": 4
                        }

                        strength_value = strength_mapping.get(strength.lower(), 2)

                        dependency = EndpointDependency(
                            source_endpoint_id=from_id,
                            target_endpoint_id=to_id,
                            dependency_type=mapped_type,
                            description=f"{description} (强度: {strength})",
                            condition=edge.get("condition")  # 使用condition而不是conditions
                        )

                        dependencies.append(dependency)
                        logger.debug(f"创建依赖关系: {source_endpoint.path} -> {target_endpoint.path} ({dependency_type})")

                    else:
                        logger.warning(f"无法找到依赖关系的端点: {from_id} -> {to_id}")

                except Exception as e:
                    logger.warning(f"处理依赖边失败: {str(e)}, 边数据: {edge}")
                    continue

            logger.info(f"成功构建 {len(dependencies)} 个依赖关系对象")
            return dependencies

        except Exception as e:
            logger.error(f"从分析结果构建依赖关系对象失败: {str(e)}")
            return []

    def _build_dependency_objects(
        self, 
        dependencies_data: List[Dict[str, Any]], 
        endpoints: List[ParsedEndpoint]
    ) -> List[EndpointDependency]:
        """构建依赖关系对象"""
        dependencies = []
        endpoint_id_map = {ep.endpoint_id: ep for ep in endpoints}
        
        for dep_data in dependencies_data:
            try:
                # 验证端点ID存在
                source_id = dep_data.get("source_endpoint_id")
                target_id = dep_data.get("target_endpoint_id")
                
                if source_id in endpoint_id_map and target_id in endpoint_id_map:
                    dependency = EndpointDependency(
                        source_endpoint_id=source_id,
                        target_endpoint_id=target_id,
                        dependency_type=DependencyType(dep_data.get("dependency_type", "sequence")),
                        description=dep_data.get("description", ""),
                        data_mapping=dep_data.get("data_mapping", {}),
                        condition=dep_data.get("condition")
                    )
                    dependencies.append(dependency)
                    
            except Exception as e:
                logger.warning(f"构建依赖对象失败: {str(e)}")
                continue
        
        return dependencies

    def _create_execution_groups_from_analysis(
        self,
        analysis_result: Dict[str, Any],
        dependencies: List[EndpointDependency],
        endpoints: List[ParsedEndpoint]
    ) -> List[ExecutionGroup]:
        """从分析结果创建执行组 - 使用大模型分析的执行顺序"""
        execution_groups = []

        try:
            # 从分析结果中提取执行顺序
            dependency_analysis = analysis_result.get("dependency_analysis", {})
            execution_order = dependency_analysis.get("execution_order", [])

            logger.info(f"开始创建执行组，发现 {len(execution_order)} 个执行阶段")

            # 创建端点映射
            endpoint_map = {}
            for endpoint in endpoints:
                endpoint_key = f"{endpoint.method.value}:{endpoint.path}"
                endpoint_map[endpoint_key] = endpoint

            # 创建节点ID到端点的映射
            nodes = dependency_analysis.get("dependency_graph", {}).get("nodes", [])
            node_to_endpoint_map = {}
            for node in nodes:
                node_id = node.get("endpoint_id")
                method = node.get("method", "").upper()
                path = node.get("path", "")
                endpoint_key = f"{method}:{path}"

                if endpoint_key in endpoint_map:
                    node_to_endpoint_map[node_id] = endpoint_map[endpoint_key]

            # 根据执行顺序创建执行组
            for phase_info in execution_order:
                try:
                    phase_name = phase_info.get("phase", "unknown")
                    endpoint_ids = phase_info.get("endpoints", [])
                    parallel_groups = phase_info.get("parallel_groups", [])
                    prerequisites = phase_info.get("prerequisites", [])

                    # 获取该阶段的端点
                    phase_endpoints = []
                    for endpoint_id in endpoint_ids:
                        if endpoint_id in node_to_endpoint_map:
                            phase_endpoints.append(node_to_endpoint_map[endpoint_id])
                        else:
                            logger.warning(f"无法找到端点ID对应的端点: {endpoint_id}")

                    if not phase_endpoints:
                        logger.warning(f"阶段 {phase_name} 没有有效的端点")
                        continue

                    # 创建执行组
                    if parallel_groups:
                        # 如果有并行组，为每个并行组创建执行组
                        for i, parallel_group in enumerate(parallel_groups):
                            parallel_endpoints = []
                            for endpoint_id in parallel_group:
                                if endpoint_id in node_to_endpoint_map:
                                    parallel_endpoints.append(node_to_endpoint_map[endpoint_id])

                            if parallel_endpoints:
                                execution_group = ExecutionGroup(
                                    group_id=f"{phase_name}_parallel_{i+1}",
                                    group_name=f"{phase_name}阶段并行组{i+1}",
                                    endpoint_ids=[ep.path for ep in parallel_endpoints],  # 添加endpoint_ids
                                    endpoints=parallel_endpoints,
                                    execution_order=0,  # 并行执行
                                    prerequisites=prerequisites,
                                    description=f"{phase_name}阶段并行组{i+1}"
                                )
                                execution_groups.append(execution_group)
                                logger.debug(f"创建并行执行组: {execution_group.group_id}, 端点数: {len(parallel_endpoints)}")
                    else:
                        # 创建顺序执行组
                        execution_group = ExecutionGroup(
                            group_id=f"{phase_name}_sequential",
                            group_name=f"{phase_name}阶段顺序执行",
                            endpoint_ids=[ep.path for ep in phase_endpoints],  # 添加endpoint_ids
                            endpoints=phase_endpoints,
                            execution_order=1,  # 顺序执行
                            prerequisites=prerequisites,
                            description=f"{phase_name}阶段顺序执行"
                        )
                        execution_groups.append(execution_group)
                        logger.debug(f"创建顺序执行组: {execution_group.group_id}, 端点数: {len(phase_endpoints)}")

                except Exception as e:
                    logger.warning(f"处理执行阶段失败: {str(e)}, 阶段数据: {phase_info}")
                    continue

            # 如果没有从分析结果中创建执行组，使用默认方法
            if not execution_groups:
                logger.warning("未能从分析结果创建执行组，使用默认方法")
                return self._create_execution_groups(dependencies, endpoints)

            logger.info(f"成功创建 {len(execution_groups)} 个执行组")
            return execution_groups

        except Exception as e:
            logger.error(f"从分析结果创建执行组失败: {str(e)}")
            # 降级到默认方法
            return self._create_execution_groups(dependencies, endpoints)

    def _create_execution_groups(
        self, 
        dependencies: List[EndpointDependency], 
        endpoints: List[ParsedEndpoint]
    ) -> List[ExecutionGroup]:
        """创建执行组"""
        try:
            # 构建依赖图
            dependency_graph = self._build_dependency_graph(dependencies, endpoints)
            
            # 拓扑排序确定执行顺序
            execution_order = self._topological_sort(dependency_graph)
            
            # 创建执行组
            groups = []
            group_order = 1
            
            for level_endpoints in execution_order:
                if level_endpoints:
                    group = ExecutionGroup(
                        group_name=f"执行组_{group_order}",
                        endpoint_ids=list(level_endpoints),
                        execution_order=group_order,
                        parallel_execution=len(level_endpoints) > 1
                    )
                    groups.append(group)
                    group_order += 1
            
            return groups
            
        except Exception as e:
            logger.error(f"创建执行组失败: {str(e)}")
            # 返回默认执行组
            return [ExecutionGroup(
                group_name="默认执行组",
                endpoint_ids=[ep.endpoint_id for ep in endpoints],
                execution_order=1,
                parallel_execution=False
            )]

    def _build_dependency_graph(
        self, 
        dependencies: List[EndpointDependency], 
        endpoints: List[ParsedEndpoint]
    ) -> Dict[str, Set[str]]:
        """构建依赖图"""
        graph = {ep.endpoint_id: set() for ep in endpoints}
        
        for dep in dependencies:
            # target依赖于source，所以source必须在target之前执行
            graph[dep.target_endpoint_id].add(dep.source_endpoint_id)
        
        return graph

    def _topological_sort(self, graph: Dict[str, Set[str]]) -> List[List[str]]:
        """拓扑排序，返回分层的执行顺序"""
        in_degree = {node: len(deps) for node, deps in graph.items()}
        result = []
        
        while in_degree:
            # 找到入度为0的节点（可以并行执行）
            current_level = [node for node, degree in in_degree.items() if degree == 0]
            
            if not current_level:
                # 存在循环依赖，返回剩余节点
                result.append(list(in_degree.keys()))
                break
            
            result.append(current_level)
            
            # 移除当前层节点，更新入度
            for node in current_level:
                del in_degree[node]
                for other_node in in_degree:
                    if node in graph[other_node]:
                        graph[other_node].remove(node)
                        in_degree[other_node] -= 1
        
        return result

    def _assess_testing_risks(
        self, 
        dependencies: List[EndpointDependency], 
        endpoints: List[ParsedEndpoint]
    ) -> Dict[str, Any]:
        """评估测试风险"""
        risks = {
            "high_risk_endpoints": [],
            "circular_dependencies": [],
            "complex_data_flows": [],
            "auth_bottlenecks": [],
            "risk_score": 0.0
        }
        
        # 识别高风险端点（依赖较多的端点）
        dependency_count = {}
        for dep in dependencies:
            dependency_count[dep.target_endpoint_id] = dependency_count.get(dep.target_endpoint_id, 0) + 1
        
        for endpoint_id, count in dependency_count.items():
            if count >= 3:  # 依赖超过3个端点的被认为是高风险
                risks["high_risk_endpoints"].append({
                    "endpoint_id": endpoint_id,
                    "dependency_count": count
                })
        
        # 计算风险分数
        risks["risk_score"] = min(len(risks["high_risk_endpoints"]) * 0.2, 1.0)
        
        return risks

    def _generate_test_strategy(
        self, 
        dependencies: List[EndpointDependency], 
        execution_groups: List[ExecutionGroup]
    ) -> List[str]:
        """生成测试策略建议"""
        strategies = []
        
        # 基于依赖关系的策略
        if dependencies:
            strategies.append("建议按照依赖顺序执行测试，确保数据流的正确性")
            
            auth_deps = [d for d in dependencies if d.dependency_type == DependencyType.AUTH_TOKEN]
            if auth_deps:
                strategies.append("优先测试认证相关接口，确保后续测试能够正常进行")
        
        # 基于执行组的策略
        parallel_groups = [g for g in execution_groups if g.parallel_execution]
        if parallel_groups:
            strategies.append(f"可以并行执行{len(parallel_groups)}个测试组，提高测试效率")
        
        # 默认策略
        if not strategies:
            strategies.append("建议进行全面的功能测试，包括正向和负向测试用例")
        
        return strategies


    async def _send_to_test_case_generator(
        self, 
        output: AnalysisOutput, 
        original_input: AnalysisInput,
        ctx: MessageContext
    ):
        """发送分析结果到测试用例生成智能体"""
        try:
            from .schemas import TestCaseGenerationInput
            
            # 构建测试用例生成输入
            test_case_input = TestCaseGenerationInput(
                session_id=output.session_id,
                document_id=output.document_id,
                api_info=original_input.api_info,
                endpoints=original_input.endpoints,
                dependencies=output.dependencies,
                execution_groups=output.execution_groups,
                generation_options={}
            )
            
            # 发送到测试用例生成智能体
            await self.runtime.publish_message(
                test_case_input,
                topic_id=TopicId(type=TopicTypes.API_TEST_CASE_GENERATOR.value, source=self.agent_name)
            )
            
            logger.info(f"已发送分析结果到测试用例生成智能体: {output.document_id}")
            
        except Exception as e:
            logger.error(f"发送到测试用例生成智能体失败: {str(e)}")

    async def _send_to_script_generator(
        self,
        output: AnalysisOutput,
        original_input: AnalysisInput,
        ctx: MessageContext
    ):
        """发送分析结果到脚本生成智能体（跳过测试用例生成步骤）"""
        try:
            from .schemas import ScriptGenerationInput, GeneratedTestCase, TestCaseType

            # 为每个端点生成基础测试用例
            test_cases = []
            for endpoint in original_input.endpoints:
                # 生成基础功能测试用例
                test_case = GeneratedTestCase(
                    test_case_id=f"test_{endpoint.endpoint_id}",
                    name=f"测试{endpoint.summary or endpoint.path}",
                    description=f"测试接口 {endpoint.method} {endpoint.path}",
                    endpoint_id=endpoint.endpoint_id,
                    test_type=TestCaseType.FUNCTIONAL,
                    priority=1,
                    test_data={},
                    expected_results={},
                    assertions=[],
                    setup_steps=[],
                    cleanup_steps=[]
                )
                test_cases.append(test_case)

            # 构建脚本生成输入
            # 获取第一个端点的ID作为interface_id（单接口场景）
            interface_id = original_input.endpoints[0].endpoint_id if original_input.endpoints else None

            script_input = ScriptGenerationInput(
                session_id=output.session_id,
                document_id=output.document_id,
                interface_id=interface_id,
                api_info=original_input.api_info,
                endpoints=original_input.endpoints,
                test_cases=test_cases,
                execution_groups=output.execution_groups,
                generation_options={}
            )

            # 发送到脚本生成智能体
            await self.runtime.publish_message(
                script_input,
                topic_id=TopicId(type=TopicTypes.TEST_SCRIPT_GENERATOR.value, source=self.agent_name)
            )

            logger.info(f"已发送分析结果到脚本生成智能体: {output.document_id}")

        except Exception as e:
            logger.error(f"发送到脚本生成智能体失败: {str(e)}")

    def get_analysis_statistics(self) -> Dict[str, Any]:
        """获取分析统计信息"""
        base_stats = self.get_common_statistics()
        base_stats.update({
            "analysis_metrics": self.analysis_metrics,
            "avg_dependencies_per_analysis": (
                self.analysis_metrics["total_dependencies_identified"] / 
                max(self.analysis_metrics["successful_analyses"], 1)
            ),
            "avg_groups_per_analysis": (
                self.analysis_metrics["total_execution_groups_created"] / 
                max(self.analysis_metrics["successful_analyses"], 1)
            )
        })
        return base_stats

    async def _perform_rag_search_for_api_analysis(self, message: AnalysisInput) -> Optional[Dict[str, Any]]:
        """为API分析执行RAG搜索，获取相关上下文信息"""
        try:
            # 1. 构建专业的搜索提示词
            search_query = self._build_rag_search_query(message)

            # 2. 执行RAG搜索
            search_results = await self._execute_rag_search(search_query)

            # 3. 分析搜索结果，提取依赖关系信息
            context_info = self._extract_context_from_search_results(search_results, message)

            logger.info(f"RAG搜索完成，找到 {len(search_results.get('results', []))} 个相关文档")
            return context_info

        except Exception as e:
            logger.error(f"RAG搜索失败: {str(e)}")
            return None

    def _build_rag_search_query(self, message: AnalysisInput) -> str:
        """构建专业的RAG搜索查询 - 使用优化的上下文感知版本"""
        return self._build_context_aware_search_query(message)

    async def _execute_rag_search(self, query: str) -> Dict[str, Any]:
        """执行优化的RAG搜索 - 基于R2R官方文档"""
        try:
            if self.r2r_client is None:
                logger.info("使用模拟RAG搜索结果")
                return self._create_mock_rag_results(query)

            # 构建高级搜索设置
            search_settings = self._build_advanced_search_settings(query)

            # 执行搜索 - 使用官方推荐的配置
            search_response = self.r2r_client.retrieval.search(
                query=query,
                search_mode=self.rag_config.get("default_search_mode", "advanced"),
                search_settings=search_settings
            )

            # 解析搜索响应
            parsed_results = self._parse_search_response(search_response, query)

            # 如果启用了RAG生成，执行RAG调用
            if self.rag_config.get('enable_rag_generation', False):
                rag_response = await self._execute_rag_generation(query, search_settings)
                parsed_results['rag_answer'] = rag_response

            return parsed_results

        except Exception as e:
            logger.error(f"RAG搜索执行失败: {str(e)}")
            return self._create_mock_rag_results(query)

    def _build_advanced_search_settings(self, query: str) -> Dict[str, Any]:
        """构建高级搜索设置"""
        base_settings = self.rag_config.get('search_settings', {}).copy()

        # 根据查询内容动态调整设置
        query_lower = query.lower()

        # 如果查询包含技术术语，增加语义搜索权重
        if any(term in query_lower for term in ['api', 'interface', 'dependency', 'authentication', 'error']):
            if 'hybrid_settings' in base_settings:
                base_settings['hybrid_settings']['semantic_weight'] = 7.0
                base_settings['hybrid_settings']['full_text_weight'] = 1.0

        # 添加API相关的过滤器
        if self.rag_config.get('enable_advanced_filtering', True):
            base_settings['filters'] = self._build_api_filters()

        return base_settings

    def _build_api_filters(self) -> Dict[str, Any]:
        """构建API相关的过滤器"""
        return {
            "$or": [
                {"metadata.category": {"$in": ["api", "testing", "documentation"]}},
                {"metadata.type": {"$in": ["api_spec", "test_case", "best_practice"]}},
                {"document_type": {"$in": ["json", "yaml", "markdown", "pdf"]}}
            ]
        }

    def _parse_search_response(self, search_response, query: str) -> Dict[str, Any]:
        """解析搜索响应 - 支持新的响应格式"""
        try:
            results = []
            total_results = 0

            # 处理搜索结果
            if hasattr(search_response, 'results'):
                aggregate_results = search_response.results

                # 处理文本块搜索结果
                if hasattr(aggregate_results, 'chunk_search_results'):
                    chunk_results = aggregate_results.chunk_search_results
                    for chunk in chunk_results:
                        results.append({
                            'id': getattr(chunk, 'id', ''),
                            'text': getattr(chunk, 'text', ''),
                            'score': getattr(chunk, 'score', 0.0),
                            'document_id': getattr(chunk, 'document_id', ''),
                            'metadata': getattr(chunk, 'metadata', {}),
                            'type': 'chunk'
                        })

                # 处理知识图谱搜索结果
                if hasattr(aggregate_results, 'graph_search_results'):
                    graph_results = aggregate_results.graph_search_results
                    for graph_item in graph_results:
                        results.append({
                            'id': getattr(graph_item, 'id', ''),
                            'content': getattr(graph_item, 'content', {}),
                            'score': getattr(graph_item, 'score', 0.0),
                            'result_type': getattr(graph_item, 'result_type', 'UNKNOWN'),
                            'metadata': getattr(graph_item, 'metadata', {}),
                            'type': 'graph'
                        })

                # 处理网络搜索结果（如果启用）
                if hasattr(aggregate_results, 'web_search_results'):
                    web_results = aggregate_results.web_search_results
                    for web_item in web_results:
                        results.append({
                            'url': getattr(web_item, 'url', ''),
                            'title': getattr(web_item, 'title', ''),
                            'snippet': getattr(web_item, 'snippet', ''),
                            'score': getattr(web_item, 'score', 0.0),
                            'type': 'web'
                        })

                total_results = len(results)

            return {
                "results": results,
                "total_results": total_results,
                "query": query,
                "search_metadata": {
                    "search_mode": self.rag_config.get("default_search_mode", "advanced"),
                    "timestamp": datetime.now().isoformat()
                }
            }

        except Exception as e:
            logger.error(f"解析搜索响应失败: {str(e)}")
            return self._create_mock_rag_results(query)

    async def _execute_rag_generation(self, query: str, search_settings: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """执行RAG生成 - 基于R2R官方文档"""
        try:
            if self.r2r_client is None:
                return self._create_mock_rag_generation(query)

            # 获取RAG生成配置
            rag_config = self.rag_config.get('rag_generation_config', {})

            # 执行RAG调用
            rag_response = self.r2r_client.retrieval.rag(
                query=query,
                search_settings=search_settings,
                rag_generation_config=rag_config,
                include_web_search=self.rag_config.get('enable_web_search', False)
            )

            # 解析RAG响应
            return self._parse_rag_response(rag_response)

        except Exception as e:
            logger.error(f"RAG生成失败: {str(e)}")
            return self._create_mock_rag_generation(query)

    def _parse_rag_response(self, rag_response) -> Dict[str, Any]:
        """解析RAG响应"""
        try:
            if hasattr(rag_response, 'results'):
                results = rag_response.results
                return {
                    'generated_answer': getattr(results, 'generated_answer', ''),
                    'citations': self._extract_citations(getattr(results, 'citations', [])),
                    'metadata': getattr(results, 'metadata', {}),
                    'search_results_used': getattr(results, 'search_results', {})
                }
            return {}
        except Exception as e:
            logger.error(f"解析RAG响应失败: {str(e)}")
            return {}

    def _extract_citations(self, citations) -> List[Dict[str, Any]]:
        """提取引用信息"""
        extracted_citations = []
        for citation in citations:
            try:
                extracted_citations.append({
                    'id': getattr(citation, 'id', ''),
                    'payload': getattr(citation, 'payload', {}),
                    'spans': getattr(citation, 'spans', [])
                })
            except Exception as e:
                logger.warning(f"提取引用失败: {str(e)}")
                continue
        return extracted_citations

    def _create_mock_rag_generation(self, query: str) -> Dict[str, Any]:
        """创建模拟RAG生成结果"""
        return {
            'generated_answer': f"基于知识库分析，关于'{query}'的相关信息包括：API接口依赖关系分析表明登录接口通常是其他需要认证接口的前置依赖。建议在测试策略中优先考虑认证流程的完整性测试。",
            'citations': [
                {'id': 'cit.1', 'payload': {'source': 'api_best_practices.md'}, 'spans': [[0, 20]]},
                {'id': 'cit.2', 'payload': {'source': 'testing_guidelines.md'}, 'spans': [[50, 80]]}
            ],
            'metadata': {'model': 'mock', 'confidence': 0.8}
        }

    def _create_mock_rag_results(self, query: str) -> Dict[str, Any]:
        """创建增强的模拟RAG搜索结果"""
        return {
            "results": [
                {
                    "id": "chunk-001",
                    "text": "API接口依赖关系分析：登录接口通常是其他需要认证的接口的前置依赖，成功登录后会返回access-token用于后续接口调用",
                    "score": 0.85,
                    "document_id": "doc-api-best-practices",
                    "metadata": {"source": "api_best_practices.md", "category": "api", "confidence": 0.85},
                    "type": "chunk"
                },
                {
                    "id": "chunk-002",
                    "text": "错误处理最佳实践：应该测试所有可能的错误状态码，包括认证失败、参数错误等。特别注意重复登录和验证码错误的场景",
                    "score": 0.80,
                    "document_id": "doc-testing-guidelines",
                    "metadata": {"source": "testing_guidelines.md", "category": "testing", "confidence": 0.80},
                    "type": "chunk"
                },
                {
                    "id": "graph-001",
                    "content": {"name": "Authentication Flow", "description": "用户认证流程实体"},
                    "score": 0.78,
                    "result_type": "ENTITY",
                    "metadata": {"category": "authentication", "confidence": 0.78},
                    "type": "graph"
                },
                {
                    "id": "chunk-003",
                    "text": "安全考虑：登录接口应该使用HTTPS传输，密码字段不应明文传输，需要验证请求头中的必要参数如access-token等",
                    "score": 0.82,
                    "document_id": "doc-security-guidelines",
                    "metadata": {"source": "security_guidelines.md", "category": "security", "confidence": 0.82},
                    "type": "chunk"
                },
                {
                    "id": "chunk-004",
                    "text": "性能测试建议：登录接口通常是高频调用接口，需要考虑并发测试和限流机制的验证，建议测试不同负载下的响应时间",
                    "score": 0.75,
                    "document_id": "doc-performance-testing",
                    "metadata": {"source": "performance_testing.md", "category": "performance", "confidence": 0.75},
                    "type": "chunk"
                }
            ],
            "total_results": 5,
            "query": query,
            "search_metadata": {
                "search_mode": "advanced",
                "timestamp": datetime.now().isoformat(),
                "mock_mode": True
            }
        }

    def _extract_context_from_search_results(
        self,
        search_results: Dict[str, Any],
        message: AnalysisInput
    ) -> Dict[str, Any]:
        """从搜索结果中提取上下文信息 - 优化版本"""
        context_info = {
            "dependency_insights": [],
            "testing_recommendations": [],
            "security_considerations": [],
            "performance_insights": [],
            "error_handling_patterns": [],
            "related_apis": [],
            "graph_insights": [],  # 新增：知识图谱洞察
            "web_insights": [],    # 新增：网络搜索洞察
            "confidence_score": 0.0,
            "search_metadata": search_results.get("search_metadata", {}),
            "rag_answer": search_results.get("rag_answer", {})  # 新增：RAG生成的答案
        }

        results = search_results.get("results", [])
        if not results:
            return context_info

        # 按类型和置信度排序结果
        sorted_results = sorted(results, key=lambda x: x.get("score", 0.0), reverse=True)

        total_confidence = 0.0
        processed_count = 0

        for result in sorted_results:
            # 根据结果类型获取内容
            content = self._extract_content_from_result(result)
            if not content:
                continue

            score = result.get("score", 0.0)
            result_type = result.get("type", "chunk")

            # 只处理高质量结果
            if score < self.rag_config.get('default_confidence_threshold', 0.6):
                continue

            total_confidence += score
            processed_count += 1

            # 构建结果项
            result_item = {
                "content": content,
                "confidence": score,
                "source": self._extract_source_info(result),
                "type": result_type,
                "metadata": result.get("metadata", {})
            }

            # 智能分类 - 改进的关键词匹配
            self._classify_result_content(content, result_item, context_info)

            # 处理特殊类型的结果
            if result_type == "graph":
                context_info["graph_insights"].append(result_item)
            elif result_type == "web":
                context_info["web_insights"].append(result_item)

        # 计算加权平均置信度
        context_info["confidence_score"] = total_confidence / processed_count if processed_count > 0 else 0.0

        # 对每个类别按置信度排序并限制数量
        self._optimize_context_categories(context_info)

        return context_info

    def _extract_content_from_result(self, result: Dict[str, Any]) -> str:
        """从结果中提取内容文本"""
        result_type = result.get("type", "chunk")

        if result_type == "chunk":
            return result.get("text", "")
        elif result_type == "graph":
            content_obj = result.get("content", {})
            if isinstance(content_obj, dict):
                name = content_obj.get("name", "")
                desc = content_obj.get("description", "")
                return f"{name}: {desc}" if name and desc else name or desc
            return str(content_obj)
        elif result_type == "web":
            title = result.get("title", "")
            snippet = result.get("snippet", "")
            return f"{title} - {snippet}" if title and snippet else title or snippet

        return result.get("content", "")

    def _extract_source_info(self, result: Dict[str, Any]) -> str:
        """提取来源信息"""
        metadata = result.get("metadata", {})

        # 优先使用metadata中的source
        if "source" in metadata:
            return metadata["source"]

        # 根据类型提取不同的来源信息
        result_type = result.get("type", "chunk")
        if result_type == "web":
            return result.get("url", "web_search")
        elif result_type == "graph":
            return "knowledge_graph"

        # 使用document_id或默认值
        return result.get("document_id", "unknown")

    def _classify_result_content(self, content: str, result_item: Dict[str, Any], context_info: Dict[str, Any]):
        """智能分类结果内容 - 改进的分类逻辑"""
        content_lower = content.lower()

        # 定义更精确的关键词集合
        classification_rules = {
            "dependency_insights": [
                "依赖", "dependency", "前置", "prerequisite", "require", "depend",
                "先决条件", "前提", "关联", "关系", "调用", "invoke"
            ],
            "testing_recommendations": [
                "测试", "test", "验证", "validation", "检查", "check", "断言", "assert",
                "用例", "case", "场景", "scenario", "覆盖", "coverage"
            ],
            "security_considerations": [
                "安全", "security", "认证", "auth", "授权", "authorization", "token",
                "密码", "password", "加密", "encrypt", "https", "ssl", "tls"
            ],
            "performance_insights": [
                "性能", "performance", "限流", "rate", "并发", "concurrent", "负载", "load",
                "响应时间", "response time", "吞吐量", "throughput", "延迟", "latency"
            ],
            "error_handling_patterns": [
                "错误", "error", "异常", "exception", "失败", "fail", "状态码", "status code",
                "异常处理", "error handling", "重试", "retry", "降级", "fallback"
            ],
            "related_apis": [
                "接口", "api", "endpoint", "服务", "service", "方法", "method",
                "路径", "path", "url", "uri", "请求", "request", "响应", "response"
            ]
        }

        # 计算每个类别的匹配分数
        category_scores = {}
        for category, keywords in classification_rules.items():
            score = sum(1 for keyword in keywords if keyword in content_lower)
            if score > 0:
                category_scores[category] = score

        # 将结果添加到得分最高的类别（可能多个类别）
        if category_scores:
            max_score = max(category_scores.values())
            for category, score in category_scores.items():
                if score >= max_score * 0.8:  # 允许多分类，阈值为最高分的80%
                    context_info[category].append(result_item)

    def _optimize_context_categories(self, context_info: Dict[str, Any]):
        """优化上下文类别 - 排序和限制数量"""
        categories_to_optimize = [
            "dependency_insights", "testing_recommendations", "security_considerations",
            "performance_insights", "error_handling_patterns", "related_apis"
        ]

        for category in categories_to_optimize:
            items = context_info.get(category, [])
            if items:
                # 按置信度排序
                items.sort(key=lambda x: x.get("confidence", 0.0), reverse=True)
                # 限制每个类别的最大数量
                max_items = 5 if category in ["dependency_insights", "testing_recommendations"] else 3
                context_info[category] = items[:max_items]

    def _build_enhanced_analysis_prompt(
        self,
        api_info_str: str,
        endpoints_info: str,
        rag_context: Optional[Dict[str, Any]]
    ) -> str:
        """构建增强的分析提示词（包含RAG上下文）"""
        base_prompt = AgentPrompts.API_ANALYZER_TASK_PROMPT.format(
            api_info=api_info_str,
            endpoints=endpoints_info
        )

        if not rag_context:
            return base_prompt

        # 构建RAG上下文部分
        rag_context_str = "\n\n## 知识库上下文信息\n"

        if rag_context.get("dependency_insights"):
            rag_context_str += "\n### 依赖关系洞察：\n"
            for insight in rag_context["dependency_insights"][:3]:  # 取前3个最相关的
                rag_context_str += f"- {insight['content']} (置信度: {insight['confidence']:.2f})\n"

        if rag_context.get("testing_recommendations"):
            rag_context_str += "\n### 测试建议：\n"
            for rec in rag_context["testing_recommendations"][:3]:
                rag_context_str += f"- {rec['content']} (置信度: {rec['confidence']:.2f})\n"

        if rag_context.get("security_considerations"):
            rag_context_str += "\n### 安全考虑：\n"
            for sec in rag_context["security_considerations"][:2]:
                rag_context_str += f"- {sec['content']} (置信度: {sec['confidence']:.2f})\n"

        if rag_context.get("error_handling_patterns"):
            rag_context_str += "\n### 错误处理模式：\n"
            for err in rag_context["error_handling_patterns"][:2]:
                rag_context_str += f"- {err['content']} (置信度: {err['confidence']:.2f})\n"

        rag_context_str += f"\n### 上下文置信度：{rag_context.get('confidence_score', 0.0):.2f}\n"
        rag_context_str += "\n请结合以上知识库信息进行更准确的依赖关系分析。\n"

        return base_prompt + rag_context_str

    def _generate_test_strategy_with_rag_context(
        self,
        dependencies: List[EndpointDependency],
        execution_groups: List[ExecutionGroup],
        rag_context: Optional[Dict[str, Any]]
    ) -> List[str]:
        """生成结合RAG上下文的测试策略建议"""
        # 基础测试策略
        base_strategy = self._generate_test_strategy(dependencies, execution_groups)

        if not rag_context:
            return base_strategy

        # 基于RAG上下文增强测试策略
        enhanced_strategy = base_strategy.copy()

        # 添加基于依赖洞察的策略
        if rag_context.get("dependency_insights"):
            enhanced_strategy.append("基于知识库依赖分析：")
            for insight in rag_context["dependency_insights"][:2]:
                enhanced_strategy.append(f"  - {insight['content']}")

        # 添加基于测试建议的策略
        if rag_context.get("testing_recommendations"):
            enhanced_strategy.append("基于知识库测试建议：")
            for rec in rag_context["testing_recommendations"][:2]:
                enhanced_strategy.append(f"  - {rec['content']}")

        # 添加基于安全考虑的策略
        if rag_context.get("security_considerations"):
            enhanced_strategy.append("基于知识库安全建议：")
            for sec in rag_context["security_considerations"][:2]:
                enhanced_strategy.append(f"  - {sec['content']}")

        # 添加基于错误处理的策略
        if rag_context.get("error_handling_patterns"):
            enhanced_strategy.append("基于知识库错误处理建议：")
            for err in rag_context["error_handling_patterns"][:2]:
                enhanced_strategy.append(f"  - {err['content']}")

        return enhanced_strategy

    async def _execute_streaming_rag(self, query: str, search_settings: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """执行流式RAG - 基于R2R官方文档"""
        try:
            if self.r2r_client is None:
                return None

            # 配置流式RAG
            rag_config = self.rag_config.get('rag_generation_config', {}).copy()
            rag_config['stream'] = True

            # 执行流式RAG调用
            result_stream = self.r2r_client.retrieval.rag(
                query=query,
                search_settings=search_settings,
                rag_generation_config=rag_config,
                include_web_search=self.rag_config.get('enable_web_search', False)
            )

            # 处理流式响应
            return await self._process_streaming_response(result_stream)

        except Exception as e:
            logger.error(f"流式RAG执行失败: {str(e)}")
            return None

    async def _process_streaming_response(self, result_stream) -> Dict[str, Any]:
        """处理流式响应"""
        try:
            # 导入流式事件类型
            from r2r import (
                CitationEvent, FinalAnswerEvent, MessageEvent, SearchResultsEvent
            )

            accumulated_answer = ""
            search_results = None
            citations = []

            for event in result_stream:
                if isinstance(event, SearchResultsEvent):
                    search_results = event.data.data
                    logger.info(f"收到搜索结果: {len(search_results.chunk_search_results)} 个文本块")

                elif isinstance(event, MessageEvent):
                    # 累积消息内容
                    if (event.data.delta and event.data.delta.content and
                        event.data.delta.content[0].type == 'text'):
                        content = event.data.delta.content[0].payload.value
                        accumulated_answer += content

                elif isinstance(event, CitationEvent):
                    if event.data.is_new:
                        citations.append({
                            'id': event.data.id,
                            'payload': event.data.payload,
                            'span': event.data.span
                        })

                elif isinstance(event, FinalAnswerEvent):
                    return {
                        'generated_answer': event.data.generated_answer,
                        'citations': event.data.citations,
                        'search_results': search_results,
                        'streaming': True
                    }

            # 如果没有收到FinalAnswerEvent，返回累积的结果
            return {
                'generated_answer': accumulated_answer,
                'citations': citations,
                'search_results': search_results,
                'streaming': True
            }

        except ImportError:
            logger.warning("R2R流式事件类型未找到，跳过流式处理")
            return None
        except Exception as e:
            logger.error(f"处理流式响应失败: {str(e)}")
            return None

    def _build_context_aware_search_query(self, message: AnalysisInput) -> str:
        """构建上下文感知的搜索查询 - 优化版本"""
        # 提取API基本信息
        api_title = message.api_info.title
        api_description = message.api_info.description
        base_url = message.api_info.base_url

        # 分析API类型和特征
        api_characteristics = self._analyze_api_characteristics(message)

        # 提取端点信息
        endpoint_summaries = []
        for endpoint in message.endpoints:
            summary = f"{endpoint.method.value} {endpoint.path}"
            if endpoint.summary:
                summary += f" - {endpoint.summary}"

            # 添加参数信息
            if endpoint.parameters:
                param_types = [p.location.value for p in endpoint.parameters]
                summary += f" (参数: {', '.join(set(param_types))})"

            endpoint_summaries.append(summary)

        # 提取错误码和测试建议
        error_info = self._extract_error_information(message)
        testing_info = self._extract_testing_information(message)

        # 构建结构化查询
        search_query = f"""
API接口智能分析查询：

## 基本信息
- 接口名称：{api_title}
- 接口描述：{api_description}
- 基础URL：{base_url}
- API特征：{', '.join(api_characteristics)}

## 端点详情
{chr(10).join(f"- {summary}" for summary in endpoint_summaries)}

## 错误码分析
{error_info}

## 现有测试建议
{testing_info}

## 搜索目标
基于以上API特征，请查找：
1. 相似API的依赖关系模式和最佳实践
2. 针对{', '.join(api_characteristics)}类型接口的专项测试策略
3. 相关的错误处理和异常场景处理方案
4. 安全性和性能优化建议
5. 接口集成和数据流分析

## 关键搜索词
{' '.join(self._generate_search_keywords(message, api_characteristics))}
"""

        return search_query.strip()

    def _analyze_api_characteristics(self, message: AnalysisInput) -> List[str]:
        """分析API特征"""
        characteristics = []

        # 基于API标题和描述分析
        title_desc = f"{message.api_info.title} {message.api_info.description}".lower()

        if any(word in title_desc for word in ["login", "登录", "auth", "认证"]):
            characteristics.append("认证接口")
        if any(word in title_desc for word in ["user", "用户", "customer", "客户"]):
            characteristics.append("用户管理")
        if any(word in title_desc for word in ["payment", "支付", "order", "订单"]):
            characteristics.append("业务核心")
        if any(word in title_desc for word in ["query", "查询", "search", "搜索"]):
            characteristics.append("查询接口")

        # 基于HTTP方法分析
        methods = [ep.method.value for ep in message.endpoints]
        if "POST" in methods:
            characteristics.append("数据提交")
        if "GET" in methods:
            characteristics.append("数据获取")
        if any(m in methods for m in ["PUT", "PATCH"]):
            characteristics.append("数据更新")
        if "DELETE" in methods:
            characteristics.append("数据删除")

        return characteristics or ["通用接口"]

    def _extract_error_information(self, message: AnalysisInput) -> str:
        """提取错误信息"""
        error_codes = []
        for endpoint in message.endpoints:
            if hasattr(endpoint, 'extended_info') and endpoint.extended_info:
                error_codes_dict = endpoint.extended_info.get('error_codes', {})
                for code, desc in error_codes_dict.items():
                    error_codes.append(f"{code}: {desc}")

        return "\n".join(f"- {code}" for code in error_codes) if error_codes else "- 无特定错误码信息"

    def _extract_testing_information(self, message: AnalysisInput) -> str:
        """提取测试信息"""
        testing_recommendations = []
        for endpoint in message.endpoints:
            if hasattr(endpoint, 'extended_info') and endpoint.extended_info:
                test_recs = endpoint.extended_info.get('testing_recommendations', [])
                for rec in test_recs:
                    if isinstance(rec, dict):
                        category = rec.get('category', 'general')
                        description = rec.get('description', '')
                        testing_recommendations.append(f"{category}: {description}")

        return "\n".join(f"- {rec}" for rec in testing_recommendations) if testing_recommendations else "- 无现有测试建议"

    def _generate_search_keywords(self, message: AnalysisInput, characteristics: List[str]) -> List[str]:
        """生成搜索关键词"""
        keywords = ["API", "接口", "测试", "依赖关系"]

        # 添加特征相关关键词
        keyword_mapping = {
            "认证接口": ["authentication", "login", "token", "session"],
            "用户管理": ["user management", "customer", "account"],
            "业务核心": ["business logic", "transaction", "workflow"],
            "查询接口": ["query", "search", "filter", "pagination"],
            "数据提交": ["validation", "input", "form", "submission"],
            "数据获取": ["retrieval", "response", "output", "format"],
            "数据更新": ["update", "modification", "patch", "versioning"],
            "数据删除": ["deletion", "cleanup", "cascade", "soft delete"]
        }

        for char in characteristics:
            keywords.extend(keyword_mapping.get(char, []))

        # 添加API特定关键词
        api_words = message.api_info.title.lower().split()
        keywords.extend([word for word in api_words if len(word) > 2])

        return list(set(keywords))  # 去重
