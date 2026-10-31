import { useEffect, useState } from 'react'
import type { Stage } from '../lib/types'

/*
 * The mentorship workflow drawn as a confluence: the student's stream (request, IIC review,
 * mentor asked) meets the mentor's stream (mentor confirms) at IIC approval, and the two
 * continue as one river (mentoring). Progress comes from the backend-derived request stage.
 */

const NODES = [
  { x: 40, y: 38, label: 'Requested', above: true },
  { x: 150, y: 38, label: 'IIC review', above: true },
  { x: 260, y: 38, label: 'Mentor asked', above: true },
  { x: 330, y: 100, label: 'Mentor confirms', above: false },
  { x: 440, y: 66, label: 'IIC approves', above: true },
  { x: 560, y: 66, label: 'Mentoring', above: true },
] as const

const REACHED: Record<Stage, number> = {
  SUBMITTED: 0, UNDER_REVIEW: 1, WAITING: 1, AVAILABILITY_CHECK_SENT: 2, MENTOR_CONFIRMED: 3,
  AWAITING_IIC_APPROVAL: 3, MATCHED: 5, ACTIVE: 5, WITHDRAWN: -1, CLOSED: -1,
}

// Fraction (0-100) of each stream drawn for a given reached node.
const STUDENT = [8, 30, 52, 82, 100, 100]
const MENTOR = [0, 0, 0, 46, 100, 100]
const RIVER = [0, 0, 0, 0, 0, 100]

const STUDENT_PATH = 'M0 38 H260 C330 38 360 66 440 66'
const MENTOR_PATH = 'M250 112 C285 112 300 100 330 100 C370 100 395 66 440 66'
const RIVER_PATH = 'M440 66 H600'

export function Confluence({ stage, tone = 'light', waiting }: { stage: Stage; tone?: 'light' | 'dark'; waiting?: boolean }) {
  const [ready, setReady] = useState(false)
  useEffect(() => { const id = requestAnimationFrame(() => setReady(true)); return () => cancelAnimationFrame(id) }, [])
  const reached = REACHED[stage] ?? 0
  const ended = reached < 0
  const at = Math.max(0, reached)
  const dark = tone === 'dark'
  const bed = dark ? 'rgba(220,235,230,.18)' : 'var(--color-base-300)'
  const flow = dark ? '#4fb3a2' : 'var(--color-primary)'
  const mentorFlow = dark ? '#f0b54a' : 'var(--color-accent)'
  const offset = (fraction: number) => ({ ['--flow-offset' as string]: String(100 - (ended ? 0 : fraction)) })
  const current = ended || reached >= 5 ? -1 : reached + 1

  return (
    <div className={`relative w-full ${ready ? 'confluence-ready' : ''}`} role="img"
      aria-label={ended ? `Request ${stage.toLowerCase()}` : `Mentorship progress: ${NODES[at].label} reached${current >= 0 ? `, next ${NODES[current].label}` : ''}`}>
      <svg viewBox="0 0 600 140" className="block h-auto w-full overflow-visible" aria-hidden>
        <path d={STUDENT_PATH} fill="none" stroke={bed} strokeWidth="6" strokeLinecap="round" />
        <path d={MENTOR_PATH} fill="none" stroke={bed} strokeWidth="6" strokeLinecap="round" />
        <path d={RIVER_PATH} fill="none" stroke={bed} strokeWidth="12" strokeLinecap="round" />
        {!ended && (
          <>
            <path className="confluence-flow" d={STUDENT_PATH} pathLength={100} fill="none" stroke={flow} strokeWidth="6" strokeLinecap="round" style={offset(STUDENT[at])} />
            <path className="confluence-flow" d={MENTOR_PATH} pathLength={100} fill="none" stroke={mentorFlow} strokeWidth="6" strokeLinecap="round" style={offset(MENTOR[at])} />
            <path className="confluence-flow" d={RIVER_PATH} pathLength={100} fill="none" stroke={flow} strokeWidth="12" strokeLinecap="round" style={offset(RIVER[at])} />
          </>
        )}
        {NODES.map((n, i) => {
          const done = !ended && i <= reached
          const now = i === current
          return (
            <g key={n.label}>
              {now && <circle className="confluence-node-now" cx={n.x} cy={n.y} r="11" fill={waiting ? mentorFlow : flow} opacity=".35" />}
              <circle cx={n.x} cy={n.y} r={i === 5 ? 9 : 7} fill={done ? (i === 3 ? mentorFlow : flow) : dark ? '#102632' : 'var(--color-base-100)'}
                stroke={done || now ? (i === 3 ? mentorFlow : flow) : bed} strokeWidth="3" />
            </g>
          )
        })}
      </svg>
      {NODES.map((n, i) => (
        <span key={n.label} className={`absolute -translate-x-1/2 text-[11px] leading-tight font-medium whitespace-nowrap sm:text-xs ${
          i === 0 || i === 5 || i === current || (current < 0 && i === reached) ? '' : 'hidden sm:block'} ${
          !ended && i <= reached ? (dark ? 'text-white' : 'text-base-content') : i === current ? (dark ? 'text-[#f0b54a]' : 'text-accent') : dark ? 'text-white/45' : 'text-base-content/45'}`}
          style={{ left: `${(n.x / 600) * 100}%`, top: n.above ? `${((n.y - 30) / 140) * 100}%` : `${((n.y + 16) / 140) * 100}%` }}>
          {n.label}
        </span>
      ))}
    </div>
  )
}
