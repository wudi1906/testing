<template>
  <div class="interface-management">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-content">
        <div class="title-section">
          <h1 class="page-title">
            <Icon icon="mdi:api" class="title-icon" />
            接口管理
          </h1>
          <p class="page-description">
            管理API接口信息，支持上传文档自动解析接口并存储到数据库
          </p>
        </div>
        <div class="action-section">
          <n-button type="primary" @click="showUploadModal = true">
            <template #icon>
              <Icon icon="mdi:upload" />
            </template>
            上传接口文档
          </n-button>
        </div>
      </div>
    </div>

    <!-- 全局解析进度提示 -->
    <div v-if="globalProgress.show" class="global-progress">
      <n-card>
        <div class="progress-content">
          <div class="progress-info">
            <div class="progress-title">
              <Icon icon="mdi:file-document-outline" class="progress-icon" />
              正在解析文档: {{ globalProgress.fileName }}
            </div>
            <div class="progress-text">{{ globalProgress.text }}</div>
          </div>
          <div class="progress-bar">
            <n-progress
              type="line"
              :percentage="globalProgress.percentage"
              :status="globalProgress.status"
              :show-indicator="true"
            />
          </div>
        </div>
      </n-card>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-cards">
      <n-grid :cols="4" :x-gap="16">
        <n-grid-item>
          <n-card class="stat-card">
            <div class="stat-content">
              <div class="stat-icon documents">
                <Icon icon="mdi:file-document" />
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ statistics.total_documents || 0 }}</div>
                <div class="stat-label">API文档</div>
              </div>
            </div>
          </n-card>
        </n-grid-item>
        <n-grid-item>
          <n-card class="stat-card">
            <div class="stat-content">
              <div class="stat-icon interfaces">
                <Icon icon="mdi:api" />
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ statistics.total_interfaces || 0 }}</div>
                <div class="stat-label">接口数量</div>
              </div>
            </div>
          </n-card>
        </n-grid-item>
        <n-grid-item>
          <n-card class="stat-card">
            <div class="stat-content">
              <div class="stat-icon methods">
                <Icon icon="mdi:code-braces" />
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ Object.keys(statistics.method_statistics || {}).length }}</div>
                <div class="stat-label">HTTP方法</div>
              </div>
            </div>
          </n-card>
        </n-grid-item>
        <n-grid-item>
          <n-card class="stat-card">
            <div class="stat-content">
              <div class="stat-icon formats">
                <Icon icon="mdi:file-code" />
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ Object.keys(statistics.format_statistics || {}).length }}</div>
                <div class="stat-label">文档格式</div>
              </div>
            </div>
          </n-card>
        </n-grid-item>
      </n-grid>
    </div>

    <!-- 主要内容区域 -->
    <div class="main-content">
      <n-tabs v-model:value="activeTab" type="line" animated>
        <!-- 接口管理标签页 - 调整为第一个 -->
        <n-tab-pane name="interfaces" tab="接口管理">
          <div class="tab-content">
            <!-- 搜索和筛选 -->
            <div class="search-section">
              <n-space>
                <n-input
                  v-model:value="interfaceSearch.search"
                  placeholder="搜索接口名称或路径..."
                  clearable
                  style="width: 300px"
                  @input="handleInterfaceSearch"
                >
                  <template #prefix>
                    <Icon icon="mdi:magnify" />
                  </template>
                </n-input>
                <n-select
                  v-model:value="interfaceSearch.method"
                  placeholder="HTTP方法"
                  clearable
                  style="width: 120px"
                  :options="methodOptions"
                  @update:value="handleInterfaceSearch"
                />
                <n-select
                  v-model:value="interfaceSearch.doc_id"
                  placeholder="选择文档"
                  clearable
                  style="width: 200px"
                  :options="documentOptions"
                  @update:value="handleInterfaceSearch"
                />
                <n-button @click="refreshInterfaces">
                  <template #icon>
                    <Icon icon="mdi:refresh" />
                  </template>
                  刷新
                </n-button>
              </n-space>
            </div>

            <!-- 接口列表 -->
            <n-data-table
              :columns="interfaceColumns"
              :data="interfaceList"
              :loading="interfaceLoading"
              :pagination="interfacePagination"
              :row-key="(row) => row.interface_id"
              :max-height="600"
              remote
              @update:page="handleInterfacePageChange"
              @update:page-size="handleInterfacePageSizeChange"
            />
          </div>
        </n-tab-pane>

        <!-- 文档管理标签页 - 调整为第二个 -->
        <n-tab-pane name="documents" tab="文档管理">
          <div class="tab-content">
            <!-- 搜索和筛选 -->
            <div class="search-section">
              <n-space>
                <n-input
                  v-model:value="documentSearch.search"
                  placeholder="搜索文档名称..."
                  clearable
                  style="width: 300px"
                  @input="handleDocumentSearch"
                >
                  <template #prefix>
                    <Icon icon="mdi:magnify" />
                  </template>
                </n-input>
                <n-select
                  v-model:value="documentSearch.format"
                  placeholder="文档格式"
                  clearable
                  style="width: 150px"
                  :options="formatOptions"
                  @update:value="handleDocumentSearch"
                />
                <n-button @click="refreshDocuments">
                  <template #icon>
                    <Icon icon="mdi:refresh" />
                  </template>
                  刷新
                </n-button>
              </n-space>
            </div>

            <!-- 文档列表 -->
            <n-data-table
              :columns="documentColumns"
              :data="documentList"
              :loading="documentLoading"
              :pagination="documentPagination"
              :row-key="(row) => row.doc_id"
              :max-height="600"
              remote
              @update:page="handleDocumentPageChange"
              @update:page-size="handleDocumentPageSizeChange"
            />
          </div>
        </n-tab-pane>
      </n-tabs>
    </div>

    <!-- 上传文档模态框 -->
    <n-modal v-model:show="showUploadModal" preset="dialog" title="上传接口文档">
      <template #header>
        <div class="modal-header">
          <Icon icon="mdi:upload" class="modal-icon" />
          上传接口文档
        </div>
      </template>
      
      <div class="upload-content">
        <n-upload
          ref="uploadRef"
          v-model:file-list="fileList"
          :max="1"
          :show-file-list="true"
          :default-upload="false"
          :on-before-upload="handleBeforeUpload"
          :on-change="handleFileChange"
          :on-remove="handleFileRemove"
          accept=".json,.yaml,.yml,.pdf,.md,.txt"
        >
          <n-upload-dragger>
            <div class="upload-area">
              <Icon icon="mdi:cloud-upload" class="upload-icon" />
              <div class="upload-text">
                <p class="upload-hint">点击或拖拽文件到此区域上传</p>
                <p class="upload-desc">
                  支持 JSON、YAML、PDF、Markdown 等格式的API文档
                </p>
              </div>
            </div>
          </n-upload-dragger>
        </n-upload>

        <!-- 上传进度 -->
        <div v-if="uploadProgress.show" class="upload-progress">
          <n-progress
            type="line"
            :percentage="uploadProgress.percentage"
            :status="uploadProgress.status"
            :show-indicator="true"
          />
          <p class="progress-text">{{ uploadProgress.text }}</p>
        </div>
      </div>

      <template #action>
        <n-space>
          <n-button @click="handleCancelUpload">取消</n-button>
          <n-button
            type="primary"
            :loading="uploading"
            :disabled="fileList.length === 0 || uploading"
            @click="handleUpload"
          >
            {{ uploading ? '上传中...' : '上传并解析' }}
          </n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 详情模态框 -->
    <n-modal v-model:show="showDetailModal" style="width: 80%; max-width: 1200px;">
      <n-card
        :title="selectedInterface?.isDocument ? '文档详情' : '接口详情'"
        :bordered="false"
        size="huge"
        role="dialog"
        aria-modal="true"
      >
        <template #header-extra>
          <n-button quaternary circle @click="showDetailModal = false">
            <template #icon>
              <Icon icon="mdi:close" />
            </template>
          </n-button>
        </template>
        
        <div v-if="selectedInterface" class="interface-detail">
          <!-- 文档详情 -->
          <div v-if="selectedInterface.isDocument">
            <n-descriptions :column="2" bordered>
              <n-descriptions-item label="文档名称">
                {{ selectedInterface.file_name }}
              </n-descriptions-item>
              <n-descriptions-item label="文档格式">
                <n-tag size="small">{{ selectedInterface.doc_format?.toUpperCase() }}</n-tag>
              </n-descriptions-item>
              <n-descriptions-item label="API标题">
                {{ selectedInterface.api_info?.title || '暂无标题' }}
              </n-descriptions-item>
              <n-descriptions-item label="API版本">
                {{ selectedInterface.api_info?.version || '暂无版本' }}
              </n-descriptions-item>
              <n-descriptions-item label="接口数量">
                {{ selectedInterface.endpoints_count || 0 }}
              </n-descriptions-item>
              <n-descriptions-item label="解析状态">
                <n-tag :type="getParseStatusType(selectedInterface.parse_status)">
                  {{ getParseStatusText(selectedInterface.parse_status) }}
                </n-tag>
              </n-descriptions-item>
              <n-descriptions-item label="置信度">
                <n-progress
                  type="line"
                  :percentage="Math.round((selectedInterface.confidence_score || 0) * 100)"
                  :show-indicator="true"
                  style="width: 200px"
                />
              </n-descriptions-item>
              <n-descriptions-item label="创建时间">
                {{ formatTime(selectedInterface.created_at) }}
              </n-descriptions-item>
            </n-descriptions>

            <!-- API信息 -->
            <div v-if="selectedInterface.api_info" class="detail-section">
              <h3>API信息</h3>
              <n-descriptions :column="1" bordered>
                <n-descriptions-item label="描述">
                  {{ selectedInterface.api_info.description || '暂无描述' }}
                </n-descriptions-item>
                <n-descriptions-item label="基础URL">
                  {{ selectedInterface.api_info.base_url || '暂无' }}
                </n-descriptions-item>
                <n-descriptions-item v-if="selectedInterface.api_info.contact" label="联系信息">
                  {{ JSON.stringify(selectedInterface.api_info.contact) }}
                </n-descriptions-item>
                <n-descriptions-item v-if="selectedInterface.api_info.license" label="许可证">
                  {{ JSON.stringify(selectedInterface.api_info.license) }}
                </n-descriptions-item>
              </n-descriptions>
            </div>

            <!-- 接口列表 -->
            <div v-if="selectedInterface.interfaces && selectedInterface.interfaces.length > 0" class="detail-section">
              <h3>接口列表 ({{ selectedInterface.interfaces.length }})</h3>
              <n-data-table
                :columns="[
                  { title: '接口名称', key: 'name', width: 200 },
                  { title: '方法', key: 'method', width: 80, render: (row) => h('n-tag', { type: getMethodTagType(row.method), size: 'small' }, { default: () => row.method }) },
                  { title: '路径', key: 'path', width: 250 },
                  { title: '摘要', key: 'summary', ellipsis: { tooltip: true } },
                  { title: '参数数量', key: 'parameters', width: 100, render: (row) => row.parameters?.length || 0 },
                  { title: '响应数量', key: 'responses', width: 100, render: (row) => row.responses?.length || 0 }
                ]"
                :data="selectedInterface.interfaces"
                :pagination="false"
                size="small"
                max-height="300px"
              />
            </div>

            <!-- 解析错误和警告 -->
            <div v-if="selectedInterface.parse_errors && selectedInterface.parse_errors.length > 0" class="detail-section">
              <h3>解析错误</h3>
              <n-alert type="error" style="margin-bottom: 16px;">
                <ul style="margin: 0; padding-left: 20px;">
                  <li v-for="error in selectedInterface.parse_errors" :key="error">{{ error }}</li>
                </ul>
              </n-alert>
            </div>

            <div v-if="selectedInterface.parse_warnings && selectedInterface.parse_warnings.length > 0" class="detail-section">
              <h3>解析警告</h3>
              <n-alert type="warning">
                <ul style="margin: 0; padding-left: 20px;">
                  <li v-for="warning in selectedInterface.parse_warnings" :key="warning">{{ warning }}</li>
                </ul>
              </n-alert>
            </div>
          </div>

          <!-- 接口详情 -->
          <div v-else>
            <n-descriptions :column="2" bordered>
              <n-descriptions-item label="接口名称">
                {{ selectedInterface.name }}
              </n-descriptions-item>
              <n-descriptions-item label="请求路径">
                <n-tag :type="getMethodTagType(selectedInterface.method)">
                  {{ selectedInterface.method }}
                </n-tag>
                {{ selectedInterface.path }}
              </n-descriptions-item>
              <n-descriptions-item label="接口描述">
                {{ selectedInterface.description || '暂无描述' }}
              </n-descriptions-item>
              <n-descriptions-item label="是否需要认证">
                <n-tag :type="selectedInterface.auth_required ? 'warning' : 'success'">
                  {{ selectedInterface.auth_required ? '需要认证' : '无需认证' }}
                </n-tag>
              </n-descriptions-item>
              <n-descriptions-item label="置信度">
                <n-progress
                  type="line"
                  :percentage="Math.round(selectedInterface.confidence_score * 100)"
                  :show-indicator="true"
                  style="width: 200px"
                />
              </n-descriptions-item>
              <n-descriptions-item label="标签">
                <n-space>
                  <n-tag v-for="tag in selectedInterface.tags" :key="tag" size="small">
                    {{ tag }}
                  </n-tag>
                </n-space>
              </n-descriptions-item>
            </n-descriptions>
          </div>

          <!-- 接口参数和响应信息（仅在接口详情时显示） -->
          <div v-if="!selectedInterface.isDocument">
            <!-- 参数信息 -->
            <div class="detail-section">
              <h3>请求参数</h3>
              <n-tabs type="line" animated>
                <n-tab-pane
                  v-for="(params, location) in groupedParameters"
                  :key="location"
                  :name="location"
                  :tab="getLocationTabTitle(location, params.length)"
                >
                  <div class="parameter-group">
                    <div class="parameter-group-header">
                      <n-tag :type="getLocationTagType(location)" size="medium">
                        {{ getLocationDisplayName(location) }}
                      </n-tag>
                      <span class="parameter-count">{{ params.length }} 个参数</span>
                    </div>

                    <!-- 普通参数表格 -->
                    <div v-if="location !== 'body'">
                      <n-data-table
                        :columns="parameterColumns"
                        :data="params"
                        :pagination="false"
                        size="small"
                      />
                    </div>

                    <!-- Body参数特殊处理 -->
                    <div v-else>
                      <div v-if="params.length === 0" class="empty-state">
                        <n-empty description="暂无Body参数" />
                      </div>
                      <div v-else>
                        <!-- Body参数结构展示 -->
                        <div v-for="param in params" :key="param.name" class="body-parameter">
                          <n-card size="small" :bordered="false" class="body-param-card">
                            <template #header>
                              <div class="body-param-header">
                                <span class="param-name">{{ param.name }}</span>
                                <n-tag v-if="param.required" type="error" size="small">必需</n-tag>
                                <n-tag type="info" size="small">{{ param.data_type }}</n-tag>
                              </div>
                            </template>

                            <div class="body-param-content">
                              <div v-if="param.description" class="param-description">
                                <strong>描述：</strong>{{ param.description }}
                              </div>

                              <!-- Schema结构展示 -->
                              <div v-if="param.schema && Object.keys(param.schema).length > 0" class="param-schema">
                                <strong>结构：</strong>
                                <n-code
                                  :code="JSON.stringify(param.schema, null, 2)"
                                  language="json"
                                  show-line-numbers
                                  style="margin-top: 8px;"
                                />
                              </div>

                              <!-- 示例展示 -->
                              <div v-if="param.example" class="param-example">
                                <strong>示例：</strong>
                                <n-code
                                  :code="typeof param.example === 'string' ? param.example : JSON.stringify(param.example, null, 2)"
                                  :language="typeof param.example === 'string' ? 'text' : 'json'"
                                  style="margin-top: 8px;"
                                />
                              </div>

                              <!-- 约束条件 -->
                              <div v-if="param.constraints && Object.keys(param.constraints).length > 0" class="param-constraints">
                                <strong>约束：</strong>
                                <div class="constraints-list">
                                  <n-tag
                                    v-for="(value, key) in param.constraints"
                                    :key="key"
                                    size="small"
                                    type="default"
                                    style="margin: 2px;"
                                  >
                                    {{ key }}: {{ value }}
                                  </n-tag>
                                </div>
                              </div>
                            </div>
                          </n-card>
                        </div>
                      </div>
                    </div>
                  </div>
                </n-tab-pane>

                <!-- 如果没有参数，显示空状态 -->
                <n-tab-pane v-if="Object.keys(groupedParameters).length === 0" name="empty" tab="暂无参数">
                  <n-empty description="该接口暂无请求参数" />
                </n-tab-pane>
              </n-tabs>
            </div>

            <!-- 响应信息 -->
            <div class="detail-section">
              <h3>响应信息</h3>
              <n-data-table
                :columns="responseColumns"
                :data="selectedInterface.responses || []"
                :pagination="false"
                size="small"
              />
            </div>
          </div>
        </div>
      </n-card>
    </n-modal>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch, h } from 'vue'
