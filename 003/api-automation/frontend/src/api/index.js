import { request } from '@/utils'

export default {
  login: (data) => request.post('/base/access_token', data, { noNeedToken: true }),
  getUserInfo: () => request.get('/base/userinfo'),
  getUserMenu: () => request.get('/base/usermenu'),
  getUserApi: () => request.get('/base/userapi'),
  // profile
  updatePassword: (data = {}) => request.post('/base/update_password', data),
  // users
  getUserList: (params = {}) => request.get('/user/list', { params }),
  getUserById: (params = {}) => request.get('/user/get', { params }),
  createUser: (data = {}) => request.post('/user/create', data),
  updateUser: (data = {}) => request.post('/user/update', data),
  deleteUser: (params = {}) => request.delete(`/user/delete`, { params }),
  resetPassword: (data = {}) => request.post(`/user/reset_password`, data),
  // role
  getRoleList: (params = {}) => request.get('/role/list', { params }),
  createRole: (data = {}) => request.post('/role/create', data),
  updateRole: (data = {}) => request.post('/role/update', data),
  deleteRole: (params = {}) => request.delete('/role/delete', { params }),
  updateRoleAuthorized: (data = {}) => request.post('/role/authorized', data),
  getRoleAuthorized: (params = {}) => request.get('/role/authorized', { params }),
  // menus
  getMenus: (params = {}) => request.get('/menu/list', { params }),
  createMenu: (data = {}) => request.post('/menu/create', data),
  updateMenu: (data = {}) => request.post('/menu/update', data),
  deleteMenu: (params = {}) => request.delete('/menu/delete', { params }),
  // apis
  getApis: (params = {}) => request.get('/api/list', { params }),
  createApi: (data = {}) => request.post('/api/create', data),
  updateApi: (data = {}) => request.post('/api/update', data),
  deleteApi: (params = {}) => request.delete('/api/delete', { params }),
  refreshApi: (data = {}) => request.post('/api/refresh', data),
  // depts
  getDepts: (params = {}) => request.get('/dept/list', { params }),
  createDept: (data = {}) => request.post('/dept/create', data),
  updateDept: (data = {}) => request.post('/dept/update', data),
  deleteDept: (params = {}) => request.delete('/dept/delete', { params }),
  // auditlog
  getAuditLogList: (params = {}) => request.get('/auditlog/list', { params }),

  // API自动化相关接口
  // 仪表板统计
  getDashboardStatistics: () => request.get('/api-automation/dashboard/statistics'),
  getRecentActivities: (params = {}) => request.get('/api-automation/dashboard/activities', { params }),
  getExecutionQueue: () => request.get('/api-automation/dashboard/queue'),
  getSystemStatus: () => request.get('/api-automation/dashboard/status'),

  // 文档管理
  uploadDocument: (formData) => request.post('/api-automation/upload-document', formData),
  getParseStatus: (sessionId) => request.get(`/api-automation/parse-status/${sessionId}`),
  triggerDocumentParse: (sessionId, config = {}) => request.post(`/api-automation/parse-document/${sessionId}`, config),
  parseApiDocument: (data = {}) => request.post('/api-automation/parse-document', data),
  getParseResult: (params = {}) => request.get('/api-automation/parse-result', { params }),
  getApiDocuments: (params = {}) => request.get('/api-automation/documents', { params }),
  getDocumentDetail: (params = {}) => request.get('/api-automation/document-detail', { params }),

  // 接口管理
  getApiEndpoints: (params = {}) => request.get('/api-automation/endpoints', { params }),
  analyzeApiEndpoints: (data = {}) => request.post('/api-automation/analyze-endpoints', data),
  getAnalysisResult: (params = {}) => request.get('/api-automation/analysis-result', { params }),

  // 测试脚本管理
  getTestScripts: (params = {}) => request.get('/api-automation/test-scripts', { params }),
  createTestScript: (data = {}) => request.post('/api-automation/test-scripts', data),
  updateTestScript: (data = {}) => request.put('/api-automation/test-scripts', data),
  deleteTestScript: (params = {}) => request.delete('/api-automation/test-scripts', { params }),
  getScriptContent: (params = {}) => request.get('/api-automation/script-content', { params }),
  updateScriptContent: (data = {}) => request.put('/api-automation/script-content', data),
  executeTestScript: (data = {}) => request.post('/api-automation/execute-script', data),
  debugTestScript: (data = {}) => request.post('/api-automation/debug-script', data),
  getScriptExecutionHistory: (params = {}) => request.get('/api-automation/script-history', { params }),

  // 测试生成
  generateTestScripts: (data = {}) => request.post('/api-automation/generate-tests', data),
  getGenerationResult: (params = {}) => request.get('/api-automation/generation-result', { params }),
  executeScript: (data = {}) => request.post('/api-automation/execute-script', data),
  executeAllScripts: (data = {}) => request.post('/api-automation/execute-all-scripts', data),

  // 测试执行
  getTestExecutions: (params = {}) => request.get('/api-automation/test-executions', { params }),
  executeTests: (data = {}) => request.post('/api-automation/execute-tests', data),
  getExecutionDetail: (params = {}) => request.get('/api-automation/execution-detail', { params }),
  getTestResults: (params = {}) => request.get('/api-automation/test-results', { params }),
  getExecutionLogs: (params = {}) => request.get('/api-automation/execution-logs', { params }),
  stopExecution: (data = {}) => request.post('/api-automation/stop-execution', data),

  // 测试报告
  generateTestReport: (data = {}) => request.post('/api-automation/generate-report', data),
  getTestReports: (params = {}) => request.get('/api-automation/test-reports', { params }),
  getReportContent: (params = {}) => request.get('/api-automation/report-content', { params }),
  downloadReport: (params = {}) => request.get('/api-automation/download-report', { params, responseType: 'blob' }),

  // 定时任务管理
  getScheduledTasks: (params = {}) => request.get('/api-automation/scheduled-tasks', { params }),
  createScheduledTask: (data = {}) => request.post('/api-automation/scheduled-tasks', data),
  updateScheduledTask: (data = {}) => request.put('/api-automation/scheduled-tasks', data),
  deleteScheduledTask: (params = {}) => request.delete('/api-automation/scheduled-tasks', { params }),
  updateTaskStatus: (data = {}) => request.put('/api-automation/task-status', data),
  getTaskExecutionHistory: (params = {}) => request.get('/api-automation/task-history', { params }),

  // 系统管理
  getSystemLogs: (params = {}) => request.get('/api-automation/logs', { params }),
  getAgentMetrics: (params = {}) => request.get('/api-automation/metrics', { params }),
}
