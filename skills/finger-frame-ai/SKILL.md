---
name: finger-frame-ai
description: "Generate a finished cyberpunk-styled finger-frame effect video from a local clip using Gemini Omni restyling, MediaPipe hand tracking, and FFmpeg compositing. Use when someone asks to make, create, restyle, or process a video where a two-hand finger-frame becomes a window into an AI-stylized (default: neon cyberpunk CGI) world."
author: shangliy
version: 1.0.0
---

# Finger Frame AI

Turn a local video of the two-hand finger-frame gesture into an H.264 MP4 where the area inside the fingers reveals an AI-restyled version of the scene.

The bundled pipeline uses:

1. **Gemini Omni** to restyle the existing clip while asking it to preserve timing, motion, framing, pose, and expression.
2. **MediaPipe Hand Landmarker** to track both index fingers and thumbs.
3. **FFmpeg/OpenCV** to composite the restyled video into the tracked quadrilateral and retain source audio.

## When to Use

Trigger when the user asks to:

- Apply a finger-frame, hand-frame, or fingers-as-a-window video effect.
- Put an anime, claymation, watercolor, CGI, or custom AI world inside a finger gesture.
- Run the Finger Frame AI video pipeline on a local clip.

Do not substitute Veo video generation. This effect needs a restyled version of the existing timeline so it can align with hand tracking from the source.

## Required Input and Consent

Ask for the **absolute local source-video path** if it was not supplied.

The Gemini Omni request can take several minutes and may incur Google API charges. Before calling it, clearly state that and obtain confirmation unless the user already authorized the paid generation in the current conversation.

A key with `gemini-omni-flash-preview` access and quota is required. Never ask the user to paste a key into chat. Ask them to configure it in the terminal that launches AdaL:

```bash
export GEMINI_API_KEY='...'
```

`GOOGLE_API_KEY` is also supported. Never print, log, commit, or place a key in command arguments.

## Instructions

Set `<skill>` to this skill directory, then perform these steps.

### 1. Check readiness

```bash
python3 <skill>/scripts/process.py --check
```

This check does not install packages, upload media, or call Gemini. If FFmpeg is missing, tell the user to install `ffmpeg` and `ffprobe`; do not attempt privileged installation.

### 2. Validate the source

Confirm the file exists. The clip should clearly show two hands forming opposing index-and-thumb “L” shapes. Preserve the original file.

Short clips are faster and cheaper. Sources larger than 15 MB are automatically compressed to a temporary 720p H.264 upload copy; the original remains untouched.

### 3. Generate

Default cyberpunk-styled 3D animated-movie look:

```bash
python3 <skill>/scripts/process.py "/absolute/path/to/input.mov"
```

Custom style:

```bash
python3 <skill>/scripts/process.py "/absolute/path/to/input.mov" \
  --prompt "Transform the scene into hand-painted watercolor animation while preserving the original motion and framing."
```

Optional output controls:

```bash
python3 <skill>/scripts/process.py input.mp4 \
  --output /absolute/path/to/result.mp4 \
  --keep-stylized
```

The runner automatically:

- Creates/reuses `<skill>/.venv`.
- Installs bundled Python requirements when missing.
- Prompts for a hidden, non-persisted key only in an interactive terminal.
- Creates and cleans up an oversized-source working copy.
- Runs Gemini Omni restyling and local finger-frame compositing.
- Deletes the intermediate fully stylized video unless `--keep-stylized` is set.
- Writes the default result beside the source as `<source>-finger-frame.mp4`.

In headless AdaL, always provide the video path and set the key in AdaL's launching environment because hidden prompts require a terminal.

### 4. Verify and report

After completion, run `ffprobe` on the final file. Report:

- Absolute output path
- Duration
- Resolution and frame rate
- Video/audio codecs
- File size

Do not claim success unless the file exists, is non-empty, and FFmpeg can decode it without errors.

## Error Handling

- **HTTP 429 / quota 0:** Stop. Ask the user to enable billing/quota or configure another key. Do not retry repeatedly.
- **Authentication failure:** Ask the user to replace the locally configured key. Never request it in chat.
- **No tracked frame:** Explain that both hands and spread index/thumb shapes must be visible.
- **Large upload still exceeds limit:** Ask the user to trim the clip or explicitly choose a larger `--max-upload-mb` only if their API supports it.
- **Generation drift:** Explain that Omni is generative and cannot guarantee mathematical frame-perfect alignment.
- **Interrupted run:** Preserve the original and remove only pipeline-created temporary media.
