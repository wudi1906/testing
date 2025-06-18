# UI自动化测试系统 - 智能体工厂

## 概述

智能体工厂（AgentFactory）是UI自动化测试系统的核心组件，提供统一的智能体创建、管理和注册接口。通过工厂模式，系统可以灵活地创建和管理各种类型的智能体，包括 AssistantAgent 和自定义智能体。

## 核心特性

### 🏭 统一工厂管理
- 集中管理所有智能体的创建和注册
- 支持多种模型客户端（DeepSeek、UI-TARS等）
- 提供标准化的智能体初始化流程

### 🤖 智能体类型支持
- **图片分析智能体** - 基于多模态模型的UI界面分析
- **YAML生成智能体** - 生成MidScene.js格式的测试脚本
- **Playwright生成智能体** - 生成Playwright测试代码
- **YAML执行智能体** - 执行YAML格式的测试脚本
- **Playwright执行智能体** - 执行Playwright测试脚本

### 🔧 灵活配置
- 支持不同模型客户端的选择
- 可配置智能体初始化参数
- 支持用户反馈和流式响应

## 使用方法

### 基础使用

```python
from app.agents.factory import AgentFactory, agent_factory

# 使用全局工厂实例
factory = agent_factory

# 或创建新的工厂实例
factory = AgentFactory()
```

### 创建 AssistantAgent

```python
# 创建基于DeepSeek模型的智能体
deepseek_agent = factory.create_assistant_agent(
    name="yaml_generator",
    system_message="你是YAML生成专家...",
    model_client_type="deepseek",
    model_client_stream=True
)

# 创建基于UI-TARS模型的智能体
uitars_agent = factory.create_assistant_agent(
    name="ui_analyzer",
    system_message="你是UI分析专家...",
    model_client_type="uitars",
    model_client_stream=True
)
```

### 创建自定义智能体

```python
from app.core.types import AgentTypes

# 创建YAML生成智能体
yaml_agent = factory.create_agent(
    agent_type=AgentTypes.YAML_GENERATOR.value
)

# 创建图片分析智能体
image_agent = factory.create_agent(
    agent_type=AgentTypes.IMAGE_ANALYZER.value,
    enable_user_feedback=False,
    collector=response_collector
)
```

### 注册智能体到运行时

```python
from autogen_core import SingleThreadedAgentRuntime
from app.core.agents import StreamResponseCollector

# 创建运行时和收集器
runtime = SingleThreadedAgentRuntime()
runtime.start()
collector = StreamResponseCollector()

# 注册所有Web智能体
await factory.register_all_agents(
    runtime=runtime,
    collector=collector,
    enable_user_feedback=False
)

# 或只注册Web平台智能体
await factory.register_web_agents(
    runtime=runtime,
    collector=collector,
    enable_user_feedback=False
)
```

### 管理智能体

```python
# 获取可用智能体列表
available_agents = factory.list_available_agents()
for agent in available_agents:
    print(f"{agent['agent_name']} ({agent['agent_type']})")

# 获取已注册智能体列表
registered_agents = factory.list_registered_agents()

# 获取特定智能体信息
agent_info = factory.get_agent_info(AgentTypes.YAML_GENERATOR.value)

# 清空注册记录
factory.clear_registered_agents()
```

## 智能体类型

### 分析类智能体

#### ImageAnalyzerAgent
- **功能**: 基于多模态模型分析UI界面图片
- **特性**: 支持团队协作、用户反馈、GraphFlow工作流
- **模型**: UI-TARS（推荐）
- **输出**: 结构化的UI元素和交互流程分析

### 生成类智能体

#### YAMLGeneratorAgent
- **功能**: 生成MidScene.js格式的YAML测试脚本
- **特性**: 基于UI分析结果生成高质量测试脚本
- **模型**: DeepSeek（推荐）
- **输出**: 标准MidScene.js YAML格式脚本

#### PlaywrightGeneratorAgent
- **功能**: 生成Playwright + MidScene.js测试代码
- **特性**: 生成完整的TypeScript测试项目
- **模型**: DeepSeek（推荐）
- **输出**: 完整的Playwright测试项目文件

