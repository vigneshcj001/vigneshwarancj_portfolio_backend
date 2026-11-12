# Portfolio Assistant Backend

FastAPI backend for Vigneshwaran C. J.'s portfolio. It serves a grounded AI assistant, job-description matching, ATS-friendly résumés, page translation, project simulations, public activity metadata, and optional PostgreSQL-backed platform features.

[Assistant architecture](ASSISTANT_ARCHITECTURE.md) · [AI system design review](AI_SYSTEM_DESIGN.md) · [Setup and verification guide](AGENTIC_ASSISTANT.md)

## Capabilities

- JSON and Server-Sent Events responses for portfolio questions.
- Local prompt checks and optional Laya scope/topic classification.
- A bounded LangGraph tool plan over committed Markdown evidence.
- Groq answers with citations, project-specific follow-ups, and prepared UI actions.
- Job-description match: keyword evidence and gaps, plus a schema-validated requirement assessment.
- PostgreSQL session persistence with bounded process-memory fallback, server-side erasure, and a retention purge.
- A shared answer cache for opening questions, invalidated automatically when knowledge changes.
- ATS-friendly résumé as PDF, DOCX, and plain text from canonical content; translation into six target languages.
- An offline retrieval evaluation that gates retrieval quality in tests.
- Cached GitHub/PyPI metadata and safe, deterministic project simulations.
- Contact/subscription storage, a conversion funnel, aggregate analytics, and protected admin revision/link-check endpoints.

## Stack

Python, FastAPI, Uvicorn, Pydantic, LangGraph, LangChain, Groq, HTTPX, asyncpg/PostgreSQL, PyYAML, SlowAPI, and FPDF2. Dependencies are pinned in `requirements.txt`. The Docker runtime uses Python 3.11.

## Local setup

Use Python 3.11 or a compatible newer version. From this repository, create a virtual environment and install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

On macOS/Linux, activate with `source .venv/bin/activate` instead.

Set the required Groq key and the frontend's exact browser origin:

```powershell
$env:GROQ_API_KEY = "your-groq-api-key"
$env:FRONTEND_ORIGIN = "http://localhost:1234"
python -m uvicorn main:app --reload --port 8080
```

