"""Assemble narrated slides and browser recordings into the final product demo MP4."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import imageio_ffmpeg

ROOT = Path(__file__).resolve().parents[1]
DEMO_DIR = ROOT / "docs" / "demo"
VIDEO_DIR = DEMO_DIR / "video"
AUDIO_DIR = VIDEO_DIR / "audio"
BROWSER_DIR = VIDEO_DIR / "browser"
RENDER_DIR = ROOT / "test-results" / "demo-deck-render-v2"
WORK_DIR = ROOT / "test-results" / "demo-video-build"
FINAL_VIDEO = VIDEO_DIR / "Azure_Migrate_AI_Feasibility_Product_Demo.mp4"
FINAL_CAPTIONS = VIDEO_DIR / "Azure_Migrate_AI_Feasibility_Product_Demo.srt"
MANIFEST_PATH = VIDEO_DIR / "video_manifest.json"
FFMPEG = Path(imageio_ffmpeg.get_ffmpeg_exe())

PADDING_SECONDS = 1.0
VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
FPS = 30

SEQUENCE: list[dict[str, Any]] = [
    {"id": "slide_01", "visual_type": "image", "visual": "Slide1.PNG"},
    {"id": "slide_02", "visual_type": "image", "visual": "Slide2.PNG"},
    {"id": "slide_03", "visual_type": "image", "visual": "Slide3.PNG"},
    {"id": "slide_04", "visual_type": "image", "visual": "Slide4.PNG"},
    {"id": "slide_05", "visual_type": "image", "visual": "Slide5.PNG"},
    {"id": "slide_06", "visual_type": "image", "visual": "Slide6.PNG"},
    {"id": "slide_07", "visual_type": "image", "visual": "Slide7.PNG"},
    {
        "id": "live_02",
        "visual_type": "video",
        "visual": "live_02_application_groups.webm",
        "visual_start": 3.0,
        "visual_end": 9.6,
    },
    {
        "id": "live_03",
        "visual_type": "video",
        "visual": "live_03_base_architecture.webm",
        "visual_start": 3.0,
        "visual_end": 10.5,
    },
    {
        "id": "live_04",
        "visual_type": "video",
        "visual": "live_04_application_selection.webm",
        "visual_start": 3.3,
        "visual_end": 13.9,
    },
    {
        "id": "live_05",
        "visual_type": "video",
        "visual": "live_05_intent_outcome.webm",
        "visual_start": 2.0,
        "visual_end": 12.8,
    },
    {
        "id": "live_06",
        "visual_type": "video",
        "visual": "live_06_decision_pack.webm",
        "visual_start": 14.5,
        "visual_end": 37.2,
    },
    {
        "id": "live_07",
        "visual_type": "video",
        "visual": "live_07_ai_ready_architecture.webm",
        "visual_start": 4.0,
        "visual_end": 15.8,
    },
    {"id": "slide_08", "visual_type": "image", "visual": "Slide8.PNG"},
    {"id": "slide_09", "visual_type": "image", "visual": "Slide9.PNG"},
    {"id": "slide_10", "visual_type": "image", "visual": "Slide10.PNG"},
]


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


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


def sentence_chunks(
    text: str,
    maximum_words: int = 12,
    maximum_characters: int = 84,
) -> list[str]:
    words = text.split()
    chunks: list[str] = []
    current: list[str] = []
    for word in words:
        candidate = " ".join([*current, word])
        if current and (
            len(current) >= maximum_words
            or len(candidate) > maximum_characters
        ):
            chunks.append(" ".join(current))
            current = []
        current.append(word)
        sentence_end = word.rstrip('”\"').endswith((".", "?", "!", ":"))
        if sentence_end:
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
        if not chunks:
            continue
        duration = entry["audio_duration"]
        total_words = sum(len(chunk.split()) for chunk in chunks)
        cursor = entry["start"]
        for chunk_index, chunk in enumerate(chunks):
            ratio = len(chunk.split()) / max(total_words, 1)
            chunk_duration = duration * ratio
            end = cursor + chunk_duration
            if chunk_index == len(chunks) - 1:
                end = entry["start"] + duration
            blocks.append(
                f"{index}\n{timestamp(cursor)} --> {timestamp(end)}\n{chunk}\n"
            )
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
    if source_duration <= 0:
        raise RuntimeError(f"Empty browser recording: {source}")
    visual_start = max(0.0, float(entry.get("visual_start", 0.0)))
    visual_end = min(source_duration, float(entry.get("visual_end", source_duration)))
    selected_duration = visual_end - visual_start
    if selected_duration <= 0:
        raise RuntimeError(f"Invalid visual range for {source}: {visual_start}..{visual_end}")
    speed = selected_duration / duration
    # Clamp protects against invalid setpts values if a narration segment is unexpectedly tiny.
    speed = max(speed, 0.01)
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


def build_segment(entry: dict[str, Any], index: int, audio_meta: dict[str, Any]) -> dict[str, Any]:
    audio = AUDIO_DIR / audio_meta["media"]
    audio_duration = float(audio_meta["duration_seconds"])
    duration = audio_duration + PADDING_SECONDS
    visual_path = WORK_DIR / f"visual_{index:02d}.mp4"
    segment_path = WORK_DIR / f"segment_{index:02d}.mp4"
    padded_audio = WORK_DIR / f"audio_{index:02d}.m4a"

    build_visual(entry, visual_path, duration)
    run([
        str(FFMPEG), "-y", "-i", str(audio),
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
        "audio_duration": audio_duration,
        "duration": duration,
        "text": audio_meta["text"],
    }


def main() -> None:
    VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    for path in WORK_DIR.iterdir():
        if path.is_file():
            path.unlink()
        elif path.is_dir():
            shutil.rmtree(path)

    audio_manifest = json.loads((AUDIO_DIR / "segments.json").read_text(encoding="utf-8"))
    audio_by_id = {item["id"]: item for item in audio_manifest["segments"]}

    built: list[dict[str, Any]] = []
    for index, entry in enumerate(SEQUENCE, 1):
        print(f"[{index:02d}/{len(SEQUENCE):02d}] {entry['id']}")
        built.append(build_segment(entry, index, audio_by_id[entry["id"]]))

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
        item["start"] = cursor
        item["end"] = cursor + item["duration"]
        cursor = item["end"]
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
        "voice": audio_manifest["voice"],
        "assessment_id": json.loads((BROWSER_DIR / "manifest.json").read_text())["assessment_id"],
        "segments": built,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Video: {FINAL_VIDEO}")
    print(f"Captions: {FINAL_CAPTIONS}")
    print(f"Duration: {cursor / 60:.2f} minutes")


if __name__ == "__main__":
    main()
