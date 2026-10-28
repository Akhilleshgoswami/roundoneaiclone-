import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'

export default function HomePage() {
  const [healthy, setHealthy] = useState<boolean | null>(null)

  useEffect(() => {
    api
      .health()
      .then(() => setHealthy(true))
      .catch(() => setHealthy(false))
  }, [])

  return (
    <div className="page">
      <section className="home-hero">
        <div className="brand-mark">AiVoice</div>
        <h1>Realtime voice interviews that score themselves.</h1>
        <p>
          Publish a role, add a candidate, and run a live WebRTC interview —
          transcripts and skill scores land when the call ends.
        </p>
        <div className="cta-row">
          <Link className="btn" to="/jobs">
            Create a job
          </Link>
          <Link className="btn secondary" to="/pipeline">
            Open pipeline
          </Link>
        </div>
        <div className="home-meta">
          <span>
            <span className={`status-dot ${healthy ? 'ok' : ''}`} />{' '}
            API {healthy == null ? 'checking…' : healthy ? 'online' : 'offline'}
          </span>
          <span>
            Typical flow: <strong>Jobs → Candidates → Pipeline → Interview</strong>
          </span>
        </div>
      </section>

      <section className="surface section-gap">
        <h2>How it works</h2>
        <ol className="flow-steps">
          <li>Define the role and the skills you want probed.</li>
          <li>Add candidates with resume notes for context.</li>
          <li>Match them in Pipeline and start a live AiVoice session.</li>
        </ol>
      </section>
    </div>
  )
}
