import React, { useState, useEffect } from 'react';
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
  DatePicker,
  Switch,
  InputNumber,
  message,
  Popconfirm,
  Tooltip,
  Row,
  Col,
  Statistic,
  Typography,
  Divider,
  Badge
} from 'antd';
import {
  PlayCircleOutlined,
  PauseCircleOutlined,
  DeleteOutlined,
  EditOutlined,
  PlusOutlined,
  ReloadOutlined,
  ClockCircleOutlined,
  SettingOutlined,
  HistoryOutlined,
  SearchOutlined,
  CalendarOutlined,
  ThunderboltOutlined
} from '@ant-design/icons';
import { motion } from 'framer-motion';
import dayjs from 'dayjs';
import {
  searchScheduledTasks,
  getTaskStatistics,
  createScheduledTask,
  updateScheduledTask,
  deleteScheduledTask,
  executeScheduledTask,
  pauseScheduledTask,
  resumeScheduledTask,
  enableScheduledTask,
  disableScheduledTask,
  getAvailableScripts,
  type ScheduledTask as ScheduledTaskType,
  type TaskStatistics as TaskStatisticsType,
  type TaskCreateRequest,
  type TaskUpdateRequest
} from '../../../services/scheduledTasksApi';
import './ScheduledTasks.css';

const { Title, Text } = Typography;
const { Option } = Select;
const { TextArea } = Input;
const { RangePicker } = DatePicker;

// 使用从API服务导入的类型
type ScheduledTask = ScheduledTaskType;
type TaskStatistics = TaskStatisticsType;

interface Script {
  id: string;
  name: string;
  description?: string;
  script_format: string;
}

