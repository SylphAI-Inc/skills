#!/usr/bin/env python3
"""Composite an AI-restyled video inside a tracked finger frame.

Tracks the finger-frame gesture (both hands, index + thumb "L"s) in the
original footage with MediaPipe Hand Landmarker, then reveals the stylized
video through the quad the fingers form — the same window effect as the
finger-frame-effect web app, with the dashed outline and corner dots.

The tracking logic is a direct port of the web app's audited pipeline:
anatomical corner ordering (crossed fingers = bowtie), spread/area gates
with hysteresis, teleport rejection, velocity-adaptive smoothing, dropout
hold, and presence fade.

Usage:
    python composite.py finger-effect-raw.mp4 stylized.mp4 -o final.mp4
"""

import argparse
import math
import os
from pathlib import Path
import subprocess
import sys
import urllib.request

import cv2
import numpy as np

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/1/hand_landmarker.task"
)
MODEL_PATH = Path(__file__).resolve().parent.parent / "hand_landmarker.task"

WRIST, THUMB_TIP, INDEX_TIP, MIDDLE_MCP = 0, 4, 8, 9

# Tracking constants — mirror main.js in the web app.
MAX_LOST_FRAMES = 25
JUMP_CONFIRM_FRAMES = 2
JUMP_FRACTION = 0.3
ALPHA_MIN, ALPHA_MAX = 0.35, 0.85
ALPHA_SCALE = 0.05
PRESENCE_IN, PRESENCE_OUT = 0.12, 0.05
SPREAD_ACQUIRE, SPREAD_KEEP = 0.75, 0.2
AREA_ACQUIRE, AREA_KEEP = 0.005, 0.0005


