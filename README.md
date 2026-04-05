# AMONG·AI 🚀

> **6 AI Crewmates. 1 Winner.** Ask anything and watch multiple AI models debate in real-time to find the best answer.

Inspired by *Among Us*, AMONG·AI pits 6 different LLMs against each other in a multi-round debate. Each model responds independently, then reads the others' answers and refines their position. A synthesis engine combines the best insights into one collaborative answer.

**J & M · J©M · ©2026**

---

## ✨ Features

- **Multi-model debate** — 6 different AI models respond to every question
- **Real-time streaming** — Watch crewmates respond one-by-one via Server-Sent Events
- **Multi-language** — Auto-detects 50+ languages and responds in the same language
- **Collaborative synthesis** — Best ideas from all models combined into one answer
- **Full debate log** — Expand to see every model's opening statement and debate response
- **Markdown rendering** — Responses render with formatting, code blocks, and lists
- **Rate limiting** — Built-in protection against API abuse
- **Mobile responsive** — Works on phones, tablets, and desktops

---

## 🏗 Architecture

```
User → Browser (index.html)
         ↓ POST /chat (SSE stream)
       FastAPI Backend (main.py)
         ↓ Parallel async calls
    ┌────┼────┬────┬────┬────┐
    │    │    │    │    │    │
  LLAMA LLAMA LLAMA QWEN GPT  GPT
  70B   8B   4Scout 32B  120  20
    │    │    │    │    │    │
    └────┼────┴────┴────┴────┘
         ↓ Responses streamed as they arrive
       Synthesis Model
         ↓ Final consensus
       Browser (real-time UI update)
```

---

## 🚀 Quick Start

### 1. Clone & install

```bash
git clone https://github.com/YOUR_USERNAME/among-ai.git
cd among-ai
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env and add your Groq API key
```

Get a free API key at [console.groq.com/keys](https://console.groq.com/keys)

### 3. Run

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Open [http://localhost:8000](http://localhost:8000)

---

## 🐳 Docker

### Build & Run

```bash
docker build -t among-ai .
docker run -p 8000:8000 --env-file .env among-ai
```

### Docker Compose

Create a `docker-compose.yml`:

```yaml
services:
  among-ai:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 5s
      retries: 3
```

Then run:

```bash
docker compose up -d
```

### Passing Environment Variables

You can also pass variables directly instead of using `--env-file`:

```bash
docker run -p 8000:8000 \
  -e GROQ_API_KEY=your_key_here \
  -e SYNTHESIS_MODEL=llama-3.1-8b-instant \
  -e ALLOWED_ORIGINS=https://your-domain.com \
  among-ai
```

---

## 🌐 Deployment

### Railway / Render / Fly.io

1. Push your repo to GitHub
2. Connect the repo to your platform of choice
3. Set these environment variables in the platform dashboard:
   - `GROQ_API_KEY` — your Groq API key
   - `ALLOWED_ORIGINS` — your production domain (e.g., `https://among-ai.example.com`)
4. The platform will auto-detect the `Dockerfile` and deploy

### Manual VPS (Ubuntu)

```bash
# Clone and configure
git clone https://github.com/YOUR_USERNAME/among-ai.git
cd among-ai
cp .env.example .env
nano .env  # Add your GROQ_API_KEY

# Option A: Run with Docker
docker build -t among-ai .
docker run -d -p 8000:8000 --env-file .env --restart unless-stopped among-ai

# Option B: Run directly
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

> **Tip:** For production, put a reverse proxy (Nginx/Caddy) in front of uvicorn for TLS and better performance.

---

## 📡 API

| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | Serves the frontend |
| `/health` | GET | Health check — returns `{"status": "ok", ...}` |
| `/models` | GET | Returns the list of available crewmate models |
| `/chat` | POST | SSE streaming debate — send `{"question": "..."}` |

### SSE Event Types

| Event | Description |
|---|---|
| `round_start` | A new debate round is beginning |
| `model_response` | A crewmate has responded (streamed immediately) |
| `synthesizing` | All crewmates responded, generating consensus |
| `done` | Final result with consensus answer and scores |

---

## ⚙️ Configuration

| Variable | Default | Description |
|---|---|---|
| `GROQ_API_KEY` | *(required)* | Your Groq API key |
| `SYNTHESIS_MODEL` | `llama-3.1-8b-instant` | Model used for debate synthesis |
| `ALLOWED_ORIGINS` | `*` | CORS allowed origins (comma-separated) |

---

## 🧪 Testing

```bash
pip install pytest httpx
pytest tests/ -v
```

---

## 🤝 Contributing

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/amazing`)
3. Commit your changes
4. Push and open a Pull Request

---

## 📄 License

© 2026 J & M. All rights reserved.
