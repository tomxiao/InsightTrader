import axios from 'axios'
import { createRouter, createWebHistory } from 'vue-router'
import { userApi } from '@api/user'
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
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach(async to => {
  const authStore = useAuthStore()

  if (authStore.token && !authStore.hasCheckedSession) {
    let shouldMarkSessionChecked = true
    try {
      const user = await userApi.getCurrentUser()
      authStore.setUser(user)
    } catch (error) {
      // 401 handling is centralized in the axios interceptor.
      shouldMarkSessionChecked = axios.isAxiosError(error) && error.response?.status === 401
    } finally {
      authStore.markSessionChecked(shouldMarkSessionChecked)
    }
  }

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
