import axios from 'axios';

// API基础配置
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

// 创建axios实例
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000, // 30秒超时，因为AI分析可能需要较长时间
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    // 可以在这里添加认证token等
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器
apiClient.interceptors.response.use(
  (response) => {
    return response.data;
  },
  (error) => {
    console.error('API Error:', error);
    
    if (error.response) {
      // 服务器返回错误状态码
      const { status, data } = error.response;
      
      switch (status) {
        case 400:
          throw new Error(data.message || '请求参数错误');
        case 401:
          throw new Error('未授权访问');
        case 403:
          throw new Error('禁止访问');
        case 404:
          throw new Error('资源不存在');
        case 500:
          throw new Error('服务器内部错误');
        default:
          throw new Error(data.message || `请求失败 (${status})`);
      }
    } else if (error.request) {
      // 网络错误
      throw new Error('网络连接失败，请检查网络设置');
    } else {
      // 其他错误
      throw new Error(error.message || '未知错误');
    }
  }
);

// 页面分析状态枚举
export enum AnalysisStatus {
  PENDING = 'pending',
  ANALYZING = 'analyzing',
  COMPLETED = 'completed',
  FAILED = 'failed'
}

// 页面数据接口
export interface PageData {
  id: string;
  page_name: string;
  page_description: string;
  page_url?: string;
  analysis_status: AnalysisStatus;
  confidence_score: number;
  elements_count: number;
  created_at: string;
  updated_at: string;
  raw_analysis_json?: any;
  parsed_ui_elements?: any[];
}

// 页面元素接口
export interface PageElement {
  id: string;
  element_name: string;
  element_type: string;
  element_description: string;
  element_data: any;
  confidence_score: number;
  is_testable: boolean;
  created_at: string;
  updated_at: string;
}

// API响应接口
export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  message?: string;
  error?: string;
}

// 页面分析API类
export class PageAnalysisApi {
  
  /**
   * 获取页面列表
   */
  async getPageList(params?: {
    page?: number;
    page_size?: number;
    search?: string;
    status?: AnalysisStatus;
  }): Promise<ApiResponse<PageData[]>> {
    const response = await apiClient.get('/api/v1/web/page-analysis/pages', { params });
    return response;
  }

  /**
   * 获取页面详情
   */
  async getPageDetail(pageId: string): Promise<ApiResponse<PageData>> {
    const response = await apiClient.get(`/api/v1/web/page-analysis/pages/${pageId}`);
    return response;
  }

  /**
   * 获取页面元素列表
   */
  async getPageElements(pageId: string): Promise<ApiResponse<PageElement[]>> {
    const response = await apiClient.get(`/api/v1/web/page-analysis/pages/${pageId}/elements`);
    return response;
  }

  /**
   * 上传文件并开始AI分析
   */
  async uploadAndAnalyze(formData: FormData): Promise<ApiResponse<{
    session_id: string;
    uploaded_files: string[];
    analysis_started: boolean;
  }>> {
    const response = await apiClient.post('/api/v1/web/page-analysis/upload-and-analyze', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response;
  }

  /**
   * 删除页面
   */
  async deletePage(pageId: string): Promise<ApiResponse> {
    const response = await apiClient.delete(`/api/v1/web/page-analysis/pages/${pageId}`);
    return response;
  }

  /**
   * 重新分析页面
   */
  async reanalyzePage(pageId: string): Promise<ApiResponse> {
    const response = await apiClient.post(`/api/web/pages/${pageId}/reanalyze`);
    return response;
  }

  /**
   * 获取分析状态
   */
  async getAnalysisStatus(sessionId: string): Promise<ApiResponse<{
    session_id: string;
    status: AnalysisStatus;
    progress: number;
    total_files: number;
    processed_files: number;
    created_at: string;
    last_activity: string;
    error?: string;
    completed_at?: string;
    page_info: any;
  }>> {
    const response = await apiClient.get(`/api/v1/web/page-analysis/status/${sessionId}`);
    return response;
  }

  /**
   * 批量删除页面
   */
  async batchDeletePages(pageIds: string[]): Promise<ApiResponse> {
    const response = await apiClient.post('/api/web/pages/batch-delete', {
      page_ids: pageIds
    });
    return response;
  }

  /**
   * 导出页面数据
   */
  async exportPageData(pageIds: string[], format: 'json' | 'csv' = 'json'): Promise<ApiResponse<{
    download_url: string;
    filename: string;
  }>> {
    const response = await apiClient.post('/api/web/pages/export', {
      page_ids: pageIds,
      format
    });
    return response;
  }

  /**
   * 获取页面分析统计
   */
  async getAnalysisStatistics(): Promise<ApiResponse<{
    total_pages: number;
    completed_pages: number;
    analyzing_pages: number;
    failed_pages: number;
    average_confidence: number;
    total_elements: number;
    testable_elements: number;
  }>> {
    const response = await apiClient.get('/api/web/pages/statistics');
    return response;
  }

  /**
   * 搜索页面
   */
  async searchPages(query: string, filters?: {
    status?: AnalysisStatus;
    min_confidence?: number;
    max_confidence?: number;
    date_from?: string;
    date_to?: string;
  }): Promise<ApiResponse<PageData[]>> {
    const response = await apiClient.get('/api/web/pages/search', {
      params: {
        q: query,
        ...filters
      }
    });
    return response;
  }

  /**
   * 获取元素类型统计
   */
  async getElementTypeStatistics(): Promise<ApiResponse<{
    [elementType: string]: {
      count: number;
      testable_count: number;
      average_confidence: number;
    };
  }>> {
    const response = await apiClient.get('/api/web/elements/statistics');
    return response;
  }

  /**
   * 更新页面信息
   */
  async updatePage(pageId: string, data: {
    page_name?: string;
    page_description?: string;
    page_url?: string;
  }): Promise<ApiResponse<PageData>> {
    const response = await apiClient.put(`/api/web/pages/${pageId}`, data);
    return response;
  }

  /**
   * 获取可测试元素
   */
  async getTestableElements(pageId: string): Promise<ApiResponse<PageElement[]>> {
    const response = await apiClient.get(`/api/web/pages/${pageId}/testable-elements`);
    return response;
  }

  /**
   * 生成测试用例
   */
  async generateTestCases(pageId: string, options?: {
    test_type?: 'functional' | 'ui' | 'accessibility';
    include_negative_cases?: boolean;
    max_cases?: number;
  }): Promise<ApiResponse<{
    test_cases: any[];
    generated_count: number;
  }>> {
    const response = await apiClient.post(`/api/web/pages/${pageId}/generate-test-cases`, options);
    return response;
  }
}

// 创建API实例
export const pageAnalysisApi = new PageAnalysisApi();

// 默认导出
export default pageAnalysisApi;
