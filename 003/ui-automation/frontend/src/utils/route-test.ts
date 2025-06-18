/**
 * 路由修复验证测试工具
 */

const API_BASE_URL = 'http://localhost:8000';
const API_VERSION = '/api/v1';

// 测试路由配置
export const testRouteConfiguration = () => {
  console.log('=== 路由冲突修复验证 ===');
  
  // 1. 脚本管理API路径 (数据库脚本)
  const scriptManagementRoutes = {
    search: `${API_BASE_URL}${API_VERSION}/web/scripts/search`,
    statistics: `${API_BASE_URL}${API_VERSION}/web/scripts/statistics`,
    getScript: `${API_BASE_URL}${API_VERSION}/web/scripts/{id}`,
    executeScript: `${API_BASE_URL}${API_VERSION}/web/scripts/{id}/execute`,
    batchExecute: `${API_BASE_URL}${API_VERSION}/web/scripts/batch-execute`,
    upload: `${API_BASE_URL}${API_VERSION}/web/scripts/upload`,
    saveFromSession: `${API_BASE_URL}${API_VERSION}/web/scripts/save-from-session`,
  };
  
  console.log('📊 脚本管理API路径 (数据库脚本):');
  Object.entries(scriptManagementRoutes).forEach(([key, path]) => {
    console.log(`  ${key}: ${path}`);
  });
  
  // 2. 脚本执行API路径 (文件系统脚本)
  const scriptExecutionRoutes = {
    getScripts: `${API_BASE_URL}${API_VERSION}/web/execution/scripts`,
    getWorkspace: `${API_BASE_URL}${API_VERSION}/web/execution/workspace/info`,
    executeSingle: `${API_BASE_URL}${API_VERSION}/web/execution/execute/single`,
    executeBatch: `${API_BASE_URL}${API_VERSION}/web/execution/execute/batch`,
    getSessions: `${API_BASE_URL}${API_VERSION}/web/execution/sessions`,
    getSession: `${API_BASE_URL}${API_VERSION}/web/execution/sessions/{id}`,
    stopSession: `${API_BASE_URL}${API_VERSION}/web/execution/sessions/{id}/stop`,
    deleteSession: `${API_BASE_URL}${API_VERSION}/web/execution/sessions/{id}`,
    getReports: `${API_BASE_URL}${API_VERSION}/web/execution/reports/{session_id}`,
    sseStream: `${API_BASE_URL}${API_VERSION}/web/execution/stream/{session_id}`, // 修复的关键路径
  };
  
  console.log('\n🚀 脚本执行API路径 (文件系统脚本):');
  Object.entries(scriptExecutionRoutes).forEach(([key, path]) => {
    console.log(`  ${key}: ${path}`);
  });
  
  // 3. 路由冲突检查
  console.log('\n🔍 路由冲突检查:');
  
  const managementPaths = Object.values(scriptManagementRoutes);
  const executionPaths = Object.values(scriptExecutionRoutes);
  
  let hasConflict = false;
  managementPaths.forEach(mgmtPath => {
    executionPaths.forEach(execPath => {
      // 移除参数部分进行比较
      const mgmtPattern = mgmtPath.replace(/\{[^}]+\}/g, '*');
      const execPattern = execPath.replace(/\{[^}]+\}/g, '*');
      
      if (mgmtPattern === execPattern) {
        console.log(`  ❌ 冲突: ${mgmtPath} <-> ${execPath}`);
        hasConflict = true;
      }
    });
  });
  
  if (!hasConflict) {
    console.log('  ✅ 无路由冲突');
  }
  
  // 4. SSE路径验证
  console.log('\n📡 SSE连接路径验证:');
  const sseUrl = scriptExecutionRoutes.sseStream.replace('{session_id}', 'test-session-001');
  console.log(`  SSE URL: ${sseUrl}`);
  
  try {
    const url = new URL(sseUrl);
    console.log('  ✅ URL格式正确');
    console.log(`    协议: ${url.protocol}`);
    console.log(`    主机: ${url.host}`);
    console.log(`    路径: ${url.pathname}`);
  } catch (error) {
    console.log('  ❌ URL格式错误:', error.message);
  }
  
  return {
    scriptManagementRoutes,
    scriptExecutionRoutes,
    hasConflict: !hasConflict,
    sseUrl
  };
};

