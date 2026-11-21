# Bolta Khata AI — बोलता खाता AI

> **Voice-first digital ledger for Indian kirana shopkeepers.**  
> Record credit/debit transactions by speaking in Hindi or regional languages.

---

## Table of contents

1. [Project overview](#project-overview)
2. [Tech stack](#tech-stack)
3. [Prerequisites](#prerequisites)
4. [Quick start — Backend](#quick-start--backend)
5. [Quick start — Frontend](#quick-start--frontend)
6. [Running tests](#running-tests)
7. [Project structure](#project-structure)
8. [Environment variables](#environment-variables)
9. [Roadmap](#roadmap)

---

## Project overview

Bolta Khata AI lets a kirana shopkeeper say *"Ramesh ne 500 rupaye liye"*
("Ramesh took ₹500") and have the transaction recorded automatically, with
the balance read back in the shopkeeper's language.

**Current phase: B0 — initial scaffold. No ledger, auth, or AI features yet.**

---

## Tech stack

| Layer        | Technology                        |
|--------------|-----------------------------------|
| Frontend     | React 18 + Vite 6 + TypeScript    |
| Backend      | Python FastAPI + Uvicorn          |
| Database     | SQLite (Python built-in `sqlite3`)|
| AI *(later)* | Google Gemini Flash               |
| STT *(later)*| GNANI Prisma                      |
| TTS *(later)*| GNANI Timbre                      |
| Wake word *(later)* | Picovoice Porcupine        |

---

## Prerequisites

| Tool        | Minimum version | Check command          |
|-------------|-----------------|------------------------|
| Node.js     | 18+             | `node --version`       |
| npm         | 9+              | `npm --version`        |
| Python      | 3.10+           | `python --version`     |
| Git         | any             | `git --version`        |

---

## Quick start — Backend

```bash
# 1. Enter the backend folder
cd backend

# 2. Create a Python virtual environment
python -m venv venv

# 3. Activate it
#    Windows (PowerShell):
.\venv\Scripts\Activate.ps1
#    macOS / Linux:
source venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Copy environment template
cp ../.env.example ../.env
#    (then open .env and fill in your real API keys)

# 6. Start the development server
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The API will be available at **http://127.0.0.1:8000**  
Interactive docs: **http://127.0.0.1:8000/docs**  
Health check: **http://127.0.0.1:8000/api/health**

---

## Quick start — Frontend

```bash
# 1. Enter the frontend folder
cd frontend

# 2. Install dependencies
npm install

# 3. Start the Vite dev server
npm run dev
```

The UI will be available at **http://localhost:5173**

> The frontend expects the backend running at `http://127.0.0.1:8000` by default.
> Override with `VITE_API_BASE_URL` in a `frontend/.env.local` file.

---

## Running tests

### Backend tests

```bash
# From the repo root (with venv active):
pytest tests/backend/ -v
```

### Frontend tests *(coming in a later phase)*

```bash
cd frontend
npm run test
```

---

## Project structure

```
voice-khata-ai/
├── frontend/
│   ├── src/
│   │   ├── components/     # Shared UI components
│   │   ├── pages/          # Page-level components
│   │   ├── voice/          # Voice pipeline (STT, TTS, wake word — placeholders)
│   │   ├── services/       # API client
│   │   └── assets/         # Static assets
│   ├── index.html
│   ├── vite.config.ts
│   └── package.json
│
├── backend/
│   ├── app/
│   │   ├── api/            # FastAPI route handlers
│   │   ├── ai/             # Gemini integration (placeholder)
│   │   ├── speech/         # GNANI STT / TTS (placeholder)
│   │   ├── services/       # Business logic
│   │   ├── database/       # SQLite connection helpers
│   │   └── main.py         # App entry point
│   └── requirements.txt
│
├── docs/
│   └── contracts.md        # Shared API contracts (frontend ↔ backend)
│
├── tests/
│   └── backend/
│       └── test_health.py
│
├── .env.example
├── .gitignore
├── AGENTS.md
└── README.md
```

---

## Environment variables

Copy `.env.example` → `.env` and fill in values. **Never commit `.env`.**

| Variable               | Description                            |
|------------------------|----------------------------------------|
| `GEMINI_API_KEY`       | Google Gemini API key                  |
| `GNANI_STT_API_KEY`    | GNANI Prisma STT key                   |
| `GNANI_TTS_API_KEY`    | GNANI Timbre TTS key                   |
| `PICOVOICE_ACCESS_KEY` | Picovoice Porcupine key                |
| `DATABASE_PATH`        | SQLite file path (default `./khata.db`)|
| `CORS_ORIGINS`         | Comma-separated allowed frontend URLs  |

---

## Roadmap

- [x] B0 — Project scaffold (frontend + backend + health check)
- [ ] B1 — Database schema (customers, transactions)
- [ ] B2 — Ledger CRUD API
- [ ] B3 — Gemini AI intent parsing
- [ ] B4 — GNANI STT integration
- [ ] B5 — GNANI TTS integration
- [ ] B6 — Picovoice wake-word detection
- [ ] B7 — WhatsApp reminder integration
