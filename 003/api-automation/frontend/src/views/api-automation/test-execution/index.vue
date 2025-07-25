<template>
  <div class="test-execution">
    <!-- 执行控制面板 -->
    <n-card title="测试执行" class="mb-6">
      <template #header-extra>
        <n-space>
          <n-button type="primary" @click="showExecutionModal = true">
            <template #icon>
              <n-icon><Icon icon="mdi:play" /></n-icon>
            </template>
            新建执行
          </n-button>
          <n-button @click="loadExecutions">
            <template #icon>
              <n-icon><Icon icon="mdi:refresh" /></n-icon>
            </template>
            刷新
          </n-button>
        </n-space>
      </template>

      <!-- 筛选条件 -->
      <div class="grid grid-cols-1 md:grid-cols-5 gap-4 mb-4">
        <n-select
          v-model:value="filters.status"
          :options="statusOptions"
          placeholder="执行状态"
          clearable
          @update:value="loadExecutions"
        />
        <n-select
          v-model:value="filters.environment"
          :options="environmentOptions"
          placeholder="执行环境"
          clearable
          @update:value="loadExecutions"
        />
        <n-date-picker
          v-model:value="filters.dateRange"
          type="datetimerange"
          placeholder="执行时间"
          @update:value="loadExecutions"
        />
        <n-input
          v-model:value="filters.keyword"
          placeholder="搜索执行会话..."
          clearable
          @keyup.enter="loadExecutions"
        />
        <n-button type="primary" @click="loadExecutions">搜索</n-button>
      </div>
    </n-card>

    <!-- 执行会话列表 -->
    <n-card title="执行会话">
      <n-data-table
        :columns="executionColumns"
        :data="executions"
        :loading="loading"
        :pagination="pagination"
        @update:page="handlePageChange"
      />
    </n-card>

    <!-- 新建执行模态框 -->
    <n-modal v-model:show="showExecutionModal" preset="card" title="新建测试执行" style="width: 600px">
      <n-form ref="executionFormRef" :model="executionForm" label-placement="left" label-width="120px">
        <n-form-item label="选择脚本" path="scriptIds" required>
          <n-select
            v-model:value="executionForm.scriptIds"
            :options="scriptOptions"
            placeholder="选择要执行的测试脚本"
            multiple
            filterable
          />
        </n-form-item>
        
        <n-form-item label="执行环境" path="environment" required>
          <n-select v-model:value="executionForm.environment" :options="environmentOptions" />
        </n-form-item>
        
        <n-form-item label="并行执行">
          <n-switch v-model:value="executionForm.parallelExecution" />
          <span class="ml-2 text-gray-500">启用并行执行可提高效率</span>
        </n-form-item>
        
        <n-form-item v-if="executionForm.parallelExecution" label="最大并发数">
          <n-input-number v-model:value="executionForm.maxWorkers" :min="1" :max="10" />
        </n-form-item>
        
        <n-form-item label="超时时间">
          <n-input-number v-model:value="executionForm.timeout" :min="60" :max="3600" />
          <span class="ml-2 text-gray-500">秒</span>
        </n-form-item>
        
        <n-form-item label="报告格式">
          <n-checkbox-group v-model:value="executionForm.reportFormats">
            <n-space>
              <n-checkbox value="html">HTML</n-checkbox>
              <n-checkbox value="json">JSON</n-checkbox>
              <n-checkbox value="allure">Allure</n-checkbox>
              <n-checkbox value="junit">JUnit XML</n-checkbox>
            </n-space>
          </n-checkbox-group>
        </n-form-item>
        
        <n-form-item label="执行描述">
          <n-input
            v-model:value="executionForm.description"
            type="textarea"
            :rows="3"
            placeholder="描述本次执行的目的..."
          />
        </n-form-item>
      </n-form>

      <template #footer>
        <div class="flex justify-end space-x-2">
          <n-button @click="showExecutionModal = false">取消</n-button>
          <n-button type="primary" @click="startExecution" :loading="starting">开始执行</n-button>
        </div>
      </template>
    </n-modal>

    <!-- 执行详情模态框 -->
    <n-modal v-model:show="showDetailModal" preset="card" title="执行详情" style="width: 90%">
      <div v-if="selectedExecution">
        <div class="grid grid-cols-1 md:grid-cols-5 gap-4 mb-6">
          <n-statistic label="总测试数" :value="selectedExecution.totalTests" />
          <n-statistic label="已执行" :value="selectedExecution.executedTests" />
          <n-statistic label="通过" :value="selectedExecution.passedTests" />
          <n-statistic label="失败" :value="selectedExecution.failedTests" />
          <n-statistic label="成功率" :value="`${selectedExecution.successRate}%`" />
        </div>

        <n-tabs type="line" v-model:value="detailTab">
          <n-tab-pane name="progress" tab="执行进度">
            <div class="mb-4">
              <div class="flex items-center justify-between mb-2">
                <span>执行进度</span>
                <span>{{ selectedExecution.progress }}%</span>
              </div>
              <n-progress 
                type="line" 
                :percentage="selectedExecution.progress" 
                :status="getProgressStatus(selectedExecution.status)"
              />
            </div>
            
            <div v-if="selectedExecution.status === 'running'" class="mb-4">
              <n-alert type="info" title="正在执行">
                当前测试: {{ selectedExecution.currentTest }}
              </n-alert>
            </div>

            <!-- 实时日志 -->
            <div class="mt-4">
              <h4 class="font-semibold mb-2">执行日志</h4>
              <div class="bg-black text-green-400 p-4 rounded font-mono text-sm h-64 overflow-y-auto">
                <div v-for="(log, index) in executionLogs" :key="index" class="mb-1">
                  <span class="text-gray-500">[{{ formatTime(log.timestamp) }}]</span>
                  <span :class="getLogLevelClass(log.level)">[{{ log.level }}]</span>
                  <span>{{ log.message }}</span>
                </div>
              </div>
            </div>
          </n-tab-pane>
          
          <n-tab-pane name="results" tab="测试结果">
            <n-data-table
              :columns="resultColumns"
              :data="testResults"
              :pagination="{ pageSize: 20 }"
              max-height="500"
            />
          </n-tab-pane>
          
          <n-tab-pane name="reports" tab="测试报告">
            <div v-if="selectedExecution.reportFiles && selectedExecution.reportFiles.length">
              <n-list>
                <n-list-item v-for="report in selectedExecution.reportFiles" :key="report.path">
                  <div class="flex items-center justify-between w-full">
                    <div>
                      <div class="font-medium">{{ report.name }}</div>
                      <div class="text-sm text-gray-500">
                        {{ report.format }} • {{ formatFileSize(report.size) }} • {{ formatTime(report.createdAt) }}
                      </div>
                    </div>
                    <n-space>
                      <n-button size="small" @click="previewReport(report)">预览</n-button>
                      <n-button size="small" type="primary" @click="downloadReport(report)">下载</n-button>
                    </n-space>
                  </div>
                </n-list-item>
              </n-list>
            </div>
            <n-empty v-else description="暂无报告文件" />
          </n-tab-pane>
          
          <n-tab-pane name="performance" tab="性能分析">
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
              <n-statistic label="总执行时间" :value="`${selectedExecution.totalExecutionTime}s`" />
              <n-statistic label="平均响应时间" :value="`${selectedExecution.avgResponseTime}ms`" />
              <n-statistic label="最大响应时间" :value="`${selectedExecution.maxResponseTime || 0}ms`" />
            </div>

            <!-- 性能图表占位 -->
            <div class="border border-dashed border-gray-300 rounded-lg p-8 text-center text-gray-500">
              <n-icon size="48"><Icon icon="mdi:chart-line" /></n-icon>
              <div class="mt-2">性能图表功能开发中...</div>
            </div>
          </n-tab-pane>
        </n-tabs>
      </div>

      <template #footer>
        <div class="flex justify-between">
          <n-space>
            <n-button 
              v-if="selectedExecution?.status === 'running'" 
              type="error" 
              @click="stopExecution"
            >
              停止执行
            </n-button>
            <n-button @click="generateReport" :loading="generatingReport">
              生成报告
            </n-button>
          </n-space>
          <n-button @click="showDetailModal = false">关闭</n-button>
        </div>
      </template>
    </n-modal>

    <!-- 报告预览模态框 -->
    <n-modal v-model:show="showReportModal" preset="card" title="报告预览" style="width: 95%; height: 90%">
      <div v-if="previewReportContent" class="report-preview">
        <iframe 
          v-if="previewReportType === 'html'"
          :src="previewReportContent" 
          class="w-full h-full border-0"
          style="height: 70vh"
        />
        <n-code 
          v-else
          :code="previewReportContent" 
          :language="previewReportType" 
          show-line-numbers
          style="height: 70vh; overflow: auto"
        />
      </div>
    </n-modal>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, h } from 'vue'