import { Icon } from '@iconify/vue'
import { useMessage, useDialog, NButton } from 'naive-ui'
import { useRouter } from 'vue-router'
import api from '@/api'
import { request } from '@/utils'
import { formatTime, formatFileSize } from '@/utils'
import SessionLogViewer from '@/components/SessionLogViewer.vue'

const message = useMessage()
const dialog = useDialog()
const router = useRouter()

// 响应式数据
const activeTab = ref('interfaces')
const showUploadModal = ref(false)
const showDetailModal = ref(false)
const uploading = ref(false)
const documentLoading = ref(false)
const interfaceLoading = ref(false)

// 统计数据
const statistics = ref({})

// 文件上传
const uploadRef = ref()
const fileList = ref([])
const uploadProgress = reactive({
  show: false,
  percentage: 0,
  status: 'active',
  text: ''
})

// 全局解析进度
const globalProgress = reactive({
  show: false,
  percentage: 0,
  status: 'active',
  text: '',
  sessionId: '',
  fileName: ''
})

// 文档管理
const documentList = ref([])
const documentSearch = reactive({
  search: '',
  format: null
})
const documentPagination = reactive({
  page: 1,
  pageSize: 20,
  itemCount: 0,
  showSizePicker: true,
  pageSizes: [10, 20, 50, 100],
  showQuickJumper: true,
  prefix: ({ itemCount }) => `共 ${itemCount} 条`
})

