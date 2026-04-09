<script setup lang="ts">
import { showToast } from 'vant'
import { useRouter } from 'vue-router'

import MobilePageLayout from '@components/layout/MobilePageLayout.vue'
import { useAuthStore } from '@stores/auth'
import { useConversationStore } from '@stores/conversation'
import { useTaskStore } from '@stores/task'

const router = useRouter()
const authStore = useAuthStore()
const conversationStore = useConversationStore()
const taskStore = useTaskStore()

const logout = () => {
  conversationStore.setConversations([])
  conversationStore.resetCurrentConversation()
  conversationStore.setDrawerOpen(false)
  taskStore.clearTask()
  taskStore.setDraftMessage('')
  authStore.clearAuth()
  showToast('已退出登录')
  router.replace({ name: 'Login' })
}
</script>

<template>
  <MobilePageLayout title="设置">
    <template #header>
      <div class="settings-page__header">
        <div>
          <strong>设置</strong>
          <p class="mobile-subtle">账户、帮助与基础偏好</p>
        </div>
      </div>
    </template>

    <div class="settings-page">
      <section class="mobile-card settings-page__section">
        <span class="settings-page__eyebrow">账户</span>
        <h2 class="settings-page__title">{{ authStore.user?.displayName || authStore.user?.username }}</h2>
        <p class="mobile-muted">当前账号已登录，可直接继续对话、查看报告并追问。</p>
      </section>

      <section class="mobile-card settings-page__section">
        <div class="settings-page__row">
          <div>
            <strong>系统设置</strong>
            <p class="mobile-muted">当前版本保持轻量，优先打磨对话与报告阅读体验。</p>
          </div>
          <span class="mobile-subtle">即将完善</span>
        </div>
        <div class="settings-page__row">
          <div>
            <strong>帮助与反馈</strong>
            <p class="mobile-muted">若分析状态异常或报告未显示，建议返回会话页重新拉取。</p>
          </div>
          <span class="mobile-subtle">使用提示</span>
        </div>
      </section>

      <van-button round block type="danger" @click="logout">退出登录</van-button>
    </div>
  </MobilePageLayout>
</template>

<style scoped>
.settings-page__header {
  padding: var(--mobile-space-md);
}

.settings-page__header p,
.settings-page__header strong {
  margin: 0;
}

.settings-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.settings-page__section {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.settings-page__eyebrow {
  color: var(--mobile-color-primary-strong);
  font-size: 13px;
  font-weight: 600;
}

.settings-page__title {
  margin: 0;
  font-size: 26px;
  line-height: 1.15;
}

.settings-page__row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 0;
}

.settings-page__row + .settings-page__row {
  border-top: 1px solid var(--mobile-color-border);
}

.settings-page__row strong,
.settings-page__row p {
  margin: 0;
}

.settings-page__row p {
  margin-top: 6px;
}
</style>
