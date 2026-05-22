# Sistema multi-agente con LangChain DeepAgents para consultas ERP, produccion y RAG

Aplicacion FastAPI para responder preguntas de negocio en lenguaje natural combinando:

- ERP/Northwind para clientes, pedidos e importes.
- API REST de produccion para estados, bloqueos y retrasos.
- RAG sobre documentos PDF indexados en base vectorial.
- Interfaz Chainlit.
- Trazabilidad publica de fuentes consultadas, pasos ejecutados y tool calls.

La solucion utiliza LangChain DeepAgents como framework principal de orquestacion agentic. El DeepAgent principal interpreta la consulta, selecciona herramientas, consulta las fuentes necesarias y genera una respuesta trazable. LangChain se utiliza para la definicion de tools, integracion con el modelo y RAG. LangGraph se conserva unicamente como implementacion experimental/legacy para comparacion tecnica y no forma parte del flujo principal por defecto.

## Arquitectura

```text
POST /api/query
  -> AgentRouter
      -> mode=deepagent          [principal y por defecto]
      -> mode=deepagent_sidecar  [experimental]
      -> mode=legacy_langgraph   [experimental/comparativo]
  -> ResponseNormalizer
  -> QueryResponse
```

Componentes principales:

- `app/api/routes_query.py`: endpoint fino `POST /api/query`.
- `app/agents/router.py`: selecciona el motor agentic.
- `app/agents/deep_agent.py`: servicio principal con LangChain DeepAgents.
- `app/agents/deepagents_tools_service.py`: DeepAgent con tools de ERP, produccion, memoria y RAG.
- `app/agents/sidecar_agent.py`: modo experimental DeepAgents sidecar sobre legacy.
- `app/agents/legacy_langgraph_agent.py`: modo experimental LangGraph legacy.
- `app/services/response_normalizer.py`: normaliza cualquier salida a `QueryResponse`.
- `app/services/trace_service.py`: registra fuentes, acciones y pasos auditables.
- `chainlit_app/main.py`: UI Chainlit conectada al mismo `/api/query`.

## Flujo principal

1. El cliente envia una pregunta a `POST /api/query`.
2. `AgentRouter` usa `mode=deepagent` si no se especifica otro modo.
3. El DeepAgent decide que tools ejecutar:
   - `query_erp_orders`
   - `query_erp_customer_summary`
   - `query_production_status`
   - `query_blocked_orders`
   - `search_documents`
   - `summarize_document_context`
4. Las tools devuelven datos estructurados y trazables.
5. `ResponseNormalizer` garantiza el contrato publico:

```json
{
  "answer": "...",
  "sources": ["ERP", "Produccion", "Documentos"],
  "reasoning": ["Consulta ERP", "Consulta API de produccion"],
  "metadata": {
    "agent_mode": "deepagent",
    "agent_framework": "LangChain DeepAgents"
  }
}
```

La respuesta puede incluir campos adicionales de auditoria ya existentes, como `tool_calls`, `status`, `data`, `fallbacks` y `confidence`.

## Endpoint

`POST /api/query`

Request:

```json
{
  "question": "Que pedidos pendientes tiene ALFKI y en que estado de produccion estan?",
  "conversation_id": "demo-001",
  "mode": "deepagent"
}
```

`mode` es opcional. Si falta o es `null`, se usa siempre `deepagent`.

Response:

```json
{
  "answer": "El cliente ALFKI tiene pedidos pendientes...",
  "sources": ["ERP", "Produccion"],
  "reasoning": [
    "Consulta ERP de pedidos pendientes",
    "Consulta API de produccion para pedidos referenciados"
  ],
  "metadata": {
    "agent_mode": "deepagent",
    "agent_framework": "LangChain DeepAgents"
  },
  "status": "completed"
}
```

## Modos agentic