// 接口管理
const interfaceList = ref([])
const selectedInterface = ref(null)
const interfaceSearch = reactive({
  search: '',
  method: null,
  doc_id: null
})
const interfacePagination = reactive({
  page: 1,
  pageSize: 20,
  itemCount: 0,
  showSizePicker: true,
  pageSizes: [10, 20, 50, 100],
  showQuickJumper: true,
  prefix: ({ itemCount }) => `共 ${itemCount} 条`
})

// 脚本生成状态
const scriptGenerationLoading = ref(null)
const currentSessionId = ref('')
const showSessionLogs = ref(false)

// 选项数据
const formatOptions = [
  { label: 'OpenAPI', value: 'openapi' },
  { label: 'Swagger', value: 'swagger' },
  { label: 'Postman', value: 'postman' },
  { label: 'Markdown', value: 'markdown' },
  { label: 'PDF', value: 'pdf' }
]

const methodOptions = [
  { label: 'GET', value: 'GET' },
  { label: 'POST', value: 'POST' },
  { label: 'PUT', value: 'PUT' },
  { label: 'DELETE', value: 'DELETE' },
  { label: 'PATCH', value: 'PATCH' },
  { label: 'HEAD', value: 'HEAD' },
  { label: 'OPTIONS', value: 'OPTIONS' }
]

const documentOptions = ref([])

// 表格列定义
const documentColumns = [
  {
    title: '文档名称',
    key: 'file_name',
    width: 200,
    ellipsis: {
      tooltip: true
    }
  },
  {
    title: 'API标题',
    key: 'api_title',
    width: 150,
    ellipsis: {
      tooltip: true
    }
  },
  {
    title: '版本',
    key: 'api_version',
    width: 100
  },
  {
    title: '格式',
    key: 'doc_format',
    width: 100,
    render(row) {
      return h('n-tag', { size: 'small' }, { default: () => row.doc_format.toUpperCase() })
    }
  },
  {
    title: '接口数量',
    key: 'endpoints_count',
    width: 100
  },
  {
    title: '置信度',
    key: 'confidence_score',
    width: 120,
    render(row) {
      return h('n-progress', {
        type: 'line',
        percentage: Math.round(row.confidence_score * 100),
        showIndicator: false,
        height: 8
      })
    }
  },
  {
    title: '状态',
    key: 'parse_status',
    width: 100,
    render(row) {
      const statusMap = {
        'CREATED': { type: 'info', text: '已创建' },
        'PROCESSING': { type: 'warning', text: '处理中' },
        'COMPLETED': { type: 'success', text: '已完成' },
        'FAILED': { type: 'error', text: '失败' }
      }
      const status = statusMap[row.parse_status] || { type: 'default', text: row.parse_status }
      return h('n-tag', { type: status.type, size: 'small' }, { default: () => status.text })
    }
  },
  {
    title: '创建时间',
    key: 'created_at',
    width: 160,
    render(row) {
      return formatTime(row.created_at)
    }
  },
  {
    title: '操作',
    key: 'actions',
    width: 180,
    render(row) {
      return [
        h(NButton, {
          size: 'small',
          type: 'primary',
          style: 'margin-right: 8px;',
          onClick: () => viewDocumentDetail(row)
        }, {
          default: () => '查看',
          icon: () => h(Icon, { icon: 'mdi:eye' })
        }),
        h(NButton, {
          size: 'small',
          type: 'error',
          onClick: () => deleteDocument(row)
        }, {
          default: () => '删除',
          icon: () => h(Icon, { icon: 'mdi:delete' })
        })
      ]
    }
  }
]

