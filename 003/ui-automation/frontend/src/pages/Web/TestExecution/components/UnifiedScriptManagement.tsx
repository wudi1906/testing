/**
 * 统一脚本管理组件 - 基于脚本ID的执行逻辑
 * 支持数据库脚本和文件系统脚本的统一管理和执行
 */
import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  Input,
  Select,
  Tag,
  Tooltip,
  message,
  Modal,
  Row,
  Col,
  Statistic,
  Typography,
  Badge,
  Divider,
  Switch,
  Form,
  Radio
} from 'antd';
import {
  PlayCircleOutlined,
  ReloadOutlined,
  SearchOutlined,
  SettingOutlined,
  ThunderboltOutlined,
  FileTextOutlined,
  EyeOutlined,
  DeleteOutlined,
  StopOutlined,
  InfoCircleOutlined,
  FileSearchOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined
} from '@ant-design/icons';
import { toast } from 'react-hot-toast';

// 导入API服务
import {
  executeScript,
  batchExecuteScripts,
  createExecutionMonitor,
  UnifiedExecutionMonitor
} from '../../../../services/unifiedScriptApi';
import {
  searchScripts,
  getScriptStatistics,
  getScript,
  deleteScript,
  getAvailableScripts,
  getWorkspaceInfo
} from '../../../../services/api';

const { Text } = Typography;
const { Option } = Select;

interface UnifiedScriptManagementProps {
  onExecutionStart: (sessionId: string, scriptName?: string) => void;
  onBatchExecutionStart: (sessionId: string, scriptNames: string[]) => void;
}

interface Script {
  id: string;
  name: string;
  description?: string;
  type?: 'database' | 'filesystem'; // 脚本来源类型
  format?: string;
  category?: string;
  tags?: string[];
  execution_count?: number;
  created_at?: string;
  updated_at?: string;
  size?: number;
  modified?: string;
  path?: string;
}

// 脚本执行状态接口
interface ScriptExecutionStatus {
  scriptId: string;
  sessionId: string;
  status: 'idle' | 'running' | 'completed' | 'failed' | 'stopped';
  startTime?: string;
  endTime?: string;
  hasReport?: boolean;
}

