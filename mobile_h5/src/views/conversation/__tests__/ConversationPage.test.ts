import { describe, expect, it, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { defineComponent } from 'vue'

import ConversationPage from '../ConversationPage.vue'
import { useAuthStore } from '@stores/auth'
import { useConversationStore } from '@stores/conversation'
import { MessageType } from '@/types/messageTypes'
import type {
  ConversationDetail,
  ConversationMessage,
  ConversationSummary,
  TaskProgress,
} from '@/types/conversation'

const mockPush = vi.fn()
const mockReplace = vi.fn()
const mockListConversations = vi.fn()
const mockGetConversation = vi.fn()
const mockCreateConversation = vi.fn()
const mockDeleteConversation = vi.fn()
const mockResolve = vi.fn()
const mockPostMessage = vi.fn()
const mockStreamPostMessage = vi.fn()
const mockConfirmResolution = vi.fn()
const mockLogout = vi.fn()

vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: mockPush,
    replace: mockReplace,
  }),
}))

vi.mock('@api/conversations', () => ({
  conversationsApi: {
    listConversations: (...args: unknown[]) => mockListConversations(...args),
    getConversation: (...args: unknown[]) => mockGetConversation(...args),
    createConversation: (...args: unknown[]) => mockCreateConversation(...args),
    deleteConversation: (...args: unknown[]) => mockDeleteConversation(...args),
    resolve: (...args: unknown[]) => mockResolve(...args),
    postMessage: (...args: unknown[]) => mockPostMessage(...args),
    streamPostMessage: (...args: unknown[]) => mockStreamPostMessage(...args),
    confirmResolution: (...args: unknown[]) => mockConfirmResolution(...args),
  },
}))

vi.mock('@api/auth', () => ({
  authApi: {
    logout: (...args: unknown[]) => mockLogout(...args),
  },
}))

vi.mock('@composables/useConversationPolling', () => ({
  useConversationPolling: vi.fn(() => ({
    startPolling: vi.fn(),
    stopPolling: vi.fn(),
  })),
}))

vi.mock('@composables/useDrawerPolling', () => ({
  useDrawerPolling: vi.fn(),
}))

vi.mock('vant', () => ({
  showToast: vi.fn(),
}))

const MobilePageLayoutStub = defineComponent({
  template: `
    <div class="mobile-page-layout-stub">
      <header><slot name="header" /></header>
      <main><slot /></main>
    </div>
  `,
})

const VanButtonStub = defineComponent({
  template: `<button type="button"><slot /></button>`,
})

const VanPopupStub = defineComponent({
  template: `<div class="van-popup-stub"><slot /></div>`,
})

const VanIconStub = defineComponent({
  template: `<i class="van-icon-stub" />`,
})

const VanFieldStub = defineComponent({
  props: {
    modelValue: {
      type: String,
      default: '',
    },
  },
  emits: ['update:modelValue', 'focus', 'blur'],
  template: `
    <input
      class="van-field-stub"
      :value="modelValue"
      @input="$emit('update:modelValue', $event.target.value)"
      @focus="$emit('focus', $event)"
      @blur="$emit('blur', $event)"
    />
  `,
})

const baseConversation: ConversationDetail = {
  id: 'conv-1',
  title: '测试会话',
  status: 'analyzing',
  updatedAt: '2026-04-15T08:30:00.000Z',
  taskProgress: null,
  messages: [],
}

const makeSummary = (detail: ConversationDetail): ConversationSummary => ({
  id: detail.id,
  title: detail.title,
  status: detail.status,
  updatedAt: detail.updatedAt,
})

const createMessage = (
  overrides: Partial<ConversationMessage> & Pick<ConversationMessage, 'id' | 'messageType' | 'content'>
): ConversationMessage => ({
  id: overrides.id,
  role: overrides.role ?? 'assistant',
  messageType: overrides.messageType,
  content: overrides.content,
  createdAt: overrides.createdAt ?? '2026-04-15T08:30:00.000Z',
})

const mountConversationPage = async (detail: ConversationDetail) => {
  mockListConversations.mockResolvedValue([makeSummary(detail)])
  mockGetConversation.mockResolvedValue(detail)
  mockCreateConversation.mockResolvedValue(makeSummary(detail))
  mockDeleteConversation.mockResolvedValue(undefined)
  mockResolve.mockResolvedValue({ messages: [], conversationStatus: detail.status })
  mockPostMessage.mockResolvedValue({ messages: [] })
  mockStreamPostMessage.mockResolvedValue(undefined)
  mockConfirmResolution.mockResolvedValue({ messages: [], conversationStatus: detail.status })
  mockLogout.mockResolvedValue(undefined)

  const wrapper = mount(ConversationPage, {
    global: {
      stubs: {
        MobilePageLayout: MobilePageLayoutStub,
        'van-button': VanButtonStub,
        'van-popup': VanPopupStub,
        'van-icon': VanIconStub,
        'van-field': VanFieldStub,
      },
    },
  })

  await flushPromises()
  return wrapper
}

