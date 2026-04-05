import os
import logging
import asyncio
import json
import re
from typing import List, Optional, Dict, Any
from collections import defaultdict

from dotenv import load_dotenv
from fastapi import FastAPI, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from pydantic import BaseModel, Field
from groq import AsyncGroq
import langdetect
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
#dft shwit hagat shar7ha fe file alzatona.txt 
# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("among-ai")

# ── Environment ──────────────────────────────────────────────────────────────
load_dotenv()

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY is not set. Add it to your .env file.")

SYNTHESIS_MODEL = os.environ.get("SYNTHESIS_MODEL", "llama-3.1-8b-instant")
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "*").split(",")

# ── App Setup ────────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="Among-AI Backend", version="3.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = AsyncGroq(api_key=GROQ_API_KEY)

# ── Global In-Memory Leaderboard ─────────────────────────────────────────────
leaderboard_wins: Dict[str, int] = {}
leaderboard_debates: Dict[str, int] = {}

# ── Models ───────────────────────────────────────────────────────────────────
MODELS = [
    {
        "id": "llama-3.3-70b-versatile",
        "name": "LLAMA 70B",
        "role": "The Brain",
        "color": "#FF4655",
        "dark": "#7A1520",
        "glow": "rgba(255,70,85,0.25)",
    },
    {
        "id": "llama-3.1-8b-instant",
        "name": "LLAMA 8B",
        "role": "The Quick",
        "color": "#26D07C",
        "dark": "#0C6035",
        "glow": "rgba(38,208,124,0.25)",
    },
    {
        "id": "meta-llama/llama-4-scout-17b-16e-instruct",
        "name": "LLAMA 4",
        "role": "The Scout",
        "color": "#2E86DE",
        "dark": "#134070",
        "glow": "rgba(46,134,222,0.25)",
    },
    {
        "id": "qwen/qwen3-32b",
        "name": "QWEN 32B",
        "role": "The Sage",
        "color": "#00D4FF",
        "dark": "#005A6B",
        "glow": "rgba(0,212,255,0.25)",
    },
    {
        "id": "openai/gpt-oss-120b",
        "name": "GPT-OSS 120",
        "role": "The Titan",
        "color": "#FFCB2F",
        "dark": "#7A5800",
        "glow": "rgba(255,203,47,0.25)",
    },
    {
        "id": "openai/gpt-oss-20b",
        "name": "GPT-OSS 20",
        "role": "The Nimble",
        "color": "#FF8C42",
        "dark": "#7A3A00",
        "glow": "rgba(255,140,66,0.25)",
    },
]

# Init leaderboard counters
for m in MODELS:
    leaderboard_wins[m["name"]] = 0
    leaderboard_debates[m["name"]] = 0


# ── Pydantic Models ──────────────────────────────────────────────────────────
class HistoryItem(BaseModel):
    question: str
    answer: str


class ChatRequest(BaseModel):
    question: str
    rounds: int = Field(default=2, ge=1, le=3)
    debate_mode: bool = False
    active_models: List[int] = []          # empty list = all models
    history: List[HistoryItem] = []        # conversation memory


class VoteRequest(BaseModel):
    model_name: str


class ModelInfo(BaseModel):
    id: str
    name: str
    role: str
    color: str
    dark: str
    glow: str


# ── Language Detection ────────────────────────────────────────────────────────
LANG_MAP = {
    "ar": "Arabic", "en": "English", "es": "Spanish", "fr": "French",
    "de": "German", "it": "Italian", "pt": "Portuguese", "ru": "Russian",
    "zh": "Chinese", "ja": "Japanese", "ko": "Korean", "hi": "Hindi",
    "tr": "Turkish", "pl": "Polish", "nl": "Dutch", "sv": "Swedish",
    "da": "Danish", "no": "Norwegian", "fi": "Finnish", "cs": "Czech",
    "hu": "Hungarian", "el": "Greek", "he": "Hebrew", "th": "Thai",
    "vi": "Vietnamese", "id": "Indonesian", "ms": "Malay", "uk": "Ukrainian",
    "ro": "Romanian", "bg": "Bulgarian", "hr": "Croatian", "sk": "Slovak",
    "fa": "Persian", "ur": "Urdu", "bn": "Bengali", "ta": "Tamil",
    "sw": "Swahili", "af": "Afrikaans", "hy": "Armenian", "ka": "Georgian",
    "az": "Azerbaijani", "kk": "Kazakh", "uz": "Uzbek", "ne": "Nepali",
}


