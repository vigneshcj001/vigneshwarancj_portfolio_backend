# Portfolio assistant architecture

## Request flow

1. `knowledge/index.md` lists canonical Open Knowledge Format documents organised by content type.
2. Local OKF retrieval selects relevant profile, project, experience, skill, education, or research documents.
3. LangGraph runs `route -> plan -> execute`, using Laya `POST /v1/systemone` for typed `scope` and `topic` decisions.
4. Planner selects from nine Pydantic-validated portfolio and UI tools, with four executions maximum per turn.
5. Off-topic and prompt-extraction requests receive fixed replies without an LLM call.
6. Groq generates visitor-facing text only from tool-retrieved OKF context and isolated session history.
7. SSE emits status, tool, validated UI action, token, and final metadata events.
8. Existing output sanitizer, request limits, rate limits, and timeouts remain active.

Full gap analysis, setup, protocol, and verification steps: [`AGENTIC_ASSISTANT.md`](AGENTIC_ASSISTANT.md).

## Environment

Backend loads `E:\full_stack_portfolio\.env` so both repositories use one workspace configuration.

```dotenv
GROQ_API_KEY=gsk_...
LAYA_API_KEY=...
LAYA_BASE_URL=https://laya-production-b57e.up.railway.app
LAYA_TIMEOUT_SECONDS=8
```

Laya and Groq use separate provider credentials. Keys stay in backend environment variables and never enter browser bundles, logs, analytics, or OKF documents. When Laya is unavailable, local prompt-injection checks and Groq's portfolio-only system rule preserve service availability.

## Updating knowledge

Edit typed Markdown files under `knowledge/`, then validate them:

```powershell
node scripts/check_okf.mjs
python -m unittest discover -s tests -v
```

Backend compiles these files into portfolio objects for résumé and API use. Frontend prebuild compiles same Markdown into `src/data/portfolio.generated.js`. Deployment validates bundle at startup. Missing, empty, duplicated, unsupported, or unsafe entries stop startup instead of silently running with ungrounded knowledge.
