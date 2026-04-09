const fallbackApiBaseUrl = 'http://127.0.0.1:8100'
const fallbackAppName = 'InsightTrader Mobile'

export const env = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL || fallbackApiBaseUrl,
  appName: import.meta.env.VITE_APP_NAME || fallbackAppName
}
