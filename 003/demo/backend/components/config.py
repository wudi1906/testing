"""
配置管理模块
基于marker官方配置，提供文件处理的配置选项
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class MarkerConfig:
    """Marker配置类"""
    
    # 输出格式配置
    output_format: str = "markdown"  # markdown, json, html
    output_dir: str = "output"
    
    # LLM配置
    use_llm: bool = False
    llm_service: str = "marker.services.openai.OpenAIService"
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"
    openai_api_key: str = ""
    
    # 阿里云通义千问配置
    qwen_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    qwen_model: str = "qwen-vl-max-latest"
    qwen_api_key: str = ""
    
    # 处理配置
    disable_image_extraction: bool = True  # 启用图片描述功能时设为True
    force_ocr: bool = False
    format_lines: bool = True
    strip_existing_ocr: bool = False
    redo_inline_math: bool = False

    # 图片描述配置
    enable_image_description: bool = True  # 是否启用图片描述功能
    image_description_prompt: str = "请详细描述这张图片的内容，包括文字、图表、数据等所有可见信息。"
    
    # 页面范围配置
    page_range: Optional[str] = None
    paginate_output: bool = False
    
    # 调试配置
    debug: bool = False
    
    # 文件大小限制 (50MB)
    max_file_size: int = 50 * 1024 * 1024
    
    # 支持的文件类型
    supported_extensions: tuple = (
        '.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif',
        '.pptx', '.ppt', '.docx', '.doc', '.xlsx', '.xls',
        '.html', '.htm', '.epub', '.txt'  # 添加TXT支持
    )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        config_dict = {
            "output_format": self.output_format,
            "output_dir": self.output_dir,
            "use_llm": self.use_llm,
            "disable_image_extraction": self.disable_image_extraction,
            "force_ocr": self.force_ocr,
            "format_lines": self.format_lines,
            "strip_existing_ocr": self.strip_existing_ocr,
            "redo_inline_math": self.redo_inline_math,
            "debug": self.debug,
        }
        
        # 添加LLM服务配置
        if self.use_llm:
            config_dict.update({
                "llm_service": self.llm_service,
            })

            # 根据不同的LLM服务添加相应配置
            if "openai" in self.llm_service.lower():
                if self.qwen_api_key:  # 使用通义千问
                    config_dict.update({
                        "openai_base_url": self.qwen_base_url,
                        "openai_model": self.qwen_model,
                        "openai_api_key": self.qwen_api_key,
                    })
                else:  # 使用OpenAI
                    config_dict.update({
                        "openai_base_url": self.openai_base_url,
                        "openai_model": self.openai_model,
                        "openai_api_key": self.openai_api_key,
                    })

        # 图片描述功能配置
        if self.enable_image_description and self.use_llm:
            config_dict["disable_image_extraction"] = True  # 启用图片描述时必须禁用图片提取
        
        # 添加页面范围配置
        if self.page_range:
            config_dict["page_range"] = self.page_range
            
        if self.paginate_output:
            config_dict["paginate_output"] = self.paginate_output
            
        return config_dict

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'MarkerConfig':
        """从字典创建配置对象"""
        return cls(**{k: v for k, v in config_dict.items() if hasattr(cls, k)})

    def validate(self) -> bool:
        """验证配置是否有效"""
        if self.use_llm and not (self.openai_api_key or self.qwen_api_key):
            raise ValueError("使用LLM时必须提供API密钥")
        
        if self.output_format not in ["markdown", "json", "html"]:
            raise ValueError("输出格式必须是 markdown, json 或 html")
            
        if self.max_file_size <= 0:
            raise ValueError("文件大小限制必须大于0")
            
        return True


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config: Optional[MarkerConfig] = None):
        self.config = config or MarkerConfig()
    
    def update_config(self, **kwargs) -> None:
        """更新配置"""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
            else:
                raise ValueError(f"未知的配置项: {key}")
    
    def get_config_dict(self) -> Dict[str, Any]:
        """获取配置字典"""
        return self.config.to_dict()
    
    def validate_config(self) -> bool:
        """验证配置"""
        return self.config.validate()
    
    def is_file_supported(self, filename: str) -> bool:
        """检查文件是否支持"""
        from pathlib import Path
        extension = Path(filename).suffix.lower()
        return extension in self.config.supported_extensions
    
    def get_supported_extensions(self) -> tuple:
        """获取支持的文件扩展名"""
        return self.config.supported_extensions


# 默认配置实例
default_config = MarkerConfig()
default_config_manager = ConfigManager(default_config)