import { Icon } from '@iconify/vue'
import { NButton, NTag, useMessage } from 'naive-ui'
import api from '@/api'
import { formatTime, formatFileSize } from '@/utils'

const message = useMessage()

// 数据
const executions = ref([])
const loading = ref(false)
const selectedExecution = ref(null)
const testResults = ref([])
const executionLogs = ref([])

// 模态框状态
const showExecutionModal = ref(false)
const showDetailModal = ref(false)
const showReportModal = ref(false)
const detailTab = ref('progress')

// 表单数据
const executionForm = ref({
  scriptIds: [],
  environment: 'test',
  parallelExecution: false,
  maxWorkers: 3,
  timeout: 300,
  reportFormats: ['html', 'json'],
  description: ''
})

// 状态
const starting = ref(false)
const generatingReport = ref(false)
const previewReportContent = ref('')
const previewReportType = ref('html')

// 筛选条件
const filters = ref({
  status: '',
  environment: '',
  dateRange: null,
  keyword: ''
})

// 分页
const pagination = ref({
  page: 1,
  pageSize: 20,
  itemCount: 0,
  showSizePicker: true,
  pageSizes: [10, 20, 50]
})

// 选项数据
const statusOptions = [
  { label: '全部', value: '' },
  { label: '等待中', value: 'pending' },
  { label: '运行中', value: 'running' },
  { label: '已完成', value: 'completed' },
  { label: '已失败', value: 'failed' },
  { label: '已取消', value: 'cancelled' }
]

