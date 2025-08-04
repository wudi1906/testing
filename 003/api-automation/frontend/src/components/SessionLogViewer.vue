<template>
  <div class="session-log-viewer">
    <!-- 日志展示头部 -->
    <div class="log-header">
      <div class="header-left">
        <n-button 
          text 
          @click="toggleExpanded"
          class="expand-button"
        >
          <template #icon>
            <Icon :icon="expanded ? 'mdi:chevron-down' : 'mdi:chevron-right'" />
          </template>
          会话日志 ({{ logs.length }})
        </n-button>
        <n-tag v-if="sessionId" type="info" size="small">
          {{ sessionId.substring(0, 8) }}...
        </n-tag>
      </div>
      <div class="header-right" v-if="expanded">
        <n-button 
          size="small" 
          @click="refreshLogs"
          :loading="loading"
        >
          <template #icon>
            <Icon icon="mdi:refresh" />
          </template>
          刷新
        </n-button>
        <n-button 
          size="small" 
          @click="clearLogs"
          type="warning"
        >
          <template #icon>
            <Icon icon="mdi:delete-sweep" />
          </template>
          清空
        </n-button>
      </div>
    </div>

    <!-- 日志内容区域 -->
    <div v-show="expanded" class="log-content">
        <div v-if="loading" class="loading-container">
          <n-spin size="small" />
          <span>加载日志中...</span>
        </div>
        
        <div v-else-if="logs.length === 0" class="empty-container">
          <n-empty description="暂无日志记录" />
        </div>
        
        <div v-else class="log-list">
          <div 
            v-for="log in displayLogs" 
            :key="log.log_id"
            class="log-item"
            :class="getLogLevelClass(log.level)"
          >
            <div class="log-header-item">
              <div class="log-time">
                {{ formatTime(log.timestamp) }}
              </div>
              <div class="log-level">
                <n-tag 
                  :type="getLogLevelType(log.level)" 
                  size="small"
                >
                  {{ log.level }}
                </n-tag>
              </div>
              <div class="log-agent">
                {{ log.agent_name }}
              </div>
            </div>
            <div class="log-message">
              {{ log.message }}
            </div>
            <div v-if="log.data && Object.keys(log.data).length > 0" class="log-details">
              <n-collapse>
                <n-collapse-item title="详细信息" name="details">
                  <pre class="log-data">{{ JSON.stringify(log.data, null, 2) }}</pre>
                </n-collapse-item>
              </n-collapse>
            </div>
          </div>
        </div>

        <!-- 分页控制 -->
        <div v-if="logs.length > pageSize" class="pagination-container">
          <n-pagination
            v-model:page="currentPage"
            :page-count="Math.ceil(logs.length / pageSize)"
            :page-size="pageSize"
            show-size-picker
            :page-sizes="[10, 20, 50]"
            @update:page-size="handlePageSizeChange"
          />
        </div>
      </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { Icon } from '@iconify/vue'
import { useMessage } from 'naive-ui'
import api from '@/api'
import { formatTime } from '@/utils'

const props = defineProps({
  sessionId: {
    type: String,
    default: ''
  },
  autoRefresh: {
    type: Boolean,
    default: false
  },
  refreshInterval: {
    type: Number,
    default: 5000 // 5秒
  }
})

const message = useMessage()

// 响应式数据
const expanded = ref(false)
const loading = ref(false)
const logs = ref([])
const currentPage = ref(1)
const pageSize = ref(20)

// 自动刷新定时器
let refreshTimer = null

// 计算属性
const displayLogs = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return logs.value.slice(start, end)
})

// 方法
const toggleExpanded = () => {
  expanded.value = !expanded.value
  if (expanded.value && logs.value.length === 0) {
    refreshLogs()
  }
}

