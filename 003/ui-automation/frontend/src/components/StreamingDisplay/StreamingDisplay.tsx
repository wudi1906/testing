import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Card,
  Typography,
  Timeline,
  Alert,
  Progress,
  Space,
  Tag,
  Divider,
  Button,
  Empty,
  Spin,
  Collapse
} from 'antd';
import {
  RobotOutlined,
  CheckCircleOutlined,
  LoadingOutlined,
  ExclamationCircleOutlined,
  ClockCircleOutlined,
  ThunderboltOutlined,
  GlobalOutlined,
  CodeOutlined,
  DownOutlined
} from '@ant-design/icons';
import { ThoughtChain } from '@ant-design/x';
import ReactMarkdown from 'react-markdown';
import './StreamingDisplay.css';

const { Title, Text, Paragraph } = Typography;
const { Panel } = Collapse;

// JSON格式化工具函数
const formatJsonContent = (content: string): string => {
  try {
    // 尝试提取JSON内容
    const jsonRegex = /```json\s*([\s\S]*?)\s*```/g;
    const yamlRegex = /```yaml\s*([\s\S]*?)\s*```/g;
    const codeRegex = /```(\w+)?\s*([\s\S]*?)\s*```/g;

    let formattedContent = content;

    // 格式化JSON代码块
    formattedContent = formattedContent.replace(jsonRegex, (match, jsonStr) => {
      try {
        const parsed = JSON.parse(jsonStr.trim());
        const formatted = JSON.stringify(parsed, null, 2);
        return `\`\`\`json\n${formatted}\n\`\`\``;
      } catch (e) {
        return match; // 如果解析失败，返回原内容
      }
    });

    // 检测并格式化裸露的JSON对象
    const jsonObjectRegex = /(\{[\s\S]*?\}|\[[\s\S]*?\])/g;
    formattedContent = formattedContent.replace(jsonObjectRegex, (match) => {
      // 跳过已经在代码块中的内容
      if (content.indexOf('```') !== -1 &&
          content.indexOf(match) > content.indexOf('```') &&
          content.indexOf(match) < content.lastIndexOf('```')) {
        return match;
      }

      try {
        const parsed = JSON.parse(match.trim());
        const formatted = JSON.stringify(parsed, null, 2);
        return `\`\`\`json\n${formatted}\n\`\`\``;
      } catch (e) {
        return match;
      }
    });

    return formattedContent;
  } catch (error) {
    return content; // 如果处理失败，返回原内容
  }
};

