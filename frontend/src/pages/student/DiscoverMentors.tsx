import { useState } from 'react'
import { Link } from 'react-router'
import { Link2, Search, ShieldCheck, SlidersHorizontal, X } from 'lucide-react'
import { useAuth } from '../../auth/AuthContext'
import { useMentorDirectory, useMentorFacets } from '../../lib/queries'
import type { DirectoryMentor } from '../../lib/types'
import { Badge, EmptyState, ErrorAlert, Loading, Modal, PageHeader, Pager } from '../../components/ui'
import { RequestFormModal, useOpenRequest } from './requestModals'

const EMPTY = { search: '', domain: '', specialty: '', career_path: '', min_experience: '', available: '' }

function initials(name: string) {
  return name.split(' ').map((p) => p[0]).slice(0, 2).join('').toUpperCase()
}

function MentorAvatar({ m, size = 'md' }: { m: DirectoryMentor; size?: 'md' | 'lg' }) {
  return (
    <span className={`bg-neutral text-neutral-content font-display grid shrink-0 place-items-center rounded-2xl font-semibold ${size === 'lg' ? 'size-16 text-xl' : 'size-12 text-base'}`}>
      {initials(m.name)}
    </span>
  )
}

function MentorProfileModal({ mentor, onClose, onRequest, blockedReason }: { mentor: DirectoryMentor | null; onClose: () => void; onRequest: () => void; blockedReason?: string }) {
  return (
    <Modal variant="sheet" open={!!mentor} onClose={onClose} title={mentor?.name ?? ''} subtitle={mentor && `${mentor.current_role}${mentor.company ? ` at ${mentor.company}` : ''}`}>
      {mentor && (
        <>
          <div className="flex items-center gap-4">
            <MentorAvatar m={mentor} size="lg" />
            <div className="flex flex-col items-start gap-1.5">
              <span className="text-primary inline-flex items-center gap-1.5 text-sm font-medium"><ShieldCheck size={16} />Verified IITM alumnus{mentor.graduation_year ? `, class of ${mentor.graduation_year}` : ''}</span>
              <Badge tone={mentor.availability.accepting_requests ? 'success' : 'neutral'}>{mentor.availability.label}</Badge>
            </div>
          </div>
          {mentor.bio && <p className="text-base-content/80">{mentor.bio}</p>}
          <dl className="grid grid-cols-2 gap-3">
            <div className="bg-base-200 rounded-xl p-3"><dt className="text-base-content/60 text-xs">Domain</dt><dd className="font-medium">{mentor.domain}</dd></div>
            <div className="bg-base-200 rounded-xl p-3"><dt className="text-base-content/60 text-xs">Specialty</dt><dd className="font-medium">{mentor.specialty}</dd></div>
            <div className="bg-base-200 rounded-xl p-3"><dt className="text-base-content/60 text-xs">Experience</dt><dd className="font-medium">{mentor.experience_years} years</dd></div>
            <div className="bg-base-200 rounded-xl p-3"><dt className="text-base-content/60 text-xs">Career pathway</dt><dd className="font-medium">{mentor.career_path || 'Not stated'}</dd></div>
          </dl>
          {mentor.skills.length > 0 && (
            <div>
              <h4 className="mb-2 text-sm font-semibold">Skills</h4>
              <div className="flex flex-wrap gap-1.5">{mentor.skills.map((s) => <span key={s} className="border-base-300 rounded-full border px-3 py-1 text-sm">{s}</span>)}</div>
            </div>
          )}
          {mentor.linkedin_url && <a href={mentor.linkedin_url} target="_blank" rel="noopener noreferrer" className="link link-hover inline-flex items-center gap-1.5 text-sm"><Link2 size={15} />LinkedIn profile</a>}
          <div className="bg-base-200 rounded-xl p-4 text-sm">
            <p className="font-semibold">How this works</p>
            <p className="text-base-content/70 mt-1">You can name {mentor.name.split(' ')[0]} as your preference. IIC reviews your request, checks whether they can take you on, and approves the pairing. Contact details are shared after approval.</p>
          </div>
          {blockedReason ? <p className="text-base-content/60 text-sm">{blockedReason}</p> : (
            <button className="btn btn-primary btn-lg mt-auto" onClick={onRequest}>Ask for {mentor.name.split(' ')[0]} as my mentor</button>
          )}
        </>
      )}
    </Modal>
  )
}

