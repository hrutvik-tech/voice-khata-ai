# Gnani TTS Documentation (Compiled)

**Sources**:
- Realtime TTS (WebSocket): <https://docs.gnani.ai/api/TTS/tts-websocket>
- Available Voices: <https://docs.gnani.ai/api/TTS/available-voices>
- Text Normalization Guide: <https://docs.gnani.ai/api/TTS/tts-input-formating>

---

## 1. Realtime Text‑to‑Speech (WebSocket)

**Endpoint**
```text
WSS wss://api.vachana.ai/api/v1/tts
```

**Connection headers** (sent as WebSocket upgrade headers):
| Header | Required | Description |
|---|---|---|
| `X-API-Key-ID` | Yes | Your Gnani API key |
| `voice` | Yes | Voice name from the catalog of the selected model |
| `model` | Yes | `timbre-v2.5` or `timbre-v3.0` |
| `language` | Yes | Language code (e.g. `hi-IN`, `en-IN`, `auto`) |
| `speed` | No (default `1.0`) | Playback speed multiplier (model‑specific range) |
| `audio_config.sample_rate` | No (default `48000`) | 8000, 16000, 44100, 48000 |
| `audio_config.num_channels` | No (default `1`) |
| `audio_config.sample_width` | No (default `2`) |
| `audio_config.encoding` | No (default `linear_pcm`) |
| `audio_config.container` | Yes (`wav` or `mp3` etc.) |
| **Audio Tags** (v3.0 only) | No | Inline tags like `<whispers>`, `<laugh>`, `<pauses>` to add non‑verbal cues |

**Message flow**
1. Client opens the WebSocket with the headers above.
2. Client sends a single JSON synthesis request:
```json
{
  "text": "नमस्ते, आप कैसे हैं?",
  "voice": "Nalini",
  "model": "timbre-v2.5",
  "language": "hi-IN",
  "speed": 1.0,
  "audio_config": {
    "sample_rate": 48000,
    "num_channels": 1,
    "sample_width": 2,
    "encoding": "linear_pcm",
    "container": "wav"
  }
}
```
3. Server streams audio chunks as base64‑encoded JSON messages (`type: "audio"`).
4. Final message `type: "complete"` (or `type: "error"` on failure).
5. Close the connection when done.

**Typical limits**
- One synthesis request per connection.
- Low‑latency streaming – suitable for interactive assistants.
- Errors returned as JSON with `error` field, e.g. `SYNTHESIS_FAILED`.

---

## 2. Available Voices

Gnani provides two TTS models, each with its own voice catalog.

| Model | `model` value | Number of voices | Languages per voice | Audio tags support |
|---|---|---|---|---|
| **Timbre v2.5** | `timbre-v2.5` | 42 | One preferred language per voice (see table) | ❌ (no tags) |
| **Timbre v3.0** | `timbre-v3.0` | 34 | All 10 Indian languages for every voice | ✅ (see *Audio Tags* section) |

### Timbre v2.5 – Preferred voices by language
| Language | `language` value | Sample voices |
|---|---|---|
| English | `en-IN` | Kaveri, Trupti, Devika, Pranav, Shlok, Girish |
| Hindi | `hi-IN` | Nalini, Bhavna, Yashvi, Urmila, Jwala, Chitra, Ambuja, Deepak, Roopesh, Vikrant, Hemraj, Jalaj, Omkar |
| Hinglish | `hi-en` | Poorvi |
| Tamil | `ta-IN` | Asmita, Trisha, Brinda, Vedika, Noopur |
| Telugu | `te-IN` | Suhana, Lehara, Lavanya, Yukti, Varuni |
| Kannada | `kn-IN` | Saanvi, Kavin |
| Malayalam | `ml-IN` | Reshma, Riyaan |
| Marathi | `mr-IN` | Zahira, Ishaan |
| Bengali | `bn-IN` | Kirra, Dhruva |
| Gujarati | `gu-IN` | Falak, Veera |
| Punjabi | `pa-IN` | Mehuli, Zayan |

### Timbre v3.0 – Full catalog (all voices work with any of the 10 languages)
| Voice | Gender | Persona / best‑for |
|---|---|---|
| Shivani | Female | Conversational, expressive |
| Avinash | Male | Calm, captivating |
| Anitasingh | Female | Firm yet empathetic (collections, payment reminders) |
| Arko | Male | Deep authoritative baritone (narration, brand) |
| ... | ... | (full list available in the official catalog) |

**Important:** Voices are **not interchangeable** between models. Using a v2.5 voice with `model: "timbre-v3.0"` (or vice‑versa) results in a `400 Bad Request` error.

### Audio Tags (Timbre v3.0 only)
Insert tags inline in the `text` field to control non‑verbal cues:
```
<whispers>   <laugh>   <pauses>   <shouting>   <sigh>   <coughs>   <excited>   <slow>   <yawns>   <clears throat>
```
Example:
```json
{
  "text": "Let me check that for you.<pauses>Found it.<laugh> Your order ships tomorrow.",
  "voice": "Shivani",
  "model": "timbre-v3.0",
  "language": "en-IN"
}
```
For details see the Audio Tags page: <https://docs.gnani.ai/api/TTS/tts-audio-tags>.

---

## 3. Text Normalization Guide

Gnani automatically normalizes numbers, dates, currencies, IDs, and common abbreviations before synthesis. This applies to **all** voices (v2.5 and v3.0).

### Language selection
- Use `language` parameter (`hi-IN`, `en-IN`, `ta-IN`, …) or `auto` to let the system detect the script.
- `auto` chooses a profile based on the dominant script; Latin‑only text defaults to English.

### What is normalized
- **Numbers** (cardinals, negatives, decimals, Indian lakh grouping, ordinals)
- **Currency** (₹, USD, EUR, etc.)
- **Dates & times** (e.g., `23/06/2026`, `12:30 PM`)
- **Durations** (`15 minutes`, `2 hrs`)
- **Common abbreviations** (`St.`, `Rd`, `Ltd`, `Co.`)
- **Brand / product names** – special pronunciations for known brands (e.g., “Gnani” is spoken native to the language).
- **Units of measurement** (`kg`, `km`, `°C`, `GB`) stay in English.
- **Initialisms** (`OTP`, `EMI`, `GST`, `URL`) are spelled out letter‑by‑letter.
- **Audio tags** do **not** affect normalization; they are stripped before speaking.

### Known limitations & work‑arounds
| Limitation | Work‑around |
|---|---|
| Two‑part dates like `23/06` read as a fraction | Include the year (`23/06/2026`) |
| `5°` without a unit letter | Write `5°C` or `5°F` |
| Very long IDs (14+ digits) read as a raw digit string | Insert spaces or hyphens between groups |
| `minus` is not localized (always English) | None – currently unavoidable |
| `auto` with Latin‑only input resolves to English | Pass explicit `language` code (e.g., `kn`) |

For the full list of supported patterns and examples, see the official guide: <https://docs.gnani.ai/api/TTS/tts-input-formating>

---

*These files are intended to be the single source of truth for Gnani TTS within the Voice Khata project.*