<template>
  <div class="analysis-detail">
    <!-- 分析概览 -->
    <n-card title="分析概览" class="mb-6">
      <div v-if="analysisResult">
        <div class="grid grid-cols-1 md:grid-cols-5 gap-4 mb-6">
          <n-statistic label="总体评分" :value="analysisResult.overallScore" suffix="/100" />
          <n-statistic label="安全评分" :value="analysisResult.securityScore" suffix="/100" />
          <n-statistic label="复杂度评分" :value="analysisResult.complexityScore" suffix="/100" />
          <n-statistic label="可维护性" :value="analysisResult.maintainabilityScore" suffix="/100" />
          <n-statistic label="接口数量" :value="analysisResult.totalEndpoints" />
        </div>

        <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
          <n-statistic label="GET接口" :value="analysisResult.getCount" />
          <n-statistic label="POST接口" :value="analysisResult.postCount" />
          <n-statistic label="PUT接口" :value="analysisResult.putCount" />
          <n-statistic label="DELETE接口" :value="analysisResult.deleteCount" />
        </div>
      </div>
    </n-card>

    <!-- 详细分析 -->
    <n-card title="详细分析">
      <n-tabs type="line" v-model:value="activeTab">
        <n-tab-pane name="categories" tab="接口分类">
          <div v-if="analysisResult?.categories">
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <n-card v-for="category in analysisResult.categories" :key="category.name" size="small">
                <template #header>
                  <div class="flex items-center justify-between">
                    <span>{{ category.name }}</span>
                    <n-tag :type="getCategoryType(category.level)">{{ category.level }}</n-tag>
                  </div>
                </template>
                <div>
                  <p class="text-sm text-gray-600 mb-2">{{ category.description }}</p>
                  <div class="text-sm">
                    <div>接口数量: {{ category.endpoints?.length || 0 }}</div>
                    <div>复杂度: {{ category.complexity || 'N/A' }}</div>
                  </div>
                </div>
              </n-card>
            </div>
          </div>
        </n-tab-pane>

        <n-tab-pane name="dependencies" tab="依赖关系">
          <div v-if="analysisResult?.dependencies">
            <div class="mb-4">
              <n-alert type="info" title="依赖关系分析">
                发现 {{ analysisResult.dependencies.length }} 个依赖关系
              </n-alert>
            </div>
            
            <n-data-table
              :columns="dependencyColumns"
              :data="analysisResult.dependencies"
              :pagination="{ pageSize: 20 }"
            />
          </div>
        </n-tab-pane>

        <n-tab-pane name="security" tab="安全评估">
          <div v-if="analysisResult?.securityAssessment">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <h4 class="font-semibold mb-3">安全风险</h4>
                <n-list v-if="analysisResult.securityAssessment.risks">
                  <n-list-item v-for="risk in analysisResult.securityAssessment.risks" :key="risk.id">
                    <div class="flex items-start justify-between w-full">
                      <div class="flex-1">
                        <div class="font-medium">{{ risk.title }}</div>
                        <div class="text-sm text-gray-600">{{ risk.description }}</div>
                      </div>
                      <n-tag :type="getRiskType(risk.level)">{{ risk.level }}</n-tag>
                    </div>
                  </n-list-item>
                </n-list>
              </div>
              
              <div>
                <h4 class="font-semibold mb-3">安全建议</h4>
                <n-list v-if="analysisResult.securityAssessment.recommendations">
                  <n-list-item v-for="rec in analysisResult.securityAssessment.recommendations" :key="rec.id">
                    <div>
                      <div class="font-medium">{{ rec.title }}</div>
                      <div class="text-sm text-gray-600">{{ rec.description }}</div>
                    </div>
                  </n-list-item>
                </n-list>
              </div>
            </div>
          </div>
        </n-tab-pane>

        <n-tab-pane name="performance" tab="性能分析">
          <div v-if="analysisResult?.performanceAnalysis">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <h4 class="font-semibold mb-3">性能指标</h4>
                <div class="space-y-3">
                  <div v-for="metric in performanceMetrics" :key="metric.name" class="flex justify-between">
                    <span>{{ metric.label }}</span>
                    <span class="font-medium">{{ metric.value }}</span>
                  </div>
                </div>
              </div>
              
              <div>
                <h4 class="font-semibold mb-3">优化建议</h4>
                <n-list v-if="analysisResult.performanceAnalysis.suggestions">
                  <n-list-item v-for="suggestion in analysisResult.performanceAnalysis.suggestions" :key="suggestion.id">
                    <div>
                      <div class="font-medium">{{ suggestion.title }}</div>
                      <div class="text-sm text-gray-600">{{ suggestion.description }}</div>
                    </div>
                  </n-list-item>
                </n-list>
              </div>
            </div>
          </div>
        </n-tab-pane>

        <n-tab-pane name="endpoints" tab="接口详情">
          <n-data-table
            :columns="endpointColumns"
            :data="endpoints"
            :pagination="{ pageSize: 20 }"
            :loading="loadingEndpoints"
          />
        </n-tab-pane>
      </n-tabs>
    </n-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { NTag, useMessage } from 'naive-ui'
