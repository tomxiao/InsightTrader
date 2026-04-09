<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { showToast } from 'vant'

import { analysisApi } from '@api/analysis'
import { conversationsApi } from '@api/conversations'
import TaskStatusBanner from '@components/conversation/TaskStatusBanner.vue'
import MobilePageLayout from '@components/layout/MobilePageLayout.vue'
import { useConversationStore } from '@stores/conversation'
import { useTaskStore } from '@stores/task'
import type { ConversationMessage, ConversationSummary } from '@/types/conversation'
import { formatConversationGroup, formatTimeLabel } from '@utils/format'

const router = useRouter()
const conversationStore = useConversationStore()
const taskStore = useTaskStore()

let pollingTimer: number | null = null

const promptModel = computed({
  get: () => taskStore.draftMessage,
  set: value => taskStore.setDraftMessage(value)
})

const currentConversation = computed(() => conversationStore.currentConversation)
const currentMessages = computed(() => conversationStore.currentMessages)
const currentTask = computed(() => taskStore.currentTask)
const hasRunningTask = computed(() => taskStore.hasRunningTask)

const groupedConversations = computed(() => {
  const groups = new Map<string, ConversationSummary[]>()
  for (const item of conversationStore.conversations) {
    const label = formatConversationGroup(item.updatedAt)
    const list = groups.get(label) || []
    list.push(item)
    groups.set(label, list)
  }
  return Array.from(groups.entries())
})

const suggestedPrompts = [
  '分析宁德时代，重点看长期持有风险',
  '查看腾讯控股最新报告',
  '分析苹果，重点关注估值与催化'
]

const conversationStatusLabelMap: Record<ConversationSummary['status'], string> = {
  idle: '待开始',
  collecting_inputs: '补充信息中',
  ready_to_analyze: '可发起分析',
  analyzing: '分析中',
  report_ready: '报告已生成',
  report_explaining: '继续解读中',
  failed: '需要重试'
}

const bannerVisible = computed(() => ['pending', 'running', 'failed'].includes(currentTask.value.status))

const isFollowupMode = computed(
  () =>
    Boolean(currentConversation.value.lastReportId) &&
    !hasRunningTask.value &&
    currentConversation.value.status !== 'idle'
)

const placeholderText = computed(() =>
  hasRunningTask.value ? '分析仍在进行中，你的新问题会先保留为草稿' : '问一只股票、一个观点，或继续追问'
)

const composerHint = computed(() =>
  hasRunningTask.value
    ? '分析进行中，消息会先保留为草稿。'
    : ''
)

const currentConversationStatusLabel = computed(
  () => conversationStatusLabelMap[currentConversation.value.status] || '待开始'
)

const loadConversation = async (conversationId: string) => {
  const detail = await conversationsApi.getConversation(conversationId)
  conversationStore.setCurrentConversation(detail)
  if (detail.currentTaskId) {
    try {
      const status = await analysisApi.getTaskStatus(detail.currentTaskId)
      taskStore.setTask(status)
    } catch {
      // ignore stale task references
    }
  } else if (taskStore.currentTask.status === 'completed' || taskStore.currentTask.status === 'failed') {
    taskStore.clearTask()
  }
}

const createConversation = async () => {
  const summary = await conversationsApi.createConversation({ title: '新会话' })
  conversationStore.upsertConversation(summary)
  await loadConversation(summary.id)
  conversationStore.setDrawerOpen(false)
}

const bootstrap = async () => {
  conversationStore.setLoading(true)
  try {
    const conversations = await conversationsApi.listConversations()
    conversationStore.setConversations(conversations)

    if (!conversations.length) {
      await createConversation()
      return
    }

    const preferredId =
      conversationStore.currentConversationId ||
      conversations[0]?.id

    if (preferredId) {
      await loadConversation(preferredId)
    }
  } catch (error) {
    showToast((error as Error).message || '初始化会话失败')
  } finally {
    conversationStore.setLoading(false)
  }
}

const extractTicker = (input: string) => {
  const match = input.match(/([A-Z]{1,5}(?:\.[A-Z]{1,5})?|\d{3,6}(?:\.[A-Z]{2})?|[\u4e00-\u9fa5]{2,12})/)
  return match?.[1] || input.trim()
}

