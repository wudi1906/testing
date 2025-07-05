import React, { useState, useEffect, useCallback } from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  Input,
  Select,
  Checkbox,
  Tag,
  Tooltip,
  message,
  Modal,
  Row,
  Col,
  Statistic,
  Alert,
  Typography,
  Divider,
  Badge,
  Form,
  Upload
} from 'antd';
import {
  PlayCircleOutlined,
  ReloadOutlined,
  SearchOutlined,
  SettingOutlined,
  ThunderboltOutlined,
  FileTextOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  FolderOpenOutlined,
  UploadOutlined,
  EditOutlined,
  DeleteOutlined,
  FileSearchOutlined,
  LoadingOutlined,
  SyncOutlined
} from '@ant-design/icons';
import { motion } from 'framer-motion';
import toast from 'react-hot-toast';
import CodeEditor from '../../../../components/CodeEditor';

import {
  // 数据库脚本管理API
  searchScripts,
  getScriptStatistics,
  getScript,
  updateScript,
  deleteScript,
  executeScriptFromDB,
  batchExecuteScriptsFromDB,
  uploadScriptFile,
  syncScriptsToWorkspace
} from '../../../../services/api';

const { Search } = Input;
const { Option } = Select;
const { Text, Title } = Typography;

interface DatabaseScript {
  id: string;
  name: string;
  description: string;
  content: string;
  script_format: string;
  script_type: string;
  category?: string;
  tags: string[];
  priority: number;
  created_at: string;
  updated_at: string;
  execution_count: number;
}

interface ScriptExecutionStatus {
  sessionId: string;
  status: 'running' | 'completed' | 'failed';
  startTime: string;
  endTime?: string;
  hasReport?: boolean;
}

interface ScriptManagementTabProps {
  onExecutionStart: (sessionId: string, scriptName: string) => void;
  onBatchExecutionStart: (sessionId: string, scriptNames: string[]) => void;
  executionCount?: number; // 用于触发刷新
  onExecutionComplete?: (sessionId: string, scriptName: string) => void; // 新增执行完成回调
}