- `deepagent`: principal y por defecto. Usa LangChain DeepAgents con tools directas de negocio.
- `deepagent_sidecar`: experimental. DeepAgents delega en el workflow legacy como sidecar para comparativa.
- `legacy_langgraph`: experimental/comparativo. Conserva el flujo LangGraph anterior para regresion tecnica.

LangGraph puede seguir apareciendo en codigo y documentacion historica como runtime interno o legacy, pero no es la arquitectura principal de entrega.

Los endpoints `/api/experimental/deepagents/*` son endpoints heredados de diagnostico y comparativa. La entrega principal no los necesita: el DeepAgent productivo entra por `POST /api/query` con `mode=deepagent`.

## Configuracion

Copia `.env.example` a `.env` para ejecucion local:

```env
AGENT_MODE=deepagent
LLM_PROVIDER=deterministic
DEEPAGENTS_MODEL=google_genai:gemini-3.5-flash
PRODUCTION_API_BASE_URL=http://localhost:8001
CHROMA_MODE=persistent
CHROMA_PERSIST_DIRECTORY=data/chroma
EMBEDDING_PROVIDER=deterministic
```

Para usar Gemini u OpenAI:

```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=tu_clave_local
GEMINI_MODEL=gemini-2.5-flash

# o bien
LLM_PROVIDER=openai
OPENAI_API_KEY=tu_clave_local
OPENAI_MODEL=gpt-4o-mini
```

No versiones secretos reales. En Docker, usa `docker-compose.secrets.yml` y archivos en `.secrets/`.

## Ejecucion local

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
pip install -r requirements-chroma.txt
```

Levantar la API mock de produccion:

```powershell
.\.venv\Scripts\python.exe -m uvicorn production_mock.main:app --port 8001
```

Levantar backend:

```powershell
$env:AGENT_MODE="deepagent"
$env:PRODUCTION_API_BASE_URL="http://localhost:8001"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --reload-dir app --port 8000
```

Probar `/api/query`:

```powershell
curl.exe -X POST http://localhost:8000/api/query `
  -H "Content-Type: application/json" `
  --data "{""question"":""Que pedidos pendientes tiene ALFKI y en que estado de produccion estan?""}"
```

Verificar que usa DeepAgents por defecto:

- No envies `mode` en el request.
- Revisa `metadata.agent_mode`: debe ser `deepagent`.
- Revisa `metadata.agent_framework`: debe ser `LangChain DeepAgents`.

## Chainlit

Chainlit llama al mismo endpoint `/api/query` y envia `AGENT_MODE=deepagent` por defecto.

```powershell
$env:BACKEND_API_BASE_URL="http://localhost:8000"
$env:AGENT_MODE="deepagent"
Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
.\.venv\Scripts\python.exe -m chainlit run chainlit_app/main.py -w --port 8002
```

UI: `http://localhost:8002`

Puedes adjuntar PDFs desde Chainlit. El backend los indexa mediante `POST /api/documents/upload` y quedan disponibles para preguntas RAG.

## Docker

```powershell
docker compose up --build
```

Servicios:

- Backend FastAPI: `http://localhost:8000`
- Production mock API: `http://localhost:8001`
- Chainlit UI: `http://localhost:8002`
- ChromaDB HTTP: `http://localhost:8003`

El compose arranca con:

```env
AGENT_MODE=deepagent
LLM_PROVIDER=deterministic
EMBEDDING_PROVIDER=deterministic
```

No arranca en `legacy_langgraph` salvo que lo fuerces explicitamente para desarrollo.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest
```

La suite principal usa mocks/datos deterministas y valida el flujo `deepagent`. Los tests con LLM real siguen siendo opt-in si se habilitan por variable de entorno.

## Documentos de apoyo

- `docs/ARCHITECTURE.md`
- `docs/API_CONTRACT.md`
- `docs/TRACEABILITY.md`
- `docs/MANUAL_VALIDATION.md`
- `docs/DEMO_SCRIPT.md`
- `docs/DEEPAGENTS_COMPARISON_REPORT.md`
