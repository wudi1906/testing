"""
测试脚本服务
处理测试用例和测试脚本的存储、查询和管理
"""
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
from loguru import logger

from app.models.api_automation import TestCase, TestScript, TestResult, ApiDocument, ApiEndpoint
from app.core.enums import TestType, Priority, TestLevel, ExecutionStatus


class TestScriptService:
    """测试脚本服务类"""
    
    @staticmethod
    async def save_test_case(
        test_case_data: Dict[str, Any],
        doc_id: str,
        endpoint_id: Optional[str] = None
    ) -> str:
        """保存测试用例"""
        try:
            test_case_id = str(uuid.uuid4())
            
            # 获取关联的文档和端点
            document = await ApiDocument.get(doc_id=doc_id)
            endpoint = None
            if endpoint_id:
                endpoint = await ApiEndpoint.get(endpoint_id=endpoint_id)
            
            test_case = await TestCase.create(
                test_id=test_case_id,
                document=document,
                endpoint=endpoint,
                name=test_case_data.get("name", ""),
                description=test_case_data.get("description", ""),
                test_type=TestType(test_case_data.get("test_type", "FUNCTIONAL")),
                test_level=TestLevel(test_case_data.get("test_level", "API")),
                priority=Priority(test_case_data.get("priority", "MEDIUM")),
                test_data=test_case_data.get("test_data", []),
                assertions=test_case_data.get("assertions", []),
                setup_steps=test_case_data.get("setup_steps", []),
                teardown_steps=test_case_data.get("teardown_steps", []),
                dependencies=test_case_data.get("dependencies", []),
                tags=test_case_data.get("tags", []),
                timeout=test_case_data.get("timeout", 30),
                retry_count=test_case_data.get("retry_count", 0)
            )
            
            logger.info(f"保存测试用例成功: {test_case_id}")
            return test_case_id
            
        except Exception as e:
            logger.error(f"保存测试用例失败: {str(e)}")
            raise
    
    @staticmethod
    async def save_test_script(
        script_data: Dict[str, Any],
        test_case_id: str,
        doc_id: str
    ) -> str:
        """保存测试脚本"""
        try:
            script_id = str(uuid.uuid4())
            
            # 获取关联的测试用例和文档
            test_case = await TestCase.get(test_id=test_case_id)
            document = await ApiDocument.get(doc_id=doc_id)
            
            test_script = await TestScript.create(
                script_id=script_id,
                test_case=test_case,
                document=document,
                name=script_data.get("name", ""),
                description=script_data.get("description", ""),
                file_name=script_data.get("file_name", ""),
                content=script_data.get("content", ""),
                file_path=script_data.get("file_path"),
                framework=script_data.get("framework", "pytest"),
                language=script_data.get("language", "python"),
                version=script_data.get("version", "1.0"),
                dependencies=script_data.get("dependencies", []),
                requirements=script_data.get("requirements"),
                timeout=script_data.get("timeout", 300),
                retry_count=script_data.get("retry_count", 0),
                parallel_execution=script_data.get("parallel_execution", False),
                generated_by=script_data.get("generated_by", "AI")
            )
            
            logger.info(f"保存测试脚本成功: {script_id}")
            return script_id
            
        except Exception as e:
            logger.error(f"保存测试脚本失败: {str(e)}")
            raise
    
    @staticmethod
    async def get_test_cases_by_document(doc_id: str) -> List[TestCase]:
        """根据文档ID获取测试用例"""
        try:
            document = await ApiDocument.get(doc_id=doc_id)
            test_cases = await TestCase.filter(document=document).prefetch_related("endpoint", "scripts")
            return test_cases
            
        except Exception as e:
            logger.error(f"获取测试用例失败: {str(e)}")
            raise
    
    @staticmethod
    async def get_test_scripts_by_case(test_case_id: str) -> List[TestScript]:
        """根据测试用例ID获取测试脚本"""
        try:
            test_case = await TestCase.get(test_id=test_case_id)
            scripts = await TestScript.filter(test_case=test_case).all()
            return scripts
            
        except Exception as e:
            logger.error(f"获取测试脚本失败: {str(e)}")
            raise
    
    @staticmethod
    async def update_script_execution_stats(
        script_id: str,
        execution_result: Dict[str, Any]
    ) -> None:
        """更新脚本执行统计"""
        try:
            script = await TestScript.get(script_id=script_id)
            
            # 更新执行次数
            script.execution_count += 1
            
            # 更新成功次数
            if execution_result.get("status") == "PASSED":
                script.success_count += 1
            
            # 更新最后执行时间
            script.last_execution_time = datetime.utcnow()
            
            await script.save()
            
            logger.info(f"更新脚本执行统计成功: {script_id}")
            
        except Exception as e:
            logger.error(f"更新脚本执行统计失败: {str(e)}")
            raise
    
    @staticmethod
    async def save_test_execution_result(
        execution_data: Dict[str, Any],
        test_case_id: str,
        script_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> str:
        """保存测试执行结果"""
        try:
            result_id = str(uuid.uuid4())
            
            # 获取关联对象
            test_case = await TestCase.get(test_id=test_case_id)
            script = None
            if script_id:
                script = await TestScript.get(script_id=script_id)
            
            # 创建执行记录（这里需要先创建TestExecution）
            execution = await TestExecution.create(
                execution_id=str(uuid.uuid4()),
                session_id=session_id or str(uuid.uuid4()),
                document=test_case.document,
                status=ExecutionStatus(execution_data.get("status", "PENDING"))
            )
            
            test_result = await TestResult.create(
                result_id=result_id,
                execution=execution,
                test_case=test_case,
                status=ExecutionStatus(execution_data.get("status", "PENDING")),
                start_time=execution_data.get("start_time", datetime.utcnow()),
                end_time=execution_data.get("end_time"),
                duration=execution_data.get("duration", 0.0),
                request_data=execution_data.get("request_data"),
                response_data=execution_data.get("response_data"),
                assertion_results=execution_data.get("assertion_results", []),
                error_message=execution_data.get("error_message", ""),
                logs=execution_data.get("logs", []),
                screenshots=execution_data.get("screenshots", []),
                attachments=execution_data.get("attachments", [])
            )
            
            # 更新脚本统计
            if script:
                await TestScriptService.update_script_execution_stats(script_id, execution_data)
            
            logger.info(f"保存测试执行结果成功: {result_id}")
            return result_id
            
        except Exception as e:
            logger.error(f"保存测试执行结果失败: {str(e)}")
            raise
    
    @staticmethod
    async def get_test_results_by_session(session_id: str) -> List[TestResult]:
        """根据会话ID获取测试结果"""
        try:
            results = await TestResult.filter(
                execution__session_id=session_id
            ).prefetch_related("test_case", "execution").all()
            return results
            
        except Exception as e:
            logger.error(f"获取测试结果失败: {str(e)}")
            raise
    
    @staticmethod
    async def get_script_statistics(script_id: str) -> Dict[str, Any]:
        """获取脚本统计信息"""
        try:
            script = await TestScript.get(script_id=script_id)
            
            # 计算成功率
            success_rate = 0.0
            if script.execution_count > 0:
                success_rate = (script.success_count / script.execution_count) * 100
            
            # 获取最近的执行结果
            recent_results = await TestResult.filter(
                test_case=script.test_case
            ).order_by("-start_time").limit(10)
            
            return {
                "script_id": script_id,
                "name": script.name,
                "execution_count": script.execution_count,
                "success_count": script.success_count,
                "success_rate": round(success_rate, 2),
                "last_execution_time": script.last_execution_time.isoformat() if script.last_execution_time else None,
                "recent_results": [
                    {
                        "result_id": result.result_id,
                        "status": result.status.value,
                        "start_time": result.start_time.isoformat(),
                        "duration": result.duration
                    }
                    for result in recent_results
                ]
            }
            
        except Exception as e:
            logger.error(f"获取脚本统计失败: {str(e)}")
            raise
    
    @staticmethod
    async def get_test_case_coverage(doc_id: str) -> Dict[str, Any]:
        """获取测试用例覆盖率"""
        try:
            document = await ApiDocument.get(doc_id=doc_id)
            
            # 获取所有端点
            endpoints = await ApiEndpoint.filter(document=document).all()
            total_endpoints = len(endpoints)
            
            # 获取有测试用例的端点
            covered_endpoints = set()
            test_cases = await TestCase.filter(document=document).prefetch_related("endpoint").all()
            
            for test_case in test_cases:
                if test_case.endpoint:
                    covered_endpoints.add(test_case.endpoint.endpoint_id)
            
            coverage_rate = 0.0
            if total_endpoints > 0:
                coverage_rate = (len(covered_endpoints) / total_endpoints) * 100
            
            return {
                "doc_id": doc_id,
                "total_endpoints": total_endpoints,
                "covered_endpoints": len(covered_endpoints),
                "coverage_rate": round(coverage_rate, 2),
                "total_test_cases": len(test_cases),
                "test_cases_by_type": {},
                "test_cases_by_priority": {}
            }
            
        except Exception as e:
            logger.error(f"获取测试用例覆盖率失败: {str(e)}")
            raise
    
    @staticmethod
    async def export_test_scripts(doc_id: str, export_path: str) -> Dict[str, Any]:
        """导出测试脚本"""
        try:
            document = await ApiDocument.get(doc_id=doc_id)
            scripts = await TestScript.filter(document=document).prefetch_related("test_case").all()
            
            export_dir = Path(export_path)
            export_dir.mkdir(parents=True, exist_ok=True)
            
            exported_files = []
            
            for script in scripts:
                # 创建脚本文件
                script_file = export_dir / script.file_name
                with open(script_file, 'w', encoding='utf-8') as f:
                    f.write(script.content)
                
                exported_files.append({
                    "script_id": script.script_id,
                    "file_name": script.file_name,
                    "file_path": str(script_file),
                    "test_case_name": script.test_case.name
                })
                
                # 创建requirements文件
                if script.requirements:
                    req_file = export_dir / f"{script.file_name}_requirements.txt"
                    with open(req_file, 'w', encoding='utf-8') as f:
                        f.write(script.requirements)
            
            return {
                "doc_id": doc_id,
                "export_path": str(export_dir),
                "exported_count": len(exported_files),
                "exported_files": exported_files
            }
            
        except Exception as e:
            logger.error(f"导出测试脚本失败: {str(e)}")
            raise
