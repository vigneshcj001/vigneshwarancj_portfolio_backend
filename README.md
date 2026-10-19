# Portfolio Assistant Backend

FastAPI backend for Vigneshwaran C. J.'s portfolio. It serves a grounded AI assistant, résumé PDFs, page translation, project simulations, public activity metadata, and optional PostgreSQL-backed platform features.

[Assistant architecture](ASSISTANT_ARCHITECTURE.md) · [Setup and verification guide](AGENTIC_ASSISTANT.md)

## Capabilities

- JSON and Server-Sent Events responses for portfolio questions.
- Local prompt checks and optional Laya scope/topic classification.
- A bounded LangGraph tool plan over committed Markdown evidence.
- Groq answers with citations, project-specific follow-ups, and prepared UI actions.
- PostgreSQL session persistence with bounded process-memory fallback.
- Canonical-content résumé PDF generation and translation into six target languages.
- Cached GitHub/PyPI metadata and safe, deterministic project simulations.
- Contact/subscription storage, aggregate analytics, and protected admin revision/link-check endpoints.

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
- `FRONTEND_ORIGIN`: adds one allowed browser origin alongside the deployed portfolio origin.
- `METADATA_CACHE_SECONDS`: public metadata cache duration; defaults to `3600`.
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
- `POST /api/assistant/stream`: streaming assistant response.
- `GET /api/resume`: generated PDF download.
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
- `POST /api/admin/check-links`: check canonical content links.

Saving a revision does not rebuild Markdown knowledge or publish frontend changes. Newsletter storage does not send newsletters. Frontend contact email delivery uses its separate EmailJS integration.

## Knowledge maintenance

`knowledge/index.md` lists 25 YAML-frontmatter Markdown documents covering profile, education, certifications, skills, research, ten independent projects, and four experience records. AIORA facts live in the Ceiyone experience document.

Edit indexed documents and validate from this repository:

```powershell
node scripts/check_okf.mjs
python -m unittest discover -s tests -v
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
app/services/             PostgreSQL storage, metadata, demos, and translation
app/schemas/              Platform and translation request validation
app/models.py             Assistant request/response models
knowledge/                Canonical structured Markdown evidence
scripts/check_okf.mjs      Knowledge-bundle validator
tests/                    Unit and asynchronous regression tests
Dockerfile                Non-root Python 3.11 container
```

## Tests

With dependencies installed and the virtual environment active:

```powershell
python -m unittest discover -s tests -v
```

Coverage includes retrieval, routing, tool plans, action validation, contextual recommendations, streamed operation summaries, history bounds, session isolation, JSONB decoding, translation validation, and demo behavior. Tests do not establish production provider availability, live answer quality, PostgreSQL connectivity, email delivery, or Docker runtime behavior. Frontend Playwright suites cover browser action outcomes separately.

## Docker

From this repository:

```powershell
docker build -t portfolio-backend .
docker run --rm -p 8080:8000 --env GROQ_API_KEY --env FRONTEND_ORIGIN portfolio-backend
```

The command passes the previously set host environment values into the container. Add other variables as needed. The image listens on port `8000`; this example publishes host port `8080`. Required knowledge Markdown is explicitly included by `.dockerignore`. Supply secrets through deployment environment variables rather than copying them into the image.

## Current limits

Messages are limited to 500 characters and request bodies to 64 KiB. Generation history is bounded to eight items within 1,200 characters. Assistant endpoints allow 10 requests/minute and 100/day per IP, with a 30-second generation timeout.

Prompt guards and classification are heuristic; grounding instructions do not guarantee correct answers. Session IDs partition history but are not account authentication. Process fallback, rate-limit state, and caches are not shared across workers or durable across restarts. Browser Clear chat does not erase the server session. Suggestions are curated templates rather than a second generated response.

For the complete execution order, memory budgets, streaming contract, and configuration notes, see [ASSISTANT_ARCHITECTURE.md](ASSISTANT_ARCHITECTURE.md).
