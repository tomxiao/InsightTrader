import axios from 'axios'

type ErrorScene =
  | 'login'
  | 'conversation-bootstrap'
  | 'conversation-create'
  | 'conversation-load'
  | 'conversation-delete'
  | 'conversation-send'
  | 'conversation-resolution-action'
  | 'admin-users-load'
  | 'admin-user-create'
  | 'admin-user-toggle'
  | 'admin-user-reset-password'

type ErrorPayload = {
  code?: string
  detail?: string
  message?: string
}

const sceneFallbackMap: Record<ErrorScene, string> = {
  login: '登录失败，请稍后重试',
  'conversation-bootstrap': '初始化会话失败',
  'conversation-create': '创建会话失败，请稍后再试',
  'conversation-load': '加载会话失败',
  'conversation-delete': '删除会话失败',
  'conversation-send': '发送失败，请稍后再试',
  'conversation-resolution-action': '操作失败，请稍后再试',
  'admin-users-load': '加载用户列表失败',
  'admin-user-create': '创建用户失败',
  'admin-user-toggle': '更新用户状态失败',
  'admin-user-reset-password': '重置密码失败',
}

const codeMessageMap: Record<string, string> = {
  AUTH_INVALID_CREDENTIALS: '用户名或密码错误',
  AUTH_SESSION_EXPIRED: '登录已过期，请重新登录',
  CONVERSATION_NOT_FOUND: '会话不存在或已被删除',
  CONVERSATION_STATE_CONFLICT: '当前状态已变化，请按最新状态操作',
  CONVERSATION_DELETE_FORBIDDEN_ANALYZING: '分析进行中，暂时不能删除会话',
  ANALYSIS_ALREADY_RUNNING: '当前已有分析任务进行中，请稍后再试',
  RESOLUTION_CONFLICT: '当前状态已变化，请按最新状态操作',
  RESOLUTION_TIMEOUT: '识别耗时较长，请稍后查看结果或重新发送',
}

const sceneStatusMessageMap: Partial<Record<ErrorScene, Partial<Record<number, string>>>> = {
  login: {
    400: '用户名或密码错误',
    401: '用户名或密码错误',
    429: '登录尝试过于频繁，请稍后再试',
  },
  'conversation-load': {
    401: '登录已过期，请重新登录',
    404: '会话不存在或已被删除',
  },
  'conversation-delete': {
    401: '登录已过期，请重新登录',
    404: '会话不存在或已被删除',
    409: '分析进行中，暂时不能删除会话',
  },
  'conversation-send': {
    401: '登录已过期，请重新登录',
    404: '会话不存在或已被删除',
    409: '当前状态已变化，请按最新状态操作',
  },
  'conversation-resolution-action': {
    401: '登录已过期，请重新登录',
    404: '当前标的确认请求已失效，请重新输入',
    409: '当前状态已变化，请按最新状态操作',
  },
  'admin-users-load': {
    401: '登录已过期，请重新登录',
    403: '你没有权限查看用户列表',
  },
  'admin-user-create': {
    401: '登录已过期，请重新登录',
    403: '你没有权限创建用户',
    409: '用户名已存在，请更换后重试',
  },
  'admin-user-toggle': {
    401: '登录已过期，请重新登录',
    403: '你没有权限修改用户状态',
    404: '目标用户不存在或已被删除',
  },
  'admin-user-reset-password': {
    401: '登录已过期，请重新登录',
    403: '你没有权限重置密码',
    404: '目标用户不存在或已被删除',
  },
}

const extractPayload = (error: unknown): ErrorPayload => {
  if (axios.isAxiosError<ErrorPayload>(error)) {
    return {
      code: error.response?.data?.code,
      detail: error.response?.data?.detail,
      message: error.message,
    }
  }

  if (error && typeof error === 'object') {
    const candidate = error as ErrorPayload
    if (
      typeof candidate.code === 'string' ||
      typeof candidate.detail === 'string' ||
      typeof candidate.message === 'string'
    ) {
      return {
        code: candidate.code,
        detail: candidate.detail,
        message: candidate.message,
      }
    }
  }

  if (error instanceof Error) {
    return { message: error.message }
  }

  return {}
}

const isSafeUserMessage = (message: string) => {
  const trimmed = message.trim()
  if (!trimmed) return false

  const blockedPatterns = [
    /^Request failed with status code \d+$/i,
    /^Network Error$/i,
    /Traceback/i,
    /Exception/i,
    / at /,
    /Error:/i,
    /<[^>]+>/,
  ]

  return !blockedPatterns.some(pattern => pattern.test(trimmed))
}

export const resolveUserErrorMessage = (error: unknown, scene: ErrorScene, fallback?: string) => {
  const payload = extractPayload(error)
  const fallbackMessage = fallback || sceneFallbackMap[scene]

  if (payload.code && codeMessageMap[payload.code]) {
    return codeMessageMap[payload.code]
  }

  if (axios.isAxiosError(error)) {
    const status = error.response?.status
    if (status != null) {
      const sceneMessage = sceneStatusMessageMap[scene]?.[status]
      if (sceneMessage) return sceneMessage
    }
  } else if (error && typeof error === 'object' && 'status' in error) {
    const status = (error as { status?: unknown }).status
    if (typeof status === 'number') {
      const sceneMessage = sceneStatusMessageMap[scene]?.[status]
      if (sceneMessage) return sceneMessage
    }
  }

  if (payload.detail && isSafeUserMessage(payload.detail)) {
    return payload.detail
  }

  if (payload.message && isSafeUserMessage(payload.message)) {
    return payload.message
  }

  return fallbackMessage
}
