import { useEffect, useRef, type ReactNode } from 'react'
import { Link } from 'react-router'
import { AlertCircle, ChevronRight, X } from 'lucide-react'
import type { UseQueryResult } from '@tanstack/react-query'
import { errorMessage } from '../lib/api'
import { PRIORITY, STAGE, formatDateTime, type Tone } from '../lib/format'
import type { Priority, Stage, Task } from '../lib/types'

const BADGE_TONE: Record<Tone, string> = {
  neutral: 'bg-base-content/8 text-base-content/75', info: 'bg-info/12 text-info', primary: 'bg-primary/12 text-primary',
  success: 'bg-success/12 text-success', warning: 'bg-warning/20 text-warning-content dark:text-warning', error: 'bg-error/12 text-error',
  ghost: 'bg-transparent text-base-content/50 border border-base-300',
}

export function Badge({ tone = 'neutral', children, className = '' }: { tone?: Tone; children: ReactNode; className?: string }) {
  return <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium whitespace-nowrap ${BADGE_TONE[tone]} ${className}`}>{children}</span>
}

export function StageBadge({ stage }: { stage: Stage }) {
  const s = STAGE[stage] ?? { label: stage, tone: 'neutral' as Tone }
  return <Badge tone={s.tone}>{s.label}</Badge>
}

export function PriorityBadge({ priority }: { priority: Priority }) {
  const p = PRIORITY[priority]
  return <Badge tone={p.tone}>{p.label} priority</Badge>
}

export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: ReactNode; actions?: ReactNode }) {
  return (
    <header className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div className="min-w-0 max-w-2xl">
        <h1 className="text-title sm:text-display font-semibold">{title}</h1>
        {subtitle && <p className="text-base-content/65 mt-1.5">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </header>
  )
}

/** A quiet surface. Titles are plain headings; no decorative chrome. */
export function Card({ title, actions, children, className = '', bodyClass = '' }: { title?: ReactNode; actions?: ReactNode; children: ReactNode; className?: string; bodyClass?: string }) {
  return (
    <section className={`panel ${className}`}>
      <div className={`flex flex-col gap-3 p-5 ${bodyClass}`}>
        {(title || actions) && (
          <div className="flex items-center justify-between gap-2">
            {title && <h2 className="text-base font-semibold">{title}</h2>}
            {actions}
          </div>
        )}
        {children}
      </div>
    </section>
  )
}

export function EmptyState({ title, description, action, icon }: { title: string; description?: string; action?: ReactNode; icon?: ReactNode }) {
  return (
    <div className="flex flex-col items-start gap-2 px-1 py-8">
      {icon && <span className="text-primary/70">{icon}</span>}
      <p className="font-display text-lg font-semibold">{title}</p>
      {description && <p className="text-base-content/65 max-w-md">{description}</p>}
      {action && <div className="mt-1">{action}</div>}
    </div>
  )
}

export function ErrorAlert({ error, title }: { error: unknown; title?: string }) {
  if (!error) return null
  return (
    <div role="alert" className="bg-error/10 text-error flex items-start gap-2 rounded-xl px-3 py-2 text-sm">
      <AlertCircle size={16} className="mt-0.5 shrink-0" />
      <span>{title ? <strong className="mr-1">{title}</strong> : null}{errorMessage(error)}</span>
    </div>
  )
}

export function Loading({ label = 'Loading' }: { label?: string }) {
  return (
    <div className="flex items-center justify-center py-12" role="status" aria-live="polite">
      <span className="loading loading-ring loading-lg text-primary" />
      <span className="sr-only">{label}</span>
    </div>
  )
}

export function QueryView<T>({ query, children }: { query: UseQueryResult<T>; children: (data: T) => ReactNode }) {
  if (query.isPending) return <Loading />
  if (query.isError) return <ErrorAlert error={query.error} />
  return <>{children(query.data)}</>
}

type ModalSize = 'sm' | 'md' | 'lg'
const MODAL_WIDTH: Record<ModalSize, string> = { sm: 'max-w-md', md: 'max-w-xl', lg: 'max-w-3xl' }

/**
 * Native <dialog> modal. `variant="sheet"` slides in from the right for detail views;
 * the centred variant is for focused actions. Escape and backdrop click close it.
 */
export function Modal({ open, onClose, title, subtitle, children, actions, size = 'md', variant = 'center', wide }: {
  open: boolean; onClose: () => void; title: ReactNode; subtitle?: ReactNode; children: ReactNode; actions?: ReactNode
  size?: ModalSize; variant?: 'center' | 'sheet'; wide?: boolean
}) {
  const ref = useRef<HTMLDialogElement>(null)
  useEffect(() => {
    const dialog = ref.current
    if (!dialog) return
    if (open && !dialog.open) dialog.showModal()
    if (!open && dialog.open) dialog.close()
  }, [open])
  const sheet = variant === 'sheet'
  return (
    <dialog ref={ref} className={`modal ${sheet ? `sheet ${wide ? 'sheet-wide' : ''}` : 'modal-bottom sm:modal-middle'}`} onClose={onClose}>
      <div className={`modal-box flex flex-col gap-0 p-0 ${sheet ? '' : `${MODAL_WIDTH[wide ? 'lg' : size]} w-full`}`}>
        <div className="flex items-start justify-between gap-3 px-6 pt-5 pb-3">
          <div className="min-w-0">
            <h3 className="font-display text-xl font-semibold leading-tight">{title}</h3>
            {subtitle && <div className="text-base-content/60 mt-1 text-sm">{subtitle}</div>}
          </div>
          <button type="button" className="btn btn-ghost btn-sm btn-circle -mr-2" onClick={onClose} aria-label="Close"><X size={18} /></button>
        </div>
        <div className={`flex flex-col gap-4 px-6 pb-6 ${sheet ? 'flex-1 overflow-y-auto' : ''}`}>{open && children}</div>
        {actions && <div className="border-base-300 bg-base-200/50 flex flex-wrap justify-end gap-2 border-t px-6 py-3">{actions}</div>}
      </div>
      <form method="dialog" className="modal-backdrop"><button aria-label="Close">close</button></form>
    </dialog>
  )
}

export function Field({ label, error, hint, children }: { label: string; error?: string; hint?: string; children: ReactNode }) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-sm font-medium">{label}</span>
      {children}
      {error ? <span className="text-error text-xs">{error}</span> : hint ? <span className="text-base-content/55 text-xs">{hint}</span> : null}
    </label>
  )
}

/** A figure: big number, small label. Linked figures are the IIC's queue entry points. */
export function Stat({ label, value, hint, to, attention }: { label: string; value: ReactNode; hint?: ReactNode; to?: string; attention?: boolean }) {
  const body = (
    <div className="flex h-full flex-col gap-0.5 px-1 py-2">
      <span className={`font-display text-3xl font-semibold tabular-nums ${attention ? 'text-accent dark:text-accent' : ''}`}>{value}</span>
      <span className="text-base-content/70 text-sm leading-snug">{label}</span>
      {hint && <span className="text-base-content/50 text-xs">{hint}</span>}
    </div>
  )
  return to ? <Link to={to} className="row-link block px-2">{body}</Link> : <div className="px-2">{body}</div>
}

export function TaskList({ tasks, emptyText = 'Nothing needs your attention.' }: { tasks: Task[]; emptyText?: string }) {
  if (!tasks.length) return <p className="text-base-content/60 text-sm">{emptyText}</p>
  return (
    <ul className="rows">
      {tasks.map((t) => (
        <li key={t.key}>
          <Link to={t.link} className="row-link -mx-2 flex items-center gap-3 px-2 py-2.5">
            <span className={`size-2 shrink-0 rounded-full ${t.tone === 'warning' || t.tone === 'primary' ? 'bg-accent' : 'bg-primary/50'}`} aria-hidden />
            <span className="flex-1 text-sm">{t.label}</span>
            {t.count != null && <span className="font-display text-sm font-semibold tabular-nums">{t.count}</span>}
            <ChevronRight size={16} className="text-base-content/35" />
          </Link>
        </li>
      ))}
    </ul>
  )
}

export function Timeline({ items }: { items: { key: string | number; title: string; detail?: string; at: string; tone?: Tone }[] }) {
  if (!items.length) return <p className="text-base-content/60 text-sm">No activity yet.</p>
  return (
    <ol className="border-base-300 ml-1.5 border-l-2">
      {items.map((item) => (
        <li key={item.key} className="relative pb-4 pl-5 last:pb-0">
          <span aria-hidden className={`ring-base-100 absolute top-1.5 -left-[7px] size-3 rounded-full ring-3 ${item.tone === 'success' ? 'bg-success' : item.tone === 'warning' ? 'bg-accent' : item.tone === 'ghost' ? 'bg-base-300' : 'bg-primary'}`} />
          <div className="flex flex-wrap items-baseline justify-between gap-x-3">
            <span className="text-sm font-semibold">{item.title}</span>
            <time className="text-base-content/50 text-xs whitespace-nowrap">{formatDateTime(item.at)}</time>
          </div>
          {item.detail && <p className="text-base-content/65 text-sm">{item.detail}</p>}
        </li>
      ))}
    </ol>
  )
}

export function Pager({ page, count, pageSize = 50, onChange }: { page: number; count: number; pageSize?: number; onChange: (p: number) => void }) {
  const pages = Math.max(1, Math.ceil(count / pageSize))
  if (pages <= 1) return null
  return (
    <div className="mt-4 flex items-center justify-end gap-2 text-sm">
      <button className="btn btn-ghost btn-sm" disabled={page <= 1} onClick={() => onChange(page - 1)}>Previous</button>
      <span className="text-base-content/60 tabular-nums">Page {page} of {pages}</span>
      <button className="btn btn-ghost btn-sm" disabled={page >= pages} onClick={() => onChange(page + 1)}>Next</button>
    </div>
  )
}

export function Tabs<K extends string>({ tabs, value, onChange }: { tabs: { key: K; label: string; count?: number }[]; value: K; onChange: (k: K) => void }) {
  return (
    <div role="tablist" className="bg-base-100 border-base-300 mb-4 inline-flex max-w-full gap-1 overflow-x-auto rounded-full border p-1">
      {tabs.map((t) => (
        <button key={t.key} role="tab" aria-selected={value === t.key} onClick={() => onChange(t.key)}
          className={`rounded-full px-3.5 py-1.5 text-sm font-medium whitespace-nowrap transition-colors ${value === t.key ? 'bg-neutral text-neutral-content' : 'text-base-content/65 hover:text-base-content'}`}>
          {t.label}{t.count != null && <span className="ml-1.5 tabular-nums opacity-70">{t.count}</span>}
        </button>
      ))}
    </div>
  )
}

/** Clickable list row that opens a modal. */
export function RowButton({ onClick, children, className = '' }: { onClick: () => void; children: ReactNode; className?: string }) {
  return <button type="button" onClick={onClick} className={`row-link -mx-2 flex w-[calc(100%+1rem)] items-center gap-3 px-2 py-3 text-left ${className}`}>{children}</button>
}
