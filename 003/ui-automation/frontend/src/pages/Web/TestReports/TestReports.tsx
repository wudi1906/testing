import React, { useState, useEffect } from 'react';
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
  message
} from 'antd';
import {
  FileTextOutlined,
  EyeOutlined,
  DownloadOutlined,
  ReloadOutlined,
  SearchOutlined,
  CalendarOutlined,
  BarChartOutlined
} from '@ant-design/icons';
import { motion } from 'framer-motion';
import { useQuery } from 'react-query';
import dayjs from 'dayjs';

import './TestReports.css';

const { Title, Text } = Typography;
const { Option } = Select;
const { RangePicker } = DatePicker;

interface TestReport {
  id: string;
  name: string;
  execution_id: string;
  script_name: string;
  script_format: 'yaml' | 'playwright';
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
  const [searchParams, setSearchParams] = useState({
    query: '',
    status: '',
    script_format: '',
    date_range: null as any,
    limit: 20,
    offset: 0
  });

  // 获取测试报告列表
  const {
    data: reportsData,
    isLoading: isLoadingReports,
    refetch: refetchReports
  } = useQuery(
    ['test-reports', searchParams],
    () => fetchTestReports(searchParams),
    {
      keepPreviousData: true
    }
  );

  // 获取报告统计
  const { data: statistics } = useQuery(
    'report-statistics',
    fetchReportStatistics
  );

  const handleSearch = (values: any) => {
    setSearchParams({
      ...searchParams,
      ...values,
      offset: 0
    });
  };

  const handleViewReport = (report: TestReport) => {
    setSelectedReport(report);
    setIsReportModalVisible(true);
  };

  const handleDownloadReport = (report: TestReport) => {
    // 下载HTML报告
    const link = document.createElement('a');
    link.href = `/api/v1/test-automation/reports/${report.id}/download`;
    link.download = `${report.name}_report.html`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    message.success('报告下载已开始');
  };

  const getStatusColor = (status: string) => {
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
        <Tag color={getFormatColor(format)}>
          {format.toUpperCase()}
        </Tag>
      )
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 80,
      render: (status: string) => (
        <Tag color={getStatusColor(status)}>
          {status.toUpperCase()}
        </Tag>
      )
    },
    {
      title: '测试用例',
      dataIndex: 'test_cases',
      key: 'test_cases',
      width: 120,
      render: (testCases: any) => (
        <div>
          <Text style={{ fontSize: '12px' }}>
            总计: {testCases.total}
          </Text>
          <br />
          <Space size={4}>
            <Tag color="success" style={{ fontSize: '10px', padding: '0 4px' }}>
              {testCases.passed}
            </Tag>
            <Tag color="error" style={{ fontSize: '10px', padding: '0 4px' }}>
              {testCases.failed}
            </Tag>
            <Tag color="warning" style={{ fontSize: '10px', padding: '0 4px' }}>
              {testCases.skipped}
            </Tag>
          </Space>
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
      width: 150,
      render: (_, record: TestReport) => (
        <Space size="small">
          <Button
            type="primary"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => handleViewReport(record)}
          >
            查看
          </Button>
          <Button
            size="small"
            icon={<DownloadOutlined />}
            onClick={() => handleDownloadReport(record)}
          >
            下载
          </Button>
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
        {/* 统计信息 */}
        {statistics && (
          <Row gutter={16} style={{ marginBottom: 24 }}>
            <Col span={6}>
              <Card>
                <Statistic
                  title="总报告数"
                  value={statistics.total_reports}
                  prefix={<FileTextOutlined />}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="最近7天"
                  value={statistics.recent_reports}
                  prefix={<CalendarOutlined />}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="成功率"
                  value={statistics.success_rate}
                  precision={1}
                  suffix="%"
                  prefix={<BarChartOutlined />}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="平均耗时"
                  value={statistics.average_duration}
                  precision={1}
                  suffix="s"
                />
              </Card>
            </Col>
          </Row>
        )}

        {/* 搜索和过滤 */}
        <Card style={{ marginBottom: 16 }}>
          <div className="compact-search-bar">
            <Input
              placeholder="搜索报告名称"
              prefix={<SearchOutlined />}
              value={searchParams.query}
              onChange={(e) => setSearchParams({
                ...searchParams,
                query: e.target.value
              })}
              style={{ width: 180 }}
              size="small"
              allowClear
            />
            <Select
              placeholder="状态"
              style={{ width: 90 }}
              value={searchParams.status}
              onChange={(value) => setSearchParams({
                ...searchParams,
                status: value
              })}
              allowClear
              size="small"
            >
              <Option value="passed">通过</Option>
              <Option value="failed">失败</Option>
              <Option value="skipped">跳过</Option>
            </Select>
            <Select
              placeholder="格式"
              style={{ width: 90 }}
              value={searchParams.script_format}
              onChange={(value) => setSearchParams({
                ...searchParams,
                script_format: value
              })}
              allowClear
              size="small"
            >
              <Option value="yaml">YAML</Option>
              <Option value="playwright">Playwright</Option>
            </Select>
            <RangePicker
              style={{ width: 200 }}
              value={searchParams.date_range}
              onChange={(dates) => setSearchParams({
                ...searchParams,
                date_range: dates
              })}
              size="small"
            />
            <Button
              type="primary"
              icon={<SearchOutlined />}
              onClick={() => handleSearch(searchParams)}
              size="small"
            >
              搜索
            </Button>
            <Button
              icon={<ReloadOutlined />}
              onClick={() => refetchReports()}
              size="small"
            >
              刷新
            </Button>
          </div>
        </Card>

        {/* 报告列表 */}
        <Card>
          <Table
            columns={columns}
            dataSource={reportsData?.reports || []}
            rowKey="id"
            loading={isLoadingReports}
            pagination={{
              current: Math.floor(searchParams.offset / searchParams.limit) + 1,
              pageSize: searchParams.limit,
              total: reportsData?.total_count || 0,
              showSizeChanger: true,
              showQuickJumper: true,
              showTotal: (total, range) =>
                `第 ${range[0]}-${range[1]} 条，共 ${total} 条`,
              onChange: (page, pageSize) => {
                setSearchParams({
                  ...searchParams,
                  offset: (page - 1) * pageSize!,
                  limit: pageSize!
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

  const response = await fetch(`/api/v1/test-automation/reports?${queryParams}`);
  return response.json();
};

const fetchReportStatistics = async () => {
  const response = await fetch('/api/v1/test-automation/reports/statistics');
  return response.json();
};

export default TestReports;
