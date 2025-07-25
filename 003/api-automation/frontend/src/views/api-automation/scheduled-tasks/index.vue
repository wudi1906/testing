<template>
  <div class="scheduled-tasks">
    <!-- 工具栏 -->
    <n-card class="mb-6">
      <div class="flex justify-between items-center">
        <div class="flex items-center space-x-4">
          <n-input
            v-model:value="searchKeyword"
            placeholder="搜索定时任务..."
            clearable
            style="width: 300px"
            @keyup.enter="loadTasks"
          >
            <template #prefix>
              <n-icon><Icon icon="mdi:magnify" /></n-icon>
            </template>
          </n-input>
          
          <n-select
            v-model:value="filterStatus"
            :options="statusOptions"
            placeholder="状态筛选"
            clearable
            style="width: 150px"
            @update:value="loadTasks"
          />
        </div>
        
        <n-space>
          <n-button type="primary" @click="showCreateModal = true">
            <template #icon>
              <n-icon><Icon icon="mdi:plus" /></n-icon>
            </template>
            新建任务
          </n-button>
          
          <n-button @click="loadTasks">
            <template #icon>
              <n-icon><Icon icon="mdi:refresh" /></n-icon>
            </template>
            刷新
          </n-button>
        </n-space>
      </div>
    </n-card>

    <!-- 任务列表 -->
    <n-card title="定时任务列表">
      <n-data-table
        :columns="taskColumns"
        :data="tasks"
        :loading="loading"
        :pagination="pagination"
        @update:page="handlePageChange"
      />
    </n-card>

    <!-- 新建/编辑任务模态框 -->
    <n-modal v-model:show="showTaskModal" preset="card" :title="isEditing ? '编辑定时任务' : '新建定时任务'" style="width: 700px">
      <n-form ref="taskFormRef" :model="taskForm" label-placement="left" label-width="120px">
        <n-form-item label="任务名称" path="taskName" required>
          <n-input v-model:value="taskForm.taskName" placeholder="输入任务名称" />
        </n-form-item>
        
        <n-form-item label="选择脚本" path="scriptIds" required>
          <n-select
            v-model:value="taskForm.scriptIds"
            :options="scriptOptions"
            placeholder="选择要执行的测试脚本"
            multiple
            filterable
          />
        </n-form-item>
        
        <n-form-item label="执行环境" path="environment" required>
          <n-select v-model:value="taskForm.environment" :options="environmentOptions" />
        </n-form-item>
        
        <n-form-item label="调度类型" path="scheduleType" required>
          <n-radio-group v-model:value="taskForm.scheduleType">
            <n-space vertical>
              <n-radio value="cron">Cron表达式</n-radio>
              <n-radio value="interval">固定间隔</n-radio>
              <n-radio value="once">单次执行</n-radio>
            </n-space>
          </n-radio-group>
        </n-form-item>
        
        <!-- Cron表达式配置 -->
        <div v-if="taskForm.scheduleType === 'cron'">
          <n-form-item label="Cron表达式" path="cronExpression" required>
            <n-input v-model:value="taskForm.cronExpression" placeholder="0 0 2 * * ?" />
            <template #feedback>
              <div class="text-sm text-gray-500 mt-1">
                格式: 秒 分 时 日 月 周 年(可选)
                <n-button text type="primary" @click="showCronHelper = true">表达式助手</n-button>
              </div>
            </template>
          </n-form-item>
          
          <n-form-item label="下次执行时间">
            <n-input :value="nextExecutionTime" readonly />
          </n-form-item>
        </div>
        
        <!-- 固定间隔配置 -->
        <div v-if="taskForm.scheduleType === 'interval'">
          <n-form-item label="执行间隔" required>
            <div class="flex items-center space-x-2">
              <n-input-number v-model:value="taskForm.intervalValue" :min="1" style="width: 120px" />
              <n-select v-model:value="taskForm.intervalUnit" :options="intervalUnitOptions" style="width: 100px" />
            </div>
          </n-form-item>
          
          <n-form-item label="首次执行时间">
            <n-date-picker
              v-model:value="taskForm.firstExecutionTime"
              type="datetime"
              placeholder="选择首次执行时间"
            />
          </n-form-item>
        </div>
        
        <!-- 单次执行配置 -->
        <div v-if="taskForm.scheduleType === 'once'">
          <n-form-item label="执行时间" path="executionTime" required>
            <n-date-picker
              v-model:value="taskForm.executionTime"
              type="datetime"
              placeholder="选择执行时间"
            />
          </n-form-item>
        </div>
        
        <n-form-item label="并行执行">
          <n-switch v-model:value="taskForm.parallelExecution" />
        </n-form-item>
        
        <n-form-item v-if="taskForm.parallelExecution" label="最大并发数">
          <n-input-number v-model:value="taskForm.maxWorkers" :min="1" :max="10" />
        </n-form-item>
        
        <n-form-item label="超时时间">
          <n-input-number v-model:value="taskForm.timeout" :min="60" :max="3600" />
          <span class="ml-2 text-gray-500">秒</span>
        </n-form-item>
        
        <n-form-item label="失败重试">
          <n-switch v-model:value="taskForm.retryOnFailure" />
        </n-form-item>
        
        <n-form-item v-if="taskForm.retryOnFailure" label="重试次数">
          <n-input-number v-model:value="taskForm.maxRetries" :min="1" :max="5" />
        </n-form-item>
        
        <n-form-item label="通知设置">
          <n-checkbox-group v-model:value="taskForm.notifications">
            <n-space vertical>
              <n-checkbox value="on_success">执行成功时通知</n-checkbox>
              <n-checkbox value="on_failure">执行失败时通知</n-checkbox>
              <n-checkbox value="on_timeout">执行超时时通知</n-checkbox>
            </n-space>
          </n-checkbox-group>
        </n-form-item>
        
        <n-form-item label="任务描述">
          <n-input
            v-model:value="taskForm.description"
            type="textarea"
            :rows="3"
            placeholder="描述任务的目的和注意事项..."
          />
        </n-form-item>
      </n-form>

      <template #footer>
        <div class="flex justify-end space-x-2">
          <n-button @click="showTaskModal = false">取消</n-button>
          <n-button type="primary" @click="saveTask" :loading="saving">
            {{ isEditing ? '更新' : '创建' }}
          </n-button>
        </div>
      </template>
    </n-modal>

    <!-- Cron表达式助手 -->
    <n-modal v-model:show="showCronHelper" preset="card" title="Cron表达式助手" style="width: 600px">
      <div class="cron-helper">
        <n-tabs type="line">
          <n-tab-pane name="common" tab="常用表达式">
            <n-list>
              <n-list-item v-for="cron in commonCronExpressions" :key="cron.expression">
                <div class="flex items-center justify-between w-full">
                  <div>
                    <div class="font-medium">{{ cron.description }}</div>
                    <div class="text-sm text-gray-500">{{ cron.expression }}</div>
                  </div>
                  <n-button size="small" @click="selectCronExpression(cron.expression)">
                    选择
                  </n-button>
                </div>
              </n-list-item>
            </n-list>
          </n-tab-pane>
          
          <n-tab-pane name="builder" tab="表达式构建器">
            <div class="grid grid-cols-2 gap-4">
              <n-form-item label="秒">
                <n-select v-model:value="cronBuilder.second" :options="secondOptions" />
              </n-form-item>
              <n-form-item label="分">
                <n-select v-model:value="cronBuilder.minute" :options="minuteOptions" />
              </n-form-item>
              <n-form-item label="时">
                <n-select v-model:value="cronBuilder.hour" :options="hourOptions" />
              </n-form-item>
              <n-form-item label="日">
                <n-select v-model:value="cronBuilder.day" :options="dayOptions" />
              </n-form-item>
              <n-form-item label="月">
                <n-select v-model:value="cronBuilder.month" :options="monthOptions" />
              </n-form-item>
              <n-form-item label="周">
                <n-select v-model:value="cronBuilder.week" :options="weekOptions" />
              </n-form-item>
            </div>
            
            <div class="mt-4">
              <n-form-item label="生成的表达式">
                <n-input :value="builtCronExpression" readonly />
              </n-form-item>
              <n-button type="primary" @click="selectCronExpression(builtCronExpression)">
                使用此表达式
              </n-button>
            </div>
          </n-tab-pane>
        </n-tabs>
      </div>
    </n-modal>

    <!-- 执行历史模态框 -->
    <n-modal v-model:show="showHistoryModal" preset="card" title="执行历史" style="width: 80%">
      <div v-if="selectedTask">
        <div class="mb-4">
          <h4 class="font-semibold">{{ selectedTask.taskName }}</h4>
          <p class="text-gray-500">{{ selectedTask.description }}</p>
        </div>
        
        <n-data-table
          :columns="historyColumns"
          :data="executionHistory"
          :pagination="{ pageSize: 20 }"
          max-height="500"
        />
      </div>
    </n-modal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, h } from 'vue'
import { Icon } from '@iconify/vue'
import { NButton, NTag, useMessage } from 'naive-ui'
import api from '@/api'
import { formatTime } from '@/utils'

const message = useMessage()

// 数据
const tasks = ref([])
const loading = ref(false)
const selectedTask = ref(null)
const executionHistory = ref([])
const searchKeyword = ref('')
const filterStatus = ref('')

// 模态框状态
const showTaskModal = ref(false)
const showCreateModal = ref(false)
const showCronHelper = ref(false)
const showHistoryModal = ref(false)
const isEditing = ref(false)

// 表单数据
const taskForm = ref({
  taskName: '',
  scriptIds: [],
  environment: 'test',
  scheduleType: 'cron',
  cronExpression: '0 0 2 * * ?',
  intervalValue: 1,
  intervalUnit: 'hours',
  firstExecutionTime: null,
  executionTime: null,
  parallelExecution: false,
  maxWorkers: 3,
  timeout: 300,
  retryOnFailure: false,
  maxRetries: 3,
  notifications: [],
  description: ''
})

// Cron构建器
const cronBuilder = ref({
  second: '0',
  minute: '0',
  hour: '2',
  day: '*',
  month: '*',
  week: '?'
})

// 状态
const saving = ref(false)

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
  { label: '启用', value: 'enabled' },
  { label: '禁用', value: 'disabled' },
  { label: '已完成', value: 'completed' }
]