const interfaceColumns = [
  {
    title: '接口名称',
    key: 'name',
    width: 200,
    ellipsis: {
      tooltip: true
    }
  },
  {
    title: '请求方法',
    key: 'method',
    width: 100,
    render(row) {
      return h('n-tag', {
        type: getMethodTagType(row.method),
        size: 'small'
      }, { default: () => row.method })
    }
  },
  {
    title: '请求路径',
    key: 'path',
    width: 250,
    ellipsis: {
      tooltip: true
    }
  },
  {
    title: '摘要',
    key: 'summary',
    width: 200,
    ellipsis: {
      tooltip: true
    }
  },
  {
    title: '标签',
    key: 'tags',
    width: 150,
    render(row) {
      if (!row.tags || row.tags.length === 0) return '-'
      return h('n-space', { size: 'small' },
        row.tags.slice(0, 2).map(tag =>
          h('n-tag', { size: 'small' }, { default: () => tag })
        ).concat(
          row.tags.length > 2 ? [h('span', `+${row.tags.length - 2}`)] : []
        )
      )
    }
  },
  {
    title: '认证',
    key: 'auth_required',
    width: 80,
    render(row) {
      return h('n-tag', {
        type: row.auth_required ? 'warning' : 'success',
        size: 'small'
      }, { default: () => row.auth_required ? '需要' : '无需' })
    }
  },
  {
    title: '置信度',
    key: 'confidence_score',
    width: 100,
    render(row) {
      return h('n-progress', {
        type: 'line',
        percentage: Math.round(row.confidence_score * 100),
        showIndicator: false,
        height: 8
      })
    }
  },
  {
    title: '所属文档',
    key: 'document_name',
    width: 150,
    ellipsis: {
      tooltip: true
    }
  },
  {
    title: '创建时间',
    key: 'created_at',
    width: 160,
    render(row) {
      return formatTime(row.created_at)
    }
  },
  {
    title: '操作',
    key: 'actions',
    width: 200,
    render(row) {
      return [
        h(NButton, {
          size: 'small',
          type: 'primary',
          style: 'margin-right: 8px;',
          onClick: () => viewInterfaceDetail(row)
        }, {
          default: () => '详情',
          icon: () => h(Icon, { icon: 'mdi:eye' })
        }),
        h(NButton, {
          size: 'small',
          type: 'success',
          loading: scriptGenerationLoading.value === row.interface_id,
          onClick: () => generateScript(row)
        }, {
          default: () => '生成脚本',
          icon: () => h(Icon, { icon: 'mdi:code-braces' })
        }),
        h(NButton, {
          size: 'small',
          type: 'info',
          style: 'margin-left: 8px;',
          onClick: () => viewInterfaceScripts(row)
        }, {
          default: () => '脚本管理',
          icon: () => h(Icon, { icon: 'mdi:script-text-outline' })
        })
      ]
    }
  }
]

const parameterColumns = [
  {
    title: '参数名',
    key: 'name',
    width: 120
  },
  {
    title: '位置',
    key: 'location',
    width: 80,
    render(row) {
      const locationMap = {
        'header': { type: 'info', text: 'Header' },
        'query': { type: 'success', text: 'Query' },
        'path': { type: 'warning', text: 'Path' },
        'body': { type: 'error', text: 'Body' },
        'form': { type: 'default', text: 'Form' }
      }
      const location = locationMap[row.location] || { type: 'default', text: row.location }
      return h('n-tag', { type: location.type, size: 'small' }, { default: () => location.text })
    }
  },
  {
    title: '类型',
    key: 'data_type',
    width: 80
  },
  {
    title: '必需',
    key: 'required',
    width: 60,
    render(row) {
      return h('n-tag', {
        type: row.required ? 'error' : 'success',
        size: 'small'
      }, { default: () => row.required ? '是' : '否' })
    }
  },
  {
    title: '描述',
    key: 'description',
    ellipsis: {
      tooltip: true
    }
  },
  {
    title: '示例',
    key: 'example',
    width: 120,
    ellipsis: {
      tooltip: true
    }
  }
]

const responseColumns = [
  {
    title: '状态码',
    key: 'status_code',
    width: 80,
    render(row) {
      const getStatusType = (code) => {
        if (code.startsWith('2')) return 'success'
        if (code.startsWith('4')) return 'warning'
        if (code.startsWith('5')) return 'error'
        return 'info'
      }
      return h('n-tag', {
        type: getStatusType(row.status_code),
        size: 'small'
      }, { default: () => row.status_code })
    }
  },
  {
    title: '内容类型',
    key: 'content_type',
    width: 150
  },
  {
    title: '描述',
    key: 'description',
    ellipsis: {
      tooltip: true
    }
  }
]

// 方法定义
const getMethodTagType = (method) => {
  const methodTypes = {
    'GET': 'success',
    'POST': 'info',
    'PUT': 'warning',
    'DELETE': 'error',
    'PATCH': 'default',
    'HEAD': 'default',
    'OPTIONS': 'default'
  }
  return methodTypes[method] || 'default'
}

const getParseStatusType = (status) => {
  const statusTypes = {
    'CREATED': 'info',
    'PROCESSING': 'warning',
    'COMPLETED': 'success',
    'FAILED': 'error',
    'CANCELLED': 'default'
  }
  return statusTypes[status] || 'default'
}

const getParseStatusText = (status) => {
  const statusTexts = {
    'CREATED': '已创建',
    'PROCESSING': '处理中',
    'COMPLETED': '已完成',
    'FAILED': '失败',
    'CANCELLED': '已取消'
  }
  return statusTexts[status] || status
}

// 参数分组相关方法
const groupedParameters = computed(() => {
  if (!selectedInterface.value || !selectedInterface.value.parameters) {
    return {}
  }

  const groups = {}
  selectedInterface.value.parameters.forEach(param => {
    const location = param.location || 'query'
    if (!groups[location]) {
      groups[location] = []
    }
    groups[location].push(param)
  })

  // 按照优先级排序
  const locationOrder = ['path', 'query', 'header', 'body', 'form', 'cookie']
  const sortedGroups = {}
  locationOrder.forEach(location => {
    if (groups[location]) {
      sortedGroups[location] = groups[location]
    }
  })

  // 添加其他未知的location
  Object.keys(groups).forEach(location => {
    if (!locationOrder.includes(location)) {
      sortedGroups[location] = groups[location]
    }
  })

  return sortedGroups
})

