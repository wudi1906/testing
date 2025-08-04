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
        :row-key="(row) => row.script_id"
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
                  <n-tag type="success" size="small">Monaco Editor</n-tag>
                </n-space>
                <n-space>
                  <n-button size="small" @click="insertTemplate">
                    <template #icon>
                      <n-icon><Icon icon="mdi:file-code" /></n-icon>
                    </template>
                    插入模板
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
              <component
                :is="codeEditorComponent"
                v-model="scriptForm.scriptContent"
                :language="getEditorLanguage()"
                :height="500"
                theme="vs-dark"
                :show-header="true"
                :placeholder="getEditorPlaceholder()"
                @change="onCodeChange"
                @focus="onCodeFocus"
                @blur="onCodeBlur"
              />
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
import { ref, onMounted, h, shallowRef } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, NTag, useMessage } from 'naive-ui'
import { Icon } from '@iconify/vue'
import api from '@/api'
import { formatTime } from '@/utils'
import SimpleCodeEditor from '@/components/SimpleCodeEditor.vue'

// 动态导入Monaco Editor，如果失败则使用SimpleCodeEditor
const codeEditorComponent = shallowRef(SimpleCodeEditor)

// 异步加载Monaco Editor
const loadMonacoEditor = async () => {
  try {
    const MonacoEditor = await import('@/components/MonacoEditor.vue')
    codeEditorComponent.value = MonacoEditor.default
    console.log('✅ Monaco Editor 加载成功')
  } catch (error) {
    console.warn('⚠️ Monaco Editor 加载失败，使用简化编辑器:', error.message)
    codeEditorComponent.value = SimpleCodeEditor
  }
}

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
  { title: '脚本名称', key: 'name', width: 200, ellipsis: true },
  {
    title: '接口信息',
    key: 'interface_info',
    width: 300,
    render: (row) => {
      if (row.interface_info) {
        return h('div', [
          h('div', { style: 'font-weight: bold; margin-bottom: 4px;' }, row.interface_info.name || '未知接口'),
          h('div', { style: 'font-size: 12px; color: #666;' }, [
            h(NTag, {
              type: getMethodType(row.interface_info.method),
              size: 'small',
              style: 'margin-right: 8px;'
            }, { default: () => row.interface_info.method }),
            row.interface_info.path
          ])
        ])
      }
      return h('span', { style: 'color: #999;' }, '无关联接口')
    }
  },
  { title: '框架', key: 'framework', width: 100 },
  {
    title: '状态',
    key: 'status',
    width: 100,
    render: (row) => {
      const statusMap = {
        'ACTIVE': { type: 'success', text: '活跃' },
        'INACTIVE': { type: 'default', text: '非活跃' },
        'DRAFT': { type: 'warning', text: '草稿' },
        'ARCHIVED': { type: 'info', text: '已归档' }
      }
      const status = statusMap[row.status] || { type: 'default', text: row.status || '未知' }
      return h(NTag, { type: status.type }, { default: () => status.text })
    }
  },
  {
    title: '质量评分',
    key: 'code_quality_score',
    width: 100,
    render: (row) => {
      const score = row.code_quality_score || 'N/A'
      const color = score === 'A' ? 'success' : score === 'B' ? 'warning' : 'default'
      return h(NTag, { type: color, size: 'small' }, { default: () => score })
    }
  },
  {
    title: '最后执行',
    key: 'last_execution_time',
    width: 150,
    render: (row) => formatTime(row.last_execution_time)
  },
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
      page_size: pagination.value.pageSize,
      search: searchKeyword.value,
      status: filterStatus.value,
      framework: filterFramework.value,
      include_inactive: false
    }

    console.log('加载脚本参数:', params)
    const response = await api.getAllScripts(params)
    console.log('脚本响应:', response)
    console.log('响应类型:', typeof response)
    console.log('响应结构:', Object.keys(response || {}))

    // 检查响应数据结构
    if (response && response.data && response.data.scripts) {
      console.log('✅ 检测到正确的数据结构')
      // 转换数据格式，确保字段名匹配
      const scripts = response.data.scripts || []
      testScripts.value = scripts.map(script => ({
        ...script,
        scriptId: script.script_id, // 添加前端期望的字段名
        scriptName: script.name,    // 添加脚本名称的别名
      }))
      pagination.value.itemCount = response.data.total || 0

      console.log(`✅ 成功加载 ${testScripts.value.length} 个脚本`)
      console.log('转换后的脚本数据:', testScripts.value)

      if (testScripts.value.length === 0) {
        message.info('暂无测试脚本数据')
      } else {
        message.success(`成功加载 ${testScripts.value.length} 个脚本`)
      }
    } else {
      console.error('❌ 脚本响应格式错误:', response)
      console.error('期望的结构: response.data.scripts')
      console.error('实际结构:', response)
      testScripts.value = []
      pagination.value.itemCount = 0
      message.warning('获取脚本列表失败，数据格式不正确')
    }
  } catch (error) {
    console.error('❌ 加载测试脚本失败:', error)
    console.error('错误详情:', error)

    // 检查错误中是否包含数据
    if (error && error.error && error.error.data && error.error.data.scripts) {
      console.log('🔄 从错误对象中提取数据')
      const scripts = error.error.data.scripts || []
      testScripts.value = scripts.map(script => ({
        ...script,
        scriptId: script.script_id,
        scriptName: script.name,
      }))
      pagination.value.itemCount = error.error.data.total || 0
      message.success(`从错误中恢复，成功加载 ${testScripts.value.length} 个脚本`)
    } else {
      message.error('加载测试脚本失败: ' + (error.message || '未知错误'))
      testScripts.value = []
      pagination.value.itemCount = 0
    }
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
  console.log('编辑脚本参数:', script)
  console.log('参数类型:', typeof script)

  // 安全地处理script对象
  if (!script || typeof script !== 'object') {
    console.error('无效的脚本对象:', script)
    message.error('无效的脚本数据')
    return
  }

  selectedScript.value = script

  // 安全地复制脚本数据，避免"target must be an object"错误
  try {
    scriptForm.value = {
      scriptId: script.script_id || script.scriptId || '',
      scriptName: script.name || script.scriptName || '',
      description: script.description || '',
      framework: script.framework || 'pytest',
      language: script.language || 'python',
      testType: script.test_type || 'functional',
      priority: script.priority || 'medium',
      endpointPath: script.interface_info?.path || '',
      httpMethod: script.interface_info?.method || '',
      timeout: script.timeout || 30,
      retryCount: script.retry_count || 0,
      environment: script.environment || 'test',
      parallelExecution: script.parallel_execution || false,
      dataDrivern: script.data_driven || false,
      prerequisites: script.prerequisites || [],
      scriptContent: script.content || ''
    }
  } catch (error) {
    console.error('复制脚本数据失败:', error)
    message.error('处理脚本数据失败')
    return
  }

  // 获取脚本详细信息（包含脚本内容）
  try {
    const scriptId = script.script_id || script.scriptId
    console.log('获取脚本详情:', scriptId)

    const detailResponse = await api.getScriptDetail(scriptId)
    console.log('脚本详情响应:', detailResponse)

    if (detailResponse && detailResponse.data) {
      // 安全地更新脚本表单数据
      scriptForm.value = {
        ...scriptForm.value,
        scriptContent: detailResponse.data.content || '',
        scriptId: detailResponse.data.script_id || scriptForm.value.scriptId,
        scriptName: detailResponse.data.name || scriptForm.value.scriptName,
        description: detailResponse.data.description || scriptForm.value.description,
        framework: detailResponse.data.framework || scriptForm.value.framework,
        language: detailResponse.data.language || scriptForm.value.language
      }
      console.log('脚本内容长度:', detailResponse.data.content?.length || 0)
    }
  } catch (error) {
    console.error('获取脚本详情失败:', error)
    message.error('获取脚本详情失败: ' + (error.message || '未知错误'))
  }

  // 加载执行历史
  try {
    const scriptId = script.script_id || script.scriptId
    const response = await api.getScriptExecutionHistory(scriptId)
    executionHistory.value = response.data || []
  } catch (error) {
    console.error('加载执行历史失败:', error)
    executionHistory.value = []
  }

  showScriptModal.value = true
}

