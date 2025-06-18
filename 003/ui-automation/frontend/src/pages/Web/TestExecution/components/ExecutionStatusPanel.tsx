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
  Tooltip,
  Badge,
  Divider,
  Row,
  Col,
  Statistic,
  Timeline,
  Modal,
  message
} from 'antd';
import {
  PlayCircleOutlined,
  PauseCircleOutlined,
  StopOutlined,
  ReloadOutlined,
  EyeOutlined,
  DownloadOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  LoadingOutlined,
  FileTextOutlined,
  BugOutlined
} from '@ant-design/icons';
import { motion, AnimatePresence } from 'framer-motion';
import toast from 'react-hot-toast';

import {
  createScriptExecutionSSE,
  stopScriptSession,
  getScriptSessionReports,
  getScriptSessionStatus
} from '../../../../services/api';

const { Text, Title } = Typography;

interface ExecutionMessage {
  id: string;
  type: string;
  source: string;
  content: string;
  region: string;
  timestamp: string;
  result?: any;
}

interface ScriptStatus {
  script_name: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  start_time?: string;
  end_time?: string;
  duration?: number;
  error_message?: string;
  report_path?: string;
}

interface ExecutionStatusPanelProps {
  sessionId: string | null;
  onSessionEnd?: () => void;
}

