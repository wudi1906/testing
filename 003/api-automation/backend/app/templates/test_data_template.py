"""
测试数据模板
提供各种测试场景的数据
"""
import json
import random
import string
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional


class TestData:
    """测试数据生成器"""
    
    def __init__(self):
        """初始化测试数据生成器"""
        self.timestamp = datetime.now().isoformat()
        self.test_id = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    def get_valid_data(self, endpoint_name: str) -> Dict[str, Any]:
        """获取有效的测试数据"""
        data_generators = {
            # 用户相关接口
            "users": self._get_user_valid_data,
            "create_user": self._get_create_user_valid_data,
            "update_user": self._get_update_user_valid_data,
            "get_user": self._get_get_user_valid_data,
            "delete_user": self._get_delete_user_valid_data,
            
            # 产品相关接口
            "products": self._get_product_valid_data,
            "create_product": self._get_create_product_valid_data,
            "update_product": self._get_update_product_valid_data,
            "get_product": self._get_get_product_valid_data,
            "delete_product": self._get_delete_product_valid_data,
            
            # 订单相关接口
            "orders": self._get_order_valid_data,
            "create_order": self._get_create_order_valid_data,
            "update_order": self._get_update_order_valid_data,
            "get_order": self._get_get_order_valid_data,
            "cancel_order": self._get_cancel_order_valid_data,
        }
        
        generator = data_generators.get(endpoint_name, self._get_default_valid_data)
        return generator()
    
    def get_invalid_data(self, endpoint_name: str) -> Dict[str, Any]:
        """获取无效的测试数据"""
        data_generators = {
            "users": self._get_user_invalid_data,
            "create_user": self._get_create_user_invalid_data,
            "update_user": self._get_update_user_invalid_data,
            "products": self._get_product_invalid_data,
            "create_product": self._get_create_product_invalid_data,
            "orders": self._get_order_invalid_data,
            "create_order": self._get_create_order_invalid_data,
        }
        
        generator = data_generators.get(endpoint_name, self._get_default_invalid_data)
        return generator()
    
    def get_boundary_data(self, endpoint_name: str) -> Dict[str, Any]:
        """获取边界值测试数据"""
        data_generators = {
            "users": self._get_user_boundary_data,
            "create_user": self._get_create_user_boundary_data,
            "products": self._get_product_boundary_data,
            "create_product": self._get_create_product_boundary_data,
            "orders": self._get_order_boundary_data,
            "create_order": self._get_create_order_boundary_data,
        }
        
        generator = data_generators.get(endpoint_name, self._get_default_boundary_data)
        return generator()
    
    # 用户相关数据生成器
    def _get_user_valid_data(self) -> Dict[str, Any]:
        """用户列表查询有效数据"""
        return {
            "params": {
                "page": random.randint(1, 10),
                "size": random.randint(10, 50),
                "status": random.choice(["active", "inactive", "all"])
            }
        }
    
    def _get_create_user_valid_data(self) -> Dict[str, Any]:
        """创建用户有效数据"""
        return {
            "json": {
                "username": f"testuser_{self.generate_random_string(8)}",
                "email": f"test_{self.generate_random_string(6)}@example.com",
                "name": f"Test User {self.generate_random_string(4)}",
                "password": self.generate_random_string(12),
                "phone": f"1{random.randint(3000000000, 9999999999)}",
                "age": random.randint(18, 65),
                "gender": random.choice(["male", "female", "other"]),
                "address": {
                    "country": "China",
                    "city": "Beijing",
                    "street": f"Test Street {random.randint(1, 999)}"
                }
            }
        }
    
    def _get_update_user_valid_data(self) -> Dict[str, Any]:
        """更新用户有效数据"""
        return {
            "json": {
                "name": f"Updated User {self.generate_random_string(4)}",
                "email": f"updated_{self.generate_random_string(6)}@example.com",
                "phone": f"1{random.randint(3000000000, 9999999999)}",
                "status": random.choice(["active", "inactive"])
            }
        }
    
    def _get_get_user_valid_data(self) -> Dict[str, Any]:
        """获取用户详情有效数据"""
        return {
            "params": {
                "include_profile": True,
                "include_orders": False
            }
        }
    
    def _get_delete_user_valid_data(self) -> Dict[str, Any]:
        """删除用户有效数据"""
        return {
            "params": {
                "force": False,
                "reason": "Test deletion"
            }
        }
    
    # 用户无效数据生成器
    def _get_user_invalid_data(self) -> Dict[str, Any]:
        """用户列表查询无效数据"""
        return {
            "params": {
                "page": -1,  # 无效页码
                "size": 0,   # 无效大小
                "status": "invalid_status"  # 无效状态
            }
        }
    
    def _get_create_user_invalid_data(self) -> Dict[str, Any]:
        """创建用户无效数据"""
        invalid_cases = [
            # 缺少必需字段
            {
                "json": {
                    "email": "invalid_email",  # 无效邮箱格式
                    "name": "",  # 空名称
                }
            },
            # 字段类型错误
            {
                "json": {
                    "username": 123,  # 应该是字符串
                    "email": "test@example.com",
                    "name": "Test User",
                    "age": "invalid_age"  # 应该是数字
                }
            },
            # 字段值超出范围
            {
                "json": {
                    "username": "a" * 256,  # 用户名过长
                    "email": "test@example.com",
                    "name": "Test User",
                    "age": 200  # 年龄超出合理范围
                }
            }
        ]
        return random.choice(invalid_cases)
    
    def _get_update_user_invalid_data(self) -> Dict[str, Any]:
        """更新用户无效数据"""
        return {
            "json": {
                "name": "",  # 空名称
                "email": "invalid_email_format",  # 无效邮箱
                "phone": "invalid_phone",  # 无效电话
                "status": "invalid_status"  # 无效状态
            }
        }
    
    # 用户边界值数据生成器
    def _get_user_boundary_data(self) -> Dict[str, Any]:
        """用户列表查询边界值数据"""
        boundary_cases = [
            {"params": {"page": 1, "size": 1}},  # 最小值
            {"params": {"page": 1, "size": 100}},  # 最大值
            {"params": {"page": 999999, "size": 10}},  # 极大页码
        ]
        return random.choice(boundary_cases)
    
    def _get_create_user_boundary_data(self) -> Dict[str, Any]:
        """创建用户边界值数据"""
        boundary_cases = [
            # 最短有效值
            {
                "json": {
                    "username": "a",  # 最短用户名
                    "email": "a@b.c",  # 最短邮箱
                    "name": "A",  # 最短姓名
                    "password": "12345678"  # 最短密码
                }
            },
            # 最长有效值
            {
                "json": {
                    "username": "a" * 50,  # 最长用户名
                    "email": f"{'a' * 50}@{'b' * 50}.com",  # 最长邮箱
                    "name": "A" * 100,  # 最长姓名
                    "password": "a" * 128  # 最长密码
                }
            },
            # 特殊字符
            {
                "json": {
                    "username": "test_user-123",
                    "email": "test+tag@example-domain.co.uk",
                    "name": "Test User-O'Connor",
                    "password": "P@ssw0rd!@#$%"
                }
            }
        ]
        return random.choice(boundary_cases)
    
    # 产品相关数据生成器
    def _get_product_valid_data(self) -> Dict[str, Any]:
        """产品列表查询有效数据"""
        return {
            "params": {
                "category": random.choice(["electronics", "clothing", "books", "all"]),
                "price_min": random.randint(0, 100),
                "price_max": random.randint(100, 1000),
                "in_stock": random.choice([True, False, None])
            }
        }
    
    def _get_create_product_valid_data(self) -> Dict[str, Any]:
        """创建产品有效数据"""
        return {
            "json": {
                "name": f"Test Product {self.generate_random_string(6)}",
                "description": f"This is a test product description {self.generate_random_string(10)}",
                "price": round(random.uniform(10.0, 999.99), 2),
                "category": random.choice(["electronics", "clothing", "books", "home"]),
                "stock_quantity": random.randint(0, 1000),
                "sku": f"SKU-{self.generate_random_string(8).upper()}",
                "tags": [f"tag{i}" for i in range(random.randint(1, 5))],
                "specifications": {
                    "weight": f"{random.randint(1, 100)}kg",
                    "dimensions": f"{random.randint(10, 100)}x{random.randint(10, 100)}x{random.randint(10, 100)}cm",
                    "color": random.choice(["red", "blue", "green", "black", "white"])
                }
            }
        }
    
    def _get_update_product_valid_data(self) -> Dict[str, Any]:
        """更新产品有效数据"""
        return {
            "json": {
                "name": f"Updated Product {self.generate_random_string(6)}",
                "price": round(random.uniform(10.0, 999.99), 2),
                "stock_quantity": random.randint(0, 1000),
                "status": random.choice(["active", "inactive", "discontinued"])
            }
        }
    
    def _get_get_product_valid_data(self) -> Dict[str, Any]:
        """获取产品详情有效数据"""
        return {
            "params": {
                "include_reviews": random.choice([True, False]),
                "include_related": random.choice([True, False])
            }
        }
    
    def _get_delete_product_valid_data(self) -> Dict[str, Any]:
        """删除产品有效数据"""
        return {
            "params": {
                "force": random.choice([True, False]),
                "reason": "Test deletion"
            }
        }
    
    # 产品无效数据生成器
    def _get_product_invalid_data(self) -> Dict[str, Any]:
        """产品列表查询无效数据"""
        return {
            "params": {
                "category": "invalid_category",
                "price_min": -1,  # 负价格
                "price_max": "invalid_price",  # 非数字价格
                "in_stock": "invalid_boolean"  # 无效布尔值
            }
        }
    
    def _get_create_product_invalid_data(self) -> Dict[str, Any]:
        """创建产品无效数据"""
        invalid_cases = [
            # 缺少必需字段
            {
                "json": {
                    "description": "Missing name and price"
                }
            },
            # 无效数据类型
            {
                "json": {
                    "name": 123,  # 应该是字符串
                    "price": "invalid_price",  # 应该是数字
                    "stock_quantity": -1  # 负库存
                }
            },
            # 无效字段值
            {
                "json": {
                    "name": "",  # 空名称
                    "price": -10.0,  # 负价格
                    "category": "invalid_category"  # 无效分类
                }
            }
        ]
        return random.choice(invalid_cases)
    
    def _get_update_product_invalid_data(self) -> Dict[str, Any]:
        """更新产品无效数据"""
        return {
            "json": {
                "name": "",  # 空名称
                "price": -1,  # 负价格
                "stock_quantity": "invalid_quantity",  # 无效库存
                "status": "invalid_status"  # 无效状态
            }
        }
    
    # 产品边界值数据生成器
    def _get_product_boundary_data(self) -> Dict[str, Any]:
        """产品列表查询边界值数据"""
        return {
            "params": {
                "price_min": 0,  # 最小价格
                "price_max": 999999.99,  # 最大价格
                "category": "a" * 100  # 超长分类名
            }
        }
    
    def _get_create_product_boundary_data(self) -> Dict[str, Any]:
        """创建产品边界值数据"""
        boundary_cases = [
            # 最小值
            {
                "json": {
                    "name": "A",  # 最短名称
                    "price": 0.01,  # 最小价格
                    "stock_quantity": 0  # 最小库存
                }
            },
            # 最大值
            {
                "json": {
                    "name": "A" * 255,  # 最长名称
                    "price": 999999.99,  # 最大价格
                    "stock_quantity": 999999  # 最大库存
                }
            }
        ]
        return random.choice(boundary_cases)
    
    # 订单相关数据生成器（简化示例）
    def _get_order_valid_data(self) -> Dict[str, Any]:
        """订单列表查询有效数据"""
        return {
            "params": {
                "status": random.choice(["pending", "confirmed", "shipped", "delivered", "cancelled"]),
                "date_from": (datetime.now() - timedelta(days=30)).isoformat(),
                "date_to": datetime.now().isoformat()
            }
        }
    
    def _get_create_order_valid_data(self) -> Dict[str, Any]:
        """创建订单有效数据"""
        return {
            "json": {
                "user_id": random.randint(1, 1000),
                "items": [
                    {
                        "product_id": random.randint(1, 100),
                        "quantity": random.randint(1, 5),
                        "price": round(random.uniform(10.0, 100.0), 2)
                    }
                    for _ in range(random.randint(1, 3))
                ],
                "shipping_address": {
                    "street": f"Test Street {random.randint(1, 999)}",
                    "city": "Test City",
                    "postal_code": f"{random.randint(100000, 999999)}",
                    "country": "China"
                },
                "payment_method": random.choice(["credit_card", "paypal", "bank_transfer"])
            }
        }
    
    def _get_update_order_valid_data(self) -> Dict[str, Any]:
        """更新订单有效数据"""
        return {
            "json": {
                "status": random.choice(["confirmed", "shipped", "delivered"]),
                "tracking_number": f"TRK{self.generate_random_string(10).upper()}"
            }
        }
    
    def _get_get_order_valid_data(self) -> Dict[str, Any]:
        """获取订单详情有效数据"""
        return {
            "params": {
                "include_items": True,
                "include_shipping": True
            }
        }
    
    def _get_cancel_order_valid_data(self) -> Dict[str, Any]:
        """取消订单有效数据"""
        return {
            "json": {
                "reason": random.choice(["customer_request", "out_of_stock", "payment_failed"]),
                "refund": True
            }
        }
    
    # 订单无效数据生成器
    def _get_order_invalid_data(self) -> Dict[str, Any]:
        """订单列表查询无效数据"""
        return {
            "params": {
                "status": "invalid_status",
                "date_from": "invalid_date",
                "date_to": "invalid_date"
            }
        }
    
    def _get_create_order_invalid_data(self) -> Dict[str, Any]:
        """创建订单无效数据"""
        return {
            "json": {
                "user_id": "invalid_user_id",  # 应该是数字
                "items": [],  # 空商品列表
                "payment_method": "invalid_method"  # 无效支付方式
            }
        }
    
    # 订单边界值数据生成器
    def _get_order_boundary_data(self) -> Dict[str, Any]:
        """订单列表查询边界值数据"""
        return {
            "params": {
                "date_from": "1970-01-01T00:00:00Z",  # 最早日期
                "date_to": "2099-12-31T23:59:59Z"  # 最晚日期
            }
        }
    
    def _get_create_order_boundary_data(self) -> Dict[str, Any]:
        """创建订单边界值数据"""
        return {
            "json": {
                "user_id": 1,  # 最小用户ID
                "items": [
                    {
                        "product_id": 1,
                        "quantity": 1,  # 最小数量
                        "price": 0.01  # 最小价格
                    }
                ] * 100  # 最大商品数量
            }
        }
    
    # 默认数据生成器
    def _get_default_valid_data(self) -> Dict[str, Any]:
        """默认有效数据"""
        return {
            "params": {"test": True},
            "json": {"message": "test data"}
        }
    
    def _get_default_invalid_data(self) -> Dict[str, Any]:
        """默认无效数据"""
        return {
            "params": {"invalid": "data"},
            "json": {"error": "invalid test data"}
        }
    
    def _get_default_boundary_data(self) -> Dict[str, Any]:
        """默认边界值数据"""
        return {
            "params": {"boundary": "test"},
            "json": {"limit": "boundary test data"}
        }
    
    # 工具方法
    def generate_random_string(self, length: int) -> str:
        """生成随机字符串"""
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))
    
    def generate_random_email(self) -> str:
        """生成随机邮箱"""
        username = self.generate_random_string(8)
        domain = random.choice(["example.com", "test.org", "demo.net"])
        return f"{username}@{domain}"
    
    def generate_random_phone(self) -> str:
        """生成随机电话号码"""
        return f"1{random.randint(3000000000, 9999999999)}"
    
    def generate_future_date(self, days: int = 30) -> str:
        """生成未来日期"""
        future_date = datetime.now() + timedelta(days=days)
        return future_date.isoformat()
    
    def generate_past_date(self, days: int = 30) -> str:
        """生成过去日期"""
        past_date = datetime.now() - timedelta(days=days)
        return past_date.isoformat()