const environmentOptions = [
  { label: '测试环境', value: 'test' },
  { label: '预发布环境', value: 'staging' },
  { label: '生产环境', value: 'production' }
]

const intervalUnitOptions = [
  { label: '分钟', value: 'minutes' },
  { label: '小时', value: 'hours' },
  { label: '天', value: 'days' },
  { label: '周', value: 'weeks' }
]

const scriptOptions = ref([])

// Cron选项
const secondOptions = [
  { label: '每秒', value: '*' },
  { label: '0秒', value: '0' },
  { label: '30秒', value: '30' }
]

const minuteOptions = [
  { label: '每分钟', value: '*' },
  { label: '0分', value: '0' },
  { label: '15分', value: '15' },
  { label: '30分', value: '30' },
  { label: '45分', value: '45' }
]

const hourOptions = [
  { label: '每小时', value: '*' },
  ...Array.from({ length: 24 }, (_, i) => ({ label: `${i}时`, value: i.toString() }))
]

const dayOptions = [
  { label: '每天', value: '*' },
  ...Array.from({ length: 31 }, (_, i) => ({ label: `${i + 1}日`, value: (i + 1).toString() }))
]

const monthOptions = [
  { label: '每月', value: '*' },
  ...Array.from({ length: 12 }, (_, i) => ({ label: `${i + 1}月`, value: (i + 1).toString() }))
]