def detect_language(text: str) -> str:
    if len(text.strip()) < 10: 
        return "English"  # da 3shan al klam al so8er zy HI 
    try:
        lang = langdetect.detect(text)
        return LANG_MAP.get(lang, lang)
    except Exception:
        return "English"


def truncate_text(text: str, max_chars: int = 300) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(" ", 1)[0] + "..."


# ── Build System Prompt ───────────────────────────────────────────────────────
def build_system_prompt(
    language: str,
    history: List[HistoryItem],
    seeing_responses: Optional[List[dict]] = None,
    debate_side: Optional[str] = None,
    round_num: int = 1,
) -> str:
    prompt = (
        f"You are a helpful AI assistant. You MUST respond in {language} only.\n"
        f"Keep your response concise (2-3 paragraphs max)."
    )

    # Conversation memory
    if history:
        history_text = "\n".join(
            f"Q: {h.question}\nA: {truncate_text(h.answer, 200)}" for h in history[-3:]
        )
        prompt += f"\n\nPrevious conversation context:\n{history_text}\n"

    # Debate mode sides
    if debate_side:
        prompt += (
            f"\n\nYou are arguing the {debate_side} side of this topic. "
            f"Present strong {debate_side.upper()} arguments. Be persuasive."
        )

    # Round 2+ — see what others said
    if seeing_responses:
        others_text = "\n".join(
            f"{r['model_name']}: {truncate_text(r['response'], 200)}"
            for r in seeing_responses
        )
        if debate_side:
            prompt += (
                f"\n\nOpposing arguments you must counter:\n{others_text}\n"
                f"Defend your {debate_side} position firmly."
            )
        else:
            prompt += (
                f"\n\nYour crewmates said:\n{others_text}\n"
                f"Build on their ideas, add new insights, and improve the answer."
            )

    # Round 3 — final synthesis push
    if round_num == 3:
        prompt += "\n\nThis is your FINAL statement. Be definitive and conclusive."

    return prompt


# ── Single Model Call ─────────────────────────────────────────────────────────
async def ask_model(
    model_id: str,
    question: str,
    language: str,
    history: List[HistoryItem],
    seeing_responses: Optional[List[dict]] = None,
    debate_side: Optional[str] = None,
    round_num: int = 1,
) -> tuple:
    system_prompt = build_system_prompt(language, history, seeing_responses, debate_side, round_num)
    what_they_saw = ""

    if seeing_responses:
        what_they_saw = "\n".join(
            f"{r['model_name']}: {truncate_text(r['response'], 200)}"
            for r in seeing_responses
        )

    r = await client.chat.completions.create(
        model=model_id,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ],
        max_tokens=450,
        temperature=0.75,
    )
    return r.choices[0].message.content.strip(), what_they_saw


