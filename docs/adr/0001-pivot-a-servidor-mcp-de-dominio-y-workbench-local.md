# ADR 0001: Pivot de Chatbot a Servidor MCP de Dominio y Workbench Local

- **Estado:** Aceptado
- **Fecha:** 2026-11-12
- **Decisores:** Jesús Morales Aguiar, Asistente Antigravity, Strata Local

---

## Contexto

El repositorio nació originalmente como un experimento fullstack ("Chatbot") con Django, Django REST Framework, React, PostgreSQL (pgvector) y Redis. Con la evolución de los modelos locales y los protocolos de integración para agentes (MCP - Model Context Protocol), mantener una interfaz gráfica de chat y un backend monolítico dejó de aportar valor:

1. Los modelos locales (especialmente Strata en la RTX 5070 Ti) ya disponen de interfaces de inferencia de alto rendimiento y APIs estándar.
2. El cuello de botella real de los agentes locales no es la interfaz visual, sino el **acceso quirúrgico al contexto del código** sin desbordar los presupuestos de tokens ni contaminar la ventana de atención con ficheros irrelevantes.
3. El laboratorio Django/React requería arrancar contenedores Docker pesados, bases de datos relacionales y servicios en segundo plano para tareas que deben resolverse de forma instantánea.

## Decisión

1. **Deprecar el laboratorio Django/React:** Las carpetas `chatbot_project/` y `frontend/` se congelan como artefactos históricos y bancos de pruebas aislados, dejando de ser el foco del desarrollo.
2. **Convertir el repositorio en un Servidor MCP de Dominio:** Implementar el paquete `mcp_server/` con FastMCP, configurado en `pyproject.toml` con transporte `stdio-first`.
3. **Herramientas quirúrgicas de Nivel 0:** Exponer herramientas directas sobre el sistema de archivos local (`repo_map`, `search_code`, `get_symbol`, `get_feature_pack`) con filtrado estricto de secretos y dependencias, sin requerir servicios externos.
4. **Tríada de arquitectura local:**
   * **Inferencia Local:** Strata (`Qwen3.8-Flash-Next` en NVIDIA RTX 5070 Ti) como motor primario para razonamiento, refactorización y resolución de issues.
   * **Herramientas de Código:** Servidor MCP stdio-first consumible por Strata, Antigravity, Cursor o Claude Desktop.
   * **Memoria Persistente:** Grafo en Neo4j alojado en la Raspberry Pi (`bolt://192.168.1.128:7687`), rigiéndose por los criterios de destilación conceptual (nodos `:Memory`).

## Consecuencias

### Positivas
- Arranque inmediato (< 1 segundo) sin dependencias de Docker, PostgreSQL o Redis.
- Interoperabilidad total: cualquier cliente MCP estándar puede consumir las herramientas de contexto del repositorio.
- Batería de pruebas unitarias pura en Python (`tests/`) que garantiza que no se fugan secretos ni se satura el contexto.

### Negativas / Mitigaciones
- El repositorio mantenía los directorios antiguos de Django/React, lo que podía generar confusión. *Mitigación:* Se excluyen del empaquetado principal, se documenta su estatus de deprecación y se rebautiza el proyecto para reflejar su nueva identidad.

## Enmienda (2026-11-12)

El laboratorio ya no se congela: se **elimina** del repositorio. Se borran
`chatbot_project/`, `frontend/`, `docker-compose.yml`, `requirements.txt` e
`init_project.sh`, junto con la documentación asociada (`CODEBASE_MAP.md`,
`MCP_ARCHITECTURE.md`, `WEB_SEARCH_OPENWEBUI.md`, `SMALL_CONTEXT_STRATEGY.md`) y
el archivo historico de `docs/archive/`. El repositorio queda exclusivamente
como servidor MCP de dominio y pasa a llamarse **McpServer** (paquete Python
`mcpserver`). La decision original sigue vigente en lo demas.
