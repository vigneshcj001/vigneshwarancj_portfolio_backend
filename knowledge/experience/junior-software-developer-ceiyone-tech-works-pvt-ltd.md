---
type: experience
title: Junior Software Developer
order: 0
data:
  role: Junior Software Developer
  company: Ceiyone Tech Works Pvt. Ltd.
  period: Dec 2025 – Present
  type: Full-time
  overview: Designing and maintaining AIORA, a multi-tenant WhatsApp commerce platform spanning 13 microservices for bookings,
    e-commerce, document validation, payments, logistics, and AI interactions. Work covers Node.js/TypeScript and Python APIs,
    concurrent messaging sessions, Redis queues, OCR and GPT-4o Vision, PostgreSQL usage tracking, Razorpay and Shiprocket
    integrations, n8n workflows, and production deployment on Ubuntu VPS and Railway. Also built Kural, a multi-tenant AI
    customer-care voice platform on Sarvam AI, and contributed to CMO Copilot, a grounded marketing-analytics agent.
  projects:
  - name: Kural (multi-tenant AI voice customer-care platform)
    description: 'Built solo (Nov 2026): one shared agent engine where each business gets its own data, knowledge base, agent
      configuration, languages, tools and escalation rules, demonstrated with a real-estate and a hospital business in English
      and Tamil. The engine runs guardrails → context → LLM ⇄ tool calls (max four rounds, 20-second budget); industry modules
      add their own tables and tools; tools are tenant-scoped, validated, time-limited and audited, and bookings require the
      caller''s explicit confirmation. Emergency, human-request and repeated-failure guardrails escalate with a context summary.
      The first version streamed Sarvam STT → LLM → TTS over WebSockets with barge-in and Tamil/English switching; streaming
      LLM replies into speech sentence by sentence cut time to first audio from about 1.27 s to 0.85 s. Voice calls then moved
      to hosted Sarvam Voice Agents via the browser SDK, calling Kural''s tools over signed HTTPS webhooks, because the target
      host (Zoho Catalyst AppSail) cannot keep WebSockets open. JWT/RBAC, Fernet-encrypted integration credentials, tenant-isolation
      tests, 88 backend tests. A live call on hosted Sarvam agents was still pending verification at last update.'
    tech:
    - Python
    - FastAPI
    - SQLAlchemy
    - Alembic
    - PostgreSQL
    - Redis
    - Sarvam AI
    - React
    - TypeScript
    - Vite
    - Tailwind CSS
    - Supabase
    - Zoho Catalyst
    - Docker
  - name: CMO Copilot (marketing analytics AI agent)
    description: 'Team project (Oct 2026): a marketing-analytics agent that answers natural-language questions over Google
      Analytics 4 (Data API and BigQuery), Google Ads, Meta Ads and Search Console. A LangGraph pipeline (guard → understand
      → plan → analyze → compose → validate → respond) builds SQL only from validated query plans, never from users or the
      model, and rejects any number in an answer that cannot be traced to a query result. Multi-tenant configuration, OIDC
      or demo authentication, SSE chat, dashboards, budgets and board-slide export, with Gemini, Anthropic or OpenAI as the
      model. Contributed as a member of the Ceiyone team.'
    tech:
    - Python
    - FastAPI
    - LangGraph
    - BigQuery
    - Google Analytics 4
    - PostgreSQL
    - React
    - TypeScript
    - TanStack Query
    - Recharts
  - name: Bullion Handler
    description: FastAPI service that reads gold-shipment AWB and invoice PDFs with GPT-4o vision, then runs a two-stage rules
      engine — Stage 1 checks the invoice alone (weight, purity, calculations), Stage 2 compares it against its matched AWB
      — and produces bilingual EN/ES PDF reports delivered by email. PostgreSQL for records, Redis Streams/Pub-Sub for job
      pickup and SHA-256 dedup.
    tech:
    - Python
    - FastAPI
    - OpenAI GPT-4o
    - PostgreSQL
    - Redis
    - ReportLab
    - systemd
  - name: Bullion Listener
    description: 'Node.js WhatsApp bot bridging group chats and Bullion Handler: saves incoming PDFs to the shared filesystem,
      hands them to the Python service via HTTP/n8n, and watches report directories with chokidar to deliver finished reports
      back to the originating group.'
    tech:
    - Node.js
    - whatsapp-web.js
    - Chokidar
    - Redis
    - PM2
  - name: Splendor
    description: Express 5 REST API that meters AI token consumption and subscription quotas per client/agent, enforces plan
      limits, and fires low-balance WhatsApp alerts through Oblion with a 4-hour cooldown. OpenAPI docs at /api-docs.
    tech:
    - Node.js
    - Express.js
    - PostgreSQL
    - Joi
    - Winston
    - Swagger/OpenAPI
    - Docker
    - PM2
  - name: Oblion
    description: 'Multi-number WhatsApp gateway: one whatsapp-web.js session per business number, BullMQ-queued outbound sends
      with retries and a dead-letter queue, HMAC-signed inbound webhooks feeding n8n.'
    tech:
    - TypeScript
    - Node.js
    - Express.js
    - BullMQ
    - Redis
    - PostgreSQL
    - WhatsApp Web API
    - n8n
  - name: meridian-api
    description: 'Shared service layer every AIORA WhatsApp conversation runs through: slot availability, bookings, operator-authored
      intake questions, per-agent bot configuration, broadcast campaigns, document ingest, and the single outbound /send endpoint
      that formats every WhatsApp reply.'
    tech:
    - Node.js
    - Express.js
    - PostgreSQL
    - Joi
    - Winston
  - name: Meridian
    description: Customer-facing appointment booking page, pre-filled from WhatsApp, backed by meridian-api for slots and
      intake questions. Recently integrated Healthora's dietician-appointment booking flow into Meridian, consolidating both
      products onto one booking experience.
    tech:
    - React 19
    - Vite
    - Tailwind CSS
  - name: polaris-ui
    description: 'Business-owner dashboard fanning out to four backends (healthora-api, meridian-api, Oblion, ecomm-api):
      bookings, orders, inventory, bot settings, document uploads, broadcast campaigns, WhatsApp session status, a Shiprocket
      connection page, and a home dashboard of revenue, booking/order status, low-stock and campaign charts. E-commerce calls
      are proxied server-side so the API key never reaches the browser.'
    tech:
    - React 19
    - TypeScript
    - Vite
    - Tailwind CSS
    - Axios
    - Node.js
    - Railway
  - name: AIORA E-Commerce
    description: Next.js multi-store commerce platform with catalogue, order, payment, and shipping workflows. Integrated
      Razorpay payments and per-client Shiprocket logistics, normalised courier status webhooks, sent WhatsApp updates through
      Oblion, and stored third-party credentials with AES-256-GCM encryption.
    tech:
    - Next.js 16
    - React 19
    - TypeScript
    - PostgreSQL
    - Tailwind CSS
    - Shiprocket API
    - Razorpay
    - AES-256-GCM
  - name: Client Onboarding Portal
    description: 'Operator tool that provisions a client and all of its WhatsApp agents (booking, storefront, or both) in
      a single all-or-nothing transaction: client, agents, subscription limits, WhatsApp status, intake questions, seeded
      slots, storefronts and optional Shiprocket config either all land or none do; failures name the module that broke.'
    tech:
    - React 18
    - Vite
    - shadcn/ui
    - Node.js
    - Express.js
    - PostgreSQL
    - Zod
    - Nodemailer
  - name: AIORA Agent Router (n8n)
    description: 'n8n-driven conversation layer letting one WhatsApp number serve multiple bots: a Redis-backed router greets
      the customer, offers a menu when a business runs more than one bot, and hands off to AI-agent workflows (OpenAI chat
      model, per-agent Redis memory) that run the booking or shopping conversation end to end.'
    tech:
    - n8n
    - OpenAI
    - Redis
    - WhatsApp
  - name: Orbit
    description: Express utility service that aggregates health across all AIORA services via GET /api/health/all and scrapes
      the OpenAI account balance with Playwright for billing visibility.
    tech:
    - Node.js
    - Express.js
    - Playwright
    - PM2
  - name: Gluzo
    description: Cloud-native AWS application using Lambda, API Gateway, DynamoDB, IAM, CloudWatch, Secrets Manager, and EC2
      for serverless backend operations.
    tech:
    - AWS Lambda
    - API Gateway
    - DynamoDB
    - IAM
    - CloudWatch
    - Python
  additional_responsibilities:
  - WhatsApp automation for customer communication and onboarding
  - REST API design with FastAPI and Express.js
  - PostgreSQL and MongoDB management and query optimisation
  - Multi-tenant platform design (shared WhatsApp numbers, multi-agent routing)
  - Multi-environment VPS deployment (dev/SIT/prod) with systemd, PM2, nginx and isolated Postgres/Redis
  - IAM, Secrets Manager, CloudWatch configuration on AWS
  - Mentoring interns (code review, architecture guidance)
  - Voice AI with Sarvam (speech recognition, text-to-speech, LLM tool calling) in English and Tamil
---

# Junior Software Developer

Designing and maintaining AIORA, a multi-tenant WhatsApp commerce platform spanning 13 microservices for bookings, e-commerce, document validation, payments, logistics, and AI interactions. Work covers Node.js/TypeScript and Python APIs, concurrent messaging sessions, Redis queues, OCR and GPT-4o Vision, PostgreSQL usage tracking, Razorpay and Shiprocket integrations, n8n workflows, and production deployment on Ubuntu VPS and Railway.

Also built Kural, a multi-tenant AI customer-care voice platform on Sarvam AI (English and Tamil, tenant-isolated tools, guardrails and escalation), and contributed to CMO Copilot, a marketing-analytics agent whose answers are validated against the underlying query results.
