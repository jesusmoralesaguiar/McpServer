# Plan de Estudio: MCP + Neo4j + Chatbot RAG

## Estado actual del proyecto (Mayo 2026)

### Lo que ya existe

| Componente | Estado | Detalles |
|---|---|---|
| Django backend | 100% | 6 modelos, 10 endpoints REST, RAG con pgvector + Ollama |
| React frontend | 100% | Vite 8 + Tailwind CSS 4 + TanStack Query |
| PostgreSQL/pgvector | 100% | Vector embeddings (768-dim, HNSW index), Docker Compose |
| Redis | 100% | Memoria de conversacion (TTL 30min, sliding window 20) |
| Ollama | 100% | Modelo `minimax-m2.1:cloud`, embeddings `nomic-embed-text` |
| Bridge Neo4j | Campos creados | `Document.neo4j_node_id`, `DocumentChunk.neo4j_node_id` |
| Neo4j en Raspberry Pi | 100% | Datos de proyectos de desarrollo + estadisticas La Liga + memoria IA |
| MCP Server/Client | **No existe** | A construir |
| Dockerfile del app | **No existe** | Solo docker-compose para DBs |
| CI/CD | **No existe** | A construir |

### El patron de la empresa: ods-cicd-python-quicksilver-mcp

En `/mnt/c/Users/jesus/VS/ods-cicd-python-quicksilver-mcp/` tenemos un MCP server
de produccion del Santander ODS que sirve como **plantilla de referencia**:

**Arquitectura hexagonal (4 capas):**
```
cli.py -> MCP Server (main) -> Domain MCPs (10 sub-servers)
                                  |
                            Domain Services (BaseService[Input, Output])
                                  |
                            Infrastructure (DataSources -> HTTP -> Quicksilver API)
```

**Estructura de dominio MCP (patron exacto):**
```python
# model_context_protocol/domains/environments/mcp.py
from ods_mcp_core import OdsMCP
from pydantic import BaseModel, Field

mcp = OdsMCP(name="...", instructions="...")

@mcp.tool(
    name="list_environments",
    title="List Environments",
    description="Retrieve all environments...",
    tags={"quicksilver", "environments", "list"},
)
async def list_environments(
    appname: str = Field(description="The name of the application"),
) -> EnvironmentListResponse:
    ...
```

**Key takeaways del patron empresa:**
- FastMCP 3.0 con `@mcp.tool` decorator en funciones async
- Parametros tipados con `pydantic.Field(description=...)`
- Modelos Pydantic para input/output (`BaseModel`)
- Sub-MCPs por dominio montados en un servidor principal (`mcp.mount()`)
- Entry point: `cli.py` -> `parse_arguments(on_launch=start_mcp_server)`
- Transports: stdio / http / sse (configurable por `--mode`)
- Docker: `python:3.13-slim`, usuario no-root (`appuser:1000`)
- CI/CD: GitHub Actions + SonarQube + Ruff + Bandit
- Gestor de paquetes: `uv` con `pyproject.toml`
- **Sin BBDD** (la API REST de Quicksilver es el unico data store)

### Datos en Neo4j (Raspberry Pi)

El Neo4j en la Raspberry Pi funciona como **memoria general para tu IA local** con 3 dominios de datos reales:

1. **Proyectos de desarrollo**: aprendizajes, notas, tecnologias, decisiones de arquitectura
2. **Estadisticas La Liga**: equipos, jugadores, partidos, goles, clasificaciones
3. **Memoria general IA**: entidades, hechos y relaciones que el agente va persistir

Esto significa que el MCP server debe ser **generico**: capaz de consultar cualquier dominio
del grafo, no solo documentos RAG.

---

## Arquitectura objetivo

