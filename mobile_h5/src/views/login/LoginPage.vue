<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { showToast } from 'vant'

import { authApi } from '@api/auth'
import MobilePageLayout from '@components/layout/MobilePageLayout.vue'
import { useAuthStore } from '@stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const loading = ref(false)

const form = reactive({
  username: '',
  password: ''
})

const submit = async () => {
  if (!form.username.trim() || !form.password.trim()) {
    showToast('请输入用户名和密码')
    return
  }

  loading.value = true
  try {
    const response = await authApi.login({
      username: form.username.trim(),
      password: form.password
    })
    authStore.setAuth(response.access_token, response.user)
    showToast('登录成功')
    router.replace({ name: 'Conversation' })
  } catch (error) {
    showToast((error as Error).message || '登录失败，请稍后重试')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <MobilePageLayout title="欢迎使用">
    <section class="login-page">
      <div class="login-page__hero">
        <p class="login-page__eyebrow">InsightTrader Mobile</p>
        <h1 class="login-page__title">像聊天一样做投研。</h1>
        <p class="login-page__subtitle">登录后即可在同一个线程里发起分析、阅读报告，并继续追问关键结论。</p>
      </div>

      <van-form class="mobile-card login-page__form" @submit="submit">
        <van-field
          v-model="form.username"
          name="username"
          label="用户名"
          placeholder="请输入用户名"
          autocomplete="username"
        />
        <van-field
          v-model="form.password"
          name="password"
          label="密码"
          type="password"
          placeholder="请输入密码"
          autocomplete="current-password"
        />

        <div class="login-page__actions">
          <van-button block round type="primary" native-type="submit" :loading="loading">
            进入 InsightTrader
          </van-button>
        </div>
      </van-form>
    </section>
  </MobilePageLayout>
</template>

<style scoped>
.login-page {
  display: flex;
  flex-direction: column;
  gap: 24px;
  min-height: calc(100vh - 96px);
  justify-content: center;
}

.login-page__hero {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.login-page__eyebrow {
  margin: 0;
  color: var(--mobile-color-primary-strong);
  font-weight: 600;
}

.login-page__title {
  margin: 0;
  font-size: clamp(34px, 12vw, 48px);
  line-height: 1.04;
  letter-spacing: -0.04em;
}

.login-page__subtitle {
  margin: 0;
  color: var(--mobile-color-text-secondary);
  line-height: 1.7;
}

.login-page__form {
  padding: 8px 0;
}

.login-page__actions {
  padding: 20px 16px 8px;
}
</style>
