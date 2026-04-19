import { describe, expect, it, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { defineComponent } from 'vue'

import ConversationPage from '../ConversationPage.vue'
import type { StreamMessageEvent } from '@api/conversations'
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
const mockStreamResolve = vi.fn()
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
    streamResolve: (...args: unknown[]) => mockStreamResolve(...args),
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
      <footer><slot name="footer" /></footer>
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
  mockStreamResolve.mockResolvedValue(undefined)
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
    Object.defineProperty(HTMLElement.prototype, 'scrollTo', {
      configurable: true,
      value: vi.fn(),
    })

    setActivePinia(createPinia())
    mockPush.mockReset()
    mockReplace.mockReset()
    mockListConversations.mockReset()
    mockGetConversation.mockReset()
    mockCreateConversation.mockReset()
    mockDeleteConversation.mockReset()
    mockResolve.mockReset()
    mockStreamResolve.mockReset()
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
    expect(wrapper.findAll('.task-status-list__item')).toHaveLength(3)
    expect(wrapper.findAll('.task-status-list__label').map(node => node.text())).toEqual([
      '市场分析师梳理价格走势与技术信号',
      '情绪分析师整理社交舆情与市场情绪',
      '风险团队评估下行风险与仓位约束',
    ])
    expect(wrapper.findAll('.task-status-list__status').map(node => node.text())).toEqual([
      '04/15 16:32',
      '04/15 16:33',
      '工作中',
    ])
    expect(wrapper.find('.task-status-card__footer').text()).toContain('已完成 2 / 3')
    expect(wrapper.find('.task-status-card__footer').text()).toContain('已用 1分钟')
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
    expect(wrapper.find('.task-status-card__footer').text()).toContain('已完成，耗时')
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

    expect(wrapper.find('.task-status-list__label').text()).toBe('交易分析师输出交易方案与执行思路')
    expect(wrapper.text()).not.toContain('交易分析师生成交易方案')
  })

  it('keeps multiple analyst timeline items active when analyst stages run in parallel', async () => {
    const detail: ConversationDetail = {
      ...baseConversation,
      status: 'analyzing',
      messages: [
        createMessage({
          id: 'task-market',
          role: 'system',
          messageType: MessageType.TASK_STATUS,
          content: { text: '市场阶段', stageId: 'analysts.market' },
          createdAt: '2026-04-15T08:32:00.000Z',
        }),
        createMessage({
          id: 'task-news',
          role: 'system',
          messageType: MessageType.TASK_STATUS,
          content: { text: '新闻阶段', stageId: 'analysts.news' },
          createdAt: '2026-04-15T08:33:00.000Z',
        }),
        createMessage({
          id: 'task-fundamentals',
          role: 'system',
          messageType: MessageType.TASK_STATUS,
          content: { text: '基本面阶段', stageId: 'analysts.fundamentals' },
          createdAt: '2026-04-15T08:34:00.000Z',
        }),
      ],
      taskProgress: {
        stageId: 'analysts.market',
        nodeId: 'Market Analyst',
        stageSnapshot: {
          'analysts.market': 'in_progress',
          'analysts.news': 'in_progress',
          'analysts.fundamentals': 'pending',
          'decision.finalize': 'pending',
        },
        displayState: 'active',
        elapsedTime: 45,
        remainingTime: 180,
      },
    }

    const wrapper = await mountConversationPage(detail)

    expect(wrapper.findAll('.task-status-card')).toHaveLength(1)
    expect(wrapper.findAll('.task-status-list__label').map(node => node.text())).toEqual([
      '市场分析师梳理价格走势与技术信号',
      '新闻分析师整理近期关键事件与新闻影响',
      '基本面分析师梳理财务表现、盈利与估值',
    ])
    expect(wrapper.findAll('.task-status-list__status').map(node => node.text())).toEqual([
      '工作中',
      '工作中',
      '待完成',
    ])
    expect(wrapper.find('.task-status-card__footer').text()).toContain('已完成 0 / 3')
  })

  it('keeps lite decision stage copy compatible with the original final decision wording', async () => {
    const detail: ConversationDetail = {
      ...baseConversation,
      status: 'analyzing',
      messages: [
        createMessage({
          id: 'task-lite-finalize',
          role: 'system',
          messageType: MessageType.TASK_STATUS,
          content: { text: '最终结论阶段', stageId: 'decision.finalize' },
          createdAt: '2026-04-15T08:33:00.000Z',
        }),
      ],
      taskProgress: {
        stageId: 'decision.finalize',
        nodeId: 'Decision Manager',
        displayState: 'active',
      } as TaskProgress,
    }

    const wrapper = await mountConversationPage(detail)

    expect(wrapper.find('.task-status-list__label').text()).toBe('投资总监输出最终投资决策')
    expect(wrapper.find('.task-status-list__status').text()).toBe('工作中')
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

  it('keeps older long summary cards collapsed while leaving the latest expanded', async () => {
    const detail: ConversationDetail = {
      ...baseConversation,
      status: 'report_ready',
      messages: [
        createMessage({
          id: 'summary-long-old',
          messageType: MessageType.SUMMARY_CARD,
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
          id: 'summary-long-latest',
          messageType: MessageType.SUMMARY_CARD,
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
    const cards = wrapper.findAll('.conversation-inline-card--summary')
    const toggles = wrapper.findAll('.conversation-summary__toggle')

    expect(cards).toHaveLength(2)
    expect(toggles).toHaveLength(2)
    expect(toggles[0]?.text()).toBe('展开全文')
    expect(toggles[1]?.text()).toBe('展开全文')

    await toggles[1]!.trigger('click')

    const nextToggles = wrapper.findAll('.conversation-summary__toggle')
    expect(nextToggles[0]?.text()).toBe('展开全文')
    expect(nextToggles[1]?.text()).toBe('收起')
  })

  it('does not render conversation A stream chunks into conversation B after switching', async () => {
    const conversationA: ConversationDetail = {
      ...baseConversation,
      id: 'conv-a',
      title: '会话 A',
      status: 'report_ready',
      updatedAt: '2026-04-15T08:30:00.000Z',
      messages: [
        createMessage({
          id: 'summary-a',
          messageType: MessageType.SUMMARY_CARD,
          content: { text: 'A 的总结卡' },
          createdAt: '2026-04-15T08:31:00.000Z',
        }),
      ],
    }

    const conversationB: ConversationDetail = {
      ...baseConversation,
      id: 'conv-b',
      title: '会话 B',
      status: 'report_ready',
      updatedAt: '2026-04-15T08:32:00.000Z',
      messages: [
        createMessage({
          id: 'summary-b',
          messageType: MessageType.SUMMARY_CARD,
          content: { text: 'B 的总结卡' },
          createdAt: '2026-04-15T08:33:00.000Z',
        }),
      ],
    }

    mockListConversations.mockResolvedValue([
      makeSummary(conversationA),
      makeSummary(conversationB),
    ])
    mockGetConversation.mockImplementation(async (id: string) =>
      id === 'conv-b' ? conversationB : conversationA
    )
    mockCreateConversation.mockResolvedValue(makeSummary(conversationA))
    mockDeleteConversation.mockResolvedValue(undefined)
    mockResolve.mockResolvedValue({ messages: [], conversationStatus: conversationA.status })
    mockStreamResolve.mockResolvedValue(undefined)
    mockPostMessage.mockResolvedValue({ messages: [] })
    mockConfirmResolution.mockResolvedValue({ messages: [], conversationStatus: conversationA.status })
    mockLogout.mockResolvedValue(undefined)

    let emitEvent: ((event: StreamMessageEvent) => void) | undefined
    let resolveStream: (() => void) | undefined

    mockStreamPostMessage.mockImplementation(
      async (
        _conversationId: string,
        _payload: unknown,
        handlers: { onEvent: (event: StreamMessageEvent) => void }
      ) =>
        await new Promise<void>(resolve => {
          emitEvent = handlers.onEvent
          resolveStream = resolve
        })
    )

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

    await wrapper.find('.van-field-stub').setValue('继续追问 A')
    await wrapper.find('.conversation-input__send').trigger('click')
    await flushPromises()

    expect(emitEvent).toBeTypeOf('function')

    emitEvent?.({
      event: 'started',
      userMessage: createMessage({
        id: 'user-a-followup',
        role: 'user',
        messageType: MessageType.TEXT,
        content: '继续追问 A',
        createdAt: '2026-04-15T08:34:00.000Z',
      }),
    })
    await flushPromises()

    const conversationStore = useConversationStore()
    conversationStore.setCurrentConversation(conversationB)
    await flushPromises()

    emitEvent?.({
      event: 'delta',
      text: '这是 A 会话的流式片段',
    })
    resolveStream?.()
    await flushPromises()

    expect(conversationStore.currentConversation.id).toBe('conv-b')
    expect(
      conversationStore.currentConversation.messages.some(message =>
        String(message.content).includes('这是 A 会话的流式片段')
      )
    ).toBe(false)
  })
})
