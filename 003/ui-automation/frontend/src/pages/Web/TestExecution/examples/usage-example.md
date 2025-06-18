# 脚本执行功能使用示例

## 快速开始

### 1. 启动后端服务
确保后端脚本执行服务正在运行：
```bash
# 在后端目录下
python -m uvicorn app.main:app --reload --port 8000
```

### 2. 验证工作空间
确保Playwright工作空间存在并配置正确：
```
C:\Users\86134\Desktop\workspace\playwright-workspace\
├── package.json
├── e2e/
│   ├── fixture.ts
│   ├── test1.spec.ts
│   ├── test2.spec.ts
│   └── ...
└── midscene_run/
    └── report/
```

### 3. 访问前端页面
打开浏览器访问：`http://localhost:3000/web/test-execution`

## 使用场景示例

### 场景1: 执行单个现有脚本

1. **进入脚本管理标签**
   - 查看工作空间状态（应显示"正常"）
   - 浏览可用脚本列表

2. **选择并执行脚本**
   - 在脚本列表中找到目标脚本（如`ebay-search.spec.ts`）
   - 点击"执行"按钮
   - 系统会创建执行会话并显示会话ID

3. **监控执行状态**
   - 右侧状态面板自动显示
   - 实时查看执行进度和日志
   - 等待执行完成

4. **查看结果**
   - 执行完成后查看测试报告
   - 点击报告链接在浏览器中打开

### 场景2: 批量执行多个脚本

1. **选择多个脚本**
   - 在脚本管理标签中
   - 使用复选框选择多个脚本
   - 配置批量执行选项

2. **配置执行参数**
   - 点击"配置"按钮
   - 设置基础URL、超时时间等
   - 选择串行或并行执行模式

3. **启动批量执行**
   - 点击"批量执行"按钮
   - 监控每个脚本的执行状态
   - 查看整体执行进度

### 场景3: 快速执行自定义脚本

1. **进入快速执行标签**
   - 选择"输入脚本内容"模式

2. **编写测试脚本**
   ```typescript
   import { test, expect } from '@playwright/test';
   
   test('快速测试示例', async ({ page }) => {
     await page.goto('https://www.baidu.com');
     await expect(page).toHaveTitle(/百度/);
     
     // 搜索功能测试
     await page.fill('#kw', 'Playwright');
     await page.click('#su');
     await page.waitForSelector('.result');
     
     const results = await page.locator('.result').count();
     expect(results).toBeGreaterThan(0);
   });
   ```

3. **配置执行环境**
   - 设置基础URL（可选）
   - 选择有界面模式（用于调试）
   - 配置超时时间

4. **执行并监控**
   - 点击"开始执行"
   - 实时查看执行日志
   - 等待完成并查看报告

## API调用示例

### 前端调用示例

```typescript
// 获取可用脚本
const scripts = await getAvailableScripts();
console.log('可用脚本:', scripts.scripts);

// 执行单个脚本
const result = await executeSingleScript({
  script_name: 'test.spec.ts',
  base_url: 'https://example.com',
  headed: false,
  timeout: 90
});
console.log('执行会话ID:', result.session_id);

// 创建SSE连接监控状态
const eventSource = createScriptExecutionSSE(
  result.session_id,
  (event) => {
    const data = JSON.parse(event.data);
    console.log('收到消息:', data);
  }
);
```

### 后端API测试

```bash
# 获取脚本列表
curl -X GET "http://localhost:8000/api/v1/web/scripts/scripts"

# 执行单个脚本
curl -X POST "http://localhost:8000/api/v1/web/scripts/execute/single" \
  -F "script_name=test.spec.ts" \
  -F "base_url=https://example.com" \
  -F "headed=false"

# 获取会话状态
curl -X GET "http://localhost:8000/api/v1/web/scripts/sessions/{session_id}/status"
```

## 常见问题解决

### 问题1: 工作空间显示异常
**症状**: 工作空间状态显示"异常"或脚本数量为0

**解决方案**:
1. 检查工作空间路径是否存在
2. 确认e2e目录下有.spec.ts文件
3. 检查文件权限
4. 点击"刷新"按钮重新加载

### 问题2: 脚本执行失败
**症状**: 脚本状态显示"failed"

**解决方案**:
1. 查看错误日志了解具体原因
2. 检查脚本语法是否正确
3. 确认依赖环境是否安装
4. 调整超时时间配置

### 问题3: SSE连接断开
**症状**: 状态面板显示"disconnected"

**解决方案**:
1. 检查网络连接
2. 确认后端服务正常运行
3. 点击"重连"按钮
4. 刷新页面重新建立连接

### 问题4: 报告无法打开
**症状**: 点击报告链接无响应

**解决方案**:
1. 确认报告文件已生成
2. 检查文件路径是否正确
3. 确认浏览器允许打开本地文件
4. 手动导航到报告目录

## 最佳实践

### 1. 脚本组织
- 将相关测试脚本放在同一目录
- 使用描述性的文件名
- 添加适当的注释和文档

### 2. 执行配置
- 根据测试环境调整超时时间
- 在调试时使用有界面模式
- 合理设置环境变量

### 3. 批量执行
- 对于独立测试使用并行执行
- 对于有依赖关系的测试使用串行执行
- 设置合理的失败处理策略

### 4. 监控和调试
- 及时查看执行日志
- 保存重要的测试报告
- 定期清理过期会话

## 性能建议

### 1. 前端优化
- 避免同时打开过多会话
- 定期清理浏览器缓存
- 使用合适的刷新频率

### 2. 后端优化
- 控制并发执行数量
- 定期清理临时文件
- 监控系统资源使用

### 3. 网络优化
- 使用稳定的网络连接
- 避免在网络高峰期执行大量测试
- 考虑使用本地代理

通过以上示例和指导，您可以充分利用优化后的脚本执行功能，提高测试效率和用户体验。
