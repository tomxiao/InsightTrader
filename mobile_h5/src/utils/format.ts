export const formatSeconds = (seconds = 0) => {
  if (seconds <= 0) return '计算中'

  if (seconds < 60) {
    return `${Math.floor(seconds)}秒`
  }

  const minutes = Math.floor(seconds / 60)
  const remain = Math.floor(seconds % 60)
  return remain > 0 ? `${minutes}分${remain}秒` : `${minutes}分钟`
}
