<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import DOMPurify from 'dompurify'
import { marked } from 'marked'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { showToast } from 'vant'

import { authApi } from '@api/auth'
import { conversationsApi } from '@api/conversations'
import MobilePageLayout from '@components/layout/MobilePageLayout.vue'
import { useConversationPolling } from '@composables/useConversationPolling'
import { useDrawerPolling } from '@composables/useDrawerPolling'
import { useAuthStore } from '@stores/auth'
import { useConversationStore } from '@stores/conversation'
import type { ConversationMessage, ConversationSummary } from '@/types/conversation'
import {
  MessageType,
  isTickerResolutionContent,
} from '@/types/messageTypes'
import type {
  ResolutionAction,
  ResolutionCandidate,
  ResolutionResponse,
  ResolutionStatus,
} from '@/types/resolution'
import { formatConversationGroup, formatSeconds, formatTimeLabel } from '@utils/format'

const router = useRouter()
const authStore = useAuthStore()
const conversationStore = useConversationStore()
const accountMenuOpen = ref(false)
const logoutLoading = ref(false)
const resolutionActionLoading = ref(false)
const sendingLoading = ref(false)

const promptModel = ref('')
const conversationBodyRef = ref<HTMLElement | null>(null)
const conversationEndRef = ref<HTMLElement | null>(null)
const conversationInputRef = ref<HTMLElement | null>(null)
const isHeaderCompact = ref(false)
const showScrollToBottom = ref(false)
const skipAutoStickMessageId = ref<string | null>(null)

const currentConversation = computed(() => conversationStore.currentConversation)
const currentMessages = computed(() => conversationStore.currentMessages)
const isAnalyzing = computed(() => currentConversation.value.status === 'analyzing')
const taskProgress = computed(() => currentConversation.value.taskProgress ?? null)

const isNearConversationBottom = (threshold = 96) => {
  const element = conversationBodyRef.value
  if (!element) return true
  return element.scrollHeight - element.scrollTop - element.clientHeight < threshold
}

const scrollConversationToBottom = (behavior: ScrollBehavior = 'auto') => {
  const marker = conversationEndRef.value
  if (marker) {
    marker.scrollIntoView({ block: 'end', behavior })
    return
  }

  const element = conversationBodyRef.value
  if (element) {
    element.scrollTo({ top: element.scrollHeight, behavior })
  }
}

const getComposerOffset = () => {
  const composerHeight = conversationInputRef.value?.getBoundingClientRect().height ?? 72
  return composerHeight + 12
}

const scrollMessageAboveComposer = (messageId: string, behavior: ScrollBehavior = 'smooth') => {
  const body = conversationBodyRef.value
  if (!body) return

  const message = body.querySelector<HTMLElement>(`[data-message-id="${messageId}"]`)
  if (!message) return

  const bodyRect = body.getBoundingClientRect()
  const messageRect = message.getBoundingClientRect()
  const desiredBottom = bodyRect.bottom - getComposerOffset()
  const delta = messageRect.bottom - desiredBottom

  if (delta > 0) {
    body.scrollTo({
      top: body.scrollTop + delta,
      behavior,
    })
  }
}

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
  '分析宁德时代',
  '研究腾讯控股最新趋势',
  '帮我看下Apple'
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

const conversationHeaderSubtitleMap: Record<ConversationSummary['status'], string> = {
  idle: '输入标的后开始分析',
  collecting_inputs: '补充信息后继续',
  ready_to_analyze: '可以开始分析',
  analyzing: '正在分析',
  report_ready: '可继续追问',
  report_explaining: '继续解读',
  failed: '分析未完成'
}

const latestTaskStatusId = computed(() => {
  if (!isAnalyzing.value) return null
  const messages = currentMessages.value
  for (let i = messages.length - 1; i >= 0; i--) {
    if (messages[i].messageType === MessageType.TASK_STATUS) {
      return messages[i].id
    }
  }
  return null
})

const isFollowupMode = computed(() =>
  ['report_ready', 'report_explaining'].includes(currentConversation.value.status)
)