const ScheduledTasks: React.FC = () => {
  const [tasks, setTasks] = useState<ScheduledTask[]>([]);
  const [statistics, setStatistics] = useState<TaskStatistics | null>(null);
  const [scripts, setScripts] = useState<Script[]>([]);
  const [loading, setLoading] = useState(false);
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [editingTask, setEditingTask] = useState<ScheduledTask | null>(null);
  const [searchParams, setSearchParams] = useState({
    query: '',
    status: undefined as string | undefined,
    schedule_type: undefined as string | undefined,
    is_enabled: undefined as boolean | undefined,
    limit: 20,
    offset: 0
  });
  const [form] = Form.useForm();

  // 加载任务列表
  const loadTasks = async () => {
    setLoading(true);
    try {
      const data = await searchScheduledTasks(searchParams);
      setTasks(data.tasks || []);
    } catch (error) {
      console.error('加载任务列表失败:', error);
      message.error('加载任务列表失败');
    } finally {
      setLoading(false);
    }
  };

  // 加载统计信息
  const loadStatistics = async () => {
    try {
      const data = await getTaskStatistics();
      setStatistics(data);
    } catch (error) {
      console.error('加载统计信息失败:', error);
    }
  };

  // 加载脚本列表
  const loadScripts = async () => {
    try {
      const data = await getAvailableScripts();
      setScripts(data);
    } catch (error) {
      console.error('加载脚本列表失败:', error);
    }
  };

  useEffect(() => {
    loadTasks();
    loadStatistics();
    loadScripts();
  }, [searchParams]);

  // 创建/更新任务
  const handleSubmit = async (values: any) => {
    try {
      // 处理时间字段
      const submitData = {
        ...values,
        scheduled_time: values.scheduled_time ? values.scheduled_time.toISOString() : undefined,
        start_time: values.time_range?.[0]?.toISOString(),
        end_time: values.time_range?.[1]?.toISOString()
      };
      delete submitData.time_range;

      if (editingTask) {
        await updateScheduledTask(editingTask.id, submitData as TaskUpdateRequest);
        message.success('任务更新成功');
      } else {
        await createScheduledTask(submitData as TaskCreateRequest);
        message.success('任务创建成功');
      }

      setIsModalVisible(false);
      setEditingTask(null);
      form.resetFields();
      loadTasks();
      loadStatistics();
    } catch (error) {
      console.error('提交失败:', error);
      message.error('操作失败');
    }
  };

  // 删除任务
  const handleDelete = async (taskId: string) => {
    try {
      await deleteScheduledTask(taskId);
      message.success('任务删除成功');
      loadTasks();
      loadStatistics();
    } catch (error) {
      console.error('删除失败:', error);
      message.error('删除失败');
    }
  };

  // 执行任务
  const handleExecute = async (taskId: string) => {
    try {
      await executeScheduledTask(taskId);
      message.success('任务执行已启动');
      loadTasks();
    } catch (error) {
      console.error('执行失败:', error);
      message.error('执行失败');
    }
  };

  // 暂停/恢复任务
  const handleTogglePause = async (task: ScheduledTask) => {
    try {
      if (task.status === 'active') {
        await pauseScheduledTask(task.id);
        message.success('任务已暂停');
      } else {
        await resumeScheduledTask(task.id);
        message.success('任务已恢复');
      }
      loadTasks();
      loadStatistics();
    } catch (error) {
      console.error('操作失败:', error);
      message.error('操作失败');
    }
  };

  // 启用/禁用任务
  const handleToggleEnable = async (task: ScheduledTask) => {
    try {
      if (task.is_enabled) {
        await disableScheduledTask(task.id);
        message.success('任务已禁用');
      } else {
        await enableScheduledTask(task.id);
        message.success('任务已启用');
      }
      loadTasks();
      loadStatistics();
    } catch (error) {
      console.error('操作失败:', error);
      message.error('操作失败');
    }
  };

  // 打开编辑模态框
  const handleEdit = (task: ScheduledTask) => {
    setEditingTask(task);
    form.setFieldsValue({
      ...task,
      scheduled_time: task.scheduled_time ? dayjs(task.scheduled_time) : undefined,
      time_range: task.start_time && task.end_time 
        ? [dayjs(task.start_time), dayjs(task.end_time)]
        : undefined
    });
    setIsModalVisible(true);
  };

  // 获取状态标签
  const getStatusTag = (status: string, isEnabled: boolean) => {
    if (!isEnabled) {
      return <Tag color="default">已禁用</Tag>;
    }
    
    switch (status) {
      case 'active':
        return <Tag color="green">活跃</Tag>;
      case 'paused':
        return <Tag color="orange">暂停</Tag>;
      case 'disabled':
        return <Tag color="red">禁用</Tag>;
      case 'expired':
        return <Tag color="gray">过期</Tag>;
      default:
        return <Tag>{status}</Tag>;
    }
  };

  // 获取调度类型标签
  const getScheduleTypeTag = (type: string) => {
    switch (type) {
      case 'cron':
        return <Tag color="blue" icon={<ClockCircleOutlined />}>Cron</Tag>;
      case 'interval':
        return <Tag color="cyan" icon={<ThunderboltOutlined />}>间隔</Tag>;
      case 'once':
        return <Tag color="purple" icon={<CalendarOutlined />}>一次</Tag>;
      default:
        return <Tag>{type}</Tag>;
    }
  };

  // 表格列定义
  const columns = [
    {
      title: '任务名称',
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: ScheduledTask) => (
        <div>
          <Text strong>{text}</Text>
          {record.description && (
            <div>
              <Text type="secondary" style={{ fontSize: '12px' }}>
                {record.description}
              </Text>
            </div>
          )}
        </div>
      ),
    },
    {
      title: '调度类型',
      dataIndex: 'schedule_type',
      key: 'schedule_type',
      render: (type: string, record: ScheduledTask) => (
        <div>
          {getScheduleTypeTag(type)}
          <div style={{ marginTop: 4, fontSize: '12px', color: '#666' }}>
            {type === 'cron' && record.cron_expression}
            {type === 'interval' && `${record.interval_seconds}秒`}
            {type === 'once' && record.scheduled_time && dayjs(record.scheduled_time).format('YYYY-MM-DD HH:mm')}
          </div>
        </div>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string, record: ScheduledTask) => getStatusTag(status, record.is_enabled),
    },
    {
      title: '执行统计',
      key: 'executions',
      render: (record: ScheduledTask) => (
        <div>
          <div>总计: {record.total_executions}</div>
          <div style={{ fontSize: '12px', color: '#666' }}>
            成功: {record.successful_executions} | 失败: {record.failed_executions}
          </div>
        </div>
      ),
    },
    {
      title: '下次执行',
      dataIndex: 'next_execution_time',
      key: 'next_execution_time',
      render: (time: string) => time ? dayjs(time).format('MM-DD HH:mm') : '-',
    },
    {
      title: '操作',
      key: 'actions',
      render: (record: ScheduledTask) => (
        <Space size="small">
          <Tooltip title="手动执行">
            <Button
              type="text"
              icon={<PlayCircleOutlined />}
              onClick={() => handleExecute(record.id)}
              disabled={!record.is_enabled}
            />
          </Tooltip>
          
          <Tooltip title={record.status === 'active' ? '暂停' : '恢复'}>
            <Button
              type="text"
              icon={record.status === 'active' ? <PauseCircleOutlined /> : <PlayCircleOutlined />}
              onClick={() => handleTogglePause(record)}
              disabled={!record.is_enabled}
            />
          </Tooltip>
          
          <Tooltip title="编辑">
            <Button
              type="text"
              icon={<EditOutlined />}
              onClick={() => handleEdit(record)}
            />
          </Tooltip>
          
          <Tooltip title={record.is_enabled ? '禁用' : '启用'}>
            <Button
              type="text"
              icon={<SettingOutlined />}
              onClick={() => handleToggleEnable(record)}
            />
          </Tooltip>
          
          <Popconfirm
            title="确定要删除这个定时任务吗？"
            onConfirm={() => handleDelete(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Tooltip title="删除">
              <Button
                type="text"
                danger
                icon={<DeleteOutlined />}
              />
            </Tooltip>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div className="scheduled-tasks-container">
      {/* 统计卡片 */}
      {statistics && (
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={6}>
            <Card>
              <Statistic
                title="总任务数"
                value={statistics.total_tasks}
                prefix={<ClockCircleOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="活跃任务"
                value={statistics.active_tasks}
                prefix={<Badge status="processing" />}
                valueStyle={{ color: '#3f8600' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="总执行次数"
                value={statistics.total_executions}
                prefix={<ThunderboltOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="成功率"
                value={statistics.success_rate}
                suffix="%"
                precision={1}
                valueStyle={{ color: statistics.success_rate >= 80 ? '#3f8600' : '#cf1322' }}
              />
            </Card>
          </Col>
        </Row>
      )}

      {/* 主要内容卡片 */}
      <Card
        title={
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span>
              <ClockCircleOutlined style={{ marginRight: 8 }} />
              定时任务管理
            </span>
            <Space>
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => {
                  setEditingTask(null);
                  form.resetFields();
                  setIsModalVisible(true);
                }}
              >
                创建任务
              </Button>
              <Button
                icon={<ReloadOutlined />}
                onClick={() => {
                  loadTasks();
                  loadStatistics();
                }}
              >
                刷新
              </Button>
            </Space>
          </div>
        }
      >
        {/* 搜索栏 */}
        <div style={{ marginBottom: 16 }}>
          <Row gutter={16}>
            <Col span={8}>
              <Input
                placeholder="搜索任务名称或描述"
                prefix={<SearchOutlined />}
                value={searchParams.query}
                onChange={(e) => setSearchParams({ ...searchParams, query: e.target.value, offset: 0 })}
                allowClear
              />
            </Col>
            <Col span={4}>
              <Select
                placeholder="状态"
                value={searchParams.status}
                onChange={(value) => setSearchParams({ ...searchParams, status: value, offset: 0 })}
                allowClear
                style={{ width: '100%' }}
              >
                <Option value="active">活跃</Option>
                <Option value="paused">暂停</Option>
                <Option value="disabled">禁用</Option>
                <Option value="expired">过期</Option>
              </Select>
            </Col>
            <Col span={4}>
              <Select
                placeholder="调度类型"
                value={searchParams.schedule_type}
                onChange={(value) => setSearchParams({ ...searchParams, schedule_type: value, offset: 0 })}
                allowClear
                style={{ width: '100%' }}
              >
                <Option value="cron">Cron</Option>
                <Option value="interval">间隔</Option>
                <Option value="once">一次</Option>
              </Select>
            </Col>
            <Col span={4}>
              <Select
                placeholder="启用状态"
                value={searchParams.is_enabled}
                onChange={(value) => setSearchParams({ ...searchParams, is_enabled: value, offset: 0 })}
                allowClear
                style={{ width: '100%' }}
              >
                <Option value={true}>已启用</Option>
                <Option value={false}>已禁用</Option>
              </Select>
            </Col>
          </Row>
        </div>

        {/* 任务表格 */}
        <Table
          columns={columns}
          dataSource={tasks}
          rowKey="id"
          loading={loading}
          pagination={{
            current: Math.floor(searchParams.offset / searchParams.limit) + 1,
            pageSize: searchParams.limit,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total) => `共 ${total} 条记录`,
            onChange: (page, pageSize) => {
              setSearchParams({
                ...searchParams,
                offset: (page - 1) * pageSize,
                limit: pageSize
              });
            },
          }}
        />
      </Card>

      {/* 创建/编辑模态框 */}
      <Modal
        title={editingTask ? '编辑定时任务' : '创建定时任务'}
        open={isModalVisible}
        onCancel={() => {
          setIsModalVisible(false);
          setEditingTask(null);
          form.resetFields();
        }}
        footer={null}
        width={800}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
          initialValues={{
            schedule_type: 'cron',
            timeout_seconds: 300,
            max_retries: 0,
            retry_interval_seconds: 60,
            notify_on_failure: true,
            notify_on_success: false
          }}
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="name"
                label="任务名称"
                rules={[{ required: true, message: '请输入任务名称' }]}
              >
                <Input placeholder="输入任务名称" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="script_id"
                label="关联脚本"
                rules={[{ required: true, message: '请选择关联脚本' }]}
              >
                <Select
                  placeholder="选择要执行的脚本"
                  showSearch
                  filterOption={(input, option) =>
                    (option?.children as string)?.toLowerCase().includes(input.toLowerCase())
                  }
                >
                  {scripts.map(script => (
                    <Option key={script.id} value={script.id}>
                      {script.name} ({script.script_format})
                      {script.description && (
                        <div style={{ fontSize: '12px', color: '#666' }}>
                          {script.description}
                        </div>
                      )}
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="description"
            label="任务描述"
          >
            <TextArea rows={3} placeholder="输入任务描述（可选）" />
          </Form.Item>

          <Divider>调度配置</Divider>

          <Form.Item
            name="schedule_type"
            label="调度类型"
            rules={[{ required: true, message: '请选择调度类型' }]}
          >
            <Select>
              <Option value="cron">Cron表达式</Option>
              <Option value="interval">固定间隔</Option>
              <Option value="once">一次性任务</Option>
            </Select>
          </Form.Item>

          <Form.Item
            noStyle
            shouldUpdate={(prevValues, currentValues) =>
              prevValues.schedule_type !== currentValues.schedule_type
            }
          >
            {({ getFieldValue }) => {
              const scheduleType = getFieldValue('schedule_type');
              
              if (scheduleType === 'cron') {
                return (
                  <Form.Item
                    name="cron_expression"
                    label="Cron表达式"
                    rules={[{ required: true, message: '请输入Cron表达式' }]}
                  >
                    <Input placeholder="例如: 0 9 * * * (每天上午9点)" />
                  </Form.Item>
                );
              }
              
              if (scheduleType === 'interval') {
                return (
                  <Form.Item
                    name="interval_seconds"
                    label="间隔时间（秒）"
                    rules={[{ required: true, message: '请输入间隔时间' }]}
                  >
                    <InputNumber min={1} placeholder="输入间隔秒数" style={{ width: '100%' }} />
                  </Form.Item>
                );
              }
              
              if (scheduleType === 'once') {
                return (
                  <Form.Item
                    name="scheduled_time"
                    label="执行时间"
                    rules={[{ required: true, message: '请选择执行时间' }]}
                  >
                    <DatePicker
                      showTime
                      format="YYYY-MM-DD HH:mm:ss"
                      placeholder="选择执行时间"
                      style={{ width: '100%' }}
                    />
                  </Form.Item>
                );
              }
              
              return null;
            }}
          </Form.Item>

          <Form.Item
            name="time_range"
            label="有效时间范围"
          >
            <RangePicker
              showTime
              format="YYYY-MM-DD HH:mm:ss"
              placeholder={['开始时间', '结束时间']}
              style={{ width: '100%' }}
            />
          </Form.Item>

          <Divider>执行配置</Divider>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                name="timeout_seconds"
                label="超时时间（秒）"
              >
                <InputNumber min={1} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="max_retries"
                label="最大重试次数"
              >
                <InputNumber min={0} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="retry_interval_seconds"
                label="重试间隔（秒）"
              >
                <InputNumber min={1} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <Divider>通知配置</Divider>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="notify_on_success"
                label="成功时通知"
                valuePropName="checked"
              >
                <Switch />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="notify_on_failure"
                label="失败时通知"
                valuePropName="checked"
              >
                <Switch />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item style={{ marginTop: 24, textAlign: 'right' }}>
            <Space>
              <Button onClick={() => setIsModalVisible(false)}>
                取消
              </Button>
              <Button type="primary" htmlType="submit">
                {editingTask ? '更新' : '创建'}
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default ScheduledTasks;
