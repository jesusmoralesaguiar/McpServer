"""Context packaging and repo-map generation."""

from __future__ import annotations

import datetime as _dt
import math
import os
import re
from typing import Dict, List, Optional, Sequence, Set, Tuple

from mcp_server.core.config import (
    ANCHOR_FILES,
    LANG_BY_EXT,
    SOURCE_EXTS,
    STOPWORDS,
    SYNONYMS,
)
from mcp_server.core.scanner import (
    FileInfo,
    collect_files,
    git_diff,
    git_metadata,
    is_excluded,
    is_secret,
)
from mcp_server.core.symbols import extract_definitions

TEST_RE = re.compile(r"(^|[/_.\-])(tests?|specs?|__tests__)([/_.\-]|$)", re.IGNORECASE)
WORD_RE = re.compile(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ_][A-Za-z0-9ÁÉÍÓÚÜÑáéíóúüñ_./\\-]*")
QUOTED_RE = re.compile(r'"([^"]+)"|\'([^\']+)\'')
CAMEL_RE = re.compile(r"[A-Z]+(?=[A-Z][a-z]|\d|\b)|[A-Z]?[a-z]+|\d+")


def is_test_path(rel: str) -> bool:
    return bool(TEST_RE.search(rel))


def is_doc_path(rel: str) -> bool:
    name = os.path.basename(rel).lower()
    ext = os.path.splitext(name)[1].lower()
    if ext in {".md", ".mdx", ".rst", ".txt"}:
        return True
    return name.startswith(("readme", "agents", "contributing", "changelog"))


def load_file_infos(root: str, rels: Sequence[str], max_bytes: int = 1_000_000) -> List[FileInfo]:
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
        info.defs = extract_definitions(rel, text, lines)
        infos.append(info)
    return infos


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
        if len(keyword) >= 3 and keyword not in STOPWORDS and keyword not in seen:
            seen.add(keyword)
            result.append(keyword)
    return result[:40]


def keyword_weights(infos: Sequence[FileInfo], keywords: Sequence[str]) -> Dict[str, float]:
    total = max(1, len(infos))
    weights: Dict[str, float] = {}
    for keyword in keywords:
        df = sum(1 for info in infos if keyword in info.text.lower())
        weights[keyword] = max(0.5, min(5.0, math.log((total + 1) / (df + 1)) + 1.0))
    return weights


def is_offtopic_tooling(rel: str, keywords: Sequence[str]) -> bool:
    rel_l = rel.lower()
    name = os.path.basename(rel_l)
    if rel_l.startswith("scripts/"):
        tool_terms = {"script", "scripts", "herramienta", "tool", "tools", "context_pack", "cli"}
        return not any(term in keywords for term in tool_terms)
    if "planing" in name or name in {"roadmap.md"} or rel_l.startswith("docs/adr/"):
        plan_terms = {"plan", "planing", "roadmap", "mcp", "neo4j", "fase", "adr", "decision"}
        return not any(term in keywords for term in plan_terms)
    return False


def role_adjustment(info: FileInfo) -> float:
    rel = info.rel.lower()
    name = os.path.basename(rel)
    adjust = 0.0
    if info.is_doc:
        adjust -= 8.0
    if rel.startswith(("docs/", "scripts/")) or name in {"readme.md", "agents.md"}:
        adjust -= 10.0
    if name in {"views.py", "urls.py", "serializers.py", "models.py", "routes.py", "server.py"}:
        adjust += 18.0
    elif "/services/" in rel or rel.startswith("services/") or "/core/" in rel:
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
    if "/migrations/" in rel_l:
        score -= 8.0
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


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def fence(text: str, lang: str = "") -> str:
    body = text
    marker = "```"
    while marker in body:
        marker += "`"
    if lang:
        return marker + lang + "\n" + body + "\n" + marker
    return marker + "\n" + body + "\n" + marker


def render_file_section(
    info: FileInfo,
    windows: Sequence[Tuple[int, int]],
    score: Optional[float] = None,
    reasons: Optional[Sequence[str]] = None,
) -> str:
    ext = os.path.splitext(info.rel)[1].lower()
    lang = LANG_BY_EXT.get(ext, "")
    title = f"### `{info.rel}`"
    if windows:
        covered = ", ".join(f"{start}-{end}" for start, end in windows)
        title += f" (lineas {covered})"
    if score is not None and score < 1000:
        title += f" - score {score:.1f}"
    parts = [title]
    if reasons:
        parts.append("Motivo: " + ", ".join(list(reasons)[:6]))
    for start, end in windows:
        code = "\n".join(info.lines[start - 1 : end])
        parts.append(f"**Lineas {start}-{end}**")
        parts.append(fence(code, lang))
    return "\n\n".join(parts) + "\n"