const getLocationDisplayName = (location) => {
  const locationNames = {
    'query': 'Query 参数',
    'path': 'Path 参数',
    'header': 'Header 参数',
    'body': 'Body 参数',
    'form': 'Form 参数',
    'cookie': 'Cookie 参数'
  }
  return locationNames[location] || location.toUpperCase() + ' 参数'
}

const getLocationTagType = (location) => {
  const locationTypes = {
    'query': 'success',
    'path': 'warning',
    'header': 'info',
    'body': 'error',
    'form': 'default',
    'cookie': 'primary'
  }
  return locationTypes[location] || 'default'
}

const getLocationTabTitle = (location, count) => {
  const displayName = getLocationDisplayName(location)
  return `${displayName} (${count})`
}

// 生命周期和事件处理
onMounted(() => {
  loadStatistics()
  loadDocuments()
  loadInterfaces()
  loadDocumentOptions()
})

// 监听文件列表变化
watch(fileList, (newList) => {
  console.log('文件列表变化:', newList)
}, { deep: true })

// 加载统计数据
const loadStatistics = async () => {
  try {
    const response = await api.getInterfaceStatistics()
    statistics.value = response.data
  } catch (error) {
    console.error('加载统计数据失败:', error)
  }
}

// 加载文档列表
const loadDocuments = async () => {
  documentLoading.value = true
  try {
    const params = {
      page: documentPagination.page,
      page_size: documentPagination.pageSize,
      search: documentSearch.search || undefined,
      doc_format: documentSearch.format || undefined
    }

    console.log('加载文档列表参数:', params)
    const response = await api.getApiDocuments(params)
    console.log('文档列表响应:', response)

    documentList.value = response.data
    documentPagination.itemCount = response.total

    console.log('文档分页信息:', {
      itemCount: documentPagination.itemCount,
      page: documentPagination.page,
      pageSize: documentPagination.pageSize,
      showSizePicker: documentPagination.showSizePicker
    })
  } catch (error) {
    message.error('加载文档列表失败')
    console.error('加载文档列表失败:', error)
  } finally {
    documentLoading.value = false
  }
}

// 加载接口列表
const loadInterfaces = async () => {
  interfaceLoading.value = true
  try {
    const params = {
      page: interfacePagination.page,
      page_size: interfacePagination.pageSize,
      search: interfaceSearch.search || undefined,
      method: interfaceSearch.method || undefined,
      doc_id: interfaceSearch.doc_id || undefined
    }

    console.log('加载接口列表参数:', params)
    const response = await api.getApiInterfaces(params)
    console.log('接口列表响应:', response)

    interfaceList.value = response.data
    interfacePagination.itemCount = response.total || 0

    console.log('接口分页信息:', {
      itemCount: interfacePagination.itemCount,
      page: interfacePagination.page,
      pageSize: interfacePagination.pageSize,
      showSizePicker: interfacePagination.showSizePicker,
      total: response.total,
      dataLength: response.data?.length
    })
  } catch (error) {
    message.error('加载接口列表失败')
    console.error('加载接口列表失败:', error)
  } finally {
    interfaceLoading.value = false
  }
}

// 加载文档选项
const loadDocumentOptions = async () => {
  try {
    const response = await api.getApiDocuments({ page: 1, page_size: 100 })
    documentOptions.value = response.data.map(doc => ({
      label: doc.file_name,
      value: doc.doc_id
    }))
  } catch (error) {
    console.error('加载文档选项失败:', error)
  }
}

// 搜索处理
const handleDocumentSearch = () => {
  documentPagination.page = 1
  loadDocuments()
}

const handleInterfaceSearch = () => {
  interfacePagination.page = 1
  loadInterfaces()
}

// 分页处理
const handleDocumentPageChange = (page) => {
  documentPagination.page = page
  loadDocuments()
}

const handleDocumentPageSizeChange = (pageSize) => {
  documentPagination.pageSize = pageSize
  documentPagination.page = 1
  loadDocuments()
}

const handleInterfacePageChange = (page) => {
  interfacePagination.page = page
  loadInterfaces()
}

const handleInterfacePageSizeChange = (pageSize) => {
  interfacePagination.pageSize = pageSize
  interfacePagination.page = 1
  loadInterfaces()
}

// 刷新数据
const refreshDocuments = () => {
  loadDocuments()
  loadStatistics()
}

const refreshInterfaces = () => {
  loadInterfaces()
  loadStatistics()
}

// 文件上传处理
const handleBeforeUpload = (data) => {
  const { file } = data
  console.log('文件上传前验证:', file)

  // 检查文件扩展名
  const fileName = file.name.toLowerCase()
  const allowedExtensions = ['.json', '.yaml', '.yml', '.pdf', '.md', '.txt']
  const hasValidExtension = allowedExtensions.some(ext => fileName.endsWith(ext))

  if (!hasValidExtension) {
    message.error(`不支持的文件类型。支持的格式: ${allowedExtensions.join(', ')}`)
    return false
  }

  if (file.size > 50 * 1024 * 1024) {
    message.error('文件大小不能超过50MB')
    return false
  }

  console.log('文件验证通过:', file.name, file.size)
  return true
}

