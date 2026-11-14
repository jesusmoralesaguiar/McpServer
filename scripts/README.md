# Scripts de desarrollo

> Contexto del proyecto: [`docs/STRATEGY.md`](../docs/STRATEGY.md) y
> [`docs/ROADMAP.md`](../docs/ROADMAP.md).

## `context_pack.py`

Genera un **feature pack**: un Markdown con el contexto minimo necesario para
una tarea. Sirve para que el modelo local de 48k/64k no tenga que leer el repo
entero y para que tu mismo puedas revisar que informacion se le esta pasando.

Funciona en cualquier proyecto (Django, React, Python, JS, Go, etc.) y solo usa
la biblioteca estandar de Python. No necesita `rg`, `ctags` ni LSP.

### Uso rapido

```bash
python scripts/context_pack.py \
  --task "anadir la tool impact_of_change" \
  --budget 24000 \
  --out context/impact-tool.md
```

Luego abre `context/impact-tool.md` o pasaselo al modelo como contexto.

### Buscar por simbolo

```bash
python scripts/context_pack.py \
  --symbol build_feature_pack \
  --symbol find_symbol \
  --budget 20000
```

### Incluir archivos concretos

```bash
python scripts/context_pack.py \
  --file mcp_server/core/pack.py \
  --file tests/test_pack.py \
  --budget 12000
```

### Incluir el diff local

```bash
python scripts/context_pack.py \
  --task "revisar cambios del empaquetador de feature packs" \
  --diff \
  --budget 16000
```

### Anadir contexto web

```bash
context-pack \
  --task "implementar server FastMCP con transporte stdio" \
  --web-query "FastMCP stdio server documentation" \
  --web-fetch-results 1 \
  --budget 24000 \
  --out context/fastmcp-stdio.md
```

El pack incluye un brief web con snippets, extracto relevante, code blocks y URLs
para citar. No vuelca la pagina completa: recorta y prioriza parrafos. Para solo
snippets, usa `--no-web-fetch`.

### Opciones utiles

| Opcion | Efecto |
|---|---|
| `--root` | Raiz del proyecto (por defecto `.`) |
| `--budget` | Tokens estimados a incluir (por defecto 30000) |
| `--out` | Escribe el pack en un archivo; si no, lo imprime por stdout |
| `--diff` / `--staged` | Incluye cambios locales |
| `--web` | Busca en internet usando `--task` como consulta |
| `--web-query` | Consulta web explicita (mejor en ingles para docs) |
| `--web-url` | URL concreta a incluir (repetible) |
| `--web-fetch-results` | Paginas a descargar (por defecto 2) |
| `--no-web-fetch` | Solo snippets, sin descargar paginas |
| `--max-file-lines` | Limite de lineas por archivo (por defecto 220) |
| `--max-files` | Limite de archivos incluidos (por defecto 40) |
| `--max-tests` | Limite de tests relacionados (por defecto 8) |
| `--min-score` | Puntuacion minima para incluir un archivo (por defecto 8) |
| `--exclude` | Glob adicional a excluir, repetible |
| `--no-anchors` | No incluir AGENTS.md/README/docs/ARCHITECTURE.md/pyproject.toml |
| `--no-tests` | No incluir tests relacionados |
| `--no-tree` | No incluir el mapa del repo |
| `--quiet` | Silencia los diagnosticos de stderr |

### Presupuestos recomendados

| Tarea | Presupuesto |
|---|---|
| Un archivo o simbolo concreto | 8.000 - 12.000 |
| Feature fullstack (backend + frontend) | 24.000 - 32.000 |
| Refactor mediano o cambio transversal | 32.000 - 40.000 |

Deja siempre margen para que el modelo razone y escriba la respuesta.

### Usarlo en otros proyectos

El script es autocontenido. Puedes ejecutarlo desde cualquier repo indicando
`--root`:

```bash
python C:/Users/jesus/VS/McpServer/scripts/context_pack.py \
  --root /ruta/a/otro/proyecto \
  --task "anadir modulo de facturas" \
  --budget 24000 \
  --out /tmp/contexto-facturas.md
```

O copiarlo dentro del otro proyecto:

```bash
cp C:/Users/jesus/VS/McpServer/scripts/context_pack.py /ruta/a/otro/proyecto/scripts/
```

Si quieres un comando global (Linux/Pi):

```bash
ln -s ~/VS/McpServer/scripts/context_pack.py ~/.local/bin/context-pack
```

Despues puedes hacer `context-pack --task "..."` desde cualquier directorio.

### Que incluye el pack

1. Cabecera con tarea, rama, commit y presupuesto.
2. Instrucciones cortas para el modelo.
3. Mapa del repo (dos niveles).
4. Documentos base (`AGENTS.md`, `README.md`, `docs/ARCHITECTURE.md`, `pyproject.toml`).
5. Archivos relevantes con rutas y rangos de linea.
6. Tests relacionados.
7. Diff local, si se pide.
8. Nota con la estimacion de tokens.

