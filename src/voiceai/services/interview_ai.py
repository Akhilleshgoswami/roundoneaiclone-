"""Turn-based AI interviewer (OpenAI when keyed, scripted fallback otherwise)."""

from __future__ import annotations

import json
import re
from typing import Any

from voiceai.core.config import get_settings

FALLBACK_QUESTIONS = [
    "Thanks for joining. Please introduce yourself and walk me through your recent experience relevant to this role.",
    "Which of the required skills for this role are you strongest in, and can you share a concrete example?",
    "Tell me about a challenging project you owned end-to-end. What was your approach and the outcome?",
    "How do you handle unclear requirements or conflicting priorities with stakeholders?",
    "What questions do you have about the role or team, and why are you interested in this opportunity?",
]


def _skill_list(required_skills: str) -> list[str]:
    parts = re.split(r"[,;\n|/]+", required_skills or "")
    skills = [p.strip() for p in parts if p.strip()]
    return skills[:8] or ["general problem solving", "communication"]


async def next_question(
    *,
    job_title: str,
    job_description: str,
    required_skills: str,
    candidate_name: str,
    transcript: list[dict[str, Any]],
) -> tuple[str | None, bool]:
    """Return (prompt, done). done=True means interview should end after this."""

    user_turns = sum(1 for t in transcript if t.get("role") == "user")
    settings = get_settings()

    if not settings.openai_api_key:
        if user_turns >= len(FALLBACK_QUESTIONS):
            return None, True
        q = FALLBACK_QUESTIONS[user_turns]
        if user_turns == 0:
            q = f"Hi {candidate_name} — welcome to the {job_title} interview. {q}"
        done = user_turns + 1 >= len(FALLBACK_QUESTIONS)
        return q, done

    try:
        from openai import AsyncOpenAI
    except ImportError:
        # langchain-openai is installed; use OpenAI client from openai package if present
        return await _fallback_only(candidate_name, job_title, user_turns)

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    skills = ", ".join(_skill_list(required_skills))
    history = "\n".join(
        f"{t.get('role', 'user').upper()}: {t.get('content', '')}" for t in transcript[-12:]
    )
    system = (
        "You are a fair, concise AI hiring interviewer. Ask one question at a time. "
        "Do not invent candidate facts. Stay professional. "
        "After 4–5 strong exchanges, end the interview."
    )
    user = f"""
Role: {job_title}
Skills to probe: {skills}
Job description (abridged): {job_description[:1200]}
Candidate: {candidate_name}
User answers so far: {user_turns}

Transcript:
{history or "(interview just starting)"}

Respond with JSON only:
{{"done": false, "question": "..."}}
If the interview should end, set done=true and put a brief closing message in question.
""".strip()

    response = await client.chat.completions.create(
        model=settings.openai_model,
        temperature=0.4,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    raw = response.choices[0].message.content or "{}"
    data = json.loads(raw)
    question = (data.get("question") or "").strip()
    done = bool(data.get("done"))
    if not question and not done:
        return await _fallback_only(candidate_name, job_title, user_turns)
    return question or None, done


async def score_interview(
    *,
    job_title: str,
    required_skills: str,
    transcript: list[dict[str, Any]],
) -> tuple[float, dict[str, Any], str]:
    settings = get_settings()
    skills = _skill_list(required_skills)

    if not settings.openai_api_key:
        answers = [t["content"] for t in transcript if t.get("role") == "user"]
        avg_len = sum(len(a) for a in answers) / max(len(answers), 1)
        score = min(92.0, 45.0 + avg_len / 12.0)
        skill_scores = {s: round(min(95.0, score + (i % 3) * 2), 1) for i, s in enumerate(skills)}
        summary = (
            f"Demo scoring for {job_title}: candidate provided {len(answers)} answers. "
            "Set OPENAI_API_KEY for LLM-backed evaluation."
        )
        return round(score, 1), skill_scores, summary

    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    history = "\n".join(
        f"{t.get('role', 'user').upper()}: {t.get('content', '')}" for t in transcript
    )
    prompt = f"""
Score this interview for role "{job_title}".
Skills: {", ".join(skills)}

Transcript:
{history}

Return JSON:
{{
  "overall_score": 0-100 number,
  "skill_scores": {{"skill": 0-100}},
  "summary": "2-4 sentence evidence-based summary"
}}
""".strip()
    response = await client.chat.completions.create(
        model=settings.openai_model,
        temperature=0.2,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": "You are an evidence-only interview evaluator. Never invent facts.",
            },
            {"role": "user", "content": prompt},
        ],
    )
    data = json.loads(response.choices[0].message.content or "{}")
    overall = float(data.get("overall_score") or 0)
    skill_scores = data.get("skill_scores") or {}
    summary = data.get("summary") or "Interview completed."
    return overall, skill_scores, summary


async def _fallback_only(
    candidate_name: str,
    job_title: str,
    user_turns: int,
) -> tuple[str | None, bool]:
    if user_turns >= len(FALLBACK_QUESTIONS):
        return None, True
    q = FALLBACK_QUESTIONS[user_turns]
    if user_turns == 0:
        q = f"Hi {candidate_name} — welcome to the {job_title} interview. {q}"
    return q, user_turns + 1 >= len(FALLBACK_QUESTIONS)
