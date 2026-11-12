"""Code-level tools for FastMCP: repo_map, search_code, get_symbol, get_feature_pack."""

from __future__ import annotations

import os
from typing import List, Optional

from fastmcp import FastMCP

from mcp_server.core.pack import build_feature_pack, build_repo_map
from mcp_server.core.search import search_code as core_search_code
from mcp_server.core.symbols import find_symbol


def register_code_tools(mcp: FastMCP) -> None:
    """Registers Level 0 code tools with the FastMCP instance."""

    @mcp.tool(
        name="repo_map",
        description=(
            "Devuelve un mapa compacto del repositorio (directorios principales, conteo de ficheros "
            "y estructura raíz), excluyendo dependencias (node_modules, venv), cachés y secretos. "
            "Ideal para orientarse rápidamente con mínimo consumo de contexto."
        ),
    )
    def repo_map(path: str = ".") -> str:
        target_path = os.path.abspath(path)
        if not os.path.isdir(target_path):
            return f"Error: la ruta especificada no existe o no es un directorio: {path}"
        return build_repo_map(target_path)

    @mcp.tool(
        name="search_code",
        description=(
            "Busca texto o patrones en los ficheros del código de forma quirúrgica. "
            "Devuelve ruta relativa, número de línea y un snippet acotado alrededor de cada match, "
            "evitando volcar ficheros completos al contexto."
        ),
    )
    def search_code(
        query: str,
        path: str = ".",
        glob_pattern: str = "",
        max_results: int = 20,
    ) -> str:
        target_path = os.path.abspath(path)
        if not os.path.isdir(target_path):
            return f"Error: la ruta no es un directorio válido: {path}"

        matches = core_search_code(
            query=query,
            root=target_path,
            glob_pattern=glob_pattern if glob_pattern.strip() else None,
            max_results=max_results,
        )

        if not matches:
            return f"No se encontraron coincidencias para '{query}' en '{path}'."

        lines = [f"### Coincidencias de búsqueda para '{query}' ({len(matches)} resultados):", ""]
        for m in matches:
            lines.append(f"- **`{m['file']}:{m['line']}`**")
            lines.append("```")
            lines.append(m["snippet"].rstrip())
            lines.append("```")
            lines.append("")
        return "\n".join(lines)

    @mcp.tool(
        name="get_symbol",
        description=(
            "Localiza y extrae la definición exacta de un símbolo (función, método, clase o componente) "
            "mediante AST (Python) o analizador sintáctico (JS/TS/otros). Devuelve la ruta del archivo, "
            "el rango de líneas y el código de la definición."
        ),
    )
    def get_symbol(name: str, path: str = ".") -> str:
        target_path = os.path.abspath(path)
        if not os.path.isdir(target_path):
            return f"Error: ruta inválida: {path}"

        results = find_symbol(symbol_name=name, root=target_path)
        if not results:
            return f"No se encontró ninguna definición para el símbolo '{name}' en '{path}'."

        blocks = [f"### Definiciones encontradas para el símbolo `{name}` ({len(results)}):", ""]
        for res in results:
            blocks.append(f"#### `{res['file']}` (líneas {res['start_line']}-{res['end_line']})")
            blocks.append("```python" if res['file'].endswith(".py") else "```")
            blocks.append(res["snippet"])
            blocks.append("```")
            blocks.append("")
        return "\n".join(blocks)

    @mcp.tool(
        name="get_feature_pack",
        description=(
            "Genera un feature pack quirúrgico en formato Markdown para una tarea o issue concreto "
            "dentro de un presupuesto de tokens especificado. Selecciona los fragmentos de código más "
            "relevantes sin inflar el contexto innecesariamente."
        ),
    )
    def get_feature_pack(
        task: str,
        path: str = ".",
        budget: int = 16000,
        symbols: str = "",
        files: str = "",
        include_diff: bool = False,
    ) -> str:
        target_path = os.path.abspath(path)
        if not os.path.isdir(target_path):
            return f"Error: ruta inválida: {path}"

        parsed_symbols: List[str] = [s.strip() for s in symbols.split(",") if s.strip()] if symbols else []
        parsed_files: List[str] = [f.strip() for f in files.split(",") if f.strip()] if files else []

        return build_feature_pack(
            task=task,
            root=target_path,
            budget=budget,
            symbols=parsed_symbols,
            files=parsed_files,
            include_diff=include_diff,
        )
