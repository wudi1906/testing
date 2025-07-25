<template>
  <div class="test-management">
    <!-- 工具栏 -->
    <n-card class="mb-6">
      <div class="flex justify-between items-center">
        <div class="flex items-center space-x-4">
          <n-input
            v-model:value="searchKeyword"
            placeholder="搜索测试脚本..."
            clearable
            style="width: 300px"
            @keyup.enter="loadTestScripts"
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
            @update:value="loadTestScripts"
          />
          
          <n-select
            v-model:value="filterFramework"
            :options="frameworkOptions"
            placeholder="框架筛选"
            clearable
            style="width: 150px"
            @update:value="loadTestScripts"
          />
        </div>
        
        <n-space>
          <n-button type="primary" @click="showCreateModal = true">
            <template #icon>
              <n-icon><Icon icon="mdi:plus" /></n-icon>
            </template>
            新建测试
          </n-button>

          <n-button @click="batchExecute" :disabled="!selectedScripts.length">
            <template #icon>
              <n-icon><Icon icon="mdi:play" /></n-icon>
            </template>
            批量执行
          </n-button>

          <n-button @click="loadTestScripts">
            <template #icon>
              <n-icon><Icon icon="mdi:refresh" /></n-icon>
            </template>
            刷新
          </n-button>
        </n-space>
      </div>
    </n-card>

    <!-- 测试脚本列表 -->
    <n-card title="测试脚本列表">
      <n-data-table
        :columns="scriptColumns"
        :data="testScripts"
        :loading="loading"
        :pagination="pagination"
        :row-key="(row) => row.scriptId"
        @update:checked-row-keys="handleSelectionChange"
        @update:page="handlePageChange"
      />
    </n-card>

    <!-- 脚本详情/编辑模态框 -->
    <n-modal v-model:show="showScriptModal" preset="card" title="测试脚本详情" style="width: 90%">
      <div v-if="selectedScript">
        <n-tabs type="line" v-model:value="activeTab">
          <n-tab-pane name="info" tab="基本信息">
            <n-form
              ref="scriptFormRef"
              :model="scriptForm"
              label-placement="left"
              label-width="120px"
            >
              <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <n-form-item label="脚本名称" path="scriptName">
                    <n-input v-model:value="scriptForm.scriptName" />
                  </n-form-item>
                  
                  <n-form-item label="测试框架" path="framework">
                    <n-select v-model:value="scriptForm.framework" :options="frameworkOptions" />
                  </n-form-item>
                  
                  <n-form-item label="测试类型" path="testType">
                    <n-select v-model:value="scriptForm.testType" :options="testTypeOptions" />
                  </n-form-item>
                  
                  <n-form-item label="优先级" path="priority">
                    <n-select v-model:value="scriptForm.priority" :options="priorityOptions" />
                  </n-form-item>
                </div>
                
                <div>
                  <n-form-item label="关联接口" path="endpointPath">
                    <n-input v-model:value="scriptForm.endpointPath" readonly />
                  </n-form-item>
                  
                  <n-form-item label="HTTP方法" path="httpMethod">
                    <n-tag :type="getMethodType(scriptForm.httpMethod)">
                      {{ scriptForm.httpMethod }}
                    </n-tag>
                  </n-form-item>
                  
                  <n-form-item label="超时时间" path="timeout">
                    <n-input-number v-model:value="scriptForm.timeout" :min="1" :max="300" />
                    <span class="ml-2 text-gray-500">秒</span>
                  </n-form-item>
                  
                  <n-form-item label="重试次数" path="retryCount">
                    <n-input-number v-model:value="scriptForm.retryCount" :min="0" :max="5" />
                  </n-form-item>
                </div>
              </div>
              
              <n-form-item label="描述" path="description">
                <n-input
                  v-model:value="scriptForm.description"
                  type="textarea"
                  :rows="3"
                  placeholder="测试脚本描述..."
                />
              </n-form-item>
            </n-form>
          </n-tab-pane>
          
          <n-tab-pane name="code" tab="脚本代码">
            <div class="code-editor-container">
              <div class="flex justify-between items-center mb-4">
                <n-space>
                  <n-tag>{{ scriptForm.framework }}</n-tag>
                  <n-tag type="info">{{ scriptForm.language || 'Python' }}</n-tag>
                </n-space>
                <n-space>
                  <n-button size="small" @click="formatCode">
                    <template #icon>
                      <n-icon><Icon icon="mdi:code-braces" /></n-icon>
                    </template>
                    格式化
                  </n-button>
                  <n-button size="small" @click="validateCode">
                    <template #icon>
                      <n-icon><Icon icon="mdi:check-circle" /></n-icon>
                    </template>
                    验证语法
                  </n-button>
                </n-space>
              </div>
              
              <!-- 代码编辑器 -->
              <div class="code-editor">
                <n-input
                  v-model:value="scriptForm.scriptContent"
                  type="textarea"
                  :rows="20"
                  placeholder="测试脚本代码..."
                  style="font-family: 'Courier New', monospace"
                />
              </div>
            </div>
          </n-tab-pane>
          
          <n-tab-pane name="config" tab="执行配置">
            <n-form label-placement="left" label-width="120px">
              <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <n-form-item label="执行环境">
                    <n-select v-model:value="scriptForm.environment" :options="environmentOptions" />
                  </n-form-item>
                  
                  <n-form-item label="并行执行">
                    <n-switch v-model:value="scriptForm.parallelExecution" />
                  </n-form-item>
                  
                  <n-form-item label="数据驱动">
                    <n-switch v-model:value="scriptForm.dataDrivern" />
                  </n-form-item>
                </div>
                
                <div>
                  <n-form-item label="前置条件">
                    <n-select
                      v-model:value="scriptForm.prerequisites"
                      :options="prerequisiteOptions"
                      multiple
                      placeholder="选择前置测试脚本"
                    />
                  </n-form-item>
                  
                  <n-form-item label="测试数据">
                    <n-input
                      v-model:value="scriptForm.testDataPath"
                      placeholder="测试数据文件路径"
                    />
                  </n-form-item>
                </div>
              </div>
              
              <n-form-item label="环境变量">
                <n-dynamic-input
                  v-model:value="scriptForm.environmentVariables"
                  :on-create="() => ({ key: '', value: '' })"
                >
                  <template #default="{ value }">
                    <div class="flex space-x-2 w-full">
                      <n-input v-model:value="value.key" placeholder="变量名" style="flex: 1" />
                      <n-input v-model:value="value.value" placeholder="变量值" style="flex: 1" />
                    </div>
                  </template>
                </n-dynamic-input>
              </n-form-item>
            </n-form>
          </n-tab-pane>
          
          <n-tab-pane name="history" tab="执行历史">
            <n-data-table
              :columns="historyColumns"
              :data="executionHistory"
              :pagination="{ pageSize: 10 }"
              max-height="400"
            />
          </n-tab-pane>
        </n-tabs>
      </div>

      <template #footer>
        <div class="flex justify-between">
          <n-space>
            <n-button @click="executeScript" type="primary" :loading="executing">
              <template #icon>
                <n-icon><Icon icon="mdi:play" /></n-icon>
              </template>
              执行测试
            </n-button>
            <n-button @click="debugScript" :loading="debugging">
              <template #icon>
                <n-icon><Icon icon="mdi:bug" /></n-icon>
              </template>
              调试模式
            </n-button>
          </n-space>
          
          <n-space>
            <n-button @click="showScriptModal = false">取消</n-button>
            <n-button type="primary" @click="saveScript" :loading="saving">保存</n-button>
          </n-space>
        </div>
      </template>
    </n-modal>

    <!-- 新建测试模态框 -->
    <n-modal v-model:show="showCreateModal" preset="card" title="新建测试脚本" style="width: 600px">
      <n-form ref="createFormRef" :model="createForm" label-placement="left" label-width="120px">
        <n-form-item label="选择接口" path="endpointId" required>
          <n-select
            v-model:value="createForm.endpointId"
            :options="endpointOptions"
            placeholder="选择要测试的接口"
            filterable
            @update:value="handleEndpointSelect"
          />
        </n-form-item>
        
        <n-form-item label="脚本名称" path="scriptName" required>
          <n-input v-model:value="createForm.scriptName" placeholder="输入脚本名称" />
        </n-form-item>
        
        <n-form-item label="测试框架" path="framework" required>
          <n-select v-model:value="createForm.framework" :options="frameworkOptions" />
        </n-form-item>
        
        <n-form-item label="测试类型" path="testType" required>
          <n-select v-model:value="createForm.testType" :options="testTypeOptions" />
        </n-form-item>
        
        <n-form-item label="生成模板">
          <n-checkbox-group v-model:value="createForm.templateOptions">
            <n-space vertical>
              <n-checkbox value="basic_structure">基础结构</n-checkbox>
              <n-checkbox value="mock_data">模拟数据</n-checkbox>
              <n-checkbox value="assertions">智能断言</n-checkbox>
              <n-checkbox value="error_handling">错误处理</n-checkbox>
            </n-space>
          </n-checkbox-group>
        </n-form-item>
      </n-form>

      <template #footer>
        <div class="flex justify-end space-x-2">
          <n-button @click="showCreateModal = false">取消</n-button>
          <n-button type="primary" @click="createTestScript" :loading="creating">创建</n-button>
        </div>
      </template>
    </n-modal>

    <!-- 执行结果模态框 -->
    <n-modal v-model:show="showExecutionModal" preset="card" title="测试执行结果" style="width: 80%">
      <div v-if="executionResult">
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <n-statistic label="执行状态" :value="executionResult.status" />
          <n-statistic label="执行时间" :value="`${executionResult.duration}s`" />
          <n-statistic label="响应时间" :value="`${executionResult.responseTime}ms`" />
          <n-statistic label="断言结果" :value="`${executionResult.passedAssertions}/${executionResult.totalAssertions}`" />
        </div>

        <n-tabs type="line">
          <n-tab-pane name="result" tab="执行结果">
            <n-alert
              :type="executionResult.status === 'passed' ? 'success' : 'error'"
              :title="executionResult.status === 'passed' ? '测试通过' : '测试失败'"
              class="mb-4"
            >
              {{ executionResult.message }}
            </n-alert>
            
            <div v-if="executionResult.assertions">
              <h4 class="font-semibold mb-2">断言详情</h4>
              <n-list>
                <n-list-item v-for="assertion in executionResult.assertions" :key="assertion.id">
                  <div class="flex items-center justify-between w-full">
                    <span>{{ assertion.description }}</span>
                    <n-tag :type="assertion.passed ? 'success' : 'error'">
                      {{ assertion.passed ? '通过' : '失败' }}
                    </n-tag>
                  </div>
                </n-list-item>
              </n-list>
            </div>
          </n-tab-pane>
          
          <n-tab-pane name="request" tab="请求详情">
            <n-code :code="JSON.stringify(executionResult.request, null, 2)" language="json" />
          </n-tab-pane>
          
          <n-tab-pane name="response" tab="响应详情">
            <n-code :code="JSON.stringify(executionResult.response, null, 2)" language="json" />
          </n-tab-pane>
          
          <n-tab-pane name="logs" tab="执行日志">
            <div class="bg-black text-green-400 p-4 rounded font-mono text-sm h-64 overflow-y-auto">
              <div v-for="(log, index) in executionResult.logs" :key="index" class="mb-1">
                <span class="text-gray-500">[{{ formatTime(log.timestamp) }}]</span>
                <span>{{ log.message }}</span>
              </div>
            </div>
          </n-tab-pane>
        </n-tabs>
      </div>
    </n-modal>
  </div>
