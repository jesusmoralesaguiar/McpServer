# AGENTS.md — McpServer

> **Reglas Globales Heredadas:** Este proyecto hereda automáticamente las
> directivas globales del ecosistema de trabajo, hardware (Strata RTX 5070 Ti)
> y criterios de memoria persistente en Neo4j definidas a nivel global en
> `~/.gemini/config/AGENTS.md`.

Guia para agentes que trabajen en este repo. **McpServer es el servidor MCP del
ecosistema de trabajo**: cada capacidad se da de alta como un **registro MCP**
(modulo enchufable) y un **perfil** decide que registros se montan. Lo consumen
Strata Local, los LLMs de suscripcion y cualquier cliente MCP estandar.

## Idea central

**McpServer** es un servidor MCP stdio-first escrito en Python (`mcp_server/`):

- Un paquete, N **registros**: cada modulo de `mcp_server/tools/` expone
  `register_<registro>_tools(mcp)`.
- **Perfiles por subcomando**: `mcpserver`, `mcpserver code`,
  `mcpserver memory`, `mcpserver all --exclude web`. Cada perfil construye su
  propio `FastMCP` con sus `instructions` y solo sus tools.
- Registro `code` (activo): `repo_map`, `search_code`, `get_symbol`,
  `get_feature_pack`, con filtrado estricto de exclusiones, secretos y
  dependencias.
- Registro `memory` (Fase 1): memoria de proyecto en Neo4j con lecturas tipadas
  y escrituras destiladas.
- Feature packs con presupuesto de tokens, sin volcados de ficheros completos.

### Lo que NO es de este repo (no busques aqui su codigo)

- **Strata Local** es un **consumidor**, no un registro nuestro. El modelo
  `Qwen3.8-Flash-Next IQ3_S` corre en la RTX 5070 Ti via llama.cpp y lo gestiona
  la app Strata del entorno (gateway `http://127.0.0.1:18500`). El MCP
  `strata-local` (`strata_chat`, `strata_status`) y el atajo `/strata` los monta
  **Antigravity** en su config MCP global: en este repo no hay ni una linea de
  ese codigo.
- **Otros MCP externos** que tampoco implementamos ni duplicamos:
  `mcp-neo4j-cypher` (Cypher crudo read-only) y `duckduckgo-mcp-server`
  (web search/fetch).

### Lo que SI esta aqui pero fuera del paquete

- **Scripts de contexto** en `scripts/`: `context_pack.py` (feature pack de
  repo) y `web_context.py` (brief web citable). CLI sin MCP, para preparar
  contexto a mano.
- **Lanzadores del motor local**: `start_llama.ps1` / `start_llama.bat` /
  `check_tools.ps1`. Solo envuelven alias de WSL para subir un `llama-server`
  aparte en el puerto `8080` y comprobar que levante sus servidores MCP. No son
  el gateway de Strata. Son conveniencia del entorno; no forman parte del paquete
  ni de sus tests.

## Documentos que debes leer

| Si vas a... | Lee |
|---|---|
| Entender el proyecto | `docs/STRATEGY.md` + `docs/ARCHITECTURE.md` |
| Decidir que hacer | `docs/ROADMAP.md` |
| Ver decisiones | `docs/adr/` |

## Estado actual

- `mcp_server/`: baseline completada (Fase 0). Registro `code` con tests al 100%.
- Transporte: **stdio-first**. No requiere base de datos, Docker ni servicios
  externos para funcionar.
- Arquitectura de registros y perfiles: decidida en `docs/adr/0001-*.md`
  (pendiente de implementacion en Fase 1).
- Registro `memory` (Neo4j en Raspberry Pi): pendiente (Fase 1), con degradacion
  limpia si la red no esta disponible. El grafo de codigo queda **reservado**
  hasta la Fase 3.
- La evaluacion del modelo local no es trabajo de este repo: ver
  "Fuera del alcance" en `docs/ROADMAP.md`.

## Arranque rapido

