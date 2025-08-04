<template>
  <div class="execution-report-detail">
    <!-- 页面头部 -->
    <n-page-header @back="goBack">
      <template #title>
        <span>执行报告详情</span>
      </template>
      <template #subtitle>
        <span v-if="reportDetail">{{ reportDetail.executionId }}</span>
      </template>
      <template #extra>
        <n-space>
          <n-button type="primary" @click="generateReport" :loading="generatingReport">
            <template #icon>
              <n-icon><Icon icon="mdi:file-document" /></n-icon>
            </template>
            重新生成报告
          </n-button>
          <n-button @click="shareReport">
            <template #icon>
              <n-icon><Icon icon="mdi:share" /></n-icon>
            </template>
            分享报告
          </n-button>
          <n-button @click="exportReport">
            <template #icon>
              <n-icon><Icon icon="mdi:download" /></n-icon>
            </template>
            导出报告
          </n-button>
          <n-button @click="refreshDetail">
            <template #icon>
              <n-icon><Icon icon="mdi:refresh" /></n-icon>
            </template>
            刷新
          </n-button>
        </n-space>
      </template>
    </n-page-header>

    <div v-if="loading" class="flex justify-center items-center h-64">
      <n-spin size="large" />
    </div>

    <div v-else-if="reportDetail" class="mt-6">
      <!-- 执行概览卡片 -->
      <n-card title="执行概览" class="mb-6">
        <div class="grid grid-cols-1 md:grid-cols-6 gap-4">
          <n-statistic label="总测试数" :value="reportDetail.totalTests">
            <template #suffix>
              <n-icon><Icon icon="mdi:test-tube" /></n-icon>
            </template>
          </n-statistic>
          <n-statistic label="通过测试" :value="reportDetail.passedTests">
            <template #suffix>
              <n-icon color="#18a058"><Icon icon="mdi:check-circle" /></n-icon>
            </template>
          </n-statistic>
          <n-statistic label="失败测试" :value="reportDetail.failedTests">
            <template #suffix>
              <n-icon color="#d03050"><Icon icon="mdi:close-circle" /></n-icon>
            </template>
          </n-statistic>
          <n-statistic label="跳过测试" :value="reportDetail.skippedTests">
            <template #suffix>
              <n-icon color="#f0a020"><Icon icon="mdi:skip-next-circle" /></n-icon>
            </template>
          </n-statistic>
          <n-statistic label="成功率" :value="`${reportDetail.successRate}%`">
            <template #suffix>
              <n-icon><Icon icon="mdi:percent" /></n-icon>
            </template>
          </n-statistic>
          <n-statistic label="执行时间" :value="`${reportDetail.executionTime}s`">
            <template #suffix>
              <n-icon><Icon icon="mdi:clock" /></n-icon>
            </template>
          </n-statistic>
        </div>

        <!-- 进度条 -->
        <div class="mt-6">
          <div class="flex justify-between items-center mb-2">
            <span class="font-medium">测试进度</span>
            <span class="text-sm text-gray-500">
              {{ reportDetail.passedTests + reportDetail.failedTests + reportDetail.skippedTests }} / {{ reportDetail.totalTests }}
            </span>
          </div>
          <n-progress 
            type="line" 
            :percentage="getProgressPercentage()" 
            :status="getProgressStatus()"
            :color="getProgressColor()"
          />
        </div>
      </n-card>

      <!-- 详细信息标签页 -->
      <n-card>
        <n-tabs type="line" v-model:value="activeTab">
          <!-- 基本信息 -->
          <n-tab-pane name="basic" tab="基本信息">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <h4 class="font-semibold mb-4 text-lg">执行信息</h4>
                <n-descriptions :column="1" bordered>
                  <n-descriptions-item label="执行ID">
                    <n-text code>{{ reportDetail.executionId }}</n-text>
                  </n-descriptions-item>
                  <n-descriptions-item label="会话ID">
                    <n-text code>{{ reportDetail.sessionId }}</n-text>
                  </n-descriptions-item>
                  <n-descriptions-item label="文档名称">{{ reportDetail.documentName }}</n-descriptions-item>
                  <n-descriptions-item label="执行环境">
                    <n-tag :type="getEnvironmentType(reportDetail.environment)">
                      {{ getEnvironmentText(reportDetail.environment) }}
                    </n-tag>
                  </n-descriptions-item>
                  <n-descriptions-item label="执行状态">
                    <n-tag :type="getStatusType(reportDetail.status)">
                      {{ getStatusText(reportDetail.status) }}
                    </n-tag>
                  </n-descriptions-item>
                  <n-descriptions-item label="开始时间">{{ formatTime(reportDetail.startTime) }}</n-descriptions-item>
                  <n-descriptions-item label="结束时间">{{ formatTime(reportDetail.endTime) }}</n-descriptions-item>
                  <n-descriptions-item label="并行执行">
                    <n-tag :type="reportDetail.parallel ? 'success' : 'default'">
                      {{ reportDetail.parallel ? '是' : '否' }}
                    </n-tag>
                  </n-descriptions-item>
                  <n-descriptions-item label="最大工作线程">{{ reportDetail.maxWorkers }}</n-descriptions-item>
                </n-descriptions>
              </div>
              
              <div>
                <h4 class="font-semibold mb-4 text-lg">性能统计</h4>
                <n-descriptions :column="1" bordered>
                  <n-descriptions-item label="平均响应时间">{{ reportDetail.avgResponseTime }}ms</n-descriptions-item>
                  <n-descriptions-item label="最大响应时间">{{ reportDetail.maxResponseTime }}ms</n-descriptions-item>
                  <n-descriptions-item label="最小响应时间">{{ reportDetail.minResponseTime }}ms</n-descriptions-item>
                </n-descriptions>
                
                <h4 class="font-semibold mb-4 mt-6 text-lg">执行配置</h4>
                <div class="bg-gray-50 p-4 rounded">
                  <pre class="text-sm">{{ JSON.stringify(reportDetail.executionConfig, null, 2) }}</pre>
                </div>
                
                <h4 class="font-semibold mb-4 mt-6 text-lg">执行描述</h4>
                <div class="bg-gray-50 p-4 rounded">
                  {{ reportDetail.description || '无描述' }}
                </div>
              </div>
            </div>
          </n-tab-pane>
          
          <!-- 脚本结果 -->
          <n-tab-pane name="scripts" tab="脚本结果">
            <div class="mb-4">
              <n-input
                v-model:value="scriptSearchKeyword"
                placeholder="搜索脚本名称..."
                clearable
                class="w-64"
              >
                <template #prefix>
                  <n-icon><Icon icon="mdi:magnify" /></n-icon>
                </template>
              </n-input>
            </div>
            
            <n-data-table
              :columns="scriptResultColumns"
              :data="filteredScriptResults"
              :pagination="{ pageSize: 20 }"
              max-height="600"
              :row-class-name="getScriptRowClassName"
            />
          </n-tab-pane>
          
          <!-- 报告文件 -->
          <n-tab-pane name="reports" tab="报告文件">
            <div v-if="reportDetail.reportFiles && reportDetail.reportFiles.length">
              <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                <n-card 
                  v-for="report in reportDetail.reportFiles" 
                  :key="report.path"
                  hoverable
                  class="cursor-pointer"
                >
                  <div class="text-center">
                    <n-icon size="48" :color="getFileIconColor(report.format)">
                      <Icon :icon="getFileIcon(report.format)" />
                    </n-icon>
                    <div class="mt-3">
                      <div class="font-medium">{{ report.name }}</div>
                      <div class="text-sm text-gray-500 mt-1">
                        {{ report.format.toUpperCase() }} • {{ formatFileSize(report.size) }}
                      </div>
                      <div class="text-xs text-gray-400 mt-1">
                        {{ formatTime(report.createdAt) }}
                      </div>
                    </div>
                    <div class="mt-4 space-x-2">
                      <n-button size="small" @click="previewReport(report)">预览</n-button>
                      <n-button size="small" type="primary" @click="downloadReport(report)">下载</n-button>
                    </div>
                  </div>
                </n-card>
              </div>
            </div>
            <n-empty v-else description="暂无报告文件" />
          </n-tab-pane>
          
          <!-- 执行日志 -->
          <n-tab-pane name="logs" tab="执行日志">
            <div class="mb-4 flex justify-between items-center">
              <n-space>
                <n-button @click="loadExecutionLogs" :loading="logsLoading">
                  <template #icon>
                    <n-icon><Icon icon="mdi:refresh" /></n-icon>
                  </template>
                  刷新日志
                </n-button>
                <n-select
                  v-model:value="logLevelFilter"
                  :options="logLevelOptions"
                  placeholder="筛选日志级别"
                  clearable
                  style="width: 150px"
                  @update:value="filterLogs"
                />
              </n-space>
              <n-button @click="downloadLogs">
                <template #icon>
                  <n-icon><Icon icon="mdi:download" /></n-icon>
                </template>
                下载日志
              </n-button>
            </div>
            
            <div class="bg-black text-green-400 p-4 rounded font-mono text-sm h-96 overflow-y-auto">
              <div v-for="(log, index) in filteredLogs" :key="index" class="mb-1">
                <span class="text-gray-500">[{{ formatTime(log.timestamp) }}]</span>
                <span :class="getLogLevelClass(log.level)">[{{ log.level }}]</span>
                <span class="text-gray-400">[{{ log.source }}]</span>
                <span>{{ log.message }}</span>
              </div>
              <div v-if="filteredLogs.length === 0" class="text-center text-gray-500">
                暂无日志数据
              </div>
            </div>
          </n-tab-pane>
          
          <!-- 错误详情 -->
          <n-tab-pane 
            name="errors" 
            tab="错误详情" 
            v-if="reportDetail.errorDetails && reportDetail.errorDetails.length"
          >
            <div class="space-y-4">
              <n-alert 
                v-for="(error, index) in reportDetail.errorDetails" 
                :key="index"
                type="error" 
                :title="`错误 ${index + 1}`"
                closable
              >
                <div class="space-y-2">
                  <div><strong>类型:</strong> {{ error.type || 'Unknown' }}</div>
                  <div><strong>消息:</strong> {{ error.message || 'N/A' }}</div>
                  <div><strong>时间:</strong> {{ error.timestamp || 'N/A' }}</div>
                  <div v-if="error.stack">
                    <strong>堆栈跟踪:</strong>
                    <n-code 
                      :code="error.stack" 
                      language="text" 
                      show-line-numbers
                      class="mt-2"
                    />
                  </div>
                </div>
              </n-alert>
            </div>
          </n-tab-pane>
          
          <!-- 性能分析 -->
          <n-tab-pane name="performance" tab="性能分析">
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
              <n-statistic label="总执行时间" :value="`${reportDetail.executionTime}s`" />
              <n-statistic label="平均响应时间" :value="`${reportDetail.avgResponseTime}ms`" />
              <n-statistic label="最大响应时间" :value="`${reportDetail.maxResponseTime}ms`" />
            </div>

            <!-- 性能图表占位 -->
            <div class="border border-dashed border-gray-300 rounded-lg p-8 text-center text-gray-500">
              <n-icon size="64"><Icon icon="mdi:chart-line" /></n-icon>
              <div class="mt-4 text-lg">性能分析图表</div>
              <div class="mt-2">功能开发中，敬请期待...</div>
            </div>
          </n-tab-pane>
        </n-tabs>
      </n-card>
    </div>

    <!-- 报告预览模态框 -->
    <n-modal v-model:show="showPreviewModal" preset="card" title="报告预览" style="width: 95%; height: 90%">
      <div v-if="previewContent" class="report-preview">
        <iframe 
          v-if="previewType === 'html'"
          :srcdoc="previewContent" 
          class="w-full h-full border-0"
          style="height: 75vh"
        />
        <n-code 
          v-else
          :code="previewContent" 
          :language="previewType" 
          show-line-numbers
          style="height: 75vh; overflow: auto"
        />
      </div>
    </n-modal>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Icon } from '@iconify/vue'
