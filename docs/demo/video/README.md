# AI Feasibility Assessment product demo video

## Final deliverables

- `Azure_Migrate_AI_Feasibility_Product_Demo.mp4` — 1920×1080, 30 fps, H.264 video, AAC narration, and embedded English subtitles.
- `Azure_Migrate_AI_Feasibility_Product_Demo.srt` — editable sidecar captions.
- `video_manifest.json` — scene order, timing, narration, and the temporary recording assessment ID.

The finished demo is approximately 10 minutes and combines the validated PowerPoint deck with an automated live walkthrough of the running simulator. Live footage carries the label `Simulator prototype · Proposed Azure Migrate experience`.

## Source media

- `audio/` — neural narration MP3 and WebVTT tracks generated with `en-US-AvaMultilingualNeural`.
- `browser/` — Playwright WebM recordings of the live product scenes.

## Reproduce the video

1. Start the simulator at `http://127.0.0.1:5000` with discovery data loaded and no saved BPTco assessment revision.
2. Regenerate and render the PowerPoint deck with `scripts/generate_ai_feasibility_demo_deck.py` and native PowerPoint.
3. Generate narration:

   `python scripts/generate_ai_feasibility_demo_audio.py`

4. Record the live product walkthrough:

   `node scripts/record_ai_feasibility_demo.mjs`

5. Assemble the final MP4 and captions:

   `python scripts/build_ai_feasibility_demo_video.py`

The recording script creates a temporary AI Feasibility Assessment revision so it can capture the AI-ready architecture. Delete only that exact revision after recording; its ID is stored in `browser/manifest.json`.
