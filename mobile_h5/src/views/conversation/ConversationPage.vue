<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import DOMPurify from 'dompurify'
import { marked } from 'marked'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { showToast } from 'vant'

import { authApi } from '@api/auth'
import { conversationsApi } from '@api/conversations'
import type { StreamMessageEvent, StreamResolutionEvent } from '@api/conversations'
import MobilePageLayout from '@components/layout/MobilePageLayout.vue'
import { useConversationPolling } from '@composables/useConversationPolling'
import { useDrawerPolling } from '@composables/useDrawerPolling'
import { useAuthStore } from '@stores/auth'
import { useConversationStore } from '@stores/conversation'
import type { ConversationMessage, ConversationSummary, TaskProgressItem } from '@/types/conversation'
import {
  MessageType,
  isResolutionStreamContent,
  isTaskStatusContent,
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
const isStreamingReply = ref(false)

const promptModel = ref('')
const conversationBodyRef = ref<HTMLElement | null>(null)
const conversationEndRef = ref<HTMLElement | null>(null)
const conversationInputRef = ref<HTMLElement | null>(null)
const isHeaderCompact = ref(false)
const showScrollToBottom = ref(false)
const skipAutoStickMessageId = ref<string | null>(null)
const keyboardOffset = ref(0)
const composerFocused = ref(false)
let composerBlurTimer = 0
let conversationItemClickTimer = 0
let lastConversationItemTap = { id: '', at: 0 }

const currentConversation = computed(() => conversationStore.currentConversation)
const rawMessages = computed(() => conversationStore.currentMessages)
const isAnalyzing = computed(() => currentConversation.value.status === 'analyzing')
const taskProgress = computed(() => currentConversation.value.taskProgress ?? null)

const latestTaskStatusId = computed(() => {
  const messages = rawMessages.value
  for (let i = messages.length - 1; i >= 0; i--) {
    if (messages[i].messageType === MessageType.TASK_STATUS) {
      return messages[i].id
    }
  }
  return null
})

const shouldHideTaskStatusMessage = (message: ConversationMessage) => {
  if (message.messageType !== MessageType.TASK_STATUS) return false
  if (!isTaskStatusContent(message.messageType, message.content)) return false
  return message.content.stageId == null
}

const taskStatusMessages = computed(() =>
  rawMessages.value.filter(
    message =>
      message.messageType === MessageType.TASK_STATUS &&
      !shouldHideTaskStatusMessage(message)
  )
)

const firstTaskStatusId = computed(() => taskStatusMessages.value[0]?.id ?? null)

const shouldRenderTaskStatusCard = (message: ConversationMessage) =>
  message.messageType === MessageType.TASK_STATUS && message.id === firstTaskStatusId.value

const shouldHideTaskStatusEntry = (message: ConversationMessage) =>
  message.messageType === MessageType.TASK_STATUS && message.id !== firstTaskStatusId.value

const currentMessages = computed(() =>
  rawMessages.value.filter(
    message => !shouldHideTaskStatusMessage(message) && !shouldHideTaskStatusEntry(message)
  )
)

const isNearConversationBottom = (threshold = 96) => {
  const element = conversationBodyRef.value
  if (!element) return true
  return element.scrollHeight - element.scrollTop - element.clientHeight < threshold
}

const scrollConversationToBottom = (behavior: ScrollBehavior = 'auto') => {
  const element = conversationBodyRef.value
  if (element) {
    const maxScrollTop = Math.max(0, element.scrollHeight - element.clientHeight)
    element.scrollTo({ top: maxScrollTop, behavior })
  }
}

const updateKeyboardOffset = () => {
  if (typeof window === 'undefined') return

  const viewport = window.visualViewport
  if (!viewport || !composerFocused.value) {
    keyboardOffset.value = 0
    return
  }

  const nextOffset = Math.max(0, window.innerHeight - viewport.height - viewport.offsetTop)
  keyboardOffset.value = nextOffset > 0 ? nextOffset : 0
}

const conversationViewportStyle = computed(() => ({
  '--conversation-keyboard-offset': `${keyboardOffset.value}px`,
}))

const handleComposerFocusIn = () => {
  composerFocused.value = true
  window.clearTimeout(composerBlurTimer)
  updateKeyboardOffset()
}

const handleComposerFocusOut = () => {
  if (typeof window === 'undefined') return

  window.clearTimeout(composerBlurTimer)
  composerBlurTimer = window.setTimeout(() => {
    const activeElement = document.activeElement
    const stillFocused =
      activeElement instanceof HTMLElement && conversationInputRef.value?.contains(activeElement)

    composerFocused.value = Boolean(stillFocused)
    updateKeyboardOffset()
  }, 0)
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
  '研究腾讯控股',
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

const refreshCurrentConversation = async () => {
  if (!currentConversation.value.id) return
  await loadConversation(currentConversation.value.id)
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

const applyResolutionResponse = async (
  response: ResolutionResponse,
  options?: { skipUserMessage?: boolean }
) => {
  const nextMessages =
    options?.skipUserMessage
      ? response.messages.filter(message => message.role !== 'user')
      : response.messages
  conversationStore.appendMessages(nextMessages)
  // 重新加载会话以获取最新状态，taskProgress 由后端填充在 ConversationDetail 中
  await loadConversation(currentConversation.value.id)
  if (response.conversationStatus === 'ready_to_analyze') {
    showToast('已识别标的，但当前有分析任务正在进行，请等待完成后重试')
  }
}

const handleStreamEvent = ({
  event,
  optimisticId,
  thinkingId,
  streamingAssistantId,
}: {
  event: StreamMessageEvent
  optimisticId: string
  thinkingId: string
  streamingAssistantId: string
}) => {
  if (event.event === 'started') {
    conversationStore.removeMessageById(thinkingId)
    conversationStore.removeMessageById(optimisticId)
    conversationStore.upsertMessage(event.userMessage)
    conversationStore.upsertMessage({
      id: thinkingId,
      role: 'system',
      messageType: MessageType.TEXT,
      content: '正在准备回复…',
      createdAt: new Date().toISOString(),
    })
    conversationStore.updateConversationStatus('report_explaining')
    return
  }

  if (event.event === 'routing') {
    conversationStore.upsertMessage({
      id: thinkingId,
      role: 'system',
      messageType: MessageType.TEXT,
      content: '正在组织回复…',
      createdAt: new Date().toISOString(),
    })
    return
  }

  if (event.event === 'delta') {
    conversationStore.removeMessageById(thinkingId)
    conversationStore.removeMessageById(optimisticId)
    const existing = currentMessages.value.find(item => item.id === streamingAssistantId)
    const currentText = existing ? getMessageText(existing) : ''
    conversationStore.upsertMessage({
      id: streamingAssistantId,
      role: 'assistant',
      messageType: MessageType.INSIGHT_REPLY,
      content: `${currentText}${event.text}`,
      createdAt: new Date().toISOString(),
    })
    return
  }

  if (event.event === 'completed') {
    conversationStore.removeMessageById(thinkingId)
    conversationStore.removeMessageById(optimisticId)
    conversationStore.removeMessageById(streamingAssistantId)
    conversationStore.upsertMessage(event.assistantMessage)
    conversationStore.updateConversationStatus('report_explaining')
    return
  }

  if (event.event === 'error') {
    conversationStore.removeMessageById(thinkingId)
    conversationStore.removeMessageById(streamingAssistantId)
    throw new Error(event.message || '流式回复失败，请稍后再试')
  }
}

const handleResolutionStreamEvent = ({
  event,
  optimisticId,
  thinkingId,
  streamingAssistantId,
}: {
  event: StreamResolutionEvent
  optimisticId: string
  thinkingId: string
  streamingAssistantId: string
}): ResolutionResponse | null => {
  if (event.event === 'started') {
    conversationStore.removeMessageById(thinkingId)
    conversationStore.removeMessageById(optimisticId)
    conversationStore.upsertMessage(event.userMessage)
    conversationStore.upsertMessage({
      id: thinkingId,
      role: 'system',
      messageType: MessageType.TEXT,
      content: '正在识别标的，请稍候…',
      createdAt: new Date().toISOString(),
    })
    return null
  }

  if (event.event === 'progress') {
    conversationStore.upsertMessage({
      id: thinkingId,
      role: 'system',
      messageType: MessageType.TEXT,
      content: event.message || '正在识别标的，请稍候…',
      createdAt: new Date().toISOString(),
    })
    return null
  }

  if (event.event === 'delta') {
    conversationStore.removeMessageById(thinkingId)
    const existing = currentMessages.value.find(item => item.id === streamingAssistantId)
    const currentText = existing ? getMessageText(existing) : ''
    conversationStore.upsertMessage({
      id: streamingAssistantId,
      role: 'assistant',
      messageType: MessageType.RESOLUTION_STREAM,
      content: `${currentText}${event.text}`,
      createdAt: new Date().toISOString(),
    })
    return null
  }

  if (event.event === 'completed') {
    conversationStore.removeMessageById(thinkingId)
    conversationStore.removeMessageById(streamingAssistantId)
    return event.response
  }

  if (event.event === 'error') {
    conversationStore.removeMessageById(thinkingId)
    conversationStore.removeMessageById(streamingAssistantId)
    throw new Error(event.message || '流式识别失败，请稍后再试')
  }

  return null
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
  const streamingAssistantId = `optimistic-assistant-${Date.now()}`
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
      stopPolling()
      isStreamingReply.value = true
      let streamingStarted = false
      await conversationsApi.streamPostMessage(currentConversation.value.id, { message: text }, {
        onEvent: (event: StreamMessageEvent) => {
          handleStreamEvent({
            event,
            optimisticId,
            thinkingId,
            streamingAssistantId,
          })
          streamingStarted = true
        }
      })
      if (!streamingStarted) {
        throw new Error('未收到流式回复事件')
      }
      await refreshCurrentConversation()
      return
    }

    let resolutionResponse: ResolutionResponse | null = null
    await conversationsApi.streamResolve(currentConversation.value.id, { message: text }, {
      onEvent: (event: StreamResolutionEvent) => {
        const nextResponse = handleResolutionStreamEvent({
          event,
          optimisticId,
          thinkingId,
          streamingAssistantId,
        })
        if (nextResponse) resolutionResponse = nextResponse
      }
    })
    if (!resolutionResponse) {
      throw new Error('未收到标的识别结果')
    }
    conversationStore.removeMessageById(optimisticId)
    conversationStore.removeMessageById(thinkingId)
    conversationStore.removeMessageById(streamingAssistantId)
    await applyResolutionResponse(resolutionResponse, { skipUserMessage: true })
  } catch (error) {
    conversationStore.removeMessageById(optimisticId)
    conversationStore.removeMessageById(thinkingId)
    conversationStore.removeMessageById(streamingAssistantId)
    if (axios.isAxiosError(error) && error.code === 'ECONNABORTED') {
      showToast('识别耗时较长，请稍后查看结果或重新发送')
    } else {
      showToast((error as Error).message || '发送失败，请稍后再试')
    }
  } finally {
    isStreamingReply.value = false
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

const handleConversationItemClick = (conversationId: string) => {
  const now = Date.now()
  const isDoubleTap =
    lastConversationItemTap.id === conversationId && now - lastConversationItemTap.at < 320

  lastConversationItemTap = { id: conversationId, at: now }

  if (isDoubleTap) {
    window.clearTimeout(conversationItemClickTimer)
    void copyConversationId(conversationId)
    return
  }

  window.clearTimeout(conversationItemClickTimer)
  conversationItemClickTimer = window.setTimeout(() => {
    void openConversation(conversationId)
  }, 220)
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

const { stopPolling } = useConversationPolling(() => currentConversation.value.id)

useDrawerPolling()

const quickFill = (prompt: string) => {
  promptModel.value = prompt
}

const copyConversationId = async (conversationId: string) => {
  try {
    if (navigator?.clipboard?.writeText) {
      await navigator.clipboard.writeText(conversationId)
      showToast('会话 ID 已复制')
      return
    }

    const textarea = document.createElement('textarea')
    textarea.value = conversationId
    textarea.setAttribute('readonly', 'true')
    textarea.style.position = 'fixed'
    textarea.style.opacity = '0'
    textarea.style.pointerEvents = 'none'
    textarea.style.left = '-9999px'
    document.body.appendChild(textarea)
    textarea.focus()
    textarea.select()
    textarea.setSelectionRange(0, conversationId.length)

    const copied = document.execCommand('copy')
    document.body.removeChild(textarea)
    if (!copied) {
      throw new Error('copy command failed')
    }

    showToast('会话 ID 已复制')
  } catch {
    showToast('复制失败，请检查浏览器剪贴板权限')
  }
}

const getConversationStatusLabel = (status: ConversationSummary['status']) =>
  conversationStatusLabelMap[status] || '处理中'

const getMessageText = (message: ConversationMessage) => {
  if (typeof message.content === 'string') return message.content
  return 'text' in message.content ? (message.content.text ?? '') : ''
}

const stageStatusCopyMap: Record<string, string> = {
  'analysts.market': '市场分析师梳理价格走势与技术信号',
  'analysts.social': '情绪分析师整理社交舆情与市场情绪',
  'analysts.news': '新闻分析师整理近期关键事件与新闻影响',
  'analysts.fundamentals': '基本面分析师梳理财务表现、盈利与估值',
  'research.debate': '研究团队汇总多方观点并形成研究结论',
  'trader.plan': '交易分析师输出交易方案与执行思路',
  'risk.debate': '风险团队评估下行风险与仓位约束',
  'portfolio.decision': '投资总监输出最终投资决策',
  'decision.finalize': '投资总监输出最终投资决策'
}

const nodeStatusCopyMap: Record<string, string> = {
  'Market Analyst': '市场分析师梳理价格走势与技术信号',
  'Social Analyst': '情绪分析师整理社交舆情与市场情绪',
  'Social Media Analyst': '情绪分析师整理社交舆情与市场情绪',
  'News Analyst': '新闻分析师整理近期关键事件',
  'Fundamentals Analyst': '基本面分析师梳理财务表现与估值',
  'Bull Researcher': '研究团队形成看多观点',
  'Bear Researcher': '研究团队形成看空观点',
  'Research Manager': '研究团队汇总讨论结论',
  Trader: '交易分析师输出交易方案与执行思路',
  'Aggressive Analyst': '风险团队评估积极情景',
  'Conservative Analyst': '风险团队评估保守情景',
  'Neutral Analyst': '风险团队评估中性情景',
  'Portfolio Manager': '投资总监输出最终结论',
  'Decision Manager': '投资总监输出最终结论'
}

const getTaskStatusCopy = (stageId?: string | null, nodeId?: string | null, fallback?: string) => {
  if (nodeId) {
    if (nodeId.startsWith('tools_')) return '投资团队补充数据与公开信息'
    if (!nodeId.startsWith('Msg Clear ')) {
      const nodeCopy = nodeStatusCopyMap[nodeId]
      if (nodeCopy) return nodeCopy
    }
  }

  if (stageId) {
    const stageCopy = stageStatusCopyMap[stageId]
    if (stageCopy) return stageCopy
  }

  return fallback || '投资团队推进分析'
}

const getSpeakerLabel = (message: ConversationMessage) => {
  if (message.role === 'user') return '你'
  if (message.messageType === MessageType.TASK_STATUS) return '投资团队'
  return '小I'
}

const taskStatusStateLabelMap: Record<string, string> = {
  pending: '准备中',
  active: '进行中',
  stalled: '处理中',
  done: '已完成',
  failed: '未完成'
}

const getTaskStatusState = () => {
  if (currentConversation.value.status === 'report_ready') return 'done'
  if (currentConversation.value.status === 'report_explaining') return 'done'
  if (currentConversation.value.status === 'failed') return 'failed'
  if (taskProgress.value?.displayState) return taskProgress.value.displayState
  return 'active'
}

const getStageGroup = (stageId?: string | null) => stageId?.split('.')[0] || ''

const isParallelAnalystStage = (stageId?: string | null) => getStageGroup(stageId) === 'analysts'

const taskStageSnapshot = computed(() => taskProgress.value?.stageSnapshot || {})

const isLatestTaskStatusMessage = (message: ConversationMessage) =>
  message.id === latestTaskStatusId.value

const getTaskStatusTimelineItems = () =>
  taskStatusMessages.value.map(message => {
    const content = isTaskStatusContent(message.messageType, message.content) ? message.content : null
    const state = getTaskStatusState()
    const messageStageId = content?.stageId
    const currentStageId = taskProgress.value?.stageId
    const snapshotState = messageStageId ? taskStageSnapshot.value[messageStageId] : undefined
    const isCurrentAnalystGroup =
      state !== 'done' &&
      state !== 'failed' &&
      isParallelAnalystStage(currentStageId) &&
      isParallelAnalystStage(messageStageId) &&
      (snapshotState === 'in_progress' || snapshotState === 'stalled')
    const visualState =
      snapshotState === 'completed'
        ? 'done'
        : snapshotState === 'failed'
          ? 'failed'
          : snapshotState === 'pending'
            ? 'pending'
            : isCurrentAnalystGroup || isLatestTaskStatusMessage(message)
              ? state
              : 'done'
    return {
      id: message.id,
      stageId: messageStageId,
      title: getTaskStatusCopy(content?.stageId, null, getMessageText(message)),
      time: formatTimeLabel(message.createdAt),
      createdAt: message.createdAt,
      visualState,
      isCurrent: visualState === 'active' || visualState === 'stalled'
    }
  })

const getCurrentTaskTimelineItems = () => getTaskStatusTimelineItems().filter(item => item.isCurrent)

const getTaskProgressItems = (): TaskProgressItem[] => {
  if (taskProgress.value?.tasks?.length) {
    return taskProgress.value.tasks
  }
  return getTaskStatusTimelineItems().map(item => ({
      stageId: item.stageId || item.id,
      label: item.title,
      status:
      item.visualState === 'done'
        ? 'completed'
        : item.visualState === 'failed'
          ? 'failed'
          : item.visualState === 'stalled'
            ? 'stalled'
            : item.visualState === 'active'
            ? 'in_progress'
              : 'pending',
      completedAt: item.visualState === 'done' ? item.createdAt : undefined,
  }))
}

const getTaskItemTimeLabel = (item: TaskProgressItem) =>
  item.completedAt ? formatTimeLabel(item.completedAt) : ''

const getTaskItemStatusLabel = (item: TaskProgressItem) => {
  if (item.status === 'completed') return getTaskItemTimeLabel(item)
  if (item.status === 'failed') return '未完成'
  if (item.status === 'in_progress' || item.status === 'stalled') return '工作中'
  return '待完成'
}

const getCompletedTaskCount = () =>
  getTaskProgressItems().filter(item => item.status === 'completed').length

const getTaskFooterText = () => {
  const total = getTaskProgressItems().length
  const completed = getCompletedTaskCount()
  const state = getTaskStatusState()
  if (state === 'done') {
    return `已完成，耗时 ${formatSeconds(taskProgress.value?.elapsedTime)}`
  }
  if (state === 'failed') {
    return `未完成，已用 ${formatSeconds(taskProgress.value?.elapsedTime)}`
  }
  return `已完成 ${completed} / ${total}，已用 ${formatSeconds(taskProgress.value?.elapsedTime)}`
}

const getTaskStatusSublineForStage = (stageId?: string | null, currentCount = 1) => {
  if (getTaskStatusState() === 'failed') return '分析流程已中断，你可以稍后重新发起。'
  if (getTaskStatusState() === 'done') return '分析流程已完成，团队已经给出最终结果。'
  if (getTaskStatusState() === 'stalled') return '处理时间比平时更长，但任务仍在继续。'
  if (currentCount > 1 && isParallelAnalystStage(stageId)) {
    return '该分析视角正在与其他分析师并行处理，完成后会统一汇总为最终结论。'
  }
  return '投资团队正在持续处理数据、观点和风险信息。'
}

const getTaskStatusCardItems = () => {
  const state = getTaskStatusState()
  if (state === 'done' || state === 'failed') {
    return [
      {
        id: 'task-status-overall',
        stageId: taskProgress.value?.stageId,
        title: getCurrentTaskStatusHeadline(),
        subtitle: getCurrentTaskStatusSubline(),
        state,
        time: '',
      },
    ]
  }

  const currentItems = getCurrentTaskTimelineItems()
  if (currentItems.length > 0) {
    return currentItems.map(item => ({
      id: item.id,
      stageId: item.stageId,
      title: item.title,
      subtitle: getTaskStatusSublineForStage(item.stageId, currentItems.length),
      state: item.visualState,
      time: item.time,
    }))
  }

  return [
    {
      id: 'task-status-fallback',
      stageId: taskProgress.value?.stageId,
      title: getCurrentTaskStatusHeadline(),
      subtitle: getCurrentTaskStatusSubline(),
      state,
      time: '',
    },
  ]
}

const getCurrentTaskStatusHeadline = () => {
  const state = getTaskStatusState()
  if (state === 'done') return '分析已完成'
  if (state === 'failed') return '分析未能完成'
  const currentItems = getCurrentTaskTimelineItems()
  if (currentItems.length > 1) {
    return '投资团队并行推进多路分析'
  }
  return (
    getTaskStatusCopy(taskProgress.value?.stageId, taskProgress.value?.nodeId) ||
    taskProgress.value?.currentStep ||
    taskProgress.value?.message ||
    currentItems[0]?.title ||
    '投资团队推进分析'
  )
}

const getCurrentTaskStatusSubline = () => {
  const state = getTaskStatusState()
  if (state === 'failed') return '分析流程已中断，你可以稍后重新发起。'
  if (state === 'done') return '分析流程已完成，团队已经给出最终结果。'
  if (state === 'stalled') return '处理时间比平时更长，但任务仍在继续。'
  if (getCurrentTaskTimelineItems().length > 1) {
    return '多个分析视角正在并行处理，完成后会统一汇总为最终结论。'
  }
  return '投资团队正在持续处理数据、观点和风险信息。'
}

const getTaskStatusStateForMessage = (message: ConversationMessage) => {
  const content = isTaskStatusContent(message.messageType, message.content) ? message.content : null
  const state = getTaskStatusState()
  const snapshotState = content?.stageId ? taskStageSnapshot.value[content.stageId] : undefined
  if (snapshotState === 'completed') return 'done'
  if (snapshotState === 'failed') return 'failed'
  if (snapshotState === 'pending') return 'pending'
  if (snapshotState === 'in_progress') return state
  if (snapshotState === 'stalled') return 'stalled'
  if (
    state !== 'done' &&
    state !== 'failed' &&
    isParallelAnalystStage(taskProgress.value?.stageId) &&
    isParallelAnalystStage(content?.stageId)
  ) {
    return state
  }
  if (!isLatestTaskStatusMessage(message)) return 'done'
  return getTaskStatusState()
}

const isExpandedTaskStatusMessage = (message: ConversationMessage) =>
  isLatestTaskStatusMessage(message) && getTaskStatusStateForMessage(message) !== 'done'

const getTaskStatusStateLabel = (message: ConversationMessage) =>
  taskStatusStateLabelMap[getTaskStatusStateForMessage(message)] || taskStatusStateLabelMap.active

const shouldShowRemainingTime = computed(() => {
  const remaining = taskProgress.value?.remainingTime
  return typeof remaining === 'number' && remaining > 0 && getTaskStatusState() !== 'failed'
})

const shouldShowTaskStatusTimers = computed(() => {
  if (!taskProgress.value) return false
  const state = getTaskStatusState()
  return state !== 'done' && state !== 'failed'
})


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

const INSIGHT_GUIDE_CHIPS = ['可以买吗？', '要不要卖？', '能不能持有？', '主要风险是什么？']

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
    const shouldStickToBottom =
      switchedConversation || (!isStreamingReply.value && isNearConversationBottom(220))

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
  if (typeof window !== 'undefined') {
    window.visualViewport?.addEventListener('resize', updateKeyboardOffset)
    window.visualViewport?.addEventListener('scroll', updateKeyboardOffset)
  }

  await bootstrap()
  await nextTick()
  updateKeyboardOffset()
  syncConversationChromeState()
})

onUnmounted(() => {
  if (typeof window === 'undefined') return

  window.clearTimeout(composerBlurTimer)
  window.clearTimeout(conversationItemClickTimer)
  lastConversationItemTap = { id: '', at: 0 }
  window.visualViewport?.removeEventListener('resize', updateKeyboardOffset)
  window.visualViewport?.removeEventListener('scroll', updateKeyboardOffset)
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


    <div class="conversation-page" :style="conversationViewportStyle">
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
                @click="handleConversationItemClick(item.id)"
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
                <div class="conversation-message-meta conversation-message-meta--card">
                  <span>{{ getSpeakerLabel(message) }}</span>
                  <span>{{ formatTimeLabel(message.createdAt) }}</span>
                </div>
                <h3 class="conversation-inline-card__title">投资总监的最终决策</h3>
                <div
                  class="conversation-summary conversation-summary--markdown conversation-summary--result"
                  v-html="renderMarkdown(
                    isSummaryExpanded(message.id)
                      ? getMessageText(message)
                      : getSummaryPreview(getMessageText(message))
                  )"
                />
                <div class="conversation-summary__actions">
                  <button
                    class="conversation-summary__toggle"
                    type="button"
                    :data-expanded="isSummaryExpanded(message.id) ? '' : undefined"
                    @click="toggleSummary(message.id)"
                  >
                    {{ isSummaryExpanded(message.id) ? '收起' : '展开全文' }}
                  </button>
                </div>

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
                  <div class="conversation-message-meta conversation-message-meta--card">
                    <span>{{ getSpeakerLabel(message) }}</span>
                    <span>{{ formatTimeLabel(message.createdAt) }}</span>
                  </div>
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
              <div v-if="shouldRenderTaskStatusCard(message)" class="task-status-wrapper">
                <div
                  class="task-status-card"
                  :class="`is-${getTaskStatusState()}`"
                >
                  <div
                    v-for="item in getTaskProgressItems()"
                    :key="item.stageId"
                    class="task-status-list__item"
                    :class="`is-${item.status}`"
                  >
                    <span class="task-status-list__dot" aria-hidden="true" />
                    <p class="task-status-list__label">{{ item.label }}</p>
                    <span class="task-status-list__status">{{ getTaskItemStatusLabel(item) }}</span>
                  </div>
                  <div class="task-status-card__footer">
                    {{ getTaskFooterText() }}
                  </div>
                </div>
              </div>
            </template>

            <template v-else-if="message.messageType === MessageType.ERROR">
              <div class="conversation-bubble conversation-bubble--error">
                <div class="conversation-message-meta">
                  <span>{{ getSpeakerLabel(message) }}</span>
                  <span>{{ formatTimeLabel(message.createdAt) }}</span>
                </div>
                <p>{{ getMessageText(message) }}</p>
              </div>
            </template>

            <template v-else-if="message.messageType === MessageType.INSIGHT_REPLY">
              <div class="conversation-bubble conversation-bubble--insight">
                <div class="conversation-message-meta">
                  <span>{{ getSpeakerLabel(message) }}</span>
                  <span>{{ formatTimeLabel(message.createdAt) }}</span>
                </div>
                <div class="conversation-bubble__markdown-shell">
                  <div
                    class="conversation-summary conversation-summary--markdown conversation-bubble__markdown"
                    v-html="renderMarkdown(getMessageText(message))"
                  />
                </div>
              </div>
            </template>

            <template v-else-if="message.messageType === MessageType.RESOLUTION_STREAM">
              <div class="conversation-bubble conversation-bubble--resolution-stream">
                <div class="conversation-message-meta">
                  <span>{{ getSpeakerLabel(message) }}</span>
                  <span>{{ formatTimeLabel(message.createdAt) }}</span>
                </div>
                <p>{{ isResolutionStreamContent(message.messageType, message.content) ? message.content : getMessageText(message) }}</p>
              </div>
            </template>

            <template v-else>
              <div class="conversation-bubble">
                <div class="conversation-message-meta">
                  <span>{{ getSpeakerLabel(message) }}</span>
                  <span>{{ formatTimeLabel(message.createdAt) }}</span>
                </div>
                <p>{{ getMessageText(message) }}</p>
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
      <div
        ref="conversationInputRef"
        class="conversation-input"
        :style="conversationViewportStyle"
        @focusin="handleComposerFocusIn"
        @focusout="handleComposerFocusOut"
      >
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
  --conversation-keyboard-offset: 0px;
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
  padding-bottom: calc(154px + var(--mobile-safe-bottom) + var(--conversation-keyboard-offset));
}

.conversation-page__body--locked {
  overflow: hidden;
}

.conversation-page__scroll-bottom-track {
  position: absolute;
  left: 50%;
  bottom: calc(58px + var(--mobile-safe-bottom) + var(--conversation-keyboard-offset));
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
.conversation-summary {
  margin: 0;
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

.conversation-message-meta {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 10px;
  margin-bottom: 6px;
  color: var(--mobile-color-text-tertiary);
  font-size: 11px;
  line-height: 1.4;
  font-weight: 600;
}

.conversation-message-meta--card {
  margin-bottom: 8px;
}

.conversation-message-meta span:last-child {
  flex-shrink: 0;
  opacity: 0.8;
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

.task-status-wrapper {
  display: flex;
  flex-direction: column;
  width: 100%;
  gap: 6px;
}

.task-status-card {
  width: 100%;
  padding: 12px 14px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.03);
}

.task-status-list__item {
  display: flex;
  align-items: center;
  gap: 10px;
}

.task-status-list__item + .task-status-list__item {
  margin-top: 10px;
}

.task-status-list__dot {
  width: 10px;
  height: 10px;
  border-radius: 999px;
  flex-shrink: 0;
  background: rgba(255, 255, 255, 0.18);
  box-shadow: 0 0 0 4px rgba(255, 255, 255, 0.04);
}

.task-status-list__item.is-completed .task-status-list__dot {
  background: rgba(69, 214, 156, 0.92);
  box-shadow: 0 0 0 4px rgba(69, 214, 156, 0.12);
}

.task-status-list__item.is-failed .task-status-list__dot {
  background: rgba(255, 107, 107, 0.92);
  box-shadow: 0 0 0 4px rgba(255, 107, 107, 0.12);
}

.task-status-list__item.is-in_progress .task-status-list__dot,
.task-status-list__item.is-stalled .task-status-list__dot {
  position: relative;
  background: transparent;
  box-shadow: none;
}

.task-status-list__item.is-in_progress .task-status-list__dot::before,
.task-status-list__item.is-stalled .task-status-list__dot::before {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  width: 2px;
  height: 2px;
  border-radius: 999px;
  background: rgba(93, 139, 255, 0.98);
  transform: translate(-50%, -50%);
  box-shadow:
    0 -4px 0 0 rgba(93, 139, 255, 1),
    2.8px -2.8px 0 0 rgba(93, 139, 255, 0.9),
    4px 0 0 0 rgba(93, 139, 255, 0.78),
    2.8px 2.8px 0 0 rgba(93, 139, 255, 0.62),
    0 4px 0 0 rgba(93, 139, 255, 0.48),
    -2.8px 2.8px 0 0 rgba(93, 139, 255, 0.36),
    -4px 0 0 0 rgba(93, 139, 255, 0.28),
    -2.8px -2.8px 0 0 rgba(93, 139, 255, 0.2);
  filter: drop-shadow(0 0 4px rgba(93, 139, 255, 0.22));
  animation: task-status-spinner 0.8s linear infinite;
}

.task-status-list__item.is-in_progress .task-status-list__dot::after,
.task-status-list__item.is-stalled .task-status-list__dot::after {
  content: '';
  position: absolute;
  inset: 2px;
  border-radius: 999px;
  background: rgba(93, 139, 255, 0.18);
  box-shadow: 0 0 6px rgba(93, 139, 255, 0.2);
}

.task-status-list__label {
  flex: 1;
  min-width: 0;
  margin: 0;
  color: var(--mobile-color-text);
  font-size: 13px;
  line-height: 1.55;
}

.task-status-list__item.is-in_progress .task-status-list__label,
.task-status-list__item.is-stalled .task-status-list__label {
  font-weight: 600;
}

.task-status-list__status {
  flex-shrink: 0;
  color: var(--mobile-color-text-tertiary);
  font-size: 11px;
  line-height: 1.5;
}

.task-status-list__item.is-in_progress .task-status-list__status,
.task-status-list__item.is-stalled .task-status-list__status {
  color: rgba(185, 211, 255, 0.96);
  font-weight: 600;
}

.task-status-card__footer {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  color: var(--mobile-color-text-tertiary);
  font-size: 12px;
  line-height: 1.6;
}

@keyframes task-status-pulse {
  0%,
  100% {
    transform: scale(1);
    opacity: 1;
    box-shadow:
      0 0 0 4px rgba(93, 139, 255, 0.18),
      0 0 14px rgba(93, 139, 255, 0.42);
  }

  35% {
    transform: scale(1.18);
    opacity: 1;
    box-shadow:
      0 0 0 8px rgba(93, 139, 255, 0.14),
      0 0 22px rgba(93, 139, 255, 0.52);
  }

  70% {
    transform: scale(0.92);
    opacity: 0.82;
    box-shadow:
      0 0 0 5px rgba(93, 139, 255, 0.1),
      0 0 12px rgba(93, 139, 255, 0.3);
  }
}

@keyframes task-status-spinner {
  from {
    transform: rotate(0deg);
  }

  to {
    transform: rotate(360deg);
  }
}

.conversation-notice--error p {
  color: rgba(255, 107, 107, 0.85);
}

.conversation-notice--error .conversation-notice__dot {
  color: rgba(255, 107, 107, 0.85);
}

.conversation-bubble--error p {
  color: rgba(255, 210, 210, 0.96);
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
  display: inline-flex;
  align-items: center;
  justify-content: flex-end;
  flex-shrink: 0;
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

.conversation-summary__actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 10px;
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
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.conversation-summary__guide-chip {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 34px;
  width: 100%;
  padding: 0 10px;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 999px;
  font-size: 12px;
  font-weight: 500;
  color: var(--mobile-color-text-secondary);
  line-height: 1.15;
  text-align: center;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s, transform 0.15s;

  &:active {
    background: rgba(93, 139, 255, 0.12);
    border-color: var(--van-primary-color, #1989fa);
    color: var(--van-primary-color, #1989fa);
    transform: scale(0.98);
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

.conversation-bubble__markdown-shell {
  position: relative;
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
  padding: 6px var(--mobile-space-md) calc(10px + var(--conversation-keyboard-offset));
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
