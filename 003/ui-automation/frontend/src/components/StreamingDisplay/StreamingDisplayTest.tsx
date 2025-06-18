import React, { useState } from 'react';
import { Button, Card, Space } from 'antd';
import { PlayCircleOutlined, ReloadOutlined } from '@ant-design/icons';
import StreamingDisplay from './StreamingDisplay';
import { mockStreamingMessages, simulateStreamingData } from './test-data';

const StreamingDisplayTest: React.FC = () => {
  const [sessionId, setSessionId] = useState<string>('');
  const [isActive, setIsActive] = useState<boolean>(false);
  const [preserveContent, setPreserveContent] = useState<boolean>(false);

  const startTest = () => {
    const newSessionId = `test-session-${Date.now()}`;
    setSessionId(newSessionId);
    setIsActive(true);
    setPreserveContent(false);
    
    // 模拟流式数据
    simulateStreamingData(
      (message) => {
        console.log('模拟接收消息:', message);
      },
      () => {
        console.log('模拟流式数据完成');
        setIsActive(false);
        setPreserveContent(true);
      }
    );
  };

  const resetTest = () => {
    setSessionId('');
    setIsActive(false);
    setPreserveContent(false);
  };

  const handleAnalysisComplete = (result: any) => {
    console.log('分析完成:', result);
    setIsActive(false);
    setPreserveContent(true);
  };

  const handleError = (error: string) => {
    console.error('分析错误:', error);
    setIsActive(false);
    setPreserveContent(false);
  };

  return (
    <div style={{ padding: '24px', height: '100vh' }}>
      <Card 
        title="StreamingDisplay 显示顺序测试" 
        style={{ height: '100%' }}
        extra={
          <Space>
            <Button 
              type="primary" 
              icon={<PlayCircleOutlined />}
              onClick={startTest}
              disabled={isActive}
            >
              开始测试
            </Button>
            <Button 
              icon={<ReloadOutlined />}
              onClick={resetTest}
            >
              重置
            </Button>
          </Space>
        }
      >
        <div style={{ height: 'calc(100% - 60px)' }}>
          <StreamingDisplay
            sessionId={sessionId}
            isActive={isActive || preserveContent}
            onAnalysisComplete={handleAnalysisComplete}
            onError={handleError}
          />
        </div>
      </Card>
    </div>
  );
};

export default StreamingDisplayTest;