const environmentOptions = [
  { label: '测试环境', value: 'test' },
  { label: '预发布环境', value: 'staging' },
  { label: '生产环境', value: 'production' }
]

const scriptOptions = ref([])

// 表格列定义
const executionColumns = [
  { title: '会话ID', key: 'executionSessionId', width: 150 },
  { title: '环境', key: 'environment', width: 100 },
  { 
    title: '状态', 
    key: 'status', 
    width: 100,
    render: (row) => {
      const statusMap = {
        'pending': { type: 'default', text: '等待中' },
        'running': { type: 'warning', text: '运行中' },
        'completed': { type: 'success', text: '已完成' },
        'failed': { type: 'error', text: '已失败' },
        'cancelled': { type: 'default', text: '已取消' }
      }
      const status = statusMap[row.status] || { type: 'default', text: '未知' }
      return h(NTag, { type: status.type }, { default: () => status.text })
    }
  },
  { title: '进度', key: 'progress', width: 100, render: (row) => `${row.progress}%` },
  { title: '测试数', key: 'totalTests', width: 80 },
  { title: '通过', key: 'passedTests', width: 80 },
  { title: '失败', key: 'failedTests', width: 80 },
  { title: '成功率', key: 'successRate', width: 100, render: (row) => `${row.successRate}%` },
  { title: '开始时间', key: 'startTime', width: 150, render: (row) => formatTime(row.startTime) },
  { title: '执行时长', key: 'totalExecutionTime', width: 100, render: (row) => `${row.totalExecutionTime}s` },
  {
    title: '操作',
    key: 'actions',
    width: 150,
    render: (row) => [
      h(NButton, 
        { 
          size: 'small', 
          type: 'primary',
          onClick: () => viewExecutionDetail(row)
        }, 
        { default: () => '详情' }
      ),
      h(NButton, 
        { 
          size: 'small', 
          type: 'info',
          style: 'margin-left: 8px',
          onClick: () => viewReports(row)
        }, 
        { default: () => '报告' }
      )
    ]
  }
]

const resultColumns = [
  { title: '测试名称', key: 'testName', width: 200 },
  { 
    title: '状态', 
    key: 'status', 
    width: 100,
    render: (row) => {
      const statusMap = {
        'passed': { type: 'success', text: '通过' },
        'failed': { type: 'error', text: '失败' },
        'skipped': { type: 'default', text: '跳过' }
      }
      const status = statusMap[row.status] || { type: 'default', text: '未知' }
      return h(NTag, { type: status.type }, { default: () => status.text })
    }
  },
  { title: '执行时长', key: 'duration', width: 100, render: (row) => `${row.duration}s` },
  { title: '响应时间', key: 'responseTime', width: 100, render: (row) => `${row.responseTime}ms` },
  { title: '断言', key: 'assertions', width: 100, render: (row) => `${row.passedAssertions}/${row.totalAssertions}` },
  { title: '错误信息', key: 'errorMessage', ellipsis: true }
]

let pollingInterval = null

// 方法
const loadExecutions = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.value.page,
      pageSize: pagination.value.pageSize,
      ...filters.value
    }
    
    if (filters.value.dateRange) {
      params.startTime = filters.value.dateRange[0]
      params.endTime = filters.value.dateRange[1]
    }

    const response = await api.getTestExecutions(params)
    executions.value = response.data.items
    pagination.value.itemCount = response.data.total
  } catch (error) {
    message.error('加载执行记录失败')
  } finally {
    loading.value = false
  }
}

