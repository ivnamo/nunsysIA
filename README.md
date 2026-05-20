# nunsysIA

POC tecnica de sistema agentic empresarial. El objetivo final es responder preguntas de negocio en lenguaje natural combinando:

- ERP basado en Northwind.
- API REST mock de produccion.
- Documentos PDF consultables mediante RAG.
- API principal `POST /api/query`.
- UI conversacional con Chainlit.
- Trazabilidad explicita de fuentes, pasos y tool calls.

## Estado actual

Fase actual: **Fase 8 - Trazabilidad y respuesta estructurada**.

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
- app Chainlit conectada a `POST /api/query`;
- cliente HTTP de Chainlit testeable;
- renderizado de respuesta, fuentes, pasos y tool calls en UI.
- normalizacion de trazas publicas;
- sanitizacion de argumentos, errores y failure reasons;
- resumen publico de evidencias en `data` sin filas raw ni objetos internos.

Disponible para ejecutar actualmente:

- backend FastAPI con `GET /health`;
- endpoints documentales para subir y listar PDFs;
- endpoint `POST /api/query`;
- interfaz Chainlit;
- API mock de produccion;
- tests automatizados;
- grafo LangGraph invocable desde API, tests y codigo Python;
- RAG documental invocable como tool y desde endpoints documentales.
- trazabilidad normalizada y sanitizada en `/api/query`.
- payload de demo `query.json` para probar `/api/query`.

Pendiente todavia:

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

En Cursor o VS Code, con la extension Python instalada, las terminales integradas activan `.venv` automaticamente gracias a `.vscode/settings.json`. Si no ocurre en PowerShell, revisa la politica de ejecucion (`Set-ExecutionPolicy RemoteSigned -Scope CurrentUser`) o abre una terminal nueva tras recargar la ventana.

Instalar dependencias:

```bash
pip install -r requirements-dev.txt
```

En local, `requirements-dev.txt` no instala ChromaDB nativo para evitar errores de compilacion de `chroma-hnswlib` en Windows. La POC usa fallback en memoria si Chroma no esta disponible.

Instalar ChromaDB local solo si lo necesitas:

```bash
pip install -r requirements-chroma.txt
```

Ejecutar tests:

```bash
pytest
```

Ejecutar backend principal:

```bash
python -m uvicorn app.main:app --reload --port 8000
```

Si vas a probar consultas que llamen a produccion fuera de Docker, en PowerShell apunta el backend al mock local antes de arrancarlo:

```powershell
$env:PRODUCTION_API_BASE_URL="http://localhost:8001"
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

Consultar el workflow agentic:

```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  --data @query.json
```

Ejecutar interfaz Chainlit:

```powershell
$env:BACKEND_API_BASE_URL="http://localhost:8000"
python -m chainlit run chainlit_app/main.py -w --port 8002
```

La UI queda disponible en `http://localhost:8002`.

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

Fase 9:

- preparar Dockerfile;
- preparar docker-compose;
- levantar backend, mock de produccion y Chainlit;
- documentar variables y comandos de ejecucion.