def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def lerp_pt(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def polygon_area(pts):
    a = 0.0
    for i in range(len(pts)):
        p, q = pts[i], pts[(i + 1) % len(pts)]
        a += p[0] * q[1] - q[0] * p[1]
    return abs(a / 2)


def angle_sorted(pts):
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    return sorted(pts, key=lambda p: math.atan2(p[1] - cy, p[0] - cx))


class FrameTracker:
    """Stateful quad tracker, ported from the web app's main loop."""

    def __init__(self, width, height):
        self.w, self.h = width, height
        self.corners = None
        self.presence = 0.0
        self.frame_active = False
        self.lost_frames = 0
        self.jump_frames = 0

    def compute_quad(self, hands):
        """hands: list of landmark lists (normalized). Returns anatomical quad
        [A.index, B.index, B.thumb, A.thumb] (A = smaller wrist x) or None."""
        if len(hands) != 2:
            return None
        info = []
        for lm in hands:
            px = lambda i: (lm[i].x * self.w, lm[i].y * self.h)
            index, thumb = px(INDEX_TIP), px(THUMB_TIP)
            scale = dist(px(WRIST), px(MIDDLE_MCP)) + 1
            needed = SPREAD_KEEP if self.frame_active else SPREAD_ACQUIRE
            if dist(thumb, index) < scale * needed:
                return None
            info.append({"index": index, "thumb": thumb, "wx": px(WRIST)[0]})
        info.sort(key=lambda hd: hd["wx"])
        a, b = info
        pts = [a["index"], b["index"], b["thumb"], a["thumb"]]
        min_area = AREA_KEEP if self.frame_active else AREA_ACQUIRE
        if polygon_area(angle_sorted(pts)) < self.w * self.h * min_area:
            return None
        return pts

    def update(self, hands):
        target = self.compute_quad(hands) if hands else None

        if target:
            if self.corners is None:
                self.lost_frames = 0
                self.frame_active = True
                self.jump_frames = 0
                self.corners = target
                self.presence = min(1.0, self.presence + PRESENCE_IN)
            else:
                moved = sum(dist(p, c) for p, c in zip(target, self.corners)) / 4
                if (
                    moved > self.w * JUMP_FRACTION
                    and self.jump_frames + 1 < JUMP_CONFIRM_FRAMES
                ):
                    self.jump_frames += 1
                    self.lost_frames += 1
                    if self.lost_frames > MAX_LOST_FRAMES:
                        self.presence = max(0.0, self.presence - PRESENCE_OUT)
                else:
                    self.lost_frames = 0
                    self.frame_active = True
                    self.jump_frames = 0
                    alpha = min(
                        ALPHA_MAX, max(ALPHA_MIN, moved / (self.w * ALPHA_SCALE))
                    )
                    self.corners = [
                        lerp_pt(c, p, alpha) for c, p in zip(self.corners, target)
                    ]
                    self.presence = min(1.0, self.presence + PRESENCE_IN)
        elif self.corners is not None and self.lost_frames < MAX_LOST_FRAMES:
            self.lost_frames += 1
            self.presence = min(1.0, self.presence + PRESENCE_IN)
        else:
            self.presence = max(0.0, self.presence - PRESENCE_OUT)
            if self.presence == 0:
                self.corners = None
                self.frame_active = False
                self.jump_frames = 0

        return self.corners if self.presence > 0.01 else None


def draw_outline(frame, quad, presence, t):
    """Dashed marching-ants outline + pulsing corner dots, like the web app."""
    overlay = frame.copy()

    # Dashed edges with a marching offset.
    dash_on, dash_off = 10.0, 8.0
    period = dash_on + dash_off
    offset = (t * 40.0) % period
    for i in range(4):
        p0 = np.array(quad[i], dtype=float)
        p1 = np.array(quad[(i + 1) % 4], dtype=float)
        seg = p1 - p0
        length = float(np.hypot(*seg))
        if length < 1:
            continue
        u = seg / length
        s = -offset
        while s < length:
            a = max(0.0, s)
            b = min(length, s + dash_on)
            if b > a:
                pa = (p0 + u * a).astype(int)
                pb = (p0 + u * b).astype(int)
                cv2.line(overlay, tuple(pa), tuple(pb), (242, 242, 242), 2, cv2.LINE_AA)
            s += period

    # Corner dots with pulse + expanding halo.
    for i, p in enumerate(quad):
        c = (int(p[0]), int(p[1]))
        r = 7 + math.sin(t * 3 + i * 1.5) * 1.5
        halo = (t * 0.8 + i * 0.25) % 1.0
        halo_val = int(255 * 0.5 * (1 - halo))
        cv2.circle(overlay, c, int(r + halo * 14), (halo_val,) * 3, 2, cv2.LINE_AA)
        cv2.circle(overlay, c, int(r), (255, 255, 255), -1, cv2.LINE_AA)
        cv2.circle(overlay, c, int(r), (60, 60, 60), 1, cv2.LINE_AA)

    cv2.addWeighted(overlay, presence, frame, 1 - presence, 0, dst=frame)


def ensure_model():
    if not os.path.exists(MODEL_PATH):
        print("Downloading hand landmarker model …")
        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("original", nargs="?", default="finger-effect-raw.mp4")
    ap.add_argument("stylized", nargs="?", default="stylized.mp4")
    ap.add_argument("-o", "--output", default="final.mp4")
    args = ap.parse_args()

    for f in (args.original, args.stylized):
        if not os.path.exists(f):
            sys.exit(f"Missing input: {f}")
    ensure_model()

    import mediapipe as mp
    from mediapipe.tasks import python as mp_tasks
    from mediapipe.tasks.python import vision

    cap = cv2.VideoCapture(args.original)
    sty = cv2.VideoCapture(args.stylized)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    sty_fps = sty.get(cv2.CAP_PROP_FPS) or fps
    sty_count = int(sty.get(cv2.CAP_PROP_FRAME_COUNT))

    landmarker = vision.HandLandmarker.create_from_options(
        vision.HandLandmarkerOptions(
            base_options=mp_tasks.BaseOptions(model_asset_path=str(MODEL_PATH)),
            running_mode=vision.RunningMode.VIDEO,
            num_hands=2,
            min_hand_detection_confidence=0.3,
            min_hand_presence_confidence=0.3,
            min_tracking_confidence=0.3,
        )
    )

    # Pipe frames straight into ffmpeg for a proper H.264 output.
    ff = subprocess.Popen(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{w}x{h}",
            "-r", f"{fps}", "-i", "-",
            "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
            args.output,
        ],
        stdin=subprocess.PIPE,
    )

    tracker = FrameTracker(w, h)
    sty_frames = []
    i = 0
    tracked = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break

        # Cache stylized frames lazily (they're reused when fps differ).
        t = i / fps
        j = min(int(round(t * sty_fps)), max(sty_count - 1, 0))
        while len(sty_frames) <= j:
            ok_s, sf = sty.read()
            if not ok_s:
                break
            if sf.shape[:2] != (h, w):
                sf = cv2.resize(sf, (w, h))
            sty_frames.append(sf)
        sty_frame = sty_frames[min(j, len(sty_frames) - 1)] if sty_frames else None

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = landmarker.detect_for_video(
            mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb),
            int(i * 1000 / fps),
        )
        quad = tracker.update(result.hand_landmarks or [])

        if quad is not None and sty_frame is not None:
            tracked += 1
            mask = np.zeros((h, w), dtype=np.uint8)
            cv2.fillPoly(mask, [np.array(quad, dtype=np.int32)], 255)
            m = (mask.astype(np.float32) / 255.0 * tracker.presence)[..., None]
            frame = (
                frame.astype(np.float32) * (1 - m)
                + sty_frame.astype(np.float32) * m
            ).astype(np.uint8)
            draw_outline(frame, quad, tracker.presence, t)

        ff.stdin.write(frame.tobytes())
        i += 1
        if i % 30 == 0:
            print(f"  frame {i}, frame visible on {tracked} frames so far")

    ff.stdin.close()
    ff.wait()
    cap.release()
    sty.release()

    # Carry over the original audio track if there is one.
    has_audio = (
        subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries",
             "stream=codec_type", "-of", "csv=p=0", args.original],
            capture_output=True, text=True,
        ).stdout.strip() != ""
    )
    if has_audio:
        tmp = args.output + ".mux.mp4"
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", args.output,
             "-i", args.original, "-map", "0:v", "-map", "1:a",
             "-c:v", "copy", "-c:a", "aac", "-shortest", tmp],
            check=True,
        )
        os.replace(tmp, args.output)

    print(f"Done: {args.output} ({i} frames, finger frame visible on {tracked})")


if __name__ == "__main__":
    main()
