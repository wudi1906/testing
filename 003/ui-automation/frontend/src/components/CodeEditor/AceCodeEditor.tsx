import React from 'react';
import AceEditor from 'react-ace';

// 导入语言模式
import 'ace-builds/src-noconflict/mode-typescript';
import 'ace-builds/src-noconflict/mode-yaml';
import 'ace-builds/src-noconflict/mode-javascript';

// 导入主题
import 'ace-builds/src-noconflict/theme-monokai';
import 'ace-builds/src-noconflict/theme-github';

// 导入扩展
import 'ace-builds/src-noconflict/ext-language_tools';

interface AceCodeEditorProps {
  value: string;
  onChange: (value: string) => void;
  language?: 'typescript' | 'yaml' | 'javascript';
  height?: string | number;
  readOnly?: boolean;
  theme?: 'monokai' | 'github';
  placeholder?: string;
}

const AceCodeEditor: React.FC<AceCodeEditorProps> = ({
  value,
  onChange,
  language = 'typescript',
  height = 400,
  readOnly = false,
  theme = 'monokai',
  placeholder = '// 请输入代码...'
}) => {
  const getMode = () => {
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

  return (
    <div style={{ border: '1px solid #d9d9d9', borderRadius: '6px', overflow: 'hidden' }}>
      <AceEditor
        mode={getMode()}
        theme={theme}
        value={value}
        onChange={onChange}
        name="code-editor"
        editorProps={{ $blockScrolling: true }}
        width="100%"
        height={typeof height === 'number' ? `${height}px` : height}
        readOnly={readOnly}
        placeholder={placeholder}
        fontSize={14}
        showPrintMargin={true}
        showGutter={true}
        highlightActiveLine={true}
        setOptions={{
          enableBasicAutocompletion: true,
          enableLiveAutocompletion: true,
          enableSnippets: true,
          showLineNumbers: true,
          tabSize: 2,
          useWorker: false, // 禁用worker避免加载问题
          wrap: true,
          fontFamily: 'Monaco, Menlo, "Ubuntu Mono", Consolas, "Courier New", monospace'
        }}
        style={{
          fontFamily: 'Monaco, Menlo, "Ubuntu Mono", Consolas, "Courier New", monospace'
        }}
      />
    </div>
  );
};

export default AceCodeEditor;
