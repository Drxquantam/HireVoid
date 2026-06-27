import React, { useState, useEffect, useRef } from 'react'
import { format, parseISO, isPast, formatDistanceToNow } from 'date-fns'
import type { Application, ApplicationStatus } from '../types'
import { api } from '../api'

interface Props {
  app: Application
  onUpdate: (updated: Application) => void
  onDelete: (id: number) => void
}

const STATUS_OPTIONS: { value: ApplicationStatus; label: string }[] = [
  { value: 'applied',     label: 'Applied'     },
  { value: 'in_progress', label: 'In Progress' },
  { value: 'interview',   label: 'Interview'   },
  { value: 'offer',       label: 'Offer'       },
  { value: 'rejected',    label: 'Rejected'    },
]

const STATUS_STYLE: Record<ApplicationStatus, { border: string; glow: string }> = {
  applied:     { border: 'border-l-indigo-500/60',  glow: 'hover-glow-indigo'  },
  in_progress: { border: 'border-l-amber-500/60',   glow: 'hover-glow-amber'   },
  interview:   { border: 'border-l-sky-400/60',     glow: 'hover-glow-sky'     },
  offer:       { border: 'border-l-emerald-400/60', glow: 'hover-glow-emerald' },
  rejected:    { border: 'border-l-rose-500/60',    glow: 'hover-glow-rose'    },
  unknown:     { border: 'border-l-zinc-600/60',    glow: 'hover-glow-zinc'    },
}

const AVATAR_PALETTE = [
  ['bg-violet-900/80', 'text-violet-300'],
  ['bg-indigo-900/80', 'text-indigo-300'],
  ['bg-sky-900/80',    'text-sky-300'],
  ['bg-teal-900/80',   'text-teal-300'],
  ['bg-emerald-900/80','text-emerald-300'],
  ['bg-amber-900/80',  'text-amber-300'],
  ['bg-rose-900/80',   'text-rose-300'],
  ['bg-pink-900/80',   'text-pink-300'],
]

function avatarStyle(name: string) {
  let h = 0
  for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) >>> 0
  return AVATAR_PALETTE[h % AVATAR_PALETTE.length]
}

function initials(company: string) {
  return company.split(/\s+/).slice(0, 2).map(w => w[0] ?? '').join('').toUpperCase() || '?'
}

function relativeDate(iso: string | null): string {
  if (!iso) return ''
  try { return formatDistanceToNow(parseISO(iso), { addSuffix: true }) } catch { return '' }
}

function shortDate(iso: string | null): string {
  if (!iso) return ''
  try { return format(parseISO(iso), 'MMM d') } catch { return '' }
}

