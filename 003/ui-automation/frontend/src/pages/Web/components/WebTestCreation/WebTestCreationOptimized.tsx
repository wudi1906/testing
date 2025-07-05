import React, { useState, useCallback, useEffect } from 'react';
import {
  Card,
  Tabs,
  Upload,
  Input,
  Button,
  Form,
  Select,
  Space,
  Typography,
  Alert,
  Progress,
  Divider,
  Tag,
  Row,
  Col,
  Checkbox,
  message,
  Modal,
  Spin
} from 'antd';
import {
  UploadOutlined,
  LinkOutlined,
  PlayCircleOutlined,
  DownloadOutlined,
  EyeOutlined,
  SaveOutlined,
  CodeOutlined,
  CheckCircleOutlined,
  InfoCircleOutlined
} from '@ant-design/icons';
import { motion } from 'framer-motion';
import toast from 'react-hot-toast';

import YAMLViewer from '../../../../components/YAMLViewer/YAMLViewer';
import StreamingDisplay from '../../../../components/StreamingDisplay/StreamingDisplay';
import {
  analyzeWebImage,
  analyzeWebURL,
  getGeneratedScripts,
  saveScriptFromSession,
  searchScripts,
  getScriptStatistics,
  executeScript
} from '../../../../services/api';
import { PageAnalysisApi } from '../../../../services/pageAnalysisApi';
import './WebTestCreationOptimized.css';

const { TabPane } = Tabs;
const { TextArea } = Input;
const { Title, Text } = Typography;
const { Option } = Select;

interface AnalysisResult {
  session_id: string;
  analysis_result: any;
  yaml_script: any;
  yaml_content: string;
  file_path: string;
  estimated_duration?: string;
  generated_scripts?: Array<{
    format: string;
    content: string;
    file_path: string;
  }>;
}

interface ScriptData {
  format: 'yaml' | 'playwright';
  content: string;
  filename: string;
  file_path?: string;
}

interface ScriptCollection {
  yaml?: ScriptData;
  playwright?: ScriptData;
}

