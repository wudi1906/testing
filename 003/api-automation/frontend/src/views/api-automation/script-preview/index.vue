<template>
  <div class="script-preview">
    <!-- 生成结果概览 -->
    <n-card title="生成结果概览" class="mb-6">
      <div v-if="generationResult">
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
          <n-statistic label="测试文件" :value="generationResult.totalTestFiles" />
          <n-statistic label="测试用例" :value="generationResult.totalTestCases" />
          <n-statistic label="断言数量" :value="generationResult.totalAssertions" />
          <n-statistic label="覆盖率评分" :value="`${generationResult.coverageScore}%`" />
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <n-statistic label="完整性评分" :value="`${generationResult.completenessScore}%`" />
          <n-statistic label="代码质量" :value="generationResult.codeQualityScore" />
          <n-statistic label="生成时间" :value="`${generationResult.processingTime}s`" />
        </div>
      </div>
    </n-card>

    <!-- 脚本文件列表 -->
    <n-card title="生成的测试脚本">
      <template #header-extra>
        <n-space>
          <n-button type="primary" @click="downloadAll">
            <template #icon>
              <n-icon><Icon icon="mdi:download" /></n-icon>
            </template>
            下载全部
          </n-button>
          <n-button @click="executeAll" :loading="executing">
            <template #icon>
              <n-icon><Icon icon="mdi:play" /></n-icon>
            </template>
            执行全部
          </n-button>
        </n-space>
      </template>

      <div v-if="scriptFiles.length">
        <n-list>
          <n-list-item v-for="file in scriptFiles" :key="file.fileName">
            <div class="w-full">
              <div class="flex items-center justify-between mb-2">
                <div class="flex items-center space-x-3">
                  <n-icon size="20" color="#4f46e5">
                    <Icon icon="mdi:file-code" />
                  </n-icon>
                  <div>
                    <div class="font-medium">{{ file.fileName }}</div>
                    <div class="text-sm text-gray-500">
                      {{ file.testCaseCount }} 个测试用例 • {{ file.framework }} • {{ formatFileSize(file.size) }}
                    </div>
                  </div>
                </div>
                
                <n-space>
                  <n-button size="small" @click="previewFile(file)">预览</n-button>
                  <n-button size="small" @click="editFile(file)">编辑</n-button>
                  <n-button size="small" @click="executeFile(file)" :loading="file.executing">执行</n-button>
                  <n-button size="small" @click="downloadFile(file)">下载</n-button>
                </n-space>
              </div>
              
              <!-- 测试用例列表 -->
              <div v-if="file.expanded" class="ml-8 mt-3 border-l-2 border-gray-200 pl-4">
                <div class="text-sm font-medium mb-2">测试用例:</div>
                <div class="space-y-1">
                  <div v-for="testCase in file.testCases" :key="testCase.name" class="flex items-center justify-between">
                    <div class="flex items-center space-x-2">
                      <n-icon size="16" color="#10b981">
                        <Icon icon="mdi:check-circle" />
                      </n-icon>
                      <span class="text-sm">{{ testCase.name }}</span>
                    </div>
                    <div class="text-xs text-gray-500">{{ testCase.type }}</div>
                  </div>
                </div>
              </div>
              
              <div class="mt-2">
                <n-button 
                  text 
                  size="small" 
                  @click="file.expanded = !file.expanded"
                >
                  {{ file.expanded ? '收起' : '展开' }} 测试用例
                </n-button>
              </div>
            </div>
          </n-list-item>
        </n-list>
      </div>
      
      <n-empty v-else description="暂无生成的脚本文件" />
    </n-card>

    <!-- 代码预览模态框 -->
    <n-modal v-model:show="showPreviewModal" preset="card" title="代码预览" style="width: 90%">
      <div v-if="previewFile">
        <div class="flex justify-between items-center mb-4">
          <div>
            <h4 class="font-semibold">{{ previewFile.fileName }}</h4>
            <p class="text-sm text-gray-500">{{ previewFile.framework }} • {{ previewFile.testCaseCount }} 个测试用例</p>
          </div>
          <n-space>
            <n-button size="small" @click="copyCode">
              <template #icon>
                <n-icon><Icon icon="mdi:content-copy" /></n-icon>
              </template>
              复制代码
            </n-button>
            <n-button size="small" type="primary" @click="editFile(previewFile)">
              编辑
            </n-button>
          </n-space>
        </div>
        
        <div class="code-preview">
          <n-code 
            :code="previewFile.content" 
            :language="getLanguage(previewFile.framework)"
            show-line-numbers
            style="max-height: 60vh; overflow: auto"
          />
        </div>
      </div>
    </n-modal>

    <!-- 代码编辑模态框 -->
    <n-modal v-model:show="showEditModal" preset="card" title="编辑测试脚本" style="width: 95%">
      <div v-if="editingFile">
        <div class="flex justify-between items-center mb-4">
          <div>
            <h4 class="font-semibold">{{ editingFile.fileName }}</h4>
            <div class="flex items-center space-x-4 text-sm text-gray-500">
              <span>{{ editingFile.framework }}</span>
              <span>{{ editingFile.testCaseCount }} 个测试用例</span>
              <n-tag :type="getQualityType(editingFile.quality)">{{ editingFile.quality }}</n-tag>
            </div>
          </div>
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
            <n-button size="small" @click="executeFile(editingFile)" :loading="editingFile.executing">
              <template #icon>
                <n-icon><Icon icon="mdi:play" /></n-icon>
              </template>
              测试运行
            </n-button>
          </n-space>
        </div>
        
        <div class="code-editor">
          <n-input
            v-model:value="editingFile.content"
            type="textarea"
            :rows="25"
            placeholder="测试脚本代码..."
            style="font-family: 'Courier New', monospace; font-size: 14px"
          />
        </div>
      </div>

      <template #footer>
        <div class="flex justify-between">
          <n-space>
            <n-button @click="resetCode">重置</n-button>
            <n-button @click="previewChanges">预览变更</n-button>
          </n-space>
          <n-space>
            <n-button @click="showEditModal = false">取消</n-button>
            <n-button type="primary" @click="saveChanges" :loading="saving">保存</n-button>
          </n-space>
        </div>
      </template>
    </n-modal>

    <!-- 执行结果模态框 -->
    <n-modal v-model:show="showExecutionModal" preset="card" title="执行结果" style="width: 80%">
      <div v-if="executionResult">
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <n-statistic label="执行状态" :value="executionResult.status" />
          <n-statistic label="执行时间" :value="`${executionResult.duration}s`" />
          <n-statistic label="通过用例" :value="executionResult.passedTests" />
          <n-statistic label="失败用例" :value="executionResult.failedTests" />
        </div>

        <n-tabs type="line">
          <n-tab-pane name="summary" tab="执行摘要">
            <n-alert
              :type="executionResult.status === 'success' ? 'success' : 'error'"
              :title="executionResult.status === 'success' ? '执行成功' : '执行失败'"
              class="mb-4"
            >
              {{ executionResult.message }}
            </n-alert>
            
            <div v-if="executionResult.testResults">
              <h4 class="font-semibold mb-2">测试用例结果</h4>
              <n-list>
                <n-list-item v-for="result in executionResult.testResults" :key="result.name">
                  <div class="flex items-center justify-between w-full">
                    <div class="flex items-center space-x-2">
                      <n-icon :color="result.passed ? '#10b981' : '#ef4444'">
                        <mdi:check-circle v-if="result.passed" />
                        <mdi:close-circle v-else />
                      </n-icon>
                      <span>{{ result.name }}</span>
                    </div>
                    <div class="text-sm text-gray-500">{{ result.duration }}ms</div>
                  </div>
                </n-list-item>
              </n-list>
            </div>
          </n-tab-pane>
          
          <n-tab-pane name="logs" tab="执行日志">
            <div class="bg-black text-green-400 p-4 rounded font-mono text-sm h-64 overflow-y-auto">
              <div v-for="(log, index) in executionResult.logs" :key="index" class="mb-1">
                <span class="text-gray-500">[{{ formatTime(log.timestamp) }}]</span>
                <span>{{ log.message }}</span>
              </div>
            </div>
          </n-tab-pane>
          
          <n-tab-pane name="coverage" tab="覆盖率报告">
            <div class="border border-dashed border-gray-300 rounded-lg p-8 text-center text-gray-500">
              <n-icon size="48"><Icon icon="mdi:chart-pie" /></n-icon>
              <div class="mt-2">覆盖率报告功能开发中...</div>
            </div>
          </n-tab-pane>
        </n-tabs>
      </div>
    </n-modal>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Icon } from '@iconify/vue'
