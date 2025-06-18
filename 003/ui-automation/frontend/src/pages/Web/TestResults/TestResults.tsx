import React, { useState } from 'react';
import {
  Card,
  Table,
  Tag,
  Button,
  Space,
  Typography,
  Row,
  Col,
  Statistic,
  Progress,
  Tabs,
  List,
  Avatar,
  Tooltip,
  Modal,
  Image
} from 'antd';
import {
  EyeOutlined,
  DownloadOutlined,
  ReloadOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
  BarChartOutlined,
  FileTextOutlined,
  PlayCircleOutlined
} from '@ant-design/icons';
import { motion } from 'framer-motion';
import { useQuery } from 'react-query';

import { getExecutionHistory, getPlaywrightExecutionHistory } from '../../../services/api';
import './TestResults.css';

const { TabPane } = Tabs;
const { Title, Paragraph, Text } = Typography;

const TestResults: React.FC = () => {
  const [activeTab, setActiveTab] = useState('yaml');
  const [selectedResult, setSelectedResult] = useState<any>(null);
  const [detailModalVisible, setDetailModalVisible] = useState(false);

  // 获取YAML执行历史
  const { data: yamlHistory, isLoading: yamlLoading, refetch: refetchYaml } = useQuery(
    'yamlExecutionHistory',
    () => getExecutionHistory(50),
    {
      refetchInterval: 10000
    }
  );

  // 获取Playwright执行历史
  const { data: playwrightHistory, isLoading: playwrightLoading, refetch: refetchPlaywright } = useQuery(
    'playwrightExecutionHistory',
    () => getPlaywrightExecutionHistory(50),
    {
      refetchInterval: 10000
    }
  );

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
      case 'passed': return 'success';
      case 'failed':
      case 'error': return 'error';
      case 'running': return 'processing';
      default: return 'default';
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'completed': return '已完成';
      case 'passed': return '通过';
      case 'failed': return '失败';
      case 'error': return '错误';
      case 'running': return '执行中';
      default: return '未知';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
      case 'passed': return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
      case 'failed':
      case 'error': return <CloseCircleOutlined style={{ color: '#ff4d4f' }} />;
      case 'running': return <ClockCircleOutlined style={{ color: '#1890ff' }} />;
      default: return <ClockCircleOutlined style={{ color: '#d9d9d9' }} />;
    }
  };

  const yamlColumns = [
    {
      title: '执行ID',
      dataIndex: 'execution_id',
      key: 'execution_id',
      width: 120,
      render: (id: string) => (
        <Text code>{id.slice(0, 8)}</Text>
      )
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => (
        <Tag color={getStatusColor(status)} icon={getStatusIcon(status)}>
          {getStatusText(status)}
        </Tag>
      )
    },
    {
      title: '开始时间',
      dataIndex: 'start_time',
      key: 'start_time',
      width: 180,
      render: (time: string) => new Date(time).toLocaleString()
    },
    {
      title: '执行时长',
      dataIndex: 'duration',
      key: 'duration',
      width: 100,
      render: (duration: number) => duration ? `${duration.toFixed(1)}s` : '-'
    },
    {
      title: '进度',
      dataIndex: 'progress',
      key: 'progress',
      width: 120,
      render: (progress: number) => (
        <Progress 
          percent={progress} 
          size="small" 
          status={progress === 100 ? 'success' : 'active'}
        />
      )
    },
    {
      title: '操作',
      key: 'actions',
      width: 150,
      render: (_: any, record: any) => (
        <Space>
          <Tooltip title="查看详情">
            <Button
              type="text"
              icon={<EyeOutlined />}
              onClick={() => {
                setSelectedResult(record);
                setDetailModalVisible(true);
              }}
            />
          </Tooltip>
          <Tooltip title="重新执行">
            <Button
              type="text"
              icon={<PlayCircleOutlined />}
              onClick={() => {
                // TODO: 实现重新执行逻辑
              }}
            />
          </Tooltip>
          <Tooltip title="下载报告">
            <Button
              type="text"
              icon={<DownloadOutlined />}
              onClick={() => {
                // TODO: 实现下载报告逻辑
              }}
            />
          </Tooltip>
        </Space>
      )
    }
  ];

  const playwrightColumns = [
    {
      title: '执行ID',
      dataIndex: 'execution_id',
      key: 'execution_id',
      width: 120,
      render: (id: string) => (
        <Text code>{id.slice(0, 8)}</Text>
      )
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => (
        <Tag color={getStatusColor(status)} icon={getStatusIcon(status)}>
          {getStatusText(status)}
        </Tag>
      )
    },
    {
      title: '测试类型',
      dataIndex: 'test_type',
      key: 'test_type',
      width: 100,
      render: () => 'Playwright'
    },
    {
      title: '开始时间',
      dataIndex: 'start_time',
      key: 'start_time',
      width: 180,
      render: (time: string) => new Date(time).toLocaleString()
    },
    {
      title: '执行时长',
      dataIndex: 'duration',
      key: 'duration',
      width: 100,
      render: (duration: number) => duration ? `${duration.toFixed(1)}s` : '-'
    },
    {
      title: '操作',
      key: 'actions',
      width: 150,
      render: (_: any, record: any) => (
        <Space>
          <Tooltip title="查看详情">
            <Button
              type="text"
              icon={<EyeOutlined />}
              onClick={() => {
                setSelectedResult(record);
                setDetailModalVisible(true);
              }}
            />
          </Tooltip>
          <Tooltip title="下载报告">
            <Button
              type="text"
              icon={<DownloadOutlined />}
              onClick={() => {
                // TODO: 实现下载报告逻辑
              }}
            />
          </Tooltip>
        </Space>
      )
    }
  ];

  const calculateStats = (data: any[]) => {
    if (!data || data.length === 0) {
      return { total: 0, passed: 0, failed: 0, successRate: 0 };
    }

    const total = data.length;
    const passed = data.filter(item => 
      item.status === 'completed' || item.status === 'passed'
    ).length;
    const failed = data.filter(item => 
      item.status === 'failed' || item.status === 'error'
    ).length;
    const successRate = total > 0 ? (passed / total) * 100 : 0;

    return { total, passed, failed, successRate };
  };

  const yamlStats = calculateStats(yamlHistory?.history || []);
  const playwrightStats = calculateStats(playwrightHistory?.history || []);

  return (
    <div className="test-results-container">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          size="large"
          className="results-tabs"
        >
          <TabPane
            tab={
              <span>
                <FileTextOutlined />
                YAML执行结果
              </span>
            }
            key="yaml"
          >
            {/* YAML执行统计 */}
            <Row gutter={[24, 24]} style={{ marginBottom: 24 }}>
              <Col span={6}>
                <Card className="stat-card">
                  <Statistic
                    title="总执行次数"
                    value={yamlStats.total}
                    valueStyle={{ color: '#1890ff' }}
                  />
                </Card>
              </Col>
              <Col span={6}>
                <Card className="stat-card">
                  <Statistic
                    title="成功次数"
                    value={yamlStats.passed}
                    valueStyle={{ color: '#52c41a' }}
                  />
                </Card>
              </Col>
              <Col span={6}>
                <Card className="stat-card">
                  <Statistic
                    title="失败次数"
                    value={yamlStats.failed}
                    valueStyle={{ color: '#ff4d4f' }}
                  />
                </Card>
              </Col>
              <Col span={6}>
                <Card className="stat-card">
                  <Statistic
                    title="成功率"
                    value={yamlStats.successRate}
                    precision={1}
                    suffix="%"
                    valueStyle={{ color: yamlStats.successRate >= 80 ? '#52c41a' : '#fa8c16' }}
                  />
                </Card>
              </Col>
            </Row>

            {/* YAML执行历史表格 */}
            <Card
              title="YAML执行历史"
              extra={
                <Button
                  icon={<ReloadOutlined />}
                  onClick={() => refetchYaml()}
                  loading={yamlLoading}
                >
                  刷新
                </Button>
              }
            >
              <Table
                columns={yamlColumns}
                dataSource={yamlHistory?.history || []}
                loading={yamlLoading}
                rowKey="execution_id"
                pagination={{
                  pageSize: 10,
                  showSizeChanger: true,
                  showQuickJumper: true,
                  showTotal: (total) => `共 ${total} 条记录`
                }}
              />
            </Card>
          </TabPane>

          <TabPane
            tab={
              <span>
                <PlayCircleOutlined />
                Playwright执行结果
              </span>
            }
            key="playwright"
          >
            {/* Playwright执行统计 */}
            <Row gutter={[24, 24]} style={{ marginBottom: 24 }}>
              <Col span={6}>
                <Card className="stat-card">
                  <Statistic
                    title="总执行次数"
                    value={playwrightStats.total}
                    valueStyle={{ color: '#722ed1' }}
                  />
                </Card>
              </Col>
              <Col span={6}>
                <Card className="stat-card">
                  <Statistic
                    title="成功次数"
                    value={playwrightStats.passed}
                    valueStyle={{ color: '#52c41a' }}
                  />
                </Card>
              </Col>
              <Col span={6}>
                <Card className="stat-card">
                  <Statistic
                    title="失败次数"
                    value={playwrightStats.failed}
                    valueStyle={{ color: '#ff4d4f' }}
                  />
                </Card>
              </Col>
              <Col span={6}>
                <Card className="stat-card">
                  <Statistic
                    title="成功率"
                    value={playwrightStats.successRate}
                    precision={1}
                    suffix="%"
                    valueStyle={{ color: playwrightStats.successRate >= 80 ? '#52c41a' : '#fa8c16' }}
                  />
                </Card>
              </Col>
            </Row>

            {/* Playwright执行历史表格 */}
            <Card
              title="Playwright执行历史"
              extra={
                <Button
                  icon={<ReloadOutlined />}
                  onClick={() => refetchPlaywright()}
                  loading={playwrightLoading}
                >
                  刷新
                </Button>
              }
            >
              <Table
                columns={playwrightColumns}
                dataSource={playwrightHistory?.history || []}
                loading={playwrightLoading}
                rowKey="execution_id"
                pagination={{
                  pageSize: 10,
                  showSizeChanger: true,
                  showQuickJumper: true,
                  showTotal: (total) => `共 ${total} 条记录`
                }}
              />
            </Card>
          </TabPane>
        </Tabs>

        {/* 详情模态框 */}
        <Modal
          title="执行详情"
          open={detailModalVisible}
          onCancel={() => setDetailModalVisible(false)}
          footer={null}
          width={800}
        >
          {selectedResult && (
            <div className="result-detail">
              <Row gutter={[16, 16]}>
                <Col span={12}>
                  <Text strong>执行ID: </Text>
                  <Text code>{selectedResult.execution_id}</Text>
                </Col>
                <Col span={12}>
                  <Text strong>状态: </Text>
                  <Tag color={getStatusColor(selectedResult.status)}>
                    {getStatusText(selectedResult.status)}
                  </Tag>
                </Col>
                <Col span={12}>
                  <Text strong>开始时间: </Text>
                  <Text>{new Date(selectedResult.start_time).toLocaleString()}</Text>
                </Col>
                <Col span={12}>
                  <Text strong>执行时长: </Text>
                  <Text>{selectedResult.duration ? `${selectedResult.duration.toFixed(1)}s` : '-'}</Text>
                </Col>
              </Row>

              {selectedResult.error_message && (
                <div style={{ marginTop: 16 }}>
                  <Text strong>错误信息: </Text>
                  <div style={{
                    background: '#fff2f0',
                    border: '1px solid #ffccc7',
                    borderRadius: 4,
                    padding: 12,
                    marginTop: 8
                  }}>
                    <Text type="danger">{selectedResult.error_message}</Text>
                  </div>
                </div>
              )}

              {selectedResult.logs && selectedResult.logs.length > 0 && (
                <div style={{ marginTop: 16 }}>
                  <Text strong>执行日志: </Text>
                  <div style={{
                    background: '#fafafa',
                    border: '1px solid #d9d9d9',
                    borderRadius: 4,
                    padding: 12,
                    marginTop: 8,
                    maxHeight: 300,
                    overflow: 'auto'
                  }}>
                    <pre style={{ margin: 0, fontSize: '12px', lineHeight: '1.4' }}>
                      {selectedResult.logs.join('\n')}
                    </pre>
                  </div>
                </div>
              )}

              {selectedResult.results && (
                <div style={{ marginTop: 16 }}>
                  <Text strong>执行结果: </Text>
                  <div style={{
                    background: '#f6ffed',
                    border: '1px solid #b7eb8f',
                    borderRadius: 4,
                    padding: 12,
                    marginTop: 8,
                    maxHeight: 300,
                    overflow: 'auto'
                  }}>
                    <pre style={{ margin: 0, fontSize: '12px', lineHeight: '1.4' }}>
                      {JSON.stringify(selectedResult.results, null, 2)}
                    </pre>
                  </div>
                </div>
              )}
            </div>
          )}
        </Modal>
      </motion.div>
    </div>
  );
};

export default TestResults;
