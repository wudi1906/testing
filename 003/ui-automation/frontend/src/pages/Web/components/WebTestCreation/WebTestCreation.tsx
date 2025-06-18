import React, { useState, useMemo } from 'react';
import { useLocation } from 'react-router-dom';
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
  message
} from 'antd';
import {
  UploadOutlined,
  LinkOutlined,
  PlayCircleOutlined,
  DownloadOutlined,
  EyeOutlined,
  RobotOutlined,
  ThunderboltOutlined,
  GlobalOutlined,
  NodeIndexOutlined,
  InfoCircleOutlined,
  CodeOutlined,
  SaveOutlined,
  CloseOutlined,
  CheckCircleOutlined
} from '@ant-design/icons';
import { motion } from 'framer-motion';
import { useMutation } from 'react-query';
import toast from 'react-hot-toast';

import YAMLViewer from '../../../../components/YAMLViewer/YAMLViewer';
import StreamingDisplay from '../../../../components/StreamingDisplay/StreamingDisplay';
import {
  analyzeWebImage,
  analyzeWebURL,
  startWebCrawl,
  saveScriptFile,
  executeYAMLContent,
  executePlaywrightScript,
  getGeneratedScripts,
  saveScriptFromSession
} from '../../../../services/api';
import './WebTestCreation.css';

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

