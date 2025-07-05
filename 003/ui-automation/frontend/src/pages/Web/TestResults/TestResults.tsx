import React, { useState, useCallback, useEffect } from 'react';
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
  Image,
  Input,
  Select,
  DatePicker,
  message,
  Popconfirm,
  Drawer,
  Descriptions,
  Alert,
  Badge,
  Divider
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
  PlayCircleOutlined,
  SearchOutlined,
  FilterOutlined,
  ExportOutlined,
  DeleteOutlined,
  InfoCircleOutlined,
  CalendarOutlined,
  SyncOutlined
} from '@ant-design/icons';
import { motion } from 'framer-motion';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import dayjs from 'dayjs';

import {
  getExecutionHistory,
  getPlaywrightExecutionHistory,
  executeScriptFromDB,
  cleanupExecution
} from '../../../services/api';
import {
  getReportViewUrl,
  openReportInNewWindow,
  checkReportExists
} from '../../../services/testReportApi';
import './TestResults.css';

const { TabPane } = Tabs;
const { Title, Paragraph, Text } = Typography;
const { Option } = Select;
const { RangePicker } = DatePicker;

const TestResults: React.FC = () => {
  const [activeTab, setActiveTab] = useState('yaml');
  const [selectedResult, setSelectedResult] = useState<any>(null);
  const [detailModalVisible, setDetailModalVisible] = useState(false);
  const [filterDrawerVisible, setFilterDrawerVisible] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [dateRange, setDateRange] = useState<any>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);

  const queryClient = useQueryClient();

  // 获取YAML执行历史
  const { data: yamlHistory, isLoading: yamlLoading, refetch: refetchYaml } = useQuery(
    ['yamlExecutionHistory', searchText, statusFilter, dateRange],
    () => getExecutionHistory(50),
    {
      refetchInterval: autoRefresh ? 10000 : false,
      keepPreviousData: true
    }
  );

  // 获取Playwright执行历史
  const { data: playwrightHistory, isLoading: playwrightLoading, refetch: refetchPlaywright } = useQuery(
    ['playwrightExecutionHistory', searchText, statusFilter, dateRange],
    () => getPlaywrightExecutionHistory(50),
    {
      refetchInterval: autoRefresh ? 10000 : false,
      keepPreviousData: true
    }
  );

  // 重新执行脚本的mutation
  const reExecuteMutation = useMutation(
    (executionId: string) => executeScriptFromDB(executionId, {}),
    {
      onSuccess: (data) => {
        message.success(`脚本重新执行成功，执行ID: ${data.execution_id}`);
        queryClient.invalidateQueries(['yamlExecutionHistory']);
        queryClient.invalidateQueries(['playwrightExecutionHistory']);
      },
      onError: (error: any) => {
        message.error(`重新执行失败: ${error.message}`);
      }
    }
  );

  // 清理执行数据的mutation
  const cleanupMutation = useMutation(
    (executionId: string) => cleanupExecution(executionId),
    {
      onSuccess: () => {
        message.success('执行数据清理成功');
        queryClient.invalidateQueries(['yamlExecutionHistory']);
        queryClient.invalidateQueries(['playwrightExecutionHistory']);
      },
      onError: (error: any) => {
        message.error(`清理失败: ${error.message}`);
      }
    }
  );

  // 自动刷新控制
  useEffect(() => {
    const interval = setInterval(() => {
      if (autoRefresh) {
        refetchYaml();
        refetchPlaywright();
      }
    }, 10000);

    return () => clearInterval(interval);
  }, [autoRefresh, refetchYaml, refetchPlaywright]);

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

  // 处理重新执行
  const handleReExecute = useCallback(async (record: any) => {
    try {
      await reExecuteMutation.mutateAsync(record.execution_id);
    } catch (error) {
      console.error('重新执行失败:', error);
    }
  }, [reExecuteMutation]);

  // 处理下载报告
  const handleDownloadReport = useCallback(async (record: any) => {
    try {
      const hasReport = await checkReportExists(record.execution_id);
      if (hasReport) {
        const reportUrl = getReportViewUrl(record.execution_id);
        const link = document.createElement('a');
        link.href = reportUrl;
        link.download = `test_report_${record.execution_id}.html`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        message.success('报告下载已开始');
      } else {
        message.warning('该执行记录暂无可用报告');
      }
    } catch (error) {
      message.error('下载报告失败');
    }
  }, []);

  // 处理查看报告
  const handleViewReport = useCallback(async (record: any) => {
    try {
      const hasReport = await checkReportExists(record.execution_id);
      if (hasReport) {
        openReportInNewWindow(record.execution_id);
      } else {
        message.warning('该执行记录暂无可用报告');
      }
    } catch (error) {
      message.error('查看报告失败');
    }
  }, []);

  // 处理清理执行数据
  const handleCleanup = useCallback(async (record: any) => {
    try {
      await cleanupMutation.mutateAsync(record.execution_id);
    } catch (error) {
      console.error('清理失败:', error);
    }
  }, [cleanupMutation]);

  // 过滤数据
  const filterData = useCallback((data: any[]) => {
    if (!data) return [];

    return data.filter(item => {
      // 文本搜索
      if (searchText && !item.execution_id.toLowerCase().includes(searchText.toLowerCase())) {
        return false;
      }

      // 状态过滤
      if (statusFilter && item.status !== statusFilter) {
        return false;
      }

      // 日期范围过滤
      if (dateRange && dateRange.length === 2) {
        const itemDate = dayjs(item.start_time);
        if (!itemDate.isBetween(dateRange[0], dateRange[1], 'day', '[]')) {
          return false;
        }
      }

      return true;
    });
  }, [searchText, statusFilter, dateRange]);

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
              loading={reExecuteMutation.isLoading}
              onClick={() => handleReExecute(record)}
            />
          </Tooltip>
          <Tooltip title="查看报告">
            <Button
              type="text"
              icon={<EyeOutlined />}
              onClick={() => handleViewReport(record)}
            />
          </Tooltip>
          <Tooltip title="下载报告">
            <Button
              type="text"
              icon={<DownloadOutlined />}
              onClick={() => handleDownloadReport(record)}
            />
          </Tooltip>
          <Tooltip title="清理数据">
            <Popconfirm
              title="确定要清理此执行数据吗？"
              description="清理后将无法恢复"
              onConfirm={() => handleCleanup(record)}
              okText="确定"
              cancelText="取消"
            >
              <Button
                type="text"
                icon={<DeleteOutlined />}
                loading={cleanupMutation.isLoading}
                danger
              />
            </Popconfirm>
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
          <Tooltip title="查看报告">
            <Button
              type="text"
              icon={<EyeOutlined />}
              onClick={() => handleViewReport(record)}
            />
          </Tooltip>
          <Tooltip title="下载报告">
            <Button
              type="text"
              icon={<DownloadOutlined />}
              onClick={() => handleDownloadReport(record)}
            />
          </Tooltip>
          <Tooltip title="清理数据">
            <Popconfirm
              title="确定要清理此执行数据吗？"
              description="清理后将无法恢复"
              onConfirm={() => handleCleanup(record)}
              okText="确定"
              cancelText="取消"
            >
              <Button
                type="text"
                icon={<DeleteOutlined />}
                loading={cleanupMutation.isLoading}
                danger
              />
            </Popconfirm>
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

  // 应用过滤器
  const filteredYamlHistory = filterData(yamlHistory?.history || []);
  const filteredPlaywrightHistory = filterData(playwrightHistory?.history || []);

  const yamlStats = calculateStats(filteredYamlHistory);
  const playwrightStats = calculateStats(filteredPlaywrightHistory);

  // 导出数据
  const handleExportData = useCallback(() => {
    const currentData = activeTab === 'yaml' ? filteredYamlHistory : filteredPlaywrightHistory;
    const csvContent = [
      ['执行ID', '状态', '开始时间', '执行时长', '进度'].join(','),
      ...currentData.map(item => [
        item.execution_id,
        getStatusText(item.status),
        new Date(item.start_time).toLocaleString(),
        item.duration ? `${item.duration.toFixed(1)}s` : '-',
        `${item.progress || 0}%`
      ].join(','))
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', `test_results_${activeTab}_${dayjs().format('YYYY-MM-DD')}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    message.success('数据导出成功');
  }, [activeTab, filteredYamlHistory, filteredPlaywrightHistory, getStatusText]);

  // 清空过滤器
  const handleClearFilters = useCallback(() => {
    setSearchText('');
    setStatusFilter('');
    setDateRange(null);
    message.info('过滤器已清空');
  }, []);

  return (
    <div className="test-results-container">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        {/* 页面头部 */}
        <Card className="page-header" style={{ marginBottom: 24 }}>
          <Row justify="space-between" align="middle">
            <Col>
              <Title level={2} style={{ margin: 0 }}>
                <BarChartOutlined className="header-icon" />
                测试执行结果
              </Title>
              <Text type="secondary">查看和管理测试执行历史记录</Text>
            </Col>
            <Col>
              <Space>
                <Button
                  icon={<FilterOutlined />}
                  onClick={() => setFilterDrawerVisible(true)}
                >
                  过滤器
                </Button>
                <Button
                  icon={<ExportOutlined />}
                  onClick={handleExportData}
                >
                  导出数据
                </Button>
                <Button
                  icon={autoRefresh ? <SyncOutlined spin /> : <SyncOutlined />}
                  type={autoRefresh ? 'primary' : 'default'}
                  onClick={() => setAutoRefresh(!autoRefresh)}
                >
                  {autoRefresh ? '自动刷新' : '手动刷新'}
                </Button>
              </Space>
            </Col>
          </Row>
        </Card>

        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          size="large"
          className="results-tabs"
          tabBarExtraContent={
            <Space>
              <Badge
                count={filteredYamlHistory.length + filteredPlaywrightHistory.length}
                showZero
                style={{ backgroundColor: '#52c41a' }}
              >
                <Text type="secondary">总记录数</Text>
              </Badge>
            </Space>
          }
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
              title={
                <Space>
                  <FileTextOutlined />
                  YAML执行历史
                  <Badge count={filteredYamlHistory.length} showZero />
                </Space>
              }
              extra={
                <Space>
                  <Button
                    icon={<ReloadOutlined />}
                    onClick={() => refetchYaml()}
                    loading={yamlLoading}
                    size="small"
                  >
                    刷新
                  </Button>
                </Space>
              }
            >
              {filteredYamlHistory.length === 0 && !yamlLoading ? (
                <Alert
                  message="暂无数据"
                  description="当前过滤条件下没有找到执行记录"
                  type="info"
                  showIcon
                  style={{ marginBottom: 16 }}
                />
              ) : null}
              <Table
                columns={yamlColumns}
                dataSource={filteredYamlHistory}
                loading={yamlLoading}
                rowKey="execution_id"
                pagination={{
                  pageSize: 10,
                  showSizeChanger: true,
                  showQuickJumper: true,
                  showTotal: (total, range) =>
                    `第 ${range[0]}-${range[1]} 条，共 ${total} 条记录`
                }}
                scroll={{ x: 800 }}
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
              title={
                <Space>
                  <PlayCircleOutlined />
                  Playwright执行历史
                  <Badge count={filteredPlaywrightHistory.length} showZero />
                </Space>
              }
              extra={
                <Space>
                  <Button
                    icon={<ReloadOutlined />}
                    onClick={() => refetchPlaywright()}
                    loading={playwrightLoading}
                    size="small"
                  >
                    刷新
                  </Button>
                </Space>
              }
            >
              {filteredPlaywrightHistory.length === 0 && !playwrightLoading ? (
                <Alert
                  message="暂无数据"
                  description="当前过滤条件下没有找到执行记录"
                  type="info"
                  showIcon
                  style={{ marginBottom: 16 }}
                />
              ) : null}
              <Table
                columns={playwrightColumns}
                dataSource={filteredPlaywrightHistory}
                loading={playwrightLoading}
                rowKey="execution_id"
                pagination={{
                  pageSize: 10,
                  showSizeChanger: true,
                  showQuickJumper: true,
                  showTotal: (total, range) =>
                    `第 ${range[0]}-${range[1]} 条，共 ${total} 条记录`
                }}
                scroll={{ x: 800 }}
              />
            </Card>
          </TabPane>
        </Tabs>

        {/* 过滤器抽屉 */}
        <Drawer
          title="过滤器设置"
          placement="right"
          onClose={() => setFilterDrawerVisible(false)}
          open={filterDrawerVisible}
          width={400}
        >
          <Space direction="vertical" style={{ width: '100%' }} size="large">
            <div>
              <Text strong>搜索执行ID</Text>
              <Input
                placeholder="输入执行ID进行搜索"
                value={searchText}
                onChange={(e) => setSearchText(e.target.value)}
                prefix={<SearchOutlined />}
                allowClear
                style={{ marginTop: 8 }}
              />
            </div>

            <div>
              <Text strong>执行状态</Text>
              <Select
                placeholder="选择执行状态"
                value={statusFilter}
                onChange={setStatusFilter}
                allowClear
                style={{ width: '100%', marginTop: 8 }}
              >
                <Option value="completed">已完成</Option>
                <Option value="passed">通过</Option>
                <Option value="failed">失败</Option>
                <Option value="error">错误</Option>
                <Option value="running">执行中</Option>
              </Select>
            </div>

            <div>
              <Text strong>时间范围</Text>
              <RangePicker
                value={dateRange}
                onChange={setDateRange}
                style={{ width: '100%', marginTop: 8 }}
                showTime
              />
            </div>

            <Divider />

            <Space style={{ width: '100%', justifyContent: 'space-between' }}>
              <Button onClick={handleClearFilters}>
                清空过滤器
              </Button>
              <Button
                type="primary"
                onClick={() => setFilterDrawerVisible(false)}
              >
                应用过滤器
              </Button>
            </Space>
          </Space>
        </Drawer>

        {/* 详情模态框 */}
        <Modal
          title={
            <Space>
              <InfoCircleOutlined />
              执行详情
              {selectedResult && (
                <Tag color={getStatusColor(selectedResult.status)}>
                  {getStatusText(selectedResult.status)}
                </Tag>
              )}
            </Space>
          }
          open={detailModalVisible}
          onCancel={() => setDetailModalVisible(false)}
          footer={[
            <Button key="close" onClick={() => setDetailModalVisible(false)}>
              关闭
            </Button>,
            selectedResult && (
              <Button
                key="report"
                type="primary"
                icon={<EyeOutlined />}
                onClick={() => handleViewReport(selectedResult)}
              >
                查看报告
              </Button>
            )
          ]}
          width={900}
        >
          {selectedResult && (
            <div className="result-detail">
              <Descriptions
                title="基本信息"
                bordered
                column={2}
                size="small"
                style={{ marginBottom: 24 }}
              >
                <Descriptions.Item label="执行ID">
                  <Text code>{selectedResult.execution_id}</Text>
                </Descriptions.Item>
                <Descriptions.Item label="状态">
                  <Tag color={getStatusColor(selectedResult.status)} icon={getStatusIcon(selectedResult.status)}>
                    {getStatusText(selectedResult.status)}
                  </Tag>
                </Descriptions.Item>
                <Descriptions.Item label="开始时间">
                  <Text>{new Date(selectedResult.start_time).toLocaleString()}</Text>
                </Descriptions.Item>
                <Descriptions.Item label="执行时长">
                  <Text>{selectedResult.duration ? `${selectedResult.duration.toFixed(1)}s` : '-'}</Text>
                </Descriptions.Item>
                <Descriptions.Item label="进度">
                  <Progress
                    percent={selectedResult.progress || 0}
                    size="small"
                    status={selectedResult.progress === 100 ? 'success' : 'active'}
                  />
                </Descriptions.Item>
                <Descriptions.Item label="创建时间">
                  <Text>{selectedResult.created_at ? new Date(selectedResult.created_at).toLocaleString() : '-'}</Text>
                </Descriptions.Item>
              </Descriptions>

              {selectedResult.error_message && (
                <Alert
                  message="错误信息"
                  description={selectedResult.error_message}
                  type="error"
                  showIcon
                  style={{ marginBottom: 16 }}
                />
              )}

              {selectedResult.logs && selectedResult.logs.length > 0 && (
                <Card
                  title={
                    <Space>
                      <FileTextOutlined />
                      执行日志
                      <Badge count={selectedResult.logs.length} />
                    </Space>
                  }
                  size="small"
                  style={{ marginBottom: 16 }}
                >
                  <div style={{
                    background: '#fafafa',
                    border: '1px solid #d9d9d9',
                    borderRadius: 4,
                    padding: 12,
                    maxHeight: 300,
                    overflow: 'auto'
                  }}>
                    <pre style={{ margin: 0, fontSize: '12px', lineHeight: '1.4' }}>
                      {selectedResult.logs.join('\n')}
                    </pre>
                  </div>
                </Card>
              )}

              {selectedResult.results && (
                <Card
                  title={
                    <Space>
                      <CheckCircleOutlined />
                      执行结果
                    </Space>
                  }
                  size="small"
                  style={{ marginBottom: 16 }}
                >
                  <div style={{
                    background: '#f6ffed',
                    border: '1px solid #b7eb8f',
                    borderRadius: 4,
                    padding: 12,
                    maxHeight: 300,
                    overflow: 'auto'
                  }}>
                    <pre style={{ margin: 0, fontSize: '12px', lineHeight: '1.4' }}>
                      {JSON.stringify(selectedResult.results, null, 2)}
                    </pre>
                  </div>
                </Card>
              )}

              {selectedResult.screenshots && selectedResult.screenshots.length > 0 && (
                <Card
                  title={
                    <Space>
                      <Image />
                      截图文件
                      <Badge count={selectedResult.screenshots.length} />
                    </Space>
                  }
                  size="small"
                >
                  <Space wrap>
                    {selectedResult.screenshots.map((screenshot: string, index: number) => (
                      <Image
                        key={index}
                        width={100}
                        height={60}
                        src={screenshot}
                        placeholder={
                          <div style={{
                            width: 100,
                            height: 60,
                            background: '#f0f0f0',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center'
                          }}>
                            <Text type="secondary">截图{index + 1}</Text>
                          </div>
                        }
                      />
                    ))}
                  </Space>
                </Card>
              )}
            </div>
          )}
        </Modal>
      </motion.div>
    </div>
  );
};

export default TestResults;