const weekOptions = [
  { label: '不指定', value: '?' },
  { label: '周日', value: '1' },
  { label: '周一', value: '2' },
  { label: '周二', value: '3' },
  { label: '周三', value: '4' },
  { label: '周四', value: '5' },
  { label: '周五', value: '6' },
  { label: '周六', value: '7' }
]

// 常用Cron表达式
const commonCronExpressions = [
  { description: '每天凌晨2点执行', expression: '0 0 2 * * ?' },
  { description: '每小时执行一次', expression: '0 0 * * * ?' },
  { description: '每30分钟执行一次', expression: '0 */30 * * * ?' },
  { description: '每周一凌晨2点执行', expression: '0 0 2 ? * MON' },
  { description: '每月1号凌晨2点执行', expression: '0 0 2 1 * ?' },
  { description: '工作日上午9点执行', expression: '0 0 9 ? * MON-FRI' }
]

// 计算属性
const builtCronExpression = computed(() => {
  const { second, minute, hour, day, month, week } = cronBuilder.value
  return `${second} ${minute} ${hour} ${day} ${month} ${week}`
})

const nextExecutionTime = computed(() => {
  // 这里应该调用后端API计算下次执行时间
  return '2024-01-22 02:00:00'
})

// 表格列定义
const taskColumns = [
  { title: '任务名称', key: 'taskName', width: 200 },
  { title: '调度类型', key: 'scheduleType', width: 100 },
  { title: '调度表达式', key: 'scheduleExpression', width: 150 },
  { title: '环境', key: 'environment', width: 100 },
  { 
    title: '状态', 
    key: 'status', 
    width: 100,
    render: (row) => {
      const statusMap = {
        'enabled': { type: 'success', text: '启用' },
        'disabled': { type: 'default', text: '禁用' },
        'completed': { type: 'info', text: '已完成' }
      }
      const status = statusMap[row.status] || { type: 'default', text: '未知' }
      return h(NTag, { type: status.type }, { default: () => status.text })
    }
  },
  { title: '下次执行', key: 'nextExecutionTime', width: 150, render: (row) => formatTime(row.nextExecutionTime) },
  { title: '最后执行', key: 'lastExecutionTime', width: 150, render: (row) => formatTime(row.lastExecutionTime) },
  { title: '创建时间', key: 'createdAt', width: 150, render: (row) => formatTime(row.createdAt) },
  {
    title: '操作',
    key: 'actions',
    width: 250,
    render: (row) => [
      h(NButton, 
        { 
          size: 'small', 
          type: 'primary',
          onClick: () => editTask(row)
        }, 
        { default: () => '编辑' }
      ),
      h(NButton, 
        { 
          size: 'small', 
          type: row.status === 'enabled' ? 'warning' : 'success',
          style: 'margin-left: 8px',
          onClick: () => toggleTaskStatus(row)
        }, 
        { default: () => row.status === 'enabled' ? '禁用' : '启用' }
      ),
      h(NButton, 
        { 
          size: 'small', 
          type: 'info',
          style: 'margin-left: 8px',
          onClick: () => viewHistory(row)
        }, 
        { default: () => '历史' }
      ),
      h(NButton, 
        { 
          size: 'small', 
          type: 'error',
          style: 'margin-left: 8px',
          onClick: () => deleteTask(row)
        }, 
        { default: () => '删除' }
      )
    ]
  }
]