const handleUpload = async () => {
  if (fileList.value.length === 0) {
    message.error('请选择要上传的文件')
    return
  }

  uploading.value = true
  uploadProgress.show = true
  uploadProgress.percentage = 0
  uploadProgress.status = 'active'
  uploadProgress.text = '正在上传文件...'

  try {
    // 获取文件对象，处理不同的文件结构
    const fileItem = fileList.value[0]
    const file = fileItem.file || fileItem

    console.log('准备上传的文件:', file)

    // 创建FormData，使用与document-workflow相同的格式
    const formData = new FormData()
    formData.append('file', file)
    formData.append('doc_format', 'auto')
    formData.append('auto_parse', 'true')  // 启用自动解析
    formData.append('config', JSON.stringify({
      extractSchemas: true,
      analyzeDependencies: true,
      generateExamples: true,
      isPdfDocument: file.name.toLowerCase().endsWith('.pdf'),
      // 接口管理特有配置
      enableDataPersistence: true,  // 启用数据持久化
      storeToDatabase: true         // 存储到数据库
    }))

    uploadProgress.percentage = 30
    uploadProgress.text = '文件上传中...'

    // 使用原生fetch避免响应拦截器问题
    let response
    try {
      console.log('使用原生fetch上传文档')
      const fetchResponse = await fetch('/api/v1/api-automation/upload-document', {
        method: 'POST',
        body: formData
      })

      if (!fetchResponse.ok) {
        throw new Error(`HTTP ${fetchResponse.status}: ${fetchResponse.statusText}`)
      }

      response = await fetchResponse.json()
      console.log('原生fetch上传响应:', response)

    } catch (error) {
      console.error('原生fetch上传失败:', error)
      throw error
    }

    console.log('最终处理的响应:', response)

    // 检查响应是否成功
    const isSuccess = response && (
      response.success === true ||
      response.success === 'true' ||
      (response.data && response.data.sessionId) // 如果有sessionId，也认为是成功的
    )

    if (isSuccess) {
      uploadProgress.percentage = 60
      uploadProgress.text = '文档上传成功，正在解析...'

      const sessionId = response.data.sessionId

      // 如果启用了自动解析，开始监控解析状态
      if (response.data.autoParse && response.data.status === 'parsing') {
        uploadProgress.percentage = 100
        uploadProgress.status = 'success'
        uploadProgress.text = '上传成功，开始解析...'

        message.success('文档上传成功，开始解析')

        // 关闭上传模态框
        setTimeout(() => {
          showUploadModal.value = false
          fileList.value = []
          uploadProgress.show = false
        }, 1000)

        // 启用全局进度提示
        globalProgress.show = true
        globalProgress.percentage = 10
        globalProgress.status = 'active'
        globalProgress.text = '正在解析文档结构...'
        globalProgress.sessionId = sessionId
        globalProgress.fileName = file.name

        console.log('开始轮询解析状态，sessionId:', sessionId)
        console.log('上传响应中的sessionId:', response.data.sessionId)

        // 轮询解析状态
        await pollParseStatusGlobal(sessionId)

      } else {
        uploadProgress.percentage = 100
        uploadProgress.status = 'success'
        uploadProgress.text = '文档上传成功！'

        message.success('文档上传成功，等待解析')

        // 延迟关闭模态框
        setTimeout(() => {
          showUploadModal.value = false
          fileList.value = []
          uploadProgress.show = false
        }, 1500)
      }

      // 刷新数据
      refreshDocuments()
      refreshInterfaces()

    } else {
      // 如果响应存在但success不为true，提取错误信息
      const errorMsg = response?.message || response?.msg || response?.error || '上传失败'
      throw new Error(errorMsg)
    }

  } catch (error) {
    console.error('上传失败:', error)
    uploadProgress.status = 'error'
    uploadProgress.text = '上传或解析失败'

    // 提取错误信息
    let errorMessage = '未知错误'

    // 优先从error对象中提取信息
    if (error.message && error.message !== 'OK' && error.message !== 'Network Error') {
      errorMessage = error.message
    } else if (error.response?.data?.message) {
      errorMessage = error.response.data.message
    } else if (error.response?.data?.msg) {
      errorMessage = error.response.data.msg
    } else if (error.response?.data?.detail) {
      errorMessage = error.response.data.detail
    } else if (error.error?.message) {
      errorMessage = error.error.message
    } else if (error.error?.msg) {
      errorMessage = error.error.msg
    } else if (typeof error === 'string') {
      errorMessage = error
    }

    console.error('上传错误详情:', {
      error,
      extractedMessage: errorMessage,
      errorType: typeof error,
      errorKeys: Object.keys(error || {})
    })

    message.error('上传失败: ' + errorMessage)

    // 延迟隐藏进度条
    setTimeout(() => {
      uploadProgress.show = false
    }, 3000)
  } finally {
    uploading.value = false
  }
}

// 轮询解析状态 - 与document-workflow保持一致
const pollParseStatus = async (sessionId) => {
  const maxAttempts = 60 // 最多轮询60次，每次2秒，总共2分钟
  let attempts = 0

  return new Promise((resolve, reject) => {
    const checkStatus = async () => {
      try {
        attempts++
        console.log(`轮询解析状态 (${attempts}/${maxAttempts}):`, sessionId)

        const response = await api.getParseStatus(sessionId)
        console.log('解析状态响应:', response)

        if (response.success && response.data) {
          const status = response.data.status
          const progress = response.data.progress || 0

          // 更新进度
          uploadProgress.percentage = Math.max(80, Math.min(95, 80 + (progress * 0.15)))

          if (status === 'completed') {
            uploadProgress.text = '解析完成，正在存储数据...'
            resolve(response.data)
          } else if (status === 'failed' || status === 'error') {
            reject(new Error(response.data.message || '解析失败'))
          } else if (attempts >= maxAttempts) {
            reject(new Error('解析超时，请稍后查看结果'))
          } else {
            // 继续轮询
            uploadProgress.text = `解析中... (${Math.round(progress)}%)`
            setTimeout(checkStatus, 2000)
          }
        } else {
          if (attempts >= maxAttempts) {
            reject(new Error('解析状态查询失败'))
          } else {
            setTimeout(checkStatus, 2000)
          }
        }
      } catch (error) {
        console.error('轮询解析状态失败:', error)
        if (attempts >= maxAttempts) {
          reject(error)
        } else {
          setTimeout(checkStatus, 2000)
        }
      }
    }

    checkStatus()
  })
}

// 全局进度轮询解析状态
const pollParseStatusGlobal = async (sessionId) => {
  const maxAttempts = 60 // 最多轮询60次，每次2秒，总共2分钟
  let attempts = 0

  return new Promise((resolve, reject) => {
    const checkStatus = async () => {
      try {
        attempts++
        console.log(`全局轮询解析状态 (${attempts}/${maxAttempts}):`, sessionId)

        // 使用原生fetch查询解析状态，避免响应拦截器问题
        let response
        try {
          console.log('使用原生fetch查询解析状态')
          const fetchResponse = await fetch(`/api/v1/api-automation/parse-status/${sessionId}`)

          if (!fetchResponse.ok) {
            throw new Error(`HTTP ${fetchResponse.status}: ${fetchResponse.statusText}`)
          }

          response = await fetchResponse.json()
          console.log('原生fetch解析状态响应:', response)

        } catch (error) {
          console.error('原生fetch查询状态失败:', error)
          throw error
        }

        console.log('查询的sessionId:', sessionId)

        if (response && response.success === true && response.data) {
          const status = response.data.status
          const progress = response.data.progress || 0

          // 更新全局进度
          globalProgress.percentage = Math.max(10, Math.min(95, 10 + (progress * 0.85)))

          if (status === 'completed') {
            globalProgress.percentage = 100
            globalProgress.status = 'success'
            globalProgress.text = '解析完成，数据已存储到数据库'

            message.success('文档解析完成！')

            console.log('解析完成，停止轮询')

            // 延迟隐藏进度条并刷新数据
            setTimeout(() => {
              globalProgress.show = false
              refreshDocuments()
              refreshInterfaces()
            }, 2000)

            resolve(response.data)
            return // 重要：解析完成后立即返回，停止轮询
          } else if (status === 'failed' || status === 'error') {
            globalProgress.status = 'error'
            globalProgress.text = '解析失败: ' + (response.data.error || response.message || '未知错误')

            message.error('文档解析失败: ' + (response.data.error || response.message || '未知错误'))

            console.log('解析失败，停止轮询')

            setTimeout(() => {
              globalProgress.show = false
            }, 3000)

            reject(new Error(response.data.error || response.message || '解析失败'))
            return // 重要：解析失败后立即返回，停止轮询
          } else if (attempts >= maxAttempts) {
            globalProgress.status = 'error'
            globalProgress.text = '解析超时，请稍后查看结果'

            message.warning('解析超时，请稍后查看结果')

            console.log('解析超时，停止轮询')

            setTimeout(() => {
              globalProgress.show = false
            }, 3000)

            reject(new Error('解析超时，请稍后查看结果'))
            return // 重要：超时后立即返回，停止轮询
          } else {
            // 继续轮询
            globalProgress.text = `正在解析文档... (${Math.round(progress)}%)`
            console.log(`继续轮询 (${attempts}/${maxAttempts}), 进度: ${Math.round(progress)}%`)
            setTimeout(checkStatus, 2000)
          }
        } else {
          // 处理响应失败的情况
          console.log('解析状态查询失败:', response)

          if (response && response.success === false) {
            // 后端明确返回失败
            globalProgress.status = 'error'
            globalProgress.text = response.message || '解析状态查询失败'

            message.error(response.message || '解析状态查询失败')

            console.log('后端返回失败，停止轮询:', response.message)

            setTimeout(() => {
              globalProgress.show = false
            }, 3000)

            reject(new Error(response.message || '解析状态查询失败'))
            return // 重要：后端返回失败后立即返回，停止轮询
          } else if (attempts >= maxAttempts) {
            globalProgress.status = 'error'
            globalProgress.text = '解析状态查询超时'

            setTimeout(() => {
              globalProgress.show = false
            }, 3000)

            reject(new Error('解析状态查询超时'))
          } else {
            setTimeout(checkStatus, 2000)
          }
        }
      } catch (error) {
        console.error('全局轮询解析状态失败:', error)

        // 提取错误信息
        let errorMessage = '解析状态查询失败'
        if (error.message && error.message !== 'OK') {
          errorMessage = error.message
        } else if (error.error?.message) {
          errorMessage = error.error.message
        }

        if (attempts >= maxAttempts) {
          globalProgress.status = 'error'
          globalProgress.text = errorMessage

          message.error(errorMessage)

          setTimeout(() => {
            globalProgress.show = false
          }, 3000)

          reject(error)
        } else {
          // 继续重试，但显示当前错误
          globalProgress.text = `查询状态中... (${errorMessage})`
          setTimeout(checkStatus, 2000)
        }
      }
    }

    checkStatus()
  })
}

