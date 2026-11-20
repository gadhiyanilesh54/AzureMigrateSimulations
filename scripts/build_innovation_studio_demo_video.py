"""Build a captioned, sub-five-minute Innovation Studio product demo."""

from __future__ import annotations

import asyncio
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import edge_tts
import imageio_ffmpeg
from mutagen.mp3 import MP3

ROOT = Path(__file__).resolve().parents[1]
DEMO_DIR = ROOT / "docs" / "demo"
VIDEO_DIR = DEMO_DIR / "video"
BROWSER_DIR = VIDEO_DIR / "browser"
RENDER_DIR = ROOT / "test-results" / "demo-deck-render-v2"
WORK_DIR = ROOT / "test-results" / "innovation-studio-video-build"
AUDIO_DIR = WORK_DIR / "audio"
FINAL_VIDEO = DEMO_DIR / "Innovation_Studio_AI_Feasibility_Demo.mp4"
FINAL_CAPTIONS = DEMO_DIR / "Innovation_Studio_AI_Feasibility_Demo.srt"
MANIFEST_PATH = DEMO_DIR / "Innovation_Studio_AI_Feasibility_Demo.json"
FFMPEG = Path(imageio_ffmpeg.get_ffmpeg_exe())

VOICE = "en-US-AvaMultilingualNeural"
RATE = "+5%"
PITCH = "+0Hz"
PADDING_SECONDS = 0.7
VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
FPS = 30
MAX_DURATION_SECONDS = 120.0

SEQUENCE: list[dict[str, Any]] = [
    {
        "id": "opening",
        "visual_type": "image",
        "visual": "Slide1.PNG",
        "text": (
            "Azure Migrate explains how applications move to Azure. AI Feasibility Assessment answers the "
            "next question: where can AI create value, and what evidence, controls, and proof are needed?"
        ),
    },
    {
        "id": "selection",
        "visual_type": "video",
        "visual": "live_04_application_selection.webm",
        "visual_start": 3.3,
        "visual_end": 13.9,
        "text": (
            "In the simulator, we select B P T co as a complete discovered application and choose Document "
            "Processing and Enrichment. The assessment reuses observed dependencies, runtimes, assessed "
            "targets, readiness, and cost without assuming AI is feasible."
        ),
    },
    {
        "id": "intent",
        "visual_type": "video",
        "visual": "live_05_intent_outcome.webm",
        "visual_start": 2.0,
        "visual_end": 12.8,
        "text": (
            "The customer supplies what discovery cannot know: classify documents, extract fields, enrich "
            "metadata, validate rules, and route exceptions to people, targeting less manual work, faster "
            "processing, controlled access, and measurable accuracy."
        ),
    },
    {
        "id": "decision",
        "visual_type": "video",
        "visual": "live_06_decision_pack.webm",
        "visual_start": 14.5,
        "visual_end": 37.2,
        "text": (
            "After consent, Foundry improves only the grounded narrative; deterministic rules control "
            "eligibility, gaps, cost, and disposition. The versioned pack separates business, data, "
            "integration, governance, operations, and economics; proposes Document Intelligence, AI Search, "
            "model access, orchestration, storage, and monitoring; shows low, base, and high scenarios; and "
            "defines a bounded proof of concept with acceptance tests and production gates. Proof-of-concept "
            "candidate means justified experimentation, not production readiness."
        ),
    },
    {
        "id": "architecture",
        "visual_type": "video",
        "visual": "live_07_ai_ready_architecture.webm",
        "visual_start": 4.0,
        "visual_end": 15.8,
        "text": (
            "One action opens linked AI-ready architecture. The base migration design remains intact, while "
            "proposed AI services appear as an explicit extension tied to the assessment revision and costed "
            "separately."
        ),
    },
    {
        "id": "value",
        "visual_type": "image",
        "visual": "Slide8.PNG",
        "text": (
            "This converts migration context into an inspectable investment decision and delivery handoff. It "
            "may recommend a proof of concept, remediation, conventional automation, an existing product, or "
            "no AI. Azure Migrate understands the application; AI Feasibility helps choose its next value."
        ),
    },
]


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def spoken_text(text: str) -> str:
    return re.sub(r"\bAI\b", "A I", text)