const todayTradeDate = () => new Date().toISOString().slice(0, 10)

const submitPrompt = async () => {
  const text = promptModel.value.trim()
  if (!text) {
    showToast('请输入内容')
    return
  }

  if (!currentConversation.value.id) {
    await createConversation()
  }

  if (hasRunningTask.value) {
    taskStore.setDraftMessage(text)
    showToast('当前分析尚未完成，已为你保留草稿')
    return
  }

  try {
    if (isFollowupMode.value) {
      const response = await conversationsApi.postMessage(currentConversation.value.id, { message: text })
      conversationStore.appendMessages(response.messages)
      conversationStore.updateConversationStatus('report_explaining', currentConversation.value.currentTaskId, response.reportId)
      taskStore.setDraftMessage('')
      return
    }

    const task = await analysisApi.createTask({
      conversationId: currentConversation.value.id,
      ticker: extractTicker(text),
      tradeDate: todayTradeDate(),
      prompt: text
    })
    taskStore.setTask(task)
    conversationStore.updateConversationStatus('analyzing', task.taskId, task.reportId)
    taskStore.setDraftMessage('')
    await loadConversation(currentConversation.value.id)
    startPolling()
  } catch (error) {
    showToast((error as Error).message || '发送失败，请稍后再试')
  }
}

const openConversation = async (conversationId: string) => {
  try {
    await loadConversation(conversationId)
    conversationStore.setDrawerOpen(false)
  } catch (error) {
    showToast((error as Error).message || '加载会话失败')
  }
}

const stopPolling = () => {
  if (pollingTimer) {
    window.clearInterval(pollingTimer)
    pollingTimer = null
  }
}

const pollTask = async () => {
  if (!taskStore.currentTask.taskId) return

  try {
    const status = await analysisApi.getTaskStatus(taskStore.currentTask.taskId)
    taskStore.setTask(status)
    conversationStore.updateConversationStatus(
      status.status === 'completed'
        ? 'report_ready'
        : status.status === 'failed'
          ? 'failed'
          : 'analyzing',
      status.taskId,
      status.reportId
    )

    if (status.status === 'completed' || status.status === 'failed') {
      stopPolling()
      await loadConversation(currentConversation.value.id)
    }
  } catch {
    stopPolling()
  }
}

const startPolling = () => {
  stopPolling()
  if (!taskStore.currentTask.taskId) return
  pollingTimer = window.setInterval(pollTask, 3000)
}

const quickFill = (prompt: string) => {
  promptModel.value = prompt
}

const getConversationStatusLabel = (status: ConversationSummary['status']) =>
  conversationStatusLabelMap[status] || '处理中'

const getMessageText = (message: ConversationMessage) => {
  if (typeof message.content === 'string') {
    return message.content
  }
  return message.content.text || ''
}

const getReportCardId = (message: ConversationMessage) =>
  typeof message.content === 'string' ? '' : message.content.reportId || ''

const getReportCardTitle = (message: ConversationMessage) =>
  typeof message.content === 'string' ? '查看完整报告' : message.content.title || '查看完整报告'

watch(
  () => taskStore.currentTask.status,
  status => {
    if (status === 'pending' || status === 'running') {
      startPolling()
    }
    if (status === 'completed' || status === 'failed' || status === 'idle') {
      stopPolling()
    }
  },
  { immediate: true }
)

onMounted(bootstrap)
onBeforeUnmount(stopPolling)
</script>