const canSubmitPrompt = computed(() =>
  Boolean(promptModel.value.trim()) && !sendingLoading.value && !isAnalyzing.value
)


const currentConversationStatusLabel = computed(
  () => conversationHeaderSubtitleMap[currentConversation.value.status] || '输入标的后开始分析'
)

const accountDisplayName = computed(() => authStore.user?.displayName || authStore.user?.username || '未登录')
const accountInitial = computed(() => accountDisplayName.value.trim().charAt(0).toUpperCase() || 'U')
const isAdmin = computed(() => authStore.isAdmin)

const loadConversation = async (conversationId: string) => {
  const detail = await conversationsApi.getConversation(conversationId)
  conversationStore.setCurrentConversation(detail)
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

const getResolutionContent = (message: ConversationMessage) =>
  isTickerResolutionContent(message.messageType, message.content) ? message.content : null

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
  return resolutionId === activeResolutionId.value && !isAnalyzing.value
}

const applyResolutionResponse = async (response: ResolutionResponse) => {
  conversationStore.appendMessages(response.messages)
  // 重新加载会话以获取最新状态，taskProgress 由后端填充在 ConversationDetail 中
  await loadConversation(currentConversation.value.id)
  if (response.conversationStatus === 'ready_to_analyze') {
    showToast('已识别标的，但当前有分析任务正在进行，请等待完成后重试')
  }
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

  sendingLoading.value = true

  if (!currentConversation.value.id) {
    try {
      await createConversation()
    } catch (error) {
      showToast((error as Error).message || '创建会话失败，请稍后再试')
      sendingLoading.value = false
      return
    }
  }

  if (isAnalyzing.value) {
    sendingLoading.value = false
    return
  }
  promptModel.value = ''

  const optimisticId = `optimistic-user-${Date.now()}`
  const thinkingId = `optimistic-thinking-${Date.now()}`
  skipAutoStickMessageId.value = thinkingId

  conversationStore.appendMessages([
    {
      id: optimisticId,
      role: 'user',
      messageType: MessageType.TEXT,
      content: text,
      createdAt: new Date().toISOString(),
    },
    {
      id: thinkingId,
      role: 'system',
      messageType: MessageType.TEXT,
      content: isFollowupMode.value ? '正在处理追问…' : '正在识别标的，请稍候…',
      createdAt: new Date().toISOString(),
    },
  ])

  await nextTick()
  scrollMessageAboveComposer(optimisticId, 'smooth')
  syncConversationChromeState()

  try {
    if (isFollowupMode.value) {
      const response = await conversationsApi.postMessage(currentConversation.value.id, { message: text })
      conversationStore.removeMessageById(optimisticId)
      conversationStore.removeMessageById(thinkingId)
      conversationStore.appendMessages(response.messages)
      conversationStore.updateConversationStatus('report_explaining')
      return
    }

    const response = await conversationsApi.resolve(currentConversation.value.id, { message: text })
    conversationStore.removeMessageById(optimisticId)
    conversationStore.removeMessageById(thinkingId)
    await applyResolutionResponse(response)
  } catch (error) {
    conversationStore.removeMessageById(optimisticId)
    conversationStore.removeMessageById(thinkingId)
    if (axios.isAxiosError(error) && error.code === 'ECONNABORTED') {
      showToast('识别耗时较长，请稍后查看结果或重新发送')
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
  } catch (error) {
    showToast((error as Error).message || '删除会话失败')
    return
  }

  conversationStore.removeConversation(conversationId)
  if (currentConversation.value.id === conversationId) {
    conversationStore.resetCurrentConversation()
    const remaining = conversationStore.conversations
    if (remaining.length > 0) {
      try {
        await loadConversation(remaining[0].id)
      } catch (error) {
        showToast((error as Error).message || '加载会话失败')
      }
    } else {
      try {
        await createConversation()
      } catch (error) {
        showToast((error as Error).message || '创建会话失败，请稍后再试')
      }
    }
  }
}

const clearLocalState = () => {
  conversationStore.setConversations([])
  conversationStore.resetCurrentConversation()
  conversationStore.setDrawerOpen(false)
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

const openUserManagement = () => {
  closeDrawer()
  void router.push({ name: 'AdminUsers' })
}

useConversationPolling(() => currentConversation.value.id)

useDrawerPolling()

const quickFill = (prompt: string) => {
  promptModel.value = prompt
}

const getConversationStatusLabel = (status: ConversationSummary['status']) =>
  conversationStatusLabelMap[status] || '处理中'

const getMessageText = (message: ConversationMessage) => {
  if (typeof message.content === 'string') return message.content
  return 'text' in message.content ? (message.content.text ?? '') : ''
}


const formatDateTime = (iso: string | null | undefined): string => {
  if (!iso) return ''
  const d = new Date(iso)
  if (isNaN(d.getTime())) return ''
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

const expandedSummaries = ref(new Set<string>())

const isSummaryExpanded = (id: string) => expandedSummaries.value.has(id)

const toggleSummary = (id: string) => {
  const next = new Set(expandedSummaries.value)
  if (next.has(id)) {
    next.delete(id)
  } else {
    next.add(id)
  }
  expandedSummaries.value = next
}

const getSummaryPreview = (text: string) => {
  const first = text.split(/\n\n+/)[0] ?? text
  return first.trim()
}

const INSIGHT_GUIDE_CHIPS = ['主要风险是什么？', '适合什么类型的投资者？', '短期和中长期如何看？', '核心催化剂有哪些？']

const isLatestSummaryCard = (messageId: string): boolean => {
  const summaryMessages = currentMessages.value.filter(
    m => m.messageType === MessageType.SUMMARY_CARD
  )
  if (!summaryMessages.length) return false
  return summaryMessages[summaryMessages.length - 1].id === messageId
}

const submitGuideChip = (chip: string) => {
  promptModel.value = chip
  void submitPrompt()
}

const renderMarkdown = (text: string): string =>
  DOMPurify.sanitize(marked.parse(text, { async: false }) as string, {
    USE_PROFILES: { html: true }
  })

const syncConversationChromeState = () => {
  const element = conversationBodyRef.value
  if (!element) {
    isHeaderCompact.value = false
    showScrollToBottom.value = false
    return
  }

  const nearBottom = isNearConversationBottom()
  isHeaderCompact.value = element.scrollTop > 8
  showScrollToBottom.value = currentMessages.value.length > 0 && !nearBottom
}

const handleConversationScroll = () => {
  syncConversationChromeState()
}

watch(
  () => conversationStore.isDrawerOpen,
  open => {
    if (!open) {
      accountMenuOpen.value = false
    }
  }
)

watch(
  [() => currentConversation.value.id, () => currentMessages.value[currentMessages.value.length - 1]?.id],
  async ([nextConversationId, nextLatestMessageId], [prevConversationId]) => {
    const switchedConversation = nextConversationId !== prevConversationId
    const shouldStickToBottom = switchedConversation || isNearConversationBottom(220)

    await nextTick()

    if (nextLatestMessageId && skipAutoStickMessageId.value === nextLatestMessageId) {
      skipAutoStickMessageId.value = null
      syncConversationChromeState()
      return
    }

    if (shouldStickToBottom) {
      scrollConversationToBottom(switchedConversation ? 'auto' : 'smooth')
    }

    syncConversationChromeState()
  },
  { flush: 'pre' }
)

onMounted(async () => {
  await bootstrap()
  await nextTick()
  syncConversationChromeState()
})
</script>

<template>
  <MobilePageLayout :title="conversationStore.currentTitle" :with-content-padding="false">
    <template #header>
      <div
        class="conversation-page__header"
        :class="{ 'conversation-page__header--compact': isHeaderCompact }"
      >
        <van-button
          plain
          size="small"
          class="conversation-page__icon-button"
          @click="conversationStore.setDrawerOpen(true)"
        >
          <van-icon name="wap-nav" />
        </van-button>
        <div class="conversation-page__header-main">
          <strong class="conversation-page__header-title">{{ conversationStore.currentTitle }}</strong>
          <span class="conversation-page__header-subtitle">{{ currentConversationStatusLabel }}</span>
        </div>
      </div>
    </template>


    <div class="conversation-page">
      <van-popup
        :show="conversationStore.isDrawerOpen"
        position="left"
        :style="{ width: '61.8%', height: '100%' }"
        :lock-scroll="false"
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
            <p class="mobile-muted">围绕同一只股票，持续分析，随时追问。</p>
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
                <button
                  v-if="isAdmin"
                  class="conversation-drawer__account-menu-item"
                  type="button"
                  @click="openUserManagement"
                >
                  <van-icon name="manager-o" />
                  <span>用户管理</span>
                </button>
                <button class="conversation-drawer__account-menu-item" type="button" :disabled="logoutLoading" @click="logout">
                  <van-icon name="revoke" />
                  <span>{{ logoutLoading ? '退出中...' : '退出登录' }}</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </van-popup>

      <div
        ref="conversationBodyRef"
        class="conversation-page__body"
        :class="{ 'conversation-page__body--locked': conversationStore.isDrawerOpen }"
        @scroll.passive="handleConversationScroll"
      >
        <div v-if="!currentMessages.length" class="conversation-empty">
          <div class="conversation-empty__hero">
            <h2>今天想研究什么？</h2>
            <p class="mobile-muted">输入股票、公司信息，我会给出详尽的分析报告。</p>
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
        </div>

        <div v-else class="conversation-stream">
          <article
            v-for="message in currentMessages"
            :key="message.id"
            class="conversation-message"
            :data-message-id="message.id"
            :class="[
              `conversation-message--${message.role}`,
              `conversation-message--${message.messageType}`
            ]"
          >
            <template v-if="message.messageType === MessageType.SUMMARY_CARD">
              <section class="conversation-inline-card conversation-inline-card--summary">
                <span class="conversation-inline-card__eyebrow">研究结果</span>
                <h3 class="conversation-inline-card__title">投资总监的最终决策</h3>
                <div
                  class="conversation-summary conversation-summary--markdown conversation-summary--result"
                  v-html="renderMarkdown(
                    isSummaryExpanded(message.id)
                      ? getMessageText(message)
                      : getSummaryPreview(getMessageText(message))
                  )"
                />
                <button
                  class="conversation-summary__toggle"
                  type="button"
                  :data-expanded="isSummaryExpanded(message.id) ? '' : undefined"
                  @click="toggleSummary(message.id)"
                >
                  {{ isSummaryExpanded(message.id) ? '收起' : '展开全文' }}
                </button>

                <div
                  v-if="isLatestSummaryCard(message.id)"
                  class="conversation-summary__guide"
                >
                  <p class="conversation-summary__guide-text">
                    你有什么想深入了解的？可以直接提问，我将基于分析报告集为你解读。
                  </p>
                  <div class="conversation-summary__guide-chips">
                    <button
                      v-for="chip in INSIGHT_GUIDE_CHIPS"
                      :key="chip"
                      class="conversation-summary__guide-chip"
                      type="button"
                      @click="submitGuideChip(chip)"
                    >
                      {{ chip }}
                    </button>
                  </div>
                </div>
              </section>
            </template>

            <template v-else-if="message.messageType === MessageType.TICKER_RESOLUTION">
              <section
                class="conversation-inline-card conversation-inline-card--resolution"
                :class="{
                  'conversation-inline-card--resolution-error':
                    getResolutionStatus(message) === 'failed' || getResolutionStatus(message) === 'unsupported'
                }"
              >
                  <span class="conversation-inline-card__eyebrow">标的确认</span>
                  <h3 class="conversation-inline-card__title">{{ getResolutionCardTitle(message) }}</h3>
                  <p class="conversation-inline-card__description">{{ getMessageText(message) }}</p>
                  <p v-if="getResolutionFocusText(message)" class="conversation-inline-card__meta">
                    {{ getResolutionFocusText(message) }}
                  </p>

                  <p
                    v-if="getResolutionStatus(message) === 'failed'"
                    class="conversation-inline-card__alert"
                  >
                    请重新输入公司全名或股票代码，例如 AAPL、0700.HK、300750.SZ。
                  </p>
                  <p
                    v-else-if="getResolutionStatus(message) === 'unsupported'"
                    class="conversation-inline-card__alert"
                  >
                    当前仅支持 A 股、港股、美股标的，请重新输入。
                  </p>

                  <div
                    v-else-if="getResolutionStatus(message) === 'need_confirm' && canInteractWithResolution(message)"
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

            <template v-else-if="message.messageType === MessageType.TASK_STATUS">
              <div class="task-status-wrapper">
                <div class="conversation-notice conversation-notice--progress">
                  <span class="conversation-notice__dot" aria-hidden="true" />
                  <p>{{ getMessageText(message) }}</p>
                </div>
                <div
                  v-if="message.id === latestTaskStatusId && taskProgress"
                  class="task-inline-timer"
                >
                  <span>已用 {{ formatSeconds(taskProgress.elapsedTime) }}</span>
                  <span v-if="taskProgress.remainingTime">· 预计剩余 {{ formatSeconds(taskProgress.remainingTime) }}</span>
                </div>
              </div>
            </template>

            <template v-else-if="message.messageType === MessageType.ERROR">
              <div class="conversation-notice conversation-notice--error">
                <span class="conversation-notice__dot" aria-hidden="true">!</span>
                <p>{{ getMessageText(message) }}</p>
              </div>
            </template>

            <template v-else-if="message.messageType === MessageType.INSIGHT_REPLY">
              <div class="conversation-bubble conversation-bubble--insight">
                <div
                  class="conversation-summary conversation-summary--markdown conversation-bubble__markdown"
                  v-html="renderMarkdown(getMessageText(message))"
                />
                <small>{{ formatTimeLabel(message.createdAt) }}</small>
              </div>
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
          <div ref="conversationEndRef" class="conversation-stream__end" aria-hidden="true" />
        </div>
      </div>
      <div v-if="showScrollToBottom" class="conversation-page__scroll-bottom-track" aria-hidden="true">
        <button
          class="conversation-page__scroll-bottom"
          type="button"
          aria-label="跳到底部"
          @click="scrollConversationToBottom('smooth')"
        >
          <van-icon name="down" />
        </button>
      </div>
    </div>

    <template #footer>
      <div ref="conversationInputRef" class="conversation-input">
        <div class="conversation-input__shell">
          <div class="conversation-input__row">
            <van-field
              v-model="promptModel"
              rows="1"
              :autosize="{ minHeight: 24, maxHeight: 112 }"
              type="textarea"
              placeholder="输入股票、公司，或继续追问"
              @keydown.enter.exact.prevent="submitPrompt"
            />
            <van-button
              round
              type="primary"
              class="conversation-input__send"
              :class="{ 'is-ready': canSubmitPrompt }"
              :loading="sendingLoading"
              :disabled="!canSubmitPrompt"
              @click="submitPrompt"
            >
              发送
            </van-button>
          </div>
        </div>
      </div>
    </template>
  </MobilePageLayout>
