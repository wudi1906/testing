/**
 * 测试用例解析组件
 * 支持根据用户编写的测试用例内容，智能分析并从数据库中获取相应的页面元素信息
 */
import React, { useState, useCallback, useRef, useEffect } from 'react';
import {
  Card,
  Button,
  Form,
  Input,
  Select,
  Space,
  Typography,
  message,
  Progress,
  Alert,
  Tag,
  Divider
} from 'antd';
import {
  RobotOutlined,
  PlayCircleOutlined,
  FileTextOutlined,
  BulbOutlined,
  ThunderboltOutlined
} from '@ant-design/icons';
import MDEditor from '@uiw/react-md-editor';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;
const { Option } = Select;

interface TestCaseParserProps {
  onParseComplete?: (result: any) => void;
  className?: string;
}

const TestCaseParser: React.FC<TestCaseParserProps> = ({ onParseComplete, className }) => {
  const [form] = Form.useForm();
  
  // 基础状态
  const [testCaseContent, setTestCaseContent] = useState<string>('');
  const [targetFormat, setTargetFormat] = useState<string>('yaml');
  const [isParsing, setIsParsing] = useState(false);
  
  // 解析状态
  const [parseProgress, setParseProgress] = useState(0);
  const [currentStep, setCurrentStep] = useState<string>('');
  const [parseLog, setParseLog] = useState<string>('');
  const [parseResult, setParseResult] = useState<any>(null);
  
  // SSE连接状态
  const [sessionId, setSessionId] = useState<string>('');
  const eventSourceRef = useRef<EventSource | null>(null);

  // 清理SSE连接
  const cleanupEventSource = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
  }, []);

  // 组件卸载时清理连接
  useEffect(() => {
    return () => {
      cleanupEventSource();
    };
  }, [cleanupEventSource]);

  // 处理测试用例解析
  const handleParseTestCase = useCallback(async () => {
    if (!testCaseContent.trim()) {
      message.error('请输入测试用例内容');
      return;
    }

    try {
      setIsParsing(true);
      setParseProgress(0);
      setCurrentStep('准备解析测试用例...');
      setParseLog('🔍 开始解析测试用例内容...\n');
      setParseResult(null);

      // 获取表单数据
      const formValues = form.getFieldsValue();
      
      // 创建FormData
      const formData = new FormData();
      formData.append('test_case_content', testCaseContent);
      formData.append('test_description', formValues.test_description || '');
      formData.append('target_format', targetFormat);
      formData.append('additional_context', formValues.additional_context || '');

      setCurrentStep('提交解析请求...');
      setParseProgress(10);

      // 调用后端API启动解析任务
      const response = await fetch('/api/v1/web/test-case-parser/parse', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const result = await response.json();
      
      if (result.status !== 'success') {
        throw new Error(result.message || '解析请求失败');
      }

      const newSessionId = result.session_id;
      setSessionId(newSessionId);
      setCurrentStep('连接解析流...');
      setParseProgress(20);

      // 建立SSE连接监听解析过程
      const sseUrl = result.sse_endpoint;
      const eventSource = new EventSource(sseUrl);
      eventSourceRef.current = eventSource;

      eventSource.onopen = () => {
        setCurrentStep('已连接到解析流');
        setParseProgress(30);
      };

      eventSource.addEventListener('connected', (event) => {
        const data = JSON.parse(event.data);
        setParseLog(prev => prev + `✅ ${data.message}\n`);
        setParseProgress(40);
      });

      eventSource.addEventListener('message', (event) => {
        const data = JSON.parse(event.data);
        setParseLog(prev => prev + `📝 ${data.content}\n`);
        setCurrentStep(data.content);
        
        // 根据消息内容更新进度
        if (data.content.includes('开始分析')) {
          setParseProgress(50);
        } else if (data.content.includes('查询数据库')) {
          setParseProgress(70);
        } else if (data.content.includes('整理')) {
          setParseProgress(85);
        }
      });

      eventSource.addEventListener('final_result', (event) => {
        const data = JSON.parse(event.data);
        setParseLog(prev => prev + `🎉 ${data.content}\n`);
        setCurrentStep('解析完成');
        setParseProgress(100);
        
        // 获取解析结果
        fetchParseResult(newSessionId);
        
        cleanupEventSource();
        setIsParsing(false);
      });

      eventSource.addEventListener('error', (event) => {
        const data = JSON.parse(event.data);
        setParseLog(prev => prev + `❌ 错误: ${data.message || data.error}\n`);
        setCurrentStep('解析失败');
        
        cleanupEventSource();
        setIsParsing(false);
        message.error(`解析失败: ${data.message || data.error}`);
      });

      eventSource.onerror = (error) => {
        console.error('SSE连接错误:', error);
        setParseLog(prev => prev + '❌ 连接中断\n');
        setCurrentStep('连接中断');
        
        cleanupEventSource();
        setIsParsing(false);
        message.error('连接中断，请重试');
      };

    } catch (error: any) {
      console.error('解析测试用例失败:', error);
      setParseLog(prev => prev + `❌ 解析失败: ${error.message}\n`);
      setCurrentStep('解析失败');
      setIsParsing(false);
      message.error(`解析失败: ${error.message}`);
    }
  }, [testCaseContent, targetFormat, form, cleanupEventSource]);

  // 获取解析结果
  const fetchParseResult = useCallback(async (sessionId: string) => {
    try {
      const response = await fetch(`/api/v1/web/test-case-parser/status/${sessionId}`);
      if (response.ok) {
        const result = await response.json();
        if (result.success && result.data) {
          setParseResult(result.data);
          onParseComplete?.(result.data);
        }
      }
    } catch (error) {
      console.error('获取解析结果失败:', error);
    }
  }, [onParseComplete]);

  // 清空内容
  const handleClear = useCallback(() => {
    setTestCaseContent('');
    setParseLog('');
    setParseResult(null);
    setParseProgress(0);
    setCurrentStep('');
    form.resetFields();
    cleanupEventSource();
  }, [form, cleanupEventSource]);

  // 使用示例
  const handleUseExample = useCallback(() => {
    const exampleContent = `测试场景：电商网站商品搜索功能测试

测试步骤：
1. 打开电商网站首页
2. 在搜索框中输入商品关键词 "iPhone 15"
3. 点击搜索按钮
4. 验证搜索结果页面是否正确显示
5. 点击第一个商品进入详情页
6. 检查商品详情信息是否完整
7. 点击"加入购物车"按钮
8. 验证购物车图标是否显示商品数量

预期结果：
- 搜索结果页面显示相关商品列表
- 商品详情页面显示完整的商品信息
- 成功添加商品到购物车`;

    setTestCaseContent(exampleContent);
    form.setFieldsValue({
      test_description: '电商网站商品搜索功能的完整测试流程',
      additional_context: '这是一个标准的电商网站功能测试用例'
    });
  }, [form]);

  return (
    <div className={className}>
      <Card
        title={
          <Space>
            <RobotOutlined style={{ color: '#722ed1' }} />
            <span>测试用例元素解析</span>
            <Tag color="purple">智能解析</Tag>
          </Space>
        }
        extra={
          <Space>
            <Button 
              icon={<BulbOutlined />} 
              onClick={handleUseExample}
              disabled={isParsing}
            >
              使用示例
            </Button>
            <Button 
              icon={<FileTextOutlined />} 
              onClick={handleClear}
              disabled={isParsing}
            >
              清空
            </Button>
          </Space>
        }
      >
        <Form form={form} layout="vertical">
          <Form.Item
            label="测试用例内容"
            name="test_case_content"
            required
            rules={[{ required: true, message: '请输入测试用例内容' }]}
          >
            <TextArea
              value={testCaseContent}
              onChange={(e) => setTestCaseContent(e.target.value)}
              placeholder="请输入您的测试用例内容，例如：

测试场景：用户登录功能测试

步骤：
1. 打开登录页面
2. 在用户名输入框中输入用户名
3. 在密码输入框中输入密码
4. 点击登录按钮
5. 验证登录结果

预期结果：
- 登录成功后跳转到首页
- 显示用户欢迎信息"
              rows={12}
              disabled={isParsing}
            />
          </Form.Item>

          <Form.Item label="测试描述" name="test_description">
            <Input 
              placeholder="简要描述测试目的（可选）"
              disabled={isParsing}
            />
          </Form.Item>

          <Form.Item label="目标格式" name="target_format">
            <Select
              value={targetFormat}
              onChange={setTargetFormat}
              disabled={isParsing}
            >
              <Option value="yaml">YAML (MidScene.js)</Option>
              <Option value="playwright">Playwright (TypeScript)</Option>
            </Select>
          </Form.Item>

          <Form.Item label="额外上下文" name="additional_context">
            <Input 
              placeholder="提供额外的上下文信息（可选）"
              disabled={isParsing}
            />
          </Form.Item>

          <Form.Item>
            <Space>
              <Button
                type="primary"
                icon={<PlayCircleOutlined />}
                onClick={handleParseTestCase}
                loading={isParsing}
                disabled={!testCaseContent.trim()}
                size="large"
              >
                {isParsing ? '解析中...' : '开始解析'}
              </Button>
              
              {isParsing && (
                <div style={{ flex: 1, minWidth: 200 }}>
                  <Progress 
                    percent={parseProgress} 
                    size="small" 
                    status={parseProgress === 100 ? 'success' : 'active'}
                  />
                  <Text type="secondary" style={{ fontSize: '12px' }}>
                    {currentStep}
                  </Text>
                </div>
              )}
            </Space>
          </Form.Item>
        </Form>

        {/* 解析日志 */}
        {parseLog && (
          <>
            <Divider>解析日志</Divider>
            <Card size="small" style={{ backgroundColor: '#f6f8fa' }}>
              <pre style={{ 
                margin: 0, 
                fontSize: '12px', 
                lineHeight: '1.4',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word'
              }}>
                {parseLog}
              </pre>
            </Card>
          </>
        )}

        {/* 解析结果 */}
        {parseResult && (
          <>
            <Divider>解析结果</Divider>
            <Alert
              message="解析完成"
              description={
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Text>会话ID: {parseResult.session_id}</Text>
                  <Text>状态: <Tag color="green">{parseResult.status}</Tag></Text>
                  <Text>进度: {parseResult.progress}%</Text>
                  <Text>目标格式: <Tag color="blue">{parseResult.test_case_info?.target_format}</Tag></Text>
                  <Text>内容长度: {parseResult.test_case_info?.content_length} 字符</Text>
                </Space>
              }
              type="success"
              showIcon
            />
          </>
        )}
      </Card>
    </div>
  );
};

export default TestCaseParser;
