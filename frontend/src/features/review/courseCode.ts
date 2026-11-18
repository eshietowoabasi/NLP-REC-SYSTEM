/** Course codes like "CSC 419": 2 to 4 letters, then 3 digits and an optional letter. */
export const COURSE_CODE = /^([A-Za-z]{2,4})\s*(\d{3}[A-Za-z]?)$/

export const COURSE_CODE_MESSAGE = 'Use a course code like “CSC 419” (2–4 letters, then 3 digits).'

/** "csc419" → "CSC 419", mirroring the server's normalisation. */
export function normaliseCode(value: string) {
  const match = COURSE_CODE.exec(value.trim().replace(/\s+/g, ' '))
  return match ? `${match[1].toUpperCase()} ${match[2].toUpperCase()}` : value.trim()
}
