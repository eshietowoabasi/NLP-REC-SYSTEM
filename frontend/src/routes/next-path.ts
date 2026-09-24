/** Only allow same-site relative paths as a post-login destination (no open redirects). */
export function safeNextPath(next: string | null): string {
  if (!next || !next.startsWith('/') || next.startsWith('//') || next.startsWith('/login')) {
    return '/'
  }
  return next
}
