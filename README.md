# nunsysIA

## Descripcion

nunsysIA es una POC de workflow multi-agente para responder consultas de
negocio en lenguaje natural combinando datos de ERP, una API REST de produccion
y documentos PDF indexados mediante RAG.

El objetivo no es sustituir sistemas corporativos reales, sino demostrar una
orquestacion agentic trazable: el sistema consulta fuentes, ejecuta tools,
combina evidencias y devuelve una respuesta con `answer`, `sources` y
`reasoning`.

## Funcionalidades principales

- Consultas sobre ERP/Northwind con clientes, pedidos, estados e importes.
- Consultas sobre API REST de produccion con estados, bloqueos y retrasos.
- Combinacion de fuentes ERP + produccion por `order_id`.
- RAG sobre PDFs subidos e indexados en ChromaDB con embeddings reales.
- Endpoint principal `POST /api/query`.
- Respuestas trazables con `answer`, `sources`, `reasoning`, `tool_calls`,
  `fallbacks`, `status` y `data`.
- Interfaz grafica con Chainlit.
- Ejecucion con Docker y Docker Compose.

## Flujo principal actual

El flujo de entrega es unico y explicito:

```text
Usuario / Chainlit
-> FastAPI POST /api/query
-> AgentRouter
-> mode=deepagent
-> DeepAgentService
-> LangChain DeepAgents + tools de negocio
-> ResponseNormalizer
-> QueryResponse
```

DeepAgents es el modo por defecto real del endpoint de negocio. El servicio
principal puede ejecutar tools deterministas obligatorias antes y despues de la
invocacion agentic para garantizar trazabilidad y evitar respuestas no
grounded; esa logica forma parte del guardrail de entrega, no de un flujo
paralelo.

Componentes reales:

- `app/api/routes_query.py`: endpoint `POST /api/query`.
- `app/api/routes_documents.py`: subida y listado de documentos.
- `app/agents/router.py`: seleccion del modo agentic.
- `app/agents/deep_agent.py`: envoltorio del servicio principal.
- `app/agents/deepagents_tools_service.py`: flujo principal con DeepAgents y
  tools directas de ERP, produccion, RAG y memoria.
- `app/services/response_normalizer.py`: normaliza la salida a `QueryResponse`.
- `app/tools/`: tools deterministas para ERP, produccion, RAG, memoria y Query
  DSL interna.
- `app/rag/`: ingestion, chunking, embeddings, vector store y retrieval.
- `production_mock/`: API REST mock de produccion.
- `chainlit_app/`: interfaz Chainlit conectada al backend.

## Flujos legacy/experimentales

- Flujo principal: `mode=deepagent`. Es el modo por defecto de `/api/query`.
- Flujo alternativo: `mode=deepagent_sidecar`. DeepAgents delega en el workflow
  legacy y se conserva para comparativas.
- Flujo legacy o experimental: `mode=legacy_langgraph`. Mantiene el flujo
  anterior basado en LangGraph para regresion tecnica. No es la arquitectura
  principal de entrega.

Los endpoints `/api/experimental/deepagents/*` estan deshabilitados por defecto
y solo se activan con `ENABLE_DEEPAGENTS_EXPERIMENT=true`.

## Decisiones tecnicas

- LangChain / DeepAgents: se usa como motor principal para que el agente pueda
  decidir y ejecutar tools de negocio en consultas multi-fuente.
- Tools: encapsulan acceso a ERP, produccion, memoria y RAG. Esto evita que el
  agente invente datos o acceda directamente a infraestructura.
- RAG: permite responder preguntas sobre PDFs subidos, con chunks y metadatos
  auditables.
- Vector store: ChromaDB es obligatorio en el runtime de entrega. Si ChromaDB
  no esta disponible, la app falla de forma explicita en lugar de usar memoria.
- Docker: levanta backend, API mock de produccion, Chainlit y ChromaDB con un
  comando reproducible.
- API REST: FastAPI expone un contrato estable para la UI y para consumidores
  externos.
