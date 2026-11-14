# McpServer

**El servidor MCP de nuestro ecosistema de trabajo.** Cada capacidad que usan
los modelos se da de alta como un **registro MCP** (módulo enchufable) y un
**perfil** decide qué registros se montan en cada arranque.

Consumido por **Strata Local** (llama.cpp), **modelos de suscripción** y
cualquier cliente MCP estándar: **Antigravity**, **Cursor**, **Claude Desktop** o CLI.

---

## Características

* **Registros enchufables:** `code` (activo) y `memory` en Neo4j (Fase 1), cada uno con su módulo `register_<registro>_tools(mcp)`.
* **Perfiles por subcomando** (Fase 1): `mcpserver code`, `mcpserver memory`, `mcpserver all --exclude web`. Cada perfil paga solo el coste de esquema que aporta a la tarea.
* **Agnóstico y desacoplado:** No depende de un modelo ni de un cliente concreto.
* **Contexto quirúrgico:** `repo_map`, `search_code`, `get_symbol` y `get_feature_pack` seleccionan solo los fragmentos y líneas estrictamente necesarios.
* **Seguridad de serie:** Filtra automáticamente secretos (`.env*`, claves privadas, certificados) y carpetas pesadas (`node_modules`, `.venv`, cachés).
* **Cero servicios externos requeridos:** El registro `code` analiza el repositorio directamente, sin bases de datos ni Docker.
* **Memoria con criterio:** Neo4j (Raspberry Pi) guarda entidades destiladas `:Memory`; el Cypher crudo read-only sigue en `mcp-neo4j-cypher`, sin duplicar tools.

---

## Arranque Rápido

### 1. Instalar el paquete

```bash
pip install -e .
```

### 2. Ejecutar el servidor MCP en modo stdio

```bash
python -m mcp_server --transport stdio
```

o si está instalado como paquete:

```bash
mcpserver --transport stdio
```

### 3. Configuración en Clientes MCP

Añade el servidor a tu `mcp_config.json` (en Cursor, Claude Desktop, Antigravity, etc.):

```json
{
  "mcpServers": {
    "mcpserver": {
      "command": "python",
      "args": ["-m", "mcp_server", "--transport", "stdio"],
      "cwd": "C:/Users/jesus/VS/McpServer"
    }
  }
}
```

### 4. Tests

```bash
python -m unittest discover -s tests
```

---

## Documentación

* [Visión del proyecto](docs/STRATEGY.md)
* [Arquitectura del Sistema](docs/ARCHITECTURE.md)
* [Roadmap de Desarrollo](docs/ROADMAP.md)
* [ADR 0001: Perfiles de servidor, registros MCP y memoria en Neo4j](docs/adr/0001-perfiles-de-servidor-registros-mcp-y-memoria-neo4j.md)

---

## Repositorio remoto

El repo en GitHub se llama **McpServer** (renombrado desde `chatbot`):

```bash
git remote -v
# origin  https://github.com/jesusmoralesaguiar/McpServer.git
```

`main` ya está trackeando contra `origin`, así que basta con:

```bash
git push
```

GitHub mantiene redirecciones desde `jesusmoralesaguiar/chatbot`, pero los
clones nuevos deben usar la URL actual.
