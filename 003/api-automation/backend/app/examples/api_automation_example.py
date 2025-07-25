"""
接口自动化智能体系统使用示例
演示如何使用智能体系统进行API文档解析、测试生成和执行
"""
import asyncio
import json
from pathlib import Path
from datetime import datetime

from app.services.api_automation import ApiAutomationOrchestrator
from app.core.agents.collector import StreamResponseCollector
from app.core.types import AgentPlatform


async def example_api_automation_workflow():
    """演示完整的API自动化工作流程"""
    print("🚀 开始API自动化智能体系统演示")
    
    # 1. 创建响应收集器
    collector = StreamResponseCollector(platform=AgentPlatform.API_AUTOMATION)
    
    # 设置回调函数来处理智能体响应
    async def response_callback(closure_ctx, message, msg_ctx):
        print(f"[{message.agent_name}] {message.content}")
        if message.result:
            print(f"  结果: {json.dumps(message.result, indent=2, ensure_ascii=False)}")
    
    collector.set_callback(response_callback)
    
    # 2. 创建编排器
    orchestrator = ApiAutomationOrchestrator(collector=collector)
    
    try:
        # 3. 初始化编排器
        print("\n📋 初始化智能体编排器...")
        await orchestrator.initialize()
        
        # 4. 创建示例API文档
        sample_api_doc = create_sample_api_document()
        doc_file_path = "./sample_api.json"
        
        with open(doc_file_path, 'w', encoding='utf-8') as f:
            json.dump(sample_api_doc, f, indent=2, ensure_ascii=False)
        
        print(f"✅ 创建示例API文档: {doc_file_path}")
        
        # 5. 处理API文档
        session_id = f"demo_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        print(f"\n🔍 开始处理API文档 (会话ID: {session_id})...")
        
        result = await orchestrator.process_api_document(
            session_id=session_id,
            file_path=doc_file_path,
            file_name="sample_api.json",
            doc_format="openapi",
            config={
                "include_error_cases": True,
                "include_boundary_cases": True,
                "include_performance_cases": False
            }
        )
        
        print(f"✅ API文档处理完成: {result}")
        
        # 6. 等待一段时间让智能体完成处理
        print("\n⏳ 等待智能体完成处理...")
        await asyncio.sleep(5)
        
        # 7. 获取会话状态
        status = await orchestrator.get_session_status(session_id)
        print(f"\n📊 会话状态: {json.dumps(status, indent=2, ensure_ascii=False)}")
        
        # 8. 获取系统指标
        metrics = await orchestrator.get_orchestrator_metrics()
        print(f"\n📈 系统指标: {json.dumps(metrics, indent=2, ensure_ascii=False)}")
        
        # 9. 演示测试执行（如果有生成的脚本）
        script_files = ["./generated_tests/test_users_api.py"]  # 示例脚本文件
        
        if Path(script_files[0]).parent.exists():
            print(f"\n🧪 执行测试脚本...")
            
            test_result = await orchestrator.execute_test_suite(
                session_id=session_id,
                script_files=script_files,
                test_config={
                    "framework": "pytest",
                    "parallel": False,
                    "max_workers": 1,
                    "timeout": 60,
                    "report_formats": ["html", "json"]
                }
            )
            
            print(f"✅ 测试执行结果: {test_result}")
        
        print("\n🎉 API自动化工作流程演示完成!")
        
    except Exception as e:
        print(f"❌ 演示过程中发生错误: {str(e)}")
        
    finally:
        # 10. 清理资源
        print("\n🧹 清理系统资源...")
        await orchestrator.cleanup()
        
        # 清理示例文件
        if Path(doc_file_path).exists():
            Path(doc_file_path).unlink()