export default function DiscoverMentorsPage() {
  const { me } = useAuth()
  if (me?.effective_role === 'STUDENT' && me.student_profile?.approval_status !== 'APPROVED') {
    return (
      <>
        <PageHeader title="Discover mentors" />
        <EmptyState title="The directory opens once IIC approves you" description="IIC verifies your academic details first. You'll get a notification when that's done."
          action={<Link to="/profile" className="btn btn-primary btn-sm">Check my profile</Link>} />
      </>
    )
  }
  return <Directory />
}

function Directory() {
  const facets = useMentorFacets()
  const [filters, setFilters] = useState(EMPTY)
  const [page, setPage] = useState(1)
  const [viewing, setViewing] = useState<DirectoryMentor | null>(null)
  const [requesting, setRequesting] = useState<DirectoryMentor | null>(null)
  const [showFilters, setShowFilters] = useState(false)
  const directory = useMentorDirectory({ ...filters, page })
  const { open: openRequest } = useOpenRequest()
  const set = (key: keyof typeof EMPTY, value: string) => { setPage(1); setFilters((f) => ({ ...f, [key]: value })) }
  const activeFilters = Object.entries(filters).filter(([k, v]) => v && k !== 'search' && k !== 'available').length
  const blocked = openRequest ? (openRequest.stage === 'ACTIVE' ? 'You already have an active mentorship.' : 'You already have a request with IIC. Withdraw it first to ask for someone else.') : undefined

  return (
    <>
      <PageHeader title="Discover mentors" subtitle="Verified IITM alumni, curated by IIC. Name someone you'd like to learn from; IIC makes the final pairing." />
      {openRequest && (
        <div className="bg-accent/15 mb-5 flex flex-wrap items-center justify-between gap-2 rounded-2xl px-4 py-3 text-sm">
          <span>{blocked}</span>
          <Link to={openRequest.stage === 'ACTIVE' ? '/mentorship' : `/requests/${openRequest.id}`} className="btn btn-sm">View it</Link>
        </div>
      )}
      <div className="mb-6 flex flex-wrap items-center gap-2">
        <label className="bg-base-100 border-base-300 focus-within:border-primary flex h-11 min-w-64 flex-1 items-center gap-2 rounded-full border px-4">
          <Search size={17} className="opacity-50" />
          <input type="search" className="w-full bg-transparent outline-none" placeholder="Search by name, company or skill" value={filters.search} onChange={(e) => set('search', e.target.value)} aria-label="Search mentors" />
        </label>
        <button className={`btn h-11 rounded-full ${activeFilters ? 'btn-neutral' : 'bg-base-100 border-base-300'}`} onClick={() => setShowFilters(true)}>
          <SlidersHorizontal size={16} />Filters{activeFilters ? ` (${activeFilters})` : ''}
        </button>
        <label className="bg-base-100 border-base-300 flex h-11 cursor-pointer items-center gap-2 rounded-full border px-4 text-sm">
          <input type="checkbox" className="toggle toggle-primary toggle-sm" checked={filters.available === 'true'} onChange={(e) => set('available', e.target.checked ? 'true' : '')} />
          Accepting mentees
        </label>
      </div>

      {directory.isPending ? <Loading /> : directory.isError ? <ErrorAlert error={directory.error} /> : directory.data.results.length === 0 ? (
        <EmptyState title="No mentors match" description={activeFilters || filters.search ? 'Try removing a filter or searching for a broader skill.' : 'IIC has not published any mentor profiles yet.'}
          action={(activeFilters > 0 || !!filters.search) && <button className="btn btn-sm" onClick={() => setFilters(EMPTY)}><X size={14} />Clear filters</button>} />
      ) : (
        <>
          <p className="text-base-content/60 mb-3 text-sm">{directory.data.count} {directory.data.count === 1 ? 'mentor' : 'mentors'}</p>
          <ul className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {directory.data.results.map((m) => (
              <li key={m.id}>
                <button onClick={() => setViewing(m)} className="panel hover:border-primary/50 flex h-full w-full flex-col gap-3 p-5 text-left transition-colors">
                  <div className="flex items-start gap-3">
                    <MentorAvatar m={m} />
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-1.5"><span className="font-display truncate text-lg font-semibold">{m.name}</span><ShieldCheck size={16} className="text-primary shrink-0" aria-label="Verified" /></div>
                      <p className="text-base-content/70 text-sm">{m.current_role}{m.company && ` at ${m.company}`}</p>
                    </div>
                  </div>
                  <p className="text-sm"><span className="block font-semibold">{m.domain}</span><span className="text-base-content/60 block">{m.specialty}</span></p>
                  {m.skills.length > 0 && <div className="flex flex-wrap gap-1">{m.skills.slice(0, 4).map((s) => <span key={s} className="bg-base-200 rounded-full px-2.5 py-0.5 text-xs">{s}</span>)}{m.skills.length > 4 && <span className="text-base-content/50 px-1 text-xs">+{m.skills.length - 4}</span>}</div>}
                  <div className="mt-auto flex items-center justify-between pt-1 text-sm">
                    <span className="text-base-content/60">{m.experience_years} yrs experience</span>
                    <span className={`inline-flex items-center gap-1.5 font-medium ${m.availability.accepting_requests ? 'text-success' : 'text-base-content/50'}`}>
                      <span className={`size-2 rounded-full ${m.availability.accepting_requests ? 'bg-success' : 'bg-base-300'}`} />{m.availability.label}
                    </span>
                  </div>
                </button>
              </li>
            ))}
          </ul>
          <Pager page={page} count={directory.data.count} onChange={setPage} />
        </>
      )}

      <Modal open={showFilters} onClose={() => setShowFilters(false)} title="Filter mentors" size="sm"
        actions={<><button className="btn btn-ghost btn-sm" onClick={() => setFilters({ ...EMPTY, search: filters.search, available: filters.available })}>Reset</button>
          <button className="btn btn-primary btn-sm" onClick={() => setShowFilters(false)}>Show {directory.data?.count ?? ''} mentors</button></>}>
        {([['domain', 'Domain', facets.data?.domains], ['specialty', 'Specialty', facets.data?.specialties], ['career_path', 'Career pathway', facets.data?.career_paths]] as const).map(([key, label, options]) => (
          <label key={key} className="flex flex-col gap-1.5"><span className="text-sm font-medium">{label}</span>
            <select className="select w-full" value={filters[key]} onChange={(e) => set(key, e.target.value)}><option value="">Any</option>{options?.map((o) => <option key={o}>{o}</option>)}</select>
          </label>
        ))}
        <div className="flex flex-col gap-1.5"><span className="text-sm font-medium">Experience</span>
          <div className="flex flex-wrap gap-2">
            {[['', 'Any'], ['2', '2+ years'], ['5', '5+ years'], ['10', '10+ years']].map(([v, l]) => (
              <button key={l} type="button" onClick={() => set('min_experience', v)} className={`btn btn-sm rounded-full ${filters.min_experience === v ? 'btn-neutral' : 'btn-outline border-base-300'}`}>{l}</button>
            ))}
          </div>
        </div>
      </Modal>

      <MentorProfileModal mentor={viewing} blockedReason={blocked} onClose={() => setViewing(null)} onRequest={() => { setRequesting(viewing); setViewing(null) }} />
      <RequestFormModal open={!!requesting} mentor={requesting} onClose={() => setRequesting(null)} />
    </>
  )
}