const executeScript = async (script) => {
  if (!script) script = selectedScript.value

  executing.value = true
  try {
    const scriptId = script.script_id || script.scriptId

    // 启动脚本执行
    const response = await api.executeSingleScript(scriptId, {
      execution_config: {
        framework: script.framework || 'pytest',
        verbose: true
      },
      environment: script.environment || 'test',
      timeout: 300
    })

    if (response.success) {
      const executionId = response.data.execution_id
      message.success('脚本执行已启动，正在等待结果...')

      // 开始轮询执行结果
      await pollExecutionResult(scriptId, executionId)
    } else {
      message.error('启动脚本执行失败')
    }

  } catch (error) {
    console.error('执行脚本失败:', error)
    message.error('执行测试失败: ' + (error.message || '未知错误'))
  } finally {
    executing.value = false
  }
}

const pollExecutionResult = async (scriptId, executionId, maxAttempts = 30) => {
  let attempts = 0

  const checkResult = async () => {
    try {
      attempts++
      const response = await api.getScriptExecutionResult(scriptId, executionId)

      if (response.success && response.data) {
        const result = response.data

        if (result.status === 'RUNNING') {
          // 继续轮询
          if (attempts < maxAttempts) {
            setTimeout(checkResult, 2000) // 2秒后再次检查
            return
          } else {
            message.warning('执行超时，请稍后查看结果')
            return
          }
        } else {
          // 执行完成，显示结果
          executionResult.value = {
            execution_id: executionId,
            script_id: scriptId,
            status: result.status === 'success' ? 'passed' : 'failed',
            message: result.status === 'success' ? '测试执行成功' : '测试执行失败',
            duration: result.total_duration || 0,
            responseTime: 0,
            passedAssertions: result.summary?.passed_tests || 0,
            totalAssertions: result.summary?.total_tests || 0,
            assertions: result.script_results?.map(sr => ({
              id: sr.script_id,
              description: sr.script_name,
              passed: sr.status === 'PASSED'
            })) || [],
            request: {},
            response: {},
            logs: result.script_results?.map(sr => ({
              timestamp: new Date().toISOString(),
              message: `${sr.script_name}: ${sr.status}`
            })) || []
          }

          showExecutionModal.value = true

          if (result.status === 'success') {
            message.success('脚本执行完成')
          } else {
            message.error('脚本执行失败')
          }

          // 刷新脚本列表
          loadTestScripts()
        }
      }
    } catch (error) {
      console.error('获取执行结果失败:', error)
      if (attempts < maxAttempts) {
        setTimeout(checkResult, 2000)
      } else {
        message.error('获取执行结果失败')
      }
    }
  }

  // 开始检查
  checkResult()
}

