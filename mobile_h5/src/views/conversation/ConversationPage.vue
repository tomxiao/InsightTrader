<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { showToast } from 'vant'

import { analysisApi } from '@api/analysis'
import { authApi } from '@api/auth'
import { conversationsApi } from '@api/conversations'
import TaskStatusBanner from '@components/conversation/TaskStatusBanner.vue'
import MobilePageLayout from '@components/layout/MobilePageLayout.vue'
import { useAuthStore } from '@stores/auth'
import { useConversationStore } from '@stores/conversation'
import { useTaskStore } from '@stores/task'
import type { ConversationMessage, ConversationSummary } from '@/types/conversation'
import type {
  ResolutionAction,
  ResolutionCandidate,
  ResolutionMessageContent,
  ResolutionResponse,
  ResolutionStatus
} from '@/types/resolution'
import { formatConversationGroup, formatTimeLabel } from '@utils/format'

const router = useRouter()
const authStore = useAuthStore()
const conversationStore = useConversationStore()
const taskStore = useTaskStore()
const accountMenuOpen = ref(false)
const logoutLoading = ref(false)
const resolutionActionLoading = ref(false)
const sendingLoading = ref(false)

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
    !hasRunningTask.value &&
    ['report_ready', 'report_explaining'].includes(currentConversation.value.status)
)

const placeholderText = computed(() =>
  hasRunningTask.value ? '分析仍在进行中，你的新问题会先保留为草稿' : '问一只股票、一个观点，或继续追问'
)

const composerHint = computed(() =>
  hasRunningTask.value ? '分析进行中，消息会先保留为草稿。' : ''
)

const currentConversationStatusLabel = computed(
  () => conversationStatusLabelMap[currentConversation.value.status] || '待开始'
)

const accountDisplayName = computed(() => authStore.user?.displayName || authStore.user?.username || '未登录')
const accountInitial = computed(() => accountDisplayName.value.trim().charAt(0).toUpperCase() || 'U')

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

const isResolutionContent = (content: ConversationMessage['content']): content is ResolutionMessageContent =>
  typeof content === 'object' && content !== null

const getResolutionContent = (message: ConversationMessage): ResolutionMessageContent | null =>
  message.messageType === 'ticker_resolution' && isResolutionContent(message.content) ? message.content : null

const getResolutionStatus = (message: ConversationMessage): ResolutionStatus | '' =>
  getResolutionContent(message)?.status || ''

const getResolutionId = (message: ConversationMessage) =>
  getResolutionContent(message)?.resolutionId || ''

const getResolutionCandidates = (message: ConversationMessage): ResolutionCandidate[] =>
  getResolutionContent(message)?.candidates || []

const getResolutionCardTitle = (message: ConversationMessage) => {
  const status = getResolutionStatus(message)
  if (status === 'need_confirm') return '请确认分析标的'
  if (status === 'need_disambiguation') return '请选择分析标的'
  if (status === 'resolved') return '标的已确认'
  if (status === 'unsupported') return '当前范围提示'
  if (status === 'failed') return '需要重新输入'
  return '继续补充标的信息'
}

const getResolutionFocusText = (message: ConversationMessage) => {
  const focusPoints = getResolutionContent(message)?.focusPoints || []
  return focusPoints.length ? `关注点：${focusPoints.join('、')}` : ''
}

const getCandidateLabel = (candidate: ResolutionCandidate) =>
  `${candidate.name}（${candidate.ticker}）${candidate.market ? ` · ${candidate.market}` : ''}`

const activeResolutionId = computed(() => {
  // Collect resolutionIds that already have a follow-up response (settled).
  // A resolution is settled when any message with the same id carries a status
  // other than 'need_confirm' / 'need_disambiguation' (e.g. resolved, failed,
  // unsupported, collect_more), meaning the user already acted on it.
  const settledIds = new Set<string>()
  for (const message of currentMessages.value) {
    const content = getResolutionContent(message)
    if (!content?.resolutionId) continue
    if (content.status !== 'need_confirm' && content.status !== 'need_disambiguation') {
      settledIds.add(content.resolutionId)
    }
  }

  for (let index = currentMessages.value.length - 1; index >= 0; index -= 1) {
    const message = currentMessages.value[index]
    const content = getResolutionContent(message)
    if (!content?.resolutionId) continue
    if (
      (content.status === 'need_confirm' || content.status === 'need_disambiguation') &&
      !settledIds.has(content.resolutionId)
    ) {
      return content.resolutionId
    }
  }
  return ''
})

