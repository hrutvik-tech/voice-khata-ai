import argparse
import asyncio
import json
import os
from pathlib import Path
import re
import sys
import wave

from app.speech.stt import SttSession
from app.speech.tts import synthesize
from app.speech.number_words import HINDI_1_TO_99

# Build reverse mapping from Devanagari words to numbers
DEV_WORDS: dict[str, int] = {word: num for num, word in HINDI_1_TO_99.items()}
DEV_WORDS.update({
    "पाँच": 5,
    "शून्य": 0,
    "हजार": 1000,
    "हज़ार": 1000,
    "लाख": 100000,
    "करोड़": 10000000,
    "करोड़": 10000000,
})

DEV_MULTIPLIERS: dict[str, int] = {
    "सौ": 100,
    "हज़ार": 1000,
    "हजार": 1000,
    "लाख": 100000,
    "करोड़": 10000000,
    "करोड़": 10000000,
}


def _ensure_api_key() -> None:
    if os.getenv("GNANI_API_KEY"):
        return
    for env_path in [
        Path.cwd() / ".env",
        Path.cwd() / ".env.txt",
        Path(__file__).resolve().parents[2].parent / ".env",
        Path(__file__).resolve().parents[2].parent / ".env.txt",
    ]:
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("GNANI_API_KEY="):
                    os.environ["GNANI_API_KEY"] = line.split("=", 1)[1].strip()
                    return
                elif line.startswith("vach_"):
                    os.environ["GNANI_API_KEY"] = line
                    return


def parse_devanagari_amount(text: str) -> int | None:
    """Parses Devanagari number phrases (e.g. 'तीन सौ चालीस', 'छह हजार दो सौ') to paise."""
    # Clean punctuation
    cleaned = re.sub(r"[।,!?'\"]", "", text)
    tokens = cleaned.split()

    total_rupees = 0
    current_block = 0
    found_number = False

    for token in tokens:
        if token in DEV_MULTIPLIERS:
            mult = DEV_MULTIPLIERS[token]
            if current_block == 0:
                current_block = 1
            total_rupees += current_block * mult
            current_block = 0
            found_number = True
        elif token in DEV_WORDS:
            val = DEV_WORDS[token]
            current_block += val
            found_number = True
        elif token.isdigit():
            val = int(token)
            current_block += val
            found_number = True
        else:
            if found_number:
                # Accumulate whatever number we have so far
                if current_block > 0:
                    total_rupees += current_block
                    current_block = 0
                if total_rupees > 0:
                    break

    total_rupees += current_block
    if total_rupees > 0:
        return total_rupees * 100
    return None


def parse_amount_from_transcript(text: str | None) -> int | None:
    """Extract money amount in integer paise from transcript text."""
    if not text:
        return None

    # 1. Try providers.ai().parse_amount if available
    try:
        from app.services import providers
        amt = providers.ai().parse_amount(text)
        if amt is not None:
            return amt
    except Exception:
        pass

    # 2. Try Devanagari words parsing (e.g., 'तीन सौ चालीस')
    dev_amt = parse_devanagari_amount(text)
    if dev_amt is not None:
        return dev_amt

    # 3. Try app.ai.number_parser.parse_amount if available
    try:
        from app.ai.number_parser import parse_amount
        amt = parse_amount(text)
        if amt is not None:
            return amt

        # If sentence contains digits, extract digits and parse
        m = re.search(r"\b\d+\b", text)
        if m:
            amt = parse_amount(m.group(0))
            if amt is not None:
                return amt
    except Exception:
        pass

    # 4. Fallback: extract plain digits and convert rupees to paise
    m = re.search(r"\b\d+\b", text)
    if m:
        try:
            return int(m.group(0)) * 100
        except ValueError:
            return None

    return None


