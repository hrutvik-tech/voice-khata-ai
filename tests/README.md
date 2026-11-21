# Tests

## Backend tests

```bash
# From the repo root, with the venv active:
pytest tests/backend/ -v
```

Dependencies are installed via `backend/requirements.txt`.
`httpx` is included there — it is the transport used by FastAPI's `TestClient`.

## Frontend tests

Vitest will be configured in a later phase (B2+).
