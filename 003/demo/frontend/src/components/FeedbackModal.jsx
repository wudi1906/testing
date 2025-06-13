import React, { useState } from 'react'
import { Card, Input, Button, Space, message } from 'antd'
import { CheckOutlined, SendOutlined } from '@ant-design/icons'
import './FeedbackModal.css'

const { TextArea } = Input

const FeedbackModal = ({
  visible,
  onClose,
  onSubmit,
  userProxyMessage = '',
  sessionId
}) => {
  const [feedbackText, setFeedbackText] = useState('')
  const [loading, setLoading] = useState(false)

  const handleAgree = async () => {
    setLoading(true)
    try {
      await onSubmit({
        content: 'APPROVE',
        action: 'agree'
      })
      message.success('已同意')
      onClose()
      setFeedbackText('')
    } catch (error) {
      message.error('操作失败，请重试')
    } finally {
      setLoading(false)
    }
  }

  const handleSend = async () => {
    if (!feedbackText.trim()) {
      message.warning('请输入反馈内容')
      return
    }

    setLoading(true)
    try {
      await onSubmit({
        content: feedbackText.trim(),
        action: 'send'
      })
      message.success('反馈已发送')
      onClose()
      setFeedbackText('')
    } catch (error) {
      message.error('发送失败，请重试')
    } finally {
      setLoading(false)
    }
  }

  if (!visible) return null

  return (
    <div className="feedback-overlay">
      <Card className="feedback-card" title="系统请求用户反馈">
        <div className="feedback-content">
          {userProxyMessage && (
            <div className="user-proxy-message">
              <div className="message-text">{userProxyMessage}</div>
            </div>
          )}

          <div className="feedback-input-section">
            <TextArea
              value={feedbackText}
              onChange={(e) => setFeedbackText(e.target.value)}
              placeholder="请输入您的反馈或建议..."
              rows={3}
              className="feedback-textarea"
            />
          </div>

          <div className="feedback-actions">
            <Space size="large">
              <Button
                type="primary"
                icon={<CheckOutlined />}
                onClick={handleAgree}
                loading={loading}
                className="agree-button"
                size="large"
              >
                同意并继续
              </Button>
              <Button
                type="primary"
                icon={<SendOutlined />}
                onClick={handleSend}
                loading={loading}
                disabled={!feedbackText.trim()}
                className="send-button"
                size="large"
              >
                发送反馈
              </Button>
            </Space>
          </div>
        </div>
      </Card>
    </div>
  )
}

export default FeedbackModal
