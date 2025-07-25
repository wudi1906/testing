"""
API测试类模板
自动生成的API接口测试脚本
"""
import pytest
import allure
import requests
import json
from typing import Dict, Any, Optional
from datetime import datetime

from .base_api_test import BaseApiTest
from .test_data import TestData
from .config import Config


@allure.feature("{feature_name}")
class Test{class_name}(BaseApiTest):
    """
    {class_description}
    
    测试目标API: {api_path}
    HTTP方法: {http_method}
    """
    
    def setup_class(self):
        """测试类初始化"""
        super().setup_class()
        self.api_path = "{api_path}"
        self.http_method = "{http_method}"
        
        # 设置特定的请求头
        self.headers.update({
            "Content-Type": "{content_type}",
            "Accept": "application/json"
        })
        
        # 认证设置
        if {auth_required}:
            self.setup_authentication()
    
    def setup_method(self):
        """测试方法初始化"""
        super().setup_method()
        self.test_data = TestData()
        
        # 执行前置依赖
        {setup_dependencies}
    
    def teardown_method(self):
        """测试方法清理"""
        super().teardown_method()
        
        # 执行清理步骤
        {teardown_steps}
    
    def setup_authentication(self):
        """设置认证信息"""
        # 根据认证类型设置认证信息
        auth_type = "{auth_type}"
        
        if auth_type == "bearer":
            token = self.get_auth_token()
            self.headers["Authorization"] = f"Bearer {token}"
        elif auth_type == "api_key":
            self.headers["X-API-Key"] = Config.API_KEY
        elif auth_type == "basic":
            import base64
            credentials = base64.b64encode(f"{Config.USERNAME}:{Config.PASSWORD}".encode()).decode()
            self.headers["Authorization"] = f"Basic {credentials}"
    
    def get_auth_token(self) -> str:
        """获取认证token"""
        # 实现获取token的逻辑
        auth_response = self.make_request(
            "POST", 
            "/auth/login",
            json={
                "username": Config.USERNAME,
                "password": Config.PASSWORD
            }
        )
        return auth_response.json().get("token", "")
    
    @allure.story("{success_story}")
    @allure.severity(allure.severity_level.{success_severity})
    @pytest.mark.{success_test_type}
    @pytest.mark.{success_priority}
    def test_{method_name}_success(self):
        """
        测试 {http_method} {api_path} 成功场景
        
        测试步骤：
        1. 准备有效的测试数据
        2. 发送 {http_method} 请求到 {api_path}
        3. 验证响应状态码为 {expected_success_code}
        4. 验证响应内容格式正确
        5. 验证响应时间在合理范围内
        
        预期结果：
        - 状态码: {expected_success_code}
        - 响应格式: JSON
        - 响应时间: < 5秒
        """
        with allure.step("准备测试数据"):
            test_data = self.test_data.get_valid_data("{method_name}")
            allure.attach(
                json.dumps(test_data, indent=2, ensure_ascii=False),
                name="测试数据",
                attachment_type=allure.attachment_type.JSON
            )
        
        with allure.step("发送API请求"):
            response = self.make_request(
                self.http_method,
                self.api_path,
                **test_data
            )
        
        with allure.step("验证响应结果"):
            # 验证状态码
            self.assert_status_code(response, {expected_success_code})
            
            # 验证响应时间
            self.assert_response_time(response, 5.0)
            
            # 验证响应格式
            if response.headers.get("content-type", "").startswith("application/json"):
                response_data = response.json()
                
                # 执行具体的断言
                {success_assertions}
            
        with allure.step("记录测试结果"):
            self.log_test_result(response, "test_{method_name}_success")
    
    @allure.story("{error_story}")
    @allure.severity(allure.severity_level.{error_severity})
    @pytest.mark.{error_test_type}
    @pytest.mark.{error_priority}
    def test_{method_name}_error(self):
        """
        测试 {http_method} {api_path} 错误场景
        
        测试步骤：
        1. 准备无效的测试数据
        2. 发送 {http_method} 请求到 {api_path}
        3. 验证响应状态码为 4xx 或 5xx
        4. 验证错误信息格式正确
        
        预期结果：
        - 状态码: 400/404/422等错误码
        - 响应包含错误信息
        """
        with allure.step("准备无效测试数据"):
            test_data = self.test_data.get_invalid_data("{method_name}")
            allure.attach(
                json.dumps(test_data, indent=2, ensure_ascii=False),
                name="无效测试数据",
                attachment_type=allure.attachment_type.JSON
            )
        
        with allure.step("发送API请求"):
            response = self.make_request(
                self.http_method,
                self.api_path,
                **test_data
            )
        
        with allure.step("验证错误响应"):
            # 验证错误状态码
            assert response.status_code >= 400, f"期望错误状态码(>=400)，实际: {response.status_code}"
            
            # 验证错误信息
            if response.headers.get("content-type", "").startswith("application/json"):
                error_data = response.json()
                
                # 执行错误场景的断言
                {error_assertions}
        
        with allure.step("记录测试结果"):
            self.log_test_result(response, "test_{method_name}_error")
    
    @allure.story("{boundary_story}")
    @allure.severity(allure.severity_level.{boundary_severity})
    @pytest.mark.{boundary_test_type}
    @pytest.mark.{boundary_priority}
    def test_{method_name}_boundary(self):
        """
        测试 {http_method} {api_path} 边界值场景
        
        测试步骤：
        1. 准备边界值测试数据
        2. 发送 {http_method} 请求到 {api_path}
        3. 验证响应处理正确
        
        预期结果：
        - 系统能正确处理边界值
        - 响应状态码合理
        """
        with allure.step("准备边界值测试数据"):
            test_data = self.test_data.get_boundary_data("{method_name}")
            allure.attach(
                json.dumps(test_data, indent=2, ensure_ascii=False),
                name="边界值测试数据",
                attachment_type=allure.attachment_type.JSON
            )
        
        with allure.step("发送API请求"):
            response = self.make_request(
                self.http_method,
                self.api_path,
                **test_data
            )
        
        with allure.step("验证边界值响应"):
            # 边界值测试的状态码可能是成功或失败
            assert response.status_code in [200, 201, 400, 422], f"意外的状态码: {response.status_code}"
            
            # 执行边界值场景的断言
            {boundary_assertions}
        
        with allure.step("记录测试结果"):
            self.log_test_result(response, "test_{method_name}_boundary")
    
    @allure.story("{performance_story}")
    @allure.severity(allure.severity_level.{performance_severity})
    @pytest.mark.{performance_test_type}
    @pytest.mark.{performance_priority}
    @pytest.mark.slow
    def test_{method_name}_performance(self):
        """
        测试 {http_method} {api_path} 性能场景
        
        测试步骤：
        1. 准备性能测试数据
        2. 多次发送请求测试性能
        3. 验证响应时间和并发处理能力
        
        预期结果：
        - 平均响应时间 < 2秒
        - 95%请求响应时间 < 5秒
        - 系统能处理并发请求
        """
        import time
        import statistics
        
        with allure.step("准备性能测试数据"):
            test_data = self.test_data.get_valid_data("{method_name}")
            request_count = 10  # 性能测试请求次数
            
        with allure.step(f"执行 {request_count} 次性能测试"):
            response_times = []
            
            for i in range(request_count):
                start_time = time.time()
                response = self.make_request(
                    self.http_method,
                    self.api_path,
                    **test_data
                )
                end_time = time.time()
                
                response_times.append(end_time - start_time)
                
                # 验证每次请求都成功
                assert response.status_code < 400, f"第{i+1}次请求失败: {response.status_code}"
        
        with allure.step("分析性能指标"):
            avg_time = statistics.mean(response_times)
            p95_time = statistics.quantiles(response_times, n=20)[18]  # 95th percentile
            max_time = max(response_times)
            min_time = min(response_times)
            
            performance_report = f"""
性能测试报告:
- 请求次数: {request_count}
- 平均响应时间: {avg_time:.3f}秒
- 95%响应时间: {p95_time:.3f}秒
- 最大响应时间: {max_time:.3f}秒
- 最小响应时间: {min_time:.3f}秒
            """
            
            allure.attach(
                performance_report,
                name="性能测试报告",
                attachment_type=allure.attachment_type.TEXT
            )
            
            # 性能断言
            assert avg_time < 2.0, f"平均响应时间过长: {avg_time:.3f}秒"
            assert p95_time < 5.0, f"95%响应时间过长: {p95_time:.3f}秒"
        
        with allure.step("记录测试结果"):
            self.log_test_result(response, "test_{method_name}_performance")
    
    # 参数化测试示例
    @allure.story("参数化测试")
    @pytest.mark.parametrize("test_case", [
        {"name": "case1", "data": {"param1": "value1"}, "expected": 200},
        {"name": "case2", "data": {"param1": "value2"}, "expected": 200},
        {"name": "case3", "data": {"param1": ""}, "expected": 400},
    ])
    def test_{method_name}_parametrized(self, test_case):
        """参数化测试用例"""
        with allure.step(f"执行测试用例: {test_case['name']}"):
            response = self.make_request(
                self.http_method,
                self.api_path,
                json=test_case["data"]
            )
            
            self.assert_status_code(response, test_case["expected"])
            self.log_test_result(response, f"test_{method_name}_parametrized_{test_case['name']}")
