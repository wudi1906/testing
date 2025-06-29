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
  message,
  Tooltip,
  Drawer,
  Descriptions,
  Badge,
  Popconfirm,
  Row,
  Col,
  Statistic,
  Progress,
  Typography,
  Divider,
  Empty,
  Spin
} from 'antd';
import {
  PlusOutlined,
  EyeOutlined,
  DeleteOutlined,
  UploadOutlined,
  RobotOutlined,
  FileImageOutlined,
  InfoCircleOutlined,
  ReloadOutlined,
  DownloadOutlined,
  SearchOutlined
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import type { UploadFile, UploadProps } from 'antd/es/upload';
import { motion } from 'framer-motion';
import { pageAnalysisApi } from '../../../services/pageAnalysisApi';
import './PageManagement.css';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;

// 页面分析状态枚举
enum AnalysisStatus {
  PENDING = 'pending',
  ANALYZING = 'analyzing', 
  COMPLETED = 'completed',
  FAILED = 'failed'
}

// 页面数据接口
interface PageData {
  id: string;
  page_name: string;
  page_description: string;
  page_url?: string;
  analysis_status: AnalysisStatus;
  confidence_score: number;
  elements_count: number;
  created_at: string;
  updated_at: string;
  raw_analysis_json?: any;
  parsed_ui_elements?: any[];
}

// 页面元素接口
interface PageElement {
  id: string;
  element_name: string;
  element_type: string;
  element_description: string;
  element_data: any;
  confidence_score: number;
  is_testable: boolean;
  created_at: string;
}

const PageManagement: React.FC = () => {
  const [pages, setPages] = useState<PageData[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploadModalVisible, setUploadModalVisible] = useState(false);
  const [detailDrawerVisible, setDetailDrawerVisible] = useState(false);
  const [selectedPage, setSelectedPage] = useState<PageData | null>(null);
  const [pageElements, setPageElements] = useState<PageElement[]>([]);
  const [elementsLoading, setElementsLoading] = useState(false);
  const [uploadForm] = Form.useForm();
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [analyzing, setAnalyzing] = useState(false);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [analysisProgress, setAnalysisProgress] = useState<{
    progress: number;
    status: string;
    message: string;
  } | null>(null);

  // 页面统计数据
  const [statistics, setStatistics] = useState({
    total: 0,
    completed: 0,
    analyzing: 0,
    failed: 0
  });

  // 加载页面列表
  const loadPages = async () => {
    setLoading(true);
    try {
      const response = await pageAnalysisApi.getPageList();
      setPages(response.data || []);
      
      // 计算统计数据
      const stats = {
        total: response.data?.length || 0,
        completed: response.data?.filter(p => p.analysis_status === AnalysisStatus.COMPLETED).length || 0,
        analyzing: response.data?.filter(p => p.analysis_status === AnalysisStatus.ANALYZING).length || 0,
        failed: response.data?.filter(p => p.analysis_status === AnalysisStatus.FAILED).length || 0
      };
      setStatistics(stats);
    } catch (error) {
      message.error('加载页面列表失败');
      console.error('Load pages error:', error);
    } finally {
      setLoading(false);
    }
  };

  // 加载页面元素
  const loadPageElements = async (pageId: string) => {
    setElementsLoading(true);
    try {
      const response = await pageAnalysisApi.getPageElements(pageId);
      setPageElements(response.data || []);
    } catch (error) {
      message.error('加载页面元素失败');
      console.error('Load page elements error:', error);
    } finally {
      setElementsLoading(false);
    }
  };

  // 查看页面详情
  const handleViewDetails = async (page: PageData) => {
    setSelectedPage(page);
    setDetailDrawerVisible(true);
    await loadPageElements(page.id);
  };

  // 删除页面
  const handleDeletePage = async (pageId: string) => {
    try {
      await pageAnalysisApi.deletePage(pageId);
      message.success('删除成功');
      loadPages();
    } catch (error) {
      message.error('删除失败');
      console.error('Delete page error:', error);
    }
  };

  // 文件上传配置
  const uploadProps: UploadProps = {
    name: 'files',
    multiple: true,
    accept: 'image/*',
    beforeUpload: () => false, // 阻止自动上传
    fileList,
    onChange: ({ fileList: newFileList }) => {
      setFileList(newFileList);
    },
    onRemove: (file) => {
      setFileList(fileList.filter(f => f.uid !== file.uid));
    }
  };

  // 提交上传和分析
  const handleSubmitUpload = async () => {
    try {
      // 获取表单值，不进行验证（因为所有字段都是可选的）
      const values = uploadForm.getFieldsValue();

      if (fileList.length === 0) {
        message.error('请至少上传一个文件');
        return;
      }

      setAnalyzing(true);

      // 创建FormData，不生成默认值，保持用户输入的原始值
      const formData = new FormData();
      fileList.forEach(file => {
        if (file.originFileObj) {
          formData.append('files', file.originFileObj);
        }
      });

      // 只有当用户实际输入了值时才添加到FormData中
      if (values.description && values.description.trim()) {
        formData.append('description', values.description.trim());
      }
      if (values.page_url && values.page_url.trim()) {
        formData.append('page_url', values.page_url.trim());
      }
      if (values.page_name && values.page_name.trim()) {
        formData.append('page_name', values.page_name.trim());
      }

      // 调用上传和分析API
      const response = await pageAnalysisApi.uploadAndAnalyze(formData);

      console.log('上传响应:', response); // 调试日志

      if (response.success && response.data?.session_id) {
        const { session_id, uploaded_files, files_info } = response.data;

        message.success(`文件上传成功！已上传 ${uploaded_files?.length || files_info?.length || fileList.length} 个文件，AI分析已在后台开始`);

        // 设置当前会话ID并开始状态轮询
        setCurrentSessionId(session_id);
        startStatusPolling(session_id);

        // 立即关闭上传对话框
        setUploadModalVisible(false);
        uploadForm.resetFields();
        setFileList([]);

        // 保存会话ID到本地存储，以便页面刷新后恢复
        localStorage.setItem('currentAnalysisSession', session_id);
      } else {
        throw new Error('上传响应格式错误');
      }

    } catch (error) {
      message.error('上传失败');
      console.error('Upload error:', error);
      setAnalyzing(false);
    }
  };

  // 开始状态轮询
  const startStatusPolling = (sessionId: string) => {
    let pollCount = 0;
    const maxPolls = 300; // 最多轮询5分钟（每秒一次）

    const pollStatus = async () => {
      try {
        const response = await pageAnalysisApi.getAnalysisStatus(sessionId);

        if (response.success && response.data) {
          const { status, progress, processed_files, total_files, error } = response.data;

          // 更新进度状态
          setAnalysisProgress({
            progress: progress || 0,
            status,
            message: total_files > 0
              ? `正在分析页面元素... ${processed_files || 0}/${total_files} 个文件 (${progress || 0}%)`
              : '正在启动AI分析...',
            processed_files: processed_files || 0,
            total_files: total_files || 0
          });

          if (status === 'completed') {
            message.success(`页面分析完成！成功分析了 ${total_files} 个文件`);
            setAnalyzing(false);
            setAnalysisProgress(null);
            setCurrentSessionId(null);
            // 清理本地存储
            localStorage.removeItem('currentAnalysisSession');
            // 重新加载页面列表
            loadPages();
            return; // 停止轮询
          } else if (status === 'failed' || status === 'error') {
            message.error(`分析失败: ${error || '未知错误'}`);
            setAnalyzing(false);
            setAnalysisProgress(null);
            setCurrentSessionId(null);
            // 清理本地存储
            localStorage.removeItem('currentAnalysisSession');
            return; // 停止轮询
          }
        }

        // 继续轮询
        pollCount++;
        if (pollCount < maxPolls) {
          setTimeout(pollStatus, 1000); // 1秒后再次轮询
        } else {
          message.warning('分析超时，请手动刷新页面查看结果');
          setAnalyzing(false);
          setAnalysisProgress(null);
          setCurrentSessionId(null);
          localStorage.removeItem('currentAnalysisSession');
        }

      } catch (error) {
        console.error('状态轮询失败:', error);
        pollCount++;
        if (pollCount < maxPolls) {
          setTimeout(pollStatus, 2000); // 出错时2秒后重试
        } else {
          message.error('无法获取分析状态，请手动刷新页面');
          setAnalyzing(false);
          setAnalysisProgress(null);
          setCurrentSessionId(null);
          localStorage.removeItem('currentAnalysisSession');
        }
      }
    };

    // 开始轮询
    pollStatus();
  };

  // 获取状态标签
  const getStatusTag = (status: AnalysisStatus) => {
    const statusConfig = {
      [AnalysisStatus.PENDING]: { color: 'default', text: '待分析' },
      [AnalysisStatus.ANALYZING]: { color: 'processing', text: '分析中' },
      [AnalysisStatus.COMPLETED]: { color: 'success', text: '分析完成' },
      [AnalysisStatus.FAILED]: { color: 'error', text: '分析失败' }
    };
    
    const config = statusConfig[status];
    return <Tag color={config.color}>{config.text}</Tag>;
  };

  // 表格列定义
  const columns: ColumnsType<PageData> = [
    {
      title: '页面名称',
      dataIndex: 'page_name',
      key: 'page_name',
      width: 200,
      render: (text: string, record: PageData) => (
        <div>
          <Text strong>{text}</Text>
          {record.page_url && (
            <div>
              <Text type="secondary" style={{ fontSize: '12px' }}>
                {record.page_url}
              </Text>
            </div>
          )}
        </div>
      )
    },
    {
      title: '页面描述',
      dataIndex: 'page_description',
      key: 'page_description',
      ellipsis: true,
      render: (text: string) => (
        <Tooltip title={text}>
          <Text>{text}</Text>
        </Tooltip>
      )
    },
    {
      title: '解析状态',
      dataIndex: 'analysis_status',
      key: 'analysis_status',
      width: 120,
      render: (status: AnalysisStatus) => getStatusTag(status)
    },
    {
      title: '置信度',
      dataIndex: 'confidence_score',
      key: 'confidence_score',
      width: 120,
      render: (score: number) => (
        <div>
          <Progress 
            percent={Math.round(score * 100)} 
            size="small" 
            status={score >= 0.8 ? 'success' : score >= 0.6 ? 'normal' : 'exception'}
          />
        </div>
      )
    },
    {
      title: '元素数量',
      dataIndex: 'elements_count',
      key: 'elements_count',
      width: 100,
      render: (count: number) => (
        <Badge count={count} showZero color="#1890ff" />
      )
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (time: string) => new Date(time).toLocaleString()
    },
    {
      title: '操作',
      key: 'actions',
      width: 150,
      render: (_, record: PageData) => (
        <Space>
          <Tooltip title="查看详情">
            <Button
              type="text"
              icon={<EyeOutlined />}
              onClick={() => handleViewDetails(record)}
            />
          </Tooltip>
          <Popconfirm
            title="确定要删除这个页面吗？"
            onConfirm={() => handleDeletePage(record.id)}
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
      )
    }
  ];

  // 检查本地存储中是否有正在进行的分析任务
  const checkOngoingAnalysis = () => {
    const savedSessionId = localStorage.getItem('currentAnalysisSession');
    if (savedSessionId) {
      // 检查该会话是否仍在进行中
      pageAnalysisApi.getAnalysisStatus(savedSessionId)
        .then(response => {
          if (response.success && response.data) {
            const { status } = response.data;
            if (status === 'processing') {
              setCurrentSessionId(savedSessionId);
              setAnalyzing(true);
              startStatusPolling(savedSessionId);
              message.info('检测到正在进行的分析任务，已恢复监控');
            } else {
              // 清理已完成或失败的会话
              localStorage.removeItem('currentAnalysisSession');
            }
          }
        })
        .catch(() => {
          // 会话不存在或出错，清理本地存储
          localStorage.removeItem('currentAnalysisSession');
        });
    }
  };

  useEffect(() => {
    loadPages();
    checkOngoingAnalysis();
  }, []);

  // 保存当前分析会话到本地存储
  useEffect(() => {
    if (currentSessionId) {
      localStorage.setItem('currentAnalysisSession', currentSessionId);
    } else {
      localStorage.removeItem('currentAnalysisSession');
    }
  }, [currentSessionId]);

  return (
    <div style={{ padding: '24px' }}>
      {/* 页面标题和统计 */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
          <Col span={24}>
            <Card>
              <Row gutter={[16, 16]} align="middle">
                <Col flex="auto">
                  <Title level={2} style={{ margin: 0 }}>
                    <FileImageOutlined style={{ marginRight: '8px', color: '#1890ff' }} />
                    页面管理
                  </Title>
                  <Paragraph type="secondary" style={{ margin: '8px 0 0 0' }}>
                    管理和分析页面截图，使用AI智能识别页面元素
                  </Paragraph>
                </Col>
                <Col>
                  <Space>
                    <Button
                      icon={<ReloadOutlined />}
                      onClick={loadPages}
                      loading={loading}
                    >
                      刷新
                    </Button>
                    <Button
                      type="primary"
                      icon={analyzing ? <RobotOutlined /> : <PlusOutlined />}
                      onClick={() => setUploadModalVisible(true)}
                      disabled={analyzing}
                      loading={analyzing}
                    >
                      {analyzing ? 'AI分析中...' : '上传页面截图'}
                    </Button>
                  </Space>
                </Col>
              </Row>
            </Card>
          </Col>
        </Row>

        {/* 分析状态显示 */}
        {analyzing && analysisProgress && (
          <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
            <Col span={24}>
              <Card>
                <Row gutter={[16, 16]} align="middle">
                  <Col flex="auto">
                    <Space direction="vertical" style={{ width: '100%' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <RobotOutlined style={{ fontSize: '20px', color: '#1890ff' }} />
                        <Title level={4} style={{ margin: 0, color: '#1890ff' }}>
                          AI分析进行中...
                        </Title>
                      </div>
                      <Progress
                        percent={analysisProgress.progress}
                        status="active"
                        strokeColor={{
                          '0%': '#108ee9',
                          '100%': '#87d068',
                        }}
                      />
                      <Text type="secondary">{analysisProgress.message}</Text>
                      {analysisProgress.total_files && (
                        <Text type="secondary">
                          正在处理: {analysisProgress.processed_files || 0} / {analysisProgress.total_files} 个文件
                        </Text>
                      )}
                    </Space>
                  </Col>
                </Row>
              </Card>
            </Col>
          </Row>
        )}

        {/* 统计卡片 */}
        <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic
                title="总页面数"
                value={statistics.total}
                prefix={<FileImageOutlined />}
                valueStyle={{ color: '#1890ff' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic
                title="分析完成"
                value={statistics.completed}
                prefix={<Badge status="success" />}
                valueStyle={{ color: '#52c41a' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic
                title="分析中"
                value={statistics.analyzing + (analyzing ? 1 : 0)}
                prefix={<Badge status="processing" />}
                valueStyle={{ color: '#1890ff' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic
                title="分析失败"
                value={statistics.failed}
                prefix={<Badge status="error" />}
                valueStyle={{ color: '#ff4d4f' }}
              />
            </Card>
          </Col>
        </Row>
      </motion.div>

      {/* 页面列表 */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.2 }}
      >
        <Card title="页面列表" extra={
          <Space>
            <Text type="secondary">共 {statistics.total} 个页面</Text>
          </Space>
        }>
          <Table
            columns={columns}
            dataSource={pages}
            rowKey="id"
            loading={loading}
            pagination={{
              total: pages.length,
              pageSize: 10,
              showSizeChanger: true,
              showQuickJumper: true,
              showTotal: (total, range) => `第 ${range[0]}-${range[1]} 条，共 ${total} 条`
            }}
            locale={{
              emptyText: (
                <Empty
                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                  description="暂无页面数据，请上传页面截图进行分析"
                />
              )
            }}
          />
        </Card>
      </motion.div>

      {/* 上传模态框 */}
      <Modal
        title={
          <Space>
            <UploadOutlined />
            上传页面截图
          </Space>
        }
        open={uploadModalVisible}
        onCancel={() => {
          setUploadModalVisible(false);
          uploadForm.resetFields();
          setFileList([]);
        }}
        footer={[
          <Button key="cancel" onClick={() => setUploadModalVisible(false)}>
            取消
          </Button>,
          <Button
            key="submit"
            type="primary"
            loading={analyzing}
            onClick={handleSubmitUpload}
            icon={<RobotOutlined />}
          >
            {analyzing ? 'AI分析中...' : '开始AI分析'}
          </Button>
        ]}
        width={600}
      >
        <Form form={uploadForm} layout="vertical">
          <Form.Item
            name="page_name"
            label="页面名称（可选）"
          >
            <Input placeholder="例如：用户登录页面、商品列表页面等" />
          </Form.Item>

          <Form.Item
            name="description"
            label="页面描述（可选）"
          >
            <TextArea
              rows={3}
              placeholder="请描述这个页面的功能、布局和主要元素，这将帮助AI更准确地识别页面元素"
            />
          </Form.Item>

          <Form.Item
            name="page_url"
            label="页面URL（可选）"
          >
            <Input placeholder="https://example.com/page" />
          </Form.Item>

          <Form.Item
            label="页面截图"
            required
            extra="这是唯一必填项，其他信息都是可选的"
          >
            <Upload.Dragger {...uploadProps}>
              <p className="ant-upload-drag-icon">
                <FileImageOutlined style={{ fontSize: '48px', color: '#1890ff' }} />
              </p>
              <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
              <p className="ant-upload-hint">
                支持单个或批量上传页面截图，支持 PNG、JPG、JPEG 格式
              </p>
            </Upload.Dragger>
          </Form.Item>
        </Form>
      </Modal>

      {/* 页面详情抽屉 */}
      <Drawer
        title={
          <Space>
            <EyeOutlined />
            页面详情
          </Space>
        }
        placement="right"
        width={800}
        open={detailDrawerVisible}
        onClose={() => {
          setDetailDrawerVisible(false);
          setSelectedPage(null);
          setPageElements([]);
        }}
      >
        {selectedPage && (
          <div>
            {/* 页面基本信息 */}
            <Card title="基本信息" style={{ marginBottom: '16px' }}>
              <Descriptions column={1}>
                <Descriptions.Item label="页面名称">
                  {selectedPage.page_name}
                </Descriptions.Item>
                <Descriptions.Item label="页面描述">
                  {selectedPage.page_description}
                </Descriptions.Item>
                {selectedPage.page_url && (
                  <Descriptions.Item label="页面URL">
                    <a href={selectedPage.page_url} target="_blank" rel="noopener noreferrer">
                      {selectedPage.page_url}
                    </a>
                  </Descriptions.Item>
                )}
                <Descriptions.Item label="解析状态">
                  {getStatusTag(selectedPage.analysis_status)}
                </Descriptions.Item>
                <Descriptions.Item label="置信度">
                  <Progress 
                    percent={Math.round(selectedPage.confidence_score * 100)} 
                    size="small"
                    status={selectedPage.confidence_score >= 0.8 ? 'success' : 'normal'}
                  />
                </Descriptions.Item>
                <Descriptions.Item label="元素数量">
                  <Badge count={selectedPage.elements_count} showZero />
                </Descriptions.Item>
                <Descriptions.Item label="创建时间">
                  {new Date(selectedPage.created_at).toLocaleString()}
                </Descriptions.Item>
                <Descriptions.Item label="更新时间">
                  {new Date(selectedPage.updated_at).toLocaleString()}
                </Descriptions.Item>
              </Descriptions>
            </Card>

            {/* 页面元素列表 */}
            <Card 
              title={`页面元素 (${pageElements.length})`}
              extra={
                <Button
                  icon={<ReloadOutlined />}
                  size="small"
                  onClick={() => loadPageElements(selectedPage.id)}
                  loading={elementsLoading}
                >
                  刷新
                </Button>
              }
            >
              <Spin spinning={elementsLoading}>
                {pageElements.length > 0 ? (
                  <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
                    {pageElements.map((element, index) => (
                      <Card
                        key={element.id}
                        size="small"
                        style={{ marginBottom: '8px' }}
                        title={
                          <Space>
                            <Badge count={index + 1} size="small" />
                            <Text strong>{element.element_name}</Text>
                            <Tag color="blue">{element.element_type}</Tag>
                            {element.is_testable && <Tag color="green">可测试</Tag>}
                          </Space>
                        }
                        extra={
                          <Text type="secondary">
                            置信度: {Math.round(element.confidence_score * 100)}%
                          </Text>
                        }
                      >
                        <Paragraph ellipsis={{ rows: 2, expandable: true }}>
                          {element.element_description}
                        </Paragraph>
                        
                        {element.element_data && (
                          <details style={{ marginTop: '8px' }}>
                            <summary style={{ cursor: 'pointer', color: '#1890ff' }}>
                              查看详细数据
                            </summary>
                            <pre style={{ 
                              background: '#f5f5f5', 
                              padding: '8px', 
                              borderRadius: '4px',
                              fontSize: '12px',
                              marginTop: '8px',
                              maxHeight: '200px',
                              overflow: 'auto'
                            }}>
                              {JSON.stringify(element.element_data, null, 2)}
                            </pre>
                          </details>
                        )}
                      </Card>
                    ))}
                  </div>
                ) : (
                  <Empty description="暂无页面元素数据" />
                )}
              </Spin>
            </Card>
          </div>
        )}
      </Drawer>
    </div>
  );
};

export default PageManagement;
