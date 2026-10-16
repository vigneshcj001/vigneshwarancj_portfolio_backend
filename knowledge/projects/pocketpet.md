---
type: "concept"
title: "PocketPet"
tags: ["project","Rust","Tauri","JavaScript","React.js","TypeScript","Vite","Tailwind CSS","Tokio","Win32"]
source: "portfolio_data.json#projects/PocketPet"
---

# PocketPet

- **Type:** Desktop / Agentic AI

- **Subtitle:** Desktop Companion, AI Browser Agent + Download Website

- **Description:** One cross-platform product comprising a Tauri 2/Rust desktop companion and its React 19/TypeScript download website. The desktop app provides JavaScript/SVG pets, games, customisation, break reminders, and a streamed task agent that searches, reads pages, and controls a dedicated Chromium profile via CDP. It supports Anthropic and OpenAI-compatible providers including Ollama, with approval gates, secret-field refusal, spend limits, scheduling, and cancellation. The website reuses the app's sprites as an interactive demo, explains platform support, reads GitHub Releases, and directs visitors to the correct Windows, macOS, or Linux download. Win32/UI Automation window tricks are Windows-only; macOS and Linux provide reduced features.

## Tech Stack

- Rust
- Tauri
- JavaScript
- React.js
- TypeScript
- Vite
- Tailwind CSS
- Tokio
- Win32
- Chrome DevTools Protocol
- Agentic AI
- GitHub API
- GitHub Actions
- Vercel

- **Live Link:** https://pocketpet-web.vercel.app/

- **Github:** https://github.com/vigneshcj001/Pocketpet

- **Github Website:** https://github.com/vigneshcj001/Pocketpet-web

- **Website Role:** Official product website and application download surface; it is part of PocketPet, not a separate project.

- **Limitations:** macOS overlay covers one display; Linux click-through requires X11/XWayland. Approval detection is heuristic, not a guarantee against every sensitive action. OS keychain storage has a restricted-permission file fallback on Linux when no keyring is available. Website downloads fall back to GitHub Releases when direct asset discovery is unavailable.
