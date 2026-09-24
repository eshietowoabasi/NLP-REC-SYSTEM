/**
 * Thin fetch wrapper for the Flask API. Auth uses the session cookie (same origin),
 * and errors follow the API error model: {success: false, error: {code, message, details}}.
 */
export class ApiError extends Error {
  constructor(status, code, message, details = {}) {
    super(message)
    this.status = status
    this.code = code
    this.details = details
  }
}

let unauthorizedHandler = null
export function onUnauthorized(handler) {
  unauthorizedHandler = handler
}

export async function request(method, url, { body, form, query } = {}) {
  const qs = query
    ? '?' + new URLSearchParams(Object.entries(query).filter(([, v]) => v !== undefined && v !== null && v !== '')).toString()
    : ''
  const options = { method, credentials: 'same-origin', headers: { Accept: 'application/json' } }
  if (form) {
    options.body = form // browser sets the multipart boundary
  } else if (body !== undefined) {
    options.headers['Content-Type'] = 'application/json'
    options.body = JSON.stringify(body)
  }

  let response
  try {
    response = await fetch(`/api${url}${qs === '?' ? '' : qs}`, options)
  } catch {
    throw new ApiError(0, 'NETWORK_ERROR', 'Cannot reach the server. Check your connection and try again.')
  }
  const data = await response.json().catch(() => null)
  if (!response.ok) {
    const error = data?.error || {}
    if (response.status === 401 && unauthorizedHandler && !url.startsWith('/auth/login')) unauthorizedHandler()
    throw new ApiError(response.status, error.code || 'HTTP_ERROR', error.message || response.statusText, error.details || {})
  }
  return data
}

export const api = {
  get: (url, query) => request('GET', url, { query }),
  post: (url, body) => request('POST', url, { body }),
  put: (url, body) => request('PUT', url, { body }),
  patch: (url, body) => request('PATCH', url, { body }),
  delete: (url) => request('DELETE', url),
  upload: (url, form) => request('POST', url, { form }),
}

/** Human-readable message, including per-field details when present. */
export function describeError(error) {
  if (!(error instanceof ApiError)) return 'Something went wrong.'
  const details = Object.entries(error.details || {})
    .filter(([, v]) => typeof v === 'string')
    .map(([k, v]) => `${k.replaceAll('_', ' ')}: ${v}`)
  return details.length ? `${error.message} (${details.join('; ')})` : error.message
}
