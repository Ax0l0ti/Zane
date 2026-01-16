"""Git operations for safe self-modification.

Why this exists:
    Zane can write his own skills, but code generation is risky.
    Git provides a safety net: snapshot before changes, rollback on failure.
    This is the "optimistic concurrency" pattern applied to code generation.

Pattern: Command Pattern with Memento
    - snapshot() = save state (Memento)
    - rollback() = restore state
    - commit() = finalize changes
"""

import git
from datetime import datetime
from pathlib import Path
from typing import Optional


class GitTools:
    """Git wrapper for safe code modification."""

    def __init__(self, repo_path: Optional[Path] = None):
        """Initialize with repository path.

        Args:
            repo_path: Path to git repo. Defaults to current directory.
        """
        self.repo_path = repo_path or Path.cwd()
        self.repo = git.Repo(self.repo_path)
        self._snapshot_ref: Optional[str] = None

    def snapshot(self, message: Optional[str] = None) -> str:
        """Create a snapshot before making changes.

        Why: Before Zane generates code, we save the current state.
             If generation fails, we can rollback to this point.

        Args:
            message: Optional description of what's about to happen.

        Returns:
            The commit SHA of the snapshot.
        """
        # Stage any uncommitted changes first
        self.repo.git.add(A=True)

        # Check if there are changes to commit
        if self.repo.is_dirty() or self.repo.untracked_files:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            commit_msg = f"[SNAPSHOT] {message or 'Pre-modification snapshot'} ({timestamp})"
            self.repo.index.commit(commit_msg)

        # Store the current HEAD as our rollback point
        self._snapshot_ref = self.repo.head.commit.hexsha
        return self._snapshot_ref

    def rollback(self) -> bool:
        """Rollback to the last snapshot.

        Why: If code generation fails (syntax error, test failure),
             we restore the codebase to its pre-modification state.
             This prevents Zane from breaking himself.

        Returns:
            True if rollback succeeded, False if no snapshot exists.
        """
        if not self._snapshot_ref:
            return False

        try:
            # Hard reset to snapshot point
            self.repo.git.reset('--hard', self._snapshot_ref)
            # Clean untracked files
            self.repo.git.clean('-fd')
            return True
        except git.GitCommandError:
            return False

    def commit(self, message: str) -> str:
        """Commit successful changes.

        Why: After code generation succeeds (passes tests),
             we commit the changes to make them permanent.

        Args:
            message: Commit message describing what was created.

        Returns:
            The commit SHA.
        """
        # Stage all changes
        self.repo.git.add(A=True)

        # Only commit if there are changes
        if self.repo.is_dirty():
            commit = self.repo.index.commit(f"[ZANE] {message}")
            self._snapshot_ref = None  # Clear snapshot after successful commit
            return commit.hexsha

        return self.repo.head.commit.hexsha

    def get_status(self) -> dict:
        """Get current repository status.

        Returns:
            Dict with branch, dirty status, and recent commits.
        """
        return {
            "branch": self.repo.active_branch.name,
            "is_dirty": self.repo.is_dirty(),
            "untracked": self.repo.untracked_files,
            "head_sha": self.repo.head.commit.hexsha[:8],
            "head_message": self.repo.head.commit.message.strip(),
            "snapshot_active": self._snapshot_ref is not None
        }

    def get_diff(self) -> str:
        """Get diff of uncommitted changes.

        Returns:
            String diff output.
        """
        return self.repo.git.diff()


class GitToolsSkill:
    """Skill wrapper for GitTools (follows skill.json pattern)."""

    def __init__(self):
        self.git = GitTools()

    def run(self, action: str = "status", **kwargs) -> dict:
        """Execute a git action.

        Args:
            action: One of 'status', 'snapshot', 'rollback', 'commit'
            **kwargs: Additional arguments for the action.

        Returns:
            Result dict with success status and data.
        """
        try:
            if action == "status":
                return {"success": True, "result": self.git.get_status()}
            elif action == "snapshot":
                sha = self.git.snapshot(kwargs.get("message"))
                return {"success": True, "result": {"snapshot_sha": sha}}
            elif action == "rollback":
                success = self.git.rollback()
                return {"success": success, "result": {"rolled_back": success}}
            elif action == "commit":
                sha = self.git.commit(kwargs.get("message", "Automated commit"))
                return {"success": True, "result": {"commit_sha": sha}}
            else:
                return {"success": False, "error": f"Unknown action: {action}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
