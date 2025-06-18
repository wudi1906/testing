"""
文件处理工具模块
"""
import os
import uuid
import shutil
from pathlib import Path
from typing import Optional, List, Tuple
from datetime import datetime
import aiofiles
from fastapi import UploadFile, HTTPException
from loguru import logger

from app.core.config import settings


def ensure_directories():
    """确保所有必要的目录存在"""
    directories = [
        settings.UPLOAD_DIR,
        settings.IMAGE_UPLOAD_DIR,
        settings.YAML_OUTPUT_DIR,
        settings.PLAYWRIGHT_OUTPUT_DIR,
        "logs",
        "static",
        "screenshots"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        logger.info(f"确保目录存在: {directory}")


def get_file_extension(filename: str) -> str:
    """获取文件扩展名"""
    return Path(filename).suffix.lower()


def is_allowed_image(filename: str) -> bool:
    """检查是否为允许的图片格式"""
    ext = get_file_extension(filename)
    return ext in settings.ALLOWED_IMAGE_EXTENSIONS_LIST


def generate_unique_filename(original_filename: str, prefix: str = "") -> str:
    """生成唯一的文件名"""
    ext = get_file_extension(original_filename)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    
    if prefix:
        return f"{prefix}_{timestamp}_{unique_id}{ext}"
    else:
        return f"{timestamp}_{unique_id}{ext}"


async def save_uploaded_image(file: UploadFile) -> Tuple[str, str]:
    """
    保存上传的图片文件
    
    Returns:
        Tuple[str, str]: (文件路径, 文件名)
    """
    try:
        # 验证文件类型
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="只支持图片文件")
        
        if not is_allowed_image(file.filename):
            raise HTTPException(
                status_code=400,
                detail=f"不支持的图片格式。支持的格式: {', '.join(settings.ALLOWED_IMAGE_EXTENSIONS_LIST)}"
            )
        
        # 检查文件大小
        file_size = 0
        content = await file.read()
        file_size = len(content)
        
        if file_size > settings.MAX_IMAGE_SIZE:
            raise HTTPException(
                status_code=400, 
                detail=f"图片文件过大。最大支持 {settings.MAX_IMAGE_SIZE // (1024*1024)}MB"
            )
        
        # 生成唯一文件名
        unique_filename = generate_unique_filename(file.filename, "image")
        file_path = Path(settings.IMAGE_UPLOAD_DIR) / unique_filename
        
        # 确保目录存在
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 保存文件
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)
        
        logger.info(f"图片保存成功: {file_path}")
        return str(file_path), unique_filename
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"保存图片失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"保存图片失败: {str(e)}")


async def save_yaml_content(content: str, session_id: str, filename: Optional[str] = None) -> str:
    """
    保存YAML内容到文件
    
    Args:
        content: YAML内容
        session_id: 会话ID
        filename: 可选的文件名
    
    Returns:
        str: 文件路径
    """
    try:
        if not filename:
            filename = f"test_script_{session_id}.yaml"
        
        file_path = Path(settings.YAML_OUTPUT_DIR) / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
            await f.write(content)
        
        logger.info(f"YAML文件保存成功: {file_path}")
        return str(file_path)
        
    except Exception as e:
        logger.error(f"保存YAML文件失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"保存YAML文件失败: {str(e)}")


async def save_playwright_content(content: str, session_id: str, filename: Optional[str] = None) -> str:
    """
    保存Playwright内容到文件
    
    Args:
        content: Playwright TypeScript内容
        session_id: 会话ID
        filename: 可选的文件名
    
    Returns:
        str: 文件路径
    """
    try:
        if not filename:
            filename = f"test_script_{session_id}.ts"
        
        file_path = Path(settings.PLAYWRIGHT_OUTPUT_DIR) / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
            await f.write(content)
        
        logger.info(f"Playwright文件保存成功: {file_path}")
        return str(file_path)
        
    except Exception as e:
        logger.error(f"保存Playwright文件失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"保存Playwright文件失败: {str(e)}")


def cleanup_old_files(directory: str, max_age_days: int = 7):
    """清理旧文件"""
    try:
        directory_path = Path(directory)
        if not directory_path.exists():
            return
        
        cutoff_time = datetime.now().timestamp() - (max_age_days * 24 * 60 * 60)
        
        for file_path in directory_path.iterdir():
            if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                file_path.unlink()
                logger.info(f"清理旧文件: {file_path}")
                
    except Exception as e:
        logger.error(f"清理文件失败: {str(e)}")


def get_file_info(file_path: str) -> dict:
    """获取文件信息"""
    try:
        path = Path(file_path)
        if not path.exists():
            return {}
        
        stat = path.stat()
        return {
            "filename": path.name,
            "size": stat.st_size,
            "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "extension": path.suffix.lower()
        }
    except Exception as e:
        logger.error(f"获取文件信息失败: {str(e)}")
        return {}


async def read_file_content(file_path: str) -> str:
    """读取文件内容"""
    try:
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
            return await f.read()
    except Exception as e:
        logger.error(f"读取文件失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"读取文件失败: {str(e)}")


def list_files_in_directory(directory: str, extension: Optional[str] = None) -> List[dict]:
    """列出目录中的文件"""
    try:
        directory_path = Path(directory)
        if not directory_path.exists():
            return []
        
        files = []
        for file_path in directory_path.iterdir():
            if file_path.is_file():
                if extension and not file_path.suffix.lower() == extension.lower():
                    continue
                
                files.append({
                    "filename": file_path.name,
                    "path": str(file_path),
                    "size": file_path.stat().st_size,
                    "modified_at": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                })
        
        return sorted(files, key=lambda x: x["modified_at"], reverse=True)
        
    except Exception as e:
        logger.error(f"列出文件失败: {str(e)}")
        return []
