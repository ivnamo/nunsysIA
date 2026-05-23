# Arquitectura

## Objetivo

La POC responde preguntas de negocio en lenguaje natural combinando tres tipos
de evidencia:

- ERP/Northwind reducido.
- API REST mock de produccion.
- PDFs indexados mediante RAG.

La arquitectura publica se centra en un contrato estable: `POST /api/query`
devuelve `QueryResponse` con respuesta, fuentes, pasos visibles y trazabilidad.

## Flujo principal

```text
Usuario o Chainlit
-> FastAPI
-> POST /api/query
-> AgentRouter
-> DeepAgentService
-> DeepAgentsToolsQueryService
-> ERPTool / ProductionAPITool / DocumentRAGTool / MemoryTool
-> ResponseNormalizer
-> QueryResponse
```

`mode` es opcional. Si no se envia, se usa `AGENT_MODE`; la configuracion de
entrega debe mantener `AGENT_MODE=deepagent`.

## Modos agentic

- `deepagent`: principal y por defecto. Usa LangChain DeepAgents con tools de
  negocio directas y compuestas.
- `deepagent_sidecar`: alternativo y experimental. DeepAgents llama al workflow
  legacy como herramienta de comparativa.
- `legacy_langgraph`: legacy/experimental. Conserva la implementacion previa con
  LangGraph para regresion tecnica.

Los endpoints `/api/experimental/deepagents/query` y
`/api/experimental/deepagents/tools/query` existen solo para diagnostico y
requieren `ENABLE_DEEPAGENTS_EXPERIMENT=true`.

## Capas

### API

`app/api/` contiene rutas FastAPI finas:

- `GET /health`
- `POST /api/query`
- `POST /api/documents/upload`
- `GET /api/documents`
- `DELETE /api/documents?confirm=reset-delivery-rag`, limitado a entornos
  `development`, `docker` o `test` para validacion reproducible
- endpoints experimentales DeepAgents deshabilitados por defecto

Las rutas validan input, invocan servicios y devuelven schemas Pydantic.

### Servicios

`app/services/agent_service.py` construye el router agentic y conecta:

- tools ERP;
- tools de produccion;
- tool RAG;
- normalizador de respuesta;
- servicios legacy o experimentales cargados de forma lazy. Si `/api/query`
  usa `deepagent`, no se construye el workflow LangGraph.

`ResponseNormalizer` evita filtrar objetos internos de LangChain, LangGraph o
ChromaDB.

### Agentes

`app/agents/deepagents_tools_service.py` implementa el flujo principal. La
politica de seleccion de tools vive en `deepagents_policy.py`, la configuracion
del harness DeepAgents en `deepagents_harness.py` y la respuesta determinista
grounded en `deepagents_answering.py`. Antes de responder, el flujo ejecuta
tools obligatorias segun la intencion detectada y registra tool calls.
DeepAgents recibe solo tools directas de negocio. El flujo activo no registra
subagents de DeepAgents; las especializaciones ERP, produccion, RAG y memoria se
modelan como tools auditables. Tampoco se exponen tools de filesystem o shell al
endpoint de negocio.

La implementacion legacy en LangGraph sigue disponible en `app/agents/graph.py`
y modulos relacionados, pero no es el camino principal.

### Tools

`app/tools/` agrupa capacidades deterministas:

- `ERPTool` y `ERPQueryTool`.
- `ProductionAPITool` y `ProductionQueryTool`.
- `DocumentRAGTool`.
- `MemoryTool`.
- Query DSL interna validada con Pydantic.

Las tools devuelven datos estructurados y trazas sanitizadas.

### RAG

`app/rag/` gestiona:

- extraccion de texto PDF;
- particionado en chunks;
- embeddings;
- persistencia obligatoria en ChromaDB en el runtime de entrega;
- retrieval con metadatos.

El factory documental de la aplicacion falla de forma explicita si no puede
crear ChromaDB o si el proveedor de embeddings es determinista. Las clases
in-memory/deterministicas se conservan solo para tests unitarios acotados.

Cada chunk conserva `document_id`, `document_hash`, `filename`, `page`,
`chunk_id`, `uploaded_at` e `indexed_at`.

### Datos

- ERP: seed SQL reducido en `data/northwind_seed.sql`, cargado en SQLite en
  memoria por `app/services/erp_service.py`.
- Produccion: seed JSON en `data/production_seed.json`, servido por
  `production_mock/`.
- Documentos: los PDFs oficiales de demo son los `v2_*` en
  `data/sample_docs/`; los PDFs base quedan como historico de desarrollo.

## Trazabilidad

La respuesta publica incluye:

- `sources`: fuentes usadas.
- `reasoning`: pasos visibles, resumidos y aptos para auditoria.
- `tool_calls`: tool, accion, argumentos sanitizados, estado, fuente,
  duracion y resumen.
- `fallbacks`: rutas alternativas usadas por capas no documentales. En la
  entrega no debe aparecer fallback de vector store en memoria ni embeddings
  deterministas.
- `data`: resumen publico de evidencias, no filas raw completas.

No se devuelve chain-of-thought interno.

## Fronteras de responsabilidad

- `api/` no contiene logica de negocio.
- `agents/` coordina decision y ejecucion.
- `tools/` accede a fuentes y capacidades deterministas.
- `rag/` se limita a ingestion y retrieval documental.
- `services/` conecta dependencias y normaliza contratos.
- `schemas/` define los modelos publicos.