</template>

<script setup>
import { ref, onMounted, h } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, NTag, useMessage } from 'naive-ui'
import { Icon } from '@iconify/vue'
import api from '@/api'
import { formatTime } from '@/utils'

const router = useRouter()
const message = useMessage()

// 数据
const testScripts = ref([])
const loading = ref(false)
const selectedScripts = ref([])
const searchKeyword = ref('')
const filterStatus = ref('')
const filterFramework = ref('')

// 模态框状态
const showScriptModal = ref(false)
const showCreateModal = ref(false)
const showExecutionModal = ref(false)
const activeTab = ref('info')

// 表单数据
const selectedScript = ref(null)
const scriptForm = ref({})
const createForm = ref({
  endpointId: '',
  scriptName: '',
  framework: 'pytest',
  testType: 'functional',
  templateOptions: ['basic_structure']
})

// 执行状态
const executing = ref(false)
const debugging = ref(false)
const saving = ref(false)
const creating = ref(false)
const executionResult = ref(null)
const executionHistory = ref([])

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
  { label: '草稿', value: 'draft' },
  { label: '就绪', value: 'ready' },
  { label: '运行中', value: 'running' },
  { label: '已完成', value: 'completed' }
]

const frameworkOptions = [
  { label: 'pytest', value: 'pytest' },
  { label: 'unittest', value: 'unittest' },
  { label: 'requests', value: 'requests' }
]

