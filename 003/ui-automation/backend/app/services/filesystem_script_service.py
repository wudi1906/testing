"""
文件系统脚本服务
管理独立存储的文件系统脚本，与执行工作空间分离
"""

import os
import json
import shutil
import aiofiles
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from app.core.config import get_settings
from app.models.test_scripts import TestScript, ScriptFormat, ScriptType

logger = logging.getLogger(__name__)
settings = get_settings()


class FileSystemScriptService:
    """文件系统脚本服务"""
    
    def __init__(self):
        self.storage_dir = Path(settings.FILESYSTEM_SCRIPTS_DIR)
        self.scripts_dir = self.storage_dir / "scripts"
        self.metadata_dir = self.storage_dir / "metadata"
        
        # 确保目录存在
        self.scripts_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"文件系统脚本服务初始化完成，存储目录: {self.storage_dir}")
    
    async def save_script(self, script_name: str, content: str, description: str = None) -> Dict[str, Any]:
        """
        保存文件系统脚本
        
        Args:
            script_name: 脚本名称
            content: 脚本内容
            description: 脚本描述
            
        Returns:
            Dict: 保存结果
        """
        try:
            # 确保脚本名称安全
            safe_name = self._make_safe_filename(script_name)
            if not safe_name.endswith('.spec.ts'):
                safe_name = f"{safe_name}.spec.ts"
            
            # 脚本文件路径
            script_path = self.scripts_dir / safe_name
            
            # 元数据文件路径
            metadata_path = self.metadata_dir / f"{safe_name}.json"
            
            # 保存脚本文件
            async with aiofiles.open(script_path, 'w', encoding='utf-8') as f:
                await f.write(content)
            
            # 保存元数据
            metadata = {
                "name": safe_name,
                "original_name": script_name,
                "description": description or f"文件系统脚本: {script_name}",
                "file_path": str(script_path),
                "size": len(content.encode('utf-8')),
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "script_type": "filesystem",
                "script_format": "playwright"
            }
            
            async with aiofiles.open(metadata_path, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(metadata, ensure_ascii=False, indent=2))
            
            logger.info(f"文件系统脚本保存成功: {safe_name}")
            
            return {
                "success": True,
                "script_name": safe_name,
                "file_path": str(script_path),
                "metadata": metadata
            }
            
        except Exception as e:
            logger.error(f"保存文件系统脚本失败: {script_name} - {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_script(self, script_name: str) -> Optional[Dict[str, Any]]:
        """
        获取文件系统脚本
        
        Args:
            script_name: 脚本名称
            
        Returns:
            Optional[Dict]: 脚本信息
        """
        try:
            # 脚本文件路径
            script_path = self.scripts_dir / script_name
            metadata_path = self.metadata_dir / f"{script_name}.json"
            
            if not script_path.exists():
                return None
            
            # 读取脚本内容
            async with aiofiles.open(script_path, 'r', encoding='utf-8') as f:
                content = await f.read()
            
            # 读取元数据
            metadata = {}
            if metadata_path.exists():
                async with aiofiles.open(metadata_path, 'r', encoding='utf-8') as f:
                    metadata = json.loads(await f.read())
            else:
                # 如果没有元数据，生成基本信息
                stat = script_path.stat()
                metadata = {
                    "name": script_name,
                    "original_name": script_name,
                    "description": f"文件系统脚本: {script_name}",
                    "file_path": str(script_path),
                    "size": stat.st_size,
                    "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    "updated_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "script_type": "filesystem",
                    "script_format": "playwright"
                }
            
            return {
                "name": script_name,
                "content": content,
                "metadata": metadata,
                "file_path": str(script_path)
            }
            
        except Exception as e:
            logger.error(f"获取文件系统脚本失败: {script_name} - {e}")
            return None
    
    async def list_scripts(self) -> List[Dict[str, Any]]:
        """
        列出所有文件系统脚本
        
        Returns:
            List[Dict]: 脚本列表
        """
        try:
            scripts = []
            
            # 遍历脚本目录
            for script_file in self.scripts_dir.glob("*.spec.ts"):
                metadata_file = self.metadata_dir / f"{script_file.name}.json"
                
                # 读取元数据
                if metadata_file.exists():
                    async with aiofiles.open(metadata_file, 'r', encoding='utf-8') as f:
                        metadata = json.loads(await f.read())
                else:
                    # 生成基本元数据
                    stat = script_file.stat()
                    metadata = {
                        "name": script_file.name,
                        "original_name": script_file.name,
                        "description": f"文件系统脚本: {script_file.name}",
                        "file_path": str(script_file),
                        "size": stat.st_size,
                        "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        "updated_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "script_type": "filesystem",
                        "script_format": "playwright"
                    }
                
                scripts.append({
                    "id": script_file.name,  # 使用文件名作为ID
                    "name": script_file.name,
                    "description": metadata.get("description", f"文件系统脚本: {script_file.name}"),
                    "size": metadata.get("size", 0),
                    "modified": metadata.get("updated_at", ""),
                    "path": str(script_file),
                    "type": "filesystem",
                    "format": "playwright"
                })
            
            # 按修改时间排序
            scripts.sort(key=lambda x: x["modified"], reverse=True)
            
            logger.info(f"获取文件系统脚本列表成功，共 {len(scripts)} 个脚本")
            return scripts
            
        except Exception as e:
            logger.error(f"获取文件系统脚本列表失败: {e}")
            return []
    
    async def delete_script(self, script_name: str) -> bool:
        """
        删除文件系统脚本
        
        Args:
            script_name: 脚本名称
            
        Returns:
            bool: 是否删除成功
        """
        try:
            script_path = self.scripts_dir / script_name
            metadata_path = self.metadata_dir / f"{script_name}.json"
            
            # 删除脚本文件
            if script_path.exists():
                script_path.unlink()
            
            # 删除元数据文件
            if metadata_path.exists():
                metadata_path.unlink()
            
            logger.info(f"文件系统脚本删除成功: {script_name}")
            return True
            
        except Exception as e:
            logger.error(f"删除文件系统脚本失败: {script_name} - {e}")
            return False
    
    async def copy_to_workspace(self, script_name: str, workspace_path: Path) -> Optional[Path]:
        """
        将脚本复制到执行工作空间
        
        Args:
            script_name: 脚本名称
            workspace_path: 工作空间路径
            
        Returns:
            Optional[Path]: 复制后的文件路径
        """
        try:
            source_path = self.scripts_dir / script_name
            if not source_path.exists():
                logger.error(f"源脚本文件不存在: {source_path}")
                return None
            
            # 确保目标目录存在
            target_dir = workspace_path / "e2e"
            target_dir.mkdir(parents=True, exist_ok=True)
            
            # 目标文件路径
            target_path = target_dir / script_name
            
            # 复制文件
            shutil.copy2(source_path, target_path)
            
            logger.info(f"脚本复制到工作空间成功: {source_path} -> {target_path}")
            return target_path
            
        except Exception as e:
            logger.error(f"复制脚本到工作空间失败: {script_name} - {e}")
            return None
    
    def _make_safe_filename(self, filename: str) -> str:
        """生成安全的文件名"""
        # 移除或替换不安全的字符
        safe_chars = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_', '.'))
        safe_chars = safe_chars.replace(' ', '_')
        return safe_chars.strip('_')


# 全局实例
filesystem_script_service = FileSystemScriptService()
