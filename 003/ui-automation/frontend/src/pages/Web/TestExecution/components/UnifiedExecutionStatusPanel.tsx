/**
 * 统一执行状态面板组件
 * 支持统一脚本执行的实时状态监控和日志显示
 */
import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Card,
  List,
  Tag,
  Typography,
  Space,
  Button,
  Progress,
  Alert,
  Divider,
  Badge,
  Tooltip,
  Empty,
  Spin,
  Row,
  Col,
  Statistic
} from 'antd';
import {
  PlayCircleOutlined,
  PauseCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
  ReloadOutlined,
  DownloadOutlined,
  StopOutlined,
  InfoCircleOutlined
} from '@ant-design/icons';
import { toast } from 'react-hot-toast';

import {
  createUnifiedExecutionSSE,
  getSessionInfo,
  stopSession,
  SessionDetailResponse
} from '../../../../services/unifiedScriptApi';

const { Text, Title } = Typography;

interface UnifiedExecutionStatusPanelProps {
  sessionId: string | null;
  scriptName?: string;
  onSessionEnd?: () => void;
}

interface ExecutionMessage {
  id: string;
  type: string;
  source: string;
  content: string;
  timestamp: string;
  region?: string;
  platform?: string;
  is_final?: boolean;
}

interface ScriptStatus {
  session_id: string;
  script_name: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  start_time?: string;
  end_time?: string;
  error_message?: string;
}

