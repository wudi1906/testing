<template>
  <div class="document-workflow">
    <!-- 步骤导航 -->
    <n-card class="mb-6">
      <n-steps :current="currentStep" :status="stepStatus">
        <n-step title="上传文档" description="上传API文档文件" />
        <n-step title="文档解析" description="智能解析API结构" />
        <n-step title="接口分析" description="深度分析API接口" />
        <n-step title="生成测试" description="生成测试脚本" />
      </n-steps>
    </n-card>

    <!-- 步骤1: 文档上传 -->
    <n-card v-if="currentStep === 1" title="上传API文档" class="mb-6">
      <div class="upload-section">
        <n-upload
          ref="uploadRef"
          :file-list="fileList"
          :max="1"
          accept=".json,.yaml,.yml,.pdf"
          :default-upload="false"
          @before-upload="beforeUpload"
          @change="handleFileChange"
        >
          <n-upload-dragger>
            <div style="margin-bottom: 12px">
              <n-icon size="48" :depth="3">
                <Icon icon="mdi:cloud-upload" />
              </n-icon>
            </div>
            <n-text style="font-size: 16px">
              点击或者拖动文件到该区域来上传
            </n-text>
            <n-p depth="3" style="margin: 8px 0 0 0">
              支持 OpenAPI/Swagger (.json, .yaml)、Postman Collection (.json) 和 PDF 接口文档格式
            </n-p>
          </n-upload-dragger>
        </n-upload>

        <div v-if="selectedFile" class="mt-4">
          <n-alert type="info" title="文件已选择">
            文件: {{ selectedFile.name }} ({{ formatFileSize(selectedFile.size) }})
          </n-alert>

          <div class="mt-4 flex justify-end">
            <n-button type="primary" @click="uploadAndParse" :loading="uploading || parsing">
              {{ uploading ? '上传中...' : parsing ? '解析中...' : '上传并解析' }}
            </n-button>
          </div>
        </div>

        <div v-if="uploadedFile && !parsing" class="mt-4">
          <n-alert type="success" title="文件上传成功">
            文件: {{ uploadedFile.name }} ({{ formatFileSize(uploadedFile.size) }})
          </n-alert>
        </div>
      </div>
    </n-card>

    <!-- 步骤2: 文档解析 -->
    <n-card v-if="currentStep === 2" title="文档解析中" class="mb-6">
      <div class="parsing-section">
        <div class="flex items-center mb-4">
          <n-spin size="small" />
          <span class="ml-2">{{ parsingStatus }}</span>
        </div>
        
        <n-progress 
          type="line" 
          :percentage="parsingProgress" 
          :show-indicator="true"
          status="active"
        />

        <!-- 实时解析日志 -->
        <div class="mt-4">
          <n-collapse>
            <n-collapse-item title="解析日志" name="logs">
              <div class="bg-black text-green-400 p-4 rounded font-mono text-sm h-48 overflow-y-auto">
                <div v-for="(log, index) in parsingLogs" :key="index" class="mb-1">
                  <span class="text-gray-500">[{{ formatTime(log.timestamp) }}]</span>
                  <span>{{ log.message }}</span>
                </div>
              </div>
            </n-collapse-item>
          </n-collapse>
        </div>
      </div>
    </n-card>

    <!-- 步骤3: 解析结果 -->
    <n-card v-if="currentStep === 3" title="解析结果" class="mb-6">
      <div v-if="parseResult">
        <!-- 解析摘要 -->
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <n-statistic label="接口数量" :value="parseResult.endpointsCount" />
          <n-statistic label="数据模型" :value="parseResult.schemasCount" />
          <n-statistic label="解析置信度" :value="`${parseResult.confidenceScore}%`" />
          <n-statistic label="处理时间" :value="`${parseResult.processingTime}s`" />
        </div>

        <!-- 接口列表预览 -->
        <n-tabs type="line" class="mb-4">
          <n-tab-pane name="endpoints" tab="接口列表">
            <n-data-table
              :columns="endpointColumns"
              :data="parseResult.endpoints || []"
              :pagination="{ pageSize: 10 }"
              max-height="400"
            />
          </n-tab-pane>
          
          <n-tab-pane name="schemas" tab="数据模型">
            <n-tree
              :data="schemaTreeData"
              :render-label="renderSchemaLabel"
              block-line
            />
          </n-tab-pane>
        </n-tabs>

        <div class="flex justify-between">
          <n-button @click="currentStep = 1">重新上传</n-button>
          <n-button type="primary" @click="startAnalysis">
            开始接口分析
          </n-button>
        </div>
      </div>
    </n-card>

    <!-- 步骤4: 接口分析 -->
    <n-card v-if="currentStep === 4" title="接口分析" class="mb-6">
      <div v-if="!analyzing">
        <!-- 分析配置 -->
        <n-form ref="analysisFormRef" :model="analysisConfig" label-placement="left" label-width="120px">
          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <n-form-item label="分析类型">
                <n-checkbox-group v-model:value="analysisConfig.analysisTypes">
                  <n-space vertical>
                    <n-checkbox value="dependency">依赖关系分析</n-checkbox>
                    <n-checkbox value="security">安全性评估</n-checkbox>
                    <n-checkbox value="performance">性能分析</n-checkbox>
                    <n-checkbox value="complexity">复杂度评估</n-checkbox>
                  </n-space>
                </n-checkbox-group>
              </n-form-item>
            </div>
            
            <div>
              <n-form-item label="分析深度">
                <n-radio-group v-model:value="analysisConfig.depth">
                  <n-space vertical>
                    <n-radio value="basic">基础分析</n-radio>
                    <n-radio value="detailed">详细分析</n-radio>
                    <n-radio value="comprehensive">全面分析</n-radio>
                  </n-space>
                </n-radio-group>
              </n-form-item>
            </div>
          </div>
          
          <n-form-item>
            <n-button type="primary" @click="executeAnalysis" :loading="analyzing">
              执行分析
            </n-button>
          </n-form-item>
        </n-form>
      </div>

      <!-- 分析进行中 -->
      <div v-if="analyzing" class="analysis-progress">
        <div class="flex items-center mb-4">
          <n-spin size="small" />
          <span class="ml-2">{{ analysisStatus }}</span>
        </div>
        
        <n-progress 
          type="line" 
          :percentage="analysisProgress" 
          :show-indicator="true"
          status="active"
        />
      </div>

      <!-- 分析结果 -->
      <div v-if="analysisResult" class="analysis-result mt-6">
        <n-alert type="success" title="分析完成" class="mb-4">
          接口分析已完成，发现 {{ analysisResult.totalEndpoints }} 个接口，
          {{ analysisResult.dependenciesCount }} 个依赖关系
        </n-alert>

        <div class="flex justify-between">
          <n-button @click="viewAnalysisDetail">查看详细分析</n-button>
          <n-button type="primary" @click="proceedToTestGeneration">
            生成测试脚本
          </n-button>
        </div>
      </div>
    </n-card>

    <!-- 步骤5: 测试生成 -->
    <n-card v-if="currentStep === 5" title="生成测试脚本" class="mb-6">
      <div v-if="!generating">
        <!-- 测试生成配置 -->
        <n-form ref="generationFormRef" :model="generationConfig" label-placement="left" label-width="120px">
          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <n-form-item label="测试框架">
                <n-select v-model:value="generationConfig.framework" :options="frameworkOptions" />
              </n-form-item>
              
              <n-form-item label="测试类型">
                <n-checkbox-group v-model:value="generationConfig.testTypes">
                  <n-space vertical>
                    <n-checkbox value="functional">功能测试</n-checkbox>
                    <n-checkbox value="boundary">边界测试</n-checkbox>
                    <n-checkbox value="security">安全测试</n-checkbox>
                    <n-checkbox value="performance">性能测试</n-checkbox>
                  </n-space>
                </n-checkbox-group>
              </n-form-item>
            </div>
            
            <div>
              <n-form-item label="测试级别">
                <n-radio-group v-model:value="generationConfig.testLevel">
                  <n-space vertical>
                    <n-radio value="unit">单元测试</n-radio>
                    <n-radio value="integration">集成测试</n-radio>
                    <n-radio value="e2e">端到端测试</n-radio>
                  </n-space>
                </n-radio-group>
              </n-form-item>
              
              <n-form-item label="生成选项">
                <n-checkbox-group v-model:value="generationConfig.options">
                  <n-space vertical>
                    <n-checkbox value="mock_data">生成模拟数据</n-checkbox>
                    <n-checkbox value="assertions">智能断言</n-checkbox>
                    <n-checkbox value="error_handling">错误处理</n-checkbox>
                    <n-checkbox value="documentation">测试文档</n-checkbox>
                  </n-space>
                </n-checkbox-group>
              </n-form-item>
            </div>
          </div>
          
          <n-form-item>
            <n-button type="primary" @click="generateTests" :loading="generating">
              生成测试脚本
            </n-button>
          </n-form-item>
        </n-form>
      </div>

      <!-- 生成进行中 -->
      <div v-if="generating" class="generation-progress">
        <div class="flex items-center mb-4">
          <n-spin size="small" />
          <span class="ml-2">{{ generationStatus }}</span>
        </div>
        
        <n-progress 
          type="line" 
          :percentage="generationProgress" 
          :show-indicator="true"
          status="active"
        />
      </div>

      <!-- 生成结果 -->
      <div v-if="generationResult" class="generation-result mt-6">
        <n-alert type="success" title="测试脚本生成完成" class="mb-4">
          已生成 {{ generationResult.totalTestFiles }} 个测试文件，
          包含 {{ generationResult.totalTestCases }} 个测试用例
        </n-alert>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
          <n-statistic label="测试文件" :value="generationResult.totalTestFiles" />
          <n-statistic label="测试用例" :value="generationResult.totalTestCases" />
          <n-statistic label="覆盖率评分" :value="`${generationResult.coverageScore}%`" />
        </div>

        <div class="flex justify-between">
          <n-space>
            <n-button @click="previewTestScripts">预览脚本</n-button>
            <n-button @click="downloadTestScripts">下载脚本</n-button>
          </n-space>
          <n-button type="primary" @click="goToTestManagement">
            管理测试脚本
          </n-button>
        </div>
      </div>
    </n-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, h } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, NTag, useMessage } from 'naive-ui'
