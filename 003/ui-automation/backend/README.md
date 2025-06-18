# UI自动化测试系统 - 后端服务

基于多模态大模型与多智能体协作的自动化测试系统后端服务。

## 🏗️ 架构概览

### 核心架构
```
├── 🌐 API层 (FastAPI)
│   ├── Web图像分析接口
│   ├── 脚本管理接口
│   ├── 脚本执行接口
│   └── 测试报告接口
│
├── 🔧 服务层 (Business Logic)
│   ├── 图像分析服务
│   ├── 脚本管理服务
│   ├── 执行编排服务
│   └── 测试报告服务
│
├── 🤖 智能体层 (AI Agents)
│   ├── Web图像分析智能体
│   ├── YAML生成智能体
│   ├── Playwright生成智能体
│   └── 脚本执行智能体
│
├── 💾 数据层 (Database)
│   ├── MySQL (主数据库)
│   ├── Neo4j (图数据库)
│   └── Milvus (向量数据库)
│
└── 🔌 集成层 (External Services)
    ├── MidScene.js
    ├── Playwright
    └── 多模态AI模型
```

## 📁 目录结构

```
backend/
├── app/                          # 主应用目录
│   ├── api/                      # API接口层
│   │   └── v1/
│   │       ├── endpoints/        # API端点
│   │       │   ├── web/         # Web模块API
│   │       │   ├── sessions.py  # 会话管理
│   │       │   └── system.py    # 系统管理
│   │       └── api.py           # 路由汇总
│   │
│   ├── services/                 # 业务服务层
│   │   ├── script.py            # 脚本管理服务
│   │   ├── report.py            # 测试报告服务
│   │   ├── analysis.py          # 图像分析服务
│   │   └── execution.py         # 执行编排服务
│   │
│   ├── agents/                   # 智能体层
│   │   ├── web/                 # Web平台智能体
│   │   └── factory.py           # 智能体工厂
│   │
│   ├── core/                     # 核心模块
│   │   ├── config.py            # 配置管理
│   │   ├── logging.py           # 日志管理
│   │   ├── llms.py              # AI模型客户端
│   │   ├── agents/              # 智能体基础组件
│   │   ├── messages/            # 消息类型定义
│   │   └── types/               # 类型定义
│   │
│   ├── database/                 # 数据库层
│   │   ├── connection.py        # 数据库连接
│   │   ├── models/              # 数据模型
│   │   └── repositories/        # 数据仓库
│   │
│   ├── models/                   # Pydantic模型
│   ├── schemas/                  # API模式定义
│   ├── utils/                    # 工具函数
│   └── main.py                   # 应用入口
│
├── tests/                        # 测试目录
│   ├── unit/                    # 单元测试
│   ├── integration/             # 集成测试
│   └── e2e/                     # 端到端测试
│
├── docs/                         # 文档目录
├── migrations/                   # 数据库迁移
├── scripts/                      # 脚本工具
├── logs/                         # 日志文件
├── uploads/                      # 上传文件
├── .env.example                  # 环境变量模板
└── README.md                     # 项目说明
```

## 🚀 快速开始

### 环境要求
- Python 3.8+
- MySQL 8.0+
- Redis 6.0+
- Node.js 16+ (用于Playwright)

### 安装依赖
```bash
# 安装Python依赖
pip install -r requirements.txt

# 安装Playwright浏览器
playwright install
```

### 配置环境
```bash

# 编辑配置文件
.env
```

### 启动服务
```bash
# 开发模式
python app/main.py

# 生产模式
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 🔧 核心功能

### 1. Web图像分析
- 多模态AI模型图像分析
- UI元素识别和定位
- 用户交互流程分析
- 测试场景自动生成

### 2. 脚本管理
- 测试脚本的CRUD操作
- 脚本搜索和过滤
- 标签和分类管理
- 版本控制支持

### 3. 脚本执行
- 多格式脚本执行支持
- 实时执行状态监控
- 批量执行管理
- 执行结果收集

### 4. 测试报告
- 自动生成测试报告
- 执行结果统计分析
- 报告文件管理
- 历史记录查询

## 🤖 AI模型集成

### 支持的模型
- **UI-TARS**: 专业GUI分析和坐标定位
- **Qwen-VL**: 通用视觉理解和多模态推理
- **DeepSeek**: 文本生成和逻辑推理

### 智能选择策略
系统根据任务类型自动选择最适合的AI模型：
- GUI任务优先使用UI-TARS
- 通用视觉任务使用Qwen-VL
- 文本生成任务使用DeepSeek

## 📊 数据库设计

### 主要数据表
- `projects`: 项目管理
- `sessions`: 分析会话
- `test_scripts`: 测试脚本
- `script_executions`: 执行记录
- `test_reports`: 测试报告

## 🔌 API接口

### 主要端点
```
POST /api/v1/web/create/analyze/image    # 图像分析
GET  /api/v1/web/scripts                 # 脚本列表
POST /api/v1/web/execution/execute       # 执行脚本
GET  /api/v1/web/reports                 # 测试报告
```

详细API文档: http://localhost:8000/api/v1/docs

## 🧪 测试

```bash
# 运行单元测试
pytest tests/unit/

# 运行集成测试
pytest tests/integration/

# 运行所有测试
pytest tests/
```

## 📝 开发指南

### 代码规范
- 遵循PEP 8代码风格
- 使用类型注解
- 编写完整的文档字符串
- 保持函数和类的单一职责

### 提交规范
- feat: 新功能
- fix: 修复bug
- docs: 文档更新
- style: 代码格式调整
- refactor: 代码重构
- test: 测试相关
- chore: 构建过程或辅助工具的变动

## 🔒 安全性

- API密钥安全存储
- 输入数据验证
- SQL注入防护
- 文件上传安全检查
- 访问权限控制

## 📈 性能优化

- 异步处理支持
- 数据库连接池
- 缓存机制
- 批量操作优化
- 资源清理机制

## 🛠️ 故障排除

### 常见问题
1. **数据库连接失败**: 检查数据库配置和网络连接
2. **AI模型调用失败**: 验证API密钥和网络访问
3. **脚本执行超时**: 调整超时配置和资源限制
4. **文件上传失败**: 检查文件大小和格式限制

### 日志查看
```bash
# 查看应用日志
tail -f logs/app.log

# 查看错误日志
tail -f logs/error.log
```

## 📞 支持

如有问题或建议，请联系开发团队或提交Issue。
