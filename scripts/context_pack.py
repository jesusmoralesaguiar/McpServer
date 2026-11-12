#!/usr/bin/env python3
"""Genera un feature pack de contexto para una tarea de desarrollo.

El script es generico: funciona en cualquier repo (Django, React, Python, JS,
Go, etc.) y no necesita dependencias externas. Busca por palabras clave,
simbolos o archivos concretos, selecciona los fragmentos mas relevantes y
produce un Markdown con rutas, rangos de linea, tests y diff opcional.

Ejemplos:
    python scripts/context_pack.py --task "anadir endpoint para borrar conversacion"
    python scripts/context_pack.py --symbol Conversation --symbol ChatMessage
    python scripts/context_pack.py --file chatbot_app/models.py --file src/hooks/useChat.js
    python scripts/context_pack.py --task "cambiar UI del chat" --diff --budget 16000
"""

from __future__ import annotations

import argparse
import ast
import datetime as _dt
import fnmatch
import math
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

# Permite importar web_context aunque este script se invoque desde un symlink.
_SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

# ---------------------------------------------------------------------------
# Configuracion de busqueda
# ---------------------------------------------------------------------------

EXCLUDE_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    "bower_components",
    "dist",
    "build",
    "out",
    ".venv",
    "venv",
    "env",
    "ENV",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".nox",
    ".coverage",
    "htmlcov",
    "staticfiles",
    "static",
    "media",
    "coverage",
    ".next",
    ".nuxt",
    ".turbo",
    ".cache",
    "vendor",
    "target",
    "obj",
    "Pods",
    "DerivedData",
}

EXCLUDE_GLOBS = [
    "*.lock",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "poetry.lock",
    "Pipfile.lock",
    "Cargo.lock",
    "composer.lock",
    "go.sum",
    "*.min.js",
    "*.min.css",
    "*.map",
    "*.bundle.js",
    "*.pyc",
    "*.pyo",
    "*.so",
    "*.dll",
    "*.dylib",
    "*.exe",
    "*.bin",
    "*.gguf",
    "*.safetensors",
    "*.ckpt",
    "*.pt",
    "*.onnx",
    "*.jpg",
    "*.jpeg",
    "*.png",
    "*.gif",
    "*.webp",
    "*.ico",
    "*.svg",
    "*.mp4",
    "*.mov",
    "*.mp3",
    "*.wav",
    "*.pdf",
    "*.zip",
    "*.tar",
    "*.gz",
    "*.sqlite3",
    "db.sqlite3",
    "*.db",
]

SECRET_NAMES = {
    ".env",
    ".netrc",
    ".pgpass",
    "credentials",
    "credentials.json",
}

SECRET_GLOBS = [
    "*.pem",
    "*.key",
    "*.p12",
    "*.pfx",
    "*.kdbx",
    "*.jks",
    "*.keystore",
    ".env.*",
    "id_rsa*",
    "id_dsa*",
    "id_ecdsa*",
    "id_ed25519*",
]

TEXT_EXTS = {
    ".py",
    ".pyi",
    ".js",
    ".jsx",
    ".mjs",
    ".cjs",
    ".ts",
    ".tsx",
    ".json",
    ".md",
    ".mdx",
    ".rst",
    ".txt",
    ".yml",
    ".yaml",
    ".toml",
    ".ini",
    ".cfg",
    ".conf",
    ".css",
    ".scss",
    ".sass",
    ".less",
    ".html",
    ".htm",
    ".vue",
    ".svelte",
    ".go",
    ".rs",
    ".java",
    ".kt",
    ".kts",
    ".rb",
    ".php",
    ".cs",
    ".c",
    ".h",
    ".cc",
    ".cpp",
    ".hpp",
    ".m",
    ".mm",
    ".swift",
    ".sql",
    ".graphql",
    ".gql",
    ".sh",
    ".bash",
    ".zsh",
    ".fish",
}

SPECIAL_TEXT_NAMES = {
    ".clinerules",
    ".gitignore",
    ".dockerignore",
    ".editorconfig",
    ".eslintrc",
    ".prettierrc",
    ".babelrc",
    ".npmrc",
    ".flake8",
    "Dockerfile",
    "Makefile",
    "Procfile",
}

SOURCE_EXTS = {
    ".py",
    ".js",
    ".jsx",
    ".mjs",
    ".cjs",
    ".ts",
    ".tsx",
    ".go",
    ".rs",
    ".java",
    ".kt",
    ".rb",
    ".php",
    ".cs",
    ".c",
    ".h",
    ".cc",
    ".cpp",
    ".hpp",
    ".swift",
    ".vue",
    ".svelte",
}

LANG_BY_EXT = {
    ".py": "python",
    ".pyi": "python",
    ".js": "javascript",
    ".jsx": "jsx",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".json": "json",
    ".md": "markdown",
    ".mdx": "markdown",
    ".rst": "rst",
    ".txt": "text",
    ".yml": "yaml",
    ".yaml": "yaml",
    ".toml": "toml",
    ".ini": "ini",
    ".cfg": "ini",
    ".conf": "text",
    ".css": "css",
    ".scss": "scss",
    ".less": "less",
    ".html": "html",
    ".htm": "html",
    ".vue": "vue",
    ".svelte": "svelte",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".kt": "kotlin",
    ".rb": "ruby",
    ".php": "php",
    ".cs": "csharp",
    ".c": "c",
    ".h": "c",
    ".cc": "cpp",
    ".cpp": "cpp",
    ".hpp": "cpp",
    ".sql": "sql",
    ".graphql": "graphql",
    ".gql": "graphql",
    ".sh": "bash",
    ".bash": "bash",
    ".zsh": "bash",
    ".fish": "fish",
}

STOPWORDS = {
    # es
    "al",
    "algo",
    "algun",
    "alguna",
    "algunos",
    "algunas",
    "ante",
    "antes",
    "como",
    "con",
    "contra",
    "cual",
    "cuando",
    "de",
    "del",
    "desde",
    "donde",
    "dos",
    "el",
    "ella",
    "ellas",
    "ellos",
    "en",
    "entre",
    "era",
    "es",
    "esa",
    "ese",
    "eso",
    "esta",
    "este",
    "esto",
    "fue",
    "ha",
    "hacia",
    "hasta",
    "hay",
    "la",
    "las",
    "le",
    "les",
    "lo",
    "los",
    "mas",
    "me",
    "mi",
    "mis",
    "mucho",
    "muy",
    "no",
    "nos",
    "o",
    "otra",
    "otro",
    "para",
    "pero",
    "poco",
    "por",
    "porque",
    "que",
    "quien",
    "se",
    "ser",
    "si",
    "sin",
    "sobre",
    "su",
    "sus",
    "tambien",
    "te",
    "tiene",
    "todo",
    "todos",
    "tu",
    "tus",
    "un",
    "una",
    "uno",
    "unos",
    "unas",
    "y",
    "ya",
    # en
    "the",
    "an",
    "and",
    "or",
    "but",
    "for",
    "with",
    "from",
    "into",
    "onto",
    "of",
    "to",
    "in",
    "on",
    "at",
    "by",
    "as",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
    "this",
    "that",
    "these",
    "those",
    "it",
    "its",
    "we",
    "you",
    "they",
    "he",
    "she",
    "i",
    "not",
    "do",
    "does",
    "did",
    "done",
    "can",
    "could",
    "should",
    "would",
    "will",
    "just",
    "also",
    "only",
    "more",
    "most",
    "some",
    "any",
    "all",
    "each",
    "how",
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
    # verbos y palabras de tarea muy frecuentes
    "add",
    "create",
    "change",
    "update",
    "remove",
    "delete",
    "make",
    "implement",
    "fix",
    "use",
    "using",
    "new",
    "old",
    "please",
    "quiero",
    "necesito",
    "anadir",
    "agregar",
    "crear",
    "cambiar",
    "actualizar",
    "borrar",
    "eliminar",
    "implementar",
    "hacer",
    "nuevo",
    "nueva",
    "tarea",
}

SYNONYMS = {
    "borrar": ["delete", "remove", "clear"],
    "eliminar": ["delete", "remove", "clear"],
    "crear": ["create", "add"],
    "anadir": ["add", "create"],
    "añadir": ["add", "create"],
    "agregar": ["add", "create"],
    "actualizar": ["update", "edit"],
    "editar": ["edit", "update"],
    "listar": ["list", "history", "index"],
    "conversacion": ["conversation", "chat", "history"],
    "conversación": ["conversation", "chat", "history"],
    "mensaje": ["message", "chat"],
    "usuario": ["user", "preference"],
    "preferencias": ["preferences", "preference"],
    "configuracion": ["config", "configuration", "settings"],
    "configuración": ["config", "configuration", "settings"],
    "archivo": ["file", "document"],
    "subir": ["upload"],
    "buscar": ["search", "query"],
    "grafo": ["graph", "neo4j"],
    "embedding": ["embedding", "vector"],
    "prueba": ["test", "spec"],
    "pruebas": ["test", "spec"],
    "endpoint": ["endpoint", "url", "view", "api"],
    "ui": ["frontend", "component", "jsx", "interfaz"],
    "interfaz": ["frontend", "component", "jsx", "ui"],
    "pantalla": ["page", "screen", "component", "view"],
    "componente": ["component", "jsx", "ui"],
    "estilo": ["css", "tailwind", "style"],
}

ANCHOR_FILES = ["AGENTS.md", "README.md", "docs/ARCHITECTURE.md", "pyproject.toml"]

TEST_RE = re.compile(r"(^|[/_.\-])(tests?|specs?|__tests__)([/_.\-]|$)", re.IGNORECASE)
WORD_RE = re.compile(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ_][A-Za-z0-9ÁÉÍÓÚÜÑáéíóúüñ_./\\-]*")
QUOTED_RE = re.compile(r'"([^"]+)"|\'([^\']+)\'')
CAMEL_RE = re.compile(r"[A-Z]+(?=[A-Z][a-z]|\d|\b)|[A-Z]?[a-z]+|\d+")

