# Roadmap del Proyecto

Este documento establece el plan de trabajo de **McpServer**: convertirlo en el
servidor MCP del ecosistema de trabajo —registros MCP enchufables activables por
perfil— con contexto quirúrgico y memoria persistente.

Aqui solo entran fases cuyo trabajo **se escribe, se prueba y se versiona en este
repo**. Lo que hagan los modelos con ese contexto se mide en el entorno, no aqui
(ver "Fuera del alcance" al final).

---

## Estado Global

| Fase | Estado | Objetivo |
|---|---|---|
| **0. Baseline MCP** | **Completada** | Paquete `mcp_server` stdio-first con el registro `code` (`repo_map`, `search_code`, `get_symbol`, `get_feature_pack`) y tests unitarios al 100%. |
| **1. Registro `memory` (Neo4j) y perfiles** | **Siguiente** | Perfiles por subcomando + alta del registro de memoria: Neo4j en la Raspberry Pi, lecturas tipadas y escrituras destiladas. |
| **2. Workflow Autónomo de Issues** | **Pendiente** | Plantilla de issue + bucle automatizado: Issue -> feature pack -> propuesta y diff -> edición -> tests -> commit. |
| **3. Grafo de Impacto** | **Pendiente** | Registro `graph`: predecir qué se rompe al modificar un componente o función antes de aplicar cambios. |

---

## Detalle de Fases

### Fase 0: Baseline MCP de Dominio (Completada)
- [x] Paquete `mcp_server/` con FastMCP y `pyproject.toml`.
- [x] Filtrado de exclusiones, secretos y dependencias (`core/config.py`, `core/scanner.py`).
- [x] Extractor AST de símbolos y definiciones (`core/symbols.py`).
- [x] Búsqueda quirúrgica sin volcado de ficheros (`core/search.py`).
- [x] Empaquetador de feature packs con presupuesto (`core/pack.py`).
- [x] Tools FastMCP (`tools/code.py`): `repo_map`, `search_code`, `get_symbol`, `get_feature_pack`.
- [x] Batería de pruebas unitarias (`tests/`) pasando al 100%.
- [x] Archivo formal de ADRs antiguos y creación de ADR 0001.

### Fase 1: Registro `memory` y perfiles de servidor (Siguiente)
- [ ] Perfiles por subcomando en `mcp_server/__main__.py` (`code`, `memory`,
      `all`, `--exclude`/`--only`) y `create_server(profile)` en `server.py`.
      Cada perfil construye su propio `FastMCP` con sus `instructions`.
- [ ] Tests de perfil: assertar el conjunto exacto de tools montadas por cada
      perfil con `list_tools()`.
- [ ] Implementar `mcp_server/tools/memory.py` con `register_memory_tools(mcp)`:
  - `get_project_context(project_name)`: recupera decisiones y tecnologías de la Raspberry Pi.
  - `log_decision(title, rationale, alternatives)`: registra un nodo `:Memory:Decision` validado.
  - `search_knowledge(query)`: consulta en el grafo con salida tipada y citas.
- [ ] Enlace directo con la Raspberry Pi (`bolt://192.168.1.128:7687`) con degradación limpia si la red no está disponible.
- [ ] Criterio de memoria: solo entidades destiladas (criterio global en
      `~/.gemini/config/AGENTS.md`). Sin volcados de código ni logs.
- [ ] No duplicar `mcp-neo4j-cypher`: Cypher crudo read-only sigue allí; aquí
      van las escrituras validadas y las lecturas de alto nivel.
- [ ] Esquema del grafo de código documentado en el ADR, **sin indexador**
      hasta la Fase 3 (un grafo desactualizado responde mal con seguridad).

### Fase 2: Workflow Autónomo de Issues
- [ ] Definir plantilla estándar de issue (`sintoma`, `reproduccion`, `candidatos`, `criterio de exito`).
- [ ] Automatizar el bucle de desarrollo desde el lado del repo:
  `Issue -> get_feature_pack() -> propuesta y diff del cliente MCP -> aplicacion -> pytest -> commit`.
  El razonamiento lo hace el consumidor (Strata o un LLM de suscripcion); aqui
  solo se preparan el pack, la plantilla y el bucle de validacion.

### Fase 3: Grafo de Impacto de Código
- [ ] Modelar dependencias entre módulos en Neo4j (archivo -> importa -> símbolo -> llamado_por).
- [ ] Tool `impact_of_change(symbol)`: reporta qué partes del repo se ven afectadas antes de tocar una línea.

---

## Fuera del alcance de este repo

Cosas que forman parte del ecosistema pero **no** son trabajo nuestro, y que por
eso ya no aparecen como fases:

- **Evaluación de Strata y de los LLMs de suscripción.** Medir hasta qué punto
  resuelven tareas reales de desarrollo con nuestro contexto (catálogo de
  pruebas, tokens/s, acierto en tests, corrección humana) es trabajo del
  entorno de trabajo, no un entregable versionable aqui. Este repo solo
  garantiza que el contexto que consumen sea quirúrgico y suficiente.
- **El MCP `strata-local`** (`strata_chat`, `strata_status`) y el atajo
  `/strata`: los monta Antigravity en su config MCP global.
- **MCPs externos** ya cubiertos: `mcp-neo4j-cypher` y `duckduckgo-mcp-server`.
- **La app Strata y el motor llama.cpp** (gateway `127.0.0.1:18500`): se
  gestionan desde el entorno. Los lanzadores de `scripts/` solo suben un
  `llama-server` aparte para probar que los servidores MCP se montan dentro de
  `llama-server`.
