/**
 * 测试组件 - 用于验证前后端集成优化后的组件是否正常工作
 */
import React from 'react';
import { Card, Button, Space, message, Alert, Divider } from 'antd';
import { PlayCircleOutlined, BugOutlined, DatabaseOutlined, FolderOutlined } from '@ant-design/icons';

// 测试导入优化后的组件
import ScriptManagementTab from './components/ScriptManagementTab';
import QuickExecutionTab from './components/QuickExecutionTab';
import ExecutionStatusPanel from './components/ExecutionStatusPanel';

const TestComponents: React.FC = () => {
  const [sessionId, setSessionId] = React.useState<string | null>(null);

  const handleExecutionStart = (sessionId: string, scriptName?: string) => {
    console.log('执行开始:', sessionId, scriptName);
    setSessionId(sessionId);
    message.success(`模拟执行开始: ${scriptName || '脚本'}`);
  };

  const handleBatchExecutionStart = (sessionId: string, scriptNames: string[]) => {
    console.log('批量执行开始:', sessionId, scriptNames);
    setSessionId(sessionId);
    message.success(`模拟批量执行开始: ${scriptNames.length}个脚本`);
  };

  const handleSessionEnd = () => {
    console.log('会话结束');
    setSessionId(null);
    message.info('模拟会话结束');
  };

  return (
    <div style={{ padding: 24 }}>
      <Alert
        message="前后端集成测试页面"
        description="此页面用于测试优化后的脚本管理和执行功能，包括数据库脚本管理和文件系统脚本执行的集成。"
        type="info"
        showIcon
        style={{ marginBottom: 24 }}
      />

      <Card title="功能测试控制台" style={{ marginBottom: 24 }}>
        <Space wrap>
          <Button
            type="primary"
            icon={<DatabaseOutlined />}
            onClick={() => handleExecutionStart('db-session-001', 'database-script.yaml')}
          >
            模拟数据库脚本执行
          </Button>
          <Button
            type="primary"
            icon={<FolderOutlined />}
            onClick={() => handleExecutionStart('fs-session-001', 'test.spec.ts')}
          >
            模拟文件系统脚本执行
          </Button>
          <Button
            icon={<BugOutlined />}
            onClick={() => handleBatchExecutionStart('batch-session-002', ['test1.spec.ts', 'test2.spec.ts', 'test3.spec.ts'])}
          >
            模拟批量执行
          </Button>
          <Button
            onClick={() => handleSessionEnd()}
          >
            结束会话
          </Button>
        </Space>

        <Divider />

        <div style={{ fontSize: 12, color: '#666' }}>
          <p><strong>测试说明：</strong></p>
          <ul>
            <li>点击"模拟数据库脚本执行"测试数据库脚本管理功能</li>
            <li>点击"模拟文件系统脚本执行"测试文件系统脚本执行功能</li>
            <li>点击"模拟批量执行"测试批量执行功能</li>
            <li>右侧执行状态面板会显示实时执行状态（模拟）</li>
          </ul>
        </div>
      </Card>

      <div style={{ display: 'flex', gap: 24 }}>
        <div style={{ flex: 1 }}>
          <Card title="脚本管理标签测试" style={{ marginBottom: 24 }}>
            <ScriptManagementTab
              onExecutionStart={handleExecutionStart}
              onBatchExecutionStart={handleBatchExecutionStart}
            />
          </Card>

          <Card title="快速执行标签测试">
            <QuickExecutionTab
              onExecutionStart={handleExecutionStart}
            />
          </Card>
        </div>

        <div style={{ width: 400 }}>
          <Card title="执行状态面板测试">
            <ExecutionStatusPanel
              sessionId={sessionId}
              onSessionEnd={handleSessionEnd}
            />
          </Card>
        </div>
      </div>
    </div>
  );
};

export default TestComponents;