import { useRoute, useRouter } from 'vue-router'
import { useMessage } from 'naive-ui'
import api from '@/api'
import { formatTime, formatFileSize } from '@/utils'

const route = useRoute()
const router = useRouter()
const message = useMessage()

// 数据
const generationResult = ref(null)
const scriptFiles = ref([])
const previewFile = ref(null)
const editingFile = ref(null)
const executionResult = ref(null)

// 模态框状态
const showPreviewModal = ref(false)
const showEditModal = ref(false)
const showExecutionModal = ref(false)

// 状态
const executing = ref(false)
const saving = ref(false)

// 方法
const loadGenerationResult = async () => {
  try {
    const taskId = route.query.taskId
    if (!taskId) {
      message.error('缺少任务ID参数')
      return
    }

    const response = await api.getGenerationResult({ taskId })
    generationResult.value = response.data
    
    // 加载脚本文件
    if (response.data.generatedScripts) {
      scriptFiles.value = response.data.generatedScripts.map(script => ({
        ...script,
        expanded: false,
        executing: false
      }))
    }
  } catch (error) {
    message.error('加载生成结果失败')
  }
}

const previewFile = async (file) => {
  try {
    const response = await api.getScriptContent({ 
      taskId: route.query.taskId,
      fileName: file.fileName 
    })
    
    previewFile.value = {
      ...file,
      content: response.data.content
    }
    showPreviewModal.value = true
  } catch (error) {
    message.error('加载脚本内容失败')
  }
}

