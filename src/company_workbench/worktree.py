from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from .errors import WorktreeError


def _run_git(argv: Sequence[str], *, cwd: Path) -> str:
    try:
        proc = subprocess.run(
            ["git", *argv],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
            encoding="utf-8",
            errors="replace",
        )
    except OSError as exc:
        raise WorktreeError(f"Failed to invoke git: {exc}") from exc

    if proc.returncode != 0:
        raise WorktreeError(f"git {' '.join(argv)} failed (exit {proc.returncode}): {proc.stderr.strip() or proc.stdout.strip()}")
    return proc.stdout.strip()


@dataclass(frozen=True)
class WorktreeEnvironment:
    """Represents an isolated temporary worktree for a specific Run."""
    run_id: str
    branch_name: str
    worktree_path: Path
    repo_root: Path

    def get_changed_files(self) -> list[str]:
        """List files modified, added, or untracked within this worktree."""
        output = _run_git(["status", "--porcelain"], cwd=self.worktree_path)
        files = []
        for line in output.splitlines():
            if line.strip():
                files.append(line.strip())
        return files

    def get_diff(self) -> str:
        """Get the full unified diff of changes against the base branch."""
        return _run_git(["diff", "HEAD"], cwd=self.worktree_path)

    def run_verification(self, command: str, *, timeout_seconds: float = 120) -> dict[str, Any]:
        """Execute a verification command directly inside this isolated worktree without shell injection."""
        import shlex
        import time
        start_time = time.monotonic()
        try:
            # Tokenize command string safely without shell injection
            raw_tokens = shlex.split(command, posix=False)
            argv = [t.strip('"').strip("'") for t in raw_tokens if t.strip()]
            if not argv:
                raise ValueError("Verification command cannot be empty")
            proc = subprocess.run(
                argv,
                cwd=self.worktree_path,
                shell=False,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                encoding="utf-8",
                errors="replace",
            )

            duration = round(time.monotonic() - start_time, 3)
            return {
                "command": command,
                "exit_code": proc.returncode,
                "stdout": proc.stdout.strip(),
                "stderr": proc.stderr.strip(),
                "duration_seconds": duration,
                "passed": (proc.returncode == 0),
            }
        except subprocess.TimeoutExpired:
            return {
                "command": command,
                "exit_code": -1,
                "stdout": "",
                "stderr": f"Verification timed out after {timeout_seconds}s",
                "duration_seconds": timeout_seconds,
                "passed": False,
            }
        except Exception as exc:
            return {
                "command": command,
                "exit_code": -1,
                "stdout": "",
                "stderr": f"Failed to execute verification command: {exc}",
                "duration_seconds": round(time.monotonic() - start_time, 3),
                "passed": False,
            }

    def cleanup(self, *, force: bool = True) -> None:
        """Prune and remove the temporary worktree."""
        try:
            flag = ["--force"] if force else []
            _run_git(["worktree", "remove", *flag, str(self.worktree_path)], cwd=self.repo_root)
        except Exception:
            # Fallback manual directory cleanup if git worktree remove encounters lock on Windows
            if self.worktree_path.exists():
                shutil.rmtree(self.worktree_path, ignore_errors=True)
            try:
                _run_git(["worktree", "prune"], cwd=self.repo_root)
            except Exception:
                pass


class GitWorktreeManager:
    """Manages creation and teardown of isolated worktrees for AI runs."""

    def __init__(self, repo_root: str | Path, *, worktree_base_dir: str | Path | None = None):
        self.repo_root = Path(repo_root).resolve()
        if not (self.repo_root / ".git").exists():
            raise WorktreeError(f"Directory {self.repo_root} is not a git repository root")

        self.worktree_base = (
            Path(worktree_base_dir).resolve()
            if worktree_base_dir
            else self.repo_root / ".workbench" / "worktrees"
        )
        self.worktree_base.mkdir(parents=True, exist_ok=True)

    def create_worktree(self, run_id: str, *, base_ref: str = "HEAD") -> WorktreeEnvironment:
        """Create an isolated worktree and branch for the specified run_id."""
        branch_name = f"wb-run/{run_id}"
        worktree_path = self.worktree_base / run_id

        if worktree_path.exists():
            raise WorktreeError(f"Worktree path already exists: {worktree_path}")

        # Ensure base worktree directory exists
        self.worktree_base.mkdir(parents=True, exist_ok=True)

        # git worktree add -b <branch_name> <worktree_path> <base_ref>
        _run_git(
            ["worktree", "add", "-b", branch_name, str(worktree_path), base_ref],
            cwd=self.repo_root,
        )

        return WorktreeEnvironment(
            run_id=run_id,
            branch_name=branch_name,
            worktree_path=worktree_path,
            repo_root=self.repo_root,
        )
