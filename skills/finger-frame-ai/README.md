# Finger Frame AI

Turn a local video of a two-hand finger-frame gesture into an MP4 where the area inside the fingers reveals an AI-restyled version of the same scene. The pipeline uses Gemini Omni for restyling, MediaPipe for hand tracking, and FFmpeg/OpenCV for compositing while preserving the source audio.

## Requirements

- Python 3.10+
- `ffmpeg` and `ffprobe` available on `PATH`
- A Gemini API key with `gemini-omni-flash-preview` access and quota

Set the key locally—never paste it into chat or commit it:

```bash
export GEMINI_API_KEY='YOUR_API_KEY'
```

Gemini processing may take several minutes and may incur API charges.

## How to use

1. Clone the repository and enter the skill directory:

   ```bash
   git clone https://github.com/SylphAI-Inc/skills.git
   cd skills/skills/finger-frame-ai
   ```

2. Check that Python, FFmpeg, and your API key are ready:

   ```bash
   python3 scripts/process.py --check
   ```

3. Run the pipeline with an absolute path to your video:

   ```bash
   python3 scripts/process.py "/absolute/path/to/input.mov"
   ```

   For a custom visual style:

   ```bash
   python3 scripts/process.py "/absolute/path/to/input.mov" \
     --prompt "Transform the scene into hand-painted watercolor animation while preserving the original motion and framing."
   ```

4. Find the finished video beside the source as:

   ```text
   input-finger-frame.mp4
   ```

   The original video is not modified. For best tracking, keep both hands visible with the index fingers and thumbs forming opposing “L” shapes.

**Final result reference:** [Watch `finger-frame-skill.mov`](./assets/finger-frame-skill.mov)