const debugScript = async () => {
  debugging.value = true
  try {
    const scriptId = selectedScript.value.script_id || selectedScript.value.scriptId
    const response = await api.executeSingleScript(scriptId, {
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
    const scriptId = selectedScript.value.script_id || selectedScript.value.scriptId
    await api.updateScriptStatus(scriptId, {
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
    // 暂时禁用创建功能，提示用户使用脚本生成功能
    message.warning('请使用接口管理页面的"生成脚本"功能来创建测试脚本')
    showCreateModal.value = false

    // 重置表单
    createForm.value = {
      endpointId: '',
      scriptName: '',
      framework: 'pytest',
      testType: 'functional',
      templateOptions: ['basic_structure']
    }
  } catch (error) {
    message.error('操作失败')
  } finally {
    creating.value = false
  }
}

const deleteScript = async (script) => {
  try {
    const scriptId = script.script_id || script.scriptId
    await api.deleteScript(scriptId)
    message.success('删除成功')
    await loadTestScripts() // 重新加载列表
  } catch (error) {
    console.error('删除脚本失败:', error)
    message.error('删除脚本失败: ' + (error.message || '未知错误'))
  }
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

// Monaco Editor 相关方法
const getEditorLanguage = () => {
  const framework = scriptForm.value.framework || 'pytest'
  const language = scriptForm.value.language || 'python'

  // 根据框架和语言返回Monaco Editor支持的语言
  if (language.toLowerCase() === 'python' || framework.includes('pytest') || framework.includes('unittest')) {
    return 'python'
  } else if (language.toLowerCase() === 'javascript' || framework.includes('jest') || framework.includes('mocha')) {
    return 'javascript'
  } else if (language.toLowerCase() === 'java' || framework.includes('junit')) {
    return 'java'
  }

  return 'python' // 默认返回Python
}

const getEditorPlaceholder = () => {
  const framework = scriptForm.value.framework || 'pytest'
  const interfacePath = scriptForm.value.endpointPath || '/api/test'
  const method = (scriptForm.value.httpMethod || 'GET').toLowerCase()

  if (framework === 'pytest') {
    return `# Python + Pytest 测试脚本
import pytest
import requests

def test_${scriptForm.value.scriptName || 'api_endpoint'}():
    """测试 ${interfacePath} 接口"""
    url = "http://localhost:8000${interfacePath}"
    response = requests.${method}(url)
    assert response.status_code == 200`
  } else if (framework === 'unittest') {
    return `# Python + Unittest 测试脚本
import unittest
import requests

class TestAPI(unittest.TestCase):
    def test_${scriptForm.value.scriptName || 'api_endpoint'}(self):
        """测试 ${interfacePath} 接口"""
        url = "http://localhost:8000${interfacePath}"
        response = requests.${method}(url)
        self.assertEqual(response.status_code, 200)`
  }

  return '# 请输入测试脚本代码...'
}

const onCodeChange = (value) => {
  console.log('代码内容变化:', value.length, '字符')
}

const onCodeFocus = () => {
  console.log('代码编辑器获得焦点')
}

const onCodeBlur = () => {
  console.log('代码编辑器失去焦点')
}

const insertTemplate = () => {
  const framework = scriptForm.value.framework || 'pytest'
  let template = ''

  if (framework === 'pytest') {
    template = `import pytest
import requests
from typing import Dict, Any


class TestAPI:
    """API测试类"""

    def setup_method(self):
        """测试前置设置"""
        self.base_url = "http://localhost:8000"
        self.headers = {"Content-Type": "application/json"}

    def test_${scriptForm.value.scriptName || 'api_endpoint'}(self):
        """测试API端点"""
        # 准备测试数据
        url = f"{self.base_url}${scriptForm.value.endpointPath || '/api/test'}"
        data = {
            # 添加测试数据
        }

        # 发送请求
        response = requests.${(scriptForm.value.httpMethod || 'GET').toLowerCase()}(
            url,
            headers=self.headers,
            json=data if '${scriptForm.value.httpMethod || 'GET'}' != 'GET' else None
        )

        # 验证响应
        assert response.status_code == 200
        assert response.json() is not None

        # 添加更多断言
        result = response.json()
        # assert result["success"] is True
        # assert "data" in result

    def teardown_method(self):
        """测试后清理"""
        pass`
  } else if (framework === 'unittest') {
    template = `import unittest
import requests
from typing import Dict, Any


class Test${scriptForm.value.scriptName || 'API'}(unittest.TestCase):
    """API测试类"""

    def setUp(self):
        """测试前置设置"""
        self.base_url = "http://localhost:8000"
        self.headers = {"Content-Type": "application/json"}

    def test_${scriptForm.value.scriptName || 'api_endpoint'}(self):
        """测试API端点"""
        # 准备测试数据
        url = f"{self.base_url}${scriptForm.value.endpointPath || '/api/test'}"
        data = {
            # 添加测试数据
        }

        # 发送请求
        response = requests.${(scriptForm.value.httpMethod || 'GET').toLowerCase()}(
            url,
            headers=self.headers,
            json=data if '${scriptForm.value.httpMethod || 'GET'}' != 'GET' else None
        )

        # 验证响应
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.json())

        # 添加更多断言
        result = response.json()
        # self.assertTrue(result["success"])
        # self.assertIn("data", result)

    def tearDown(self):
        """测试后清理"""
        pass


if __name__ == '__main__':
    unittest.main()`
  }

  if (template) {
    scriptForm.value.scriptContent = template
    message.success('模板插入成功')
  } else {
    message.warning('暂不支持该框架的模板')
  }
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

onMounted(async () => {
  // 异步加载Monaco Editor
  await loadMonacoEditor()

  // 加载页面数据
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
