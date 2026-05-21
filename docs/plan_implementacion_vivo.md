# Plan de implementacion vivo

Este documento refleja el estado actual del repositorio. Para el desglose historico por fases, ver `docs/TASK_PLAN.md`.

## Estado actual

La POC tiene **P9 cerrada a nivel funcional**. El siguiente bloque pendiente es **P10 - Docker Compose**.

Ya existe codigo funcional para:

- Backend FastAPI con `GET /health`, `POST /api/query`, `POST /api/documents/upload` y `GET /api/documents`.
- API mock de produccion en `production_mock/`.
- ERP Northwind reducido con SQLite en memoria y seed `data/northwind_seed.sql`.
- Tools deterministas para ERP, produccion y RAG.
- Grafo LangGraph con Planner, Reasoner/Executor, Validator y FinalResponseBuilder.
- Planner hibrido con Gemini/OpenAI opcionales y fallback determinista.
- FinalResponseBuilder con LLM controlado y fallback determinista.
- RAG PDF con ChromaDB como objetivo y fallback en memoria cuando Chroma no esta disponible.
- Chainlit conectado al backend, con subida de PDFs y comando `/documentos`.
- Memoria conversacional simple de ultimas 5 interacciones por `conversation_id`.
- Trazabilidad publica: fuentes, pasos, tool calls, fallbacks, estado, confianza y resumen de evidencias.
- Tests automatizados versionados: `115 passed, 2 warnings` en la validacion local actual.

## Pendiente real

- Cerrar Docker Compose con backend, API mock de produccion, ChromaDB y Chainlit.
- Mantener el ERP con SQLite en memoria para la demo salvo decision explicita de cambiar persistencia.
- Preparar guion demo final de 3-5 minutos.

## Decisiones vigentes

| Decision | Estado | Nota |
|---|---|---|
| FastAPI como backend principal | Vigente | Rutas finas, logica en servicios/tools/grafo. |
| LangGraph para orquestacion | Vigente | `MAX_REPLANS = 2` esta fijado en `app/agents/state.py`. |
| LangChain para LLM/tools/embeddings | Vigente | Gemini y OpenAI son opcionales; tests no dependen de llamadas pagadas. |
| ChromaDB como vector store objetivo | Vigente | Soporta `persistent` embebido y `http`; sin cliente o servidor disponible hay fallback en memoria. |
| ERP con SQLite en memoria | Vigente | Se carga desde `data/northwind_seed.sql`; `ERP_DATABASE_URL` queda reservado para persistencia externa futura. |
| Chainlit como UI de demo | Vigente | Muestra respuesta, fuentes, citas, pasos, tool calls y fallbacks. |
| Memoria conversacional | Vigente | In-memory por proceso, maximo 5 turnos por `conversation_id`; sirve para resolver referencias, no como fuente de verdad. |

## Plan inmediato

1. Docker Compose.
   - Crear `Dockerfile`.
   - Crear `docker-compose.yml`.
   - Incluir servicios para backend, produccion mock, Chainlit y ChromaDB.
   - Ajustar variables por entorno Docker frente a local.

2. Cierre de demo.
   - Ejecutar `pytest`.
   - Ejecutar checklist de `docs/MANUAL_VALIDATION.md`.
   - Confirmar que no hay secretos en Git.
   - Preparar preguntas obligatorias ERP/produccion/RAG/mixtas.

## Criterios para pasar a cierre

- `pytest` pasa sin llamadas pagadas.
- Las preguntas obligatorias funcionan en API y Chainlit.
- Las respuestas muestran trazabilidad y fallbacks cuando aplica.
- Las consultas documentales sin evidencia devuelven `insufficient_context`.
- Docker Compose levanta todos los servicios o queda documentado como pendiente explicito.
