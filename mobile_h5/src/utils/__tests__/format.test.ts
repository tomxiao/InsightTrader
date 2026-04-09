import { describe, expect, it } from 'vitest'
import { formatSeconds } from '@utils/format'

describe('formatSeconds', () => {
  it('formats seconds into friendly chinese text', () => {
    expect(formatSeconds(75)).toBe('1分15秒')
  })
})
