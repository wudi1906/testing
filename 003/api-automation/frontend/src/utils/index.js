export * from './common'
export * from './storage'
export * from './http'
export * from './auth'

// 时间格式化工具函数
export const formatTime = (time) => {
  if (!time) return '-'
  const date = new Date(time)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

// 文件大小格式化工具函数
export const formatFileSize = (bytes) => {
  if (!bytes || bytes === 0) return '0 B'

  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))

  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

// 数字格式化工具函数
export const formatNumber = (num) => {
  if (!num && num !== 0) return '-'
  return num.toLocaleString()
}

// 百分比格式化工具函数
export const formatPercent = (value, decimals = 1) => {
  if (!value && value !== 0) return '-'
  return `${Number(value).toFixed(decimals)}%`
}

// 持续时间格式化工具函数
export const formatDuration = (seconds) => {
  if (!seconds && seconds !== 0) return '-'

  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const secs = Math.floor(seconds % 60)

  if (hours > 0) {
    return `${hours}h ${minutes}m ${secs}s`
  } else if (minutes > 0) {
    return `${minutes}m ${secs}s`
  } else {
    return `${secs}s`
  }
}

// 相对时间格式化工具函数
export const formatRelativeTime = (time) => {
  if (!time) return '-'

  const now = new Date()
  const target = new Date(time)
  const diff = now - target

  const seconds = Math.floor(diff / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)
  const days = Math.floor(hours / 24)

  if (days > 0) {
    return `${days}天前`
  } else if (hours > 0) {
    return `${hours}小时前`
  } else if (minutes > 0) {
    return `${minutes}分钟前`
  } else {
    return `${seconds}秒前`
  }
}