const refreshLogs = async () => {
  if (!props.sessionId || loading.value) return
  
  try {
    loading.value = true
    const response = await api.getSessionLogs(props.sessionId, { limit: 1000 })
    
    if (response.success) {
      logs.value = response.logs.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
    } else {
      message.error('获取日志失败')
    }
  } catch (error) {
    console.error('获取会话日志失败:', error)
    message.error('获取日志失败')
  } finally {
    loading.value = false
  }
}

const clearLogs = () => {
  logs.value = []
  currentPage.value = 1
}

const handlePageSizeChange = (newPageSize) => {
  pageSize.value = newPageSize
  currentPage.value = 1
}

const getLogLevelClass = (level) => {
  const levelMap = {
    'DEBUG': 'log-debug',
    'INFO': 'log-info',
    'WARNING': 'log-warning',
    'ERROR': 'log-error',
    'CRITICAL': 'log-critical'
  }
  return levelMap[level] || 'log-info'
}

const getLogLevelType = (level) => {
  const typeMap = {
    'DEBUG': 'default',
    'INFO': 'info',
    'WARNING': 'warning',
    'ERROR': 'error',
    'CRITICAL': 'error'
  }
  return typeMap[level] || 'info'
}

// 启动自动刷新
const startAutoRefresh = () => {
  if (props.autoRefresh && props.sessionId) {
    refreshTimer = setInterval(refreshLogs, props.refreshInterval)
  }
}

// 停止自动刷新
const stopAutoRefresh = () => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
}

// 监听sessionId变化
watch(() => props.sessionId, (newSessionId) => {
  if (newSessionId) {
    logs.value = []
    currentPage.value = 1
    if (expanded.value) {
      refreshLogs()
    }
    stopAutoRefresh()
    startAutoRefresh()
  } else {
    stopAutoRefresh()
  }
})

// 监听autoRefresh变化
watch(() => props.autoRefresh, (newValue) => {
  if (newValue) {
    startAutoRefresh()
  } else {
    stopAutoRefresh()
  }
})

// 生命周期
onMounted(() => {
  if (props.sessionId && expanded.value) {
    refreshLogs()
  }
  startAutoRefresh()
})

onUnmounted(() => {
  stopAutoRefresh()
})
</script>

<style scoped>
.session-log-viewer {
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: var(--card-color);
}

.log-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-color);
  background: var(--header-color);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.header-right {
  display: flex;
  gap: 8px;
}

.expand-button {
  font-weight: 500;
}

.log-content {
  max-height: 400px;
  overflow-y: auto;
}

.loading-container,
.empty-container {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
  gap: 8px;
}

.log-list {
  padding: 8px;
}

.log-item {
  padding: 8px 12px;
  margin-bottom: 4px;
  border-radius: 4px;
  border-left: 3px solid transparent;
}

.log-item.log-debug {
  background: var(--debug-bg, #f8f9fa);
  border-left-color: var(--debug-color, #6c757d);
}

.log-item.log-info {
  background: var(--info-bg, #e3f2fd);
  border-left-color: var(--info-color, #2196f3);
}

.log-item.log-warning {
  background: var(--warning-bg, #fff3e0);
  border-left-color: var(--warning-color, #ff9800);
}

.log-item.log-error,
.log-item.log-critical {
  background: var(--error-bg, #ffebee);
  border-left-color: var(--error-color, #f44336);
}

.log-header-item {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 4px;
  font-size: 12px;
}

.log-time {
  color: var(--text-color-3);
  font-family: monospace;
}

.log-agent {
  color: var(--text-color-2);
  font-weight: 500;
}

.log-message {
  font-size: 14px;
  line-height: 1.4;
  color: var(--text-color-1);
}

.log-details {
  margin-top: 8px;
}

.log-data {
  font-size: 12px;
  background: var(--code-bg, #f5f5f5);
  padding: 8px;
  border-radius: 4px;
  overflow-x: auto;
}

.pagination-container {
  padding: 16px;
  border-top: 1px solid var(--border-color);
  display: flex;
  justify-content: center;
}
</style>
