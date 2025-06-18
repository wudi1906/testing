"""
UI自动化测试系统 - 数据模型定义
统一管理所有Pydantic数据模型
"""
from typing import Dict, List, Any, Optional
from pydantic import BaseModel
from .enums import TestTypes, ActionTypes, BrowserTypes, DeviceTypes


class TestCase(BaseModel):
    """测试用例数据模型"""
    id: Optional[str] = None
    name: str
    description: str
    test_type: TestTypes
    priority: int = 1  # 1-5, 5为最高优先级
    tags: List[str] = []
    preconditions: List[str] = []
    steps: List[Dict[str, Any]] = []
    expected_results: List[str] = []
    test_data: Dict[str, Any] = {}
    environment: Dict[str, Any] = {}
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class TestAction(BaseModel):
    """测试动作数据模型"""
    id: Optional[str] = None
    action_type: ActionTypes
    target: str  # 目标元素描述
    value: Optional[str] = None  # 输入值或参数
    timeout: int = 30000  # 超时时间（毫秒）
    retry_count: int = 3  # 重试次数
    screenshot: bool = False  # 是否截图
    description: str = ""
    expected_result: Optional[str] = None


class TestResult(BaseModel):
    """测试结果数据模型"""
    id: Optional[str] = None
    test_case_id: str
    status: str  # PASS, FAIL, SKIP, ERROR
    start_time: str
    end_time: str
    duration: float  # 执行时间（秒）
    error_message: Optional[str] = None
    screenshots: List[str] = []
    logs: List[str] = []
    performance_metrics: Dict[str, Any] = {}
    browser_info: Dict[str, Any] = {}
    environment_info: Dict[str, Any] = {}


class UIElement(BaseModel):
    """UI元素数据模型"""
    id: Optional[str] = None
    name: str
    element_type: str  # button, input, link, etc.
    selector: str  # CSS选择器或XPath
    description: str
    attributes: Dict[str, Any] = {}
    position: Dict[str, float] = {}  # x, y, width, height
    screenshot_path: Optional[str] = None
    confidence_score: float = 0.0  # AI识别置信度


class TestEnvironment(BaseModel):
    """测试环境配置"""
    id: Optional[str] = None
    name: str
    base_url: str
    browser: BrowserTypes
    device: DeviceTypes
    viewport_width: int = 1280
    viewport_height: int = 960
    user_agent: Optional[str] = None
    headers: Dict[str, str] = {}
    cookies: List[Dict[str, Any]] = []
    proxy: Optional[str] = None
    timeout: int = 30000


class TestExecutionContext(BaseModel):
    """测试执行上下文"""
    execution_id: str
    session_id: str
    environment: TestEnvironment
    start_time: str
    end_time: Optional[str] = None
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    skipped_tests: int = 0
    execution_metadata: Dict[str, Any] = {}
