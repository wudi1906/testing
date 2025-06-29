/**
 * Web测试创建组件 V2 - 简化版本
 * 支持基于自然语言描述编写测试用例，图片自动生成描述，以及多格式脚本生成
 */
import React, { useState, useCallback, useRef } from 'react';
import {
  Card,
  Row,
  Col,
  Button,
  Upload,
  Select,
  Space,
  Typography,
  Divider,
  message,
  Form,
  Input,
  Alert,
  Tag,
  Progress,
} from 'antd';
import {
  PictureOutlined,
  PlayCircleOutlined,
  ClearOutlined,
  RobotOutlined
} from '@ant-design/icons';
import MDEditor from '@uiw/react-md-editor';

import {
  analyzeImageToDescription,
  generateTestFromText,
  getGeneratedScripts,
  saveScriptFromSession
} from '../../../../services/api';
import './WebTestCreation.css';

const { Title, Text, Paragraph } = Typography;
const { Option } = Select;

const WebTestCreation: React.FC = () => {
  // 基础状态
  const [form] = Form.useForm();
  const [testDescription, setTestDescription] = useState<string>('');
  const [selectedFormats, setSelectedFormats] = useState<string[]>(['yaml']);
  // 移除了activeTab状态，因为只保留手动编写标签页

  // 处理状态
  const [isGenerating, setIsGenerating] = useState(false);
  const [isAnalyzingImage, setIsAnalyzingImage] = useState(false);

  // 图片上传状态
  const [imagePreview, setImagePreview] = useState<string>('');
  const [showImageUpload, setShowImageUpload] = useState(false);

  // 右侧面板状态
  const [analysisLog, setAnalysisLog] = useState<string>('');
  const [analysisProgress, setAnalysisProgress] = useState(0);
  const [currentStep, setCurrentStep] = useState<string>('');
  const [infoOutput, setInfoOutput] = useState<string>(''); // 信息输出区域

  // 使用ref跟踪分析完成状态，避免闭包问题
  const analysisCompletedRef = useRef(false);

  // 处理图片上传和分析
  const handleImageUpload = useCallback(async (file: any) => {
    try {
      setIsAnalyzingImage(true);
      setAnalysisProgress(0);
      setCurrentStep('准备分析...');
      analysisCompletedRef.current = false;

      // 创建预览
      const reader = new FileReader();
      reader.onload = (e) => {
        setImagePreview(e.target?.result as string);
      };
      reader.readAsDataURL(file);

      // 清空现有内容和日志
      setTestDescription('');
      setAnalysisLog('🔍 开始分析界面截图...\n');

      // 创建FormData并调用新的API
      const formData = new FormData();
      formData.append('file', file);
      formData.append('analysis_type', 'description_generation');
      formData.append('additional_context', form.getFieldValue('additional_context') || '');

      setCurrentStep('启动分析任务...');
      setAnalysisProgress(10);

      // 调用后端API启动图片分析任务
      const response = await fetch('/api/v1/web/create/analyze-image-to-description', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();

      if (result.status === 'success' && result.session_id) {
        setCurrentStep('建立连接...');
        setAnalysisProgress(20);

        // 建立SSE连接接收流式数据
        const eventSource = new EventSource(
          `/api/v1/web/create/stream-description/${result.session_id}`
        );

        let finalTestCase = '';
        let currentThought = '';

        eventSource.onopen = () => {
          console.log('SSE连接已建立');
          setAnalysisLog(prev => prev + '✅ 连接已建立\n');
          setCurrentStep('AI正在分析...');
          setAnalysisProgress(30);
        };

        eventSource.addEventListener('connected', (event) => {
          console.log('已连接到描述生成流');
          setAnalysisLog(prev => prev + '🤖 AI智能体已启动\n');
        });

        eventSource.addEventListener('message', (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.content) {
              // 根据region区分处理
              if (data.region === 'testcase') {
                // 最终测试用例显示在富文本编辑器（Markdown格式）
                finalTestCase += data.content;
                setTestDescription(finalTestCase);
                setCurrentStep('生成测试用例...');
                setAnalysisProgress(90);
              } else {
                // 思考过程和分析日志显示在右侧面板
                currentThought += data.content;
                setAnalysisLog(prev => prev + data.content);
                setAnalysisProgress(prev => Math.min(prev + 5, 85));
              }
            }
          } catch (e) {
            console.error('解析SSE消息失败:', e);
            setAnalysisLog(prev => prev + '⚠️ 消息解析错误\n');
          }
        });

        eventSource.addEventListener('final_result', (event) => {
          try {
            // 检查是否有data字段且不为undefined
            if (event.data && event.data !== 'undefined') {
              const data = JSON.parse(event.data);
              console.log('分析完成:', data.content);
              setAnalysisLog(prev => prev + '\n✅ ' + (data.content || '分析完成') + '\n');
              setCurrentStep('分析完成');
              setAnalysisProgress(100);
              analysisCompletedRef.current = true;

              // 如果富文本编辑器还是空的，将思考过程作为最终结果
              if (!finalTestCase.trim() && currentThought.trim()) {
                setTestDescription(currentThought);
              }

              message.success('图片分析完成，已生成测试用例描述');
            } else {
              // 没有具体数据的完成事件
              console.log('分析完成，无具体数据');
              setAnalysisLog(prev => prev + '\n✅ 分析完成\n');
              setCurrentStep('分析完成');
              setAnalysisProgress(100);
              analysisCompletedRef.current = true;

              // 如果富文本编辑器还是空的，将思考过程作为最终结果
              if (!finalTestCase.trim() && currentThought.trim()) {
                setTestDescription(currentThought);
              }

              message.success('图片分析完成，已生成测试用例描述');
            }
            eventSource.close();
            setIsAnalyzingImage(false);
          } catch (e) {
            console.error('解析最终结果失败:', e);
            setAnalysisLog(prev => prev + '❌ 最终结果解析失败\n');
            setCurrentStep('解析错误');
            // 不要因为解析错误就不关闭连接和重置状态
            eventSource.close();
            setIsAnalyzingImage(false);
          }
        });

        eventSource.addEventListener('error', (event) => {
          // 首先检查是否是正常的连接关闭
          if (eventSource.readyState === EventSource.CLOSED && analysisCompletedRef.current) {
            console.log('SSE连接正常关闭（error事件）- 分析已完成');
            eventSource.close();
            setIsAnalyzingImage(false);
            return;
          }

          try {
            // 检查是否有data字段且不为undefined
            if (event.data && event.data !== 'undefined') {
              const data = JSON.parse(event.data);
              console.error('分析错误:', data);
              setAnalysisLog(prev => prev + `❌ 错误: ${data.error || '未知错误'}\n`);
              setCurrentStep('分析失败');
              message.error(`分析失败: ${data.error || '未知错误'}`);
            } else {
              // 没有具体错误信息的情况
              console.error('SSE错误事件，无具体错误信息');
              setAnalysisLog(prev => prev + '❌ 连接或处理过程中出现错误\n');
              setCurrentStep('连接错误');
              message.error('连接或处理过程中出现错误');
            }
          } catch (e) {
            console.error('解析错误消息失败:', e);
            setAnalysisLog(prev => prev + '❌ 分析过程中出现错误\n');
            setCurrentStep('解析错误');
            message.error('分析过程中出现错误');
          }
          eventSource.close();
          setIsAnalyzingImage(false);
        });

        eventSource.onerror = (error) => {
          console.error('SSE连接错误:', error);

          // 检查是否是正常的连接关闭（分析完成后）
          if (eventSource.readyState === EventSource.CLOSED && analysisCompletedRef.current) {
            console.log('SSE连接正常关闭（onerror事件）- 分析已完成');
            eventSource.close();
            setIsAnalyzingImage(false);
            return;
          }

          setAnalysisLog(prev => prev + '❌ 连接中断\n');
          setCurrentStep('连接中断');
          message.error('连接中断，请重试');
          eventSource.close();
          setIsAnalyzingImage(false);
        };

        // 设置超时处理
        setTimeout(() => {
          if (eventSource.readyState !== EventSource.CLOSED) {
            eventSource.close();
            setIsAnalyzingImage(false);
            setCurrentStep('分析超时');
            setAnalysisLog(prev => prev + '⏰ 分析超时\n');
            message.warning('分析超时，请重试');
          }
        }, 60000); // 60秒超时

      } else {
        throw new Error('启动分析任务失败');
      }

    } catch (error: any) {
      console.error('图片分析失败:', error);
      setAnalysisLog(prev => prev + `❌ 分析失败: ${error.message || '未知错误'}\n`);
      setCurrentStep('分析失败');
      message.error(`图片分析失败: ${error.message || '未知错误'}`);
      setIsAnalyzingImage(false);
    }
  }, [form]);

  // 处理基于文本生成测试脚本
  const handleGenerateFromText = useCallback(async () => {
    if (!testDescription.trim()) {
      message.warning('请输入测试用例描述');
      return;
    }

    try {
      setIsGenerating(true);

      // 获取表单数据
      const formValues = form.getFieldsValue();

      // 创建FormData
      const formData = new FormData();
      formData.append('test_case_content', testDescription);
      formData.append('test_description', formValues.test_description || '');
      formData.append('target_format', selectedFormats.join(','));
      formData.append('additional_context', formValues.additional_context || '');

      // 调用后端API启动解析任务（使用与智能解析相同的接口）
      const response = await fetch('/api/v1/web/test-case-parser/parse', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const result = await response.json();

      if (result.status === 'success') {
        message.success('测试脚本生成任务已启动');
        console.log('生成结果:', result);
      } else {
        throw new Error(result.message || '生成失败');
      }

    } catch (error: any) {
      message.error(`生成失败: ${error.message}`);
    } finally {
      setIsGenerating(false);
    }
  }, [testDescription, selectedFormats, form]);

  // 清空所有内容
  const handleClear = useCallback(() => {
    setTestDescription('');
    setImagePreview('');
    setShowImageUpload(false);
    setAnalysisLog('');
    setAnalysisProgress(0);
    setCurrentStep('');
    analysisCompletedRef.current = false;
    form.resetFields();
    message.success('已清空所有内容');
  }, [form]);

  // 切换图片上传显示
  const toggleImageUpload = useCallback(() => {
    setShowImageUpload(!showImageUpload);
    if (showImageUpload) {
      setImagePreview('');
    }
  }, [showImageUpload]);

  // 示例模板
  const exampleTemplates = [
    {
      title: '登录功能测试',
      description: `# 登录功能测试用例

## 测试目标
验证用户登录功能的正确性

## 测试步骤
1. 打开登录页面
2. 输入用户名: admin
3. 输入密码: password123
4. 点击登录按钮
5. 验证登录成功，跳转到首页

## 预期结果
- 登录成功后显示用户信息
- 页面跳转到首页或仪表板`
    },
    {
      title: '表单提交测试',
      description: `# 表单提交测试用例

## 测试目标
验证表单数据提交功能

## 测试步骤
1. 填写姓名字段
2. 选择性别
3. 输入邮箱地址
4. 填写电话号码
5. 点击提交按钮
6. 验证提交成功提示

## 预期结果
- 表单验证通过
- 显示提交成功消息`
    }
  ];

  return (
    <div className="web-test-creation-v2">
      <div>
        <Card
          title={
            <Space size="middle">
              <RobotOutlined style={{ color: '#1890ff', fontSize: '18px' }} />
              <span style={{
                fontSize: '18px',
                fontWeight: 600,
                color: '#1890ff'
              }}>
                AI智能测试创建
              </span>
              <Tag color="blue" style={{ borderRadius: '6px', fontWeight: 500 }}>V2.0</Tag>
            </Space>
          }
          extra={
            <Space>
              <Button
                icon={<ClearOutlined />}
                onClick={handleClear}
                type="text"
              >
                清空
              </Button>
            </Space>
          }
        >
          <Row gutter={[16, 16]} style={{ minHeight: '650px', alignItems: 'stretch' }}>
            {/* 左侧：输入区域 */}
            <Col xs={24} lg={14}>
              <div className="test-creation-section">
                {/* 标题和操作按钮 */}
                <div style={{ marginBottom: 12, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div style={{ flex: 1 }}>
                    <Text strong style={{
                      fontSize: 16,
                      color: '#1e293b',
                      fontWeight: 600
                    }}>
                      📝 测试用例描述
                    </Text>
                    <Paragraph type="secondary" style={{
                      margin: '4px 0 0 0',
                      fontSize: 13,
                      color: '#64748b'
                    }}>
                      手工编写测试用例或上传界面截图自动生成
                    </Paragraph>
                  </div>
                  <Button
                    type={showImageUpload ? "primary" : "default"}
                    icon={<PictureOutlined />}
                    onClick={toggleImageUpload}
                    loading={isAnalyzingImage}
                    size="small"
                    style={{
                      borderRadius: '8px',
                      fontWeight: 500
                    }}
                  >
                    {showImageUpload ? '隐藏' : '图片'}
                  </Button>
                </div>

                {/* 图片上传区域（可折叠） */}
                {showImageUpload && (
                  <div className="image-upload-section" style={{ marginBottom: 12 }}>
                    <Upload.Dragger
                      accept="image/*"
                      beforeUpload={(file) => {
                        handleImageUpload(file);
                        return false;
                      }}
                      showUploadList={false}
                      style={{ marginBottom: 12 }}
                    >
                      {imagePreview ? (
                        <div style={{ padding: 16 }}>
                          <img
                            src={imagePreview}
                            alt="预览"
                            style={{ maxWidth: '100%', maxHeight: 120 }}
                          />
                          <p style={{ marginTop: 6, color: '#666', fontSize: 12 }}>点击重新上传</p>
                        </div>
                      ) : (
                        <div style={{ padding: 20 }}>
                          <PictureOutlined style={{ fontSize: 28, color: '#1890ff' }} />
                          <p style={{ margin: '8px 0 4px 0' }}>点击或拖拽图片上传</p>
                          <p style={{ color: '#999', fontSize: 11, margin: 0 }}>支持 JPG、PNG、GIF 格式</p>
                        </div>
                      )}
                    </Upload.Dragger>

                    {isAnalyzingImage && (
                      <Alert
                        message="正在分析图片..."
                        description="AI正在分析您上传的图片并生成测试用例描述，请稍候"
                        type="info"
                        showIcon
                        style={{ marginBottom: 16 }}
                      />
                    )}
                  </div>
                )}

                {/* 富文本编辑器 */}
                <div className="text-input-section">
                  <MDEditor
                    value={testDescription}
                    onChange={(val) => setTestDescription(val || '')}
                    height={showImageUpload ? 200 : 250}
                    preview="edit"
                    hideToolbar={false}
                    data-color-mode="light"
                  />

                  {/* 快速模板 */}
                  <div style={{
                    marginTop: 12,
                    padding: '12px',
                    background: 'rgba(248, 250, 252, 0.8)',
                    borderRadius: '8px',
                    border: '1px solid rgba(226, 232, 240, 0.6)'
                  }}>
                    <Space wrap size="small">
                      <Text strong style={{ color: '#475569', fontSize: '13px' }}>
                        💡 模板：
                      </Text>
                      {exampleTemplates.map((template, index) => (
                        <Button
                          key={index}
                          size="small"
                          type="dashed"
                          onClick={() => setTestDescription(template.description)}
                          style={{
                            borderRadius: '6px',
                            fontSize: '12px',
                            height: '28px',
                            padding: '0 8px',
                            borderColor: '#cbd5e1',
                            color: '#475569'
                          }}
                        >
                          {template.title}
                        </Button>
                      ))}
                    </Space>
                  </div>
                </div>

                <Divider style={{
                  margin: '20px 0',
                  borderColor: 'rgba(226, 232, 240, 0.8)'
                }} />

                {/* 配置选项 */}
                <div style={{
                  background: 'rgba(255, 255, 255, 0.9)',
                  padding: '16px',
                  borderRadius: '8px',
                  border: '1px solid rgba(255, 255, 255, 0.3)',
                  backdropFilter: 'blur(8px)'
                }}>
                  <Text strong style={{
                    fontSize: '14px',
                    color: '#1e293b',
                    marginBottom: '12px',
                    display: 'block'
                  }}>
                    ⚙️ 生成配置
                  </Text>
                  <Form form={form} layout="vertical" size="small">
                    <Row gutter={16}>
                      <Col span={12}>
                        <Form.Item label="生成格式" name="generate_formats">
                          <Select
                            mode="multiple"
                            placeholder="选择要生成的脚本格式"
                            value={selectedFormats}
                            onChange={setSelectedFormats}
                          >
                            <Option value="yaml">YAML (MidScene.js)</Option>
                            <Option value="playwright">Playwright + MidScene.js</Option>
                          </Select>
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item label="额外上下文" name="additional_context">
                          <Input.TextArea
                            placeholder="补充说明或特殊要求（可选）"
                            rows={2}
                          />
                        </Form.Item>
                      </Col>
                    </Row>
                  </Form>
                </div>

                {/* 生成按钮 */}
                <div style={{
                  textAlign: 'center',
                  marginTop: 20,
                  padding: '16px',
                  background: 'rgba(255, 255, 255, 0.6)',
                  borderRadius: '12px',
                  border: '1px solid rgba(255, 255, 255, 0.3)'
                }}>
                  <Button
                    type="primary"
                    size="large"
                    icon={<PlayCircleOutlined />}
                    onClick={handleGenerateFromText}
                    loading={isGenerating}
                    disabled={!testDescription.trim() || selectedFormats.length === 0}
                    style={{
                      fontSize: '14px',
                      fontWeight: 600,
                      height: '44px',
                      padding: '0 32px',
                      borderRadius: '10px'
                    }}
                  >
                    {isGenerating ? '🤖 生成中...' : '🚀 生成脚本'}
                  </Button>
                </div>
              </div>
            </Col>
            
            {/* 右侧：分析过程和结果展示区域 */}
            <Col xs={24} lg={10} style={{ display: 'flex', flexDirection: 'column' }}>
              <Card
                title={
                  <Space size="middle">
                    <RobotOutlined style={{ color: '#3b82f6', fontSize: '18px' }} />
                    <span style={{
                      fontSize: '16px',
                      fontWeight: 600,
                      color: '#1e293b'
                    }}>
                      🤖 AI处理过程
                    </span>
                    {(isAnalyzingImage || isGenerating) && (
                      <Tag color="processing" style={{ borderRadius: '8px', fontWeight: 500 }}>
                        ⚡ 处理中
                      </Tag>
                    )}
                  </Space>
                }
                bodyStyle={{
                  padding: '16px',
                  flex: 1,
                  display: 'flex',
                  flexDirection: 'column'
                }}
                style={{
                  height: '100%', // Card占满容器高度
                  display: 'flex',
                  flexDirection: 'column'
                }}
                size="small"
                extra={
                  <Space>
                    {currentStep && (
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        步骤 {currentStep}
                      </Text>
                    )}
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {analysisLog ? '处理完成' : '等待处理'}
                    </Text>
                  </Space>
                }
              >
                {/* 进度条 - 紧凑布局 */}
                {(isAnalyzingImage || isGenerating) && (
                  <div style={{ marginBottom: 12, flexShrink: 0 }}>
                    <Progress
                      percent={isAnalyzingImage ? analysisProgress : (isGenerating ? 50 : 0)}
                      size="small"
                      status={isAnalyzingImage ? (analysisProgress === 100 ? "success" : "active") : "active"}
                      showInfo={true}
                      format={(percent) => `${percent}%`}
                    />
                  </div>
                )}

                {/* 快速操作区域 */}
                {analysisLog && (
                  <div style={{
                    marginBottom: 12,
                    padding: '8px 12px',
                    background: '#f0f8ff',
                    borderRadius: '6px',
                    border: '1px solid #d6e4ff',
                    flexShrink: 0
                  }}>
                    <Space size="small">
                      <Text style={{ fontSize: 12, color: '#1890ff' }}>
                        📊 {(isAnalyzingImage || isGenerating) ? '处理中...' : '处理完成'}
                      </Text>
                      <Button
                        size="small"
                        type="link"
                        style={{ fontSize: 12, padding: '0 4px', height: 'auto' }}
                        onClick={() => {
                          const element = document.querySelector('.analysis-log-container');
                          if (element) element.scrollTop = element.scrollHeight;
                        }}
                      >
                        跳到底部
                      </Button>
                      <Button
                        size="small"
                        type="link"
                        style={{ fontSize: 12, padding: '0 4px', height: 'auto' }}
                        onClick={() => {
                          setAnalysisLog('');
                          setCurrentStep('');
                          setAnalysisProgress(0);
                        }}
                      >
                        清空日志
                      </Button>
                    </Space>
                  </div>
                )}

                {/* 分析日志 - Markdown渲染 - 确保滚动条显示 */}
                <div
                  className="analysis-log-container"
                  style={{
                    flex: 1, // 自动填充剩余空间
                    minHeight: '450px', // 调整最小高度，为快速操作区域留出空间
                    maxHeight: '600px', // 添加最大高度，确保滚动条显示
                    overflowY: 'scroll', // 强制显示垂直滚动条
                    overflowX: 'hidden', // 隐藏水平滚动
                    backgroundColor: '#f8f9fa',
                    padding: '16px',
                    borderRadius: '8px',
                    border: '1px solid #e8e8e8',
                    fontSize: '14px',
                    lineHeight: '1.6'
                  }}
                >
                  {analysisLog ? (
                    <>
                      <MDEditor.Markdown
                        source={analysisLog}
                        style={{
                          backgroundColor: 'transparent',
                          fontSize: '13px',
                          lineHeight: '1.5',
                          minHeight: 'auto', // 允许内容自然高度
                          overflow: 'visible' // 让内容正常显示
                        }}
                      />
                      {/* 底部操作区域 - 固定在底部 */}
                      {!isAnalyzingImage && (
                        <div style={{
                          marginTop: 'auto',
                          paddingTop: '16px',
                          textAlign: 'center',
                          borderTop: '1px solid #e8e8e8',
                          backgroundColor: '#f8f9fa'
                        }}>
                          <Button
                            size="small"
                            type="text"
                            onClick={() => {
                              setAnalysisLog('');
                              setAnalysisProgress(0);
                              setCurrentStep('');
                            }}
                          >
                            清空日志
                          </Button>
                        </div>
                      )}
                    </>
                  ) : (
                    <div className="empty-state" style={{
                      padding: '20px',
                      textAlign: 'center',
                      display: 'flex',
                      flexDirection: 'column',
                      justifyContent: 'center',
                      height: '100%',
                      minHeight: '400px'
                    }}>
                      <div style={{ marginBottom: 24 }}>
                        <RobotOutlined style={{ fontSize: 48, color: '#d9d9d9', marginBottom: 16 }} />
                        <Text type="secondary" style={{ fontSize: '16px', display: 'block', marginBottom: 8 }}>
                          AI分析助手就绪
                        </Text>
                        <Text type="secondary" style={{ fontSize: '13px' }}>
                          上传图片或输入测试描述开始分析
                        </Text>
                      </div>

                      <div style={{
                        background: '#f6f8fa',
                        padding: '16px',
                        borderRadius: '8px',
                        textAlign: 'left',
                        marginBottom: 16
                      }}>
                        <Text strong style={{ fontSize: '13px', color: '#374151' }}>
                          💡 功能说明：
                        </Text>
                        <div style={{ marginTop: 8, fontSize: '12px', color: '#6b7280', lineHeight: '1.6' }}>
                          • <strong>图片分析</strong>：上传界面截图，AI自动识别元素并生成测试用例<br/>
                          • <strong>文本描述</strong>：手工编写测试场景，AI生成对应脚本<br/>
                          • <strong>实时反馈</strong>：分析过程实时显示，包含思考步骤<br/>
                          • <strong>多格式输出</strong>：支持YAML和Playwright格式
                        </div>
                      </div>

                      <div style={{
                        background: '#fff7e6',
                        padding: '12px',
                        borderRadius: '6px',
                        border: '1px solid #ffd591'
                      }}>
                        <Text style={{ fontSize: '12px', color: '#d46b08' }}>
                          🚀 <strong>快速开始</strong>：点击左侧"图片"按钮上传截图，或直接在文本框中描述测试场景
                        </Text>
                      </div>

                      {/* 临时测试内容 - 用于验证滚动条 */}
                      <div style={{
                        marginTop: 16,
                        padding: '12px',
                        background: '#f0f0f0',
                        borderRadius: '6px',
                        fontSize: '11px',
                        color: '#666'
                      }}>
                        <Text style={{ fontSize: '11px', color: '#999' }}>
                          测试滚动内容区域 - 当内容超出容器高度时，右侧应显示滚动条
                          <br/>这是第2行测试内容
                          <br/>这是第3行测试内容
                          <br/>这是第4行测试内容
                          <br/>这是第5行测试内容
                          <br/>这是第6行测试内容
                          <br/>这是第7行测试内容
                          <br/>这是第8行测试内容
                          <br/>这是第9行测试内容
                          <br/>这是第10行测试内容
                          <br/>滚动条应该在右侧显示
                        </Text>
                      </div>
                    </div>
                  )}
                </div>
              </Card>
            </Col>
          </Row>
        </Card>
      </div>
    </div>
  );
};

export default WebTestCreation;