### Como elige los archivos

- Puntua coincidencias en la ruta, en el contenido y en definiciones de simbolos.
- Da mas peso a clases/funciones/componentes que a menciones sueltas.
- Incluye la cabecera del archivo (imports) y ventanas alrededor de las coincidencias.
- Penaliza archivos enormes, minificados y migraciones.
- Nunca incluye `.env`, claves, lockfiles, binarios ni `node_modules`.
- Si no hay coincidencias, incluye el mapa y los documentos base.

### Limites actuales

- La seleccion es lexica, no semantica. Para busqueda por significado hace falta
  la fase de embeddings/grafo.
- No conoce el grafo de imports ni el impacto de cambios; eso llega con Neo4j.
- La estimacion de tokens es aproximada (`caracteres / 4`).
- No usa `rg`, `ctags` ni LSP para mantenerlo sin dependencias. Cuando el repo
  crezca, `rg` acelera la busqueda, `ctags` indexa definiciones y un LSP da
  referencias y tipos exactos. El grafo en Neo4j sera el siguiente salto.

### Siguiente evolucion

1. Instalar `ripgrep` y `ctags` para acelerar y precisar la busqueda.
2. Indexar el codigo en Neo4j con nodos y relaciones.
3. Anadir `impact_of_change` al servidor MCP (`search_code`, `get_symbol` y
   `get_feature_pack` ya estan expuestos en `mcp_server/`).
4. Usar el grafo para construir el pack automaticamente.

## `web_context.py`

Busca en internet y genera un Markdown citable con snippets, extracto relevante
y bloques de codigo. Es el motor que usa `context-pack --web`.

```bash
python scripts/web_context.py \
  --query "FastMCP stdio server documentation" \
  --max-results 3 \
  --fetch-results 1 \
  --max-chars-per-page 5000 \
  --out context/web-fastmcp.md
```

O directamente sobre una URL:

```bash
python scripts/web_context.py \
  --url https://gofastmcp.com/getting-started/quickstart \
  --fetch-results 1
```

Caracteristicas:

- Busca con DDGS y prueba varios backends si uno falla.
- Descarga con `requests` o `urllib` (sin dependencias obligatorias).
- Extrae texto legible con la biblioteca estandar y prioriza parrafos relevantes.
- Conserva bloques `<pre>` como codigo.
- Bloquea localhost, IPs privadas y metadatos cloud (SSRF).
- Limita tamano, tiempo y caracteres por pagina.
- No ejecuta JavaScript.

Si quieres usarlo como comando global:

```bash
ln -s ~/VS/McpServer/scripts/web_context.py ~/.local/bin/web-context
```

`web-context --query "..."` funciona desde cualquier proyecto. Para la busqueda
necesita `ddgs` en el Python activo; si no esta, usa `--url` o instala
`pip install ddgs`.

## `web_search_agent.py` — eliminado

Era un agente CLI de busqueda web sobre `llama-server` con tool-calling. Nacio
en el enfoque anterior (el chatbot hablando con llama.cpp por su API
OpenAI-compatible) y hoy sobra: la busqueda web con citas ya la dan
`duckduckgo-mcp-server` y `web_context.py`, y el agente que orquesta el flujo es
el cliente MCP. El fichero esta borrado del arbol y sigue recuperable en el
historial de git.

## Lanzadores del motor local

`start_llama.ps1`, `start_llama.bat` y `check_tools.ps1` no son parte del
paquete ni entran en los tests. Son conveniencia del entorno para tener un
`llama-server` de prueba con servidores MCP montados:

| Script | Que hace |
|---|---|
| `start_llama.ps1` / `start_llama.bat` | Arranca un `llama-server` crudo en WSL con contexto 48k o 64k. Solo envuelven el alias `llama-server-qwen38-<ctx>` definido en WSL. |
| `check_tools.ps1` | Consulta `GET http://127.0.0.1:8080/tools` para comprobar que ese `llama-server` levanto sus servidores MCP (`--mcp-servers-config`). |

Ojo con no mezclar los dos caminos al motor local:

- **Strata** (la app instalada) es quien sirve el modelo de trabajo en
  `http://127.0.0.1:18500` — `qwen3.8-flash-next-iq3_s`, contexto 131072. No es
  codigo de este repo ni arranca desde estos scripts.
- Los **launchers de WSL** suben un `llama-server` aparte en el puerto `8080`
  con el GGUF `Qwen3.8-27B-UD-Q3_K_XL` y `--spec-type draft-mtp`, y sirven para
  probar que los servidores MCP se montan dentro de `llama-server`.

Dependencias reales: los alias y el `mcp.json` de WSL. Si cambian alli, estos
scripts quedan obsoletos; no hay config que mantener aqui.