const WebTestCreationOptimized: React.FC = () => {
  // 基础状态
  const [activeTab, setActiveTab] = useState('image');
  const [form] = Form.useForm();
  const [urlForm] = Form.useForm();
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [uploadedFile, setUploadedFile] = useState<any>(null);
  const [selectedFormats, setSelectedFormats] = useState<string[]>(['playwright']);
  const [currentSessionId, setCurrentSessionId] = useState<string>('');
  const [preserveStreamingContent, setPreserveStreamingContent] = useState<boolean>(false);

  // 脚本管理状态
  const [showScriptEditor, setShowScriptEditor] = useState(false);
  const [scripts, setScripts] = useState<ScriptCollection>({});
  const [activeScriptTab, setActiveScriptTab] = useState<'yaml' | 'playwright'>('playwright');
  const [isEditingScript, setIsEditingScript] = useState<{yaml: boolean, playwright: boolean}>({yaml: false, playwright: false});
  const [isSavingScript, setIsSavingScript] = useState(false);
  const [isExecutingScript, setIsExecutingScript] = useState(false);

  // 数据库保存配置 - 默认启用，UI测试自动保存
  const databaseConfig = {
    save_to_database: true,
    script_name: '',
    script_description: '',
    tags: ['UI测试', '自动化'] as string[],
    category: 'UI测试',
    priority: 1
  };

  // 脚本统计信息
  const [scriptStats, setScriptStats] = useState<any>(null);

  // 重复点击防护状态
  const [lastAnalysisParams, setLastAnalysisParams] = useState<{
    type: 'image' | 'url';
    content: string;
    formats: string[];
    description: string;
  } | null>(null);

  // 页面选择相关状态
  const [selectedPageIds, setSelectedPageIds] = useState<string[]>([]);
  const [availablePages, setAvailablePages] = useState<any[]>([]);
  const [loadingPages, setLoadingPages] = useState(false);

  // 页面分析API实例
  const pageAnalysisApi = new PageAnalysisApi();

  // 获取脚本统计信息
  useEffect(() => {
    const fetchStats = async () => {
      try {
        const stats = await getScriptStatistics();
        setScriptStats(stats);
      } catch (error) {
        console.error('获取脚本统计失败:', error);
      }
    };
    fetchStats();
  }, []);

  // 加载可用页面列表
  useEffect(() => {
    const loadAvailablePages = async () => {
      setLoadingPages(true);
      try {
        const response = await pageAnalysisApi.getPageList();
        if (response.data) {
          // 只显示分析完成的页面
          const completedPages = response.data.filter(page =>
            page.analysis_status === 'completed' && page.elements_count > 0
          );
          setAvailablePages(completedPages);
        }
      } catch (error) {
        console.error('加载页面列表失败:', error);
        message.error('加载页面列表失败');
      } finally {
        setLoadingPages(false);
      }
    };

    loadAvailablePages();
  }, []);

  // 处理图片上传
  const handleImageUpload = useCallback((file: any) => {
    setUploadedFile(file);
    return false; // 阻止自动上传
  }, []);

  // 处理图片分析
  const handleImageAnalysis = useCallback(async (values: any) => {
    if (!uploadedFile) {
      message.error('请先上传图片');
      return;
    }

    // 检查是否重复点击
    const currentParams = {
      type: 'image' as const,
      content: uploadedFile.name + uploadedFile.size, // 使用文件名和大小作为唯一标识
      formats: [...selectedFormats].sort(),
      description: values.test_description || ''
    };

    if (lastAnalysisParams &&
        lastAnalysisParams.type === currentParams.type &&
        lastAnalysisParams.content === currentParams.content &&
        JSON.stringify(lastAnalysisParams.formats) === JSON.stringify(currentParams.formats) &&
        lastAnalysisParams.description === currentParams.description) {
      message.warning('参数未修改，无需重复分析');
      return;
    }

    setIsAnalyzing(true);
    setCurrentSessionId('');

    const formData = new FormData();
    formData.append('file', uploadedFile);
    formData.append('test_description', values.test_description);
    if (values.additional_context) {
      formData.append('additional_context', values.additional_context);
    }
    formData.append('generate_formats', selectedFormats.join(','));

    // 默认保存到数据库 - UI测试自动保存
    formData.append('save_to_database', 'true');
    formData.append('script_name', `UI测试脚本_${Date.now()}`);
    formData.append('script_description', values.test_description || 'UI自动化测试脚本');
    formData.append('tags', JSON.stringify(databaseConfig.tags));
    formData.append('category', databaseConfig.category);
    formData.append('priority', databaseConfig.priority.toString());

    // 添加选择的页面ID
    if (selectedPageIds.length > 0) {
      formData.append('selected_page_ids', selectedPageIds.join(','));
    }

    try {
      const result = await analyzeWebImage(formData);

      // 记录本次分析参数
      setLastAnalysisParams(currentParams);

      if (result.sse_endpoint && result.session_id) {
        setCurrentSessionId(result.session_id);
        toast.success('开始实时分析...');
      } else {
        setAnalysisResult(result);
        setIsAnalyzing(false);
        if (result.session_id) {
          setCurrentSessionId(result.session_id);
          await fetchGeneratedScripts(result.session_id);
        }
        toast.success('图片分析完成！');
      }
    } catch (error: any) {
      setIsAnalyzing(false);
      toast.error(`分析失败: ${error.message}`);
    }
  }, [uploadedFile, selectedFormats, databaseConfig, lastAnalysisParams, selectedPageIds]);

  // 处理URL分析
  const handleURLAnalysis = useCallback(async (values: any) => {
    // 检查是否重复点击
    const currentParams = {
      type: 'url' as const,
      content: values.url || '',
      formats: [...selectedFormats].sort(),
      description: values.test_description || ''
    };

    if (lastAnalysisParams &&
        lastAnalysisParams.type === currentParams.type &&
        lastAnalysisParams.content === currentParams.content &&
        JSON.stringify(lastAnalysisParams.formats) === JSON.stringify(currentParams.formats) &&
        lastAnalysisParams.description === currentParams.description) {
      message.warning('参数未修改，无需重复分析');
      return;
    }

    setIsAnalyzing(true);

    const analysisRequest = {
      ...values,
      generate_formats: selectedFormats.join(','),
      // 默认保存到数据库 - UI测试自动保存
      save_to_database: true,
      script_name: `UI测试脚本_${Date.now()}`,
      script_description: values.test_description || 'UI自动化测试脚本',
      tags: JSON.stringify(databaseConfig.tags),
      category: databaseConfig.category,
      priority: databaseConfig.priority,
      // 添加选择的页面ID
      selected_page_ids: selectedPageIds.length > 0 ? selectedPageIds.join(',') : undefined
    };

    try {
      const result = await analyzeWebURL(analysisRequest);

      // 记录本次分析参数
      setLastAnalysisParams(currentParams);

      if (result.sse_endpoint && result.session_id) {
        setCurrentSessionId(result.session_id);
        toast.success('开始实时分析...');
      } else {
        setAnalysisResult(result);
        setIsAnalyzing(false);
        if (result.session_id) {
          setCurrentSessionId(result.session_id);
          await fetchGeneratedScripts(result.session_id);
        }
        toast.success('URL分析完成！');
      }
    } catch (error: any) {
      setIsAnalyzing(false);
      toast.error(`分析失败: ${error.message}`);
    }
  }, [selectedFormats, lastAnalysisParams, selectedPageIds]);

  // 获取生成的脚本
  const fetchGeneratedScripts = useCallback(async (sessionId: string) => {
    try {
      await new Promise(resolve => setTimeout(resolve, 500));
      const response = await getGeneratedScripts(sessionId);
      
      if (response.status === 'success' && response.scripts && response.scripts.length > 0) {
        const newScripts: ScriptCollection = {};
        
        response.scripts.forEach((script: any) => {
          const scriptData: ScriptData = {
            format: script.format as 'yaml' | 'playwright',
            content: script.content,
            filename: script.filename,
            file_path: script.file_path
          };

          if (script.format === 'yaml') {
            newScripts.yaml = scriptData;
          } else if (script.format === 'playwright') {
            newScripts.playwright = scriptData;
          }
        });

        setScripts(newScripts);
        setShowScriptEditor(true);
        setIsEditingScript({yaml: false, playwright: false});
        setActiveScriptTab(newScripts.yaml ? 'yaml' : 'playwright');
        
        toast.success(`成功加载 ${response.scripts.length} 个脚本！`);
      }
    } catch (error: any) {
      console.error('获取脚本失败:', error);
      toast.error('获取脚本失败');
    }
  }, []);

  // 处理流式分析完成
  const handleStreamingComplete = useCallback(async (result: any) => {
    setAnalysisResult(result);
    setIsAnalyzing(false);
    setPreserveStreamingContent(true); // 保持流式内容显示

    if (result && result.session_id) {
      setCurrentSessionId(result.session_id);
      await fetchGeneratedScripts(result.session_id);
    }

    toast.success('分析完成！');
  }, [fetchGeneratedScripts]);

  // 保存脚本到数据库
  const handleSaveScript = useCallback(async (scriptFormat: 'yaml' | 'playwright') => {
    const script = scripts[scriptFormat];
    if (!script || !currentSessionId) {
      message.error('没有可保存的脚本或会话ID');
      return;
    }

    setIsSavingScript(true);

    try {
      const saveData = {
        session_id: currentSessionId,
        name: `UI测试${scriptFormat}脚本_${Date.now()}`,
        description: '自动生成的UI测试脚本',
        script_format: scriptFormat,
        script_type: 'image_analysis',
        test_description: form.getFieldValue('test_description') || '',
        content: script.content,
        tags: databaseConfig.tags
      };

      const result = await saveScriptFromSession(saveData);
      
      if (result.status === 'success') {
        toast.success('脚本保存成功！');
        message.success(`脚本已保存到数据库，ID: ${result.script_id}`);
        
        // 刷新统计信息
        const stats = await getScriptStatistics();
        setScriptStats(stats);
      }
    } catch (error: any) {
      toast.error(`保存失败: ${error.message}`);
    } finally {
      setIsSavingScript(false);
    }
  }, [scripts, currentSessionId, databaseConfig, form]);

  // 执行脚本
  const handleExecuteScript = useCallback(async (scriptFormat: 'yaml' | 'playwright') => {
    const script = scripts[scriptFormat];
    if (!script) {
      message.error('没有可执行的脚本');
      return;
    }

    setIsExecutingScript(true);

    try {
      // 这里需要根据实际的执行API调整
      toast.success('脚本执行已启动！');
    } catch (error: any) {
      toast.error(`执行失败: ${error.message}`);
    } finally {
      setIsExecutingScript(false);
    }
  }, [scripts]);

  return (
    <div className="web-test-creation-optimized">
      <Card title="Web测试创建 - 优化版" className="main-card">
        {/* 统计信息显示 */}
        {scriptStats && (
          <Alert
            message={`数据库统计: 共 ${scriptStats.total_scripts} 个脚本，成功率 ${(scriptStats.success_rate * 100).toFixed(1)}%`}
            type="info"
            showIcon
            style={{ marginBottom: 16 }}
          />
        )}

        <Tabs activeKey={activeTab} onChange={setActiveTab}>
          <TabPane tab="图片分析" key="image">
            <Form form={form} onFinish={handleImageAnalysis} layout="vertical">
              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item label="上传图片" required>
                    <Upload
                      beforeUpload={handleImageUpload}
                      showUploadList={false}
                      accept="image/*"
                    >
                      <Button icon={<UploadOutlined />}>
                        {uploadedFile ? uploadedFile.name : '选择图片'}
                      </Button>
                    </Upload>
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item label="生成格式">
                    <Checkbox.Group
                      value={selectedFormats}
                      onChange={setSelectedFormats}
                      options={[
                        { label: 'YAML', value: 'yaml' },
                        { label: 'Playwright + MidScene.js', value: 'playwright' }
                      ]}
                    />
                  </Form.Item>
                </Col>
              </Row>

              <Form.Item
                name="test_description"
                label="测试描述"
                rules={[{ required: true, message: '请输入测试描述' }]}
              >
                <TextArea rows={3} placeholder="描述要测试的功能..." />
              </Form.Item>

              <Form.Item name="additional_context" label="附加上下文">
                <TextArea rows={2} placeholder="提供额外的测试上下文..." />
              </Form.Item>

              <div style={{ marginBottom: 16 }}>
                <label style={{
                  display: 'block',
                  marginBottom: 8,
                  fontWeight: 500,
                  color: 'rgba(0, 0, 0, 0.85)'
                }}>
                  关联页面（可选）
                </label>
                <Select
                  mode="multiple"
                  placeholder="选择已分析的页面，用于获取页面元素信息优化脚本生成"
                  value={selectedPageIds}
                  onChange={(value) => {
                    console.log('🔍 页面选择变化 (Optimized):', value);
                    setSelectedPageIds(value);
                  }}
                  loading={loadingPages}
                  showSearch
                  filterOption={(input, option) =>
                    (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                  }
                  options={availablePages.map(page => ({
                    value: page.id,
                    label: `${page.page_name} (${page.elements_count}个元素)`,
                    title: page.page_description || page.page_name
                  }))}
                  maxTagCount={3}
                  maxTagTextLength={20}
                  style={{ width: '100%' }}
                />
                <div style={{ marginTop: 4, fontSize: 12, color: '#666' }}>
                  💡 选择相关页面可以帮助AI获取准确的页面元素信息，生成更高质量的测试脚本
                </div>
              </div>

              <Form.Item>
                <Button
                  type="primary"
                  htmlType="submit"
                  loading={isAnalyzing}
                  icon={<EyeOutlined />}
                  size="large"
                >
                  {isAnalyzing ? '分析中...' : '开始分析'}
                </Button>
              </Form.Item>
            </Form>
          </TabPane>

          <TabPane tab="URL分析" key="url">
            <Form form={urlForm} onFinish={handleURLAnalysis} layout="vertical">
              <Form.Item
                name="url"
                label="网页URL"
                rules={[
                  { required: true, message: '请输入网页URL' },
                  { type: 'url', message: '请输入有效的URL' }
                ]}
              >
                <Input placeholder="https://example.com" prefix={<LinkOutlined />} />
              </Form.Item>

              <Form.Item
                name="test_description"
                label="测试描述"
                rules={[{ required: true, message: '请输入测试描述' }]}
              >
                <TextArea rows={3} placeholder="描述要测试的功能..." />
              </Form.Item>

              <Form.Item name="additional_context" label="附加上下文">
                <TextArea rows={2} placeholder="提供额外的测试上下文..." />
              </Form.Item>

              <div style={{ marginBottom: 16 }}>
                <label style={{
                  display: 'block',
                  marginBottom: 8,
                  fontWeight: 500,
                  color: 'rgba(0, 0, 0, 0.85)'
                }}>
                  关联页面（可选）
                </label>
                <Select
                  mode="multiple"
                  placeholder="选择已分析的页面，用于获取页面元素信息优化脚本生成"
                  value={selectedPageIds}
                  onChange={(value) => {
                    console.log('🔍 页面选择变化 (Optimized 2):', value);
                    setSelectedPageIds(value);
                  }}
                  loading={loadingPages}
                  showSearch
                  filterOption={(input, option) =>
                    (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                  }
                  options={availablePages.map(page => ({
                    value: page.id,
                    label: `${page.page_name} (${page.elements_count}个元素)`,
                    title: page.page_description || page.page_name
                  }))}
                  maxTagCount={3}
                  maxTagTextLength={20}
                  style={{ width: '100%' }}
                />
                <div style={{ marginTop: 4, fontSize: 12, color: '#666' }}>
                  💡 选择相关页面可以帮助AI获取准确的页面元素信息，生成更高质量的测试脚本
                </div>
              </div>

              <Form.Item>
                <Button
                  type="primary"
                  htmlType="submit"
                  loading={isAnalyzing}
                  icon={<EyeOutlined />}
                  size="large"
                >
                  {isAnalyzing ? '分析中...' : '开始分析'}
                </Button>
              </Form.Item>
            </Form>
          </TabPane>
        </Tabs>

        {/* 流式显示组件 */}
        {currentSessionId && (
          <StreamingDisplay
            sessionId={currentSessionId}
            isActive={(isAnalyzing && !!currentSessionId) || preserveStreamingContent}
            onAnalysisComplete={handleStreamingComplete}
            platform="web"
          />
        )}

        {/* 脚本编辑器 */}
        {showScriptEditor && (
          <Card title="生成的脚本" style={{ marginTop: 16 }}>
            <Tabs activeKey={activeScriptTab} onChange={(key) => setActiveScriptTab(key as 'yaml' | 'playwright')}>
              {scripts.yaml && (
                <TabPane tab="YAML脚本" key="yaml">
                  <Space style={{ marginBottom: 16 }}>
                    <Button
                      icon={<SaveOutlined />}
                      onClick={() => handleSaveScript('yaml')}
                      loading={isSavingScript}
                    >
                      保存到数据库
                    </Button>
                    <Button
                      icon={<PlayCircleOutlined />}
                      onClick={() => handleExecuteScript('yaml')}
                      loading={isExecutingScript}
                    >
                      执行脚本
                    </Button>
                    <Button icon={<DownloadOutlined />}>
                      下载脚本
                    </Button>
                  </Space>
                  <YAMLViewer content={scripts.yaml.content} />
                </TabPane>
              )}
              
              {scripts.playwright && (
                <TabPane tab="Playwright + MidScene.js" key="playwright">
                  <Space style={{ marginBottom: 16 }}>
                    <Button
                      icon={<SaveOutlined />}
                      onClick={() => handleSaveScript('playwright')}
                      loading={isSavingScript}
                    >
                      保存到数据库
                    </Button>
                    <Button
                      icon={<PlayCircleOutlined />}
                      onClick={() => handleExecuteScript('playwright')}
                      loading={isExecutingScript}
                    >
                      执行脚本
                    </Button>
                    <Button icon={<DownloadOutlined />}>
                      下载脚本
                    </Button>
                  </Space>
                  <pre style={{ background: '#f5f5f5', padding: 16, borderRadius: 4 }}>
                    {scripts.playwright.content}
                  </pre>
                </TabPane>
              )}
            </Tabs>
          </Card>
        )}
      </Card>
    </div>
  );
};

export default WebTestCreationOptimized;
