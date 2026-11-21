# Gnani STT Documentation (Compiled)

**Sources**:
- Realtime streaming: <https://docs.gnani.ai/api/STT/stt-websocket>
- REST transcription: <https://docs.gnani.ai/api/STT/speech-to-text>
- Limits: <https://docs.gnani.ai/api/STT/limits>
- Prisma v3.0 model details: <https://docs.gnani.ai/api/STT/models/prisma-v3>

---

## 1. Realtime Streaming (WebSocket)

**Endpoint**
```text
WSS wss://api.vachana.ai/stt/v3/stream
```

**Connection headers** (sent as WebSocket upgrade headers):
| Header | Required | Default | Description |
|---|---|---|---|
| `x-api-key-id` | Yes | — | Your Gnani API key |
| `language_code` | Yes | — | Language code (e.g. `hi-IN`, `en-IN`, `indic-auto`). For Prisma v3.0 you may supply a comma‑separated list of 1‑4 languages. |
| `model` | No | — | `prisma-v3.0` selects Prisma v3.0; otherwise Prisma v2.5 is used |
| `keyterms` | No | — | Up to 200 words/phrases to favour (Prisma v3.0). Same as `bias_list` for v2.5 |
| `topic` | No | — | Free‑text hint about the audio (Prisma v3.0 only) |
| `previous_text` | No | — | Text that preceded the audio (Prisma v3.0 only) |
| `speaker_names` | No | — | JSON array or comma‑separated list of 1‑4 speaker names (Prisma v3.0 only) |
| `x-idle-timeout-sec` | No | `60` | Session idle timeout (5‑900 s) |
| `x-sample-rate` | No | `16000` | Audio sample rate (8000, 16000, 44100, 48000) |
| `format` | No | `verbatim` | `verbatim`, `transcribe`, `codemix` (v3.0 only), `transliterate` (v3.0 only) |
| `bias_list` / `bias_score` | No | — | Word‑boosting for v2.5 (up to 100 single words) |
| VAD tuning headers (optional) | — | — | `x-vad-threshold`, `x-min-silence-ms`, `x-min-speech-ms`, `x-min-segment-ms`, `x-max-speech-s` (see full table below) |

### VAD Tuning (optional)
| Header | Default | Range | Typical use |
|---|---|---|---|
| `x-vad-threshold` | `0.7` | 0.0‑1.0 | Higher = stricter noise rejection |
| `x-min-silence-ms` | `500` | 100‑2000 | Lower = faster transcripts, higher = more complete sentences |
| `x-min-speech-ms` | `100` (200 @ 8 kHz) | 50‑2000 | Noise gate at start |
| `x-min-segment-ms` | `120` | 100‑1000 | Minimum speech length to open a segment |
| `x-max-speech-s` | disabled | 5.0‑120.0 | Hard cap on a single segment (useful for monologues) |

**Message flow**
1. Client opens WebSocket with the headers above.
2. Client streams raw PCM audio frames (16‑bit, mono) matching `x-sample-rate`.
3. Server emits JSON `transcript` messages when a segment ends (VAD decides).
4. An `error` message is sent if required headers are missing or a limit is hit.
5. Session automatically ends after **15 minutes** of streaming.

**Word boosting (Prisma v2.5)**
```text
bias_list: ["Prisma","EMI"]
bias_score: 1.0   # allowed: 0.0, 0.5, 1.0, 1.5, 2.0
```
For Prisma v3.0 use `keyterms` instead of `bias_list`.

---

## 2. REST Transcription

**Endpoint**
```http
POST https://api.vachana.ai/stt/v3
Content-Type: multipart/form-data
```
(The path shown in the docs is `/stt/v3`; the host may be `api.vachana.ai`.)

**Request parameters** (form‑fields):
- `audio_file`: WAV, MP3, OGG, FLAC, AAC, or M4A (30 s max per request).
- `language_code` (required): same values as WebSocket.
- `model` (optional): `prisma-v3.0` to opt‑in to the multilingual model.
- `format` (optional): `verbatim`, `transcribe`, `codemix`, `transliterate`.
- `keyterms`, `topic`, `previous_text`, `speaker_names` – same semantics as WebSocket.
- `bias_list` / `bias_score` – word boosting for v2.5.

**Response** (JSON)
```json
{
  "transcript": "...",
  "model": "prisma-v3.0" ,
  "detected_language_code": "hi-IN",   // only for v3.0 when auto detection is used
  "confidence": 0.96,
  "metadata": { ... }
}
```

### Limits (per‑account)
| Item | Prisma v3.0 | Prisma v2.5 |
|---|---|---|
| Audio length per REST request | **30 s** | **30 s** |
| Shortest accepted audio | 0.1 s (returns empty transcript) | n/a |
| Audio formats | wav, mp3, ogg, flac, aac, m4a (detected from extension) | Same |
| Languages in `language_code` | `indic-auto` or 1‑4 comma‑separated codes | 1 (Batch up to 3) |
| `keyterms` size | up to 200 items | up to 100 single words (`bias_list`) |
| `topic` length | up to 1 600 chars (REST) | n/a |
| `speaker_names` | 1‑4 names | n/a |
| Substitution map | up to 10 rules | Same |
| Streaming session length | 15 min | 15 min |
| Request‑rate & concurrent sessions | See **Limits** page (account‑specific) | Same |

For the full list of rate‑limit values see the **Limits** page.

---

## 3. Supported Languages

Gnani supports ten Indian languages plus English. See the language index page for the exact codes:
- `hi-IN` – Hindi
- `en-IN` – English
- `ta-IN` – Tamil
- `te-IN` – Telugu
- `kn-IN` – Kannada
- `ml-IN` – Malayalam
- `mr-IN` – Marathi
- `pa-IN` – Punjabi
- `bn-IN` – Bengali
- `gu-IN` – Gujarati
- `indic-auto` – automatic language detection (Prisma v3.0)

Full list: <https://docs.gnani.ai/api/STT/languages>

---

## 4. Prisma v3.0 Model (Multilingual)

Prisma v3.0 is a single model that handles all ten languages and can auto‑detect the spoken language. It also supports mixed‑language utterances.
- Select with `model=prisma-v3.0` (REST or WebSocket).
- `language_code=indic-auto` (default) or a comma‑separated list of up to four languages.
- Output formats: `verbatim`, `transcribe`, `codemix`, `transliterate`.
- Hints: `keyterms`, `topic`, `previous_text`, `speaker_names` improve accuracy.
- Response includes `detected_language_code` when auto detection is used.

Detailed model docs: <https://docs.gnani.ai/api/STT/models/prisma-v3>

---

## 5. Session & API Limits

All limits are listed on the **Limits** page. The most relevant values for STT are reproduced above. Additional limits include:
- **Idle timeout**: `x-idle-timeout-sec` (default 60 s) controls how long a streaming session can stay silent before the server closes it.
- **Concurrent streaming sessions**: per‑organisation cap (error `RATE_LIMITED` if exceeded).
- **Rate limiting**: HTTP 429 with `error_code=RATE_LIMITED`; implement exponential back‑off.

Full page: <https://docs.gnani.ai/api/STT/limits>

---

*These files are intended to be the single source of truth for Gnani STT within the Voice Khata project.*