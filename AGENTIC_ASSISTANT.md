# Agentic portfolio assistant

## Current implementation

Reviewed 19 October 2026. Detailed execution order, protocol, limits, and caveats: [ASSISTANT_ARCHITECTURE.md](ASSISTANT_ARCHITECTURE.md).

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

## Files changed

- `app/agent/graph.py`: LangGraph state machine and bounded plan.
- `app/agent/tools.py`: typed tool definitions and implementations.
- `app/agent/protocol.py`: structured action and trace contracts.
- `app/agent/memory.py`: session validation and isolated persistence.
- `app/routes/assistant.py`: enriched SSE protocol and memory lifecycle.
- `src/features/assistant/actions.js`: frontend action allowlist and executor.
- `src/features/assistant/stream.js`: typed event consumer.
- `src/Components/PortfolioAssistant.js`: tool status, action controls, walkthrough UI, existing voice input.

## Setup

```powershell
cd E:\full_stack_portfolio\vigneshwarancj_portfolio_backend
python -m pip install -r requirements.txt
```

Backend loads shared `E:\full_stack_portfolio\.env`. Set `GROQ_API_KEY` and `LAYA_API_KEY` there. Set `DATABASE_URL` for durable server memory. For LangSmith tracing, set `LANGCHAIN_API_KEY` and optionally `LANGCHAIN_PROJECT`; tracing stays disabled without a key.

```powershell
uvicorn main:app --reload --port 8080
cd E:\full_stack_portfolio\vigneshwarancj-portfolio-website
npm install
npm start
```

## Verification

```powershell
python -m unittest discover -s tests -v
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
- Visit `/assistant-architecture`. Check seven normal stages, four refusal stages, scenario resets, keyboard controls, mobile layout, and composer prefill without an automatic request.
