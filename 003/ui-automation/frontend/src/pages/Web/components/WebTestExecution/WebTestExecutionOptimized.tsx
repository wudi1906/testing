import React, { useState, useEffect, useCallback } from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  Tag,
  Modal,
  Form,
  Input,
  Select,
  Upload,
  message,
  Tooltip,
  Progress,
  Alert,
  Row,
  Col,
  Statistic,
  Tabs,
  List,
  Typography,
  Divider
} from 'antd';
import {
  PlayCircleOutlined,
  PauseCircleOutlined,
  StopOutlined,
  EyeOutlined,
  DownloadOutlined,
  UploadOutlined,
  ReloadOutlined,
  DeleteOutlined,
  SettingOutlined,
  FileTextOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  CloseCircleOutlined
} from '@ant-design/icons';
import { motion } from 'framer-motion';
import toast from 'react-hot-toast';

import {
  searchScripts,
  executeScript,
  batchExecuteScripts,
  getScriptExecutions,
  getExecutionStatus,
  stopExecution,
  getActiveExecutions,
  getExecutionHistory,
  executeYAMLContent,
  executePlaywrightScript
} from '../../../../services/api';
import './WebTestExecutionOptimized.css';

const { TabPane } = Tabs;
const { TextArea } = Input;
const { Title, Text } = Typography;
const { Option } = Select;

interface Script {
  id: string;
  name: string;
  description: string;
  script_format: 'yaml' | 'playwright';
  script_type: string;
  tags: string[];
  category: string;
  created_at: string;
  updated_at: string;
  execution_count: number;
  last_execution_status?: string;
}

interface ExecutionRecord {
  execution_id: string;
  script_id: string;
  status: 'running' | 'completed' | 'failed' | 'stopped';
  start_time: string;
  end_time?: string;
  duration?: number;
  error_message?: string;
  results?: any;
}

