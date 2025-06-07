import React, { useState, useRef, useEffect } from 'react'
import { Layout, Typography, Button, Space, message, Input, Avatar } from 'antd'
import {
  SendOutlined,
  MenuOutlined,
  MoreOutlined,
  StarOutlined,
  ShareAltOutlined,
  EditOutlined,
  RobotOutlined,
  UserOutlined
} from '@ant-design/icons'
import { motion, AnimatePresence } from 'framer-motion'
import StreamingText from './components/StreamingText'
import MessageRenderer from './components/MessageRenderer'
import './App.css'

const { Header, Content, Sider } = Layout
const { Title, Text } = Typography
const { TextArea } = Input

function App() {
  const [messages, setMessages] = useState([])
  const [inputValue, setInputValue] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [sessionId] = useState(() => `session_${Date.now()}`)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)

  // 自动滚动到底部
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // 发送消息
  const sendMessage = async () => {
    if (!inputValue.trim() || isStreaming) return

    const userMessage = {
      id: Date.now(),
      type: 'user',
      content: inputValue,
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    setInputValue('')
    setIsStreaming(true)

    // 创建助手消息
    const assistantMessage = {
      id: Date.now() + 1,
      type: 'assistant',
      content: '',
      timestamp: new Date(),
      streaming: true
    }

    setMessages(prev => [...prev, assistantMessage])

    try {
      const response = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: userMessage.content,
          session_id: sessionId
        })
      })

      if (!response.ok) {
        throw new Error('网络请求失败')
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value)
        const lines = chunk.split('\n')

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))
              
              if (data.type === 'chunk' && data.content) {
                setMessages(prev => prev.map(msg => 
                  msg.id === assistantMessage.id 
                    ? { ...msg, content: msg.content + data.content }
                    : msg
                ))
              } else if (data.type === 'end') {
                setMessages(prev => prev.map(msg => 
                  msg.id === assistantMessage.id 
                    ? { ...msg, streaming: false }
                    : msg
                ))
              } else if (data.type === 'error') {
                message.error(data.content)
                setMessages(prev => prev.map(msg => 
                  msg.id === assistantMessage.id 
                    ? { ...msg, content: data.content, streaming: false }
                    : msg
                ))
              }
            } catch (e) {
              console.warn('解析 SSE 数据失败:', e)
            }
          }
        }
      }
    } catch (error) {
      console.error('发送消息失败:', error)
      message.error('发送消息失败，请重试')
      setMessages(prev => prev.map(msg => 
        msg.id === assistantMessage.id 
          ? { ...msg, content: '抱歉，发送消息时出现错误，请重试。', streaming: false }
          : msg
      ))
    } finally {
      setIsStreaming(false)
    }
  }

  // 清除对话
  const clearChat = async () => {
    try {
      await fetch(`/api/chat/session/${sessionId}`, {
        method: 'DELETE'
      })
      setMessages([])
      message.success('对话已清除')
    } catch (error) {
      console.error('清除对话失败:', error)
      message.error('清除对话失败')
    }
  }

  // 处理键盘事件
  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <Layout className="gemini-layout">
      {/* 侧边栏 */}
      <Sider
        className="gemini-sidebar"
        collapsed={sidebarCollapsed}
        collapsedWidth={0}
        width={280}
        trigger={null}
      >
        <div className="sidebar-content">
          <div className="sidebar-header">
            <Title level={4} className="sidebar-title">但问智能</Title>
          </div>

          <Button
            className="new-chat-btn"
            icon={<EditOutlined />}
            onClick={clearChat}
            block
          >
            新对话
          </Button>

          <div className="chat-history">
            <Text className="history-title">最近对话</Text>
            {/* 这里可以添加历史对话列表 */}
          </div>
        </div>
      </Sider>

      {/* 主内容区 */}
      <Layout className="main-layout">
        <Header className="gemini-header">
          <div className="header-left">
            <Button
              type="text"
              icon={<MenuOutlined />}
              onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
              className="menu-btn"
            />
            <Title level={4} className="header-title">但问智能</Title>
          </div>

          <div className="header-right">
            <Space>
              <Button type="text" icon={<ShareAltOutlined />} className="header-btn" />
              <Button type="text" icon={<MoreOutlined />} className="header-btn" />
              <Avatar size="small" className="user-avatar">U</Avatar>
            </Space>
          </div>
        </Header>

      <Content className="app-content">
        <div className="chat-container glass-effect">
          <div className="messages-container">
            <AnimatePresence>
              {messages.length === 0 ? (
                <motion.div 
                  className="welcome-message"
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ duration: 0.5 }}
                >
                  <RobotOutlined className="welcome-icon" />
                  <Title level={4} className="gradient-text">
                    欢迎使用但问智能
                  </Title>
                  <Text className="welcome-text">
                    我是您的 AI 智能助手，有什么可以帮助您的吗？
                  </Text>
                </motion.div>
              ) : (
                messages.map((msg) => (
                  <motion.div
                    key={msg.id}
                    className={`message-wrapper ${msg.type}-message`}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.3 }}
                  >
                    <div className={`message-bubble ${msg.type}`}>
                      <div className="message-header">
                        {msg.type === 'user' ? (
                          <UserOutlined className="message-icon user" />
                        ) : (
                          <RobotOutlined className="message-icon assistant" />
                        )}
                        <Text className="message-time">
                          {msg.timestamp.toLocaleTimeString()}
                        </Text>
                      </div>
                      <div className="message-content">
                        <MessageRenderer
                          content={msg.content}
                          isStreaming={msg.streaming}
                        />
                      </div>
                    </div>
                  </motion.div>
                ))
              )}
            </AnimatePresence>
            <div ref={messagesEndRef} />
          </div>

          <div className="input-container">
            <div className="input-wrapper glass-effect">
              <TextArea
                ref={inputRef}
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="输入您的问题..."
                className="chat-input"
                disabled={isStreaming}
                autoSize={{ minRows: 1, maxRows: 4 }}
              />
              <Button
                type="primary"
                icon={<SendOutlined />}
                onClick={sendMessage}
                loading={isStreaming}
                className="send-button glow-effect"
                disabled={!inputValue.trim()}
              >
                发送
              </Button>
            </div>
          </div>
        </div>
      </Content>
      </Layout>
    </Layout>
  )
}

export default App
