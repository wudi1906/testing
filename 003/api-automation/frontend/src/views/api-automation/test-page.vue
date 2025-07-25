<template>
  <div class="test-page">
    <n-card title="测试页面">
      <p>这是一个测试页面，用于验证修复是否成功。</p>
      
      <div class="mt-4">
        <h3>图标测试</h3>
        <div class="flex space-x-4 mt-2">
          <n-button type="primary">
            <template #icon>
              <n-icon><Icon icon="mdi:check" /></n-icon>
            </template>
            成功图标
          </n-button>
          
          <n-button type="info">
            <template #icon>
              <n-icon><Icon icon="mdi:information" /></n-icon>
            </template>
            信息图标
          </n-button>
          
          <n-button type="warning">
            <template #icon>
              <n-icon><Icon icon="mdi:alert" /></n-icon>
            </template>
            警告图标
          </n-button>
        </div>
      </div>
      
      <div class="mt-4">
        <h3>工具函数测试</h3>
        <div class="space-y-2 mt-2">
          <p>当前时间: {{ formatTime(new Date()) }}</p>
          <p>文件大小: {{ formatFileSize(1024 * 1024 * 5.5) }}</p>
          <p>格式化数字: {{ formatNumber(123456) }}</p>
          <p>百分比: {{ formatPercent(85.67) }}</p>
        </div>
      </div>
      
      <div class="mt-4">
        <h3>API测试</h3>
        <n-button @click="testApi" :loading="loading">测试API调用</n-button>
        <div v-if="apiResult" class="mt-2">
          <n-alert type="success" title="API调用结果">
            {{ apiResult }}
          </n-alert>
        </div>
      </div>
    </n-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { Icon } from '@iconify/vue'
import { useMessage } from 'naive-ui'
import api from '@/api'
import { formatTime, formatFileSize, formatNumber, formatPercent } from '@/utils'

const message = useMessage()

// 数据
const loading = ref(false)
const apiResult = ref('')

// 方法
const testApi = async () => {
  loading.value = true
  try {
    // 测试一个简单的API调用
    const response = await api.getDashboardStatistics()
    apiResult.value = JSON.stringify(response, null, 2)
    message.success('API调用成功')
  } catch (error) {
    apiResult.value = `API调用失败: ${error.message}`
    message.error('API调用失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.test-page {
  padding: 20px;
}
</style>
