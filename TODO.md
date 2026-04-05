# AMONG·AI — TODO & Future Features

> Tracked improvements and new features that could take Among·AI to the next level.

---

## 🔴 High Priority

- [ ] **Conversation History** — Allow follow-up questions that reference previous debates (session memory)
- [ ] **Model Health Check on Startup** — Ping each model at boot and disable any that are decommissioned/unreachable instead of failing at request time
- [ ] **Graceful Degradation UI** — When a model fails mid-debate, show a "disconnected" state on its crewmate avatar instead of silently skipping it
- [ ] **Input Validation** — Reject empty or excessively long questions (max 2000 chars) with user-friendly error messages
- [ ] **API Key Rotation Support** — Accept multiple comma-separated Groq API keys and round-robin between them to avoid rate limits

---

## 🟡 Medium Priority

- [ ] **Dark/Light Theme Toggle** — Add a theme switcher in the header (persist preference in localStorage)
- [ ] **Voting System** — Let users upvote/downvote individual model responses to crowdsource which models perform best
- [ ] **Export Debate** — Download the full debate log as Markdown or PDF
- [ ] **Custom System Prompts** — Let users set a persona or context (e.g., "explain like I'm 5", "answer as a senior engineer")
- [ ] **Model Selection** — Let users pick which crewmates participate in the debate (checkbox per model)
- [ ] **Response Caching** — Cache identical question+model responses with a TTL to reduce API calls and costs
- [ ] **Debate Rounds Config** — Let users choose 1-3 rounds of debate (currently fixed at 2)
- [ ] **Typing Indicators** — Show animated "thinking..." text under each crewmate while waiting for their response
- [ ] **Sound Effects** — Optional Among Us-style sound effects for round starts, emergency meeting, and voting (with mute toggle)

---

## 🟢 Nice to Have

- [ ] **Share Link** — Generate a shareable URL for a completed debate (requires backend persistence)
- [ ] **Debate History Page** — Store past debates in localStorage or a database, with search and replay
- [ ] **Model Leaderboard** — Track win rates and average scores across all debates in a persistent leaderboard
- [ ] **Image/File Input** — Support vision-capable models by accepting image uploads alongside text questions
- [ ] **Multi-User Rooms** — WebSocket-based rooms where multiple users watch the same debate live
- [ ] **Localized UI** — Translate the interface chrome (buttons, labels, tooltips) to match the detected question language
- [ ] **Accessibility (a11y)** — Add ARIA labels, keyboard navigation, screen reader support, and reduced-motion media queries
- [ ] **PWA Support** — Add a service worker and manifest so users can install Among·AI as a progressive web app
- [ ] **Analytics Dashboard** — Track popular questions, model performance, average response times, and language distribution

---

## 🛠 Technical Debt

- [ ] **Split index.html** — Extract CSS and JS into separate files when the codebase grows beyond ~600 lines
- [ ] **WebSocket Migration** — Replace SSE with WebSockets for bidirectional communication (needed for follow-ups and rooms)
- [ ] **Database Layer** — Add SQLite or PostgreSQL for persistent debate storage, user accounts, and leaderboards
- [ ] **OpenAPI Schema** — Add proper response models to all endpoints so `/docs` auto-generates accurate Swagger UI
- [ ] **Load Testing** — Run k6 or Locust benchmarks to find the concurrency ceiling with Groq's rate limits
- [ ] **Error Boundary in Frontend** — Catch and display JS runtime errors gracefully instead of silently breaking
- [ ] **CI: Browser Tests** — Add Playwright E2E tests to the GitHub Actions pipeline to validate the full SSE flow

---

## ✅ Recently Completed

- [x] Environment variables for API keys (`.env` + `python-dotenv`)
- [x] Rate limiting with `slowapi` (10 req/min)
- [x] Removed broken `frontend/` directory with exposed API key
- [x] SSE streaming with real-time progress UI
- [x] Markdown rendering in responses (`marked.js`)
- [x] Copy-to-clipboard button on consensus card
- [x] Mobile responsive design
- [x] Error-resilient model calls (30s timeout per model)
- [x] Proper logging (replaced `print()`)
- [x] `/health` and `/models` API endpoints
- [x] Configurable synthesis model and CORS origins
- [x] Dockerfile + GitHub Actions CI
- [x] Unit and integration tests (15 passing)
