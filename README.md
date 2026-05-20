# nunsysIA

POC tecnica de sistema agentic empresarial. El objetivo final es responder preguntas de negocio en lenguaje natural combinando:

- ERP basado en Northwind.
- API REST mock de produccion.
- Documentos PDF consultables mediante RAG.
- API principal `POST /api/query`.
- UI conversacional con Chainlit.
- Trazabilidad explicita de fuentes, pasos y tool calls.

## Estado actual

Fase actual: **Fase 6 - RAG con subida de PDFs**.

Este repositorio contiene por ahora:

- reglas de Cursor en `.cursor/rules/`;
- documentacion tecnica en `docs/`;
- prompts reutilizables en `prompts/`;
- estructura base de carpetas;
- requirements iniciales;
- configuracion minima de pytest.
- backend FastAPI minimo;
- endpoint `GET /health`;
- schema Pydantic de health;
- tests unitarios e integracion para health.
- seed SQL Northwind minimo;
- schemas Pydantic ERP;
- repositorio ERP testeable sin Docker;
- tests deterministas de consultas ERP.
- API mock de produccion separada del backend principal;
- seed JSON de estados productivos;
- tests HTTP basicos del mock de produccion.
- trazabilidad estructurada para tool calls;
- `ERPTool` determinista con input/output Pydantic;
- `ProductionAPITool` determinista con input/output Pydantic;
- cliente HTTP de produccion;
- tests unitarios de tools.
- `AgentState` compartido para LangGraph;
- Planner determinista con plan estructurado;
- Reasoner/Executor que ejecuta tools ERP y produccion;
- Validator con replanning limitado por `MAX_REPLANS = 2`;
- FinalResponseBuilder con `QueryResponse` estructurada;
- tests unitarios e integracion del grafo basico.
- pipeline RAG PDF -> texto -> chunks -> embeddings -> vector store;
- adaptador ChromaDB con fallback local en memoria si Chroma no esta disponible;
- `DocumentRAGTool` con trazabilidad y `insufficient_context`;
- endpoints `POST /api/documents/upload` y `GET /api/documents`;
- tests de ingestion, retrieval, tool RAG y endpoints documentales.

Disponible para ejecutar actualmente:

- backend FastAPI con `GET /health`;
- endpoints documentales para subir y listar PDFs;
- API mock de produccion;
- tests automatizados;
- grafo LangGraph invocable desde tests y codigo Python;
- RAG documental invocable como tool y desde endpoints documentales.

Pendiente todavia:

- endpoint `POST /api/query`;
- integracion del grafo en el backend principal;
- interfaz Chainlit;
- Docker Compose.

## Arquitectura decidida

- Backend: FastAPI.
- Orquestacion agentic: LangGraph `StateGraph`.
- Tools, RAG y llamadas LLM: LangChain.
- UI: Chainlit.
- Vector store inicial: ChromaDB.
- Schemas: Pydantic.
- Tests: pytest.
- Runtime objetivo: Docker Compose.

Flujo objetivo:

```text
Usuario
-> FastAPI / Chainlit
-> LangGraph StateGraph
-> Planner Agent
-> Reasoner / Executor Agent
-> Validator Node
-> FinalResponseBuilder
```

## Estructura base

```text
app/
  api/
  agents/
  tools/
  rag/
  erp/
  production/
  core/
  schemas/
production_mock/
chainlit_app/
data/
  sample_docs/
tests/
  unit/
  integration/
  e2e/
  fixtures/
```

## Desarrollo por fases

La guia principal esta en:

- `docs/TASK_PLAN.md`
- `docs/ARCHITECTURE.md`
- `docs/API_CONTRACT.md`
- `docs/TRACEABILITY.md`
- `docs/DEVELOPMENT_GUIDE.md`

Antes de implementar una fase, leer tambien `.cursor/rules/`.

## Preparacion local

Crear entorno virtual:

```bash
python -m venv .venv
```

Activar entorno en PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Instalar dependencias:

```bash
pip install -r requirements-dev.txt
```

Ejecutar tests:

```bash
pytest
```

Ejecutar backend principal:

```bash
python -m uvicorn app.main:app --reload --port 8000
```

Comprobar health:

```bash
curl http://localhost:8000/health
```

Subir un PDF:

```bash
curl -X POST http://localhost:8000/api/documents/upload \
  -F "file=@ruta/al/documento.pdf;type=application/pdf"
```

Listar documentos indexados:

```bash
curl http://localhost:8000/api/documents
```

## API mock de produccion

Ejecutar manualmente:

```bash
python -m uvicorn production_mock.main:app --reload --port 8001
```

Endpoints del mock:

- `GET /health`
- `GET /production/orders`
- `GET /production/orders?status=blocked`
- `GET /production/orders?status=delayed`
- `GET /production/orders/{order_id}`

## Siguiente fase

Fase 7:

- preparar interfaz Chainlit para demo;
- mostrar respuesta, fuentes, reasoning visible y tool calls;
- conectar con el backend cuando exista `/api/query`;
- mantener UI ligera y orientada a la prueba tecnica.

Antes de Chainlit puede ser conveniente implementar `POST /api/query` si se decide priorizar una demo end-to-end desde API.