Check [the basic health endpoint](http://127.0.0.1:8080/) or [detailed health](http://127.0.0.1:8080/api/health). Interactive API docs and OpenAPI endpoints are disabled by the application.

Configuration also loads `.env` from the **parent workspace**, not from this repository's own `.env` path. Existing environment variables take precedence. Keep provider credentials server-side and outside Git.

For a local frontend, set its build-time `PORTFOLIO_API_URL` to `http://127.0.0.1:8080`. The backend's `FRONTEND_ORIGIN` must match the URL used in the browser; `localhost` and `127.0.0.1` are different origins.

## Configuration

- `GROQ_API_KEY`: required at application import/startup, including when using non-AI API routes.
- `LAYA_API_KEY`: optional intent-classification credential. Without it, local routing is used.
- `LAYA_BASE_URL`: optional Laya service origin; defaults to the configured Railway endpoint in `app/config.py`.
- `LAYA_TIMEOUT_SECONDS`: classification timeout; defaults to `8`.
- `DATABASE_URL`: optional PostgreSQL connection string. Configured storage creates its tables at startup; the database role needs the appropriate privileges. A configured but unreachable database can prevent startup.
- `ADMIN_API_KEY`: required to use admin endpoints, supplied as `X-Admin-Key` on requests.
- `TRUSTED_PROXY_COUNT`: number of reverse proxies that append to `X-Forwarded-For` (default `0`). **Set to `1` on Render/Railway**; otherwise every visitor shares the proxy's IP and therefore one rate-limit bucket. Left-most (client-supplied) entries are never trusted.
- `EXTRA_ALLOWED_ORIGINS`: optional comma-separated CORS origins, e.g. `http://localhost:1234` for local frontend development.
- `GITHUB_TOKEN`: optional read-only token for `/api/proof`, raising GitHub's limit from 60 to 5,000 requests/hour. Upstream failures back off for 5 minutes and serve stale data when available.
- Errors, including rate limits (`429` with `Retry-After`), use the `{"detail": "..."}` shape. Every response carries an `X-Request-ID` that also appears in the access log. `/api/health` pings the database and reports `degraded` when configured storage is unreachable.
- `FRONTEND_ORIGIN`: adds one allowed browser origin alongside the deployed portfolio origin.
- `METADATA_CACHE_SECONDS`: public metadata cache duration; defaults to `3600`.
- `GROQ_MODEL`: generation model for the assistant, job match, and translation; defaults to `openai/gpt-oss-120b`.
- `ANSWER_TEMPERATURE`: assistant answer sampling temperature; defaults to `0.65`. Lower values (0.2–0.4) favour strict adherence to retrieved facts; see [AI_SYSTEM_DESIGN.md](AI_SYSTEM_DESIGN.md).
- `ANSWER_CACHE_DAYS`: days a cached opening answer stays valid; defaults to `7`.
- `SESSION_RETENTION_DAYS`: days an idle chat session is kept in PostgreSQL before the startup purge; defaults to `30`.
- `LANGCHAIN_API_KEY`, `LANGCHAIN_PROJECT`, and `LANGCHAIN_TRACING_V2`: optional LangSmith tracing. A supplied key enables tracing unless explicitly disabled with `LANGCHAIN_TRACING_V2=false`; traces can include user content and session metadata.

Without PostgreSQL, the assistant still works with process-memory fallback. Contact/subscription writes and storage-dependent admin operations return unavailable responses; analytics ingestion can acknowledge events without persisting them.

## Assistant request flow

```text
Question + language + session ID
  → Validate request and restore bounded conversation history
  → Local prompt checks and optional Laya scope/topic classification
  → LangGraph route → plan → execute, with up to four typed tool calls
  → Read OKF Markdown context and prepare allowlisted UI actions
  → Groq streams a grounded answer
  → Clean final text, save the exchange, and emit done metadata
  → Frontend validates and executes permitted actions
```

The planner uses explicit rules to select from nine tools; it is not an autonomous LLM tool-selection loop. Retrieval uses local token matching, not embeddings or a vector database. The assistant does not browse the web or operate employer systems.

Blocked requests receive fixed localized replies without retrieval or Groq generation. Laya failures fall back to local topic rules, whose scope detection is narrower. Contact actions only prepare drafts for the visitor to review and send.

`POST /api/assistant/stream` uses a streaming POST with `data: {JSON}` SSE frames. Events include `status`, `tool`, `ui_action`, `token`, and `done`; errors carry an `error` field. Prepared action events do not mean the browser has completed the action. See [ASSISTANT_ARCHITECTURE.md](ASSISTANT_ARCHITECTURE.md) for protocol examples, exact limits, and memory behavior.

## API surface

Public endpoints:

- `GET /` and `GET /api/health`: basic and detailed health.
- `POST /api/assistant`: one JSON assistant response.
- `POST /api/assistant/stream`: streaming assistant response. Opening questions (no prior history) are cached in memory and, when configured, in PostgreSQL (`portfolio_answer_cache`, `ANSWER_CACHE_DAYS`, default 7). The cache key includes a hash of the knowledge base, so Markdown edits invalidate it.
- `DELETE /api/assistant/session/{id}`: erase a conversation's server-side history (204 even for unknown IDs).
- `POST /api/match`: job-description fit. Keyword evidence/gaps from the portfolio plus a schema-validated Groq requirement assessment; falls back to keywords only. The job text is not stored.
- `GET /api/resume`, `/api/resume.docx`, `/api/resume.txt`: ATS-friendly résumé (single column, standard headings, contact in body, no tables/icons) from one content model in `app/services/resume_document.py`. `python scripts/export_resume.py ../vigneshwarancj-portfolio-website` refreshes the website's static copies offline.
- `POST /api/translate`: ordered translation of text batches.
- `GET /api/proof`: cached public GitHub/PyPI metadata.
- `POST /api/demo/{slug}`: simulations for `aiora`, `pocketpet`, and `glycanbench`.
- `POST /api/events`: conversion/feedback event ingestion.
- `POST /api/contact`: contact-message storage, not email delivery.
- `POST /api/newsletter`: subscriber storage with deduplication.
- `GET /api/og/{slug}.svg`: generated sharing-card SVG.

Admin endpoints require `X-Admin-Key`:

- `GET /api/admin/content` and `PUT /api/admin/content`: read/save content revisions.
- `GET /api/admin/analytics`: event aggregates.
- `GET /api/admin/funnel?days=30`: daily page view → case study → résumé → job match → contact counts and top case studies.
- `POST /api/admin/check-links`: check canonical content links.

Saving a revision does not rebuild Markdown knowledge or publish frontend changes. Newsletter storage does not send newsletters. Frontend contact email delivery uses its separate EmailJS integration.

## Knowledge maintenance

`knowledge/index.md` lists 25 YAML-frontmatter Markdown documents covering profile, education, certifications, skills, research, ten independent projects, and four experience records. AIORA facts live in the Ceiyone experience document.

Edit indexed documents and validate from this repository:

```powershell
node scripts/check_okf.mjs
python -m unittest discover -s tests -v
python -m evals.retrieval_eval
```

When adding a document, add at least one labelled question for it to `evals/retrieval_cases.json` so the retrieval gate covers it. After content changes, refresh the website's static résumé copies:

```powershell
python scripts/export_resume.py ../vigneshwarancj-portfolio-website
```

The Node validator requires Node.js. Application startup also validates knowledge with Python. Restart the backend after content changes because loaded documents are cached.

The sibling frontend's prebuild compiles this content into `src/data/portfolio.generated.js`; standalone frontend builds can use their committed snapshot. Some frontend presentation data remains separate and must be kept aligned. Changes to the agent's flow, tools, models, or limits should also update the frontend architecture explorer.

## Source layout

```text
main.py                   Application, middleware, routes, and lifecycle
app/config.py             Environment configuration and limits
app/content.py            Indexed Markdown validation and portfolio compilation
app/agent/                Graph, typed tools/actions, and session memory
app/ai/                   Routing, lexical retrieval, generation, and presentation
app/routes/               Assistant, résumé, platform, and translation endpoints
app/services/             Storage, job match, résumé document model, metadata, demos, translation
app/schemas/              Platform and translation request validation
app/models.py             Assistant request/response models
knowledge/                Canonical structured Markdown evidence
evals/                    Retrieval evaluation cases and runner
scripts/check_okf.mjs     Knowledge-bundle validator
scripts/export_resume.py  Offline PDF/DOCX/TXT résumé export
tests/                    Unit and asynchronous regression tests
Dockerfile                Non-root Python 3.11 container
```

## Tests

With dependencies installed and the virtual environment active:

```powershell
python -m unittest discover -s tests -v
```

Coverage includes retrieval quality (a recall@4 and MRR gate over `evals/retrieval_cases.json`), routing, tool plans, action validation, contextual recommendations, streamed operation summaries, history bounds, session isolation and erasure, answer-cache keys, JSONB decoding, translation validation, job-match keyword precision and output parsing, résumé rendering in all three formats, proxy-aware rate-limit keys, the 429 error shape, and demo behavior. Tests do not establish production provider availability, live answer quality, PostgreSQL connectivity, email delivery, or Docker runtime behavior. Frontend Playwright suites cover browser action outcomes separately.

Run the retrieval evaluation directly to see per-question rankings:

```powershell
python -m evals.retrieval_eval --verbose
```

## Docker

From this repository:

```powershell
docker build -t portfolio-backend .
docker run --rm -p 8080:8000 --env GROQ_API_KEY --env FRONTEND_ORIGIN portfolio-backend
```

The command passes the previously set host environment values into the container. Add other variables as needed. The image listens on port `8000`; this example publishes host port `8080`. Required knowledge Markdown is explicitly included by `.dockerignore`. Supply secrets through deployment environment variables rather than copying them into the image.

## Current limits

Messages are limited to 500 characters and request bodies to 64 KiB. Generation history is bounded to eight items within 1,200 characters. Assistant endpoints allow 10 requests/minute and 100/day per visitor IP, with a 30-second generation timeout. Job match allows 6/minute and 40/day.

Prompt guards and classification are heuristic; grounding instructions do not guarantee correct answers, and no automated check verifies answers against retrieved context. Retrieval is lexical, so some paraphrased questions miss their document (measured paraphrase recall@4: 0.857). Session IDs partition history but are not account authentication. Rate-limit state and process fallback are not shared across workers; the answer cache is shared only through PostgreSQL. Suggestions are curated templates rather than a second generated response. [AI_SYSTEM_DESIGN.md](AI_SYSTEM_DESIGN.md) lists the recommended next steps.

For the complete execution order, memory budgets, streaming contract, and configuration notes, see [ASSISTANT_ARCHITECTURE.md](ASSISTANT_ARCHITECTURE.md).
