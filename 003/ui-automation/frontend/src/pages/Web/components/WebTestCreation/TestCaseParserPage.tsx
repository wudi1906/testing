/**
 * 独立的测试用例解析页面
 * 专门用于测试用例元素解析功能
 */
import React, { useState, useCallback } from 'react';
import {
  Card,
  Row,
  Col,
  Button,
  Space,
  Typography,
  message,
  Alert,
  Divider,
  Statistic,
  Tag
} from 'antd';
import {
  RobotOutlined,
  ThunderboltOutlined,
  HeartOutlined,
  ReloadOutlined,
  BugOutlined,
  ArrowLeftOutlined
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import TestCaseParser from './TestCaseParser';
import {
  checkTestCaseParserHealth,
  testTestCaseParserAgent,
  getActiveTestCaseParseSessions
} from '../../../../services/api';
import './TestCaseParser.css';

const { Title, Text, Paragraph } = Typography;

const TestCaseParserPage: React.FC = () => {
  const navigate = useNavigate();
  
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
    <div style={{ padding: '20px', minHeight: '100vh', background: '#f5f5f5' }}>
      {/* 页面标题 */}
      <Card style={{ marginBottom: 20 }}>
        <Row justify="space-between" align="middle">
          <Col>
            <Space size="large">
              <Button 
                icon={<ArrowLeftOutlined />} 
                onClick={() => navigate('/web/create')}
              >
                返回
              </Button>
              <div>
                <Title level={2} style={{ margin: 0 }}>
                  <Space>
                    <ThunderboltOutlined style={{ color: '#722ed1' }} />
                    测试用例元素解析
                    <Tag color="purple">智能解析</Tag>
                  </Space>
                </Title>
                <Text type="secondary">
                  根据测试用例内容智能分析并从数据库中获取相应的页面元素信息
                </Text>
              </div>
            </Space>
          </Col>
          <Col>
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
          </Col>
        </Row>
      </Card>

      <Row gutter={[20, 20]}>
        {/* 左侧：测试用例解析 */}
        <Col xs={24} lg={16}>
          <TestCaseParser 
            onParseComplete={handleParseComplete}
            className="test-case-parser-page"
          />
        </Col>

        {/* 右侧：状态监控 */}
        <Col xs={24} lg={8}>
          {/* 服务状态 */}
          <Card 
            title={
              <Space>
                <HeartOutlined style={{ color: '#52c41a' }} />
                <span>服务状态</span>
              </Space>
            }
            style={{ marginBottom: 20 }}
          >
            <Row gutter={[16, 16]}>
              <Col span={12}>
                <Statistic
                  title="服务状态"
                  value={healthStatus?.status || '未知'}
                  valueStyle={{ 
                    color: healthStatus?.status === 'ok' ? '#3f8600' : '#cf1322' 
                  }}
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title="活跃会话"
                  value={activeSessions?.data?.total_sessions || 0}
                  valueStyle={{ color: '#1890ff' }}
                />
              </Col>
            </Row>
            {healthStatus && (
              <div style={{ marginTop: 16 }}>
                <Text type="secondary" style={{ fontSize: '12px' }}>
                  最后检查: {new Date(healthStatus.timestamp).toLocaleString()}
                </Text>
              </div>
            )}
          </Card>

          {/* 活跃会话详情 */}
          {activeSessions && activeSessions.data.sessions.length > 0 && (
            <Card 
              title={
                <Space>
                  <RobotOutlined style={{ color: '#1890ff' }} />
                  <span>活跃会话</span>
                </Space>
              }
              style={{ marginBottom: 20 }}
            >
              <Space direction="vertical" style={{ width: '100%' }}>
                {activeSessions.data.sessions.map((session: any, index: number) => (
                  <Card size="small" key={session.session_id}>
                    <Space direction="vertical" style={{ width: '100%' }}>
                      <div>
                        <Text strong>会话 {index + 1}</Text>
                        <Tag color="blue" style={{ marginLeft: 8 }}>
                          {session.status}
                        </Tag>
                      </div>
                      <Text><strong>ID:</strong> {session.session_id.substring(0, 8)}...</Text>
                      <Text><strong>进度:</strong> {session.progress}%</Text>
                      <Text><strong>格式:</strong> <Tag color="green">{session.target_format}</Tag></Text>
                      <Text><strong>创建:</strong> {new Date(session.created_at).toLocaleString()}</Text>
                    </Space>
                  </Card>
                ))}
              </Space>
            </Card>
          )}

          {/* 使用说明 */}
          <Card 
            title={
              <Space>
                <BugOutlined style={{ color: '#faad14' }} />
                <span>使用说明</span>
              </Space>
            }
          >
            <Alert
              message="功能说明"
              description={
                <div>
                  <Paragraph style={{ marginBottom: 8 }}>
                    <strong>1. 健康检查</strong>: 检查解析服务状态
                  </Paragraph>
                  <Paragraph style={{ marginBottom: 8 }}>
                    <strong>2. 测试智能体</strong>: 使用预设测试用例
                  </Paragraph>
                  <Paragraph style={{ marginBottom: 8 }}>
                    <strong>3. 手动解析</strong>: 输入自定义测试用例
                  </Paragraph>
                  <Paragraph style={{ marginBottom: 0 }}>
                    <strong>4. 实时监控</strong>: SSE流式查看解析过程
                  </Paragraph>
                </div>
              }
              type="info"
              showIcon
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default TestCaseParserPage;
