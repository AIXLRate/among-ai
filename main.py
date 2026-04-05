import os
import logging
import asyncio
import json
import re
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from groq import AsyncGroq
import langdetect
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

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
app = FastAPI(title="Among-AI Backend", version="2.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = AsyncGroq(api_key=GROQ_API_KEY)

# ── Models ───────────────────────────────────────────────────────────────────
MODELS = [
    {"id": "llama-3.3-70b-versatile",           "name": "LLAMA 70B",     "role": "The Brain",   "color": "#FF4655", "dark": "#7A1520", "glow": "rgba(255,70,85,0.25)"},
    {"id": "llama-3.1-8b-instant",              "name": "LLAMA 8B",      "role": "The Quick",   "color": "#26D07C", "dark": "#0C6035", "glow": "rgba(38,208,124,0.25)"},
    {"id": "meta-llama/llama-4-scout-17b-16e-instruct", "name": "LLAMA 4 SCOUT", "role": "The Scout", "color": "#2E86DE", "dark": "#134070", "glow": "rgba(46,134,222,0.25)"},
    {"id": "qwen/qwen3-32b",                    "name": "QWEN 32B",      "role": "The Sage",    "color": "#00D4FF", "dark": "#005A6B", "glow": "rgba(0,212,255,0.25)"},
    {"id": "openai/gpt-oss-120b",               "name": "GPT-OSS 120",   "role": "The Titan",   "color": "#FFCB2F", "dark": "#7A5800", "glow": "rgba(255,203,47,0.25)"},
    {"id": "openai/gpt-oss-20b",                "name": "GPT-OSS 20",    "role": "The Nimble",  "color": "#FF8C42", "dark": "#7A3A00", "glow": "rgba(255,140,66,0.25)"},
]


# ── Pydantic Models ──────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    question: str

class ModelInfo(BaseModel):
    id: str
    name: str
    role: str
    color: str
    dark: str
    glow: str

class RoundResponse(BaseModel):
    model_idx: int
    model_name: str
    role: str
    color: str
    response: str
    responding_to: Optional[str] = None

class DebateRound(BaseModel):
    round: int
    title: str
    responses: List[RoundResponse]

class ChatResponse(BaseModel):
    question: str
    detected_language: str
    debate_log: List[DebateRound]
    final_answer: str
    debate_summary: str
    winner: int
    top_contributors: List[str]
    scores: List[int]
    total_rounds: int


# ── Utilities ────────────────────────────────────────────────────────────────
LANG_MAP = {
    'ar': 'Arabic', 'en': 'English', 'es': 'Spanish', 'fr': 'French',
    'de': 'German', 'it': 'Italian', 'pt': 'Portuguese', 'ru': 'Russian',
    'zh': 'Chinese', 'ja': 'Japanese', 'ko': 'Korean', 'hi': 'Hindi',
    'tr': 'Turkish', 'pl': 'Polish', 'nl': 'Dutch', 'sv': 'Swedish',
    'da': 'Danish', 'no': 'Norwegian', 'fi': 'Finnish', 'cs': 'Czech',
    'hu': 'Hungarian', 'el': 'Greek', 'he': 'Hebrew', 'th': 'Thai',
    'vi': 'Vietnamese', 'id': 'Indonesian', 'ms': 'Malay', 'uk': 'Ukrainian',
    'ro': 'Romanian', 'bg': 'Bulgarian', 'hr': 'Croatian', 'sk': 'Slovak',
    'sl': 'Slovenian', 'lt': 'Lithuanian', 'lv': 'Latvian', 'et': 'Estonian',
    'fa': 'Persian', 'ur': 'Urdu', 'bn': 'Bengali', 'ta': 'Tamil',
    'te': 'Telugu', 'mr': 'Marathi', 'kn': 'Kannada', 'gu': 'Gujarati',
    'pa': 'Punjabi', 'ml': 'Malayalam', 'sw': 'Swahili', 'af': 'Afrikaans',
    'sq': 'Albanian', 'hy': 'Armenian', 'ka': 'Georgian', 'az': 'Azerbaijani',
    'kk': 'Kazakh', 'uz': 'Uzbek', 'mn': 'Mongolian', 'ne': 'Nepali',
}


def detect_language(text: str) -> str:
    """Detect the language of the input text."""
    try:
        lang = langdetect.detect(text)
        return LANG_MAP.get(lang, lang)
    except Exception:
        return "English"


def truncate_text(text: str, max_chars: int = 300) -> str:
    """Truncate text to stay within token limits."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(' ', 1)[0] + "..."


# ── Model Calls ──────────────────────────────────────────────────────────────
async def ask_model(
    model_id: str,
    question: str,
    language: str,
    context: str = "",
    seeing_responses: Optional[List[dict]] = None,
) -> tuple:
    """Ask a single model with optional context from other models."""
    what_they_saw = ""

    system_prompt = (
        f"You are a helpful AI assistant. You MUST respond in {language} only.\n"
        f"The user asked their question in {language}, so you must answer in the same language.\n"
        f"Respond naturally and fluently in {language}. Keep your response concise (2-3 paragraphs max)."
    )

    if seeing_responses:
        what_they_saw = "\n\n".join(
            f"{r['model_name']}: {truncate_text(r['response'], 200)}"
            for r in seeing_responses
        )
        system_prompt += (
            f"\n\nYou are in a group discussion. Crewmates said:\n{what_they_saw}\n\n"
            f"Respond in {language}, building on their ideas. Be concise."
        )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question},
    ]

    r = await client.chat.completions.create(
        model=model_id,
        messages=messages,
        max_tokens=400,
        temperature=0.7,
    )
    return r.choices[0].message.content.strip(), what_they_saw


async def ask_model_safe(
    model_id: str,
    question: str,
    language: str,
    context: str = "",
    seeing_responses: Optional[List[dict]] = None,
    timeout: float = 30.0,
) -> tuple:
    """Wrapper with timeout and error handling — never crashes the debate."""
    try:
        return await asyncio.wait_for(
            ask_model(model_id, question, language, context, seeing_responses),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        logger.warning("Model %s timed out after %.0fs", model_id, timeout)
        return f"[Timed out after {timeout:.0f}s]", ""
    except Exception as e:
        logger.error("Model %s failed: %s", model_id, e)
        return f"[Error: {e}]", ""


# ── Synthesis ────────────────────────────────────────────────────────────────
async def synthesize_debate(
    question: str, language: str, debate_log: List[dict]
) -> dict:
    """Create final answer with token-efficient summary."""
    debate_summary = ""
    for round_data in debate_log:
        debate_summary += f"\n{round_data['title']}:\n"
        for r in round_data["responses"]:
            truncated = truncate_text(r["response"], 150)
            debate_summary += f"- {r['model_name']}: {truncated}\n"

    prompt = (
        f'Question: "{question}"\n'
        f"Language: {language}\n\n"
        f"Debate summary:\n{debate_summary}\n\n"
        f"Synthesize into ONE excellent answer in {language}. Be comprehensive but concise.\n\n"
        f"Return JSON:\n"
        f'{{"final_answer": "your answer in {language}", '
        f'"top_contributors": ["Name1", "Name2"], '
        f'"debate_summary": "brief analysis in {language}"}}'
    )

    result = await client.chat.completions.create(
        model=SYNTHESIS_MODEL,
        messages=[
            {"role": "system", "content": f"You are a debate moderator. Output ONLY in {language}."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=600,
        temperature=0.3,
    )

    text = result.choices[0].message.content.strip()
    m = re.search(r'\{[\s\S]*?\}', text)
    if m:
        try:
            return json.loads(m.group())
        except Exception:
            logger.warning("Failed to parse synthesis JSON, using fallback")

    fallback_msg = {
        "Arabic": "اكتملت مناظرة الحوار",
        "English": "Debate synthesis completed",
        "French": "Synthèse du débat terminée",
        "Spanish": "Síntesis del debate completada",
        "German": "Debattenzusammenfassung abgeschlossen",
    }.get(language, "Debate completed")

    return {
        "final_answer": debate_log[-1]["responses"][0]["response"],
        "top_contributors": [MODELS[0]["name"]],
        "debate_summary": fallback_msg,
    }


# ── API Endpoints ────────────────────────────────────────────────────────────
@app.get("/")
async def serve_frontend():
    return FileResponse("index.html")


@app.get("/health")
async def health():
    return {"status": "ok", "models": len(MODELS), "synthesis_model": SYNTHESIS_MODEL}


@app.get("/models", response_model=List[ModelInfo])
async def get_models():
    return MODELS


@app.post("/chat")
@limiter.limit("10/minute")
async def chat_stream(request: Request, req: ChatRequest):
    """
    SSE streaming endpoint — replaces the old synchronous /chat.
    Streams debate progress in real-time as each model responds.
    """
    detected_language = detect_language(req.question)
    logger.info("Chat request — language=%s, question=%s", detected_language, req.question[:80])

    async def event_generator():
        debate_log = []
        current_responses = []

        def sse(data: dict) -> str:
            return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

        async def tagged_call(idx: int, coro):
            """Wrap a coroutine so its result is tagged with model index."""
            result = await coro
            return idx, result

        # ── Round 1: Opening Statements ──────────────────────────────────
        yield sse({"type": "round_start", "round": 1, "title": "🎤 Opening Statements", "total_models": len(MODELS)})

        round1_responses = []
        tasks = [
            asyncio.create_task(tagged_call(i, ask_model_safe(m["id"], req.question, detected_language)))
            for i, m in enumerate(MODELS)
        ]

        for coro in asyncio.as_completed(tasks):
            idx, (resp, _) = await coro
            entry = {
                "model_idx": idx,
                "model_name": MODELS[idx]["name"],
                "role": MODELS[idx]["role"],
                "color": MODELS[idx]["color"],
                "response": resp,
                "responding_to": None,
            }
            round1_responses.append(entry)
            yield sse({"type": "model_response", "round": 1, **entry})

        round1_responses.sort(key=lambda r: r["model_idx"])
        debate_log.append({"round": 1, "title": "🎤 Opening Statements", "responses": round1_responses})
        current_responses = round1_responses

        # ── Round 2: Debate ──────────────────────────────────────────────
        yield sse({"type": "round_start", "round": 2, "title": "💬 Debate Round", "total_models": len(MODELS)})

        round2_responses = []
        tasks2 = []
        for i, model in enumerate(MODELS):
            others = [r for r in current_responses if r["model_idx"] != i]
            tasks2.append(
                asyncio.create_task(tagged_call(i, ask_model_safe(model["id"], req.question, detected_language, "", others)))
            )

        for coro in asyncio.as_completed(tasks2):
            idx, (resp, saw) = await coro
            entry = {
                "model_idx": idx,
                "model_name": MODELS[idx]["name"],
                "role": MODELS[idx]["role"],
                "color": MODELS[idx]["color"],
                "response": resp,
                "responding_to": saw if saw else None,
            }
            round2_responses.append(entry)
            yield sse({"type": "model_response", "round": 2, **entry})

        round2_responses.sort(key=lambda r: r["model_idx"])
        debate_log.append({"round": 2, "title": "💬 Debate Round", "responses": round2_responses})

        # ── Synthesis ────────────────────────────────────────────────────
        yield sse({"type": "synthesizing"})

        try:
            final_answer = await synthesize_debate(req.question, detected_language, debate_log)
        except Exception as e:
            logger.error("Synthesis failed: %s", e)
            # Build a best-effort answer from whatever we collected
            best = ""
            for rd in reversed(debate_log):
                for r in rd["responses"]:
                    if not r["response"].startswith("["):
                        best = r["response"]
                        break
                if best:
                    break
            final_answer = {
                "final_answer": best or f"Synthesis failed: {e}",
                "top_contributors": [],
                "debate_summary": f"Synthesis error: {e}",
            }

        top_contributors = final_answer.get("top_contributors", [])
        scores = [95 if m["name"] in top_contributors else 70 for m in MODELS]
        winner_idx = 0
        for i, m in enumerate(MODELS):
            if m["name"] in top_contributors:
                winner_idx = i
                break

        yield sse({
            "type": "done",
            "question": req.question,
            "detected_language": detected_language,
            "debate_log": debate_log,
            "final_answer": final_answer.get("final_answer", ""),
            "debate_summary": final_answer.get("debate_summary", ""),
            "winner": winner_idx,
            "top_contributors": top_contributors,
            "scores": scores,
            "total_rounds": len(debate_log),
        })

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )