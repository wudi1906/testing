import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  Tag,
  Modal,
  Upload,
  Form,
  Input,
  Select,
  Checkbox,
  message,
  Popconfirm,
  Tooltip,
  Row,
  Col,
  Statistic,
  Typography
} from 'antd';
import {
  PlayCircleOutlined,
  DownloadOutlined,
  DeleteOutlined,
  EyeOutlined,
  UploadOutlined,
  SearchOutlined,
  ReloadOutlined,
  FileTextOutlined,
  CodeOutlined
} from '@ant-design/icons';
import { motion } from 'framer-motion';
import { useMutation, useQuery } from 'react-query';
import toast from 'react-hot-toast';

import {
  searchScripts,
  getScriptStatistics,
  deleteScript,
  batchExecuteScripts,
  executeScript,
  uploadScript
} from '../../services/api';
import './ScriptManager.css';

const { Title, Text } = Typography;
const { Option } = Select;
const { TextArea } = Input;

interface TestScript {
  id: string;
  name: string;
  description: string;
  script_format: 'yaml' | 'playwright';
  script_type: string;
  content: string;
  file_path: string;
  execution_count: number;
  last_execution_time?: string;
  last_execution_status?: string;
  created_at: string;
  updated_at: string;
  tags: string[];
  category?: string;
  priority: number;
}

interface ScriptManagerProps {
  onExecuteScript?: (scriptId: string) => void;
  onBatchExecute?: (scriptIds: string[]) => void;
  showUpload?: boolean; // 控制是否显示上传功能
}