```
+---------------------------------------------------------------+
|                     MAQUINA DE DESARROLLO                     |
|                                                                |
|  +----------+    +--------------+    +-----------------------+ |
|  | React    |--->| Django       |--->| MCP Server (stdio)    | |
|  | (Vite)   |    | views.py     |    | mcp_server/cli.py     | |
|  +----------+    |              |    |                       | |
|                  | pgvector ----+    | +-------------------+ | |
|                  | Redis             | | knowledge_graph/  | | |
|                  | Ollama            | |   mcp.py          | | |
|                  +------------------+ | |                   | | |
|                                       | | @mcp.tool:        | | |
|                                       | | - query_graph     | | |
|                                       | | - discover_schema | | |
|                                       | | - search_nodes    | | |
|                                       | | - get_neighbors   | | |
|                                       | | - full_text_search| | |
|                                       | | - get_doc_graph   | | |
|                                       | | - sync_document   | | |
|                                       | +-------------------+ | |
|                                       +---------+-------------+ |
|                                                 | Bolt          |
+-------------------------------------------------+----------------+
                                                  |
+-------------------------------------------------+----------------+
|                  RASPBERRY PI                   |                |
|  +----------------------------------------------v-------------+  |
|  |  Neo4j (grafo multi-dominio)                              |  |
|  |                                                           |  |
|  |  Proyectos:   (:Project)-[:USES]->(:Technology)           |  |
|  |  Futbol:      (:Team)-[:PLAYED]->(:Match)<-[:SCORED_IN]-(:Player) |
|  |  RAG:         (:Document)-[:HAS_CHUNK]->(:Chunk)          |  |
|  |  Memoria IA:  (:Entity)-[:RELATED_TO]->(:Entity)          |  |
|  +-----------------------------------------------------------+  |
+-----------------------------------------------------------------+
```

**Flujo de una pregunta del usuario:**
```
Usuario pregunta "cuantos goles lleva el Barcelona?"
  |
  +-- Django views.py:chat()
  |     +-- pgvector (busqueda semantica, ya existe)
  |     +-- MCP Client -> MCP Server -> Neo4j RPi (nuevo: grafo)
  |     |     +-- search_nodes("Team", {name:"Barcelona"})
  |     |         get_neighbors(node_id, depth=2)
  |     +-- Prompt enriquecido -> Ollama -> Respuesta
```

---

## Decisiones de diseno tomadas

| Decision | Eleccion | Justificacion |
|---|---|---|
| **Ubicacion MCP Server** | Maquina de desarrollo | Simplicidad para empezar. El server se conecta a Neo4j en RPi via Bolt. |
| **Transporte** | stdio | Mas simple. El patron empresa soporta los 3 modos; empezamos con stdio. |
| **Datos en Neo4j (Fase 1)** | Herramientas genericas de grafo | Porque ya tienes datos multi-dominio (proyectos, futbol, memoria IA). Luego especializamos para RAG. |
| **Framework MCP** | `fastmcp` (sin wrapper interno `ods_mcp_core`) | El wrapper de la empresa es privado. fastmcp es equivalente y publico. |
| **Patron de codigo** | Hexagonal simplificado (empresa sin capas Service/Repository) | Seguimos el refactor `simplify-service-repository-layers` de la empresa. Tools llaman a DataSource directamente. |
| **Escritura en Neo4j** | Solo lectura en Fase 1, escritura en Fase 2 | Mas seguro para empezar. La escritura se anade cuando el flujo de lectura este estable. |

---

## Estructura de archivos a crear/modificar

```
Chatbot/                                  <- repo actual
|
|-- planing-estudio.md                    <- MODIFICADO (este archivo)
|
|-- mcp_server/                           <- NUEVO (patron empresa simplificado)
|   |-- pyproject.toml                    <- fastmcp + neo4j + pydantic + pydantic-settings
|   |-- cli.py                            <- entry point
|   |-- cli_tools/
|   |   |-- __init__.py
|   |   +-- arguments.py                  <- LaunchArguments(mode, verbose)
|   |-- model_context_protocol/
|   |   |-- __init__.py
|   |   |-- mcp.py                        <- main server + start_mcp_server(args)
|   |   +-- domains/
|   |       |-- __init__.py
|   |       +-- knowledge_graph/
|   |           |-- __init__.py
|   |           +-- mcp.py                <- @mcp.tool tools
|   +-- infrastructure/
|       |-- __init__.py
|       +-- neo4j/
|           |-- __init__.py
|           |-- client.py                 <- Neo4j async connection manager
|           +-- settings.py               <- NEO4J_URI, creds via .env
|
|-- mcp_client/                           <- NUEVO (se integra en Django)
|   |-- __init__.py
|   +-- neo4j_mcp_client.py               <- stdio MCP client wrapper
|
|-- scripts/
|   +-- init_neo4j_graph.py               <- Exploracion del esquema actual
|
|-- chatbot_project/
|   |-- .env                              <- MODIFICAR: anadir NEO4J_URI, NEO4J_USER, NEO4J_PASS
|   |-- requirements.txt                  <- MODIFICAR: anadir mcp, neo4j
|   +-- chatbot_app/
|       |-- views.py                      <- MODIFICAR: chat() anade consulta MCP
|       +-- services/
|           +-- langchain_service.py      <- MODIFICAR: get_response_with_graph_context()
|
|-- Dockerfile                            <- NUEVO (patron empresa: python:3.13-slim, no-root)
+-- docker-compose.yml                    <- MODIFICAR: anadir servicio mcp-server
```

