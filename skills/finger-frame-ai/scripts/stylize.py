#!/usr/bin/env python3
"""Restyle a video with Gemini Omni Flash (video-to-video editing).

The whole clip is regenerated per the prompt while motion and framing are
preserved, so the result stays aligned with the original footage and
composite.py can use the finger frame as a window over it.

Usage:
    export GEMINI_API_KEY=...   # https://aistudio.google.com/apikey
    python stylize.py finger-effect-raw.mp4 -o stylized.mp4

Docs: https://ai.google.dev/gemini-api/docs/omni
"""

import argparse
import os
import sys
import time

MODEL = "gemini-omni-flash-preview"
DEFAULT_PROMPT = (
    "Transform the person into a 3D animated movie character (stylized CGI "
    "animation look, expressive big eyes, soft lighting). This is a strict "
    "pixel-aligned edit of the source video: keep the same pose, motion, "
    "timing, clothing colors, and background. The camera must not change — "
    "no zoom, no crop, no recentering, and no change to the field of view. "
    "The person's face and body must stay at exactly the same position and "
    "size in the frame as the source: eyes, nose, and mouth must remain at "
    "the same screen coordinates in every frame. Match the facial "
    "expression exactly, frame by frame: preserve the exact degree of "
    "mouth openness at every moment — if the mouth is slightly open and "
    "still, keep it slightly open and still; do not close it, and do not "
    "add talking or any mouth movement that is not in the source. Mirror "
    "blinks, gaze direction, and eyebrow position at the same moments as "
    "the source. Change only the visual style, nothing about the geometry, "
    "composition, or performance."
)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("video", nargs="?", default="finger-effect-raw.mp4")
    ap.add_argument("-o", "--output", default="stylized.mp4")
    ap.add_argument("-p", "--prompt", default=DEFAULT_PROMPT)
    args = ap.parse_args()

    if not (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")):
        sys.exit("Set GEMINI_API_KEY first — https://aistudio.google.com/apikey")
    if not os.path.exists(args.video):
        sys.exit(f"Input video not found: {args.video}")

    from google import genai  # imported late so --help works without the dep

    client = genai.Client()

    print(f"Uploading {args.video} …")
    video_file = client.files.upload(file=args.video)
    while getattr(video_file, "state", "") and "PROCESS" in str(video_file.state):
        time.sleep(3)
        video_file = client.files.get(name=video_file.name)
    print(f"Uploaded: {video_file.uri}")

    print(f"Generating with {MODEL} (typically a few minutes) …")
    interaction = client.interactions.create(
        model=MODEL,
        input=[
            {"type": "document", "uri": video_file.uri},
            {"type": "text", "text": args.prompt},
        ],
    )

    # Poll if the interaction reports as still running.
    waited = 0
    while (
        str(getattr(interaction, "status", "")).lower()
        in ("pending", "in_progress", "processing", "running", "queued")
        and waited < 900
    ):
        time.sleep(5)
        waited += 5
        interaction = client.interactions.get(id=interaction.id)
        print(f"  … {waited}s ({interaction.status})")

    video_out = getattr(interaction, "output_video", None)
    if video_out is None:
        sys.exit(f"No video in response — raw interaction:\n{interaction}")

    data = getattr(video_out, "data", None)
    if data:
        import base64

        with open(args.output, "wb") as f:
            f.write(base64.b64decode(data) if isinstance(data, str) else data)
    else:
        uri = getattr(video_out, "uri", None)
        if not uri:
            sys.exit(f"No data or uri on output video:\n{video_out}")
        name = "files/" + uri.split("/files/")[1].split("?")[0] if "/files/" in uri else uri
        for _ in range(120):
            f = client.files.get(name=name)
            if "ACTIVE" in str(getattr(f, "state", "")):
                break
            time.sleep(5)
        print("Downloading result …")
        client.files.download(file=f, path=args.output) if hasattr(
            client.files, "download"
        ) else None
        if not os.path.exists(args.output):
            blob = client.files.download(file=f)
            with open(args.output, "wb") as out:
                out.write(blob)

    print(f"Done: {args.output}")


if __name__ == "__main__":
    main()
