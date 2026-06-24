"""Tiny git helper so the grader tool can commit + push regenerated prompts.

Grader rubrics (``backend/graders/<name>/prompt.md`` + ``grader.yml``) are the
single source of truth and live in git. After a reinit rewrites a prompt.md the
file is "uncommitted"; the UI calls :func:`commit_and_push` to land it on GitHub.

All operations are scoped to the graders directory via a git pathspec, so a
commit never sweeps in the user's other working-tree changes. The server runs
locally as the user, so it inherits their git identity + push credentials.
"""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

from . import config

# Bound every git call so a hung credential prompt / network can't wedge a request.
_DEFAULT_TIMEOUT = 30.0
_PUSH_TIMEOUT = 120.0


def _repo_root() -> Path:
    return config.PROJECT_ROOT


def _run_git(args: List[str], timeout: float = _DEFAULT_TIMEOUT) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=str(_repo_root()),
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def graders_rel() -> Optional[str]:
    """The graders dir as a POSIX path relative to the repo root, or None if it
    lives outside the repo (then git features are unavailable)."""
    try:
        rel = config.IMPORT_EVALS_GRADERS_DIR.resolve().relative_to(_repo_root().resolve())
    except (ValueError, OSError):
        return None
    return str(rel).replace(os.sep, "/")


def _grader_name_from_path(path: str, rel_prefix: str) -> Optional[str]:
    """Pull '<name>' out of 'backend/graders/<name>/prompt.md' (handles quoting)."""
    p = path.strip().strip('"')
    prefix = rel_prefix.rstrip("/") + "/"
    if not p.startswith(prefix):
        return None
    rest = p[len(prefix):]
    if not rest:
        return None
    return rest.split("/", 1)[0] or None


def _parse_branch_line(line: str, info: Dict) -> None:
    """Parse a porcelain '## branch...upstream [ahead N, behind M]' header."""
    body = line[3:].strip()
    m = re.search(r"\[([^\]]*)\]\s*$", body)
    if m:
        for part in m.group(1).split(","):
            part = part.strip()
            if part.startswith("ahead "):
                info["ahead"] = int(part[len("ahead "):] or 0)
            elif part.startswith("behind "):
                info["behind"] = int(part[len("behind "):] or 0)
        body = body[: m.start()].strip()
    if "..." in body:
        info["has_upstream"] = True
        info["branch"] = body.split("...", 1)[0].strip()
    else:
        # e.g. "main" (no upstream) or "No commits yet on main".
        info["branch"] = body.replace("No commits yet on ", "").strip() or None


def graders_status() -> Dict:
    """Git state of the graders dir for the UI: branch, ahead/behind, and which
    graders have uncommitted changes. Never raises — reports errors in-band."""
    info: Dict = {
        "is_repo": False,
        "branch": None,
        "has_upstream": False,
        "ahead": 0,
        "behind": 0,
        "dirty_graders": [],
        "error": None,
    }
    rel = graders_rel()
    if rel is None:
        info["error"] = "graders dir is outside the git repo"
        return info
    try:
        # -uall lists untracked files individually (otherwise a fully-untracked
        # graders/ collapses to one entry and we can't tell graders apart).
        cp = _run_git(["status", "--porcelain=v1", "--branch", "--untracked-files=all", "--", rel])
    except FileNotFoundError:
        info["error"] = "git is not installed"
        return info
    except subprocess.TimeoutExpired:
        info["error"] = "git status timed out"
        return info
    if cp.returncode != 0:
        info["error"] = (cp.stderr or "git status failed").strip()
        return info

    info["is_repo"] = True
    dirty = set()
    for line in cp.stdout.splitlines():
        if line.startswith("## "):
            _parse_branch_line(line, info)
            continue
        if len(line) < 4:
            continue
        path = line[3:]
        # Renames show as "old -> new"; the new path is what matters.
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        name = _grader_name_from_path(path, rel)
        if name:
            dirty.add(name)
    info["dirty_graders"] = sorted(dirty)
    return info


def commit_and_push(
    grader_names: List[str],
    message: str,
    *,
    push: bool = True,
    timeout: float = _PUSH_TIMEOUT,
) -> Dict:
    """Stage + commit the given graders' files (pathspec-scoped) and push.

    Returns a structured result; never raises for ordinary git failures. A failed
    push after a successful commit is a partial success (``committed`` true,
    ``pushed`` false, ``error`` set) so the caller can tell the user the change is
    saved locally but not on GitHub yet."""
    res: Dict = {
        "committed": False,
        "pushed": False,
        "nothing_to_commit": False,
        "commit_sha": None,
        "branch": None,
        "error": None,
    }
    rel = graders_rel()
    if rel is None:
        res["error"] = "graders dir is outside the git repo; cannot commit"
        return res
    paths = [f"{rel}/{n}" for n in grader_names] if grader_names else [rel]

    try:
        add = _run_git(["add", "--", *paths])
        if add.returncode != 0:
            res["error"] = (add.stderr or "git add failed").strip()
            return res

        commit = _run_git(["commit", "-m", message, "--", *paths])
        combined = f"{commit.stdout}\n{commit.stderr}".lower()
        if commit.returncode == 0:
            res["committed"] = True
        elif "nothing to commit" in combined or "no changes added" in combined:
            res["nothing_to_commit"] = True
        else:
            res["error"] = (commit.stderr or commit.stdout or "git commit failed").strip()
            return res

        sha = _run_git(["rev-parse", "--short", "HEAD"])
        if sha.returncode == 0:
            res["commit_sha"] = sha.stdout.strip()
        branch = _run_git(["rev-parse", "--abbrev-ref", "HEAD"])
        if branch.returncode == 0:
            res["branch"] = branch.stdout.strip()

        if push:
            pushed = _run_git(["push"], timeout=timeout)
            if pushed.returncode == 0:
                res["pushed"] = True
            else:
                res["error"] = (pushed.stderr or pushed.stdout or "git push failed").strip()
    except FileNotFoundError:
        res["error"] = "git is not installed"
    except subprocess.TimeoutExpired:
        res["error"] = "git timed out (push may need credentials configured)"
    return res
