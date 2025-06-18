/**
 * 统一测试执行页面
 * 基于脚本ID的前后端数据传输逻辑
 * 支持数据库脚本和文件系统脚本的统一管理和执行
 */
import React, { useState, useCallback, useEffect } from 'react';
import { Row, Col, Card, Typography, Space, Button, Tabs } from 'antd';
import { ReloadOutlined, EyeOutlined, EyeInvisibleOutlined } from '@ant-design/icons';
import { toast } from 'react-hot-toast';

import UnifiedScriptManagement from './components/UnifiedScriptManagement';
import UnifiedExecutionStatusPanel from './components/UnifiedExecutionStatusPanel';
import QuickExecutionTab from './components/QuickExecutionTab';

const { Title, Text } = Typography;

interface UnifiedTestExecutionProps {
  // 可以添加一些全局配置属性
}

const UnifiedTestExecution: React.FC<UnifiedTestExecutionProps> = () => {
  // 状态管理
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [currentScriptName, setCurrentScriptName] = useState<string | null>(null);
  const [executionCount, setExecutionCount] = useState(0);
  const [showStatusPanel, setShowStatusPanel] = useState(false);
  const [activeTab, setActiveTab] = useState('script-management');

  // 处理单脚本执行开始
  const handleExecutionStart = useCallback((sessionId: string, scriptName?: string) => {
    setCurrentSessionId(sessionId);
    setCurrentScriptName(scriptName || null);
    setShowStatusPanel(true);
    setExecutionCount(prev => prev + 1);
    
    toast.success(`开始执行: ${scriptName || sessionId}`);
  }, []);

  // 处理批量执行开始
  const handleBatchExecutionStart = useCallback((sessionId: string, scriptNames: string[]) => {
    setCurrentSessionId(sessionId);
    setCurrentScriptName(`批量执行 (${scriptNames.length}个脚本)`);
    setShowStatusPanel(true);
    setExecutionCount(prev => prev + 1);
    
    toast.success(`开始批量执行: ${scriptNames.length}个脚本`);
  }, []);

  // 处理会话结束
  const handleSessionEnd = useCallback(() => {
    // 保持状态面板显示，但可以开始新的执行
    toast.info('执行会话已结束');
  }, []);

  // 安全刷新页面
  const handleRefresh = () => {
    // 先清理当前会话
    setCurrentSessionId('');
    setCurrentScriptName('');

    // 等待一小段时间确保状态清理完成
    setTimeout(() => {
      window.location.reload();
    }, 100);
  };

  // 切换状态面板显示
  const toggleStatusPanel = () => {
    setShowStatusPanel(prev => !prev);
  };

  // 页面卸载时清理资源
  useEffect(() => {
    const handleBeforeUnload = (event: BeforeUnloadEvent) => {
      // 如果有活动会话，提示用户
      if (currentSessionId) {
        event.preventDefault();
        event.returnValue = '有脚本正在执行中，确定要离开页面吗？';
        return '有脚本正在执行中，确定要离开页面吗？';
      }
    };

    const handleUnload = () => {
      // 页面卸载时清理会话
      if (currentSessionId) {
        console.log('页面卸载，清理会话:', currentSessionId);
        // 发送停止请求（使用 navigator.sendBeacon 确保请求能发送）
        try {
          navigator.sendBeacon(`/api/v1/web/execution/sessions/${currentSessionId}/stop`);
        } catch (error) {
          console.error('停止会话失败:', error);
        }
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    window.addEventListener('unload', handleUnload);

    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
      window.removeEventListener('unload', handleUnload);
    };
  }, [currentSessionId]);

  return (
    <div style={{ padding: '24px', height: '100vh', overflow: 'hidden' }}>
      {/* 页面标题 */}
      <div style={{ marginBottom: 24 }}>
        <Space align="center" style={{ width: '100%', justifyContent: 'space-between' }}>
          <Space>
            <Title level={3} style={{ margin: 0 }}>
              Web自动化执行引擎
            </Title>
            <Text type="secondary">
              基于多模态大模型驱动
            </Text>
          </Space>
          <Space>
            <Text type="secondary">
              执行次数: {executionCount}
            </Text>
            <Button
              icon={showStatusPanel ? <EyeInvisibleOutlined /> : <EyeOutlined />}
              onClick={toggleStatusPanel}
              type={showStatusPanel ? "default" : "primary"}
            >
              {showStatusPanel ? '隐藏状态面板' : '显示状态面板'}
            </Button>
            <Button
              icon={<ReloadOutlined />}
              onClick={handleRefresh}
            >
              刷新页面
            </Button>
          </Space>
        </Space>
      </div>

      {/* 主要内容区域 */}
      <Row gutter={24} style={{ height: 'calc(100vh - 140px)' }}>
        {/* 左侧：脚本管理和快速执行 */}
        <Col span={showStatusPanel ? 14 : 24}>
          <Card
            style={{ height: '100%' }}
            bodyStyle={{ height: 'calc(100% - 57px)', padding: 0 }}
          >
            <Tabs
              activeKey={activeTab}
              onChange={setActiveTab}
              style={{
                height: '100%',
                paddingLeft: '16px' // 添加左侧内边距，使标签页标题不会太靠左
              }}
              tabBarStyle={{
                paddingLeft: '8px', // 标签栏左侧内边距
                marginBottom: 0
              }}
              items={[
                {
                  key: 'script-management',
                  label: '脚本管理',
                  children: (
                    <div style={{ height: 'calc(100vh - 220px)', overflow: 'auto', padding: 16 }}>
                      <UnifiedScriptManagement
                        onExecutionStart={handleExecutionStart}
                        onBatchExecutionStart={handleBatchExecutionStart}
                      />
                    </div>
                  )
                },
                {
                  key: 'quick-execution',
                  label: '快速执行',
                  children: (
                    <div style={{ height: 'calc(100vh - 220px)', overflow: 'auto', padding: 16 }}>
                      <QuickExecutionTab
                        onExecutionStart={handleExecutionStart}
                      />
                    </div>
                  )
                }
              ]}
            />
          </Card>
        </Col>

        {/* 右侧：执行状态面板 */}
        {showStatusPanel && (
          <Col span={10}>
            <UnifiedExecutionStatusPanel
              sessionId={currentSessionId}
              scriptName={currentScriptName}
              onSessionEnd={handleSessionEnd}
            />
          </Col>
        )}
      </Row>

      {/* 底部状态栏 */}
      <div style={{
        position: 'fixed',
        bottom: 0,
        left: 0,
        right: 0,
        height: 40,
        backgroundColor: '#f0f2f5',
        borderTop: '1px solid #d9d9d9',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 24px',
        zIndex: 1000
      }}>
        <Space>
          <Text type="secondary" style={{ fontSize: 12 }}>
            统一脚本执行系统 v1.0
          </Text>
          {currentSessionId && (
            <Text type="secondary" style={{ fontSize: 12 }}>
              当前会话: {currentSessionId.slice(-8)}
            </Text>
          )}
        </Space>
        <Space>
          <Text type="secondary" style={{ fontSize: 12 }}>
            状态: {showStatusPanel ? '执行中' : '就绪'}
          </Text>
          <div style={{
            width: 8,
            height: 8,
            borderRadius: '50%',
            backgroundColor: showStatusPanel ? '#52c41a' : '#d9d9d9'
          }} />
        </Space>
      </div>
    </div>
  );
};

export default UnifiedTestExecution;