// 检测内容是否包含JSON数据
const hasJsonContent = (content: string): boolean => {
  const jsonRegex = /```json|(\{[\s\S]*?\}|\[[\s\S]*?\])/;
  return jsonRegex.test(content);
};

// 创建可折叠的JSON显示组件
const JsonCollapsible: React.FC<{ content: string; title?: string }> = ({ content, title = "JSON数据" }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <Collapse
      size="small"
      ghost
      activeKey={isExpanded ? ['json'] : []}
      onChange={(keys) => setIsExpanded(keys.includes('json'))}
      className="json-collapsible"
      style={{ margin: '8px 0' }}
    >
      <Panel
        header={
          <Space>
            <CodeOutlined style={{ color: '#1890ff' }} />
            <Text strong style={{ color: '#1890ff' }}>{title}</Text>
            <Tag className="json-tag" size="small">JSON</Tag>
          </Space>
        }
        key="json"
        extra={<DownOutlined rotate={isExpanded ? 180 : 0} />}
      >
        <div className="json-content">
          <ReactMarkdown
            components={{
              code: ({ node, inline, className, children, ...props }) => {
                if (!inline) {
                  return (
                    <pre style={{
                      background: 'transparent',
                      padding: 0,
                      margin: 0,
                      border: 'none',
                      overflow: 'visible'
                    }}>
                      <code style={{
                        fontFamily: 'SFMono-Regular, Consolas, "Liberation Mono", Menlo, monospace',
                        fontSize: '12px',
                        lineHeight: '1.45',
                        color: '#24292e',
                        whiteSpace: 'pre-wrap'
                      }} {...props}>
                        {children}
                      </code>
                    </pre>
                  );
                }
                return <code {...props}>{children}</code>;
              }
            }}
          >
            {formatJsonContent(content)}
          </ReactMarkdown>
        </div>
      </Panel>
    </Collapse>
  );
};

// 按时间顺序构建思考链数据，保持think和普通内容的实际输出顺序
const buildThoughtChainData = (messages: StreamMessage[]) => {
  const thoughtChainItems: Array<{
    title: string;
    content: string;
    status: 'success' | 'pending' | 'error';
    timestamp: string;
    hasJson?: boolean;
  }> = [];

  // 按时间戳排序所有消息
  const sortedMessages = [...messages].sort((a, b) => {
    const timeA = new Date(a.timestamp || 0).getTime();
    const timeB = new Date(b.timestamp || 0).getTime();
    return timeA - timeB;
  });

  // 逐个处理每条消息，按实际输出顺序解析内容
  sortedMessages.forEach((message) => {
    if (!message.content || !message.content.trim()) {
      return;
    }

    // 解析消息内容，按顺序提取think和普通内容
    const contentParts = parseContentInOrder(message.content);

    contentParts.forEach((part, index) => {
      if (part.content.trim()) {
        thoughtChainItems.push({
          title: message.source, // 直接使用source属性值作为节点名称
          content: part.content,
          status: message.type === 'error' ? 'error' : 'success',
          timestamp: message.timestamp || new Date().toISOString(),
          hasJson: hasJsonContent(part.content) // 标记是否包含JSON内容
        });
      }
    });
  });

  return thoughtChainItems;
};

// 按实际输出顺序解析内容，保持think和普通内容的原始顺序
const parseContentInOrder = (content: string) => {
  const parts: Array<{
    type: 'think' | 'normal';
    content: string;
  }> = [];

  // 使用正则表达式找到所有think标签的位置
  const thinkRegex = /<think>([\s\S]*?)<\/think>/g;
  let lastIndex = 0;
  let match;

  while ((match = thinkRegex.exec(content)) !== null) {
    // 添加think标签前的普通内容
    if (match.index > lastIndex) {
      const normalContent = content.slice(lastIndex, match.index).trim();
      if (normalContent) {
        parts.push({
          type: 'normal',
          content: normalContent
        });
      }
    }

    // 添加think内容
    const thinkContent = match[1].trim();
    if (thinkContent) {
      parts.push({
        type: 'think',
        content: `**🤔 AI思考过程：**\n\n${thinkContent}`
      });
    }

    lastIndex = thinkRegex.lastIndex;
  }

  // 添加最后剩余的普通内容
  if (lastIndex < content.length) {
    const remainingContent = content.slice(lastIndex).trim();
    if (remainingContent) {
      parts.push({
        type: 'normal',
        content: remainingContent
      });
    }
  }

  // 如果没有找到任何think标签，整个内容作为普通内容
  if (parts.length === 0 && content.trim()) {
    parts.push({
      type: 'normal',
      content: content.trim()
    });
  }

  return parts;
};

interface StreamMessage {
  message_id: string;
  type: string;
  source: string;
  content: string;
  region: string;
  platform: string;
  is_final: boolean;
  timestamp?: string;
  result?: any;
}

interface StreamingDisplayProps {
  sessionId?: string;
  isActive: boolean;
  onAnalysisComplete?: (result: any) => void;
  onError?: (error: string) => void;
  testMode?: boolean; // 添加测试模式
}

const StreamingDisplay: React.FC<StreamingDisplayProps> = ({
  sessionId,
  isActive,
  onAnalysisComplete,
  onError,
  testMode = false
}) => {
  const [messages, setMessages] = useState<StreamMessage[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<'disconnected' | 'connecting' | 'connected' | 'error'>('disconnected');
  const [analysisResult, setAnalysisResult] = useState<any>(null);
  const [progress, setProgress] = useState(0);
  const eventSourceRef = useRef<EventSource | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // 自动滚动到最新消息（使用防抖）
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  // 使用防抖优化滚动
  useEffect(() => {
    const timer = setTimeout(scrollToBottom, 100);
    return () => clearTimeout(timer);
  }, [messages, scrollToBottom]);

  // 连接SSE或启动测试模式
  useEffect(() => {
    if (!sessionId || !isActive) {
      // 如果isActive为false但有sessionId和消息，说明分析已完成，保持当前状态
      if (!isActive && sessionId && messages.length > 0) {
        console.log('分析已完成，保持当前内容显示，不重置');
        return; // 保持当前内容，不重置
      }
      return;
    }

    // 只有在开始新的分析时才重置状态（当前没有消息或者是新的sessionId）
    if (messages.length === 0 || isActive) {
      console.log('开始新的分析，重置状态');
      setMessages([]);
      setProgress(0);
    }

    if (testMode) {
      // 测试模式：使用本地模拟数据
      startTestMode();
    } else {
      // 正常模式：连接SSE
      connectSSE();
    }

    return () => {
      disconnectSSE();
    };
  }, [sessionId, isActive, testMode]);

  const startTestMode = () => {
    console.log('启动测试模式，sessionId:', sessionId);
    setConnectionStatus('connected');
    setMessages([]);
    setProgress(0);

    // 模拟测试数据
    const testMessages = [
      {
        message_id: "msg-1",
        type: "message",
        source: "UI分析专家",
        content: "<think>我需要分析这个界面的UI元素，首先观察整体布局</think>开始分析UI界面结构...",
        region: "analysis",
        platform: "web",
        is_final: false,
        timestamp: new Date(Date.now() - 5000).toISOString()
      },
      {
        message_id: "msg-2",
        type: "message",
        source: "UI分析专家",
        content: "识别到登录表单，包含用户名和密码输入框。<think>这个表单看起来是标准的登录界面，我需要分析每个元素的定位方式</think>",
        region: "analysis",
        platform: "web",
        is_final: false,
        timestamp: new Date(Date.now() - 4000).toISOString()
      },
      {
        message_id: "msg-3",
        type: "message",
        source: "交互流程设计师",
        content: "<think>基于UI专家的分析，我需要设计用户交互流程</think>设计测试交互流程：\n1. 输入用户名\n2. 输入密码\n3. 点击登录按钮",
        region: "interaction",
        platform: "web",
        is_final: false,
        timestamp: new Date(Date.now() - 3000).toISOString()
      },
      {
        message_id: "msg-4",
        type: "message",
        source: "交互流程设计师",
        content: "验证交互元素的可访问性。<think>我需要确保所有的交互元素都能被正确识别和操作</think>所有元素均可正常交互。",
        region: "interaction",
        platform: "web",
        is_final: false,
        timestamp: new Date(Date.now() - 2000).toISOString()
      },
      {
        message_id: "msg-5",
        type: "message",
        source: "质量保证专家",
        content: "<think>我需要审查前面专家们的分析结果，确保测试用例的完整性</think>审查测试用例设计...\n\n发现以下测试场景：\n- 正常登录流程\n- 错误处理验证",
        region: "quality",
        platform: "web",
        is_final: false,
        timestamp: new Date(Date.now() - 1000).toISOString()
      },
      {
        message_id: "msg-6",
        type: "message",
        source: "YAML脚本生成器",
        content: "<think>基于所有专家的分析，我现在开始生成YAML测试脚本</think>开始生成MidScene.js YAML脚本...\n\n```yaml\nname: 登录功能测试\nsteps:\n  - action: type\n    target: '[placeholder=\"用户名\"]'\n    value: 'testuser'\n```",
        region: "generation",
        platform: "web",
        is_final: true,
        timestamp: new Date().toISOString()
      }
    ];

    // 模拟逐步接收消息
    testMessages.forEach((message, index) => {
      setTimeout(() => {
        setMessages(prev => [...prev, message]);
        setProgress(prev => Math.min(prev + 15, 90));

        if (index === testMessages.length - 1) {
          // 最后一条消息
          setTimeout(() => {
            setProgress(100);
            if (onAnalysisComplete) {
              onAnalysisComplete({ test: 'completed' });
            }
          }, 500);
        }
      }, index * 1000);
    });
  };

  const connectSSE = () => {
    if (!sessionId) {
      console.log('没有sessionId，无法连接SSE');
      return;
    }

    console.log('开始连接SSE，sessionId:', sessionId);
    setConnectionStatus('connecting');
    // 只有在开始新分析时才清除消息，如果已有消息则保持
    if (messages.length === 0) {
      setMessages([]);
      setProgress(0);
    }

    const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    const sseUrl = `${baseUrl}/api/v1/web/create/stream/${sessionId}`;

    console.log('连接SSE URL:', sseUrl);

    const eventSource = new EventSource(sseUrl);
    eventSourceRef.current = eventSource;

    eventSource.onopen = () => {
      console.log('SSE连接已建立');
      setIsConnected(true);
      setConnectionStatus('connected');
    };

    eventSource.onmessage = (event) => {
      // 默认的onmessage只处理没有指定事件类型的消息
      // 由于我们使用自定义事件类型，这里通常不会被调用
      console.log('收到默认message事件（通常不应该发生）:', event);
      console.log('事件数据:', event.data);

      try {
        const data = JSON.parse(event.data);
        console.log('默认事件解析成功:', data);
        handleSSEMessage(data);
      } catch (error) {
        console.warn('默认事件解析失败，这是正常的，因为我们使用自定义事件类型:', error);
        console.log('原始数据:', event.data);
      }
    };

    // 统一的事件处理函数
    const handleEvent = (eventType: string, event: MessageEvent) => {
      console.log(`🎯 收到 ${eventType} 事件:`, event);
      console.log(`📝 ${eventType} 事件原始数据:`, event.data);

      try {
        // 提取JSON数据：如果event.data包含SSE格式，需要提取data:后面的内容
        let jsonData = event.data;

        // 检查是否是SSE格式的数据
        if (typeof jsonData === 'string' && jsonData.includes('data: ')) {
          // 提取data:后面的JSON内容
          const lines = jsonData.split('\n');
          const dataLine = lines.find(line => line.startsWith('data: '));
          if (dataLine) {
            jsonData = dataLine.substring(6); // 移除"data: "前缀
            console.log(`🔧 提取的JSON数据:`, jsonData);
          } else {
            console.warn(`⚠️ 未找到data:行，原始数据:`, jsonData);
            return;
          }
        }

        const data = JSON.parse(jsonData);
        console.log(`✅ 解析后的 ${eventType} 数据:`, data);
        console.log(`📄 content字段:`, data.content);

        switch (eventType) {
          case 'session':
            console.log('🔗 会话已连接:', data);
            setConnectionStatus('connected');
            break;
          case 'message':
            console.log('💬 处理消息事件:', data);
            handleSSEMessage(data);
            break;
          case 'final_result':
            console.log('🏁 处理最终结果:', data);
            handleFinalResult(data);
            break;
          case 'error':
            console.log('❌ 处理错误事件:', data);
            handleError(data.content || '分析过程出错');
            break;
          case 'ping':
            console.log('💓 收到心跳消息');
            // ping消息不处理，不显示在界面上
            return;
          default:
            // 对于未知事件类型，尝试作为普通消息处理
            if (data.type) {
              console.log(`🔄 处理未知事件类型 ${eventType} 作为消息:`, data);
              handleSSEMessage(data);
            }
        }
      } catch (error) {
        console.error(`❌ 解析 ${eventType} 事件失败:`, error, 'Raw data:', event.data);
        if (eventType === 'error') {
          handleError('连接出错');
        }
      }
    };

    // 注册所有事件监听器
    ['session', 'message', 'final_result', 'error', 'ping', 'close'].forEach(eventType => {
      eventSource.addEventListener(eventType, (event) => handleEvent(eventType, event));
    });

    // 添加调试信息
    console.log('已注册所有SSE事件监听器');

    eventSource.onerror = (error) => {
      console.error('SSE连接错误:', error);
      setConnectionStatus('error');
      setIsConnected(false);
      if (onError) {
        onError('连接中断，请重试');
      }
    };
  };

  const disconnectSSE = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    setIsConnected(false);
    setConnectionStatus('disconnected');
  };

  const handleSSEMessage = (data: any) => {
    console.log('🔄 处理SSE消息:', data);
    console.log('📄 消息内容:', `"${data.content}"`);

    // 过滤ping消息
    if (data.type === 'ping') {
      console.log('💓 收到心跳消息，跳过显示');
      return;
    }

    // 同时保存到messages数组用于ThoughtChain
    if (data.content && data.source) {
      const message: StreamMessage = {
        message_id: data.message_id || `msg-${Date.now()}`,
        type: data.type || 'message',
        source: data.source || '系统',
        content: data.content || '',
        region: data.region || 'general',
        platform: data.platform || 'web',
        is_final: data.is_final || false,
        timestamp: data.timestamp || new Date().toISOString()
      };

      setMessages(prev => {
        const newMessages = [...prev];
        // 查找同一来源的最后一条消息
        const lastMessageIndex = newMessages.findLastIndex(msg => msg.source === data.source);

        if (lastMessageIndex >= 0 && !newMessages[lastMessageIndex].is_final) {
          // 累积到现有消息
          newMessages[lastMessageIndex] = {
            ...newMessages[lastMessageIndex],
            content: newMessages[lastMessageIndex].content + data.content,
            timestamp: data.timestamp || new Date().toISOString(),
            is_final: data.is_final || false
          };
        } else {
          // 创建新消息
          newMessages.push(message);
        }

        return newMessages;
      });
    }

    // 更新进度
    if (data.type === 'message') {
      setProgress(prev => Math.min(prev + 2, 90));
    }

    // 处理最终结果
    if (data.type === 'final_result') {
      setProgress(100);
      if (onAnalysisComplete) {
        onAnalysisComplete(data.result || '分析完成');
      }
    }

    // 处理错误
    if (data.type === 'error') {
      if (onError) {
        onError(data.content || '分析过程出错');
      }
    }
  };

  const handleFinalResult = (data: any) => {
    console.log('收到最终结果:', data);

    // 添加完成消息
    const finalMessage: StreamMessage = {
      message_id: `final-${Date.now()}`,
      type: 'final_result',
      source: '系统',
      content: data.content || '分析完成',
      region: 'result',
      platform: 'web',
      is_final: true,
      timestamp: new Date().toISOString(),
      result: data.result
    };

    setMessages(prev => [...prev, finalMessage]);
    setProgress(100);

    if (data.result) {
      setAnalysisResult(data.result);
      if (onAnalysisComplete) {
        onAnalysisComplete(data.result);
      }
    }
  };

  const handleError = (errorMessage: string) => {
    const errorMsg: StreamMessage = {
      message_id: `error-${Date.now()}`,
      type: 'error',
      source: '系统',
      content: errorMessage,
      region: 'error',
      platform: 'web',
      is_final: true,
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, errorMsg]);
    setConnectionStatus('error');

    if (onError) {
      onError(errorMessage);
    }
  };

  const getMessageIcon = (type: string) => {
    switch (type) {
      case 'final_result':
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
      case 'error':
        return <ExclamationCircleOutlined style={{ color: '#ff4d4f' }} />;
      case 'message':
        return <RobotOutlined style={{ color: '#1890ff' }} />;
      default:
        return <ClockCircleOutlined style={{ color: '#faad14' }} />;
    }
  };

  const getConnectionStatusColor = () => {
    switch (connectionStatus) {
      case 'connected':
        return '#52c41a';
      case 'connecting':
        return '#faad14';
      case 'error':
        return '#ff4d4f';
      default:
        return '#d9d9d9';
    }
  };

  const getConnectionStatusText = () => {
    switch (connectionStatus) {
      case 'connected':
        return '已连接';
      case 'connecting':
        return '连接中';
      case 'error':
        return '连接错误';
      default:
        return '未连接';
    }
  };

  return (
    <Card
      className="streaming-display"
      title={
        <Space>
          <ThunderboltOutlined />
          <span>实时分析进度</span>
          <Tag color={getConnectionStatusColor()}>
            {getConnectionStatusText()}
          </Tag>
        </Space>
      }
      extra={
        sessionId && (
          <Text type="secondary" style={{ fontSize: '12px' }}>
            会话: {sessionId.slice(0, 8)}...
          </Text>
        )
      }
      style={{ height: '100%', display: 'flex', flexDirection: 'column' }}
      bodyStyle={{ flex: 1, padding: '16px', overflow: 'hidden' }}
    >
      {!sessionId || (!isActive && messages.length === 0) ? (
        <Empty
          image={<GlobalOutlined style={{ fontSize: '48px', color: '#d9d9d9' }} />}
          description={
            <div>
              <Text type="secondary">等待开始分析</Text>
              <br />
              <Text type="secondary" style={{ fontSize: '12px' }}>
                上传图片或输入URL后，实时分析进度将在此显示
              </Text>
            </div>
          }
        />
      ) : (
        <div className="streaming-content" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
          {/* 进度条 */}
          {((isActive && progress > 0) || (!isActive && progress === 100)) && (
            <div style={{ marginBottom: 16, flexShrink: 0 }}>
              <Progress
                percent={progress}
                status={connectionStatus === 'error' ? 'exception' : (progress === 100 ? 'success' : 'active')}
                strokeColor={{
                  '0%': '#108ee9',
                  '100%': '#87d068',
                }}
              />
            </div>
          )}

          {/* 分析完成提示 */}
          {!isActive && progress === 100 && messages.length > 0 && (
            <div style={{ marginBottom: 16, flexShrink: 0 }}>
              <Alert
                message="分析完成"
                description="AI分析已完成，您可以查看下方的详细分析过程和结果"
                type="success"
                showIcon
                icon={<CheckCircleOutlined />}
              />
            </div>
          )}

          {/* 思考链和流式内容显示 */}
          <div className="messages-container" style={{ flex: 1, overflowY: 'auto', paddingRight: '8px' }}>
            {/* 调试信息 */}
            <div style={{ fontSize: '12px', color: '#999', marginBottom: '8px' }}>
              消息数: {messages.length} | 连接状态: {connectionStatus}
            </div>

            {!messages.length && connectionStatus === 'connected' ? (
              <div style={{ textAlign: 'center', padding: '20px' }}>
                <Spin indicator={<LoadingOutlined style={{ fontSize: 24 }} spin />} />
                <div style={{ marginTop: 8 }}>
                  <Text type="secondary">正在初始化分析流程...</Text>
                </div>
              </div>
            ) : (
              <>
                {/* 思考链展示 - 按时间顺序显示 */}
                {messages.length > 0 && (
                  <div style={{ marginBottom: 24 }}>
                    <div style={{ marginBottom: 12, fontSize: '14px', fontWeight: 'bold', color: '#1890ff' }}>
                      🧠 AI分析过程 (按时间顺序)
                    </div>
                    <ThoughtChain
                      items={buildThoughtChainData(messages).map(item => ({
                        title: item.title,
                        content: (
                          <div>
                            {/* 如果包含JSON内容，显示可折叠的JSON组件 */}
                            {item.hasJson ? (
                              <div>
                                <ReactMarkdown
                                  components={{
                                    p: ({ children }) => <p style={{ margin: '0.5em 0', lineHeight: '1.6' }}>{children}</p>,
                                    h1: ({ children }) => <h1 style={{ fontSize: '1.2em', margin: '0.8em 0 0.4em 0', color: '#1890ff' }}>{children}</h1>,
                                    h2: ({ children }) => <h2 style={{ fontSize: '1.1em', margin: '0.7em 0 0.3em 0', color: '#1890ff' }}>{children}</h2>,
                                    h3: ({ children }) => <h3 style={{ fontSize: '1.05em', margin: '0.6em 0 0.2em 0', color: '#1890ff' }}>{children}</h3>,
                                    strong: ({ children }) => <strong style={{ color: '#1890ff', fontWeight: 'bold' }}>{children}</strong>,
                                    em: ({ children }) => <em style={{ color: '#52c41a', fontStyle: 'italic' }}>{children}</em>,
                                    hr: () => <hr style={{ border: 'none', borderTop: '2px solid #e8e8e8', margin: '16px 0' }} />,
                                    code: ({ node, inline, className, children, ...props }) => {
                                      const match = /language-(\w+)/.exec(className || '');
                                      const language = match ? match[1] : '';

                                      if (!inline && (language === 'json' || language === 'yaml')) {
                                        // JSON/YAML代码块使用可折叠组件
                                        return (
                                          <JsonCollapsible
                                            content={`\`\`\`${language}\n${children}\n\`\`\``}
                                            title={`${language.toUpperCase()} 数据`}
                                          />
                                        );
                                      } else if (!inline) {
                                        // 其他代码块
                                        return (
                                          <pre style={{
                                            background: '#f6f8fa',
                                            padding: '12px',
                                            borderRadius: '6px',
                                            overflow: 'auto',
                                            margin: '8px 0',
                                            border: '1px solid #e1e4e8'
                                          }}>
                                            <code style={{
                                              fontFamily: 'SFMono-Regular, Consolas, "Liberation Mono", Menlo, monospace',
                                              fontSize: '13px',
                                              lineHeight: '1.45',
                                              color: '#24292e'
                                            }} {...props}>
                                              {children}
                                            </code>
                                          </pre>
                                        );
                                      } else {
                                        // 行内代码
                                        return (
                                          <code style={{
                                            background: '#f6f8fa',
                                            padding: '2px 4px',
                                            borderRadius: '3px',
                                            fontSize: '0.9em',
                                            color: '#d73a49',
                                            fontFamily: 'SFMono-Regular, Consolas, "Liberation Mono", Menlo, monospace'
                                          }} {...props}>
                                            {children}
                                          </code>
                                        );
                                      }
                                    },
                                    pre: ({ children }) => children, // 让code组件处理pre
                                    ul: ({ children }) => <ul style={{ margin: '0.5em 0', paddingLeft: '1.5em' }}>{children}</ul>,
                                    li: ({ children }) => <li style={{ margin: '0.2em 0' }}>{children}</li>,
                                    blockquote: ({ children }) => (
                                      <blockquote style={{
                                        borderLeft: '4px solid #1890ff',
                                        paddingLeft: '1em',
                                        margin: '0.5em 0',
                                        fontStyle: 'italic',
                                        color: '#666',
                                        background: '#f9f9f9',
                                        borderRadius: '0 4px 4px 0'
                                      }}>{children}</blockquote>
                                    )
                                  }}
                                >
                                  {formatJsonContent(item.content)}
                                </ReactMarkdown>
                              </div>
                            ) : (
                              <ReactMarkdown
                                components={{
                                  p: ({ children }) => <p style={{ margin: '0.5em 0', lineHeight: '1.6' }}>{children}</p>,
                                  h1: ({ children }) => <h1 style={{ fontSize: '1.2em', margin: '0.8em 0 0.4em 0', color: '#1890ff' }}>{children}</h1>,
                                  h2: ({ children }) => <h2 style={{ fontSize: '1.1em', margin: '0.7em 0 0.3em 0', color: '#1890ff' }}>{children}</h2>,
                                  h3: ({ children }) => <h3 style={{ fontSize: '1.05em', margin: '0.6em 0 0.2em 0', color: '#1890ff' }}>{children}</h3>,
                                  strong: ({ children }) => <strong style={{ color: '#1890ff', fontWeight: 'bold' }}>{children}</strong>,
                                  em: ({ children }) => <em style={{ color: '#52c41a', fontStyle: 'italic' }}>{children}</em>,
                                  hr: () => <hr style={{ border: 'none', borderTop: '2px solid #e8e8e8', margin: '16px 0' }} />,
                                  code: ({ node, inline, className, children, ...props }) => {
                                    if (!inline) {
                                      return (
                                        <pre style={{
                                          background: '#f6f8fa',
                                          padding: '12px',
                                          borderRadius: '6px',
                                          overflow: 'auto',
                                          margin: '8px 0',
                                          border: '1px solid #e1e4e8'
                                        }}>
                                          <code style={{
                                            fontFamily: 'SFMono-Regular, Consolas, "Liberation Mono", Menlo, monospace',
                                            fontSize: '13px',
                                            lineHeight: '1.45',
                                            color: '#24292e'
                                          }} {...props}>
                                            {children}
                                          </code>
                                        </pre>
                                      );
                                    } else {
                                      return (
                                        <code style={{
                                          background: '#f6f8fa',
                                          padding: '2px 4px',
                                          borderRadius: '3px',
                                          fontSize: '0.9em',
                                          color: '#d73a49',
                                          fontFamily: 'SFMono-Regular, Consolas, "Liberation Mono", Menlo, monospace'
                                        }} {...props}>
                                          {children}
                                        </code>
                                      );
                                    }
                                  },
                                  pre: ({ children }) => children,
                                  ul: ({ children }) => <ul style={{ margin: '0.5em 0', paddingLeft: '1.5em' }}>{children}</ul>,
                                  li: ({ children }) => <li style={{ margin: '0.2em 0' }}>{children}</li>,
                                  blockquote: ({ children }) => (
                                    <blockquote style={{
                                      borderLeft: '4px solid #1890ff',
                                      paddingLeft: '1em',
                                      margin: '0.5em 0',
                                      fontStyle: 'italic',
                                      color: '#666',
                                      background: '#f9f9f9',
                                      borderRadius: '0 4px 4px 0'
                                    }}>{children}</blockquote>
                                  )
                                }}
                              >
                                {item.content}
                              </ReactMarkdown>
                            )}
                          </div>
                        ),
                        status: item.status
                      }))}
                    />
                  </div>
                )}



                {/* 等待状态 */}
                {!messages.length && (
                  <div style={{ textAlign: 'center', padding: '20px' }}>
                    <Text type="secondary">等待开始分析...</Text>
                  </div>
                )}
              </>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* 连接状态提示 */}
          {connectionStatus === 'error' && (
            <div style={{ marginTop: 16 }}>
              <Alert
                message="连接中断"
                description="实时连接已中断，请刷新页面重试"
                type="error"
                showIcon
                action={
                  <Button size="small" onClick={() => window.location.reload()}>
                    刷新页面
                  </Button>
                }
              />
            </div>
          )}
        </div>
      )}
    </Card>
  );
};

export default StreamingDisplay;
