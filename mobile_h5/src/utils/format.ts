export const formatSeconds = (seconds = 0) => {
  if (seconds <= 0) return '计算中'

  if (seconds < 60) {
    return `${Math.floor(seconds)}秒`
  }

  const minutes = Math.floor(seconds / 60)
  const remain = Math.floor(seconds % 60)
  return remain > 0 ? `${minutes}分${remain}秒` : `${minutes}分钟`
}

export const formatTimeLabel = (value?: string) => {
  if (!value) return ''

  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value

  return new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  }).format(date)
}

export const formatConversationGroup = (value?: string) => {
  if (!value) return '更早'

  const target = new Date(value)
  if (Number.isNaN(target.getTime())) return '更早'

  const now = new Date()
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime()
  const startOfTarget = new Date(
    target.getFullYear(),
    target.getMonth(),
    target.getDate()
  ).getTime()
  const dayDiff = Math.round((startOfToday - startOfTarget) / (24 * 60 * 60 * 1000))

  if (dayDiff === 0) return '今天'
  if (dayDiff === 1) return '昨天'
  if (dayDiff <= 7) return '近 7 天'
  return '更早'
}
