import { useEffect, useState, type FormEvent } from 'react'
import { api, type Job } from '../api'
import { useOrg } from '../hooks/useOrg'

export default function JobsPage() {
  const { org, error: orgError } = useOrg()
  const [jobs, setJobs] = useState<Job[]>([])
  const [error, setError] = useState<string | null>(null)
  const [title, setTitle] = useState('Frontend Engineer')
  const [skills, setSkills] = useState('React, TypeScript, System Design')
  const [description, setDescription] = useState(
    'Build recruiter-facing product surfaces. Own interview loops, performance, and accessibility.',
  )
  const [busy, setBusy] = useState(false)

  async function refresh(organizationId: string) {
    const data = await api.listJobs(organizationId)
    setJobs(data)
  }

  useEffect(() => {
    if (!org) return
    refresh(org.id).catch((e: Error) => setError(e.message))
  }, [org])

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    if (!org) return
    setBusy(true)
    setError(null)
    try {
      await api.createJob({
        organization_id: org.id,
        title,
        description,
        required_skills: skills,
        status: 'published',
      })
      await refresh(org.id)
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="page">
      <header className="page-header">
        <h1>Jobs</h1>
        <p>Define the role once. Every interview probes the same skill bar.</p>
      </header>

      <div className="grid two">
        <form className="surface stack" onSubmit={onSubmit}>
          <h2>Create job</h2>
          {(error || orgError) && <p className="error">{error || orgError}</p>}
          <label>
            Title
            <input value={title} onChange={(e) => setTitle(e.target.value)} required />
          </label>
          <label>
            Required skills
            <input value={skills} onChange={(e) => setSkills(e.target.value)} />
          </label>
          <label>
            Description
            <textarea value={description} onChange={(e) => setDescription(e.target.value)} required />
          </label>
          <div className="cta-row">
            <button className="btn" disabled={busy || !org}>
              {busy ? 'Saving…' : 'Publish job'}
            </button>
          </div>
        </form>

        <section className="surface">
          <h2>Open roles</h2>
          <div className="list">
            {jobs.length === 0 && <p className="empty">No jobs yet — publish one to get started.</p>}
            {jobs.map((job) => (
              <div className="list-item" key={job.id}>
                <div>
                  <strong>{job.title}</strong>
                  <div className="muted">{job.required_skills || 'No skills listed'}</div>
                </div>
                <span className="badge ok">{job.status}</span>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  )
}
