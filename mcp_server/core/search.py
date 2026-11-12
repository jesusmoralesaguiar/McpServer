"""Surgical code search without dumping full files into context."""

from __future__ import annotations

import fnmatch
import os
import re
from typing import Any, Dict, List, Optional

from mcp_server.core.scanner import collect_files


def search_code(
    query: str,
    root: str = ".",
    glob_pattern: Optional[str] = None,
    max_results: int = 25,
    context_lines: int = 2,
) -> List[Dict[str, Any]]:
    """Performs a surgical search across the repository files.
    
    Returns structured matches with line numbers, relative paths,
    and a small context window around the match.
    """
    if not query.strip():
        return []

    files = collect_files(root)
    if glob_pattern:
        files = [f for f in files if fnmatch.fnmatch(f, glob_pattern) or fnmatch.fnmatch(os.path.basename(f), glob_pattern)]

    try:
        regex = re.compile(re.escape(query), re.IGNORECASE)
    except re.error:
        regex = re.compile(query, re.IGNORECASE)

    matches: List[Dict[str, Any]] = []

    for rel in files:
        abs_path = os.path.join(root, rel)
        try:
            with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
        except OSError:
            continue

        for idx, line in enumerate(lines, 1):
            if regex.search(line):
                start = max(1, idx - context_lines)
                end = min(len(lines), idx + context_lines)
                snippet = "".join(lines[start - 1 : end])

                matches.append({
                    "file": rel,
                    "line": idx,
                    "matched_line": line.strip(),
                    "start_line": start,
                    "end_line": end,
                    "snippet": snippet,
                })

                if len(matches) >= max_results:
                    return matches

    return matches