const handleFileChange = ({ file, fileList: newFileList, event }) => {
  console.log('文件变化:', file, newFileList)
  fileList.value = newFileList
}

const handleFileRemove = ({ file, fileList: newFileList }) => {
  console.log('文件移除:', file, newFileList)
  fileList.value = newFileList
  return true
}

// 取消上传
const handleCancelUpload = () => {
  showUploadModal.value = false
  fileList.value = []
  uploadProgress.show = false
  uploadProgress.percentage = 0
  uploadProgress.status = 'active'
  uploadProgress.text = ''
  uploading.value = false
}

// 查看详情
const viewDocumentDetail = async (document) => {
  try {
    const response = await api.getApiDocumentDetail(document.doc_id)
    // 在模态框中显示文档详情
    selectedInterface.value = {
      ...response.data,
      isDocument: true  // 标记这是文档详情而不是接口详情
    }
    showDetailModal.value = true
  } catch (error) {
    message.error('获取文档详情失败')
    console.error('获取文档详情失败:', error)
  }
}

const viewInterfaceDetail = async (interfaceItem) => {
  try {
    const response = await api.getApiInterfaceDetail(interfaceItem.interface_id)
    selectedInterface.value = response.data
    showDetailModal.value = true
  } catch (error) {
    message.error('获取接口详情失败')
  }
}

// 跳转到接口脚本管理页面
const viewInterfaceScripts = (interfaceItem) => {
  router.push({
    name: '接口脚本管理',
    params: {
      interfaceId: interfaceItem.interface_id
    }
  })
}

// 删除文档
const deleteDocument = (document) => {
  dialog.warning({
    title: '确认删除',
    content: `确定要删除文档 "${document.file_name}" 吗？此操作不可恢复。`,
    positiveText: '确定',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await api.deleteApiDocument(document.doc_id)
        message.success('删除成功')
        refreshDocuments()
        refreshInterfaces()
      } catch (error) {
        message.error('删除失败')
      }
    }
  })
}

// 生成脚本
const generateScript = async (interfaceItem) => {
  try {
    scriptGenerationLoading.value = interfaceItem.interface_id

    const response = await api.generateInterfaceScript(interfaceItem.interface_id)
    console.log('脚本生成响应:', response)

    // 检查响应数据结构
    const responseData = response.data || response

    if (responseData.success) {
      message.success('脚本生成任务已启动')

      // 设置当前会话ID以显示日志
      currentSessionId.value = responseData.session_id

      // 开始轮询状态
      if (responseData.session_id) {
        pollScriptGenerationStatus(responseData.session_id, interfaceItem.interface_id)
      }
    } else {
      message.error(responseData.message || response.msg || '脚本生成失败')
      scriptGenerationLoading.value = null
    }
  } catch (error) {
    console.error('生成脚本失败:', error)
    message.error('生成脚本失败: ' + (error.message || '未知错误'))
    scriptGenerationLoading.value = null
  }
}

// 轮询脚本生成状态
const pollScriptGenerationStatus = async (sessionId, interfaceId) => {
  const maxAttempts = 30 // 最多轮询30次（约5分钟）
  let attempts = 0

  const poll = async () => {
    try {
      attempts++
      const statusResponse = await api.getScriptGenerationStatus(sessionId)
      console.log('状态轮询响应:', statusResponse)

      // 检查响应数据结构
      const responseData = statusResponse.data || statusResponse

      if (responseData.success) {
        const status = responseData.status

        if (status === 'completed') {
          message.success('脚本生成完成！')
          scriptGenerationLoading.value = null
          // 保持日志显示一段时间后清除
          setTimeout(() => {
            currentSessionId.value = ''
          }, 10000) // 10秒后清除日志显示
          return
        } else if (status === 'failed') {
          message.error('脚本生成失败：' + (responseData.error_message || responseData.message || statusResponse.msg || '未知错误'))
          scriptGenerationLoading.value = null
          // 保持日志显示以查看错误信息
          setTimeout(() => {
            currentSessionId.value = ''
          }, 30000) // 30秒后清除日志显示
          return
        } else if (status === 'processing' && attempts < maxAttempts) {
          // 继续轮询
          setTimeout(poll, 10000) // 10秒后再次查询
          return
        }
      }

      // 超时或其他情况
      if (attempts >= maxAttempts) {
        message.warning('脚本生成超时，请稍后手动查看结果')
      } else {
        message.error('获取脚本生成状态失败')
      }

      scriptGenerationLoading.value = null

    } catch (error) {
      console.error('查询脚本生成状态失败:', error)
      if (attempts >= maxAttempts) {
        message.warning('脚本生成状态查询超时，请稍后手动查看结果')
        scriptGenerationLoading.value = null
      } else {
        // 继续轮询
        setTimeout(poll, 10000)
      }
    }
  }

  // 开始轮询
  setTimeout(poll, 5000) // 5秒后开始第一次查询
}
</script>

<style scoped>
.interface-management {
  padding: 24px;
  background: #f5f5f5;
  min-height: 100vh;
}

