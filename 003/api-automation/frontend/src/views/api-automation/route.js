import i18n from '~/i18n'
const { t } = i18n.global

const Layout = () => import('@/layout/index.vue')

export default {
  name: 'API自动化',
  path: '/api-automation',
  component: Layout,
  redirect: '/api-automation/dashboard',
  meta: {
    title: 'API自动化',
    icon: 'mdi:api',
    order: 2,
  },
  children: [
    {
      name: 'API自动化仪表板',
      path: 'dashboard',
      component: () => import('./dashboard/index.vue'),
      meta: {
        title: 'API自动化仪表板',
        icon: 'mdi:view-dashboard',
        affix: true,
      },
    },
    {
      name: '接口管理',
      path: 'interface-management',
      component: () => import('./interface-management/index.vue'),
      meta: {
        title: '接口管理',
        icon: 'mdi:api-off',
        description: '管理API接口信息，上传文档自动解析',
      },
    },
    {
      name: '文档工作流',
      path: 'document-workflow',
      component: () => import('./document-workflow/index.vue'),
      meta: {
        title: '文档工作流',
        icon: 'mdi:file-document-outline',
        description: '上传API文档，智能解析接口结构',
      },
    },
    {
      name: '分析详情',
      path: 'analysis-detail',
      component: () => import('./analysis-detail/index.vue'),
      meta: {
        title: '分析详情',
        icon: 'mdi:chart-line',
        hideInMenu: true,
      },
    },
    {
      name: '脚本预览',
      path: 'script-preview',
      component: () => import('./script-preview/index.vue'),
      meta: {
        title: '脚本预览',
        icon: 'mdi:script-text-outline',
        hideInMenu: true,
      },
    },
    {
      name: '脚本管理',
      path: 'script-management',
      component: () => import('@/views/api-automation/script-management/index.vue'),
      meta: {
        title: '测试管理',
        icon: 'mdi:test-tube',
        description: '查看、编辑和管理生成的测试脚本',
      },
    },
    {
      name: '测试执行',
      path: 'test-execution',
      component: () => import('./test-execution/index.vue'),
      meta: {
        title: '测试执行',
        icon: 'mdi:play-circle-outline',
        description: '执行测试脚本，查看执行结果和测试报告',
      },
    },
    {
      name: '定时任务',
      path: 'scheduled-tasks',
      component: () => import('./scheduled-tasks/index.vue'),
      meta: {
        title: '定时任务',
        icon: 'mdi:clock-outline',
        description: '配置和管理定时执行的测试任务',
      },
    },
    {
      name: '执行报告',
      path: 'execution-reports',
      component: () => import('./execution-reports/index.vue'),
      meta: {
        title: '执行报告',
        icon: 'mdi:file-chart',
        description: '查看和管理脚本执行报告',
      },
    },
    {
      name: '执行报告详情',
      path: 'execution-reports/:executionId',
      component: () => import('./execution-reports/detail.vue'),
      meta: {
        title: '执行报告详情',
        icon: 'mdi:file-chart-outline',
        hideInMenu: true,
      },
    },
  ],
}
