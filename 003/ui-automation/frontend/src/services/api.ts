/**
 * API服务模块
 * 处理与后端的所有HTTP通信
 */
import axios, { AxiosResponse } from 'axios';

// 配置基础URL
// 使用相对路径，走 Vite 代理到 8002；如需直连后端，可设置 VITE_API_URL
const API_BASE_URL = import.meta.env.VITE_API_URL || '';
const API_VERSION = '/api/v1';

// 创建axios实例
const apiClient = axios.create({
  baseURL: `${API_BASE_URL}${API_VERSION}`,
  timeout: 30000, // 30秒超时
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    // 可以在这里添加认证token等
    console.log(`API请求: ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    console.error('API请求错误:', error);
    return Promise.reject(error);
  }
);

// 响应拦截器
apiClient.interceptors.response.use(
  (response: AxiosResponse) => {
    console.log(`API响应: ${response.status} ${response.config.url}`);
    return response;
  },
  (error) => {
    console.error('API响应错误:', error);

    // 统一错误处理
    if (error.response) {
      // 服务器返回错误状态码
      const { status, data } = error.response;
      let errorMessage = '请求失败';

      switch (status) {
        case 400:
          errorMessage = data.detail || '请求参数错误';
          break;
        case 401:
          errorMessage = '未授权访问';
          break;
        case 403:
          errorMessage = '禁止访问';
          break;
        case 404:
          errorMessage = '资源不存在';
          break;
        case 500:
          errorMessage = data.detail || '服务器内部错误';
          break;
        default:
          errorMessage = data.detail || `请求失败 (${status})`;
      }

      throw new Error(errorMessage);
    } else if (error.request) {
      // 网络错误
      throw new Error('网络连接失败，请检查网络设置');
    } else {
      // 其他错误
      throw new Error(error.message || '未知错误');
    }
  }
);

// 类型定义
export interface AnalysisResult {
  session_id: string;
  analysis_result: {
    analysis_id: string;
    analysis_type: string;
    page_analysis: {
      page_title?: string;
      page_type: string;
      main_content: string;
      ui_elements: Array<{
        id: string;
        name: string;
        element_type: string;
        description: string;
        position?: any;
        confidence_score: number;
        interaction_hint?: string;
      }>;
      user_flows: string[];
      test_scenarios: string[];
    };
    confidence_score: number;
    processing_time: number;
  };
  yaml_script: any;
  yaml_content: string;
  file_path: string;
  estimated_duration?: string;
}

export interface URLAnalysisRequest {
  url: string;
  test_description: string;
  additional_context?: string;
  viewport_width?: number;
  viewport_height?: number;
  wait_for_load?: boolean;
}

export interface ExecutionStatus {
  execution_id: string;
  status: string;
  start_time: string;
  end_time?: string;
  duration?: number;
  results?: any;
  logs: string[];
  screenshots: string[];
  error_message?: string;
}

export interface Template {
  id: string;
  name: string;
  description: string;
  category: string;
  template: {
    test_description: string;
    additional_context: string;
  };
}

export interface TemplatesResponse {
  templates: Template[];
  total: number;
}

export interface HistoryItem {
  session_id: string;
  status: string;
  created_at: string;
  analysis_type: string;
  test_description: string;
}

export interface HistoryResponse {
  total: number;
  limit: number;
  offset: number;
  items: HistoryItem[];
}

// API函数

/**
 * Web平台图片分析
 */
export const analyzeWebImage = async (formData: FormData): Promise<AnalysisResult> => {
  const response = await apiClient.post('/web/create/analyze/image', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

/**
 * Android平台图片分析
 */
export const analyzeAndroidImage = async (formData: FormData): Promise<AnalysisResult> => {
  const response = await apiClient.post('/android/analyze/image', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

/**
 * 分析网页URL
 */
export const analyzeURL = async (data: URLAnalysisRequest): Promise<AnalysisResult> => {
  const response = await apiClient.post('/test/analyze/url', data);
  return response.data;
};

/**
 * Web平台URL分析
 */
export const analyzeWebURL = async (data: URLAnalysisRequest): Promise<AnalysisResult> => {
  const response = await apiClient.post('/web/create/analyze/url', data);
  return response.data;
};

/**
 * Web平台Crawl4AI多页面抓取
 */
export const startWebCrawl = async (data: {
  homepage_url: string;
  test_description: string;
  additional_context?: string;
  max_pages?: number;
  max_depth?: number;
  crawl_strategy?: string;
  user_query?: string;
  generate_formats?: string[];
}): Promise<AnalysisResult> => {
  const response = await apiClient.post('/web/crawl4ai/start', data);
  return response.data;
};

/**
 * 下载YAML文件 (通用接口，保持向后兼容)
 */
export const downloadYAML = async (sessionId: string): Promise<Blob> => {
  const response = await apiClient.get(`/test/download/yaml/${sessionId}`, {
    responseType: 'blob',
  });
  return response.data;
};

/**
 * Web平台下载YAML文件
 */
export const downloadWebYAML = async (sessionId: string): Promise<Blob> => {
  const response = await apiClient.get(`/web/download/yaml/${sessionId}`, {
    responseType: 'blob',
  });
  return response.data;
};

/**
 * Android平台下载YAML文件
 */
export const downloadAndroidYAML = async (sessionId: string): Promise<Blob> => {
  const response = await apiClient.get(`/android/download/yaml/${sessionId}`, {
    responseType: 'blob',
  });
  return response.data;
};

/**
 * 执行YAML脚本（文件上传）
 */
export const executeYAML = async (formData: FormData): Promise<{ execution_id: string; status: string; message: string; config: any }> => {
  const response = await apiClient.post('/test/execute/yaml', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

/**
 * 执行YAML脚本内容
 */
export const executeYAMLContent = async (data: {
  yaml_content: string;
  execution_config?: any;
}): Promise<{ execution_id: string; status: string; message: string }> => {
  const response = await apiClient.post('/test/execute/yaml/content', data);
  return response.data;
};

/**
 * 执行YAML文件
 */
export const executeYAMLFile = async (data: {
  file_path: string;
  config?: any;
}): Promise<{ execution_id: string; status: string; message: string }> => {
  const response = await apiClient.post('/test/execute/yaml/file', data);
  return response.data;
};

/**
 * 执行YAML目录
 */
export const executeYAMLDirectory = async (data: {
  dir_path: string;
  config?: any;
}): Promise<{ execution_ids: string[]; status: string; message: string }> => {
  const response = await apiClient.post('/test/execute/yaml/directory', data);
  return response.data;
};

/**
 * 保存脚本文件
 */
export const saveScriptFile = async (data: {
  content: string;
  filename: string;
  format: 'yaml' | 'playwright';
}): Promise<{ file_path: string; message: string }> => {
  const response = await apiClient.post('/web/create/save-script', data);
  return response.data;
};

/**
 * 执行Playwright脚本
 */
export const executePlaywrightScript = async (data: {
  script_content: string;
  config?: any;
}): Promise<{ execution_id: string; status: string; message: string }> => {
  const response = await apiClient.post('/playwright/execute/script', data);
  return response.data;
};

// ==================== 脚本管理API (数据库) ====================

/**
 * 搜索脚本
 */
export const searchScripts = async (searchRequest: {
  query?: string;
  script_format?: string;
  script_type?: string;
  category?: string;
  tags?: string[];
  page?: number;
  page_size?: number;
  sort_by?: string;
  sort_order?: string;
}): Promise<{
  scripts: Array<any>;
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}> => {
  const response = await apiClient.post('/web/scripts/search', searchRequest);
  return response.data;
};

/**
 * 获取脚本统计信息
 */
export const getScriptStatistics = async (): Promise<{
  total_scripts: number;
  by_format: Record<string, number>;
  by_type: Record<string, number>;
  by_category: Record<string, number>;
  recent_executions: number;
}> => {
  const response = await apiClient.get('/web/scripts/statistics');
  return response.data;
};

/**
 * 获取脚本详情
 */
export const getScript = async (scriptId: string): Promise<any> => {
  const response = await apiClient.get(`/web/scripts/${scriptId}`);
  return response.data;
};

/**
 * 更新脚本
 */
export const updateScript = async (scriptId: string, updateData: {
  name?: string;
  description?: string;
  content?: string;
  test_description?: string;
  additional_context?: string;
  tags?: string[];
  category?: string;
  priority?: number;
}): Promise<any> => {
  const response = await apiClient.put(`/web/scripts/${scriptId}`, updateData);
  return response.data;
};

/**
 * 删除脚本
 */
export const deleteScript = async (scriptId: string): Promise<{
  message: string;
  script_id: string;
}> => {
  const response = await apiClient.delete(`/web/scripts/${scriptId}`);
  return response.data;
};

/**
 * 同步所有脚本到工作空间
 */
export const syncScriptsToWorkspace = async (): Promise<{
  status: string;
  message: string;
  synced_count: number;
  failed_count: number;
  total_scripts: number;
}> => {
  const response = await apiClient.post('/web/scripts/sync-workspace');
  return response.data;
};

/**
 * 获取脚本执行记录
 */
export const getScriptExecutions = async (scriptId: string, limit: number = 20): Promise<Array<any>> => {
  const response = await apiClient.get(`/web/scripts/${scriptId}/executions?limit=${limit}`);
  return response.data;
};

/**
 * 执行数据库中的脚本
 */
export const executeScriptFromDB = async (scriptId: string, executeRequest: {
  execution_config?: Record<string, any>;
  environment_variables?: Record<string, any>;
}): Promise<{
  execution_id: string;
  script_id: string;
  status: string;
  message: string;
}> => {
  const response = await apiClient.post(`/web/scripts/${scriptId}/execute`, executeRequest);
  return response.data;
};

/**
 * 执行脚本 - 兼容性别名
 * 为了兼容现有的WebTestExecutionOptimized组件
 */
export const executeScript = executeScriptFromDB;

/**
 * 基于自然语言文本生成测试脚本
 */
export const generateTestFromText = async (data: {
  test_description: string;
  generate_formats: string[];
  additional_context?: string;
}): Promise<AnalysisResult> => {
  const response = await apiClient.post('/web/create/generate-from-text', data);
  return response.data;
};

/**
 * 分析图片生成自然语言描述
 */
export const analyzeImageToDescription = async (formData: FormData): Promise<{
  description: string;
  session_id: string;
  analysis_result?: any;
}> => {
  const response = await apiClient.post('/web/create/analyze-image-to-description', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

/**
 * 批量执行数据库中的脚本
 */
export const batchExecuteScriptsFromDB = async (batchRequest: {
  script_ids: string[];
  execution_config?: Record<string, any>;
  parallel?: boolean;
  continue_on_error?: boolean;
}): Promise<{
  batch_id: string;
  script_count: number;
  execution_ids: string[];
  status: string;
  message: string;
}> => {
  const response = await apiClient.post('/web/scripts/batch-execute', batchRequest);
  return response.data;
};

/**
 * 批量执行脚本 - 兼容性别名
 * 为了兼容现有的WebTestExecutionOptimized组件
 */
export const batchExecuteScripts = batchExecuteScriptsFromDB;

/**
 * 上传脚本文件
 */
export const uploadScriptFile = async (data: {
  file: File;
  name: string;
  description: string;
  script_format: string;
  category?: string;
  tags?: string[];
}): Promise<{
  status: string;
  script_id: string;
  message: string;
  script: any;
}> => {
  const formData = new FormData();
  formData.append('file', data.file);
  formData.append('name', data.name);
  formData.append('description', data.description);
  formData.append('script_format', data.script_format);

  if (data.category) {
    formData.append('category', data.category);
  }
  if (data.tags && data.tags.length > 0) {
    formData.append('tags', JSON.stringify(data.tags));
  }

  const response = await apiClient.post('/web/scripts/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

/**
 * 上传脚本 - 兼容性别名
 * 为了兼容现有的ScriptManager组件
 */
export const uploadScript = async (formData: FormData): Promise<{
  status: string;
  script_id: string;
  message: string;
  script: any;
}> => {
  const response = await apiClient.post('/web/scripts/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

/**
 * 从会话保存脚本
 */
export const saveScriptFromSession = async (data: {
  session_id: string;
  name: string;
  description: string;
  script_format: string;
  script_type: string;
  test_description: string;
  content: string;
  additional_context?: string;
  source_url?: string;
  tags?: string[];
}): Promise<{
  status: string;
  script_id: string;
  message: string;
  script: any;
}> => {
  const formData = new FormData();
  Object.entries(data).forEach(([key, value]) => {
    if (value !== undefined) {
      if (key === 'tags' && Array.isArray(value)) {
        formData.append(key, JSON.stringify(value));
      } else {
        formData.append(key, String(value));
      }
    }
  });

  const response = await apiClient.post('/web/scripts/save-from-session', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

// ==================== 脚本执行API (文件系统) ====================

/**
 * 获取可用脚本列表（从文件系统）
 */
export const getAvailableScripts = async (): Promise<{
  scripts: Array<{
    name: string;
    path: string;
    size: number;
    modified: string;
  }>;
  total: number;
  workspace: string;
  timestamp: string;
}> => {
  const response = await apiClient.get('/web/execution/scripts');
  return response.data;
};

/**
 * 获取工作空间信息
 */
export const getWorkspaceInfo = async (): Promise<{
  workspace: {
    path: string;
    exists: boolean;
    e2e_dir_exists: boolean;
    package_json_exists: boolean;
    total_scripts: number;
    recent_scripts: Array<any>;
  };
  scripts: Array<any>;
  timestamp: string;
}> => {
  const response = await apiClient.get('/web/execution/workspace/info');
  return response.data;
};

/**
 * 执行单个脚本
 */
export const executeSingleScript = async (data: {
  script_name: string;
  execution_config?: string;
  base_url?: string;
  headed?: boolean;
  timeout?: number;
}): Promise<{
  session_id: string;
  status: string;
  script_name: string;
  message: string;
  sse_endpoint: string;
}> => {
  const formData = new FormData();
  formData.append('script_name', data.script_name);

  if (data.execution_config) {
    formData.append('execution_config', data.execution_config);
  }
  if (data.base_url) {
    formData.append('base_url', data.base_url);
  }
  if (data.headed !== undefined) {
    formData.append('headed', data.headed.toString());
  }
  if (data.timeout) {
    formData.append('timeout', data.timeout.toString());
  }

  const response = await apiClient.post('/web/execution/execute/single', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

/**
 * 批量执行脚本
 */
export const executeBatchScripts = async (data: {
  script_names: string;
  execution_config?: string;
  parallel_execution?: boolean;
  stop_on_failure?: boolean;
  base_url?: string;
  headed?: boolean;
  timeout?: number;
}): Promise<{
  session_id: string;
  status: string;
  script_names: string[];
  total_scripts: number;
  parallel_execution: boolean;
  stop_on_failure: boolean;
  message: string;
  sse_endpoint: string;
}> => {
  const formData = new FormData();
  formData.append('script_names', data.script_names);

  if (data.execution_config) {
    formData.append('execution_config', data.execution_config);
  }
  if (data.parallel_execution !== undefined) {
    formData.append('parallel_execution', data.parallel_execution.toString());
  }
  if (data.stop_on_failure !== undefined) {
    formData.append('stop_on_failure', data.stop_on_failure.toString());
  }
  if (data.base_url) {
    formData.append('base_url', data.base_url);
  }
  if (data.headed !== undefined) {
    formData.append('headed', data.headed.toString());
  }
  if (data.timeout) {
    formData.append('timeout', data.timeout.toString());
  }

  const response = await apiClient.post('/web/execution/execute/batch', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

/**
 * 获取所有会话列表
 */
export const getScriptSessions = async (): Promise<{
  sessions: Record<string, any>;
  total: number;
  timestamp: string;
}> => {
  const response = await apiClient.get('/web/execution/sessions');
  return response.data;
};

/**
 * 获取会话信息
 */
export const getScriptSession = async (sessionId: string): Promise<{
  session_info: any;
  script_statuses: Record<string, any>;
  timestamp: string;
}> => {
  const response = await apiClient.get(`/web/execution/sessions/${sessionId}`);
  return response.data;
};

/**
 * 获取会话脚本状态
 */
export const getScriptSessionStatus = async (sessionId: string): Promise<{
  session_id: string;
  script_statuses: Record<string, any>;
  total_scripts: number;
  timestamp: string;
}> => {
  const response = await apiClient.get(`/web/execution/sessions/${sessionId}/status`);
  return response.data;
};

/**
 * 停止会话执行
 */
export const stopScriptSession = async (sessionId: string): Promise<{
  status: string;
  message: string;
  timestamp: string;
}> => {
  const response = await apiClient.post(`/web/execution/sessions/${sessionId}/stop`);
  return response.data;
};

/**
 * 删除会话
 */
export const deleteScriptSession = async (sessionId: string): Promise<{
  status: string;
  message: string;
  timestamp: string;
}> => {
  const response = await apiClient.delete(`/web/execution/sessions/${sessionId}`);
  return response.data;
};

/**
 * 获取会话报告
 */
export const getScriptSessionReports = async (sessionId: string): Promise<{
  session_id: string;
  reports: Array<{
    name: string;
    path: string;
    size: number;
    created: string;
    url: string;
  }>;
  total_reports: number;
  timestamp: string;
}> => {
  const response = await apiClient.get(`/web/execution/reports/${sessionId}`);
  return response.data;
};

/**
 * 创建SSE连接获取实时执行状态
 */
export const createScriptExecutionSSE = (
  sessionId: string,
  onMessage: (event: MessageEvent) => void,
  onError?: (error: Event) => void,
  onOpen?: (event: Event) => void,
  onClose?: (event: Event) => void
): EventSource => {
  const eventSource = new EventSource(`${API_BASE_URL}/api/v1/web/execution/stream/${sessionId}`);

  eventSource.onmessage = onMessage;

  if (onError) {
    eventSource.onerror = onError;
  }

  if (onOpen) {
    eventSource.onopen = onOpen;
  }

  // 监听特定事件类型
  eventSource.addEventListener('session', onMessage);
  eventSource.addEventListener('message', onMessage);
  eventSource.addEventListener('script_status', onMessage);
  eventSource.addEventListener('batch_status', onMessage);
  eventSource.addEventListener('progress', onMessage);
  eventSource.addEventListener('final_result', onMessage);
  eventSource.addEventListener('error', onMessage);
  eventSource.addEventListener('ping', onMessage);
  eventSource.addEventListener('close', (event) => {
    eventSource.close();
    if (onClose) {
      onClose(event);
    }
  });

  return eventSource;
};

/**
 * 获取生成的脚本内容
 */
export const getGeneratedScripts = async (sessionId: string): Promise<{
  status: string;
  session_id: string;
  scripts: Array<{
    format: string;
    content: string;
    filename: string;
    file_path: string;
  }>;
  total_scripts: number;
  saved_scripts: Array<{
    script_id: string;
    script_name: string;
    script_format: string;
    saved_at: string;
  }>;
  message: string;
}> => {
  const response = await apiClient.get(`/web/create/scripts/${sessionId}`);
  return response.data;
};



/**
 * 获取会话已保存的脚本列表
 */
export const getSavedScripts = async (sessionId: string): Promise<{
  session_id: string;
  saved_scripts: Array<{
    script_id: string;
    name: string;
    description: string;
    script_format: string;
    tags: string[];
    category: string;
    created_at: string;
    saved_at: string;
  }>;
  total_count: number;
}> => {
  const response = await apiClient.get(`/web/create/saved-scripts/${sessionId}`);
  return response.data;
};

// ==================== 脚本管理API ====================
// 注意：脚本管理相关的函数定义在文件后面，这里移除重复定义

/**
 * 停止执行
 */
export const stopExecution = async (executionId: string): Promise<{ message: string }> => {
  const response = await apiClient.post(`/test/execution/stop/${executionId}`);
  return response.data;
};

/**
 * 获取执行状态
 */
export const getExecutionStatus = async (executionId: string): Promise<ExecutionStatus> => {
  const response = await apiClient.get(`/test/execution/status/${executionId}`);
  return response.data;
};

/**
 * 获取执行日志
 */
export const getExecutionLogs = async (executionId: string): Promise<{ logs: string[] }> => {
  const response = await apiClient.get(`/test/execution/logs/${executionId}`);
  return response.data;
};

/**
 * 获取执行结果
 */
export const getExecutionResults = async (executionId: string): Promise<{ results: any }> => {
  const response = await apiClient.get(`/test/execution/results/${executionId}`);
  return response.data;
};

/**
 * 清理执行数据
 */
export const cleanupExecution = async (executionId: string): Promise<{ message: string }> => {
  const response = await apiClient.delete(`/test/execution/cleanup/${executionId}`);
  return response.data;
};

/**
 * 获取活跃执行
 */
export const getActiveExecutions = async (): Promise<{ active_executions: any[]; count: number }> => {
  const response = await apiClient.get('/test/execution/active');
  return response.data;
};

/**
 * 获取执行历史
 */
export const getExecutionHistory = async (limit = 50): Promise<{ history: any[]; count: number }> => {
  const response = await apiClient.get('/test/execution/history', {
    params: { limit },
  });
  return response.data;
};

// ==================== Playwright集成相关API ====================

/**
 * 生成Playwright测试代码
 */
export const generatePlaywrightTest = async (data: {
  test_description: string;
  target_url?: string;
  additional_context?: string;
  ui_analysis_result?: any;
}): Promise<{ generation_id: string; status: string; message: string }> => {
  const response = await apiClient.post('/test/playwright/generate', data);
  return response.data;
};

/**
 * 获取Playwright代码生成状态
 */
export const getPlaywrightGenerationStatus = async (generationId: string): Promise<any> => {
  const response = await apiClient.get(`/test/playwright/generation/status/${generationId}`);
  return response.data;
};

/**
 * 执行Playwright测试
 */
export const executePlaywrightTest = async (data: {
  test_content: string;
  execution_config?: any;
}): Promise<{ execution_id: string; status: string; message: string }> => {
  const response = await apiClient.post('/test/playwright/execute', data);
  return response.data;
};

/**
 * 执行已生成的Playwright测试
 */
export const executeGeneratedPlaywrightTest = async (
  generationId: string,
  config?: any
): Promise<{ execution_id: string; status: string; message: string }> => {
  const response = await apiClient.post(`/test/playwright/execute/generated/${generationId}`, config);
  return response.data;
};

/**
 * 获取Playwright执行状态
 */
export const getPlaywrightExecutionStatus = async (executionId: string): Promise<any> => {
  const response = await apiClient.get(`/test/playwright/execution/status/${executionId}`);
  return response.data;
};

/**
 * 停止Playwright执行
 */
export const stopPlaywrightExecution = async (executionId: string): Promise<{ message: string }> => {
  const response = await apiClient.post(`/test/playwright/execution/stop/${executionId}`);
  return response.data;
};

/**
 * 获取Playwright执行日志
 */
export const getPlaywrightExecutionLogs = async (executionId: string): Promise<{ logs: string[] }> => {
  const response = await apiClient.get(`/test/playwright/execution/logs/${executionId}`);
  return response.data;
};

/**
 * 获取Playwright执行结果
 */
export const getPlaywrightExecutionResults = async (executionId: string): Promise<{ results: any }> => {
  const response = await apiClient.get(`/test/playwright/execution/results/${executionId}`);
  return response.data;
};

/**
 * 清理Playwright执行数据
 */
export const cleanupPlaywrightExecution = async (executionId: string): Promise<{ message: string }> => {
  const response = await apiClient.delete(`/test/playwright/execution/cleanup/${executionId}`);
  return response.data;
};

/**
 * 清理Playwright生成数据
 */
export const cleanupPlaywrightGeneration = async (generationId: string): Promise<{ message: string }> => {
  const response = await apiClient.delete(`/test/playwright/generation/cleanup/${generationId}`);
  return response.data;
};

/**
 * 获取活跃的Playwright执行
 */
export const getActivePlaywrightExecutions = async (): Promise<{ active_executions: any[]; count: number }> => {
  const response = await apiClient.get('/test/playwright/executions/active');
  return response.data;
};

/**
 * 获取Playwright执行历史
 */
export const getPlaywrightExecutionHistory = async (limit = 50): Promise<{ history: any[]; count: number }> => {
  const response = await apiClient.get('/test/playwright/executions/history', {
    params: { limit },
  });
  return response.data;
};

/**
 * 获取生成的Playwright测试列表
 */
export const getPlaywrightGeneratedTests = async (limit = 50): Promise<{ generated_tests: any[]; count: number }> => {
  const response = await apiClient.get('/test/playwright/generations', {
    params: { limit },
  });
  return response.data;
};

/**
 * 获取测试模板 (通用接口，保持向后兼容)
 */
export const getTestTemplates = async (): Promise<TemplatesResponse> => {
  const response = await apiClient.get('/test/templates');
  return response.data;
};

/**
 * 获取Web平台测试模板
 */
export const getWebTestTemplates = async (): Promise<TemplatesResponse> => {
  const response = await apiClient.get('/web/create/templates');
  return response.data;
};

/**
 * 获取Android平台测试模板
 */
export const getAndroidTestTemplates = async (): Promise<TemplatesResponse> => {
  const response = await apiClient.get('/android/templates');
  return response.data;
};

/**
 * 获取分析历史 (通用接口，保持向后兼容)
 */
export const getAnalysisHistory = async (limit = 50, offset = 0): Promise<HistoryResponse> => {
  const response = await apiClient.get('/test/history', {
    params: { limit, offset },
  });
  return response.data;
};

/**
 * 获取Web平台分析历史
 */
export const getWebAnalysisHistory = async (limit = 50, offset = 0): Promise<HistoryResponse> => {
  const response = await apiClient.get('/web/history', {
    params: { limit, offset },
  });
  return response.data;
};

/**
 * 获取Android平台分析历史
 */
export const getAndroidAnalysisHistory = async (limit = 50, offset = 0): Promise<HistoryResponse> => {
  const response = await apiClient.get('/android/history', {
    params: { limit, offset },
  });
  return response.data;
};

/**
 * 清理会话数据 (通用接口，保持向后兼容)
 */
export const cleanupSession = async (sessionId: string): Promise<{ message: string }> => {
  const response = await apiClient.delete(`/test/cleanup/${sessionId}`);
  return response.data;
};

/**
 * 清理Web平台会话数据
 */
export const cleanupWebSession = async (sessionId: string): Promise<{ message: string }> => {
  const response = await apiClient.delete(`/web/cleanup/${sessionId}`);
  return response.data;
};

/**
 * 清理Android平台会话数据
 */
export const cleanupAndroidSession = async (sessionId: string): Promise<{ message: string }> => {
  const response = await apiClient.delete(`/android/cleanup/${sessionId}`);
  return response.data;
};

/**
 * 获取系统状态
 */
export const getSystemStatus = async (): Promise<any> => {
  const response = await apiClient.get('/system/status');
  return response.data;
};

/**
 * 获取系统健康状态
 */
export const getHealthStatus = async (): Promise<any> => {
  const response = await axios.get(`${API_BASE_URL}/health`);
  return response.data;
};

// 工具函数

/**
 * 创建下载链接
 */
export const createDownloadLink = (blob: Blob, filename: string): void => {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
};

/**
 * 格式化文件大小
 */
export const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes';

  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

/**
 * 格式化时间
 */
export const formatDuration = (seconds: number): string => {
  if (seconds < 60) {
    return `${Math.round(seconds)}秒`;
  } else if (seconds < 3600) {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.round(seconds % 60);
    return `${minutes}分${remainingSeconds}秒`;
  } else {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `${hours}小时${minutes}分钟`;
  }
};

/**
 * 验证URL格式
 */
export const isValidURL = (url: string): boolean => {
  try {
    new URL(url);
    return true;
  } catch {
    return false;
  }
};

/**
 * 获取文件扩展名
 */
export const getFileExtension = (filename: string): string => {
  return filename.slice((filename.lastIndexOf('.') - 1 >>> 0) + 2);
};

/**
 * 检查文件类型
 */
export const isImageFile = (file: File): boolean => {
  return file.type.startsWith('image/');
};

export const isYAMLFile = (file: File): boolean => {
  const extension = getFileExtension(file.name).toLowerCase();
  return extension === 'yaml' || extension === 'yml';
};

// ==================== 脚本管理相关API ====================

export interface ScriptInfo {
  id: string;
  session_id: string;
  name: string;
  description: string;
  script_format: 'yaml' | 'playwright';
  script_type: string;
  content: string;
  file_path: string;
  test_description: string;
  additional_context?: string;
  source_url?: string;
  source_image_path?: string;
  execution_count: number;
  last_execution_time?: string;
  last_execution_status?: string;
  created_at: string;
  updated_at: string;
  tags: string[];
  category?: string;
  priority: number;
}

export interface ScriptSearchRequest {
  query?: string;
  script_format?: 'yaml' | 'playwright';
  script_type?: string;
  tags?: string[];
  category?: string;
  date_from?: string;
  date_to?: string;
  limit?: number;
  offset?: number;
}

export interface ScriptSearchResponse {
  scripts: ScriptInfo[];
  total_count: number;
  has_more: boolean;
}

export interface ScriptStatistics {
  total_scripts: number;
  yaml_scripts: number;
  playwright_scripts: number;
  total_executions: number;
  successful_executions: number;
  failed_executions: number;
  success_rate: number;
  average_execution_time: number;
  most_used_scripts: Array<{
    id: string;
    name: string;
    execution_count: number;
    script_format: string;
  }>;
  recent_scripts: Array<{
    id: string;
    name: string;
    created_at: string;
    script_format: string;
  }>;
}

/**
 * 创建脚本
 */
export const createScript = async (data: {
  session_id: string;
  name: string;
  description: string;
  content: string;
  script_format: 'yaml' | 'playwright';
  script_type: string;
  test_description: string;
  additional_context?: string;
  source_url?: string;
  source_image_path?: string;
  analysis_result_id?: string;
  tags?: string[];
  category?: string;
  priority?: number;
}): Promise<ScriptInfo> => {
  const response = await apiClient.post('/web/scripts', data);
  return response.data;
};



// 重复的 saveScriptFromSession 函数已移除，使用上面的版本

// 重复的函数定义已移除，使用上面的版本

// 重复的 createScript 函数已移除，使用上面的版本

// ==================== 测试用例元素解析API ====================

/**
 * 测试用例解析请求接口
 */
export interface TestCaseParseRequest {
  test_case_content: string;
  test_description?: string;
  target_format: 'yaml' | 'playwright';
  additional_context?: string;
}

/**
 * 测试用例解析响应接口
 */
export interface TestCaseParseResponse {
  status: string;
  session_id: string;
  sse_endpoint: string;
  message: string;
  target_format: string;
  test_case_info: {
    content_length: number;
    has_description: boolean;
    has_context: boolean;
  };
}

/**
 * 测试用例解析状态接口
 */
export interface TestCaseParseStatus {
  success: boolean;
  data: {
    session_id: string;
    status: string;
    progress: number;
    created_at: string;
    last_activity: string;
    error?: string;
    completed_at?: string;
    test_case_info: {
      content_length: number;
      target_format: string;
      has_description: boolean;
      has_context: boolean;
    };
  };
}

/**
 * 提交测试用例解析请求
 */
export const parseTestCaseElements = async (data: TestCaseParseRequest): Promise<TestCaseParseResponse> => {
  const formData = new FormData();
  formData.append('test_case_content', data.test_case_content);
  if (data.test_description) {
    formData.append('test_description', data.test_description);
  }
  formData.append('target_format', data.target_format);
  if (data.additional_context) {
    formData.append('additional_context', data.additional_context);
  }

  const response = await fetch(`${API_BASE_URL}${API_VERSION}/web/test-case-parser/parse`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }

  return response.json();
};

/**
 * 获取测试用例解析状态
 */
export const getTestCaseParseStatus = async (sessionId: string): Promise<TestCaseParseStatus> => {
  const response = await apiClient.get(`/web/test-case-parser/status/${sessionId}`);
  return response.data;
};

/**
 * 清理测试用例解析会话
 */
export const cleanupTestCaseParseSession = async (sessionId: string): Promise<{ success: boolean; message: string }> => {
  const response = await apiClient.delete(`/web/test-case-parser/session/${sessionId}`);
  return response.data;
};

/**
 * 获取活跃的测试用例解析会话列表
 */
export const getActiveTestCaseParseSessions = async (): Promise<{
  success: boolean;
  data: {
    total_sessions: number;
    sessions: Array<{
      session_id: string;
      status: string;
      progress: number;
      created_at: string;
      last_activity: string;
      target_format: string;
    }>;
  };
}> => {
  const response = await apiClient.get('/web/test-case-parser/sessions');
  return response.data;
};

/**
 * 测试测试用例解析智能体功能
 */
export const testTestCaseParserAgent = async (): Promise<{
  success: boolean;
  message: string;
  data: {
    session_id: string;
    sse_endpoint: string;
    test_case_length: number;
    target_format: string;
  };
}> => {
  const response = await apiClient.post('/web/test-case-parser/test');
  return response.data;
};

/**
 * 健康检查测试用例解析服务
 */
export const checkTestCaseParserHealth = async (): Promise<{
  status: string;
  service: string;
  timestamp: string;
}> => {
  const response = await apiClient.get('/web/test-case-parser/health');
  return response.data;
};

// 导出API客户端
export { apiClient };
export default apiClient;
