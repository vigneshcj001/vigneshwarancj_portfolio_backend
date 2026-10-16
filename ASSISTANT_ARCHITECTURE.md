# Portfolio assistant architecture

## Request flow

1. `knowledge/index.md` lists trusted Open Knowledge Format documents generated from `portfolio_data.json`.
2. Local OKF retrieval selects relevant profile, project, experience, skill, education, or research documents.
3. Laya `POST /v1/systemone` makes typed `scope` and `topic` decisions in one request.
4. Off-topic and prompt-extraction requests receive fixed replies without an LLM call.
5. Groq generates visitor-facing text from retrieved OKF context and recent chat history.
6. Existing output sanitizer, request limits, rate limits, timeouts, and SSE streaming remain active.

## Environment

```dotenv
GROQ_API_KEY=gsk_...
LAYA_API_KEY=...
LAYA_BASE_URL=https://laya-production-b57e.up.railway.app
LAYA_TIMEOUT_SECONDS=8
```

Laya and Groq use separate provider credentials. Keys stay in backend environment variables and never enter browser bundles, logs, analytics, or OKF documents. When Laya is unavailable, local prompt-injection checks and Groq's portfolio-only system rule preserve service availability.

## Updating knowledge

After editing `portfolio_data.json`, rebuild and validate committed OKF documents:

```powershell
node scripts/build_okf.mjs
node scripts/check_okf.mjs
```

Deployment validates bundle at startup. Missing, empty, or unsafe indexed paths stop startup instead of silently running with ungrounded knowledge.
