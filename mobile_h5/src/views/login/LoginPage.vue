<script setup lang="ts">
import axios from 'axios'
import { onMounted, onUnmounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { showToast } from 'vant'

import { authApi } from '@api/auth'
import MobilePageLayout from '@components/layout/MobilePageLayout.vue'
import { useAuthStore } from '@stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const loading = ref(false)
const showPassword = ref(false)
const keyboardActive = ref(false)
let focusResetFrame = 0

const form = reactive({
  username: '',
  password: ''
})

const resetWindowScroll = () => {
  if (typeof window === 'undefined') {
    return
  }

  window.scrollTo(0, 0)
  document.documentElement.scrollTop = 0
  document.body.scrollTop = 0
}

const scheduleFocusReset = () => {
  if (typeof window === 'undefined') {
    return
  }

  cancelAnimationFrame(focusResetFrame)
  focusResetFrame = window.requestAnimationFrame(() => {
    resetWindowScroll()
  })
}

const handleFocusIn = () => {
  keyboardActive.value = true
  scheduleFocusReset()
}

const handleFocusOut = () => {
  if (typeof window === 'undefined') {
    return
  }

  window.setTimeout(() => {
    keyboardActive.value = document.activeElement instanceof HTMLInputElement
  }, 0)
}

onMounted(() => {
  if (typeof window === 'undefined') {
    return
  }

  document.addEventListener('focusin', handleFocusIn)
  document.addEventListener('focusout', handleFocusOut)
})

onUnmounted(() => {
  if (typeof window === 'undefined') {
    return
  }

  cancelAnimationFrame(focusResetFrame)
  document.removeEventListener('focusin', handleFocusIn)
  document.removeEventListener('focusout', handleFocusOut)
})

const resolveLoginErrorMessage = (error: unknown) => {
  if (axios.isAxiosError<{ detail?: string }>(error)) {
    const detail = error.response?.data?.detail
    if (typeof detail === 'string' && detail.trim()) {
      return detail
    }
  }

  if (error instanceof Error && error.message) {
    return error.message
  }

  return '登录失败，请稍后重试'
}

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
    showToast(resolveLoginErrorMessage(error))
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <MobilePageLayout :with-content-padding="false">
    <section class="login-page" :class="{ 'is-keyboard-active': keyboardActive }">
      <div class="login-page__content">
        <div class="login-page__brand">
          <div class="login-page__brand-mark" aria-hidden="true">
            <span class="login-page__brand-mark-main" />
            <span class="login-page__brand-mark-cut" />
            <span class="login-page__brand-mark-dot" />
          </div>
          <p class="login-page__brand-name">InsightTrader</p>
          <p class="login-page__brand-subtitle">像聊天一样完成投研分析</p>
        </div>

        <van-form class="login-page__form" @submit="submit">
          <van-field
            v-model="form.username"
            class="login-page__field"
            name="login-identity"
            placeholder="请输入手机号 / 邮箱 / 用户名"
            autocomplete="off"
            autocapitalize="none"
            autocorrect="off"
            :spellcheck="false"
          />
          <van-field
            v-model="form.password"
            :class="['login-page__field', 'login-page__field--password', { 'is-visible': showPassword }]"
            name="login-secret"
            :type="showPassword ? 'text' : 'password'"
            inputmode="text"
            placeholder="请输入密码"
            autocomplete="off"
            autocapitalize="none"
            autocorrect="off"
            :spellcheck="false"
          >
            <template #right-icon>
              <button
                class="login-page__field-toggle"
                type="button"
                :aria-label="showPassword ? '隐藏密码' : '显示密码'"
                :aria-pressed="showPassword"
                @click="showPassword = !showPassword"
              >
                <van-icon :name="showPassword ? 'closed-eye' : 'eye-o'" aria-hidden="true" />
                <span class="login-page__sr-only">{{ showPassword ? '隐藏密码' : '显示密码' }}</span>
              </button>
            </template>
          </van-field>

          <p class="login-page__agreement">
            注册登录即代表已阅读并同意我们的
            <span>用户协议</span>
            与
            <span>隐私政策</span>
          </p>

          <div class="login-page__actions">
            <van-button block round type="primary" native-type="submit" :loading="loading">
              登录
            </van-button>
          </div>
        </van-form>
      </div>

      <footer class="login-page__footer">粤ICP备 2026037148 号 · 联系我们</footer>
    </section>
  </MobilePageLayout>
</template>

<style scoped>
.login-page {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 100vh;
  height: 100svh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  overscroll-behavior: none;
  padding: max(28px, calc(env(safe-area-inset-top, 0px) + 20px)) 24px
    calc(var(--mobile-safe-bottom) + 22px);
  background:
    radial-gradient(circle at 50% 0, rgba(93, 139, 255, 0.22), transparent 34%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.014), rgba(255, 255, 255, 0)),
    var(--mobile-color-bg);
}

