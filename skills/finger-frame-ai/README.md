# Finger Frame AI

Turn a local video of a two-hand finger-frame gesture into an MP4 where the area inside the fingers reveals an AI-restyled version of the same scene. The pipeline uses Gemini Omni for restyling, MediaPipe for hand tracking, and FFmpeg/OpenCV for compositing while preserving the source audio.

## Requirements

- Python 3.10+
- `ffmpeg` and `ffprobe` available on `PATH`
- A Gemini API key with `gemini-omni-flash-preview` access and quota

Gemini processing may take several minutes and may incur API charges.

## How to use

1. Install AdaL:

   ```bash
   curl -fsSL https://adal.sylph.ai/install.sh | bash
   ```

2. In AdaL, install the skills plugin:

   ```text
   /plugin install SylphAI-Inc/skills
   ```

3. Configure your Gemini API key:

   ```bash
   export GEMINI_API_KEY='YOUR_API_KEY'
   ```

**Final result reference:** [Watch `finger-frame-skill.mov`](./assets/finger-frame-skill.mov)
