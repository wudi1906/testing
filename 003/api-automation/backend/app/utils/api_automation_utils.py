"""
接口自动化工具函数
提供各种辅助功能和工具方法
"""
import os
import json
import yaml
import hashlib
import zipfile
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from pathlib import Path

from loguru import logger


class FileUtils:
    """文件操作工具类"""
    
    @staticmethod
    def get_file_hash(file_path: str) -> str:
        """获取文件MD5哈希值"""
        try:
            hash_md5 = hashlib.md5()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            logger.error(f"计算文件哈希失败: {str(e)}")
            return ""
    
    @staticmethod
    def get_file_info(file_path: str) -> Dict[str, Any]:
        """获取文件信息"""
        try:
            path = Path(file_path)
            if not path.exists():
                return {"error": "文件不存在"}
            
            stat = path.stat()
            return {
                "name": path.name,
                "size": stat.st_size,
                "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "extension": path.suffix,
                "hash": FileUtils.get_file_hash(file_path)
            }
        except Exception as e:
            logger.error(f"获取文件信息失败: {str(e)}")
            return {"error": str(e)}
    
    @staticmethod
    def create_zip_archive(files: List[str], output_path: str) -> bool:
        """创建ZIP压缩包"""
        try:
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in files:
                    if os.path.exists(file_path):
                        arcname = os.path.basename(file_path)
                        zipf.write(file_path, arcname)
            return True
        except Exception as e:
            logger.error(f"创建ZIP压缩包失败: {str(e)}")
            return False
    
    @staticmethod
    def clean_old_files(directory: str, days: int = 7) -> int:
        """清理指定天数前的旧文件"""
        try:
            count = 0
            cutoff_time = datetime.now().timestamp() - (days * 24 * 3600)
            
            for file_path in Path(directory).rglob("*"):
                if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                    file_path.unlink()
                    count += 1
            
            return count
        except Exception as e:
            logger.error(f"清理旧文件失败: {str(e)}")
            return 0


