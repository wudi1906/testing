"""
API数据持久化智能体
负责将解析后的接口信息存储到数据库中

核心职责：
1. 接收API文档解析结果
2. 将接口信息存储到数据库
3. 处理参数和响应数据的存储
4. 维护数据的完整性和一致性
"""
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from loguru import logger

from autogen_core import message_handler, type_subscription, MessageContext, TopicId
from tortoise.transactions import in_transaction

from app.agents.api_automation.base_api_agent import BaseApiAutomationAgent
from app.core.types import AgentTypes, TopicTypes
from app.models.api_automation import (
    ApiDocument, ApiInterface, ApiParameter as DbApiParameter,
    ApiResponse as DbApiResponse, TestScript
)
from .schemas import DocumentParseOutput, ParsedEndpoint, ApiParameter, ApiResponse, ScriptPersistenceInput


class ApiDataPersistenceInput:
    """数据持久化输入模型"""
    def __init__(self, parse_result: DocumentParseOutput):
        self.session_id = parse_result.session_id
        self.document_id = parse_result.document_id
        self.file_name = parse_result.file_name
        self.doc_format = parse_result.doc_format
        self.api_info = parse_result.api_info
        self.endpoints = parse_result.endpoints
        self.confidence_score = parse_result.confidence_score
        self.processing_time = parse_result.processing_time
        self.extended_info = parse_result.extended_info
        self.raw_parsed_data = parse_result.raw_parsed_data
        self.parse_errors = parse_result.parse_errors
        self.parse_warnings = parse_result.parse_warnings


