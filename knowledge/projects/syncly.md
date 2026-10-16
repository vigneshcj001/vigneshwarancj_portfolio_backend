---
type: "concept"
title: "Syncly"
tags: ["project","React 19","Vite","Redux Toolkit","React Router 7","Tailwind CSS 4","daisyUI","Axios","Node.js","Express 5"]
source: "portfolio_data.json#projects/Syncly"
---

# Syncly

- **Type:** Full-Stack Web Application

- **Subtitle:** Developer Networking Platform

- **Description:** Developer-to-developer networking platform built solo end to end. Members pick a mentorship role (mentor, learner, both), swipe a paginated feed of developers they have not met (Vibe to connect, Ghost to pass); the recipient replies Link or Noped, and a mutual Link unlocks real-time 1:1 chat over Socket.IO with persisted history. Each member gets a shareable portfolio page at their slug (projects, experience, education, certifications, theme, SEO, visibility). httpOnly JWT cookie auth with bcrypt; AWS SES email on every swipe plus a daily 08:00 node-cron reminder for pending Vibes. Loop: Discover → Vibe → Link → Chat → Showcase.

## Tech Stack

- React 19
- Vite
- Redux Toolkit
- React Router 7
- Tailwind CSS 4
- daisyUI
- Axios
- Node.js
- Express 5
- MongoDB
- Mongoose
- Socket.IO
- JWT
- bcrypt
- AWS SES
- node-cron
- AWS EC2

- **Role:** Solo full-stack development: React SPA, REST + WebSocket API, data model, email automation, deployment

- **Github Frontend:** https://github.com/vigneshcj001/Syncly_fronend

## Highlights

- Swipe matchmaking: Vibe/Ghost by initiator, Link/Noped by recipient; one swipe per pair enforced by a unique compound index
- Real-time 1:1 chat via Socket.IO; rooms keyed by SHA-256 of the sorted user-ID pair; history persisted in MongoDB
- No-code portfolio page per user with theme, SEO metadata and visibility flag, served by profile slug
- AWS SES email on each swipe plus a daily 08:00 node-cron reminder for pending Vibes
- httpOnly JWT cookie auth, bcrypt (cost 12), strong-password and URL validation
- Deployed on AWS EC2

- **Note:** Backend repository is private; the original live domain is no longer active.
