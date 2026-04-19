import type { ConversationSummary } from '@/types/conversation'

export const conversationStatusLabelMap: Record<ConversationSummary['status'], string> = {
  idle: '待开始',
  collecting_inputs: '补充信息中',
  ready_to_analyze: '可发起分析',
  analyzing: '分析中',
  report_ready: '报告已生成',
  report_explaining: '继续解读中',
  failed: '需要重试'
}

export const getConversationStatusLabel = (status: ConversationSummary['status']) =>
  conversationStatusLabelMap[status] || '处理中'
