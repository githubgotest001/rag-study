// 后端 API 客户端：统一处理请求与中文错误信息

import type {
  ChunksResponse,
  DocumentInfo,
  HealthInfo,
  QueryResponse,
  SettingsInfo,
  UploadResponse,
} from './types'

/** 解析 FastAPI 的错误响应（detail 可能是字符串或校验错误数组） */
async function parseError(resp: Response): Promise<string> {
  try {
    const body = await resp.json()
    if (typeof body.detail === 'string') return body.detail
    if (Array.isArray(body.detail)) {
      return body.detail.map((d: { msg?: string }) => d.msg ?? '').join('；')
    }
  } catch {
    // 响应不是 JSON 时忽略
  }
  return `请求失败（HTTP ${resp.status}），请检查后端服务是否已启动`
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let resp: Response
  try {
    resp = await fetch(path, init)
  } catch {
    throw new Error('无法连接后端服务，请确认已启动 uvicorn（端口 8000）')
  }
  if (!resp.ok) throw new Error(await parseError(resp))
  return resp.json() as Promise<T>
}

export const api = {
  health: () => request<HealthInfo>('/api/health'),

  settings: () => request<SettingsInfo>('/api/settings'),

  listDocuments: () => request<DocumentInfo[]>('/api/documents'),

  uploadDocument: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return request<UploadResponse>('/api/documents', { method: 'POST', body: form })
  },

  deleteDocument: (id: string) =>
    request<{ ok: boolean; id: string }>(`/api/documents/${id}`, { method: 'DELETE' }),

  getChunks: (id: string) => request<ChunksResponse>(`/api/documents/${id}/chunks`),

  query: (question: string, topK?: number) =>
    request<QueryResponse>('/api/query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, top_k: topK ?? null }),
    }),
}