import { useMessage } from 'naive-ui'
import { 
  getExecutionReportDetail,
  getExecutionLogs,
  generateExecutionReport,
  shareExecutionReport,
  exportExecutionReport,
  previewReportFile,
  getReportDownloadUrl
} from '@/api/execution-reports'
import { formatTime, formatFileSize } from '@/utils'

const route = useRoute()
const router = useRouter()
const message = useMessage()

// 数据
const reportDetail = ref(null)
const executionLogs = ref([])
const previewContent = ref('')
const previewType = ref('html')
const scriptSearchKeyword = ref('')
const logLevelFilter = ref('')

// 状态
const loading = ref(false)
const logsLoading = ref(false)
const generatingReport = ref(false)
const showPreviewModal = ref(false)
const activeTab = ref('basic')

// 计算属性
const filteredScriptResults = computed(() => {
  if (!reportDetail.value?.scriptResults) return []
  
  if (!scriptSearchKeyword.value) {
    return reportDetail.value.scriptResults
  }
  
  return reportDetail.value.scriptResults.filter(script =>
    script.scriptName.toLowerCase().includes(scriptSearchKeyword.value.toLowerCase())
  )
})

const filteredLogs = computed(() => {
  if (!logLevelFilter.value) return executionLogs.value
  
  return executionLogs.value.filter(log => log.level === logLevelFilter.value)
})

