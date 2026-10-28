import { NavLink, Route, Routes } from 'react-router-dom'
import CandidatesPage from './pages/CandidatesPage'
import HomePage from './pages/HomePage'
import InterviewPage from './pages/InterviewPage'
import JobsPage from './pages/JobsPage'
import PipelinePage from './pages/PipelinePage'

export default function App() {
  return (
    <div className="app-shell">
      <header className="topbar">
        <NavLink to="/" className="brand" end>
          <span className="brand-mark">AiVoice</span>
          <span className="brand-sub">Hiring interviews</span>
        </NavLink>
        <nav className="nav">
          <NavLink to="/" end>
            Home
          </NavLink>
          <NavLink to="/jobs">Jobs</NavLink>
          <NavLink to="/candidates">Candidates</NavLink>
          <NavLink to="/pipeline">Pipeline</NavLink>
        </nav>
      </header>

      <main>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/jobs" element={<JobsPage />} />
          <Route path="/candidates" element={<CandidatesPage />} />
          <Route path="/pipeline" element={<PipelinePage />} />
          <Route path="/interview/:id" element={<InterviewPage />} />
        </Routes>
      </main>
    </div>
  )
}
