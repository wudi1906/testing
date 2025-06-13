import os
import sys
import uuid
import json
import hashlib
from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime
from fastapi import UploadFile, HTTPException

# 添加components目录到Python路径
sys.path.append(str(Path(__file__).parent.parent))

from components.config import MarkerConfig
from components.file_processor import FileProcessor


class DocumentService:
    def __init__(self, upload_dir: str = "uploads"):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(exist_ok=True)

        # 创建文件存储目录
        self.files_db_dir = self.upload_dir / "files_db"
        self.files_db_dir.mkdir(exist_ok=True)

        # 内存中的文件存储（生产环境应使用数据库）
        self.uploaded_files: Dict[str, Dict[str, Any]] = {}
        self.session_files: Dict[str, List[str]] = {}  # session_id -> [file_ids]

        # 文件解析缓存 - 基于文件内容哈希
        self.file_cache: Dict[str, Dict[str, Any]] = {}  # file_hash -> parsed_content

        # 创建marker配置
        self.config = MarkerConfig(
            output_format="markdown",
            use_llm=self._should_use_llm(),
            format_lines=True,
            enable_image_description=True,  # 启用图片描述功能
            disable_image_extraction=self._should_use_llm(),  # 使用LLM时启用图片描述
            max_file_size=50 * 1024 * 1024,  # 50MB
            qwen_api_key=os.getenv("QWEN_API_KEY", ""),
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            # 使用支持视觉的模型
            openai_model="gpt-4o" if os.getenv("OPENAI_API_KEY") else "gpt-4o-mini",
            qwen_model="qwen-vl-max-latest",
        )

        # 创建文件处理器
        self.file_processor = FileProcessor(
            config=self.config,
            upload_dir=upload_dir
        )

        # 加载已存在的文件信息
        self._load_files_db()

    def _should_use_llm(self) -> bool:
        """检查是否应该使用LLM"""
        return bool(os.getenv("QWEN_API_KEY") or os.getenv("OPENAI_API_KEY"))

    def _calculate_file_hash(self, file_content: bytes) -> str:
        """计算文件内容的哈希值"""
        return hashlib.md5(file_content).hexdigest()

    def _get_cached_content(self, file_hash: str) -> Optional[Dict[str, Any]]:
        """获取缓存的文件内容"""
        return self.file_cache.get(file_hash)

    def _cache_file_content(self, file_hash: str, filename: str, content: str, markdown_content: Dict[str, Any]) -> None:
        """缓存文件内容"""
        cache_entry = {
            "filename": filename,
            "content": content,
            "markdown_content": markdown_content,
            "cached_time": datetime.now().isoformat(),
            "file_hash": file_hash
        }
        self.file_cache[file_hash] = cache_entry

        # 限制缓存大小（保留最近的100个文件）
        if len(self.file_cache) > 100:
            # 删除最旧的缓存项
            oldest_hash = min(self.file_cache.keys(),
                            key=lambda h: self.file_cache[h].get("cached_time", ""))
            del self.file_cache[oldest_hash]

    def _load_files_db(self):
        """加载文件数据库"""
        db_file = self.files_db_dir / "files.json"
        if db_file.exists():
            try:
                with open(db_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.uploaded_files = data.get('uploaded_files', {})
                    self.session_files = data.get('session_files', {})
                    self.file_cache = data.get('file_cache', {})
            except Exception as e:
                print(f"加载文件数据库失败: {e}")

        # 加载文件缓存
        cache_file = self.files_db_dir / "file_cache.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    self.file_cache = json.load(f)
            except Exception as e:
                print(f"加载文件缓存失败: {e}")

    def _save_files_db(self):
        """保存文件数据库"""
        db_file = self.files_db_dir / "files.json"
        try:
            with open(db_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'uploaded_files': self.uploaded_files,
                    'session_files': self.session_files,
                    'file_cache': self.file_cache
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存文件数据库失败: {e}")

        # 单独保存文件缓存（避免主数据库过大）
        cache_file = self.files_db_dir / "file_cache.json"
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.file_cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存文件缓存失败: {e}")

    async def save_and_extract_file(self, file: UploadFile, session_id: str = "default") -> Dict[str, Any]:
        """保存文件并使用marker提取内容，返回文件ID"""
        try:
            # 读取文件内容计算哈希
            file_content = await file.read()
            file_hash = self._calculate_file_hash(file_content)

            # 重置文件指针
            await file.seek(0)

            # 检查缓存
            cached_content = self._get_cached_content(file_hash)

            if cached_content:
                print(f"✅ 文件已解析过，使用缓存: {file.filename}")

                # 使用缓存的内容
                plain_text = cached_content["content"]
                markdown_content_data = cached_content["markdown_content"]

                # 生成文件ID
                file_id = str(uuid.uuid4())

                # 仍需保存物理文件（用于后续可能的需求）
                file_extension = Path(file.filename).suffix.lower()
                unique_filename = f"{uuid.uuid4()}{file_extension}"
                file_path = self.upload_dir / unique_filename

                with open(file_path, 'wb') as f:
                    f.write(file_content)

                result = {
                    "filename": file.filename,
                    "saved_filename": unique_filename,
                    "file_path": str(file_path),
                    "file_size": len(file_content),
                    "file_type": file_extension,
                    "markdown_content": markdown_content_data,
                    "processing_config": {"cached": True}
                }
            else:
                print(f"🔄 首次解析文件: {file.filename}")

                # 使用新的文件处理器处理上传文件
                result = await self.file_processor.process_upload_file(file)

                # 生成文件ID
                file_id = str(uuid.uuid4())

                # 提取markdown内容中的纯文本用于聊天
                markdown_content_data = result["markdown_content"]
                plain_text = markdown_content_data.get("plain_text", "")

                # 缓存解析结果
                self._cache_file_content(file_hash, file.filename, plain_text, markdown_content_data)

            # 存储文件信息
            file_info = {
                "file_id": file_id,
                "filename": result["filename"],
                "saved_filename": result["saved_filename"],
                "file_path": result["file_path"],
                "content": plain_text,  # 用于聊天的纯文本内容
                "file_size": result["file_size"],
                "file_type": result["file_type"],
                "markdown_content": result["markdown_content"],
                "processing_config": result.get("processing_config", {}),
                "upload_time": datetime.now().isoformat(),
                "session_id": session_id
            }

            # 保存到内存存储
            self.uploaded_files[file_id] = file_info

            # 关联到会话
            if session_id not in self.session_files:
                self.session_files[session_id] = []
            self.session_files[session_id].append(file_id)

            # 持久化存储
            self._save_files_db()

            # 返回文件ID和基本信息（不包含内容）
            return {
                "file_id": file_id,
                "filename": result["filename"],
                "file_size": result["file_size"],
                "file_type": result["file_type"],
                "upload_time": file_info["upload_time"],
                "statistics": {
                    "total_characters": markdown_content_data["statistics"]["total_characters"],
                    "total_words": markdown_content_data["statistics"]["total_words"],
                    "tables_count": markdown_content_data["statistics"]["tables_count"],
                    "images_count": markdown_content_data["statistics"]["images_count"],
                    "headers_count": markdown_content_data["statistics"]["headers_count"]
                },
                "processing_info": {
                    "llm_enabled": result.get("processing_config", {}).get("use_llm", False),
                    "format_enhanced": result.get("processing_config", {}).get("format_lines", False)
                }
            }

        except HTTPException:
            # 重新抛出HTTP异常
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"文件处理失败: {str(e)}")

    def get_file_content(self, file_id: str) -> Optional[str]:
        """根据文件ID获取文件内容"""
        if file_id in self.uploaded_files:
            return self.uploaded_files[file_id]["content"]
        return None

    def get_file_info_by_id(self, file_id: str) -> Optional[Dict[str, Any]]:
        """根据文件ID获取文件信息"""
        return self.uploaded_files.get(file_id)

    def get_session_files(self, session_id: str) -> List[Dict[str, Any]]:
        """获取会话关联的所有文件"""
        file_ids = self.session_files.get(session_id, [])
        files = []
        for file_id in file_ids:
            if file_id in self.uploaded_files:
                file_info = self.uploaded_files[file_id].copy()
                # 不返回完整内容，只返回基本信息
                file_info.pop("content", None)
                file_info.pop("markdown_content", None)
                files.append(file_info)
        return files

    def get_session_content(self, session_id: str) -> str:
        """获取会话所有文件的合并内容"""
        file_ids = self.session_files.get(session_id, [])
        contents = []

        for file_id in file_ids:
            if file_id in self.uploaded_files:
                file_info = self.uploaded_files[file_id]
                content = file_info["content"]
                filename = file_info["filename"]
                contents.append(f"=== 文件: {filename} ===\n{content}\n")

        return "\n".join(contents)

    def remove_file(self, file_id: str, session_id: str = None) -> bool:
        """删除文件"""
        if file_id not in self.uploaded_files:
            return False

        file_info = self.uploaded_files[file_id]

        # 删除物理文件
        try:
            file_path = Path(file_info["file_path"])
            if file_path.exists():
                file_path.unlink()
        except Exception as e:
            print(f"删除物理文件失败: {e}")

        # 从内存中删除
        del self.uploaded_files[file_id]

        # 从会话中移除
        if session_id and session_id in self.session_files:
            if file_id in self.session_files[session_id]:
                self.session_files[session_id].remove(file_id)

        # 从所有会话中移除
        for sid, file_list in self.session_files.items():
            if file_id in file_list:
                file_list.remove(file_id)

        # 持久化
        self._save_files_db()
        return True

    def clear_session_files(self, session_id: str) -> int:
        """清除会话的所有文件"""
        if session_id not in self.session_files:
            return 0

        file_ids = self.session_files[session_id].copy()
        removed_count = 0

        for file_id in file_ids:
            if self.remove_file(file_id, session_id):
                removed_count += 1

        return removed_count

    async def process_file_direct(self, file_path: str) -> Dict[str, Any]:
        """直接处理文件路径"""
        try:
            markdown_content = await self.file_processor.process_file(file_path)
            structured_content = self.file_processor.markdown_extractor.get_structured_content(markdown_content)

            return {
                "status": "success",
                "file_path": file_path,
                "content": structured_content["plain_text"],
                "markdown_content": structured_content
            }
        except Exception as e:
            return {
                "status": "error",
                "file_path": file_path,
                "error": str(e)
            }

    async def search_in_document(self, file_path: str, query: str, case_sensitive: bool = False) -> List[Dict[str, Any]]:
        """在文档中搜索内容"""
        try:
            markdown_content = await self.file_processor.process_file(file_path)
            return self.file_processor.search_in_content(markdown_content, query, case_sensitive)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")

    def get_supported_formats(self) -> Dict[str, Any]:
        """获取支持的文件格式"""
        return {
            "supported_formats": self.file_processor.get_supported_formats(),
            "max_file_size_mb": self.config.max_file_size / 1024 / 1024,
            "llm_enabled": self.config.use_llm
        }

    def delete_file(self, file_path: str) -> bool:
        """删除文件"""
        return self.file_processor.delete_file(file_path)

    def get_file_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        """获取文件信息"""
        return self.file_processor.get_file_info(file_path)

    def update_config(self, **kwargs) -> None:
        """更新处理配置"""
        self.file_processor.update_config(**kwargs)
        # 同步更新本地配置
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)

    def get_processing_config(self) -> Dict[str, Any]:
        """获取当前处理配置"""
        return self.file_processor.get_config()

    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        return {
            "cache_size": len(self.file_cache),
            "cache_entries": [
                {
                    "file_hash": file_hash[:8] + "...",  # 只显示前8位
                    "filename": entry["filename"],
                    "cached_time": entry["cached_time"],
                    "content_length": len(entry["content"])
                }
                for file_hash, entry in self.file_cache.items()
            ]
        }

    def clear_cache(self) -> int:
        """清除所有缓存"""
        cache_count = len(self.file_cache)
        self.file_cache.clear()
        self._save_files_db()
        return cache_count

    def remove_cache_entry(self, file_hash: str) -> bool:
        """删除特定的缓存项"""
        if file_hash in self.file_cache:
            del self.file_cache[file_hash]
            self._save_files_db()
            return True
        return False

    def is_file_cached(self, file_content: bytes) -> bool:
        """检查文件是否已缓存"""
        file_hash = self._calculate_file_hash(file_content)
        return file_hash in self.file_cache
