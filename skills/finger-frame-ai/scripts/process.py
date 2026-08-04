#!/usr/bin/env python3
"""Run the complete Finger Frame AI pipeline with guided setup."""

import argparse
import getpass
import os
from pathlib import Path
import shutil
import subprocess
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
VENV_DIR = SKILL_DIR / ".venv"
REQUIREMENTS = SCRIPT_DIR / "requirements.txt"
STYLIZE_SCRIPT = SCRIPT_DIR / "stylize.py"
COMPOSITE_SCRIPT = SCRIPT_DIR / "composite.py"
VENV_MARKER = "FINGER_FRAME_VENV_READY"
DEFAULT_MAX_UPLOAD_MB = 15
AUDIO_BITRATE_KBPS = 128


def venv_python(venv_dir=VENV_DIR):
    return venv_dir / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def run_command(command, *, env=None):
    print("+", " ".join(map(str, command)))
    subprocess.run([str(part) for part in command], check=True, env=env)


def dependencies_available():
    try:
        import cv2  # noqa: F401
        import mediapipe  # noqa: F401
        import numpy  # noqa: F401
        from google import genai

        if not hasattr(genai.Client, "interactions"):
            return False
    except (ImportError, TypeError):
        return False
    return True


def ensure_environment():
    """Create the project virtual environment and re-exec inside it if needed."""
    if os.environ.get(VENV_MARKER) == "1" and dependencies_available():
        return

    python = venv_python()
    if not python.exists():
        print(f"Creating virtual environment at {VENV_DIR} …")
        run_command([sys.executable, "-m", "venv", VENV_DIR])

    check = subprocess.run(
        [
            str(python),
            "-c",
            (
                "import cv2, mediapipe, numpy; from google import genai; "
                "assert hasattr(genai.Client, 'interactions')"
            ),
        ],
        capture_output=True,
    )
    if check.returncode != 0:
        print("Installing Python dependencies …")
        run_command([python, "-m", "pip", "install", "-r", REQUIREMENTS])

    env = os.environ.copy()
    env[VENV_MARKER] = "1"
    os.execve(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]], env)


def resolve_video(value):
    while not value:
        if not sys.stdin.isatty():
            raise SystemExit("Provide a local video path as the first argument.")
        value = input("Local video path: ").strip()

    video = Path(value).expanduser().resolve()
    if not video.is_file():
        raise SystemExit(f"Input video not found: {video}")
    return video


def resolve_api_key():
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if key:
        return key
    if not sys.stdin.isatty():
        raise SystemExit(
            "Set GEMINI_API_KEY or GOOGLE_API_KEY before running in headless mode."
        )
    key = getpass.getpass("Gemini API key (hidden, not saved): ").strip()
    if not key:
        raise SystemExit("A Gemini API key is required.")
    return key


def default_output(video):
    return video.parent / f"{video.stem}-finger-frame.mp4"


def probe_duration(video):
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(video),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(result.stdout.strip())


def prepare_upload(video, output_dir, max_upload_mb):
    max_bytes = int(max_upload_mb * 1_000_000)
    if video.stat().st_size <= max_bytes:
        return video, False

    duration = probe_duration(video)
    if duration <= 0:
        raise SystemExit("Could not determine a valid source-video duration.")

    target_total_kbps = max_bytes * 8 * 0.94 / duration / 1000
    video_kbps = max(300, int(target_total_kbps - AUDIO_BITRATE_KBPS))
    working = output_dir / f"{video.stem}-working-720p.mp4"

    print(
        f"Source exceeds {max_upload_mb:g} MB; creating a 720p upload copy at "
        f"{working} …"
    )
    run_command(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-i",
            video,
            "-map",
            "0:v:0",
            "-map",
            "0:a:0?",
            "-vf",
            "scale=-2:720",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-b:v",
            f"{video_kbps}k",
            "-c:a",
            "aac",
            "-b:a",
            f"{AUDIO_BITRATE_KBPS}k",
            "-movflags",
            "+faststart",
            working,
        ]
    )
    if working.stat().st_size > max_bytes:
        working.unlink()
        raise SystemExit(
            "The compressed upload is still too large. Trim the source clip or "
            "raise --max-upload-mb if your Gemini quota supports larger files."
        )
    return working, True


def check_readiness():
    missing = [
        command for command in ("ffmpeg", "ffprobe") if shutil.which(command) is None
    ]
    print(f"Python: {sys.version.split()[0]}")
    print(f"ffmpeg: {'missing' if 'ffmpeg' in missing else 'ready'}")
    print(f"ffprobe: {'missing' if 'ffprobe' in missing else 'ready'}")
    print(f"virtualenv: {'ready' if venv_python().exists() else 'will be created'}")
    print(
        "Gemini key: "
        + (
            "configured"
            if os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
            else "not configured"
        )
    )
    return not missing


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", nargs="?", help="Path to the source video")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check local prerequisites without installing or generating anything",
    )
    parser.add_argument("-o", "--output", help="Final MP4 path")
    parser.add_argument("-p", "--prompt", help="Custom video restyling prompt")
    parser.add_argument(
        "--keep-stylized",
        action="store_true",
        help="Keep the intermediate fully stylized video",
    )
    parser.add_argument(
        "--max-upload-mb",
        type=float,
        default=DEFAULT_MAX_UPLOAD_MB,
        help=f"Compress sources larger than this many MB (default: {DEFAULT_MAX_UPLOAD_MB})",
    )
    return parser


def main():
    args = build_parser().parse_args()
    if args.check:
        raise SystemExit(0 if check_readiness() else 1)

    video = resolve_video(args.video)

    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        raise SystemExit("ffmpeg and ffprobe must be installed and available on PATH.")

    ensure_environment()
    key = resolve_api_key()

    output = (
        Path(args.output).expanduser().resolve()
        if args.output
        else default_output(video)
    )
    if output == video:
        raise SystemExit("Output path must be different from the source video.")

    output.parent.mkdir(parents=True, exist_ok=True)
    stylized = output.with_name(f"{output.stem}-stylized.mp4")
    upload, upload_is_temporary = prepare_upload(
        video, output.parent, args.max_upload_mb
    )

    env = os.environ.copy()
    env["GEMINI_API_KEY"] = key

    stylize_command = [
        sys.executable,
        STYLIZE_SCRIPT,
        upload,
        "-o",
        stylized,
    ]
    if args.prompt:
        stylize_command.extend(["--prompt", args.prompt])

    try:
        run_command(stylize_command, env=env)
        run_command(
            [
                sys.executable,
                COMPOSITE_SCRIPT,
                upload,
                stylized,
                "-o",
                output,
            ],
            env=env,
        )
    except subprocess.CalledProcessError as exc:
        raise SystemExit(f"Pipeline stage failed with exit code {exc.returncode}.") from exc
    finally:
        if stylized.exists() and not args.keep_stylized:
            stylized.unlink()
        if upload_is_temporary and upload.exists():
            upload.unlink()

    print(f"Finger-frame video ready: {output}")


if __name__ == "__main__":
    main()
