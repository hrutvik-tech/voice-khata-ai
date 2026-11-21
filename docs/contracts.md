# Contracts, part 1: structure, settings and data

Member 4 pastes this section and the next one into docs/contracts.md before anyone starts. Every name, route, column and constant below is fixed; it changes only at a checkpoint, agreed by all four.

## Repository and owners

```
bolta-khata/
├── AGENTS.md                                                M4 (pasted from this doc)
├── .gitignore, README.md                                    M4
├── docs/contracts.md                                        M4 (pasted from this doc)
├── docs/vendor/gnani-stt.md                                 M2 (official Gnani realtime and REST STT pages)
├── docs/vendor/gnani-tts.md                                 M2 (official Gnani realtime TTS page and voice list)
├── docs/vendor/gemini.md                                    M3 (official structured-output and thinking pages)
├── test_data/audio/                                         M2 (WAV clips + expected.json)
├── test_data/sentences.json                                 M3 (text cases + expected operations)
├── frontend/
│   ├── package.json, vite.config.js, index.html, .env.example M4 in P0, then M1
│   ├── public/porcupine/                                    M2 (suno_munshi.ppn, porcupine_params.pv)
│   ├── src/main.jsx, src/App.jsx                            M1
│   ├── src/pages/                                           M1 Login, Setup, Home, Customers, CustomerProfile, ShopProfile
│   ├── src/components/                                      M1
│   ├── src/store/appStore.js                                M1
│   ├── src/api/rest.js, mockRest.js                         M1
│   ├── src/test/                                            M1 (frontend test setup and M1 tests)
│   └── src/voice/                                           M2 useVoice.js, voiceStore.js, voiceSocket.js, wakeWord.js, frameTap.js, localVad.js, player.js, offlineQueue.js, mockVoice.js, voice.test.js
└── backend/
    ├── requirements.txt, requirements-prod.txt, .env.example M4
    ├── app/main.py                                          M4
    ├── app/core/config.py, tokens.py                        M4
    ├── app/core/crypto.py, retention.py                     M2
    ├── app/db/models.py, session.py, seed.py                M4
    ├── app/schemas/contracts.py                             M4 (shared models; checkpoint-only changes)
    ├── app/api/                                             M4 auth, shop, customers, summary, sync, me, ws, debug
    ├── app/services/                                        M4 providers, ledger, validation, conversation, orchestrator, replies
    ├── app/speech/                                          M2 stt.py, tts.py, number_words.py, stub.py, cli.py
    ├── app/ai/                                              M3 interpreter.py, prompts.py, fast_path.py, number_parser.py, matching.py, shop_clock.py, stub.py, eval.py
    └── tests/                                               conftest.py (M4); m2/, m3/, m4/ (each owner); integration/ (M4)
```

