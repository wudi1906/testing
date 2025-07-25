"""
API文档解析智能体
基于公共基类实现，使用大模型智能解析各种格式的API文档
"""
import os
import json

from loguru import logger
import yaml
import uuid
import re
from typing import Dict, List, Any, Optional, AsyncGenerator
from datetime import datetime
from pathlib import Path

# PDF处理相关导入
try:
    import PyPDF2
    import pdfplumber
    import fitz  # PyMuPDF

    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    logger.warning("PDF处理库未安装，PDF解析功能将不可用")

from autogen_core import message_handler, type_subscription, MessageContext, TopicId
from loguru import logger
from pydantic import BaseModel, Field

from app.agents.api_automation.base_api_agent import BaseApiAutomationAgent
from app.core.types import AgentTypes, AGENT_NAMES, TopicTypes
from app.core.messages.api_automation import (
    ApiDocParseRequest, ApiDocParseResponse,
    ApiEndpointInfo, ApiDocumentInfo
)
from app.core.enums import HttpMethod, ContentType, AuthType


@type_subscription(topic_type=TopicTypes.API_DOC_PARSER.value)
class ApiDocParserAgent(BaseApiAutomationAgent):
    """
    API文档解析智能体

    核心功能：
    1. 使用大模型智能解析OpenAPI/Swagger文档
    2. 解析Postman Collection
    3. 解析PDF格式的API文档
    4. 提取接口信息和参数
    5. 生成标准化的API描述
    6. 支持流式输出和实时反馈
    """

    def __init__(self, model_client_instance=None, agent_config=None, **kwargs):
        """初始化API文档解析智能体"""
        super().__init__(
            agent_type=AgentTypes.API_DOC_PARSER,
            model_client_instance=model_client_instance,
            **kwargs
        )

        # 存储智能体配置信息
        self.agent_config = agent_config or {}

        # 初始化AssistantAgent
        self._initialize_assistant_agent()

        # 解析统计（继承公共统计）
        self.parse_metrics = {
            "total_documents": 0,
            "successful_parses": 0,
            "failed_parses": 0,
            "document_types": {},
            "total_endpoints_extracted": 0
        }

        # 支持的文档格式
        self.supported_formats = {
            "openapi": ["3.0", "3.1"],
            "swagger": ["2.0"],
            "postman": ["2.0", "2.1"],
            "custom": ["json", "yaml"]
        }

        logger.info(f"API文档解析智能体初始化完成: {self.agent_name}")



    @message_handler
    async def handle_api_doc_parse_request(
        self, 
        message: ApiDocParseRequest, 
        ctx: MessageContext
    ) -> None:
        """处理API文档解析请求"""
        start_time = datetime.now()
        self.parse_metrics["total_documents"] += 1
        
        try:
            logger.info(f"开始解析API文档: {message.file_name}")
            
            # 读取文档内容
            document_content = await self._read_document(message)
            
            # 使用大模型智能解析文档
            api_info, endpoints = await self._intelligent_parse_document(
                document_content,
                message.file_name,
                message.doc_format
            )
            
            # 构建响应
            response = ApiDocParseResponse(
                session_id=message.session_id,
                doc_id=str(uuid.uuid4()),
                file_name=message.file_name,
                doc_format=message.doc_format,
                api_info=api_info,
                endpoints=endpoints,
                confidence_score=0.9,  # 基础解析置信度
                processing_time=(datetime.now() - start_time).total_seconds()
            )
            
            # 更新统计
            self.parse_metrics["successful_parses"] += 1
            self.parse_metrics["total_endpoints_extracted"] += len(endpoints)
            
            doc_type = message.doc_format
            self.parse_metrics["document_types"][doc_type] = \
                self.parse_metrics["document_types"].get(doc_type, 0) + 1
            
            logger.info(f"API文档解析完成: {message.file_name}, 提取了 {len(endpoints)} 个端点")
            
            # 发送到接口分析智能体
            await self._send_to_api_analyzer(response)
            
        except Exception as e:
            self.parse_metrics["failed_parses"] += 1
            logger.error(f"API文档解析失败: {str(e)}")
            
            # 发送错误响应
            error_response = ApiDocParseResponse(
                session_id=message.session_id,
                doc_id=str(uuid.uuid4()),
                file_name=message.file_name,
                doc_format=message.doc_format,
                api_info={"title": "解析失败", "version": "unknown"},
                endpoints=[],
                parse_errors=[str(e)],
                confidence_score=0.0,
                processing_time=(datetime.now() - start_time).total_seconds()
            )
            
            await self._send_error_response(error_response, str(e))

    async def _read_document(self, message: ApiDocParseRequest) -> str:
        """读取文档内容，支持JSON、YAML和PDF格式"""
        try:
            # 如果已经有文件内容，直接返回
            if message.file_content:
                return message.file_content

            # 检查文件路径是否存在
            if not message.file_path or not os.path.exists(message.file_path):
                raise ValueError("文件路径不存在")

            # 检查是否为PDF文件
            is_pdf = message.file_path.lower().endswith('.pdf')

            if is_pdf:
                # 确保PDF处理库已安装
                if not PDF_AVAILABLE:
                    raise ImportError("PDF处理库未安装，无法解析PDF文件")

                # 解析PDF文件
                logger.info(f"开始解析PDF文件: {message.file_path}")
                return await self._extract_text_from_pdf(message.file_path)
            else:
                # 读取普通文本文件
                with open(message.file_path, 'r', encoding='utf-8') as f:
                    return f.read()

        except Exception as e:
            logger.error(f"读取文档失败: {str(e)}")
            raise

    async def _extract_text_from_pdf(self, pdf_path: str) -> str:
        """从PDF文件中提取文本内容，使用多种方法确保最佳结果"""
        logger.info(f"开始从PDF提取文本: {pdf_path}")

        extracted_text = ""

        try:
            # 方法1: 使用PyPDF2
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                pdf_text = []

                # 提取每一页的文本
                for page_num in range(len(reader.pages)):
                    page = reader.pages[page_num]
                    pdf_text.append(page.extract_text())

                pypdf_text = "\n\n".join(pdf_text)
                logger.info(f"PyPDF2提取了 {len(pypdf_text)} 字符")

            # 方法2: 使用pdfplumber (更好的文本布局保留)
            plumber_text = ""
            with pdfplumber.open(pdf_path) as pdf:
                pages_text = []
                for page in pdf.pages:
                    pages_text.append(page.extract_text() or "")
                plumber_text = "\n\n".join(pages_text)
                logger.info(f"pdfplumber提取了 {len(plumber_text)} 字符")

            # 方法3: 使用PyMuPDF (通常效果最好)
            pymupdf_text = ""
            with fitz.open(pdf_path) as doc:
                pages_text = []
                for page in doc:
                    pages_text.append(page.get_text())
                pymupdf_text = "\n\n".join(pages_text)
                logger.info(f"PyMuPDF提取了 {len(pymupdf_text)} 字符")

            # 选择提取文本最多的结果
            candidates = [
                (pypdf_text, len(pypdf_text), "PyPDF2"),
                (plumber_text, len(plumber_text), "pdfplumber"),
                (pymupdf_text, len(pymupdf_text), "PyMuPDF")
            ]

            # 按提取的文本长度排序
            candidates.sort(key=lambda x: x[1], reverse=True)

            # 选择文本最多的结果
            extracted_text = candidates[0][0]
            method = candidates[0][2]
            logger.info(f"选择了 {method} 提取的文本，共 {len(extracted_text)} 字符")

            # 清理文本
            extracted_text = self._clean_pdf_text(extracted_text)

            return extracted_text

        except Exception as e:
            logger.error(f"PDF文本提取失败: {str(e)}")
            raise ValueError(f"无法从PDF提取文本: {str(e)}")

    def _clean_pdf_text(self, text: str) -> str:
        """清理从PDF提取的文本"""
        # 移除多余的空白行
        text = re.sub(r'\n{3,}', '\n\n', text)

        # 移除分页符
        text = re.sub(r'\f', '\n', text)

        # 修复被错误分割的单词
        text = re.sub(r'(\w+)-\n(\w+)', r'\1\2', text)

        # 移除页眉页脚（通常是重复出现的文本）
        # 这需要根据具体PDF格式调整

        return text

    async def _intelligent_parse_document(
        self,
        content: str,
        filename: str,
        doc_format: str
    ) -> tuple[ApiDocumentInfo, List[ApiEndpointInfo]]:
        """使用大模型智能解析文档内容，支持PDF格式"""
        try:
            # 检查是否为PDF文档
            is_pdf = filename.lower().endswith('.pdf') or doc_format.lower() == 'pdf'

            if is_pdf:
                # 为PDF文档构建特殊的解析任务
                task = await self._build_pdf_parse_task(content, filename)
            else:
                # 为结构化文档构建标准解析任务
                task = await self._build_standard_parse_task(content, filename, doc_format)

            # 使用大模型解析
            response = await self._run_assistant_agent(task)

            # 解析响应
            return await self._parse_llm_response(response, is_pdf)

        except Exception as e:
            logger.error(f"智能解析文档失败: {str(e)}")
            raise

    async def _build_pdf_parse_task(self, content: str, filename: str) -> str:
        """为PDF文档构建解析任务"""
        # 预处理PDF文本，提取关键信息
        api_patterns = self._extract_api_patterns_from_text(content)

        task = f"""请解析以下PDF格式的API文档内容，并提供详细的分析结果：

## 文档信息
- 文件名: {filename}
- 文档类型: PDF格式API文档
- 文本长度: {len(content)} 字符

## 预处理结果
{api_patterns}

## 原始文档内容（前8000字符）
```
{content[:8000]}
```

## PDF文档解析要求
1. **接口识别**: 从文本中识别所有API端点，包括：
   - HTTP方法 (GET, POST, PUT, DELETE等)
   - 接口路径 (如 /api/users, /v1/orders等)
   - 接口描述和功能说明

2. **参数提取**: 提取每个接口的参数信息：
   - 请求参数 (query, path, body参数)
   - 参数类型、是否必需、默认值
   - 参数描述和示例

3. **响应分析**: 分析接口响应：
   - 响应状态码
   - 响应数据结构
   - 错误响应格式

4. **认证信息**: 识别API认证方式：
   - 认证类型 (Bearer Token, API Key, OAuth等)
   - 认证参数位置和格式

5. **数据模型**: 提取数据模型定义：
   - 实体对象结构
   - 字段类型和约束
   - 关联关系

请严格按照系统提示中的JSON格式输出结果，特别注意PDF文档可能存在格式不规范的情况。"""

        return task

    async def _build_standard_parse_task(self, content: str, filename: str, doc_format: str) -> str:
        """为结构化文档构建标准解析任务"""
        task = f"""请解析以下API文档内容，并提供详细的分析结果：

## 文档信息
- 文件名: {filename}
- 声明格式: {doc_format}

## 文档内容
```
{content[:8000]}  # 限制内容长度避免token超限
```

## 解析要求
1. 识别文档的真实格式和版本
2. 提取所有API端点的完整信息
3. 分析API的设计模式和业务逻辑
4. 识别潜在的问题和改进建议
5. 评估解析的置信度

请严格按照系统提示中的JSON格式输出结果。"""

        return task

    def _extract_api_patterns_from_text(self, text: str) -> str:
        """从PDF文本中提取API相关的模式和结构"""
        patterns = []

        # 1. 查找HTTP方法和路径
        http_methods = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']
        method_pattern = r'\b(' + '|'.join(http_methods) + r')\s+(/[^\s]*)'
        matches = re.findall(method_pattern, text, re.IGNORECASE)

        if matches:
            patterns.append("## 发现的API端点:")
            for method, path in matches[:20]:  # 限制数量
                patterns.append(f"- {method.upper()} {path}")

        # 2. 查找URL模式
        url_pattern = r'https?://[^\s]+|/api/[^\s]*|/v\d+/[^\s]*'
        urls = re.findall(url_pattern, text)
        if urls:
            patterns.append("\n## 发现的URL模式:")
            for url in list(set(urls))[:10]:  # 去重并限制数量
                patterns.append(f"- {url}")

        # 3. 查找参数模式
        param_patterns = [
            r'\{[^}]+\}',  # 路径参数 {id}
            r'[?&]\w+=[^&\s]*',  # 查询参数
            r'"[^"]*":\s*"[^"]*"'  # JSON键值对
        ]

        for pattern_name, pattern in [
            ("路径参数", param_patterns[0]),
            ("查询参数", param_patterns[1]),
            ("JSON字段", param_patterns[2])
        ]:
            matches = re.findall(pattern, text)
            if matches:
                patterns.append(f"\n## 发现的{pattern_name}:")
                for match in list(set(matches))[:10]:
                    patterns.append(f"- {match}")

        # 4. 查找状态码
        status_pattern = r'\b(200|201|400|401|403|404|500)\b'
        status_codes = re.findall(status_pattern, text)
        if status_codes:
            patterns.append("\n## 发现的状态码:")
            for code in list(set(status_codes)):
                patterns.append(f"- {code}")

        return '\n'.join(patterns) if patterns else "未发现明显的API模式"

    async def _parse_llm_response(self, response: str, is_pdf: bool = False) -> tuple[ApiDocumentInfo, List[ApiEndpointInfo]]:
        """解析大模型的响应结果"""
        try:
            # 解析大模型返回的结果
            if response:
                parsed_data = self._extract_json_from_content(response)
                if parsed_data:
                    return self._convert_to_api_objects(parsed_data, is_pdf)

            # 如果解析失败，抛出异常
            raise ValueError("无法解析大模型响应")

        except Exception as e:
            logger.error(f"解析大模型响应失败: {str(e)}")
            raise

    def _convert_to_api_objects(self, parsed_data: Dict[str, Any], is_pdf: bool = False) -> tuple[ApiDocumentInfo, List[ApiEndpointInfo]]:
        """将解析数据转换为API对象，支持PDF解析结果"""
        try:
            # 从解析数据中获取文档信息
            doc_info = parsed_data.get("document_info", {})

            # 构建API文档信息
            api_info = ApiDocumentInfo(
                title=doc_info.get("title", parsed_data.get("title", "API文档")),
                version=doc_info.get("version", parsed_data.get("api_version", "1.0.0")),
                description=doc_info.get("description", parsed_data.get("description", "")),
                base_url=doc_info.get("base_url", parsed_data.get("base_url", "")),
                contact_info={},
                license_info={},
                tags=parsed_data.get("tags", []),
                external_docs={}
            )

            # 为PDF文档添加特殊标记
            if is_pdf:
                api_info.description = f"[PDF文档解析] {api_info.description}"

            # 构建端点信息
            endpoints = []
            for ep_data in parsed_data.get("endpoints", []):
                try:
                    endpoint = ApiEndpointInfo(
                        path=ep_data.get("path", ""),
                        method=HttpMethod(ep_data.get("method", "GET").upper()),
                        summary=ep_data.get("summary", ""),
                        description=ep_data.get("description", ""),
                        parameters=ep_data.get("parameters", []),
                        request_body=ep_data.get("request_body"),
                        responses=ep_data.get("responses", {}),
                        tags=ep_data.get("tags", []),
                        auth_required=bool(ep_data.get("security")),
                        auth_type=AuthType.BEARER if ep_data.get("security") else AuthType.NONE,
                        content_type=ContentType.JSON
                    )
                    endpoints.append(endpoint)
                except Exception as e:
                    logger.warning(f"转换端点信息失败: {str(e)}")
                    continue

            return api_info, endpoints

        except Exception as e:
            logger.error(f"转换API对象失败: {str(e)}")
            return ApiDocumentInfo(title=filename, version="unknown"), []

    async def _fallback_parse_document(
        self,
        content: str,
        filename: str,
        doc_format: str
    ) -> tuple[ApiDocumentInfo, List[ApiEndpointInfo]]:
        """备用解析方法"""
        try:
            # 尝试解析JSON/YAML
            if content.strip().startswith('{'):
                data = json.loads(content)
            else:
                data = yaml.safe_load(content)

            # 提取基本信息
            info = data.get("info", {})
            api_info = ApiDocumentInfo(
                title=info.get("title", filename),
                version=info.get("version", "1.0.0"),
                description=info.get("description", ""),
                base_url=self._extract_base_url(data),
                contact_info=info.get("contact", {}),
                license_info=info.get("license", {}),
                tags=[tag.get("name", "") for tag in data.get("tags", [])],
                external_docs=data.get("externalDocs", {})
            )

            # 提取端点信息
            endpoints = self._extract_endpoints(data)

            return api_info, endpoints

        except Exception as e:
            logger.error(f"备用解析失败: {str(e)}")
            # 返回基础信息
            return ApiDocumentInfo(title=filename, version="unknown"), []

    def _extract_base_url(self, data: Dict[str, Any]) -> str:
        """提取基础URL"""
        try:
            # OpenAPI 3.x
            servers = data.get("servers", [])
            if servers and isinstance(servers, list):
                return servers[0].get("url", "")
            
            # Swagger 2.x
            host = data.get("host", "")
            base_path = data.get("basePath", "")
            schemes = data.get("schemes", ["https"])
            
            if host:
                return f"{schemes[0]}://{host}{base_path}"
            
            return ""
            
        except Exception:
            return ""

    def _extract_endpoints(self, data: Dict[str, Any]) -> List[ApiEndpointInfo]:
        """提取端点信息"""
        endpoints = []
        paths = data.get("paths", {})
        
        for path, methods in paths.items():
            for method, details in methods.items():
                if method.upper() in ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]:
                    try:
                        endpoint = ApiEndpointInfo(
                            path=path,
                            method=HttpMethod(method.upper()),
                            summary=details.get("summary", ""),
                            description=details.get("description", ""),
                            parameters=details.get("parameters", []),
                            request_body=details.get("requestBody"),
                            responses=details.get("responses", {}),
                            tags=details.get("tags", []),
                            auth_required=bool(details.get("security")),
                            auth_type=AuthType.BEARER if details.get("security") else AuthType.NONE,
                            content_type=ContentType.JSON
                        )
                        endpoints.append(endpoint)
                        
                    except Exception as e:
                        logger.warning(f"提取端点信息失败: {str(e)}")
                        continue
        
        return endpoints

    async def _send_to_api_analyzer(self, response: ApiDocParseResponse):
        """发送到接口分析智能体"""
        try:
            from app.core.messages.api_automation import DependencyAnalysisRequest
            
            analysis_request = DependencyAnalysisRequest(
                session_id=response.session_id,
                doc_id=response.doc_id,
                endpoints=response.endpoints,
                analysis_config={}
            )
            
            # 这里应该发送到消息队列或直接调用分析智能体
            logger.info(f"已发送到接口分析智能体: {response.doc_id}")
            
        except Exception as e:
            logger.error(f"发送到接口分析智能体失败: {str(e)}")

    def _extract_basic_info_from_task(self, task: str) -> dict:
        """从任务描述中提取基本API信息"""
        # 基础的文本解析逻辑
        import re

        # 查找API端点
        endpoints = []

        # 简单的正则匹配来提取API信息
        method_pattern = r'\b(GET|POST|PUT|DELETE|PATCH)\s+(/[^\s]*)'
        matches = re.findall(method_pattern, task, re.IGNORECASE)

        for method, path in matches:
            endpoint = {
                "path": path,
                "method": method.upper(),
                "summary": f"{method.upper()} {path}",
                "description": f"API端点: {method.upper()} {path}",
                "parameters": [],
                "responses": {
                    "200": {
                        "description": "成功响应",
                        "schema": {"type": "object"}
                    }
                },
                "tags": ["API"],
                "security": []
            }
            endpoints.append(endpoint)

        # 如果没有找到端点，创建一个默认的
        if not endpoints:
            endpoints = [{
                "path": "/api/default",
                "method": "GET",
                "summary": "默认API端点",
                "description": "从文档中解析的默认端点",
                "parameters": [],
                "responses": {
                    "200": {
                        "description": "成功响应",
                        "schema": {"type": "object"}
                    }
                },
                "tags": ["默认"],
                "security": []
            }]

        return {
            "document_info": {
                "title": "解析的API文档",
                "version": "1.0.0",
                "description": "通过文档解析提取的API信息",
                "base_url": "https://api.example.com",
                "confidence_score": 0.8
            },
            "endpoints": endpoints,
            "schemas": {},
            "security_definitions": {}
        }

    async def _send_error_response(self, response: ApiDocParseResponse, error: str):
        """发送错误响应"""
        logger.error(f"API文档解析错误: {error}")

    def get_parse_statistics(self) -> Dict[str, Any]:
        """获取解析统计信息"""
        # 获取基类的公共统计
        common_stats = self.get_common_statistics()

        # 计算解析特定的统计
        success_rate = 0.0
        if self.parse_metrics["total_documents"] > 0:
            success_rate = (self.parse_metrics["successful_parses"] / self.parse_metrics["total_documents"]) * 100

        avg_endpoints = 0.0
        if self.parse_metrics["successful_parses"] > 0:
            avg_endpoints = self.parse_metrics["total_endpoints_extracted"] / self.parse_metrics["successful_parses"]

        # 合并统计信息
        return {
            **common_stats,
            "parse_metrics": self.parse_metrics,
            "parse_success_rate": round(success_rate, 2),
            "avg_endpoints_per_doc": round(avg_endpoints, 2),
            "supported_formats": self.supported_formats
        }