def create_sample_api_document():
    """创建示例API文档"""
    return {
        "openapi": "3.0.0",
        "info": {
            "title": "用户管理API",
            "version": "1.0.0",
            "description": "用户管理系统的RESTful API接口"
        },
        "servers": [
            {
                "url": "https://api.example.com/v1",
                "description": "生产环境"
            }
        ],
        "paths": {
            "/users": {
                "get": {
                    "summary": "获取用户列表",
                    "description": "分页获取用户列表",
                    "tags": ["用户管理"],
                    "parameters": [
                        {
                            "name": "page",
                            "in": "query",
                            "description": "页码",
                            "required": False,
                            "schema": {
                                "type": "integer",
                                "default": 1
                            }
                        },
                        {
                            "name": "size",
                            "in": "query",
                            "description": "每页数量",
                            "required": False,
                            "schema": {
                                "type": "integer",
                                "default": 10
                            }
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "成功获取用户列表",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "code": {"type": "integer"},
                                            "message": {"type": "string"},
                                            "data": {
                                                "type": "object",
                                                "properties": {
                                                    "users": {
                                                        "type": "array",
                                                        "items": {"$ref": "#/components/schemas/User"}
                                                    },
                                                    "total": {"type": "integer"},
                                                    "page": {"type": "integer"},
                                                    "size": {"type": "integer"}
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                },
                "post": {
                    "summary": "创建用户",
                    "description": "创建新用户",
                    "tags": ["用户管理"],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/CreateUserRequest"}
                            }
                        }
                    },
                    "responses": {
                        "201": {
                            "description": "用户创建成功",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "code": {"type": "integer"},
                                            "message": {"type": "string"},
                                            "data": {"$ref": "#/components/schemas/User"}
                                        }
                                    }
                                }
                            }
                        },
                        "400": {
                            "description": "请求参数错误"
                        }
                    }
                }
            },
            "/users/{userId}": {
                "get": {
                    "summary": "获取用户详情",
                    "description": "根据用户ID获取用户详细信息",
                    "tags": ["用户管理"],
                    "parameters": [
                        {
                            "name": "userId",
                            "in": "path",
                            "required": True,
                            "description": "用户ID",
                            "schema": {
                                "type": "integer"
                            }
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "成功获取用户信息",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "code": {"type": "integer"},
                                            "message": {"type": "string"},
                                            "data": {"$ref": "#/components/schemas/User"}
                                        }
                                    }
                                }
                            }
                        },
                        "404": {
                            "description": "用户不存在"
                        }
                    }
                },
                "put": {
                    "summary": "更新用户信息",
                    "description": "更新指定用户的信息",
                    "tags": ["用户管理"],
                    "parameters": [
                        {
                            "name": "userId",
                            "in": "path",
                            "required": True,
                            "description": "用户ID",
                            "schema": {
                                "type": "integer"
                            }
                        }
                    ],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/UpdateUserRequest"}
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "用户信息更新成功"
                        },
                        "404": {
                            "description": "用户不存在"
                        }
                    }
                },
                "delete": {
                    "summary": "删除用户",
                    "description": "删除指定的用户",
                    "tags": ["用户管理"],
                    "parameters": [
                        {
                            "name": "userId",
                            "in": "path",
                            "required": True,
                            "description": "用户ID",
                            "schema": {
                                "type": "integer"
                            }
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "用户删除成功"
                        },
                        "404": {
                            "description": "用户不存在"
                        }
                    }
                }
            }
        },
        "components": {
            "schemas": {
                "User": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer", "description": "用户ID"},
                        "username": {"type": "string", "description": "用户名"},
                        "email": {"type": "string", "description": "邮箱"},
                        "name": {"type": "string", "description": "姓名"},
                        "status": {"type": "string", "enum": ["active", "inactive"], "description": "状态"},
                        "created_at": {"type": "string", "format": "date-time", "description": "创建时间"},
                        "updated_at": {"type": "string", "format": "date-time", "description": "更新时间"}
                    }
                },
                "CreateUserRequest": {
                    "type": "object",
                    "required": ["username", "email", "name"],
                    "properties": {
                        "username": {"type": "string", "description": "用户名"},
                        "email": {"type": "string", "description": "邮箱"},
                        "name": {"type": "string", "description": "姓名"},
                        "password": {"type": "string", "description": "密码"}
                    }
                },
                "UpdateUserRequest": {
                    "type": "object",
                    "properties": {
                        "email": {"type": "string", "description": "邮箱"},
                        "name": {"type": "string", "description": "姓名"},
                        "status": {"type": "string", "enum": ["active", "inactive"], "description": "状态"}
                    }
                }
            }
        }
    }


async def example_individual_agents():
    """演示单个智能体的使用"""
    print("\n🔧 演示单个智能体使用...")
    
    from app.agents.factory import agent_factory
    from app.core.messages.api_automation import ApiDocParseRequest
    from autogen_core import SingleThreadedAgentRuntime, TopicId
    
    # 创建运行时
    runtime = SingleThreadedAgentRuntime()
    
    try:
        # 注册智能体
        await agent_factory.register_agents_to_runtime(runtime)
        runtime.start()
        
        # 创建API文档解析请求
        parse_request = ApiDocParseRequest(
            session_id="individual_test",
            file_path="./sample_api.json",
            file_name="sample_api.json",
            doc_format="openapi"
        )
        
        # 发送请求到API文档解析智能体
        await runtime.publish_message(
            parse_request,
            topic_id=TopicId(type="api_doc_parser", source="example")
        )
        
        print("✅ 已发送API文档解析请求")
        
        # 等待处理
        await asyncio.sleep(3)
        
    finally:
        runtime.stop()
        await agent_factory.cleanup_all()


if __name__ == "__main__":
    # 运行完整工作流程演示
    asyncio.run(example_api_automation_workflow())
    
    # 运行单个智能体演示
    # asyncio.run(example_individual_agents())
