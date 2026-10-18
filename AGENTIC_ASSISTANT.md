# Agentic portfolio assistant

## Current versus target

| Capability | Before | Upgraded design |
| --- | --- | --- |
| Orchestration | Laya topic routing followed by one OKF retrieval and Groq call | LangGraph `route -> plan -> execute` state graph; Laya remains scope/topic router |
| Knowledge | Structured Markdown OKF retrieval | Same source of truth, accessed only through typed portfolio tools |
| Tools | Retrieval embedded in route | Nine named tools with Pydantic input models and four-call turn budget |
| Browser behavior | Answer links only | Typed SSE UI actions interpreted through fixed frontend target allowlist |
| Memory | Browser-local transcripts sent as request history | Isolated server session memory backed by PostgreSQL when configured, bounded process fallback, plus existing browser persistence |
| Streaming | Text and final metadata | Status, tool completion, UI action, token, and done events |
| Observability | Optional LangChain tracing environment | LangGraph run names, tags, session metadata, and existing optional LangSmith configuration |
| Safety | Scope routing, prompt guard, output cleaning, rate limits | Existing controls plus Pydantic tools, fixed targets, tool budget, session validation, and confirmation-gated contact handoff |

## Request flow

Progress describes the requested project and the records actually being read, rather than exposing tool identifiers. LangGraph streams each operation's status and outcome before generation starts. Browser actions remain prepared until the frontend finds the destination and reports a result; contact handoffs prepare drafts only. Restoring a saved conversation does not replay navigation.

Project follow-ups carry the named project into retrieval and navigation. Suggested questions name the project, cover a different aspect from the current request, and omit questions already asked in the session. Answer instructions lead with the requested fact and supporting implementation details, and never claim a browser action has already happened.

1. Frontend sends message, selected language, recent transcript, and browser session ID.
2. API restores isolated server memory when available.
3. LangGraph asks Laya for scope and topic, builds an approved tool plan, then executes at most four tools.
4. Tools read only committed Markdown portfolio content or create validated UI actions.
5. API streams tool progress and UI actions, then Groq streams an answer grounded in tool context.
6. Frontend validates every action against `AGENT_TARGETS`; unknown targets are discarded. No generated code, selector, URL, or JavaScript executes.
7. Completed turn persists in PostgreSQL when `DATABASE_URL` exists. Bounded memory keeps local development usable without a database.

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

- Ask “Show me PocketPet.” Confirm `search_portfolio` and `get_project_details` traces, navigation to PocketPet, highlight, sources, and grounded answer.
- Ask “Give me a PocketPet walkthrough.” Start walkthrough and step through overview, role, architecture, and decisions.
- Ask a follow-up such as “What safety controls does it use?” Confirm project context remains.
- Start another saved conversation. Confirm histories stay isolated.
- Ask to contact Vigneshwaran. Confirm assistant offers contact preparation and never submits form without visitor action.
- Send an unknown action target in a mocked response. Confirm frontend ignores it.
- Unset `LANGCHAIN_API_KEY`. Confirm chat works without remote traces.