</template>

<style scoped>
.conversation-page {
  flex: 1;
  position: relative;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.conversation-page__header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px clamp(24px, 6vw, 40px) 6px;
  transition: padding 0.18s ease, gap 0.18s ease;
}

.conversation-page__header--compact {
  gap: 8px;
  padding-top: 5px;
  padding-bottom: 5px;
}

.conversation-page__header :deep(.van-button) {
  min-width: 40px;
  width: 40px;
  height: 40px;
  padding: 0;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.04);
  color: var(--mobile-color-text-secondary);
  border-color: rgba(255, 255, 255, 0.08);
  transition:
    background 0.18s ease,
    border-color 0.18s ease,
    color 0.18s ease,
    transform 0.18s ease;
}

.conversation-page__icon-button :deep(.van-icon) {
  font-size: 18px;
}

.conversation-page__header-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 1px;
}

.conversation-page__header-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-align: left;
  font-size: 15px;
  font-weight: 700;
  line-height: 1.25;
  transition: font-size 0.18s ease, line-height 0.18s ease;
}

.conversation-page__header--compact .conversation-page__header-title {
  font-size: 14px;
}

.conversation-page__header-subtitle {
  color: var(--mobile-color-text-tertiary);
  font-size: 11px;
  line-height: 1.2;
  transition: opacity 0.18s ease, transform 0.18s ease;
}