<template>
  <MobilePageLayout :title="conversationStore.currentTitle" :with-content-padding="false">
    <template #header>
      <div class="conversation-page__header">
        <van-button plain size="small" class="conversation-page__icon-button" @click="conversationStore.setDrawerOpen(true)">
          <van-icon name="wap-nav" />
        </van-button>
        <div class="conversation-page__header-main">
          <strong class="conversation-page__header-title">{{ conversationStore.currentTitle }}</strong>
          <span class="conversation-page__header-subtitle">{{ currentConversationStatusLabel }}</span>
        </div>
        <van-button plain size="small" class="conversation-page__icon-button" @click="router.push({ name: 'Settings' })">
          <van-icon name="setting-o" />
        </van-button>
      </div>
    </template>

    <template v-if="bannerVisible" #banner>
      <TaskStatusBanner
        :status="currentTask.status"
        :title="currentTask.currentStep || '任务状态'"
        :detail="currentTask.message || '分析正在处理中，请稍候'"
        :elapsed-time="currentTask.elapsedTime"
        :remaining-time="currentTask.remainingTime"
      />
    </template>

    <div class="conversation-page">
      <van-popup
        :show="conversationStore.isDrawerOpen"
        position="left"
        :style="{ width: '61.8%', height: '100%' }"
        @click-overlay="conversationStore.setDrawerOpen(false)"
      >
        <div class="conversation-drawer">
          <div class="conversation-drawer__brand">
            <strong>InsightTrader</strong>
            <p class="mobile-muted">在同一个线程里发起分析、查看报告、继续追问。</p>
          </div>

          <van-button block round type="primary" @click="createConversation">开始新对话</van-button>

          <div class="conversation-drawer__groups">
            <section v-for="[label, items] in groupedConversations" :key="label" class="conversation-drawer__group">
              <h3>{{ label }}</h3>
              <button
                v-for="item in items"
                :key="item.id"
                class="conversation-drawer__item"
                :class="{ 'is-active': item.id === currentConversation.id }"
                @click="openConversation(item.id)"
              >
                <div class="conversation-drawer__item-head">
                  <strong>{{ item.title }}</strong>
                </div>
                <small>{{ getConversationStatusLabel(item.status) }}</small>
              </button>
            </section>
          </div>

          <div class="conversation-drawer__account">
            <div>
              <strong>账户与偏好</strong>
              <p class="mobile-muted">查看登录状态、帮助说明和退出入口。</p>
            </div>
            <van-button plain size="small" @click="router.push({ name: 'Settings' })">
              打开
            </van-button>
          </div>
        </div>
      </van-popup>

      <div class="conversation-page__body">
        <van-pull-refresh v-model="conversationStore.isLoading" @refresh="bootstrap">
          <div v-if="!currentMessages.length" class="conversation-empty">
            <div class="conversation-empty__hero">
              <p class="conversation-empty__eyebrow">InsightTrader Mobile</p>
              <h2>今晚想研究什么？</h2>
              <p class="mobile-muted">用自然语言输入股票、公司或观点。我会先发起分析，再把结论留在这条对话里。</p>
            </div>
            <div class="conversation-empty__chips">
              <van-button
                v-for="prompt in suggestedPrompts"
                :key="prompt"
                plain
                round
                size="small"
                @click="quickFill(prompt)"
              >
                {{ prompt }}
              </van-button>
            </div>
            <p class="conversation-empty__example mobile-subtle">例如：分析英伟达，关注估值、未来两季催化，以及当前最大的下行风险。</p>
          </div>

          <div v-else class="conversation-stream">
            <article
              v-for="message in currentMessages"
              :key="message.id"
              class="conversation-message"
              :class="[
                `conversation-message--${message.role}`,
                `conversation-message--${message.messageType}`
              ]"
            >
              <template v-if="message.messageType === 'summary_card'">
                <section class="conversation-inline-card conversation-inline-card--summary">
                  <span class="conversation-inline-card__eyebrow">执行摘要</span>
                  <h3 class="conversation-inline-card__title">先看核心观点，再决定是否进入全文。</h3>
                  <p class="conversation-summary">{{ getMessageText(message) }}</p>
                </section>
              </template>

              <template v-else-if="message.messageType === 'report_card'">
                <section class="conversation-inline-card conversation-inline-card--report">
                  <span class="conversation-inline-card__eyebrow">完整报告</span>
                  <h3 class="conversation-inline-card__title">{{ getReportCardTitle(message) }}</h3>
                  <p class="conversation-inline-card__description">完整报告已经生成，你可以进入独立阅读页查看全文。</p>
                  <div class="conversation-inline-card__action">
                    <van-button
                      size="small"
                      type="primary"
                      @click="router.push({ name: 'ReportReader', params: { id: getReportCardId(message) } })"
                    >
                      查看完整报告
                    </van-button>
                  </div>
                </section>
              </template>

              <template v-else>
                <div class="conversation-bubble">
                  <span v-if="message.role !== 'assistant'" class="conversation-bubble__role">
                    {{ message.role === 'user' ? '你' : message.role === 'assistant' ? 'InsightTrader' : '系统' }}
                  </span>
                  <p>{{ getMessageText(message) }}</p>
                  <small>{{ formatTimeLabel(message.createdAt) }}</small>
                </div>
              </template>
            </article>
          </div>
        </van-pull-refresh>
      </div>
    </div>

    <template #footer>
      <div class="conversation-input">
        <div class="conversation-input__shell">
          <div class="conversation-input__row">
            <van-field
              v-model="promptModel"
              rows="3"
              autosize
              type="textarea"
              :placeholder="placeholderText"
            />
            <van-button round type="primary" @click="submitPrompt">发送</van-button>
          </div>
          <div v-if="composerHint" class="conversation-input__actions">
            <span class="mobile-subtle">
              {{ composerHint }}
            </span>
          </div>
        </div>
      </div>
    </template>
  </MobilePageLayout>
