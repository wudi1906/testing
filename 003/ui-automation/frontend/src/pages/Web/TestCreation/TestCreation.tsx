import React, { useMemo } from 'react';
import { useLocation, Navigate } from 'react-router-dom';
import WebModule from '../';
import {
  Card,
  Typography,
  Space,
  Tag
} from 'antd';
import {
  RobotOutlined,
  ThunderboltOutlined,
  GlobalOutlined
} from '@ant-design/icons';
import './TestCreation.css';

const { Title, Text } = Typography;

const TestCreation: React.FC = () => {
  const location = useLocation();

  // 检测当前平台并重定向到对应的模块
  const platform = useMemo(() => {
    const path = location.pathname;
    if (path.includes('/web/')) return 'web';
    if (path.includes('/android/')) return 'android';
    return 'general';
  }, [location.pathname]);

  // 如果是Web平台，使用新的Web模块
  if (platform === 'web') {
    return <WebModule />;
  }

  // 如果是Android平台，暂时重定向到Web（后续可以创建Android模块）
  if (platform === 'android') {
    return <Navigate to="/web/create" replace />;
  }

  // 通用平台的简单处理（显示平台选择页面）
  return (
    <div className="test-creation-container">
      <Card
        className="platform-selector"
        style={{
          maxWidth: 600,
          margin: '50px auto',
          textAlign: 'center'
        }}
      >
        <Space direction="vertical" size="large">
          <div>
            <ThunderboltOutlined style={{ fontSize: '48px', color: '#722ed1' }} />
            <Title level={2} style={{ margin: '16px 0', color: '#722ed1' }}>
              选择测试平台
            </Title>
            <Text type="secondary">
              请选择您要进行自动化测试的平台
            </Text>
          </div>
          
          <Space direction="vertical" size="middle" style={{ width: '100%' }}>
            <Card
              hoverable
              onClick={() => window.location.href = '/web/create'}
              style={{ cursor: 'pointer' }}
            >
              <Space>
                <GlobalOutlined style={{ fontSize: '24px', color: '#1890ff' }} />
                <div style={{ textAlign: 'left' }}>
                  <Title level={4} style={{ margin: 0, color: '#1890ff' }}>
                    Web平台
                  </Title>
                  <Text type="secondary">
                    Web应用UI自动化测试，支持图片分析和网页抓取
                  </Text>
                </div>
              </Space>
            </Card>
            
            <Card
              hoverable
              onClick={() => window.location.href = '/android/create'}
              style={{ cursor: 'pointer', opacity: 0.6 }}
            >
              <Space>
                <RobotOutlined style={{ fontSize: '24px', color: '#52c41a' }} />
                <div style={{ textAlign: 'left' }}>
                  <Title level={4} style={{ margin: 0, color: '#52c41a' }}>
                    Android平台
                  </Title>
                  <Text type="secondary">
                    Android应用UI自动化测试（开发中）
                  </Text>
                </div>
              </Space>
            </Card>
          </Space>
        </Space>
      </Card>
    </div>
  );
};

export default TestCreation;