import { Icon } from '@iconify/vue'
import api from '@/api'
import { formatTime, formatFileSize } from '@/utils'

const router = useRouter()
const message = useMessage()

// 当前步骤
const currentStep = ref(1)
const stepStatus = ref('process')

// 文件上传
const uploadRef = ref()
const fileList = ref([])
const selectedFile = ref(null)
const uploadedFile = ref(null)
const uploading = ref(false)

// 解析状态
const parsing = ref(false)
const parsingStatus = ref('')
const parsingProgress = ref(0)
const parsingLogs = ref([])
const parseResult = ref(null)

// 分析状态
const analyzing = ref(false)
const analysisStatus = ref('')
const analysisProgress = ref(0)
const analysisResult = ref(null)
const analysisConfig = ref({
  analysisTypes: ['dependency', 'security'],
  depth: 'detailed'
})

// 生成状态
const generating = ref(false)
const generationStatus = ref('')
const generationProgress = ref(0)
const generationResult = ref(null)
const generationConfig = ref({
  framework: 'pytest',
  testTypes: ['functional'],
  testLevel: 'integration',
  options: ['mock_data', 'assertions']
})

// 选项数据
const frameworkOptions = [
  { label: 'pytest', value: 'pytest' },
  { label: 'unittest', value: 'unittest' },
  { label: 'requests', value: 'requests' }
]

