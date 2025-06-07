import React from 'react'
import ReactMarkdown from 'react-markdown'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism'
import remarkGfm from 'remark-gfm'
import rehypeRaw from 'rehype-raw'
import { CopyOutlined, CheckOutlined } from '@ant-design/icons'
import { Button, message } from 'antd'
import './MessageRenderer.css'

const MessageRenderer = ({ content, isStreaming = false }) => {
  const [copiedCode, setCopiedCode] = React.useState(null)

  const copyToClipboard = async (code, index) => {
    try {
      await navigator.clipboard.writeText(code)
      setCopiedCode(index)
      message.success('代码已复制到剪贴板')
      setTimeout(() => setCopiedCode(null), 2000)
    } catch (err) {
      message.error('复制失败')
    }
  }

  const CodeBlock = ({ node, inline, className, children, ...props }) => {
    const match = /language-(\w+)/.exec(className || '')
    const language = match ? match[1] : ''
    const code = String(children).replace(/\n$/, '')
    const codeIndex = `${language}-${code.slice(0, 20)}`

    if (!inline && match) {
      return (
        <div className="code-block-wrapper">
          <div className="code-block-header">
            <span className="code-language">{language.toUpperCase()}</span>
            <Button
              type="text"
              size="small"
              icon={copiedCode === codeIndex ? <CheckOutlined /> : <CopyOutlined />}
              onClick={() => copyToClipboard(code, codeIndex)}
              className="copy-button"
            >
              {copiedCode === codeIndex ? '已复制' : '复制'}
            </Button>
          </div>
          <SyntaxHighlighter
            style={vscDarkPlus}
            language={language}
            PreTag="div"
            className="code-block"
            showLineNumbers={code.split('\n').length > 3}
            wrapLines={true}
            wrapLongLines={true}
            customStyle={{
              margin: 0,
              background: '#1e1e1e',
              fontSize: '14px',
              lineHeight: '1.6'
            }}
            {...props}
          >
            {code}
          </SyntaxHighlighter>
        </div>
      )
    }

    return (
      <code className="inline-code" {...props}>
        {children}
      </code>
    )
  }

  const components = {
    code: CodeBlock,
    pre: ({ children }) => <div className="pre-wrapper">{children}</div>,
    blockquote: ({ children }) => (
      <blockquote className="markdown-blockquote">{children}</blockquote>
    ),
    table: ({ children }) => (
      <div className="table-wrapper">
        <table className="markdown-table">{children}</table>
      </div>
    ),
    h1: ({ children }) => <h1 className="markdown-h1">{children}</h1>,
    h2: ({ children }) => <h2 className="markdown-h2">{children}</h2>,
    h3: ({ children }) => <h3 className="markdown-h3">{children}</h3>,
    h4: ({ children }) => <h4 className="markdown-h4">{children}</h4>,
    h5: ({ children }) => <h5 className="markdown-h5">{children}</h5>,
    h6: ({ children }) => <h6 className="markdown-h6">{children}</h6>,
    ul: ({ children }) => <ul className="markdown-ul">{children}</ul>,
    ol: ({ children }) => <ol className="markdown-ol">{children}</ol>,
    li: ({ children }) => <li className="markdown-li">{children}</li>,
    p: ({ children }) => <p className="markdown-p">{children}</p>,
    a: ({ href, children }) => (
      <a href={href} className="markdown-link" target="_blank" rel="noopener noreferrer">
        {children}
      </a>
    ),
    strong: ({ children }) => <strong className="markdown-strong">{children}</strong>,
    em: ({ children }) => <em className="markdown-em">{children}</em>,
    hr: () => <hr className="markdown-hr" />,
  }

  return (
    <div className={`message-renderer ${isStreaming ? 'streaming' : ''}`}>
      <ReactMarkdown
        components={components}
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeRaw]}
        skipHtml={false}
      >
        {content}
      </ReactMarkdown>
      {isStreaming && <span className="cursor-blink">|</span>}
    </div>
  )
}

export default MessageRenderer
