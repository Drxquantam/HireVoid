import type { GroupedApplications, Stats, SyncResult, Application, ApplicationStatus } from './types'

const BASE = '/api'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail ?? 'Request failed')
  }
  return res.json()
}

export const api = {
  authStatus: () => request<{ authenticated: boolean; email: string | null }>('/auth/status'),
  logout: () => request<{ success: boolean }>('/auth/logout', { method: 'POST' }),

  sync: () =>
    request<SyncResult>('/sync', { method: 'POST' }),

  listApplications: () =>
    request<GroupedApplications>('/applications'),

  getApplication: (id: number) =>
    request<Application>(`/applications/${id}`),

  updateApplication: (id: number, patch: { status?: ApplicationStatus; deadline?: string; role?: string; company?: string }) =>
    request<Application>(`/applications/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(patch),
    }),

  createApplication: (body: { company: string; role: string; status: string; applied_date?: string; deadline?: string }) =>
    request<Application>('/applications', { method: 'POST', body: JSON.stringify(body) }),

  deleteApplication: (id: number) =>
    request<{ deleted: number }>(`/applications/${id}`, { method: 'DELETE' }),

  deleteByStatus: (status: ApplicationStatus) =>
    request<{ deleted: number; status: string }>(`/applications?status=${status}`, { method: 'DELETE' }),

  stats: () => request<Stats>('/stats'),
}
