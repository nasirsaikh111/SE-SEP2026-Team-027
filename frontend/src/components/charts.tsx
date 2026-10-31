import { Bar, BarChart, CartesianGrid, LabelList, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { MonthPoint } from '../lib/types'

const tooltipStyle = {
  contentStyle: { background: 'var(--color-base-100)', border: '1px solid var(--color-base-300)', borderRadius: 8, fontSize: 12, color: 'var(--color-base-content)' },
  labelStyle: { color: 'var(--color-base-content)', fontWeight: 600 },
  cursor: { fill: 'var(--color-base-200)' },
}

/** Single-series horizontal bars (magnitude by category). Value labels at the bar tip; no legend. */
export function CategoryBars({ data, label, height }: { data: { name: string; value: number }[]; label: string; height?: number }) {
  if (!data.length) return <p className="text-base-content/60 py-6 text-center text-sm">No data yet.</p>
  return (
    <div className="viz" role="img" aria-label={`${label}: ${data.map((d) => `${d.name} ${d.value}`).join(', ')}`}>
      <ResponsiveContainer width="100%" height={height ?? Math.max(120, data.length * 34 + 20)}>
        <BarChart data={data} layout="vertical" margin={{ top: 4, right: 32, bottom: 4, left: 4 }} barCategoryGap={8}>
          <CartesianGrid horizontal={false} strokeWidth={1} />
          <XAxis type="number" allowDecimals={false} axisLine={false} tickLine={false} />
          <YAxis type="category" dataKey="name" width={120} axisLine={false} tickLine={false} />
          <Tooltip {...tooltipStyle} formatter={(v) => [v, label]} />
          <Bar dataKey="value" name={label} fill="var(--viz-1)" radius={[0, 4, 4, 0]} maxBarSize={24} isAnimationActive={false}>
            <LabelList dataKey="value" position="right" style={{ fill: 'var(--viz-text)', fontSize: 11 }} />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

const SERIES = [
  { key: 'requests', name: 'Requests submitted', color: 'var(--viz-1)' },
  { key: 'mentorships', name: 'Mentorships started', color: 'var(--viz-2)' },
  { key: 'meetings', name: 'Meetings held', color: 'var(--viz-3)' },
] as const

/** Three count series on one shared axis (same unit), legend + crosshair tooltip. */
export function MonthlyActivity({ requests, mentorships, meetings }: { requests: MonthPoint[]; mentorships: MonthPoint[]; meetings: MonthPoint[] }) {
  const rows = requests.map((r, i) => ({
    month: new Date(`${r.month}-01T00:00:00`).toLocaleDateString('en-IN', { month: 'short' }),
    requests: r.count, mentorships: mentorships[i]?.count ?? 0, meetings: meetings[i]?.count ?? 0,
  }))
  return (
    <div className="viz" role="img" aria-label="Monthly requests, mentorships started and meetings held over the last six months">
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={rows} margin={{ top: 8, right: 12, bottom: 0, left: -16 }}>
          <CartesianGrid vertical={false} strokeWidth={1} />
          <XAxis dataKey="month" axisLine={false} tickLine={false} />
          <YAxis allowDecimals={false} axisLine={false} tickLine={false} />
          <Tooltip {...tooltipStyle} cursor={{ stroke: 'var(--color-base-300)', strokeWidth: 1 }} />
          <Legend iconType="plainline" wrapperStyle={{ fontSize: 12 }} />
          {SERIES.map((s) => (
            <Line key={s.key} type="linear" dataKey={s.key} name={s.name} stroke={s.color} strokeWidth={2}
              dot={{ r: 4, strokeWidth: 2, stroke: 'var(--color-base-100)', fill: s.color }} activeDot={{ r: 5 }} isAnimationActive={false} />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

/** Accessible table view of a chart's data. */
export function DataTable({ rows, columns }: { rows: Record<string, string | number>[]; columns: { key: string; label: string }[] }) {
  return (
    <details className="mt-1">
      <summary className="text-base-content/60 cursor-pointer text-xs">View as table</summary>
      <table className="table table-xs mt-2">
        <thead><tr>{columns.map((c) => <th key={c.key}>{c.label}</th>)}</tr></thead>
        <tbody>{rows.map((r, i) => <tr key={i}>{columns.map((c) => <td key={c.key} className="tabular-nums">{r[c.key]}</td>)}</tr>)}</tbody>
      </table>
    </details>
  )
}