import api from '@/api'

const route = useRoute()
const message = useMessage()

// 数据
const analysisResult = ref(null)
const endpoints = ref([])
const loading = ref(false)
const loadingEndpoints = ref(false)
const activeTab = ref('categories')

// 计算属性
const performanceMetrics = computed(() => {
  if (!analysisResult.value?.performanceAnalysis) return []
  
  const analysis = analysisResult.value.performanceAnalysis
  return [
    { name: 'avgComplexity', label: '平均复杂度', value: analysis.avgComplexity || 'N/A' },
    { name: 'maxComplexity', label: '最大复杂度', value: analysis.maxComplexity || 'N/A' },
    { name: 'authRequiredRatio', label: '需认证接口比例', value: `${analysis.authRequiredRatio || 0}%` },
    { name: 'deprecatedRatio', label: '废弃接口比例', value: `${analysis.deprecatedRatio || 0}%` }
  ]
})

// 表格列定义
const dependencyColumns = [
  { title: '源接口', key: 'sourceEndpoint', width: 200 },
  { title: '目标接口', key: 'targetEndpoint', width: 200 },
  { title: '依赖类型', key: 'dependencyType', width: 120 },
  { title: '依赖强度', key: 'strength', width: 100, render: (row) => `${row.strength || 0}%` },
  { title: '是否关键', key: 'isCritical', width: 100, render: (row) => row.isCritical ? '是' : '否' },
  { title: '描述', key: 'description', ellipsis: true }
]

const endpointColumns = [
  { title: '方法', key: 'method', width: 80 },
  { title: '路径', key: 'path', width: 250 },
  { title: '摘要', key: 'summary', ellipsis: true },
  { 
    title: '复杂度', 
    key: 'complexityScore', 
    width: 100,
    render: (row) => {
      const score = row.complexityScore || 0
      const type = score > 7 ? 'error' : score > 4 ? 'warning' : 'success'
      return h(NTag, { type }, { default: () => score.toFixed(1) })
    }
  },
  { 
    title: '安全等级', 
    key: 'securityLevel', 
    width: 100,
    render: (row) => {
      const typeMap = {
        'HIGH': 'error',
        'MEDIUM': 'warning', 
        'LOW': 'success'
      }
      return h(NTag, { type: typeMap[row.securityLevel] || 'default' }, { default: () => row.securityLevel })
    }
  },
  { title: '认证', key: 'authRequired', width: 80, render: (row) => row.authRequired ? '是' : '否' }
]

// 方法
const loadAnalysisResult = async () => {
  loading.value = true
  try {
    const analysisId = route.query.analysisId
    if (!analysisId) {
      message.error('缺少分析ID参数')
      return
    }

    const response = await api.getAnalysisResult({ analysisId })
    analysisResult.value = response.data
    
    // 加载接口详情
    loadEndpoints()
  } catch (error) {
    message.error('加载分析结果失败')
  } finally {
    loading.value = false
  }
}

const loadEndpoints = async () => {
  loadingEndpoints.value = true
  try {
    const response = await api.getApiEndpoints({ 
      documentId: analysisResult.value.documentId 
    })
    endpoints.value = response.data
  } catch (error) {
    message.error('加载接口详情失败')
  } finally {
    loadingEndpoints.value = false
  }
}

const getCategoryType = (level) => {
  const typeMap = {
    'HIGH': 'error',
    'MEDIUM': 'warning',
    'LOW': 'success'
  }
  return typeMap[level] || 'default'
}

const getRiskType = (level) => {
  const typeMap = {
    'CRITICAL': 'error',
    'HIGH': 'error',
    'MEDIUM': 'warning',
    'LOW': 'info'
  }
  return typeMap[level] || 'default'
}

onMounted(() => {
  loadAnalysisResult()
})
</script>

<style scoped>
.analysis-detail {
  padding: 20px;
}
</style>
