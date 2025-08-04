<template>
  <div class="api-automation-dashboard">
    <!-- 统计卡片 -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      <n-card class="stat-card">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-gray-500 text-sm">已解析文档</p>
            <p class="text-2xl font-bold text-blue-600">{{ stats.parsedDocs }}</p>
          </div>
          <n-icon size="40" color="#3b82f6">
            <Icon icon="mdi:file-document-outline" />
          </n-icon>
        </div>
      </n-card>
      
      <n-card class="stat-card">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-gray-500 text-sm">分析接口</p>
            <p class="text-2xl font-bold text-green-600">{{ stats.analyzedApis }}</p>
          </div>
          <n-icon size="40" color="#10b981">
            <Icon icon="mdi:api" />
          </n-icon>
        </div>
      </n-card>
      
      <n-card class="stat-card">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-gray-500 text-sm">生成测试</p>
            <p class="text-2xl font-bold text-purple-600">{{ stats.generatedTests }}</p>
          </div>
          <n-icon size="40" color="#8b5cf6">
            <Icon icon="mdi:code-braces" />
          </n-icon>
        </div>
      </n-card>
      
      <n-card class="stat-card">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-gray-500 text-sm">执行次数</p>
            <p class="text-2xl font-bold text-orange-600">{{ stats.executions }}</p>
          </div>
          <n-icon size="40" color="#f59e0b">
            <Icon icon="mdi:play-circle-outline" />
          </n-icon>
        </div>
      </n-card>
    </div>

    <!-- 业务流程 -->
    <n-card title="业务流程" class="mb-6">
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div
          v-for="workflow in workflows"
          :key="workflow.id"
          class="workflow-item p-4 border border-gray-200 rounded-lg hover:border-blue-300 hover:shadow-md transition-all cursor-pointer"
          @click="navigateToWorkflow(workflow)"
        >
          <div class="flex items-center space-x-3">
            <div class="workflow-icon">
              <n-icon size="24" :color="workflow.color">
                <component :is="workflow.icon" />
              </n-icon>
            </div>
            <div class="flex-1">
              <h3 class="font-semibold text-gray-800">{{ workflow.title }}</h3>
              <p class="text-sm text-gray-600">{{ workflow.description }}</p>
            </div>
            <div class="workflow-arrow">
              <n-icon size="16" color="#9ca3af">
                <Icon icon="mdi:chevron-right" />
              </n-icon>
            </div>
          </div>
        </div>
      </div>
    </n-card>

    <!-- 快速操作 -->
    <n-card title="快速操作" class="mb-6">
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <n-button
          type="primary"
          size="large"
          block
          @click="$router.push('/api-automation/document-workflow')"
        >
          <template #icon>
            <n-icon><Icon icon="mdi:upload" /></n-icon>
          </template>
          上传文档
        </n-button>

        <n-button
          type="info"
          size="large"
          block
          @click="$router.push('/api-automation/script-management')"
        >
          <template #icon>
            <n-icon><Icon icon="mdi:script-text" /></n-icon>
          </template>
          管理脚本
        </n-button>

        <n-button
          type="success"
          size="large"
          block
          @click="$router.push('/api-automation/test-execution')"
        >
          <template #icon>
            <n-icon><Icon icon="mdi:play" /></n-icon>
          </template>
          执行测试
        </n-button>

        <n-button
          type="warning"
          size="large"
          block
          @click="$router.push('/api-automation/scheduled-tasks')"
        >
          <template #icon>
            <n-icon><Icon icon="mdi:clock-outline" /></n-icon>
          </template>
          定时任务
        </n-button>
      </div>
    </n-card>

    <!-- 最近活动和系统状态 -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- 最近活动 -->
      <n-card title="最近活动">
        <n-timeline>
          <n-timeline-item
            v-for="activity in recentActivities"
            :key="activity.id"
            :type="activity.type"
            :title="activity.title"
            :content="activity.description"
            :time="activity.time"
          />
        </n-timeline>
      </n-card>

      <!-- 系统状态 -->
      <n-card title="系统状态">
        <div class="space-y-4">
          <div v-for="agent in agentStatus" :key="agent.name" class="flex items-center justify-between">
            <div class="flex items-center space-x-2">
              <n-icon :color="agent.status === 'online' ? '#10b981' : '#ef4444'">
                <Icon icon="mdi:circle" />
              </n-icon>
              <span>{{ agent.name }}</span>
            </div>
            <n-tag :type="agent.status === 'online' ? 'success' : 'error'">
              {{ agent.status === 'online' ? '在线' : '离线' }}
            </n-tag>
          </div>
        </div>
      </n-card>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Icon } from '@iconify/vue'
