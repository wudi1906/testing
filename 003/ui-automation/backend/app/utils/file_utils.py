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


async def sync_script_to_workspace(script_name: str, script_content: str, script_format: str, old_file_path: Optional[str] = None) -> Tuple[str, str]:
    """
    同步脚本到工作空间和存储目录

    Args:
        script_name: 脚本名称
        script_content: 脚本内容
        script_format: 脚本格式 ('yaml' 或 'playwright')
        old_file_path: 旧文件路径（用于清理）

    Returns:
        Tuple[str, str]: (存储目录文件路径, 工作空间文件路径)
    """
    try:
        # 确定文件扩展名和目录
        if script_format.lower() == 'yaml':
            extension = "yaml"
            storage_dir = Path(settings.YAML_OUTPUT_DIR)
            workspace_subdir = "yaml"
        else:
            extension = "ts"
            storage_dir = Path(settings.PLAYWRIGHT_OUTPUT_DIR)
            workspace_subdir = "e2e"

        # 确保目录存在
        storage_dir.mkdir(parents=True, exist_ok=True)
        workspace_dir = Path(settings.MIDSCENE_SCRIPT_PATH) / workspace_subdir
        workspace_dir.mkdir(parents=True, exist_ok=True)

        # 生成安全的文件名
        safe_name = "".join(c for c in script_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_name = safe_name.replace(' ', '_')
        
        # 详细日志记录文件名生成过程
        logger.info(f"🔍 文件名生成调试 - 原始脚本名: '{script_name}'")
        logger.info(f"🔍 文件名生成调试 - 安全文件名: '{safe_name}'")
        logger.info(f"🔍 文件名生成调试 - 脚本格式: '{script_format}'")
        logger.info(f"🔍 文件名生成调试 - 扩展名: '{extension}'")

        # 为Playwright脚本处理文件名
        if script_format.lower() == 'playwright':
            # 如果文件名已经包含完整的 .spec.ts 格式，直接使用
            if safe_name.endswith('.spec.ts') or safe_name.endswith('.spec.js'):
                filename = safe_name
                logger.info(f"🔍 文件名生成调试 - 使用现有完整格式: '{filename}'")
            else:
                # 移除可能的扩展名
                name_without_ext = safe_name
                logger.info(f"🔍 文件名生成调试 - 处理前文件名: '{name_without_ext}'")
                
                for ext in ['.ts', '.js']:
                    if name_without_ext.endswith(ext):
                        name_without_ext = name_without_ext[:-len(ext)]
                        logger.info(f"🔍 文件名生成调试 - 移除扩展名 {ext}: '{name_without_ext}'")
                
                # 重要修复：清理文件名中的spec，防止重复
                # 先移除可能存在的spec后缀，然后重新添加
                if name_without_ext.endswith('spec') or name_without_ext.endswith('spects'):
                    # 移除末尾的spec或spects
                    if name_without_ext.endswith('spects'):
                        name_without_ext = name_without_ext[:-6]  # 移除'spects'
                        logger.info(f"🔍 文件名生成调试 - 移除错误的'spects': '{name_without_ext}'")
                    elif name_without_ext.endswith('spec'):
                        name_without_ext = name_without_ext[:-4]  # 移除'spec'
                        logger.info(f"🔍 文件名生成调试 - 移除现有'spec': '{name_without_ext}'")
                
                # 移除末尾可能的下划线或点
                name_without_ext = name_without_ext.rstrip('_.')
                
                # 生成最终文件名
                filename = f"{name_without_ext}.spec.{extension}"
                logger.info(f"🔍 文件名生成调试 - 最终Playwright文件名: '{filename}'")
        else:
            filename = f"{safe_name}.{extension}"
            logger.info(f"🔍 文件名生成调试 - 非Playwright文件名: '{filename}'")
        storage_file_path = storage_dir / filename
        workspace_file_path = workspace_dir / filename

        # 清理旧文件
        if old_file_path and Path(old_file_path).exists():
            try:
                Path(old_file_path).unlink()
                logger.info(f"删除旧存储文件: {old_file_path}")

                # 同时清理工作空间中的旧文件
                old_filename = Path(old_file_path).name
                old_workspace_file = workspace_dir / old_filename
                if old_workspace_file.exists():
                    old_workspace_file.unlink()
                    logger.info(f"删除旧工作空间文件: {old_workspace_file}")
            except Exception as e:
                logger.warning(f"清理旧文件失败: {old_file_path} - {e}")

        # 保存到存储目录
        async with aiofiles.open(storage_file_path, 'w', encoding='utf-8') as f:
            await f.write(script_content)
        logger.info(f"脚本已保存到存储目录: {storage_file_path}")

        # 保存到工作空间
        async with aiofiles.open(workspace_file_path, 'w', encoding='utf-8') as f:
            await f.write(script_content)
        logger.info(f"脚本已保存到工作空间: {workspace_file_path}")

        return str(storage_file_path), str(workspace_file_path)

    except Exception as e:
        logger.error(f"同步脚本到工作空间失败: {e}")
        raise HTTPException(status_code=500, detail=f"同步脚本失败: {str(e)}")


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
