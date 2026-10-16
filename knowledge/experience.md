---
type: "reference"
title: "Work experience"
tags: ["experience","employment","internship","career"]
source: "portfolio_data.json#work_experience"
---

# Work experience

## Junior Software Developer

- **Role:** Junior Software Developer

- **Company:** Ceiyone Tech Works Pvt. Ltd.

- **Period:** Dec 2025 – Present

- **Type:** Full-time

- **Overview:** Designing and maintaining AIORA, a multi-tenant WhatsApp commerce platform spanning 13 microservices for bookings, e-commerce, document validation, payments, logistics, and AI interactions. Work covers Node.js/TypeScript and Python APIs, concurrent messaging sessions, Redis queues, OCR and GPT-4o Vision, PostgreSQL usage tracking, Razorpay and Shiprocket integrations, n8n workflows, and production deployment on Ubuntu VPS and Railway.

### Projects

#### Bullion Handler

- **Name:** Bullion Handler

- **Description:** FastAPI service that reads gold-shipment AWB and invoice PDFs with GPT-4o vision, then runs a two-stage rules engine — Stage 1 checks the invoice alone (weight, purity, calculations), Stage 2 compares it against its matched AWB — and produces bilingual EN/ES PDF reports delivered by email. PostgreSQL for records, Redis Streams/Pub-Sub for job pickup and SHA-256 dedup.

##### Tech

- Python
- FastAPI
- OpenAI GPT-4o
- PostgreSQL
- Redis
- ReportLab
- systemd

#### Bullion Listener

- **Name:** Bullion Listener

- **Description:** Node.js WhatsApp bot bridging group chats and Bullion Handler: saves incoming PDFs to the shared filesystem, hands them to the Python service via HTTP/n8n, and watches report directories with chokidar to deliver finished reports back to the originating group.

##### Tech

- Node.js
- whatsapp-web.js
- Chokidar
- Redis
- PM2

#### Splendor

- **Name:** Splendor

- **Description:** Express 5 REST API that meters AI token consumption and subscription quotas per client/agent, enforces plan limits, and fires low-balance WhatsApp alerts through Oblion with a 4-hour cooldown. OpenAPI docs at /api-docs.

##### Tech

- Node.js
- Express.js
- PostgreSQL
- Joi
- Winston
- Swagger/OpenAPI
- Docker
- PM2

#### Oblion

- **Name:** Oblion

- **Description:** Multi-number WhatsApp gateway: one whatsapp-web.js session per business number, BullMQ-queued outbound sends with retries and a dead-letter queue, HMAC-signed inbound webhooks feeding n8n.

##### Tech

- TypeScript
- Node.js
- Express.js
- BullMQ
- Redis
- PostgreSQL
- WhatsApp Web API
- n8n

#### meridian-api

- **Name:** meridian-api

- **Description:** Shared service layer every AIORA WhatsApp conversation runs through: slot availability, bookings, operator-authored intake questions, per-agent bot configuration, broadcast campaigns, document ingest, and the single outbound /send endpoint that formats every WhatsApp reply.

##### Tech

- Node.js
- Express.js
- PostgreSQL
- Joi
- Winston

#### Meridian

- **Name:** Meridian

- **Description:** Customer-facing appointment booking page, pre-filled from WhatsApp, backed by meridian-api for slots and intake questions. Recently integrated Healthora's dietician-appointment booking flow into Meridian, consolidating both products onto one booking experience.

##### Tech

- React 19
- Vite
- Tailwind CSS

#### polaris-ui

- **Name:** polaris-ui

- **Description:** Business-owner dashboard fanning out to four backends (healthora-api, meridian-api, Oblion, ecomm-api): bookings, orders, inventory, bot settings, document uploads, broadcast campaigns, WhatsApp session status, a Shiprocket connection page, and a home dashboard of revenue, booking/order status, low-stock and campaign charts. E-commerce calls are proxied server-side so the API key never reaches the browser.

##### Tech

- React 19
- TypeScript
- Vite
- Tailwind CSS
- Axios
- Node.js
- Railway

#### AIORA E-Commerce

- **Name:** AIORA E-Commerce

- **Description:** Next.js multi-store commerce platform with catalogue, order, payment, and shipping workflows. Integrated Razorpay payments and per-client Shiprocket logistics, normalised courier status webhooks, sent WhatsApp updates through Oblion, and stored third-party credentials with AES-256-GCM encryption.

##### Tech

- Next.js 16
- React 19
- TypeScript
- PostgreSQL
- Tailwind CSS
- Shiprocket API
- Razorpay
- AES-256-GCM

#### Client Onboarding Portal

- **Name:** Client Onboarding Portal

- **Description:** Operator tool that provisions a client and all of its WhatsApp agents (booking, storefront, or both) in a single all-or-nothing transaction: client, agents, subscription limits, WhatsApp status, intake questions, seeded slots, storefronts and optional Shiprocket config either all land or none do; failures name the module that broke.

##### Tech

- React 18
- Vite
- shadcn/ui
- Node.js
- Express.js
- PostgreSQL
- Zod
- Nodemailer

#### AIORA Agent Router (n8n)

- **Name:** AIORA Agent Router (n8n)

- **Description:** n8n-driven conversation layer letting one WhatsApp number serve multiple bots: a Redis-backed router greets the customer, offers a menu when a business runs more than one bot, and hands off to AI-agent workflows (OpenAI chat model, per-agent Redis memory) that run the booking or shopping conversation end to end.