// 表格列定义
const endpointColumns = [
  { title: '方法', key: 'method', width: 80 },
  { title: '路径', key: 'path', width: 200 },
  { title: '摘要', key: 'summary', ellipsis: true },
  { title: '认证', key: 'authRequired', width: 80, render: (row) => row.authRequired ? '是' : '否' }
]

// 计算属性
const schemaTreeData = computed(() => {
  if (!parseResult.value?.schemas) return []
  return Object.keys(parseResult.value.schemas).map(key => ({
    label: key,
    key: key,
    children: []
  }))
})

// 方法
const beforeUpload = (data) => {
  const { file } = data

  console.log('文件上传检查:', {
    name: file.name,
    type: file.type,
    size: file.size,
    sizeInMB: (file.size / 1024 / 1024).toFixed(2)
  })

  // 支持的文件类型（包含各种可能的MIME类型）
  const supportedTypes = [
    // JSON格式
    'application/json',
    'text/json',
    'text/plain', // 有时JSON文件被识别为text/plain

    // YAML格式
    'text/yaml',
    'text/x-yaml',
    'application/x-yaml',
    'application/yaml',

    // PDF格式
    'application/pdf'
  ]

  const supportedExtensions = ['.json', '.yaml', '.yml', '.pdf']

  // 检查文件类型
  const fileName = file.name.toLowerCase()
  const fileType = file.type.toLowerCase()

  const isValidType = supportedTypes.includes(fileType) ||
                     supportedExtensions.some(ext => fileName.endsWith(ext))

  if (!isValidType) {
    message.error(`不支持的文件格式。文件: ${file.name}, 类型: ${file.type}`)
    return false
  }

  // 判断是否为PDF文件
  const isPdfFile = fileName.endsWith('.pdf') || fileType === 'application/pdf'

  // 根据文件类型设置大小限制
  const maxSize = isPdfFile ? 50 : 10 // PDF: 50MB, 其他: 10MB
  const fileSizeInMB = file.size / 1024 / 1024

  console.log('文件大小检查:', {
    isPdfFile,
    maxSize,
    fileSizeInMB: fileSizeInMB.toFixed(2),
    isValid: fileSizeInMB < maxSize
  })

  if (fileSizeInMB >= maxSize) {
    message.error(`文件大小 ${fileSizeInMB.toFixed(2)}MB 超过限制 ${maxSize}MB`)
    return false
  }

  // 文件大小为0的检查
  if (file.size === 0) {
    message.error('文件为空，请选择有效的文件')
    return false
  }

  message.success(`文件检查通过: ${file.name} (${fileSizeInMB.toFixed(2)}MB)`)
  return true
}

