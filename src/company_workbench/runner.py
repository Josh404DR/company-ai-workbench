from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Sequence


_ALLOWED_EXECUTABLES = {"codex", "codex.exe", "codex.cmd"}
_SECRET_PATTERNS = (
    re.compile(r"(?i)(authorization\s*:\s*bearer\s+)[^\s]+"),
    re.compile(r"(?i)((?:api[_-]?key|token|password|secret)\s*[=:]\s*)[^\r\n]+"),
    re.compile(r"\b(?:sk|AIza)[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),
)


@dataclass(frozen=True)
class ProcessResult:
    exit_code: int | None
    stdout: str = ""
    stderr: str = ""
    timed_out: bool = False
    cancelled: bool = False
    pid: int | None = None
    usage: dict | None = None


@dataclass(frozen=True)
class RunnerResult:
    outcome: str
    error_code: str | None
    stdout: str
    stderr: str
    exit_code: int | None
    pid: int | None
    usage: dict | None = None


class ProcessExecutor(Protocol):
    def execute(
        self,
        argv: Sequence[str],
        *,
        cwd: Path,
        timeout_seconds: float,
        cancel_event: threading.Event | None,
    ) -> ProcessResult: ...

    def start(self, argv: Sequence[str], *, cwd: Path) -> "ProcessHandle": ...


class ProcessHandle:
    """A spawned process whose PID is known immediately, before it is waited on."""

    def __init__(self, process: subprocess.Popen, stdout_file, stderr_file):
        self.pid = process.pid
        self._process = process
        self._stdout_file = stdout_file
        self._stderr_file = stderr_file
        self._waited = False

    def wait(self, *, timeout_seconds: float, cancel_event: threading.Event | None = None) -> ProcessResult:
        if self._waited:
            raise RuntimeError("ProcessHandle.wait() was already called")
        self._waited = True
        cancelled = False
        timed_out = False
        deadline = time.monotonic() + timeout_seconds
        try:
            while self._process.poll() is None:
                if cancel_event and cancel_event.is_set():
                    _stop_process(self._process, terminate=True)
                    cancelled = True
                    break
                if time.monotonic() >= deadline:
                    _stop_process(self._process, terminate=False)
                    timed_out = True
                    break
                time.sleep(0.05)
            stdout = _read_bounded_bytes(self._stdout_file)
            stderr = _read_bounded_bytes(self._stderr_file)
        finally:
            self._stdout_file.close()
            self._stderr_file.close()
        return ProcessResult(
            self._process.returncode, stdout, stderr, timed_out=timed_out,
            cancelled=cancelled, pid=self._process.pid,
        )


class SubprocessExecutor:
    def start(self, argv: Sequence[str], *, cwd: Path) -> ProcessHandle:
        stdout_file = tempfile.TemporaryFile("w+b")
        stderr_file = tempfile.TemporaryFile("w+b")
        resolved_argv = list(argv)
        if resolved_argv:
            exe_target = resolved_argv[0]
            if not Path(exe_target).is_absolute():
                cmd_path = shutil.which(exe_target)
                if cmd_path:
                    exe_target = cmd_path
            target_path = Path(exe_target)
            if target_path.suffix.lower() in (".cmd", ".bat"):
                # On Windows, npm global .cmd scripts lose multiline args in %*.
                # If the backing JS entry point exists under node_modules, invoke node directly.
                stem = target_path.stem.lower()
                js_candidate = target_path.parent / "node_modules" / "@openai" / stem / "bin" / f"{stem}.js"
                if not js_candidate.exists():
                    js_candidate = target_path.parent / "node_modules" / stem / "bin" / f"{stem}.js"
                if js_candidate.exists() and shutil.which("node"):
                    resolved_argv = ["node", str(js_candidate)] + resolved_argv[1:]
                else:
                    resolved_argv[0] = str(target_path)
            else:
                resolved_argv[0] = str(target_path)
        try:
            process = subprocess.Popen(
                resolved_argv, cwd=cwd, shell=False, stdin=subprocess.DEVNULL,
                stdout=stdout_file, stderr=stderr_file,
            )
        except Exception:
            stdout_file.close()
            stderr_file.close()
            raise
        return ProcessHandle(process, stdout_file, stderr_file)

    def execute(
        self,
        argv: Sequence[str],
        *,
        cwd: Path,
        timeout_seconds: float,
        cancel_event: threading.Event | None,
    ) -> ProcessResult:
        return self.start(argv, cwd=cwd).wait(timeout_seconds=timeout_seconds, cancel_event=cancel_event)


class RunnerInvocation:
    """A Runner invocation whose process has already been spawned and exposes its PID immediately.

    Splitting spawn (fast, synchronous) from wait (potentially long-running) lets a caller such as
    the Engine persist the PID atomically with 'running' state before blocking on completion.
    """

    def __init__(
        self,
        handle: ProcessHandle,
        *,
        timeout_seconds: float,
        max_output_chars: int,
        cancel_event: threading.Event | None,
        sensitive_values: Sequence[str],
    ):
        self._handle = handle
        self._timeout_seconds = timeout_seconds
        self._max_output_chars = max_output_chars
        self._cancel_event = cancel_event
        self._sensitive_values = tuple(sensitive_values)

    @property
    def pid(self) -> int:
        return self._handle.pid

    def cancel(self) -> None:
        if self._cancel_event is not None:
            self._cancel_event.set()

    def wait(self) -> RunnerResult:
        result = self._handle.wait(timeout_seconds=self._timeout_seconds, cancel_event=self._cancel_event)
        return _classify(result, self._max_output_chars, self._sensitive_values)


class CodexCliRunner:
    def __init__(
        self,
        executable: str = "codex",
        executor: ProcessExecutor | None = None,
        default_model: str | None = None,
    ):
        if executable.lower() not in _ALLOWED_EXECUTABLES or Path(executable).name != executable:
            raise ValueError("Codex executable is not allowlisted")
        self.executable = executable
        self.executor = executor or SubprocessExecutor()
        self.default_model = default_model or os.environ.get("CODEX_MODEL")

    def _build_invocation(
        self, prompt: str, cwd: str | Path, timeout_seconds: float, max_output_chars: int,
        model: str | None = None,
    ) -> tuple[Path, tuple[str, ...]]:
        workdir = Path(cwd).resolve()
        if not workdir.is_dir():
            raise ValueError("Runner cwd must be an existing directory")
        if not prompt.strip() or "\x00" in prompt:
            raise ValueError("Runner prompt must be non-empty and contain no NUL")
        if not 1 <= timeout_seconds <= 3600:
            raise ValueError("Runner timeout must be between 1 and 3600 seconds")
        if not 256 <= max_output_chars <= 1_000_000:
            raise ValueError("Runner output limit must be between 256 and 1000000 characters")
        argv: list[str] = [
            self.executable, "exec",
            "--dangerously-bypass-approvals-and-sandbox",
            "--ephemeral",
            "--json",
            "--cd", str(workdir),
        ]
        effective_model = model or self.default_model
        if effective_model:
            argv += ["-m", effective_model]
        argv.append(prompt)
        return workdir, tuple(argv)

    def run(
        self,
        prompt: str,
        *,
        cwd: str | Path,
        timeout_seconds: float = 300,
        max_output_chars: int = 32_000,
        cancel_event: threading.Event | None = None,
        sensitive_values: Sequence[str] = (),
        model: str | None = None,
    ) -> RunnerResult:
        workdir, argv = self._build_invocation(prompt, cwd, timeout_seconds, max_output_chars, model)
        result = self.executor.execute(
            argv, cwd=workdir, timeout_seconds=timeout_seconds, cancel_event=cancel_event
        )
        return _classify(result, max_output_chars, sensitive_values)

    def start_invocation(
        self,
        prompt: str,
        *,
        cwd: str | Path,
        timeout_seconds: float = 300,
        max_output_chars: int = 32_000,
        cancel_event: threading.Event | None = None,
        sensitive_values: Sequence[str] = (),
        model: str | None = None,
    ) -> RunnerInvocation:
        workdir, argv = self._build_invocation(prompt, cwd, timeout_seconds, max_output_chars, model)
        handle = self.executor.start(argv, cwd=workdir)
        return RunnerInvocation(
            handle,
            timeout_seconds=timeout_seconds,
            max_output_chars=max_output_chars,
            cancel_event=cancel_event,
            sensitive_values=sensitive_values,
        )



def _classify(result: ProcessResult, max_output_chars: int, sensitive_values: Sequence[str]) -> RunnerResult:
    stdout = _bounded(_redact(result.stdout, sensitive_values), max_output_chars)
    stderr = _bounded(_redact(result.stderr, sensitive_values), max_output_chars)
    if result.cancelled:
        outcome, error = "cancelled", "RUNNER-CANCELLED"
    elif result.timed_out:
        outcome, error = "failed", "RUNNER-TIMEOUT"
    elif result.exit_code != 0:
        outcome, error = "failed", "RUNNER-EXIT-NONZERO"
    elif not stdout.strip():
        outcome, error = "failed", "RUNNER-INVALID-OUTPUT"
    else:
        outcome, error = "completed", None
    usage = _normalize_usage(result.usage) or _extract_usage(result.stdout)
    return RunnerResult(outcome, error, stdout, stderr, result.exit_code, result.pid, usage)


def _extract_usage(stdout: str) -> dict | None:
    """Best-effort token usage from JSON/JSONL runner output (e.g. Codex `exec --json`).

    Scans each line and any top-level JSON object for a `usage` mapping carrying
    input/output token counts; the last one wins. Never raises: usage is diagnostic
    evidence, not a gate.
    """
    found: dict | None = None
    candidates: list[str] = stdout.splitlines()
    if stdout.strip().startswith("{"):
        candidates.append(stdout)
    for line in candidates:
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            obj = json.loads(line)
        except (ValueError, TypeError):
            continue
        usage = obj.get("usage") if isinstance(obj, dict) else None
        if isinstance(usage, dict):
            normalized = _normalize_usage(usage)
            if normalized:
                found = normalized
    return found


def _normalize_usage(usage: dict | None) -> dict | None:
    if not isinstance(usage, dict):
        return None
    aliases = {
        "input_tokens": ("input_tokens", "prompt_tokens", "promptTokenCount"),
        "output_tokens": ("output_tokens", "completion_tokens", "candidatesTokenCount"),
    }
    out: dict = {}
    for key, names in aliases.items():
        for name in names:
            value = usage.get(name)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                out[key] = int(value)
                break
    return out or None


def _redact(value: str, sensitive_values: Sequence[str] = ()) -> str:
    redacted = value
    for pattern in _SECRET_PATTERNS:
        redacted = pattern.sub(lambda match: (match.group(1) if match.lastindex else "") + "[REDACTED]", redacted)
    for secret in sorted((item for item in sensitive_values if len(item) >= 4), key=len, reverse=True):
        redacted = redacted.replace(secret, "[REDACTED]")
    return redacted


def _bounded(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    marker = "\n...[TRUNCATED]...\n"
    remaining = limit - len(marker)
    return value[: remaining // 2] + marker + value[-(remaining - remaining // 2) :]


def _stop_process(process: subprocess.Popen, *, terminate: bool) -> None:
    if terminate:
        process.terminate()
        try:
            process.wait(timeout=2)
            return
        except subprocess.TimeoutExpired:
            pass
    process.kill()
    process.wait()


def _read_bounded_bytes(stream, limit: int = 1_000_000) -> str:
    stream.flush()
    stream.seek(0, 2)
    size = stream.tell()
    if size <= limit:
        stream.seek(0)
        data = stream.read()
    else:
        half = limit // 2
        stream.seek(0)
        start = stream.read(half)
        stream.seek(-half, 2)
        end = stream.read(half)
        data = start + b"\n...[CAPTURE TRUNCATED]...\n" + end
    return data.decode("utf-8", errors="replace")
