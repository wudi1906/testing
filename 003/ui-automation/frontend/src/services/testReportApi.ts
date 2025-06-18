/**
 * 测试报告API服务
 */
import apiClient from './api';

// 测试报告接口类型定义
export interface TestReport {
  id: number;
  script_id: string;
  script_name: string;
  session_id: string;
  execution_id: string;
  status: 'passed' | 'failed' | 'error';
  return_code: number;
  start_time?: string;
  end_time?: string;
  duration: number;
  total_tests: number;
  passed_tests: number;
  failed_tests: number;
  skipped_tests: number;
  success_rate: number;
  report_path?: string;
  report_url?: string;
  report_size: number;
  screenshots?: string[];
  videos?: string[];
  artifacts?: string[];
  error_message?: string;
  logs?: string[];
  execution_config?: Record<string, any>;
  environment_variables?: Record<string, any>;
  created_at?: string;
  updated_at?: string;
}

export interface TestReportListResponse {
  success: boolean;
  data: TestReport[];
  pagination?: {
    page: number;
    page_size: number;
    total: number;
    total_pages: number;
  };
  total?: number;
  message: string;
}

export interface TestReportResponse {
  success: boolean;
  data: TestReport;
  message: string;
}

export interface TestReportStats {
  total_reports: number;
  passed_reports: number;
  failed_reports: number;
  error_reports: number;
  success_rate: number;
  recent_reports: TestReport[];
}

export interface TestReportStatsResponse {
  success: boolean;
  data: TestReportStats;
  message: string;
}

/**
 * 根据脚本ID获取最新的测试报告
 */
export const getLatestReportByScriptId = async (scriptId: string): Promise<TestReport> => {
  const response = await apiClient.get(`/web/reports/script/${scriptId}/latest`);
  return response.data.data;
};

/**
 * 根据执行ID获取测试报告
 */
export const getReportByExecutionId = async (executionId: string): Promise<TestReport> => {
  const response = await apiClient.get(`/web/reports/execution/${executionId}`);
  return response.data.data;
};

/**
 * 根据会话ID获取所有测试报告
 */
export const getReportsBySessionId = async (sessionId: string): Promise<TestReport[]> => {
  const response = await apiClient.get(`/web/reports/session/${sessionId}`);
  return response.data.data;
};

/**
 * 获取测试报告列表
 */
export const getReportList = async (params: {
  page?: number;
  page_size?: number;
  script_id?: string;
  status?: string;
}): Promise<TestReportListResponse> => {
  const response = await apiClient.get('/web/reports/list', { params });
  return response.data;
};

/**
 * 删除测试报告
 */
export const deleteReport = async (reportId: number): Promise<{ success: boolean; message: string }> => {
  const response = await apiClient.delete(`/web/reports/${reportId}`);
  return response.data;
};

/**
 * 获取测试报告统计信息
 */
export const getReportStats = async (): Promise<TestReportStats> => {
  const response = await apiClient.get('/web/reports/stats');
  return response.data.data;
};

/**
 * 获取HTML报告查看URL
 */
export const getReportViewUrl = (executionId: string): string => {
  return `/api/v1/web/reports/view/${executionId}`;
};

/**
 * 根据脚本ID获取最新报告查看URL
 */
export const getLatestReportViewUrlByScriptId = (scriptId: string): string => {
  return `/api/v1/web/reports/view/script/${scriptId}`;
};

/**
 * 打开HTML报告（新窗口）
 */
export const openReportInNewWindow = (executionId: string): void => {
  const url = getReportViewUrl(executionId);
  window.open(url, '_blank', 'noopener,noreferrer');
};

/**
 * 根据脚本ID打开最新HTML报告（新窗口）
 */
export const openLatestReportByScriptId = (scriptId: string): void => {
  const url = getLatestReportViewUrlByScriptId(scriptId);
  window.open(url, '_blank', 'noopener,noreferrer');
};

/**
 * 检查报告是否存在
 */
export const checkReportExists = async (scriptId: string): Promise<boolean> => {
  try {
    await getLatestReportByScriptId(scriptId);
    return true;
  } catch (error: any) {
    if (error.response?.status === 404) {
      return false;
    }
    throw error;
  }
};

/**
 * 格式化报告状态
 */
export const formatReportStatus = (status: string): { text: string; color: string } => {
  switch (status) {
    case 'passed':
      return { text: '通过', color: 'green' };
    case 'failed':
      return { text: '失败', color: 'red' };
    case 'error':
      return { text: '错误', color: 'orange' };
    default:
      return { text: '未知', color: 'gray' };
  }
};

/**
 * 格式化执行时长
 */
export const formatDuration = (duration: number): string => {
  if (duration < 60) {
    return `${duration.toFixed(1)}秒`;
  } else if (duration < 3600) {
    const minutes = Math.floor(duration / 60);
    const seconds = Math.floor(duration % 60);
    return `${minutes}分${seconds}秒`;
  } else {
    const hours = Math.floor(duration / 3600);
    const minutes = Math.floor((duration % 3600) / 60);
    return `${hours}小时${minutes}分`;
  }
};

/**
 * 格式化成功率
 */
export const formatSuccessRate = (rate: number): string => {
  return `${rate.toFixed(1)}%`;
};

/**
 * 格式化文件大小
 */
export const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B';
  
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
};

/**
 * 获取报告摘要信息
 */
export const getReportSummary = (report: TestReport): string => {
  const { total_tests, passed_tests, failed_tests, duration } = report;
  const durationStr = formatDuration(duration);
  
  if (total_tests === 0) {
    return `执行时长: ${durationStr}`;
  }
  
  return `${total_tests}个测试, ${passed_tests}个通过, ${failed_tests}个失败, 耗时: ${durationStr}`;
};
