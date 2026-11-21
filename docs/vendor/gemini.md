# docs/vendor/gemini.md — Gemini API (Member 3)

Vendor reference for the LLM interpreter. Per AGENTS.md rule 6, the interpreter's
endpoint, model ID and request shape come **only** from this file. Copy the exact model
ID from AI Studio's "Get code" button before relying on it — model names change.

Source: https://ai.google.dev/gemini-api/docs (models, structured-output, rate-limits),
read 2026-11-21.

---

## Model

- **Model ID:** `gemini-3.5-flash-lite`
- Fastest, lowest-cost model in the 3.5 family; GA and production-ready.
- **Do not use `gemini-2.5-flash-lite`** — the 2.5 models were shut down in October 2026.
- Fallback if Flash-Lite struggles with Hindi/Kannada parsing: `gemini-3.6-flash`
  (smarter, slower, pricier).

Always confirm the current ID in AI Studio → type a prompt → **Get code** (Python) →
copy the string after `model=`. The dropdown display name ("Gemini 3.5 Flash-Lite") is
NOT the API ID.

---

## SDK

- Package: **`google-genai`** (`pip install google-genai`).
- Import: `from google import genai`
- Client: `client = genai.Client()` — reads the key from the `GEMINI_API_KEY`
  environment variable. Never hardcode the key; it lives in `backend/.env`.

---

## Structured JSON output

To get a guaranteed-valid JSON object (not just a hint), the request **must set both**
`response_mime_type` AND `response_schema`. Setting the mime type alone is only a strong
hint and can still return malformed JSON.

The SDK accepts a **Pydantic** model's JSON schema directly, so we reuse our contract
models. The model emits fields in the same order as the schema keys.

```python
from google import genai
from app.schemas.contracts import Interpretation   # our Pydantic model

client = genai.Client()

response = client.models.generate_content(
    model="gemini-3.5-flash-lite",
    contents=prompt,                    # SYSTEM_PROMPT + few-shot + transcript
    config={
        "response_mime_type": "application/json",
        "response_schema": Interpretation.model_json_schema(),
        "thinking_level": "low",        # low = fast; do NOT use "minimal"
    },
)

result = Interpretation.model_validate_json(response.text)
```

Notes:
- `thinking_level: "low"` keeps latency down. **Avoid `"minimal"`** — on the 3.5 family
  it can cut off multi-step work; `low` is the safe fast setting for our single-call
  extraction.
- All JSON-Schema fields are optional unless marked `required` in the schema. Mark the
  fields the ledger depends on (intent) as required in the Pydantic model.
- The LLM returns `amount_spoken`, `customer_name`, `direction`, `date_expression`,
  `intent`, `confidence`. It must **not** compute `amount_paise` or `business_date` —
  those come from our own `number_parser` and `shop_clock` (rule 8).

---

## Rate limits (free tier)

Measured per **project** (not per key), across three dimensions:
- **RPM** — requests per minute
- **TPM** — tokens per minute (input)
- **RPD** — requests per day (resets midnight Pacific time)

The exact free-tier numbers change and are shown live for your project at
**https://aistudio.google.com/rate-limit** — read them there; do not hardcode a number.
Flash-Lite is one of the free-tier models.

Implications for our build:
- A 429 `RESOURCE_EXHAUSTED` error = rate limited. Handle it: our interpreter already
  retries once on failure (4 s timeout, then `fallback`); on a 429 it falls back to the
  fast path / "not understood" rather than crashing.
- During the demo, only one phone drives the LLM, so free-tier RPM is ample. In testing,
  if all four members hammer the same key, you may hit RPM — space out test runs or use
  separate keys/projects.

---

## Endpoints reference

- Models list: https://ai.google.dev/gemini-api/docs/models
- Structured output: https://ai.google.dev/gemini-api/docs/generate-content/structured-output
- Rate limits: https://ai.google.dev/gemini-api/docs/rate-limits
- Your live limits: https://aistudio.google.com/rate-limit

---

## Do / don't

- DO read the key from env; DO set both mime type and schema; DO keep `thinking_level`
  at `low`; DO parse the response back through the Pydantic model.
- DON'T use a 2.x model; DON'T let the LLM produce paise or dates; DON'T hardcode the
  key or the rate-limit numbers; DON'T use `thinking_level: "minimal"`.
