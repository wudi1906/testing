#!/usr/bin/env python3
"""
接口自动化智能体系统完整测试脚本
验证系统各个组件的功能是否正常
"""
import asyncio
import json
import tempfile
import os
from pathlib import Path
from datetime import datetime

from loguru import logger

# 配置日志
logger.add(
    "./logs/system_test_{time:YYYY-MM-DD}.log",
    rotation="1 day",
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}"
)


class SystemTester:
    """系统测试器"""
    
    def __init__(self):
        self.test_results = []
        self.session_id = f"system_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
    async def run_all_tests(self):
        """运行所有测试"""
        logger.info("🚀 开始系统完整性测试")
        
        tests = [
            ("测试目录结构", self.test_directory_structure),
            ("测试配置文件", self.test_config_files),
            ("测试智能体工厂", self.test_agent_factory),
            ("测试消息类型", self.test_message_types),
            ("测试编排器", self.test_orchestrator),
            ("测试API文档解析", self.test_api_doc_parsing),
            ("测试接口分析", self.test_api_analysis),
            ("测试脚本生成", self.test_script_generation),
            ("测试工具函数", self.test_utility_functions),
            ("测试模板系统", self.test_template_system)
        ]
        
        for test_name, test_func in tests:
            try:
                logger.info(f"📋 执行测试: {test_name}")
                result = await test_func()
                self.test_results.append({
                    "test_name": test_name,
                    "status": "PASSED" if result else "FAILED",
                    "timestamp": datetime.now().isoformat()
                })
                logger.info(f"✅ {test_name}: {'通过' if result else '失败'}")
            except Exception as e:
                logger.error(f"❌ {test_name} 执行失败: {str(e)}")
                self.test_results.append({
                    "test_name": test_name,
                    "status": "ERROR",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })
        
        # 生成测试报告
        await self.generate_test_report()
        
        # 输出测试摘要
        self.print_test_summary()
    
    async def test_directory_structure(self) -> bool:
        """测试目录结构"""
        required_dirs = [
            "app/core",
            "app/core/agents",
            "app/core/messages",
            "app/agents",
            "app/agents/api_automation",
            "app/services",
            "app/services/api_automation",
            "app/api/v1/endpoints",
            "app/models",
            "app/utils",
            "app/config",
            "app/templates",
            "app/examples"
        ]
        
        missing_dirs = []
        for dir_path in required_dirs:
            if not Path(dir_path).exists():
                missing_dirs.append(dir_path)
        
        if missing_dirs:
            logger.error(f"缺少目录: {missing_dirs}")
            return False
        
        logger.info("目录结构检查通过")
        return True
    
    async def test_config_files(self) -> bool:
        """测试配置文件"""
        config_files = [
            "app/config/api_automation_config.yaml",
            "app/config/allure-categories.json",
            "app/config/pytest.ini"
        ]
        
        missing_files = []
        for file_path in config_files:
            if not Path(file_path).exists():
                missing_files.append(file_path)
        
        if missing_files:
            logger.error(f"缺少配置文件: {missing_files}")
            return False
        
        # 测试YAML配置加载
        try:
            from app.utils.api_automation_utils import ConfigUtils
            config = ConfigUtils.load_config("app/config/api_automation_config.yaml")
            if not config:
                logger.error("YAML配置文件加载失败")
                return False
        except Exception as e:
            logger.error(f"配置文件测试失败: {str(e)}")
            return False
        
        logger.info("配置文件检查通过")
        return True
    
    async def test_agent_factory(self) -> bool:
        """测试智能体工厂"""
        try:
            from app.agents.factory import agent_factory
            
            # 测试工厂状态
            status = agent_factory.get_factory_status()
            if not isinstance(status, dict):
                logger.error("工厂状态获取失败")
                return False
            
            # 测试智能体类型获取
            agent_types = agent_factory.get_agent_types()
            if not agent_types:
                logger.error("没有注册的智能体类型")
                return False
            
            logger.info(f"智能体工厂检查通过，注册了 {len(agent_types)} 个智能体类型")
            return True
            
        except Exception as e:
            logger.error(f"智能体工厂测试失败: {str(e)}")
            return False
    
    async def test_message_types(self) -> bool:
        """测试消息类型"""
        try:
            from app.core.messages.api_automation import (
                ApiDocParseRequest, ApiDocParseResponse,
                DependencyAnalysisRequest, DependencyAnalysisResponse,
                TestScriptGenerationRequest, TestScriptGenerationResponse,
                TestExecutionRequest, TestExecutionResponse,
                LogRecordRequest, LogRecordResponse
            )
            
            # 测试消息创建
            parse_request = ApiDocParseRequest(
                session_id=self.session_id,
                file_path="test.json",
                file_name="test.json"
            )
            
            if not parse_request.session_id:
                logger.error("消息创建失败")
                return False
            
            logger.info("消息类型检查通过")
            return True
            
        except Exception as e:
            logger.error(f"消息类型测试失败: {str(e)}")
            return False
    
    async def test_orchestrator(self) -> bool:
        """测试编排器"""
        try:
            from app.services.api_automation import ApiAutomationOrchestrator
            from app.core.agents.collector import StreamResponseCollector
            from app.core.types import AgentPlatform
            
            # 创建收集器和编排器
            collector = StreamResponseCollector(platform=AgentPlatform.API_AUTOMATION)
            orchestrator = ApiAutomationOrchestrator(collector=collector)
            
            # 测试初始化
            await orchestrator.initialize()
            
            # 测试指标获取
            metrics = await orchestrator.get_orchestrator_metrics()
            if not isinstance(metrics, dict):
                logger.error("编排器指标获取失败")
                return False
            
            # 清理资源
            await orchestrator.cleanup()
            
            logger.info("编排器检查通过")
            return True
            
        except Exception as e:
            logger.error(f"编排器测试失败: {str(e)}")
            return False
    
    async def test_api_doc_parsing(self) -> bool:
        """测试API文档解析"""
        try:
            from app.utils.api_automation_utils import ValidationUtils
            
            # 创建测试API文档
            test_doc = {
                "openapi": "3.0.0",
                "info": {"title": "Test API", "version": "1.0.0"},
                "paths": {
                    "/test": {
                        "get": {
                            "summary": "Test endpoint",
                            "responses": {"200": {"description": "Success"}}
                        }
                    }
                }
            }
            
            # 写入临时文件
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(test_doc, f)
                temp_file = f.name
            
            try:
                # 验证文档格式
                validation_result = ValidationUtils.validate_api_doc_format(temp_file)
                
                if not validation_result.get("valid"):
                    logger.error(f"API文档验证失败: {validation_result}")
                    return False
                
                if validation_result.get("format") != "openapi":
                    logger.error(f"API文档格式识别错误: {validation_result.get('format')}")
                    return False
                
                logger.info("API文档解析检查通过")
                return True
                
            finally:
                # 清理临时文件
                os.unlink(temp_file)
            
        except Exception as e:
            logger.error(f"API文档解析测试失败: {str(e)}")
            return False
    
    async def test_api_analysis(self) -> bool:
        """测试接口分析"""
        try:
            from app.core.messages.api_automation import ApiEndpointInfo, DependencyInfo
            from app.core.enums import HttpMethod, DependencyType
            from app.agents.api_automation.api_analyzer_helper import ApiAnalyzerHelper

            # 创建测试端点
            endpoint1 = ApiEndpointInfo(
                path="/users",
                method=HttpMethod.POST,
                summary="Create user",
                parameters=[
                    {
                        "name": "email",
                        "type": "string",
                        "in": "body",
                        "required": True,
                        "description": "User email"
                    }
                ]
            )

            endpoint2 = ApiEndpointInfo(
                path="/users/{id}",
                method=HttpMethod.GET,
                summary="Get user"
            )

            # 测试辅助方法
            operation_type = ApiAnalyzerHelper.identify_operation_type(endpoint1)
            if operation_type != "create":
                logger.error(f"操作类型识别错误: {operation_type}")
                return False

            business_domain = ApiAnalyzerHelper.identify_business_domain(endpoint1)
            if business_domain != "user_management":
                logger.error(f"业务域识别错误: {business_domain}")
                return False

            # 测试参数分析
            validation_rules = ApiAnalyzerHelper.generate_parameter_validation_rules(
                "email", "string", {"required": True}
            )
            if "必填验证" not in validation_rules:
                logger.error("参数验证规则生成失败")
                return False

            # 创建依赖关系
            dependency = DependencyInfo(
                dependency_id="test_dep",
                dependency_type=DependencyType.DATA_DEPENDENCY,
                source_test="POST /users",
                target_test="GET /users/{id}",
                is_required=True,
                description="Test dependency"
            )

            if not dependency.dependency_id:
                logger.error("依赖信息创建失败")
                return False

            logger.info("接口分析检查通过")
            return True

        except Exception as e:
            logger.error(f"接口分析测试失败: {str(e)}")
            return False
    
    async def test_script_generation(self) -> bool:
        """测试脚本生成"""
        try:
            from app.utils.api_automation_utils import TemplateUtils
            
            # 测试模板渲染
            template = "Hello {name}, welcome to {system}!"
            variables = {"name": "Test", "system": "API Automation"}
            
            result = TemplateUtils.render_template(template, variables)
            expected = "Hello Test, welcome to API Automation!"
            
            if result != expected:
                logger.error(f"模板渲染失败: {result} != {expected}")
                return False
            
            # 测试pytest模板获取
            pytest_template = TemplateUtils.get_pytest_base_template()
            if not pytest_template or "BaseApiTest" not in pytest_template:
                logger.error("pytest模板获取失败")
                return False
            
            logger.info("脚本生成检查通过")
            return True
            
        except Exception as e:
            logger.error(f"脚本生成测试失败: {str(e)}")
            return False
    
    async def test_utility_functions(self) -> bool:
        """测试工具函数"""
        try:
            from app.utils.api_automation_utils import FileUtils, ReportUtils
            
            # 测试文件工具
            test_data = {"test": "data"}
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(test_data, f)
                temp_file = f.name
            
            try:
                file_info = FileUtils.get_file_info(temp_file)
                if "error" in file_info:
                    logger.error(f"文件信息获取失败: {file_info}")
                    return False
                
                # 测试报告工具
                test_results = [
                    {"status": "SUCCESS", "duration": 1.0},
                    {"status": "FAILED", "duration": 2.0},
                    {"status": "SUCCESS", "duration": 1.5}
                ]
                
                summary = ReportUtils.generate_summary_report(test_results)
                if "error" in summary:
                    logger.error(f"报告生成失败: {summary}")
                    return False
                
                logger.info("工具函数检查通过")
                return True
                
            finally:
                os.unlink(temp_file)
            
        except Exception as e:
            logger.error(f"工具函数测试失败: {str(e)}")
            return False
    
    async def test_template_system(self) -> bool:
        """测试模板系统"""
        try:
            # 检查模板文件是否存在
            template_files = [
                "app/templates/test_class_template.py",
                "app/templates/test_data_template.py",
                "app/templates/config_template.py"
            ]
            
            missing_templates = []
            for template_file in template_files:
                if not Path(template_file).exists():
                    missing_templates.append(template_file)
            
            if missing_templates:
                logger.error(f"缺少模板文件: {missing_templates}")
                return False
            
            # 测试模板内容
            with open("app/templates/test_class_template.py", 'r', encoding='utf-8') as f:
                template_content = f.read()
                if "Test{class_name}" not in template_content:
                    logger.error("测试类模板格式错误")
                    return False
            
            logger.info("模板系统检查通过")
            return True
            
        except Exception as e:
            logger.error(f"模板系统测试失败: {str(e)}")
            return False
    
    async def generate_test_report(self):
        """生成测试报告"""
        try:
            report_dir = Path("./reports")
            report_dir.mkdir(exist_ok=True)
            
            report_file = report_dir / f"system_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            report_data = {
                "test_session": self.session_id,
                "test_time": datetime.now().isoformat(),
                "total_tests": len(self.test_results),
                "passed_tests": sum(1 for r in self.test_results if r["status"] == "PASSED"),
                "failed_tests": sum(1 for r in self.test_results if r["status"] == "FAILED"),
                "error_tests": sum(1 for r in self.test_results if r["status"] == "ERROR"),
                "test_results": self.test_results
            }
            
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"测试报告已生成: {report_file}")
            
        except Exception as e:
            logger.error(f"生成测试报告失败: {str(e)}")
    
    def print_test_summary(self):
        """打印测试摘要"""
        total = len(self.test_results)
        passed = sum(1 for r in self.test_results if r["status"] == "PASSED")
        failed = sum(1 for r in self.test_results if r["status"] == "FAILED")
        errors = sum(1 for r in self.test_results if r["status"] == "ERROR")
        
        print("\n" + "="*60)
        print("📊 系统测试摘要")
        print("="*60)
        print(f"总测试数: {total}")
        print(f"通过: {passed} ✅")
        print(f"失败: {failed} ❌")
        print(f"错误: {errors} 💥")
        print(f"成功率: {(passed/total*100):.1f}%" if total > 0 else "成功率: 0%")
        print("="*60)
        
        if failed > 0 or errors > 0:
            print("\n❌ 失败的测试:")
            for result in self.test_results:
                if result["status"] in ["FAILED", "ERROR"]:
                    print(f"  - {result['test_name']}: {result['status']}")
                    if "error" in result:
                        print(f"    错误: {result['error']}")
        
        print(f"\n🎯 测试完成! 会话ID: {self.session_id}")


async def main():
    """主函数"""
    # 确保必要的目录存在
    for directory in ["./logs", "./reports", "./uploads", "./generated_tests"]:
        Path(directory).mkdir(exist_ok=True)
    
    # 运行系统测试
    tester = SystemTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
