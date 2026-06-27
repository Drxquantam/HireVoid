import React from 'react'
import type { Application, ApplicationStatus, GroupedApplications } from '../types'
import StatusColumn from './StatusColumn'

const COLUMN_ORDER: ApplicationStatus[] = [
  'applied', 'in_progress', 'interview', 'offer', 'rejected',
]

interface Props {
  grouped: GroupedApplications
  onUpdate: (updated: Application) => void
  onDelete: (id: number) => void
  onDeleteAll: (status: ApplicationStatus) => void
}

export default function KanbanBoard({ grouped, onUpdate, onDelete, onDeleteAll }: Props) {
  return (
    <div className="flex gap-4 px-5 pb-8 overflow-x-auto">
      {COLUMN_ORDER.map(status => (
        <StatusColumn
          key={status}
          status={status}
          applications={grouped[status] ?? []}
          onUpdate={onUpdate}
          onDelete={onDelete}
          onDeleteAll={onDeleteAll}
        />
      ))}
    </div>
  )
}
