import React, { useState, useRef, useEffect } from 'react'
import type { Stats } from '../types'

interface Props {
  stats: Stats | null
  syncing: boolean
  authenticated: boolean
  connectedEmail: string | null
  lastSync: string | null
  onSync: () => void
  onLogout: () => void
  onAddJob: () => void
}

const STATUS_PILLS = [
  { key: 'applied',     label: 'Applied',     color: 'text-indigo-400',  dot: 'bg-indigo-400' },
  { key: 'in_progress', label: 'In Progress', color: 'text-amber-400',   dot: 'bg-amber-400'  },
  { key: 'interview',   label: 'Interview',   color: 'text-sky-400',     dot: 'bg-sky-400'    },
  { key: 'offer',       label: 'Offer',       color: 'text-emerald-400', dot: 'bg-emerald-400'},
  { key: 'rejected',    label: 'Rejected',    color: 'text-rose-400',    dot: 'bg-rose-400'   },
]

export default function TopBar({ stats, syncing, authenticated, connectedEmail, lastSync, onSync, onLogout, onAddJob }: Props) {
  const [accountMenuOpen, setAccountMenuOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  // Close menu on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setAccountMenuOpen(false)
      }
    }
    if (accountMenuOpen) document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [accountMenuOpen])

  return (
    <header className="sticky top-0 z-30 border-b border-white/[0.06] glass">
      <div className="max-w-[1800px] mx-auto px-5 h-[52px] flex items-center gap-5">

        {/* ── Logo ── */}
        <div className="flex items-center gap-2.5 shrink-0 select-none">
          <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shadow-lg shadow-indigo-900/40">
            <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round"
                d="M20.25 14.15v4.073a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V14.15
                   M16.5 6V4.5A2.25 2.25 0 0014.25 2.25h-4.5A2.25 2.25 0 007.5 4.5V6
                   M12 12.75h.008v.008H12v-.008z" />
            </svg>
          </div>
          <span className="font-bold text-[15px] bg-gradient-to-r from-white to-zinc-400 bg-clip-text text-transparent tracking-tight">
            HireVoid
          </span>
        </div>

        {/* ── Divider ── */}
        {stats && <div className="h-4 w-px bg-white/10 shrink-0" />}

        {/* ── Stats pills ── */}
        {stats && (
          <div className="hidden md:flex items-center gap-1">
            <span className="text-[11px] text-zinc-500 font-medium mr-2">
              {stats.total} tracked
            </span>
            {STATUS_PILLS.map(({ key, label, color, dot }) => {
              const count = stats.by_status[key as keyof typeof stats.by_status] ?? 0
              if (count === 0) return null
              return (
                <span
                  key={key}
                  className={`
                    inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium
                    bg-white/[0.04] border border-white/[0.06] ${color}
                  `}
                >
                  <span className={`w-1.5 h-1.5 rounded-full ${dot} shrink-0`} />
                  {count} {label}
                </span>
              )
            })}
          </div>
        )}

        <div className="flex-1" />

        {/* ── Last sync time ── */}
        {lastSync && (
          <span className="hidden sm:flex items-center gap-1.5 text-[11px] text-zinc-600">
            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Synced {lastSync}
          </span>
        )}

        {!authenticated ? (
          /* ── Not logged in — single CTA ── */
          <a
            href="/api/auth/login"
            className="
              inline-flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-sm font-medium
              bg-gradient-to-r from-indigo-600 to-violet-600
              hover:from-indigo-500 hover:to-violet-500
              text-white shadow-lg shadow-indigo-900/30
              transition-all duration-200 active:scale-95
            "
          >
            <GoogleIcon />
            Sign in with Google
          </a>
        ) : (
          <div className="flex items-center gap-2">
            {/* ── Add Job button ── */}
            <button
              onClick={onAddJob}
              className="
                inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium
                bg-white/[0.05] border border-white/[0.08]
                text-zinc-300 hover:text-white hover:bg-white/[0.09]
                transition-all duration-150
              "
            >
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
              </svg>
              Add Job
            </button>

            {/* ── Sync button ── */}
            <button
              onClick={onSync}
              disabled={syncing}
              className="
                inline-flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-sm font-medium
                bg-gradient-to-r from-indigo-600 to-violet-600
                hover:from-indigo-500 hover:to-violet-500
                disabled:opacity-40 disabled:cursor-not-allowed
                text-white shadow-lg shadow-indigo-900/30
                transition-all duration-200 active:scale-95
              "
            >
              <svg
                className={`w-3.5 h-3.5 ${syncing ? 'animate-spin' : ''}`}
                fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}
              >
                <path strokeLinecap="round" strokeLinejoin="round"
                  d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0
                     0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182m0-4.991v4.99" />
              </svg>
              {syncing ? 'Syncing…' : 'Sync Gmail'}
            </button>

            {/* ── Account avatar / menu ── */}
            <div className="relative" ref={menuRef}>
              <button
                onClick={() => setAccountMenuOpen(v => !v)}
                title={connectedEmail ?? 'Account'}
                className="
                  w-8 h-8 rounded-full flex items-center justify-center
                  bg-gradient-to-br from-indigo-600/40 to-violet-600/40
                  border border-white/10
                  text-[11px] font-bold text-indigo-300
                  hover:border-white/20 hover:from-indigo-600/60 hover:to-violet-600/60
                  transition-all duration-150
                "
              >
                {connectedEmail ? connectedEmail[0].toUpperCase() : '?'}
              </button>

              {accountMenuOpen && (
                <div className="
                  absolute right-0 top-10 z-50 w-64
                  bg-zinc-900 border border-white/10 rounded-xl
                  shadow-2xl shadow-black/60 overflow-hidden
                  animate-fade-in
                ">
                  {/* Connected account info */}
                  <div className="px-4 py-3 border-b border-white/[0.06]">
                    <p className="text-[10px] text-zinc-600 uppercase tracking-widest font-semibold mb-1">
                      Connected account
                    </p>
                    <div className="flex items-center gap-2.5">
                      <div className="
                        w-7 h-7 rounded-full shrink-0
                        bg-gradient-to-br from-indigo-600/50 to-violet-600/50
                        border border-white/10
                        flex items-center justify-center
                        text-[11px] font-bold text-indigo-300
                      ">
                        {connectedEmail ? connectedEmail[0].toUpperCase() : '?'}
                      </div>
                      <span className="text-xs text-zinc-300 truncate">
                        {connectedEmail ?? 'Unknown email'}
                      </span>
                    </div>
                  </div>

                  {/* Switch account */}
                  <a
                    href="/api/auth/login"
                    onClick={() => { onLogout(); setAccountMenuOpen(false) }}
                    className="
                      flex items-center gap-3 px-4 py-3 text-xs text-zinc-400
                      hover:bg-white/[0.05] hover:text-zinc-100
                      transition-colors duration-100
                    "
                  >
                    <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round"
                        d="M7.5 21L3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5" />
                    </svg>
                    Switch to a different account
                  </a>

                  {/* Disconnect */}
                  <button
                    onClick={() => { onLogout(); setAccountMenuOpen(false) }}
                    className="
                      w-full flex items-center gap-3 px-4 py-3 mb-1 text-xs text-rose-400
                      hover:bg-rose-500/10 hover:text-rose-300
                      transition-colors duration-100
                    "
                  >
                    <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round"
                        d="M15.75 9V5.25A2.25 2.25 0 0013.5 3h-6a2.25 2.25 0 00-2.25 2.25v13.5A2.25 2.25 0
                           007.5 21h6a2.25 2.25 0 002.25-2.25V15m3 0l3-3m0 0l-3-3m3 3H9" />
                    </svg>
                    Disconnect Gmail
                  </button>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </header>
  )
}

function GoogleIcon() {
  return (
    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
      <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
      <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
      <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
      <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
    </svg>
  )
}
