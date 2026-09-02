from __future__ import annotations

import json
import os
import threading
import urllib.request
import urllib.error
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from .runner import RunnerResult, _classify, ProcessResult, _redact, _bounded, RunnerInvocation
from .errors import RunnerLaunchError


def load_gemini_api_key(env_path: Path | None = None) -> str:
    """Load GEMINI_API_KEY from environment or .env file without leaking."""
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if key:
        return key

    target_env = env_path or (Path.cwd() / ".env")
    if target_env.exists():
        for line in target_env.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("GEMINI_API_KEY="):
                key = line.split("=", 1)[1].strip().strip('"').strip("'")
                if key:
                    return key

    raise RunnerLaunchError("GEMINI_API_KEY not found in environment or .env file")


class _GeminiInvocationHandle:
    """Synchronous handle implementing the ProcessHandle protocol for API runners."""

    def __init__(
        self,
        prompt: str,
        api_key: str,
        model: str,
        cwd: Path,
        system_instruction: str,
    ):
        self.pid = None  # Direct API has no OS process PID
        self._prompt = prompt
        self._api_key = api_key
        self._model = model
        self._cwd = cwd
        self._system_instruction = system_instruction
        self._waited = False

    def wait(self, *, timeout_seconds: float, cancel_event: threading.Event | None = None) -> ProcessResult:
        if self._waited:
            raise RuntimeError("_GeminiInvocationHandle.wait() was already called")
        self._waited = True

        if cancel_event and cancel_event.is_set():
            return ProcessResult(None, "", "Cancelled before dispatch", cancelled=True, pid=None)

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self._model}:generateContent?key={self._api_key}"
        payload = {
            "contents": [{"parts": [{"text": self._prompt}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 4096},
        }
        if self._system_instruction:
            payload["systemInstruction"] = {"parts": [{"text": self._system_instruction}]}

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
                candidates = resp_data.get("candidates", [])
                if not candidates:
                    return ProcessResult(1, "", "No candidates returned by Gemini", pid=None)
                parts = candidates[0].get("content", {}).get("parts", [])
                text = "".join(part.get("text", "") for part in parts)
                return ProcessResult(0, text, "", pid=None)
        except urllib.error.HTTPError as err:
            err_body = err.read().decode("utf-8", errors="replace")
            return ProcessResult(err.code, "", f"Gemini HTTP {err.code}: {err_body}", pid=None)
        except Exception as exc:
            return ProcessResult(1, "", f"Gemini request failed: {exc}", pid=None)


class GeminiRunner:
    """Direct API Runner for Gemini models conforming to the managed Runner boundary."""

    def __init__(self, api_key: str | None = None, model: str = "gemini-2.5-flash"):
        self.api_key = api_key
        self.model = model

    def start_invocation(
        self,
        prompt: str,
        *,
        cwd: str | Path,
        timeout_seconds: float = 60,
        max_output_chars: int = 32_000,
        cancel_event: threading.Event | None = None,
        sensitive_values: Sequence[str] = (),
        model: str | None = None,
        system_instruction: str = "You are an expert AI software engineer. Generate production-ready code or direct answers as requested.",
    ) -> RunnerInvocation:
        key = self.api_key or load_gemini_api_key()
        workdir = Path(cwd).resolve()
        if not workdir.is_dir():
            raise ValueError("Runner cwd must be an existing directory")
        if not prompt.strip() or "\x00" in prompt:
            raise ValueError("Runner prompt must be non-empty and contain no NUL")

        all_sensitive = (*sensitive_values, key)
        handle = _GeminiInvocationHandle(
            prompt=prompt,
            api_key=key,
            model=model or self.model,
            cwd=workdir,
            system_instruction=system_instruction,
        )
        return RunnerInvocation(
            handle,
            timeout_seconds=timeout_seconds,
            max_output_chars=max_output_chars,
            cancel_event=cancel_event,
            sensitive_values=all_sensitive,
        )

    def run(
        self,
        prompt: str,
        *,
        cwd: str | Path,
        timeout_seconds: float = 60,
        max_output_chars: int = 32_000,
        cancel_event: threading.Event | None = None,
        sensitive_values: Sequence[str] = (),
        model: str | None = None,
        system_instruction: str = "You are an expert AI software engineer.",
    ) -> RunnerResult:
        invocation = self.start_invocation(
            prompt,
            cwd=cwd,
            timeout_seconds=timeout_seconds,
            max_output_chars=max_output_chars,
            cancel_event=cancel_event,
            sensitive_values=sensitive_values,
            model=model,
            system_instruction=system_instruction,
        )
        return invocation.wait()
