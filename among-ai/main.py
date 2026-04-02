from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Dict
import asyncio, json, re
from groq import AsyncGroq
import langdetect

app = FastAPI(title="Among-AI Backend")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

GROQ_API_KEY = "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"
client = AsyncGroq(api_key=GROQ_API_KEY)

MODELS = [
    {"id": "llama-3.3-70b-versatile",           "name": "LLAMA 70B",   "role": "The Brain",    "color": "#FF4655", "dark": "#7A1520", "glow": "rgba(255,70,85,0.25)"},
    {"id": "llama-3.1-8b-instant",              "name": "LLAMA 8B",    "role": "The Quick",    "color": "#26D07C", "dark": "#0C6035", "glow": "rgba(38,208,124,0.25)"},
    {"id": "meta-llama/llama-4-scout-17b-16e-instruct", "name": "LLAMA 4 SCOUT", "role": "The Scout", "color": "#2E86DE", "dark": "#134070", "glow": "rgba(46,134,222,0.25)"},
    {"id": "qwen/qwen3-32b",                    "name": "QWEN 32B",    "role": "The Sage",     "color": "#00D4FF", "dark": "#005A6B", "glow": "rgba(0,212,255,0.25)"},
    {"id": "openai/gpt-oss-120b",               "name": "GPT-OSS 120", "role": "The Titan",    "color": "#FFCB2F", "dark": "#7A5800", "glow": "rgba(255,203,47,0.25)"},
    {"id": "openai/gpt-oss-20b",                "name": "GPT-OSS 20",  "role": "The Nimble",   "color": "#FF8C42", "dark": "#7A3A00", "glow": "rgba(255,140,66,0.25)"},
    {"id": "llama-3.3-70b-versatile",           "name": "LLAMA 70B-2", "role": "The Maverick", "color": "#A855F7", "dark": "#4C1D95", "glow": "rgba(168,85,247,0.25)"},
]

class ChatRequest(BaseModel):
    question: str