const WebTestCreation: React.FC = () => {
  const [activeTab, setActiveTab] = useState('image');
  const [form] = Form.useForm();
  const [urlForm] = Form.useForm();
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [uploadedFile, setUploadedFile] = useState<any>(null);
  const [selectedFormats, setSelectedFormats] = useState<string[]>(['playwright']);
  const [crawlMode, setCrawlMode] = useState<'single' | 'multi'>('single');
  const [currentSessionId, setCurrentSessionId] = useState<string>('');
  const [preserveStreamingContent, setPreserveStreamingContent] = useState<boolean>(false);
  const [testMode, setTestMode] = useState<boolean>(false);

  // 脚本编辑相关状态
  const [showScriptEditor, setShowScriptEditor] = useState(false);
  const [scripts, setScripts] = useState<ScriptCollection>({});
  const [activeScriptTab, setActiveScriptTab] = useState<'yaml' | 'playwright'>('playwright');
  const [isEditingScript, setIsEditingScript] = useState<{yaml: boolean, playwright: boolean}>({yaml: false, playwright: false});
  const [isSavingScript, setIsSavingScript] = useState(false);
  const [isExecutingScript, setIsExecutingScript] = useState(false);

  // Web平台配置
  const apiConfig = {
    analyzeImage: analyzeWebImage,
    analyzeURL: analyzeWebURL,
    startCrawl: startWebCrawl,
    platformName: 'Web',
    platformIcon: <GlobalOutlined />,
    platformColor: '#1890ff'
  };

  // 图片分析mutation - 上传文件并获取session_id
  const imageAnalysisMutation = useMutation(apiConfig.analyzeImage, {
    onSuccess: (data) => {
      // 检查是否返回了SSE端点
      if (data.sse_endpoint && data.session_id) {
        // 设置会话ID，启动流式显示
        console.log('设置会话ID:', data.session_id);
        console.log('SSE端点:', data.sse_endpoint);
        setCurrentSessionId(data.session_id);
        toast.success('开始实时分析...');
      } else {
        // 直接返回结果的情况（兼容旧版本）
        setAnalysisResult(data);
        setIsAnalyzing(false);
        toast.success(`${apiConfig.platformName}图片分析完成！`);
        message.success('YAML测试脚本生成成功');
      }
    },
    onError: (error: any) => {
      setIsAnalyzing(false);
      setCurrentSessionId('');
      // 只有在真正的错误情况下才清除内容，而不是每次都清除
      // setPreserveStreamingContent(false);
      toast.error(`分析失败: ${error.message}`);
      message.error(`${apiConfig.platformName}图片分析失败`);
    }
  });

  // URL分析mutation
  const urlAnalysisMutation = useMutation(apiConfig.analyzeURL, {
    onSuccess: (data) => {
      // 检查是否返回了SSE端点
      if (data.sse_endpoint && data.session_id) {
        // 设置会话ID，启动流式显示
        console.log('URL分析设置会话ID:', data.session_id);
        console.log('SSE端点:', data.sse_endpoint);
        setCurrentSessionId(data.session_id);
        toast.success('开始实时分析...');
      } else {
        // 直接返回结果的情况（兼容旧版本）
        setAnalysisResult(data);
        setIsAnalyzing(false);

        // 如果有session_id，设置它
        if (data.session_id) {
          setCurrentSessionId(data.session_id);
          // 立即获取生成的脚本
          fetchGeneratedScripts(data.session_id);
        }

        toast.success(`${apiConfig.platformName}网页分析完成！`);
        message.success('YAML测试脚本生成成功');
      }
    },
    onError: (error: any) => {
      setIsAnalyzing(false);
      setCurrentSessionId('');
      // 只有在真正的错误情况下才清除内容，而不是每次都清除
      // setPreserveStreamingContent(false);
      toast.error(`分析失败: ${error.message}`);
      message.error(`${apiConfig.platformName}网页分析失败`);
    }
  });

  // 多页面抓取mutation
  const multiCrawlMutation = useMutation(
    async (data: any) => {
      // Web平台的多页面抓取API
      const apiEndpoint = '/api/v1/web/create/crawl4ai/start';

      // 启动抓取任务
      const response = await fetch(apiEndpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      });

      if (!response.ok) {
        throw new Error('启动抓取任务失败');
      }

      const result = await response.json();
      const integrationId = result.integration_id || result.session_id;

      // 轮询检查状态
      return new Promise((resolve, reject) => {
        const checkStatus = async () => {
          try {
            const statusEndpoint = `/api/v1/web/create/crawl4ai/status/${integrationId}`;
            const statusResponse = await fetch(statusEndpoint);
            const status = await statusResponse.json();

            if (status.status === 'completed') {
              // 获取结果
              const resultsEndpoint = `/api/v1/web/create/crawl4ai/results/${integrationId}`;
              const resultsResponse = await fetch(resultsEndpoint);
              const results = await resultsResponse.json();
              resolve(results);
            } else if (status.status === 'failed') {
              reject(new Error(status.error_message || '抓取任务失败'));
            } else {
              // 继续轮询
              setTimeout(checkStatus, 3000);
            }
          } catch (error) {
            reject(error);
          }
        };

        checkStatus();
      });
    },
    {
      onSuccess: (data: any) => {
        // 转换多页面抓取结果为单页面格式
        const convertedResult = convertMultiCrawlResult(data);
        setAnalysisResult(convertedResult);
        setIsAnalyzing(false);

        // 设置会话ID
        if (convertedResult.session_id) {
          setCurrentSessionId(convertedResult.session_id);
          // 立即获取生成的脚本
          fetchGeneratedScripts(convertedResult.session_id);
        }

        toast.success('多页面抓取和分析完成！');
        message.success(`成功抓取 ${data.crawl_results?.length || 0} 个页面并生成测试脚本`);
      },
      onError: (error: any) => {
        setIsAnalyzing(false);
        toast.error(`抓取失败: ${error.message}`);
        message.error('多页面抓取失败');
      }
    }
  );

  // 转换多页面抓取结果为单页面格式
  const convertMultiCrawlResult = (multiResult: any) => {
    const crawlResults = multiResult.crawl_results || [];
    const generatedScripts = multiResult.generated_scripts || [];

    // 合并所有页面的YAML内容
    let combinedYaml = '';
    let combinedAnalysis = {
      analysis_id: `multi_crawl_${Date.now()}`,
      analysis_type: 'multi_page_crawl',
      page_analysis: {
        page_title: `多页面测试套件 (${crawlResults.length}页)`,
        page_type: 'multi_page_suite',
        main_content: `基于Crawl4AI抓取的${crawlResults.length}个页面生成的完整测试套件`,
        ui_elements: [],
        user_flows: [],
        test_scenarios: []
      },
      confidence_score: 0.9,
      processing_time: 0
    };

    // 处理生成的脚本
    if (generatedScripts.length > 0) {
      const yamlScripts = generatedScripts
        .filter((script: any) => script.yaml_content)
        .map((script: any, index: number) => {
          const pageInfo = script.page_info || {};
          return `# 页面 ${index + 1}: ${pageInfo.title || pageInfo.url || '未知页面'}
# URL: ${pageInfo.url || ''}
# 页面类型: ${pageInfo.page_type || 'unknown'}
# 复杂度: ${pageInfo.complexity_score || 1}/10

${script.yaml_content}

---
`;
        });

      combinedYaml = yamlScripts.join('\n');

      // 合并分析结果
      generatedScripts.forEach((script: any) => {
        if (script.analysis_result?.page_analysis) {
          const pageAnalysis = script.analysis_result.page_analysis;

          // 合并UI元素
          if (pageAnalysis.ui_elements) {
            combinedAnalysis.page_analysis.ui_elements.push(...pageAnalysis.ui_elements);
          }

          // 合并用户流程
          if (pageAnalysis.user_flows) {
            combinedAnalysis.page_analysis.user_flows.push(...pageAnalysis.user_flows);
          }

          // 合并测试场景
          if (pageAnalysis.test_scenarios) {
            combinedAnalysis.page_analysis.test_scenarios.push(...pageAnalysis.test_scenarios);
          }
        }
      });
    }

    return {
      session_id: `multi_crawl_${Date.now()}`,
      analysis_result: combinedAnalysis,
      yaml_script: null,
      yaml_content: combinedYaml || '# 多页面抓取完成，但未生成YAML脚本\n# 请检查抓取配置和生成设置',
      file_path: '',
      estimated_duration: `${crawlResults.length * 30}秒`,
      multi_crawl_data: {
        total_pages: crawlResults.length,
        crawl_results: crawlResults,
        generated_scripts: generatedScripts
      }
    };
  };

  const handleImageUpload = (file: any) => {
    setUploadedFile(file);
    return false; // 阻止自动上传
  };

  const handleImageAnalysis = async (values: any) => {
    if (!uploadedFile) {
      message.error('请先上传图片');
      return;
    }

    setIsAnalyzing(true);
    setCurrentSessionId(''); // 重置会话ID
    // 注意：不要在开始新分析时重置preserveStreamingContent，让StreamingDisplay自己处理

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
    formData.append('tags', JSON.stringify(['UI测试', '自动化']));
    formData.append('category', 'UI测试');
    formData.append('priority', '1');

    imageAnalysisMutation.mutate(formData);
  };

  const handleURLAnalysis = async (values: any) => {
    setIsAnalyzing(true);
    // 注意：不要在开始新分析时重置preserveStreamingContent，让StreamingDisplay自己处理

    // 根据抓取模式选择不同的API
    if (crawlMode === 'multi') {
      // 使用Crawl4AI集成服务
      const crawlRequest = {
        homepage_url: values.url,
        test_description: values.test_description,
        additional_context: values.additional_context,
        max_pages: values.max_pages || 20,
        max_depth: values.max_depth || 2,
        crawl_strategy: values.crawl_strategy || 'bfs',
        user_query: values.user_query,
        generate_formats: selectedFormats
      };

      // 调用多页面抓取API
      multiCrawlMutation.mutate(crawlRequest);
    } else {
      // 使用单页面分析
      const analysisRequest = {
        ...values,
        generate_formats: selectedFormats.join(',')
      };
      urlAnalysisMutation.mutate(analysisRequest);
    }
  };

  const handleStreamingComplete = async (result: any) => {
    console.log('流式分析完成，结果:', result);

    setAnalysisResult(result);
    setIsAnalyzing(false);
    setPreserveStreamingContent(true); // 保持流式内容显示
    setTestMode(false); // 关闭测试模式

    // 确保会话ID被正确设置
    if (result && result.session_id) {
      console.log('设置会话ID:', result.session_id);
      setCurrentSessionId(result.session_id); // 确保会话ID被设置

      console.log('自动获取生成的脚本，会话ID:', result.session_id);
      // 立即获取生成的脚本并显示编辑器
      await fetchGeneratedScripts(result.session_id);
    } else {
      console.log('没有会话ID，尝试使用分析结果中的内容');
      // 如果没有session_id，尝试直接使用分析结果中的内容
      if (result && result.yaml_content) {
        const newScripts: ScriptCollection = {
          yaml: {
            format: 'yaml',
            content: result.yaml_content,
            filename: `test_${Date.now()}.yaml`,
            file_path: result.file_path || ''
          }
        };

        setScripts(newScripts);
        setShowScriptEditor(true);
        setIsEditingScript({yaml: false, playwright: false});
        setActiveScriptTab('yaml');

        // 清除分析结果，确保只显示脚本编辑器
        setAnalysisResult(null);

        toast.success('成功加载YAML脚本！');

        // 自动保存脚本到数据库
        const scriptDataForSave = [{
          format: 'yaml',
          content: result.yaml_content,
          filename: `test_${Date.now()}.yaml`
        }];
        await autoSaveScriptsToDatabase(scriptDataForSave, result.session_id);
      }
    }

    toast.success('Web图片分析完成！');
    message.success('YAML测试脚本生成成功');
  };

  // 获取生成的脚本
  const fetchGeneratedScripts = async (sessionId: string) => {
    try {
      console.log('开始获取生成的脚本，会话ID:', sessionId);

      // 减少延迟，因为流式分析完成时脚本应该已经生成
      await new Promise(resolve => setTimeout(resolve, 500));

      const response = await getGeneratedScripts(sessionId);
      console.log('获取脚本响应:', response);
      console.log('响应中的scripts:', response?.scripts);

      const newScripts: ScriptCollection = {};

      console.log('检查响应状态:', response.status);
      console.log('检查脚本数组:', response.scripts);

      if (response.status === 'success' && response.scripts && response.scripts.length > 0) {
        console.log('找到脚本，开始处理...');
        console.log('脚本数量:', response.scripts.length);

        // 处理所有返回的脚本
        response.scripts.forEach((script, index) => {
          console.log(`处理脚本 ${index}:`, script);
          console.log(`脚本格式: ${script.format}, 内容长度: ${script.content?.length || 0}`);

          const scriptData: ScriptData = {
            format: script.format as 'yaml' | 'playwright',
            content: script.content,
            filename: script.filename,
            file_path: script.file_path
          };

          if (script.format === 'yaml') {
            newScripts.yaml = scriptData;
            console.log('设置YAML脚本');
          } else if (script.format === 'playwright') {
            newScripts.playwright = scriptData;
            console.log('设置Playwright脚本');
          }
        });

        console.log('设置脚本数据:', newScripts);
        console.log('showScriptEditor将被设置为true');
        setScripts(newScripts);
        setShowScriptEditor(true);
        setIsEditingScript({yaml: false, playwright: false}); // 重置编辑状态

        // 设置默认激活的标签页
        if (newScripts.yaml) {
          setActiveScriptTab('yaml');
          console.log('设置活动标签页为yaml');
        } else if (newScripts.playwright) {
          setActiveScriptTab('playwright');
          console.log('设置活动标签页为playwright');
        }

        // 清除分析结果，确保只显示脚本编辑器
        setAnalysisResult(null);
        console.log('分析结果已清除，脚本编辑器应该显示');

        toast.success(`成功加载${response.scripts.length}个脚本！`);

        // 自动保存脚本到数据库
        await autoSaveScriptsToDatabase(response.scripts, sessionId);

        // 自动保存脚本到数据库
        await autoSaveScriptsToDatabase(response.scripts, sessionId);
      } else {
        console.log('没有找到生成的脚本，尝试使用分析结果中的内容');

        // 如果API没有返回脚本，尝试从分析结果中获取
        if (analysisResult && analysisResult.yaml_content) {
          newScripts.yaml = {
            format: 'yaml',
            content: analysisResult.yaml_content,
            filename: `test_${sessionId.slice(0, 8)}.yaml`,
            file_path: analysisResult.file_path || ''
          };

          console.log('使用分析结果中的YAML内容:', newScripts);
          console.log('从分析结果设置脚本编辑器');
          setScripts(newScripts);
          setShowScriptEditor(true);
          setIsEditingScript({yaml: false, playwright: false});
          setActiveScriptTab('yaml');

          // 清除分析结果，确保只显示脚本编辑器
          setAnalysisResult(null);
          console.log('脚本编辑器应该显示 - 从分析结果');

          toast.success('成功加载YAML脚本！');

          // 自动保存脚本到数据库
          const scriptDataFromAnalysis = [{
            format: 'yaml',
            content: analysisResult.yaml_content,
            filename: `test_${sessionId.slice(0, 8)}.yaml`
          }];
          await autoSaveScriptsToDatabase(scriptDataFromAnalysis, sessionId);
        } else {
          console.log('没有找到任何脚本内容');
          toast.info('分析完成，但没有生成脚本内容');
        }
      }
    } catch (error: any) {
      console.error('获取生成的脚本失败:', error);

      // 如果API调用失败，尝试使用分析结果中的内容
      if (analysisResult && analysisResult.yaml_content) {
        console.log('API调用失败，使用分析结果中的内容');
        const newScripts: ScriptCollection = {
          yaml: {
            format: 'yaml',
            content: analysisResult.yaml_content,
            filename: `test_${sessionId.slice(0, 8)}.yaml`,
            file_path: analysisResult.file_path || ''
          }
        };

        setScripts(newScripts);
        setShowScriptEditor(true);
        setIsEditingScript({yaml: false, playwright: false});
        setActiveScriptTab('yaml');

        // 清除分析结果，确保只显示脚本编辑器
        setAnalysisResult(null);

        toast.success('成功加载YAML脚本！');

        // 自动保存脚本到数据库
        const scriptDataFallback1 = [{
          format: 'yaml',
          content: analysisResult.yaml_content,
          filename: `test_${sessionId.slice(0, 8)}.yaml`
        }];
        await autoSaveScriptsToDatabase(scriptDataFallback1, sessionId);

        // 自动保存脚本到数据库
        const scriptDataFallback2 = [{
          format: 'yaml',
          content: analysisResult.yaml_content,
          filename: `test_${sessionId.slice(0, 8)}.yaml`
        }];
        await autoSaveScriptsToDatabase(scriptDataFallback2, sessionId);
      } else {
        toast.error(`获取脚本失败: ${error.message}`);
      }
    }
  };

  const handleStreamingError = (error: string) => {
    setIsAnalyzing(false);
    setCurrentSessionId('');
    // 只有在真正的错误情况下才清除内容，而不是每次都清除
    // setPreserveStreamingContent(false);
    toast.error(`分析失败: ${error}`);
    message.error('Web图片分析失败');
  };



  // 保存脚本文件
  const handleSaveScript = async () => {
    const currentScript = scripts[activeScriptTab];
    if (!currentScript) return;

    setIsSavingScript(true);
    try {
      const response = await saveScriptFile({
        content: currentScript.content,
        filename: currentScript.filename,
        format: currentScript.format
      });

      // 更新脚本的文件路径
      setScripts(prev => ({
        ...prev,
        [activeScriptTab]: {
          ...currentScript,
          file_path: response.file_path
        }
      }));

      // 重置编辑状态
      setIsEditingScript(prev => ({
        ...prev,
        [activeScriptTab]: false
      }));

      toast.success('脚本保存成功！');
      message.success(`${currentScript.format.toUpperCase()}脚本已保存`);
    } catch (error: any) {
      toast.error(`保存失败: ${error.message}`);
      message.error('脚本保存失败');
    } finally {
      setIsSavingScript(false);
    }
  };



  // 保存脚本到数据库
  const handleSaveScriptToDatabase = async () => {
    const currentScript = scripts[activeScriptTab];
    if (!currentScript || !currentSessionId) {
      message.error('没有可保存的脚本或会话信息');
      return;
    }

    // 弹出对话框让用户输入脚本信息
    Modal.confirm({
      title: '保存脚本到数据库',
      width: 600,
      content: (
        <div>
          <p>将当前脚本保存到数据库中，以便后续管理和执行。</p>
          <Form layout="vertical">
            <Form.Item label="脚本名称" required>
              <Input
                id="script-name"
                placeholder="请输入脚本名称"
                defaultValue={`${currentScript.format.toUpperCase()}测试脚本_${new Date().toLocaleDateString()}`}
              />
            </Form.Item>
            <Form.Item label="脚本描述">
              <TextArea
                id="script-description"
                rows={3}
                placeholder="请描述这个脚本的功能和用途"
                defaultValue={`基于AI分析生成的${currentScript.format.toUpperCase()}自动化测试脚本`}
              />
            </Form.Item>
            <Form.Item label="标签">
              <Input
                id="script-tags"
                placeholder="请输入标签，用逗号分隔，如：登录,UI测试,自动化"
              />
            </Form.Item>
          </Form>
        </div>
      ),
      onOk: async () => {
        const nameInput = document.getElementById('script-name') as HTMLInputElement;
        const descriptionInput = document.getElementById('script-description') as HTMLTextAreaElement;
        const tagsInput = document.getElementById('script-tags') as HTMLInputElement;

        const name = nameInput?.value || `${currentScript.format.toUpperCase()}测试脚本_${new Date().toLocaleDateString()}`;
        const description = descriptionInput?.value || `基于AI分析生成的${currentScript.format.toUpperCase()}自动化测试脚本`;
        const tagsStr = tagsInput?.value || '';
        const tags = tagsStr ? tagsStr.split(',').map(tag => tag.trim()).filter(tag => tag) : [];

        try {
          // 获取测试描述信息
          const testDescription = form.getFieldValue('test_description') || urlForm.getFieldValue('test_description') || '自动化测试';
          const additionalContext = form.getFieldValue('additional_context') || urlForm.getFieldValue('additional_context');
          const sourceUrl = urlForm.getFieldValue('url');

          const response = await saveScriptFromSession({
            session_id: currentSessionId,
            name,
            description,
            script_format: currentScript.format as 'yaml' | 'playwright',
            script_type: activeTab === 'image' ? 'image_analysis' : 'url_analysis',
            test_description: testDescription,
            content: currentScript.content,
            additional_context: additionalContext,
            source_url: sourceUrl,
            tags
          });

          toast.success('脚本已保存到数据库！');
          message.success(`脚本ID: ${response.script_id}`);

          // 可以选择跳转到脚本管理页面
          Modal.info({
            title: '保存成功',
            content: (
              <div>
                <p>脚本已成功保存到数据库！</p>
                <p><strong>脚本ID:</strong> {response.script_id}</p>
                <p><strong>脚本名称:</strong> {name}</p>
                <p>您可以在"执行测试"页面中管理和执行此脚本。</p>
              </div>
            ),
            onOk: () => {
              // 可以选择跳转到执行页面
              // window.open('/web/execution', '_blank');
            }
          });

        } catch (error: any) {
          toast.error(`保存到数据库失败: ${error.message}`);
          message.error('保存到数据库失败');
        }
      }
    });
  };

  // 自动保存脚本到数据库
  const autoSaveScriptsToDatabase = async (scripts: any[], sessionId: string) => {
    try {
      console.log('开始自动保存脚本到数据库:', scripts);

      for (const script of scripts) {
        // 获取测试描述信息
        const testDescription = form.getFieldValue('test_description') || urlForm.getFieldValue('test_description') || '自动化测试';
        const additionalContext = form.getFieldValue('additional_context') || urlForm.getFieldValue('additional_context');
        const sourceUrl = urlForm.getFieldValue('url');

        // 生成脚本名称
        const scriptName = `AI生成${script.format.toUpperCase()}脚本_${new Date().toLocaleDateString()}`;
        const description = `基于AI分析自动生成的${script.format.toUpperCase()}自动化测试脚本`;

        // 确定脚本类型
        const scriptType = activeTab === 'image' ? 'image_analysis' : 'url_analysis';

        // 自动标签
        const autoTags = [
          script.format.toUpperCase(),
          'AI生成',
          '自动保存',
          scriptType === 'image_analysis' ? '图片分析' : 'URL分析'
        ];

        try {
          const response = await saveScriptFromSession({
            session_id: sessionId,
            name: scriptName,
            description: description,
            script_format: script.format as 'yaml' | 'playwright',
            script_type: scriptType,
            test_description: testDescription,
            content: script.content,
            additional_context: additionalContext,
            source_url: sourceUrl,
            tags: autoTags
          });

          console.log(`脚本自动保存成功: ${response.script_id} - ${scriptName}`);

          // 显示成功通知
          message.success(`${script.format.toUpperCase()}脚本已自动保存到数据库`);

        } catch (error: any) {
          console.error(`自动保存脚本失败:`, error);
          message.warning(`${script.format.toUpperCase()}脚本自动保存失败: ${error.message}`);
        }
      }

      // 显示总体成功信息
      if (scripts.length > 0) {
        toast.success(`已自动保存${scripts.length}个脚本到数据库！`);

        // 显示提示信息
        Modal.info({
          title: '脚本自动保存成功',
          content: (
            <div>
              <p>✅ 已成功将生成的脚本自动保存到数据库！</p>
              <p><strong>保存数量:</strong> {scripts.length}个脚本</p>
              <p><strong>脚本格式:</strong> {scripts.map(s => s.format.toUpperCase()).join(', ')}</p>
              <p>您可以在"执行测试"页面的"脚本管理"中查看和管理这些脚本。</p>
            </div>
          ),
          onOk: () => {
            // 可以选择跳转到执行页面
            // window.open('/web/execution', '_blank');
          }
        });
      }

    } catch (error: any) {
      console.error('自动保存脚本过程中发生错误:', error);
      toast.error(`自动保存脚本失败: ${error.message}`);
    }
  };

  // 执行脚本
  const handleExecuteScript = async () => {
    const currentScript = scripts[activeScriptTab];
    if (!currentScript) return;

    setIsExecutingScript(true);
    try {
      let response;
      if (currentScript.format === 'yaml') {
        response = await executeYAMLContent({
          yaml_content: currentScript.content
        });
      } else {
        response = await executePlaywrightScript({
          script_content: currentScript.content
        });
      }

      toast.success('脚本执行已启动！');
      message.success(`执行ID: ${response.execution_id}`);
    } catch (error: any) {
      toast.error(`执行失败: ${error.message}`);
      message.error('脚本执行失败');
    } finally {
      setIsExecutingScript(false);
    }
  };

  // 编辑脚本内容
  const handleScriptContentChange = (value: string) => {
    const currentScript = scripts[activeScriptTab];
    if (currentScript) {
      setScripts(prev => ({
        ...prev,
        [activeScriptTab]: {
          ...currentScript,
          content: value
        }
      }));

      setIsEditingScript(prev => ({
        ...prev,
        [activeScriptTab]: true
      }));
    }
  };

  // 下载脚本文件
  const handleDownloadScript = () => {
    const currentScript = scripts[activeScriptTab];
    if (!currentScript) return;

    const blob = new Blob([currentScript.content], {
      type: currentScript.format === 'yaml' ? 'text/yaml' : 'text/typescript'
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = currentScript.filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    toast.success(`${currentScript.format.toUpperCase()}文件下载成功！`);
  };



  const handleExecuteTest = () => {
    if (analysisResult) {
      // 跳转到测试执行页面
      window.open(`/web/execution/${analysisResult.session_id}`, '_blank');
    }
  };

  const handleTestDisplayOrder = () => {
    const newSessionId = `test-display-order-${Date.now()}`;
    setCurrentSessionId(newSessionId);
    setIsAnalyzing(true);
    // 测试模式下可以重置内容，因为这是用户主动触发的测试
    setPreserveStreamingContent(false);
    setTestMode(true);
  };

  return (
    <div className="web-test-creation-container">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        {/* Web平台标题 */}
        <Card
          className="platform-header"
          style={{
            marginBottom: 24,
            background: `linear-gradient(135deg, ${apiConfig.platformColor}15 0%, ${apiConfig.platformColor}05 100%)`,
            border: `1px solid ${apiConfig.platformColor}30`
          }}
        >
          <Row align="middle" justify="space-between">
            <Col>
              <Space size="large">
                <div style={{ fontSize: '24px', color: apiConfig.platformColor }}>
                  {apiConfig.platformIcon}
                </div>
                <div>
                  <Title level={3} style={{ margin: 0, color: apiConfig.platformColor }}>
                    {apiConfig.platformName}平台 - 自动化测试生成引擎
                  </Title>
                  <Text type="secondary">
                    使用AI智能分析生成{apiConfig.platformName}自动化测试脚本
                  </Text>
                </div>
              </Space>
            </Col>
            <Col>
              <Space>
                <Tag color={apiConfig.platformColor} style={{ fontSize: '14px', padding: '4px 12px' }}>
                  {apiConfig.platformName}自动化企业级应用
                </Tag>
                <Tag color="blue">AI双模型驱动</Tag>
                <Tag color="blue">Pytest 集成</Tag>
                <Tag color="green">Playwright 集成</Tag>
                <Tag color="blue">Puppeteer 集成</Tag>
                <Tag color="green">MCP服务 支持</Tag>
              </Space>
            </Col>
          </Row>
        </Card>

        <Row gutter={24} style={{ height: 'calc(100vh - 200px)' }}>
          <Col span={16} style={{ height: '100%' }}>
            <Card className="main-card" style={{ height: '100%' }}>
              <Tabs
                activeKey={activeTab}
                onChange={setActiveTab}
                size="large"
                tabBarStyle={{ marginBottom: 24 }}
              >
                <TabPane
                  tab={
                    <span>
                      <UploadOutlined />
                      图片分析
                    </span>
                  }
                  key="image"
                >
                  <Form
                    form={form}
                    layout="vertical"
                    onFinish={handleImageAnalysis}
                    disabled={isAnalyzing}
                  >
                    <Form.Item
                      label="上传UI截图"
                      required
                    >
                      <Upload
                        beforeUpload={handleImageUpload}
                        accept="image/*"
                        maxCount={1}
                        listType="picture-card"
                        className="image-uploader"
                      >
                        {uploadedFile ? null : (
                          <div>
                            <UploadOutlined />
                            <div style={{ marginTop: 8 }}>点击上传</div>
                          </div>
                        )}
                      </Upload>
                      <Text type="secondary">
                        支持 PNG, JPG, JPEG 格式，建议尺寸不超过 5MB
                      </Text>
                    </Form.Item>

                    <Form.Item
                      name="test_description"
                      label="测试需求描述"
                      rules={[{ required: true, message: '请输入测试需求描述' }]}
                    >
                      <TextArea
                        rows={3}
                        placeholder="请详细描述您想要测试的功能，例如：测试用户登录功能，包括正常登录、错误密码、空字段验证等场景"
                      />
                    </Form.Item>

                    <Form.Item
                      name="additional_context"
                      label="额外上下文信息"
                    >
                      <TextArea
                        rows={2}
                        placeholder="可选：提供额外的测试要求或特殊说明"
                      />
                    </Form.Item>

                    <Form.Item
                      label="生成脚本格式"
                    >
                      <div>
                        <Checkbox.Group
                          value={selectedFormats}
                          onChange={setSelectedFormats}
                          style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}
                        >
                          <Checkbox value="yaml">YAML</Checkbox>
                          <Checkbox value="playwright">Playwright</Checkbox>
                        </Checkbox.Group>
                        <Text type="secondary" style={{ display: 'block', marginTop: 8, fontSize: '12px' }}>
                          可以同时生成多种格式的测试脚本
                        </Text>
                      </div>
                    </Form.Item>

                    {/* 数据库保存设置已移除 - UI测试默认自动保存 */}

                    <Form.Item>
                      <Button
                        type="primary"
                        htmlType="submit"
                        size="large"
                        loading={isAnalyzing}
                        icon={<ThunderboltOutlined />}
                        block
                        disabled={selectedFormats.length === 0}
                      >
                        {isAnalyzing ? '正在分析图片...' : '开始AI分析'}
                      </Button>
                    </Form.Item>
                  </Form>
                </TabPane>

                <TabPane
                  tab={
                    <span>
                      <LinkOutlined />
                      网页分析
                    </span>
                  }
                  key="url"
                >
                  <Form
                    form={urlForm}
                    layout="vertical"
                    onFinish={handleURLAnalysis}
                    disabled={isAnalyzing}
                  >
                    <Form.Item
                      name="url"
                      label="网页URL"
                      rules={[
                        { required: true, message: '请输入网页URL' },
                        { type: 'url', message: '请输入有效的URL' }
                      ]}
                    >
                      <Input
                        size="large"
                        placeholder="https://example.com"
                        prefix={<LinkOutlined />}
                      />
                    </Form.Item>

                    <Form.Item
                      name="test_description"
                      label="测试需求描述"
                      rules={[{ required: true, message: '请输入测试需求描述' }]}
                    >
                      <TextArea
                        rows={3}
                        placeholder="请详细描述您想要测试的功能"
                      />
                    </Form.Item>

                    <Form.Item
                      name="additional_context"
                      label="额外上下文信息"
                    >
                      <TextArea
                        rows={2}
                        placeholder="可选：提供额外的测试要求或特殊说明"
                      />
                    </Form.Item>

                    <Form.Item
                      label={
                        <Space>
                          <span>抓取方式</span>
                          <InfoCircleOutlined
                            style={{ color: '#1890ff' }}
                            title="选择单页面抓取或多页面递归抓取"
                          />
                        </Space>
                      }
                    >
                      <Select
                        value={crawlMode}
                        onChange={setCrawlMode}
                        size="large"
                      >
                        <Option value="single">
                          <Space>
                            <GlobalOutlined />
                            <div>
                              <div>单页面抓取</div>
                              <Text type="secondary" style={{ fontSize: '12px' }}>
                                仅分析指定URL页面，快速生成测试脚本
                              </Text>
                            </div>
                          </Space>
                        </Option>
                        <Option value="multi">
                          <Space>
                            <NodeIndexOutlined />
                            <div>
                              <div>多页面递归抓取 (Crawl4AI)</div>
                              <Text type="secondary" style={{ fontSize: '12px' }}>
                                智能抓取整个网站，生成完整测试套件
                              </Text>
                            </div>
                          </Space>
                        </Option>
                      </Select>
                    </Form.Item>

                    {crawlMode === 'multi' && (
                      <Card
                        size="small"
                        title={
                          <Space>
                            <NodeIndexOutlined />
                            <span>多页面抓取配置</span>
                          </Space>
                        }
                        style={{ marginBottom: 16 }}
                      >
                        <Row gutter={16}>
                          <Col span={12}>
                            <Form.Item
                              name="max_pages"
                              label="最大页面数"
                              initialValue={20}
                            >
                              <Select>
                                <Option value={10}>10页 (小型网站)</Option>
                                <Option value={20}>20页 (中型网站)</Option>
                                <Option value={50}>50页 (大型网站)</Option>
                                <Option value={100}>100页 (完整抓取)</Option>
                              </Select>
                            </Form.Item>
                          </Col>
                          <Col span={12}>
                            <Form.Item
                              name="max_depth"
                              label="抓取深度"
                              initialValue={2}
                            >
                              <Select>
                                <Option value={1}>1层 (仅首页链接)</Option>
                                <Option value={2}>2层 (推荐)</Option>
                                <Option value={3}>3层 (深度抓取)</Option>
                                <Option value={4}>4层 (完整抓取)</Option>
                              </Select>
                            </Form.Item>
                          </Col>
                        </Row>

                        <Form.Item
                          name="crawl_strategy"
                          label="抓取策略"
                          initialValue="bfs"
                        >
                          <Select>
                            <Option value="bfs">广度优先 (BFS) - 发现主要功能页面</Option>
                            <Option value="dfs">深度优先 (DFS) - 深入探索功能模块</Option>
                          </Select>
                        </Form.Item>

                        <Form.Item
                          name="user_query"
                          label="内容过滤查询"
                        >
                          <Input
                            placeholder="例如：登录注册功能、购物流程、用户中心"
                            prefix={<RobotOutlined />}
                          />
                          <Text type="secondary" style={{ display: 'block', marginTop: 4 }}>
                            可选：指定关注的功能模块，AI将重点抓取相关页面
                          </Text>
                        </Form.Item>
                      </Card>
                    )}

                    <Row gutter={16}>
                      <Col span={12}>
                        <Form.Item
                          name="viewport_width"
                          label="视口宽度"
                          initialValue={1280}
                        >
                          <Select>
                            <Option value={1280}>1280px (桌面)</Option>
                            <Option value={768}>768px (平板)</Option>
                            <Option value={375}>375px (手机)</Option>
                          </Select>
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item
                          name="viewport_height"
                          label="视口高度"
                          initialValue={960}
                        >
                          <Select>
                            <Option value={960}>960px</Option>
                            <Option value={1024}>1024px</Option>
                            <Option value={667}>667px</Option>
                          </Select>
                        </Form.Item>
                      </Col>
                    </Row>

                    <Form.Item
                      label="生成脚本格式"
                    >
                      <div>
                        <Checkbox.Group
                          value={selectedFormats}
                          onChange={setSelectedFormats}
                          style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}
                        >
                          <Checkbox value="yaml">YAML (MidScene.js)</Checkbox>
                          <Checkbox value="playwright">Playwright + MidScene.js</Checkbox>
                        </Checkbox.Group>
                        <Text type="secondary" style={{ display: 'block', marginTop: 8, fontSize: '12px' }}>
                          可以同时生成多种格式的测试脚本
                        </Text>
                      </div>
                    </Form.Item>

                    <Form.Item>
                      <Button
                        type="primary"
                        htmlType="submit"
                        size="large"
                        loading={isAnalyzing}
                        icon={crawlMode === 'multi' ? <NodeIndexOutlined /> : <ThunderboltOutlined />}
                        block
                        disabled={selectedFormats.length === 0}
                      >
                        {isAnalyzing
                          ? (crawlMode === 'multi' ? '正在抓取网站并生成测试...' : '正在分析网页...')
                          : (crawlMode === 'multi' ? '开始多页面抓取分析' : '开始AI分析')
                        }
                      </Button>
                      {crawlMode === 'multi' && (
                        <Text type="secondary" style={{ display: 'block', marginTop: 8, textAlign: 'center' }}>
                          多页面抓取可能需要较长时间，请耐心等待
                        </Text>
                      )}
                    </Form.Item>
                  </Form>
                </TabPane>
              </Tabs>
            </Card>
          </Col>

          <Col span={8} style={{ height: '100%' }}>
            {/* 流式数据展示组件 */}
            {!showScriptEditor && (
              <div style={{ height: '100%' }}>
                <StreamingDisplay
                  sessionId={currentSessionId}
                  isActive={(isAnalyzing && !!currentSessionId) || preserveStreamingContent}
                  onAnalysisComplete={handleStreamingComplete}
                  onError={handleStreamingError}
                  testMode={testMode}
                />
              </div>
            )}

            {/* 脚本编辑器 */}
            {showScriptEditor && (
              <Card
                title={
                  <Space>
                    <CodeOutlined />
                    <span>脚本编辑器</span>
                    <Button
                      type="text"
                      size="small"
                      icon={<CloseOutlined />}
                      onClick={() => {
                        setShowScriptEditor(false);
                        setScripts({});
                        setIsEditingScript({yaml: false, playwright: false});
                      }}
                    />
                  </Space>
                }
                style={{ height: '100%' }}
                bodyStyle={{ height: 'calc(100% - 60px)', padding: '12px' }}
              >
                {Object.keys(scripts).length > 0 ? (
                  <Tabs
                    activeKey={activeScriptTab}
                    onChange={(key) => setActiveScriptTab(key as 'yaml' | 'playwright')}
                    size="small"
                    tabBarExtraContent={
                      <Space size="small">
                        <Button
                          type="primary"
                          size="small"
                          icon={<SaveOutlined />}
                          onClick={handleSaveScript}
                          loading={isSavingScript}
                          disabled={!isEditingScript[activeScriptTab]}
                        >
                          保存文件
                        </Button>
                        <Button
                          type="default"
                          size="small"
                          icon={<SaveOutlined />}
                          onClick={handleSaveScriptToDatabase}
                          style={{ backgroundColor: '#52c41a', borderColor: '#52c41a', color: 'white' }}
                        >
                          保存到数据库
                        </Button>
                        <Button
                          type="default"
                          size="small"
                          icon={<PlayCircleOutlined />}
                          onClick={handleExecuteScript}
                          loading={isExecutingScript}
                        >
                          执行
                        </Button>
                        <Button
                          type="default"
                          size="small"
                          icon={<DownloadOutlined />}
                          onClick={handleDownloadScript}
                        >
                          下载
                        </Button>
                      </Space>
                    }
                  >
                    {scripts.yaml && (
                      <TabPane tab="YAML" key="yaml">
                        <div style={{ height: 'calc(100vh - 400px)' }}>
                          <TextArea
                            value={scripts.yaml.content}
                            onChange={(e) => handleScriptContentChange(e.target.value)}
                            style={{
                              height: '100%',
                              fontFamily: 'Monaco, Menlo, "Ubuntu Mono", monospace',
                              fontSize: '12px'
                            }}
                            placeholder="YAML脚本内容..."
                          />
                        </div>
                        <div style={{ marginTop: 8, fontSize: '12px', color: '#666' }}>
                          <Text type="secondary">
                            文件名: {scripts.yaml.filename} |
                            格式: {scripts.yaml.format.toUpperCase()} |
                            {isEditingScript.yaml && <span style={{ color: '#faad14' }}> 已修改</span>}
                          </Text>
                        </div>
                      </TabPane>
                    )}
                    {scripts.playwright && (
                      <TabPane tab="Playwright + MidScene.js" key="playwright">
                        <div style={{ height: 'calc(100vh - 400px)' }}>
                          <TextArea
                            value={scripts.playwright.content}
                            onChange={(e) => handleScriptContentChange(e.target.value)}
                            style={{
                              height: '100%',
                              fontFamily: 'Monaco, Menlo, "Ubuntu Mono", monospace',
                              fontSize: '12px'
                            }}
                            placeholder="Playwright + MidScene.js 脚本内容..."
                          />
                        </div>
                        <div style={{ marginTop: 8, fontSize: '12px', color: '#666' }}>
                          <Text type="secondary">
                            文件名: {scripts.playwright.filename} |
                            格式: {scripts.playwright.format.toUpperCase()} |
                            {isEditingScript.playwright && <span style={{ color: '#faad14' }}> 已修改</span>}
                          </Text>
                        </div>
                      </TabPane>
                    )}
                  </Tabs>
                ) : (
                  <div style={{ textAlign: 'center', padding: '50px 0' }}>
                    <Text type="secondary">暂无脚本内容</Text>
                  </div>
                )}
              </Card>
            )}
          </Col>
        </Row>
      </motion.div>
    </div>
  );
};

export default WebTestCreation;
