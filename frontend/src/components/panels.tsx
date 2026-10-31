import { useState } from 'react'
import { Bot, CheckCheck, SendHorizonal, ShieldCheck } from 'lucide-react'
import { errorMessage } from '../lib/api'
import { timeAgo } from '../lib/format'
import { useChat, useNotificationActions, useNotifications } from '../lib/queries'
import type { ChatReply } from '../lib/types'
import { EmptyState, ErrorAlert, Loading, Pager } from './ui'

interface Turn { question: string; reply?: ChatReply; error?: string }

const STARTERS = ['How does mentor matching work?', 'How long does a mentor have to respond?', 'Who can see my feedback?']

/** Helpdesk chat grounded in IIC-published guidance. Nothing typed here is stored. */
export function AssistantPanel() {
  const chat = useChat()
  const [turns, setTurns] = useState<Turn[]>([])
  const [message, setMessage] = useState('')
  const ask = async (text = message) => {
    const question = text.trim()
    if (question.length < 2) return
    setMessage('')
    setTurns((t) => [...t, { question }])
    try {
      const reply = await chat.mutateAsync(question)
      setTurns((t) => t.map((x, i) => (i === t.length - 1 ? { ...x, reply } : x)))
    } catch (err) {
      setTurns((t) => t.map((x, i) => (i === t.length - 1 ? { ...x, error: errorMessage(err) } : x)))
    }
  }
  return (
    <div className="flex h-full min-h-[60vh] flex-col gap-4">
      <div className="flex flex-1 flex-col gap-4" aria-live="polite">
        {turns.length === 0 && (
          <div className="flex flex-col gap-3 py-4">
            <Bot size={28} className="text-primary" strokeWidth={1.6} />
            <p className="text-base-content/70">Ask about how Sangam works. Answers come from guidance published by IIC; the assistant cannot approve requests or pairings.</p>
            <div className="flex flex-wrap gap-2">
              {STARTERS.map((s) => <button key={s} className="btn btn-sm btn-outline border-base-300 font-normal" onClick={() => ask(s)}>{s}</button>)}
            </div>
          </div>
        )}
        {turns.map((t, i) => (
          <div key={i} className="flex flex-col gap-2">
            <div className="bg-neutral text-neutral-content ml-auto max-w-[85%] rounded-2xl rounded-br-md px-4 py-2 text-sm">{t.question}</div>
            <div className="bg-base-200 mr-auto max-w-[90%] rounded-2xl rounded-bl-md px-4 py-2.5 text-sm whitespace-pre-line">
              {t.error ? <span className="text-error">{t.error}</span> : t.reply ? t.reply.answer : <span className="loading loading-dots loading-sm" />}
              {t.reply && t.reply.sources.length > 0 && <div className="text-base-content/50 mt-2 text-xs">From: {t.reply.sources.map((s) => s.title).join(', ')}</div>}
            </div>
          </div>
        ))}
      </div>
      <form className="bg-base-200 sticky bottom-0 flex items-center gap-2 rounded-2xl p-1.5" onSubmit={(e) => { e.preventDefault(); ask() }}>
        <input className="w-full bg-transparent px-3 py-2 outline-none" maxLength={1000} placeholder="Ask a question" value={message} onChange={(e) => setMessage(e.target.value)} aria-label="Question" />
        <button className="btn btn-primary btn-circle btn-sm" disabled={chat.isPending || message.trim().length < 2} aria-label="Send"><SendHorizonal size={16} /></button>
      </form>
      <p className="text-base-content/50 flex items-center gap-1.5 text-xs"><ShieldCheck size={13} />Conversations are not saved. Leave out passwords and roll numbers.</p>
    </div>
  )
}

export function NotificationsList({ pageSize = 30 }: { pageSize?: number }) {
  const [page, setPage] = useState(1)
  const list = useNotifications({ page, page_size: pageSize })
  const { read, readAll } = useNotificationActions()
  if (list.isPending) return <Loading />
  if (list.isError) return <ErrorAlert error={list.error} />
  if (list.data.results.length === 0) return <EmptyState title="You're all caught up" description="Updates about approvals, requests and meetings appear here." />
  const unread = list.data.results.some((n) => !n.is_read)
  return (
    <div className="flex flex-col">
      {unread && <button className="btn btn-ghost btn-sm mb-1 self-end" disabled={readAll.isPending} onClick={() => readAll.mutate()}><CheckCheck size={15} />Mark all as read</button>}
      <ul className="rows">
        {list.data.results.map((n) => (
          <li key={n.id}>
            <button className="row-link -mx-2 flex w-[calc(100%+1rem)] items-start gap-3 px-2 py-3 text-left" onClick={() => !n.is_read && read.mutate(n.id)} disabled={n.is_read}>
              <span className={`mt-2 size-2 shrink-0 rounded-full ${n.is_read ? 'bg-transparent' : 'bg-accent'}`} aria-label={n.is_read ? undefined : 'Unread'} />
              <span className="min-w-0 flex-1">
                <span className={`block ${n.is_read ? 'text-base-content/80' : 'font-semibold'}`}>{n.title}</span>
                <span className="text-base-content/65 block text-sm">{n.message}</span>
                <span className="text-base-content/45 text-xs">{timeAgo(n.created_at)}</span>
              </span>
            </button>
          </li>
        ))}
      </ul>
      <Pager page={page} count={list.data.count} pageSize={pageSize} onChange={setPage} />
    </div>
  )
}
