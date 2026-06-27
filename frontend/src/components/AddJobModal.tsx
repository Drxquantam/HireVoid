import React, { useState, useEffect, useRef } from 'react'
import type { Application, ApplicationStatus } from '../types'
import { api } from '../api'

interface Props {
  onClose: () => void
  onCreated: (app: Application) => void
}

const STATUS_OPTIONS: { value: ApplicationStatus; label: string; dot: string }[] = [
  { value: 'applied',     label: 'Applied',     dot: 'bg-indigo-400'  },
  { value: 'in_progress', label: 'In Progress', dot: 'bg-amber-400'   },
  { value: 'interview',   label: 'Interview',   dot: 'bg-sky-400'     },
  { value: 'offer',       label: 'Offer',       dot: 'bg-emerald-400' },
  { value: 'rejected',    label: 'Rejected',    dot: 'bg-rose-400'    },
]

export default function AddJobModal({ onClose, onCreated }: Props) {
  const [company, setCompany]         = useState('')
  const [role, setRole]               = useState('')
  const [status, setStatus]           = useState<ApplicationStatus>('applied')
  const [appliedDate, setAppliedDate] = useState(new Date().toISOString().slice(0, 10))
  const [deadline, setDeadline]       = useState('')
  const [saving, setSaving]           = useState(false)
  const [error, setError]             = useState('')
  const companyRef = useRef<HTMLInputElement>(null)

  // Auto-focus company field and close on Escape
  useEffect(() => {
    companyRef.current?.focus()
    function onKey(e: KeyboardEvent) { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [onClose])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!company.trim()) { setError('Company name is required.'); return }
    if (!role.trim())    { setError('Role / position is required.'); return }

    setSaving(true)
    setError('')
    try {
      const created = await api.createApplication({
        company: company.trim(),
        role:    role.trim(),
        status,
        applied_date: appliedDate || undefined,
        deadline:     deadline    || undefined,
      })
      onCreated(created)
      onClose()
    } catch (e: any) {
      setError(e.message ?? 'Something went wrong.')
      setSaving(false)
    }
  }

  return (
    /* Backdrop */
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(4px)' }}
      onMouseDown={e => { if (e.target === e.currentTarget) onClose() }}
    >
      <div className="
        w-full max-w-md rounded-2xl
        bg-zinc-900 border border-white/10
        shadow-2xl shadow-black/60
        animate-slide-up
      ">
        {/* Header */}
        <div className="flex items-center justify-between px-6 pt-5 pb-4 border-b border-white/[0.06]">
          <div>
            <h2 className="text-base font-semibold text-zinc-100">Add a job manually</h2>
            <p className="text-xs text-zinc-500 mt-0.5">Track an application you submitted outside email</p>
          </div>
          <button
            onClick={onClose}
            className="w-7 h-7 rounded-lg flex items-center justify-center text-zinc-600 hover:text-zinc-300 hover:bg-white/[0.06] transition-colors"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="px-6 py-5 flex flex-col gap-4">

          {/* Company */}
          <div className="flex flex-col gap-1.5">
            <label className="text-[11px] font-semibold text-zinc-500 uppercase tracking-widest">
              Company <span className="text-rose-400">*</span>
            </label>
            <input
              ref={companyRef}
              value={company}
              onChange={e => setCompany(e.target.value)}
              placeholder="e.g. Google, Stripe, Zepto"
              className="
                w-full px-3.5 py-2.5 rounded-xl text-sm text-zinc-100
                bg-white/[0.04] border border-white/[0.08]
                placeholder:text-zinc-700
                focus:outline-none focus:border-indigo-500/60 focus:bg-white/[0.06]
                transition-colors
              "
            />
          </div>

          {/* Role */}
          <div className="flex flex-col gap-1.5">
            <label className="text-[11px] font-semibold text-zinc-500 uppercase tracking-widest">
              Role / Position <span className="text-rose-400">*</span>
            </label>
            <input
              value={role}
              onChange={e => setRole(e.target.value)}
              placeholder="e.g. Software Engineer Intern"
              className="
                w-full px-3.5 py-2.5 rounded-xl text-sm text-zinc-100
                bg-white/[0.04] border border-white/[0.08]
                placeholder:text-zinc-700
                focus:outline-none focus:border-indigo-500/60 focus:bg-white/[0.06]
                transition-colors
              "
            />
          </div>

          {/* Status */}
          <div className="flex flex-col gap-1.5">
            <label className="text-[11px] font-semibold text-zinc-500 uppercase tracking-widest">
              Status
            </label>
            <div className="grid grid-cols-5 gap-1.5">
              {STATUS_OPTIONS.map(opt => (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => setStatus(opt.value)}
                  className={`
                    flex flex-col items-center gap-1.5 py-2.5 px-1 rounded-xl text-[10px] font-semibold
                    border transition-all duration-150
                    ${status === opt.value
                      ? 'border-white/20 bg-white/[0.08] text-zinc-100'
                      : 'border-white/[0.05] bg-white/[0.02] text-zinc-600 hover:text-zinc-400 hover:bg-white/[0.04]'}
                  `}
                >
                  <span className={`w-2 h-2 rounded-full ${opt.dot}`} />
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {/* Dates row */}
          <div className="grid grid-cols-2 gap-3">
            <div className="flex flex-col gap-1.5">
              <label className="text-[11px] font-semibold text-zinc-500 uppercase tracking-widest">
                Applied Date
              </label>
              <input
                type="date"
                value={appliedDate}
                onChange={e => setAppliedDate(e.target.value)}
                className="
                  w-full px-3.5 py-2.5 rounded-xl text-sm text-zinc-300
                  bg-white/[0.04] border border-white/[0.08]
                  focus:outline-none focus:border-indigo-500/60
                  transition-colors [color-scheme:dark]
                "
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-[11px] font-semibold text-zinc-500 uppercase tracking-widest">
                Deadline <span className="text-zinc-700 normal-case font-normal">(optional)</span>
              </label>
              <input
                type="date"
                value={deadline}
                onChange={e => setDeadline(e.target.value)}
                className="
                  w-full px-3.5 py-2.5 rounded-xl text-sm text-zinc-300
                  bg-white/[0.04] border border-white/[0.08]
                  focus:outline-none focus:border-indigo-500/60
                  transition-colors [color-scheme:dark]
                "
              />
            </div>
          </div>

          {/* Error */}
          {error && (
            <p className="text-xs text-rose-400 bg-rose-500/10 border border-rose-500/20 rounded-lg px-3 py-2">
              {error}
            </p>
          )}

          {/* Actions */}
          <div className="flex gap-2 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="
                flex-1 py-2.5 rounded-xl text-sm font-medium text-zinc-500
                bg-white/[0.03] border border-white/[0.06]
                hover:text-zinc-300 hover:bg-white/[0.06]
                transition-colors
              "
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="
                flex-1 py-2.5 rounded-xl text-sm font-semibold text-white
                bg-gradient-to-r from-indigo-600 to-violet-600
                hover:from-indigo-500 hover:to-violet-500
                disabled:opacity-50 disabled:cursor-not-allowed
                shadow-lg shadow-indigo-900/30
                transition-all duration-200 active:scale-[0.98]
              "
            >
              {saving ? 'Adding…' : 'Add Job'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
