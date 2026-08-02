import os
import signal
import subprocess
import tempfile
import textwrap
import time
import unittest
from pathlib import Path


SCRAPER_ROOT = Path(__file__).resolve().parents[1]
ENTRYPOINT = SCRAPER_ROOT / "docker" / "entrypoint.sh"


class EntrypointLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.app_dir = self.root / "app"
        self.config_dir = self.root / "config"
        self.media_dir = self.root / "media"
        self.bin_dir = self.root / "bin"
        for directory in (
            self.app_dir,
            self.config_dir,
            self.media_dir,
            self.bin_dir,
        ):
            directory.mkdir()

        (self.config_dir / "config.yml").write_text("scanner: {}\n")
        self._write_executable(
            "getent",
            """
            #!/bin/sh
            case "$1" in
              group) printf 'testgroup:x:%s:\n' "$TEST_GID" ;;
              passwd) printf '%s:x:%s:%s:test:%s:/bin/sh\n' \
                "$TEST_USER" "$TEST_UID" "$TEST_GID" "$APP_DIR" ;;
              *) exit 1 ;;
            esac
            """,
        )
        self._write_executable(
            "gosu",
            """
            #!/bin/sh
            shift
            exec "$@"
            """,
        )
        self._write_executable(
            "curl",
            """
            #!/bin/sh
            test -f "$METATUBE_READY_FILE"
            """,
        )
        self.metatube_bin = self._write_executable(
            "fake-metatube",
            """
            #!/usr/bin/env python3
            import os
            import signal
            import sys
            from pathlib import Path

            if os.environ.get("METATUBE_TEST_MODE", "ready") == "fail":
                raise SystemExit(42)

            Path(os.environ["METATUBE_PID_FILE"]).write_text(f"{os.getpid()}\\n")
            Path(os.environ["METATUBE_READY_FILE"]).touch()

            def stop(_signum, _frame):
                Path(os.environ["METATUBE_STOPPED_FILE"]).touch()
                raise SystemExit(0)

            signal.signal(signal.SIGTERM, stop)
            signal.signal(signal.SIGINT, stop)
            while True:
                signal.pause()
            """,
        )
        self.javsp_bin = self._write_executable(
            "fake-javsp",
            """
            #!/usr/bin/env python3
            import os
            import signal
            from pathlib import Path

            Path(os.environ["JAVSP_PID_FILE"]).write_text(f"{os.getpid()}\\n")
            Path(os.environ["JAVSP_STARTED_FILE"]).touch()

            def stop(_signum, _frame):
                Path(os.environ["JAVSP_STOPPED_FILE"]).touch()
                raise SystemExit(0)

            if os.environ.get("JAVSP_TEST_MODE", "exit") == "block":
                signal.signal(signal.SIGTERM, stop)
                signal.signal(signal.SIGINT, stop)
                while True:
                    signal.pause()

            raise SystemExit(int(os.environ.get("JAVSP_EXIT_CODE", "0")))
            """,
        )

        self.env = os.environ.copy()
        self.env.update(
            {
                "PATH": f"{self.bin_dir}:{self.env['PATH']}",
                "PUID": str(os.getuid()),
                "PGID": str(os.getgid()),
                "UMASK": "022",
                "APP_DIR": str(self.app_dir),
                "CONFIG_DIR": str(self.config_dir),
                "MEDIA_DIR": str(self.media_dir),
                "JAVSP_USER": "testuser",
                "JAVSP_BIN": str(self.javsp_bin),
                "METATUBE_BIN": str(self.metatube_bin),
                "METATUBE_ENABLED": "1",
                "METATUBE_PORT": "18080",
                "PROCESS_STOP_TIMEOUT": "0.5",
                "TEST_UID": str(os.getuid()),
                "TEST_GID": str(os.getgid()),
                "TEST_USER": "testuser",
                "METATUBE_READY_FILE": str(self.root / "metatube-ready"),
                "METATUBE_PID_FILE": str(self.root / "metatube-pid"),
                "METATUBE_STOPPED_FILE": str(self.root / "metatube-stopped"),
                "JAVSP_STARTED_FILE": str(self.root / "javsp-started"),
                "JAVSP_PID_FILE": str(self.root / "javsp-pid"),
                "JAVSP_STOPPED_FILE": str(self.root / "javsp-stopped"),
            }
        )

    def tearDown(self):
        self.tempdir.cleanup()

    def _write_executable(self, name, body):
        path = self.bin_dir / name
        path.write_text(textwrap.dedent(body).lstrip())
        path.chmod(0o755)
        return path

    def _run(self, **env_overrides):
        env = self.env | {key: str(value) for key, value in env_overrides.items()}
        return subprocess.run(
            ["bash", str(ENTRYPOINT), "-c", str(self.config_dir / "config.yml")],
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=10,
            check=False,
        )

    def _assert_pid_stopped(self, filename):
        pid = int((self.root / filename).read_text().strip())
        with self.assertRaises(ProcessLookupError):
            os.kill(pid, 0)

    def test_successful_scan_stops_metatube_and_exits_zero(self):
        result = self._run(JAVSP_EXIT_CODE=0)

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertTrue((self.root / "javsp-started").exists())
        self._assert_pid_stopped("metatube-pid")
        self.assertIn("JavSP completed successfully", result.stdout)

    def test_metatube_readiness_failure_prevents_javsp(self):
        result = self._run(METATUBE_TEST_MODE="fail")

        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertFalse((self.root / "javsp-started").exists())
        self.assertIn("JavSP will not run", result.stdout)

    def test_empty_input_exit_is_propagated(self):
        result = self._run(JAVSP_EXIT_CODE=1)

        self.assertEqual(result.returncode, 1, result.stdout)
        self._assert_pid_stopped("metatube-pid")
        self.assertIn("JavSP failed with exit code 1", result.stdout)

    def test_sigterm_stops_javsp_and_metatube(self):
        env = self.env | {"JAVSP_TEST_MODE": "block"}
        process = subprocess.Popen(
            ["bash", str(ENTRYPOINT), "-c", str(self.config_dir / "config.yml")],
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if (self.root / "javsp-started").exists():
                break
            time.sleep(0.05)
        else:
            process.kill()
            self.fail("JavSP did not start before the timeout")

        process.send_signal(signal.SIGTERM)
        output, _ = process.communicate(timeout=10)

        self.assertEqual(process.returncode, 143, output)
        self._assert_pid_stopped("javsp-pid")
        self._assert_pid_stopped("metatube-pid")


if __name__ == "__main__":
    unittest.main()
