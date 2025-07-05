import React, { useState, useEffect, useCallback } from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  Tag,
  Modal,
  Select,
  Input,
  DatePicker,
  Row,
  Col,
  Statistic,
  Typography,
  Empty,
  Spin,
  message,
  Popconfirm,
  Drawer,
  Descriptions,
  Alert,
  Badge,
  Divider,
  Progress,
  Tooltip,
  Image
} from 'antd';
import {
  FileTextOutlined,
  EyeOutlined,
  DownloadOutlined,
  ReloadOutlined,
  SearchOutlined,
  CalendarOutlined,
  BarChartOutlined,
  DeleteOutlined,
  FilterOutlined,
  ExportOutlined,
  InfoCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  PlayCircleOutlined,
  SyncOutlined
} from '@ant-design/icons';
import { motion } from 'framer-motion';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import dayjs from 'dayjs';

import {
  getReportList,
  getReportStats,
  deleteReport,
  getReportViewUrl,
  openReportInNewWindow,
  formatReportStatus
} from '../../../services/testReportApi';
import './TestReports.css';

const { Title, Text } = Typography;
const { Option } = Select;
const { RangePicker } = DatePicker;

interface TestReport {
  id: string;
  name: string;
  execution_id: string;
  script_name: string;
  script_format?: 'yaml' | 'playwright';  // 可选字段
  status: 'passed' | 'failed' | 'skipped';
  start_time: string;
  end_time: string;
  duration: number;
  html_report_path: string;
  json_report_path?: string;
  screenshots: string[];
  test_cases: {
    total: number;
    passed: number;
    failed: number;
    skipped: number;
  };
}

interface ReportStatistics {
  total_reports: number;
  recent_reports: number;
  success_rate: number;
  average_duration: number;
  total_test_cases: number;
}