@type_subscription(topic_type=TopicTypes.API_DATA_PERSISTENCE.value)
class ApiDataPersistenceAgent(BaseApiAutomationAgent):
    """
    API数据持久化智能体
    
    负责将API文档解析结果存储到数据库中，
    包括接口信息、参数、响应等详细数据。
    """

    def __init__(self, model_client_instance=None, agent_config=None, **kwargs):
        """初始化API数据持久化智能体"""
        super().__init__(
            agent_type=AgentTypes.API_DATA_PERSISTENCE,
            model_client_instance=model_client_instance,
            **kwargs
        )

        self.agent_config = agent_config or {}
        
        # 持久化统计指标
        self.persistence_metrics = {
            "total_documents_processed": 0,
            "total_interfaces_stored": 0,
            "total_parameters_stored": 0,
            "total_responses_stored": 0,
            "successful_saves": 0,
            "failed_saves": 0
        }

        logger.info(f"API数据持久化智能体初始化完成: {self.agent_name}")

    @message_handler
    async def handle_persistence_request(
        self,
        message: DocumentParseOutput,
        ctx: MessageContext
    ) -> None:
        """处理数据持久化请求 - 主要入口点"""
        start_time = datetime.now()
        self.persistence_metrics["total_documents_processed"] += 1

        try:
            logger.info(f"开始存储API数据: {message.file_name}")

            # 创建输入对象
            persistence_input = ApiDataPersistenceInput(message)
            
            # 在事务中执行数据存储
            async with in_transaction() as conn:
                # 1. 更新或创建API文档记录
                document = await self._update_api_document(persistence_input, conn)
                
                # 2. 存储接口信息
                interfaces = await self._store_interfaces(document, persistence_input, conn)
                
                # 3. 存储参数信息
                await self._store_parameters(interfaces, persistence_input, conn)
                
                # 4. 存储响应信息
                await self._store_responses(interfaces, persistence_input, conn)

            # 更新统计指标
            processing_time = (datetime.now() - start_time).total_seconds()
            self.persistence_metrics["successful_saves"] += 1
            self.persistence_metrics["total_interfaces_stored"] += len(message.endpoints)
            self._update_metrics("data_persistence", True, processing_time)

            logger.info(f"API数据存储完成: {message.file_name}, 接口数: {len(message.endpoints)}")

        except Exception as e:
            self.persistence_metrics["failed_saves"] += 1
            self._update_metrics("data_persistence", False)
            error_info = self._handle_common_error(e, "data_persistence")
            logger.error(f"API数据存储失败: {error_info}")

    @message_handler
    async def handle_script_persistence_request(
        self,
        message: ScriptPersistenceInput,
        ctx: MessageContext
    ) -> None:
        """处理脚本持久化请求"""
        start_time = datetime.now()

        try:
            logger.info(f"开始存储脚本数据: interface_id={message.interface_id}, 脚本数量={len(message.scripts)}")

            # 在事务中执行脚本存储
            async with in_transaction() as conn:
                # 获取文档信息
                document = await ApiDocument.filter(doc_id=message.document_id).using_db(conn).first()
                if not document:
                    logger.error(f"文档不存在: {message.document_id}")
                    return

                # 获取接口信息
                interface = await ApiInterface.filter(
                    interface_id=message.interface_id
                ).using_db(conn).first()

                if not interface:
                    logger.error(f"接口不存在: {message.interface_id}")
                    return

                # 存储脚本信息
                for script in message.scripts:
                    # 检查是否已存在相同的脚本
                    existing_script = await TestScript.filter(
                        script_id=script.script_id
                    ).using_db(conn).first()

                    if existing_script:
                        # 更新现有脚本
                        existing_script.name = script.script_name
                        existing_script.description = f"为接口 {interface.name} 生成的测试脚本"
                        existing_script.file_name = f"{script.script_name}.py"
                        existing_script.content = script.script_content
                        existing_script.file_path = script.file_path
                        existing_script.framework = script.framework
                        existing_script.dependencies = script.dependencies
                        existing_script.requirements = message.requirements_txt
                        existing_script.updated_at = datetime.now()

                        await existing_script.save(using_db=conn)
                        logger.info(f"更新脚本: {script.script_id}")
                    else:
                        # 创建新脚本
                        await TestScript.create(
                            script_id=script.script_id,
                            name=script.script_name,
                            description=f"为接口 {interface.name} 生成的测试脚本",
                            file_name=f"{script.script_name}.py",
                            test_case_id=message.interface_id,  # 使用接口ID作为测试用例ID
                            document=document,
                            content=script.script_content,
                            file_path=script.file_path,
                            framework=script.framework,
                            dependencies=script.dependencies,
                            requirements=message.requirements_txt,
                            timeout=300,  # 默认5分钟超时
                            retry_count=3,  # 默认重试3次
                            parallel_execution=True,
                            status="READY",
                            is_executable=True,
                            using_db=conn
                        )
                        logger.info(f"创建脚本: {script.script_id}")

            # 更新统计指标
            processing_time = (datetime.now() - start_time).total_seconds()
            self._update_metrics("script_persistence", True, processing_time)

            logger.info(f"脚本存储完成: interface_id={message.interface_id}, 脚本数量={len(message.scripts)}")

        except Exception as e:
            self._update_metrics("script_persistence", False)
            error_info = self._handle_common_error(e, "script_persistence")
            logger.error(f"脚本存储失败: {error_info}")

    async def _update_api_document(
        self, 
        persistence_input: ApiDataPersistenceInput, 
        conn
    ) -> ApiDocument:
        """更新或创建API文档记录"""
        try:
            # 尝试获取现有文档
            document = await ApiDocument.filter(
                doc_id=persistence_input.document_id
            ).using_db(conn).first()

            if document:
                # 更新现有文档
                document.api_info = {
                    "title": persistence_input.api_info.title,
                    "version": persistence_input.api_info.version,
                    "description": persistence_input.api_info.description,
                    "base_url": persistence_input.api_info.base_url,
                    "contact": persistence_input.api_info.contact,
                    "license": persistence_input.api_info.license
                }
                document.endpoints_count = len(persistence_input.endpoints)
                document.confidence_score = persistence_input.confidence_score
                document.processing_time = persistence_input.processing_time
                document.parse_errors = persistence_input.parse_errors
                document.parse_warnings = persistence_input.parse_warnings
                document.updated_at = datetime.now()
                
                await document.save(using_db=conn)
                logger.info(f"更新API文档记录: {document.doc_id}")
            else:
                # 创建新文档记录
                document = await ApiDocument.create(
                    doc_id=persistence_input.document_id,
                    session_id=persistence_input.session_id,
                    file_name=persistence_input.file_name,
                    file_path="",  # 这里可以根据需要设置
                    doc_format=persistence_input.doc_format.value,
                    api_info={
                        "title": persistence_input.api_info.title,
                        "version": persistence_input.api_info.version,
                        "description": persistence_input.api_info.description,
                        "base_url": persistence_input.api_info.base_url,
                        "contact": persistence_input.api_info.contact,
                        "license": persistence_input.api_info.license
                    },
                    endpoints_count=len(persistence_input.endpoints),
                    confidence_score=persistence_input.confidence_score,
                    processing_time=persistence_input.processing_time,
                    parse_errors=persistence_input.parse_errors,
                    parse_warnings=persistence_input.parse_warnings,
                    using_db=conn
                )
                logger.info(f"创建API文档记录: {document.doc_id}")

            return document

        except Exception as e:
            logger.error(f"更新API文档记录失败: {str(e)}")
            raise

    async def _store_interfaces(
        self, 
        document: ApiDocument, 
        persistence_input: ApiDataPersistenceInput, 
        conn
    ) -> Dict[str, ApiInterface]:
        """存储接口信息"""
        interfaces = {}
        
        try:
            # 删除现有的接口记录（如果是更新）
            await ApiInterface.filter(document=document).using_db(conn).delete()
            
            for endpoint in persistence_input.endpoints:
                interface = await ApiInterface.create(
                    interface_id=str(uuid.uuid4()),
                    document=document,
                    endpoint_id=endpoint.endpoint_id,
                    name=endpoint.summary or f"{endpoint.method} {endpoint.path}",
                    path=endpoint.path,
                    method=endpoint.method,
                    summary=endpoint.summary,
                    description=endpoint.description,
                    api_title=persistence_input.api_info.title,
                    api_version=persistence_input.api_info.version,
                    base_url=persistence_input.api_info.base_url,
                    tags=endpoint.tags,
                    auth_required=endpoint.auth_required,
                    is_deprecated=endpoint.deprecated,
                    confidence_score=persistence_input.confidence_score,
                    extended_info=persistence_input.extended_info,
                    raw_data=persistence_input.raw_parsed_data,
                    using_db=conn
                )
                
                interfaces[endpoint.endpoint_id] = interface
                logger.debug(f"存储接口: {interface.name}")

            logger.info(f"存储接口信息完成，共 {len(interfaces)} 个接口")
            return interfaces

        except Exception as e:
            logger.error(f"存储接口信息失败: {str(e)}")
            raise

    async def _store_parameters(
        self, 
        interfaces: Dict[str, ApiInterface], 
        persistence_input: ApiDataPersistenceInput, 
        conn
    ) -> None:
        """存储参数信息"""
        try:
            total_parameters = 0
            
            for endpoint in persistence_input.endpoints:
                interface = interfaces.get(endpoint.endpoint_id)
                if not interface:
                    continue
                
                # 删除现有参数记录
                await DbApiParameter.filter(interface=interface).using_db(conn).delete()
                
                for param in endpoint.parameters:
                    await DbApiParameter.create(
                        parameter_id=str(uuid.uuid4()),
                        interface=interface,
                        name=param.name,
                        location=param.location.value,
                        data_type=param.data_type.value,
                        required=param.required,
                        description=param.description,
                        example=str(param.example) if param.example is not None else None,
                        constraints=param.constraints,
                        using_db=conn
                    )
                    total_parameters += 1

            self.persistence_metrics["total_parameters_stored"] += total_parameters
            logger.info(f"存储参数信息完成，共 {total_parameters} 个参数")

        except Exception as e:
            logger.error(f"存储参数信息失败: {str(e)}")
            raise

    async def _store_responses(
        self, 
        interfaces: Dict[str, ApiInterface], 
        persistence_input: ApiDataPersistenceInput, 
        conn
    ) -> None:
        """存储响应信息"""
        try:
            total_responses = 0
            
            for endpoint in persistence_input.endpoints:
                interface = interfaces.get(endpoint.endpoint_id)
                if not interface:
                    continue
                
                # 删除现有响应记录
                await DbApiResponse.filter(interface=interface).using_db(conn).delete()
                
                for response in endpoint.responses:
                    await DbApiResponse.create(
                        response_id=str(uuid.uuid4()),
                        interface=interface,
                        status_code=response.status_code,
                        description=response.description,
                        content_type=response.content_type,
                        response_schema=response.response_schema,
                        example=response.example,
                        using_db=conn
                    )
                    total_responses += 1

            self.persistence_metrics["total_responses_stored"] += total_responses
            logger.info(f"存储响应信息完成，共 {total_responses} 个响应")

        except Exception as e:
            logger.error(f"存储响应信息失败: {str(e)}")
            raise

    def get_persistence_metrics(self) -> Dict[str, Any]:
        """获取持久化统计指标"""
        return {
            **self.persistence_metrics,
            **self.common_metrics
        }