const loadScriptOptions = async () => {
  try {
    const response = await api.getTestScripts({ status: 'ready' })
    scriptOptions.value = response.data.items.map(script => ({
      label: `${script.scriptName} (${script.endpointPath})`,
      value: script.scriptId
    }))
  } catch (error) {
    message.error('加载脚本列表失败')
  }
}

const handlePageChange = (page) => {
  pagination.value.page = page
  loadExecutions()
}

const startExecution = async () => {
  starting.value = true
  try {
    const response = await api.executeTests(executionForm.value)
    
    message.success('测试执行已启动')
    showExecutionModal.value = false
    
    // 重置表单
    executionForm.value = {
      scriptIds: [],
      environment: 'test',
      parallelExecution: false,
      maxWorkers: 3,
      timeout: 300,
      reportFormats: ['html', 'json'],
      description: ''
    }
    
    // 刷新列表
    loadExecutions()
    
    // 自动打开详情页面
    setTimeout(() => {
      const newExecution = executions.value.find(e => e.executionSessionId === response.data.executionSessionId)
      if (newExecution) {
        viewExecutionDetail(newExecution)
      }
    }, 1000)
    
  } catch (error) {
    message.error('启动执行失败')
  } finally {
    starting.value = false
  }
}

const viewExecutionDetail = async (execution) => {
  selectedExecution.value = execution
  
  // 加载测试结果
  try {
    const response = await api.getTestResults({ executionSessionId: execution.executionSessionId })
    testResults.value = response.data
  } catch (error) {
    console.error('加载测试结果失败:', error)
  }
  
  // 加载执行日志
  loadExecutionLogs(execution.executionSessionId)
  
  showDetailModal.value = true
  
  // 如果正在运行，开始轮询
  if (execution.status === 'running') {
    startPolling(execution.executionSessionId)
  }
}

const loadExecutionLogs = async (executionSessionId) => {
  try {
    const response = await api.getExecutionLogs({ executionSessionId })
    executionLogs.value = response.data
  } catch (error) {
    console.error('加载执行日志失败:', error)
  }
}

const startPolling = (executionSessionId) => {
  if (pollingInterval) {
    clearInterval(pollingInterval)
  }
  
  pollingInterval = setInterval(async () => {
    try {
      // 更新执行状态
      const response = await api.getExecutionDetail({ executionSessionId })
      selectedExecution.value = response.data
      
      // 更新日志
      loadExecutionLogs(executionSessionId)
      
      // 如果执行完成，停止轮询
      if (response.data.status !== 'running') {
        clearInterval(pollingInterval)
        pollingInterval = null
        
        // 刷新列表
        loadExecutions()
      }
    } catch (error) {
      console.error('轮询执行状态失败:', error)
    }
  }, 3000)
}

const stopExecution = async () => {
  try {
    await api.stopExecution({ executionSessionId: selectedExecution.value.executionSessionId })
    message.success('执行已停止')
    
    if (pollingInterval) {
      clearInterval(pollingInterval)
      pollingInterval = null
    }
    
    loadExecutions()
  } catch (error) {
    message.error('停止执行失败')
  }
}

const generateReport = async () => {
  generatingReport.value = true
  try {
    await api.generateTestReport({
      executionSessionId: selectedExecution.value.executionSessionId,
      formats: ['html', 'json']
    })
    
    message.success('报告生成成功')
    
    // 重新加载执行详情
    viewExecutionDetail(selectedExecution.value)
  } catch (error) {
    message.error('生成报告失败')
  } finally {
    generatingReport.value = false
  }
}

const viewReports = (execution) => {
  viewExecutionDetail(execution)
  detailTab.value = 'reports'
}

const previewReport = async (report) => {
  try {
    const response = await api.getReportContent({ reportPath: report.path })
    previewReportContent.value = response.data.content
    previewReportType.value = report.format
    showReportModal.value = true
  } catch (error) {
    message.error('加载报告内容失败')
  }
}

const downloadReport = (report) => {
  const link = document.createElement('a')
  link.href = `/api/api-automation/download-report?path=${encodeURIComponent(report.path)}`
  link.download = report.name
  link.click()
}

const getProgressStatus = (status) => {
  const statusMap = {
    'running': 'active',
    'completed': 'success',
    'failed': 'error',
    'cancelled': 'warning'
  }
  return statusMap[status] || 'default'
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

onMounted(() => {
  loadExecutions()
  loadScriptOptions()
})

onUnmounted(() => {
  if (pollingInterval) {
    clearInterval(pollingInterval)
  }
})
</script>

<style scoped>
.test-execution {
  padding: 20px;
}

.report-preview {
  height: 70vh;
}
</style>
