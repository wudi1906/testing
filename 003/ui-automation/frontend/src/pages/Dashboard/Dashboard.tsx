import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Typography, Button, Space, Tabs, Switch } from 'antd';
import {
  PlayCircleOutlined,
  CodeOutlined,
  FileTextOutlined,
  BarChartOutlined,
  RocketOutlined,
  CheckCircleOutlined,
  ThunderboltOutlined,
  ExperimentOutlined,
  MonitorOutlined,
  SettingOutlined,
  FullscreenOutlined
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';

// 导入新的组件
import SystemOverview from '../../components/Dashboard/SystemOverview';
import KnowledgeGraph from '../../components/Dashboard/KnowledgeGraph';
import AIAnalyticsDashboard from '../../components/Dashboard/AIAnalyticsDashboard';
import RealTimeMonitor from '../../components/Dashboard/RealTimeMonitor';

import '../../components/Dashboard/Dashboard.css';

const { Title, Paragraph, Text } = Typography;
const { TabPane } = Tabs;

const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('overview');
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);

  // 快速操作数据
  const quickActions = [
    {
      title: '多模态分析',
      description: '上传图片或输入URL进行AI智能分析，自动识别UI元素',
      icon: <ExperimentOutlined />,
      path: '/test/create',
      color: '#1890ff',
      gradient: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
    },
    {
      title: 'YAML脚本执行',
      description: '执行 YAML测试脚本，支持批量运行',
      icon: <PlayCircleOutlined />,
      path: '/test/execution',
      color: '#52c41a',
      gradient: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)'
    },
    {
      title: 'Playwright集成',
      description: '生成和执行Playwright测试代码，支持多浏览器',
      icon: <CodeOutlined />,
      path: '/test/create',
      color: '#722ed1',
      gradient: 'linear-gradient(135deg, #a8edea 0%, #fed6e3 100%)'
    },
    {
      title: '测试结果分析',
      description: '查看详细的测试执行结果和智能分析报告',
      icon: <BarChartOutlined />,
      path: '/test/results',
      color: '#fa8c16',
      gradient: 'linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%)'
    },
    {
      title: 'Android自动化',
      description: '移动端UI自动化测试，支持多设备适配',
      icon: <ThunderboltOutlined />,
      path: '/android/create',
      color: '#13c2c2',
      gradient: 'linear-gradient(135deg, #a8e6cf 0%, #dcedc1 100%)'
    },
    {
      title: '接口自动化',
      description: 'API接口自动化测试，支持复杂业务场景',
      icon: <CheckCircleOutlined />,
      path: '/api/create',
      color: '#eb2f96',
      gradient: 'linear-gradient(135deg, #fbc2eb 0%, #a6c1ee 100%)'
    }
  ];

  return (
    <div className="enhanced-dashboard">
      <div className="dashboard-content">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          {/* 欢迎区域 */}
          <div className="welcome-section">
            <Row align="middle" justify="space-between">
              <Col span={16}>
                <Title className="welcome-title">
                  <RocketOutlined style={{ marginRight: 12 }} />
                  但问智能自动化测试平台（100%自研）
                </Title>
                <Paragraph className="welcome-subtitle">
                  基于多模态AI与多智能体协作的下一代智能自动化测试系统
                </Paragraph>
              </Col>
              <Col span={8} style={{ textAlign: 'right' }}>
                <Space>
                  <Switch
                    checked={autoRefresh}
                    onChange={setAutoRefresh}
                    checkedChildren="自动刷新"
                    unCheckedChildren="手动刷新"
                  />
                  <Button
                    icon={<FullscreenOutlined />}
                    onClick={() => setIsFullscreen(!isFullscreen)}
                  >
                    {isFullscreen ? '退出全屏' : '全屏模式'}
                  </Button>
                  <Button
                    type="primary"
                    size="large"
                    icon={<PlayCircleOutlined />}
                    onClick={() => navigate('/test/create')}
                  >
                    开始测试
                  </Button>
                </Space>
              </Col>
            </Row>
          </div>

          {/* 快速操作面板 */}
          <div className="quick-actions-panel">
            <Title level={3} style={{ marginBottom: 24, color: '#333' }}>
              <ThunderboltOutlined style={{ marginRight: 8, color: '#1890ff' }} />
              快速操作中心
            </Title>
            <div className="action-grid">
              {quickActions.map((action, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, y: 30 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.6, delay: index * 0.1 }}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  className="action-item"
                  onClick={() => navigate(action.path)}
                >
                  <div
                    className="action-item-icon"
                    style={{
                      color: action.color,
                      background: action.gradient
                    }}
                  >
                    {action.icon}
                  </div>
                  <div className="action-item-title">{action.title}</div>
                  <div className="action-item-description">{action.description}</div>
                </motion.div>
              ))}
            </div>
          </div>

          {/* 主要内容区域 - 标签页 */}
          <Tabs
            activeKey={activeTab}
            onChange={setActiveTab}
            size="large"
            style={{ background: 'rgba(255, 255, 255, 0.95)', borderRadius: '16px', padding: '16px' }}
          >
            <TabPane
              tab={
                <span>
                  <BarChartOutlined />
                  系统概览
                </span>
              }
              key="overview"
            >
              <SystemOverview />
            </TabPane>

            <TabPane
              tab={
                <span>
                  <ExperimentOutlined />
                  AI分析
                </span>
              }
              key="ai-analytics"
            >
              <AIAnalyticsDashboard autoRefresh={autoRefresh} />
            </TabPane>

            <TabPane
              tab={
                <span>
                  <MonitorOutlined />
                  实时监控
                </span>
              }
              key="real-time"
            >
              <RealTimeMonitor autoRefresh={autoRefresh} />
            </TabPane>

            <TabPane
              tab={
                <span>
                  <CheckCircleOutlined />
                  知识图谱
                </span>
              }
              key="knowledge-graph"
            >
              <KnowledgeGraph width={1200} height={600} />
            </TabPane>
          </Tabs>

        </motion.div>
      </div>
    </div>
  );
};

export default Dashboard;