---

## Plan de ejecucion (sesiones de 45-90 min)

### Fase 0: Puesta a punto y diagnostico (Sesion 1)

**Objetivo:** Verificar conectividad con Neo4j en la RPi y explorar el grafo existente.

**Tareas:**
- [ ] Conectar a RPi por SSH, verificar `neo4j status`
- [ ] Verificar que el puerto Bolt (7687) es accesible desde la maquina dev
- [ ] Crear `scripts/init_neo4j_graph.py` que:
  - Se conecte a Neo4j
  - Liste todos los labels de nodos (`CALL db.labels()`)
  - Liste todos los tipos de relaciones (`CALL db.relationshipTypes()`)
  - Muestre ejemplos de propiedades por label
  - Verifique si hay indices de texto creados
- [ ] Documentar credenciales en `.env`
- [ ] Anadir dependencias a `requirements.txt` (neo4j, mcp)

**Checklist de verificacion:**
- [ ] Conexion Bolt exitosa desde Python
- [ ] Documentado el esquema actual del grafo (labels, relaciones, indices)

### Fase 1: MCP Server generico para Neo4j (Sesiones 2-5)

**Objetivo:** Crear el MCP server siguiendo el patron de la empresa.

#### Sesion 2: Infraestructura Neo4j
- [ ] Crear `mcp_server/pyproject.toml` con:
  ```toml
  dependencies = ["fastmcp>=3.0.0", "neo4j>=5.0", "pydantic>=2.0", "pydantic-settings>=2.0"]
  ```
- [ ] Crear `mcp_server/infrastructure/neo4j/settings.py`:
  - `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` desde `.env`
- [ ] Crear `mcp_server/infrastructure/neo4j/client.py`:
  - `Neo4jClient` con `GraphDatabase.driver()`
  - Metodo `async run_query(cypher, params)` -> lista de dicts
  - Read-only transaction por defecto, write opcional con flag

**Primera prueba:** Conectar y hacer un `MATCH (n) RETURN labels(n), count(n)` desde Python

#### Sesion 3: Domain MCP tools genericas
- [ ] Crear `mcp_server/model_context_protocol/domains/knowledge_graph/mcp.py`
- [ ] Tools:
  - `query_graph(cypher: str, params: dict = {})` -> Read-only Cypher
  - `discover_schema()` -> Labels, relationship types, property keys con ejemplos
  - `search_nodes(label: str, properties: dict, limit: int = 10)` -> Busqueda por label + filtros
  - `get_node_neighbors(node_id: int, depth: int = 1)` -> Expandir desde un nodo
  - `full_text_search(query: str, limit: int = 10)` -> Busqueda textual
- [ ] Usar el patron exacto de la empresa: `@mcp.tool(name=..., description=..., tags=...)` + `Field(description=...)`

**Modelos Pydantic recomendados:**
```python
class QueryResult(BaseModel):
    columns: list[str]
    rows: list[dict]
    row_count: int

class SchemaInfo(BaseModel):
    node_labels: list[dict]
    relationship_types: list[dict]
    indexes: list[dict]

class SearchResult(BaseModel):
    nodes: list[dict]
    total: int
```