export default function ApplicationCard({ app, onUpdate, onDelete }: Props) {
  const [menuOpen, setMenuOpen] = useState(false)
  const [saving, setSaving]     = useState(false)
  const [deleting, setDeleting] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  // Close on any click outside the menu wrapper
  useEffect(() => {
    if (!menuOpen) return
    function onMouseDown(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', onMouseDown)
    return () => document.removeEventListener('mousedown', onMouseDown)
  }, [menuOpen])

  async function changeStatus(status: ApplicationStatus) {
    setMenuOpen(false)
    setSaving(true)
    try {
      const updated = await api.updateApplication(app.id, { status })
      onUpdate(updated)
    } catch (e) {
      console.error(e)
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete() {
    setMenuOpen(false)
    setDeleting(true)
    try {
      await api.deleteApplication(app.id)
      onDelete(app.id)
    } catch (e) {
      console.error(e)
      setDeleting(false)
    }
  }

  const style = STATUS_STYLE[app.status] ?? STATUS_STYLE.unknown
  const [avatarBg, avatarText] = avatarStyle(app.company)
  const deadlinePast = app.deadline ? isPast(parseISO(app.deadline)) : false

  return (
    <div className={`
      group relative rounded-xl border-l-2 ${style.border} ${style.glow}
      bg-white/[0.03] border border-white/[0.07]
      shadow-[0_2px_8px_rgba(0,0,0,0.35)]
      transition-all duration-200
      ${saving || deleting ? 'opacity-50 pointer-events-none' : 'cursor-default'}
      animate-slide-up
    `}>
      {/* Inner top highlight */}
      <div className="absolute inset-x-0 top-0 h-px rounded-t-xl bg-gradient-to-r from-white/[0.06] via-white/[0.10] to-white/[0.06]" />

      <div className="p-4">
        {/* Avatar + Company + Menu */}
        <div className="flex items-start gap-3">
          <div className={`
            shrink-0 w-9 h-9 rounded-lg ${avatarBg}
            flex items-center justify-center text-[11px] font-bold ${avatarText}
            ring-1 ring-white/10 select-none
          `}>
            {initials(app.company)}
          </div>

          <div className="flex-1 min-w-0 pt-0.5">
            <p className="font-semibold text-zinc-100 text-[13px] leading-snug truncate">
              {app.company}
            </p>
            <p className="text-zinc-400 text-xs mt-0.5 truncate leading-relaxed">
              {app.role || 'Unknown role'}
            </p>
          </div>

          {/* Three-dot menu — ref wraps button + dropdown together */}
          <div className="relative shrink-0 -mt-0.5 -mr-0.5" ref={menuRef}>
            <button
              onClick={() => setMenuOpen(v => !v)}
              className="
                opacity-0 group-hover:opacity-100 transition-opacity duration-150
                w-6 h-6 rounded-md flex items-center justify-center
                text-zinc-600 hover:text-zinc-300 hover:bg-white/[0.07]
              "
            >
              <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
                <path d="M10 6a2 2 0 110-4 2 2 0 010 4zm0 6a2 2 0 110-4 2 2 0 010 4zm0 6a2 2 0 110-4 2 2 0 010 4z" />
              </svg>
            </button>

            {menuOpen && (
              <div className="
                absolute right-0 top-8 z-50 w-40
                bg-zinc-900 border border-white/10 rounded-xl
                shadow-2xl shadow-black/60 overflow-hidden
                animate-fade-in
              ">
                <p className="px-3 pt-2.5 pb-1 text-[10px] font-semibold text-zinc-600 uppercase tracking-widest">
                  Move to
                </p>
                {STATUS_OPTIONS.map(opt => (
                  <button
                    key={opt.value}
                    onClick={() => changeStatus(opt.value)}
                    className="
                      w-full text-left px-3 py-2 text-xs text-zinc-400
                      hover:bg-white/[0.06] hover:text-zinc-100
                      transition-colors duration-100 flex items-center gap-2
                    "
                  >
                    <StatusDot status={opt.value} />
                    {opt.label}
                  </button>
                ))}
                <div className="h-px bg-white/[0.06] mx-3 my-1" />
                <button
                  onClick={handleDelete}
                  className="
                    w-full text-left px-3 py-2 mb-1 text-xs text-rose-400
                    hover:bg-rose-500/10 hover:text-rose-300
                    transition-colors duration-100 flex items-center gap-2
                  "
                >
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round"
                      d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16
                         19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456
                         0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11
                         0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32
                         0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
                  </svg>
                  Remove
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Snippet */}
        {app.email_snippet && (
          <p className="mt-3 text-[11px] text-zinc-400 leading-relaxed line-clamp-2">
            {app.email_snippet}
          </p>
        )}

        {/* Footer */}
        <div className="mt-3 pt-3 border-t border-white/[0.05] flex items-center justify-between gap-2">
          <span className="text-[11px] text-zinc-500 font-medium">
            {relativeDate(app.applied_date) || shortDate(app.applied_date)}
          </span>
          {app.deadline && (
            <span className={`
              text-[10px] px-2 py-0.5 rounded-full font-semibold tracking-wide
              ${deadlinePast
                ? 'bg-rose-500/10 text-rose-400 ring-1 ring-rose-500/20'
                : 'bg-amber-500/10 text-amber-400 ring-1 ring-amber-500/20'}
            `}>
              {deadlinePast ? 'Overdue' : `Due ${shortDate(app.deadline)}`}
            </span>
          )}
        </div>
      </div>
    </div>
  )
}

function StatusDot({ status }: { status: ApplicationStatus }) {
  const colors: Record<ApplicationStatus, string> = {
    applied:     'bg-indigo-400',
    in_progress: 'bg-amber-400',
    interview:   'bg-sky-400',
    offer:       'bg-emerald-400',
    rejected:    'bg-rose-400',
    unknown:     'bg-zinc-500',
  }
  return <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${colors[status] ?? 'bg-zinc-500'}`} />
}
