/**
 * 定时任务API服务
 */
import apiClient from './api';

// 定时任务相关类型定义
export interface ScheduledTask {
  id: string;
  script_id: string;
  project_id?: string;
  name: string;
  description?: string;
  schedule_type: 'cron' | 'interval' | 'once';
  cron_expression?: string;
  interval_seconds?: number;
  scheduled_time?: string;
  status: 'active' | 'paused' | 'disabled' | 'expired';
  is_enabled: boolean;
  total_executions: number;
  successful_executions: number;
  failed_executions: number;
  last_execution_time?: string;
  last_execution_status?: string;
  next_execution_time?: string;
  created_at: string;
  updated_at: string;
}

export interface TaskStatistics {
  total_tasks: number;
  active_tasks: number;
  paused_tasks: number;
  disabled_tasks: number;
  total_executions: number;
  successful_executions: number;
  failed_executions: number;
  success_rate: number;
}

export interface TaskSearchParams {
  query?: string;
  script_id?: string;
  project_id?: string;
  status?: string;
  schedule_type?: string;
  is_enabled?: boolean;
  created_by?: string;
  limit?: number;
  offset?: number;
  sort_by?: string;
  sort_order?: string;
}

export interface TaskSearchResponse {
  tasks: ScheduledTask[];
  total: number;
  limit: number;
  offset: number;
}

export interface TaskCreateRequest {
  script_id: string;
  project_id?: string;
  name: string;
  description?: string;
  schedule_type: 'cron' | 'interval' | 'once';
  cron_expression?: string;
  interval_seconds?: number;
  scheduled_time?: string;
  execution_config?: Record<string, any>;
  environment_variables?: Record<string, string>;
  timeout_seconds?: number;
  max_retries?: number;
  retry_interval_seconds?: number;
  start_time?: string;
  end_time?: string;
  notification_config?: Record<string, any>;
  notify_on_success?: boolean;
  notify_on_failure?: boolean;
}

export interface TaskUpdateRequest {
  name?: string;
  description?: string;
  schedule_type?: 'cron' | 'interval' | 'once';
  cron_expression?: string;
  interval_seconds?: number;
  scheduled_time?: string;
  execution_config?: Record<string, any>;
  environment_variables?: Record<string, string>;
  timeout_seconds?: number;
  max_retries?: number;
  retry_interval_seconds?: number;
  status?: 'active' | 'paused' | 'disabled' | 'expired';
  is_enabled?: boolean;
  start_time?: string;
  end_time?: string;
  notification_config?: Record<string, any>;
  notify_on_success?: boolean;
  notify_on_failure?: boolean;
}

export interface TaskExecutionRequest {
  execution_config?: Record<string, any>;
  environment_variables?: Record<string, string>;
}

export interface TaskExecutionResponse {
  execution_id: string;
  task_id: string;
  script_id: string;
  session_id: string;
  status: string;
  message: string;
  sse_endpoint: string;
  created_at: string;
}

export interface TaskExecution {
  id: string;
  task_id: string;
  script_id: string;
  session_id?: string;
  execution_id?: string;
  trigger_type: 'scheduled' | 'manual' | 'retry';
  status: 'pending' | 'running' | 'completed' | 'failed' | 'timeout' | 'cancelled';
  scheduled_time?: string;
  start_time?: string;
  end_time?: string;
  duration_seconds?: number;
  exit_code?: number;
  error_message?: string;
  output_log?: string;
  retry_count: number;
  is_retry: boolean;
  created_at: string;
  updated_at: string;
}

// API函数

/**
 * 创建定时任务
 */
export const createScheduledTask = async (data: TaskCreateRequest): Promise<ScheduledTask> => {
  const response = await apiClient.post('/web/scheduled-tasks', data);
  return response.data;
};

/**
 * 搜索定时任务
 */
export const searchScheduledTasks = async (params: TaskSearchParams): Promise<TaskSearchResponse> => {
  const response = await apiClient.get('/web/scheduled-tasks/search', { params });
  return response.data;
};

/**
 * 获取定时任务统计信息
 */
export const getTaskStatistics = async (): Promise<TaskStatistics> => {
  const response = await apiClient.get('/web/scheduled-tasks/statistics');
  return response.data;
};

/**
 * 获取定时任务详情
 */
export const getScheduledTask = async (taskId: string): Promise<ScheduledTask> => {
  const response = await apiClient.get(`/web/scheduled-tasks/${taskId}`);
  return response.data;
};

/**
 * 更新定时任务
 */
export const updateScheduledTask = async (taskId: string, data: TaskUpdateRequest): Promise<ScheduledTask> => {
  const response = await apiClient.put(`/web/scheduled-tasks/${taskId}`, data);
  return response.data;
};

/**
 * 删除定时任务
 */
export const deleteScheduledTask = async (taskId: string): Promise<void> => {
  await apiClient.delete(`/web/scheduled-tasks/${taskId}`);
};

/**
 * 手动执行定时任务
 */
export const executeScheduledTask = async (taskId: string, data: TaskExecutionRequest = {}): Promise<TaskExecutionResponse> => {
  const response = await apiClient.post(`/web/scheduled-tasks/${taskId}/execute`, data);
  return response.data;
};

/**
 * 暂停定时任务
 */
export const pauseScheduledTask = async (taskId: string): Promise<void> => {
  await apiClient.post(`/web/scheduled-tasks/${taskId}/pause`);
};

/**
 * 恢复定时任务
 */
export const resumeScheduledTask = async (taskId: string): Promise<void> => {
  await apiClient.post(`/web/scheduled-tasks/${taskId}/resume`);
};

/**
 * 启用定时任务
 */
export const enableScheduledTask = async (taskId: string): Promise<void> => {
  await apiClient.post(`/web/scheduled-tasks/${taskId}/enable`);
};

/**
 * 禁用定时任务
 */
export const disableScheduledTask = async (taskId: string): Promise<void> => {
  await apiClient.post(`/web/scheduled-tasks/${taskId}/disable`);
};

/**
 * 获取任务执行历史
 */
export const getTaskExecutions = async (taskId: string, limit: number = 20): Promise<TaskExecution[]> => {
  const response = await apiClient.get(`/web/scheduled-tasks/${taskId}/executions`, {
    params: { limit }
  });
  return response.data;
};

/**
 * 根据脚本ID获取定时任务
 */
export const getTasksByScript = async (scriptId: string): Promise<ScheduledTask[]> => {
  const response = await apiClient.get(`/web/scheduled-tasks/script/${scriptId}`);
  return response.data;
};

/**
 * 获取最近的任务执行记录
 */
export const getRecentExecutions = async (limit: number = 50): Promise<TaskExecution[]> => {
  const response = await apiClient.get('/web/task-executions/recent', {
    params: { limit }
  });
  return response.data;
};

/**
 * 获取可用的脚本列表（用于任务创建时选择）
 */
export const getAvailableScripts = async (): Promise<any[]> => {
  try {
    const response = await apiClient.post('/web/scripts/search', {
      limit: 100,
      offset: 0
    });
    return response.data.scripts || [];
  } catch (error) {
    console.error('获取脚本列表失败:', error);
    return [];
  }
};

export default {
  createScheduledTask,
  searchScheduledTasks,
  getTaskStatistics,
  getScheduledTask,
  updateScheduledTask,
  deleteScheduledTask,
  executeScheduledTask,
  pauseScheduledTask,
  resumeScheduledTask,
  enableScheduledTask,
  disableScheduledTask,
  getTaskExecutions,
  getTasksByScript,
  getRecentExecutions,
  getAvailableScripts
};
