import React, { useState } from 'react';
import {
  Card,
  Tabs,
  Typography,
  Tag,
  List,
  Collapse,
  Space,
  Button,
  Tooltip,
  Badge,
  Row,
  Col,
  Descriptions
} from 'antd';
import {
  CodeOutlined,
  EyeOutlined,
  PlayCircleOutlined,
  InfoCircleOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined
} from '@ant-design/icons';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { tomorrow } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { motion } from 'framer-motion';

import './YAMLViewer.css';

const { TabPane } = Tabs;
const { Title, Text, Paragraph } = Typography;
const { Panel } = Collapse;

interface YAMLViewerProps {
  yamlContent: string;
  analysisResult?: any;
}

const YAMLViewer: React.FC<YAMLViewerProps> = ({ yamlContent, analysisResult }) => {
  const [activeTab, setActiveTab] = useState('yaml');

  const getActionTypeColor = (actionType: string) => {
    const colorMap: { [key: string]: string } = {
      'ai': 'blue',
      'aiTap': 'green',
      'aiInput': 'orange',
      'aiHover': 'purple',
      'aiScroll': 'cyan',
      'aiAssert': 'red',
      'aiWaitFor': 'gold',
      'sleep': 'gray'
    };
    return colorMap[actionType] || 'default';
  };

  const parseYAMLActions = (yamlContent: string) => {
    try {
      // 简单解析YAML内容中的动作
      const lines = yamlContent.split('\n');
      const actions: any[] = [];
      let currentTask = '';
      
      lines.forEach((line, index) => {
        const trimmed = line.trim();
        if (trimmed.startsWith('- name:')) {
          currentTask = trimmed.replace('- name:', '').trim();
        } else if (trimmed.startsWith('- ai:') || 
                   trimmed.startsWith('- aiTap:') ||
                   trimmed.startsWith('- aiInput:') ||
                   trimmed.startsWith('- aiHover:') ||
                   trimmed.startsWith('- aiScroll:') ||
                   trimmed.startsWith('- aiAssert:') ||
                   trimmed.startsWith('- aiWaitFor:') ||
                   trimmed.startsWith('- sleep:')) {
          const [actionType, ...contentParts] = trimmed.substring(2).split(':');
          const content = contentParts.join(':').trim();
          actions.push({
            id: index,
            task: currentTask,
            type: actionType,
            content: content.replace(/['"]/g, ''),
            line: index + 1
          });
        }
      });
      
      return actions;
    } catch (error) {
      console.error('解析YAML失败:', error);
      return [];
    }
  };

  const actions = parseYAMLActions(yamlContent);

  const renderAnalysisTab = () => (
    <div className="analysis-tab">
      {analysisResult?.page_analysis && (
        <>
          <Card title="页面信息" size="small" className="info-card">
            <Descriptions column={2} size="small">
              <Descriptions.Item label="页面标题">
                {analysisResult.page_analysis.page_title || '未知'}
              </Descriptions.Item>
              <Descriptions.Item label="页面类型">
                <Tag color="blue">{analysisResult.page_analysis.page_type}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="置信度" span={2}>
                <Badge 
                  status={analysisResult.confidence_score > 0.8 ? 'success' : 'warning'} 
                  text={`${(analysisResult.confidence_score * 100).toFixed(1)}%`}
                />
              </Descriptions.Item>
            </Descriptions>
            <Paragraph className="page-description">
              {analysisResult.page_analysis.main_content}
            </Paragraph>
          </Card>

          <Card title="识别的UI元素" size="small" className="elements-card">
            <List
              dataSource={analysisResult.page_analysis.ui_elements || []}
              renderItem={(element: any, index: number) => (
                <List.Item>
                  <div className="element-item">
                    <div className="element-header">
                      <Space>
                        <Tag color={getActionTypeColor(element.element_type)}>
                          {element.element_type}
                        </Tag>
                        <Text strong>{element.name}</Text>
                        <Badge 
                          count={`${(element.confidence_score * 100).toFixed(0)}%`}
                          style={{ backgroundColor: element.confidence_score > 0.8 ? '#52c41a' : '#faad14' }}
                        />
                      </Space>
                    </div>
                    <Text type="secondary">{element.description}</Text>
                    {element.interaction_hint && (
                      <div className="interaction-hint">
                        <InfoCircleOutlined /> {element.interaction_hint}
                      </div>
                    )}
                  </div>
                </List.Item>
              )}
            />
          </Card>

          <Row gutter={16}>
            <Col span={12}>
              <Card title="用户流程" size="small">
                <List
                  dataSource={analysisResult.page_analysis.user_flows || []}
                  renderItem={(flow: string, index: number) => (
                    <List.Item>
                      <Space>
                        <Badge count={index + 1} style={{ backgroundColor: '#1890ff' }} />
                        <Text>{flow}</Text>
                      </Space>
                    </List.Item>
                  )}
                />
              </Card>
            </Col>
            <Col span={12}>
              <Card title="测试场景" size="small">
                <List
                  dataSource={analysisResult.page_analysis.test_scenarios || []}
                  renderItem={(scenario: string) => (
                    <List.Item>
                      <Space>
                        <CheckCircleOutlined style={{ color: '#52c41a' }} />
                        <Text>{scenario}</Text>
                      </Space>
                    </List.Item>
                  )}
                />
              </Card>
            </Col>
          </Row>
        </>
      )}
    </div>
  );

  const renderActionsTab = () => (
    <div className="actions-tab">
      <div className="actions-summary">
        <Row gutter={16}>
          <Col span={8}>
            <Card size="small">
              <div className="stat-item">
                <Text type="secondary">总动作数</Text>
                <div className="stat-value">{actions.length}</div>
              </div>
            </Card>
          </Col>
          <Col span={8}>
            <Card size="small">
              <div className="stat-item">
                <Text type="secondary">动作类型</Text>
                <div className="stat-value">
                  {new Set(actions.map(a => a.type)).size}
                </div>
              </div>
            </Card>
          </Col>
          <Col span={8}>
            <Card size="small">
              <div className="stat-item">
                <Text type="secondary">预估时长</Text>
                <div className="stat-value">
                  <ClockCircleOutlined /> {Math.ceil(actions.length * 3)}s
                </div>
              </div>
            </Card>
          </Col>
        </Row>
      </div>

      <Card title="动作序列" size="small">
        <List
          dataSource={actions}
          renderItem={(action: any, index: number) => (
            <List.Item className="action-item">
              <div className="action-content">
                <div className="action-header">
                  <Space>
                    <Badge count={index + 1} style={{ backgroundColor: '#1890ff' }} />
                    <Tag color={getActionTypeColor(action.type)}>{action.type}</Tag>
                    <Text type="secondary">第{action.line}行</Text>
                  </Space>
                </div>
                <div className="action-description">
                  <Text>{action.content}</Text>
                </div>
                {action.task && (
                  <div className="action-task">
                    <Text type="secondary">任务: {action.task}</Text>
                  </div>
                )}
              </div>
            </List.Item>
          )}
        />
      </Card>
    </div>
  );

  const renderYAMLTab = () => (
    <div className="yaml-tab">
      <div className="yaml-header">
        <Space>
          <CodeOutlined />
          <Text strong>MidScene.js YAML脚本</Text>
          <Tag color="green">可执行</Tag>
        </Space>
      </div>
      <div className="yaml-content">
        <SyntaxHighlighter
          language="yaml"
          style={tomorrow}
          customStyle={{
            margin: 0,
            borderRadius: '6px',
            fontSize: '14px',
            lineHeight: '1.5'
          }}
          showLineNumbers
          wrapLines
        >
          {yamlContent}
        </SyntaxHighlighter>
      </div>
    </div>
  );

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="yaml-viewer"
    >
      <Card
        title={
          <Space>
            <EyeOutlined />
            <span>测试脚本预览</span>
          </Space>
        }
        extra={
          <Space>
            <Tooltip title="复制YAML内容">
              <Button 
                size="small" 
                onClick={() => {
                  navigator.clipboard.writeText(yamlContent);
                  // message.success('已复制到剪贴板');
                }}
              >
                复制
              </Button>
            </Tooltip>
            <Tooltip title="在新窗口中查看">
              <Button size="small" icon={<EyeOutlined />}>
                新窗口
              </Button>
            </Tooltip>
          </Space>
        }
        className="viewer-card"
      >
        <Tabs activeKey={activeTab} onChange={setActiveTab} size="small">
          <TabPane
            tab={
              <span>
                <CodeOutlined />
                YAML脚本
              </span>
            }
            key="yaml"
          >
            {renderYAMLTab()}
          </TabPane>
          
          <TabPane
            tab={
              <span>
                <PlayCircleOutlined />
                动作序列 ({actions.length})
              </span>
            }
            key="actions"
          >
            {renderActionsTab()}
          </TabPane>
          
          {analysisResult && (
            <TabPane
              tab={
                <span>
                  <InfoCircleOutlined />
                  分析结果
                </span>
              }
              key="analysis"
            >
              {renderAnalysisTab()}
            </TabPane>
          )}
        </Tabs>
      </Card>
    </motion.div>
  );
};

export default YAMLViewer;
