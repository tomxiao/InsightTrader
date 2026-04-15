const fallbackAppName = 'InsightTrader Mobile'

const resolveFallbackApiBaseUrl = () => {
  if (typeof window === 'undefined') {
    return 'http://127.0.0.1:8100'
  }

  const { protocol, hostname } = window.location
  return `${protocol}//${hostname}:8100`
}

export const env = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL || resolveFallbackApiBaseUrl(),
  appName: import.meta.env.VITE_APP_NAME || fallbackAppName
}
