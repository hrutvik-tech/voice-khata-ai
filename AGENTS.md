# Bolta Khata — rules for every coding agent

Bolta Khata is a voice ledger website for kirana shops: React (Vite,
JavaScript) in /frontend,
Python FastAPI in /backend. The full contracts are in docs/contracts.md.

## Always
1. Read docs/contracts.md before planning. Event names, routes, function
signatures, table
columns, settings and constants come only from it.
2. Show an implementation plan and wait for approval before writing code.
3. Edit only the files the prompt names. Never edit another member's files
(owners are listed
in docs/contracts.md). Never edit docs/contracts.md or AGENTS.md.
4. Never change a function signature, event name, route, column or constant.
If one seems
wrong, stop and say so instead of working around it.
5. Read secrets only from environment variables. Never hardcode, print or log
a key. Never
commit a .env file.
6. For Gnani and Gemini, use only the endpoints, headers, parameters and
message fields written
in docs/vendor/. If something isn't documented there, stop and ask. Never
guess.
7. Money is integer paise everywhere. Never use floats for money.
8. The language model only proposes operations. It never writes to the
database, never
converts amounts to numbers and never calculates balances or dates.
9. Never use voice cloning. Use Gnani's stock voices only.
10. Every change ships with tests. Run them and report the exact command and
its output.
11. Do not add dependencies; everything needed is already installed. If
something is truly
missing, stop and ask.
12. Keep code simple and readable. No unrelated refactors, no extra layers of
abstraction.
13. No reminders, lending, interest or pressure language anywhere in the
product.

## Commands
- Backend setup: cd backend && python -m venv .venv && activate it && pip install -r requirements.txt
- Backend run: cd backend && uvicorn app.main:app --reload
- Backend tests: cd backend && pytest -q
- Frontend setup and run: cd frontend && npm install && npm run dev
- Frontend tests: cd frontend && npm test