- Separacion por capas: las rutas son finas; la logica vive en servicios,
  agentes, tools y modulos RAG/ERP/produccion.

## Estructura del proyecto

```text
.
|-- app/
|   |-- api/              # Rutas FastAPI
|   |-- agents/           # Router agentic, DeepAgents y flujo legacy
|   |-- core/             # Configuracion, LLM y trazabilidad
|   |-- erp/              # Repositorio Northwind reducido
|   |-- production/       # Cliente y schemas de produccion
|   |-- rag/              # Ingestion, embeddings y vector store
|   |-- schemas/          # Modelos Pydantic publicos
|   |-- services/         # Wiring de servicios y normalizacion
|   `-- tools/            # Tools de negocio
|-- chainlit_app/         # UI conversacional
|-- data/
|   |-- northwind_seed.sql
|   |-- production_seed.json
|   `-- sample_docs/      # PDFs mock de demo
|-- docs/
|   |-- api.md
|   |-- ARCHITECTURE.md
|   |-- validation.md
|   |-- VALIDACION_ENTREGA.md
|   `-- archive/          # Documentacion historica
|-- production_mock/      # API REST mock de produccion
|-- scripts/              # Generacion de PDFs y evaluaciones
|-- tests/                # Unit, integration y e2e
|-- Dockerfile
|-- docker-compose.yml
`-- .env.example
```

## Configuracion

Copia `.env.example` a `.env` para ejecucion local:

```powershell
Copy-Item .env.example .env
```

No se debe commitear `.env`. El archivo ya esta ignorado por `.gitignore`.

Variables principales:

- `AGENT_MODE=deepagent`: modo principal por defecto.
- `PRODUCTION_API_BASE_URL`: URL de la API mock de produccion.
- `CHROMA_MODE`: `persistent` en local o `http` en Docker.
- `CHROMA_HOST`, `CHROMA_PORT`, `CHROMA_COLLECTION`: conexion a ChromaDB.
- `LLM_PROVIDER`: proveedor usado por capas auxiliares y legacy.
- `DEEPAGENTS_MODEL`: modelo usado por DeepAgents.
- `GEMINI_API_KEY` / `OPENAI_API_KEY`: claves locales en `.env`.
- `GEMINI_API_KEY_FILE` / `OPENAI_API_KEY_FILE`: alternativa por archivo para
  Docker o entornos con secretos montados.
- `EMBEDDING_PROVIDER`: `gemini` u `openai` para ejecucion real. El proveedor
  `deterministic` queda limitado a tests unitarios y no se acepta en el factory
  documental de la app.

El `docker-compose.yml` arranca la infraestructura sin publicar secretos. Docker
Compose lee automaticamente `.env` si existe; si ahi configuras proveedores
reales como `gemini` u `openai`, asegurate de definir tambien la clave
correspondiente. Para consultas reales con DeepAgents configura una clave
compatible con `DEEPAGENTS_MODEL`. En Docker, la opcion preferida para Gemini es
crear `.secrets/gemini_api_key` y usar `docker-compose.secrets.yml`.

## Ejecucion con Docker

```powershell
docker compose up --build
```

Servicios:

- Backend FastAPI: `http://localhost:8000`
- API mock de produccion: `http://localhost:8001`
- Chainlit: `http://localhost:8002`
- ChromaDB: `http://localhost:8003`

Validaciones rapidas:

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/health"
Invoke-RestMethod -Uri "http://localhost:8000/health/ready"
Invoke-RestMethod -Uri "http://localhost:8000/api/documents"
```

Con secreto Gemini por archivo:

```powershell
New-Item -ItemType Directory -Force .secrets
# escribe la clave real en .secrets/gemini_api_key sin versionarla
docker compose -f docker-compose.yml -f docker-compose.secrets.yml up --build
```

## Ejecucion local

El repo soporta ejecucion local en Windows/PowerShell:

- `requirements.txt`: dependencias de ejecucion de la app.
- `requirements-dev.txt`: dependencias opcionales de desarrollo y testing. Este
  archivo incluye `requirements.txt`.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Para desarrollo y tests:

```powershell
pip install -r requirements-dev.txt
```

Levantar API mock de produccion:

```powershell
.\.venv\Scripts\python.exe -m uvicorn production_mock.main:app --port 8001
```

Levantar backend:

```powershell
$env:PRODUCTION_API_BASE_URL="http://localhost:8001"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Levantar Chainlit:

```powershell
$env:BACKEND_API_BASE_URL="http://localhost:8000"
.\.venv\Scripts\python.exe -m chainlit run chainlit_app/main.py -w --port 8002
```

## Ejemplos de uso

- Que pedidos pendientes tiene el cliente ALFKI y en que estado de produccion
  estan?
- Que pedidos estan bloqueados y cual es el motivo?
- Que clientes tienen pedidos retrasados por problemas de produccion?
- Dame un resumen del estado de los pedidos de este mes.
- Que dice este documento sobre plazos de entrega?

## API

Endpoint principal:

```http
POST /api/query
Content-Type: application/json
```

Request:

```json
{
  "question": "Que pedidos pendientes tiene el cliente ALFKI y en que estado de produccion estan?"
}
```

Response simplificada:

```json
{
  "answer": "El cliente ALFKI tiene 2 pedidos pendientes: 10248 en curso y 10252 bloqueado por falta de material.",
  "sources": ["ERP", "Produccion"],
  "reasoning": [
    "Consulta ERP para pedidos",
    "Consulta API de produccion",
    "Fusion de resultados"
  ]
}
```

La respuesta real puede incluir tambien `metadata`, `tool_calls`, `fallbacks`,
`confidence`, `status`, `data` y `failure_reason`.

Mas detalle: `docs/api.md`.

## Validacion de entrega

Con Docker levantado y credenciales reales configuradas, ejecuta:

```powershell
.\.venv\Scripts\python.exe scripts\run_delivery_validation.py --output docs\VALIDACION_ENTREGA.md
```

El criterio de entrega es `PASS=18, FAIL=0` sobre las preguntas obligatorias y
extendidas de negocio. Los informes beta anteriores se conservan bajo
`docs/archive/validation/` solo como evidencia historica.

## Trazabilidad y explicabilidad

El sistema devuelve:

- fuentes consultadas en `sources`;
- pasos visibles en `reasoning`;
- tools ejecutadas en `tool_calls`;
- fallbacks usados en `fallbacks`;
- estado final en `status`;
- evidencias publicas resumidas en `data`.

La trazabilidad expone decisiones auditables, no chain-of-thought interno del
modelo. Los logs de backend existen via logging estandar de FastAPI/Uvicorn y
los errores controlados se traducen a estados o codigos HTTP.

## Limitaciones conocidas

- El ERP es un Northwind reducido con seed local, no una integracion ERP real.
- La API de produccion es mock y vive en `production_mock/`.
- El flujo principal DeepAgents necesita una dependencia `deepagents`
  compatible y credenciales del proveedor si se usa un modelo real.
- La memoria conversacional es in-memory por proceso y conserva una ventana
  corta de interacciones.
- RAG depende de PDFs previamente subidos o versionados en `data/sample_docs/`.
- El runtime documental no usa fallback vectorial en memoria ni embeddings
  deterministas; requiere ChromaDB y proveedor real de embeddings.
- No hay autenticacion, autorizacion ni multi-tenant productivo.
- LangGraph sigue en el repo como flujo legacy para comparativa, no como camino
  principal.

## Proximas mejoras

- Conectar ERP y produccion a servicios reales o bases persistentes.
- Persistir memoria conversacional y trazas de ejecucion.
- Anadir autenticacion y control de acceso por usuario.
- Automatizar smoke tests Docker en CI.
- Endurecer observabilidad con logs estructurados y metricas por tool.
- Mejorar evaluacion RAG con fixtures documentales versionadas y criterios de
  relevancia mas estrictos.
