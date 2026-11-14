# ADR 0001: Perfiles de servidor, registros MCP y memoria en Neo4j

- **Estado:** Aceptado
- **Fecha:** 2026-11-12
- **Decisores:** Jesús Morales Aguiar, Asistente Copilot, Strata Local

---

## Contexto

El repositorio deja de ser "un servidor MCP de dominio para un repo" y pasa a
ser **el servidor MCP del ecosistema de trabajo**. Las capacidades que usan los
modelos (Strata local y LLMs de suscripción) se dan de alta como **registros
MCP**: módulos con sus propias tools, su propio ciclo de vida y sus propios
requisitos. El primer registro tras `code` es la **persistencia/memoria en
Neo4j** (Raspberry Pi).

Restricciones que condicionan la decisión:

1. **Contexto limitado.** Cada tool registrada añade su esquema al prompt. En
   un modelo local con ventana de atención cara, pagar por tools que la tarea
   no usa es un coste real. El orden de magnitud es de centenas de tokens por
   tool, pero es una estimación sin medir en Strata.
2. **Un solo lenguaje y un solo paquete** ya resuelven el registro de código;
   partir el proyecto en varios paquetes multiplica empaquetado, tests y
   configuración de clientes MCP.
3. **Migración futura:** algún registro podrá correr en otra máquina (la Pi).
   La arquitectura no debe impedir mover un registro sin reescribirlo.
4. **No duplicar** lo que ya aportan `mcp-neo4j-cypher` (Cypher crudo
   read-only) y `duckduckgo-mcp-server` (web).

## Decisión

### 1. Arquitectura: un paquete, N registros, perfiles por subcomando (opción C)

- Cada registro es un módulo en `mcp_server/tools/` que expone
  `register_<registro>_tools(mcp)`.
- `create_server(profile)` construye un `FastMCP` distinto por perfil, con sus
  propias `instructions` y solo las tools del perfil.
- Los perfiles se eligen por subcomando en `mcp_server/__main__.py`:

  ```bash
  mcpserver                    # all: todos los registros
  mcpserver code               # solo contexto de código
  mcpserver memory             # solo memoria Neo4j
  mcpserver all --exclude web  # recorte fino
  ```

- Se prevé un `mount(server, mcp)` para que un perfil pueda montarse en un
  servidor agregador sin copiar código.
- Un registro puede fallar al cargar (sin Neo4j, sin red) y el perfil degrada
  con un mensaje claro en las `instructions`, no con un crash.

### 2. Alcance del registro `memory`: lecturas tipadas + escrituras destiladas

- **Ahora:** Neo4j como memoria de proyecto.
  - Lecturas de alto nivel: `get_project_context(project_name)`,
    `search_knowledge(query)`.
  - Escrituras validadas: `log_decision(title, rationale, alternatives)` sobre
    nodos `:Memory` (criterio de destilación del config global).
- **Reservado, sin indexador:** el grafo de código
  (`File-[:IMPORTS]->Module-[:CALLS]->Symbol`) queda documentado como esquema
  objetivo y se implementa en la Fase 4.
- **Complementario, no duplicado:** el Cypher crudo y libre sigue en
  `mcp-neo4j-cypher` (read-only). Aquí van las escrituras y las lecturas
  tipadas con formato compacto y citas.

## Alternativas consideradas

### A. Monolito modular (un único `FastMCP` con todas las tools)

| Pros | Contras |
|---|---|
| Un solo punto de entrada y una sola config de cliente | Esquema completo siempre en el prompt |
| Cero fricción para añadir un registro | Un registro roto puede tumbar el servidor |
| Tests simples | Sin control del radio de acción por modelo |

### B. Un servidor MCP por registro (`mcpserver-code`, `mcpserver-memory`)

| Pros | Contras |
|---|---|
| Aislamiento total: un registro caído no afecta a los demás | N empaquetados, N configs, N ciclos de release |
| Coste de esquema mínimo por cliente | El cliente debe saber cuántos servidores existen |
| Despliegue natural en otra máquina | Duplica infraestructura compartida (scanner, config, tests) |

### C. Híbrida: módulos + perfiles por subcomando — **elegida**

| Pros | Contras |
|---|---|
| Ergonomía de A (un paquete, una install) | Un `main()` con argparse que mantener |
| Control de contexto y radio de acción de B | Un registro roto sigue dentro del mismo proceso |
| Migrar un registro a la Pi = cambiar el perfil, no el código | |
| Permite probar B más tarde sin reescribir registros | |

### Neo4j: opción 2 (memoria destilada) vs. opción 3 (memoria + grafo de código)

Se eligió **2 ahora con el esquema de 3 reservado**. El argumento decisivo es
el **riesgo de índice obsoleto**: un grafo de código sin invalidación
automática en cada edición responde con seguridad respuestas equivocadas, lo
que es peor que no tener grafo. Primero se demuestra el valor con memoria
destilada; el indexador llega cuando exista un mecanismo de refresco fiable.

## Consecuencias

### Positivas
- Cada modelo consume solo el registro que necesita (`mcpserver code` para
  tareas de repo, `mcpserver memory` para consultas de proyecto).
- Añadir un registro es añadir un módulo y nombrarlo en un perfil.
- El paso de un registro a la Pi no cambia el código, solo el perfil desplegado.
- La memoria queda gobernada por un criterio explícito de destilación.

### Negativas / Mitigaciones
- Más superficie de CLI y más combinaciones que testear. *Mitigación:* tests
  por perfil que asserten el conjunto exacto de tools (`list_tools()`).
- Riesgo de que el perfil `all` se convierta en el default perezoso y
  contamine el contexto. *Mitigación:* documentar el perfil recomendado por
  tarea y medir el coste real de esquema en Strata.
- Escrituras contra Neo4j implican credenciales y red. *Mitigación:* variables
  de entorno, nunca `.env` en el repo, y degradación limpia si la Pi no
  responde.
