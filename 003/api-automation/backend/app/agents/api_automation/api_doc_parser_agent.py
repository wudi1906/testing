"""
API文档解析智能体 - 重新设计版本
专门负责解析各种格式的API文档，提取接口信息并输出标准化数据

核心职责：
1. 解析多种格式的API文档（OpenAPI、Swagger、Postman、PDF等）
2. 提取API基本信息和端点详情
3. 标准化数据结构，为后续智能体提供清晰的输入
4. 进行解析质量评估和错误处理

数据流：DocumentParseInput -> 智能解析 -> DocumentParseOutput
"""
import json
import uuid
import yaml
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

from autogen_core import message_handler, type_subscription, MessageContext, TopicId
from loguru import logger

from app.agents.api_automation.base_api_agent import BaseApiAutomationAgent
from app.core.types import AgentTypes, TopicTypes

# 导入重新设计的数据模型
from .schemas import (
    DocumentParseInput, DocumentParseOutput, ParsedEndpoint, ParsedApiInfo,
    ApiParameter, ApiResponse, DocumentFormat, HttpMethod, ParameterLocation, 
    DataType, AgentPrompts
)


@type_subscription(topic_type=TopicTypes.API_DOC_PARSER.value)
class ApiDocParserAgent(BaseApiAutomationAgent):
    """
    API文档解析智能体
    
    专注于将各种格式的API文档转换为标准化的数据结构，
    为后续的接口分析智能体提供清晰、完整的输入数据。
    """

    def __init__(self, model_client_instance=None, agent_config=None, **kwargs):
        """初始化API文档解析智能体"""
        super().__init__(
            agent_type=AgentTypes.API_DOC_PARSER,
            model_client_instance=model_client_instance,
            **kwargs
        )

        self.agent_config = agent_config or {}
        self._initialize_assistant_agent()

        # 解析统计指标
        self.parse_metrics = {
            "total_documents": 0,
            "successful_parses": 0,
            "failed_parses": 0,
            "total_endpoints_extracted": 0,
            "avg_confidence_score": 0.0
        }

        logger.info(f"API文档解析智能体初始化完成: {self.agent_name}")

    @message_handler
    async def handle_document_parse_request(
        self,
        message: DocumentParseInput,
        ctx: MessageContext
    ) -> None:
        """处理文档解析请求 - 主要入口点"""
        start_time = datetime.now()
        self.parse_metrics["total_documents"] += 1

        try:
            logger.info(f"开始解析API文档: {message.file_name}")

            # 1. 读取文档内容
            document_content = await self._read_document_content(message)
            
            # 2. 检测文档格式
            detected_format = self._detect_document_format(document_content, message.doc_format)
            
            # 3. 使用大模型智能解析文档
            parse_result = await self._intelligent_parse_document(
                document_content, message.file_name, detected_format
            )
            
            # 4. 构建增强的输出结果 - 保留所有有价值信息
            output = DocumentParseOutput(
                session_id=message.session_id,
                file_name=message.file_name,
                doc_format=detected_format,
                api_info=parse_result["api_info"],
                endpoints=parse_result["endpoints"],
                parse_errors=self._format_errors_for_output(parse_result.get("errors", [])),
                parse_warnings=self._format_warnings_for_output(parse_result.get("warnings", [])),
                confidence_score=parse_result.get("confidence_score", 0.8),
                processing_time=(datetime.now() - start_time).total_seconds(),

                # 保留扩展信息
                extended_info=parse_result.get("extended_info", {}),
                raw_parsed_data=parse_result.get("raw_parsed_data", {}),
                quality_assessment=parse_result.get("extended_info", {}).get("quality_assessment", {}),
                testing_recommendations=parse_result.get("extended_info", {}).get("testing_recommendations", []),
                error_codes=parse_result.get("extended_info", {}).get("error_codes", {}),
                global_headers=parse_result.get("extended_info", {}).get("global_headers", {}),
                security_schemes=parse_result.get("extended_info", {}).get("security_schemes", {}),
                servers=parse_result.get("extended_info", {}).get("servers", [])
            )

            # 5. 更新统计指标
            self.parse_metrics["successful_parses"] += 1
            self.parse_metrics["total_endpoints_extracted"] += len(output.endpoints)
            self._update_metrics("document_parse", True, output.processing_time)

            # 6. 发送结果到数据持久化智能体
            await self._send_to_data_persistence(output, ctx)

            # 7. 发送结果到接口分析智能体
            # await self._send_to_api_analyzer(output, ctx)

            logger.info(f"文档解析完成: {message.file_name}, 提取端点数: {len(output.endpoints)}")

        except Exception as e:
            self.parse_metrics["failed_parses"] += 1
            self._update_metrics("document_parse", False)
            error_info = self._handle_common_error(e, "document_parse")
            logger.error(f"文档解析失败: {error_info}")

    async def _read_document_content(self, message: DocumentParseInput) -> str:
        """读取文档内容"""
        try:
            # 如果消息中已包含内容，直接使用
            if message.file_content:
                return message.file_content
            
            # 否则从文件路径读取
            file_path = Path(message.file_path)
            if not file_path.exists():
                raise FileNotFoundError(f"文档文件不存在: {message.file_path}")
            
            # 根据文件扩展名选择读取方式
            if file_path.suffix.lower() in ['.json', '.yaml', '.yml']:
                return file_path.read_text(encoding='utf-8')
            elif file_path.suffix.lower() == '.pdf':
                return await self._extract_pdf_content(file_path)
            else:
                return file_path.read_text(encoding='utf-8')
                
        except Exception as e:
            logger.error(f"读取文档内容失败: {str(e)}")
            raise

    def _detect_document_format(self, content: str, specified_format: DocumentFormat) -> DocumentFormat:
        """检测文档格式"""
        if specified_format != DocumentFormat.AUTO:
            return specified_format
        
        try:
            # 尝试解析为JSON
            data = json.loads(content)
            if "swagger" in data:
                return DocumentFormat.SWAGGER
            elif "openapi" in data:
                return DocumentFormat.OPENAPI
            elif "info" in data and "item" in data:
                return DocumentFormat.POSTMAN
        except json.JSONDecodeError:
            pass
        
        try:
            # 尝试解析为YAML
            data = yaml.safe_load(content)
            if isinstance(data, dict):
                if "swagger" in data:
                    return DocumentFormat.SWAGGER
                elif "openapi" in data:
                    return DocumentFormat.OPENAPI
        except yaml.YAMLError:
            pass
        
        # 默认返回OpenAPI格式
        return DocumentFormat.OPENAPI

    async def _intelligent_parse_document(
        self, 
        content: str, 
        file_name: str, 
        doc_format: DocumentFormat
    ) -> Dict[str, Any]:
        """使用大模型智能解析文档"""
        try:
            # 构建解析任务提示词
            task_prompt = AgentPrompts.DOCUMENT_PARSER_TASK_PROMPT.format(
                file_name=file_name,
                doc_format=doc_format.value,
                document_content=content[:10000]  # 限制内容长度
            )
            
            # 使用AssistantAgent进行智能解析
            result_content = await self._run_assistant_agent(task_prompt)
            
            if result_content:
                # 提取JSON结果
                parsed_data = self._extract_json_from_content(result_content)
                if parsed_data:
                    return self._convert_to_standard_format(parsed_data)

        except Exception as e:
            logger.error(f"智能解析文档失败: {str(e)}")
            return await self._fallback_parse_document(content, doc_format)

    def _convert_to_standard_format(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """将解析结果转换为标准格式 - 保留更多有价值信息"""
        try:
            logger.info("开始转换解析结果为标准格式，保留完整信息")

            # 提取API基本信息 - 支持多种字段名
            api_info = self._extract_api_info(parsed_data)

            # 提取端点信息 - 保留更多细节
            endpoints = self._extract_endpoints_with_details(parsed_data)

            # 构建增强的标准格式，保留原始数据的丰富信息
            # 处理错误和警告信息，确保格式正确
            raw_errors = parsed_data.get("errors", parsed_data.get("parsing_issues", []))
            raw_warnings = parsed_data.get("warnings", [])

            standard_result = {
                "api_info": api_info,
                "endpoints": endpoints,
                "errors": self._format_errors_for_output(raw_errors),
                "warnings": self._format_warnings_for_output(raw_warnings),
                "confidence_score": parsed_data.get("confidence_score", 0.8),

                # 保留额外的有价值信息
                "extended_info": {
                    "document_type": parsed_data.get("document_type", "unknown"),
                    "quality_assessment": parsed_data.get("quality_assessment", {}),
                    "testing_recommendations": parsed_data.get("testing_recommendations", []),
                    "error_codes": parsed_data.get("error_codes", {}),
                    "security_schemes": parsed_data.get("security_schemes", {}),
                    "global_headers": parsed_data.get("global_headers", {}),
                    "global_parameters": parsed_data.get("global_parameters", {}),
                    "rate_limiting": parsed_data.get("rate_limiting", {}),
                    "versioning_strategy": parsed_data.get("versioning_strategy", ""),
                    "servers": parsed_data.get("servers", []),
                    "schemas": parsed_data.get("schemas", {}),
                    "parsing_issues": parsed_data.get("parsing_issues", [])
                },

                # 保留原始解析数据的完整副本，供后续智能体使用
                "raw_parsed_data": parsed_data
            }

            logger.info(f"标准格式转换完成，保留了 {len(endpoints)} 个端点和丰富的扩展信息")
            return standard_result

        except Exception as e:
            logger.error(f"转换标准格式失败: {str(e)}")
            # 即使转换失败，也要保留原始数据
            return {
                "api_info": ParsedApiInfo(
                    title=parsed_data.get("title", "Unknown API"),
                    version=parsed_data.get("api_version", "1.0.0"),
                    description=parsed_data.get("description", ""),
                    base_url=parsed_data.get("base_url", "")
                ),
                "endpoints": [],
                "errors": [f"标准格式转换失败: {str(e)}"],
                "warnings": [],
                "confidence_score": 0.5,
                "extended_info": {},
                "raw_parsed_data": parsed_data  # 确保原始数据不丢失
            }

    def _extract_api_info(self, parsed_data: Dict[str, Any]) -> ParsedApiInfo:
        """提取API基本信息 - 支持多种字段名"""
        try:
            # 支持多种可能的字段名
            title = (parsed_data.get("title") or
                    parsed_data.get("api_title") or
                    parsed_data.get("name") or
                    "Unknown API")

            version = (parsed_data.get("api_version") or
                      parsed_data.get("version") or
                      parsed_data.get("info", {}).get("version") or
                      "1.0.0")

            description = (parsed_data.get("description") or
                          parsed_data.get("api_description") or
                          parsed_data.get("info", {}).get("description") or
                          "")

            base_url = (parsed_data.get("base_url") or
                       parsed_data.get("baseUrl") or
                       parsed_data.get("host") or
                       parsed_data.get("servers", [{}])[0].get("url", "") or
                       "")

            # 提取联系信息
            contact = parsed_data.get("contact", {})
            if not contact and "info" in parsed_data:
                contact = parsed_data["info"].get("contact", {})

            # 提取许可证信息
            license_info = parsed_data.get("license", {})
            if not license_info and "info" in parsed_data:
                license_info = parsed_data["info"].get("license", {})

            return ParsedApiInfo(
                title=title,
                version=version,
                description=description,
                base_url=base_url,
                contact=contact,
                license=license_info
            )

        except Exception as e:
            logger.warning(f"提取API基本信息失败: {str(e)}")
            return ParsedApiInfo(
                title="Unknown API",
                version="1.0.0",
                description="",
                base_url=""
            )

    def _extract_endpoints_with_details(self, parsed_data: Dict[str, Any]) -> List[ParsedEndpoint]:
        """提取端点信息 - 保留更多细节"""
        endpoints = []

        try:
            endpoints_data = parsed_data.get("endpoints", [])
            logger.info(f"开始提取 {len(endpoints_data)} 个端点的详细信息")

            for endpoint_data in endpoints_data:
                try:
                    endpoint = self._create_enhanced_parsed_endpoint(endpoint_data)
                    if endpoint:
                        endpoints.append(endpoint)
                        logger.debug(f"成功提取端点: {endpoint.method.value} {endpoint.path}")
                    else:
                        logger.warning(f"端点创建失败: {endpoint_data.get('path', 'unknown')}")

                except Exception as e:
                    logger.warning(f"处理端点失败: {str(e)}, 数据: {endpoint_data}")
                    continue

            logger.info(f"成功提取 {len(endpoints)} 个端点")
            return endpoints

        except Exception as e:
            logger.error(f"提取端点信息失败: {str(e)}")
            return []

    def _create_enhanced_parsed_endpoint(self, endpoint_data: Dict[str, Any]) -> Optional[ParsedEndpoint]:
        """创建增强的解析端点对象 - 保留更多信息"""
        try:
            # 提取基本信息 - 支持多种字段名
            path = (endpoint_data.get("path") or
                   endpoint_data.get("url") or
                   endpoint_data.get("endpoint") or
                   "")

            method_str = (endpoint_data.get("method") or
                         endpoint_data.get("http_method") or
                         endpoint_data.get("verb") or
                         "GET").upper()

            # 验证HTTP方法
            try:
                method = HttpMethod(method_str)
            except ValueError:
                logger.warning(f"无效的HTTP方法: {method_str}, 使用GET作为默认值")
                method = HttpMethod.GET

            # 提取描述信息
            summary = (endpoint_data.get("summary") or
                      endpoint_data.get("title") or
                      endpoint_data.get("name") or
                      "")

            description = (endpoint_data.get("description") or
                          endpoint_data.get("desc") or
                          endpoint_data.get("detail") or
                          "")

            # 提取标签
            tags = endpoint_data.get("tags", [])
            if isinstance(tags, str):
                tags = [tags]
            elif not isinstance(tags, list):
                tags = []

            # 提取参数 - 增强处理
            parameters = self._extract_enhanced_parameters(endpoint_data)

            # 提取响应 - 增强处理
            responses = self._extract_enhanced_responses(endpoint_data)

            # 提取其他信息
            auth_required = endpoint_data.get("auth_required", False)
            deprecated = endpoint_data.get("deprecated", False)
            operation_id = endpoint_data.get("operation_id", endpoint_data.get("operationId", ""))

            # 创建端点对象
            endpoint = ParsedEndpoint(
                path=path,
                method=method,
                summary=summary,
                description=description,
                tags=tags,
                parameters=parameters,
                responses=responses,
                auth_required=auth_required,
                deprecated=deprecated
            )

            # 将额外信息存储在端点对象中（如果支持的话）
            if hasattr(endpoint, 'extended_info'):
                endpoint.extended_info = {
                    "operation_id": operation_id,
                    "request_body": endpoint_data.get("request_body", {}),
                    "security": endpoint_data.get("security", []),
                    "servers": endpoint_data.get("servers", []),
                    "callbacks": endpoint_data.get("callbacks", {}),
                    "examples": endpoint_data.get("examples", {}),
                    "external_docs": endpoint_data.get("externalDocs", {}),
                    "raw_data": endpoint_data  # 保留原始数据
                }

            return endpoint

        except Exception as e:
            logger.error(f"创建增强端点对象失败: {str(e)}")
            return None

    def _extract_enhanced_parameters(self, endpoint_data: Dict[str, Any]) -> List[ApiParameter]:
        """提取增强的参数信息"""
        parameters = []

        try:
            # 从多个可能的字段中提取参数
            params_data = (endpoint_data.get("parameters", []) or
                          endpoint_data.get("params", []) or
                          endpoint_data.get("arguments", []) or
                          [])

            for param_data in params_data:
                try:
                    # 支持多种参数位置表示
                    location_str = (param_data.get("in") or
                                   param_data.get("location") or
                                   param_data.get("place") or
                                   "query")

                    # 映射参数位置
                    location_mapping = {
                        "query": ParameterLocation.QUERY,
                        "header": ParameterLocation.HEADER,
                        "path": ParameterLocation.PATH,
                        "body": ParameterLocation.BODY,
                        "form": ParameterLocation.FORM,
                        "formData": ParameterLocation.FORM,
                        "cookie": ParameterLocation.COOKIE
                    }

                    location = location_mapping.get(location_str.lower(), ParameterLocation.QUERY)

                    # 支持多种数据类型表示
                    type_str = (param_data.get("type") or
                               param_data.get("data_type") or
                               param_data.get("dataType") or
                               "string")

                    # 映射数据类型
                    type_mapping = {
                        "string": DataType.STRING,
                        "integer": DataType.INTEGER,
                        "number": DataType.NUMBER,
                        "boolean": DataType.BOOLEAN,
                        "array": DataType.ARRAY,
                        "object": DataType.OBJECT,
                        "file": DataType.STRING
                    }

                    data_type = type_mapping.get(type_str.lower(), DataType.STRING)

                    parameter = ApiParameter(
                        name=param_data.get("name", ""),
                        location=location,
                        data_type=data_type,
                        required=param_data.get("required", False),
                        description=param_data.get("description", ""),
                        example=param_data.get("example"),
                        constraints=param_data.get("constraints", {})
                    )
                    parameters.append(parameter)

                except Exception as e:
                    logger.warning(f"处理参数失败: {str(e)}, 参数数据: {param_data}")
                    continue

            # 处理请求体参数
            request_body = endpoint_data.get("request_body", {})
            if request_body:
                body_param = ApiParameter(
                    name="body",
                    location=ParameterLocation.BODY,
                    data_type=DataType.OBJECT,
                    required=request_body.get("required", False),
                    description=request_body.get("description", "请求体"),
                    example=request_body.get("example"),
                    constraints={
                        "content_type": request_body.get("content_type", "application/json"),
                        "schema": request_body.get("schema", {})
                    }
                )
                parameters.append(body_param)

            return parameters

        except Exception as e:
            logger.error(f"提取参数信息失败: {str(e)}")
            return []

    def _extract_enhanced_responses(self, endpoint_data: Dict[str, Any]) -> List[ApiResponse]:
        """提取增强的响应信息"""
        responses = []

        try:
            responses_data = endpoint_data.get("responses", {})

            for status_code, response_info in responses_data.items():
                try:
                    response = ApiResponse(
                        status_code=str(status_code),
                        description=response_info.get("description", ""),
                        content_type=response_info.get("content_type", "application/json"),
                        response_schema=response_info.get("schema", {}),
                        example=response_info.get("example")
                    )
                    responses.append(response)

                except Exception as e:
                    logger.warning(f"处理响应失败: {str(e)}, 响应数据: {response_info}")
                    continue

            # 如果没有响应定义，添加默认响应
            if not responses:
                default_response = ApiResponse(
                    status_code="200",
                    description="成功响应",
                    content_type="application/json",
                    response_schema={},
                    example=None
                )
                responses.append(default_response)

            return responses

        except Exception as e:
            logger.error(f"提取响应信息失败: {str(e)}")
            return []

    def _format_errors_for_output(self, errors: List) -> List[str]:
        """格式化错误信息为字符串列表"""
        formatted_errors = []

        try:
            for error in errors:
                if isinstance(error, dict):
                    # 如果是结构化错误对象，转换为描述性字符串
                    level = error.get("level", "error")
                    message = error.get("message", "")
                    location = error.get("location", "")
                    suggestion = error.get("suggestion", "")

                    error_str = f"[{level.upper()}]"
                    if location:
                        error_str += f" {location}:"
                    error_str += f" {message}"
                    if suggestion:
                        error_str += f" (建议: {suggestion})"

                    formatted_errors.append(error_str)
                elif isinstance(error, str):
                    # 如果已经是字符串，直接使用
                    formatted_errors.append(error)
                else:
                    # 其他类型，转换为字符串
                    formatted_errors.append(str(error))

        except Exception as e:
            logger.warning(f"格式化错误信息失败: {str(e)}")
            # 如果格式化失败，至少保留原始信息的字符串表示
            formatted_errors = [str(error) for error in errors]

        return formatted_errors

    def _format_warnings_for_output(self, warnings: List) -> List[str]:
        """格式化警告信息为字符串列表"""
        formatted_warnings = []

        try:
            for warning in warnings:
                if isinstance(warning, dict):
                    # 如果是结构化警告对象，转换为描述性字符串
                    level = warning.get("level", "warning")
                    message = warning.get("message", "")
                    location = warning.get("location", "")
                    suggestion = warning.get("suggestion", "")

                    warning_str = f"[{level.upper()}]"
                    if location:
                        warning_str += f" {location}:"
                    warning_str += f" {message}"
                    if suggestion:
                        warning_str += f" (建议: {suggestion})"

                    formatted_warnings.append(warning_str)
                elif isinstance(warning, str):
                    # 如果已经是字符串，直接使用
                    formatted_warnings.append(warning)
                else:
                    # 其他类型，转换为字符串
                    formatted_warnings.append(str(warning))

        except Exception as e:
            logger.warning(f"格式化警告信息失败: {str(e)}")
            # 如果格式化失败，至少保留原始信息的字符串表示
            formatted_warnings = [str(warning) for warning in warnings]

        return formatted_warnings

    def _create_parsed_endpoint(self, endpoint_data: Dict[str, Any]) -> Optional[ParsedEndpoint]:
        """创建解析后的端点对象"""
        try:
            # 解析参数
            parameters = []
            for param_data in endpoint_data.get("parameters", []):
                parameter = ApiParameter(
                    name=param_data.get("name", ""),
                    location=ParameterLocation(param_data.get("location", "query")),
                    data_type=DataType(param_data.get("data_type", "string")),
                    required=param_data.get("required", False),
                    description=param_data.get("description", ""),
                    example=param_data.get("example"),
                    constraints=param_data.get("constraints", {})
                )
                parameters.append(parameter)
            
            # 解析响应
            responses = []
            for resp_data in endpoint_data.get("responses", []):
                response = ApiResponse(
                    status_code=str(resp_data.get("status_code", "200")),
                    description=resp_data.get("description", ""),
                    content_type=resp_data.get("content_type", "application/json"),
                    response_schema=resp_data.get("schema", {}),
                    example=resp_data.get("example")
                )
                responses.append(response)
            
            # 创建端点对象
            endpoint = ParsedEndpoint(
                path=endpoint_data.get("path", ""),
                method=HttpMethod(endpoint_data.get("method", "GET")),
                summary=endpoint_data.get("summary", ""),
                description=endpoint_data.get("description", ""),
                tags=endpoint_data.get("tags", []),
                parameters=parameters,
                responses=responses,
                auth_required=endpoint_data.get("auth_required", False),
                deprecated=endpoint_data.get("deprecated", False)
            )
            
            return endpoint
            
        except Exception as e:
            logger.error(f"创建端点对象失败: {str(e)}")
            return None

    async def _fallback_parse_document(self, content: str, doc_format: DocumentFormat) -> Dict[str, Any]:
        """备用文档解析方法"""
        try:
            if doc_format in [DocumentFormat.OPENAPI, DocumentFormat.SWAGGER]:
                return await self._parse_openapi_document(content)
            elif doc_format == DocumentFormat.POSTMAN:
                return await self._parse_postman_collection(content)
            else:
                # 基础解析
                return {
                    "api_info": ParsedApiInfo(
                        title="Unknown API",
                        version="1.0.0",
                        description="Parsed by fallback method"
                    ),
                    "endpoints": [],
                    "errors": ["使用备用解析方法"],
                    "warnings": [],
                    "confidence_score": 0.5
                }
        except Exception as e:
            logger.error(f"备用解析失败: {str(e)}")
            raise

    async def _send_to_data_persistence(self, output: DocumentParseOutput, ctx: MessageContext):
        """发送解析结果到数据持久化智能体"""
        try:
            # 发送到数据持久化智能体
            await self.runtime.publish_message(
                output,
                topic_id=TopicId(type=TopicTypes.API_DATA_PERSISTENCE.value, source=self.agent_name)
            )

            logger.info(f"已发送解析结果到数据持久化智能体: {output.document_id}")

        except Exception as e:
            logger.error(f"发送到数据持久化智能体失败: {str(e)}")

    async def _send_to_api_analyzer(self, output: DocumentParseOutput, ctx: MessageContext):
        """发送解析结果到接口分析智能体"""
        try:
            from .schemas import AnalysisInput

            # 构建接口分析输入
            analysis_input = AnalysisInput(
                session_id=output.session_id,
                document_id=output.document_id,
                api_info=output.api_info,
                endpoints=output.endpoints,
                analysis_options={}
            )
            
            # 发送到接口分析智能体
            await self.runtime.publish_message(
                analysis_input,
                topic_id=TopicId(type=TopicTypes.API_ANALYZER.value, source=self.agent_name)
            )
            
            logger.info(f"已发送解析结果到接口分析智能体: {output.document_id}")
            
        except Exception as e:
            logger.error(f"发送到接口分析智能体失败: {str(e)}")

    async def _extract_pdf_content(self, file_path: Path) -> str:
        """提取PDF文档内容"""
        try:
            logger.info(f"开始提取PDF内容: {file_path.name}")

            # 方法1: 尝试使用PyPDF2提取文本
            try:
                import PyPDF2
                return await self._extract_with_pypdf2(file_path)
            except ImportError:
                logger.debug("PyPDF2未安装，尝试其他方法")
            except Exception as e:
                logger.warning(f"PyPDF2提取失败: {str(e)}")

            # # 方法2: 尝试使用pdfplumber提取文本
            # try:
            #     import pdfplumber
            #     return await self._extract_with_pdfplumber(file_path)
            # except ImportError:
            #     logger.debug("pdfplumber未安装，尝试其他方法")
            # except Exception as e:
            #     logger.warning(f"pdfplumber提取失败: {str(e)}")
            #
            # # 方法3: 尝试使用pymupdf (fitz)提取文本
            # try:
            #     import fitz  # PyMuPDF
            #     return await self._extract_with_pymupdf(file_path)
            # except ImportError:
            #     logger.debug("PyMuPDF未安装，尝试其他方法")
            # except Exception as e:
            #     logger.warning(f"PyMuPDF提取失败: {str(e)}")
            #
            # # 方法4: 尝试使用pdfminer提取文本
            # try:
            #     from pdfminer.high_level import extract_text
            #     return await self._extract_with_pdfminer(file_path)
            # except ImportError:
            #     logger.debug("pdfminer未安装")
            # except Exception as e:
            #     logger.warning(f"pdfminer提取失败: {str(e)}")

            # 方法5: 借助多模态大模型做ocr识别（推荐）、docling、marker等

            # 如果所有方法都失败，返回错误信息
            error_msg = f"无法提取PDF内容: {file_path.name}。请安装PDF解析库: pip install PyPDF2 pdfplumber PyMuPDF pdfminer.six"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        except Exception as e:
            logger.error(f"PDF内容提取失败: {str(e)}")
            raise

    async def _extract_with_pypdf2(self, file_path: Path) -> str:
        """使用PyPDF2提取PDF内容"""
        import PyPDF2

        text_content = []
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)

            for page_num, page in enumerate(pdf_reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text.strip():
                        text_content.append(f"=== 第{page_num + 1}页 ===\n{page_text}\n")
                except Exception as e:
                    logger.warning(f"PyPDF2提取第{page_num + 1}页失败: {str(e)}")
                    continue

        if not text_content:
            raise RuntimeError("PyPDF2未能提取到任何文本内容")

        return "\n".join(text_content)

    async def _extract_with_pdfplumber(self, file_path: Path) -> str:
        """使用pdfplumber提取PDF内容"""
        import pdfplumber

        text_content = []
        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                try:
                    page_text = page.extract_text()
                    if page_text and page_text.strip():
                        text_content.append(f"=== 第{page_num + 1}页 ===\n{page_text}\n")

                    # 尝试提取表格内容
                    tables = page.extract_tables()
                    if tables:
                        for table_num, table in enumerate(tables):
                            table_text = self._format_table_content(table, page_num + 1, table_num + 1)
                            text_content.append(table_text)

                except Exception as e:
                    logger.warning(f"pdfplumber提取第{page_num + 1}页失败: {str(e)}")
                    continue

        if not text_content:
            raise RuntimeError("pdfplumber未能提取到任何文本内容")

        return "\n".join(text_content)

    async def _extract_with_pymupdf(self, file_path: Path) -> str:
        """使用PyMuPDF提取PDF内容"""
        import fitz  # PyMuPDF

        text_content = []
        pdf_document = fitz.open(file_path)

        try:
            for page_num in range(pdf_document.page_count):
                try:
                    page = pdf_document[page_num]
                    page_text = page.get_text()

                    if page_text.strip():
                        text_content.append(f"=== 第{page_num + 1}页 ===\n{page_text}\n")

                    # 尝试提取表格
                    tables = page.find_tables()
                    if tables:
                        for table_num, table in enumerate(tables):
                            try:
                                table_data = table.extract()
                                table_text = self._format_table_content(table_data, page_num + 1, table_num + 1)
                                text_content.append(table_text)
                            except Exception as e:
                                logger.warning(f"提取表格失败: {str(e)}")

                except Exception as e:
                    logger.warning(f"PyMuPDF提取第{page_num + 1}页失败: {str(e)}")
                    continue
        finally:
            pdf_document.close()

        if not text_content:
            raise RuntimeError("PyMuPDF未能提取到任何文本内容")

        return "\n".join(text_content)

    async def _extract_with_pdfminer(self, file_path: Path) -> str:
        """使用pdfminer提取PDF内容"""
        from pdfminer.high_level import extract_text

        try:
            text_content = extract_text(str(file_path))
            if not text_content or not text_content.strip():
                raise RuntimeError("pdfminer未能提取到任何文本内容")

            return f"=== PDF文档内容 ===\n{text_content}"

        except Exception as e:
            logger.error(f"pdfminer提取失败: {str(e)}")
            raise

    def _format_table_content(self, table_data: list, page_num: int, table_num: int) -> str:
        """格式化表格内容"""
        try:
            if not table_data:
                return ""

            formatted_lines = [f"=== 第{page_num}页 表格{table_num} ==="]

            for row_num, row in enumerate(table_data):
                if row and any(cell for cell in row if cell):  # 跳过空行
                    # 清理和格式化单元格内容
                    cleaned_row = []
                    for cell in row:
                        if cell:
                            # 清理单元格内容
                            cleaned_cell = str(cell).strip().replace('\n', ' ').replace('\r', '')
                            cleaned_row.append(cleaned_cell)
                        else:
                            cleaned_row.append("")

                    # 使用制表符分隔
                    formatted_lines.append("\t".join(cleaned_row))

            formatted_lines.append("")  # 添加空行分隔
            return "\n".join(formatted_lines)

        except Exception as e:
            logger.warning(f"格式化表格内容失败: {str(e)}")
            return f"=== 第{page_num}页 表格{table_num} (格式化失败) ===\n"

    async def _parse_openapi_document(self, content: str) -> Dict[str, Any]:
        """解析OpenAPI/Swagger文档"""
        try:
            # 尝试JSON解析
            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                # 尝试YAML解析
                data = yaml.safe_load(content)

            # 提取基本信息
            info = data.get("info", {})
            api_info = ParsedApiInfo(
                title=info.get("title", "Unknown API"),
                version=info.get("version", "1.0.0"),
                description=info.get("description", ""),
                base_url=data.get("host", "") or data.get("servers", [{}])[0].get("url", ""),
                contact=info.get("contact", {}),
                license=info.get("license", {})
            )

            # 提取端点信息
            endpoints = []
            paths = data.get("paths", {})
            for path, methods in paths.items():
                for method, details in methods.items():
                    if method.upper() in [m.value for m in HttpMethod]:
                        endpoint_data = {
                            "path": path,
                            "method": method.upper(),
                            "summary": details.get("summary", ""),
                            "description": details.get("description", ""),
                            "tags": details.get("tags", []),
                            "parameters": self._extract_openapi_parameters(details),
                            "responses": self._extract_openapi_responses(details),
                            "auth_required": "security" in details,
                            "deprecated": details.get("deprecated", False)
                        }
                        endpoint = self._create_parsed_endpoint(endpoint_data)
                        if endpoint:
                            endpoints.append(endpoint)

            return {
                "api_info": api_info,
                "endpoints": endpoints,
                "errors": [],
                "warnings": [],
                "confidence_score": 0.9
            }

        except Exception as e:
            logger.error(f"OpenAPI文档解析失败: {str(e)}")
            raise

    def _extract_openapi_parameters(self, endpoint_details: Dict[str, Any]) -> List[Dict[str, Any]]:
        """提取OpenAPI参数信息"""
        parameters = []

        # 提取parameters字段
        for param in endpoint_details.get("parameters", []):
            parameters.append({
                "name": param.get("name", ""),
                "location": param.get("in", "query"),
                "data_type": param.get("type", "string"),
                "required": param.get("required", False),
                "description": param.get("description", ""),
                "example": param.get("example"),
                "constraints": {}
            })

        # 提取requestBody参数
        request_body = endpoint_details.get("requestBody", {})
        if request_body:
            content = request_body.get("content", {})
            for content_type, schema_info in content.items():
                parameters.append({
                    "name": "body",
                    "location": "body",
                    "data_type": "object",
                    "required": request_body.get("required", False),
                    "description": request_body.get("description", ""),
                    "example": schema_info.get("example"),
                    "constraints": {"content_type": content_type}
                })

        return parameters

    def _extract_openapi_responses(self, endpoint_details: Dict[str, Any]) -> List[Dict[str, Any]]:
        """提取OpenAPI响应信息"""
        responses = []

        for status_code, response_info in endpoint_details.get("responses", {}).items():
            responses.append({
                "status_code": status_code,
                "description": response_info.get("description", ""),
                "content_type": "application/json",
                "schema": response_info.get("schema", {}),  # 保持原字段名，在构建对象时会转换
                "example": response_info.get("example")
            })

        return responses

    async def _parse_postman_collection(self, content: str) -> Dict[str, Any]:
        """解析Postman Collection"""
        try:
            data = json.loads(content)

            # 提取基本信息
            info = data.get("info", {})
            api_info = ParsedApiInfo(
                title=info.get("name", "Postman Collection"),
                version=info.get("version", "1.0.0"),
                description=info.get("description", ""),
                base_url="",  # Postman中通常在变量中定义
                contact={},
                license={}
            )

            # 提取端点信息
            endpoints = []
            items = data.get("item", [])
            for item in items:
                if "request" in item:
                    endpoint_data = self._extract_postman_request(item)
                    endpoint = self._create_parsed_endpoint(endpoint_data)
                    if endpoint:
                        endpoints.append(endpoint)

            return {
                "api_info": api_info,
                "endpoints": endpoints,
                "errors": [],
                "warnings": [],
                "confidence_score": 0.8
            }

        except Exception as e:
            logger.error(f"Postman Collection解析失败: {str(e)}")
            raise

    def _extract_postman_request(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """提取Postman请求信息"""
        request = item.get("request", {})

        return {
            "path": request.get("url", {}).get("path", ""),
            "method": request.get("method", "GET"),
            "summary": item.get("name", ""),
            "description": item.get("description", ""),
            "tags": [],
            "parameters": [],  # 简化处理
            "responses": [],   # 简化处理
            "auth_required": "auth" in request,
            "deprecated": False
        }

