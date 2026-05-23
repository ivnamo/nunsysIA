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

`mode` es opcional. Si no se envia, se usa `deepagent`.

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
- endpoints experimentales DeepAgents deshabilitados por defecto

Las rutas validan input, invocan servicios y devuelven schemas Pydantic.

### Servicios

`app/services/agent_service.py` construye el router agentic y conecta:

- tools ERP;
- tools de produccion;
- tool RAG;
- normalizador de respuesta;
- servicios legacy o experimentales.

`ResponseNormalizer` evita filtrar objetos internos de LangChain, LangGraph o
ChromaDB.

### Agentes

`app/agents/deepagents_tools_service.py` implementa el flujo principal. Antes de
responder, ejecuta tools obligatorias segun la intencion detectada y registra
tool calls. DeepAgents recibe solo tools de negocio; no se exponen tools de
filesystem, shell ni subagentes genericos al endpoint de negocio.

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
- persistencia en ChromaDB o fallback en memoria;
- retrieval con metadatos.

Cada chunk conserva `document_id`, `filename`, `page`, `chunk_id` y
`uploaded_at`.

### Datos

- ERP: seed SQL reducido en `data/northwind_seed.sql`, cargado en SQLite en
  memoria por `app/services/erp_service.py`.
- Produccion: seed JSON en `data/production_seed.json`, servido por
  `production_mock/`.
- Documentos: PDFs mock en `data/sample_docs/`.

## Trazabilidad

La respuesta publica incluye:

- `sources`: fuentes usadas.
- `reasoning`: pasos visibles, resumidos y aptos para auditoria.
- `tool_calls`: tool, accion, argumentos sanitizados, estado y resumen.
- `fallbacks`: rutas de fallback usadas.
- `data`: resumen publico de evidencias, no filas raw completas.

No se devuelve chain-of-thought interno.

## Fronteras de responsabilidad

- `api/` no contiene logica de negocio.
- `agents/` coordina decision y ejecucion.
- `tools/` accede a fuentes y capacidades deterministas.
- `rag/` se limita a ingestion y retrieval documental.
- `services/` conecta dependencias y normaliza contratos.
- `schemas/` define los modelos publicos.