const ScriptManagementTab: React.FC<ScriptManagementTabProps> = ({
  onExecutionStart,
  onBatchExecutionStart,
  executionCount,
  onExecutionComplete
}) => {
  const [scriptSource, setScriptSource] = useState<'database' | 'filesystem'>('database');
  const [scripts, setScripts] = useState<Script[]>([]);
  const [workspaceInfo, setWorkspaceInfo] = useState<WorkspaceInfo | null>(null);
  const [statistics, setStatistics] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [selectedScripts, setSelectedScripts] = useState<string[]>([]);
  const [searchText, setSearchText] = useState('');
  const [sortBy, setSortBy] = useState<'name' | 'modified' | 'size'>('modified');
  const [scriptExecutionStatuses, setScriptExecutionStatuses] = useState<Record<string, ScriptExecutionStatus>>({});
  const [showExecutionConfig, setShowExecutionConfig] = useState(false);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [editingScript, setEditingScript] = useState<DatabaseScript | null>(null);
  const [editorContent, setEditorContent] = useState('');
  const [isSavingScript, setIsSavingScript] = useState(false);
  const [isSyncingWorkspace, setIsSyncingWorkspace] = useState(false);
  const [executionConfig, setExecutionConfig] = useState({
    base_url: '',
    headed: false,
    timeout: 90,
    parallel_execution: false,
    stop_on_failure: true
  });

  // 表单实例
  const [editForm] = Form.useForm();

  // 加载数据库脚本
  const loadDatabaseScripts = useCallback(async () => {
    setLoading(true);
    try {
      const [scriptsData, statsData] = await Promise.all([
        searchScripts({
          query: searchText,
          page: 1,
          page_size: 100,
          sort_by: sortBy,
          sort_order: 'desc'
        }),
        getScriptStatistics()
      ]);

      setScripts(scriptsData.scripts);
      setStatistics(statsData);

      if (scriptsData.scripts.length === 0) {
        message.info('数据库中没有找到脚本');
      }
    } catch (error: any) {
      message.error(`加载数据库脚本失败: ${error.message}`);
      toast.error('无法连接到脚本管理服务');
    } finally {
      setLoading(false);
    }
  }, [searchText, sortBy]);

  // 加载文件系统脚本
  const loadFileSystemScripts = useCallback(async () => {
    setLoading(true);
    try {
      const [scriptsData, workspaceData] = await Promise.all([
        getAvailableScripts(),
        getWorkspaceInfo()
      ]);

      setScripts(scriptsData.scripts);
      setWorkspaceInfo(workspaceData.workspace);

      if (scriptsData.scripts.length === 0) {
        message.warning('工作空间中没有找到可执行的脚本文件');
      }
    } catch (error: any) {
      message.error(`加载文件系统脚本失败: ${error.message}`);
      toast.error('无法连接到脚本执行服务');
    } finally {
      setLoading(false);
    }
  }, []);

  // 根据脚本源加载脚本
  const loadScripts = useCallback(async () => {
    if (scriptSource === 'database') {
      await loadDatabaseScripts();
    } else {
      await loadFileSystemScripts();
    }
  }, [scriptSource, loadDatabaseScripts, loadFileSystemScripts]);

  // 更新脚本执行状态
  const updateScriptExecutionStatus = useCallback((scriptId: string, status: Partial<ScriptExecutionStatus>) => {
    setScriptExecutionStatuses(prev => ({
      ...prev,
      [scriptId]: { ...prev[scriptId], ...status } as ScriptExecutionStatus
    }));
  }, []);

  // 检查脚本报告状态
  const checkScriptReport = useCallback(async (scriptId: string): Promise<boolean> => {
    try {
      const checkUrl = `/api/v1/web/reports/script/${scriptId}/latest`;
      const response = await fetch(checkUrl);
      return response.ok;
    } catch (error) {
      console.error('检查报告状态失败:', error);
      return false;
    }
  }, []);

  // 监听执行完成，刷新脚本列表
  useEffect(() => {
    if (executionCount && executionCount > 0) {
      console.log('检测到执行完成，刷新脚本列表');
      loadScripts();
    }
  }, [executionCount, loadScripts]);



  // 删除脚本
  const handleDeleteScript = async (scriptId: string) => {
    Modal.confirm({
      title: '确认删除',
      content: '确定要删除这个脚本吗？此操作不可恢复。',
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          await deleteScript(scriptId);
          message.success('脚本删除成功');
          toast.success('脚本已删除');
          loadScripts(); // 重新加载列表
        } catch (error: any) {
          message.error(`删除脚本失败: ${error.message}`);
          toast.error('删除失败');
        }
      }
    });
  };

  // 查看最新测试报告
  const handleViewReport = async (script: Script) => {
    try {
      const scriptId = isDatabaseScript(script) ? script.id : script.name;

      // 先检查是否有报告
      const hasReport = await checkScriptReport(scriptId);

      if (hasReport) {
        // 有报告，直接打开
        const reportUrl = `/api/v1/web/reports/view/script/${scriptId}`;
        window.open(reportUrl, '_blank');

        // 更新本地状态
        updateScriptExecutionStatus(scriptId, { hasReport: true });
      } else {
        // 没有报告
        message.info(`脚本 "${script.name || scriptId}" 还没有执行过，暂无测试报告`);

        // 更新本地状态
        updateScriptExecutionStatus(scriptId, { hasReport: false });
      }
    } catch (error) {
      console.error('查看报告失败:', error);
      message.error('查看报告失败，请检查网络连接');
    }
  };

  // 处理文件上传
  const handleUploadScript = async (values: any) => {
    try {
      const result = await uploadScriptFile({
        file: values.file.file,
        name: values.name,
        description: values.description,
        script_format: values.script_format,
        category: values.category,
        tags: values.tags || []
      });

      message.success('脚本上传成功');
      toast.success(`脚本 ${values.name} 上传成功`);
      setShowUploadModal(false);
      loadScripts(); // 重新加载列表
    } catch (error: any) {
      message.error(`上传脚本失败: ${error.message}`);
      toast.error('上传失败');
    }
  };

  // 编辑脚本
  const handleEditScript = async (script: DatabaseScript) => {
    try {
      const scriptDetail = await getScript(script.id);
      setEditingScript(scriptDetail);
      setEditorContent(scriptDetail.content || '');
      editForm.setFieldsValue({
        name: scriptDetail.name,
        description: scriptDetail.description,
        category: scriptDetail.category,
        tags: scriptDetail.tags,
        priority: scriptDetail.priority
      });
      setShowEditModal(true);
    } catch (error: any) {
      message.error(`获取脚本详情失败: ${error.message}`);
    }
  };

  // 保存脚本编辑
  const handleSaveScript = async (values: any) => {
    if (!editingScript || isSavingScript) return;

    setIsSavingScript(true);
    try {
      const updateData = {
        name: values.name,
        description: values.description,
        content: editorContent, // 使用编辑器的内容
        category: values.category,
        tags: values.tags || [],
        priority: values.priority || 1
      };

      await updateScript(editingScript.id, updateData);

      message.success('脚本更新成功');
      toast.success(`脚本 ${values.name} 更新成功`);

      // 确保对话框关闭和状态重置
      setShowEditModal(false);
      setEditingScript(null);
      setEditorContent('');
      editForm.resetFields();

      // 重新加载列表
      await loadScripts();
    } catch (error: any) {
      console.error('更新脚本失败:', error);
      message.error(`更新脚本失败: ${error.message}`);
      toast.error('更新失败');
      // 发生错误时不关闭对话框，让用户可以重试
    } finally {
      setIsSavingScript(false);
    }
  };

  useEffect(() => {
    loadScripts();
  }, [loadScripts]);

  // 过滤和排序脚本
  const filteredAndSortedScripts = React.useMemo(() => {
    let filtered = scripts.filter(script =>
      script.name.toLowerCase().includes(searchText.toLowerCase())
    );

    filtered.sort((a, b) => {
      switch (sortBy) {
        case 'name':
          return a.name.localeCompare(b.name);
        case 'size':
          return b.size - a.size;
        case 'modified':
        default:
          return new Date(b.modified).getTime() - new Date(a.modified).getTime();
      }
    });

    return filtered;
  }, [scripts, searchText, sortBy]);

  // 执行单个脚本
  const handleExecuteScript = async (script: Script) => {
    try {
      const scriptId = isDatabaseScript(script) ? script.id : script.name;

      // 更新执行状态为运行中
      updateScriptExecutionStatus(scriptId, {
        sessionId: '',
        status: 'running',
        startTime: new Date().toISOString(),
        hasReport: false
      });

      if (isDatabaseScript(script)) {
        // 执行数据库脚本
        const result = await executeScriptFromDB(script.id, {
          execution_config: {
            base_url: executionConfig.base_url || undefined,
            headed: executionConfig.headed,
            timeout: executionConfig.timeout
          }
        });

        // 更新会话ID
        updateScriptExecutionStatus(scriptId, { sessionId: result.execution_id });

        toast.success(`脚本 ${script.name} 开始执行`);
        message.success(`执行ID: ${result.execution_id}`);

        onExecutionStart(result.execution_id, script.name);
      } else {
        // 执行文件系统脚本
        const config = {
          ...executionConfig,
          execution_config: JSON.stringify({
            base_url: executionConfig.base_url || undefined,
            headed: executionConfig.headed,
            timeout: executionConfig.timeout
          })
        };

        const result = await executeSingleScript({
          script_name: script.name,
          ...config
        });

        // 更新会话ID
        updateScriptExecutionStatus(scriptId, { sessionId: result.session_id });

        toast.success(`脚本 ${script.name} 开始执行`);
        message.success(`执行会话已创建: ${result.session_id}`);

        onExecutionStart(result.session_id, script.name);
      }
    } catch (error: any) {
      const scriptId = isDatabaseScript(script) ? script.id : script.name;

      // 更新执行状态为失败
      updateScriptExecutionStatus(scriptId, {
        status: 'failed',
        endTime: new Date().toISOString()
      });

      toast.error(`执行失败: ${error.message}`);
      message.error(`脚本 ${script.name} 执行失败`);
    }
  };

  // 处理脚本执行完成
  const handleScriptExecutionComplete = useCallback(async (sessionId: string, scriptName: string) => {
    console.log(`脚本执行完成: ${scriptName}, 会话ID: ${sessionId}`);

    // 找到对应的脚本
    const script = scripts.find(s =>
      scriptExecutionStatuses[s.id]?.sessionId === sessionId
    );

    if (script) {
      const scriptId = script.id;

      // 检查是否有报告生成
      const hasReport = await checkScriptReport(scriptId);

      // 更新执行状态为完成
      updateScriptExecutionStatus(scriptId, {
        status: 'completed',
        endTime: new Date().toISOString(),
        hasReport
      });

      toast.success(`脚本 ${scriptName} 执行完成`);

      // 通知父组件
      if (onExecutionComplete) {
        onExecutionComplete(sessionId, scriptName);
      }

      // 刷新脚本列表以获取最新的执行次数等信息
      setTimeout(() => {
        loadScripts();
      }, 1000);
    }
  }, [scripts, scriptExecutionStatuses, checkScriptReport, updateScriptExecutionStatus, onExecutionComplete, loadScripts]);

  // 批量执行脚本
  const handleBatchExecute = async () => {
    if (selectedScripts.length === 0) {
      message.warning('请选择要执行的脚本');
      return;
    }

    try {
      if (scriptSource === 'database') {
        // 批量执行数据库脚本
        const result = await batchExecuteScriptsFromDB({
          script_ids: selectedScripts,
          execution_config: {
            base_url: executionConfig.base_url || undefined,
            headed: executionConfig.headed,
            timeout: executionConfig.timeout
          },
          parallel: executionConfig.parallel_execution,
          continue_on_error: !executionConfig.stop_on_failure
        });

        toast.success(`批量执行已启动，共 ${selectedScripts.length} 个脚本`);
        message.success(`批量执行ID: ${result.batch_id}`);

        onBatchExecutionStart(result.batch_id, selectedScripts);
      } else {
        // 批量执行文件系统脚本
        const config = {
          script_names: selectedScripts.join(','),
          execution_config: JSON.stringify({
            base_url: executionConfig.base_url || undefined,
            headed: executionConfig.headed,
            timeout: executionConfig.timeout
          }),
          parallel_execution: executionConfig.parallel_execution,
          stop_on_failure: executionConfig.stop_on_failure
        };

        const result = await executeBatchScripts(config);

        toast.success(`批量执行已启动，共 ${selectedScripts.length} 个脚本`);
        message.success(`批量执行会话: ${result.session_id}`);

        onBatchExecutionStart(result.session_id, selectedScripts);
      }

      setSelectedScripts([]);
    } catch (error: any) {
      toast.error(`批量执行失败: ${error.message}`);
      message.error('批量执行启动失败');
    }
  };

  // 同步脚本到工作空间
  const handleSyncWorkspace = async () => {
    try {
      setIsSyncingWorkspace(true);
      const result = await syncScriptsToWorkspace();

      toast.success(`工作空间同步完成: 成功 ${result.synced_count} 个，失败 ${result.failed_count} 个`);
      message.success(`同步完成，共处理 ${result.total_scripts} 个脚本`);

      // 刷新脚本列表
      await loadScripts();
    } catch (error: any) {
      toast.error(`同步工作空间失败: ${error.message}`);
      message.error('同步工作空间失败');
    } finally {
      setIsSyncingWorkspace(false);
    }
  };

  // 格式化修改时间
  const formatModifiedTime = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    
    if (diffDays === 0) {
      return '今天 ' + date.toLocaleTimeString();
    } else if (diffDays === 1) {
      return '昨天 ' + date.toLocaleTimeString();
    } else if (diffDays < 7) {
      return `${diffDays}天前`;
    } else {
      return date.toLocaleDateString();
    }
  };

  // 获取脚本执行状态
  const getScriptExecutionStatus = (script: Script): ScriptExecutionStatus | undefined => {
    const scriptId = isDatabaseScript(script) ? script.id : script.name;
    return scriptExecutionStatuses[scriptId];
  };

  // 获取状态标签
  const getStatusTag = (status: string) => {
    switch (status) {
      case 'running':
        return <Tag color="processing" icon={<LoadingOutlined spin />}>执行中</Tag>;
      case 'completed':
        return <Tag color="success" icon={<CheckCircleOutlined />}>已完成</Tag>;
      case 'failed':
        return <Tag color="error" icon={<ExclamationCircleOutlined />}>失败</Tag>;
      default:
        return null;
    }
  };

  // 表格列定义
  const columns = [
    {
      title: '脚本名称',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: Script) => {
        const executionStatus = getScriptExecutionStatus(record);
        return (
          <Space>
            <FileTextOutlined style={{ color: '#1890ff' }} />
            <div>
              <Text strong>{name}</Text>
              {isDatabaseScript(record) && (
                <div>
                  <Tag size="small" color="blue">{record.script_format}</Tag>
                  <Tag size="small" color="green">{record.script_type}</Tag>
                  {record.category && <Tag size="small">{record.category}</Tag>}
                </div>
              )}
              {executionStatus && (
                <div style={{ marginTop: 4 }}>
                  {getStatusTag(executionStatus.status)}
                </div>
              )}
            </div>
          </Space>
        );
      },
    },
    {
      title: scriptSource === 'database' ? '描述' : '文件大小',
      dataIndex: scriptSource === 'database' ? 'description' : 'size',
      key: scriptSource === 'database' ? 'description' : 'size',
      render: (value: any, record: Script) => {
        if (scriptSource === 'database' && isDatabaseScript(record)) {
          return (
            <Tooltip title={record.description}>
              <Text type="secondary" ellipsis style={{ maxWidth: 200 }}>
                {record.description}
              </Text>
            </Tooltip>
          );
        } else if (isFileSystemScript(record)) {
          return <Text type="secondary">{formatFileSize(record.size)}</Text>;
        }
        return null;
      },
      width: 200,
    },
    {
      title: '更新时间',
      dataIndex: scriptSource === 'database' ? 'updated_at' : 'modified',
      key: 'time',
      render: (time: string) => (
        <Tooltip title={new Date(time).toLocaleString()}>
          <Text type="secondary">{formatModifiedTime(time)}</Text>
        </Tooltip>
      ),
      width: 150,
    },
    ...(scriptSource === 'database' ? [{
      title: '执行次数',
      dataIndex: 'execution_count',
      key: 'execution_count',
      render: (count: number) => (
        <Badge count={count} style={{ backgroundColor: '#52c41a' }} />
      ),
      width: 100,
    }] : []),
    {
      title: '操作',
      key: 'actions',
      render: (_: any, record: Script) => {
        const executionStatus = getScriptExecutionStatus(record);
        const isRunning = executionStatus?.status === 'running';
        const hasReport = executionStatus?.hasReport;

        return (
          <Space>
            <Button
              type="primary"
              size="small"
              icon={isRunning ? <LoadingOutlined spin /> : <PlayCircleOutlined />}
              onClick={() => handleExecuteScript(record)}
              disabled={isRunning}
              loading={isRunning}
            >
              {isRunning ? '执行中' : '执行'}
            </Button>
            <Button
              size="small"
              icon={<FileSearchOutlined />}
              onClick={() => handleViewReport(record)}
              title="查看最新测试报告"
              type={hasReport ? 'default' : 'dashed'}
              disabled={false} // 始终可点击，让用户知道是否有报告
            >
              报告
            </Button>
            <Button
              size="small"
              icon={<EditOutlined />}
              onClick={() => handleEditScript(record)}
              disabled={isRunning}
            >
              编辑
            </Button>
            <Button
              size="small"
              danger
              icon={<DeleteOutlined />}
              onClick={() => handleDeleteScript(record.id)}
              disabled={isRunning}
            >
              删除
            </Button>
          </Space>
        );
      },
      width: 220,
    },
  ];

  // 暴露执行完成处理函数给父组件
  useEffect(() => {
    // 将处理函数挂载到组件实例上，供父组件调用
    (window as any).handleScriptExecutionComplete = handleScriptExecutionComplete;

    return () => {
      // 清理
      delete (window as any).handleScriptExecutionComplete;
    };
  }, [handleScriptExecutionComplete]);

  return (
    <div className="script-management-tab">
      {/* 脚本源选择和状态卡片 */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Row gutter={16} align="middle">
          <Col span={8}>
            <Space>
              <Text strong>脚本源：</Text>
              <Select
                value={scriptSource}
                onChange={(value) => {
                  setScriptSource(value);
                  setSelectedScripts([]);
                }}
                style={{ width: 150 }}
              >
                <Option value="database">数据库脚本</Option>
                <Option value="filesystem">文件系统脚本</Option>
              </Select>
            </Space>
          </Col>
          <Col span={16}>
            <Row gutter={8}>
              {scriptSource === 'database' && statistics ? (
                <>
                  <Col span={4}>
                    <Statistic
                      title="总脚本数"
                      value={statistics.total_scripts}
                      prefix={<FileTextOutlined />}
                      valueStyle={{ fontSize: 16 }}
                    />
                  </Col>
                  <Col span={4}>
                    <Statistic
                      title="最近执行"
                      value={statistics.recent_executions}
                      prefix={<PlayCircleOutlined />}
                      valueStyle={{ fontSize: 16 }}
                    />
                  </Col>
                  <Col span={4}>
                    <Statistic
                      title="YAML脚本"
                      value={statistics.by_format?.yaml || 0}
                      valueStyle={{ fontSize: 16 }}
                    />
                  </Col>
                  <Col span={4}>
                    <Statistic
                      title="Playwright脚本"
                      value={statistics.by_format?.playwright || 0}
                      valueStyle={{ fontSize: 16 }}
                    />
                  </Col>
                </>
              ) : workspaceInfo ? (
                <>
                  <Col span={4}>
                    <Statistic
                      title="工作空间状态"
                      value={workspaceInfo.exists ? '正常' : '异常'}
                      prefix={workspaceInfo.exists ?
                        <CheckCircleOutlined style={{ color: '#52c41a' }} /> :
                        <ExclamationCircleOutlined style={{ color: '#ff4d4f' }} />
                      }
                      valueStyle={{ fontSize: 16 }}
                    />
                  </Col>
                  <Col span={4}>
                    <Statistic
                      title="可用脚本"
                      value={workspaceInfo.total_scripts}
                      prefix={<FileTextOutlined />}
                      valueStyle={{ fontSize: 16 }}
                    />
                  </Col>
                  <Col span={8}>
                    <Statistic
                      title="工作空间路径"
                      value=""
                      formatter={() => (
                        <Tooltip title={workspaceInfo.path}>
                          <Text ellipsis style={{ maxWidth: 200 }}>
                            <FolderOpenOutlined /> {workspaceInfo.path}
                          </Text>
                        </Tooltip>
                      )}
                      valueStyle={{ fontSize: 14 }}
                    />
                  </Col>
                </>
              ) : null}
              <Col span={4}>
                <Space>
                  <Button
                    icon={<ReloadOutlined />}
                    onClick={loadScripts}
                    loading={loading}
                    size="small"
                  >
                    刷新
                  </Button>
                  <Button
                    icon={<SettingOutlined />}
                    onClick={() => setShowExecutionConfig(true)}
                    size="small"
                  >
                    配置
                  </Button>
                  {scriptSource === 'database' && (
                    <>
                      <Button
                        icon={<UploadOutlined />}
                        onClick={() => setShowUploadModal(true)}
                        size="small"
                        type="primary"
                      >
                        上传
                      </Button>
                      <Button
                        icon={<SyncOutlined />}
                        onClick={handleSyncWorkspace}
                        loading={isSyncingWorkspace}
                        size="small"
                        title="同步所有脚本到工作空间"
                      >
                        同步工作空间
                      </Button>
                    </>
                  )}
                </Space>
              </Col>
            </Row>
          </Col>
        </Row>
      </Card>

      {/* 搜索和批量操作栏 */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Row gutter={16} align="middle">
          <Col span={8}>
            <Search
              placeholder="搜索脚本名称..."
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              prefix={<SearchOutlined />}
              allowClear
            />
          </Col>
          <Col span={4}>
            <Select
              value={sortBy}
              onChange={setSortBy}
              style={{ width: '100%' }}
              placeholder="排序方式"
            >
              <Option value="modified">按修改时间</Option>
              <Option value="name">按名称</Option>
              <Option value="size">按大小</Option>
            </Select>
          </Col>
          <Col span={12}>
            <Space>
              <Text type="secondary">
                已选择 {selectedScripts.length} 个脚本
              </Text>
              <Button
                type="primary"
                icon={<ThunderboltOutlined />}
                onClick={handleBatchExecute}
                disabled={selectedScripts.length === 0}
              >
                批量执行
              </Button>
              {selectedScripts.length > 0 && (
                <Button
                  onClick={() => setSelectedScripts([])}
                >
                  清空选择
                </Button>
              )}
            </Space>
          </Col>
        </Row>
      </Card>

      {/* 脚本列表表格 */}
      <Card>
        <Table
          columns={columns}
          dataSource={filteredAndSortedScripts}
          rowKey={(record) => isDatabaseScript(record) ? record.id : record.name}
          loading={loading}
          size="small"
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) =>
              `第 ${range[0]}-${range[1]} 条，共 ${total} 条脚本`
          }}
          rowSelection={{
            selectedRowKeys: selectedScripts,
            onChange: (selectedRowKeys) => {
              setSelectedScripts(selectedRowKeys as string[]);
            },
            getCheckboxProps: (record) => ({
              name: isDatabaseScript(record) ? record.id : record.name,
            }),
          }}
          locale={{
            emptyText: searchText ? '没有找到匹配的脚本' :
              scriptSource === 'database' ? '数据库中没有脚本' : '工作空间中没有可用的脚本文件'
          }}
        />
      </Card>

      {/* 执行配置模态框 */}
      <Modal
        title="执行配置"
        open={showExecutionConfig}
        onCancel={() => setShowExecutionConfig(false)}
        onOk={() => setShowExecutionConfig(false)}
        width={600}
      >
        <div style={{ padding: '16px 0' }}>
          <Row gutter={16}>
            <Col span={12}>
              <div style={{ marginBottom: 16 }}>
                <Text strong>基础URL:</Text>
                <Input
                  value={executionConfig.base_url}
                  onChange={(e) => setExecutionConfig(prev => ({
                    ...prev,
                    base_url: e.target.value
                  }))}
                  placeholder="https://example.com"
                  style={{ marginTop: 8 }}
                />
              </div>
            </Col>
            <Col span={12}>
              <div style={{ marginBottom: 16 }}>
                <Text strong>超时时间（秒）:</Text>
                <Input
                  type="number"
                  value={executionConfig.timeout}
                  onChange={(e) => setExecutionConfig(prev => ({
                    ...prev,
                    timeout: parseInt(e.target.value) || 90
                  }))}
                  style={{ marginTop: 8 }}
                />
              </div>
            </Col>
          </Row>

          <Divider />

          <Space direction="vertical" style={{ width: '100%' }}>
            <Checkbox
              checked={executionConfig.headed}
              onChange={(e) => setExecutionConfig(prev => ({
                ...prev,
                headed: e.target.checked
              }))}
            >
              有界面模式（显示浏览器窗口）
            </Checkbox>

            <Checkbox
              checked={executionConfig.parallel_execution}
              onChange={(e) => setExecutionConfig(prev => ({
                ...prev,
                parallel_execution: e.target.checked
              }))}
            >
              并行执行（批量执行时）
            </Checkbox>

            <Checkbox
              checked={executionConfig.stop_on_failure}
              onChange={(e) => setExecutionConfig(prev => ({
                ...prev,
                stop_on_failure: e.target.checked
              }))}
            >
              遇到失败时停止执行
            </Checkbox>
          </Space>
        </div>
      </Modal>

      {/* 上传脚本模态框 */}
      <Modal
        title="上传脚本文件"
        open={showUploadModal}
        onCancel={() => setShowUploadModal(false)}
        footer={null}
        width={600}
      >
        <Form
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
            <Input.TextArea rows={3} placeholder="输入脚本描述" />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
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
            </Col>
            <Col span={12}>
              <Form.Item
                name="category"
                label="分类"
              >
                <Input placeholder="输入分类（可选）" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="tags"
            label="标签"
          >
            <Select
              mode="tags"
              placeholder="输入标签（可选）"
              style={{ width: '100%' }}
            />
          </Form.Item>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                上传脚本
              </Button>
              <Button onClick={() => setShowUploadModal(false)}>
                取消
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* 编辑脚本模态框 */}
      <Modal
        title={`编辑脚本 - ${editingScript?.name || ''}`}
        open={showEditModal}
        onCancel={() => {
          setShowEditModal(false);
          setEditingScript(null);
          setEditorContent('');
          editForm.resetFields();
        }}
        footer={null}
        width={800}
        destroyOnClose
      >
        <Form
          form={editForm}
          layout="vertical"
          onFinish={handleSaveScript}
        >
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
            <Input.TextArea rows={3} placeholder="输入脚本描述" />
          </Form.Item>

          <Form.Item
            label="脚本内容"
            required
          >
            <CodeEditor
              value={editorContent}
              onChange={setEditorContent}
              language={editingScript?.script_format === 'yaml' ? 'yaml' : 'typescript'}
              height={400}
              placeholder={editingScript?.script_format === 'yaml'
                ? '# 请输入YAML格式的测试脚本\n- action: navigate\n  target: "https://example.com"'
                : '// 请输入TypeScript格式的Playwright测试脚本\nimport { test, expect } from "@playwright/test";\n\ntest("测试用例", async ({ page }) => {\n  await page.goto("https://example.com");\n});'
              }
            />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="category" label="分类">
                <Input placeholder="输入分类（可选）" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="priority" label="优先级">
                <Select placeholder="选择优先级">
                  <Option value={1}>低</Option>
                  <Option value={2}>中</Option>
                  <Option value={3}>高</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

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
                loading={isSavingScript}
                disabled={isSavingScript}
              >
                {isSavingScript ? '保存中...' : '保存更改'}
              </Button>
              <Button
                onClick={() => {
                  setShowEditModal(false);
                  setEditingScript(null);
                  setEditorContent('');
                  editForm.resetFields();
                }}
                disabled={isSavingScript}
              >
                取消
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default ScriptManagementTab;
