import React, { useState, useEffect } from 'react';
import {
  Card,
  List,
  Button,
  Tag,
  Typography,
  Space,
  Input,
  Select,
  Empty,
  Spin,
  Tooltip
} from 'antd';
import {
  SearchOutlined,
  FilterOutlined,
  ThunderboltOutlined,
  LoginOutlined,
  FormOutlined,
  CompassOutlined,
  ShoppingCartOutlined,
  FileSearchOutlined
} from '@ant-design/icons';
import { motion } from 'framer-motion';
import { useQuery } from 'react-query';

import { getTestTemplates } from '../../services/api';
import './TestTemplates.css';

const { Title, Text, Paragraph } = Typography;
const { Search } = Input;
const { Option } = Select;

interface Template {
  id: string;
  name: string;
  description: string;
  category: string;
  template: {
    test_description: string;
    additional_context: string;
  };
}

interface TestTemplatesProps {
  onTemplateSelect: (template: Template['template'] & { name: string }) => void;
  platform?: string;
  getTemplatesApi?: () => Promise<any>;
}

const categoryIcons: { [key: string]: React.ReactNode } = {
  authentication: <LoginOutlined />,
  forms: <FormOutlined />,
  navigation: <CompassOutlined />,
  search: <FileSearchOutlined />,
  ecommerce: <ShoppingCartOutlined />
};

const categoryColors: { [key: string]: string } = {
  authentication: 'red',
  forms: 'blue',
  navigation: 'green',
  search: 'orange',
  ecommerce: 'purple'
};

const TestTemplates: React.FC<TestTemplatesProps> = ({
  onTemplateSelect,
  platform = 'general',
  getTemplatesApi = getTestTemplates
}) => {
  const [searchText, setSearchText] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [filteredTemplates, setFilteredTemplates] = useState<Template[]>([]);

  const { data: templatesData, isLoading, error } = useQuery(
    ['testTemplates', platform],
    getTemplatesApi,
    {
      staleTime: 5 * 60 * 1000, // 5分钟缓存
    }
  );

  const templates = templatesData?.templates || [];

  useEffect(() => {
    let filtered = templates;

    // 按分类筛选
    if (selectedCategory !== 'all') {
      filtered = filtered.filter((template: Template) => template.category === selectedCategory);
    }

    // 按搜索文本筛选
    if (searchText) {
      filtered = filtered.filter((template: Template) =>
        template.name.toLowerCase().includes(searchText.toLowerCase()) ||
        template.description.toLowerCase().includes(searchText.toLowerCase()) ||
        template.template.test_description.toLowerCase().includes(searchText.toLowerCase())
      );
    }

    setFilteredTemplates(filtered);
  }, [templates, searchText, selectedCategory]);

  const handleTemplateSelect = (template: Template) => {
    onTemplateSelect({
      name: template.name,
      test_description: template.template.test_description,
      additional_context: template.template.additional_context
    });
  };

  const categories = Array.from(new Set(templates.map((t: Template) => t.category)));

  if (error) {
    return (
      <Card title="测试模板" className="templates-card">
        <Empty description="加载模板失败" />
      </Card>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.5 }}
    >
      <Card
        title={
          <Space>
            <ThunderboltOutlined />
            <span>测试模板</span>
            {platform !== 'general' && (
              <Tag color="blue">{platform.toUpperCase()}</Tag>
            )}
          </Space>
        }
        className="templates-card"
        extra={
          <Text type="secondary">
            {filteredTemplates.length} 个模板
          </Text>
        }
      >
        <div className="templates-filters">
          <Search
            placeholder="搜索模板..."
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            style={{ marginBottom: 12 }}
            prefix={<SearchOutlined />}
          />
          
          <Select
            value={selectedCategory}
            onChange={setSelectedCategory}
            style={{ width: '100%', marginBottom: 16 }}
            prefix={<FilterOutlined />}
          >
            <Option value="all">全部分类</Option>
            {categories.map((category) => (
              <Option key={category} value={category}>
                <Space>
                  {categoryIcons[category]}
                  {category}
                </Space>
              </Option>
            ))}
          </Select>
        </div>

        <Spin spinning={isLoading}>
          {filteredTemplates.length === 0 ? (
            <Empty 
              description="没有找到匹配的模板"
              image={Empty.PRESENTED_IMAGE_SIMPLE}
            />
          ) : (
            <List
              dataSource={filteredTemplates}
              renderItem={(template: Template, index: number) => (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.1 }}
                >
                  <List.Item className="template-item">
                    <Card
                      size="small"
                      hoverable
                      className="template-card"
                      onClick={() => handleTemplateSelect(template)}
                    >
                      <div className="template-header">
                        <Space>
                          {categoryIcons[template.category]}
                          <Text strong>{template.name}</Text>
                        </Space>
                        <Tag color={categoryColors[template.category]}>
                          {template.category}
                        </Tag>
                      </div>
                      
                      <Paragraph 
                        className="template-description"
                        ellipsis={{ rows: 2, tooltip: template.description }}
                      >
                        {template.description}
                      </Paragraph>
                      
                      <div className="template-preview">
                        <Text type="secondary" className="preview-label">
                          测试描述预览:
                        </Text>
                        <Paragraph 
                          className="preview-text"
                          ellipsis={{ rows: 2, tooltip: template.template.test_description }}
                        >
                          {template.template.test_description}
                        </Paragraph>
                      </div>
                      
                      <div className="template-actions">
                        <Button 
                          type="primary" 
                          size="small"
                          block
                          onClick={(e) => {
                            e.stopPropagation();
                            handleTemplateSelect(template);
                          }}
                        >
                          使用此模板
                        </Button>
                      </div>
                    </Card>
                  </List.Item>
                </motion.div>
              )}
            />
          )}
        </Spin>

        <div className="templates-footer">
          <Text type="secondary" style={{ fontSize: '12px' }}>
            💡 点击模板卡片可快速应用到表单中
          </Text>
        </div>
      </Card>
    </motion.div>
  );
};

export default TestTemplates;
