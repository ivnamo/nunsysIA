# Guion demo final

Guion operativo para defender la POC en 3-5 minutos ante un revisor tecnico.
La demo debe mostrar comportamiento, trazabilidad y limites, no solo una
respuesta bonita.

## Objetivo de la demo

Demostrar que el sistema responde preguntas de negocio en lenguaje natural
combinando ERP Northwind, API mock de produccion y documentos PDF mediante RAG,
con un flujo agentic auditable:

```text
FastAPI / Chainlit
-> Planner
-> Reasoner / Executor
-> Validator
-> FinalResponseBuilder
```

El mensaje clave: no hay un agente monolitico improvisado; hay nodos separados,
tools deterministas, validacion y trazabilidad publica.

## Preparacion

Desde la raiz del repo:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Resultado esperado versionado:

```text
221 passed, 23 skipped, 2 warnings
```

Validacion opt-in con LLM real antes de la demo:

```powershell
$env:RUN_REAL_LLM_TESTS="1"
.\.venv\Scripts\python.exe -m pytest -m real_llm -rs
```

Resultado esperado:

```text
23 passed, 221 deselected, 2 warnings
```

Para demo Docker con Gemini real:

```powershell
docker compose -f docker-compose.yml -f docker-compose.secrets.yml up --build
```

URLs:

- Backend: `http://localhost:8000`
- Production mock: `http://localhost:8001`
- Chainlit: `http://localhost:8002`
- ChromaDB host: `http://localhost:8003`