```bash
# Instalar el paquete en modo editable
pip install -e .

# Arrancar el servidor MCP (stdio), perfil all
mcpserver

# Perfiles: solo codigo, solo memoria, o recorte fino
mcpserver code
mcpserver memory
mcpserver all --exclude web

# Tools de linea de comandas (sin MCP)
python scripts/context_pack.py --task "descripcion" --budget 24000 --out context/tarea.md
python scripts/web_context.py --query "FastMCP stdio server" --max-results 3 --out context/web.md
```

## Estructura

```text
McpServer/
|-- AGENTS.md
|-- README.md
|-- pyproject.toml           Paquete, deps y entrypoint del servidor
|-- docs/                    Vision, arquitectura, roadmap, ADRs
|-- mcp_server/
|   |-- core/                config, scanner, symbols, search, pack
|   |-- tools/               registros (code.py; memory.py en Fase 1)
|   |-- server.py            create_server(profile)
|   + -- __main__.py         Arranque stdio + perfiles por subcomando
|-- scripts/                 context_pack.py, web_context.py, lanzadores llama
+-- tests/                   Pruebas unitarias del paquete
```

## Reglas para agentes

1. **stdio-first.** El servidor y sus tools deben arrancar sin servicios
   externos. Cualquier dependencia de red o base de datos debe degradar con
   mensaje claro, nunca petar.
2. **No duplicar tools genericas.** Schema/Cypher crudo/web search ya estan
   cubiertos por `mcp-neo4j-cypher` y `duckduckgo-mcp-server`. Nuestros registros
   son complementarios: lecturas tipadas de alto nivel y escrituras validadas.
3. **No acoplar el MCP a frameworks web.** Acceso directo al sistema de
   archivos, grafo o DB; si falta un servicio, degradacion explicita.
4. **Contexto justo, no maximo.** Usa feature packs y busqueda quirurgica; no
   vuelques el repo entero ni ficheros completos.
5. **Secretos fuera.** El scanner filtra `.env`, claves y tokens; no los leas ni
   los imprimas.
6. **No inventes** endpoints, versiones, APIs ni resultados de tests.
7. **Web con citas.** Si la respuesta depende de internet, busca y cita URLs.
8. **Tests/lint antes de cerrar:** `python -m pytest tests -q` desde la raiz.
9. **Un cliente por interfaz.** El servidor MCP es la interfaz; no añadas
   frontends ni APIs HTTP salvo que aporten algo que stdio no tenga.
10. **Documenta decisiones** relevantes en `docs/adr/`.
11. **Memoria en Neo4j con criterio.** Guarda entidades y relaciones destiladas
    (nodos `:Memory`); no vuelques codigo en bruto ni logs temporales.

## Comandos utiles

```bash
# Tests del paquete
python -m pytest tests -q

# Empaquetado de contexto de una tarea
python scripts/context_pack.py --task "anadir tool de impacto" --budget 24000

# Lint/formato (si hay config)
python -m ruff check mcp_server scripts tests
```

## Roadmap resumido

Detalle y estados en `docs/ROADMAP.md`:

- **Fase 0 — Baseline MCP**: completada.
- **Fase 1 — Registro `memory` (Neo4j) y perfiles**: siguiente.
- **Fase 2 — Workflow autonomo de issues**: pendiente.
- **Fase 3 — Grafo de impacto de codigo** (`graph`): pendiente.

La evaluacion del modelo local (Strata y LLMs de suscripcion) **no es una fase de
este repo**: se mide en el entorno de trabajo. Aqui solo se garantiza el contexto
que consumen. Ver "Fuera del alcance" en `docs/ROADMAP.md`.

## Arranque de una sesion nueva

Di siempre:

> "Lee AGENTS.md, docs/STRATEGY.md y docs/ROADMAP.md. El proyecto es McpServer:
> el servidor MCP del ecosistema, con registros enchufables (primero `code`,
> luego `memory` en Neo4j) y perfiles por subcomando. [Describe que quieres
> hacer hoy]"

## No leer salvo que se pida

- `node_modules/`, `dist/`, `build/`, `.venv/`, `__pycache__/`
- `*.gguf`, `*.log`
- `.env`, claves, `mcp.json` completo (puede contener credenciales)
