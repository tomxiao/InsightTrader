import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@stores/auth'

const routes = [
  {
    path: '/',
    redirect: '/conversation'
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@views/login/LoginPage.vue'),
    meta: {
      title: '登录'
    }
  },
  {
    path: '/conversation',
    name: 'Conversation',
    component: () => import('@views/conversation/ConversationPage.vue'),
    meta: {
      title: '当前会话',
      requiresAuth: true
    }
  },
  {
    path: '/report/:id',
    name: 'ReportReader',
    component: () => import('@views/report/ReportReaderPage.vue'),
    meta: {
      title: '完整报告',
      requiresAuth: true
    }
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('@views/settings/SettingsPage.vue'),
    meta: {
      title: '设置',
      requiresAuth: true
    }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach(to => {
  const authStore = useAuthStore()

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    return { name: 'Login' }
  }

  if (to.name === 'Login' && authStore.isAuthenticated) {
    return { name: 'Conversation' }
  }

  return true
})

router.afterEach(to => {
  document.title = `${to.meta.title ?? 'TradingAgents Mobile'}`
})

export default router