const testTypeOptions = [
  { label: '功能测试', value: 'functional' },
  { label: '边界测试', value: 'boundary' },
  { label: '安全测试', value: 'security' },
  { label: '性能测试', value: 'performance' }
]

const priorityOptions = [
  { label: '高', value: 'high' },
  { label: '中', value: 'medium' },
  { label: '低', value: 'low' }
]

const environmentOptions = [
  { label: '测试环境', value: 'test' },
  { label: '预发布环境', value: 'staging' },
  { label: '生产环境', value: 'production' }
]

const endpointOptions = ref([])
const prerequisiteOptions = ref([])

// 表格列定义
const scriptColumns = [
  { type: 'selection' },
  { title: '脚本名称', key: 'scriptName', width: 200 },
  { title: '接口路径', key: 'endpointPath', width: 250 },
  { 
    title: '方法', 
    key: 'httpMethod', 
    width: 80,
    render: (row) => h(NTag, { type: getMethodType(row.httpMethod) }, { default: () => row.httpMethod })
  },
  { title: '框架', key: 'framework', width: 100 },
  { title: '类型', key: 'testType', width: 100 },
  { 
    title: '状态', 
    key: 'status', 
    width: 100,
    render: (row) => {
      const statusMap = {
        'draft': { type: 'default', text: '草稿' },
        'ready': { type: 'success', text: '就绪' },
        'running': { type: 'warning', text: '运行中' },
        'completed': { type: 'info', text: '已完成' }
      }
      const status = statusMap[row.status] || { type: 'default', text: '未知' }
      return h(NTag, { type: status.type }, { default: () => status.text })
    }
  },
  { title: '最后执行', key: 'lastExecutionTime', width: 150, render: (row) => formatTime(row.lastExecutionTime) },
  {
    title: '操作',
    key: 'actions',
    width: 200,
    render: (row) => [
      h(NButton, 
        { 
          size: 'small', 
          type: 'primary',
          onClick: () => editScript(row)
        }, 
        { default: () => '编辑' }
      ),
      h(NButton, 
        { 
          size: 'small', 
          type: 'info',
          style: 'margin-left: 8px',
          onClick: () => executeScript(row)
        }, 
        { default: () => '执行' }
      ),
      h(NButton, 
        { 
          size: 'small', 
          type: 'error',
          style: 'margin-left: 8px',
          onClick: () => deleteScript(row)
        }, 
        { default: () => '删除' }
      )
    ]
  }
]