JS_DEF_PATTERNS = [
    re.compile(r"^\s*(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)"),
    re.compile(r"^\s*(?:export\s+)?(?:default\s+)?class\s+([A-Za-z_$][\w$]*)"),
    re.compile(
        r"^\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*"
        r"(?:async\s*)?(?:\(|function|[A-Za-z_$])"
    ),
    re.compile(r"^\s*(?:export\s+)?(?:interface|type|enum)\s+([A-Za-z_$][\w$]*)"),
]


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


# ---------------------------------------------------------------------------
# Utilidades de sistema y git
# ---------------------------------------------------------------------------


def run(cmd: Sequence[str], cwd: str, timeout: int = 30) -> str:
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
    branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], root).strip()
    commit = run(["git", "rev-parse", "--short", "HEAD"], root).strip()
    return {"root": root, "branch": branch, "commit": commit}


def git_diff(root: str, staged: bool) -> str:
    args = ["git", "diff", "--no-color", "--unified=3"]
    if staged:
        args.append("--cached")
    return run(args, root, timeout=60)


# ---------------------------------------------------------------------------
# Seleccion y lectura de archivos
# ---------------------------------------------------------------------------


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


def is_excluded(rel: str, extra: Sequence[str]) -> bool:
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


def collect_files(root: str, extra_excludes: Sequence[str], max_bytes: int) -> List[str]:
    raw = run(
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


def python_definitions(text: str) -> List[Tuple[str, int, int]]:
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
    return defs


def js_definitions(lines: Sequence[str]) -> List[Tuple[str, int, int]]:
    defs: List[Tuple[str, int, int]] = []
    for idx, line in enumerate(lines, 1):
        for pattern in JS_DEF_PATTERNS:
            match = pattern.match(line)
            if match:
                defs.append((match.group(1), idx, min(len(lines), idx + 30)))
                break
    return defs


def is_test_path(rel: str) -> bool:
    return bool(TEST_RE.search(rel))


def is_doc_path(rel: str) -> bool:
    name = os.path.basename(rel).lower()
    ext = os.path.splitext(name)[1].lower()
    if ext in {".md", ".mdx", ".rst", ".txt"}:
        return True
    return name.startswith(("readme", "agents", "contributing", "changelog"))


def load_infos(root: str, rels: Sequence[str], max_bytes: int) -> List[FileInfo]:
    infos: List[FileInfo] = []
    for rel in rels:
        abs_path = os.path.join(root, rel)
        try:
            stat = os.stat(abs_path)
        except OSError:
            continue
        if not os.path.isfile(abs_path) or stat.st_size == 0 or stat.st_size > max_bytes:
            continue
        try:
            with open(abs_path, "rb") as handle:
                raw = handle.read()
        except OSError:
            continue
        if b"\x00" in raw[:4096]:
            continue
        text = raw.decode("utf-8", errors="replace")
        lines = text.splitlines()
        ext = os.path.splitext(rel)[1].lower()
        info = FileInfo(
            rel=rel,
            abs=abs_path,
            size=stat.st_size,
            ext=ext,
            text=text,
            lines=lines,
        )
        info.is_test = is_test_path(rel)
        info.is_doc = is_doc_path(rel)
        if ext == ".py":
            info.defs = python_definitions(text)
        elif ext in {".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx"}:
            info.defs = js_definitions(lines)
        infos.append(info)
    return infos


# ---------------------------------------------------------------------------
# Keywords, scoring y ventanas de lineas
# ---------------------------------------------------------------------------


def split_identifier(token: str) -> List[str]:
    parts = re.split(r"[/\\._\-]+", token)
    out: List[str] = []
    for part in parts:
        for match in CAMEL_RE.finditer(part):
            value = match.group(0)
            if len(value) >= 3:
                out.append(value.lower())
    return out


def keywords_from_task(task: str) -> List[str]:
    out: List[str] = []
    for match in QUOTED_RE.finditer(task):
        phrase = (match.group(1) or match.group(2) or "").strip()
        if phrase:
            out.append(phrase.lower())
    for token in WORD_RE.findall(task):
        low = token.lower()
        if len(low) >= 3 and low not in STOPWORDS:
            out.append(low)
        if low in SYNONYMS:
            out.extend(SYNONYMS[low])
        for part in split_identifier(token):
            out.append(part)
            if part in SYNONYMS:
                out.extend(SYNONYMS[part])
    seen: Set[str] = set()
    result: List[str] = []
    for keyword in out:
        if (
            len(keyword) >= 3
            and keyword not in STOPWORDS
            and keyword not in seen
        ):
            seen.add(keyword)
            result.append(keyword)
    return result[:40]


def keyword_weights(
    infos: Sequence[FileInfo], keywords: Sequence[str]
) -> Dict[str, float]:
    """Pondera keywords por rareza (IDF suave) para no premiar terminos genericos."""
    total = max(1, len(infos))
    weights: Dict[str, float] = {}
    for keyword in keywords:
        df = sum(1 for info in infos if keyword in info.text.lower())
        weights[keyword] = max(0.5, min(5.0, math.log((total + 1) / (df + 1)) + 1.0))
    return weights


def is_offtopic_tooling(rel: str, keywords: Sequence[str]) -> bool:
    """Evita que scripts y planes entren en tareas de producto si no se piden."""
    rel_l = rel.lower()
    name = os.path.basename(rel_l)
    if rel_l.startswith("scripts/"):
        tool_terms = {
            "script",
            "scripts",
            "herramienta",
            "herramientas",
            "tool",
            "tools",
            "context_pack",
            "generador",
            "cli",
        }
        return not any(term in keywords for term in tool_terms)
    if "planing" in name or name in {"roadmap.md"} or rel_l.startswith("docs/adr/"):
        plan_terms = {
            "plan",
            "planing",
            "roadmap",
            "mcp",
            "neo4j",
            "fase",
            "phase",
            "adr",
            "decision",
            "arquitectura",
        }
        return not any(term in keywords for term in plan_terms)
    return False


def role_adjustment(info: FileInfo) -> float:
    """Ajusta por el rol del archivo para no confundir docs/planes con codigo."""
    rel = info.rel.lower()
    name = os.path.basename(rel)
    adjust = 0.0
    if info.is_doc:
        adjust -= 8.0
    if rel.startswith(("docs/", "scripts/")) or "planing" in name or name in {
        "readme.md",
        "agents.md",
        "contributing.md",
    }:
        adjust -= 10.0
    if name in {
        "views.py",
        "urls.py",
        "serializers.py",
        "models.py",
        "admin.py",
        "routes.py",
        "controllers.py",
    }:
        adjust += 18.0
    elif "/services/" in rel or rel.startswith("services/"):
        adjust += 8.0
    if rel.startswith("src/") or "/src/" in rel:
        adjust += 6.0
    return adjust


def score_file(
    info: FileInfo,
    keywords: Sequence[str],
    symbols: Sequence[str],
    weights: Optional[Dict[str, float]] = None,
) -> Tuple[float, List[str]]:
    score = 0.0
    reasons: List[str] = []
    rel_l = info.rel.lower()
    name_l = os.path.basename(rel_l)
    text_l = info.text.lower()
    weights = weights or {}

    for keyword in keywords:
        weight = weights.get(keyword, 1.0)
        if keyword in name_l:
            score += 14.0 * weight
            reasons.append("path:" + keyword)
        count = text_l.count(keyword)
        if count:
            score += min(count, 15) * 1.5 * weight

    for symbol in symbols:
        symbol_l = symbol.lower()
        if symbol_l in name_l:
            score += 35.0
            reasons.append("path:" + symbol)
        hits = len(
            re.findall(
                r"(?<![A-Za-z0-9_$])" + re.escape(symbol) + r"(?![A-Za-z0-9_$])",
                info.text,
                re.IGNORECASE,
            )
        )
        if hits:
            score += min(hits, 20) * 4.0
        for name, _start, _end in info.defs:
            if name.lower() == symbol_l:
                score += 60.0
                reasons.append("def:" + symbol)

    score += role_adjustment(info)
    if info.ext in SOURCE_EXTS:
        score += 4.0
    if info.is_test:
        score += 2.0
    if info.is_doc:
        score += 1.0
    if info.size > 200_000:
        score -= 20.0
    if info.size > 500_000:
        score -= 40.0
    if "/migrations/" in rel_l:
        score -= 8.0
    if ".min." in rel_l:
        score -= 30.0

    return score, reasons


def merge_ranges(ranges: Sequence[Tuple[int, int]]) -> List[Tuple[int, int]]:
    if not ranges:
        return []
    ordered = sorted(ranges)
    merged: List[Tuple[int, int]] = [ordered[0]]
    for start, end in ordered[1:]:
        last_start, last_end = merged[-1]
        if start <= last_end + 4:
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))
    return merged