.conversation-page__header--compact .conversation-page__header-subtitle {
  opacity: 0.88;
  transform: translateY(-0.5px);
}

.conversation-page__body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  -webkit-overflow-scrolling: touch;
  overscroll-behavior: contain;
  padding-left: clamp(24px, 6vw, 40px);
  padding-right: clamp(24px, 6vw, 40px);
  padding-bottom: calc(154px + var(--mobile-safe-bottom));
}

.conversation-page__body--locked {
  overflow: hidden;
}

.conversation-page__scroll-bottom-track {
  position: absolute;
  left: 50%;
  bottom: calc(58px + var(--mobile-safe-bottom));
  z-index: 6;
  width: calc(100% - (2 * clamp(24px, 6vw, 40px)));
  max-width: 480px;
  transform: translateX(-50%);
  display: flex;
  justify-content: flex-end;
  pointer-events: none;
}

.conversation-page__scroll-bottom {
  pointer-events: auto;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 999px;
  background: rgba(27, 29, 35, 0.92);
  color: var(--mobile-color-text-secondary);
  box-shadow: 0 8px 18px rgba(0, 0, 0, 0.2);
  backdrop-filter: blur(10px);
  transform: translateX(50%);
}

.conversation-page__scroll-bottom :deep(.van-icon) {
  font-size: 14px;
}

