"""
Marker PDF 解析服务
使用 marker 组件实现高质量的 PDF 内容提取，采用单例模式在服务启动时初始化
"""
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any
from threading import Lock

from loguru import logger

try:
    from marker.converters.pdf import PdfConverter
    from marker.models import create_model_dict
    from marker.config.parser import ConfigParser
    from marker.output import text_from_rendered
    MARKER_AVAILABLE = True
except ImportError:
    MARKER_AVAILABLE = False
    logger.warning("Marker 库未安装，PDF 解析功能将受限")


class MarkerPdfService:
    """
    Marker PDF 解析服务 - 单例模式
    
    在应用启动时初始化 marker 组件，提供高质量的 PDF 内容提取功能
    """
    
    _instance: Optional['MarkerPdfService'] = None
    _lock = Lock()
    _initialized = False
    
    def __new__(cls) -> 'MarkerPdfService':
        """单例模式实现"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """初始化方法 - 只执行一次"""
        if not self._initialized:
            self.converter: Optional[PdfConverter] = None
            self.config: Dict[str, Any] = {}
            self.is_ready = False
            self._initialization_error: Optional[str] = None
            MarkerPdfService._initialized = True
    
    async def initialize(self, config: Optional[Dict[str, Any]] = None) -> bool:
        """
        初始化 Marker PDF 转换器
        
        Args:
            config: Marker 配置参数
            
        Returns:
            bool: 初始化是否成功
        """
        if not MARKER_AVAILABLE:
            self._initialization_error = "Marker 库未安装，请运行: pip install marker-pdf"
            logger.error(self._initialization_error)
            return False
        
        if self.is_ready:
            logger.info("Marker PDF 服务已经初始化完成")
            return True
        
        try:
            logger.info("🚀 开始初始化 Marker PDF 服务...")
            
            # 设置默认配置
            self.config = self._get_default_config()
            if config:
                self.config.update(config)
            
            # 创建配置解析器
            config_parser = ConfigParser(self.config)
            
            # 创建 PDF 转换器
            self.converter = PdfConverter(
                config=self.config,
                artifact_dict=create_model_dict(),
                processor_list=config_parser.get_processors(),
                renderer=config_parser.get_renderer(),
                llm_service=self.config.get("llm_service", "marker.services.openai.OpenAIService")
            )
            
            self.is_ready = True
            logger.info("✅ Marker PDF 服务初始化完成")
            return True
            
        except Exception as e:
            error_msg = f"Marker PDF 服务初始化失败: {str(e)}"
            self._initialization_error = error_msg
            logger.error(error_msg)
            return False
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        try:
            from app.core.config import get_marker_config
            return get_marker_config()
        except ImportError:
            # 如果配置模块不可用，使用硬编码默认值
            return {
                "output_format": "markdown",
                "output_dir": "output",
                "use_llm": False,
                "disable_image_extraction": True,
                "llm_service": "marker.services.openai.OpenAIService",
                "openai_base_url": os.getenv("MARKER_OPENAI_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
                "openai_model": os.getenv("MARKER_OPENAI_MODEL", "qwen-vl-max-latest"),
                "openai_api_key": os.getenv("MARKER_OPENAI_API_KEY", "")
            }
    
    async def extract_pdf_content(self, file_path: Path) -> str:
        """
        提取 PDF 文档内容 - 异步版本

        Args:
            file_path: PDF 文件路径

        Returns:
            str: 提取的文本内容

        Raises:
            RuntimeError: 服务未初始化或提取失败
        """
        if not self.is_ready:
            if self._initialization_error:
                raise RuntimeError(f"Marker PDF 服务未正确初始化: {self._initialization_error}")
            else:
                raise RuntimeError("Marker PDF 服务未初始化，请先调用 initialize() 方法")

        if not file_path.exists():
            raise FileNotFoundError(f"PDF 文件不存在: {file_path}")

        if not file_path.suffix.lower() == '.pdf':
            raise ValueError(f"文件不是 PDF 格式: {file_path}")

        try:
            logger.info(f"开始使用 Marker 提取 PDF 内容: {file_path.name}")

            # 在线程池中执行CPU密集型的PDF处理任务
            loop = asyncio.get_event_loop()
            text = await loop.run_in_executor(
                None,
                self._extract_pdf_sync,
                str(file_path)
            )

            if not text or not text.strip():
                raise RuntimeError("未能从 PDF 中提取到任何文本内容")

            logger.info(f"成功提取 PDF 内容，文本长度: {len(text)} 字符")
            return text

        except Exception as e:
            error_msg = f"Marker PDF 内容提取失败: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

    def _extract_pdf_sync(self, file_path: str) -> str:
        """
        同步提取PDF内容 - 在线程池中执行

        Args:
            file_path: PDF文件路径字符串

        Returns:
            str: 提取的文本内容
        """
        try:
            # 使用 marker 转换 PDF
            rendered = self.converter(file_path)

            # 提取文本内容
            text, _, images = text_from_rendered(rendered)

            # 处理图片引用，替换为描述信息
            for image_key in images.keys():
                text = text.replace(f"![]({image_key})", "[图片描述信息]")

            return text

        except Exception as e:
            logger.error(f"同步PDF提取失败: {str(e)}")
            raise
    
    def get_service_status(self) -> Dict[str, Any]:
        """获取服务状态信息"""
        return {
            "is_ready": self.is_ready,
            "marker_available": MARKER_AVAILABLE,
            "initialization_error": self._initialization_error,
            "config": self.config if self.is_ready else None
        }
    
    async def cleanup(self):
        """清理资源"""
        try:
            logger.info("清理 Marker PDF 服务资源...")
            self.converter = None
            self.is_ready = False
            logger.info("Marker PDF 服务资源清理完成")
        except Exception as e:
            logger.error(f"清理 Marker PDF 服务资源失败: {str(e)}")


# 全局单例实例
marker_pdf_service = MarkerPdfService()


async def initialize_marker_service(config: Optional[Dict[str, Any]] = None) -> bool:
    """
    初始化全局 Marker PDF 服务
    
    Args:
        config: 可选的配置参数
        
    Returns:
        bool: 初始化是否成功
    """
    return await marker_pdf_service.initialize(config)


def get_marker_service() -> MarkerPdfService:
    """
    获取全局 Marker PDF 服务实例
    
    Returns:
        MarkerPdfService: 服务实例
    """
    return marker_pdf_service