def build_repo_map(root: str = ".", max_lines: int = 70) -> str:
    """Builds a compact summary tree of the repository files."""
    files = collect_files(root)
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
        lines.append(f"{top}/  ({total} archivos)")
        for child in sorted(children)[:10]:
            lines.append(f"  {child}/  ({children[child]})")
        if len(children) > 10:
            lines.append(f"  ... ({len(children) - 10} subdirs mas)")
    if root_files:
        lines.append("")
        lines.append("Archivos raiz:")
        for name in sorted(root_files)[:12]:
            lines.append(f"  {name}")
        if len(root_files) > 12:
            lines.append(f"  ... ({len(root_files) - 12} mas)")
    lines.append("```")
    if len(lines) > max_lines:
        lines = lines[: max_lines - 1] + ["...", "```"]
    return "\n".join(lines)


def build_feature_pack(
    task: str,
    root: str = ".",
    budget: int = 16000,
    symbols: Optional[List[str]] = None,
    files: Optional[List[str]] = None,
    max_file_lines: int = 120,
    max_files: int = 8,
    include_diff: bool = False,
) -> str:
    """Builds a surgical Markdown context pack for a task within a token budget."""
    meta = git_metadata(root)
    keywords = keywords_from_task(task or "")
    clean_symbols: List[str] = []
    for s in (symbols or []):
        s_clean = s.strip()
        if s_clean:
            clean_symbols.append(s_clean)
    clean_symbols = list(dict.fromkeys(clean_symbols))

    all_files = collect_files(root)
    infos = load_file_infos(root, all_files)
    by_rel = {info.rel: info for info in infos}
    weights = keyword_weights(infos, keywords)

    scored: List[FileInfo] = []
    for info in infos:
        info.score, info.reasons = score_file(info, keywords, clean_symbols, weights)
        if info.is_test or info.rel in ANCHOR_FILES:
            continue
        if keywords and is_offtopic_tooling(info.rel, keywords):
            continue
        if info.score >= 5.0:
            scored.append(info)
    scored.sort(key=lambda info: (-info.score, info.size))

    # Add explicitly requested files
    explicit: List[FileInfo] = []
    for f in (files or []):
        rel = f.replace("\\", "/").lstrip("./")
        if rel in by_rel and not is_secret(rel):
            info = by_rel[rel]
            info.score = max(info.score, 1000.0)
            info.reasons = ["explicit"] + info.reasons
            explicit.append(info)

    candidates: List[FileInfo] = []
    seen: Set[str] = set()
    for info in explicit + scored:
        if info.rel not in seen:
            seen.add(info.rel)
            candidates.append(info)

    # Compose output
    parts: List[str] = [
        f"# Context pack: {task or 'Surgical pack'}",
        f"- Root: `{meta['root']}` | Git: `{meta.get('branch', 'unknown')}` @ `{meta.get('commit', 'unknown')}`",
        f"- Presupuesto: {budget} tokens | Fecha: {_dt.datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
    ]
    used = estimate_tokens("\n".join(parts))

    # Tree
    tree = build_repo_map(root)
    tree_tokens = estimate_tokens(tree)
    if used + tree_tokens <= int(budget * 0.18):
        parts.append(tree)
        used += tree_tokens

    # Candidates code windows
    code_limit = int(budget * 0.85)
    included = 0
    for info in candidates:
        windows = build_windows(info, keywords, clean_symbols, max_file_lines)
        section = render_file_section(info, windows, info.score, info.reasons)
        section_tokens = estimate_tokens(section)
        if used + section_tokens > code_limit:
            windows = trim_ranges(windows, max(20, max_file_lines // 2))
            section = render_file_section(info, windows, info.score, info.reasons)
            section_tokens = estimate_tokens(section)
            if used + section_tokens > code_limit:
                continue
        parts.append(section)
        used += section_tokens
        included += 1
        if included >= max_files:
            break

    if include_diff:
        diff_text = git_diff(root)
        if diff_text.strip():
            diff_section = "## Cambios locales (diff)\n\n" + fence(diff_text[:3000], "diff")
            parts.append(diff_section)

    return "\n\n".join(parts).rstrip() + "\n"