.conversation-empty {
  width: 100%;
  max-width: 480px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding-top: 34px;
  min-height: calc(100vh - 240px);
  min-height: calc(100svh - 240px);
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
  width: 100%;
  max-width: 480px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px 0 18px;
}

.conversation-stream__end {
  width: 100%;
  height: 1px;
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
  max-width: min(82%, 460px);
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
  box-sizing: border-box;
  padding: 2px 14px 2px 0;
  border: 0;
  border-radius: 0;
  background: transparent;
}

.conversation-message--system .conversation-bubble {
  max-width: 100%;
  box-sizing: border-box;
  padding: 2px 14px 2px 0;
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

.conversation-notice {
  display: flex;
  align-items: baseline;
  gap: 6px;
  padding: 4px 0;
  width: 100%;
}

.conversation-notice p {
  margin: 0;
  font-size: 12px;
  line-height: 1.6;
}

.conversation-notice__dot {
  flex-shrink: 0;
  font-size: 11px;
  font-weight: 700;
  line-height: 1;
  width: 14px;
  text-align: center;
}

.conversation-notice--progress p {
  color: var(--mobile-color-text-tertiary);
}

.conversation-notice--progress .conversation-notice__dot {
  color: var(--mobile-color-text-tertiary);
}

.conversation-notice--progress .conversation-notice__dot::before {
  content: '·';
  font-size: 18px;
}

.task-status-wrapper {
  display: flex;
  flex-direction: column;
  width: 100%;
}

.task-inline-timer {
  display: flex;
  gap: 6px;
  padding: 0 0 4px 20px;
  font-size: 11px;
  line-height: 1.6;
  color: var(--mobile-color-text-tertiary);
  opacity: 0.75;
  overflow: hidden;
}

.conversation-notice--error p {
  color: rgba(255, 107, 107, 0.85);
}

.conversation-notice--error .conversation-notice__dot {
  color: rgba(255, 107, 107, 0.85);
}

.conversation-summary {
  line-height: 1.7;
  white-space: pre-wrap;
}

.conversation-summary--markdown {
  white-space: normal;
  overflow-wrap: break-word;
  word-break: normal;

  :deep(p) {
    margin: 0 0 10px;
    line-height: 1.78;
    &:last-child {
      margin-bottom: 0;
    }
  }

  :deep(h1),
  :deep(h2),
  :deep(h3) {
    font-weight: 700;
    line-height: 1.45;
    margin: 16px 0 6px;
  }

  :deep(h1) {
    font-size: 17px;
  }

  :deep(h2) {
    font-size: 15px;
  }

  :deep(h3) {
    font-size: 14px;
  }

  :deep(ul),
  :deep(ol) {
    padding-left: 20px;
    margin: 6px 0 10px;
  }

  :deep(li) {
    margin: 3px 0;
    line-height: 1.7;
  }

  :deep(strong) {
    font-weight: 700;
  }

  :deep(blockquote) {
    margin: 12px 0;
    padding: 8px 12px;
    border-left: 2px solid rgba(93, 139, 255, 0.42);
    border-radius: 0 12px 12px 0;
    background: rgba(93, 139, 255, 0.05);
    color: var(--mobile-color-text-secondary);
    font-size: 13px;
  }

  :deep(hr) {
    border: 0;
    border-top: 1px solid rgba(255, 255, 255, 0.08);
    margin: 20px 0;
  }

  :deep(code) {
    padding: 1px 6px;
    border-radius: 7px;
    background: rgba(255, 255, 255, 0.06);
    font-size: 0.92em;
  }

  :deep(pre) {
    overflow-x: auto;
    margin: 12px 0;
    padding: 11px 13px;
    border-radius: 14px;
    background: rgba(0, 0, 0, 0.24);
    border: 1px solid rgba(255, 255, 255, 0.06);
  }

  :deep(pre code) {
    padding: 0;
    background: transparent;
  }

  :deep(table) {
    width: 100%;
    border-collapse: collapse;
    margin: 12px 0;
    font-size: 13px;
  }

  :deep(th),
  :deep(td) {
    padding: 8px 10px;
    border: 1px solid rgba(255, 255, 255, 0.08);
    text-align: left;
    vertical-align: top;
  }

  :deep(th) {
    background: rgba(255, 255, 255, 0.04);
    font-weight: 600;
  }
}

.conversation-summary__toggle {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  width: fit-content;
  margin-top: 10px;
  padding: 0;
  background: none;
  border: none;
  font-size: 13px;
  color: var(--van-primary-color, #1989fa);
  cursor: pointer;
  gap: 2px;

  &::after {
    content: '';
    display: inline-block;
    width: 8px;
    height: 8px;
    border-right: 1.5px solid currentColor;
    border-bottom: 1.5px solid currentColor;
    transform: rotate(45deg) translateY(-2px);
    transition: transform 0.2s;
  }

  &[data-expanded]::after {
    transform: rotate(-135deg) translateY(-2px);
  }
}

.conversation-summary__guide {
  margin-top: 14px;
  padding-top: 10px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.conversation-summary__guide-text {
  margin: 0 0 10px;
  font-size: 12px;
  color: var(--mobile-color-text-secondary);
  line-height: 1.5;
}

.conversation-summary__guide-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.conversation-summary__guide-chip {
  display: inline-flex;
  align-items: center;
  padding: 5px 12px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  font-size: 12px;
  color: var(--mobile-color-text-secondary);
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;

  &:active {
    background: rgba(93, 139, 255, 0.12);
    border-color: var(--van-primary-color, #1989fa);
    color: var(--van-primary-color, #1989fa);
  }
}

.conversation-inline-card {
  width: 100%;
  padding: 10px 0 6px;
}

.conversation-inline-card--summary {
  padding: 12px 14px 8px;
  border: 1px solid rgba(93, 139, 255, 0.1);
  border-radius: 18px;
  background: rgba(93, 139, 255, 0.04);
}

.conversation-inline-card__eyebrow {
  display: inline-block;
  margin-bottom: 4px;
  color: var(--mobile-color-text-tertiary);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.02em;
}

.conversation-inline-card__title,
.conversation-inline-card__description {
  margin: 0;
}

.conversation-inline-card__title {
  font-size: 15px;
  line-height: 1.45;
}

.conversation-inline-card__description {
  margin-top: 6px;
  color: var(--mobile-color-text-secondary);
  line-height: 1.6;
}

.conversation-summary--result,
.conversation-bubble__markdown {
  box-sizing: border-box;
  color: var(--mobile-color-text);
  font-size: 15px;
  margin-top: 8px;
}

.conversation-summary--result :deep(p:first-child),
.conversation-bubble__markdown :deep(p:first-child) {
  font-size: 15px;
  line-height: 1.8;
  color: rgba(255, 255, 255, 0.96);
}

.conversation-bubble--insight {
  max-width: 100%;
  padding: 2px 0;
  border: 0;
  border-radius: 0;
  background: transparent;
}

.conversation-inline-card__meta {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--mobile-color-text-secondary);
  opacity: 0.7;
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

.conversation-inline-card--resolution-error {
  border-color: rgba(255, 107, 107, 0.24);
  background: rgba(255, 107, 107, 0.05);
}

.conversation-inline-card__alert {
  margin: 8px 0 0;
  color: rgba(255, 107, 107, 0.85);
  font-size: 13px;
  line-height: 1.6;
}

.conversation-input {
  padding: 6px var(--mobile-space-md) 10px;
}

.conversation-input__shell {
  padding: 6px;
  border-radius: 26px;
  border: 1px solid var(--mobile-color-border);
  background: rgba(27, 29, 35, 0.98);
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.14);
  transition:
    border-color 0.18s ease,
    box-shadow 0.18s ease,
    background 0.18s ease;
}

.conversation-input__shell:focus-within {
  border-color: rgba(93, 139, 255, 0.28);
  background: rgba(27, 29, 35, 0.99);
  box-shadow: 0 10px 22px rgba(0, 0, 0, 0.18);
}

.conversation-input__row {
  display: flex;
  align-items: flex-end;
  gap: 8px;
}

.conversation-input :deep(.van-field) {
  flex: 1;
  padding: 7px 12px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.02);
  transition: background 0.18s ease;
}

.conversation-input__shell:focus-within :deep(.van-field) {
  background: rgba(255, 255, 255, 0.032);
}

.conversation-input :deep(textarea) {
  min-height: 24px;
  max-height: 112px;
  line-height: 1.45;
  font-size: 16px;
  padding-top: 0;
  padding-bottom: 0;
}

.conversation-input :deep(textarea::placeholder) {
  color: var(--mobile-color-text-tertiary);
}

.conversation-input__send {
  min-width: 56px;
  height: 36px;
  padding: 0 14px;
  opacity: 0.64;
  transition:
    opacity 0.18s ease,
    transform 0.18s ease,
    box-shadow 0.18s ease;
}

.conversation-input__send.is-ready {
  opacity: 1;
}

.conversation-input__send.is-ready:active {
  transform: translateY(1px);
}

.conversation-input :deep(.conversation-input__send.van-button--disabled) {
  opacity: 1;
}

.conversation-input :deep(.conversation-input__send .van-button__text) {
  font-size: 14px;
}



.conversation-drawer {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: var(--mobile-space-lg);
  gap: 18px;
  background: var(--mobile-color-bg-elevated);
  overflow-x: hidden;
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
  pointer-events: none;
  transition: opacity 0.15s ease, background-color 0.15s ease;
}

.conversation-drawer__item.is-active .conversation-drawer__item-delete {
  opacity: 1;
  pointer-events: auto;
}

@media (hover: hover) and (pointer: fine) {
  .conversation-drawer__item:hover .conversation-drawer__item-delete {
    opacity: 1;
    pointer-events: auto;
  }
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