const canInteractWithResolution = (message: ConversationMessage) => {
  const resolutionId = getResolutionId(message)
  if (!resolutionId) return false
  return resolutionId === activeResolutionId.value && !hasRunningTask.value
}

const applyResolutionResponse = async (response: ResolutionResponse) => {
  conversationStore.appendMessages(response.messages)
  if (response.conversationStatus === 'analyzing' && response.taskStatus) {
    taskStore.setTask(response.taskStatus)
    taskStore.setDraftMessage('')
    if (response.taskStatus.status === 'completed') {
      // DEBUG_SKIP_ANALYSIS 场景：后端在同一请求内完成了 analyzing→report_ready，
      // 直接重新加载会话以获取最新状态（含 report_ready 消息），无需轮询
      await loadConversation(currentConversation.value.id)
    } else {
      conversationStore.updateConversationStatus('analyzing')
      await loadConversation(currentConversation.value.id)
      startPolling()
    }
    return
  }
  conversationStore.updateConversationStatus(response.conversationStatus)
  if (response.conversationStatus === 'ready_to_analyze') {
    // 后端已识别标的但当前有其他任务正在运行，无法自动启动分析
    showToast('已识别标的，但当前有分析任务正在进行，请等待完成后重试')
  }
  taskStore.setDraftMessage('')
}

const submitResolutionAction = async (action: ResolutionAction, resolutionId: string, ticker?: string) => {
  if (!currentConversation.value.id || !resolutionId) return
  resolutionActionLoading.value = true
  try {
    const response = await conversationsApi.confirmResolution(currentConversation.value.id, {
      action,
      resolutionId,
      ticker
    })
    await applyResolutionResponse(response)
  } catch (error) {
    if (axios.isAxiosError(error) && error.response?.status === 409) {
      await loadConversation(currentConversation.value.id)
      showToast('状态已更新，请根据最新状态操作')
    } else {
      showToast((error as Error).message || '操作失败，请稍后再试')
    }
  } finally {
    resolutionActionLoading.value = false
  }
}

const submitPrompt = async () => {
  const text = promptModel.value.trim()
  if (!text || sendingLoading.value) return

  if (!currentConversation.value.id) {
    await createConversation()
  }

  if (hasRunningTask.value) {
    taskStore.setDraftMessage(text)
    showToast('当前分析尚未完成，已为你保留草稿')
    return
  }

  // 立即清空输入框，并乐观插入用户消息
  taskStore.setDraftMessage('')
  sendingLoading.value = true

  const optimisticId = `optimistic-user-${Date.now()}`
  const thinkingId = `optimistic-thinking-${Date.now()}`

  conversationStore.appendMessages([
    {
      id: optimisticId,
      role: 'user',
      messageType: 'text',
      content: text,
      createdAt: new Date().toISOString(),
    },
    {
      id: thinkingId,
      role: 'system',
      messageType: 'text',
      content: isFollowupMode.value ? '正在处理追问…' : '正在识别标的，请稍候…',
      createdAt: new Date().toISOString(),
    },
  ])

  try {
    if (isFollowupMode.value) {
      const response = await conversationsApi.postMessage(currentConversation.value.id, { message: text })
      conversationStore.removeMessageById(optimisticId)
      conversationStore.removeMessageById(thinkingId)
      conversationStore.appendMessages(response.messages)
      conversationStore.updateConversationStatus('report_explaining', currentConversation.value.currentTaskId, response.reportId)
      return
    }

    const response = await conversationsApi.resolve(currentConversation.value.id, { message: text })
    conversationStore.removeMessageById(optimisticId)
    conversationStore.removeMessageById(thinkingId)
    await applyResolutionResponse(response)
  } catch (error) {
    conversationStore.removeMessageById(thinkingId)
    if (axios.isAxiosError(error) && error.code === 'ECONNABORTED') {
      showToast('识别耗时较长，请下拉刷新查看结果，或重新发送')
    } else {
      showToast((error as Error).message || '发送失败，请稍后再试')
    }
  } finally {
    sendingLoading.value = false
  }
}