const historyColumns = [
  { title: '执行时间', key: 'executionTime', width: 150, render: (row) => formatTime(row.executionTime) },
  { title: '状态', key: 'status', width: 100 },
  { title: '执行时长', key: 'duration', width: 100, render: (row) => `${row.duration}s` },
  { title: '环境', key: 'environment', width: 100 },
  { title: '结果', key: 'result', ellipsis: true }
]

// 方法
const loadTestScripts = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.value.page,
      pageSize: pagination.value.pageSize,
      keyword: searchKeyword.value,
      status: filterStatus.value,
      framework: filterFramework.value
    }
    
    const response = await api.getTestScripts(params)
    testScripts.value = response.data.items
    pagination.value.itemCount = response.data.total
  } catch (error) {
    message.error('加载测试脚本失败')
  } finally {
    loading.value = false
  }
}

const loadEndpoints = async () => {
  try {
    const response = await api.getApiEndpoints()
    endpointOptions.value = response.data.map(endpoint => ({
      label: `${endpoint.method} ${endpoint.path}`,
      value: endpoint.endpointId
    }))
  } catch (error) {
    message.error('加载接口列表失败')
  }
}

const handleSelectionChange = (keys) => {
  selectedScripts.value = keys
}

const handlePageChange = (page) => {
  pagination.value.page = page
  loadTestScripts()
}