Checks rapidos:

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/health"
Invoke-RestMethod -Uri "http://localhost:8001/health"
Invoke-RestMethod -Uri "http://localhost:8000/api/documents"
```

## Orden recomendado

### 1. Apertura

Duracion: 30 segundos.

Mensaje:

- Esta POC no busca sustituir ERP ni MES; orquesta fuentes existentes.
- El stack esta acotado: FastAPI, LangGraph, LangChain, Chainlit, ChromaDB,
  Pydantic y pytest.
- Si preguntan por "deepAgentes de LangChain": el runtime principal usa
  LangGraph + LangChain para control fino, y existe un adapter opcional
  `app.agents.deepagents_adapter` que envuelve este workflow como sidecar
  Deep Agents sin sustituir la arquitectura auditada.
- Si se quiere ensenar la prueba comparativa, existe el endpoint experimental
  `/api/experimental/deepagents/query`, protegido por
  `ENABLE_DEEPAGENTS_EXPERIMENT=true`, y el script
  `scripts/run_deepagents_comparison.py`.
- Tambien existe `/api/experimental/deepagents/tools/query` para R22.4: Deep
  Agents con tools individuales. En la comparacion real respondio con contenido
  correcto, pero uso estrategias de tool calls menos controladas; por eso queda
  como experimento, no como ruta recomendada.
- Las respuestas deben traer `sources`, `tool_calls`, `fallbacks`, `status`,
  `reasoning` y `data`.

### 2. Upload y espacio documental

Duracion: 30 segundos.

En Chainlit, subir los PDFs `v2_*.pdf` de `data/sample_docs/` o usar el endpoint:

```powershell
curl.exe -s -X POST "http://localhost:8000/api/documents/upload" -F "file=@data/sample_docs/v2_anexo_penalizaciones_sla.pdf;type=application/pdf"
Invoke-RestMethod -Uri "http://localhost:8000/api/documents"
```

Que destacar:

- El upload multipart usa `UploadFile`.
- ChromaDB es el vector store objetivo.
- Si Chroma o embeddings caen a fallback, aparece en `fallbacks`.

### 3. ERP + produccion

Pregunta:

```text
Que pedidos pendientes tiene el cliente ALFKI y en que estado de produccion estan?
```

Esperado:

- `status`: `completed`
- `sources`: `ERP`, `Produccion`
- aparecen `10248` y `10252`
- `tool_calls`: `ERPTool.get_pending_orders_by_customer` y
  `ProductionAPITool.get_status_for_erp_orders`
- `data`: conteos e IDs, no filas raw.

Defensa:

- El Planner genera un plan estructurado.
- El Reasoner ejecuta tools deterministas.
- El FinalResponseBuilder no inventa estados: solo sintetiza evidencias.

### 4. Query DSL segura con cruce controlado

Pregunta:

```text
Cruza produccion con ERP y dime clientes afectados por bloqueos.
```

Esperado:

- `status`: `completed`
- `sources`: `Produccion`, `ERP`
- `tool_calls`: `ProductionQueryTool.query_orders` y
  `ERPQueryTool.query_orders`
- el segundo tool call filtra ERP por los `order_id` recuperados de produccion
- `data`: `production_order_ids`, `erp_query_order_ids` y
  `customers_resolved_count`, sin filas raw.

Defensa:

- El LLM no genera SQL ni endpoints HTTP.
- La DSL solo acepta entidades, filtros, selects, orden y limite allowlist.
- El cruce no vive en la DSL: lo hace el reasoner por `order_id`.

### 5. RAG documental

Pregunta:

```text
Segun el PDF, hay alguna penalizacion por retrasos?
```

Esperado:

- `status`: `completed`
- `sources`: `Documentos`
- `data.rag.documents`: incluye `v2_anexo_penalizaciones_sla.pdf`
- `data.rag.citations`: incluye `filename`, `page`, `chunk_id`, `score`
- no se expone texto completo de chunks.

Defensa:

- RAG es una tool determinista, no un agente autonomo.
- La respuesta final se construye solo desde chunks recuperados.
- Si no hay evidencia, el sistema debe devolver `insufficient_context`.

### 6. Caso mixto ERP + produccion + RAG

Pregunta:

```text
en funcion de los pedidos y su estado dime que penalizaciones vamos a tener en cada uno
```

Esperado:

- `status`: `completed`
- `sources`: `ERP`, `Produccion`, `Documentos`
- `tool_calls`: ERP, produccion por pedidos y RAG documental
- pedidos bloqueados/retrasados se explican con motivo productivo y normativa.

Defensa:

- Este es el caso fuerte: combina datos transaccionales, estado operativo y
  normativa documental.
- El Validator bloquea respuestas de penalizaciones si falta evidencia
  documental.

### 7. Memoria conversacional acotada

Primero:

```text
Que pedidos pendientes tiene el cliente ALFKI?
```

Luego con el mismo `conversation_id`:

```text
Y en que estado estan?
```

Esperado:

- `sources`: `Memoria`, `ERP`, `Produccion`
- la memoria solo resuelve la referencia a ALFKI o pedidos previos
- los datos de negocio actuales vuelven a salir de ERP/produccion.

Defensa:

- La memoria conversacional no es fuente de verdad de negocio.
- Es contexto acotado de 5 turnos y queda visible como `Memoria`.

### 8. Guardrail insufficient_context

Pregunta:

```text
Segun el PDF, que receta de cocina vegana recomienda?
```

Esperado:

- `status`: `insufficient_context`
- `sources`: `Documentos`
- `data.rag.chunks_count`: `0`
- no inventa receta.

Defensa:

- El caso demuestra que el sistema sabe no responder.
- Este guardrail es mas importante que una respuesta fluida.

### 9. Trazabilidad de replanning

No es obligatorio forzar este caso en demo en vivo, pero si aparece un replan,
mostrar:

```text
data.replanning
```

Esperado:

- `replans_count`
- `max_replans`
- eventos con `attempt`, `decision`, `status`, `failure_reason`
- sin planes raw, prompts ni chain-of-thought.

Defensa:

- `MAX_REPLANS = 2`.
- Se audita que hubo replan y por que, sin exponer razonamiento interno.

## Que defender ante el revisor

- El flujo LangGraph es explicito: Planner -> Reasoner/Executor -> Validator ->
  FinalResponseBuilder.
- Deep Agents queda cubierto como integracion opcional de bajo riesgo:
  `requirements-deepagents.txt` + `app.agents.deepagents_adapter`, manteniendo
  `/api/query` sobre el grafo validado.
- Las rutas FastAPI son finas y delegan en servicios, graph o tools.
- ERP, produccion, memoria y RAG entran como tools controladas.
- El planner LLM esta acotado por schema Pydantic, lista cerrada de actions y
  fallback determinista.
- La respuesta final LLM esta validada contra evidencias y tiene fallback
  determinista.
- RAG devuelve citas por chunk y no expone chunks completos en `data`.
- `fallbacks` son visibles; no se ocultan rutas alternativas.
- La memoria no decide hechos de negocio; solo resuelve referencias.
- Docker Compose valida backend, mock de produccion, Chainlit y ChromaDB HTTP.
- La suite cubre contratos y regresiones criticas: `221 passed` y deja los 23
  tests `real_llm` como validacion opt-in con ChromaDB persistente local y
  embeddings reales.

## Deuda consciente que conviene admitir

- ERP usa SQLite en memoria con seed Northwind reducido por ser POC.
- La API mock de produccion no representa un MES real.
- La memoria conversacional es in-memory y no distribuida.
- No hay autenticacion, roles ni multi-tenant.
- No hay observabilidad productiva completa.
- ChromaDB puede caer a fallback en memoria en desarrollo, pero queda visible.
- Los prompts son suficientes para POC, no versionado prompt registry.
- No hay reranking avanzado ni evaluacion offline extensa de retrieval.
- Docker Compose es runtime de demo, no despliegue productivo.
- La suite automatizada mockea LLMs; la beta real se documenta por separado.

## Plan de rollback en demo

Si Gemini falla:

- mostrar que `fallbacks` expone planner/final deterministas;
- ejecutar los mismos casos en modo deterministico;
- defender que los tests no dependen de proveedor pagado.

Si Chroma falla:

- el sistema cae a vector store en memoria;
- `fallbacks` incluye `FALLBACK_VECTOR_STORE_IN_MEMORY`;
- subir de nuevo los PDFs y repetir RAG.

Si Chainlit falla:

- usar `POST /api/query` desde PowerShell;
- el contrato de respuesta es el mismo.

Si un caso RAG devuelve `insufficient_context`:

- comprobar que los PDFs estan indexados con `GET /api/documents`;
- revisar `data.rag.documents` y `data.rag.citations`;
- si no hay evidencia, defender que no inventar es el comportamiento correcto.

## Cierre recomendado

Mensaje final:

La POC esta lista para revision tecnica como demostrador empresarial: integra
fuentes heterogeneas, mantiene el flujo agentic aprobado, evita alucinaciones
mediante tools deterministas y validacion, y devuelve trazabilidad auditable para
cada respuesta. La deuda restante esta acotada y documentada.