const TestReports: React.FC = () => {
  const [selectedReport, setSelectedReport] = useState<TestReport | null>(null);
  const [isReportModalVisible, setIsReportModalVisible] = useState(false);
  const [detailDrawerVisible, setDetailDrawerVisible] = useState(false);
  const [filterDrawerVisible, setFilterDrawerVisible] = useState(false);
  const [searchParams, setSearchParams] = useState({
    query: '',
    status: '',
    script_format: '',
    date_range: null as any,
    page: 1,
    page_size: 20
  });
  const [autoRefresh, setAutoRefresh] = useState(false);

  const queryClient = useQueryClient();

  // 获取测试报告列表
  const {
    data: reportsData,
    isLoading: isLoadingReports,
    refetch: refetchReports,
    error: reportsError
  } = useQuery(
    ['test-reports', searchParams],
    () => getReportList(searchParams),
    {
      keepPreviousData: true,
      refetchInterval: autoRefresh ? 30000 : false
    }
  );

  // 获取报告统计
  const {
    data: statistics,
    isLoading: isLoadingStats,
    refetch: refetchStats
  } = useQuery(
    'report-statistics',
    getReportStats,
    {
      refetchInterval: autoRefresh ? 30000 : false
    }
  );

  // 删除报告的mutation
  const deleteMutation = useMutation(
    (reportId: number) => deleteReport(reportId),
    {
      onSuccess: () => {
        message.success('报告删除成功');
        queryClient.invalidateQueries(['test-reports']);
        queryClient.invalidateQueries(['report-statistics']);
      },
      onError: (error: any) => {
        message.error(`删除失败: ${error.message}`);
      }
    }
  );

  // 自动刷新控制
  useEffect(() => {
    const interval = setInterval(() => {
      if (autoRefresh) {
        refetchReports();
        refetchStats();
      }
    }, 30000);

    return () => clearInterval(interval);
  }, [autoRefresh, refetchReports, refetchStats]);

  const handleSearch = useCallback((values: any) => {
    setSearchParams({
      ...searchParams,
      ...values,
      page: 1
    });
  }, [searchParams]);

  const handleViewReport = useCallback((report: TestReport) => {
    openReportInNewWindow(report.execution_id);
  }, []);

  const handleDownloadReport = useCallback((report: TestReport) => {
    const reportUrl = getReportViewUrl(report.execution_id);
    const link = document.createElement('a');
    link.href = reportUrl;
    link.download = `${report.script_name}_report_${report.execution_id}.html`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    message.success('报告下载已开始');
  }, []);

  const handleDeleteReport = useCallback(async (report: TestReport) => {
    try {
      await deleteMutation.mutateAsync(report.id);
    } catch (error) {
      console.error('删除报告失败:', error);
    }
  }, [deleteMutation]);

  const handleViewDetails = useCallback((report: TestReport) => {
    setSelectedReport(report);
    setDetailDrawerVisible(true);
  }, []);

  // 导出数据
  const handleExportData = useCallback(() => {
    const reports = reportsData?.data || [];
    const csvContent = [
      ['报告名称', '脚本名称', '格式', '状态', '执行时间', '耗时', '测试用例总数', '通过', '失败', '跳过'].join(','),
      ...reports.map(report => [
        report.script_name,
        report.script_name,
        (report.script_format || 'playwright').toUpperCase(),
        formatReportStatus(report.status).text,
        dayjs(report.start_time).format('YYYY-MM-DD HH:mm:ss'),
        `${Math.round(report.duration)}s`,
        report.total_tests || 0,
        report.passed_tests || 0,
        report.failed_tests || 0,
        report.skipped_tests || 0
      ].join(','))
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', `test_reports_${dayjs().format('YYYY-MM-DD')}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    message.success('数据导出成功');
  }, [reportsData]);

  // 清空过滤器
  const handleClearFilters = useCallback(() => {
    setSearchParams({
      query: '',
      status: '',
      script_format: '',
      date_range: null,
      page: 1,
      page_size: 20
    });
    message.info('过滤器已清空');
  }, []);

  const getStatusColor = (status: string) => {
    const statusInfo = formatReportStatus(status);
    switch (status) {
      case 'passed': return 'success';
      case 'failed': return 'error';
      case 'skipped': return 'warning';
      default: return 'default';
    }
  };

  const getFormatColor = (format: string) => {
    return format === 'yaml' ? 'blue' : 'green';
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'passed': return <CheckCircleOutlined />;
      case 'failed': return <CloseCircleOutlined />;
      case 'skipped': return <PlayCircleOutlined />;
      default: return <InfoCircleOutlined />;
    }
  };

  const columns = [
    {
      title: '报告名称',
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: TestReport) => (
        <div>
          <Text strong>{text}</Text>
          <br />
          <Text type="secondary" style={{ fontSize: '12px' }}>
            脚本: {record.script_name}
          </Text>
        </div>
      )
    },
    {
      title: '格式',
      dataIndex: 'script_format',
      key: 'script_format',
      width: 80,
      render: (format: string) => (
        <Tag color={getFormatColor(format || 'playwright')}>
          {(format || 'playwright').toUpperCase()}
        </Tag>
      )
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 80,
      render: (status: string) => {
        const statusInfo = formatReportStatus(status);
        return (
          <Tag color={getStatusColor(status)} icon={getStatusIcon(status)}>
            {statusInfo.text}
          </Tag>
        );
      }
    },
    {
      title: '测试用例',
      dataIndex: 'total_tests',
      key: 'test_cases',
      width: 120,
      render: (_, record: TestReport) => (
        <div>
          <Text style={{ fontSize: '12px' }}>
            总计: {record.total_tests || 0}
          </Text>
          <br />
          <Space size={4}>
            <Tag color="success" style={{ fontSize: '10px', padding: '0 4px' }}>
              通过: {record.passed_tests || 0}
            </Tag>
            <Tag color="error" style={{ fontSize: '10px', padding: '0 4px' }}>
              失败: {record.failed_tests || 0}
            </Tag>
            <Tag color="warning" style={{ fontSize: '10px', padding: '0 4px' }}>
              跳过: {record.skipped_tests || 0}
            </Tag>
          </Space>
          {record.total_tests > 0 && (
            <Progress
              percent={Math.round((record.passed_tests || 0) / record.total_tests * 100)}
              size="small"
              showInfo={false}
              style={{ marginTop: 4 }}
            />
          )}
        </div>
      )
    },
    {
      title: '执行时间',
      dataIndex: 'start_time',
      key: 'start_time',
      width: 150,
      render: (time: string, record: TestReport) => (
        <div>
          <Text style={{ fontSize: '12px' }}>
            {dayjs(time).format('YYYY-MM-DD HH:mm')}
          </Text>
          <br />
          <Text type="secondary" style={{ fontSize: '11px' }}>
            耗时: {Math.round(record.duration)}s
          </Text>
        </div>
      )
    },
    {
      title: '操作',
      key: 'actions',
      width: 200,
      render: (_, record: TestReport) => (
        <Space size="small">
          <Tooltip title="查看报告">
            <Button
              type="primary"
              size="small"
              icon={<EyeOutlined />}
              onClick={() => handleViewReport(record)}
            >
              查看
            </Button>
          </Tooltip>
          <Tooltip title="查看详情">
            <Button
              size="small"
              icon={<InfoCircleOutlined />}
              onClick={() => handleViewDetails(record)}
            >
              详情
            </Button>
          </Tooltip>
          <Tooltip title="下载报告">
            <Button
              size="small"
              icon={<DownloadOutlined />}
              onClick={() => handleDownloadReport(record)}
            >
              下载
            </Button>
          </Tooltip>
          <Tooltip title="删除报告">
            <Popconfirm
              title="确定要删除此报告吗？"
              description="删除后将无法恢复"
              onConfirm={() => handleDeleteReport(record)}
              okText="确定"
              cancelText="取消"
            >
              <Button
                size="small"
                icon={<DeleteOutlined />}
                loading={deleteMutation.isLoading}
                danger
              />
            </Popconfirm>
          </Tooltip>
        </Space>
      )
    }
  ];

  return (
    <div className="test-reports-container">
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
                <FileTextOutlined className="header-icon" />
                测试报告管理
              </Title>
              <Text type="secondary">查看和管理测试执行报告</Text>
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

        {/* 错误提示 */}
        {reportsError && (
          <Alert
            message="数据加载失败"
            description="无法获取测试报告数据，请检查网络连接或稍后重试"
            type="error"
            showIcon
            closable
            style={{ marginBottom: 24 }}
          />
        )}

        {/* 统计信息 */}
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={6}>
            <Card loading={isLoadingStats}>
              <Statistic
                title="总报告数"
                value={statistics?.total_reports || 0}
                prefix={<FileTextOutlined />}
                valueStyle={{ color: '#1890ff' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card loading={isLoadingStats}>
              <Statistic
                title="通过报告"
                value={statistics?.passed_reports || 0}
                prefix={<CheckCircleOutlined />}
                valueStyle={{ color: '#52c41a' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card loading={isLoadingStats}>
              <Statistic
                title="成功率"
                value={statistics?.success_rate || 0}
                precision={1}
                suffix="%"
                prefix={<BarChartOutlined />}
                valueStyle={{
                  color: (statistics?.success_rate || 0) >= 80 ? '#52c41a' : '#fa8c16'
                }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card loading={isLoadingStats}>
              <Statistic
                title="失败报告"
                value={statistics?.failed_reports || 0}
                prefix={<CloseCircleOutlined />}
                valueStyle={{ color: '#ff4d4f' }}
              />
            </Card>
          </Col>
        </Row>

        {/* 快速搜索栏 */}
        <Card style={{ marginBottom: 16 }}>
          <Row gutter={16} align="middle">
            <Col flex="auto">
              <Input
                placeholder="搜索报告名称或脚本名称"
                prefix={<SearchOutlined />}
                value={searchParams.query}
                onChange={(e) => setSearchParams({
                  ...searchParams,
                  query: e.target.value,
                  page: 1
                })}
                allowClear
                size="large"
              />
            </Col>
            <Col>
              <Space>
                <Select
                  placeholder="状态"
                  style={{ width: 120 }}
                  value={searchParams.status}
                  onChange={(value) => setSearchParams({
                    ...searchParams,
                    status: value,
                    page: 1
                  })}
                  allowClear
                >
                  <Option value="passed">通过</Option>
                  <Option value="failed">失败</Option>
                  <Option value="error">错误</Option>
                </Select>
                <Select
                  placeholder="格式"
                  style={{ width: 120 }}
                  value={searchParams.script_format}
                  onChange={(value) => setSearchParams({
                    ...searchParams,
                    script_format: value,
                    page: 1
                  })}
                  allowClear
                >
                  <Option value="yaml">YAML</Option>
                  <Option value="playwright">Playwright</Option>
                </Select>
                <Button
                  icon={<ReloadOutlined />}
                  onClick={() => refetchReports()}
                  loading={isLoadingReports}
                >
                  刷新
                </Button>
              </Space>
            </Col>
          </Row>
        </Card>

        {/* 报告列表 */}
        <Card>
          <Table
            columns={columns}
            dataSource={reportsData?.data || []}
            rowKey="id"
            loading={isLoadingReports}
            pagination={{
              current: searchParams.page,
              pageSize: searchParams.page_size,
              total: reportsData?.pagination?.total || 0,
              showSizeChanger: true,
              showQuickJumper: true,
              showTotal: (total, range) =>
                `第 ${range[0]}-${range[1]} 条，共 ${total} 条`,
              onChange: (page, pageSize) => {
                setSearchParams({
                  ...searchParams,
                  page: page,
                  page_size: pageSize!
                });
              }
            }}
            locale={{
              emptyText: (
                <Empty
                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                  description="暂无测试报告"
                />
              )
            }}
          />
        </Card>

        {/* 报告查看模态框 */}
        <Modal
          title={`测试报告 - ${selectedReport?.name}`}
          open={isReportModalVisible}
          onCancel={() => setIsReportModalVisible(false)}
          width="90%"
          style={{ top: 20 }}
          footer={[
            <Button key="download" icon={<DownloadOutlined />} onClick={() => {
              if (selectedReport) {
                handleDownloadReport(selectedReport);
              }
            }}>
              下载报告
            </Button>,
            <Button key="close" onClick={() => setIsReportModalVisible(false)}>
              关闭
            </Button>
          ]}
        >
          {selectedReport && (
            <div style={{ height: '70vh' }}>
              <iframe
                src={`/api/v1/test-automation/reports/${selectedReport.id}/view`}
                style={{
                  width: '100%',
                  height: '100%',
                  border: 'none',
                  borderRadius: '4px'
                }}
                title="测试报告"
              />
            </div>
          )}
        </Modal>
      </motion.div>
    </div>
  );
};

// API 函数
const fetchTestReports = async (params: any) => {
  const queryParams = new URLSearchParams();
  Object.keys(params).forEach(key => {
    if (params[key] !== '' && params[key] !== null && params[key] !== undefined) {
      if (key === 'date_range' && params[key]) {
        queryParams.append('start_date', params[key][0].format('YYYY-MM-DD'));
        queryParams.append('end_date', params[key][1].format('YYYY-MM-DD'));
      } else {
        queryParams.append(key, params[key]);
      }
    }
  });

  const response = await fetch(`/api/v1/web/reports/list?${queryParams}`);
  return response.json();
};

const fetchReportStatistics = async () => {
  const response = await fetch('/api/v1/web/reports/stats');
  return response.json();
};

export default TestReports;
