import { describe, expect, it } from 'vitest'
import { fileSize, percent, score, statusClass } from '../../src/utils/format'

describe('format helpers', () => {
  it('formats scores and handles missing values', () => {
    expect(score(0.8345)).toBe('0.83')
    expect(score(null)).toBe('–')
    expect(percent(0.456)).toBe('46%')
  })
  it('formats file sizes', () => {
    expect(fileSize(512)).toBe('512 B')
    expect(fileSize(2048)).toBe('2.0 KB')
    expect(fileSize(5 * 1024 * 1024)).toBe('5.0 MB')
  })
  it('maps statuses to badge classes', () => {
    expect(statusClass('Potential Duplicate')).toBe('text-bg-warning')
    expect(statusClass('Completed')).toBe('text-bg-success')
    expect(statusClass('Unknown')).toBe('text-bg-light')
  })
})
