# AGENTS.md — Chatbot Fullstack con RAG + MCP + Neo4j

## Resumen del proyecto

Chatbot inteligente con arquitectura Django + React que combina:
- **RAG** (Retrieval-Augmented Generation): pgvector + Ollama
- **MCP** (Model Context Protocol): integracion con Neo4j via servidor MCP
- **Grafo de conocimiento**: Neo4j en Raspberry Pi como memoria multi-dominio

El roadmap completo esta en `planing-estudio.md`. **Leelo siempre al iniciar una sesion nueva.**

---

## Stack tecnologico

| Capa | Tecnologia | Version |
|------|-----------|---------|
| Backend framework | Django + DRF | 4.2 |
| Frontend framework | React + Vite | 19 + 8 |
| CSS | Tailwind CSS | 4 |
| Estado frontend | TanStack Query | 5 |
| Base de datos | PostgreSQL + pgvector | pgvector/pgvector:0.8.2 |
| Cache/memoria | Redis | 7-alpine |
| LLM local | Ollama | minimax-m2.1:cloud |
| Embeddings | nomic-embed-text (Ollama) | 768 dimensiones |
| Grafo conocimiento | Neo4j | En Raspberry Pi (red local) |
| MCP framework | FastMCP | 3.0 |
| Python | Python | 3.9+ (backend), 3.13 (MCP server) |
| Gestor paquetes Python | pip (backend), uv (MCP server) | - |
| Gestor paquetes JS | npm | - |
| Infraestructura | Docker Compose | PostgreSQL + Redis |
| Templates referencia | ods-cicd-python-quicksilver-mcp | MCP server patron empresa |

---

## Estructura del proyecto

```
Chatbot/
|
|-- AGENTS.md                            <- Este archivo. Leer siempre al empezar.
|-- planing-estudio.md                   <- ROADMAP: plan de integracion MCP + Neo4j.
|-- README.md                            <- Documentacion general del proyecto.
|-- .clinerules                          <- Convenciones de codigo (Django + React).
|-- docker-compose.yml                   <- PostgreSQL + Redis.
|-- requirements.txt                     <- Dependencias Python del backend.
|-- init_project.sh                      <- Script de inicializacion.
|
|-- chatbot_project/                     <- BACKEND Django
|   |-- manage.py
|   |-- .env                             <- Variables de entorno (gitignored)
|   |-- pytest.ini
|   |-- chatbot_project/                  <- Configuracion Django
|   |   |-- settings.py
|   |   |-- urls.py                       <- Rutas raiz (/admin/, /api/)
|   |   |-- wsgi.py, asgi.py
|   +-- chatbot_app/                     <- App principal
|       |-- models.py                     <- 6 modelos: Conversation, ChatMessage,
|       |                                     UserPreference, BotConfiguration,
|       |                                     Document, DocumentChunk (pgvector)
|       |-- views.py                      <- 10 endpoints REST
|       |-- serializers.py
|       |-- urls.py
|       |-- admin.py
|       +-- services/
|           +-- langchain_service.py      <- Core LLM + RAG + Redis memory
|
|-- frontend/                            <- FRONTEND React
|   |-- package.json
|   |-- vite.config.js
|   +-- src/
|       |-- main.jsx                      <- Entry point (QueryClientProvider)
|       |-- App.jsx                       <- Chat UI principal
|       |-- hooks/useChat.js              <- Mutaciones API (sendMessage, uploadFile)
|       |-- components/Spinner.jsx
|       +-- queryClient.js
|
|-- mcp_server/                          <- [PENDIENTE] MCP Server para Neo4j
|-- mcp_client/                          <- [PENDIENTE] MCP Client para Django
+-- scripts/                             <- [PENDIENTE] Scripts de utilidad
```

---

## Como arrancar el proyecto

### 1. Infraestructura (Docker)
```bash
docker-compose up -d   # PostgreSQL:5432 + Redis:6379
```

### 2. Backend Django
```bash
cd chatbot_project
source ../.venv/bin/activate
python manage.py runserver   # http://localhost:8000
```

### 3. Frontend React
```bash
cd frontend
npm run dev   # http://localhost:5173
```

### 4. Ollama
```bash
ollama serve
ollama pull minimax-m2.1:cloud
ollama pull nomic-embed-text
```

### 5. Tests
```bash
cd chatbot_project && pytest
```

---

## Modelos de datos (backend)