def trim_ranges(ranges: Sequence[Tuple[int, int]], max_lines: int) -> List[Tuple[int, int]]:
    total = sum(end - start + 1 for start, end in ranges)
    if total <= max_lines:
        return list(ranges)
    result: List[Tuple[int, int]] = []
    remaining = max_lines
    for start, end in ranges:
        if remaining <= 0:
            break
        length = end - start + 1
        if length <= remaining:
            result.append((start, end))
            remaining -= length
        else:
            result.append((start, start + remaining - 1))
            remaining = 0
    return result


def build_windows(
    info: FileInfo,
    keywords: Sequence[str],
    symbols: Sequence[str],
    max_lines_per_file: int,
    max_windows: int = 4,
) -> List[Tuple[int, int]]:
    lines = info.lines
    total_lines = len(lines)
    if total_lines == 0:
        return []

    ranges: List[Tuple[int, int]] = []
    hit_lines: Set[int] = set()

    for symbol in symbols:
        symbol_l = symbol.lower()
        for name, start, end in info.defs:
            if name.lower() == symbol_l:
                ranges.append((max(1, start), min(total_lines, end)))
        for idx, line in enumerate(lines, 1):
            if symbol_l in line.lower():
                hit_lines.add(idx)

    for keyword in keywords:
        for idx, line in enumerate(lines, 1):
            if keyword in line.lower():
                hit_lines.add(idx)

    for idx in hit_lines:
        ranges.append((max(1, idx - 10), min(total_lines, idx + 14)))

    if not info.is_doc:
        ranges.append((1, min(25, total_lines)))

    if not ranges:
        ranges = [(1, min(total_lines, max_lines_per_file))]

    merged = merge_ranges(ranges)

    if len(merged) > max_windows:
        scored: List[Tuple[float, int, int]] = []
        for start, end in merged:
            block = "\n".join(lines[start - 1 : end]).lower()
            value = sum(block.count(keyword) for keyword in keywords)
            value += sum(block.count(symbol.lower()) for symbol in symbols)
            if start == 1:
                value += 5
            scored.append((value, start, end))
        scored.sort(key=lambda item: (-item[0], item[1]))
        merged = sorted((start, end) for _value, start, end in scored[:max_windows])

    return trim_ranges(merged, max_lines_per_file)


