import { describe, expect, it } from 'vitest'
import { formatConversationGroup, formatSeconds, formatTimeLabel } from '@utils/format'

describe('formatSeconds', () => {
  it('formats seconds into friendly chinese text', () => {
    expect(formatSeconds(75)).toBe('1分15秒')
  })
})

describe('formatConversationGroup', () => {
  it('groups today timestamps as 今天', () => {
    expect(formatConversationGroup(new Date().toISOString())).toBe('今天')
  })
})

describe('formatTimeLabel', () => {
  it('formats iso time into localized month day and time', () => {
    expect(formatTimeLabel('2026-04-09T08:30:00+00:00')).toMatch(/\d{2}\/\d{2}.+\d{2}:\d{2}/)
  })
})
