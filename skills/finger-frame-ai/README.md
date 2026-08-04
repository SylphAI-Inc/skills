# Finger Frame AI

Create a video where a two-hand finger-frame gesture reveals an AI-restyled version of the scene.

The effect and processing pipeline originate from
[`sophiamyang/finger-frame-effect-ai`](https://github.com/sophiamyang/finger-frame-effect-ai).

This skill bundles a guided Python runner that:

- Creates an isolated virtual environment.
- Uses Gemini Omni to restyle the source timeline.
- Tracks both hands with MediaPipe.
- Composites the restyled clip inside the finger frame with FFmpeg/OpenCV.
- Preserves source audio and leaves the original untouched.

## Requirements

- Python 3.10+
- `ffmpeg` and `ffprobe` on `PATH`
- A Gemini API key with `gemini-omni-flash-preview` access and quota

Configure the key locally:

```bash
export GEMINI_API_KEY='...'
```

Then ask AdaL to apply the Finger Frame AI effect to an absolute local video path. Gemini video generation may take several minutes and may incur API charges.
