"""Delivery adapter module for Company AI Workbench.

Implements Invariant 9:
"Commit, push, PR, merge, deployment, production verification, and Ticket acceptance
are distinct claims."

This module provides the delivery boundary: merging verified, accepted wb-run/<run> branches
into target mainline branches (e.g. master/main), generating standalone auditable patch files,
and tagging delivery milestones.
"""

import os
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence


class DeliveryError(Exception):
    """Raised when a delivery operation cannot be completed safely."""


@dataclass(frozen=True)
class DeliveryResult:
    status: str  # 'delivered', 'conflict', 'failed'
    target_branch: str
    source_branch: str
    commit_sha: str | None = None
    files_changed: tuple[str, ...] = ()
    patch_path: str | None = None
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "target_branch": self.target_branch,
            "source_branch": self.source_branch,
            "commit_sha": self.commit_sha,
            "files_changed": list(self.files_changed),
            "patch_path": self.patch_path,
            "message": self.message,
        }


class GitDeliveryAdapter:
    """Adapter for executing mainline Git branch merges, patch exports, and delivery tagging."""

    def __init__(self, repo_path: str | Path):
        self.repo_path = Path(repo_path).resolve()
        if not (self.repo_path / ".git").exists():
            raise DeliveryError(f"Target path is not a git repository: {self.repo_path}")

    def _run_git(self, args: Sequence[str], *, check: bool = True) -> subprocess.CompletedProcess:
        try:
            res = subprocess.run(
                ["git"] + list(args),
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            if check and res.returncode != 0:
                cmd_str = " ".join(args)
                raise DeliveryError(
                    f"Git command failed (exit {res.returncode}): git {cmd_str}\n"
                    f"stdout: {res.stdout.strip()}\n"
                    f"stderr: {res.stderr.strip()}"
                )
            return res
        except FileNotFoundError as err:
            raise DeliveryError(f"git executable not found: {err}") from err

    def has_run_branch(self, run_id: str) -> bool:
        branch = f"wb-run/{run_id}"
        res = self._run_git(["rev-parse", "--verify", f"refs/heads/{branch}"], check=False)
        return res.returncode == 0

    def merge_run_to_branch(
        self,
        run_id: str,
        *,
        target_branch: str = "master",
        commit_message: str | None = None,
        generate_patch: bool = True,
        output_dir: str | Path | None = None,
    ) -> DeliveryResult:
        source_branch = f"wb-run/{run_id}"
        if not self.has_run_branch(run_id):
            # No separate worktree branch was created (e.g. run executed directly on master,
            # simulated via FakeRunner, or manual runner). Use current commit on target branch.
            head_commit = self._run_git(["rev-parse", "HEAD"]).stdout.strip()
            return DeliveryResult(
                status="delivered",
                target_branch=target_branch,
                source_branch=None,
                commit_sha=head_commit,
                files_changed=[],
                patch_path=None,
                message=f"Run {run_id} has no isolated run branch; referenced HEAD ({head_commit[:8]}) as delivery baseline.",
            )

        # Check current working tree is clean of tracked modifications
        diff_unstaged = self._run_git(["diff", "--quiet"], check=False)
        diff_staged = self._run_git(["diff", "--cached", "--quiet"], check=False)
        if diff_unstaged.returncode != 0 or diff_staged.returncode != 0:
            raise DeliveryError("Working directory has uncommitted tracked changes; cannot safely merge delivery branch")

        # Check target branch exists
        tb_check = self._run_git(["rev-parse", "--verify", f"refs/heads/{target_branch}"], check=False)
        if tb_check.returncode != 0:
            raise DeliveryError(f"Target branch does not exist: {target_branch}")

        # Checkout target branch
        self._run_git(["checkout", target_branch])

        # Generate patch before or during merge if requested
        patch_file = None
        if generate_patch:
            try:
                patch_file = str(self.generate_patch(run_id, base_branch=target_branch, output_dir=output_dir))
            except Exception:
                patch_file = None

        msg = commit_message or f"delivery: merge accepted run {run_id} into {target_branch}"
        merge_res = self._run_git(["merge", "--no-ff", source_branch, "-m", msg], check=False)

        if merge_res.returncode != 0:
            # Abort failed merge
            self._run_git(["merge", "--abort"], check=False)
            return DeliveryResult(
                status="conflict",
                target_branch=target_branch,
                source_branch=source_branch,
                message=f"Merge conflict occurred: {merge_res.stderr.strip()}",
            )

        # Merge succeeded, get HEAD commit and changed files
        head_commit = self._run_git(["rev-parse", "HEAD"]).stdout.strip()
        diff_res = self._run_git(["diff-tree", "--no-commit-id", "--name-only", "-r", "-m", head_commit])
        files_changed = tuple(sorted(set(line.strip() for line in diff_res.stdout.splitlines() if line.strip())))

        return DeliveryResult(
            status="delivered",
            target_branch=target_branch,
            source_branch=source_branch,
            commit_sha=head_commit,
            files_changed=files_changed,
            patch_path=patch_file,
            message=f"Successfully delivered {source_branch} to {target_branch}",
        )

    def generate_patch(
        self,
        run_id: str,
        *,
        base_branch: str = "master",
        output_dir: str | Path | None = None,
    ) -> Path:
        source_branch = f"wb-run/{run_id}"
        if not self.has_run_branch(run_id):
            raise DeliveryError(f"Source run branch does not exist: {source_branch}")

        res = self._run_git(["diff", f"{base_branch}...{source_branch}"])
        diff_content = res.stdout

        target_dir = Path(output_dir) if output_dir else (self.repo_path / ".workbench" / "patches")
        target_dir.mkdir(parents=True, exist_ok=True)
        patch_path = target_dir / f"{run_id}.patch"
        patch_path.write_text(diff_content, encoding="utf-8")
        return patch_path

    def tag_delivery(
        self,
        commit_sha: str,
        tag_name: str,
        *,
        message: str,
    ) -> str:
        self._run_git(["tag", "-a", tag_name, commit_sha, "-m", message])
        return tag_name
