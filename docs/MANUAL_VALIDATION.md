# Validacion manual de la POC

Este checklist sirve para validar la POC en local antes de una demo. Los comandos estan pensados para PowerShell desde la raiz del repo.

No pegues API keys en la terminal ni en capturas. El backend lee `.env` automaticamente.

## 0. Preparar entorno

```powershell
.\.venv\Scripts\Activate.ps1
```

Si necesitas regenerar los PDFs mock:

```powershell
.\.venv\Scripts\python.exe scripts\generate_sample_pdfs.py
```

Ejecutar tests automatizados:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Resultado esperado:

```text
78 passed
```

Puede aparecer una warning de LangGraph; no bloquea la validacion.

## 1. Arrancar servicios

Usa tres terminales separadas.

### Terminal 1 - API mock de produccion

```powershell
.\.venv\Scripts\python.exe -m uvicorn production_mock.main:app --port 8001
```

Validar en otra terminal:

```powershell
Invoke-RestMethod -Uri "http://localhost:8001/health"
```

Resultado esperado:

```text
status
------
ok
```

### Terminal 2 - Backend FastAPI

```powershell
$env:PRODUCTION_API_BASE_URL="http://localhost:8001"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000
```

Validar:

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/health"
```

Resultado esperado:

```text
status
------
ok
```

Nota para Windows: evita `--reload` durante la validacion manual. Uvicorn puede detectar cambios dentro de `.venv` por OneDrive, antivirus o paquetes como `pywin32`, y reiniciar el proceso aunque la aplicacion este bien. Si necesitas modo desarrollo con recarga, limita el watch:

```powershell
.\.venv\Scripts\python.exe -m uvicorn production_mock.main:app --reload --reload-dir production_mock --port 8001
```

```powershell
$env:PRODUCTION_API_BASE_URL="http://localhost:8001"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --reload-dir app --port 8000
```

### Terminal 3 - Chainlit

```powershell
$env:BACKEND_API_BASE_URL="http://localhost:8000"
Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
.\.venv\Scripts\python.exe -m chainlit run chainlit_app/main.py -w --port 8002
```

Abrir:

```text
http://localhost:8002
```

## 2. Cargar documentos por API

Subir los 5 documentos mock al espacio documental:

```powershell
$docs = @(
  "contrato_marco_logistica_2026.pdf",
  "anexo_penalizaciones_sla.pdf",
  "procedimiento_produccion_bloqueos.pdf",
  "politica_calidad_entregas.pdf",
  "condiciones_comerciales_northwind.pdf"
)