// 选项数据
const logLevelOptions = [
  { label: '全部', value: '' },
  { label: 'ERROR', value: 'ERROR' },
  { label: 'WARNING', value: 'WARNING' },
  { label: 'INFO', value: 'INFO' },
  { label: 'DEBUG', value: 'DEBUG' }
]

// 表格列定义
const scriptResultColumns = [
  { title: '脚本名称', key: 'scriptName', width: 200, ellipsis: true },
  {
    title: '状态',
    key: 'status',
    width: 100,
    render: (row) => {
      const type = getStatusType(row.status)
      const text = getStatusText(row.status)
      return h('n-tag', { type }, text)
    }
  },
  { title: '总测试', key: 'totalTests', width: 80 },
  { title: '通过', key: 'passedTests', width: 80 },
  { title: '失败', key: 'failedTests', width: 80 },
  { title: '跳过', key: 'skippedTests', width: 80 },
  { title: '成功率', key: 'successRate', width: 100, render: (row) => `${row.successRate.toFixed(1)}%` },
  { title: '执行时间', key: 'duration', width: 100, render: (row) => `${row.duration}s` },
  { title: '响应时间', key: 'responseTime', width: 100, render: (row) => `${row.responseTime}ms` },
  { title: '错误信息', key: 'errorMessage', ellipsis: true }
]