##### Tech

- n8n
- OpenAI
- Redis
- WhatsApp

#### Orbit

- **Name:** Orbit

- **Description:** Express utility service that aggregates health across all AIORA services via GET /api/health/all and scrapes the OpenAI account balance with Playwright for billing visibility.

##### Tech

- Node.js
- Express.js
- Playwright
- PM2

#### Gluzo

- **Name:** Gluzo

- **Description:** Cloud-native AWS application using Lambda, API Gateway, DynamoDB, IAM, CloudWatch, Secrets Manager, and EC2 for serverless backend operations.

##### Tech

- AWS Lambda
- API Gateway
- DynamoDB
- IAM
- CloudWatch
- Python

### Additional Responsibilities

- WhatsApp automation for customer communication and onboarding
- REST API design with FastAPI and Express.js
- PostgreSQL and MongoDB management and query optimisation
- Multi-tenant platform design (shared WhatsApp numbers, multi-agent routing)
- Multi-environment VPS deployment (dev/SIT/prod) with systemd, PM2, nginx and isolated Postgres/Redis
- IAM, Secrets Manager, CloudWatch configuration on AWS
- Mentoring interns (code review, architecture guidance)

## AI Engineer Intern

- **Role:** AI Engineer Intern

- **Company:** Ceiyone Tech Works Pvt. Ltd.

- **Period:** Oct 2025 – Dec 2025

- **Type:** Internship

- **Overview:** Built AI-powered automation solutions, OCR-based document systems, LinkedIn automation tools, and multi-agent LLM systems. Integrated AI services, external APIs, and workflow automation platforms.

### Projects

#### AI Weather Agent

- **Name:** AI Weather Agent

- **Description:** Telegram bot answering weather queries via text and voice using OpenAI NLU, real-time weather APIs, and voice-to-text/TTS pipelines.

##### Tech

- Python
- Telegram Bot API
- OpenAI
- Weather APIs

#### LinkedIn Automation Platform

- **Name:** LinkedIn Automation Platform

- **Description:** Automated LinkedIn profile analytics, post scraping, engagement tracking, competitor research, and AI content generation via n8n and Apify.

##### Tech

- Apify
- n8n
- Gemini
- Python

#### LinkedIn Content Creation Agent

- **Name:** LinkedIn Content Creation Agent

- **Description:** End-to-end AI pipeline: topic research → content drafting → SEO optimisation → hashtag generation → publishing workflow.

##### Tech

- n8n
- Gemini
- Python

#### SEO DeepAgent

- **Name:** SEO DeepAgent

- **Description:** Automated SEO audit pipelines: competitor analysis, keyword research, traffic insights, AI-generated recommendations using Serpstat.

##### Tech

- DeepAgent
- Serpstat
- OpenAI
- Python

#### Multi-Agent Financial AI

- **Name:** Multi-Agent Financial AI

- **Description:** Multi-agent system for financial analysis and report generation using Groq LLaMA models orchestrated with the Phi Framework.

##### Tech

- Groq LLaMA
- Phi Framework
- Python

#### Business Card OCR System

- **Name:** Business Card OCR System

- **Description:** Automated pipeline for business card OCR extraction, contact validation, MongoDB storage, and CSV export with FastAPI backend and Streamlit UI.

##### Tech

- FastAPI
- MongoDB
- Streamlit
- Tesseract OCR

## Research Intern

- **Role:** Research Intern

- **Company:** Manipal Institute of Technology

- **Period:** Jun 2024 – Jul 2024

- **Duration:** 2 mos

- **Type:** Internship

- **Location:** Karnataka, India · On-site

- **Supervisor:** Dr. Neha Sureshchandra Gandhi

- **Research Area:** Quantitative Structure Activity Relationship (QSAR) & Quantitative Structure Property Relationship (QSPR)

- **Overview:** Built QSPR models for Posaconazole solubility in SEDDS formulations using RDKit descriptors, VIF-based feature reduction, and regression model comparison; reported R²=0.926.

### Project

- **Name:** Development of QSPR Models for Self-Emulsifying Drug Delivery System (SEDDS) of Posaconazole

- **Description:** Built ML models predicting drug solubility in SEDDS formulations from molecular descriptors. Dataset consisted of oils, surfactants, co-surfactants, and drug compositions.

#### Results

- **Reported Performance:** R² = 0.926

#### Tech

- Python
- RDKit
- Scikit-Learn
- Random Forest
- PLS
- Linear Regression
- SVM
- KNN
- Mordred

### Impact

- Reduced dependence on costly and time-consuming laboratory formulation screening
- Demonstrated practical application of AI and ML in pharmaceutical research
- Built interpretable predictive framework for estimating drug solubility using molecular descriptors
- Proposed future web-based recommendation system for suggesting optimal SEDDS formulations

## Tutor

- **Role:** Tutor

- **Company:** Kamakshi Tuition Centre

- **Period:** Jan 2023 – Jun 2023

- **Duration:** 6 mos

- **Type:** Part-time

- **Location:** Mugalivakkam, Chennai · On-site

- **Overview:** Taught mathematics to 9th grade students and Python programming to 12th grade students at Kamakshi Tuition Centre, Mugalivakkam Arasa Maram.