async def run_stt_stream(
    folder_path: str,
    min_silence_override: int | None = None,
    vad_threshold_override: float | None = None,
) -> tuple[int, int, float]:
    """Run realtime STT on a folder of WAV files, compare amounts, and print report.

    Returns:
        tuple of (amounts_correct, total_count, average_latency_ms)
    """
    _ensure_api_key()

    if min_silence_override is not None:
        os.environ["STT_MIN_SILENCE_MS"] = str(min_silence_override)
    if vad_threshold_override is not None:
        os.environ["STT_VAD_THRESHOLD"] = str(vad_threshold_override)

    folder = Path(folder_path)
    if not folder.exists() or not folder.is_dir():
        print(f"Error: Folder '{folder_path}' does not exist or is not a directory.", file=sys.stderr)
        sys.exit(1)

    expected_map: dict[str, dict] = {}
    expected_file = folder / "expected.json"
    if expected_file.exists():
        try:
            with open(expected_file, "r", encoding="utf-8") as f:
                entries = json.load(f)
                if isinstance(entries, list):
                    for item in entries:
                        if "file" in item:
                            expected_map[item["file"]] = item
        except Exception as exc:
            print(f"Warning: Failed to load expected.json: {exc}", file=sys.stderr)

    wav_files = sorted(folder.glob("*.wav"))
    if not wav_files:
        print(f"No WAV files found in '{folder_path}'.")
        return 0, 0, 0.0

    results: list[dict] = []
    chunk_size = 1024
    correct_amounts = 0
    total_evaluated = 0
    latencies: list[int] = []

    for wav_path in wav_files:
        filename = wav_path.name
        exp_item = expected_map.get(filename, {})
        expected_text = exp_item.get("text", "—")
        expected_paise = exp_item.get("amount_paise")

        try:
            with wave.open(str(wav_path), "rb") as wf:
                raw_pcm = wf.readframes(wf.getnframes())
        except Exception as exc:
            results.append({
                "file": filename,
                "expected": expected_text,
                "transcript": f"Error reading WAV: {exc}",
                "expected_paise": f"{expected_paise}p" if expected_paise is not None else "—",
                "found_paise": "—",
                "match": "❌",
                "latency": "—",
            })
            continue

        session = SttSession(lang_hints=["hi-IN"], keyterms=[])
        try:
            await session.open()

            # Stream audio frames in real time: 1,024 bytes every 32 ms
            for i in range(0, len(raw_pcm), chunk_size):
                chunk = raw_pcm[i:i + chunk_size]
                if len(chunk) < chunk_size:
                    chunk = chunk + b"\x00" * (chunk_size - len(chunk))
                await session.send(chunk)
                await asyncio.sleep(0.032)

            await session.commit()
            transcript = await session.result(timeout=6.0)

            found_paise = parse_amount_from_transcript(transcript.text)
            if transcript.latency_ms is not None:
                latencies.append(transcript.latency_ms)

            is_correct = False
            if expected_paise is not None:
                total_evaluated += 1
                if found_paise == expected_paise:
                    correct_amounts += 1
                    is_correct = True

            results.append({
                "file": filename,
                "expected": expected_text,
                "transcript": transcript.text,
                "expected_paise": f"{expected_paise}p" if expected_paise is not None else "—",
                "found_paise": f"{found_paise}p" if found_paise is not None else "None",
                "match": "✅" if is_correct else "❌",
                "latency": f"{transcript.latency_ms} ms" if transcript.latency_ms is not None else "—",
            })
        except Exception as exc:
            results.append({
                "file": filename,
                "expected": expected_text,
                "transcript": f"STT Error: {exc}",
                "expected_paise": f"{expected_paise}p" if expected_paise is not None else "—",
                "found_paise": "—",
                "match": "❌",
                "latency": "—",
            })
        finally:
            await session.close()

    # Print results as an aligned table
    headers = ["File", "Expected Text", "Transcript", "Exp Amt", "Found Amt", "Match", "Latency"]
    rows = [
        [
            r["file"],
            r["expected"],
            r["transcript"],
            r["expected_paise"],
            r["found_paise"],
            r["match"],
            r["latency"],
        ]
        for r in results
    ]

    col_widths = [len(h) for h in headers]
    for row in rows:
        for idx, cell in enumerate(row):
            col_widths[idx] = max(col_widths[idx], len(str(cell)))

    header_line = " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers))
    sep_line = "-+-".join("-" * col_widths[i] for i in range(len(headers)))

    print("\n" + header_line)
    print(sep_line)
    for row in rows:
        print(" | ".join(str(cell).ljust(col_widths[i]) for i, cell in enumerate(row)))
    print()

    avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
    print(f"amounts correct: {correct_amounts}/{total_evaluated}")

    return correct_amounts, total_evaluated, avg_latency


async def run_tts(text: str, language: str, out_file: str) -> None:
    _ensure_api_key()
    out_path = Path(out_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f'Synthesizing: "{text}" ({language}) -> {out_file}...')
    chunk_count = 0
    total_bytes = 0

    with open(out_path, "wb") as f:
        async for chunk in synthesize(text, language):  # type: ignore[arg-type]
            f.write(chunk)
            chunk_count += 1
            total_bytes += len(chunk)

    print(f"Saved {total_bytes} bytes ({chunk_count} chunks) to {out_file}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Voice Khata Speech CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    stt_parser = subparsers.add_parser("stt", help="Run realtime STT on a folder of WAV files")
    stt_parser.add_argument("folder", help="Path to folder containing WAV files and expected.json")
    stt_parser.add_argument(
        "--min-silence",
        type=int,
        default=None,
        help="Override STT_MIN_SILENCE_MS for this run",
    )
    stt_parser.add_argument(
        "--vad-threshold",
        type=float,
        default=None,
        help="Override STT_VAD_THRESHOLD for this run",
    )

    tts_parser = subparsers.add_parser("tts", help="Synthesize text to speech")
    tts_parser.add_argument("text", help="Text to speak")
    tts_parser.add_argument("language", choices=["hi", "kn", "en"], help="Language code (hi, kn, en)")
    tts_parser.add_argument("out_file", help="Path to save output audio file")

    args = parser.parse_args()
    if args.command == "stt":
        asyncio.run(
            run_stt_stream(
                args.folder,
                min_silence_override=args.min_silence,
                vad_threshold_override=args.vad_threshold,
            )
        )
    elif args.command == "tts":
        asyncio.run(run_tts(args.text, args.language, args.out_file))


if __name__ == "__main__":
    main()
