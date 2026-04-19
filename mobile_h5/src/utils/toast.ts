import { showToast } from 'vant'

export const showErrorToast = (message: string) =>
  showToast({
    message,
    duration: 5000,
  })