const editFile = async (file) => {
  try {
    const response = await api.getScriptContent({ 
      taskId: route.query.taskId,
      fileName: file.fileName 
    })
    
    editingFile.value = {
      ...file,
      content: response.data.content,
      originalContent: response.data.content
    }
    showEditModal.value = true
  } catch (error) {
    message.error('加载脚本内容失败')
  }
}

const executeFile = async (file) => {
  file.executing = true
  try {
    const response = await api.executeScript({
      taskId: route.query.taskId,
      fileName: file.fileName,
      content: file.content
    })
    
    executionResult.value = response.data
    showExecutionModal.value = true
  } catch (error) {
    message.error('执行脚本失败')
  } finally {
    file.executing = false
  }
}

const downloadFile = (file) => {
  const link = document.createElement('a')
  link.href = `/api/api-automation/download-script?taskId=${route.query.taskId}&fileName=${encodeURIComponent(file.fileName)}`
  link.download = file.fileName
  link.click()
}

const downloadAll = () => {
  const link = document.createElement('a')
  link.href = `/api/api-automation/download-all-scripts?taskId=${route.query.taskId}`
  link.download = `test_scripts_${route.query.taskId}.zip`
  link.click()
}

const executeAll = async () => {
  executing.value = true
  try {
    const response = await api.executeAllScripts({
      taskId: route.query.taskId
    })
    
    message.success('批量执行已启动')
    
    // 跳转到执行页面
    router.push({
      path: '/api-automation/test-execution',
      query: { executionId: response.data.executionId }
    })
  } catch (error) {
    message.error('批量执行失败')
  } finally {
    executing.value = false
  }
}

const copyCode = () => {
  if (previewFile.value?.content) {
    navigator.clipboard.writeText(previewFile.value.content)
    message.success('代码已复制到剪贴板')
  }
}

const formatCode = () => {
  message.info('代码格式化功能开发中...')
}

const validateCode = () => {
  message.info('语法验证功能开发中...')
}

const resetCode = () => {
  if (editingFile.value) {
    editingFile.value.content = editingFile.value.originalContent
    message.info('代码已重置')
  }
}

const previewChanges = () => {
  message.info('变更预览功能开发中...')
}

const saveChanges = async () => {
  saving.value = true
  try {
    await api.updateScriptContent({
      taskId: route.query.taskId,
      fileName: editingFile.value.fileName,
      content: editingFile.value.content
    })
    
    message.success('保存成功')
    showEditModal.value = false
    
    // 更新文件列表
    const fileIndex = scriptFiles.value.findIndex(f => f.fileName === editingFile.value.fileName)
    if (fileIndex !== -1) {
      scriptFiles.value[fileIndex] = { ...editingFile.value }
    }
  } catch (error) {
    message.error('保存失败')
  } finally {
    saving.value = false
  }
}

const getLanguage = (framework) => {
  const languageMap = {
    'pytest': 'python',
    'unittest': 'python',
    'requests': 'python',
    'jest': 'javascript',
    'mocha': 'javascript'
  }
  return languageMap[framework] || 'python'
}

const getQualityType = (quality) => {
  const typeMap = {
    'A+': 'success',
    'A': 'success',
    'B+': 'info',
    'B': 'info',
    'C': 'warning',
    'D': 'error',
    'F': 'error'
  }
  return typeMap[quality] || 'default'
}

onMounted(() => {
  loadGenerationResult()
})
</script>

<style scoped>
.script-preview {
  padding: 20px;
}

.code-preview,
.code-editor {
  border: 1px solid #e5e7eb;
  border-radius: 6px;
}

.code-editor textarea {
  font-family: 'Courier New', monospace !important;
  font-size: 14px !important;
  line-height: 1.5 !important;
}
</style>
