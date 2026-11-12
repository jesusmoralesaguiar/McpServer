# Documentacion

Indice de la documentacion del proyecto. **McpServer** es el servidor MCP del
ecosistema de trabajo: cada capacidad se da de alta como un **registro MCP**
(modulo enchufable) y un **perfil** decide que registros se montan en cada
arranque. Lo consumen Strata Local, los LLMs de suscripcion y cualquier cliente
MCP estandar.

## Empieza aqui

| Documento | Para que |
|---|---|
| [`STRATEGY.md`](STRATEGY.md) | Vision, alcance y principios de contexto |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | Componentes, flujos y modos de uso |
| [`ROADMAP.md`](ROADMAP.md) | Fases actuales y prioridades |
| [`adr/`](adr/README.md) | Decisiones de arquitectura |

## Regla de lectura

- Para decidir **que construir**: `STRATEGY.md` + `ROADMAP.md`.
- Para entender **como encaja todo**: `ARCHITECTURE.md`.
- Para el **por que** de las decisiones: `adr/`.