foreach ($doc in $docs) {
  curl.exe -s -X POST "http://localhost:8000/api/documents/upload" `
    -F "file=@data/sample_docs/$doc;type=application/pdf"
}
```

Listar documentos indexados:

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/documents" |
  ConvertTo-Json -Depth 10
```

Resultado esperado:

- aparecen 5 documentos;
- cada documento tiene `document_id`, `filename`, `uploaded_at` y `chunks_indexed`;
- `chunks_indexed` es mayor que 0.

Nota sobre `fallbacks`:

- Si aparece `FALLBACK_VECTOR_STORE_IN_MEMORY`, los PDFs se han indexado en memoria del proceso, no en ChromaDB.
- Ese modo sirve para desarrollo rapido, pero los documentos se pierden al reiniciar FastAPI.
- Para una demo evaluable con ChromaDB real, `fallbacks` no debe contener `FALLBACK_VECTOR_STORE_IN_MEMORY`.

## 3. Validar ERP + produccion por API

### Pedidos pendientes de ALFKI con estado de produccion

```powershell
$body = @{
  question = "Que pedidos pendientes tiene el cliente ALFKI y en que estado de produccion estan?"
  conversation_id = "manual-erp-001"
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "http://localhost:8000/api/query" `
  -Method Post `
  -ContentType "application/json" `
  -Body $body

$response | ConvertTo-Json -Depth 10
```

Checks esperados:

- `status`: `completed`
- `sources`: incluye `ERP` y `Produccion`
- `answer`: menciona `10248` y `10252`
- `tool_calls`: incluye `ERPTool` y `ProductionAPITool`
- `fallbacks`: si aparece, debe indicar explicitamente `FALLBACK_*` y explicar que parte no uso LLM/Chroma/embeddings reales.

### Pedidos bloqueados y motivo

```powershell
$body = @{
  question = "Que pedidos estan bloqueados y cual es el motivo?"
  conversation_id = "manual-prod-001"
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "http://localhost:8000/api/query" `
  -Method Post `
  -ContentType "application/json" `
  -Body $body

$response | ConvertTo-Json -Depth 10
```

Checks esperados:

- `status`: `completed`
- `sources`: incluye `Produccion` y `ERP`
- `answer`: menciona pedidos bloqueados y motivos como `Falta de material` o `Falta de capacidad`

### Clientes con pedidos retrasados

```powershell
$body = @{
  question = "Que clientes tienen pedidos retrasados por problemas de produccion?"
  conversation_id = "manual-prod-002"
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "http://localhost:8000/api/query" `
  -Method Post `
  -ContentType "application/json" `
  -Body $body

$response | ConvertTo-Json -Depth 10
```

Checks esperados:

- `status`: `completed`
- `answer`: menciona pedidos retrasados;
- `answer`: menciona `10301`;
- `answer`: menciona `Ana Trujillo` o `ANATR`;
- `answer`: menciona `Averia en linea de produccion`.

### Resumen de pedidos del mes

```powershell
$body = @{
  question = "Dame un resumen del estado de los pedidos de este mes"
  conversation_id = "manual-summary-001"
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "http://localhost:8000/api/query" `
  -Method Post `
  -ContentType "application/json" `
  -Body $body

$response | ConvertTo-Json -Depth 10
```

Checks esperados:

- `status`: `completed`
- `sources`: incluye `ERP` y `Produccion`
- `data.period`: `year=2026`, `month=5`
- `answer`: agrupa estados de produccion.

## 4. Validar RAG por API

### Penalizaciones por retrasos

```powershell
$body = @{
  question = "Segun el PDF, hay alguna penalizacion por retrasos?"
  conversation_id = "manual-rag-001"
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "http://localhost:8000/api/query" `
  -Method Post `
  -ContentType "application/json" `
  -Body $body

$response | ConvertTo-Json -Depth 10
```

Checks esperados:

- `status`: `completed`
- `sources`: `Documentos`
- `answer`: menciona `penalizacion`
- `data.rag.documents`: incluye `anexo_penalizaciones_sla.pdf`

### Plazos de entrega

```powershell
$body = @{
  question = "Que dice el documento sobre plazos de entrega standard?"
  conversation_id = "manual-rag-002"
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "http://localhost:8000/api/query" `
  -Method Post `
  -ContentType "application/json" `
  -Body $body

$response | ConvertTo-Json -Depth 10
```

Checks esperados:

- `status`: `completed`
- `sources`: `Documentos`
- `answer`: menciona `5 dias laborables`
- `data.rag.documents`: incluye `contrato_marco_logistica_2026.pdf`

### Resumen del contrato

```powershell
$body = @{
  question = "Resume los puntos clave del contrato"
  conversation_id = "manual-rag-003"
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "http://localhost:8000/api/query" `
  -Method Post `
  -ContentType "application/json" `
  -Body $body

$response | ConvertTo-Json -Depth 10
```

Checks esperados:

- `status`: `completed`
- `sources`: `Documentos`
- `tool_calls[0].tool`: `DocumentRAGTool`

### Pregunta sin evidencia documental

```powershell
$body = @{
  question = "Segun el PDF, que receta de cocina vegana recomienda?"
  conversation_id = "manual-rag-004"
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "http://localhost:8000/api/query" `
  -Method Post `
  -ContentType "application/json" `
  -Body $body

$response | ConvertTo-Json -Depth 10
```

Checks esperados:

- `status`: `insufficient_context`
- `answer`: indica que no hay contexto documental suficiente
- no inventa una receta.

## 5. Validar desde Chainlit

Abrir:

```text
http://localhost:8002
```

Validaciones manuales:

1. Adjuntar los PDFs de `data/sample_docs/`.
2. Esperar mensajes `Documento indexado`.
3. Escribir:

```text
/documentos
```

Resultado esperado:

- aparecen los documentos indexados y numero de chunks.

Preguntas recomendadas:

```text
Que pedidos pendientes tiene el cliente ALFKI y en que estado de produccion estan?
```

```text
Que pedidos estan bloqueados y cual es el motivo?
```

```text
Que clientes tienen pedidos retrasados por problemas de produccion?
```

```text
Segun el PDF, hay alguna penalizacion por retrasos?
```

```text
Que dice el documento sobre plazos de entrega standard?
```

Checks esperados en UI:

- respuesta clara;
- `Estado: completed` o `insufficient_context` cuando corresponda;
- fuentes visibles;
- pasos ejecutados;
- tool calls visibles;
- seccion `FALLBACKS` visible cuando se usa planner por reglas, respuesta determinista, vector store en memoria o embeddings deterministas;
- sin razonamiento interno sensible.

## 6. Validar que no hay secretos en Git

```powershell
git status --short
git diff -- .env
```

Resultado esperado:

- `.env` no aparece como archivo tracked;
- `git diff -- .env` no muestra secretos.

## 7. Troubleshooting rapido

### Chainlit muestra Internal Server Error y falta `asyncpg`

Sintoma:

```text
ModuleNotFoundError: No module named 'asyncpg'
```

Solucion:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Validar import:

```powershell
.\.venv\Scripts\python.exe -c "import asyncpg; import chainlit.data.chainlit_data_layer; print('chainlit data layer ok')"
```

Resultado esperado:

```text
chainlit data layer ok
```

### Chainlit falla con `invalid DSN ... got 'postgresql+psycopg'`

Sintoma:

```text
asyncpg.exceptions.ClientConfigurationError: invalid DSN: scheme is expected to be either "postgresql" or "postgres", got 'postgresql+psycopg'
```

Causa:

- Chainlit reserva `DATABASE_URL` para su propia persistencia interna con `asyncpg`.
- El backend usa SQLAlchemy/psycopg y por eso su DSN historico era `postgresql+psycopg://...`.

Solucion:

1. Usa `ERP_DATABASE_URL` para el ERP en `.env`.
2. No definas `DATABASE_URL` salvo que quieras configurar persistencia interna de Chainlit con un DSN `postgresql://...`.
3. Antes de arrancar Chainlit, limpia la variable en esa terminal:

```powershell
$env:BACKEND_API_BASE_URL="http://localhost:8000"
Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
.\.venv\Scripts\python.exe -m chainlit run chainlit_app/main.py -w --port 8002
```

### Chainlit muestra `500 Internal Server Error` en `/api/query`

Sintoma:

```text
HTTP Request: POST http://localhost:8000/api/query "HTTP/1.1 500 Internal Server Error"
```

Notas:

- `Translation file for es-ES not found. Using parent translation es.` es un warning inocuo de Chainlit.
- El fallo real esta en el backend, no en la UI.
- Si acabas de actualizar codigo, reinicia el proceso de FastAPI porque `uvicorn app.main:app --port 8000` no recarga cambios automaticamente.

Validacion rapida:

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/health"

$body = @{
  question = "Que pedidos pendientes tiene el cliente ALFKI y en que estado de produccion estan?"
  conversation_id = "debug-api-001"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/api/query" `
  -Method Post `
  -ContentType "application/json" `
  -Body $body `
  -TimeoutSec 30 |
  ConvertTo-Json -Depth 10
```

Resultado esperado:

- HTTP 200;
- `status` puede ser `completed`, `insufficient_context` o `tool_error`;
- si hay fallo de LLM, embeddings o Chroma, debe aparecer como respuesta controlada con `tool_calls`, no como 500.
- si se usa cualquier ruta alternativa, debe aparecer `fallbacks` con marcadores `FALLBACK_*`.

### Chainlit se queda en `Procesando consulta...`

Si `/documentos` funciona pero una pregunta se queda en `Procesando consulta...`, valida primero la API directamente:

```powershell
$body = @{
  question = "Que pedidos pendientes tiene el cliente ALFKI y en que estado de produccion estan?"
  conversation_id = "debug-chainlit"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/api/query" `
  -Method Post `
  -ContentType "application/json" `
  -Body $body `
  -TimeoutSec 20 |
  ConvertTo-Json -Depth 10
```

Si tambien se queda esperando, revisa que el backend se haya reiniciado tras cambios de `.env` y usa un timeout LLM corto:

```powershell
$env:PRODUCTION_API_BASE_URL="http://localhost:8001"
$env:LLM_TIMEOUT_SECONDS="8"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000
```

Para validar sin llamadas reales al LLM, puedes forzar planner determinista:

```powershell
$env:PRODUCTION_API_BASE_URL="http://localhost:8001"
$env:LLM_PROVIDER="deterministic"
$env:EMBEDDING_PROVIDER="deterministic"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000
```

Despues reinicia Chainlit.

### Gemini devuelve `404 models/... is not found` o `model ... no longer available`

Sintoma:

```text
NotFound: 404 models/gemini-1.5-flash is not found for API version v1beta
NotFound: 404 ... models/gemini-2.0-flash ... is no longer available to new users
```

Causa:

- el modelo configurado no esta disponible para la Gemini API usada por `langchain-google-genai`;
- LangChain puede reintentar varias veces y dejar la UI esperando.

Solucion recomendada:

```powershell
$env:GEMINI_MODEL="gemini-2.5-flash"
$env:GEMINI_API_TRANSPORT="rest"
$env:LLM_TIMEOUT_SECONDS="8"
```

Comprueba tambien que `.env` contiene:

```env
GEMINI_MODEL=gemini-2.5-flash
GEMINI_API_TRANSPORT=rest
LLM_TIMEOUT_SECONDS=8
```

Despues reinicia backend y Chainlit. El factory del LLM esta configurado con `retries=0` para que un modelo invalido falle rapido y el Planner pueda caer al fallback determinista.

### Gemini intenta conectar a `127.0.0.1:9`

Sintoma en `FALLBACKS` o consola:

```text
ServiceUnavailable: failed to connect to all addresses ... ipv4:127.0.0.1:9
```

Causa:

- hay variables de proxy (`HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY`) apuntando a un proxy local inexistente;
- el SDK intenta usar ese proxy para llamar a Gemini.

Solucion en la terminal donde arrancas FastAPI:

```powershell
Remove-Item Env:HTTP_PROXY -ErrorAction SilentlyContinue
Remove-Item Env:HTTPS_PROXY -ErrorAction SilentlyContinue
Remove-Item Env:ALL_PROXY -ErrorAction SilentlyContinue
Remove-Item Env:GIT_HTTP_PROXY -ErrorAction SilentlyContinue
Remove-Item Env:GIT_HTTPS_PROXY -ErrorAction SilentlyContinue
```

Despues arranca de nuevo el backend. Para validar Gemini directamente:

```powershell
$env:GEMINI_MODEL="gemini-2.5-flash"
$env:GEMINI_API_TRANSPORT="rest"
.\.venv\Scripts\python.exe -c "from app.core.config import get_settings; from app.core.llm import create_chat_model; s=get_settings(); m=create_chat_model(s); r=m.invoke('Respond with the single word OK'); print(getattr(r, 'content', r))"
```

Resultado esperado:

```text
OK
```

### Upload de PDFs devuelve `FALLBACK_VECTOR_STORE_IN_MEMORY`

Sintoma:

```json
{
  "status": "indexed",
  "chunks_indexed": 2,
  "fallbacks": [
    "FALLBACK_VECTOR_STORE_IN_MEMORY: ChromaDB no disponible o no usado; documentos en memoria del proceso."
  ]
}
```

Significado:

- La ingesta ha funcionado.
- Los embeddings pueden estar usando Gemini si no aparece `FALLBACK_EMBEDDINGS_DETERMINISTIC`.
- El vector store no es ChromaDB real; es memoria local del proceso.

Causas habituales:

- `chromadb` no esta instalado en la `.venv`.
- ChromaDB no esta levantado.
- `CHROMA_HOST=chromadb` se esta usando fuera de Docker Compose. En local deberia apuntar al host donde este corriendo Chroma, normalmente `localhost`.
- Docker no esta instalado o no esta disponible en PATH.

Checks rapidos:

```powershell
.\.venv\Scripts\python.exe -c "import importlib.util; print(importlib.util.find_spec('chromadb') is not None)"
docker --version
```

Resultado esperado actual si no hay Chroma:

```text
False
docker no reconocido o no disponible
```

Para quitar este fallback hay que completar la fase Docker Compose con ChromaDB o instalar y levantar ChromaDB localmente. Solo cambiar `CHROMA_HOST` no basta si no hay cliente Python y servidor Chroma disponibles.