const UnifiedExecutionStatusPanel: React.FC<UnifiedExecutionStatusPanelProps> = ({
  sessionId,
  scriptName,
  onSessionEnd
}) => {
  const [messages, setMessages] = useState<ExecutionMessage[]>([]);
  const [sessionInfo, setSessionInfo] = useState<SessionDetailResponse | null>(null);
  const [scriptStatuses, setScriptStatuses] = useState<Record<string, ScriptStatus>>({});
  const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'connected' | 'disconnected' | 'error'>('disconnected');
  const [executionProgress, setExecutionProgress] = useState(0);
  const [isExecutionComplete, setIsExecutionComplete] = useState(false);
  const [loading, setLoading] = useState(false);

  const eventSourceRef = useRef<EventSource | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // 滚动到底部
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  // 获取会话信息
  const fetchSessionInfo = useCallback(async () => {
    if (!sessionId) return;

    try {
      setLoading(true);
      const info = await getSessionInfo(sessionId);
      setSessionInfo(info);
      setScriptStatuses(info.script_statuses);
    } catch (error: any) {
      console.error('获取会话信息失败:', error);
      toast.error('获取会话信息失败');
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  // 建立SSE连接
  const connectSSE = useCallback(() => {
    if (!sessionId) {
      console.log('没有sessionId，跳过SSE连接');
      return;
    }

    console.log(`开始建立SSE连接: ${sessionId}`);
    setConnectionStatus('connecting');
    setMessages([]);

    const eventSource = createUnifiedExecutionSSE(
      sessionId,
      (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log('状态面板收到SSE消息:', event.type, data);

          // 添加消息到列表
          const message: ExecutionMessage = {
            id: data.message_id || `msg-${Date.now()}`,
            type: event.type || data.type || 'message',
            source: data.source || '系统',
            content: data.content || data.message || JSON.stringify(data),
            timestamp: data.timestamp || new Date().toISOString(),
            region: data.region,
            platform: data.platform,
            is_final: data.is_final
          };

          setMessages(prev => [...prev, message]);

          // 处理特殊消息类型
          if (message.type === 'final_result' && message.is_final) {
            setIsExecutionComplete(true);
            setExecutionProgress(100);
            toast.success('执行完成');
          }

          // 更新进度
          if (message.type === 'progress' && data.progress !== undefined) {
            setExecutionProgress(data.progress);
          }

          // 更新脚本状态
          if (data.script_status) {
            setScriptStatuses(prev => ({
              ...prev,
              [data.script_status.script_name]: data.script_status
            }));
          }

        } catch (error) {
          console.error('解析SSE消息失败:', error);
        }
      },
      (error) => {
        console.error('SSE连接错误:', error);
        setConnectionStatus('error');
        // 只有在真正的网络错误时才显示错误提示
        if (error.target && error.target.readyState === EventSource.CLOSED) {
          console.log('SSE连接被关闭');
        } else {
          toast.error('连接执行服务失败');
        }
      },
      (event) => {
        console.log('SSE连接已建立');
        setConnectionStatus('connected');
      },
      (event) => {
        console.log('SSE连接已关闭');
        setConnectionStatus('disconnected');
      }
    );

    eventSourceRef.current = eventSource;
  }, [sessionId]);

  // 断开SSE连接
  const disconnectSSE = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
      setConnectionStatus('disconnected');
    }
  }, []);

  // 停止执行
  const handleStopExecution = async () => {
    if (!sessionId) return;

    try {
      await stopSession(sessionId);
      toast.success('执行已停止');
      setIsExecutionComplete(true);
      disconnectSSE();
      if (onSessionEnd) onSessionEnd();
    } catch (error: any) {
      toast.error(`停止执行失败: ${error.message}`);
    }
  };

  // 重新连接
  const handleReconnect = () => {
    disconnectSSE();
    setTimeout(() => {
      connectSSE();
      fetchSessionInfo();
    }, 1000);
  };

  // 清空消息
  const handleClearMessages = () => {
    setMessages([]);
  };

  // 获取状态颜色
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending': return 'default';
      case 'running': return 'processing';
      case 'completed': return 'success';
      case 'failed': return 'error';
      default: return 'default';
    }
  };

  // 获取状态图标
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'pending': return <ClockCircleOutlined />;
      case 'running': return <PlayCircleOutlined />;
      case 'completed': return <CheckCircleOutlined />;
      case 'failed': return <CloseCircleOutlined />;
      default: return <InfoCircleOutlined />;
    }
  };

  // 计算执行统计
  const executionStats = React.useMemo(() => {
    const statuses = Object.values(scriptStatuses);
    return {
      total: statuses.length,
      pending: statuses.filter(s => s.status === 'pending').length,
      running: statuses.filter(s => s.status === 'running').length,
      completed: statuses.filter(s => s.status === 'completed').length,
      failed: statuses.filter(s => s.status === 'failed').length
    };
  }, [scriptStatuses]);

  // 组件挂载时建立连接
  useEffect(() => {
    if (sessionId) {
      connectSSE();
      fetchSessionInfo();
    }

    return () => {
      disconnectSSE();
    };
  }, [sessionId, connectSSE, fetchSessionInfo, disconnectSSE]);

  // 自动滚动到底部
  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  if (!sessionId) {
    return (
      <Card title="执行状态" style={{ height: '100%' }}>
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description="请选择脚本并开始执行"
        />
      </Card>
    );
  }

  return (
    <Card
      title={
        <Space>
          <span>执行状态</span>
          {scriptName && <Text type="secondary">- {scriptName}</Text>}
          <Badge
            status={connectionStatus === 'connected' ? 'success' : 'error'}
            text={connectionStatus === 'connected' ? '已连接' : '未连接'}
          />
        </Space>
      }
      extra={
        <Space>
          <Button
            size="small"
            icon={<ReloadOutlined />}
            onClick={handleReconnect}
            disabled={connectionStatus === 'connecting'}
          >
            重连
          </Button>
          <Button
            size="small"
            onClick={handleClearMessages}
          >
            清空
          </Button>
          {!isExecutionComplete && (
            <Button
              size="small"
              danger
              icon={<StopOutlined />}
              onClick={handleStopExecution}
            >
              停止
            </Button>
          )}
        </Space>
      }
      style={{ height: '100%' }}
      bodyStyle={{ height: 'calc(100% - 57px)', padding: 0 }}
    >
      <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
        {/* 执行统计 */}
        {executionStats.total > 0 && (
          <div style={{ padding: '12px 16px', borderBottom: '1px solid #f0f0f0' }}>
            <Row gutter={8}>
              <Col span={6}>
                <Statistic
                  title="总数"
                  value={executionStats.total}
                  valueStyle={{ fontSize: 14 }}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="运行中"
                  value={executionStats.running}
                  valueStyle={{ fontSize: 14, color: '#1890ff' }}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="已完成"
                  value={executionStats.completed}
                  valueStyle={{ fontSize: 14, color: '#52c41a' }}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="失败"
                  value={executionStats.failed}
                  valueStyle={{ fontSize: 14, color: '#ff4d4f' }}
                />
              </Col>
            </Row>
            
            {executionProgress > 0 && (
              <Progress
                percent={executionProgress}
                size="small"
                style={{ marginTop: 8 }}
                status={isExecutionComplete ? 'success' : 'active'}
              />
            )}
          </div>
        )}

        {/* 脚本状态列表 */}
        {Object.keys(scriptStatuses).length > 0 && (
          <div style={{ padding: '12px 16px', borderBottom: '1px solid #f0f0f0' }}>
            <Text strong style={{ marginBottom: 8, display: 'block' }}>脚本状态</Text>
            <Space direction="vertical" style={{ width: '100%' }} size="small">
              {Object.values(scriptStatuses).map((status) => (
                <div key={status.script_name} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Space>
                    {getStatusIcon(status.status)}
                    <Text>{status.script_name}</Text>
                  </Space>
                  <Tag color={getStatusColor(status.status)}>
                    {status.status}
                  </Tag>
                </div>
              ))}
            </Space>
          </div>
        )}

        {/* 消息列表 */}
        <div style={{ flex: 1, overflow: 'auto', padding: '12px 16px' }}>
          {loading ? (
            <div style={{ textAlign: 'center', padding: 20 }}>
              <Spin tip="加载中..." />
            </div>
          ) : messages.length === 0 ? (
            <Empty
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              description="暂无执行消息"
              style={{ marginTop: 40 }}
            />
          ) : (
            <List
              size="small"
              dataSource={messages}
              renderItem={(message) => (
                <List.Item style={{ padding: '8px 0', borderBottom: 'none' }}>
                  <div style={{ width: '100%' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 4 }}>
                      <Space size="small">
                        <Tag size="small" color={message.type === 'error' ? 'red' : 'blue'}>
                          {message.type}
                        </Tag>
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          {message.source}
                        </Text>
                      </Space>
                      <Text type="secondary" style={{ fontSize: 11 }}>
                        {new Date(message.timestamp).toLocaleTimeString()}
                      </Text>
                    </div>
                    <div style={{ 
                      fontSize: 13, 
                      lineHeight: 1.4,
                      color: message.type === 'error' ? '#ff4d4f' : undefined,
                      fontWeight: message.is_final ? 'bold' : 'normal'
                    }}>
                      {message.content}
                    </div>
                    {message.region && (
                      <Tag size="small" style={{ marginTop: 4 }}>
                        {message.region}
                      </Tag>
                    )}
                  </div>
                </List.Item>
              )}
            />
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* 连接状态提示 */}
        {connectionStatus === 'error' && (
          <Alert
            message="连接失败"
            description="无法连接到执行服务，请检查网络连接或重新连接"
            type="error"
            showIcon
            style={{ margin: '12px 16px' }}
            action={
              <Button size="small" onClick={handleReconnect}>
                重新连接
              </Button>
            }
          />
        )}

        {connectionStatus === 'connecting' && (
          <Alert
            message="正在连接..."
            type="info"
            showIcon
            style={{ margin: '12px 16px' }}
          />
        )}
      </div>
    </Card>
  );
};

export default UnifiedExecutionStatusPanel;