const openConversation = async (conversationId: string) => {
  try {
    await loadConversation(conversationId)
    conversationStore.setDrawerOpen(false)
    accountMenuOpen.value = false
  } catch (error) {
    showToast((error as Error).message || '加载会话失败')
  }
}

const deleteConversation = async (conversationId: string) => {
  try {
    await conversationsApi.deleteConversation(conversationId)
    conversationStore.removeConversation(conversationId)
    if (currentConversation.value.id === conversationId) {
      conversationStore.resetCurrentConversation()
      taskStore.clearTask()
      const remaining = conversationStore.conversations
      if (remaining.length > 0) {
        await loadConversation(remaining[0].id)
      } else {
        await createConversation()
      }
    }
  } catch (error) {
    showToast((error as Error).message || '删除会话失败')
  }
}

const clearLocalState = () => {
  conversationStore.setConversations([])
  conversationStore.resetCurrentConversation()
  conversationStore.setDrawerOpen(false)
  taskStore.clearTask()
  taskStore.setDraftMessage('')
  authStore.clearAuth()
}

const logout = async () => {
  logoutLoading.value = true
  try {
    await authApi.logout()
  } catch {
    // Backend session may already be invalid; local state still needs clearing.
  } finally {
    clearLocalState()
    accountMenuOpen.value = false
    logoutLoading.value = false
  }
  showToast('已退出登录')
  router.replace({ name: 'Login' })
}

