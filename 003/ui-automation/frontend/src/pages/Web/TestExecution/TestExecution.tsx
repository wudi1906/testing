import React, { useState, useEffect, useRef } from 'react';
import {
  Card,
  Button,
  Space,
  Typography,
  Row,
  Col,
  Tabs,
  message,
  Badge,
  Tooltip
} from 'antd';
import {
  PlayCircleOutlined,
  BugOutlined,
  ThunderboltOutlined,
  AppstoreOutlined,
  EyeOutlined,
  SettingOutlined
} from '@ant-design/icons';
import { motion } from 'framer-motion';
import toast from 'react-hot-toast';

// 导入新的组件
import ScriptManagementTab from './components/ScriptManagementTab';
import QuickExecutionTab from './components/QuickExecutionTab';
import ExecutionStatusPanel from './components/ExecutionStatusPanel';
import './TestExecution.css';

const { TabPane } = Tabs;
const { Title, Text } = Typography;

const TestExecution: React.FC = () => {
  const [activeTab, setActiveTab] = useState('scripts');
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [currentScriptName, setCurrentScriptName] = useState<string | null>(null);
  const [showStatusPanel, setShowStatusPanel] = useState(false);
  const [executionCount, setExecutionCount] = useState(0);

  // 处理执行开始
  const handleExecutionStart = (sessionId: string, scriptName?: string) => {
    setCurrentSessionId(sessionId);
    setCurrentScriptName(scriptName || null);
    setShowStatusPanel(true);
    setExecutionCount(prev => prev + 1);

    toast.success(`执行已启动: ${scriptName || '脚本'}`);
    message.success(`会话ID: ${sessionId}`);
  };

  // 处理批量执行开始
  const handleBatchExecutionStart = (sessionId: string, scriptNames: string[]) => {
    setCurrentSessionId(sessionId);
    setCurrentScriptName(`批量执行 (${scriptNames.length}个脚本)`);
    setShowStatusPanel(true);
    setExecutionCount(prev => prev + 1);

    toast.success(`批量执行已启动: ${scriptNames.length}个脚本`);
    message.success(`会话ID: ${sessionId}`);
  };

  // 处理会话结束
  const handleSessionEnd = () => {
    setCurrentSessionId(null);
    setCurrentScriptName(null);
    toast.info('执行会话已结束');
  };





  return (
    <div className="test-execution-container">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <Row gutter={24}>
          <Col span={showStatusPanel ? 16 : 24}>
            <Card className="main-card">
              {/* 顶部操作栏 */}
              <div style={{
                marginBottom: 16,
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
              }}>
                <Title level={4} style={{ margin: 0 }}>
                  脚本执行管理
                  {currentSessionId && (
                    <Badge
                      count={executionCount}
                      style={{ marginLeft: 8 }}
                      showZero={false}
                    />
                  )}
                </Title>
                <Space>
                  <Tooltip title="显示/隐藏执行状态面板">
                    <Button
                      type={showStatusPanel ? "primary" : "default"}
                      icon={<EyeOutlined />}
                      onClick={() => setShowStatusPanel(!showStatusPanel)}
                    >
                      {showStatusPanel ? '隐藏' : '显示'}执行状态
                    </Button>
                  </Tooltip>
                  {currentSessionId && (
                    <Tooltip title={`当前会话: ${currentSessionId}`}>
                      <Button
                        type="dashed"
                        size="small"
                        icon={<BugOutlined />}
                      >
                        {currentScriptName || '执行中'}
                      </Button>
                    </Tooltip>
                  )}
                </Space>
              </div>

              {/* 主要标签页 */}
              <Tabs activeKey={activeTab} onChange={setActiveTab} size="large">
                <TabPane
                  tab={
                    <span>
                      <AppstoreOutlined />
                      脚本管理
                    </span>
                  }
                  key="scripts"
                >
                  <ScriptManagementTab
                    onExecutionStart={handleExecutionStart}
                    onBatchExecutionStart={handleBatchExecutionStart}
                  />
                </TabPane>

                <TabPane
                  tab={
                    <span>
                      <ThunderboltOutlined />
                      快速执行
                    </span>
                  }
                  key="quick"
                >
                  <QuickExecutionTab
                    onExecutionStart={handleExecutionStart}
                  />
                </TabPane>
              </Tabs>
            </Card>
          </Col>

          {/* 右侧执行状态面板 */}
          {showStatusPanel && (
            <Col span={8}>
              <motion.div
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 20 }}
                transition={{ duration: 0.3 }}
              >
                <ExecutionStatusPanel
                  sessionId={currentSessionId}
                  onSessionEnd={handleSessionEnd}
                />
              </motion.div>
            </Col>
          )}
        </Row>
      </motion.div>
    </div>
  );
};

export default TestExecution;
