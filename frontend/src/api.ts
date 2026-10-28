// Hit the API directly so the UI keeps working even if the Vite proxy is down.
const API_BASE = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
    ...init,
  })
  if (!res.ok) {
    const detail = await res.text()
    throw new Error(detail || `Request failed (${res.status})`)
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

export type Organization = {
  id: string
  name: string
  slug: string
  created_at: string
  updated_at: string
}

export type Job = {
  id: string
  organization_id: string
  title: string
  description: string
  required_skills: string
  status: string
  created_at: string
  updated_at: string
}

export type Candidate = {
  id: string
  organization_id: string
  full_name: string
  email: string
  resume_filename: string | null
  resume_text: string | null
  created_at: string
  updated_at: string
}

export type Application = {
  id: string
  job_id: string
  candidate_id: string
  status: string
  created_at: string
  updated_at: string
}

export type Interview = {
  id: string
  application_id: string
  status: string
  scheduled_at: string | null
  started_at: string | null
  completed_at: string | null
  transcript: { role: string; content: string; at?: string; speaker?: string }[]
  question_plan?: string[] | null
  evaluation?: Record<string, unknown> | null
  overall_score: number | null
  skill_scores: Record<string, number> | null
  summary: string | null
  created_at: string
  updated_at: string
}

export type InterviewStart = {
  interview_id: string
  status: string
  opening_question: string
  question_plan: string[]
  voice_available: boolean
}

export type VoiceSession = {
  interview_id: string
  status: string
  client_secret: string
  expires_at: number | null
  model: string
  voice: string
  realtime_url: string
  opening_question: string | null
  instructions_preview: string | null
}

export type InterviewEvaluation = {
  interview_id: string
  status: string
  evaluation: {
    overall_score: number | null
    criteria: { name: string; score: number | null; evidence: string; assessment: string }[]
    strengths: string[]
    weaknesses: string[]
    recommendations: string[]
    summary: string
    insufficient_evidence: boolean
  } | null
  overall_score: number | null
  skill_scores: Record<string, number> | null
  summary: string | null
}

export const api = {
  health: () => request<{ status: string }>('/health'),
  ensureDemoOrg: () => request<Organization>('/api/v1/organizations/demo', { method: 'POST' }),
  listOrgs: () => request<Organization[]>('/api/v1/organizations'),
  listJobs: (organizationId?: string) =>
    request<Job[]>(
      organizationId
        ? `/api/v1/jobs?organization_id=${organizationId}`
        : '/api/v1/jobs',
    ),
  createJob: (body: {
    organization_id: string
    title: string
    description: string
    required_skills?: string
    status?: string
  }) => request<Job>('/api/v1/jobs', { method: 'POST', body: JSON.stringify(body) }),
  listCandidates: (organizationId?: string) =>
    request<Candidate[]>(
      organizationId
        ? `/api/v1/candidates?organization_id=${organizationId}`
        : '/api/v1/candidates',
    ),
  createCandidate: (body: {
    organization_id: string
    full_name: string
    email: string
    resume_text?: string
  }) =>
    request<Candidate>('/api/v1/candidates', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  listApplications: () => request<Application[]>('/api/v1/applications'),
  createApplication: (body: { job_id: string; candidate_id: string }) =>
    request<Application>('/api/v1/applications', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  createInterview: (application_id: string) =>
    request<Interview>('/api/v1/interviews', {
      method: 'POST',
      body: JSON.stringify({ application_id }),
    }),
  getInterview: (id: string) => request<Interview>(`/api/v1/interviews/${id}`),
  listInterviews: () => request<Interview[]>('/api/v1/interviews'),
  startInterview: (id: string) =>
    request<InterviewStart>(`/api/v1/interviews/${id}/start`, { method: 'POST' }),
  createVoiceSession: (id: string) =>
    request<VoiceSession>(`/api/v1/interviews/${id}/voice-session`, { method: 'POST' }),
  getSession: (id: string) => request(`/api/v1/interviews/${id}/session`),
  appendTranscriptEvent: (
    id: string,
    body: { speaker: 'interviewer' | 'candidate'; content: string; provider_event_id?: string },
  ) =>
    request(`/api/v1/interviews/${id}/transcript-events`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  getTranscript: (id: string) => request(`/api/v1/interviews/${id}/transcript`),
  endInterview: (id: string) =>
    request<InterviewEvaluation>(`/api/v1/interviews/${id}/end`, { method: 'POST' }),
  getEvaluation: (id: string) =>
    request<InterviewEvaluation>(`/api/v1/interviews/${id}/evaluation`),
}
