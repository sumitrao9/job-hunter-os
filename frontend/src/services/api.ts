const API_BASE = '/api'

async function extractError(res: Response, fallback: string): Promise<Error> {
  const data = await res.json().catch(() => null)
  const detail = (data as { detail?: unknown } | null)?.detail

  if (typeof detail === 'string' && detail.trim()) return new Error(detail)
  if (Array.isArray(detail)) {
    // FastAPI validation errors arrive as a list of {loc, msg, type}.
    const first = detail[0] as { msg?: string } | undefined
    if (first?.msg) return new Error(first.msg)
  }
  return new Error(fallback)
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, init)
  if (!res.ok) throw await extractError(res, `Request failed (HTTP ${res.status})`)
  if (res.status === 204) return undefined as T
  return res.json()
}

const jsonInit = (method: string, body?: unknown): RequestInit => ({
  method,
  headers: { 'Content-Type': 'application/json' },
  body: body !== undefined ? JSON.stringify(body) : undefined,
})

export function get<T>(path: string): Promise<T> {
  return request<T>(path)
}

export function post<T>(path: string, body?: unknown): Promise<T> {
  return request<T>(path, jsonInit('POST', body))
}

export function patch<T>(path: string, body?: unknown): Promise<T> {
  return request<T>(path, jsonInit('PATCH', body))
}

export function put<T>(path: string, body?: unknown): Promise<T> {
  return request<T>(path, jsonInit('PUT', body))
}

export function del<T>(path: string): Promise<T> {
  return request<T>(path, { method: 'DELETE' })
}