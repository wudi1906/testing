/**
 * 统一脚本执行API服务
 * 基于脚本ID的前后端数据传输逻辑
 */
import apiClient from './api';

// ==================== 类型定义 ====================

export interface ScriptExecutionRequest {
  script_id: string;
  execution_config?: Record<string, any>;
  environment_variables?: Record<string, any>;
}

export interface BatchScriptExecutionRequest {
  script_ids: string[];
  execution_config?: Record<string, any>;
  environment_variables?: Record<string, any>;
  parallel?: boolean;
  continue_on_error?: boolean;
}

export interface ScriptExecutionResponse {
  session_id: string;
  script_id: string;
  script_name: string;
  script_type: 'database' | 'filesystem';
  status: string;
  message: string;
  sse_endpoint: string;
  created_at: string;
}

export interface BatchExecutionResponse {
  session_id: string;
  script_count: number;
  script_ids: string[];
  status: string;
  message: string;
  sse_endpoint: string;
  created_at: string;
}

export interface SessionInfo {
  session_id: string;
  type: 'single_script' | 'batch_scripts';
  script_id?: string;
  script_ids?: string[];
  script_info?: any;
  script_infos?: any[];
  execution_config: Record<string, any>;
  environment_variables: Record<string, any>;
  status: string;
  created_at: string;
  last_activity: string;
}

export interface ScriptStatus {
  session_id: string;
  script_name: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  start_time?: string;
  end_time?: string;
  error_message?: string;
}

export interface SessionListResponse {
  sessions: Record<string, SessionInfo>;
  total: number;
  timestamp: string;
}

export interface SessionDetailResponse {
  session_info: SessionInfo;
  script_statuses: Record<string, ScriptStatus>;
  timestamp: string;
}

// ==================== API函数 ====================

/**
 * 根据脚本ID执行脚本
 */
export const executeScriptById = async (request: ScriptExecutionRequest): Promise<ScriptExecutionResponse> => {
  const response = await apiClient.post('/web/execution/execute-by-id', request);
  return response.data;
};

/**
 * 根据脚本ID列表批量执行脚本
 */
export const batchExecuteScriptsByIds = async (request: BatchScriptExecutionRequest): Promise<BatchExecutionResponse> => {
  const response = await apiClient.post('/web/execution/batch-execute-by-ids', request);
  return response.data;
};

/**
 * 获取所有活动会话列表
 */
export const getActiveSessions = async (): Promise<SessionListResponse> => {
  const response = await apiClient.get('/web/execution/sessions');
  return response.data;
};

/**
 * 获取指定会话的详细信息
 */
export const getSessionInfo = async (sessionId: string): Promise<SessionDetailResponse> => {
  const response = await apiClient.get(`/web/execution/sessions/${sessionId}`);
  return response.data;
};

/**
 * 停止指定会话的执行
 */
export const stopSession = async (sessionId: string): Promise<{
  message: string;
  session_id: string;
  timestamp: string;
}> => {
  const response = await apiClient.post(`/web/execution/sessions/${sessionId}/stop`);
  return response.data;
};

/**
 * 创建统一脚本执行的SSE连接
 */
export const createUnifiedExecutionSSE = (
  sessionId: string,
  onMessage?: (event: MessageEvent) => void,
  onError?: (error: Event) => void,
  onOpen?: (event: Event) => void,
  onClose?: (event: Event) => void
): EventSource => {
  // 使用与 axios 相同的基址（相对路径经由 Vite 代理到 8002），避免硬编码 8000 导致连接失败
  const API_BASE_URL = import.meta.env.VITE_API_URL || '';
  const eventSource = new EventSource(`${API_BASE_URL}/api/v1/web/execution/stream/${sessionId}`);

  if (onOpen) {
    eventSource.onopen = onOpen;
  }

  if (onMessage) {
    eventSource.onmessage = onMessage;
  }

  if (onError) {
    eventSource.onerror = onError;
  }

  // 监听特定事件类型
  eventSource.addEventListener('session', (event) => {
    console.log('会话事件:', event.data);
    if (onMessage) onMessage(event);
  });

  eventSource.addEventListener('message', (event) => {
    console.log('消息事件:', event.data);
    if (onMessage) onMessage(event);
  });

  eventSource.addEventListener('error', (event) => {
    console.error('执行错误:', event.data);
    if (onMessage) onMessage(event);
  });

  eventSource.addEventListener('final_result', (event) => {
    console.log('执行完成:', event.data);
    if (onMessage) onMessage(event);
  });

  eventSource.addEventListener('close', (event) => {
    console.log('连接关闭:', event.data);
    if (onClose) onClose(event);
  });

  eventSource.addEventListener('ping', (event) => {
    // 心跳消息，保持连接
    console.debug('心跳:', event.data);
  });

  return eventSource;
};

