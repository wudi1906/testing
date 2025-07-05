import React, { useState } from 'react';
import { Card, Space, Button, Select, Switch } from 'antd';
import CodeEditor from './CodeEditor';

const { Option } = Select;

const CodeEditorTest: React.FC = () => {
  const [code, setCode] = useState(`import { test, expect } from "@playwright/test";

test("示例测试", async ({ page }) => {
  await page.goto("https://example.com");
  await page.click("#login-button");
  await page.fill("#username", "test@example.com");
  await page.fill("#password", "password123");
  await page.click("#submit");
  
  await expect(page.locator(".welcome")).toBeVisible();
});`);

  const [yamlCode, setYamlCode] = useState(`# YAML测试脚本示例
- action: navigate
  target: "https://example.com"
  description: "打开网站首页"

- action: click
  target: "#login-button"
  description: "点击登录按钮"

- action: input
  target: "#username"
  value: "test@example.com"
  description: "输入用户名"

- action: input
  target: "#password"
  value: "password123"
  description: "输入密码"

- action: click
  target: "#submit"
  description: "提交登录表单"`);

  const [language, setLanguage] = useState<'typescript' | 'yaml' | 'javascript'>('typescript');
  const [useAce, setUseAce] = useState(true);

  const getCurrentCode = () => {
    return language === 'yaml' ? yamlCode : code;
  };

  const handleCodeChange = (newCode: string) => {
    if (language === 'yaml') {
      setYamlCode(newCode);
    } else {
      setCode(newCode);
    }
  };

  return (
    <div style={{ padding: '20px' }}>
      <Card title="代码编辑器测试" style={{ marginBottom: '20px' }}>
        <Space style={{ marginBottom: '16px' }}>
          <span>语言:</span>
          <Select value={language} onChange={setLanguage} style={{ width: 120 }}>
            <Option value="typescript">TypeScript</Option>
            <Option value="yaml">YAML</Option>
            <Option value="javascript">JavaScript</Option>
          </Select>
          
          <span>编辑器:</span>
          <Switch
            checked={useAce}
            onChange={setUseAce}
            checkedChildren="Ace"
            unCheckedChildren="Monaco"
          />
          
          <Button onClick={() => console.log('当前代码:', getCurrentCode())}>
            输出代码到控制台
          </Button>
        </Space>

        <CodeEditor
          value={getCurrentCode()}
          onChange={handleCodeChange}
          language={language}
          height={400}
          useAceEditor={useAce}
          placeholder={language === 'yaml' 
            ? '# 请输入YAML格式的测试脚本\n- action: navigate\n  target: "https://example.com"'
            : '// 请输入TypeScript格式的Playwright测试脚本\nimport { test, expect } from "@playwright/test";\n\ntest("测试用例", async ({ page }) => {\n  await page.goto("https://example.com");\n});'
          }
        />
      </Card>
    </div>
  );
};

export default CodeEditorTest;