async def generate_audio(entry: dict[str, Any]) -> dict[str, Any]:
    media_path = AUDIO_DIR / f"{entry['id']}.mp3"
    subtitle_path = AUDIO_DIR / f"{entry['id']}.vtt"
    communicate = edge_tts.Communicate(
        spoken_text(entry["text"]),
        VOICE,
        rate=RATE,
        pitch=PITCH,
    )
    await communicate.save(str(media_path), str(subtitle_path))
    return {
        "media": media_path,
        "subtitles": subtitle_path,
        "audio_duration": float(MP3(media_path).info.length),
    }


def media_duration(path: Path) -> float:
    completed = subprocess.run(
        [str(FFMPEG), "-hide_banner", "-i", str(path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", completed.stdout)
    if not match:
        raise RuntimeError(f"Could not determine duration for {path}")
    hours, minutes, seconds = match.groups()
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def timestamp(seconds: float) -> str:
    milliseconds = max(0, round(seconds * 1000))
    hours, milliseconds = divmod(milliseconds, 3_600_000)
    minutes, milliseconds = divmod(milliseconds, 60_000)
    secs, milliseconds = divmod(milliseconds, 1_000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"


def sentence_chunks(text: str, maximum_words: int = 12, maximum_characters: int = 84) -> list[str]:
    chunks: list[str] = []
    current: list[str] = []
    for word in text.split():
        candidate = " ".join([*current, word])
        if current and (len(current) >= maximum_words or len(candidate) > maximum_characters):
            chunks.append(" ".join(current))
            current = []
        current.append(word)
        if word.rstrip('”"').endswith((".", "?", "!", ":")):
            chunks.append(" ".join(current))
            current = []
    if current:
        chunks.append(" ".join(current))
    return chunks


def write_srt(entries: list[dict[str, Any]]) -> None:
    blocks: list[str] = []
    index = 1
    for entry in entries:
        chunks = sentence_chunks(entry["text"])
        total_words = sum(len(chunk.split()) for chunk in chunks)
        cursor = entry["start"]
        for chunk_index, chunk in enumerate(chunks):
            chunk_duration = entry["audio_duration"] * len(chunk.split()) / max(total_words, 1)
            end = cursor + chunk_duration
            if chunk_index == len(chunks) - 1:
                end = entry["start"] + entry["audio_duration"]
            blocks.append(f"{index}\n{timestamp(cursor)} --> {timestamp(end)}\n{chunk}\n")
            cursor = end
            index += 1
    FINAL_CAPTIONS.write_text("\n".join(blocks), encoding="utf-8")


def build_visual(entry: dict[str, Any], target: Path, duration: float) -> None:
    common_output = [
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-pix_fmt", "yuv420p", "-r", str(FPS), "-an", "-movflags", "+faststart",
        str(target),
    ]
    if entry["visual_type"] == "image":
        source = RENDER_DIR / entry["visual"]
        run([
            str(FFMPEG), "-y", "-loop", "1", "-framerate", str(FPS),
            "-i", str(source), "-t", f"{duration:.3f}",
            "-vf", f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:flags=lanczos,format=yuv420p",
            *common_output,
        ])
        return

    source = BROWSER_DIR / entry["visual"]
    source_duration = media_duration(source)
    visual_start = max(0.0, float(entry.get("visual_start", 0.0)))
    visual_end = min(source_duration, float(entry.get("visual_end", source_duration)))
    selected_duration = visual_end - visual_start
    if selected_duration <= 0:
        raise RuntimeError(f"Invalid visual range for {source}: {visual_start}..{visual_end}")
    speed = max(selected_duration / duration, 0.01)
    run([
        str(FFMPEG), "-y", "-ss", f"{visual_start:.3f}", "-t", f"{selected_duration:.3f}",
        "-i", str(source),
        "-vf", (
            f"setpts=PTS/{speed:.8f},"
            f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=decrease:flags=lanczos,"
            f"pad={VIDEO_WIDTH}:{VIDEO_HEIGHT}:(ow-iw)/2:(oh-ih)/2:color=061b2c,format=yuv420p"
        ),
        "-t", f"{duration:.3f}",
        *common_output,
    ])


def build_segment(
    entry: dict[str, Any],
    index: int,
    audio_meta: dict[str, Any],
) -> dict[str, Any]:
    audio_duration = float(audio_meta["audio_duration"])
    duration = audio_duration + PADDING_SECONDS
    visual_path = WORK_DIR / f"visual_{index:02d}.mp4"
    segment_path = WORK_DIR / f"segment_{index:02d}.mp4"
    padded_audio = WORK_DIR / f"audio_{index:02d}.m4a"

    build_visual(entry, visual_path, duration)
    run([
        str(FFMPEG), "-y", "-i", str(audio_meta["media"]),
        "-af", f"apad=pad_dur={PADDING_SECONDS}",
        "-t", f"{duration:.3f}", "-c:a", "aac", "-b:a", "160k",
        str(padded_audio),
    ])
    run([
        str(FFMPEG), "-y", "-i", str(visual_path), "-i", str(padded_audio),
        "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "copy",
        "-shortest", "-movflags", "+faststart", str(segment_path),
    ])
    return {
        **entry,
        "segment_file": segment_path.name,
        "audio_duration": round(audio_duration, 3),
        "duration": round(duration, 3),
    }


async def main_async() -> None:
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    for path in WORK_DIR.iterdir():
        if path.is_file():
            path.unlink()
        elif path.is_dir():
            shutil.rmtree(path)
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)

    generated_audio: dict[str, dict[str, Any]] = {}
    for index, entry in enumerate(SEQUENCE, 1):
        print(f"[audio {index:02d}/{len(SEQUENCE):02d}] {entry['id']}")
        generated_audio[entry["id"]] = await generate_audio(entry)

    built: list[dict[str, Any]] = []
    for index, entry in enumerate(SEQUENCE, 1):
        print(f"[video {index:02d}/{len(SEQUENCE):02d}] {entry['id']}")
        built.append(build_segment(entry, index, generated_audio[entry["id"]]))

    concat_file = WORK_DIR / "concat.txt"
    concat_file.write_text(
        "\n".join(f"file '{(WORK_DIR / item['segment_file']).as_posix()}'" for item in built),
        encoding="utf-8",
    )
    raw_video = WORK_DIR / "narrated_without_captions.mp4"
    run([
        str(FFMPEG), "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file),
        "-c", "copy", "-movflags", "+faststart", str(raw_video),
    ])

    cursor = 0.0
    for item in built:
        item["start"] = round(cursor, 3)
        cursor += float(item["duration"])
        item["end"] = round(cursor, 3)
    if cursor > MAX_DURATION_SECONDS:
        raise RuntimeError(
            f"Innovation Studio video is {cursor:.2f}s; limit is {MAX_DURATION_SECONDS:.0f}s."
        )

    write_srt(built)
    run([
        str(FFMPEG), "-y", "-i", str(raw_video), "-i", str(FINAL_CAPTIONS),
        "-map", "0:v:0", "-map", "0:a:0", "-map", "1:0",
        "-c:v", "copy", "-c:a", "copy", "-c:s", "mov_text",
        "-metadata:s:s:0", "language=eng", "-metadata:s:s:0", "title=English",
        "-movflags", "+faststart", str(FINAL_VIDEO),
    ])

    manifest = {
        "video": FINAL_VIDEO.name,
        "captions": FINAL_CAPTIONS.name,
        "resolution": f"{VIDEO_WIDTH}x{VIDEO_HEIGHT}",
        "fps": FPS,
        "duration_seconds": round(cursor, 3),
        "limit_seconds": MAX_DURATION_SECONDS,
        "voice": VOICE,
        "rate": RATE,
        "segments": built,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Video: {FINAL_VIDEO}")
    print(f"Captions: {FINAL_CAPTIONS}")
    print(f"Duration: {cursor:.2f}s ({cursor / 60:.2f} minutes)")
    print(f"Remaining under limit: {MAX_DURATION_SECONDS - cursor:.2f}s")


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()