// 方法
const loadReportDetail = async () => {
  const executionId = route.params.executionId
  if (!executionId) {
    message.error('缺少执行ID参数')
    return
  }

  loading.value = true
  try {
    const response = await getExecutionReportDetail(executionId)
    if (response.success) {
      reportDetail.value = response.data
    } else {
      message.error('加载报告详情失败')
    }
  } catch (error) {
    message.error('加载报告详情失败')
    console.error('加载报告详情失败:', error)
  } finally {
    loading.value = false
  }
}

const loadExecutionLogs = async () => {
  if (!reportDetail.value) return

  logsLoading.value = true
  try {
    const response = await getExecutionLogs(reportDetail.value.executionId)
    if (response.success) {
      executionLogs.value = response.data.logs
    }
  } catch (error) {
    message.error('加载执行日志失败')
    console.error('加载执行日志失败:', error)
  } finally {
    logsLoading.value = false
  }
}

const refreshDetail = () => {
  loadReportDetail()
  if (activeTab.value === 'logs') {
    loadExecutionLogs()
  }
}

const generateReport = async () => {
  if (!reportDetail.value) return

  generatingReport.value = true
  try {
    const response = await generateExecutionReport(reportDetail.value.executionId, {
      execution_id: reportDetail.value.executionId,
      formats: ['html', 'json'],
      include_details: true,
      include_logs: true
    })

    if (response.success) {
      message.success('报告生成成功')
      // 重新加载详情
      loadReportDetail()
    }
  } catch (error) {
    message.error('生成报告失败')
    console.error('生成报告失败:', error)
  } finally {
    generatingReport.value = false
  }
}

const shareReport = async () => {
  if (!reportDetail.value) return

  try {
    const response = await shareExecutionReport(reportDetail.value.executionId)
    if (response.success) {
      // 复制分享链接到剪贴板
      navigator.clipboard.writeText(response.data.share_url)
      message.success('分享链接已复制到剪贴板')
    }
  } catch (error) {
    message.error('分享报告失败')
    console.error('分享报告失败:', error)
  }
}

const exportReport = async () => {
  if (!reportDetail.value) return

  try {
    const response = await exportExecutionReport(reportDetail.value.executionId, 'json')
    if (response.success) {
      message.success('报告导出成功')
      // 下载导出的文件
      const url = response.data.download_url
      const link = document.createElement('a')
      link.href = url
      link.download = `execution_report_${reportDetail.value.executionId}.json`
      link.click()
    }
  } catch (error) {
    message.error('导出报告失败')
    console.error('导出报告失败:', error)
  }
}