### 执行类智能体

#### YAMLExecutorAgent
- **功能**: 执行YAML格式的测试脚本
- **特性**: 支持MidScene.js命令行执行
- **依赖**: Node.js、MidScene.js CLI
- **输出**: 测试执行结果和报告

#### PlaywrightExecutorAgent
- **功能**: 执行Playwright测试脚本
- **特性**: 支持完整的Playwright测试流程
- **依赖**: Node.js、Playwright
- **输出**: 测试结果、截图、视频、报告

## 与编排器集成

智能体工厂与Web编排器（WebOrchestrator）深度集成：

```python
from app.services.web.orchestrator_service import WebOrchestrator

# 创建编排器（自动使用智能体工厂）
orchestrator = WebOrchestrator(collector)

# 获取智能体工厂信息
factory_info = orchestrator.get_agent_factory_info()

# 获取可用智能体
available_agents = orchestrator.get_available_agents()

# 创建自定义工作流
workflow_result = await orchestrator.create_custom_agent_workflow(
    session_id="custom_session",
    agent_types=[AgentTypes.IMAGE_ANALYZER.value, AgentTypes.YAML_GENERATOR.value],
    workflow_config={"timeout": 300}
)
```

## 配置说明

### 模型客户端配置

智能体工厂支持多种模型客户端：

- **deepseek**: 用于文本生成任务（YAML、Playwright代码生成）
- **uitars**: 用于多模态分析任务（图片分析）

### 智能体参数配置

每个智能体支持以下通用参数：

- `model_client_instance`: 自定义模型客户端实例
- `enable_user_feedback`: 是否启用用户反馈（仅部分智能体支持）
- `collector`: 响应收集器实例
- `**kwargs`: 其他自定义参数

## 测试验证

运行测试脚本验证智能体工厂功能：

```bash
cd backend
python test_agent_factory.py
```

测试内容包括：
- 智能体工厂基础功能
- AssistantAgent创建功能
- 自定义智能体创建功能
- 智能体注册功能
- 编排器集成功能

## 最佳实践

### 1. 使用全局工厂实例
```python
from app.agents.factory import agent_factory
# 推荐使用全局实例，避免重复初始化
```

### 2. 合理选择模型客户端
```python
# 图片分析使用UI-TARS
image_agent = factory.create_agent(AgentTypes.IMAGE_ANALYZER.value)

# 文本生成使用DeepSeek
yaml_agent = factory.create_agent(AgentTypes.YAML_GENERATOR.value)
```

### 3. 及时清理资源
```python
# 使用完毕后清理注册记录
factory.clear_registered_agents()

# 关闭运行时
await runtime.stop_when_idle()
await runtime.close()
```

### 4. 错误处理
```python
try:
    agent = factory.create_agent(agent_type)
except ValueError as e:
    logger.error(f"无效的智能体类型: {e}")
except Exception as e:
    logger.error(f"创建智能体失败: {e}")
```

## 扩展开发

### 添加新的智能体类型

1. 在 `app.core.types.enums.py` 中添加新的智能体类型
2. 在 `app.core.types.constants.py` 中添加智能体名称映射
3. 创建智能体实现类，继承自 `BaseAgent`
4. 在工厂的 `_register_agent_classes` 方法中注册新类型

### 添加新的模型客户端

1. 在 `app.core.llms` 中实现新的模型客户端
2. 在工厂的 `create_assistant_agent` 方法中添加支持
3. 更新相关智能体的模型选择逻辑

## 故障排除

### 常见问题

1. **智能体创建失败**
   - 检查模型客户端配置
   - 验证智能体类型是否正确
   - 查看日志获取详细错误信息

2. **注册失败**
   - 确保运行时已正确启动
   - 检查智能体类的 `@type_subscription` 装饰器
   - 验证主题类型配置

3. **模型调用失败**
   - 检查API密钥配置
   - 验证网络连接
   - 查看模型服务状态

### 调试技巧

1. 启用详细日志：
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

2. 使用测试脚本验证功能
3. 检查智能体工厂信息：
```python
factory_info = factory.get_agent_factory_info()
print(factory_info)
```
