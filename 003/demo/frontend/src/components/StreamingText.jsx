import React, { useState, useEffect } from 'react'
import { Typography } from 'antd'
import './StreamingText.css'

const { Text } = Typography

const StreamingText = ({ content, speed = 50 }) => {
  const [displayedContent, setDisplayedContent] = useState('')
  const [isTyping, setIsTyping] = useState(true)

  useEffect(() => {
    if (!content) {
      setDisplayedContent('')
      setIsTyping(true)
      return
    }

    // 如果内容变化，重新开始打字效果
    if (content !== displayedContent) {
      setDisplayedContent(content)
      setIsTyping(content.length > 0)
      
      // 如果内容停止增长，停止打字效果
      const timer = setTimeout(() => {
        setIsTyping(false)
      }, 1000)

      return () => clearTimeout(timer)
    }
  }, [content, displayedContent])

  return (
    <div className="streaming-text-container">
      <Text className="streaming-content">
        {displayedContent}
        {isTyping && <span className="typing-cursor">|</span>}
      </Text>
    </div>
  )
}

export default StreamingText