const closeDrawer = () => {
  conversationStore.setDrawerOpen(false)
  accountMenuOpen.value = false
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

watch(
  () => conversationStore.isDrawerOpen,
  open => {
    if (!open) {
      accountMenuOpen.value = false
    }
  }
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
        @click-overlay="closeDrawer"
      >
        <div class="conversation-drawer" @click="accountMenuOpen = false">
          <div class="conversation-drawer__brand">
            <div class="conversation-drawer__brand-top">
              <strong>InsightTrader</strong>
              <button class="conversation-drawer__collapse" type="button" aria-label="收起抽屉" @click.stop="closeDrawer">
                <span class="conversation-drawer__collapse-icon" aria-hidden="true">
                  <span />
                  <span />
                </span>
              </button>
            </div>
            <p class="mobile-muted">在同一个线程里发起分析、查看报告、继续追问。</p>
          </div>

          <van-button block round type="primary" @click="createConversation">开始新对话</van-button>

          <div class="conversation-drawer__groups">
            <section v-for="[label, items] in groupedConversations" :key="label" class="conversation-drawer__group">
              <h3>{{ label }}</h3>
              <div
                v-for="item in items"
                :key="item.id"
                class="conversation-drawer__item"
                :class="{ 'is-active': item.id === currentConversation.id }"
                @click="openConversation(item.id)"
              >
                <div class="conversation-drawer__item-body">
                  <div class="conversation-drawer__item-head">
                    <strong>{{ item.title }}</strong>
                  </div>
                  <small>{{ getConversationStatusLabel(item.status) }}</small>
                </div>
                <button
                  class="conversation-drawer__item-delete"
                  type="button"
                  aria-label="删除会话"
                  @click.stop="deleteConversation(item.id)"
                >
                  <van-icon name="delete-o" />
                </button>
              </div>
            </section>
          </div>

          <div class="conversation-drawer__account">
            <div class="conversation-drawer__account-card" @click.stop>
              <div class="conversation-drawer__account-main">
                <div class="conversation-drawer__account-avatar">{{ accountInitial }}</div>
                <div class="conversation-drawer__account-meta">
                  <strong>{{ accountDisplayName }}</strong>
                </div>
              </div>
              <button
                class="conversation-drawer__account-trigger"
                type="button"
                :aria-expanded="accountMenuOpen"
                aria-label="打开账号菜单"
                @click.stop="accountMenuOpen = !accountMenuOpen"
              >
                <van-icon name="ellipsis" />
              </button>
              <div v-if="accountMenuOpen" class="conversation-drawer__account-menu">
                <button class="conversation-drawer__account-menu-item" type="button" :disabled="logoutLoading" @click="logout">
                  <van-icon name="revoke" />
                  <span>{{ logoutLoading ? '退出中...' : '退出登录' }}</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </van-popup>

      <div class="conversation-page__body">
        <van-pull-refresh v-model="conversationStore.isLoading" @refresh="bootstrap">
          <div v-if="!currentMessages.length" class="conversation-empty">
            <div class="conversation-empty__hero">
              <p class="conversation-empty__eyebrow">InsightTrader Mobile</p>
              <h2>今晚想研究什么？</h2>
              <p class="mobile-muted">用自然语言输入股票、公司或观点。我会先确认分析标的，再进入正式分析流程。</p>
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

              <template v-else-if="message.messageType === 'ticker_resolution'">
                <section class="conversation-inline-card conversation-inline-card--resolution">
                  <span class="conversation-inline-card__eyebrow">标的确认</span>
                  <h3 class="conversation-inline-card__title">{{ getResolutionCardTitle(message) }}</h3>
                  <p class="conversation-inline-card__description">{{ getMessageText(message) }}</p>
                  <p v-if="getResolutionFocusText(message)" class="conversation-inline-card__meta">
                    {{ getResolutionFocusText(message) }}
                  </p>

                  <div
                    v-if="getResolutionStatus(message) === 'need_confirm' && canInteractWithResolution(message)"
                    class="conversation-inline-card__actions"
                  >
                    <van-button
                      size="small"
                      type="primary"
                      :loading="resolutionActionLoading"
                      @click="submitResolutionAction('confirm', getResolutionId(message))"
                    >
                      确认标的
                    </van-button>
                    <van-button
                      size="small"
                      plain
                      :disabled="resolutionActionLoading"
                      @click="submitResolutionAction('restart', getResolutionId(message))"
                    >
                      重新输入
                    </van-button>
                  </div>

                  <div
                    v-else-if="getResolutionStatus(message) === 'need_disambiguation' && canInteractWithResolution(message)"
                    class="conversation-inline-card__actions conversation-inline-card__actions--stack"
                  >
                    <van-button
                      v-for="candidate in getResolutionCandidates(message)"
                      :key="candidate.ticker"
                      size="small"
                      type="primary"
                      plain
                      :disabled="resolutionActionLoading"
                      @click="submitResolutionAction('select', getResolutionId(message), candidate.ticker)"
                    >
                      {{ getCandidateLabel(candidate) }}
                    </van-button>
                    <van-button
                      size="small"
                      plain
                      :disabled="resolutionActionLoading"
                      @click="submitResolutionAction('restart', getResolutionId(message))"
                    >
                      重新输入
                    </van-button>
                  </div>
                </section>
              </template>

              <template v-else>
                <div class="conversation-bubble">
                  <span v-if="message.role !== 'assistant'" class="conversation-bubble__role">
                    {{ message.role === 'user' ? '你' : '系统' }}
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
              @keydown.enter.exact.prevent="submitPrompt"
            />
            <van-button round type="primary" :loading="sendingLoading" @click="submitPrompt">发送</van-button>
          </div>
          <div v-if="composerHint" class="conversation-input__actions">
            <span class="mobile-subtle">{{ composerHint }}</span>
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
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px 8px;
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
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
}

.conversation-page__header-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-align: left;
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

.conversation-inline-card__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 12px;
}

.conversation-inline-card__actions--stack {
  flex-direction: column;
  align-items: flex-start;
}