#### Sesion 4: CLI y entry point
- [ ] Crear `mcp_server/cli_tools/arguments.py` (mismo patron que la empresa):
  ```python
  class LaunchArguments(BaseModel):
      mode: Literal["http", "stdio", "sse"] = "stdio"
      verbose: bool = False
  ```
- [ ] Crear `mcp_server/cli.py`:
  ```python
  def main():
      parse_arguments(on_launch=start_mcp_server, ...)
  ```
- [ ] Crear `mcp_server/model_context_protocol/mcp.py`:
  ```python
  mcp = FastMCP(name="Neo4j Knowledge Graph MCP", ...)

  def start_mcp_server(args: LaunchArguments):
      mcp.mount(knowledge_graph_mcp)
      mcp.run(transport=args.mode)
  ```
- [ ] Entry point en pyproject.toml: `neo4j-mcp-server = "cli:main"`

**Prueba:** `uv run neo4j-mcp-server --mode stdio` -> conectar con MCP Inspector

#### Sesion 5: Tools RAG especificas
- [ ] Anadir al domain MCP existente tools especializadas en documentos:
  - `get_document_graph(document_name: str)` -> Todas las relaciones de un documento
  - `sync_document_to_graph(document_id: str)` -> Espejar Document+Chunks de pgvector a Neo4j
  - `get_related_documents(topic: str, limit: int = 5)` -> Documentos relacionados por conceptos
- [ ] Modelo de grafo para RAG:
  ```cypher
  (:Document {pg_id, file_name, embedding_model})
      -[:HAS_CHUNK]->(:Chunk {pg_id, chunk_index, text})
  ```

### Fase 2: MCP Client + Integracion Django (Sesiones 6-8)

#### Sesion 6: MCP Client
- [ ] Crear `mcp_client/neo4j_mcp_client.py`:
  - Usa `mcp.ClientSession` con stdio transport
  - Lanza el MCP server como subproceso
  - Metodos: `query_graph()`, `search_nodes()`, `get_document_graph()`, etc.
  - Singleton o context manager para reutilizar la conexion
- [ ] Prueba unitaria: llamar a `discover_schema()` y verificar respuesta

#### Sesion 7: Nuevo endpoint Django
- [ ] Anadir `POST /api/graph-search/` en `views.py` y `urls.py`
  - Endpoint opcional para probar consultas al grafo sin modificar el chat principal
  - `ChatbotGraphRequestSerializer`: `{message, label_filter, limit?}`
  - `ChatbotGraphResponseSerializer`: `{results, graph_context}`
- [ ] Test manual desde el frontend React

#### Sesion 8: Integracion en el chat principal
- [ ] Modificar `langchain_service.py` -- nuevo metodo:
  ```python
  def get_response_with_graph_context(
      self, user_input, context_chunks, graph_results, ...
  ) -> str:
      # Prompt incluye: {fragmentos RAG} + {resultados grafo} + {historial}
  ```
- [ ] Modificar `views.py:chat()`:
  ```python
  # Despues de la busqueda semantica en pgvector
  graph_context = neo4j_mcp_client.search_nodes(...)
  response = langchain_service.get_response_with_graph_context(
      message, context_chunks, graph_context, ...
  )
  ```
- [ ] Prompt template:
  ```
  Eres un asistente con acceso a dos fuentes de conocimiento:
  1. Documentos RAG (fragmentos de texto)
  2. Grafo de conocimiento (datos estructurados de proyectos, futbol, etc.)

  FRAGMENTOS RELEVANTES: {rag_context}
  DATOS DEL GRAFO: {graph_context}
  PREGUNTA: {user_input}
  RESPONDE combinando ambas fuentes cuando sea relevante.
  ```

### Fase 3: Poblacion del grafo y escritura (Sesiones 9-10)

#### Sesion 9: Sincronizacion pgvector -> Neo4j
- [ ] `scripts/sync_documents_to_neo4j.py`:
  - Lee Documents y DocumentChunks de PostgreSQL
  - Crea nodos `(:Document)` y `(:Chunk)` en Neo4j
  - Crea relaciones `[:HAS_CHUNK]`
  - Actualiza `neo4j_node_id` en PostgreSQL
  - Idempotente (no duplica si ya existe)
