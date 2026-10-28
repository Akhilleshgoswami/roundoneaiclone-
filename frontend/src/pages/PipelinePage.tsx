import { useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import {
  api,
  type Application,
  type Candidate,
  type Interview,
  type Job,
} from '../api'
import { useOrg } from '../hooks/useOrg'

export default function PipelinePage() {
  const { org, error: orgError } = useOrg()
  const [jobs, setJobs] = useState<Job[]>([])
  const [candidates, setCandidates] = useState<Candidate[]>([])
  const [applications, setApplications] = useState<Application[]>([])
  const [interviews, setInterviews] = useState<Interview[]>([])
  const [jobId, setJobId] = useState('')
  const [candidateId, setCandidateId] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function refresh(organizationId: string) {
    const [j, c, a, i] = await Promise.all([
      api.listJobs(organizationId),
      api.listCandidates(organizationId),
      api.listApplications(),
      api.listInterviews(),
    ])
    setJobs(j)
    setCandidates(c)
    setApplications(a)
    setInterviews(i)
    if (!jobId && j[0]) setJobId(j[0].id)
    if (!candidateId && c[0]) setCandidateId(c[0].id)
  }

  useEffect(() => {
    if (!org) return
    refresh(org.id).catch((e: Error) => setError(e.message))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [org])

  async function onApply(e: FormEvent) {
    e.preventDefault()
    if (!jobId || !candidateId) return
    setBusy(true)
    setError(null)
    try {
      await api.createApplication({ job_id: jobId, candidate_id: candidateId })
      if (org) await refresh(org.id)
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  async function startInterview(applicationId: string) {
    setBusy(true)
    setError(null)
    try {
      const interview = await api.createInterview(applicationId)
      window.location.href = `/interview/${interview.id}`
    } catch (err) {
      setError((err as Error).message)
      setBusy(false)
    }
  }

  const jobName = (id: string) => jobs.find((j) => j.id === id)?.title ?? id.slice(0, 8)
  const candidateName = (id: string) =>
    candidates.find((c) => c.id === id)?.full_name ?? id.slice(0, 8)

  return (
    <div className="page">
      <header className="page-header">
        <h1>Pipeline</h1>
        <p>Match candidates to jobs, then launch a live AiVoice interview.</p>
      </header>

      <div className="grid two">
        <form className="surface stack" onSubmit={onApply}>
          <h2>Create application</h2>
          {(error || orgError) && <p className="error">{error || orgError}</p>}
          <label>
            Job
            <select value={jobId} onChange={(e) => setJobId(e.target.value)} required>
              <option value="">Select job</option>
              {jobs.map((j) => (
                <option key={j.id} value={j.id}>
                  {j.title}
                </option>
              ))}
            </select>
          </label>
          <label>
            Candidate
            <select
              value={candidateId}
              onChange={(e) => setCandidateId(e.target.value)}
              required
            >
              <option value="">Select candidate</option>
              {candidates.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.full_name}
                </option>
              ))}
            </select>
          </label>
          <div className="cta-row">
            <button className="btn" disabled={busy || !jobId || !candidateId}>
              {busy ? 'Working…' : 'Apply candidate'}
            </button>
          </div>
        </form>

        <section className="surface">
          <h2>Applications</h2>
          <div className="list">
            {applications.length === 0 && (
              <p className="empty">No applications yet — match a candidate to a job.</p>
            )}
            {applications.map((a) => {
              const existing = interviews.find((i) => i.application_id === a.id)
              return (
                <div className="list-item" key={a.id}>
                  <div>
                    <strong>
                      {candidateName(a.candidate_id)} → {jobName(a.job_id)}
                    </strong>
                    <div className="muted">Status: {a.status}</div>
                    {existing && (
                      <div className="muted">
                        Interview {existing.status}
                        {existing.overall_score != null
                          ? ` · score ${existing.overall_score}`
                          : ''}
                      </div>
                    )}
                  </div>
                  <div className="cta-row">
                    {existing ? (
                      <Link className="btn secondary" to={`/interview/${existing.id}`}>
                        Open
                      </Link>
                    ) : (
                      <button
                        type="button"
                        className="btn"
                        disabled={busy}
                        onClick={() => startInterview(a.id)}
                      >
                        Start interview
                      </button>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </section>
      </div>
    </div>
  )
}