const handleUploadFinish = ({ file, event }) => {
  try {
    const response = JSON.parse(event.target.response)
    if (response.success) {
      uploadedFile.value = {
        name: file.name,
        size: file.size,
        docId: response.data.docId
      }
      message.success('文件上传成功')
    } else {
      message.error(response.message || '上传失败')
    }
  } catch (error) {
    message.error('上传响应解析失败')
  }
}

const handleUploadError = () => {
  message.error('文件上传失败')
}

const handleFileChange = ({ fileList: newFileList }) => {
  fileList.value = newFileList
  if (newFileList.length > 0) {
    selectedFile.value = newFileList[0].file
    console.log('选择的文件:', selectedFile.value)
  } else {
    selectedFile.value = null
  }
}

const uploadAndParse = async () => {
  if (!selectedFile.value) {
    message.error('请先选择文件')
    return
  }

  uploading.value = true

  try {
    console.log('开始上传文件:', selectedFile.value.name)

    // 创建FormData
    const formData = new FormData()
    formData.append('file', selectedFile.value)
    formData.append('doc_format', 'auto')
    formData.append('auto_parse', 'true')  // 启用自动解析
    formData.append('config', JSON.stringify({
      extractSchemas: true,
      analyzeDependencies: true,
      generateExamples: true,
      isPdfDocument: selectedFile.value.name.toLowerCase().endsWith('.pdf')
    }))

    // 调用上传API
    const response = await api.uploadDocument(formData)

    console.log('上传响应:', response)

    if (response.success) {
      uploadedFile.value = {
        name: selectedFile.value.name,
        size: selectedFile.value.size,
        docId: response.data.docId,
        sessionId: response.data.sessionId,
        status: response.data.status,
        autoParse: response.data.autoParse
      }

      message.success('文件上传成功')

      // 如果启用了自动解析，开始监控解析状态
      if (response.data.autoParse && response.data.status === 'parsing') {
        currentStep.value = 2
        parsing.value = true
        parsingStatus.value = '文档上传成功，正在后台解析...'
        parsingProgress.value = 10

        // 开始轮询解析状态
        await monitorParsingStatus(response.data.sessionId)
      } else {
        // 手动解析模式，显示解析按钮
        currentStep.value = 2
      }

    } else {
      message.error(response.message || '文件上传失败')
    }

  } catch (error) {
    console.error('上传失败:', error)
    message.error(`文件上传失败: ${error.message || '未知错误'}`)
  } finally {
    uploading.value = false
  }
}

