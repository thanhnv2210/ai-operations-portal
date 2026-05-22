# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI Operations Portal — an AI-assisted operational intelligence platform for enterprise transactional systems with natural language analytics and decision support. Targets fintech/remittance/BPM domains.

## Planned Architecture

This project is in the initial setup phase. The repository structure follows a monorepo with three main services:

```
frontend/       # React + Vite + TailwindCSS + shadcn/ui
backend/        # Spring Boot (Java 21) monolith with modular package structure
ai-service/     # Python FastAPI for AI/LLM integration
database/       # PostgreSQL schema, migrations, seeds
infrastructure/ # Docker Compose, deployment configs
docs/           # Architecture, API docs, prompt engineering
```

## Tech Stack

**Frontend:** React, Vite, TailwindCSS, shadcn/ui, React Query

**Backend:** Java 21, Spring Boot, PostgreSQL (Neon), Redis

**AI Service:** Python FastAPI, OpenAI API (Ollama later), Spring AI integration (later)

**Infrastructure:** Docker Compose, Vercel (frontend), Render/Railway (backend + AI service), Neon (DB)

## Backend Package Structure

Backend uses domain-module organization under `com.company.aiportal`:

```
modules/
  auth/         # controller, service, repository, entity, dto, mapper
  dashboard/
  transaction/
  alert/
  audit/
  analytics/
  ai/
  settings/
common/         # config, exception, security, utils, constants, logging
integration/    # openai, database, cache, external
scheduler/
```

## Key Modules / Features

1. **Operational Dashboard** — transaction counts, failures, processing time, alert metrics
2. **AI Assistant** — natural language queries over operational data
3. **Transaction Explorer** — filtering, search, audit timeline, status tracking
4. **AI Insights Engine** — summaries, anomaly explanations, recommendations, trend observations
5. **Admin Configuration** — AI prompts, thresholds, alert rules

## Development Strategy

- **Phase 1 (MVP):** `frontend/` + `backend/` + `database/` + `docker-compose.yml` only. Skip Kubernetes, RAG, embeddings, advanced monitoring.
- **Phase 2:** Add `ai-service/`, prompts engineering, analytics, AI summaries.
- **Phase 3:** Event-driven (Kafka), vector DB, AI agents, microservice extraction.

Start with prompt-based LLM intelligence (no ML training). Use LLMs to summarize, explain anomalies, and generate operational insights.

## Commands (to be added as services are scaffolded)

### Frontend
```bash
cd frontend
npm install
npm run dev       # development server
npm run build     # production build
npm run lint
```

### Backend
```bash
cd backend
./gradlew bootRun             # run locally
./gradlew test                # all tests
./gradlew test --tests "com.company.aiportal.modules.SomeTest"  # single test
./gradlew build
```

### AI Service
```bash
cd ai-service
pip install -r requirements.txt
uvicorn app.main:app --reload  # development server
```

### Infrastructure
```bash
docker-compose up -d   # start all services locally
docker-compose down
```