// ==================== 便捷函数 ====================

/**
 * 执行单个脚本的便捷函数
 */
export const executeScript = async (
  scriptId: string,
  config?: {
    base_url?: string;
    headed?: boolean;
    timeout?: number;
    [key: string]: any;
  },
  environmentVariables?: Record<string, any>
): Promise<ScriptExecutionResponse> => {
  return executeScriptById({
    script_id: scriptId,
    execution_config: config,
    environment_variables: environmentVariables
  });
};

/**
 * 批量执行脚本的便捷函数
 */
export const batchExecuteScripts = async (
  scriptIds: string[],
  config?: {
    base_url?: string;
    headed?: boolean;
    timeout?: number;
    parallel?: boolean;
    continue_on_error?: boolean;
    [key: string]: any;
  },
  environmentVariables?: Record<string, any>
): Promise<BatchExecutionResponse> => {
  const { parallel, continue_on_error, ...executionConfig } = config || {};
  
  return batchExecuteScriptsByIds({
    script_ids: scriptIds,
    execution_config: executionConfig,
    environment_variables: environmentVariables,
    parallel: parallel || false,
    continue_on_error: continue_on_error !== false
  });
};

/**
 * 创建执行监控器
 */
export class UnifiedExecutionMonitor {
  private eventSource: EventSource | null = null;
  private sessionId: string;
  private onMessageCallback?: (message: any) => void;
  private onStatusChangeCallback?: (status: string) => void;
  private onErrorCallback?: (error: any) => void;
  private onCompleteCallback?: () => void;

  constructor(sessionId: string) {
    this.sessionId = sessionId;
  }

  /**
   * 设置消息回调
   */
  onMessage(callback: (message: any) => void): this {
    this.onMessageCallback = callback;
    return this;
  }

  /**
   * 设置状态变化回调
   */
  onStatusChange(callback: (status: string) => void): this {
    this.onStatusChangeCallback = callback;
    return this;
  }

  /**
   * 设置错误回调
   */
  onError(callback: (error: any) => void): this {
    this.onErrorCallback = callback;
    return this;
  }

  /**
   * 设置完成回调
   */
  onComplete(callback: () => void): this {
    this.onCompleteCallback = callback;
    return this;
  }

  /**
   * 开始监控
   */
  start(): this {
    this.eventSource = createUnifiedExecutionSSE(
      this.sessionId,
      (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log('监控器收到消息:', event.type, data);

          // 处理消息
          if (this.onMessageCallback) {
            this.onMessageCallback({
              ...data,
              type: event.type || data.type
            });
          }

          // 处理状态变化
          if (data.type === 'status' && this.onStatusChangeCallback) {
            this.onStatusChangeCallback(data.status);
          }

          // 处理完成事件 - 检查多种完成条件
          if ((event.type === 'final_result' || data.type === 'final_result' || data.is_final) && this.onCompleteCallback) {
            console.log('检测到执行完成，触发完成回调');
            this.onCompleteCallback();
          }

        } catch (error) {
          console.error('解析SSE消息失败:', error, event.data);
          // 解析失败时不要触发错误回调，只记录日志
          // 避免将正常的SSE消息当作错误处理
        }
      },
      (error) => {
        console.error('SSE连接错误:', error);
        if (this.onErrorCallback) {
          this.onErrorCallback(error);
        }
      },
      (event) => {
        console.log('SSE连接已建立');
      },
      (event) => {
        console.log('SSE连接已关闭');
      }
    );

    return this;
  }

  /**
   * 停止监控
   */
  stop(): void {
    console.log(`停止监控器: ${this.sessionId}`);
    if (this.eventSource) {
      try {
        this.eventSource.close();
        console.log(`SSE连接已关闭: ${this.sessionId}`);
      } catch (error) {
        console.error(`关闭SSE连接失败: ${this.sessionId}`, error);
      }
      this.eventSource = null;
    }
  }

  /**
   * 停止执行
   */
  async stopExecution(): Promise<void> {
    try {
      await stopSession(this.sessionId);
      this.stop();
    } catch (error) {
      console.error('停止执行失败:', error);
      throw error;
    }
  }

  /**
   * 获取会话信息
   */
  async getSessionInfo(): Promise<SessionDetailResponse> {
    return getSessionInfo(this.sessionId);
  }
}

/**
 * 创建执行监控器的便捷函数
 */
export const createExecutionMonitor = (sessionId: string): UnifiedExecutionMonitor => {
  return new UnifiedExecutionMonitor(sessionId);
};