P0 creates every file above (real code for Member 4's files, signatures and stubs for the rest) and installs every dependency, so nobody edits package.json or requirements.txt later.

**Backend dependencies**: fastapi, uvicorn[standard], pydantic, pydantic-settings, sqlalchemy, bcrypt, pyjwt, python-multipart, websockets, httpx, google-genai, openai (only for Gnani Evon's OpenAI-compatible API), rapidfuzz, cryptography, pytest, pytest-asyncio. requirements-prod.txt = -r requirements.txt plus sqlcipher3-binary (Linux only).

**Frontend dependencies**: react, react-dom, react-router-dom, zustand, idb-keyval, @picovoice/porcupine-web, @picovoice/web-voice-processor, tailwindcss with the official Vite plugin, and for tests vitest, jsdom, @testing-library/react, @testing-library/jest-dom.

## Settings

### backend/.env.example :

```env
APP_ENV=dev # dev | prod
DEBUG=true # enables /debug routes and now_override
FRONTEND_ORIGIN=http://localhost:5173
DB_PATH=./data/khata.db
ENCRYPTION_MODE=fernet # fernet (laptops) | sqlcipher (Linux server)
DB_KEY= # Fernet key, or SQLCipher passphrase
JWT_SECRET=
JWT_EXPIRE_DAYS=30
USE_STUB_SPEECH=true # true until checkpoint I-2
USE_STUB_AI=true # true until checkpoint I-2
STUB_TRANSCRIPT=Ramesh Sharma ka 340 udhaar
GNANI_API_KEY=
STT_MODEL=prisma-v3.0
STT_FORMAT=codemix # locked by M2 in hour 0
STT_MIN_SILENCE_MS=350
STT_VAD_THRESHOLD=0.7
TTS_MODEL=timbre-v3.0
TTS_VOICE= # chosen by M2 from Gnani's voice list
TTS_CONTAINER=mp3
LLM_PROVIDER=gemini # gemini | evon
GEMINI_API_KEY=
GEMINI_MODEL= # exact model ID copied from Google AI Studio
EVON_API_KEY= # only if Gnani grants Evon access
TRANSCRIPT_RETENTION_HOURS=48
RUN_LIVE_TESTS=false # true runs tests that call Gnani and Gemini
```

### frontend/.env.example :

```env
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
VITE_USE_MOCK_REST=true # false from checkpoint I-1
VITE_USE_MOCK_VOICE=true # false from checkpoint I-2
VITE_PICOVOICE_ACCESS_KEY= # browser-visible by design
VITE_DEMO_MODE=true # shows the demo-time control
```

Browser storage keys: bk_token (JWT), bk_shop (shop JSON). IndexedDB store for offline turns: bk-offline (Member 2).

## Constants

| Name | Value | Owner |
| :--- | :--- | :--- |
| AMEND_WINDOW_SECONDS | 60 | M4 |
| DUPLICATE_WINDOW_SECONDS | 120 | M4 |
| SESSION_IDLE_MINUTES | 30 | M4 |
| MAX_AMOUNT_PAISE | 100000000 (₹10,00,000) | M4 |
| Outlier rule | at least 3 earlier credits, and amount above 5 × median of the last 10 credits, and above 200000 paise | M4 |
| MIN_CONFIDENCE | 0.6 | M4 |
| Name match: same person | score 90 or more | M3 |
| Name match: similar | score 75 to 89 | M3 |
| Default hours | open 06:00, close 02:00, Asia/Kolkata | M3, M4 |
| Business day | from opening time to the next opening time | M3 |
| Audio frame | 1,024 bytes = 512 samples, 16 kHz, signed 16-bit little-endian mono | M2 |
| Local VAD | end after 600 ms of silence; turn cancelled if no speech within 5 s of the wake word; maximum turn 12 s | M2 |
| Wake-word sensitivity | 0.65 (tune between 0.5 and 0.8) | M2 |
| LLM call | 4 s timeout, 1 retry | M3 |
| Offline queue | at most 20 turns | M2 |

Language codes are `hi`, `kn`, `en`. The shop's `language_mode` is `hi`, `kn`, `en` or `mix`. STT language hints: `hi` → `hi-IN,en-IN` ; `kn` → `kn-IN,en-IN` ; `en` → `en-IN` ; `mix` → `hi-IN,kn-IN,en-IN` . Reply language: the detected language of the speech, otherwise the shop's language (`mix` falls back to `hi`).

## Seed data (the demo shop)

Shop: owner "Sharma", shop "Sharma Kirana Store", phone 9000000001, PIN 1234, 06:00 to 02:00, language `mix`, setup complete.

| Customer | Area | Seed credit (dated 7 business days before "now", 18:00) |
| :--- | :--- | :--- |
| Ramesh Sharma | Gandhi Nagar | 50000 paise (₹500) |
| Ramesh Gupta | Station Road | 80000 paise (₹800) |
| Suresh | — | 25000 paise (₹250) |
| Amit | — | none (₹0) |

## Data model (SQLAlchemy 2, SQLite)

| Table | Columns |
| :--- | :--- |
| `shops` | id (int, pk); owner_name; shop_name; phone (unique, 10 digits); pin_hash; open_time ("HH:MM"); close_time ("HH:MM"); timezone (default "Asia/Kolkata"); language_mode; setup_complete (bool, default false); created_at |
| `customers` | id; shop_id (fk); name; name_key (normalized by M3's `normalize_name`); phone (nullable, encrypted text); area (nullable); source ("voice" or "manual"); created_at |
| `transactions` | id; shop_id; customer_id (fk); amount_paise (int, check > 0); direction ("credit" or "payment"); business_date (date); recorded_at (timezone-aware datetime, stored as UTC); status ("active" or "undone"); source ("voice", "offline" or "seed"); language (nullable); raw_transcript (nullable, encrypted text); session_id (nullable); idempotency_key (unique); created_at |
| `correction_history` | id; transaction_id (fk); action ("amend" or "undo"); old_amount_paise; new_amount_paise (nullable); session_id; at |
| `conversation_sessions` | id (uuid string, pk); shop_id; state; last_txn_id (nullable); last_txn_at (nullable); pending_json (nullable text); disclosed (bool, default false); last_language (nullable); expires_at; updated_at |

Balance = sum of active credits minus sum of active payments for that customer. It is calculated on every read and never stored. Today means `business_date` equals the business date of "now". An amendment changes `amount_paise` on the same row and writes a `correction_history` row; an undo sets `status` to "undone" and writes a `correction_history` row.

---

# Contracts, part 2: how the parts talk

These are the only connection points between members. Code to them exactly.

## WebSocket `/ws?token=<JWT>`

One connection while Home is open. Text frames are JSON; binary frames are audio. One turn runs at a time; a `turn_start` received during a turn is ignored.

### Website → backend:

```json
{"type":"turn_start","turn_id":"<uuid>","now_override":null}
```
`now_override` = ISO datetime, honoured only when `DEBUG=true`

`<binary frames: exactly 1,024 bytes of PCM each>`

```json
{"type":"commit","turn_id":"<uuid>"}
{"type":"cancel","turn_id":"<uuid>"}
{"type":"choose","turn_id":"<uuid>","choice":{"customer_id":2}} // for choose_customer
{"type":"choose","turn_id":"<uuid>","choice":{"answer":"yes"}} // yes | no | credit | payment
{"type":"ping"}
```

### Backend → website:

```json
{"type":"ready","session_id":"<uuid>","shop_id":1}
{"type":"state","state":"resting"} // resting | listening | understanding | asking | speaking
{"type":"heard","turn_id":"..","text":"Ramesh Sharma ka 340 udhaar","language":"hi"}
{"type":"entry","turn_id":"..","entry":{"id":41,"customer_id":1,"customer_name":"Ramesh Sharma","amount_paise":34000,"direction":"credit","business_date":"2026-11-21","recorded_at":"2026-11-21T19:00:00+05:30","status":"new","old_amount_paise":null,"language":"hi"},"balance_paise":84000,"new_customer":false} // status: new | amended | undone
{"type":"question","turn_id":"..","kind":"choose_customer","say":"..","options":[{"id":"1","label":"Ramesh Sharma"},{"id":"2","label":"Ramesh Gupta"}]}
{"type":"not_understood","turn_id":"..","say":".."}
{"type":"answer","turn_id":"..","kind":"entry_saved","say":"..","data":{}}
{"type":"audio_start","turn_id":"..","format":"mp3"}
// <binary audio chunks>
{"type":"audio_end","turn_id":".."}
{"type":"error","turn_id":"..","code":"stt_failed","say":".."} // stt_failed | llm_failed | tts_failed | unauthorized | bad_message
{"type":"not_saved","turn_id":"..","text":"..","say":".."} // only from /sync/audio
{"type":"pong"}
```

| Question kind | Options | Choice sent back |
| :--- | :--- | :--- |
| `choose_customer` | one per candidate, id = customer id, label = name (+ area if names are identical) | `{"customer_id": N}` |
| `confirm_similar` | yes (label "Haan, <name>"), no (label "Naya grahak") | `{"answer": "yes"}` or `no` |
| `confirm_amount`, `confirm_duplicate`, `confirm_amend`, `confirm_undo` | yes ("Haan"), no ("Nahi") | `{"answer": "yes"}` or `no` |
| `confirm_direction` | credit ("Udhaar"), payment ("Jama") | `{"answer": "credit"}` or `payment` |

| Answer kind | data |
| :--- | :--- |
| `entry_saved` | `{"count": N}` |
| `balance` | `{"customer_id", "customer_name", "balance_paise"}` |
| `daily_total` | `{"business_date", "credit_paise"}` |
| `day_summary` | `{"business_date", "credit_paise", "payment_paise", "top": [{"customer_id", "customer_name", "balance_paise"}]}` (top 3 positive balances) |
| `cancelled`, `info` | `{}` |

**Turn order (backend)**: `turn_start` → state `listening` → open STT → forward frames → `commit` (or STT end of speech) → state `understanding` → `heard` → zero or more `entry` → **exactly one** final message: `answer`, `question`, `not_understood` or `error` → if it has `say`: state `speaking`, `audio_start`, `audio`, `audio_end` → state `asking` (after a question) or `resting`. A `choose` runs the same path from "zero or more entry". An empty transcript gives `not_understood`.

## REST

JSON everywhere. Every route except `/health` and `/auth/register`, `/auth/login` needs `Authorization: Bearer <JWT>`. Errors are `{"detail": "..."}` with status 400, 401, 404, 409 or 422.

- `GET /health` -> `{"ok": true}`
- `POST /auth/register` `{"owner_name","phone","pin"}` -> 201 `{"token","shop"}` (409 if phone exists)
- `POST /auth/login` `{"phone","pin"}` -> `{"token","shop"}` (401 on wrong PIN)
- `PUT /auth/pin` `{"old_pin","new_pin"}` -> 204 (401 on wrong old PIN)
- `GET /shop` -> `shop`
- `PUT /shop` `{"shop_name","open_time","close_time","language_mode"}` -> `shop` (sets `setup_complete=true`)
- `GET /customers?search=` -> `[{"id","name","phone","area","balance_paise","last_activity_at"}]` newest activity first
- `POST /customers` `{"name","phone":null,"area":null,"confirm":false}` -> 201 `{"customer"}` or 409 `{"detail":"similar_exists","similar":[{"id","name","area"}]}` (resend with `"confirm": true` to create anyway)
- `GET /customers/{id}` -> `{"customer","balance_paise","entries":[entry fields + "source" + "history": [{"action","old_amount_paise","new_amount_paise","at"}]]}` newest first, undone entries included
- `GET /summary/today` -> `day_summary data`
- `POST /sync/audio` multipart: audio (WAV, 16 kHz mono), idempotency_key, recorded_at (ISO) -> `{"turn_id","events":[...]}` no audio; any question becomes `not_saved`
- `DELETE /me` -> 204 (deletes the shop and every row that belongs to it)
- `POST /debug/turn` `{"text","now":null,"session_id":null}` -> `{"session_id","turn_id","events":[...]}` DEBUG only
- `POST /debug/choose` `{"session_id","turn_id","choice","now":null}` -> `{"events":[...]}` DEBUG only
- `POST /debug/reset` `{"now":null}` -> 204 (deletes and reseeds the demo shop) DEBUG only

`shop` = `{"id","owner_name","shop_name","phone","open_time","close_time","timezone","language_mode","setup_complete"}`. Debug events are the JSON messages the WebSocket would send, except state and audio messages. Debug routes also need the JWT.

## Python interfaces (`app/schemas/contracts.py` and module signatures)

```python
Lang = Literal["hi", "kn", "en"]
Intent = Literal[
    "CREATE_TRANSACTION", "CORRECTION", "UNDO_LAST",
    "QUERY_BALANCE", "QUERY_DAILY_TOTAL", "QUERY_DAY_SUMMARY",
    "CONFIRM", "CHOOSE_CUSTOMER", "UNKNOWN"
]

class Transcript(BaseModel):
    text: str
    language: Lang | None = None
    latency_ms: int | None = None

class ShopInfo(BaseModel):
    shop_id: int
    open_time: str
    close_time: str
    timezone: str
    language_mode: Literal["hi", "kn", "en", "mix"]

class CustomerRef(BaseModel):
    id: int
    name: str
    area: str | None = None
    phone: str | None = None
    recent_count: int = 0  # active entries in the last 30 days
    last_activity_at: datetime | None = None

class EntryRef(BaseModel):
    id: int
    customer_id: int
    customer_name: str
    amount_paise: int
    direction: Literal["credit", "payment"]
    recorded_at: datetime

class PendingQuestion(BaseModel):
    kind: str
    turn_id: str
    options: list[dict]
    about: dict = {}

class Context(BaseModel):
    shop: ShopInfo
    customers: list[CustomerRef]
    last_entry: EntryRef | None = None
    pending_question: PendingQuestion | None = None
    now: datetime

class Operation(BaseModel):
    intent: Intent
    customer_name: str | None = None
    amount_spoken: str | None = None  # words or digits exactly as heard
    amount_paise: int | None = None  # set only by number_parser, never by the LLM
    amount_check: Literal["ok", "mismatch", "unparsed", "none"] = "none"
    direction: Literal["credit", "payment"] | None = None
    date_expression: str | None = None  # "kal", "parso", "ninne", "yesterday" ... or None
    business_date: date | None = None  # set only by shop_clock
    choice: str | None = None  # CONFIRM: yes/no/credit/payment; CHOOSE_CUSTOMER: spoken words
    confidence: float = 1.0

class Interpretation(BaseModel):
    operations: list[Operation]
    source: Literal["fast_path", "llm", "fallback"]
    language: Lang

class Candidate(BaseModel):
    customer_id: int
    name: str
    area: str | None = None
    score: float
```

### Module signatures

```python
# Member 2 — app/speech/stt.py
class SttSession:
    def __init__(self, lang_hints: list[str], keyterms: list[str]): ...
    async def open(self) -> None: ...
    async def send(self, frame: bytes) -> None: ...  # raises ValueError unless len(frame) == 1024
    async def commit(self) -> None: ...
    async def result(self, timeout: float = 6.0) -> Transcript: ...  # raises SttError
    async def close(self) -> None: ...

async def transcribe_file(wav_bytes: bytes, lang_hints: list[str], keyterms: list[str]) -> Transcript: ...

# Member 2 — app/speech/tts.py
async def synthesize(text: str, language: Lang) -> AsyncIterator[bytes]: ...  # raises TtsError

# Member 2 — app/speech/number_words.py
def rupees_in_words(paise: int, language: Lang) -> str: ...

# Member 2 — app/core/crypto.py
def make_engine(db_path: str) -> Engine: ...
def encrypt_text(value: str | None) -> str | None: ...
def decrypt_text(value: str | None) -> str | None: ...

# Member 2 — app/core/retention.py
def purge(now: datetime | None = None) -> dict: ...  # {"transcripts_cleared": n, "sessions_deleted": n}
async def retention_loop() -> None: ...  # purge() at start, then every hour

# Member 3 — app/ai/*
async def interpret(transcript: Transcript, context: Context) -> Interpretation: ...  # interpreter.py
def parse_amount(text: str | None) -> int | None: ...  # number_parser.py, paise
def business_date(moment: datetime, shop: ShopInfo) -> date: ...  # shop_clock.py
def resolve_date(expression: str | None, moment: datetime, shop: ShopInfo) -> date: ...  # shop_clock.py
def normalize_name(name: str) -> str: ...  # matching.py
def match_customers(name: str, customers: list[CustomerRef]) -> list[Candidate]: ...  # matching.py, best first, score >= 75 only

# Member 4 — app/services/orchestrator.py
async def handle_transcript(session_id: str, turn_id: str, transcript: Transcript, now: datetime, source: str = "voice", strict: bool = False) -> list[dict]: ...
async def handle_choice(session_id: str, turn_id: str, choice: dict, now: datetime) -> list[dict]: ...

# Member 4 — app/services/providers.py
def speech() -> SimpleNamespace: ...  # SttSession, transcribe_file, synthesize (stub or real by USE_STUB_SPEECH)
def ai() -> SimpleNamespace: ...  # interpret, parse_amount, business_date, resolve_date, normalize_name, match_customers (stub or real by USE_STUB_AI)
```

**Stubs (created in P0, kept working until I-2)**: the speech stub's `SttSession.result()` returns `Transcript(text=STUB_TRANSCRIPT, language="hi")`, `transcribe_file` returns the same, and `synthesize` yields nothing. The AI stub returns one `CREATE_TRANSACTION` for Ramesh Sharma, 34000 paise, credit, when the text is the stub transcript, and `UNKNOWN` otherwise; its matching is exact or first-name only; its dates use the same business-day rule as the real Shop-Clock; its `parse_amount` reads plain digits only; its `normalize_name` lowercases and trims.

`customers.name_key` is recomputed for every customer at backend startup with the active `normalize_name`, so switching from stub to real matching never leaves stale keys.

## Voice hook (`frontend/src/voice/useVoice.js`, Member 2)

```javascript
const v = useVoice();
v.start() // call from a tap: unlocks audio, asks mic permission, connects, starts the wake word
v.started // boolean
v.state // "resting" | "listening" | "understanding" | "asking" | "speaking"
v.connection // "online" | "offline" | "reconnecting"
v.micPermission // "unknown" | "granted" | "denied"
v.lastHeard // { turnId, text, language } | null
v.lastEvent // the latest entry / question / answer / not_understood / error message
v.pendingQuestion // the open question message, or null
v.lastAnswerSay // text of the last spoken reply
v.queuedCount // offline turns waiting to sync
v.notSaved // array of not_saved messages from sync
v.syncing // true while offline turns upload
v.choose(turnId, choice) // tapped answer to a question
v.replay() // plays the last reply audio again
v.setDemoTime(isoOrNull) // demo mode: send now_override with the next turns
v.dismissNotSaved(turnId)
```

With `VITE_USE_MOCK_VOICE=true`, `useVoice` uses `mockVoice.js`, which cycles through every state and message type every few seconds so Member 1 can build all screens without a backend.

## Decision rules (Member 4: `validation.py` and `orchestrator.py`)

Applied to each operation in spoken order:
1. Intent UNKNOWN, or confidence below 0.6 → `not_understood`. Stop.
2. `CREATE_TRANSACTION`:
   a. Direction missing → question `confirm_direction`.
   b. `amount_paise` missing or `amount_check` is "unparsed" → `not_understood`.
   c. `amount_check` is "mismatch", amount above `MAX_AMOUNT_PAISE`, or the outlier rule fires → question `confirm_amount`.
   d. Customer: `match_customers(customer_name)`. One candidate scoring 90 or more → that customer. Two or more scoring 90 or more → question `choose_customer`. Best score 75–89 → question `confirm_similar` (yes → that customer, no → new customer). No candidate → create a new customer (source "voice") and set `new_customer: true`.
   e. If an entry with this operation's idempotency key already exists, send that entry again and move to the next operation (a resent turn or upload). Otherwise, the same customer, amount and direction recorded within `DUPLICATE_WINDOW_SECONDS` → question `confirm_duplicate`.
   f. Write the entry in one database transaction with idempotency key `<turn_id>:<operation index>`; set the session's last entry; send entry with status "new".
3. `CORRECTION`: no last entry in this session → `not_understood`. Amount checks as in 2.2 and 2.3. Last entry within `AMEND_WINDOW_SECONDS` → amend it, write history, send entry with status "amended" and `old_amount_paise`. Older → question `confirm_amend`.
4. `UNDO_LAST`: no active last entry → answer info with `nothing_to_undo`. Within the window → undo, write history, send entry with status "undone". Older → question `confirm_undo`.
5. `QUERY_BALANCE`: customer resolved as in 2.4, except no candidate → answer info with `customer_not_found` → answer `balance`.
6. `QUERY_DAILY_TOTAL` → answer `daily_total`. `QUERY_DAY_SUMMARY` → answer `day_summary`.
7. `CONFIRM` / `CHOOSE_CUSTOMER` with no pending question → `not_understood`. With one: resolve it. A spoken `CHOOSE_CUSTOMER` is matched with `match_customers(choice, the option customers)`; exactly one at 90 or more resolves it; otherwise ask the same question once more, then `not_understood`. For `confirm_direction`, `CONFIRM`'s choice is "credit" or "payment". "no" to `confirm_duplicate`, `confirm_amount`, `confirm_amend` or `confirm_undo` → answer `cancelled`.
8. When a question is asked, the remaining operations are stored in `pending_json` and resumed after the answer. New unrelated speech while a question is pending discards the pending question and is processed normally.
9. In strict mode (offline sync), any question becomes `not_saved` instead, and nothing for that operation is written.
10. The final message: entries only → answer kind `entry_saved` whose say joins each entry's sentence (three or more entries use `entries_many`). The first final message of every session starts with the disclosure sentence; then `disclosed` is set.

## Reply templates (`app/services/replies.py`, Member 4)

`{amount}`, `{balance}`, `{credit}` and `{payment}` are always `rupees_in_words(paise, language)`. `{top}` is up to three "name amount" pairs joined by commas. Kannada text is written by the team's Kannada speaker in hour 10–12; until then Kannada falls back to Hindi.

| Key | Hindi | English |
| :--- | :--- | :--- |
| `disclosure` | नमस्ते, मैं मुंशी हूँ, एक AI सहायक। | Hello, I'm Munshi, an AI assistant. |
| `entry_credit` | {name} के खाते में {amount} उधार लिख दिया। कुल बाकी {balance}। | Added {amount} credit for {name}. Balance {balance}. |
| `entry_payment` | {name} से {amount} जमा लिया। कुल बाकी {balance}। | Received {amount} from {name}. Balance {balance}. |
| `entry_amended` | ठीक है, {name} की एंट्री बदलकर {amount} कर दी। कुल बाकी {balance}। | Changed {name}'s entry to {amount}. Balance {balance}. |
| `entry_undone` | {name} की {amount} वाली एंट्री हटा दी। कुल बाकी {balance}। | Removed {name}'s {amount} entry. Balance {balance}. |
| `entries_many` | {count} एंट्री लिख दीं। | Saved {count} entries. |
| `new_customer_prefix` | नया ग्राहक {name} जोड़ा। | Added new customer {name}. |
| `balance` | {name} का कुल बाकी {balance} है। | {name} owes {balance}. |
| `balance_zero` | {name} का कोई बाकी नहीं है। | {name} owes nothing. |
| `balance_advance` | {name} का {balance} एडवांस जमा है। | {name} has {balance} paid in advance. |
| `daily_total` | आज कुल {amount} उधार गया। | Total credit today is {amount}. |
| `day_summary` | आज {credit} उधार गया और {payment} जमा आया। सबसे ज़्यादा बाकी: {top}। | Today {credit} went on credit and {payment} came in. Highest balances: {top}. |
| `choose_customer` | कौन से? {options}? | Which one: {options}? |
| `confirm_similar` | क्या आपका मतलब {name} है? | Do you mean {name}? |
| `confirm_amount` | {amount}, सही है? हाँ या ना बोलिए। | Is {amount} right? Say yes or no. |
| `confirm_direction` | {name} का {amount} उधार है या जमा? | Is {name}'s {amount} credit or payment? |
| `confirm_duplicate` | {name} का {amount} अभी लिखा था। दोबारा लिखूँ? | I just saved {amount} for {name}. Save it again? |
| `confirm_amend` | {name} की पिछली एंट्री बदलकर {amount} कर दूँ? | Change {name}'s last entry to {amount}? |
| `confirm_undo` | {name} की {amount} वाली एंट्री हटा दूँ? | Remove {name}'s {amount} entry? |
| `cancelled` | ठीक है, कुछ नहीं लिखा। | Okay, nothing saved. |
| `not_understood` | समझ नहीं आया, दोबारा बोलिए। | I didn't catch that, please say it again. |
| `nothing_to_undo` | हटाने के लिए कोई एंट्री नहीं है। | There's no entry to remove. |
| `customer_not_found` | {name} नाम का कोई ग्राहक नहीं मिला। | No customer named {name}. |
| `not_saved` | ऑफलाइन एंट्री सेव नहीं हुई, दोबारा बोलिए। | An offline entry wasn't saved. Please say it again. |
| `stt_failed` | आवाज़ नहीं पहुँची, दोबारा बोलिए। | The voice didn't come through. Please say it again. |
