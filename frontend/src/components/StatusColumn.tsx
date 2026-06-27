import React, { useState } from 'react'
import type { Application, ApplicationStatus } from '../types'
import ApplicationCard from './ApplicationCard'
import { api } from '../api'

interface ColumnConfig {
  label: string
  accentBg: string
  accentText: string
  dot: string
  headerGlow: string
  emptyText: string
  emptyEmoji: string
}

const COLUMN_CONFIG: Record<ApplicationStatus, ColumnConfig> = {
  applied: {
    label: 'Applied',
    accentBg:   'bg-indigo-500/10',
    accentText: 'text-indigo-300',
    dot:        'bg-indigo-400',
    headerGlow: 'shadow-[0_0_24px_rgba(99,102,241,0.08)]',
    emptyText:  'No applications yet',
    emptyEmoji: '📤',
  },
  in_progress: {
    label: 'In Progress',
    accentBg:   'bg-amber-500/10',
    accentText: 'text-amber-300',
    dot:        'bg-amber-400',
    headerGlow: 'shadow-[0_0_24px_rgba(245,158,11,0.08)]',
    emptyText:  'Nothing in progress',
    emptyEmoji: '⏳',
  },
  interview: {
    label: 'Interview',
    accentBg:   'bg-sky-500/10',
    accentText: 'text-sky-300',
    dot:        'bg-sky-400',
    headerGlow: 'shadow-[0_0_24px_rgba(56,189,248,0.08)]',
    emptyText:  'No interviews yet',
    emptyEmoji: '🎤',
  },
  offer: {
    label: 'Offer',
    accentBg:   'bg-emerald-500/10',
    accentText: 'text-emerald-300',
    dot:        'bg-emerald-400',
    headerGlow: 'shadow-[0_0_24px_rgba(52,211,153,0.08)]',
    emptyText:  'No offers yet — keep going!',
    emptyEmoji: '🏆',
  },
  rejected: {
    label: 'Rejected',
    accentBg:   'bg-rose-500/10',
    accentText: 'text-rose-300',
    dot:        'bg-rose-500',
    headerGlow: 'shadow-[0_0_24px_rgba(251,113,133,0.08)]',
    emptyText:  'No rejections (keep it that way!)',
    emptyEmoji: '🚫',
  },
  unknown: {
    label: 'Unknown',
    accentBg:   'bg-zinc-500/10',
    accentText: 'text-zinc-400',
    dot:        'bg-zinc-500',
    headerGlow: '',
    emptyText:  'Nothing here',
    emptyEmoji: '❓',
  },
}

interface Props {
  status: ApplicationStatus
  applications: Application[]
  onUpdate: (updated: Application) => void
  onDelete: (id: number) => void
  onDeleteAll: (status: ApplicationStatus) => void
}

export default function StatusColumn({ status, applications, onUpdate, onDelete, onDeleteAll }: Props) {
  const cfg = COLUMN_CONFIG[status]
  const [confirmClear, setConfirmClear] = useState(false)
  const [clearing, setClearing] = useState(false)

  async function handleDeleteAll() {
    if (!confirmClear) { setConfirmClear(true); return }
    setClearing(true)
    try {
      await api.deleteByStatus(status)
      onDeleteAll(status)
    } catch (e) {
      console.error(e)
    } finally {
      setClearing(false)
      setConfirmClear(false)
    }
  }

  return (
    <div className="flex flex-col min-w-[290px] max-w-[320px] flex-1">
      {/* ── Column header ── */}
      <div className={`
        flex items-center gap-2.5 px-3.5 py-3 mb-2.5 rounded-xl
        ${cfg.accentBg} ${cfg.headerGlow}
        border border-white/[0.05]
      `}>
        <span className={`w-2 h-2 rounded-full ${cfg.dot} ring-2 ring-black/20 shrink-0`} />
        <span className={`text-[13px] font-semibold ${cfg.accentText} tracking-tight`}>
          {cfg.label}
        </span>
        <span className={`
          ml-1 text-[11px] font-bold px-2 py-0.5 rounded-full
          ${cfg.accentText} ${cfg.accentBg} ring-1 ring-white/10
        `}>
          {applications.length}
        </span>

        {/* Clear all — two-step confirm */}
        {applications.length > 0 && (
          <button
            onClick={handleDeleteAll}
            disabled={clearing}
            onBlur={() => setConfirmClear(false)}
            title={confirmClear ? 'Click again to confirm' : `Clear all ${cfg.label}`}
            className={`
              ml-auto flex items-center gap-1.5 px-2 py-1 rounded-lg text-[10px] font-semibold
              transition-all duration-150 disabled:opacity-40
              ${confirmClear
                ? 'bg-rose-500/20 text-rose-300 ring-1 ring-rose-500/40'
                : 'text-zinc-600 hover:text-zinc-400 hover:bg-white/[0.05]'}
            `}
          >
            {clearing ? (
              <svg className="w-3 h-3 animate-spin" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182m0-4.991v4.99" />
              </svg>
            ) : (
              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
              </svg>
            )}
            {confirmClear ? 'Confirm?' : 'Clear all'}
          </button>
        )}
      </div>

      {/* ── Cards ── */}
      <div className="flex flex-col gap-2.5 column-scroll pr-0.5">
        {applications.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-10 px-4 gap-2">
            <span className="text-2xl opacity-40">{cfg.emptyEmoji}</span>
            <p className="text-[11px] text-zinc-700 text-center leading-relaxed">
              {cfg.emptyText}
            </p>
          </div>
        ) : (
          applications.map((app, i) => (
            <div key={app.id} style={{ animationDelay: `${i * 40}ms` }}>
              <ApplicationCard app={app} onUpdate={onUpdate} onDelete={onDelete} />
            </div>
          ))
        )}
      </div>
    </div>
  )
}
