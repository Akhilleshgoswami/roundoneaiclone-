import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  api,
  type Interview,
  type InterviewEvaluation,
  type VoiceSession,
} from '../api'

type ConnState = 'idle' | 'connecting' | 'live' | 'ended' | 'error'

export default function InterviewPage() {
  const { id = '' } = useParams()
  const [interview, setInterview] = useState<Interview | null>(null)
  const [evaluation, setEvaluation] = useState<InterviewEvaluation | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [conn, setConn] = useState<ConnState>('idle')
  const [muted, setMuted] = useState(false)
  const [aiSpeaking, setAiSpeaking] = useState(false)
  const [opening, setOpening] = useState<string | null>(null)

  const pcRef = useRef<RTCPeerConnection | null>(null)
  const micRef = useRef<MediaStream | null>(null)
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const dcRef = useRef<RTCDataChannel | null>(null)

  const skillEntries = useMemo(() => {
    const scores =
      evaluation?.skill_scores ??
      evaluation?.evaluation?.criteria?.reduce<Record<string, number>>((acc, c) => {
        if (c.score != null) acc[c.name] = c.score
        return acc
      }, {}) ??
      interview?.skill_scores ??
      {}
    return Object.entries(scores)
  }, [evaluation, interview])

  const cleanupVoice = useCallback(() => {
    dcRef.current?.close()
    dcRef.current = null
    pcRef.current?.getSenders().forEach((s) => s.track?.stop())
    pcRef.current?.close()
    pcRef.current = null
    micRef.current?.getTracks().forEach((t) => t.stop())
    micRef.current = null
  }, [])

  useEffect(() => () => cleanupVoice(), [cleanupVoice])

  useEffect(() => {
    if (!id) return
    let alive = true
    ;(async () => {
      try {
        const current = await api.getInterview(id)
        if (!alive) return
        setInterview(current)
        if (current.status === 'completed') {
          const ev = await api.getEvaluation(id)
          if (alive) {
            setEvaluation(ev)
            setConn('ended')
          }
        }
      } catch (err) {
        if (alive) setError((err as Error).message)
      }
    })()
    return () => {
      alive = false
    }
  }, [id])

  async function persistEvent(
    speaker: 'interviewer' | 'candidate',
    content: string,
    providerEventId?: string,
  ) {
    if (!id || !content.trim()) return
    try {
      await api.appendTranscriptEvent(id, {
        speaker,
        content: content.trim(),
        provider_event_id: providerEventId,
      })
      const refreshed = await api.getInterview(id)
      setInterview(refreshed)
    } catch {
      // Keep the live call going even if transcript persistence fails briefly.
    }
  }

  function handleRealtimeEvent(raw: string) {
    try {
      const event = JSON.parse(raw) as Record<string, unknown>
      const type = String(event.type ?? '')

      if (type === 'response.output_audio.delta' || type === 'output_audio.delta') {
        setAiSpeaking(true)
      }
      if (
        type === 'response.output_audio.done' ||
        type === 'response.done' ||
        type === 'output_audio.done'
      ) {
        setAiSpeaking(false)
      }

      if (
        type === 'conversation.item.input_audio_transcription.completed' ||
        type === 'conversation.item.input_audio_transcription.done'
      ) {
        const transcript = String(
          (event.transcript as string) ||
            ((event.item as { transcript?: string } | undefined)?.transcript ?? ''),
        )
        const eventId = String(event.event_id ?? event.item_id ?? crypto.randomUUID())
        void persistEvent('candidate', transcript, eventId)
      }

      if (
        type === 'response.output_audio_transcript.done' ||
        type === 'response.audio_transcript.done'
      ) {
        const transcript = String(event.transcript ?? '')
        const eventId = String(event.event_id ?? event.response_id ?? crypto.randomUUID())
        void persistEvent('interviewer', transcript, eventId)
      }

      if (type === 'error') {
        const message =
          ((event.error as { message?: string } | undefined)?.message) ||
          'Realtime voice error'
        setError(message)
      }
    } catch {
      // ignore non-JSON data-channel frames
    }
  }

  async function connectVoice() {
    if (!id) return
    setError(null)
    setConn('connecting')
    cleanupVoice()

    try {
      const started = await api.startInterview(id)
      setOpening(started.opening_question)

      let voice: VoiceSession
      try {
        voice = await api.createVoiceSession(id)
      } catch (err) {
        setConn('error')
        setError(
          `${(err as Error).message}\n\nVoice requires OPENAI_API_KEY with Realtime access. ` +
            'You can still use transcript/evaluation APIs after a text-assisted session.',
        )
        return
      }

      const pc = new RTCPeerConnection()
      pcRef.current = pc

      if (!audioRef.current) {
        audioRef.current = new Audio()
        audioRef.current.autoplay = true
      }
      pc.ontrack = (event) => {
        if (audioRef.current) {
          audioRef.current.srcObject = event.streams[0]
        }
      }

      const mic = await navigator.mediaDevices.getUserMedia({ audio: true })
      micRef.current = mic
      mic.getTracks().forEach((track) => pc.addTrack(track, mic))

      const dc = pc.createDataChannel('oai-events')
      dcRef.current = dc
      dc.onmessage = (msg) => handleRealtimeEvent(String(msg.data))

      const offer = await pc.createOffer()
      await pc.setLocalDescription(offer)

      await new Promise<void>((resolve) => {
        if (pc.iceGatheringState === 'complete') {
          resolve()
          return
        }
        const check = () => {
          if (pc.iceGatheringState === 'complete') {
            pc.removeEventListener('icegatheringstatechange', check)
            resolve()
          }
        }
        pc.addEventListener('icegatheringstatechange', check)
      })

      const sdp = pc.localDescription?.sdp
      if (!sdp) throw new Error('Failed to create local SDP offer')

      const sdpResponse = await fetch(voice.realtime_url, {
        method: 'POST',
        body: sdp,
        headers: {
          Authorization: `Bearer ${voice.client_secret}`,
          'Content-Type': 'application/sdp',
        },
      })
      if (!sdpResponse.ok) {
        const detail = await sdpResponse.text()
        throw new Error(`Realtime connect failed: ${detail || sdpResponse.status}`)
      }
      const answer = await sdpResponse.text()
      await pc.setRemoteDescription({ type: 'answer', sdp: answer })

      setConn('live')
      const refreshed = await api.getInterview(id)
      setInterview(refreshed)
    } catch (err) {
      cleanupVoice()
      setConn('error')
      setError((err as Error).message)
    }
  }

  async function endInterview() {
    if (!id) return
    setError(null)
    try {
      cleanupVoice()
      const result = await api.endInterview(id)
      setEvaluation(result)
      setInterview(await api.getInterview(id))
      setConn('ended')
    } catch (err) {
      setError((err as Error).message)
    }
  }

  function toggleMute() {
    const next = !muted
    setMuted(next)
    micRef.current?.getAudioTracks().forEach((t) => {
      t.enabled = !next
    })
  }

  const done = interview?.status === 'completed' || conn === 'ended'

  const orbClass =
    conn === 'live' ? (aiSpeaking ? 'voice-orb speaking' : 'voice-orb listening') : 'voice-orb'

  const statusLabel =
    conn === 'idle'
      ? 'Ready'
      : conn === 'connecting'
        ? 'Connecting'
        : conn === 'live'
          ? aiSpeaking
            ? 'AI speaking'
            : muted
              ? 'Muted'
              : 'Listening'
          : conn === 'ended'
            ? 'Ended'
            : 'Error'

  return (
    <div className="page">
      <header className="page-header">
        <h1>Interview room</h1>
        <p>
          Live WebRTC voice interview. The OpenAI key stays on the server — only a
          short-lived session secret reaches the browser.
        </p>
        <div className="cta-row">
          <Link className="btn secondary" to="/pipeline">
            Back to pipeline
          </Link>
        </div>
      </header>

      {error && <p className="error">{error}</p>}

      <div className="interview-layout">
        <section className="surface voice-panel">
          <h2>Live session</h2>
          <div className="voice-stage">
            <div className={orbClass} aria-hidden />
            <div className="voice-meta">
              <strong>{statusLabel}</strong>
              <span className="muted">Connection: {conn}</span>
            </div>
          </div>

          {opening && (
            <p className="scorecard-note">
              <strong>Opening: </strong>
              {opening}
            </p>
          )}

          {!done && (
            <div className="cta-row">
              {conn !== 'live' && (
                <button className="btn" onClick={() => void connectVoice()}>
                  {conn === 'connecting' ? 'Connecting…' : 'Start voice interview'}
                </button>
              )}
              {conn === 'live' && (
                <>
                  <button className="btn secondary" onClick={toggleMute}>
                    {muted ? 'Unmute' : 'Mute'}
                  </button>
                  <button className="btn" onClick={() => void endInterview()}>
                    End interview
                  </button>
                </>
              )}
            </div>
          )}

          <h3>Transcript</h3>
          {!interview && <p className="muted">Loading session…</p>}
          {interview && (
            <div className="chat">
              {(interview.transcript ?? []).map((turn, idx) => (
                <div
                  key={`${turn.at ?? idx}-${idx}`}
                  className={`bubble ${turn.role === 'assistant' || turn.speaker === 'interviewer' ? 'assistant' : 'user'}`}
                >
                  {turn.content}
                </div>
              ))}
              {interview.transcript?.length === 0 && (
                <p className="empty">Transcript turns appear as you speak.</p>
              )}
            </div>
          )}
        </section>

        <section className="surface stack">
          <h2>Scorecard</h2>
          {(evaluation?.overall_score ?? interview?.overall_score) != null ? (
            <>
              <p className="score">{evaluation?.overall_score ?? interview?.overall_score}</p>
              <p className="scorecard-note">{evaluation?.summary ?? interview?.summary}</p>
              {evaluation?.evaluation && (
                <>
                  <p className="scorecard-note">
                    {evaluation.evaluation.insufficient_evidence
                      ? 'Insufficient evidence flagged — treat as decision support only.'
                      : 'Evidence-based evaluation for human review (not an auto hire/reject).'}
                  </p>
                  <ul className="scorecard-list">
                    {(evaluation.evaluation.strengths ?? []).map((s) => (
                      <li key={s}>Strength: {s}</li>
                    ))}
                    {(evaluation.evaluation.weaknesses ?? []).map((s) => (
                      <li key={s}>Gap: {s}</li>
                    ))}
                  </ul>
                </>
              )}
              <div className="list">
                {skillEntries.map(([skill, score]) => (
                  <div className="list-item" key={skill}>
                    <strong>{skill}</strong>
                    <span className="badge ok">{score}</span>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <p className="empty">
              Scores appear after you end the session.
              {interview ? ` Status: ${interview.status}` : ''}
            </p>
          )}
          {done && (
            <button className="btn secondary" onClick={() => void endInterview()}>
              Refresh evaluation
            </button>
          )}
        </section>
      </div>
    </div>
  )
}
