# Architecture Decision Records (ADR)

Un ADR documenta una decision tecnica importante, el contexto en el que se tomo
y sus consecuencias. Sirve para que un agente o una persona no tenga que
reconstruir la decision leyendo todo el historial de chat.

## Cuando escribir uno

- Cambios de arquitectura o de stack.
- Decisiones que afectan a varios modulos.
- Trade-offs relevantes (rendimiento, memoria, seguridad, mantenibilidad).
- Cualquier cosa que alguien preguntaria "por que se hizo asi".

No hace falta un ADR para cada bugfix o cambio de estilo.

## Formato

1. Crea `NNNN-titulo-corto.md` (numeracion consecutiva a partir del 0002; el 0001 ya esta ocupado).
2. Rellena contexto, decision, alternativas y consecuencias.
3. Anade una linea al indice de abajo.

## Indice

| ADR | Decision | Estado |
|---|---|---|
| 0001 | Perfiles de servidor, registros MCP y memoria en Neo4j | Aceptada |

> El ADR del pivot desde el laboratorio Django/React se retiro: el pivot esta
> ejecutado y el repositorio ya solo es servidor MCP, asi que su documentacion
> historica dejo de aportar. Tampoco existen los ADR 0002-0006 del plan de
> estudio anterior, descartados junto con `docs/archive/`.
