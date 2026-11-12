"""AST and regex-based symbol definition extractors."""

from __future__ import annotations

import ast
import os
import re
from typing import Any, Dict, List, Sequence, Tuple

from mcp_server.core.scanner import collect_files

JS_DEF_PATTERNS = [
    re.compile(r"^\s*(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)"),
    re.compile(r"^\s*(?:export\s+)?(?:default\s+)?class\s+([A-Za-z_$][\w$]*)"),
    re.compile(
        r"^\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*"
        r"(?:async\s*)?(?:\(|function|[A-Za-z_$])"
    ),
    re.compile(r"^\s*(?:export\s+)?(?:interface|type|enum)\s+([A-Za-z_$][\w$]*)"),
]

GENERIC_DEF_PATTERNS = [
    re.compile(r"^\s*(?:pub\s+)?(?:fn|struct|enum|trait|impl)\s+([A-Za-z_][\w]*)"), # Rust
    re.compile(r"^\s*func\s+(?:\([^)]+\)\s+)?([A-Za-z_][\w]*)"),                    # Go
    re.compile(r"^\s*(?:public|private|protected)?\s*(?:static\s+)?(?:class|interface|record|enum)\s+([A-Za-z_][\w]*)"), # Java/C#
    re.compile(r"^\s*def\s+([A-Za-z_][\w]*)"),                                      # Ruby
]


def python_definitions(text: str) -> List[Tuple[str, int, int]]:
    """Extracts function and class definitions from Python code via AST."""
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    defs: List[Tuple[str, int, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            defs.append(
                (node.name, node.lineno, getattr(node, "end_lineno", node.lineno))
            )
    return sorted(defs, key=lambda x: x[1])


def js_definitions(lines: Sequence[str]) -> List[Tuple[str, int, int]]:
    """Extracts function, class, and component definitions from JS/TS lines."""
    defs: List[Tuple[str, int, int]] = []
    for idx, line in enumerate(lines, 1):
        for pattern in JS_DEF_PATTERNS:
            match = pattern.match(line)
            if match:
                defs.append((match.group(1), idx, min(len(lines), idx + 40)))
                break
    return sorted(defs, key=lambda x: x[1])


def generic_definitions(lines: Sequence[str]) -> List[Tuple[str, int, int]]:
    """Fallback extractor for Rust, Go, Java, C#, Ruby, etc."""
    defs: List[Tuple[str, int, int]] = []
    for idx, line in enumerate(lines, 1):
        for pattern in GENERIC_DEF_PATTERNS:
            match = pattern.match(line)
            if match:
                defs.append((match.group(1), idx, min(len(lines), idx + 40)))
                break
    return sorted(defs, key=lambda x: x[1])


def extract_definitions(
    rel_path: str,
    text: str,
    lines: Sequence[str],
) -> List[Tuple[str, int, int]]:
    ext = os.path.splitext(rel_path)[1].lower()
    if ext == ".py":
        return python_definitions(text)
    elif ext in {".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx"}:
        return js_definitions(lines)
    else:
        return generic_definitions(lines)


def find_symbol(symbol_name: str, root: str = ".") -> List[Dict[str, Any]]:
    """Searches for definitions of symbol_name across all code files in root."""
    target_lower = symbol_name.lower()
    files = collect_files(root)
    matches: List[Dict[str, Any]] = []

    for rel in files:
        ext = os.path.splitext(rel)[1].lower()
        if ext not in {".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs", ".java", ".cs", ".rb"}:
            continue

        abs_path = os.path.join(root, rel)
        try:
            with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
        except OSError:
            continue

        lines = text.splitlines()
        defs = extract_definitions(rel, text, lines)

        for name, start, end in defs:
            if name.lower() == target_lower:
                snippet = "\n".join(lines[start - 1 : min(len(lines), end)])
                matches.append({
                    "file": rel,
                    "symbol": name,
                    "start_line": start,
                    "end_line": end,
                    "snippet": snippet,
                })

    return matches
