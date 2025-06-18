# Web模块组件结构

## 概述
Web模块是UI自动化测试系统的核心模块，专门处理Web应用的自动化测试。

## 目录结构
```
Web/
├── index.tsx                    # Web模块入口文件，路由配置
├── TestCreation/               # 测试创建页面
│   ├── TestCreation.tsx       # 主组件文件
│   └── TestCreation.css       # 样式文件
├── TestExecution/              # 测试执行页面
│   ├── TestExecution.tsx      # 主组件文件
│   └── TestExecution.css      # 样式文件
├── TestResults/                # 测试结果页面
│   ├── TestResults.tsx        # 主组件文件
│   └── TestResults.css        # 样式文件
├── TestReports/                # 测试报告页面
│   ├── TestReports.tsx        # 主组件文件
│   └── TestReports.css        # 样式文件
├── components/                  # Web模块组件
│   └── WebTestCreation/        # Web测试创建组件
│       ├── WebTestCreation.tsx # 主组件文件
│       ├── WebTestCreation.css # 样式文件
│       └── index.ts           # 组件导出文件
├── ImageAnalysis/              # 图片分析模块
└── README.md                   # 说明文档
```

## 主要功能

### 1. 流式数据展示
- 使用 `StreamingDisplay` 组件替换原来的测试模板
- 实时显示AI分析进度和消息
- 支持SSE (Server-Sent Events) 连接
- 显示分析完成后的最终结果

### 2. 图片分析
- 支持上传UI截图进行分析
- AI智能识别UI元素和用户流程
- 生成YAML和Playwright测试脚本
- 实时显示分析进度

### 3. 网页分析
- 支持单页面URL分析
- 支持多页面递归抓取 (Crawl4AI)
- 智能生成完整测试套件
- 可配置抓取策略和深度

## 技术特点

### 1. 模块化设计
- 按功能模块组织代码
- 组件职责清晰，易于维护
- 支持独立开发和测试

### 2. 流式处理
- 实时显示AI处理进度
- 用户体验友好
- 支持长时间运行的任务

### 3. 响应式设计
- 适配不同屏幕尺寸
- 移动端友好
- 现代化UI设计

## 使用方式

### 路由访问
- `/web/create` - Web测试创建页面
- `/web/execution` - Web测试执行页面
- `/web/results` - Web测试结果页面
- `/web/reports` - Web测试报告页面
- 更多路由可在 `index.tsx` 中配置

### 组件集成
```tsx
import WebModule from '../Web';

// 在路由中使用
<Route path="/web/*" element={<WebModule />} />
```

## 开发说明

### 1. 添加新功能
在 `components/` 目录下创建新的组件文件夹，按照现有结构组织代码。

### 2. 样式规范
- 使用CSS模块化
- 遵循Ant Design设计规范
- 支持主题定制

### 3. 状态管理
- 使用React Hooks管理组件状态
- 通过props传递数据
- 支持全局状态管理（如需要）

## 后续扩展

### 1. 测试执行模块
- 添加 `WebTestExecution` 组件
- 支持YAML和Playwright脚本执行
- 实时显示执行结果

### 2. 测试报告模块
- 添加 `WebTestReports` 组件
- 生成详细的测试报告
- 支持多种报告格式

### 3. 脚本管理模块
- 添加 `WebScriptManager` 组件
- 管理生成的测试脚本
- 支持版本控制和分享
