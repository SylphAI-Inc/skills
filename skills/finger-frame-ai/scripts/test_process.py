import os
from pathlib import Path
import subprocess
import tempfile
import types
import unittest
from unittest import mock

import process


class ProcessTests(unittest.TestCase):
    def test_default_output_uses_source_directory(self):
        output = process.default_output(Path("/tmp/My Clip.MOV"))
        self.assertEqual(output, Path("/tmp/My Clip-finger-frame.mp4"))

    def test_resolve_video_rejects_missing_path(self):
        with self.assertRaisesRegex(SystemExit, "Input video not found"):
            process.resolve_video("/definitely/missing/video.mp4")

    def test_resolve_api_key_prefers_gemini_key(self):
        with mock.patch.dict(
            os.environ,
            {"GEMINI_API_KEY": "gemini-key", "GOOGLE_API_KEY": "google-key"},
            clear=True,
        ):
            self.assertEqual(process.resolve_api_key(), "gemini-key")

    def test_resolve_api_key_requires_env_when_headless(self):
        with (
            mock.patch.dict(os.environ, {}, clear=True),
            mock.patch.object(process.sys.stdin, "isatty", return_value=False),
            self.assertRaisesRegex(SystemExit, "headless mode"),
        ):
            process.resolve_api_key()

    def test_check_readiness_reports_missing_binary(self):
        with mock.patch.object(
            process.shutil,
            "which",
            side_effect=lambda command: None if command == "ffmpeg" else "/bin/ffprobe",
        ):
            self.assertFalse(process.check_readiness())

    def test_dependencies_reject_client_without_interactions(self):
        google = types.ModuleType("google")
        google.genai = types.SimpleNamespace(Client=type("Client", (), {}))
        modules = {
            "cv2": types.ModuleType("cv2"),
            "mediapipe": types.ModuleType("mediapipe"),
            "numpy": types.ModuleType("numpy"),
            "google": google,
        }
        with mock.patch.dict(process.sys.modules, modules):
            self.assertFalse(process.dependencies_available())

    def test_dependencies_accept_client_with_interactions(self):
        google = types.ModuleType("google")
        google.genai = types.SimpleNamespace(
            Client=type("Client", (), {"interactions": property(lambda self: None)})
        )
        modules = {
            "cv2": types.ModuleType("cv2"),
            "mediapipe": types.ModuleType("mediapipe"),
            "numpy": types.ModuleType("numpy"),
            "google": google,
        }
        with mock.patch.dict(process.sys.modules, modules):
            self.assertTrue(process.dependencies_available())

    def test_environment_probe_checks_interactions_capability(self):
        with (
            mock.patch.object(
                process, "venv_python", return_value=Path(process.sys.executable)
            ),
            mock.patch.object(process.subprocess, "run") as run,
            mock.patch.object(process.os, "execve", side_effect=RuntimeError("stop")),
            self.assertRaisesRegex(RuntimeError, "stop"),
        ):
            run.return_value.returncode = 0
            process.ensure_environment()

        probe = run.call_args.args[0]
        self.assertIn("hasattr", probe[2])
        self.assertIn("interactions", probe[2])

    def test_failed_capability_probe_installs_requirements(self):
        with (
            mock.patch.object(
                process, "venv_python", return_value=Path(process.sys.executable)
            ),
            mock.patch.object(process.subprocess, "run") as run,
            mock.patch.object(process, "run_command") as install,
            mock.patch.object(process.os, "execve", side_effect=RuntimeError("stop")),
            self.assertRaisesRegex(RuntimeError, "stop"),
        ):
            run.return_value.returncode = 1
            process.ensure_environment()

        install.assert_called_once_with(
            [
                Path(process.sys.executable),
                "-m",
                "pip",
                "install",
                "-r",
                process.REQUIREMENTS,
            ]
        )

    def test_prepare_upload_keeps_small_video(self):
        with tempfile.TemporaryDirectory() as directory:
            video = Path(directory) / "small.mp4"
            video.write_bytes(b"small")
            self.assertEqual(
                process.prepare_upload(video, Path(directory), 15), (video, False)
            )

    def test_prepare_upload_compresses_large_video(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            video = root / "large.mov"
            video.write_bytes(b"x" * 101)
            working = root / "large-working-720p.mp4"

            def create_working(*args, **kwargs):
                working.write_bytes(b"x" * 80)

            with (
                mock.patch.object(process, "probe_duration", return_value=10),
                mock.patch.object(
                    process, "run_command", side_effect=create_working
                ) as run,
            ):
                result = process.prepare_upload(video, root, 0.0001)

        self.assertEqual(result, (working, True))
        self.assertIn("ffmpeg", run.call_args.args[0])
        self.assertIn("scale=-2:720", run.call_args.args[0])

    def test_main_rejects_source_as_output(self):
        with tempfile.TemporaryDirectory() as directory:
            video = Path(directory) / "input.mp4"
            video.touch()
            args = mock.Mock(
                check=False,
                video=str(video),
                output=str(video),
                prompt=None,
                keep_stylized=False,
                max_upload_mb=15,
            )
            with (
                mock.patch.object(
                    process,
                    "build_parser",
                    return_value=mock.Mock(parse_args=mock.Mock(return_value=args)),
                ),
                mock.patch.object(process.shutil, "which", return_value="/usr/bin/tool"),
                mock.patch.object(process, "ensure_environment"),
                mock.patch.object(process, "resolve_api_key", return_value="secret"),
                self.assertRaisesRegex(SystemExit, "different from the source"),
            ):
                process.main()

    def test_main_runs_both_stages_and_removes_intermediate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            video = root / "input.mp4"
            video.touch()
            output = root / "final.mp4"
            stylized = root / "final-stylized.mp4"
            stylized.touch()

            args = mock.Mock(
                check=False,
                video=str(video),
                output=str(output),
                prompt="anime",
                keep_stylized=False,
                max_upload_mb=15,
            )
            with (
                mock.patch.object(
                    process,
                    "build_parser",
                    return_value=mock.Mock(parse_args=mock.Mock(return_value=args)),
                ),
                mock.patch.object(process.shutil, "which", return_value="/usr/bin/tool"),
                mock.patch.object(process, "ensure_environment"),
                mock.patch.object(process, "resolve_api_key", return_value="secret"),
                mock.patch.object(
                    process, "prepare_upload", return_value=(video, False)
                ),
                mock.patch.object(process, "run_command") as run,
            ):
                process.main()

            self.assertEqual(run.call_count, 2)
            self.assertIn("--prompt", run.call_args_list[0].args[0])
            self.assertFalse(stylized.exists())


if __name__ == "__main__":
    unittest.main()