.conversation-inline-card__meta {
  margin: 8px 0 0;
  color: var(--mobile-color-text-tertiary);
  font-size: 12px;
  line-height: 1.5;
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

.conversation-drawer__brand-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.conversation-drawer__brand strong {
  font-size: 20px;
}

.conversation-drawer__collapse {
  width: 32px;
  height: 32px;
  padding: 0;
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.03);
  color: var(--mobile-color-text-secondary);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.conversation-drawer__collapse-icon {
  width: 14px;
  height: 14px;
  display: grid;
  grid-template-columns: 1fr 3px;
  gap: 3px;
}

.conversation-drawer__collapse-icon span {
  display: block;
  height: 100%;
  border-radius: 3px;
  background: currentColor;
  opacity: 0.9;
}

.conversation-drawer__collapse-icon span:last-child {
  opacity: 0.45;
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
  flex-direction: row;
  align-items: center;
  gap: 8px;
  padding: 12px;
  border: 1px solid var(--mobile-color-border);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.025);
  text-align: left;
  color: var(--mobile-color-text);
  overflow: hidden;
  cursor: pointer;
}

.conversation-drawer__item.is-active {
  border-color: var(--mobile-color-primary);
  background: rgba(93, 139, 255, 0.12);
}

.conversation-drawer__item-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
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

.conversation-drawer__item-delete {
  flex-shrink: 0;
  width: 28px;
  height: 28px;
  padding: 0;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: var(--mobile-color-text-secondary);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.15s ease, background-color 0.15s ease;
}

.conversation-drawer__item:hover .conversation-drawer__item-delete,
.conversation-drawer__item.is-active .conversation-drawer__item-delete {
  opacity: 1;
}

.conversation-drawer__item-delete:hover {
  background: rgba(255, 107, 107, 0.12);
  color: rgba(255, 107, 107, 0.9);
}

.conversation-drawer__account {
  position: relative;
  padding-top: 4px;
}

.conversation-drawer__account-card {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-height: 56px;
  padding: 8px 10px 8px 8px;
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.045);
}

.conversation-drawer__account-main {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 10px;
}

.conversation-drawer__account-avatar {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  flex-shrink: 0;
  color: var(--mobile-color-text);
  font-size: 14px;
  font-weight: 700;
  background: linear-gradient(180deg, rgba(111, 157, 255, 0.9), rgba(79, 121, 255, 0.82));
}

.conversation-drawer__account-meta {
  min-width: 0;
}

.conversation-drawer__account-meta strong {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 15px;
  font-weight: 600;
}

.conversation-drawer__account-trigger {
  width: 34px;
  height: 34px;
  border: 0;
  border-radius: 17px;
  padding: 0;
  background: rgba(255, 255, 255, 0.03);
  color: var(--mobile-color-text-secondary);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.conversation-drawer__account-trigger :deep(.van-icon) {
  font-size: 18px;
}

.conversation-drawer__account-menu {
  position: absolute;
  left: 4px;
  bottom: calc(100% + 12px);
  min-width: 170px;
  padding: 8px;
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 18px;
  background: rgba(62, 64, 71, 0.96);
  box-shadow:
    0 18px 42px rgba(0, 0, 0, 0.34),
    inset 0 1px 0 rgba(255, 255, 255, 0.04);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
}

.conversation-drawer__account-menu::after {
  content: '';
  position: absolute;
  left: 28px;
  bottom: -6px;
  width: 12px;
  height: 12px;
  background: rgba(62, 64, 71, 0.96);
  border-right: 1px solid rgba(255, 255, 255, 0.04);
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
  transform: rotate(45deg);
}

.conversation-drawer__account-menu-item {
  width: 100%;
  border: 0;
  border-radius: 14px;
  padding: 13px 14px;
  background: transparent;
  color: var(--mobile-color-text);
  font-size: 14px;
  text-align: left;
  display: flex;
  align-items: center;
  gap: 10px;
  transition: background-color 0.18s ease;
}

.conversation-drawer__account-menu-item:hover,
.conversation-drawer__account-menu-item:active {
  background: rgba(255, 255, 255, 0.05);
}

.conversation-drawer__account-menu-item :deep(.van-icon) {
  font-size: 16px;
  color: rgba(247, 248, 250, 0.9);
}

.conversation-drawer__account-menu-item:disabled {
  opacity: 0.65;
}

</style>