describe('ConversationPage acceptance', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    mockPush.mockReset()
    mockReplace.mockReset()
    mockListConversations.mockReset()
    mockGetConversation.mockReset()
    mockCreateConversation.mockReset()
    mockDeleteConversation.mockReset()
    mockResolve.mockReset()
    mockPostMessage.mockReset()
    mockStreamPostMessage.mockReset()
    mockConfirmResolution.mockReset()
    mockLogout.mockReset()

    const authStore = useAuthStore()
    authStore.setAuth('token', {
      id: 'admin-1',
      username: 'admin',
      displayName: '管理员',
      role: 'admin',
    })

    const conversationStore = useConversationStore()
    conversationStore.setCurrentConversation({ ...baseConversation })
    conversationStore.setConversations([makeSummary(baseConversation)])
  })

  it('shows unified XiaoI speaker metadata across system message types', async () => {
    const detail: ConversationDetail = {
      ...baseConversation,
      status: 'report_ready',
      messages: [
        createMessage({
          id: 'text-1',
          messageType: MessageType.TEXT,
          content: '普通文本回复',
          createdAt: '2026-04-15T08:31:00.000Z',
        }),
        createMessage({
          id: 'resolution-1',
          messageType: MessageType.TICKER_RESOLUTION,
          content: {
            text: '已为你确认分析标的是 Sandisk Corporation (SNDK)。',
            status: 'resolved',
          },
          createdAt: '2026-04-15T08:32:00.000Z',
        }),
        createMessage({
          id: 'insight-1',
          messageType: MessageType.INSIGHT_REPLY,
          content: '这是进一步解读。',
          createdAt: '2026-04-15T08:33:00.000Z',
        }),
        createMessage({
          id: 'summary-1',
          messageType: MessageType.SUMMARY_CARD,
          content: {
            text: '最终结论内容',
          },
          createdAt: '2026-04-15T08:34:00.000Z',
        }),
        createMessage({
          id: 'error-1',
          messageType: MessageType.ERROR,
          content: {
            text: '分析失败，请稍后重试。',
          },
          createdAt: '2026-04-15T08:35:00.000Z',
        }),
      ],
    }

    const wrapper = await mountConversationPage(detail)
    const metaRows = wrapper.findAll('.conversation-message-meta')

    expect(metaRows).toHaveLength(5)
    for (const row of metaRows) {
      const spans = row.findAll('span')
      expect(spans[0]?.text()).toBe('小I')
      expect(spans[1]?.text()).toMatch(/\d{2}\/\d{2}.+\d{2}:\d{2}/)
    }

    expect(wrapper.text()).not.toContain('研究结果')
    expect(wrapper.text()).not.toContain('标的确认')
  })

  it('renders one task status card with a timeline while hiding generic kickoff status', async () => {
    const messages: ConversationMessage[] = [
      createMessage({
        id: 'task-kickoff',
        role: 'system',
        messageType: MessageType.TASK_STATUS,
        content: { text: '任务已启动', stageId: null },
        createdAt: '2026-04-15T08:31:00.000Z',
      }),
      createMessage({
        id: 'task-market',
        role: 'system',
        messageType: MessageType.TASK_STATUS,
        content: { text: '市场阶段', stageId: 'analysts.market' },
        createdAt: '2026-04-15T08:32:00.000Z',
      }),
      createMessage({
        id: 'task-social',
        role: 'system',
        messageType: MessageType.TASK_STATUS,
        content: { text: '情绪阶段', stageId: 'analysts.social' },
        createdAt: '2026-04-15T08:33:00.000Z',
      }),
      createMessage({
        id: 'task-risk',
        role: 'system',
        messageType: MessageType.TASK_STATUS,
        content: { text: '风险阶段', stageId: 'risk.debate' },
        createdAt: '2026-04-15T08:34:00.000Z',
      }),
    ]

    const detail: ConversationDetail = {
      ...baseConversation,
      status: 'analyzing',
      messages,
      taskProgress: {
        stageId: 'risk.debate',
        nodeId: 'Conservative Analyst',
        displayState: 'active',
        elapsedTime: 60,
        remainingTime: 360,
      },
    }

    const wrapper = await mountConversationPage(detail)

    expect(wrapper.findAll('.task-status-card')).toHaveLength(1)
    expect(wrapper.text()).not.toContain('任务已启动')
    expect(wrapper.find('.task-status-card__title').text()).toBe('风险团队评估保守情景')
    expect(wrapper.find('.task-status-card__state').text()).toBe('进行中')
    expect(wrapper.findAll('.task-status-timeline__item')).toHaveLength(3)
    expect(wrapper.findAll('.task-status-timeline__item.is-current')).toHaveLength(1)
    expect(wrapper.find('.task-status-card__timers').text()).toContain('已用 1分钟')
    expect(wrapper.find('.task-status-card__timers').text()).toContain('预计剩余 6分钟')
  })

  it('turns the task card into done state after analysis completion and clears current highlight', async () => {
    const detail: ConversationDetail = {
      ...baseConversation,
      status: 'report_ready',
      messages: [
        createMessage({
          id: 'task-market',
          role: 'system',
          messageType: MessageType.TASK_STATUS,
          content: { text: '市场阶段', stageId: 'analysts.market' },
          createdAt: '2026-04-15T08:32:00.000Z',
        }),
        createMessage({
          id: 'task-trader',
          role: 'system',
          messageType: MessageType.TASK_STATUS,
          content: { text: '交易计划', stageId: 'trader.plan' },
          createdAt: '2026-04-15T08:33:00.000Z',
        }),
      ],
      taskProgress: {
        stageId: 'risk.debate',
        nodeId: 'Trader',
        displayState: 'active',
        elapsedTime: 180,
        remainingTime: 120,
      },
    }

    const wrapper = await mountConversationPage(detail)

    expect(wrapper.find('.task-status-card').classes()).toContain('is-done')
    expect(wrapper.find('.task-status-card__title').text()).toBe('分析已完成')
    expect(wrapper.find('.task-status-card__state').text()).toBe('已完成')
    expect(wrapper.find('.task-status-card__subtitle').text()).toBe('分析流程已完成，团队已经给出最终结果。')
    expect(wrapper.findAll('.task-status-timeline__item.is-current')).toHaveLength(0)
    expect(wrapper.text()).not.toContain('预计剩余')
  })

  it('uses the updated trader wording for the current task copy', async () => {
    const detail: ConversationDetail = {
      ...baseConversation,
      status: 'analyzing',
      messages: [
        createMessage({
          id: 'task-trader',
          role: 'system',
          messageType: MessageType.TASK_STATUS,
          content: { text: '交易计划', stageId: 'trader.plan' },
          createdAt: '2026-04-15T08:33:00.000Z',
        }),
      ],
      taskProgress: {
        stageId: 'trader.plan',
        nodeId: 'Trader',
        displayState: 'active',
      } as TaskProgress,
    }

    const wrapper = await mountConversationPage(detail)

    expect(wrapper.find('.task-status-card__title').text()).toBe('交易分析师输出交易方案与执行思路')
    expect(wrapper.text()).not.toContain('交易分析师生成交易方案')
  })

  it('keeps short insight replies fully visible without a collapse toggle', async () => {
    const detail: ConversationDetail = {
      ...baseConversation,
      status: 'report_explaining',
      messages: [
        createMessage({
          id: 'insight-short',
          messageType: MessageType.INSIGHT_REPLY,
          content: '结论偏谨慎，短线更适合等回调后再看确认信号。',
          createdAt: '2026-04-15T08:33:00.000Z',
        }),
      ],
    }

    const wrapper = await mountConversationPage(detail)

    expect(wrapper.find('.conversation-bubble__toggle').exists()).toBe(false)
    expect(wrapper.find('.conversation-bubble__markdown-shell').classes()).not.toContain('is-collapsed')
  })

  it('keeps older long insight replies collapsed while leaving the latest expanded', async () => {
    const detail: ConversationDetail = {
      ...baseConversation,
      status: 'report_explaining',
      messages: [
        createMessage({
          id: 'insight-long-old',
          messageType: MessageType.INSIGHT_REPLY,
          content: [
            '先看结论：中期趋势还没有彻底走坏，但短线波动会更大。',
            '第一，市场章节提到价格已经接近前高压力位，继续上冲需要更强成交量配合。',
            '第二，新闻章节显示最新催化更偏情绪驱动，不足以单独支撑估值再扩张。',
            '第三，风险章节强调如果本周财报或指引不及预期，回撤会放大。',
            '第四，交易计划建议不要追高，优先等待回踩确认再考虑分批介入。',
            '第五，如果已经持有，可以把关注点放在量价是否继续背离。',
            '第六，整体上更像高位震荡而不是确定性突破。',
          ].join('\n'),
          createdAt: '2026-04-15T08:33:00.000Z',
        }),
        createMessage({
          id: 'insight-long-latest',
          messageType: MessageType.INSIGHT_REPLY,
          content: [
            '更直接地说，这份报告暂时不支持立刻加仓。',
            '第一，风险收益比没有明显打开。',
            '第二，短线催化和中期基本面之间还有验证空档。',
            '第三，交易计划更偏向等待而不是主动进攻。',
            '第四，如果你要继续追问，可以重点问支撑位、风险点或仓位建议。',
            '第五，目前更适合把它当成观察名单而不是立即执行对象。',
            '第六，等下一次关键信号出来再判断会更稳。',
          ].join('\n'),
          createdAt: '2026-04-15T08:34:00.000Z',
        }),
      ],
    }

    const wrapper = await mountConversationPage(detail)
    const shells = wrapper.findAll('.conversation-bubble__markdown-shell')
    const toggles = wrapper.findAll('.conversation-bubble__toggle')

    expect(shells).toHaveLength(2)
    expect(toggles).toHaveLength(2)
    expect(shells[0]?.classes()).toContain('is-collapsed')
    expect(shells[1]?.classes()).not.toContain('is-collapsed')
  })
})