const WebTestExecutionOptimized: React.FC = () => {
  // 基础状态
  const [scripts, setScripts] = useState<Script[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedScripts, setSelectedScripts] = useState<string[]>([]);
  const [activeExecutions, setActiveExecutions] = useState<ExecutionRecord[]>([]);
  const [executionHistory, setExecutionHistory] = useState<ExecutionRecord[]>([]);

  // 搜索和过滤状态
  const [searchForm] = Form.useForm();
  const [searchParams, setSearchParams] = useState({
    query: '',
    script_format: '',
    script_type: '',
    category: '',
    tags: [] as string[]
  });

  // 执行配置状态
  const [showExecutionConfig, setShowExecutionConfig] = useState(false);
  const [executionConfig, setExecutionConfig] = useState({
    parallel: false,
    max_concurrent: 3,
    continue_on_error: true,
    timeout: 300,
    environment_variables: {}
  });

  // 脚本上传状态
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [uploadForm] = Form.useForm();

  // 统计信息
  const [statistics, setStatistics] = useState({
    total_scripts: 0,
    running_executions: 0,
    success_rate: 0,
    avg_execution_time: 0
  });

  // 初始化数据
  useEffect(() => {
    loadScripts();
    loadActiveExecutions();
    loadExecutionHistory();
    
    // 定期刷新活跃执行状态
    const interval = setInterval(() => {
      loadActiveExecutions();
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  // 加载脚本列表
  const loadScripts = useCallback(async () => {
    setLoading(true);
    try {
      const response = await searchScripts({
        ...searchParams,
        limit: 100,
        offset: 0
      });
      
      setScripts(response.scripts || []);
      setStatistics(prev => ({
        ...prev,
        total_scripts: response.total_count || 0
      }));
    } catch (error: any) {
      toast.error(`加载脚本失败: ${error.message}`);
    } finally {
      setLoading(false);
    }
  }, [searchParams]);

  // 加载活跃执行
  const loadActiveExecutions = useCallback(async () => {
    try {
      const response = await getActiveExecutions();
      setActiveExecutions(response.active_executions || []);
      setStatistics(prev => ({
        ...prev,
        running_executions: response.count || 0
      }));
    } catch (error: any) {
      console.error('加载活跃执行失败:', error);
    }
  }, []);

  // 加载执行历史
  const loadExecutionHistory = useCallback(async () => {
    try {
      const response = await getExecutionHistory(50);
      setExecutionHistory(response.history || []);
      
      // 计算成功率
      const total = response.history?.length || 0;
      const successful = response.history?.filter(h => h.status === 'completed').length || 0;
      const successRate = total > 0 ? successful / total : 0;
      
      // 计算平均执行时间
      const completedExecutions = response.history?.filter(h => h.duration) || [];
      const avgTime = completedExecutions.length > 0 
        ? completedExecutions.reduce((sum, h) => sum + (h.duration || 0), 0) / completedExecutions.length
        : 0;

      setStatistics(prev => ({
        ...prev,
        success_rate: successRate,
        avg_execution_time: avgTime
      }));
    } catch (error: any) {
      console.error('加载执行历史失败:', error);
    }
  }, []);

  // 执行单个脚本
  const handleExecuteScript = useCallback(async (scriptId: string) => {
    try {
      const result = await executeScript(scriptId, {
        execution_config: executionConfig
      });
      
      if (result.status === 'started') {
        toast.success(`脚本执行已启动，执行ID: ${result.execution_id}`);
        loadActiveExecutions();
      }
    } catch (error: any) {
      toast.error(`执行失败: ${error.message}`);
    }
  }, [executionConfig]);

  // 批量执行脚本
  const handleBatchExecute = useCallback(async () => {
    if (selectedScripts.length === 0) {
      message.warning('请选择要执行的脚本');
      return;
    }

    try {
      const result = await batchExecuteScripts({
        script_ids: selectedScripts,
        parallel: executionConfig.parallel,
        max_concurrent: executionConfig.max_concurrent,
        continue_on_error: executionConfig.continue_on_error,
        execution_config: executionConfig
      });

      if (result.status === 'started') {
        toast.success(`批量执行已启动，共 ${result.script_count} 个脚本`);
        setSelectedScripts([]);
        loadActiveExecutions();
      }
    } catch (error: any) {
      toast.error(`批量执行失败: ${error.message}`);
    }
  }, [selectedScripts, executionConfig]);

  // 停止执行
  const handleStopExecution = useCallback(async (executionId: string) => {
    try {
      await stopExecution(executionId);
      toast.success('执行已停止');
      loadActiveExecutions();
      loadExecutionHistory();
    } catch (error: any) {
      toast.error(`停止执行失败: ${error.message}`);
    }
  }, []);

  // 处理搜索
  const handleSearch = useCallback(async (values: any) => {
    setSearchParams(values);
  }, []);

  // 上传并执行脚本
  const handleUploadAndExecute = useCallback(async (values: any) => {
    try {
      const { script_content, script_format } = values;
      
      let result;
      if (script_format === 'yaml') {
        result = await executeYAMLContent({
          yaml_content: script_content,
          execution_config: executionConfig
        });
      } else {
        result = await executePlaywrightScript({
          script_content: script_content,
          config: executionConfig
        });
      }

      if (result.execution_id) {
        toast.success(`脚本执行已启动，执行ID: ${result.execution_id}`);
        setShowUploadModal(false);
        uploadForm.resetFields();
        loadActiveExecutions();
      }
    } catch (error: any) {
      toast.error(`执行失败: ${error.message}`);
    }
  }, [executionConfig, uploadForm]);

  // 脚本表格列定义
  const scriptColumns = [
    {
      title: '脚本名称',
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: Script) => (
        <Space>
          <Text strong>{text}</Text>
          <Tag color={record.script_format === 'yaml' ? 'blue' : 'green'}>
            {record.script_format.toUpperCase()}
          </Tag>
        </Space>
      )
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true
    },
    {
      title: '分类',
      dataIndex: 'category',
      key: 'category',
      render: (category: string) => category && <Tag>{category}</Tag>
    },
    {
      title: '标签',
      dataIndex: 'tags',
      key: 'tags',
      render: (tags: string[]) => (
        <Space wrap>
          {tags?.slice(0, 2).map(tag => (
            <Tag key={tag} size="small">{tag}</Tag>
          ))}
          {tags?.length > 2 && <Tag size="small">+{tags.length - 2}</Tag>}
        </Space>
      )
    },
    {
      title: '执行次数',
      dataIndex: 'execution_count',
      key: 'execution_count',
      width: 100,
      render: (count: number) => <Text type="secondary">{count || 0}</Text>
    },
    {
      title: '最后状态',
      dataIndex: 'last_execution_status',
      key: 'last_execution_status',
      width: 100,
      render: (status: string) => {
        if (!status) return '-';
        const statusConfig = {
          completed: { color: 'success', icon: <CheckCircleOutlined /> },
          failed: { color: 'error', icon: <CloseCircleOutlined /> },
          running: { color: 'processing', icon: <ClockCircleOutlined /> },
          stopped: { color: 'warning', icon: <ExclamationCircleOutlined /> }
        };
        const config = statusConfig[status as keyof typeof statusConfig] || { color: 'default', icon: null };
        return <Tag color={config.color} icon={config.icon}>{status}</Tag>;
      }
    },
    {
      title: '操作',
      key: 'actions',
      width: 150,
      render: (_, record: Script) => (
        <Space>
          <Tooltip title="执行脚本">
            <Button
              type="primary"
              size="small"
              icon={<PlayCircleOutlined />}
              onClick={() => handleExecuteScript(record.id)}
            />
          </Tooltip>
          <Tooltip title="查看详情">
            <Button
              size="small"
              icon={<EyeOutlined />}
              onClick={() => {/* 查看脚本详情 */}}
            />
          </Tooltip>
        </Space>
      )
    }
  ];

  // 活跃执行表格列定义
  const executionColumns = [
    {
      title: '执行ID',
      dataIndex: 'execution_id',
      key: 'execution_id',
      width: 200,
      render: (id: string) => <Text code>{id.slice(0, 8)}...</Text>
    },
    {
      title: '脚本ID',
      dataIndex: 'script_id',
      key: 'script_id',
      width: 200,
      render: (id: string) => <Text code>{id.slice(0, 8)}...</Text>
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const statusConfig = {
          running: { color: 'processing', icon: <ClockCircleOutlined /> },
          completed: { color: 'success', icon: <CheckCircleOutlined /> },
          failed: { color: 'error', icon: <CloseCircleOutlined /> },
          stopped: { color: 'warning', icon: <ExclamationCircleOutlined /> }
        };
        const config = statusConfig[status as keyof typeof statusConfig] || { color: 'default', icon: null };
        return <Tag color={config.color} icon={config.icon}>{status}</Tag>;
      }
    },
    {
      title: '开始时间',
      dataIndex: 'start_time',
      key: 'start_time',
      render: (time: string) => new Date(time).toLocaleString()
    },
    {
      title: '持续时间',
      dataIndex: 'duration',
      key: 'duration',
      render: (duration: number) => duration ? `${duration}s` : '-'
    },
    {
      title: '操作',
      key: 'actions',
      render: (_, record: ExecutionRecord) => (
        <Space>
          {record.status === 'running' && (
            <Button
              danger
              size="small"
              icon={<StopOutlined />}
              onClick={() => handleStopExecution(record.execution_id)}
            >
              停止
            </Button>
          )}
          <Button
            size="small"
            icon={<EyeOutlined />}
            onClick={() => {/* 查看执行详情 */}}
          >
            详情
          </Button>
        </Space>
      )
    }
  ];

  return (
    <div className="web-test-execution-optimized">
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="总脚本数"
              value={statistics.total_scripts}
              prefix={<FileTextOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="运行中"
              value={statistics.running_executions}
              prefix={<ClockCircleOutlined />}
              valueStyle={{ color: '#1890ff' }}
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
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="平均执行时间"
              value={statistics.avg_execution_time}
              precision={1}
              suffix="s"
              prefix={<ClockCircleOutlined />}
            />
          </Card>
        </Col>
      </Row>

      <Card title="Web测试执行管理">
        <Tabs defaultActiveKey="scripts">
          <TabPane tab="脚本管理" key="scripts">
            {/* 脚本表格 - 集成搜索功能 */}
            <Table
              columns={scriptColumns}
              dataSource={scripts}
              rowKey="id"
              loading={loading}
              rowSelection={{
                selectedRowKeys: selectedScripts,
                onChange: setSelectedScripts
              }}
              title={() => (
                <div className="compact-table-toolbar">
                  {/* 左侧搜索区域 - 使用直接的div布局 */}
                  <div className="search-controls-row">
                    <Input
                      placeholder="搜索脚本名称或描述"
                      style={{ width: 180 }}
                      prefix={<SearchOutlined />}
                      allowClear
                      size="small"
                      value={searchParams.query}
                      onChange={(e) => setSearchParams(prev => ({ ...prev, query: e.target.value }))}
                    />
                    <Select
                      placeholder="格式"
                      style={{ width: 90 }}
                      allowClear
                      size="small"
                      value={searchParams.script_format}
                      onChange={(value) => setSearchParams(prev => ({ ...prev, script_format: value || '' }))}
                    >
                      <Option value="yaml">YAML</Option>
                      <Option value="playwright">Playwright</Option>
                    </Select>
                    <Input
                      placeholder="分类"
                      style={{ width: 80 }}
                      allowClear
                      size="small"
                      value={searchParams.category}
                      onChange={(e) => setSearchParams(prev => ({ ...prev, category: e.target.value }))}
                    />
                    <Button
                      type="primary"
                      size="small"
                      onClick={() => handleSearch(searchParams)}
                    >
                      搜索
                    </Button>
                    <Button
                      icon={<ReloadOutlined />}
                      onClick={loadScripts}
                      size="small"
                    >
                      刷新
                    </Button>
                  </div>

                  {/* 右侧操作区域 */}
                  <Space>
                    {selectedScripts.length > 0 && (
                      <Button
                        type="primary"
                        icon={<PlayCircleOutlined />}
                        onClick={handleBatchExecute}
                        size="small"
                      >
                        批量执行 ({selectedScripts.length})
                      </Button>
                    )}
                    <Button
                      icon={<UploadOutlined />}
                      onClick={() => setShowUploadModal(true)}
                      size="small"
                    >
                      上传执行
                    </Button>
                    <Button
                      icon={<SettingOutlined />}
                      onClick={() => setShowExecutionConfig(true)}
                      size="small"
                    >
                      执行配置
                    </Button>
                  </Space>
                </div>
              )}
              pagination={{
                showSizeChanger: true,
                showQuickJumper: true,
                showTotal: (total) => `共 ${total} 个脚本`,
                size: 'small'
              }}
              size="small"
            />
          </TabPane>

          <TabPane tab={`活跃执行 (${activeExecutions.length})`} key="active">
            <Table
              columns={executionColumns}
              dataSource={activeExecutions}
              rowKey="execution_id"
              pagination={false}
            />
          </TabPane>

          <TabPane tab="执行历史" key="history">
            <Table
              columns={executionColumns}
              dataSource={executionHistory}
              rowKey="execution_id"
              pagination={{
                showSizeChanger: true,
                showQuickJumper: true,
                showTotal: (total) => `共 ${total} 条记录`
              }}
            />
          </TabPane>
        </Tabs>
      </Card>

      {/* 上传执行模态框 */}
      <Modal
        title="上传并执行脚本"
        open={showUploadModal}
        onCancel={() => setShowUploadModal(false)}
        footer={null}
        width={800}
      >
        <Form form={uploadForm} onFinish={handleUploadAndExecute} layout="vertical">
          <Form.Item
            name="script_format"
            label="脚本格式"
            rules={[{ required: true, message: '请选择脚本格式' }]}
          >
            <Select placeholder="选择脚本格式">
              <Option value="yaml">YAML</Option>
              <Option value="playwright">Playwright</Option>
            </Select>
          </Form.Item>

          <Form.Item
            name="script_content"
            label="脚本内容"
            rules={[{ required: true, message: '请输入脚本内容' }]}
          >
            <TextArea rows={15} placeholder="粘贴脚本内容..." />
          </Form.Item>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" icon={<PlayCircleOutlined />}>
                执行脚本
              </Button>
              <Button onClick={() => setShowUploadModal(false)}>
                取消
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* 执行配置模态框 */}
      <Modal
        title="执行配置"
        open={showExecutionConfig}
        onCancel={() => setShowExecutionConfig(false)}
        onOk={() => setShowExecutionConfig(false)}
      >
        <Form layout="vertical" initialValues={executionConfig}>
          <Form.Item label="并行执行" valuePropName="checked">
            <input
              type="checkbox"
              checked={executionConfig.parallel}
              onChange={(e) => setExecutionConfig(prev => ({ ...prev, parallel: e.target.checked }))}
            />
          </Form.Item>
          
          <Form.Item label="最大并发数">
            <Input
              type="number"
              value={executionConfig.max_concurrent}
              onChange={(e) => setExecutionConfig(prev => ({ ...prev, max_concurrent: parseInt(e.target.value) || 3 }))}
            />
          </Form.Item>

          <Form.Item label="出错时继续" valuePropName="checked">
            <input
              type="checkbox"
              checked={executionConfig.continue_on_error}
              onChange={(e) => setExecutionConfig(prev => ({ ...prev, continue_on_error: e.target.checked }))}
            />
          </Form.Item>

          <Form.Item label="超时时间(秒)">
            <Input
              type="number"
              value={executionConfig.timeout}
              onChange={(e) => setExecutionConfig(prev => ({ ...prev, timeout: parseInt(e.target.value) || 300 }))}
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default WebTestExecutionOptimized;
