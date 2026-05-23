# Validacion

## Docker Compose

Validar que la configuracion de Compose es correcta:

```powershell
docker compose config
```

Levantar servicios:

```powershell
docker compose up --build
```

Comprobar backend y documentos:

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/health"
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

## RAG

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

## Evidencia historica

Los informes beta y comparativas anteriores se conservan en
`docs/archive/validation/`. No son el contrato principal del proyecto.