</template>

<style scoped>
.conversation-page {
  min-height: calc(100vh - 56px);
}

.conversation-page__header {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 12px;
  padding: 10px 16px 6px;
}

.conversation-page__header :deep(.van-button) {
  min-width: 42px;
  width: 42px;
  height: 42px;
  padding: 0;
  border-radius: 21px;
  background: rgba(255, 255, 255, 0.045);
  color: var(--mobile-color-text-secondary);
  border-color: rgba(255, 255, 255, 0.08);
}

.conversation-page__icon-button :deep(.van-icon) {
  font-size: 19px;
}

.conversation-page__header-main {
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1px;
}

.conversation-page__header-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-align: center;
  font-size: 16px;
  font-weight: 700;
  line-height: 1.2;
}

.conversation-page__header-subtitle {
  color: var(--mobile-color-text-tertiary);
  font-size: 12px;
  line-height: 1.2;
}

.conversation-page__body {
  padding: 0 var(--mobile-space-md);
  padding-bottom: calc(154px + var(--mobile-safe-bottom));
}

.conversation-empty {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding-top: 34px;
  min-height: calc(100vh - 240px);
}

.conversation-empty__hero {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.conversation-empty__eyebrow {
  margin: 0;
  color: var(--mobile-color-text-secondary);
  font-size: 14px;
  font-weight: 600;
}

.conversation-empty h2,
.conversation-empty p {
  margin: 0;
}

.conversation-empty h2 {
  font-size: clamp(32px, 11vw, 44px);
  line-height: 1.08;
  letter-spacing: -0.04em;
}

.conversation-empty__chips {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.conversation-empty__chips :deep(.van-button) {
  height: 36px;
  padding: 0 14px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.05);
  color: var(--mobile-color-text);
}

.conversation-empty__example {
  margin: 0;
  line-height: 1.7;
}

.conversation-stream {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px 0 18px;
}

.conversation-message {
  display: flex;
}

.conversation-message--user {
  justify-content: flex-end;
}

.conversation-message--assistant,
.conversation-message--system {
  justify-content: flex-start;
}

.conversation-bubble {
  max-width: min(92%, 720px);
  padding: 12px 14px;
  border-radius: 18px;
  border: 1px solid var(--mobile-color-border);
  background: var(--mobile-color-surface);
  box-shadow: none;
}

.conversation-message--user .conversation-bubble {
  border-color: rgba(93, 139, 255, 0.22);
  background: rgba(93, 139, 255, 0.14);
}

.conversation-message--assistant .conversation-bubble {
  max-width: 100%;
  padding: 2px 0;
  border: 0;
  border-radius: 0;
  background: transparent;
}

.conversation-message--system .conversation-bubble {
  max-width: 100%;
  padding: 2px 0;
  border: 0;
  border-radius: 0;
  background: transparent;
}

.conversation-message--error .conversation-bubble {
  border-color: rgba(255, 107, 107, 0.25);
  background: rgba(255, 107, 107, 0.08);
}

.conversation-bubble p,
.conversation-bubble small,
.conversation-summary {
  margin: 0;
}

.conversation-bubble__role {
  display: inline-block;
  margin-bottom: 6px;
  color: var(--mobile-color-text-tertiary);
  font-size: 11px;
  font-weight: 600;
}

.conversation-bubble p {
  line-height: 1.66;
  white-space: pre-wrap;
  font-size: 15px;
}

.conversation-message--assistant .conversation-bubble p {
  font-size: 16px;
  line-height: 1.8;
  color: var(--mobile-color-text);
}

.conversation-message--system .conversation-bubble p {
  font-size: 13px;
  line-height: 1.6;
  color: var(--mobile-color-text-secondary);
}

.conversation-bubble small {
  display: block;
  margin-top: 6px;
  color: var(--mobile-color-text-tertiary);
  font-size: 11px;
}

.conversation-message--assistant .conversation-bubble small,
.conversation-message--system .conversation-bubble small {
  margin-top: 4px;
}

.conversation-message--system .conversation-bubble small {
  display: none;
}

.conversation-summary {
  line-height: 1.7;
  white-space: pre-wrap;
}

.conversation-inline-card {
  width: 100%;
  padding: 14px 0 6px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.conversation-inline-card__eyebrow {
  display: inline-block;
  margin-bottom: 8px;
  color: var(--mobile-color-text-tertiary);
  font-size: 11px;
  font-weight: 600;
}

.conversation-inline-card__title,
.conversation-inline-card__description {
  margin: 0;
}

.conversation-inline-card__title {
  font-size: 16px;
  line-height: 1.5;
}

.conversation-inline-card__description {
  margin-top: 6px;
  color: var(--mobile-color-text-secondary);
  line-height: 1.6;
}

.conversation-inline-card__action {
  margin-top: 12px;
}

.conversation-input {
  padding: 6px var(--mobile-space-md) 10px;
}

.conversation-input__shell {
  padding: 8px 8px 6px;
  border-radius: 30px;
  border: 1px solid var(--mobile-color-border);
  background: rgba(27, 29, 35, 0.98);
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.14);
}

.conversation-input__row {
  display: flex;
  align-items: flex-end;
  gap: 10px;
}

.conversation-input :deep(.van-field) {
  flex: 1;
  padding: 8px 12px;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.018);
}

