# Agentic portfolio assistant

## Current implementation

Reviewed 12 November 2026. Detailed execution order, protocol, limits, and caveats: [ASSISTANT_ARCHITECTURE.md](ASSISTANT_ARCHITECTURE.md). Design assessment and next steps: [AI_SYSTEM_DESIGN.md](AI_SYSTEM_DESIGN.md).

Laya classifies scope/topic before a fixed LangGraph `route → plan → execute` graph. Explicit rules select from nine typed tools, with at most four calls. Tools read committed OKF Markdown or prepare known UI actions. Groq generates the grounded answer afterward; it does not select tools.

The browser stores local transcripts, while PostgreSQL or bounded process memory stores server sessions. SSE carries specific work summaries, prepared actions, text tokens, and final metadata. Frontend targets are allowlisted, navigation receipts check the actual destination, and contact actions only prepare drafts. Optional LangSmith tracing adds named runs and session metadata.

The public frontend route `/assistant-architecture` shows interactive normal, contact, refusal, and Laya-fallback flows. Its scenario controls make no provider calls; Try this question fills the composer without auto-submitting.

## Request flow

Progress describes the requested project and the records actually being read, rather than exposing tool identifiers. LangGraph streams each operation's status and outcome before generation starts. Browser actions remain prepared until the frontend finds the destination and reports a result; contact handoffs prepare drafts only. Restoring a saved conversation does not replay navigation.

Project follow-ups carry the named project into retrieval and navigation. Suggested questions name the project, cover a different aspect from the current request, and omit questions already asked in the session. Answer instructions lead with the requested fact and supporting implementation details, and never claim a browser action has already happened.

1. Frontend sends message, selected language, recent transcript, and browser session ID.
2. API restores isolated server memory when available.
3. Local checks and optional Laya classify scope/topic. LangGraph consumes that decision, builds a rule-based plan, then executes at most four tools.
4. Tools read only committed Markdown portfolio content or create validated UI actions.
5. API streams tool progress and UI actions, then Groq streams an answer grounded in tool context.
6. API cleans the completed answer, saves the exchange through PostgreSQL or memory fallback, and sends final metadata.
7. Frontend validates actions against `AGENT_TARGETS`. Known navigation/highlights may run after the final response; tours/drafts need interaction. No arbitrary generated code, selector, or URL executes.

## Key files

- `app/agent/graph.py`: LangGraph state machine and bounded plan.
- `app/agent/tools.py`: typed tool definitions and implementations.
- `app/agent/protocol.py`: structured action and trace contracts.
- `app/agent/memory.py`: session validation, isolated persistence, and erasure.
- `app/ai/okf.py`: lexical retrieval, query expansion, and the knowledge hash used for cache invalidation.
- `app/routes/assistant.py`: SSE protocol, answer cache, memory lifecycle, and session deletion.
- `app/services/match.py`: job-description match (keyword evidence plus validated model assessment).
- `evals/retrieval_eval.py`, `evals/retrieval_cases.json`: retrieval quality measurement.
- `src/features/assistant/actions.js`: frontend action allowlist and executor.
- `src/features/assistant/stream.js`: typed event consumer.
- `src/features/assistant/storage.js`: local conversations and unguessable session IDs.
- `src/Components/PortfolioAssistant.js`: tool status, action controls, walkthrough UI, voice input, live API status.

## Setup

Paths are relative to the workspace folder that holds both repositories and the shared `.env`.

```powershell
cd vigneshwarancj_portfolio_backend
python -m pip install -r requirements.txt
```

The backend loads `.env` from the parent workspace folder. Set `GROQ_API_KEY` and `LAYA_API_KEY` there. Set `DATABASE_URL` for durable server memory, the shared answer cache, and the admin funnel. For LangSmith tracing, set `LANGCHAIN_API_KEY` and optionally `LANGCHAIN_PROJECT`; tracing stays disabled without a key. Never commit `.env`.

```powershell
uvicorn main:app --reload --port 8080
cd ..\vigneshwarancj-portfolio-website
npm install
npm start
```

For local frontend development against this API, set `EXTRA_ALLOWED_ORIGINS=http://localhost:1234` in `.env` and build the frontend with `PORTFOLIO_API_URL=http://127.0.0.1:8080`.

## Verification

```powershell
python -m unittest discover -s tests -v
python -m evals.retrieval_eval --verbose
npm run build
npm test
npm run test:browser
```

- Ask “Show me PocketPet.” Confirm specific source summaries, navigation to PocketPet, a destination receipt, citations, and grounded text.
- Ask “Give me a PocketPet walkthrough.” Start walkthrough and step through overview, role, architecture, and decisions.
- Ask a follow-up such as “What safety controls does it use?” Confirm project context remains.
- Start another saved conversation. Confirm histories stay isolated.
- Ask to contact Vigneshwaran. Confirm assistant offers contact preparation and never submits form without visitor action.
- Send an unknown action target in a mocked response. Confirm frontend ignores it.
- Unset `LANGCHAIN_API_KEY`. Confirm chat works without remote traces.
- Ask the same opening question twice in new conversations. Confirm the second answer returns without a model call (`"cached": true` on the `done` event).
- Select Clear chat, then ask a follow-up. Confirm the earlier context is gone on the server too.
- Open `/match`, select Use a sample, and analyze. Confirm the requirement checklist, evidence links, and gaps. With `GROQ_API_KEY` invalid, confirm the keyword-only result and its notice.
- Open a case study and select a suggested question. Confirm the assistant opens and answers about that project.
- Visit `/assistant-architecture`. Check seven normal stages, four refusal stages, scenario resets, keyboard controls, mobile layout, and composer prefill without an automatic request.