def detect_language(text: str) -> str:
    """Detect the language of the input text"""
    try:
        lang = langdetect.detect(text)
        lang_map = {
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
        return lang_map.get(lang, lang)
    except:
        return "English"

def truncate_text(text: str, max_chars: int = 300) -> str:
    """Truncate text to stay within token limits"""
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(' ', 1)[0] + "..."

async def ask_model(model_id: str, question: str, language: str, context: str = "", seeing_responses: List[Dict] = None) -> tuple:
    """Ask a single model with optional context from other models"""
    messages = []
    what_they_saw = ""
    
    system_prompt = f"""You are a helpful AI assistant. You MUST respond in {language} only.
The user asked their question in {language}, so you must answer in the same language.
Respond naturally and fluently in {language}. Keep your response concise (2-3 paragraphs max)."""

    if seeing_responses:
        # Truncate what models see from others to save tokens
        what_they_saw = "\n\n".join([
            f"{r['model_name']}: {truncate_text(r['response'], 200)}"
            for r in seeing_responses
        ])
        system_prompt += f"""\n\nYou are in a group discussion. Crewmates said:\n{what_they_saw}\n\nRespond in {language}, building on their ideas. Be concise."""

    messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": question})
    
    r = await client.chat.completions.create(
        model=model_id,
        messages=messages,
        max_tokens=400,  # Reduced from 800 to save tokens
        temperature=0.7,
    )
    return r.choices[0].message.content.strip(), what_they_saw

async def full_debate(question: str, language: str, rounds: int = 2) -> Dict:
    """Full multi-round debate with token management"""
    debate_log = []
    current_responses = []
    
    # Round 1: Opening statements
    print(f"Round 1: Opening statements in {language}...")
    tasks = [ask_model(m["id"], question, language) for m in MODELS]
    results = await asyncio.gather(*tasks)
    
    round1_responses = []
    for i, (resp, _) in enumerate(results):
        round1_responses.append({
            "model_idx": i,
            "model_name": MODELS[i]["name"],
            "role": MODELS[i]["role"],
            "color": MODELS[i]["color"],
            "response": resp,
            "responding_to": None
        })
    
    debate_log.append({
        "round": 1,
        "title": "🎤 Opening Statements",
        "responses": round1_responses
    })
    current_responses = round1_responses
    
    # Round 2: Debate (models see previous round - truncated)
    print(f"Round 2: Debate in {language}...")
    
    tasks = []
    for i, model in enumerate(MODELS):
        others_responses = [r for r in current_responses if r["model_idx"] != i]
        tasks.append(ask_model(model["id"], question, language, "", others_responses))
    
    results = await asyncio.gather(*tasks)
    
    round2_responses = []
    for i, (resp, saw) in enumerate(results):
        round2_responses.append({
            "model_idx": i,
            "model_name": MODELS[i]["name"],
            "role": MODELS[i]["role"],
            "color": MODELS[i]["color"],
            "response": resp,
            "responding_to": saw if saw else None
        })
    
    debate_log.append({
        "round": 2,
        "title": f"💬 Debate Round",
        "responses": round2_responses
    })
    current_responses = round2_responses
    
    # Final synthesis with heavily truncated context
    final_answer = await synthesize_debate(question, language, debate_log)
    
    return {
        "debate_log": debate_log,
        "final_answer": final_answer,
        "total_rounds": len(debate_log),
        "language": language
    }

async def synthesize_debate(question: str, language: str, debate_log: List[Dict]) -> Dict:
    """Create final answer with token-efficient summary"""
    # Build compact debate summary (truncated heavily)
    debate_summary = ""
    for round_data in debate_log:
        debate_summary += f"\n{round_data['title']}:\n"
        for r in round_data["responses"]:
            # Truncate each response to ~150 chars for summary
            truncated = truncate_text(r["response"], 150)
            debate_summary += f"- {r['model_name']}: {truncated}\n"
    
    prompt = f"""Question: "{question}"
Language: {language}

Debate summary:
{debate_summary}

Synthesize into ONE excellent answer in {language}. Be comprehensive but concise.

Return JSON:
{{"final_answer": "your answer in {language}", "top_contributors": ["Name1", "Name2"], "debate_summary": "brief analysis in {language}"}}"""

    result = await client.chat.completions.create(
        model="llama-3.1-8b-instant",  # Use smaller model for synthesis to save tokens
        messages=[
            {"role": "system", "content": f"You are a debate moderator. Output ONLY in {language}."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=600,
        temperature=0.3,
    )
    
    text = result.choices[0].message.content.strip()
    m = re.search(r'\{[\s\S]*?\}', text)
    if m:
        try:
            return json.loads(m.group())
        except:
            pass
    
    # Fallback - use best response
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
        "debate_summary": fallback_msg
    }

@app.get("/")
async def serve_frontend():
    return FileResponse("index.html")

@app.post("/chat")
async def chat(req: ChatRequest):
    detected_language = detect_language(req.question)
    print(f"Detected language: {detected_language}")
    
    debate_result = await full_debate(req.question, detected_language, rounds=2)
    
    top_contributors = debate_result["final_answer"].get("top_contributors", [])
    scores = [95 if m["name"] in top_contributors else 70 for m in MODELS]
    
    winner_idx = 0
    for i, m in enumerate(MODELS):
        if m["name"] in top_contributors:
            winner_idx = i
            break
    
    return {
        "question": req.question,
        "detected_language": detected_language,
        "debate_log": debate_result["debate_log"],
        "final_answer": debate_result["final_answer"].get("final_answer", ""),
        "debate_summary": debate_result["final_answer"].get("debate_summary", ""),
        "winner": winner_idx,
        "top_contributors": top_contributors,
        "scores": scores,
        "total_rounds": debate_result["total_rounds"]
    }