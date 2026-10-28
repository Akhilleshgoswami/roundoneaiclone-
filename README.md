# Voice AI / AiVoice

AI hiring interview platform: FastAPI backend (`voiceai`) + React frontend.

## Quick start

```bash
cd voiceai
uv sync
npm --prefix frontend install
./scripts/dev.sh
```

That starts Postgres + API + frontend. Open:

- App: http://127.0.0.1:5173
- API docs: http://127.0.0.1:8000/docs

Manual (if you prefer two terminals):

```bash
# API — must use voiceai.main:app (not main:app)
uv run uvicorn voiceai.main:app --host 127.0.0.1 --port 8000 --reload

# Frontend
npm --prefix frontend run dev -- --host 127.0.0.1 --port 5173
```

Migrations:

```bash
PYTHONPATH=src uv run alembic upgrade head
```

## Voice interviews

Set `OPENAI_API_KEY` in `.env` (Realtime-capable key). Optional:

- `OPENAI_REALTIME_MODEL` (default `gpt-realtime`)
- `OPENAI_REALTIME_VOICE` (default `marin`)
- `INTERVIEW_MAX_QUESTIONS` / `INTERVIEW_MAX_MINUTES`

### Live voice smoke test (manual)

1. Create org → job → candidate → application → interview via UI or API.
2. Open `/interview/{id}` in the frontend.
3. Click **Start voice interview** and allow microphone access.
4. Speak; confirm AI audio playback and transcript updates.
5. Click **End interview** and confirm evaluation/scorecard.

Automated tests mock OpenAI Realtime and do **not** verify live microphone audio.

## API surface

- `GET /health`
- `POST/GET /api/v1/organizations` (+ `POST /demo`)
- `POST/GET /api/v1/jobs`
- `POST/GET /api/v1/candidates`
- `POST/GET /api/v1/applications` (+ status patch)
- Interviews:
  - `POST/GET /api/v1/interviews`
  - `POST /api/v1/interviews/{id}/start`
  - `POST /api/v1/interviews/{id}/voice-session` (ephemeral Realtime credentials)
  - `GET /api/v1/interviews/{id}/session`
  - `POST /api/v1/interviews/{id}/transcript-events`
  - `GET /api/v1/interviews/{id}/transcript`
  - `POST /api/v1/interviews/{id}/end`
  - `GET /api/v1/interviews/{id}/evaluation`

## Security note

Permanent OpenAI API keys stay on the server. The browser receives only a short-lived Realtime client secret for WebRTC.
