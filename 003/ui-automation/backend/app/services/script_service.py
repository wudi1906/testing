"""
脚本管理服务
提供测试脚本的存储、检索、管理功能
"""
import json
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path

from app.models.test_scripts import (
    TestScript, ScriptFormat, ScriptType, ScriptExecutionRecord,
    ScriptSearchRequest, ScriptSearchResponse, ScriptStatistics
)
from app.core.logging import get_logger

logger = get_logger(__name__)


class ScriptService:
    """脚本管理服务类"""
    
    def __init__(self, storage_path: str = "data/scripts"):
        """初始化脚本服务
        
        Args:
            storage_path: 脚本存储路径
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # 创建子目录
        (self.storage_path / "scripts").mkdir(exist_ok=True)
        (self.storage_path / "executions").mkdir(exist_ok=True)
        (self.storage_path / "metadata").mkdir(exist_ok=True)
        
        logger.info(f"脚本服务初始化完成，存储路径: {self.storage_path}")
    
    def save_script(self, script: TestScript) -> TestScript:
        """保存脚本到数据库
        
        Args:
            script: 脚本对象
            
        Returns:
            保存后的脚本对象
        """
        try:
            # 确保脚本有ID
            if not script.id:
                script.id = str(uuid.uuid4())
            
            # 更新时间戳
            script.updated_at = datetime.now().isoformat()
            
            # 保存脚本文件
            script_file_path = self.storage_path / "scripts" / f"{script.id}.{script.script_format.value}"
            with open(script_file_path, 'w', encoding='utf-8') as f:
                f.write(script.content)
            
            # 更新文件路径
            script.file_path = str(script_file_path)
            
            # 保存元数据
            metadata_path = self.storage_path / "metadata" / f"{script.id}.json"
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(script.model_dump(), f, ensure_ascii=False, indent=2)
            
            logger.info(f"脚本保存成功: {script.id} - {script.name}")
            return script
            
        except Exception as e:
            logger.error(f"保存脚本失败: {e}")
            raise
    
    def get_script(self, script_id: str) -> Optional[TestScript]:
        """根据ID获取脚本
        
        Args:
            script_id: 脚本ID
            
        Returns:
            脚本对象或None
        """
        try:
            metadata_path = self.storage_path / "metadata" / f"{script_id}.json"
            if not metadata_path.exists():
                return None
            
            with open(metadata_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return TestScript(**data)
            
        except Exception as e:
            logger.error(f"获取脚本失败: {script_id} - {e}")
            return None
    
    def update_script(self, script_id: str, updates: Dict[str, Any]) -> Optional[TestScript]:
        """更新脚本
        
        Args:
            script_id: 脚本ID
            updates: 更新的字段
            
        Returns:
            更新后的脚本对象或None
        """
        try:
            script = self.get_script(script_id)
            if not script:
                return None
            
            # 更新字段
            for key, value in updates.items():
                if hasattr(script, key):
                    setattr(script, key, value)
            
            # 如果更新了内容，需要重新保存文件
            if 'content' in updates:
                script_file_path = self.storage_path / "scripts" / f"{script.id}.{script.script_format.value}"
                with open(script_file_path, 'w', encoding='utf-8') as f:
                    f.write(script.content)
            
            # 更新时间戳
            script.updated_at = datetime.now().isoformat()
            
            # 保存元数据
            return self.save_script(script)
            
        except Exception as e:
            logger.error(f"更新脚本失败: {script_id} - {e}")
            return None
    
    def delete_script(self, script_id: str) -> bool:
        """删除脚本
        
        Args:
            script_id: 脚本ID
            
        Returns:
            是否删除成功
        """
        try:
            script = self.get_script(script_id)
            if not script:
                return False
            
            # 删除脚本文件
            script_file_path = self.storage_path / "scripts" / f"{script_id}.{script.script_format.value}"
            if script_file_path.exists():
                script_file_path.unlink()
            
            # 删除元数据文件
            metadata_path = self.storage_path / "metadata" / f"{script_id}.json"
            if metadata_path.exists():
                metadata_path.unlink()
            
            logger.info(f"脚本删除成功: {script_id}")
            return True

        except Exception as e:
            logger.error(f"删除脚本失败: {script_id} - {e}")
            return False

    def search_scripts(self, request: ScriptSearchRequest) -> ScriptSearchResponse:
        """搜索脚本

        Args:
            request: 搜索请求

        Returns:
            搜索结果
        """
        try:
            scripts = []
            metadata_dir = self.storage_path / "metadata"

            if not metadata_dir.exists():
                return ScriptSearchResponse(scripts=[], total_count=0, has_more=False)

            # 获取所有脚本元数据
            for metadata_file in metadata_dir.glob("*.json"):
                try:
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    script = TestScript(**data)

                    # 应用过滤条件
                    if self._matches_search_criteria(script, request):
                        scripts.append(script)

                except Exception as e:
                    logger.warning(f"读取脚本元数据失败: {metadata_file} - {e}")
                    continue

            # 排序
            scripts.sort(key=lambda x: x.updated_at, reverse=True)

            # 分页
            total_count = len(scripts)
            start_idx = request.offset
            end_idx = start_idx + request.limit
            page_scripts = scripts[start_idx:end_idx]
            has_more = end_idx < total_count

            return ScriptSearchResponse(
                scripts=page_scripts,
                total_count=total_count,
                has_more=has_more
            )

        except Exception as e:
            logger.error(f"搜索脚本失败: {e}")
            return ScriptSearchResponse(scripts=[], total_count=0, has_more=False)

    def _matches_search_criteria(self, script: TestScript, request: ScriptSearchRequest) -> bool:
        """检查脚本是否匹配搜索条件

        Args:
            script: 脚本对象
            request: 搜索请求

        Returns:
            是否匹配
        """
        # 关键词搜索
        if request.query:
            query_lower = request.query.lower()
            if not any([
                query_lower in script.name.lower(),
                query_lower in script.description.lower(),
                query_lower in script.test_description.lower(),
                query_lower in (script.additional_context or "").lower()
            ]):
                return False

        # 格式过滤
        if request.script_format and script.script_format != request.script_format:
            return False

        # 类型过滤
        if request.script_type and script.script_type != request.script_type:
            return False

        # 分类过滤
        if request.category and script.category != request.category:
            return False

        # 标签过滤
        if request.tags:
            if not any(tag in script.tags for tag in request.tags):
                return False

        # 日期过滤
        if request.date_from:
            if script.created_at < request.date_from:
                return False

        if request.date_to:
            if script.created_at > request.date_to:
                return False

        return True

    def get_script_statistics(self) -> ScriptStatistics:
        """获取脚本统计信息

        Returns:
            统计信息
        """
        try:
            stats = ScriptStatistics()
            metadata_dir = self.storage_path / "metadata"

            if not metadata_dir.exists():
                return stats

            scripts = []
            total_executions = 0
            successful_executions = 0
            failed_executions = 0
            total_execution_time = 0.0
            execution_count = 0

            # 统计脚本信息
            for metadata_file in metadata_dir.glob("*.json"):
                try:
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    script = TestScript(**data)
                    scripts.append(script)

                    # 统计格式
                    if script.script_format == ScriptFormat.YAML:
                        stats.yaml_scripts += 1
                    elif script.script_format == ScriptFormat.PLAYWRIGHT:
                        stats.playwright_scripts += 1

                    # 统计执行次数
                    total_executions += script.execution_count

                except Exception as e:
                    logger.warning(f"读取脚本统计失败: {metadata_file} - {e}")
                    continue

            stats.total_scripts = len(scripts)
            stats.total_executions = total_executions

            # 计算成功率（这里需要从执行记录中获取，暂时使用模拟数据）
            if total_executions > 0:
                stats.successful_executions = int(total_executions * 0.85)  # 假设85%成功率
                stats.failed_executions = total_executions - stats.successful_executions
                stats.success_rate = stats.successful_executions / total_executions

            # 平均执行时间（模拟数据）
            stats.average_execution_time = 45.5

            # 最常用脚本
            scripts.sort(key=lambda x: x.execution_count, reverse=True)
            stats.most_used_scripts = [
                {
                    "id": script.id,
                    "name": script.name,
                    "execution_count": script.execution_count,
                    "script_format": script.script_format.value
                }
                for script in scripts[:5]
            ]

            # 最近创建脚本
            scripts.sort(key=lambda x: x.created_at, reverse=True)
            stats.recent_scripts = [
                {
                    "id": script.id,
                    "name": script.name,
                    "created_at": script.created_at,
                    "script_format": script.script_format.value
                }
                for script in scripts[:5]
            ]

            return stats

        except Exception as e:
            logger.error(f"获取脚本统计失败: {e}")
            return ScriptStatistics()

    def save_execution_record(self, record: ScriptExecutionRecord) -> ScriptExecutionRecord:
        """保存执行记录

        Args:
            record: 执行记录

        Returns:
            保存后的执行记录
        """
        try:
            # 确保记录有ID
            if not record.id:
                record.id = str(uuid.uuid4())

            # 保存执行记录
            execution_path = self.storage_path / "executions" / f"{record.id}.json"
            with open(execution_path, 'w', encoding='utf-8') as f:
                json.dump(record.model_dump(), f, ensure_ascii=False, indent=2)

            # 更新脚本的执行统计
            script = self.get_script(record.script_id)
            if script:
                script.execution_count += 1
                script.last_execution_time = record.start_time
                script.last_execution_status = record.status
                self.save_script(script)

            logger.info(f"执行记录保存成功: {record.id}")
            return record

        except Exception as e:
            logger.error(f"保存执行记录失败: {e}")
            raise

    def get_execution_record(self, record_id: str) -> Optional[ScriptExecutionRecord]:
        """获取执行记录

        Args:
            record_id: 记录ID

        Returns:
            执行记录或None
        """
        try:
            execution_path = self.storage_path / "executions" / f"{record_id}.json"
            if not execution_path.exists():
                return None

            with open(execution_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            return ScriptExecutionRecord(**data)

        except Exception as e:
            logger.error(f"获取执行记录失败: {record_id} - {e}")
            return None

    def get_script_executions(self, script_id: str, limit: int = 20) -> List[ScriptExecutionRecord]:
        """获取脚本的执行记录

        Args:
            script_id: 脚本ID
            limit: 返回数量限制

        Returns:
            执行记录列表
        """
        try:
            records = []
            executions_dir = self.storage_path / "executions"

            if not executions_dir.exists():
                return records

            # 查找该脚本的所有执行记录
            for execution_file in executions_dir.glob("*.json"):
                try:
                    with open(execution_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    record = ScriptExecutionRecord(**data)
                    if record.script_id == script_id:
                        records.append(record)

                except Exception as e:
                    logger.warning(f"读取执行记录失败: {execution_file} - {e}")
                    continue

            # 按开始时间排序
            records.sort(key=lambda x: x.start_time, reverse=True)

            return records[:limit]

        except Exception as e:
            logger.error(f"获取脚本执行记录失败: {script_id} - {e}")
            return []

    def create_script_from_analysis(
        self,
        session_id: str,
        name: str,
        description: str,
        content: str,
        script_format: ScriptFormat,
        script_type: ScriptType,
        test_description: str,
        additional_context: Optional[str] = None,
        source_url: Optional[str] = None,
        source_image_path: Optional[str] = None,
        analysis_result_id: Optional[str] = None
    ) -> TestScript:
        """从分析结果创建脚本

        Args:
            session_id: 会话ID
            name: 脚本名称
            description: 脚本描述
            content: 脚本内容
            script_format: 脚本格式
            script_type: 脚本类型
            test_description: 测试需求描述
            additional_context: 额外上下文
            source_url: 源URL
            source_image_path: 源图片路径
            analysis_result_id: 分析结果ID

        Returns:
            创建的脚本对象
        """
        script = TestScript(
            id=str(uuid.uuid4()),
            session_id=session_id,
            name=name,
            description=description,
            script_format=script_format,
            script_type=script_type,
            content=content,
            file_path="",  # 将在save_script中设置
            test_description=test_description,
            additional_context=additional_context,
            source_url=source_url,
            source_image_path=source_image_path,
            analysis_result_id=analysis_result_id
        )

        return self.save_script(script)


# 全局脚本服务实例
script_service = ScriptService()