const ExecutionStatusPanel: React.FC<ExecutionStatusPanelProps> = ({
  sessionId,
  onSessionEnd
}) => {
  const [messages, setMessages] = useState<ExecutionMessage[]>([]);
  const [scriptStatuses, setScriptStatuses] = useState<Record<string, ScriptStatus>>({});
  const [sessionStatus, setSessionStatus] = useState<'connecting' | 'connected' | 'completed' | 'error' | 'disconnected'>('disconnected');
  const [statistics, setStatistics] = useState({
    total_scripts: 0,
    completed: 0,
    failed: 0,
    running: 0
  });
  const [showLogs, setShowLogs] = useState(false);
  const [reports, setReports] = useState<any[]>([]);
  
  const eventSourceRef = useRef<EventSource | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // 滚动到最新消息
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  // 连接SSE
  const connectSSE = useCallback(() => {
    if (!sessionId || eventSourceRef.current) return;

    setSessionStatus('connecting');
    setMessages([]);

    const eventSource = createScriptExecutionSSE(
      sessionId,
      (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data);
          
          // 处理不同类型的消息
          if (event.type === 'session') {
            setSessionStatus('connected');
            toast.success('已连接到执行会话');
          } else if (event.type === 'script_status') {
            // 更新脚本状态
            if (data.result) {
              setScriptStatuses(prev => ({
                ...prev,
                [data.result.script_name]: {
                  script_name: data.result.script_name,
                  status: data.result.status,
                  start_time: data.result.start_time,
                  end_time: data.result.end_time,
                  error_message: data.result.error_message
                }
              }));
            }
          } else if (event.type === 'batch_status' || event.type === 'progress') {
            // 更新统计信息
            if (data.result) {
              setStatistics(prev => ({
                ...prev,
                ...data.result
              }));
            }
          } else if (event.type === 'final_result') {
            setSessionStatus('completed');
            toast.success('执行已完成');
            loadReports();
          } else if (event.type === 'error') {
            setSessionStatus('error');
            toast.error('执行出现错误');
          }

          // 添加消息到列表
          const message: ExecutionMessage = {
            id: data.message_id || `msg-${Date.now()}`,
            type: event.type || 'message',
            source: data.source || '系统',
            content: data.content || '',
            region: data.region || 'info',
            timestamp: data.timestamp || new Date().toISOString(),
            result: data.result
          };

          setMessages(prev => [...prev, message]);
          
        } catch (error) {
          console.error('解析SSE消息失败:', error);
        }
      },
      (error: Event) => {
        console.error('SSE连接错误:', error);
        setSessionStatus('error');
        toast.error('连接执行会话失败');
      },
      (event: Event) => {
        setSessionStatus('connected');
      },
      (event: Event) => {
        setSessionStatus('disconnected');
        eventSourceRef.current = null;
      }
    );

    eventSourceRef.current = eventSource;
  }, [sessionId]);

  // 断开SSE连接
  const disconnectSSE = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
      setSessionStatus('disconnected');
    }
  }, []);

  // 加载报告
  const loadReports = useCallback(async () => {
    if (!sessionId) return;
    
    try {
      const data = await getScriptSessionReports(sessionId);
      setReports(data.reports);
    } catch (error) {
      console.error('加载报告失败:', error);
    }
  }, [sessionId]);

  // 停止执行
  const handleStop = async () => {
    if (!sessionId) return;

    try {
      await stopScriptSession(sessionId);
      toast.success('执行已停止');
      disconnectSSE();
      if (onSessionEnd) {
        onSessionEnd();
      }
    } catch (error: any) {
      toast.error(`停止失败: ${error.message}`);
    }
  };

  // 打开报告
  const handleOpenReport = (report: any) => {
    if (report.url) {
      window.open(report.url, '_blank');
    } else {
      message.info('报告文件路径不可用');
    }
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
      case 'running': return <LoadingOutlined spin />;
      case 'completed': return <CheckCircleOutlined />;
      case 'failed': return <ExclamationCircleOutlined />;
      default: return <ClockCircleOutlined />;
    }
  };

  // 获取消息颜色
  const getMessageColor = (region: string) => {
    switch (region) {
      case 'success': return '#52c41a';
      case 'error': return '#ff4d4f';
      case 'warning': return '#faad14';
      case 'process': return '#1890ff';
      default: return '#666';
    }
  };

  useEffect(() => {
    if (sessionId) {
      connectSSE();
    } else {
      disconnectSSE();
      setMessages([]);
      setScriptStatuses({});
      setStatistics({ total_scripts: 0, completed: 0, failed: 0, running: 0 });
    }

    return () => {
      disconnectSSE();
    };
  }, [sessionId, connectSSE, disconnectSSE]);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  if (!sessionId) {
    return (
      <Card title="执行状态" size="small">
        <div style={{ textAlign: 'center', padding: '40px 0', color: '#999' }}>
          <BugOutlined style={{ fontSize: 48, marginBottom: 16 }} />
          <div>暂无执行会话</div>
          <Text type="secondary">请先启动脚本执行</Text>
        </div>
      </Card>
    );
  }

  return (
    <div className="execution-status-panel">
      {/* 会话状态卡片 */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Row gutter={16}>
          <Col span={12}>
            <Statistic
              title="会话状态"
              value={sessionStatus}
              prefix={
                <Badge
                  status={
                    sessionStatus === 'connected' ? 'processing' :
                    sessionStatus === 'completed' ? 'success' :
                    sessionStatus === 'error' ? 'error' : 'default'
                  }
                />
              }
            />
          </Col>
          <Col span={12}>
            <Space>
              <Button
                size="small"
                icon={<StopOutlined />}
                danger
                onClick={handleStop}
                disabled={sessionStatus !== 'connected'}
              >
                停止
              </Button>
              <Button
                size="small"
                icon={<ReloadOutlined />}
                onClick={connectSSE}
                disabled={sessionStatus === 'connected'}
              >
                重连
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* 执行统计 */}
      {statistics.total_scripts > 0 && (
        <Card size="small" style={{ marginBottom: 16 }}>
          <Row gutter={8}>
            <Col span={6}>
              <Statistic
                title="总数"
                value={statistics.total_scripts}
                valueStyle={{ fontSize: 14 }}
              />
            </Col>
            <Col span={6}>
              <Statistic
                title="运行中"
                value={statistics.running}
                valueStyle={{ fontSize: 14, color: '#1890ff' }}
              />
            </Col>
            <Col span={6}>
              <Statistic
                title="已完成"
                value={statistics.completed}
                valueStyle={{ fontSize: 14, color: '#52c41a' }}
              />
            </Col>
            <Col span={6}>
              <Statistic
                title="失败"
                value={statistics.failed}
                valueStyle={{ fontSize: 14, color: '#ff4d4f' }}
              />
            </Col>
          </Row>
          
          {statistics.total_scripts > 0 && (
            <Progress
              percent={Math.round(((statistics.completed + statistics.failed) / statistics.total_scripts) * 100)}
              success={{ percent: Math.round((statistics.completed / statistics.total_scripts) * 100) }}
              size="small"
              style={{ marginTop: 8 }}
            />
          )}
        </Card>
      )}

      {/* 脚本状态列表 */}
      {Object.keys(scriptStatuses).length > 0 && (
        <Card 
          title="脚本状态" 
          size="small" 
          style={{ marginBottom: 16 }}
          extra={
            <Button
              size="small"
              icon={<EyeOutlined />}
              onClick={() => setShowLogs(true)}
            >
              查看日志
            </Button>
          }
        >
          <List
            size="small"
            dataSource={Object.values(scriptStatuses)}
            renderItem={(script) => (
              <List.Item>
                <div style={{ width: '100%' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Space>
                      {getStatusIcon(script.status)}
                      <Text strong>{script.script_name}</Text>
                    </Space>
                    <Tag color={getStatusColor(script.status)}>
                      {script.status}
                    </Tag>
                  </div>
                  {script.error_message && (
                    <Text type="danger" style={{ fontSize: 12 }}>
                      {script.error_message}
                    </Text>
                  )}
                  {script.duration && (
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      耗时: {script.duration.toFixed(1)}秒
                    </Text>
                  )}
                </div>
              </List.Item>
            )}
          />
        </Card>
      )}

      {/* 实时消息流 */}
      <Card 
        title="实时执行信息" 
        size="small"
        extra={
          <Space>
            <Badge count={messages.length} size="small" />
            <Button
              size="small"
              onClick={() => setMessages([])}
              disabled={messages.length === 0}
            >
              清空
            </Button>
          </Space>
        }
      >
        <div 
          style={{ 
            height: 300, 
            overflowY: 'auto',
            border: '1px solid #f0f0f0',
            borderRadius: 4,
            padding: 8,
            backgroundColor: '#fafafa'
          }}
        >
          <AnimatePresence>
            {messages.map((msg, index) => (
              <motion.div
                key={msg.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.2 }}
                style={{ marginBottom: 8 }}
              >
                <div style={{ 
                  padding: '6px 8px',
                  backgroundColor: 'white',
                  borderRadius: 4,
                  borderLeft: `3px solid ${getMessageColor(msg.region)}`,
                  fontSize: 12
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 2 }}>
                    <Text strong style={{ color: getMessageColor(msg.region) }}>
                      {msg.source}
                    </Text>
                    <Text type="secondary" style={{ fontSize: 11 }}>
                      {new Date(msg.timestamp).toLocaleTimeString()}
                    </Text>
                  </div>
                  <div>{msg.content}</div>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
          <div ref={messagesEndRef} />
        </div>
      </Card>

      {/* 报告列表 */}
      {reports.length > 0 && (
        <Card title="测试报告" size="small" style={{ marginTop: 16 }}>
          <List
            size="small"
            dataSource={reports}
            renderItem={(report) => (
              <List.Item
                actions={[
                  <Button
                    size="small"
                    icon={<EyeOutlined />}
                    onClick={() => handleOpenReport(report)}
                  >
                    查看
                  </Button>
                ]}
              >
                <List.Item.Meta
                  avatar={<FileTextOutlined style={{ color: '#1890ff' }} />}
                  title={report.name}
                  description={`大小: ${(report.size / 1024).toFixed(1)}KB | 创建时间: ${new Date(report.created).toLocaleString()}`}
                />
              </List.Item>
            )}
          />
        </Card>
      )}

      {/* 日志查看模态框 */}
      <Modal
        title="执行日志"
        open={showLogs}
        onCancel={() => setShowLogs(false)}
        footer={null}
        width={800}
      >
        <div style={{ height: 400, overflowY: 'auto' }}>
          <Timeline>
            {messages.map((msg) => (
              <Timeline.Item
                key={msg.id}
                color={getMessageColor(msg.region)}
                dot={getStatusIcon(msg.type)}
              >
                <div>
                  <Text strong>{msg.source}</Text>
                  <Text type="secondary" style={{ marginLeft: 8, fontSize: 12 }}>
                    {new Date(msg.timestamp).toLocaleString()}
                  </Text>
                </div>
                <div style={{ marginTop: 4 }}>{msg.content}</div>
                {msg.result && (
                  <pre style={{ 
                    fontSize: 11, 
                    backgroundColor: '#f5f5f5', 
                    padding: 8, 
                    borderRadius: 4,
                    marginTop: 4,
                    maxHeight: 100,
                    overflow: 'auto'
                  }}>
                    {JSON.stringify(msg.result, null, 2)}
                  </pre>
                )}
              </Timeline.Item>
            ))}
          </Timeline>
        </div>
      </Modal>
    </div>
  );
};

export default ExecutionStatusPanel;