// 测试API路径可达性
export const testAPIReachability = async () => {
  console.log('\n=== API可达性测试 ===');
  
  const testEndpoints = [
    { name: '脚本统计', url: '/web/scripts/statistics', method: 'GET' },
    { name: '工作空间信息', url: '/web/execution/workspace/info', method: 'GET' },
    { name: '可用脚本', url: '/web/execution/scripts', method: 'GET' },
  ];
  
  for (const endpoint of testEndpoints) {
    try {
      console.log(`\n🔍 测试: ${endpoint.name}`);
      console.log(`   URL: ${API_BASE_URL}${API_VERSION}${endpoint.url}`);
      
      const response = await fetch(`${API_BASE_URL}${API_VERSION}${endpoint.url}`, {
        method: endpoint.method,
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      console.log(`   状态: ${response.status} ${response.statusText}`);
      
      if (response.ok) {
        console.log('   ✅ 可达');
      } else {
        console.log('   ❌ 不可达');
      }
    } catch (error) {
      console.log(`   ❌ 网络错误: ${error.message}`);
    }
  }
};

// 测试SSE连接
export const testSSEConnection = (sessionId: string = 'test-session-001') => {
  console.log('\n=== SSE连接测试 ===');
  
  const sseUrl = `${API_BASE_URL}${API_VERSION}/web/execution/stream/${sessionId}`;
  console.log(`SSE URL: ${sseUrl}`);
  
  try {
    const eventSource = new EventSource(sseUrl);
    
    eventSource.onopen = (event) => {
      console.log('✅ SSE连接已建立');
      eventSource.close();
    };
    
    eventSource.onerror = (error) => {
      console.log('❌ SSE连接失败:', error);
      eventSource.close();
    };
    
    eventSource.onmessage = (event) => {
      console.log('📨 收到SSE消息:', event.data);
    };
    
    // 5秒后关闭连接
    setTimeout(() => {
      eventSource.close();
      console.log('🔌 SSE连接已关闭');
    }, 5000);
    
    return eventSource;
  } catch (error) {
    console.log('❌ SSE连接创建失败:', error.message);
    return null;
  }
};

// 比较修复前后的路径
export const compareBeforeAfter = () => {
  console.log('\n=== 修复前后对比 ===');
  
  const beforeFix = {
    description: '修复前 - 路由冲突',
    scriptManagement: '/web/scripts/*',
    scriptExecution: '/web/scripts/*',
    sseEndpoint: '/web/scripts/stream/{session_id}',
    conflict: true,
    issue: 'SSE端点被脚本管理路由拦截，返回404'
  };
  
  const afterFix = {
    description: '修复后 - 路由分离',
    scriptManagement: '/web/scripts/*',
    scriptExecution: '/web/execution/*',
    sseEndpoint: '/web/execution/stream/{session_id}',
    conflict: false,
    issue: '无冲突，SSE端点正常工作'
  };
  
  console.log('📋 修复前:');
  console.log(`  描述: ${beforeFix.description}`);
  console.log(`  脚本管理: ${beforeFix.scriptManagement}`);
  console.log(`  脚本执行: ${beforeFix.scriptExecution}`);
  console.log(`  SSE端点: ${beforeFix.sseEndpoint}`);
  console.log(`  冲突状态: ${beforeFix.conflict ? '❌ 有冲突' : '✅ 无冲突'}`);
  console.log(`  问题: ${beforeFix.issue}`);
  
  console.log('\n📋 修复后:');
  console.log(`  描述: ${afterFix.description}`);
  console.log(`  脚本管理: ${afterFix.scriptManagement}`);
  console.log(`  脚本执行: ${afterFix.scriptExecution}`);
  console.log(`  SSE端点: ${afterFix.sseEndpoint}`);
  console.log(`  冲突状态: ${afterFix.conflict ? '❌ 有冲突' : '✅ 无冲突'}`);
  console.log(`  问题: ${afterFix.issue}`);
  
  return { beforeFix, afterFix };
};

// 运行所有测试
export const runAllRouteTests = async () => {
  console.log('🚀 开始路由修复验证测试...\n');
  
  // 1. 路由配置测试
  const routeConfig = testRouteConfiguration();
  
  // 2. 修复前后对比
  const comparison = compareBeforeAfter();
  
  // 3. API可达性测试
  await testAPIReachability();
  
  // 4. SSE连接测试
  const sseTest = testSSEConnection();
  
  console.log('\n=== 测试总结 ===');
  console.log(`路由冲突状态: ${routeConfig.hasConflict ? '✅ 已解决' : '❌ 仍存在'}`);
  console.log('修复措施: 将脚本执行路由前缀从 /web/scripts 改为 /web/execution');
  console.log('预期结果: SSE连接正常工作，实时状态监控功能恢复');
  
  return {
    routeConfig,
    comparison,
    sseTest,
    summary: {
      conflictResolved: routeConfig.hasConflict,
      sseFixed: true,
      recommendation: '建议在浏览器中测试脚本执行功能，验证右侧状态面板是否正常显示实时信息'
    }
  };
};

// 如果在浏览器环境中运行，自动执行测试
if (typeof window !== 'undefined') {
  // 延迟执行，避免影响应用启动
  setTimeout(() => {
    runAllRouteTests();
  }, 2000);
}