const editScript = async (script) => {
  selectedScript.value = script
  scriptForm.value = { ...script }
  
  // 加载执行历史
  try {
    const response = await api.getScriptExecutionHistory({ scriptId: script.scriptId })
    executionHistory.value = response.data
  } catch (error) {
    console.error('加载执行历史失败:', error)
  }
  
  showScriptModal.value = true
}

const executeScript = async (script) => {
  if (!script) script = selectedScript.value
  
  executing.value = true
  try {
    const response = await api.executeTestScript({
      scriptId: script.scriptId,
      environment: script.environment || 'test'
    })
    
    executionResult.value = response.data
    showExecutionModal.value = true
    
    // 刷新脚本列表
    loadTestScripts()
  } catch (error) {
    message.error('执行测试失败')
  } finally {
    executing.value = false
  }
}

const debugScript = async () => {
  debugging.value = true
  try {
    const response = await api.debugTestScript({
      scriptId: selectedScript.value.scriptId,
      debugMode: true
    })
    
    executionResult.value = response.data
    showExecutionModal.value = true
  } catch (error) {
    message.error('调试测试失败')
  } finally {
    debugging.value = false
  }
}

const saveScript = async () => {
  saving.value = true
  try {
    await api.updateTestScript({
      scriptId: selectedScript.value.scriptId,
      ...scriptForm.value
    })
    
    message.success('保存成功')
    showScriptModal.value = false
    loadTestScripts()
  } catch (error) {
    message.error('保存失败')
  } finally {
    saving.value = false
  }
}

const createTestScript = async () => {
  creating.value = true
  try {
    await api.createTestScript(createForm.value)
    
    message.success('创建成功')
    showCreateModal.value = false
    createForm.value = {
      endpointId: '',
      scriptName: '',
      framework: 'pytest',
      testType: 'functional',
      templateOptions: ['basic_structure']
    }
    loadTestScripts()
  } catch (error) {
    message.error('创建失败')
  } finally {
    creating.value = false
  }
}

const deleteScript = (script) => {
  message.warning('删除功能开发中...')
}

const batchExecute = () => {
  message.info('批量执行功能开发中...')
}

const formatCode = () => {
  message.info('代码格式化功能开发中...')
}

const validateCode = () => {
  message.info('语法验证功能开发中...')
}

const handleEndpointSelect = (endpointId) => {
  // 根据选择的接口自动填充脚本名称
  const endpoint = endpointOptions.value.find(opt => opt.value === endpointId)
  if (endpoint) {
    createForm.value.scriptName = `test_${endpoint.label.replace(/[^a-zA-Z0-9]/g, '_').toLowerCase()}`
  }
}

const getMethodType = (method) => {
  const typeMap = {
    'GET': 'success',
    'POST': 'warning',
    'PUT': 'info',
    'DELETE': 'error',
    'PATCH': 'default'
  }
  return typeMap[method] || 'default'
}

onMounted(() => {
  loadTestScripts()
  loadEndpoints()
})
</script>

<style scoped>
.test-management {
  padding: 20px;
}

.code-editor-container {
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  padding: 16px;
}

.code-editor {
  font-family: 'Courier New', monospace;
}
</style>
