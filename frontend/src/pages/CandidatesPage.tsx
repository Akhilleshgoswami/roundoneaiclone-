import { useEffect, useState, type FormEvent } from 'react'
import { api, type Candidate } from '../api'
import { useOrg } from '../hooks/useOrg'

export default function CandidatesPage() {
  const { org, error: orgError } = useOrg()
  const [candidates, setCandidates] = useState<Candidate[]>([])
  const [error, setError] = useState<string | null>(null)
  const [fullName, setFullName] = useState('Avery Chen')
  const [email, setEmail] = useState('avery@example.com')
  const [resumeText, setResumeText] = useState(
    '5 years React/TypeScript. Led design systems and hiring loops. Strong communication.',
  )
  const [busy, setBusy] = useState(false)

  async function refresh(organizationId: string) {
    setCandidates(await api.listCandidates(organizationId))
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
      await api.createCandidate({
        organization_id: org.id,
        full_name: fullName,
        email,
        resume_text: resumeText,
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
        <h1>Candidates</h1>
        <p>Add people once, then route them into interviews from the pipeline.</p>
      </header>

      <div className="grid two">
        <form className="surface stack" onSubmit={onSubmit}>
          <h2>Add candidate</h2>
          {(error || orgError) && <p className="error">{error || orgError}</p>}
          <label>
            Full name
            <input value={fullName} onChange={(e) => setFullName(e.target.value)} required />
          </label>
          <label>
            Email
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </label>
          <label>
            Resume notes
            <textarea value={resumeText} onChange={(e) => setResumeText(e.target.value)} />
          </label>
          <div className="cta-row">
            <button className="btn" disabled={busy || !org}>
              {busy ? 'Saving…' : 'Save candidate'}
            </button>
          </div>
        </form>

        <section className="surface">
          <h2>People</h2>
          <div className="list">
            {candidates.length === 0 && (
              <p className="empty">No candidates yet — add someone to interview.</p>
            )}
            {candidates.map((c) => (
              <div className="list-item" key={c.id}>
                <div>
                  <strong>{c.full_name}</strong>
                  <div className="muted">{c.email}</div>
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  )
}