.login-page.is-keyboard-active {
  padding-top: max(12px, env(safe-area-inset-top, 0px));
}

.login-page__content {
  width: min(100%, 392px);
  margin: 0 auto;
  padding-top: 48px;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 22px;
}

.login-page.is-keyboard-active .login-page__content {
  padding-top: 8px;
  gap: 14px;
}

.login-page__brand {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding-top: 6px;
  margin-bottom: 6px;
}

.login-page.is-keyboard-active .login-page__brand {
  gap: 6px;
  padding-top: 0;
  margin-bottom: 0;
}

.login-page__brand-mark {
  position: relative;
  width: 82px;
  height: 58px;
}

.login-page.is-keyboard-active .login-page__brand-mark {
  width: 56px;
  height: 40px;
}

.login-page__brand-mark-main,
.login-page__brand-mark-cut,
.login-page__brand-mark-dot {
  position: absolute;
  display: block;
}

.login-page__brand-mark-main,
.login-page__brand-mark-dot {
  background: linear-gradient(180deg, #7ea5ff 0%, #4f79ff 100%);
  box-shadow: 0 12px 26px rgba(79, 121, 255, 0.22);
}

.login-page__brand-mark-main {
  inset: 2px 12px 4px 0;
  clip-path: polygon(0 46%, 32% 8%, 88% 8%, 56% 42%, 84% 74%, 31% 74%);
  border-radius: 20px;
  opacity: 0.98;
}

.login-page__brand-mark-cut {
  width: 12px;
  height: 12px;
  top: 7px;
  left: 50px;
  background: rgba(18, 19, 22, 0.96);
  clip-path: polygon(50% 0, 100% 50%, 50% 100%, 0 50%);
  border-radius: 3px;
  transform: rotate(16deg);
}

.login-page__brand-mark-dot {
  width: 18px;
  height: 18px;
  right: 3px;
  bottom: 8px;
  border-radius: 50%;
}

.login-page__brand-name {
  margin: 0;
  color: #7da3ff;
  font-size: 26px;
  font-weight: 700;
  letter-spacing: -0.04em;
}

.login-page.is-keyboard-active .login-page__brand-name {
  font-size: 20px;
}

.login-page__brand-subtitle {
  margin: 0;
  color: rgba(247, 248, 250, 0.8);
  font-size: 11px;
  line-height: 1.4;
}

.login-page.is-keyboard-active .login-page__brand-subtitle {
  font-size: 10px;
}

.login-page__form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.login-page__field {
  min-height: 52px;
  padding: 1px 10px;
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.028);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.03),
    0 0 0 1px rgba(255, 255, 255, 0.015);
}

.login-page__field :deep(.van-field__body) {
  min-height: 46px;
}

.login-page__field :deep(.van-field__control) {
  font-size: 16px;
}

.login-page__field--password :deep(.van-field__control) {
  -webkit-text-security: disc;
  text-security: disc;
}

.login-page__field--password.is-visible :deep(.van-field__control) {
  -webkit-text-security: none;
  text-security: none;
}

.login-page__field :deep(.van-field__control::placeholder) {
  color: rgba(247, 248, 250, 0.44);
}

.login-page__field-toggle {
  border: 0;
  padding: 0;
  width: 28px;
  height: 28px;
  background: transparent;
  color: rgba(247, 248, 250, 0.5);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
}

.login-page__agreement {
  margin: 8px 0 0;
  color: rgba(247, 248, 250, 0.48);
  font-size: 11px;
  line-height: 1.7;
}

.login-page.is-keyboard-active .login-page__agreement {
  margin-top: 4px;
  line-height: 1.5;
}

.login-page__agreement span {
  color: rgba(247, 248, 250, 0.78);
}

.login-page__actions {
  padding-top: 10px;
}

.login-page.is-keyboard-active .login-page__actions {
  padding-top: 4px;
}

.login-page__footer {
  width: 100%;
  margin-top: 28px;
  color: rgba(247, 248, 250, 0.38);
  font-size: 12px;
  text-align: center;
}

.login-page.is-keyboard-active .login-page__footer {
  display: none;
}

.login-page__sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
</style>