import { useRouter } from 'vue-router'
import api from '@/api'

const router = useRouter()

// 统计数据
const stats = ref({
  parsedDocs: 0,
  analyzedApis: 0,
  generatedTests: 0,
  executions: 0
})

// 业务流程配置
const workflows = [
  {
    id: 'interface-management',
    title: '接口管理',
    description: '管理API接口信息，上传文档自动解析接口并存储到数据库',
    icon: 'mdi:api',
    color: '#2080f0',
    route: '/api-automation/interface-management'
  },
  {
    id: 'document-workflow',
    title: '文档工作流',
    description: '上传API文档，智能解析接口结构，生成测试脚本',
    icon: 'mdi:file-upload',
    color: '#18a058',
    route: '/api-automation/document-workflow'
  },
  {
    id: 'script-management',
    title: '测试脚本管理',
    description: '查看、编辑和管理生成的测试脚本',
    icon: 'mdi:script-text',
    color: '#f0a020',
    route: '/api-automation/script-management'
  },
  {
    id: 'test-execution',
    title: '测试执行与报告',
    description: '执行测试脚本，查看执行结果和测试报告',
    icon: 'mdi:play-circle',
    color: '#d03050',
    route: '/api-automation/test-execution'
  },
  {
    id: 'scheduled-tasks',
    title: '定时任务管理',
    description: '配置和管理定时执行的测试任务',
    icon: 'mdi:clock-outline',
    color: '#722ed1',
    route: '/api-automation/scheduled-tasks'
  }
]

// 最近活动
const recentActivities = ref([
  {
    id: 1,
    type: 'success',
    title: '文档解析完成',
    description: '成功解析 user-api.yaml 文档，提取了 15 个接口',
    time: '2分钟前'
  },
  {
    id: 2,
    type: 'info',
    title: '测试生成中',
    description: '正在为订单管理模块生成测试脚本...',
    time: '5分钟前'
  },
  {
    id: 3,
    type: 'warning',
    title: '测试执行失败',
    description: '用户登录接口测试失败，请检查环境配置',
    time: '10分钟前'
  }
])

// 智能体状态
const agentStatus = ref([
  { name: 'API文档解析智能体', status: 'online' },
  { name: 'API分析智能体', status: 'online' },
  { name: '测试生成智能体', status: 'online' },
  { name: '测试执行智能体', status: 'online' },
  { name: '日志记录智能体', status: 'online' }
])

// 方法
const navigateToWorkflow = (workflow) => {
  router.push(workflow.route)
}

// 加载统计数据
const loadStats = async () => {
  try {
    // 这里调用实际的API获取统计数据
    // const response = await api.getAgentMetrics()
    // stats.value = response.data

    // 模拟数据
    stats.value = {
      parsedDocs: 23,
      analyzedApis: 156,
      generatedTests: 89,
      executions: 234
    }
  } catch (error) {
    console.error('加载统计数据失败:', error)
  }
}

onMounted(() => {
  loadStats()
})
</script>

<style scoped>
.api-automation-dashboard {
  padding: 20px;
}

.stat-card {
  transition: transform 0.2s ease-in-out;
}

.stat-card:hover {
  transform: translateY(-2px);
}

.workflow-item:hover {
  transform: translateY(-2px);
}
</style>