.conversation-input :deep(textarea) {
  min-height: 44px;
  line-height: 1.5;
  font-size: 15px;
}

.conversation-input :deep(textarea::placeholder) {
  color: var(--mobile-color-text-secondary);
}

.conversation-input__actions {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  margin-top: 6px;
  padding: 0 12px 2px;
}

.conversation-input__actions span {
  font-size: 11px;
  line-height: 1.5;
}

.conversation-input__actions :deep(.van-button) {
  min-width: 46px;
  height: 46px;
  padding: 0 16px;
  font-size: 15px;
  font-weight: 700;
  flex-shrink: 0;
}

.conversation-drawer {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: var(--mobile-space-lg);
  gap: 18px;
  background: var(--mobile-color-bg-elevated);
}

.conversation-drawer__brand p,
.conversation-drawer__group h3,
.conversation-drawer__account p {
  margin: 0;
}

.conversation-drawer__brand {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.conversation-drawer__brand strong {
  font-size: 20px;
}

.conversation-drawer__groups {
  flex: 1;
  overflow: auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.conversation-drawer__group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.conversation-drawer__group h3 {
  color: var(--mobile-color-text-tertiary);
  font-size: 12px;
  font-weight: 600;
}

.conversation-drawer__item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 12px;
  border: 1px solid var(--mobile-color-border);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.025);
  text-align: left;
  color: var(--mobile-color-text);
  overflow: hidden;
}

.conversation-drawer__item.is-active {
  border-color: var(--mobile-color-primary);
  background: rgba(93, 139, 255, 0.12);
}

.conversation-drawer__item-head {
  display: flex;
  align-items: center;
  min-width: 0;
}

.conversation-drawer__item-head strong,
.conversation-drawer__item small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.conversation-drawer__item span,
.conversation-drawer__item small {
  color: var(--mobile-color-text-secondary);
}

.conversation-drawer__account {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--mobile-color-border);
}

</style>
