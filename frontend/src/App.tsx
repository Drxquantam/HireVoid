import React, { useEffect, useState, useCallback } from 'react'
import { format } from 'date-fns'
import { api } from './api'
import type { Application, GroupedApplications, Stats } from './types'
import TopBar from './components/TopBar'
import KanbanBoard from './components/KanbanBoard'
import AddJobModal from './components/AddJobModal'

const EMPTY_GROUPED: GroupedApplications = {
  applied: [], in_progress: [], interview: [],
  offer: [], rejected: [], unknown: [],
}

export default function App() {
  const [authenticated, setAuthenticated] = useState(false)
  const [connectedEmail, setConnectedEmail] = useState<string | null>(null)
  const [grouped, setGrouped] = useState<GroupedApplications>(EMPTY_GROUPED)
  const [stats, setStats] = useState<Stats | null>(null)
  const [syncing, setSyncing] = useState(false)
  const [toast, setToast] = useState<{ msg: string; type: 'success' | 'error' } | null>(null)
  const [lastSync, setLastSync] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [showAddJob, setShowAddJob] = useState(false)

  function showToast(msg: string, type: 'success' | 'error' = 'success') {
    setToast({ msg, type })
    setTimeout(() => setToast(null), 3500)
  }

  const loadData = useCallback(async () => {
    try {
      const [apps, s] = await Promise.all([api.listApplications(), api.stats()])
      setGrouped(apps)
      setStats(s)
    } catch (e) {
      console.error('Failed to load applications:', e)
    }
  }, [])

  useEffect(() => {
    async function init() {
      try {
        const { authenticated: isAuth, email } = await api.authStatus()
        setAuthenticated(isAuth)
        setConnectedEmail(email)
        if (isAuth) await loadData()
      } finally {
        setLoading(false)
      }
    }
    const params = new URLSearchParams(window.location.search)
    if (params.get('auth') === 'success') window.history.replaceState({}, '', '/')
    init()
  }, [loadData])

  async function handleLogout() {
    try {
      await api.logout()
    } catch (e) {
      console.error(e)
    }
    setAuthenticated(false)
    setConnectedEmail(null)
    setGrouped(EMPTY_GROUPED)
    setStats(null)
    setLastSync(null)
  }

  async function handleSync() {
    setSyncing(true)
    try {
      const result = await api.sync()
      setLastSync(format(new Date(), 'h:mm a'))
      showToast(`Sync done — ${result.new} new, ${result.updated} updated`)
      await loadData()
    } catch (e: any) {
      showToast(e.message ?? 'Sync failed', 'error')
    } finally {
      setSyncing(false)
    }
  }

  function handleDelete(id: number) {
    setGrouped(prev => {
      const next = { ...prev }
      for (const key of Object.keys(next) as Array<keyof GroupedApplications>) {
        next[key] = next[key].filter(a => a.id !== id)
      }
      return next
    })
  }

  function handleCreated(app: Application) {
    setGrouped(prev => {
      const bucket = (app.status in prev ? app.status : 'unknown') as keyof GroupedApplications
      return { ...prev, [bucket]: [app, ...prev[bucket]] }
    })
    setStats(prev => prev ? {
      total: prev.total + 1,
      by_status: { ...prev.by_status, [app.status]: (prev.by_status[app.status] ?? 0) + 1 }
    } : prev)
  }

  function handleDeleteAll(status: keyof GroupedApplications) {
    setGrouped(prev => ({ ...prev, [status]: [] }))
  }

  function handleUpdate(updated: Application) {
    setGrouped(prev => {
      const next = { ...prev }
      for (const key of Object.keys(next) as Array<keyof GroupedApplications>) {
        next[key] = next[key].filter(a => a.id !== updated.id)
      }
      const bucket = (updated.status in next ? updated.status : 'unknown') as keyof GroupedApplications
      next[bucket] = [updated, ...next[bucket]]
      return next
    })
  }

  /* ── Loading skeleton ── */
  if (loading) {
    return (
      <div className="min-h-screen flex flex-col">
        <div className="h-[52px] border-b border-white/[0.06] glass" />
        <div className="flex gap-4 px-5 pt-6">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="min-w-[290px] flex flex-col gap-3">
              <div className="skeleton h-10 rounded-xl" />
              {[...Array(3 - (i % 2))].map((_, j) => (
                <div key={j} className="skeleton rounded-xl" style={{ height: `${96 + (j * 16)}px` }} />
              ))}
            </div>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex flex-col">
      <TopBar
        stats={stats}
        syncing={syncing}
        authenticated={authenticated}
        connectedEmail={connectedEmail}
        lastSync={lastSync}
        onSync={handleSync}
        onLogout={handleLogout}
        onAddJob={() => setShowAddJob(true)}
      />

      <main className="flex-1 pt-5">
        {!authenticated ? <LandingHero /> : (
          <KanbanBoard
            grouped={grouped}
            onUpdate={handleUpdate}
            onDelete={handleDelete}
            onDeleteAll={handleDeleteAll}
          />
        )}
      </main>

      {/* ── Add Job Modal ── */}
      {showAddJob && (
        <AddJobModal onClose={() => setShowAddJob(false)} onCreated={handleCreated} />
      )}

      {/* ── Toast ── */}
      {toast && (
        <div className={`
          fixed bottom-6 left-1/2 -translate-x-1/2 z-50
          flex items-center gap-2.5 px-4 py-3 rounded-xl text-sm font-medium
          border shadow-2xl shadow-black/50 animate-slide-up
          ${toast.type === 'success'
            ? 'bg-zinc-900 border-emerald-500/30 text-zinc-100'
            : 'bg-zinc-900 border-rose-500/30 text-zinc-100'}
        `}>
          {toast.type === 'success'
            ? <span className="w-2 h-2 rounded-full bg-emerald-400 shrink-0" />
            : <span className="w-2 h-2 rounded-full bg-rose-400 shrink-0" />}
          {toast.msg}
        </div>
      )}
    </div>
  )
}

/* ── Unauthenticated landing ─────────────────────────────────────────────── */
function LandingHero() {
  const features = [
    { icon: '📨', label: 'Auto-detects application emails from your inbox' },
    { icon: '🏷️', label: 'Classifies status: Applied, Interview, Offer, Rejected' },
    { icon: '🗂️', label: 'Kanban board — everything in one view' },
    { icon: '🔒', label: 'Read-only Gmail access — we never modify your email' },
  ]

  return (
    <div className="flex flex-col items-center justify-center min-h-[75vh] px-4 text-center">
      {/* Glow orb */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 rounded-full bg-indigo-600/10 blur-3xl pointer-events-none" />

      {/* Icon */}
      <div className="relative w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-600 to-violet-700 flex items-center justify-center shadow-2xl shadow-indigo-900/50 mb-6">
        <svg className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round"
            d="M20.25 14.15v4.073a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V14.15
               M16.5 6V4.5A2.25 2.25 0 0014.25 2.25h-4.5A2.25 2.25 0 007.5 4.5V6
               M12 12.75h.008v.008H12v-.008z" />
        </svg>
        {/* Corner shine */}
        <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-white/20 to-transparent" />
      </div>

      {/* Headline */}
      <h1 className="text-4xl font-bold tracking-tight mb-3">
        <span className="bg-gradient-to-r from-white via-zinc-200 to-zinc-400 bg-clip-text text-transparent">
          Your job search,
        </span>
        <br />
        <span className="bg-gradient-to-r from-indigo-400 to-violet-400 bg-clip-text text-transparent">
          on autopilot.
        </span>
      </h1>
      <p className="text-zinc-500 text-base max-w-sm leading-relaxed mb-8">
        HireVoid scans your Gmail and automatically tracks every job application —
        no copy-pasting, no spreadsheets.
      </p>

      {/* Feature list */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 mb-8 max-w-md w-full text-left">
        {features.map(f => (
          <div
            key={f.label}
            className="flex items-start gap-3 px-4 py-3 rounded-xl bg-white/[0.03] border border-white/[0.06]"
          >
            <span className="text-base mt-0.5">{f.icon}</span>
            <span className="text-xs text-zinc-400 leading-relaxed">{f.label}</span>
          </div>
        ))}
      </div>

      {/* CTA */}
      <a
        href="/api/auth/login"
        className="
          inline-flex items-center gap-3 px-6 py-3 rounded-xl font-semibold text-sm text-white
          bg-gradient-to-r from-indigo-600 to-violet-600
          hover:from-indigo-500 hover:to-violet-500
          shadow-xl shadow-indigo-900/40
          transition-all duration-200 active:scale-95
          ring-1 ring-white/10
        "
      >
        <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
          <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
          <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
          <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
          <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
        </svg>
        Connect Gmail — it's free
      </a>

      <p className="mt-4 text-[11px] text-zinc-700">
        OAuth 2.0 · Read-only · No email data stored
      </p>
    </div>
  )
}
