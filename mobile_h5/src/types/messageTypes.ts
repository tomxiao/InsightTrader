/**
 * 消息类型管理器 — 前后端通讯契约
 *
 * 与后端 ta_service/models/message_types.py 的 MessageType 枚举保持同步。
 * 每种消息类型对应一个明确的 content schema interface。
 */

// ─── 消息类型枚举 ────────────────────────────────────────────────────────────

export const MessageType = {
  TEXT: 'text',
  TICKER_RESOLUTION: 'ticker_resolution',
  TASK_STATUS: 'task_status',
  SUMMARY_CARD: 'summary_card',
  INSIGHT_REPLY: 'insight_reply',
  ERROR: 'error',
} as const

export type MessageType = (typeof MessageType)[keyof typeof MessageType]

// ─── Content schema ──────────────────────────────────────────────────────────

/** TEXT: 纯文本消息，user 输入或 assistant followup 回复 */
export type TextContent = string

/** TASK_STATUS: 分析任务系统通知，stageId 为 null 表示任务整体启动 */
export interface TaskStatusContent {
  text: string
  stageId: string | null
}

/** ERROR: 分析任务执行失败的系统通知 */
export interface ErrorContent {
  text: string
}

/** SUMMARY_CARD: 分析完成后的执行摘要卡片 */
export interface SummaryCardContent {
  text: string
}

/** TICKER_RESOLUTION: 标的识别过程的交互卡片 */
export type ResolutionStatus =
  | 'collect_more'
  | 'need_confirm'
  | 'need_disambiguation'
  | 'resolved'
  | 'unsupported'
  | 'failed'

export interface ResolutionCandidate {
  ticker: string
  name: string
  market?: string | null
  exchange?: string | null
  aliases?: string[]
  score?: number | null
  assetType?: string
  isActive?: boolean | null
}

export interface TickerResolutionContent {
  text?: string
  status?: ResolutionStatus
  resolutionId?: string
  ticker?: string | null
  name?: string | null
  candidates?: ResolutionCandidate[]
  analysisPrompt?: string
  focusPoints?: string[]
}

// ─── 类型守卫 ────────────────────────────────────────────────────────────────

export function isTextContent(
  type: MessageType,
  content: unknown,
): content is TextContent {
  return type === MessageType.TEXT && typeof content === 'string'
}

export function isTaskStatusContent(
  type: MessageType,
  content: unknown,
): content is TaskStatusContent {
  return (
    type === MessageType.TASK_STATUS &&
    typeof content === 'object' &&
    content !== null &&
    'text' in content
  )
}

export function isErrorContent(
  type: MessageType,
  content: unknown,
): content is ErrorContent {
  return (
    type === MessageType.ERROR &&
    typeof content === 'object' &&
    content !== null &&
    'text' in content
  )
}

export function isSummaryCardContent(
  type: MessageType,
  content: unknown,
): content is SummaryCardContent {
  return (
    type === MessageType.SUMMARY_CARD &&
    typeof content === 'object' &&
    content !== null &&
    'text' in content
  )
}

export function isTickerResolutionContent(
  type: MessageType,
  content: unknown,
): content is TickerResolutionContent {
  return (
    type === MessageType.TICKER_RESOLUTION &&
    typeof content === 'object' &&
    content !== null
  )
}
