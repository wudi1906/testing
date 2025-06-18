import React, { useState, useCallback } from 'react';
import {
  Card,
  Form,
  Input,
  Button,
  Space,
  Switch,
  InputNumber,
  Select,
  Alert,
  Typography,
  Row,
  Col,
  Divider,
  message,
  Tooltip,
  Radio,
  Upload
} from 'antd';
import {
  PlayCircleOutlined,
  UploadOutlined,
  SettingOutlined,
  ThunderboltOutlined,
  FileTextOutlined,
  CodeOutlined,
  BugOutlined
} from '@ant-design/icons';
import { motion } from 'framer-motion';
import toast from 'react-hot-toast';

import {
  // 统一脚本执行API
  executeScript,
  batchExecuteScripts
} from '../../../../services/unifiedScriptApi';
import {
  // 脚本查询API
  searchScripts,
  getAvailableScripts
} from '../../../../services/api';

const { TextArea } = Input;
const { Option } = Select;
const { Text, Title } = Typography;

interface QuickExecutionTabProps {
  onExecutionStart: (sessionId: string, scriptName?: string) => void;
}

const QuickExecutionTab: React.FC<QuickExecutionTabProps> = ({
  onExecutionStart
}) => {
  const [form] = Form.useForm();
  const [executionMode, setExecutionMode] = useState<'existing' | 'upload' | 'content'>('existing');
  const [availableScripts, setAvailableScripts] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [showAdvancedConfig, setShowAdvancedConfig] = useState(false);
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [scriptSource, setScriptSource] = useState<'database' | 'filesystem'>('database');

  // 加载可用脚本列表（根据脚本源加载相应脚本）
  const loadAvailableScripts = useCallback(async () => {
    try {
      let scripts = [];

      if (scriptSource === 'database') {
        // 加载数据库脚本
        const dbData = await searchScripts({
          page: 1,
          page_size: 100,
          sort_by: 'updated_at',
          sort_order: 'desc'
        });

        scripts = dbData.scripts.map(script => ({
          id: script.id,
          name: script.name,
          description: script.description,
          source: 'database'
        }));
      } else {
        // 加载文件系统脚本
        const fsData = await getAvailableScripts();

        scripts = fsData.scripts.map(script => ({
          id: script.name,
          name: script.name,
          description: `文件系统脚本: ${script.name}`,
          source: 'filesystem'
        }));
      }

      setAvailableScripts(scripts);
    } catch (error: any) {
      message.error('加载脚本列表失败');
    }
  }, [scriptSource]);

  React.useEffect(() => {
    if (executionMode === 'existing') {
      loadAvailableScripts();
    }
  }, [executionMode, scriptSource, loadAvailableScripts]);

  // 处理文件上传
  const handleFileUpload = (file: File) => {
    const isValidType = file.name.endsWith('.spec.ts') || file.name.endsWith('.spec.js');
    if (!isValidType) {
      message.error('只支持 .spec.ts 或 .spec.js 格式的测试文件');
      return false;
    }

    const isLt10M = file.size / 1024 / 1024 < 10;
    if (!isLt10M) {
      message.error('文件大小不能超过 10MB');
      return false;
    }

    setUploadedFile(file);
    message.success(`文件 ${file.name} 上传成功`);
    return false; // 阻止自动上传
  };

  // 执行脚本
  const handleExecute = async (values: any) => {
    setLoading(true);
    try {
      let executionData: any = {
        base_url: values.base_url,
        headed: values.headed || false,
        timeout: values.timeout || 90
      };

      // 构建执行配置
      const executionConfig = {
        base_url: values.base_url,
        headed: values.headed,
        timeout: values.timeout,
        viewport_width: values.viewport_width || 1280,
        viewport_height: values.viewport_height || 960,
        network_idle_timeout: values.network_idle_timeout || 2000
      };

      if (values.environment_variables) {
        try {
          const envVars = JSON.parse(values.environment_variables);
          executionConfig.environment_variables = envVars;
        } catch (error) {
          message.error('环境变量格式错误，请检查JSON格式');
          return;
        }
      }

      executionData.execution_config = JSON.stringify(executionConfig);

      let result;
      let scriptName = '';

      if (executionMode === 'existing') {
        // 执行现有脚本
        if (!values.script_name) {
          message.error('请选择要执行的脚本');
          return;
        }

        // 使用统一脚本执行API
        result = await executeScript(
          values.script_name,
          executionConfig
        );
        scriptName = availableScripts.find(s => s.id === values.script_name)?.name || values.script_name;
        
      } else if (executionMode === 'upload') {
        // 上传文件执行
        if (!uploadedFile) {
          message.error('请先上传脚本文件');
          return;
        }
        
        // TODO: 实现文件上传执行逻辑
        message.info('文件上传执行功能开发中...');
        return;
        
      } else if (executionMode === 'content') {
        // 直接执行脚本内容
        if (!values.script_content) {
          message.error('请输入脚本内容');
          return;
        }
        
        // TODO: 实现脚本内容执行逻辑
        message.info('脚本内容执行功能开发中...');
        return;
      }

      toast.success(`脚本执行已启动`);
      message.success(`执行会话: ${result.session_id}`);
      
      onExecutionStart(result.session_id, scriptName);
      
      // 重置表单
      if (executionMode !== 'existing') {
        form.resetFields();
        setUploadedFile(null);
      }
      
    } catch (error: any) {
      toast.error(`执行失败: ${error.message}`);
      message.error('脚本执行失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="quick-execution-tab">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
      >
        <Alert
          message="快速执行说明"
          description="此功能支持快速执行单个脚本，包括选择现有脚本、上传文件或直接输入脚本内容。"
          type="info"
          showIcon
          style={{ marginBottom: 24 }}
        />

        <Card>
          <Form
            form={form}
            layout="vertical"
            onFinish={handleExecute}
            initialValues={{
              headed: false,
              timeout: 90,
              viewport_width: 1280,
              viewport_height: 960,
              network_idle_timeout: 2000,
              environment_variables: '{\n  "baseUrl": "https://example.com"\n}'
            }}
          >
            {/* 执行模式选择 */}
            <Form.Item label="执行模式">
              <Radio.Group
                value={executionMode}
                onChange={(e) => setExecutionMode(e.target.value)}
                buttonStyle="solid"
              >
                <Radio.Button value="existing">
                  <FileTextOutlined /> 选择现有脚本
                </Radio.Button>
                <Radio.Button value="upload">
                  <UploadOutlined /> 上传脚本文件
                </Radio.Button>
                <Radio.Button value="content">
                  <CodeOutlined /> 输入脚本内容
                </Radio.Button>
              </Radio.Group>
            </Form.Item>

            {/* 现有脚本选择 */}
            {executionMode === 'existing' && (
              <>
                <Form.Item label="脚本源">
                  <Radio.Group
                    value={scriptSource}
                    onChange={(e) => {
                      setScriptSource(e.target.value);
                      form.setFieldsValue({ script_name: undefined });
                    }}
                    buttonStyle="solid"
                    size="small"
                  >
                    <Radio.Button value="database">数据库脚本</Radio.Button>
                    <Radio.Button value="filesystem">文件系统脚本</Radio.Button>
                  </Radio.Group>
                </Form.Item>

                <Form.Item
                  name="script_name"
                  label="选择脚本"
                  rules={[{ required: true, message: '请选择要执行的脚本' }]}
                >
                  <Select
                    placeholder={`请选择要执行的${scriptSource === 'database' ? '数据库' : '文件系统'}脚本`}
                    showSearch
                    filterOption={(input, option) =>
                      (option?.children as unknown as string)
                        ?.toLowerCase()
                        ?.includes(input.toLowerCase())
                    }
                    notFoundContent={availableScripts.length === 0 ? "没有可用的脚本" : "未找到匹配的脚本"}
                  >
                    {availableScripts.map(script => (
                      <Option key={script.id || script.name} value={script.id || script.name}>
                        <Space>
                          <FileTextOutlined style={{ color: '#1890ff' }} />
                          <div>
                            <div>{script.name}</div>
                            {script.description && (
                              <div style={{ fontSize: 12, color: '#666' }}>
                                {script.description}
                              </div>
                            )}
                          </div>
                        </Space>
                      </Option>
                    ))}
                  </Select>
                </Form.Item>
              </>
            )}

            {/* 文件上传 */}
            {executionMode === 'upload' && (
              <Form.Item label="上传脚本文件">
                <Upload
                  beforeUpload={handleFileUpload}
                  accept=".spec.ts,.spec.js"
                  maxCount={1}
                  fileList={uploadedFile ? [{
                    uid: '1',
                    name: uploadedFile.name,
                    status: 'done'
                  }] : []}
                  onRemove={() => setUploadedFile(null)}
                >
                  <Button icon={<UploadOutlined />} size="large">
                    选择 Playwright 测试文件
                  </Button>
                </Upload>
                <Text type="secondary" style={{ display: 'block', marginTop: 8 }}>
                  支持 .spec.ts 和 .spec.js 格式的 Playwright 测试文件，文件大小不超过 10MB
                </Text>
              </Form.Item>
            )}

            {/* 脚本内容输入 */}
            {executionMode === 'content' && (
              <Form.Item
                name="script_content"
                label="脚本内容"
                rules={[{ required: true, message: '请输入脚本内容' }]}
              >
                <TextArea
                  rows={12}
                  placeholder={`// 请输入 Playwright 测试脚本内容
import { test, expect } from '@playwright/test';

test('示例测试', async ({ page }) => {
  await page.goto('https://example.com');
  await expect(page).toHaveTitle(/Example/);
});`}
                  style={{ fontFamily: 'Monaco, Menlo, "Ubuntu Mono", monospace' }}
                />
              </Form.Item>
            )}

            <Divider />

            {/* 基础配置 */}
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item
                  name="base_url"
                  label="基础URL"
                  tooltip="测试的起始URL地址"
                >
                  <Input placeholder="https://example.com" />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item
                  name="timeout"
                  label="超时时间（秒）"
                  tooltip="脚本执行的最大超时时间"
                >
                  <InputNumber
                    min={10}
                    max={3600}
                    placeholder="90"
                    style={{ width: '100%' }}
                  />
                </Form.Item>
              </Col>
            </Row>

            <Row gutter={16}>
              <Col span={8}>
                <Form.Item
                  name="headed"
                  label="有界面模式"
                  valuePropName="checked"
                  tooltip="在有界面模式下运行，可以看到浏览器窗口"
                >
                  <Switch />
                </Form.Item>
              </Col>
              <Col span={16}>
                <Form.Item>
                  <Button
                    type="link"
                    icon={<SettingOutlined />}
                    onClick={() => setShowAdvancedConfig(!showAdvancedConfig)}
                  >
                    {showAdvancedConfig ? '隐藏' : '显示'}高级配置
                  </Button>
                </Form.Item>
              </Col>
            </Row>

            {/* 高级配置 */}
            {showAdvancedConfig && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.3 }}
              >
                <Card size="small" style={{ backgroundColor: '#fafafa', marginBottom: 16 }}>
                  <Title level={5}>
                    <BugOutlined /> 高级配置
                  </Title>
                  
                  <Row gutter={16}>
                    <Col span={12}>
                      <Form.Item
                        name="viewport_width"
                        label="视口宽度"
                        tooltip="浏览器视口宽度（像素）"
                      >
                        <InputNumber
                          min={800}
                          max={2560}
                          style={{ width: '100%' }}
                        />
                      </Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item
                        name="viewport_height"
                        label="视口高度"
                        tooltip="浏览器视口高度（像素）"
                      >
                        <InputNumber
                          min={600}
                          max={1440}
                          style={{ width: '100%' }}
                        />
                      </Form.Item>
                    </Col>
                  </Row>

                  <Form.Item
                    name="network_idle_timeout"
                    label="网络空闲超时（毫秒）"
                    tooltip="等待网络空闲的超时时间"
                  >
                    <InputNumber
                      min={1000}
                      max={10000}
                      style={{ width: '100%' }}
                    />
                  </Form.Item>

                  <Form.Item
                    name="environment_variables"
                    label="环境变量 (JSON格式)"
                    tooltip="设置脚本中使用的环境变量"
                  >
                    <TextArea
                      rows={6}
                      placeholder={`{
  "username": "test@example.com",
  "password": "password123",
  "baseUrl": "https://example.com",
  "searchTerm": "JavaScript"
}`}
                    />
                  </Form.Item>
                </Card>
              </motion.div>
            )}

            {/* 执行按钮 */}
            <Form.Item>
              <Space size="large">
                <Button
                  type="primary"
                  htmlType="submit"
                  size="large"
                  loading={loading}
                  icon={<PlayCircleOutlined />}
                  disabled={
                    (executionMode === 'upload' && !uploadedFile) ||
                    loading
                  }
                >
                  {loading ? '执行中...' : '开始执行'}
                </Button>

                <Button
                  size="large"
                  onClick={() => {
                    form.resetFields();
                    setUploadedFile(null);
                  }}
                  disabled={loading}
                >
                  重置
                </Button>
              </Space>
            </Form.Item>
          </Form>
        </Card>
      </motion.div>
    </div>
  );
};

export default QuickExecutionTab;
