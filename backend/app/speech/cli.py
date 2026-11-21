import argparse
import asyncio
import json
import os
from pathlib import Path
import sys
import wave

from app.speech.stt import SttSession
from app.speech.tts import synthesize


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


async def run_stt_stream(folder_path: str) -> None:
    _ensure_api_key()
    folder = Path(folder_path)
    if not folder.exists() or not folder.is_dir():
        print(f"Error: Folder '{folder_path}' does not exist or is not a directory.", file=sys.stderr)
        sys.exit(1)

    expected_map: dict[str, str] = {}
    expected_file = folder / "expected.json"
    if expected_file.exists():
        try:
            with open(expected_file, "r", encoding="utf-8") as f:
                entries = json.load(f)
                if isinstance(entries, list):
                    for item in entries:
                        if "file" in item and "text" in item:
                            expected_map[item["file"]] = item["text"]
        except Exception as exc:
            print(f"Warning: Failed to load expected.json: {exc}", file=sys.stderr)

    wav_files = sorted(folder.glob("*.wav"))
    if not wav_files:
        print(f"No WAV files found in '{folder_path}'.")
        return

    results: list[dict] = []
    chunk_size = 1024

    for wav_path in wav_files:
        filename = wav_path.name
        expected_text = expected_map.get(filename, "—")

        try:
            with wave.open(str(wav_path), "rb") as wf:
                raw_pcm = wf.readframes(wf.getnframes())
        except Exception as exc:
            results.append({
                "file": filename,
                "expected": expected_text,
                "transcript": f"Error reading WAV: {exc}",
                "language": "—",
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
            results.append({
                "file": filename,
                "expected": expected_text,
                "transcript": transcript.text,
                "language": transcript.language or "—",
                "latency": f"{transcript.latency_ms} ms" if transcript.latency_ms is not None else "—",
            })
        except Exception as exc:
            results.append({
                "file": filename,
                "expected": expected_text,
                "transcript": f"STT Error: {exc}",
                "language": "—",
                "latency": "—",
            })
        finally:
            await session.close()

    # Print results as an aligned table
    headers = ["File", "Expected Text", "Transcript", "Language", "Latency"]
    rows = [
        [r["file"], r["expected"], r["transcript"], r["language"], r["latency"]]
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


async def run_tts(text: str, language: str, out_file: str) -> None:
    _ensure_api_key()
    out_path = Path(out_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Synthesizing: \"{text}\" ({language}) -> {out_file}...")
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

    tts_parser = subparsers.add_parser("tts", help="Synthesize text to speech")
    tts_parser.add_argument("text", help="Text to speak")
    tts_parser.add_argument("language", choices=["hi", "kn", "en"], help="Language code (hi, kn, en)")
    tts_parser.add_argument("out_file", help="Path to save output audio file")

    args = parser.parse_args()
    if args.command == "stt":
        asyncio.run(run_stt_stream(args.folder))
    elif args.command == "tts":
        asyncio.run(run_tts(args.text, args.language, args.out_file))


if __name__ == "__main__":
    main()
