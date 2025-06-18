import React, { useState } from 'react';
import {
  Card,
  Form,
  Input,
  Switch,
  Button,
  Select,
  InputNumber,
  Typography,
  Divider,
  Space,
  message,
  Row,
  Col,
  Tabs,
  Alert
} from 'antd';
import {
  SettingOutlined,
  ApiOutlined,
  BugOutlined,
  SecurityScanOutlined,
  ThunderboltOutlined,
  SaveOutlined,
  ReloadOutlined
} from '@ant-design/icons';
import { motion } from 'framer-motion';

import './Settings.css';

const { TabPane } = Tabs;
const { Title, Paragraph, Text } = Typography;
const { Option } = Select;

const Settings: React.FC = () => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('general');

  const handleSave = async (values: any) => {
    setLoading(true);
    try {
      // 模拟保存设置
      await new Promise(resolve => setTimeout(resolve, 1000));
      message.success('设置已保存');
      console.log('Settings saved:', values);
    } catch (error) {
      message.error('保存失败');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    form.resetFields();
    message.info('设置已重置');
  };

  return (
    <div className="settings-container">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <div className="page-header">
          <Title level={2}>
            <SettingOutlined className="header-icon" />
            系统设置
          </Title>
          <Paragraph type="secondary">
            配置系统参数、API设置和执行选项
          </Paragraph>
        </div>

        <Card className="settings-card">
          <Tabs
            activeKey={activeTab}
            onChange={setActiveTab}
            size="large"
            tabPosition="left"
            className="settings-tabs"
          >
            <TabPane
              tab={
                <span>
                  <SettingOutlined />
                  通用设置
                </span>
              }
              key="general"
            >
              <Form
                form={form}
                layout="vertical"
                onFinish={handleSave}
                initialValues={{
                  language: 'zh-CN',
                  theme: 'light',
                  autoSave: true,
                  notifications: true,
                  maxConcurrent: 3,
                  defaultTimeout: 300
                }}
              >
                <Title level={4}>界面设置</Title>
                <Row gutter={24}>
                  <Col span={12}>
                    <Form.Item
                      name="language"
                      label="界面语言"
                    >
                      <Select>
                        <Option value="zh-CN">简体中文</Option>
                        <Option value="en-US">English</Option>
                      </Select>
                    </Form.Item>
                  </Col>
                  <Col span={12}>
                    <Form.Item
                      name="theme"
                      label="主题模式"
                    >
                      <Select>
                        <Option value="light">浅色模式</Option>
                        <Option value="dark">深色模式</Option>
                        <Option value="auto">跟随系统</Option>
                      </Select>
                    </Form.Item>
                  </Col>
                </Row>

                <Divider />

                <Title level={4}>功能设置</Title>
                <Row gutter={24}>
                  <Col span={12}>
                    <Form.Item
                      name="autoSave"
                      label="自动保存"
                      valuePropName="checked"
                    >
                      <Switch />
                    </Form.Item>
                    <Text type="secondary">自动保存测试配置和结果</Text>
                  </Col>
                  <Col span={12}>
                    <Form.Item
                      name="notifications"
                      label="桌面通知"
                      valuePropName="checked"
                    >
                      <Switch />
                    </Form.Item>
                    <Text type="secondary">测试完成时显示桌面通知</Text>
                  </Col>
                </Row>

                <Divider />

                <Title level={4}>执行设置</Title>
                <Row gutter={24}>
                  <Col span={12}>
                    <Form.Item
                      name="maxConcurrent"
                      label="最大并发数"
                    >
                      <InputNumber min={1} max={10} style={{ width: '100%' }} />
                    </Form.Item>
                    <Text type="secondary">同时执行的最大测试数量</Text>
                  </Col>
                  <Col span={12}>
                    <Form.Item
                      name="defaultTimeout"
                      label="默认超时时间（秒）"
                    >
                      <InputNumber min={30} max={3600} style={{ width: '100%' }} />
                    </Form.Item>
                    <Text type="secondary">测试执行的默认超时时间</Text>
                  </Col>
                </Row>
              </Form>
            </TabPane>

            <TabPane
              tab={
                <span>
                  <ApiOutlined />
                  API配置
                </span>
              }
              key="api"
            >
              <Form
                layout="vertical"
                initialValues={{
                  apiBaseUrl: 'http://localhost:8000',
                  apiTimeout: 30000,
                  retryCount: 3,
                  retryInterval: 1000
                }}
              >
                <Alert
                  message="API配置"
                  description="配置后端API服务的连接参数"
                  type="info"
                  showIcon
                  style={{ marginBottom: 24 }}
                />

                <Title level={4}>服务器配置</Title>
                <Form.Item
                  name="apiBaseUrl"
                  label="API基础URL"
                  rules={[{ required: true, message: '请输入API基础URL' }]}
                >
                  <Input placeholder="http://localhost:8000" />
                </Form.Item>

                <Row gutter={24}>
                  <Col span={12}>
                    <Form.Item
                      name="apiTimeout"
                      label="请求超时时间（毫秒）"
                    >
                      <InputNumber min={5000} max={120000} style={{ width: '100%' }} />
                    </Form.Item>
                  </Col>
                  <Col span={12}>
                    <Form.Item
                      name="retryCount"
                      label="重试次数"
                    >
                      <InputNumber min={0} max={10} style={{ width: '100%' }} />
                    </Form.Item>
                  </Col>
                </Row>

                <Form.Item
                  name="retryInterval"
                  label="重试间隔（毫秒）"
                >
                  <InputNumber min={500} max={10000} style={{ width: '100%' }} />
                </Form.Item>

                <Divider />

                <Title level={4}>认证配置</Title>
                <Form.Item
                  name="apiKey"
                  label="API密钥"
                >
                  <Input.Password placeholder="输入API密钥（可选）" />
                </Form.Item>

                <Form.Item
                  name="authToken"
                  label="认证令牌"
                >
                  <Input.Password placeholder="输入认证令牌（可选）" />
                </Form.Item>
              </Form>
            </TabPane>

            <TabPane
              tab={
                <span>
                  <ThunderboltOutlined />
                  执行配置
                </span>
              }
              key="execution"
            >
              <Form
                layout="vertical"
                initialValues={{
                  defaultHeaded: false,
                  keepWindow: false,
                  debugMode: false,
                  screenshotOnFailure: true,
                  videoOnFailure: true,
                  generateReport: true,
                  cleanupOnSuccess: false,
                  viewportWidth: 1280,
                  viewportHeight: 960
                }}
              >
                <Alert
                  message="执行配置"
                  description="配置测试执行的默认参数和行为"
                  type="info"
                  showIcon
                  style={{ marginBottom: 24 }}
                />

                <Title level={4}>浏览器设置</Title>
                <Row gutter={24}>
                  <Col span={12}>
                    <Form.Item
                      name="defaultHeaded"
                      label="默认有界面模式"
                      valuePropName="checked"
                    >
                      <Switch />
                    </Form.Item>
                    <Text type="secondary">默认在有界面模式下运行测试</Text>
                  </Col>
                  <Col span={12}>
                    <Form.Item
                      name="keepWindow"
                      label="保持窗口打开"
                      valuePropName="checked"
                    >
                      <Switch />
                    </Form.Item>
                    <Text type="secondary">测试完成后保持浏览器窗口</Text>
                  </Col>
                </Row>

                <Row gutter={24}>
                  <Col span={12}>
                    <Form.Item
                      name="viewportWidth"
                      label="视口宽度"
                    >
                      <InputNumber min={800} max={2560} style={{ width: '100%' }} />
                    </Form.Item>
                  </Col>
                  <Col span={12}>
                    <Form.Item
                      name="viewportHeight"
                      label="视口高度"
                    >
                      <InputNumber min={600} max={1440} style={{ width: '100%' }} />
                    </Form.Item>
                  </Col>
                </Row>

                <Divider />

                <Title level={4}>调试和报告</Title>
                <Row gutter={24}>
                  <Col span={12}>
                    <Form.Item
                      name="debugMode"
                      label="调试模式"
                      valuePropName="checked"
                    >
                      <Switch />
                    </Form.Item>
                    <Text type="secondary">启用详细的调试日志</Text>
                  </Col>
                  <Col span={12}>
                    <Form.Item
                      name="generateReport"
                      label="生成报告"
                      valuePropName="checked"
                    >
                      <Switch />
                    </Form.Item>
                    <Text type="secondary">自动生成测试执行报告</Text>
                  </Col>
                </Row>

                <Row gutter={24}>
                  <Col span={12}>
                    <Form.Item
                      name="screenshotOnFailure"
                      label="失败时截图"
                      valuePropName="checked"
                    >
                      <Switch />
                    </Form.Item>
                    <Text type="secondary">测试失败时自动截图</Text>
                  </Col>
                  <Col span={12}>
                    <Form.Item
                      name="videoOnFailure"
                      label="失败时录制视频"
                      valuePropName="checked"
                    >
                      <Switch />
                    </Form.Item>
                    <Text type="secondary">测试失败时录制执行视频</Text>
                  </Col>
                </Row>

                <Form.Item
                  name="cleanupOnSuccess"
                  label="成功时清理文件"
                  valuePropName="checked"
                >
                  <Switch />
                </Form.Item>
                <Text type="secondary">测试成功时自动清理临时文件</Text>
              </Form>
            </TabPane>

            <TabPane
              tab={
                <span>
                  <SecurityScanOutlined />
                  安全设置
                </span>
              }
              key="security"
            >
              <Alert
                message="安全设置"
                description="配置系统安全相关参数"
                type="warning"
                showIcon
                style={{ marginBottom: 24 }}
              />

              <Form layout="vertical">
                <Title level={4}>访问控制</Title>
                <Form.Item
                  name="enableAuth"
                  label="启用身份验证"
                  valuePropName="checked"
                >
                  <Switch />
                </Form.Item>

                <Form.Item
                  name="sessionTimeout"
                  label="会话超时时间（分钟）"
                >
                  <InputNumber min={5} max={480} style={{ width: '100%' }} />
                </Form.Item>

                <Divider />

                <Title level={4}>数据安全</Title>
                <Form.Item
                  name="encryptData"
                  label="加密敏感数据"
                  valuePropName="checked"
                >
                  <Switch />
                </Form.Item>

                <Form.Item
                  name="logRetention"
                  label="日志保留天数"
                >
                  <InputNumber min={1} max={365} style={{ width: '100%' }} />
                </Form.Item>

                <Form.Item
                  name="autoCleanup"
                  label="自动清理过期数据"
                  valuePropName="checked"
                >
                  <Switch />
                </Form.Item>
              </Form>
            </TabPane>

            <TabPane
              tab={
                <span>
                  <BugOutlined />
                  调试设置
                </span>
              }
              key="debug"
            >
              <Alert
                message="调试设置"
                description="配置系统调试和日志相关参数"
                type="info"
                showIcon
                style={{ marginBottom: 24 }}
              />

              <Form layout="vertical">
                <Title level={4}>日志配置</Title>
                <Form.Item
                  name="logLevel"
                  label="日志级别"
                >
                  <Select>
                    <Option value="error">ERROR</Option>
                    <Option value="warn">WARN</Option>
                    <Option value="info">INFO</Option>
                    <Option value="debug">DEBUG</Option>
                  </Select>
                </Form.Item>

                <Form.Item
                  name="enableConsoleLog"
                  label="启用控制台日志"
                  valuePropName="checked"
                >
                  <Switch />
                </Form.Item>

                <Form.Item
                  name="enableFileLog"
                  label="启用文件日志"
                  valuePropName="checked"
                >
                  <Switch />
                </Form.Item>

                <Divider />

                <Title level={4}>性能监控</Title>
                <Form.Item
                  name="enablePerformanceMonitor"
                  label="启用性能监控"
                  valuePropName="checked"
                >
                  <Switch />
                </Form.Item>

                <Form.Item
                  name="enableMemoryMonitor"
                  label="启用内存监控"
                  valuePropName="checked"
                >
                  <Switch />
                </Form.Item>

                <Form.Item
                  name="monitorInterval"
                  label="监控间隔（秒）"
                >
                  <InputNumber min={1} max={60} style={{ width: '100%' }} />
                </Form.Item>
              </Form>
            </TabPane>
          </Tabs>

          <Divider />

          <div className="settings-actions">
            <Space>
              <Button
                type="primary"
                icon={<SaveOutlined />}
                onClick={() => form.submit()}
                loading={loading}
                size="large"
              >
                保存设置
              </Button>
              <Button
                icon={<ReloadOutlined />}
                onClick={handleReset}
                size="large"
              >
                重置设置
              </Button>
            </Space>
          </div>
        </Card>
      </motion.div>
    </div>
  );
};

export default Settings;