.page-header {
  background: white;
  border-radius: 8px;
  padding: 24px;
  margin-bottom: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.title-section {
  flex: 1;
}

.page-title {
  display: flex;
  align-items: center;
  margin: 0 0 8px 0;
  font-size: 24px;
  font-weight: 600;
  color: #333;
}

.title-icon {
  margin-right: 12px;
  font-size: 28px;
  color: #2080f0;
}

.page-description {
  margin: 0;
  color: #666;
  font-size: 14px;
}

.global-progress {
  margin-bottom: 16px;
}

.progress-content {
  display: flex;
  align-items: center;
  gap: 16px;
}

.progress-info {
  flex: 1;
}

.progress-title {
  display: flex;
  align-items: center;
  font-size: 16px;
  font-weight: 600;
  color: #333;
  margin-bottom: 4px;
}

.progress-icon {
  margin-right: 8px;
  font-size: 20px;
  color: #2080f0;
}

.progress-text {
  font-size: 14px;
  color: #666;
}

.progress-bar {
  width: 300px;
}

.stats-cards {
  margin-bottom: 16px;
}

.stat-card {
  height: 100px;
}

.stat-content {
  display: flex;
  align-items: center;
  height: 100%;
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 16px;
  font-size: 24px;
  color: white;
}

.stat-icon.documents {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.stat-icon.interfaces {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
}

.stat-icon.methods {
  background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
}

.stat-icon.formats {
  background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 24px;
  font-weight: 600;
  color: #333;
  line-height: 1;
}

.stat-label {
  font-size: 14px;
  color: #666;
  margin-top: 4px;
}

.main-content {
  background: white;
  border-radius: 8px;
  padding: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.tab-content {
  margin-top: 16px;
}

.search-section {
  margin-bottom: 16px;
  padding: 16px;
  background: #fafafa;
  border-radius: 6px;
}

.modal-header {
  display: flex;
  align-items: center;
}

.modal-icon {
  margin-right: 8px;
  font-size: 20px;
  color: #2080f0;
}

.upload-content {
  padding: 16px 0;
}

.upload-area {
  text-align: center;
  padding: 40px 20px;
}

.upload-icon {
  font-size: 48px;
  color: #d9d9d9;
  margin-bottom: 16px;
}

.upload-text {
  color: #666;
}

.upload-hint {
  margin: 0 0 8px 0;
  font-size: 16px;
}

.upload-desc {
  margin: 0;
  font-size: 14px;
  color: #999;
}

.upload-progress {
  margin-top: 16px;
}

.progress-text {
  margin: 8px 0 0 0;
  text-align: center;
  color: #666;
  font-size: 14px;
}

.interface-detail {
  max-height: 70vh;
  overflow-y: auto;
}

.detail-section {
  margin-top: 24px;
}

.detail-section h3 {
  margin: 0 0 16px 0;
  font-size: 16px;
  font-weight: 600;
  color: #333;
}

/* 参数分组样式 */
.parameter-group {
  margin-top: 16px;
}

.parameter-group-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  padding: 12px 16px;
  background: #f8f9fa;
  border-radius: 6px;
  border-left: 4px solid #2080f0;
}

.parameter-count {
  color: #666;
  font-size: 14px;
}

.empty-state {
  text-align: center;
  padding: 40px 20px;
}

/* Body参数特殊样式 */
.body-parameter {
  margin-bottom: 16px;
}

.body-param-card {
  border: 1px solid #e0e0e6;
  border-radius: 6px;
}

.body-param-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.param-name {
  font-weight: 600;
  color: #333;
  font-size: 14px;
}

.body-param-content {
  padding: 0;
}

.param-description,
.param-schema,
.param-example,
.param-constraints {
  margin-bottom: 12px;
}

.param-description:last-child,
.param-schema:last-child,
.param-example:last-child,
.param-constraints:last-child {
  margin-bottom: 0;
}

.constraints-list {
  margin-top: 8px;
}

/* 标签页样式优化 */
:deep(.n-tabs .n-tab-pane) {
  padding-top: 16px;
}

:deep(.n-tabs .n-tabs-tab) {
  font-weight: 500;
}

:deep(.n-tabs .n-tabs-tab--active) {
  font-weight: 600;
}

/* 表格操作按钮样式优化 */
:deep(.n-data-table .n-button) {
  border-radius: 6px;
  font-weight: 500;
  transition: all 0.2s ease;
  min-width: 70px;
  height: 28px;
  font-size: 12px;
}

:deep(.n-data-table .n-button:hover) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

:deep(.n-data-table .n-button--primary-type) {
  background: linear-gradient(135deg, #2080f0 0%, #1c6dd0 100%);
  border: none;
  color: white;
}

:deep(.n-data-table .n-button--success-type) {
  background: linear-gradient(135deg, #18a058 0%, #16924d 100%);
  border: none;
  color: white;
}

:deep(.n-data-table .n-button--error-type) {
  background: linear-gradient(135deg, #d03050 0%, #b82a47 100%);
  border: none;
  color: white;
}

:deep(.n-data-table .n-button--primary-type:hover) {
  background: linear-gradient(135deg, #1c6dd0 0%, #1a5fb8 100%);
}

:deep(.n-data-table .n-button--success-type:hover) {
  background: linear-gradient(135deg, #16924d 0%, #148043 100%);
}

:deep(.n-data-table .n-button--error-type:hover) {
  background: linear-gradient(135deg, #b82a47 0%, #a0253e 100%);
}

/* 按钮图标样式 */
:deep(.n-data-table .n-button .n-button__icon) {
  margin-right: 4px;
}

/* 会话日志区域样式 */
.session-logs-section {
  margin-top: 24px;
  padding: 16px;
  background: var(--card-color);
  border-radius: 8px;
  border: 1px solid var(--border-color);
}

/* 操作列居中对齐 */
:deep(.n-data-table td[data-col-key="actions"]) {
  text-align: center;
}

/* 确保分页插件显示 */
:deep(.n-data-table .n-data-table__pagination) {
  display: flex !important;
  justify-content: flex-end;
  margin-top: 16px;
  padding: 16px 0;
}

/* 分页插件样式优化 - 强制显示 */
:deep(.n-pagination) {
  display: flex !important;
  align-items: center;
  gap: 8px;
  visibility: visible !important;
  opacity: 1 !important;
  height: auto !important;
  overflow: visible !important;
}

/* 强制显示数据表格的分页区域 */
:deep(.n-data-table .n-data-table__pagination) {
  display: block !important;
  visibility: visible !important;
  opacity: 1 !important;
  height: auto !important;
  margin-top: 16px !important;
  padding: 16px 0 !important;
}

/* 接口管理标签页特殊样式 */
.tab-content {
  min-height: 500px;
  display: flex;
  flex-direction: column;
}

/* 确保数据表格容器有足够的空间显示分页 */
:deep(.n-data-table) {
  display: flex;
  flex-direction: column;
}

:deep(.n-data-table .n-data-table-wrapper) {
  flex: 1;
  overflow: auto;
}

/* 分页组件样式优化 */
:deep(.n-data-table .n-data-table__pagination) {
  flex-shrink: 0;
  margin-top: 16px;
  padding: 16px 0;
  border-top: 1px solid #f0f0f0;
  background: #fafafa;
}


</style>
