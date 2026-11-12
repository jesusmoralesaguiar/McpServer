"""File discovery, exclusion checks, security guards, and content loading."""

from __future__ import annotations

import fnmatch
import os
import subprocess
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from mcp_server.core.config import (
    EXCLUDE_DIRS,
    EXCLUDE_GLOBS,
    SECRET_GLOBS,
    SECRET_NAMES,
    SPECIAL_TEXT_NAMES,
    TEXT_EXTS,
)


@dataclass
class FileInfo:
    rel: str
    abs: str
    size: int
    ext: str
    text: str
    lines: List[str]
    score: float = 0.0
    reasons: List[str] = field(default_factory=list)
    windows: List[Tuple[int, int]] = field(default_factory=list)
    defs: List[Tuple[str, int, int]] = field(default_factory=list)
    is_test: bool = False
    is_doc: bool = False


def run_command(cmd: Sequence[str], cwd: str, timeout: int = 30) -> str:
    try:
        proc = subprocess.run(
            list(cmd),
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    if proc.returncode != 0:
        return ""
    return proc.stdout


def git_metadata(root: str) -> Dict[str, str]:
    branch = run_command(["git", "rev-parse", "--abbrev-ref", "HEAD"], root).strip()
    commit = run_command(["git", "rev-parse", "--short", "HEAD"], root).strip()
    return {"root": root, "branch": branch, "commit": commit}


def git_diff(root: str, staged: bool = False) -> str:
    args = ["git", "diff", "--no-color", "--unified=3"]
    if staged:
        args.append("--cached")
    return run_command(args, root, timeout=60)


def is_secret(rel: str) -> bool:
    name = os.path.basename(rel).lower()
    if name in {".env.example", ".env.sample", ".env.template"}:
        return False
    if name in SECRET_NAMES:
        return True
    if name.startswith(".env.") or name.startswith(".env-"):
        return True
    for pattern in SECRET_GLOBS:
        if fnmatch.fnmatch(name, pattern):
            return True
    return False


def is_excluded(rel: str, extra: Sequence[str] = ()) -> bool:
    rel = rel.replace("\\", "/")
    parts = rel.split("/")
    if any(part in EXCLUDE_DIRS for part in parts[:-1]):
        return True
    name = parts[-1]
    low = name.lower()
    if is_secret(rel):
        return True
    for pattern in list(EXCLUDE_GLOBS) + list(extra):
        if fnmatch.fnmatch(rel, pattern) or fnmatch.fnmatch(name, pattern):
            return True
    for pattern in EXCLUDE_GLOBS:
        if pattern.startswith("*.") and low.endswith(pattern[1:]):
            return True
    return False


def is_text_candidate(rel: str) -> bool:
    name = os.path.basename(rel)
    if name in SPECIAL_TEXT_NAMES:
        return True
    ext = os.path.splitext(name)[1].lower()
    return ext in TEXT_EXTS


def collect_files(
    root: str,
    extra_excludes: Sequence[str] = (),
    max_bytes: int = 1_000_000,
) -> List[str]:
    """Collects repository files safely, respecting gitignore and excludes."""
    raw = run_command(
        ["git", "-C", root, "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        root,
        timeout=60,
    )
    rels: List[str] = []
    if raw:
        rels = [item for item in raw.split("\0") if item]
    if not rels:
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [
                d
                for d in dirnames
                if d not in EXCLUDE_DIRS and not d.startswith(".")
            ]
            for name in filenames:
                rel = os.path.relpath(os.path.join(dirpath, name), root).replace(os.sep, "/")
                rels.append(rel)

    result: List[str] = []
    for rel in rels:
        rel = rel.replace("\\", "/")
        if rel.startswith("./"):
            rel = rel[2:]
        if not rel or is_excluded(rel, extra_excludes):
            continue
        if not is_text_candidate(rel):
            continue
        abs_path = os.path.join(root, rel)
        try:
            if not os.path.isfile(abs_path):
                continue
            if os.path.getsize(abs_path) > max_bytes:
                continue
        except OSError:
            continue
        result.append(rel)
    return sorted(set(result))