- [ ] Ejecutar contra datos existentes -> verificar en Neo4j Browser

#### Sesion 10: Escritura desde el chatbot
- [ ] Modificar `views.py:upload_text_file()`:
  - Despues de crear Document+Chunks en pgvector
  - Llamar a `sync_document_to_graph()` via MCP client
  - Rellenar `neo4j_node_id`
- [ ] Test: subir archivo -> verificar en Neo4j Browser
- [ ] Tool opcional: `create_knowledge_node()` para que el agente pueda persistir entidades

### Fase 4: Docker + extras (Sesiones 11-12)

#### Sesion 11: Dockerizar
- [ ] Dockerfile para MCP server (patron empresa):
  ```dockerfile
  FROM python:3.13-slim
  RUN useradd -m -u 1000 appuser
  WORKDIR /app
  COPY mcp_server/pyproject.toml .
  COPY mcp_server/src/ ./src/
  RUN pip install --no-cache-dir -e .
  USER appuser
  ENTRYPOINT ["neo4j-mcp-server"]
  CMD ["--mode", "stdio"]
  ```
- [ ] Anadir servicio `mcp-server` a `docker-compose.yml`
- [ ] Probar flujo completo con Docker Compose: Django + MCP server + DBs + Redis

#### Sesion 12: CI/CD y cierre
- [ ] GitHub Actions workflow (lint + test):
  - Ruff para mcp_server/
  - pytest para tests existentes + nuevos
- [ ] Documentar en README:
  - Arquitectura del flujo MCP
  - Como levantar el entorno completo
  - Herramientas disponibles del grafo
  - Ejemplos de preguntas que ahora puede responder
- [ ] Retrospectiva: que falta? proximos pasos?

---

## Herramientas del MCP Server (resumen)

### Tools genericas de grafo (Fase 1)

| Tool | Descripcion | Ejemplo de uso |
|---|---|---|
| `query_graph` | Ejecutar Cypher read-only | `MATCH (t:Team) WHERE t.name CONTAINS 'Bar' RETURN t` |
| `discover_schema` | Explorar labels, relaciones, indices | Que datos tengo en Neo4j? |
| `search_nodes` | Buscar nodos por label + filtros | `{label: "Player", properties: {team: "Barcelona"}}` |
| `get_node_neighbors` | Expandir desde un nodo (1-3 saltos) | Dado un Team, ver sus Players, Matches, etc. |
| `full_text_search` | Busqueda textual sobre indices | "goles Messi temporada 2024" |

### Tools especificas RAG (Fase 1, Sesion 5)

| Tool | Descripcion |
|---|---|
| `get_document_graph` | Subgrafo completo de un documento (chunks, relaciones) |
| `sync_document_to_graph` | Espejar Document+Chunks de pgvector a Neo4j |
| `get_related_documents` | Documentos relacionados por conceptos compartidos |

### Tool de escritura (Fase 3)

| Tool | Descripcion |
|---|---|
| `create_knowledge_node` | Persistir una entidad en el grafo (agente escribe) |

---

## Dependencias nuevas a instalar

### mcp_server/pyproject.toml
```
fastmcp >= 3.0.0, < 3.1
neo4j >= 5.0
pydantic >= 2.0
pydantic-settings >= 2.0
```

### chatbot_project/requirements.txt (anadir)
```
mcp >= 1.0
neo4j >= 5.0
```

### Dev tools (mcp_server)
```
ruff >= 0.8.0
pytest >= 7.0
pytest-asyncio >= 1.3.0
```

---

## Notas y referencias

- **FastMCP docs:** https://gofastmcp.com
- **MCP Specification:** https://spec.modelcontextprotocol.io
- **Neo4j Python Driver:** https://neo4j.com/docs/python-manual/current/
- **Proyecto empresa de referencia:** `/mnt/c/Users/jesus/VS/ods-cicd-python-quicksilver-mcp/`
  - `overview.md` -- arquitectura detallada
  - `CONTRIBUTING.md` -- guia para anadir dominios
  - `src/model_context_protocol/domains/environments/mcp.py` -- patron de tool MCP
  - `src/cli_tools/arguments.py` -- patron de CLI
  - `Dockerfile` -- patron de Docker
