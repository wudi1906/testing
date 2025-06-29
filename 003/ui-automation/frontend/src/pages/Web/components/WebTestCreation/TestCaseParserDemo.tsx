/**
 * 测试用例解析演示页面
 * 用于测试和演示测试用例解析功能
 */
import React, { useState, useCallback } from 'react';
import {
  Card,
  Button,
  Space,
  Typography,
  message,
  Alert,
  Divider,
  Row,
  Col,
  Statistic,
  Tag
} from 'antd';
import {
  RobotOutlined,
  PlayCircleOutlined,
  HeartOutlined,
  ReloadOutlined,
  BugOutlined
} from '@ant-design/icons';
import TestCaseParser from './TestCaseParser';
import {
  checkTestCaseParserHealth,
  testTestCaseParserAgent,
  getActiveTestCaseParseSessions
} from '../../../../services/api';

const { Title, Text, Paragraph } = Typography;

const TestCaseParserDemo: React.FC = () => {
  const [healthStatus, setHealthStatus] = useState<any>(null);
  const [activeSessions, setActiveSessions] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);

  // 健康检查
  const handleHealthCheck = useCallback(async () => {
    try {
      setIsLoading(true);
      const health = await checkTestCaseParserHealth();
      setHealthStatus(health);
      message.success('健康检查完成');
    } catch (error: any) {
      console.error('健康检查失败:', error);
      message.error(`健康检查失败: ${error.message}`);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // 获取活跃会话
  const handleGetActiveSessions = useCallback(async () => {
    try {
      setIsLoading(true);
      const sessions = await getActiveTestCaseParseSessions();
      setActiveSessions(sessions);
      message.success('获取活跃会话成功');
    } catch (error: any) {
      console.error('获取活跃会话失败:', error);
      message.error(`获取活跃会话失败: ${error.message}`);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // 测试智能体
  const handleTestAgent = useCallback(async () => {
    try {
      setIsLoading(true);
      const result = await testTestCaseParserAgent();
      message.success('测试智能体请求已发送');
      console.log('测试结果:', result);
      
      // 自动获取活跃会话
      setTimeout(() => {
        handleGetActiveSessions();
      }, 1000);
    } catch (error: any) {
      console.error('测试智能体失败:', error);
      message.error(`测试智能体失败: ${error.message}`);
    } finally {
      setIsLoading(false);
    }
  }, [handleGetActiveSessions]);

  // 解析完成回调
  const handleParseComplete = useCallback((result: any) => {
    console.log('解析完成:', result);
    message.success('测试用例解析完成');
    
    // 自动刷新活跃会话
    setTimeout(() => {
      handleGetActiveSessions();
    }, 1000);
  }, [handleGetActiveSessions]);

  return (
    <div style={{ padding: '20px' }}>
      <Card
        title={
          <Space>
            <RobotOutlined style={{ color: '#722ed1' }} />
            <span>测试用例解析演示</span>
            <Tag color="purple">Demo</Tag>
          </Space>
        }
        extra={
          <Space>
            <Button
              icon={<HeartOutlined />}
              onClick={handleHealthCheck}
              loading={isLoading}
            >
              健康检查
            </Button>
            <Button 
              icon={<ReloadOutlined />} 
              onClick={handleGetActiveSessions}
              loading={isLoading}
            >
              刷新会话
            </Button>
            <Button 
              icon={<BugOutlined />} 
              onClick={handleTestAgent}
              loading={isLoading}
              type="primary"
            >
              测试智能体
            </Button>
          </Space>
        }
      >
        {/* 状态信息 */}
        <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
          <Col span={8}>
            <Card size="small">
              <Statistic
                title="服务状态"
                value={healthStatus?.status || '未知'}
                valueStyle={{ 
                  color: healthStatus?.status === 'ok' ? '#3f8600' : '#cf1322' 
                }}
                prefix={<HeartOutlined />}
              />
              {healthStatus && (
                <Text type="secondary" style={{ fontSize: '12px' }}>
                  {healthStatus.timestamp}
                </Text>
              )}
            </Card>
          </Col>
          <Col span={8}>
            <Card size="small">
              <Statistic
                title="活跃会话"
                value={activeSessions?.data?.total_sessions || 0}
                valueStyle={{ color: '#1890ff' }}
                prefix={<PlayCircleOutlined />}
              />
            </Card>
          </Col>
          <Col span={8}>
            <Card size="small">
              <Statistic
                title="服务类型"
                value="test-case-parser"
                valueStyle={{ color: '#722ed1' }}
                prefix={<RobotOutlined />}
              />
            </Card>
          </Col>
        </Row>

        {/* 活跃会话详情 */}
        {activeSessions && activeSessions.data.sessions.length > 0 && (
          <>
            <Divider>活跃会话详情</Divider>
            <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
              {activeSessions.data.sessions.map((session: any, index: number) => (
                <Col span={12} key={session.session_id}>
                  <Card size="small" title={`会话 ${index + 1}`}>
                    <Space direction="vertical" style={{ width: '100%' }}>
                      <Text><strong>ID:</strong> {session.session_id.substring(0, 8)}...</Text>
                      <Text><strong>状态:</strong> <Tag color="blue">{session.status}</Tag></Text>
                      <Text><strong>进度:</strong> {session.progress}%</Text>
                      <Text><strong>格式:</strong> <Tag color="green">{session.target_format}</Tag></Text>
                      <Text><strong>创建时间:</strong> {new Date(session.created_at).toLocaleString()}</Text>
                    </Space>
                  </Card>
                </Col>
              ))}
            </Row>
          </>
        )}

        <Divider>测试用例解析功能</Divider>
        
        {/* 使用说明 */}
        <Alert
          message="使用说明"
          description={
            <div>
              <Paragraph>
                1. <strong>健康检查</strong>: 检查测试用例解析服务是否正常运行
              </Paragraph>
              <Paragraph>
                2. <strong>测试智能体</strong>: 使用预设的测试用例测试解析功能
              </Paragraph>
              <Paragraph>
                3. <strong>手动测试</strong>: 在下方输入框中编写自己的测试用例进行解析
              </Paragraph>
              <Paragraph>
                4. <strong>实时监控</strong>: 通过SSE连接实时查看解析过程和结果
              </Paragraph>
            </div>
          }
          type="info"
          showIcon
          style={{ marginBottom: 24 }}
        />

        {/* 测试用例解析组件 */}
        <TestCaseParser 
          onParseComplete={handleParseComplete}
          className="test-case-parser-demo"
        />
      </Card>
    </div>
  );
};

export default TestCaseParserDemo;