const previewReport = async (report) => {
  try {
    const response = await previewReportFile(reportDetail.value.executionId, report.name)

    previewContent.value = response
    previewType.value = report.format
    showPreviewModal.value = true
  } catch (error) {
    message.error('预览报告失败')
    console.error('预览报告失败:', error)
  }
}

const downloadReport = (report) => {
  const url = getReportDownloadUrl(reportDetail.value.executionId, report.name)
  const link = document.createElement('a')
  link.href = url
  link.download = report.name
  link.click()
}

const downloadLogs = () => {
  const logContent = executionLogs.value.map(log =>
    `[${formatTime(log.timestamp)}] [${log.level}] [${log.source}] ${log.message}`
  ).join('\n')

  const blob = new Blob([logContent], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `execution_logs_${reportDetail.value.executionId}.txt`
  link.click()
  URL.revokeObjectURL(url)
}

const filterLogs = () => {
  // 触发计算属性重新计算
}

const goBack = () => {
  router.go(-1)
}

// 工具方法
const getProgressPercentage = () => {
  if (!reportDetail.value || reportDetail.value.totalTests === 0) return 0
  const completed = reportDetail.value.passedTests + reportDetail.value.failedTests + reportDetail.value.skippedTests
  return Math.round((completed / reportDetail.value.totalTests) * 100)
}

const getProgressStatus = () => {
  if (!reportDetail.value) return 'default'

  if (reportDetail.value.status === 'COMPLETED') {
    return reportDetail.value.failedTests > 0 ? 'warning' : 'success'
  } else if (reportDetail.value.status === 'FAILED') {
    return 'error'
  } else if (reportDetail.value.status === 'PROCESSING') {
    return 'active'
  }

  return 'default'
}

const getProgressColor = () => {
  const status = getProgressStatus()
  const colorMap = {
    'success': '#18a058',
    'warning': '#f0a020',
    'error': '#d03050',
    'active': '#2080f0',
    'default': '#d9d9d9'
  }
  return colorMap[status]
}

const getStatusType = (status) => {
  const statusMap = {
    'PENDING': 'default',
    'PROCESSING': 'warning',
    'COMPLETED': 'success',
    'FAILED': 'error',
    'CANCELLED': 'default'
  }
  return statusMap[status] || 'default'
}

const getStatusText = (status) => {
  const statusMap = {
    'PENDING': '等待中',
    'PROCESSING': '处理中',
    'COMPLETED': '已完成',
    'FAILED': '已失败',
    'CANCELLED': '已取消'
  }
  return statusMap[status] || status
}

const getEnvironmentType = (environment) => {
  const envMap = {
    'test': 'info',
    'staging': 'warning',
    'production': 'error'
  }
  return envMap[environment] || 'default'
}

const getEnvironmentText = (environment) => {
  const envMap = {
    'test': '测试环境',
    'staging': '预发布环境',
    'production': '生产环境'
  }
  return envMap[environment] || environment
}

const getFileIcon = (format) => {
  const iconMap = {
    'html': 'mdi:language-html5',
    'json': 'mdi:code-json',
    'xml': 'mdi:xml',
    'txt': 'mdi:file-document-outline',
    'pdf': 'mdi:file-pdf-box'
  }
  return iconMap[format] || 'mdi:file'
}

const getFileIconColor = (format) => {
  const colorMap = {
    'html': '#e34c26',
    'json': '#f39c12',
    'xml': '#3498db',
    'txt': '#95a5a6',
    'pdf': '#e74c3c'
  }
  return colorMap[format] || '#95a5a6'
}

const getScriptRowClassName = (row) => {
  if (row.status === 'FAILED') return 'error-row'
  if (row.status === 'COMPLETED' && row.failedTests > 0) return 'warning-row'
  return ''
}

const getLogLevelClass = (level) => {
  const classMap = {
    'ERROR': 'text-red-400',
    'WARNING': 'text-yellow-400',
    'INFO': 'text-blue-400',
    'DEBUG': 'text-gray-400'
  }
  return classMap[level] || 'text-green-400'
}

// 监听标签页切换
watch(activeTab, (newTab) => {
  if (newTab === 'logs' && executionLogs.value.length === 0) {
    loadExecutionLogs()
  }
})

onMounted(() => {
  loadReportDetail()
})
</script>

<style scoped>
.execution-report-detail {
  padding: 20px;
}

.report-preview {
  height: 75vh;
}

:deep(.error-row) {
  background-color: #fef2f2;
}

:deep(.warning-row) {
  background-color: #fffbeb;
}
</style>