class ConfigUtils:
    """配置工具类"""
    
    @staticmethod
    def load_config(config_path: str) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            path = Path(config_path)
            if not path.exists():
                return {}
            
            with open(path, 'r', encoding='utf-8') as f:
                if path.suffix.lower() in ['.yaml', '.yml']:
                    return yaml.safe_load(f)
                elif path.suffix.lower() == '.json':
                    return json.load(f)
                else:
                    return {}
        except Exception as e:
            logger.error(f"加载配置文件失败: {str(e)}")
            return {}
    
    @staticmethod
    def save_config(config: Dict[str, Any], config_path: str) -> bool:
        """保存配置文件"""
        try:
            path = Path(config_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(path, 'w', encoding='utf-8') as f:
                if path.suffix.lower() in ['.yaml', '.yml']:
                    yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
                elif path.suffix.lower() == '.json':
                    json.dump(config, f, indent=2, ensure_ascii=False)
                else:
                    return False
            
            return True
        except Exception as e:
            logger.error(f"保存配置文件失败: {str(e)}")
            return False
    
    @staticmethod
    def merge_configs(base_config: Dict[str, Any], override_config: Dict[str, Any]) -> Dict[str, Any]:
        """合并配置"""
        try:
            result = base_config.copy()
            
            def deep_merge(base: Dict, override: Dict):
                for key, value in override.items():
                    if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                        deep_merge(base[key], value)
                    else:
                        base[key] = value
            
            deep_merge(result, override_config)
            return result
        except Exception as e:
            logger.error(f"合并配置失败: {str(e)}")
            return base_config


class ValidationUtils:
    """验证工具类"""
    
    @staticmethod
    def validate_api_doc_format(file_path: str) -> Dict[str, Any]:
        """验证API文档格式"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 尝试解析JSON
            try:
                data = json.loads(content)
                
                # 检查OpenAPI格式
                if 'openapi' in data:
                    return {
                        "valid": True,
                        "format": "openapi",
                        "version": data.get('openapi'),
                        "title": data.get('info', {}).get('title', ''),
                        "endpoints_count": len(data.get('paths', {}))
                    }
                
                # 检查Swagger格式
                elif 'swagger' in data:
                    return {
                        "valid": True,
                        "format": "swagger",
                        "version": data.get('swagger'),
                        "title": data.get('info', {}).get('title', ''),
                        "endpoints_count": len(data.get('paths', {}))
                    }
                
                # 检查Postman格式
                elif 'info' in data and 'item' in data:
                    return {
                        "valid": True,
                        "format": "postman",
                        "version": "2.1",
                        "title": data.get('info', {}).get('name', ''),
                        "endpoints_count": ValidationUtils._count_postman_requests(data.get('item', []))
                    }
                
                else:
                    return {
                        "valid": False,
                        "error": "未识别的JSON格式"
                    }
                    
            except json.JSONDecodeError:
                # 尝试解析YAML
                try:
                    data = yaml.safe_load(content)
                    
                    if 'openapi' in data or 'swagger' in data:
                        format_type = "openapi" if 'openapi' in data else "swagger"
                        version_key = "openapi" if format_type == "openapi" else "swagger"
                        
                        return {
                            "valid": True,
                            "format": format_type,
                            "version": data.get(version_key),
                            "title": data.get('info', {}).get('title', ''),
                            "endpoints_count": len(data.get('paths', {}))
                        }
                    else:
                        return {
                            "valid": False,
                            "error": "未识别的YAML格式"
                        }
                        
                except yaml.YAMLError:
                    return {
                        "valid": False,
                        "error": "无效的JSON或YAML格式"
                    }
                    
        except Exception as e:
            return {
                "valid": False,
                "error": str(e)
            }
    
    @staticmethod
    def _count_postman_requests(items: List[Dict]) -> int:
        """递归计算Postman集合中的请求数量"""
        count = 0
        for item in items:
            if 'request' in item:
                count += 1
            elif 'item' in item:
                count += ValidationUtils._count_postman_requests(item['item'])
        return count
    
    @staticmethod
    def validate_test_config(config: Dict[str, Any]) -> Dict[str, Any]:
        """验证测试配置"""
        errors = []
        warnings = []
        
        # 检查必需字段
        required_fields = ['framework']
        for field in required_fields:
            if field not in config:
                errors.append(f"缺少必需字段: {field}")
        
        # 检查框架支持
        supported_frameworks = ['pytest', 'unittest']
        if config.get('framework') not in supported_frameworks:
            errors.append(f"不支持的测试框架: {config.get('framework')}")
        
        # 检查并行配置
        if config.get('parallel', False):
            max_workers = config.get('max_workers', 1)
            if max_workers < 1 or max_workers > 10:
                warnings.append("建议max_workers设置在1-10之间")
        
        # 检查超时配置
        timeout = config.get('timeout', 300)
        if timeout < 10 or timeout > 3600:
            warnings.append("建议timeout设置在10-3600秒之间")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }


class ReportUtils:
    """报告工具类"""
    
    @staticmethod
    def generate_summary_report(results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成测试结果摘要报告"""
        try:
            total_tests = len(results)
            if total_tests == 0:
                return {"error": "没有测试结果"}
            
            passed = sum(1 for r in results if r.get('status') == 'SUCCESS')
            failed = sum(1 for r in results if r.get('status') == 'FAILED')
            error = sum(1 for r in results if r.get('status') == 'ERROR')
            skipped = sum(1 for r in results if r.get('status') == 'SKIPPED')
            
            total_duration = sum(r.get('duration', 0) for r in results)
            avg_duration = total_duration / total_tests if total_tests > 0 else 0
            
            pass_rate = (passed / total_tests) * 100 if total_tests > 0 else 0
            
            return {
                "summary": {
                    "total_tests": total_tests,
                    "passed": passed,
                    "failed": failed,
                    "error": error,
                    "skipped": skipped,
                    "pass_rate": round(pass_rate, 2),
                    "total_duration": round(total_duration, 2),
                    "average_duration": round(avg_duration, 2)
                },
                "status": "PASSED" if failed == 0 and error == 0 else "FAILED",
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"生成摘要报告失败: {str(e)}")
            return {"error": str(e)}
    
    @staticmethod
    def export_results_to_csv(results: List[Dict[str, Any]], output_path: str) -> bool:
        """导出测试结果到CSV文件"""
        try:
            import csv
            
            if not results:
                return False
            
            with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['test_id', 'status', 'duration', 'start_time', 'error_message']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for result in results:
                    writer.writerow({
                        'test_id': result.get('test_id', ''),
                        'status': result.get('status', ''),
                        'duration': result.get('duration', 0),
                        'start_time': result.get('start_time', ''),
                        'error_message': result.get('error_message', '')
                    })
            
            return True
            
        except Exception as e:
            logger.error(f"导出CSV失败: {str(e)}")
            return False


class TemplateUtils:
    """模板工具类"""
    
    @staticmethod
    def render_template(template_content: str, variables: Dict[str, Any]) -> str:
        """渲染模板"""
        try:
            result = template_content
            for key, value in variables.items():
                placeholder = f"{{{key}}}"
                result = result.replace(placeholder, str(value))
            return result
        except Exception as e:
            logger.error(f"渲染模板失败: {str(e)}")
            return template_content
    
    @staticmethod
    def get_pytest_base_template() -> str:
        """获取pytest基础模板"""
        return '''"""
基础API测试类
"""
import requests
import pytest
import allure
from typing import Dict, Any, Optional


class BaseApiTest:
    """基础API测试类"""
    
    def setup_class(self):
        """测试类初始化"""
        self.session = requests.Session()
        self.base_url = "{base_url}"
        self.default_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        self.session.headers.update(self.default_headers)
    
    def teardown_class(self):
        """测试类清理"""
        if hasattr(self, 'session'):
            self.session.close()
    
    def setup_method(self):
        """测试方法初始化"""
        pass
    
    def teardown_method(self):
        """测试方法清理"""
        pass
    
    def make_request(self, method: str, url: str, **kwargs) -> requests.Response:
        """发送HTTP请求"""
        full_url = f"{self.base_url}{url}" if not url.startswith('http') else url
        
        with allure.step(f"发送 {method.upper()} 请求到 {full_url}"):
            response = self.session.request(method, full_url, **kwargs)
            
            # 记录请求和响应信息
            allure.attach(
                f"URL: {full_url}\\nMethod: {method.upper()}\\nHeaders: {kwargs.get('headers', {})}",
                name="请求信息",
                attachment_type=allure.attachment_type.TEXT
            )
            
            allure.attach(
                f"Status: {response.status_code}\\nHeaders: {dict(response.headers)}\\nBody: {response.text[:1000]}",
                name="响应信息", 
                attachment_type=allure.attachment_type.TEXT
            )
            
            return response
    
    def assert_status_code(self, response: requests.Response, expected_code: int):
        """断言状态码"""
        with allure.step(f"验证状态码为 {expected_code}"):
            assert response.status_code == expected_code, f"期望状态码 {expected_code}，实际 {response.status_code}"
    
    def assert_response_time(self, response: requests.Response, max_time: float):
        """断言响应时间"""
        with allure.step(f"验证响应时间小于 {max_time}秒"):
            assert response.elapsed.total_seconds() < max_time, f"响应时间 {response.elapsed.total_seconds()}秒 超过限制 {max_time}秒"
    
    def assert_json_contains(self, response: requests.Response, key: str, value: Any = None):
        """断言JSON响应包含指定键值"""
        with allure.step(f"验证响应包含 {key}"):
            json_data = response.json()
            assert key in json_data, f"响应中不包含键: {key}"
            
            if value is not None:
                assert json_data[key] == value, f"键 {key} 的值不匹配，期望 {value}，实际 {json_data[key]}"
    
    def log_test_result(self, response: requests.Response, test_name: str):
        """记录测试结果"""
        result_info = f"""
测试名称: {test_name}
状态码: {response.status_code}
响应时间: {response.elapsed.total_seconds():.3f}秒
响应大小: {len(response.content)}字节
        """
        allure.attach(result_info, name="测试结果", attachment_type=allure.attachment_type.TEXT)
'''
    
    @staticmethod
    def get_conftest_template() -> str:
        """获取conftest.py模板"""
        return '''"""
pytest配置文件
"""
import pytest
import allure
from datetime import datetime


def pytest_configure(config):
    """pytest配置"""
    # 设置allure报告信息
    if hasattr(config.option, 'allure_report_dir'):
        allure.environment(
            测试环境="{environment}",
            测试时间=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            Python版本="{python_version}",
            Pytest版本="{pytest_version}"
        )


@pytest.fixture(scope="session")
def api_config():
    """API配置fixture"""
    return {
        "base_url": "{base_url}",
        "timeout": {timeout},
        "retry_count": {retry_count}
    }


@pytest.fixture(scope="function")
def test_data():
    """测试数据fixture"""
    return {
        "timestamp": datetime.now().isoformat(),
        "test_id": f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    }


def pytest_runtest_makereport(item, call):
    """生成测试报告钩子"""
    if "incremental" in item.keywords:
        if call.excinfo is not None:
            parent = item.parent
            parent._previousfailed = item


def pytest_runtest_setup(item):
    """测试设置钩子"""
    if "incremental" in item.keywords:
        previousfailed = getattr(item.parent, "_previousfailed", None)
        if previousfailed is not None:
            pytest.xfail(f"previous test failed ({previousfailed.name})")
'''


# 导出所有工具类
__all__ = [
    "FileUtils",
    "ConfigUtils", 
    "ValidationUtils",
    "ReportUtils",
    "TemplateUtils"
]
