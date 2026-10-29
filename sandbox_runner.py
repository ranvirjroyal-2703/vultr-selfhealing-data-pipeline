"""
Isolated sandbox execution with hard resource limits.
Designed for Vultr Agent Rush — Blast Radius Zero.
"""

import subprocess
import tempfile
import os
import time
from dataclasses import dataclass
from typing import Optional


@dataclass
class SandboxResult:
    success: bool
    stdout: str
    stderr: str
    returncode: int
    duration_sec: float
    timed_out: bool = False
    killed_by_limit: bool = False


class SandboxRunner:
    """
    Runs untrusted Python code inside a Docker container with strict limits.
    In production this runs on a Vultr VM.
    """

    def __init__(
        self,
        memory_limit: str = "256m",
        cpu_limit: str = "0.5",
        timeout_sec: int = 15,
        network_disabled: bool = True,
    ):
        self.memory_limit = memory_limit
        self.cpu_limit = cpu_limit
        self.timeout_sec = timeout_sec
        self.network_disabled = network_disabled

    def run(self, code: str) -> SandboxResult:
        """Execute code in an isolated container and return structured results."""
        with tempfile.TemporaryDirectory() as tmpdir:
            script_path = os.path.join(tmpdir, "task.py")
            with open(script_path, "w") as f:
                f.write(code)

            cmd = [
                "docker", "run",
                "--rm",
                "--memory", self.memory_limit,
                "--cpus", self.cpu_limit,
                "--user", "1000:1000",
                "--cap-drop", "ALL",
                "--security-opt", "no-new-privileges",
                "-v", f"{tmpdir}:/workspace:ro",
                "-w", "/workspace",
            ]
            if self.network_disabled:
                cmd.append("--network=none")

            cmd.extend(["python:3.11-slim", "python", "task.py"])

            start = time.time()
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_sec,
                )
                duration = time.time() - start
                return SandboxResult(
                    success=result.returncode == 0,
                    stdout=result.stdout,
                    stderr=result.stderr,
                    returncode=result.returncode,
                    duration_sec=round(duration, 2),
                    timed_out=False,
                    killed_by_limit="Killed" in result.stderr or result.returncode == 137,
                )
            except subprocess.TimeoutExpired as e:
                duration = time.time() - start
                return SandboxResult(
                    success=False,
                    stdout=e.stdout or "",
                    stderr=(e.stderr or "") + "\n[TIMEOUT] Process killed by sandbox",
                    returncode=-1,
                    duration_sec=round(duration, 2),
                    timed_out=True,
                    killed_by_limit=True,
                )