const historyColumns = [
  { title: '执行时间', key: 'executionTime', width: 150, render: (row) => formatTime(row.executionTime) },
  { 
    title: '状态', 
    key: 'status', 
    width: 100,
    render: (row) => {
      const statusMap = {
        'success': { type: 'success', text: '成功' },
        'failed': { type: 'error', text: '失败' },
        'timeout': { type: 'warning', text: '超时' }
      }
      const status = statusMap[row.status] || { type: 'default', text: '未知' }
      return h(NTag, { type: status.type }, { default: () => status.text })
    }
  },
  { title: '执行时长', key: 'duration', width: 100, render: (row) => `${row.duration}s` },
  { title: '测试数', key: 'totalTests', width: 80 },
  { title: '通过', key: 'passedTests', width: 80 },
  { title: '失败', key: 'failedTests', width: 80 },
  { title: '成功率', key: 'successRate', width: 100, render: (row) => `${row.successRate}%` },
  { title: '错误信息', key: 'errorMessage', ellipsis: true }
]

// 方法
const loadTasks = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.value.page,
      pageSize: pagination.value.pageSize,
      keyword: searchKeyword.value,
      status: filterStatus.value
    }
    
    const response = await api.getScheduledTasks(params)
    tasks.value = response.data.items
    pagination.value.itemCount = response.data.total
  } catch (error) {
    message.error('加载定时任务失败')
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
  loadTasks()
}

const editTask = (task) => {
  selectedTask.value = task
  taskForm.value = { ...task }
  isEditing.value = true
  showTaskModal.value = true
}

const saveTask = async () => {
  saving.value = true
  try {
    if (isEditing.value) {
      await api.updateScheduledTask({
        taskId: selectedTask.value.taskId,
        ...taskForm.value
      })
      message.success('任务更新成功')
    } else {
      await api.createScheduledTask(taskForm.value)
      message.success('任务创建成功')
    }
    
    showTaskModal.value = false
    resetForm()
    loadTasks()
  } catch (error) {
    message.error(isEditing.value ? '更新任务失败' : '创建任务失败')
  } finally {
    saving.value = false
  }
}

const toggleTaskStatus = async (task) => {
  try {
    const newStatus = task.status === 'enabled' ? 'disabled' : 'enabled'
    await api.updateTaskStatus({
      taskId: task.taskId,
      status: newStatus
    })
    
    message.success(`任务已${newStatus === 'enabled' ? '启用' : '禁用'}`)
    loadTasks()
  } catch (error) {
    message.error('更新任务状态失败')
  }
}

const deleteTask = async (task) => {
  try {
    await api.deleteScheduledTask({ taskId: task.taskId })
    message.success('任务删除成功')
    loadTasks()
  } catch (error) {
    message.error('删除任务失败')
  }
}

const viewHistory = async (task) => {
  selectedTask.value = task
  
  try {
    const response = await api.getTaskExecutionHistory({ taskId: task.taskId })
    executionHistory.value = response.data
    showHistoryModal.value = true
  } catch (error) {
    message.error('加载执行历史失败')
  }
}

const selectCronExpression = (expression) => {
  taskForm.value.cronExpression = expression
  showCronHelper.value = false
}

const resetForm = () => {
  taskForm.value = {
    taskName: '',
    scriptIds: [],
    environment: 'test',
    scheduleType: 'cron',
    cronExpression: '0 0 2 * * ?',
    intervalValue: 1,
    intervalUnit: 'hours',
    firstExecutionTime: null,
    executionTime: null,
    parallelExecution: false,
    maxWorkers: 3,
    timeout: 300,
    retryOnFailure: false,
    maxRetries: 3,
    notifications: [],
    description: ''
  }
  isEditing.value = false
  selectedTask.value = null
}

// 监听新建模态框
const handleCreateModal = (show) => {
  if (show) {
    resetForm()
    showTaskModal.value = true
  }
  showCreateModal.value = false
}

// 监听新建按钮
const handleCreateClick = () => {
  showCreateModal.value = true
  handleCreateModal(true)
}

onMounted(() => {
  loadTasks()
  loadScriptOptions()
})
</script>

<style scoped>
.scheduled-tasks {
  padding: 20px;
}

.cron-helper {
  max-height: 500px;
  overflow-y: auto;
}
</style>
