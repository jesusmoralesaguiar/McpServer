# Arquitectura del Sistema: McpServer

## 1. Visión General

**McpServer es el servidor MCP del ecosistema de trabajo.** Cada capacidad que
usan los modelos se da de alta como un **registro MCP** (módulo enchufable) y un
**perfil** decide qué registros se montan en cada arranque. Ver
[ADR 0001](adr/0001-perfiles-de-servidor-registros-mcp-y-memoria-neo4j.md).

```text
+--------------------------------------------------------------------------+
|                            Consumidores                                  |
|  Strata Local / llama.cpp | Antigravity | Cursor | Claude | LLM subscr.  |
+------------------------------------+-------------------------------------+
                                     |
                                     | Protocolo MCP (stdio / HTTP)
                                     v
+--------------------------------------------------------------------------+
|                mcpserver <perfil>   (un paquete, N registros)            |
|  perfiles: all (default) | code | memory | --exclude web | --only ...    |
|                                                                          |
|  registros (módulos con register_<registro>_tools(mcp)):                 |
|  - code   (activo):  repo_map, search_code, get_symbol,                  |
|                      get_feature_pack                                    |
|  - memory (Fase 1):  get_project_context, log_decision,                  |
|                      search_knowledge                                    |
|  - graph  (Fase 3):  impacto de cambios (esquema reservado)              |
+-------------------+-----------------------------------+------------------+
                    |                                   |
                    v                                   v
+-------------------------------+       +----------------------------------+
|   Repositorio / Código Local  |       | Memoria Persistente (Neo4j RPi)  |
| - Escaneo seguro y sin ruido  |       | - bolt://192.168.1.128:7687      |
| - Filtro estricto de secretos |       | - Entidades destiladas (:Memory) |
| - AST & Parser sintáctico     |       | - Decisiones y dependencias      |
+-------------------------------+       +----------------------------------+

No duplicamos: `mcp-neo4j-cypher` (Cypher crudo read-only) y
`duckduckgo-mcp-server` (web search/fetch) siguen siendo MCP genéricos.
El registro `memory` es complementario: escribe con criterio y devuelve
lecturas tipadas.
```

---

## 2. Componentes del ecosistema

### A. Motor de Inferencia Local: Strata (RTX 5070 Ti)
* **Modelo:** `Qwen3.8-Flash-Next IQ3_S` con drafter DFlash2 (`--spec 6`).
* **Hardware:** NVIDIA GeForce RTX 5070 Ti (16 GB VRAM) + Intel Core i7-12700KF.
* **Capacidad:** Contexto de hasta 128K (`--max-context 131072`) con KV residente de 16K (`--kv-resident 16384`), generando a ~55–70 tok/s.
* **Integración:** Endpoints locales `http://127.0.0.1:18500` (Gateway) y `http://127.0.0.1:8080` (Engine), expuesto vía MCP global `strata-local` (`strata_chat`, `strata_status`) y activable con `/strata`. Ese MCP y el atajo viven en la config MCP global del entorno (Antigravity), **no** en este repositorio.

### B. Servidor MCP: `mcp_server`
* **Tecnología:** Python 3.10+, FastMCP, MCP SDK oficial, Pydantic.
* **Transporte principal:** `stdio` (arranque directo con `python -m mcp_server --transport stdio`).
* **Modelo de registros:** cada capacidad es un módulo en `mcp_server/tools/`
  que expone `register_<registro>_tools(mcp)`. Un **perfil** decide qué módulos
  se montan y con qué `instructions`:

  ```bash
  mcpserver              # perfil all: todos los registros
  mcpserver code         # solo herramientas de código
  mcpserver memory       # solo memoria Neo4j
  mcpserver all --exclude web
  ```

  Un perfil construye su propio `FastMCP` (esquema de tools mínimo para el
  modelo que lo consume) y puede montarse en un servidor agregador con `mount()`.
* **Registro `code` (activo):**
  1. `repo_map`: Estructura arbórea condensada y balance de directorios.
  2. `search_code`: Búsqueda acotada con líneas de contexto sin volcar ficheros.
  3. `get_symbol`: Extracción de clases, funciones y componentes por AST.
  4. `get_feature_pack`: Empaquetado en Markdown ajustado a un presupuesto de tokens para resolver issues.
* **Registro `memory` (Fase 1):** lecturas tipadas de alto nivel
  (`get_project_context`, `search_knowledge`) y escrituras destiladas
  (`log_decision`) en Neo4j. El Cypher crudo y libre sigue en
  `mcp-neo4j-cypher`; no se duplican tools.
* **Seguridad:** Filtrado automático de secretos (`.env*`, certificados, claves SSH) y directorios masivos (`node_modules`, `.venv`, cachés).

### C. Memoria Persistente en Grafo: Neo4j (Raspberry Pi)
* **Ubicación:** Raspberry Pi (`bolt://192.168.1.128:7687`, HTTP: `7474`).
* **Criterio de memoria:** definido a nivel global en `~/.gemini/config/AGENTS.md`.
  Solo almacena entidades conceptuales duraderas (`:Memory:project`,
  `:Memory:Decision`, `:Memory:Skill`). Prohibido volcar código en bruto o logs
  efímeros.

---

## 3. Estado de los Componentes

| Componente | Rol en el Sistema | Estado |
|---|---|---|
| `mcp_server/` | Servidor MCP con registros por perfil (`code` activo) | **Activo y testeado** |
| Strata Local | Motor de razonamiento e inferencia en RTX 5070 Ti | **Activo** |
| Modelos de suscripción | Consumidores de los mismos registros vía MCP | **Activo** |
| Neo4j en Pi | Grafo de conocimiento y memoria persistente | **Activo** |
| Registro `memory` | Tools tipadas de memoria sobre Neo4j | **Pendiente** (Fase 1) |
| `tests/` | Batería de pruebas unitarias del servidor MCP | **Activo** (100% pasando) |
| `scripts/` | Utilidades complementarias (`context_pack.py`, `web_context.py`) | **Referencia/soporte** |
| `docs/` | Visión, arquitectura, roadmap y ADRs | **Activo** |

---

## 4. Filosofía de Contexto Quirúrgico

Incluso disponiendo de una ventana amplia de 128K en Strata, **la sobrecarga de contexto degrada la atención del modelo y eleva la latencia**. El principio rector es:
* **Nunca volcar un repositorio entero.**
* **Nunca volcar archivos completos si solo se necesita una función.**
* **Producir feature packs autocontenidos con tests y rutas exactas.**
* **No encender todos los registros en un modelo pequeño sin medir.** Cada tool
  registrada añade su esquema al prompt; los perfiles existen para pagar solo
  el coste del registro que aporta valor en la tarea. El coste exacto por tool
  es una estimación (orden de centenas de tokens) y debe medirse en Strata
  antes de decidir qué perfil usar.