async def ask_model_safe(
    model_id: str,
    question: str,
    language: str,
    history: List[HistoryItem],
    seeing_responses: Optional[List[dict]] = None,
    debate_side: Optional[str] = None,
    round_num: int = 1,
    timeout: float = 35.0,
) -> tuple:
    try:
        return await asyncio.wait_for(
            ask_model(model_id, question, language, history, seeing_responses, debate_side, round_num),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        logger.warning("Model %s timed out", model_id)
        return f"[Timed out after {timeout:.0f}s]", ""
    except Exception as e:
        logger.error("Model %s failed: %s", model_id, e)
        return f"[Error: {e}]", ""


# ── Synthesis ─────────────────────────────────────────────────────────────────
async def synthesize_debate(
    question: str,
    language: str,
    debate_log: List[dict],
    debate_mode: bool,
    active_model_names: List[str],
) -> dict:
    summary_parts = []
    for rd in debate_log:
        summary_parts.append(f"\n{rd['title']}:")
        for r in rd["responses"]:
            summary_parts.append(f"  {r['model_name']}: {truncate_text(r['response'], 150)}")
    debate_summary_text = "\n".join(summary_parts)

    if debate_mode:
        extra = (
            "This was a FOR vs AGAINST debate. "
            "Synthesize a balanced final answer acknowledging both sides."
        )
    else:
        extra = "Synthesize the BEST combined answer using insights from all participants."

    prompt = (
        f'Question: "{question}"\n'
        f"Language: {language}\n"
        f"Active participants: {', '.join(active_model_names)}\n\n"
        f"Debate:\n{debate_summary_text}\n\n"
        f"{extra}\n\n"
        f"Return ONLY valid JSON (no markdown, no backticks):\n"
        f'{{"final_answer": "comprehensive answer in {language}", '
        f'"top_contributors": ["Name1", "Name2"], '
        f'"debate_summary": "brief 1-2 sentence analysis in {language}"}}'
    )

    result = await client.chat.completions.create(
        model=SYNTHESIS_MODEL,
        messages=[
            {"role": "system", "content": f"You synthesize debates. Output ONLY valid JSON in {language}."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=700,
        temperature=0.25,
    )

    text = result.choices[0].message.content.strip()
    # Strip markdown code fences if present
    text = re.sub(r"```(?:json)?", "", text).strip().strip("`")
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        try:
            return json.loads(m.group())
        except Exception:
            logger.warning("Synthesis JSON parse failed, using fallback")

    fallback_map = {
        "Arabic": "اكتملت المناظرة",
        "English": "Debate synthesis completed",
        "French": "Synthèse terminée",
        "Spanish": "Síntesis completada",
    }
    best_response = debate_log[-1]["responses"][0]["response"]
    return {
        "final_answer": best_response,
        "top_contributors": [active_model_names[0]] if active_model_names else [],
        "debate_summary": fallback_map.get(language, "Debate completed"),
    }


# ── Helper: tagged coroutine ──────────────────────────────────────────────────
async def tagged_call(idx: int, coro):
    result = await coro
    return idx, result


# ── API Endpoints ─────────────────────────────────────────────────────────────
@app.get("/")
async def serve_frontend():
    return FileResponse("index.html")


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "models": len(MODELS),
        "synthesis_model": SYNTHESIS_MODEL,
        "version": "3.0.0",
    }


@app.get("/models", response_model=List[ModelInfo])
async def get_models():
    return MODELS


@app.get("/leaderboard")
async def get_leaderboard():
    board = []
    for m in MODELS:
        board.append({
            "name": m["name"],
            "role": m["role"],
            "color": m["color"],
            "dark": m["dark"],
            "wins": leaderboard_wins.get(m["name"], 0),
            "debates": leaderboard_debates.get(m["name"], 0),
        })
    board.sort(key=lambda x: x["wins"], reverse=True)
    return board


@app.post("/vote")
async def submit_vote(req: VoteRequest):
    if req.model_name in leaderboard_wins:
        leaderboard_wins[req.model_name] += 1
        logger.info("Vote recorded for %s", req.model_name)
    board = await get_leaderboard()
    return {"leaderboard": board}


@app.post("/chat")
@limiter.limit("12/minute")
async def chat_stream(request: Request, req: ChatRequest):
    """SSE streaming endpoint with rounds, debate mode, model selection, and memory."""

    detected_language = detect_language(req.question)
    logger.info(
        "Chat — lang=%s rounds=%d debate=%s active=%s q=%s",
        detected_language, req.rounds, req.debate_mode,
        req.active_models, req.question[:80],
    )

    # Resolve active models (empty = all)
    if req.active_models:
        active = [MODELS[i] for i in req.active_models if 0 <= i < len(MODELS)]
    else:
        active = list(MODELS)

    if not active:
        active = list(MODELS)

    # Debate mode sides assignment
    debate_sides: Dict[str, str] = {}
    if req.debate_mode and len(active) >= 2:
        half = len(active) // 2
        for i, m in enumerate(active):
            debate_sides[m["name"]] = "FOR" if i < half else "AGAINST"

    # Track debates for leaderboard
    for m in active:
        leaderboard_debates[m["name"]] = leaderboard_debates.get(m["name"], 0) + 1

    async def event_generator():
        debate_log: List[dict] = []
        current_responses: List[dict] = []

        def sse(data: dict) -> str:
            return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

        # ── Rounds Loop ───────────────────────────────────────────────────
        for rnd in range(1, req.rounds + 1):
            round_titles = {
                1: "🎤 Opening Statements",
                2: "💬 Debate Round",
                3: "🏁 Final Arguments",
            }
            title = round_titles.get(rnd, f"Round {rnd}")

            yield sse({
                "type": "round_start",
                "round": rnd,
                "title": title,
                "total_models": len(active),
            })

            # Reset crew slots for subsequent rounds
            if rnd > 1:
                yield sse({"type": "reset_slots", "round": rnd})

            seeing = current_responses if rnd > 1 else None
            round_responses: List[dict] = []

            tasks = [
                asyncio.create_task(
                    tagged_call(
                        i,
                        ask_model_safe(
                            m["id"],
                            req.question,
                            detected_language,
                            req.history,
                            seeing_responses=[
                                r for r in (seeing or [])
                                if r["model_name"] != m["name"]
                            ] if seeing else None,
                            debate_side=debate_sides.get(m["name"]),
                            round_num=rnd,
                        ),
                    )
                )
                for i, m in enumerate(active)
            ]

            for coro in asyncio.as_completed(tasks):
                i, (resp, saw) = await coro
                m = active[i]
                entry = {
                    "model_idx": i,
                    "model_name": m["name"],
                    "role": m["role"],
                    "color": m["color"],
                    "response": resp,
                    "responding_to": saw if saw else None,
                    "debate_side": debate_sides.get(m["name"]),
                }
                round_responses.append(entry)
                yield sse({"type": "model_response", "round": rnd, **entry})

            round_responses.sort(key=lambda r: r["model_idx"])
            debate_log.append({"round": rnd, "title": title, "responses": round_responses})
            current_responses = round_responses

        # ── Synthesis ─────────────────────────────────────────────────────
        yield sse({"type": "synthesizing"})

        try:
            final = await synthesize_debate(
                req.question,
                detected_language,
                debate_log,
                req.debate_mode,
                [m["name"] for m in active],
            )
        except Exception as e:
            logger.error("Synthesis error: %s", e)
            best = ""
            for rd in reversed(debate_log):
                for r in rd["responses"]:
                    if not r["response"].startswith("["):
                        best = r["response"]
                        break
                if best:
                    break
            final = {
                "final_answer": best or str(e),
                "top_contributors": [],
                "debate_summary": f"Synthesis failed: {e}",
            }

        top = final.get("top_contributors", [])
        scores = [
            min(98, 65 + (30 if m["name"] in top else 0) + (5 if m["name"] in debate_sides else 0))
            for m in active
        ]
        winner_idx = 0
        for i, m in enumerate(active):
            if m["name"] in top:
                winner_idx = i
                break

        # Update leaderboard for top contributors
        for name in top:
            if name in leaderboard_wins:
                leaderboard_wins[name] += 1

        yield sse({
            "type": "done",
            "question": req.question,
            "detected_language": detected_language,
            "debate_log": debate_log,
            "final_answer": final.get("final_answer", ""),
            "debate_summary": final.get("debate_summary", ""),
            "winner": winner_idx,
            "top_contributors": top,
            "scores": scores,
            "total_rounds": len(debate_log),
            "debate_mode": req.debate_mode,
            "debate_sides": debate_sides,
            "active_models": [m["name"] for m in active],
        })

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