const UnifiedScriptManagement: React.FC<UnifiedScriptManagementProps> = ({
  onExecutionStart,
  onBatchExecutionStart
}) => {
  // 状态管理
  const [scripts, setScripts] = useState<Script[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedScripts, setSelectedScripts] = useState<string[]>([]);
  const [searchText, setSearchText] = useState('');
  const [statistics, setStatistics] = useState<any>(null);
  const [workspaceInfo, setWorkspaceInfo] = useState<any>(null);

  // 脚本来源选择
  const [scriptSource, setScriptSource] = useState<'all' | 'database' | 'filesystem'>('all');

  // 执行配置
  const [showExecutionConfig, setShowExecutionConfig] = useState(false);
  const [executionConfig, setExecutionConfig] = useState({
    base_url: '',
    headed: false,
    timeout: 90,
    parallel: false,
    continue_on_error: true
  });

  // 执行监控
  const [activeMonitors, setActiveMonitors] = useState<Map<string, UnifiedExecutionMonitor>>(new Map());

  // 脚本执行状态管理
  const [scriptExecutionStatuses, setScriptExecutionStatuses] = useState<Map<string, ScriptExecutionStatus>>(new Map());

  // 加载数据库脚本
  const loadDatabaseScripts = useCallback(async () => {
    try {
      const [scriptsData, statsData] = await Promise.all([
        searchScripts({
          query: searchText,
          page: 1,
          page_size: 100,
          sort_by: 'updated_at',
          sort_order: 'desc'
        }),
        getScriptStatistics()
      ]);
      
      const dbScripts: Script[] = scriptsData.scripts.map((script: any) => ({
        id: script.id,
        name: script.name,
        description: script.description,
        type: 'database' as const,
        format: script.script_format,
        category: script.category,
        tags: script.tags,
        execution_count: script.execution_count,
        created_at: script.created_at,
        updated_at: script.updated_at
      }));

      setStatistics(statsData);
      return dbScripts;
    } catch (error: any) {
      message.error(`加载数据库脚本失败: ${error.message}`);
      return [];
    }
  }, [searchText]);

  // 加载文件系统脚本
  const loadFileSystemScripts = useCallback(async () => {
    try {
      const [scriptsData, workspaceData] = await Promise.all([
        getAvailableScripts(),
        getWorkspaceInfo()
      ]);
      
      const fsScripts: Script[] = scriptsData.scripts.map((script: any) => ({
        id: script.name, // 使用文件名作为ID
        name: script.name,
        description: `文件系统脚本: ${script.name}`,
        type: 'filesystem' as const,
        format: 'playwright',
        size: script.size,
        modified: script.modified,
        path: script.path
      }));

      setWorkspaceInfo(workspaceData.workspace);
      return fsScripts;
    } catch (error: any) {
      message.error(`加载文件系统脚本失败: ${error.message}`);
      return [];
    }
  }, []);

  // 批量检查脚本报告状态
  const checkScriptsReportStatus = useCallback(async (scripts: Script[]) => {
    const reportChecks = scripts.map(async (script) => {
      try {
        const hasReport = await checkScriptReport(script.id);
        if (hasReport) {
          updateScriptExecutionStatus(script.id, { hasReport: true });
        }
      } catch (error) {
        // 忽略单个脚本的报告检查错误
        console.warn(`检查脚本 ${script.id} 报告状态失败:`, error);
      }
    });

    await Promise.allSettled(reportChecks);
  }, []);

  // 根据来源加载脚本
  const loadScriptsBySource = useCallback(async () => {
    setLoading(true);
    try {
      let allScripts: Script[] = [];

      if (scriptSource === 'all' || scriptSource === 'database') {
        // 加载数据库脚本
        const dbScripts = await loadDatabaseScripts();
        allScripts = [...allScripts, ...dbScripts];
      }

      if (scriptSource === 'all' || scriptSource === 'filesystem') {
        // 加载文件系统脚本
        const fsScripts = await loadFileSystemScripts();
        allScripts = [...allScripts, ...fsScripts];
      }

      setScripts(allScripts);

      // 异步检查脚本报告状态
      if (allScripts.length > 0) {
        checkScriptsReportStatus(allScripts);
      }

      if (allScripts.length === 0) {
        const sourceText = scriptSource === 'all' ? '所有来源' :
                          scriptSource === 'database' ? '数据库' : '文件系统';
        message.info(`没有找到来自${sourceText}的脚本`);
      }
    } catch (error: any) {
      message.error(`加载脚本失败: ${error.message}`);
      toast.error('无法连接到脚本服务');
    } finally {
      setLoading(false);
    }
  }, [scriptSource, loadDatabaseScripts, loadFileSystemScripts, checkScriptsReportStatus]);

  // 清理所有资源
  const cleanupAllResources = useCallback(() => {
    console.log('清理所有执行资源');

    // 停止所有监控器
    activeMonitors.forEach((monitor, sessionId) => {
      try {
        console.log(`停止监控器: ${sessionId}`);
        monitor.stop();
      } catch (error) {
        console.error(`停止监控器 ${sessionId} 失败:`, error);
      }
    });

    // 清空状态
    setActiveMonitors(new Map());
    setScriptExecutionStatuses(new Map());
  }, [activeMonitors]);

  // 安全的脚本加载函数
  const loadAllScripts = useCallback(async () => {
    try {
      // 刷新前先清理资源
      cleanupAllResources();

      // 等待一小段时间确保资源清理完成
      await new Promise(resolve => setTimeout(resolve, 100));

      // 重新加载脚本
      await loadScriptsBySource();
    } catch (error) {
      console.error('加载脚本失败:', error);
      message.error('加载脚本失败');
    }
  }, [loadScriptsBySource, cleanupAllResources]);

  // 获取脚本执行状态
  const getScriptExecutionStatus = (scriptId: string): ScriptExecutionStatus | null => {
    return scriptExecutionStatuses.get(scriptId) || null;
  };

  // 更新脚本执行状态
  const updateScriptExecutionStatus = (scriptId: string, updates: Partial<ScriptExecutionStatus>) => {
    setScriptExecutionStatuses(prev => {
      const newMap = new Map(prev);
      const current = newMap.get(scriptId) || {
        scriptId,
        sessionId: '',
        status: 'idle' as const
      };
      newMap.set(scriptId, { ...current, ...updates });
      return newMap;
    });
  };

  // 检查脚本是否有可用报告
  const checkScriptReport = async (scriptId: string): Promise<boolean> => {
    try {
      const response = await fetch(`/api/v1/web/reports/script/${scriptId}/latest`);
      return response.ok;
    } catch (error) {
      return false;
    }
  };

  // 组件挂载状态引用
  const isMountedRef = useRef(true);

  // 定时检查执行状态和报告
  const checkExecutionStatusAndReports = useCallback(async () => {
    // 检查组件是否还挂载
    if (!isMountedRef.current) {
      console.log('组件已卸载，跳过状态检查');
      return;
    }

    const runningStatuses = Array.from(scriptExecutionStatuses.values())
      .filter(status => status.status === 'running');

    if (runningStatuses.length === 0) return;

    console.log(`检查 ${runningStatuses.length} 个正在执行的脚本状态`);

    for (const status of runningStatuses) {
      // 再次检查组件挂载状态
      if (!isMountedRef.current) break;

      try {
        // 检查会话是否还存在
        const response = await fetch(`/api/v1/web/execution/sessions/${status.sessionId}`);
        if (response.ok) {
          const sessionInfo = await response.json();

          // 如果会话已完成，更新脚本状态
          if (sessionInfo.session_info?.status === 'completed') {
            console.log(`会话 ${status.sessionId} 已完成，更新脚本状态`);

            // 检查报告
            const hasReport = await checkScriptReport(status.scriptId);

            // 确保组件仍然挂载再更新状态
            if (isMountedRef.current) {
              updateScriptExecutionStatus(status.scriptId, {
                status: 'completed',
                endTime: new Date().toISOString(),
                hasReport
              });

              // 清理监控器
              setActiveMonitors(prev => {
                const newMap = new Map(prev);
                newMap.delete(status.sessionId);
                return newMap;
              });
            }
          }
        } else if (response.status === 404) {
          // 会话不存在，可能已完成或失败
          console.log(`会话 ${status.sessionId} 不存在，标记为完成`);

          const hasReport = await checkScriptReport(status.scriptId);

          // 确保组件仍然挂载再更新状态
          if (isMountedRef.current) {
            updateScriptExecutionStatus(status.scriptId, {
              status: 'completed',
              endTime: new Date().toISOString(),
              hasReport
            });

            setActiveMonitors(prev => {
              const newMap = new Map(prev);
              newMap.delete(status.sessionId);
              return newMap;
            });
          }
        }
      } catch (error) {
        console.error(`检查脚本 ${status.scriptId} 状态失败:`, error);
      }
    }
  }, [scriptExecutionStatuses, checkScriptReport, updateScriptExecutionStatus]);

  // 处理脚本执行完成
  const handleScriptExecutionComplete = async (scriptId: string, scriptName: string) => {
    console.log(`处理脚本执行完成: ${scriptName}`);

    try {
      // 检查是否有报告生成
      const hasReport = await checkScriptReport(scriptId);

      // 更新状态为完成
      updateScriptExecutionStatus(scriptId, {
        status: 'completed',
        endTime: new Date().toISOString(),
        hasReport
      });

      toast.success(`脚本 ${scriptName} 执行完成`);

      // 清理监控器
      const executionStatus = getScriptExecutionStatus(scriptId);
      if (executionStatus?.sessionId) {
        setActiveMonitors(prev => {
          const newMap = new Map(prev);
          newMap.delete(executionStatus.sessionId);
          return newMap;
        });
      }
    } catch (error) {
      console.error('处理脚本执行完成时出错:', error);
    }
  };

  // 处理脚本执行错误
  const handleScriptExecutionError = (scriptId: string, scriptName: string, errorMessage: string) => {
    console.log(`处理脚本执行错误: ${scriptName} - ${errorMessage}`);

    // 只有在真正的错误情况下才更新状态和显示错误
    if (errorMessage && !errorMessage.includes('event:') && !errorMessage.includes('data:')) {
      // 更新状态为失败
      updateScriptExecutionStatus(scriptId, {
        status: 'failed',
        endTime: new Date().toISOString()
      });

      toast.error(`脚本 ${scriptName} 执行失败: ${errorMessage}`);

      // 清理监控器
      const executionStatus = getScriptExecutionStatus(scriptId);
      if (executionStatus?.sessionId) {
        setActiveMonitors(prev => {
          const newMap = new Map(prev);
          newMap.delete(executionStatus.sessionId);
          return newMap;
        });
      }
    }
  };

  // 执行单个脚本
  const handleExecuteScript = async (script: Script) => {
    // 检查是否已在执行中
    const currentStatus = getScriptExecutionStatus(script.id);
    if (currentStatus?.status === 'running') {
      message.warning(`脚本 ${script.name} 正在执行中，请等待完成`);
      return;
    }

    try {
      // 更新状态为执行中
      updateScriptExecutionStatus(script.id, {
        status: 'running',
        startTime: new Date().toISOString(),
        hasReport: false
      });

      const result = await executeScript(
        script.id,
        {
          base_url: executionConfig.base_url || undefined,
          headed: executionConfig.headed,
          timeout: executionConfig.timeout
        }
      );

      toast.success(`脚本 ${script.name} 开始执行`);
      message.success(`执行会话已创建: ${result.session_id}`);

      // 更新状态，保存session ID
      updateScriptExecutionStatus(script.id, {
        sessionId: result.session_id
      });

      // 创建执行监控器
      const monitor = createExecutionMonitor(result.session_id)
        .onMessage((msg) => {
          console.log('执行消息:', msg);

          // 检查是否是最终结果消息
          if (msg.type === 'final_result' || msg.is_final) {
            console.log('收到最终结果，脚本执行完成');
            handleScriptExecutionComplete(script.id, script.name);
          }

          // 只有明确的错误类型才处理为错误
          if (msg.type === 'error' && msg.region === 'error' && msg.content && !msg.content.includes('event:')) {
            console.log('收到错误消息，脚本执行失败');
            handleScriptExecutionError(script.id, script.name, msg.content);
          }
        })
        .onStatusChange((status) => {
          console.log('状态变化:', status);
        })
        .onComplete(async () => {
          console.log('监控器完成回调触发');
          await handleScriptExecutionComplete(script.id, script.name);
        })
        .onError((error) => {
          console.error('监控器错误回调触发:', error);
          // 只有真正的网络错误或连接错误才处理
          if (error && typeof error === 'object' && error.type === 'error') {
            handleScriptExecutionError(script.id, script.name, '网络连接错误');
          }
        })
        .start();

      // 保存监控器
      setActiveMonitors(prev => new Map(prev).set(result.session_id, monitor));

      onExecutionStart(result.session_id, script.name);
    } catch (error: any) {
      toast.error(`执行失败: ${error.message}`);
      message.error(`脚本 ${script.name} 执行失败`);

      // 更新状态为失败
      updateScriptExecutionStatus(script.id, {
        status: 'failed',
        endTime: new Date().toISOString()
      });
    }
  };

  // 批量执行脚本
  const handleBatchExecute = async () => {
    if (selectedScripts.length === 0) {
      message.warning('请选择要执行的脚本');
      return;
    }

    // 检查是否有脚本正在执行中
    const runningScripts = selectedScripts.filter(scriptId => {
      const status = getScriptExecutionStatus(scriptId);
      return status?.status === 'running';
    });

    if (runningScripts.length > 0) {
      message.warning('选中的脚本中有正在执行的，请等待完成或停止后再批量执行');
      return;
    }

    try {
      const selectedScriptNames = selectedScripts.map(id => {
        const script = scripts.find(s => s.id === id);
        return script?.name || id;
      });

      // 更新所有选中脚本的状态为执行中
      selectedScripts.forEach(scriptId => {
        updateScriptExecutionStatus(scriptId, {
          status: 'running',
          startTime: new Date().toISOString(),
          hasReport: false
        });
      });

      const result = await batchExecuteScripts(
        selectedScripts,
        {
          base_url: executionConfig.base_url || undefined,
          headed: executionConfig.headed,
          timeout: executionConfig.timeout,
          parallel: executionConfig.parallel,
          continue_on_error: executionConfig.continue_on_error
        }
      );

      toast.success(`批量执行已启动，共 ${selectedScripts.length} 个脚本`);
      message.success(`批量执行会话: ${result.session_id}`);

      // 更新所有选中脚本的session ID
      selectedScripts.forEach(scriptId => {
        updateScriptExecutionStatus(scriptId, {
          sessionId: result.session_id
        });
      });

      // 创建批量执行监控器
      const monitor = createExecutionMonitor(result.session_id)
        .onMessage((msg) => {
          console.log('批量执行消息:', msg);

          // 如果消息包含特定脚本信息，更新对应脚本状态
          if (msg.script_name) {
            const script = scripts.find(s => s.name === msg.script_name);
            if (script) {
              if (msg.type === 'script_completed') {
                updateScriptExecutionStatus(script.id, {
                  status: 'completed',
                  endTime: new Date().toISOString()
                });
                // 异步检查报告状态
                checkScriptReport(script.id).then(hasReport => {
                  if (hasReport) {
                    updateScriptExecutionStatus(script.id, { hasReport: true });
                  }
                });
              } else if (msg.type === 'script_failed') {
                updateScriptExecutionStatus(script.id, {
                  status: 'failed',
                  endTime: new Date().toISOString()
                });
              }
            }
          }

          // 检查批量执行完成
          if (msg.type === 'final_result' || msg.is_final) {
            console.log('批量执行完成');
          }
        })
        .onComplete(async () => {
          toast.success('批量执行完成');

          // 批量检查所有脚本的报告状态
          const reportChecks = selectedScripts.map(async (scriptId) => {
            const hasReport = await checkScriptReport(scriptId);
            updateScriptExecutionStatus(scriptId, {
              status: 'completed',
              endTime: new Date().toISOString(),
              hasReport
            });
          });

          await Promise.allSettled(reportChecks);

          setActiveMonitors(prev => {
            const newMap = new Map(prev);
            newMap.delete(result.session_id);
            return newMap;
          });
        })
        .onError((error) => {
          console.error('批量执行错误:', error);

          // 只有真正的网络错误才处理
          if (error && typeof error === 'object' && error.type === 'error') {
            toast.error('批量执行连接失败');

            // 更新所有选中脚本状态为失败
            selectedScripts.forEach(scriptId => {
              updateScriptExecutionStatus(scriptId, {
                status: 'failed',
                endTime: new Date().toISOString()
              });
            });
          }
        })
        .start();

      // 保存监控器
      setActiveMonitors(prev => new Map(prev).set(result.session_id, monitor));

      onBatchExecutionStart(result.session_id, selectedScriptNames);
      setSelectedScripts([]);
    } catch (error: any) {
      toast.error(`批量执行失败: ${error.message}`);
      message.error('批量执行启动失败');

      // 重置所有选中脚本状态
      selectedScripts.forEach(scriptId => {
        updateScriptExecutionStatus(scriptId, {
          status: 'failed',
          endTime: new Date().toISOString()
        });
      });
    }
  };

  // 停止执行
  const handleStopExecution = async (sessionId: string) => {
    const monitor = activeMonitors.get(sessionId);
    if (monitor) {
      try {
        await monitor.stopExecution();
        toast.success('执行已停止');
        setActiveMonitors(prev => {
          const newMap = new Map(prev);
          newMap.delete(sessionId);
          return newMap;
        });
      } catch (error: any) {
        toast.error(`停止执行失败: ${error.message}`);
      }
    }
  };

  // 查看脚本详情
  const handleViewScript = async (script: Script) => {
    try {
      const scriptDetail = await getScript(script.id);
      Modal.info({
        title: `脚本详情 - ${script.name}`,
        content: (
          <div style={{ maxHeight: '400px', overflow: 'auto' }}>
            <div style={{ marginBottom: 16 }}>
              <Text strong>描述：</Text>
              <div>{script.description}</div>
            </div>
            <div style={{ marginBottom: 16 }}>
              <Text strong>标签：</Text>
              <div>
                {script.tags?.map(tag => (
                  <Tag key={tag} style={{ margin: '2px' }}>{tag}</Tag>
                ))}
              </div>
            </div>
            <div style={{ marginBottom: 16 }}>
              <Text strong>脚本内容：</Text>
              <pre style={{
                backgroundColor: '#f5f5f5',
                padding: 12,
                borderRadius: 4,
                fontSize: 12,
                maxHeight: 300,
                overflow: 'auto'
              }}>
                {scriptDetail.content}
              </pre>
            </div>
          </div>
        ),
        width: 800
      });
    } catch (error: any) {
      message.error(`获取脚本详情失败: ${error.message}`);
    }
  };

  // 删除脚本
  const handleDeleteScript = async (script: Script) => {
    Modal.confirm({
      title: '确认删除',
      content: `确定要删除脚本 "${script.name}" 吗？此操作不可恢复。`,
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          await deleteScript(script.id);
          message.success('脚本删除成功');
          toast.success('脚本已删除');
          loadAllScripts(); // 重新加载列表
        } catch (error: any) {
          message.error(`删除脚本失败: ${error.message}`);
          toast.error('删除失败');
        }
      }
    });
  };

  // 查看测试报告
  const handleViewReport = async (script: Script) => {
    try {
      // 检查是否有可用报告
      const hasReport = await checkScriptReport(script.id);
      if (!hasReport) {
        message.warning(`脚本 ${script.name} 暂无可用的测试报告`);
        return;
      }

      // 打开新窗口查看HTML报告
      const reportUrl = `/api/v1/web/reports/view/script/${script.id}`;
      window.open(reportUrl, '_blank');
      message.success('正在打开测试报告...');
    } catch (error: any) {
      message.error(`打开测试报告失败: ${error.message}`);
    }
  };

  // 停止单个脚本执行
  const handleStopScriptExecution = async (script: Script) => {
    const executionStatus = getScriptExecutionStatus(script.id);
    if (!executionStatus || executionStatus.status !== 'running') {
      message.warning('该脚本当前未在执行中');
      return;
    }

    try {
      const monitor = activeMonitors.get(executionStatus.sessionId);
      if (monitor) {
        await monitor.stopExecution();
        toast.success(`脚本 ${script.name} 执行已停止`);

        // 更新状态
        updateScriptExecutionStatus(script.id, {
          status: 'stopped',
          endTime: new Date().toISOString()
        });

        // 清理监控器
        setActiveMonitors(prev => {
          const newMap = new Map(prev);
          newMap.delete(executionStatus.sessionId);
          return newMap;
        });
      }
    } catch (error: any) {
      toast.error(`停止执行失败: ${error.message}`);
    }
  };

  // 过滤脚本
  const filteredScripts = scripts.filter(script => {
    if (!searchText) return true;
    const searchLower = searchText.toLowerCase();
    return (
      script.name.toLowerCase().includes(searchLower) ||
      script.description?.toLowerCase().includes(searchLower) ||
      script.tags?.some(tag => tag.toLowerCase().includes(searchLower))
    );
  });

  // 获取执行状态显示组件
  const getExecutionStatusDisplay = (script: Script) => {
    const executionStatus = getScriptExecutionStatus(script.id);
    if (!executionStatus || executionStatus.status === 'idle') {
      return <Tag color="default">未执行</Tag>;
    }

    switch (executionStatus.status) {
      case 'running':
        return <Tag color="processing">执行中</Tag>;
      case 'completed':
        return <Tag color="success">已完成</Tag>;
      case 'failed':
        return <Tag color="error">执行失败</Tag>;
      case 'stopped':
        return <Tag color="warning">已停止</Tag>;
      default:
        return <Tag color="default">未知状态</Tag>;
    }
  };

  // 表格列定义
  const columns = [
    {
      title: '脚本信息',
      dataIndex: 'name',
      key: 'name',
      width: '40%', // 设置脚本信息列宽度
      render: (name: string, record: Script) => (
        <Space direction="vertical" size="small">
          <Space>
            <FileTextOutlined style={{ color: '#1890ff' }} />
            <Text strong>{name}</Text>
          </Space>
          <Space size="small">
            {/* 脚本来源标识 */}
            {record.type === 'database' ? (
              <Tag color="blue">数据库</Tag>
            ) : (
              <Tag color="green">文件系统</Tag>
            )}
            {record.format && (
              <Tag>{record.format}</Tag>
            )}
            {record.category && (
              <Tag>{record.category}</Tag>
            )}
            {/* 执行状态标识 */}
            {getExecutionStatusDisplay(record)}
          </Space>
        </Space>
      ),
    },
    {
      title: '执行统计',
      key: 'stats',
      width: 100,
      align: 'center',
      render: (_: any, record: Script) => (
        <Space direction="vertical" size="small">
          {record.execution_count !== undefined && (
            <Badge count={record.execution_count} style={{ backgroundColor: '#52c41a' }} />
          )}
          {record.size && (
            <Text type="secondary" style={{ fontSize: 12 }}>
              {(record.size / 1024).toFixed(1)}KB
            </Text>
          )}
        </Space>
      ),
    },
    {
      title: '更新时间',
      key: 'time',
      width: 120,
      align: 'center',
      render: (_: any, record: Script) => {
        const time = record.updated_at || record.modified;
        return time ? (
          <Tooltip title={new Date(time).toLocaleString()}>
            <Text type="secondary" style={{ fontSize: 12 }}>
              {new Date(time).toLocaleDateString()}
            </Text>
          </Tooltip>
        ) : null;
      },
    },
    {
      title: '操作',
      key: 'actions',
      width: 300,
      align: 'center',
      render: (_: any, record: Script) => {
        const executionStatus = getScriptExecutionStatus(record.id);
        const isRunning = executionStatus?.status === 'running';
        const isCompleted = executionStatus?.status === 'completed';
        const hasReport = executionStatus?.hasReport || false;

        return (
          <Space size="small" wrap>
            {/* 执行/停止按钮 */}
            {!isRunning ? (
              <Button
                type="primary"
                size="small"
                icon={<PlayCircleOutlined />}
                onClick={() => handleExecuteScript(record)}
                disabled={isRunning}
              >
                执行
              </Button>
            ) : (
              <Button
                size="small"
                icon={<StopOutlined />}
                onClick={() => handleStopScriptExecution(record)}
                danger
                loading={isRunning}
              >
                停止
              </Button>
            )}

            {/* 描述按钮 */}
            <Button
              size="small"
              icon={<InfoCircleOutlined />}
              onClick={() => handleViewScript(record)}
            >
              描述
            </Button>

            {/* 查看按钮 */}
            <Button
              size="small"
              icon={<EyeOutlined />}
              onClick={() => handleViewScript(record)}
            >
              查看
            </Button>

            {/* 报告按钮 - 只有执行完成且有报告时才可用 */}
            <Button
              size="small"
              icon={<FileSearchOutlined />}
              onClick={() => handleViewReport(record)}
              type="primary"
              ghost
              disabled={!hasReport}
              title={hasReport ? '查看测试报告' : '暂无可用报告'}
            >
              报告
            </Button>

            {/* 删除按钮 */}
            <Button
              size="small"
              danger
              icon={<DeleteOutlined />}
              onClick={() => handleDeleteScript(record)}
              disabled={isRunning}
            >
              删除
            </Button>
          </Space>
        );
      },
    },
  ];

  // 计算执行状态统计
  const getExecutionStatistics = useCallback(() => {
    const statuses = Array.from(scriptExecutionStatuses.values());
    return {
      total: scripts.length,
      idle: scripts.length - statuses.length,
      running: statuses.filter(s => s.status === 'running').length,
      completed: statuses.filter(s => s.status === 'completed').length,
      failed: statuses.filter(s => s.status === 'failed').length,
      stopped: statuses.filter(s => s.status === 'stopped').length,
      withReports: statuses.filter(s => s.hasReport).length
    };
  }, [scripts, scriptExecutionStatuses]);

  // 初始化加载和来源变化时重新加载
  useEffect(() => {
    loadScriptsBySource();
  }, [loadScriptsBySource]);

  // 脚本来源变化时重新加载
  useEffect(() => {
    loadScriptsBySource();
  }, [scriptSource]);

  // 定时检查执行状态
  useEffect(() => {
    const interval = setInterval(() => {
      checkExecutionStatusAndReports();
    }, 5000); // 每5秒检查一次

    return () => {
      console.log('清理状态检查定时器');
      clearInterval(interval);
    };
  }, [checkExecutionStatusAndReports]);

  // 组件卸载时清理所有资源
  useEffect(() => {
    return () => {
      console.log('组件卸载，清理所有监控器和资源');

      // 标记组件已卸载
      isMountedRef.current = false;

      // 清理所有SSE连接
      activeMonitors.forEach((monitor, sessionId) => {
        try {
          console.log(`清理监控器: ${sessionId}`);
          monitor.stop();
        } catch (error) {
          console.error(`清理监控器 ${sessionId} 失败:`, error);
        }
      });

      // 清空监控器Map
      setActiveMonitors(new Map());

      // 重置执行状态
      setScriptExecutionStatuses(new Map());
    };
  }, []);

  return (
    <div className="unified-script-management">
      {/* 统计信息卡片 */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Row gutter={16} align="middle">
          <Col span={18}>
            <Row gutter={8}>
              <Col span={3}>
                <Statistic
                  title="总脚本数"
                  value={getExecutionStatistics().total}
                  prefix={<FileTextOutlined />}
                  valueStyle={{ fontSize: 16 }}
                />
              </Col>
              <Col span={3}>
                <Statistic
                  title="数据库脚本"
                  value={scripts.filter(s => s.type === 'database').length}
                  prefix={<Badge color="blue" />}
                  valueStyle={{ fontSize: 16 }}
                />
              </Col>
              <Col span={3}>
                <Statistic
                  title="文件系统脚本"
                  value={scripts.filter(s => s.type === 'filesystem').length}
                  prefix={<Badge color="green" />}
                  valueStyle={{ fontSize: 16 }}
                />
              </Col>
              <Col span={3}>
                <Statistic
                  title="执行中"
                  value={getExecutionStatistics().running}
                  prefix={<PlayCircleOutlined />}
                  valueStyle={{ fontSize: 16, color: '#1890ff' }}
                />
              </Col>
              <Col span={3}>
                <Statistic
                  title="已完成"
                  value={getExecutionStatistics().completed}
                  prefix={<CheckCircleOutlined />}
                  valueStyle={{ fontSize: 16, color: '#52c41a' }}
                />
              </Col>
              <Col span={3}>
                <Statistic
                  title="有报告"
                  value={getExecutionStatistics().withReports}
                  prefix={<FileSearchOutlined />}
                  valueStyle={{ fontSize: 16, color: '#722ed1' }}
                />
              </Col>
              <Col span={3}>
                <Statistic
                  title="活动会话"
                  value={activeMonitors.size}
                  prefix={<ThunderboltOutlined />}
                  valueStyle={{ fontSize: 16, color: '#fa8c16' }}
                />
              </Col>
            </Row>
          </Col>
          <Col span={6}>
            <Space>
              <Button
                icon={<ReloadOutlined />}
                onClick={loadAllScripts}
                loading={loading}
                size="small"
              >
                刷新脚本
              </Button>
              <Button
                icon={<CheckCircleOutlined />}
                onClick={checkExecutionStatusAndReports}
                size="small"
                type="default"
              >
                检查状态
              </Button>
              <Button
                icon={<SettingOutlined />}
                onClick={() => setShowExecutionConfig(true)}
                size="small"
              >
                配置
              </Button>
              {getExecutionStatistics().running > 0 && (
                <Badge count={getExecutionStatistics().running} size="small">
                  <Button
                    icon={<StopOutlined />}
                    size="small"
                    danger
                    onClick={() => {
                      Modal.confirm({
                        title: '确认停止所有执行',
                        content: `确定要停止所有正在执行的脚本吗？共 ${getExecutionStatistics().running} 个脚本正在执行。`,
                        okText: '停止',
                        okType: 'danger',
                        cancelText: '取消',
                        onOk: async () => {
                          const runningStatuses = Array.from(scriptExecutionStatuses.values())
                            .filter(status => status.status === 'running');

                          for (const status of runningStatuses) {
                            try {
                              const monitor = activeMonitors.get(status.sessionId);
                              if (monitor) {
                                await monitor.stopExecution();
                                updateScriptExecutionStatus(status.scriptId, {
                                  status: 'stopped',
                                  endTime: new Date().toISOString()
                                });
                              }
                            } catch (error) {
                              console.error(`停止脚本 ${status.scriptId} 失败:`, error);
                            }
                          }

                          toast.success('所有执行已停止');
                        }
                      });
                    }}
                  >
                    停止全部
                  </Button>
                </Badge>
              )}
            </Space>
          </Col>
        </Row>
      </Card>

      {/* 搜索和操作栏 */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Row gutter={16} align="middle" style={{ marginBottom: 12 }}>
          <Col span={6}>
            <Input
              placeholder="搜索脚本名称、描述或标签..."
              prefix={<SearchOutlined />}
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              allowClear
              size="small"
            />
          </Col>
          <Col span={6}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Typography.Text strong style={{ fontSize: 12, whiteSpace: 'nowrap' }}>脚本来源:</Typography.Text>
              <Radio.Group
                value={scriptSource}
                onChange={(e) => setScriptSource(e.target.value)}
                size="small"
                buttonStyle="solid"
              >
                <Radio.Button value="all">全部</Radio.Button>
                <Radio.Button value="database">数据库</Radio.Button>
                <Radio.Button value="filesystem">文件系统</Radio.Button>
              </Radio.Group>
            </div>
          </Col>
          <Col span={6}>
            <Space>
              <Text style={{ fontSize: 12 }}>已选择 {selectedScripts.length} 个脚本</Text>
              {selectedScripts.length > 0 && (
                <Button
                  type="primary"
                  icon={<ThunderboltOutlined />}
                  onClick={handleBatchExecute}
                  disabled={selectedScripts.length === 0 || selectedScripts.some(id => {
                    const status = getScriptExecutionStatus(id);
                    return status?.status === 'running';
                  })}
                  size="small"
                  title={selectedScripts.some(id => {
                    const status = getScriptExecutionStatus(id);
                    return status?.status === 'running';
                  }) ? '选中的脚本中有正在执行的，请等待完成' : '批量执行选中的脚本'}
                >
                  批量执行
                </Button>
              )}
            </Space>
          </Col>
          <Col span={6}>
            {activeMonitors.size > 0 && (
              <Space>
                <Text type="secondary" style={{ fontSize: 12 }}>活动执行:</Text>
                {Array.from(activeMonitors.keys()).map(sessionId => (
                  <Button
                    key={sessionId}
                    size="small"
                    icon={<StopOutlined />}
                    onClick={() => handleStopExecution(sessionId)}
                    danger
                  >
                    停止 {sessionId.slice(-8)}
                  </Button>
                ))}
              </Space>
            )}
          </Col>
        </Row>
      </Card>

      {/* 脚本列表表格 */}
      <Card>
        <style>
          {`
            /* 复选框列宽度控制 */
            .ant-table-selection-column {
              width: 32px !important;
              min-width: 32px !important;
              max-width: 32px !important;
              padding: 8px 4px !important;
              background-color: #fafafa !important;
              border-right: 1px solid #f0f0f0 !important;
            }

            /* 复选框样式优化 */
            .ant-table-selection-column .ant-checkbox-wrapper {
              margin: 0 !important;
              padding: 0 !important;
            }

            /* 移除hover时的阴影和变换效果 */
            .ant-table-tbody > tr:hover > td.ant-table-selection-column {
              background-color: #fafafa !important;
              box-shadow: none !important;
            }

            /* 强力移除所有复选框相关的hover和focus效果 */
            .ant-table-selection-column .ant-checkbox,
            .ant-table-selection-column .ant-checkbox *,
            .ant-table-selection-column .ant-checkbox::before,
            .ant-table-selection-column .ant-checkbox::after,
            .ant-table-selection-column .ant-checkbox:hover,
            .ant-table-selection-column .ant-checkbox:hover *,
            .ant-table-selection-column .ant-checkbox:hover::before,
            .ant-table-selection-column .ant-checkbox:hover::after,
            .ant-table-selection-column .ant-checkbox:focus,
            .ant-table-selection-column .ant-checkbox:focus *,
            .ant-table-selection-column .ant-checkbox:focus::before,
            .ant-table-selection-column .ant-checkbox:focus::after,
            .ant-table-selection-column .ant-checkbox:active,
            .ant-table-selection-column .ant-checkbox:active *,
            .ant-table-selection-column .ant-checkbox:active::before,
            .ant-table-selection-column .ant-checkbox:active::after {
              transform: none !important;
              transition: none !important;
              background: transparent !important;
              border: none !important;
              outline: none !important;
              box-shadow: none !important;
              opacity: 1 !important;
            }

            /* 移除所有伪元素 */
            .ant-table-selection-column .ant-checkbox::before,
            .ant-table-selection-column .ant-checkbox::after {
              content: none !important;
              display: none !important;
              visibility: hidden !important;
              opacity: 0 !important;
              width: 0 !important;
              height: 0 !important;
            }

            /* 只保留复选框内部的基本样式 */
            .ant-table-selection-column .ant-checkbox-inner {
              transition: none !important;
              background: white !important;
              border: 1px solid #d9d9d9 !important;
              box-shadow: none !important;
              outline: none !important;
              position: relative !important;
              z-index: 1 !important;
            }

            .ant-table-selection-column .ant-checkbox-inner:hover,
            .ant-table-selection-column .ant-checkbox-inner:focus,
            .ant-table-selection-column .ant-checkbox-inner:active {
              border-color: #d9d9d9 !important;
              box-shadow: none !important;
              background: white !important;
              outline: none !important;
            }

            /* 移除wrapper的所有效果 */
            .ant-table-selection-column .ant-checkbox-wrapper,
            .ant-table-selection-column .ant-checkbox-wrapper:hover,
            .ant-table-selection-column .ant-checkbox-wrapper:focus,
            .ant-table-selection-column .ant-checkbox-wrapper:active {
              background: none !important;
              border: none !important;
              outline: none !important;
              box-shadow: none !important;
            }

            /* 保持选中状态的正常显示 */
            .ant-table-selection-column .ant-checkbox-checked .ant-checkbox-inner {
              background-color: #1890ff !important;
              border-color: #1890ff !important;
            }

            .ant-table-selection-column .ant-checkbox-checked:hover .ant-checkbox-inner,
            .ant-table-selection-column .ant-checkbox-checked:focus .ant-checkbox-inner,
            .ant-table-selection-column .ant-checkbox-checked:active .ant-checkbox-inner {
              background-color: #1890ff !important;
              border-color: #1890ff !important;
            }

            /* 强制移除任何可能的focus ring */
            .ant-table-selection-column input[type="checkbox"],
            .ant-table-selection-column input[type="checkbox"]:hover,
            .ant-table-selection-column input[type="checkbox"]:focus,
            .ant-table-selection-column input[type="checkbox"]:active {
              outline: none !important;
              box-shadow: none !important;
              border: none !important;
              background: none !important;
            }
          `}
        </style>
        <Table
          columns={columns}
          dataSource={filteredScripts}
          rowKey="id"
          loading={loading}
          size="small"
          scroll={{ x: 'max-content' }}
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
            getCheckboxProps: (record) => {
              const executionStatus = getScriptExecutionStatus(record.id);
              const isRunning = executionStatus?.status === 'running';
              return {
                name: record.id,
                disabled: isRunning,
                title: isRunning ? '脚本正在执行中，无法选择' : undefined
              };
            },
            columnWidth: 32, // 设置复选框列宽度为32px
            fixed: 'left', // 固定在左侧
          }}
          locale={{
            emptyText: searchText ? '没有找到匹配的脚本' : '没有可用的脚本'
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
        <Form layout="vertical">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="基础URL">
                <Input
                  value={executionConfig.base_url}
                  onChange={(e) => setExecutionConfig(prev => ({
                    ...prev,
                    base_url: e.target.value
                  }))}
                  placeholder="https://example.com"
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="超时时间（秒）">
                <Input
                  type="number"
                  value={executionConfig.timeout}
                  onChange={(e) => setExecutionConfig(prev => ({
                    ...prev,
                    timeout: parseInt(e.target.value) || 90
                  }))}
                />
              </Form.Item>
            </Col>
          </Row>

          <Divider />

          <Space direction="vertical" style={{ width: '100%' }}>
            <div>
              <Text strong>执行选项</Text>
            </div>

            <Space direction="vertical">
              <div>
                <Switch
                  checked={executionConfig.headed}
                  onChange={(checked) => setExecutionConfig(prev => ({
                    ...prev,
                    headed: checked
                  }))}
                />
                <Text style={{ marginLeft: 8 }}>有界面模式（显示浏览器窗口）</Text>
              </div>

              <div>
                <Switch
                  checked={executionConfig.parallel}
                  onChange={(checked) => setExecutionConfig(prev => ({
                    ...prev,
                    parallel: checked
                  }))}
                />
                <Text style={{ marginLeft: 8 }}>并行执行（批量执行时）</Text>
              </div>

              <div>
                <Switch
                  checked={executionConfig.continue_on_error}
                  onChange={(checked) => setExecutionConfig(prev => ({
                    ...prev,
                    continue_on_error: checked
                  }))}
                />
                <Text style={{ marginLeft: 8 }}>遇到错误时继续执行</Text>
              </div>
            </Space>
          </Space>
        </Form>
      </Modal>
    </div>
  );
};

export default UnifiedScriptManagement;
