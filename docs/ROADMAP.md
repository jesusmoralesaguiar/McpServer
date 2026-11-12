# Roadmap del Proyecto

Este documento establece el plan de trabajo actual: convertir **McpServer** en
el servidor MCP del ecosistema de trabajo —registros MCP enchufables activables
por perfil— y medir hasta qué punto **Strata Local** y los modelos de
suscripción pueden resolver tareas reales de desarrollo con ese contexto.

---

## Estado Global

| Fase | Estado | Objetivo |
|---|---|---|
| **0. Baseline MCP** | **Completada** | Paquete `mcp_server` stdio-first con el registro `code` (`repo_map`, `search_code`, `get_symbol`, `get_feature_pack`) y tests unitarios al 100%. |
| **1. Evaluación con Strata** | **En curso** | Probar y medir la capacidad de Strata para resolver tareas reales de desarrollo con contexto quirúrgico. |
| **2. Registro `memory` (Neo4j)** | **Siguiente** | Perfiles por subcomando + alta del registro de memoria: Neo4j en la Raspberry Pi, lecturas tipadas y escrituras destiladas. |
| **3. Workflow Autónomo de Issues** | **Pendiente** | Pipeline completo: Issue -> Feature Pack MCP -> Razonamiento Strata -> Edición -> Tests -> Validación. |
| **4. Grafo de Impacto** | **Pendiente** | Registro `graph`: predecir qué se rompe al modificar un componente o función antes de aplicar cambios. |

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

### Fase 1: Evaluación con Strata como Motor de Proyecto (En curso)
- [x] Integración de Strata vía MCP `strata-local` (`strata_chat`) y atajo `/strata`.
- [ ] Definir el catálogo de pruebas tipo (benchmark local):
  1. Comprensión de arquitectura y diagnóstico de bugs.
  2. Refactorizaciones acotadas en ficheros reales.
  3. Creación de nuevos endpoints o módulos respetando tipado y tests.
  4. Generación de tests unitarios a partir de firmas AST.
- [ ] Medir métricas de rendimiento con Strata: tokens/s, acierto en tests, necesidad de corrección humana.

### Fase 2: Registro `memory` y perfiles de servidor
- [ ] Perfiles por subcomando en `mcp_server/__main__.py` (`code`, `memory`,
      `all`, `--exclude`/`--only`) y `create_server(profile)` en `server.py`.
      Cada perfil construye su propio `FastMCP` con sus `instructions`.
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
      hasta la Fase 4 (un grafo desactualizado responde mal con seguridad).

### Fase 3: Workflow Autónomo de Issues
- [ ] Definir plantilla estándar de issue (`sintoma`, `reproduccion`, `candidatos`, `criterio de exito`).
- [ ] Automatizar el bucle de desarrollo:
  `Issue -> get_feature_pack() -> Strata (propuesta y diff) -> aplicacion -> pytest -> commit`.

### Fase 4: Grafo de Impacto de Código
- [ ] Modelar dependencias entre módulos en Neo4j (archivo -> importa -> símbolo -> llamado_por).
- [ ] Tool `impact_of_change(symbol)`: reporta qué partes del repo se ven afectadas antes de tocar una línea.
