import React, { useRef, useEffect, useState } from 'react';
import Editor from '@monaco-editor/react';
import { Spin, Alert } from 'antd';
import AceCodeEditor from './AceCodeEditor';

interface CodeEditorProps {
  value: string;
  onChange: (value: string) => void;
  language?: 'typescript' | 'yaml' | 'javascript';
  height?: string | number;
  readOnly?: boolean;
  theme?: 'vs-dark' | 'light';
  placeholder?: string;
  useAceEditor?: boolean; // 新增选项，是否使用Ace编辑器
}

const CodeEditor: React.FC<CodeEditorProps> = ({
  value,
  onChange,
  language = 'typescript',
  height = 400,
  readOnly = false,
  theme = 'vs-dark',
  placeholder = '// 请输入代码...',
  useAceEditor = true // 默认使用Ace编辑器，更稳定
}) => {
  const editorRef = useRef<any>(null);
  const [isEditorReady, setIsEditorReady] = useState(false);
  const [editorError, setEditorError] = useState<string | null>(null);

  // 如果选择使用Ace编辑器，直接返回Ace组件
  if (useAceEditor) {
    return (
      <AceCodeEditor
        value={value}
        onChange={onChange}
        language={language}
        height={height}
        readOnly={readOnly}
        theme={theme === 'vs-dark' ? 'monokai' : 'github'}
        placeholder={placeholder}
      />
    );
  }

  const handleEditorDidMount = (editor: any, monaco: any) => {
    try {
      editorRef.current = editor;
      setIsEditorReady(true);
      setEditorError(null);

      // 简化的TypeScript配置
      if (language === 'typescript') {
        try {
          monaco.languages.typescript.typescriptDefaults.setCompilerOptions({
            target: monaco.languages.typescript.ScriptTarget.ES2020,
            allowNonTsExtensions: true,
            noEmit: true,
            allowJs: true,
            strict: false
          });

          // 简化的Playwright类型定义
          const playwrightTypes = `
declare namespace PlaywrightTest {
  interface Page {
    goto(url: string): Promise<void>;
    click(selector: string): Promise<void>;
    fill(selector: string, value: string): Promise<void>;
    waitForSelector(selector: string): Promise<void>;
  }
  function test(name: string, fn: (page: Page) => Promise<void>): void;
  function expect(actual: any): any;
}`;

          monaco.languages.typescript.typescriptDefaults.addExtraLib(
            playwrightTypes,
            'playwright.d.ts'
          );
        } catch (tsError) {
          console.warn('TypeScript configuration failed, using basic mode:', tsError);
        }
      }
    } catch (error) {
      console.error('Editor mount failed:', error);
      setEditorError('编辑器初始化失败');
    }

      // 设置编辑器选项
      editor.updateOptions({
        fontSize: 14,
        fontFamily: 'Monaco, Menlo, "Ubuntu Mono", Consolas, "Courier New", monospace',
        lineNumbers: 'on',
        automaticLayout: true,
        minimap: { enabled: true },
        wordWrap: 'on',
        readOnly: readOnly,
        tabSize: 2,
        insertSpaces: true
      });

    // 添加快捷键
    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => {
      // Ctrl+S 保存（可以触发父组件的保存事件）
      console.log('Save shortcut triggered');
    });

    // 设置占位符
    if (!value && placeholder) {
      editor.setValue(placeholder);
      editor.setSelection(new monaco.Selection(1, 1, 1, 1));
    }
  };

  const handleEditorChange = (newValue: string | undefined) => {
    if (newValue !== undefined) {
      onChange(newValue);
    }
  };

  const handleEditorError = (error: any) => {
    console.error('Monaco Editor error:', error);
    setEditorError('编辑器加载失败，请刷新页面重试');
  };

  // 根据脚本格式确定语言
  const getLanguage = () => {
    switch (language) {
      case 'yaml':
        return 'yaml';
      case 'javascript':
        return 'javascript';
      case 'typescript':
      default:
        return 'typescript';
    }
  };

  // 根据语言确定默认主题
  const getTheme = () => {
    return theme === 'light' ? 'light' : 'vs-dark';
  };

  // 如果编辑器加载失败，显示降级的文本框
  if (editorError) {
    return (
      <div style={{ border: '1px solid #d9d9d9', borderRadius: '6px', overflow: 'hidden' }}>
        <Alert
          message="代码编辑器加载失败"
          description={editorError}
          type="warning"
          showIcon
          style={{ marginBottom: 8 }}
        />
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          readOnly={readOnly}
          style={{
            width: '100%',
            height: typeof height === 'number' ? `${height}px` : height,
            border: 'none',
            outline: 'none',
            resize: 'none',
            padding: '12px',
            fontFamily: 'Monaco, Menlo, "Ubuntu Mono", Consolas, "Courier New", monospace',
            fontSize: '14px',
            lineHeight: '1.5',
            backgroundColor: '#1e1e1e',
            color: '#d4d4d4'
          }}
        />
      </div>
    );
  }

  return (
    <div style={{ border: '1px solid #d9d9d9', borderRadius: '6px', overflow: 'hidden' }}>
      <Editor
        height={height}
        language={getLanguage()}
        value={value}
        theme={getTheme()}
        onChange={handleEditorChange}
        onMount={handleEditorDidMount}
        loading={<Spin size="large" tip="正在加载代码编辑器..." />}
        options={{
          selectOnLineNumbers: true,
          automaticLayout: true,
          scrollBeyondLastLine: false,
          minimap: { enabled: false }, // 暂时禁用小地图避免问题
          wordWrap: 'on'
        }}
      />
    </div>
  );
};

export default CodeEditor;
