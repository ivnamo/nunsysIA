# nunsysIA

POC tecnica de sistema agentic empresarial. El objetivo final es responder preguntas de negocio en lenguaje natural combinando:

- ERP basado en Northwind.
- API REST mock de produccion.
- Documentos PDF consultables mediante RAG.
- API principal `POST /api/query`.
- UI conversacional con Chainlit.
- Trazabilidad explicita de fuentes, pasos y tool calls.

## Estado actual

Fase actual: **P9 - funcionalidad evaluable de producto**.

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
- Planner hibrido con LLM opcional, plan estructurado y fallback determinista;
- Reasoner/Executor que ejecuta tools ERP y produccion;
- Validator con replanning limitado por `MAX_REPLANS = 2`;
- FinalResponseBuilder con `QueryResponse` estructurada;
- `fallbacks` visibles en API y Chainlit para auditar rutas alternativas;
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
- abstraccion LLM para Gemini/OpenAI con fallback determinista;
- Planner hibrido: LLM opcional + schema Pydantic + lista cerrada de tools/actions;
- PDFs mock realistas en `data/sample_docs/`;
- validacion manual documentada en `docs/MANUAL_VALIDATION.md`.
- citas documentales visibles por chunk en respuestas RAG (`filename`, `page`, `chunk_id`, `score`).

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
- soporte configurable para Gemini u OpenAI sin cambiar grafo, agents ni tools.
- respuesta final con LLM controlado y fallback determinista;
- marcadores `FALLBACK_*` cuando se usa planner por reglas, respuesta determinista, embeddings deterministas o vector store en memoria;
- payload de demo `query.json` para probar `/api/query`.
- PDFs mock realistas en `data/sample_docs/` para probar RAG multi-documento.

Pendiente todavia:

- memoria conversacional de ultimas 5 interacciones;
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
- `docs/MANUAL_VALIDATION.md`

Antes de implementar una fase, leer tambien `.cursor/rules/`.

## Validacion manual

Los comandos exactos para arrancar servicios, subir PDFs de demo, consultar API,
probar Chainlit y revisar que no hay secretos estan en:

```text
docs/MANUAL_VALIDATION.md
```

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

Configurar proveedor LLM en `.env`:

```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=tu_key
GEMINI_MODEL=gemini-2.5-flash
GEMINI_API_TRANSPORT=rest
LLM_TIMEOUT_SECONDS=45
EMBEDDING_PROVIDER=gemini
GEMINI_EMBEDDING_MODEL=gemini-embedding-001
```

Para el ERP usa `ERP_DATABASE_URL`, no `DATABASE_URL`. Chainlit reserva `DATABASE_URL` para su propia persistencia interna con `asyncpg`.

La arquitectura tambien permite OpenAI sin tocar el grafo ni las tools:

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=tu_key
OPENAI_MODEL=gpt-4o-mini
EMBEDDING_PROVIDER=openai
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

Ejecutar tests:

```bash
pytest
```

Ejecutar backend principal:

```powershell
$env:PRODUCTION_API_BASE_URL="http://localhost:8001"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000
```

Para desarrollo con reload en Windows, limita el directorio observado para no vigilar `.venv`:

```powershell
$env:PRODUCTION_API_BASE_URL="http://localhost:8001"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --reload-dir app --port 8000
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

Generar de nuevo los PDFs mock de demo:

```powershell
.\.venv\Scripts\python.exe scripts\generate_sample_pdfs.py
```

Documentos disponibles:

- `data/sample_docs/contrato_marco_logistica_2026.pdf`
- `data/sample_docs/anexo_penalizaciones_sla.pdf`
- `data/sample_docs/procedimiento_produccion_bloqueos.pdf`
- `data/sample_docs/politica_calidad_entregas.pdf`
- `data/sample_docs/condiciones_comerciales_northwind.pdf`

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
Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
.\.venv\Scripts\python.exe -m chainlit run chainlit_app/main.py -w --port 8002
```

La UI queda disponible en `http://localhost:8002`.

En Chainlit puedes adjuntar hasta 5 PDFs por mensaje. Los documentos se indexan
en el espacio documental del backend y quedan disponibles para las siguientes
preguntas RAG. Para listar el espacio documental desde la UI, envia:

```text
/documentos
```

## API mock de produccion

Ejecutar manualmente:

```powershell
.\.venv\Scripts\python.exe -m uvicorn production_mock.main:app --port 8001
```

Endpoints del mock:

- `GET /health`
- `GET /production/orders`
- `GET /production/orders?status=blocked`
- `GET /production/orders?status=delayed`
- `GET /production/orders/{order_id}`

## Siguiente fase

La fase actual sigue siendo P9: funcionalidad evaluable de producto.

- implementar memoria conversacional de ultimas 5 interacciones;
- despues cerrar Docker Compose y README final.
- documentar variables y comandos de ejecucion.
