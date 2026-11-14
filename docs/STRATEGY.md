# Estrategia: McpServer, el MCP del ecosistema de trabajo

## Objetivo

**McpServer es el servidor MCP de nuestro ecosistema de trabajo.** Cada
capacidad que queremos que usen los modelos se da de alta aqui como un
**registro MCP**: un modulo que registra sus tools y puede activarse o
apagarse por perfil.

Los consumidores son nuestros modelos, locales o de suscripcion:

- **Strata Local** (`Qwen3.8-Flash-Next IQ3_S` en la RTX 5070 Ti) y los
  `llama-server` de trabajo;
- **modelos de suscripcion** y clientes MCP estandar (Antigravity, Cursor,
  Claude Desktop).

Lo que se persigue sigue siendo lo mismo: que un modelo sea util en tareas
reales (buscar, resumir, aprender, resolver issues en proyectos personales)
sin perder privacidad ni control.

La pregunta no es "que interfaz construimos", sino **que registros y contexto
necesita el modelo para ser util**.

## Que ha cambiado

Cuando empezo el proyecto, construir un chatbot fullstack con Django/React era
una forma razonable de aprender RAG, pgvector, Redis y APIs. Hoy:

- llama.cpp y los clientes MCP ya dan una interfaz de chat solida;
- el valor diferencial esta en las **tools** (MCP), la **calidad del contexto**
  y la **capacidad de resolver tareas reales**;
- el laboratorio Django/React se elimino del repositorio: ya no hay frontends
  que mantener;
- los modelos locales han mejorado lo suficiente para usarlos a diario.

Por eso el centro de gravedad vuelve a moverse: de "servidor MCP de dominio" a
**"servidor MCP del ecosistema"**, donde las capacidades se dan de alta como
registros y los modelos (locales o de suscripcion) eligen que perfil encender.

## Registros MCP del ecosistema

| Registro | Que aporta | Estado |
|---|---|---|
| `code` | Nivel 0 sobre el repo: `repo_map`, `search_code`, `get_symbol`, `get_feature_pack` | **Activo** |
| `memory` | Neo4j (Pi): decisiones, aprendizajes y entidades destiladas `:Memory` | **Siguiente** (Fase 1) |
| `graph` | Grafo de codigo e impacto de cambios | Reservado (Fase 3) |
| `web` | Brief web citable (hoy vive en `scripts/`) | Soporte |

Servidores MCP **externos** que no duplicamos: `mcp-neo4j-cypher` (Cypher
crudo, read-only) y `duckduckgo-mcp-server` (web search/fetch). Nuestro
registro `memory` es **complementario**: escribe con criterio y devuelve
lecturas tipadas; el Cypher libre sigue en el MCP generico. Ver
[ADR 0001](adr/0001-perfiles-de-servidor-registros-mcp-y-memoria-neo4j.md).

## Donde invertir

| Componente | Papel |
|---|---|
| `mcp_server/` | Servidor MCP stdio-first y alta de registros por perfil |
| Modelo local (Strata / llama.cpp) | Motor de razonamiento e inferencia |
| Modelos de suscripcion | Consumidores de los mismos registros |
| Neo4j (Pi) | Memoria de proyectos, decisiones y relaciones |
| `context-pack` | Contexto minimo de repo por tarea |
| `web-context` | Brief web citable y acotado |
| Docs/ADRs | Memoria del proyecto y decisiones |

## Principios

1. **Local-first**: modelo, datos y herramientas en la maquina o en la red local.
2. **Contexto justo, no maximo**: recuperar y comprimir; 48k/64k bien usados.
3. **Tools sobre prompts**: si una tarea requiere datos externos o acciones,
   exponer una tool MCP en lugar de meter todo en el prompt.
4. **Citas y verificacion**: web, documentos y grafo deben poder rastrearse.
5. **Un cliente por interfaz**: el servidor MCP stdio es la interfaz principal;
   no se anaden frontends ni APIs HTTP salvo que aporten algo que stdio no dé.
6. **Medir el contexto**: tokens de esquema, tamano del feature pack y tools
   usadas por tarea. El exito del modelo se mide en el entorno de trabajo.

## Que construir a continuacion

1. **Registros MCP por perfil** en `mcp_server/`: `code` (Nivel 0, ya activo) y
   `memory` (Neo4j) como siguiente alta.
2. **Memoria de proyecto** en Neo4j: decisiones, aprendizajes y relaciones
   destiladas, con degradacion limpia si la Pi no responde.
3. **Workflow de issue**: dado un issue de un proyecto, generar feature pack,
   plan, cambios, tests y resumen.
4. **Grafo de codigo** para impacto de cambios y contexto quirurgico.
5. **RAG opcional** solo si aparece una necesidad real de documentos.
6. **Evaluacion** con 10-20 tareas reales de proyectos personales. Se hace en el
   entorno de trabajo, no como entregable de `McpServer`: aqui solo se
   garantiza que el contexto medido sea el correcto.

## Que dejar de hacer

- Volver a construir interfaces de chat fullstack como producto principal.
- Duplicar tools que ya existen (schema/Cypher/web).
- Encender todos los registros en un modelo pequeno sin medir el coste en el
  prompt: cada tool registrada consume tokens de esquema.
- Subir contexto a 100k sin medir el coste en VRAM y velocidad.
- Meter paginas web completas o repos enteros en el prompt.
- Mantener dos interfaces de chat como si ambas fueran prioritarias.
- Indexar el codigo en el grafo sin tener un mecanismo de refresco fiable.

## Criterios de exito

- Resolver un issue real de un proyecto personal con el modelo local, sin
  volcar el repo entero y con tests pasando.
- Mantener el contexto de trabajo en 20-35k tokens en el 80% de las tareas.
- Citar fuentes web cuando la respuesta dependa de informacion externa.
- Reutilizar decisiones y contexto entre sesiones sin repetir explicaciones.

## No objetivos

- Competir con un IDE o un agente cloud.
- Tener la interfaz mas bonita.
- Soportar multiusuario o produccion.
- Indexar todos los proyectos del mundo: solo los que se usan.