const ScriptManager: React.FC<ScriptManagerProps> = ({
  onExecuteScript,
  onBatchExecute,
  showUpload = true
}) => {
  const [selectedRowKeys, setSelectedRowKeys] = useState<string[]>([]);
  const [searchParams, setSearchParams] = useState({
    query: '',
    script_format: undefined as string | undefined,
    limit: 20,
    offset: 0
  });
  const [isUploadModalVisible, setIsUploadModalVisible] = useState(false);
  const [uploadForm] = Form.useForm();

  // 获取脚本列表
  const {
    data: scriptsData,
    isLoading: isLoadingScripts,
    refetch: refetchScripts
  } = useQuery(
    ['scripts', searchParams],
    () => searchScripts(searchParams),
    {
      keepPreviousData: true
    }
  );

  // 获取脚本统计
  const { data: statistics } = useQuery(
    'script-statistics',
    getScriptStatistics
  );

  // 删除脚本
  const deleteScriptMutation = useMutation(deleteScript, {
    onSuccess: () => {
      message.success('脚本删除成功');
      refetchScripts();
    },
    onError: (error: any) => {
      message.error(`删除失败: ${error.message}`);
    }
  });

  // 批量执行
  const batchExecuteMutation = useMutation(batchExecuteScripts, {
    onSuccess: (data) => {
      message.success(`批量执行已启动，共${data.script_count}个脚本`);
      setSelectedRowKeys([]);
      if (onBatchExecute) {
        onBatchExecute(selectedRowKeys);
      }
    },
    onError: (error: any) => {
      message.error(`批量执行失败: ${error.message}`);
    }
  });

  // 上传脚本
  const uploadScriptMutation = useMutation(uploadScript, {
    onSuccess: () => {
      message.success('脚本上传成功');
      setIsUploadModalVisible(false);
      uploadForm.resetFields();
      refetchScripts();
    },
    onError: (error: any) => {
      message.error(`上传失败: ${error.message}`);
    }
  });

  const handleSearch = (values: any) => {
    setSearchParams({
      ...searchParams,
      ...values,
      offset: 0
    });
  };

  const handleExecuteScript = async (script: TestScript) => {
    if (onExecuteScript) {
      onExecuteScript(script.id);
    } else {
      // 默认执行逻辑
      try {
        const response = await executeScript(script.id);
        message.success(`脚本执行已启动: ${response.execution_id}`);
        toast.success(`执行脚本: ${script.name}`);
      } catch (error: any) {
        message.error(`执行失败: ${error.message}`);
        toast.error(`执行脚本失败: ${script.name}`);
      }
    }
  };

  const handleBatchExecute = () => {
    if (selectedRowKeys.length === 0) {
      message.warning('请选择要执行的脚本');
      return;
    }

    Modal.confirm({
      title: '批量执行确认',
      content: `确定要执行选中的 ${selectedRowKeys.length} 个脚本吗？`,
      onOk: () => {
        batchExecuteMutation.mutate({
          script_ids: selectedRowKeys,
          execution_config: {},
          parallel: false,
          continue_on_error: true
        });
      }
    });
  };

  const handleDeleteScript = (scriptId: string) => {
    deleteScriptMutation.mutate(scriptId);
  };

  const handleUploadScript = (values: any) => {
    const formData = new FormData();
    formData.append('file', values.file.file);
    formData.append('name', values.name);
    formData.append('description', values.description);
    formData.append('script_format', values.script_format);
    formData.append('category', values.category || '');
    formData.append('tags', JSON.stringify(values.tags || []));

    uploadScriptMutation.mutate(formData);
  };

  const columns = [
    {
      title: '脚本名称',
      dataIndex: 'name',
      key: 'name',
      width: 300,
      render: (text: string, record: TestScript) => (
        <div>
          <Tooltip title={text} placement="topLeft">
            <Text strong className="script-name-truncate">
              {text}
            </Text>
          </Tooltip>
          <Tooltip title={record.description} placement="bottomLeft">
            <Text type="secondary" className="script-description-truncate">
              {record.description}
            </Text>
          </Tooltip>
        </div>
      )
    },
    {
      title: '格式',
      dataIndex: 'script_format',
      key: 'script_format',
      width: 90,
      render: (format: string) => (
        <Tag color={format === 'yaml' ? 'blue' : 'green'} icon={
          format === 'yaml' ? <FileTextOutlined /> : <CodeOutlined />
        }>
          {format.toUpperCase()}
        </Tag>
      )
    },
    {
      title: '执行次数',
      dataIndex: 'execution_count',
      key: 'execution_count',
      width: 80,
      align: 'center' as const,
      render: (count: number) => (
        <Text>{count}</Text>
      )
    },
    {
      title: '最后执行',
      dataIndex: 'last_execution_time',
      key: 'last_execution_time',
      width: 140,
      render: (time: string, record: TestScript) => (
        <div>
          {time ? (
            <>
              <Text style={{ fontSize: '12px' }}>
                {new Date(time).toLocaleDateString()}
              </Text>
              <br />
              <Tag
                color={
                  record.last_execution_status === 'passed' ? 'success' :
                  record.last_execution_status === 'failed' ? 'error' : 'default'
                }
                style={{ fontSize: '10px' }}
              >
                {record.last_execution_status || '未知'}
              </Tag>
            </>
          ) : (
            <Text type="secondary" style={{ fontSize: '12px' }}>未执行</Text>
          )}
        </div>
      )
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 100,
      render: (time: string) => (
        <Text style={{ fontSize: '12px' }}>
          {new Date(time).toLocaleDateString()}
        </Text>
      )
    },
    {
      title: '操作',
      key: 'actions',
      width: 180,
      fixed: 'right' as const,
      render: (_, record: TestScript) => (
        <Space size="small">
          <Tooltip title="执行脚本">
            <Button
              type="primary"
              size="small"
              icon={<PlayCircleOutlined />}
              onClick={() => handleExecuteScript(record)}
            />
          </Tooltip>
          <Tooltip title="预览脚本">
            <Button
              size="small"
              icon={<EyeOutlined />}
              onClick={() => {
                Modal.info({
                  title: `脚本预览 - ${record.name}`,
                  content: (
                    <pre style={{ maxHeight: '400px', overflow: 'auto' }}>
                      {record.content}
                    </pre>
                  ),
                  width: 800
                });
              }}
            />
          </Tooltip>
          <Tooltip title="下载脚本">
            <Button
              size="small"
              icon={<DownloadOutlined />}
              onClick={() => {
                const blob = new Blob([record.content], { 
                  type: record.script_format === 'yaml' ? 'text/yaml' : 'text/typescript' 
                });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `${record.name}.${record.script_format === 'yaml' ? 'yaml' : 'ts'}`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
                toast.success('脚本下载成功');
              }}
            />
          </Tooltip>
          <Popconfirm
            title="确定要删除这个脚本吗？"
            onConfirm={() => handleDeleteScript(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Tooltip title="删除脚本">
              <Button
                size="small"
                danger
                icon={<DeleteOutlined />}
              />
            </Tooltip>
          </Popconfirm>
        </Space>
      )
    }
  ];

  const rowSelection = {
    selectedRowKeys,
    onChange: setSelectedRowKeys,
    getCheckboxProps: (record: TestScript) => ({
      name: record.name,
    }),
  };

  return (
    <div className="script-manager">
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
                  title="总脚本数"
                  value={statistics.total_scripts}
                  prefix={<FileTextOutlined />}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="YAML脚本"
                  value={statistics.yaml_scripts}
                  prefix={<FileTextOutlined />}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="Playwright脚本"
                  value={statistics.playwright_scripts}
                  prefix={<CodeOutlined />}
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
                />
              </Card>
            </Col>
          </Row>
        )}

        {/* 脚本列表 - 集成搜索功能 */}
        <Card>
          <Table
            rowSelection={rowSelection}
            columns={columns}
            dataSource={scriptsData?.scripts || []}
            rowKey="id"
            loading={isLoadingScripts}
            size="middle"
            scroll={{ x: 1000 }}
            title={() => (
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px', padding: '8px 0' }}>
                {/* 左侧搜索区域 - 使用直接div布局 */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flex: 1, minWidth: '280px' }}>
                  <Input
                    placeholder="搜索脚本名称或描述"
                    prefix={<SearchOutlined />}
                    style={{ width: 180 }}
                    allowClear
                    size="small"
                    value={searchParams.query}
                    onChange={(e) => setSearchParams(prev => ({ ...prev, query: e.target.value }))}
                  />
                  <Select
                    placeholder="格式"
                    style={{ width: 80 }}
                    allowClear
                    size="small"
                    value={searchParams.script_format}
                    onChange={(value) => setSearchParams(prev => ({ ...prev, script_format: value }))}
                  >
                    <Option value="yaml">YAML</Option>
                    <Option value="playwright">Playwright</Option>
                  </Select>
                  <Button
                    type="primary"
                    size="small"
                    onClick={() => handleSearch(searchParams)}
                  >
                    搜索
                  </Button>
                  <Button
                    icon={<ReloadOutlined />}
                    onClick={() => refetchScripts()}
                    size="small"
                  >
                    刷新
                  </Button>
                </div>

                {/* 右侧操作区域 */}
                <Space size="small">
                  {showUpload && (
                    <Button
                      icon={<UploadOutlined />}
                      onClick={() => setIsUploadModalVisible(true)}
                      size="small"
                    >
                      上传脚本
                    </Button>
                  )}
                  {selectedRowKeys.length > 0 && (
                    <Button
                      type="primary"
                      icon={<PlayCircleOutlined />}
                      onClick={handleBatchExecute}
                      loading={batchExecuteMutation.isLoading}
                      size="small"
                    >
                      批量执行 ({selectedRowKeys.length})
                    </Button>
                  )}
                </Space>
              </div>
            )}
            pagination={{
              current: Math.floor(searchParams.offset / searchParams.limit) + 1,
              pageSize: searchParams.limit,
              total: scriptsData?.total_count || 0,
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
              },
              pageSizeOptions: ['10', '20', '50', '100'],
              size: 'small'
            }}
          />
        </Card>

        {/* 上传脚本模态框 */}
        {showUpload && (
          <Modal
            title="上传测试脚本"
            open={isUploadModalVisible}
            onCancel={() => setIsUploadModalVisible(false)}
            footer={null}
            width={600}
          >
          <Form
            form={uploadForm}
            layout="vertical"
            onFinish={handleUploadScript}
          >
            <Form.Item
              name="file"
              label="选择脚本文件"
              rules={[{ required: true, message: '请选择脚本文件' }]}
            >
              <Upload
                beforeUpload={() => false}
                accept=".yaml,.yml,.ts,.js"
                maxCount={1}
              >
                <Button icon={<UploadOutlined />}>选择文件</Button>
              </Upload>
            </Form.Item>

            <Form.Item
              name="name"
              label="脚本名称"
              rules={[{ required: true, message: '请输入脚本名称' }]}
            >
              <Input placeholder="输入脚本名称" />
            </Form.Item>

            <Form.Item
              name="description"
              label="脚本描述"
              rules={[{ required: true, message: '请输入脚本描述' }]}
            >
              <TextArea rows={3} placeholder="输入脚本描述" />
            </Form.Item>

            <Form.Item
              name="script_format"
              label="脚本格式"
              rules={[{ required: true, message: '请选择脚本格式' }]}
            >
              <Select placeholder="选择脚本格式">
                <Option value="yaml">YAML (MidScene.js)</Option>
                <Option value="playwright">Playwright + MidScene.js</Option>
              </Select>
            </Form.Item>

            <Form.Item name="category" label="分类">
              <Input placeholder="输入分类（可选）" />
            </Form.Item>

            <Form.Item name="tags" label="标签">
              <Select
                mode="tags"
                placeholder="输入标签（可选）"
                style={{ width: '100%' }}
              />
            </Form.Item>

            <Form.Item>
              <Space>
                <Button
                  type="primary"
                  htmlType="submit"
                  loading={uploadScriptMutation.isLoading}
                >
                  上传
                </Button>
                <Button onClick={() => setIsUploadModalVisible(false)}>
                  取消
                </Button>
              </Space>
            </Form.Item>
          </Form>
          </Modal>
        )}
      </motion.div>
    </div>
  );
};

export default ScriptManager;
