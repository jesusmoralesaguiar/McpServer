# McpServer

**El servidor MCP de nuestro ecosistema de trabajo.** Cada capacidad que usan
los modelos se da de alta como un **registro MCP** (módulo enchufable) y un
**perfil** decide qué registros se montan en cada arranque.

Consumido por **Strata Local** (llama.cpp), **modelos de suscripción** y
cualquier cliente MCP estándar: **Antigravity**, **Cursor**, **Claude Desktop** o CLI.

---

## Características

* **Registros enchufables:** `code` (activo) y `memory` en Neo4j (Fase 2), cada uno con su módulo `register_<registro>_tools(mcp)`.
* **Perfiles por subcomando** (Fase 2): `mcpserver code`, `mcpserver memory`, `mcpserver all --exclude web`. Cada perfil paga solo el coste de esquema que aporta a la tarea.
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

## Nota sobre el repositorio remoto

El remoto local ya apunta a `jesusmoralesaguiar/mcpserver`:

```bash
git remote -v
# origin  https://github.com/jesusmoralesaguiar/mcpserver.git
```

**Pendiente:** renombrar el repositorio en GitHub de `chatbot` a `mcpserver`.
Mientras no se haga, `git push` a `origin` falla con "Repository not found"; los
commits se suben al nombre antiguo:

```bash
git push https://github.com/jesusmoralesaguiar/chatbot.git main
```

Para renombrar, desde la web de GitHub (Settings → General → Repository name) o
con la CLI:

```bash
gh repo rename mcpserver --repo jesusmoralesaguiar/chatbot
```

Hecho el renombrado, `origin` ya funciona tal cual y basta con
`git push -u origin main`.