# ---------------------------------------------------------------------------
# Renderizado
# ---------------------------------------------------------------------------


def lang_for(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    return LANG_BY_EXT.get(ext, "")


def fence(text: str, lang: str = "", prefix: Optional[str] = None) -> str:
    body = text
    if prefix:
        body = prefix + "\n" + body
    marker = "```"
    while marker in body:
        marker += "`"
    if lang:
        return marker + lang + "\n" + body + "\n" + marker
    return marker + "\n" + body + "\n" + marker


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def truncate_text(text: str, max_tokens: int) -> str:
    if estimate_tokens(text) <= max_tokens:
        return text
    return text[: max_tokens * 4] + "\n... (truncado)\n"


def render_file_section(
    info: FileInfo,
    windows: Sequence[Tuple[int, int]],
    score: Optional[float] = None,
    reasons: Optional[Sequence[str]] = None,
) -> str:
    title = "### `" + info.rel + "`"
    if windows:
        covered = ", ".join("%d-%d" % (start, end) for start, end in windows)
        title += " (lineas " + covered + ")"
    if score is not None and score < 1000:
        title += " - score %.1f" % score
    parts = [title]
    if reasons:
        parts.append("Motivo: " + ", ".join(list(reasons)[:6]))
    for start, end in windows:
        code = "\n".join(info.lines[start - 1 : end])
        parts.append("**Lineas %d-%d**" % (start, end))
        parts.append(fence(code, lang_for(info.rel)))
    return "\n\n".join(parts) + "\n"


def repo_map(files: Sequence[str], max_lines: int = 70) -> str:
    tops: Dict[str, Dict[str, int]] = {}
    direct: Dict[str, int] = {}
    root_files: List[str] = []
    for rel in files:
        parts = rel.split("/")
        if len(parts) == 1:
            root_files.append(rel)
            continue
        top = parts[0]
        tops.setdefault(top, {})
        if len(parts) == 2:
            direct[top] = direct.get(top, 0) + 1
        elif len(parts) >= 3:
            child = parts[1]
            tops[top][child] = tops[top].get(child, 0) + 1

    lines = ["## Mapa del repo", "", "```text"]
    for top in sorted(tops):
        children = tops[top]
        total = direct.get(top, 0) + sum(children.values())
        lines.append(top + "/  (%d archivos)" % total)
        for child in sorted(children)[:10]:
            lines.append("  " + child + "/  (%d)" % children[child])
        if len(children) > 10:
            lines.append("  ... (%d subdirs mas)" % (len(children) - 10))
    if root_files:
        lines.append("")
        lines.append("Archivos raiz:")
        for name in sorted(root_files)[:12]:
            lines.append("  " + name)
        if len(root_files) > 12:
            lines.append("  ... (%d mas)" % (len(root_files) - 12))
    lines.append("```")
    if len(lines) > max_lines:
        lines = lines[: max_lines - 1] + ["...", "```"]
    return "\n".join(lines)


def header_section(
    args: argparse.Namespace,
    meta: Dict[str, str],
    n_files: int,
    keywords: Sequence[str],
    symbols: Sequence[str],
) -> str:
    title = args.task or (", ".join(symbols) if symbols else "archivos seleccionados")
    lines = [
        "# Context pack: " + title,
        "",
        "- Root: `" + meta["root"] + "`",
    ]
    if meta.get("branch"):
        lines.append("- Git: `" + meta["branch"] + "` @ `" + meta["commit"] + "`")
    lines.append("- Generado: " + _dt.datetime.now().strftime("%Y-%m-%d %H:%M"))
    lines.append("- Presupuesto: %d tokens (estimados)" % args.budget)
    lines.append("- Archivos incluidos: %d" % n_files)
    if keywords:
        lines.append("- Keywords: " + ", ".join("`" + k + "`" for k in keywords[:20]))
    if symbols:
        lines.append("- Simbolos: " + ", ".join("`" + s + "`" for s in symbols))
    lines.extend(
        [
            "",
            "## Como usar este contexto",
            "",
            "- Trabaja solo con los archivos y rangos incluidos.",
            "- Si falta algo, pide el simbolo o archivo exacto antes de asumir.",
            "- No inventes endpoints, modelos ni componentes.",
            "- Al terminar, ejecuta tests y lint, y resume los cambios.",
            "",
        ]
    )
    return "\n".join(lines)


def related_tests(
    infos: Sequence[FileInfo],
    selected: Sequence[FileInfo],
    keywords: Sequence[str],
    symbols: Sequence[str],
) -> List[FileInfo]:
    selected_rels = {info.rel for info in selected}
    stems = {
        os.path.splitext(os.path.basename(info.rel))[0]
        for info in selected
        if os.path.splitext(os.path.basename(info.rel))[0]
    }
    candidates: List[Tuple[float, FileInfo]] = []
    for info in infos:
        if not info.is_test or info.rel in selected_rels:
            continue
        score = 0.0
        for stem in stems:
            if stem and (stem in info.rel or stem in info.text):
                score += 8.0
        for symbol in symbols:
            if symbol.lower() in info.text.lower():
                score += 12.0
        for keyword in keywords:
            if keyword in info.rel.lower() or keyword in info.text.lower():
                score += 2.0
        if score >= 8.0 and len(info.lines) >= 5:
            candidates.append((score, info))
    candidates.sort(key=lambda item: (-item[0], item[1].size))
    return [info for _score, info in candidates]


def normalize_rel(path: str, root: str) -> str:
    if os.path.isabs(path):
        abs_path = os.path.abspath(path)
    else:
        abs_path = os.path.abspath(os.path.join(root, path))
    return os.path.relpath(abs_path, root).replace(os.sep, "/")


def is_under_root(abs_path: str, root: str) -> bool:
    try:
        return os.path.commonpath([os.path.abspath(abs_path), root]) == root
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# Construccion del pack
# ---------------------------------------------------------------------------


def build_pack(args: argparse.Namespace, root: str) -> str:
    meta = git_metadata(root)
    keywords = keywords_from_task(args.task or "")
    symbols: List[str] = []
    for raw in args.symbol:
        value = raw.strip()
        if not value:
            continue
        symbols.append(value)
        if "." in value:
            tail = value.split(".")[-1].strip()
            if tail:
                symbols.append(tail)
    symbols = list(dict.fromkeys(symbols))

    if not args.quiet:
        print("[context-pack] root=%s" % root, file=sys.stderr)
        print("[context-pack] keywords=%s" % ", ".join(keywords[:15]), file=sys.stderr)
        print("[context-pack] symbols=%s" % ", ".join(symbols), file=sys.stderr)

    files = collect_files(root, args.exclude, args.max_file_bytes)
    infos = load_infos(root, files, args.max_file_bytes)
    by_rel = {info.rel: info for info in infos}

    if not args.quiet:
        print("[context-pack] archivos escaneados=%d" % len(infos), file=sys.stderr)

    weights = keyword_weights(infos, keywords)
    anchor_rels = set(ANCHOR_FILES)
    scored: List[FileInfo] = []
    for info in infos:
        info.score, info.reasons = score_file(info, keywords, symbols, weights)
        if info.is_test or info.rel in anchor_rels:
            continue
        if keywords and is_offtopic_tooling(info.rel, keywords):
            continue
        if info.score >= args.min_score:
            scored.append(info)
    scored.sort(key=lambda info: (-info.score, info.size))
    if scored:
        score_floor = max(args.min_score, scored[0].score * 0.18)
        scored = [info for info in scored if info.score >= score_floor]

    explicit: List[FileInfo] = []
    for raw in args.file:
        rel = normalize_rel(raw, root)
        abs_path = os.path.join(root, rel)
        if not is_under_root(abs_path, root):
            print("[context-pack] aviso: %s esta fuera del root" % raw, file=sys.stderr)
            continue
        if is_excluded(rel, args.exclude):
            print("[context-pack] aviso: %s excluido por seguridad" % rel, file=sys.stderr)
            continue
        info = by_rel.get(rel)
        if info is None:
            suffix = rel.replace("\\", "/")
            matches = [candidate for candidate in by_rel if candidate.endswith("/" + suffix)]
            if len(matches) == 1:
                info = by_rel[matches[0]]
            elif len(matches) > 1:
                print(
                    "[context-pack] aviso: %s es ambiguo (%s)"
                    % (raw, ", ".join(sorted(matches)[:5])),
                    file=sys.stderr,
                )
        if info is None and os.path.isfile(abs_path):
            loaded = load_infos(root, [rel], args.max_file_bytes)
            info = loaded[0] if loaded else None
        if info is not None:
            info.score = max(info.score, 1000.0)
            info.reasons = ["explicit"] + info.reasons
            explicit.append(info)

    anchors: List[FileInfo] = []
    if not args.no_anchors:
        for rel in ANCHOR_FILES:
            info = by_rel.get(rel)
            if info is not None:
                anchors.append(info)

    candidates: List[FileInfo] = []
    seen_candidates: Set[str] = set()
    for info in explicit + scored:
        if info.rel in seen_candidates:
            continue
        seen_candidates.add(info.rel)
        candidates.append(info)

    if not candidates and not anchors:
        print(
            "[context-pack] aviso: no hay coincidencias; se incluira el mapa y los anclajes",
            file=sys.stderr,
        )

    parts: List[str] = []
    header = header_section(args, meta, 0, keywords, symbols)
    parts.append(header)
    used = estimate_tokens(header)

    diff_section = ""
    diff_reserve = 0
    if args.diff or args.staged:
        raw_diff = git_diff(root, staged=args.staged)
        if raw_diff.strip():
            raw_diff = truncate_text(raw_diff, max(800, int(args.budget * 0.18)))
            diff_section = "## Cambios locales\n\n" + fence(raw_diff, "diff")
            diff_reserve = estimate_tokens(diff_section)

    web_section = ""
    web_reserve = 0
    web_query = args.web_query or (args.task if args.web else "")
    if args.web or args.web_query or args.web_url:
        try:
            from web_context import build_web_context

            web_section = build_web_context(
                query=web_query,
                urls=args.web_url,
                max_results=args.web_max_results,
                fetch_results=args.web_fetch_results,
                max_chars_per_page=args.web_max_chars_page,
                max_total_chars=args.web_max_chars,
                no_fetch=args.no_web_fetch,
                allow_private=args.allow_private_web,
            )
            web_reserve = estimate_tokens(web_section)
        except Exception as exc:  # noqa: BLE001
            print(
                "[context-pack] aviso: no se pudo obtener contexto web: %s" % exc,
                file=sys.stderr,
            )

    budget = max(1000, args.budget - diff_reserve - web_reserve)

    if not args.no_tree:
        tree = repo_map(files)
        tree_tokens = estimate_tokens(tree)
        if used + tree_tokens <= int(budget * 0.16):
            parts.append(tree)
            used += tree_tokens

    included_rels: Set[str] = set()
    included_infos: List[FileInfo] = []

    explicit_limit = int(budget * 0.60)
    for info in explicit:
        if info.rel in included_rels:
            continue
        windows = [(1, min(len(info.lines), args.max_file_lines))]
        section = render_file_section(info, windows, reasons=["archivo solicitado"])
        section_tokens = estimate_tokens(section)
        if used + section_tokens > explicit_limit:
            windows = [(1, min(len(info.lines), max(40, args.max_file_lines // 2)))]
            section = render_file_section(info, windows, reasons=["archivo solicitado"])
            section_tokens = estimate_tokens(section)
            if used + section_tokens > explicit_limit:
                continue
        parts.append(section)
        used += section_tokens
        included_rels.add(info.rel)
        included_infos.append(info)

    for info in anchors:
        if info.rel in included_rels:
            continue
        windows = [(1, min(len(info.lines), 90))]
        section = render_file_section(info, windows, reasons=["documento base"])
        section_tokens = estimate_tokens(section)
        if used + section_tokens > int(budget * 0.22):
            continue
        parts.append(section)
        used += section_tokens
        included_rels.add(info.rel)
        included_infos.append(info)

    code_limit = int(budget * 0.78)
    for info in candidates:
        if info.rel in included_rels:
            continue
        windows = build_windows(info, keywords, symbols, args.max_file_lines)
        section = render_file_section(info, windows, info.score, info.reasons)
        section_tokens = estimate_tokens(section)
        if used + section_tokens > code_limit:
            windows = trim_ranges(windows, max(20, args.max_file_lines // 2))
            section = render_file_section(info, windows, info.score, info.reasons)
            section_tokens = estimate_tokens(section)
            if used + section_tokens > code_limit:
                continue
        parts.append(section)
        used += section_tokens
        included_rels.add(info.rel)
        included_infos.append(info)
        if len(included_infos) >= args.max_files:
            break

    if not args.no_tests:
        test_limit = int(budget * 0.88)
        for info in related_tests(infos, included_infos, keywords, symbols)[: args.max_tests]:
            if info.rel in included_rels:
                continue
            windows = build_windows(info, keywords, symbols, args.max_file_lines)
            section = render_file_section(info, windows, info.score, ["test relacionado"])
            section_tokens = estimate_tokens(section)
            if used + section_tokens > test_limit:
                continue
            parts.append(section)
            used += section_tokens
            included_rels.add(info.rel)
            included_infos.append(info)
            if len(included_infos) >= args.max_files:
                break

    if web_section:
        parts.append(web_section)
        used += estimate_tokens(web_section)

    if diff_section:
        parts.append(diff_section)
        used += estimate_tokens(diff_section)

    if not included_infos:
        parts.append(
            "## Sin archivos seleccionados\n\n"
            "Prueba con `--task`, `--symbol` o `--file`. Tambien puedes subir el presupuesto."
        )

    # Reemplaza el contador de archivos del header.
    parts[0] = header_section(args, meta, len(included_infos), keywords, symbols)

    parts.append(
        "## Nota\n\n"
        "Estimacion: ~%d tokens. Si falta contexto, vuelve a ejecutar con "
        "`--symbol` o `--file` para anadir archivos concretos." % used
    )
    return "\n\n".join(parts).rstrip() + "\n"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Genera un feature pack de contexto para una tarea de desarrollo.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--task", "-t", default="", help="Descripcion de la tarea")
    parser.add_argument(
        "--symbol",
        "-s",
        action="append",
        default=[],
        help="Simbolo a buscar (repetible): clase, funcion, componente, hook...",
    )
    parser.add_argument(
        "--file",
        "-f",
        action="append",
        default=[],
        help="Archivo a incluir (repetible, ruta relativa al root)",
    )
    parser.add_argument("--root", "-r", default=".", help="Raiz del proyecto")
    parser.add_argument(
        "--budget",
        "-b",
        type=int,
        default=30000,
        help="Presupuesto aproximado en tokens",
    )
    parser.add_argument("--out", "-o", default="", help="Archivo Markdown de salida")
    parser.add_argument(
        "--diff",
        action="store_true",
        help="Incluye el diff local no staged",
    )
    parser.add_argument(
        "--staged",
        action="store_true",
        help="Incluye el diff staged",
    )
    parser.add_argument(
        "--web",
        action="store_true",
        help="Busca en internet usando --task como consulta",
    )
    parser.add_argument(
        "--web-query",
        default="",
        help="Consulta web explicita (tiene prioridad sobre --task)",
    )
    parser.add_argument(
        "--web-url",
        action="append",
        default=[],
        help="URL concreta a incluir (repetible)",
    )
    parser.add_argument("--web-max-results", type=int, default=3)
    parser.add_argument("--web-fetch-results", type=int, default=2)
    parser.add_argument("--web-max-chars-page", type=int, default=5000)
    parser.add_argument("--web-max-chars", type=int, default=8000)
    parser.add_argument(
        "--no-web-fetch",
        action="store_true",
        help="Usa solo snippets, sin descargar paginas",
    )
    parser.add_argument(
        "--allow-private-web",
        action="store_true",
        help="Permite URLs locales/privadas en la busqueda web",
    )
    parser.add_argument(
        "--max-file-lines",
        type=int,
        default=220,
        help="Maximo de lineas por archivo incluido",
    )
    parser.add_argument(
        "--max-file-bytes",
        type=int,
        default=512 * 1024,
        help="Tamano maximo de archivo a leer",
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=40,
        help="Maximo de archivos incluidos",
    )
    parser.add_argument(
        "--max-tests",
        type=int,
        default=8,
        help="Maximo de tests relacionados incluidos",
    )
    parser.add_argument(
        "--min-score",
        type=float,
        default=8.0,
        help="Puntuacion minima para incluir un archivo (salvo --file)",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="Patron glob adicional a excluir (repetible)",
    )
    parser.add_argument(
        "--no-anchors",
        action="store_true",
        help="No incluir AGENTS.md/README/docs/ARCHITECTURE.md/pyproject.toml",
    )
    parser.add_argument(
        "--no-tests",
        action="store_true",
        help="No incluir tests relacionados",
    )
    parser.add_argument(
        "--no-tree",
        action="store_true",
        help="No incluir el mapa del repo",
    )
    parser.add_argument("--quiet", "-q", action="store_true", help="Silencia diagnosticos")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    if not any(
        [
            args.task,
            args.symbol,
            args.file,
            args.diff,
            args.staged,
            args.web,
            args.web_query,
            args.web_url,
        ]
    ):
        print(
            "Indica al menos --task, --symbol, --file, --diff, --staged o una opcion web.",
            file=sys.stderr,
        )
        return 2
    if args.web and not (args.task or args.web_query):
        print("--web requiere --task o --web-query.", file=sys.stderr)
        return 2
    if args.budget < 1000:
        print("--budget debe ser >= 1000", file=sys.stderr)
        return 2

    root = os.path.abspath(args.root)
    if not os.path.isdir(root):
        print("El root no existe: %s" % root, file=sys.stderr)
        return 2

    pack = build_pack(args, root)

    if args.out:
        out_path = os.path.abspath(os.path.join(root, args.out))
        try:
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            with open(out_path, "w", encoding="utf-8") as handle:
                handle.write(pack)
        except OSError as exc:
            print("No se pudo escribir el pack: %s" % exc, file=sys.stderr)
            return 1
        if not args.quiet:
            print(
                "[context-pack] escrito %s (~%d tokens)"
                % (out_path, estimate_tokens(pack)),
                file=sys.stderr,
            )
    else:
        sys.stdout.write(pack)
        if not args.quiet:
            print(
                "[context-pack] ~%d tokens" % estimate_tokens(pack),
                file=sys.stderr,
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