| Modelo | Campos clave | Proposito |
|--------|-------------|-----------|
| `Conversation` | id (UUID), title, is_active | Hilo de conversacion |
| `ChatMessage` | sender (user/bot), message, conversation FK | Mensaje individual |
| `UserPreference` | user_identifier, language, tone | Preferencias de usuario |
| `BotConfiguration` | temperature, max_response_length | Configuracion del bot |
| `Document` | file_name, content_hash (SHA-256), **neo4j_node_id** | Documento subido (RAG) |
| `DocumentChunk` | chunk_index, text, embedding (VectorField 768), **neo4j_node_id** | Fragmento con embedding |

**Nota:** `neo4j_node_id` en Document y DocumentChunk son campos puente para la futura integracion con Neo4j.

---

## API endpoints

| Metodo | Ruta | Descripcion |
|--------|------|-------------|
| `POST` | `/api/chat/` | Enviar mensaje (con RAG opcional) |
| `GET` | `/api/history/` | Historial de conversaciones |
| `DELETE` | `/api/history/clear/` | Borrar historial |
| `POST` | `/api/conversations/` | Crear conversacion |
| `GET` | `/api/conversations/<uuid>/` | Detalle de conversacion |
| `PUT` | `/api/conversations/<uuid>/update/` | Actualizar titulo |
| `GET` | `/api/preferences/<user_id>/` | Preferencias de usuario |
| `PUT` | `/api/preferences/<user_id>/update/` | Actualizar preferencias |
| `GET` | `/api/config/` | Configuracion del bot |
| `PUT` | `/api/config/update/` | Actualizar config del bot |
| `POST` | `/api/upload-text-file/` | Subir archivo texto (RAG) |

---

## Convenciones de codigo

### Backend (Django)
- Las vistas usan `@api_view` decorators (function-based views), NO class-based views
- Serializadores: `ModelSerializer` de DRF
- Type hints en metodos de servicio
- Logica de negocio en `services/`, no en views
- Ollama se llama directamente via `requests` (no usa langchain-ollama)
- Memoria conversacional: Redis con fallback a PostgreSQL

### Frontend (React)
- Functional components + hooks
- Tailwind CSS para estilos (NO CSS modules)
- TanStack Query para estado del servidor (staleTime: 5 min)
- Mutaciones en `hooks/useChat.js`, no inline en componentes

### MCP Server (patron empresa)
- Arquitectura hexagonal: CLI -> MCP -> Domain -> Infrastructure
- `@mcp.tool` decorator con name, description, tags
- Parametros tipados con `pydantic.Field(description=...)`
- Modelos Pydantic para input/output
- Async functions (async/await)
- Un sub-MCP por dominio, montado en servidor principal via `mcp.mount()`
- Entry point: `cli.py` -> `parse_arguments(on_launch=start_mcp_server)`
- Transporte configurable: stdio (local) / http / sse

---

## Plan MCP + Neo4j (Fase actual: 0)

El plan completo esta en `planing-estudio.md`. Resumen:

| Fase | Estado | Descripcion |
|------|--------|-------------|
| 0 | **EN CURSO** | Diagnostico de Neo4j en RPi, verificacion de conectividad |
| 1 | Pendiente | MCP Server generico (5 tools grafo + 3 tools RAG) |
| 2 | Pendiente | MCP Client en Django + integracion en chat |
| 3 | Pendiente | Sincronizacion pgvector <-> Neo4j, escritura |
| 4 | Pendiente | Docker, CI/CD, documentacion |

### Decisiones de diseno (NO cambiar sin discutir)
- MCP Server en maquina de desarrollo (no en RPi)
- Transporte: stdio (local), luego SSE/HTTP
- Herramientas genericas primero, RAG especifico despues
- Solo lectura en Fase 1, escritura en Fase 3
- FastMCP publico (no el wrapper privado ods_mcp_core)

### Neo4j en Raspberry Pi
- Datos existentes: proyectos de desarrollo + estadisticas La Liga + memoria IA
- Conexion via Bolt (puerto 7687)
- Credenciales en `chatbot_project/.env`

### Proyecto de referencia
- `/mnt/c/Users/jesus/VS/ods-cicd-python-quicksilver-mcp/` — MCP server produccion Santander
- Patron a seguir: `src/model_context_protocol/domains/environments/mcp.py`
- Documentacion: `overview.md`, `CONTRIBUTING.md`

---

## Archivos que NO debes leer a menos que se pida

- `node_modules/`, `dist/`, `build/`
- `__pycache__/`, `.venv/`, `env/`
- `static/`, `media/`
- `*.egg-info/`
- `.git/`, `.DS_Store`
- `uv.lock`

---

## Para futuras sesiones de opencode

Al iniciar una sesion nueva, di siempre:

> "Lee AGENTS.md y planing-estudio.md. Estamos en la Fase 0 del plan MCP+Neo4j. [Describe que quieres hacer hoy]"

Esto garantiza que opencode tenga todo el contexto desde el primer mensaje.