// 监控解析状态
const monitorParsingStatus = async (sessionId) => {
  const maxAttempts = 60 // 最多查询60次（5分钟）
  let attempts = 0

  const checkStatus = async () => {
    try {
      attempts++
      console.log(`查询解析状态 (${attempts}/${maxAttempts}):`, sessionId)

      const response = await api.getParseStatus(sessionId)

      if (response.success) {
        const { status, progress, message: statusMessage, result } = response.data

        // 更新进度
        parsingProgress.value = progress || 0
        parsingStatus.value = statusMessage || '正在解析...'

        console.log(`解析状态: ${status}, 进度: ${progress}%`)

        if (status === 'completed') {
          // 解析完成
          parsing.value = false
          currentStep.value = 3
          parsingProgress.value = 100
          parsingStatus.value = '文档解析完成'

          if (result) {
            parseResult.value = result
            message.success('文档解析完成！')
          }

          return true // 完成
        } else if (status === 'failed') {
          // 解析失败
          parsing.value = false
          parsingProgress.value = 0
          parsingStatus.value = `解析失败: ${response.data.error || '未知错误'}`
          message.error('文档解析失败')

          return true // 结束
        } else if (status === 'parsing' || status === 'processing') {
          // 继续解析中
          return false // 继续监控
        } else {
          // 其他状态
          console.warn('未知解析状态:', status)
          return false
        }
      } else {
        console.error('查询解析状态失败:', response.message)
        return false
      }
    } catch (error) {
      console.error('查询解析状态异常:', error)
      return false
    }
  }

  // 开始轮询
  const pollInterval = setInterval(async () => {
    const isComplete = await checkStatus()

    if (isComplete || attempts >= maxAttempts) {
      clearInterval(pollInterval)

      if (attempts >= maxAttempts && parsing.value) {
        // 超时处理
        parsing.value = false
        parsingStatus.value = '解析超时，请手动查询状态'
        message.warning('解析查询超时，请手动刷新页面查看结果')
      }
    }
  }, 5000) // 每5秒查询一次

  // 立即执行一次
  const isComplete = await checkStatus()
  if (isComplete) {
    clearInterval(pollInterval)
  }
}

