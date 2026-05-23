# Validacion

## Docker Compose

Validar que la configuracion de Compose es correcta:

```powershell
docker compose config --quiet
```

Levantar servicios:

```powershell
docker compose up --build
```

Comprobar backend y documentos:

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/health"
Invoke-RestMethod -Uri "http://localhost:8000/health/ready"
Invoke-RestMethod -Uri "http://localhost:8000/api/documents"
```

URLs esperadas:

- Backend: `http://localhost:8000`
- API mock de produccion: `http://localhost:8001`
- Chainlit: `http://localhost:8002`
- ChromaDB: `http://localhost:8003`

## Consulta API

```powershell
curl.exe -X POST "http://localhost:8000/api/query" `
  -H "Content-Type: application/json" `
  --data "{""question"":""Que pedidos pendientes tiene el cliente ALFKI y en que estado de produccion estan?""}"
```

La respuesta debe incluir al menos:

- `answer`
- `sources`
- `reasoning`
- `status`

Para usar un modelo real de DeepAgents, configura una clave compatible con
`DEEPAGENTS_MODEL`. En Docker se recomienda `docker-compose.secrets.yml` con
`.secrets/gemini_api_key`. Recuerda que Docker Compose lee `.env` si existe; los
valores locales pueden cambiar `LLM_PROVIDER` o `EMBEDDING_PROVIDER`.
Para la entrega, `EMBEDDING_PROVIDER` debe ser `gemini` u `openai`; el runtime
documental no acepta embeddings deterministas ni vector store en memoria.

## RAG

Los PDFs oficiales de demo son solo los `v2_*` en `data/sample_docs/`.
Para limpiar la coleccion y sembrar esos documentos desde el entorno Python que
ve ChromaDB:

```powershell
.\.venv\Scripts\python.exe scripts\seed_rag.py
```

Subir un PDF de demo:

```powershell
curl.exe -X POST "http://localhost:8000/api/documents/upload" `
  -F "file=@data/sample_docs/v2_anexo_penalizaciones_sla.pdf;type=application/pdf"
```

Consultar por documento:

```powershell
curl.exe -X POST "http://localhost:8000/api/query" `
  -H "Content-Type: application/json" `
  --data "{""question"":""Que dice este documento sobre plazos de entrega?""}"
```

Si no hay documentos indexados o no hay contexto suficiente, el sistema debe
devolver `insufficient_context` o una respuesta controlada, no inventar datos.

## Tests

Suite automatizada:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Tests con LLM real, solo si hay claves configuradas:

```powershell
$env:RUN_REAL_LLM_TESTS="1"
.\.venv\Scripts\python.exe -m pytest -m real_llm -rs
```

Los conteos exactos de tests pueden cambiar al evolucionar el repositorio. Para
la entrega importa que la suite rapida sea determinista y que las pruebas con
proveedor real sean opt-in.

## Informe end-to-end de entrega

La validacion Docker/API de entrega se documenta en `docs/VALIDACION_ENTREGA.md`.
Ese informe ordena primero las preguntas obligatorias del PDF y despues los
casos beta extendidos.

Comando usado para regenerarlo con Docker levantado:

```powershell
.\.venv\Scripts\python.exe scripts\run_delivery_validation.py --output docs\VALIDACION_ENTREGA.md
```

Ese comando limpia primero el indice RAG del backend con
`DELETE /api/documents?confirm=reset-delivery-rag` y despues sube solo los PDFs
`v2_*`. Asi la validacion no depende del estado previo de ChromaDB.

Tambien puede ejecutarse dentro de Compose con el perfil `eval`; el servicio
`evaluator` escribe el informe en `reports/VALIDACION_ENTREGA.md`:

```powershell
docker compose --profile eval up --build evaluator
```

El criterio de cierre es `PASS=18, FAIL=0`.

## Evidencia historica

Los informes beta y comparativas anteriores se conservan en
`docs/archive/validation/`. No son el contrato principal del proyecto.