const startParsing = async () => {
  if (!uploadedFile.value) return

  parsing.value = true
  currentStep.value = 2

  // 根据文件类型设置不同的解析提示
  const isPdf = uploadedFile.value.name.toLowerCase().endsWith('.pdf')
  parsingStatus.value = isPdf ? '开始解析PDF文档，正在提取文本内容...' : '开始解析文档...'
  parsingProgress.value = 10

  try {
    // 手动触发解析
    const response = await api.triggerDocumentParse(uploadedFile.value.sessionId, {
      extractSchemas: true,
      analyzeDependencies: true,
      generateExamples: true,
      isPdfDocument: isPdf
    })

    if (response.success) {
      message.success('解析已启动')

      // 开始监控解析状态
      await monitorParsingStatus(uploadedFile.value.sessionId)
    } else {
      throw new Error(response.message || '启动解析失败')
    }
  } catch (error) {
    parsing.value = false
    parsingProgress.value = 0
    parsingStatus.value = '解析失败'
    message.error(`解析失败: ${error.message}`)
  }
}

const startAnalysis = () => {
  currentStep.value = 4
}

const executeAnalysis = async () => {
  analyzing.value = true
  analysisStatus.value = '开始分析接口...'
  analysisProgress.value = 0
  
  try {
    const response = await api.analyzeApiEndpoints({
      docId: uploadedFile.value.docId,
      config: analysisConfig.value
    })
    
    // 模拟分析进度
    const progressInterval = setInterval(() => {
      if (analysisProgress.value < 90) {
        analysisProgress.value += 15
        analysisStatus.value = `分析中... ${analysisProgress.value}%`
      }
    }, 1500)
    
    // 轮询分析结果
    const checkAnalysis = async () => {
      const result = await api.getAnalysisResult({ analysisId: response.data.analysisId })
      if (result.data.status === 'completed') {
        clearInterval(progressInterval)
        analysisProgress.value = 100
        analysisStatus.value = '分析完成'
        analysisResult.value = result.data
        analyzing.value = false
      } else {
        setTimeout(checkAnalysis, 2000)
      }
    }
    
    setTimeout(checkAnalysis, 2000)
    
  } catch (error) {
    analyzing.value = false
    message.error('启动分析失败')
  }
}

const proceedToTestGeneration = () => {
  currentStep.value = 5
}

const generateTests = async () => {
  generating.value = true
  generationStatus.value = '开始生成测试脚本...'
  generationProgress.value = 0
  
  try {
    const response = await api.generateTestScripts({
      docId: uploadedFile.value.docId,
      analysisId: analysisResult.value.analysisId,
      config: generationConfig.value
    })
    
    // 模拟生成进度
    const progressInterval = setInterval(() => {
      if (generationProgress.value < 90) {
        generationProgress.value += 12
        generationStatus.value = `生成中... ${generationProgress.value}%`
      }
    }, 1200)
    
    // 轮询生成结果
    const checkGeneration = async () => {
      const result = await api.getGenerationResult({ taskId: response.data.taskId })
      if (result.data.status === 'completed') {
        clearInterval(progressInterval)
        generationProgress.value = 100
        generationStatus.value = '生成完成'
        generationResult.value = result.data
        generating.value = false
      } else {
        setTimeout(checkGeneration, 2000)
      }
    }
    
    setTimeout(checkGeneration, 2000)
    
  } catch (error) {
    generating.value = false
    message.error('启动生成失败')
  }
}

const viewAnalysisDetail = () => {
  router.push({
    path: '/api-automation/analysis-detail',
    query: { analysisId: analysisResult.value.analysisId }
  })
}

const previewTestScripts = () => {
  router.push({
    path: '/api-automation/script-preview',
    query: { taskId: generationResult.value.taskId }
  })
}

const downloadTestScripts = () => {
  // 下载测试脚本
  message.info('下载功能开发中...')
}

const goToTestManagement = () => {
  router.push('/api-automation/script-management')
}

const renderSchemaLabel = ({ option }) => {
  return h('span', option.label)
}

onMounted(() => {
  // 初始化
})
</script>

<style scoped>
.document-workflow {
  padding: 20px;
}

.upload-section {
  max-width: 600px;
  margin: 0 auto;
}

.parsing-section,
.analysis-progress,
.generation-progress {
  max-width: 800px;
  margin: 0 auto;
}
</style>
