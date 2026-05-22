# Arquitectura de la POC

## Objetivo

Construir una POC agentic empresarial capaz de responder preguntas de negocio
en lenguaje natural combinando ERP Northwind, una API REST de produccion y
documentos PDF consultables mediante RAG.

La prioridad de la entrega actual es demostrar DeepAgents como framework
principal real, con trazabilidad publica y contrato estable en `POST /api/query`.

## Flujo Principal

```text
Usuario
-> Chainlit o POST /api/query
-> FastAPI
-> AgentRouter
-> mode=deepagent [por defecto]
-> DeepAgentService
-> LangChain DeepAgents
-> tools ERP / Produccion / RAG / Memoria
-> ResponseNormalizer
-> QueryResponse
```

`mode` es opcional en el request. Si falta o llega como `null`, el router usa
siempre `deepagent`.

La solucion utiliza LangChain DeepAgents como framework principal de
orquestacion agentic. El DeepAgent principal interpreta la consulta, recibe
tools de negocio auditables, consulta las fuentes necesarias y devuelve una
respuesta normalizada. LangChain se usa para tools, integracion con modelo y
RAG. LangGraph queda encapsulado solo en el modo experimental/legacy.

## Modos Agentic

- `deepagent`: principal y por defecto. Implementado por
  `app.agents.deep_agent.DeepAgentService` y
  `app.agents.deepagents_tools_service.DeepAgentsToolsQueryService`.
- `deepagent_sidecar`: experimental. DeepAgents delega en el workflow legacy
  para comparativa tecnica.
- `legacy_langgraph`: experimental/comparativo. Conserva el flujo LangGraph
  anterior para regresion y contraste.

Los endpoints `/api/experimental/deepagents/*` son heredados de diagnostico.
No sustituyen al flujo principal y solo se habilitan con
`ENABLE_DEEPAGENTS_EXPERIMENT=true`.

## Componentes

### FastAPI

Expone la API del sistema:

- `GET /health`
- `POST /api/query`
- `POST /api/documents/upload`
- `GET /api/documents`
- `POST /api/experimental/deepagents/query` solo si se habilita el experimento
- `POST /api/experimental/deepagents/tools/query` solo si se habilita el experimento

Las rutas son finas: validan Pydantic, llaman a servicios y devuelven schemas
publicos. La logica agentic vive fuera del endpoint.

### AgentRouter

`app/agents/router.py` selecciona el motor segun `AgentMode`:

- Si `mode is None`, fuerza `AgentMode.DEEPAGENT`.
- Si se pide un modo experimental no disponible, devuelve un error claro.
- Todos los motores pasan por `ResponseNormalizer`.
- La salida publica es siempre `QueryResponse`.

### DeepAgent Principal

`DeepAgentService` encapsula el flujo principal. Internamente usa
`create_deep_agent` desde `deepagents` con `MAIN_DEEP_AGENT_PROMPT` y tools de
negocio:

- `query_erp_orders`
- `query_erp_customer_summary`
- `query_production_status`
- `query_blocked_orders`
- `search_documents`
- `summarize_document_context`

El servicio mantiene una capa determinista de grounding para que los tests
basicos no dependan de un LLM externo y para registrar trazas auditables. Esa
capa no cambia la arquitectura publica: el motor principal que se crea e invoca
en el flujo estable es DeepAgents.

### ResponseNormalizer

`app/services/response_normalizer.py` convierte salidas heterogeneas de
DeepAgents, sidecar o legacy a:

```json
{
  "answer": "...",
  "sources": ["ERP"],
  "reasoning": ["Consulta ERP"],
  "metadata": {
    "agent_mode": "deepagent",
    "agent_framework": "LangChain DeepAgents"
  }
}
```

Tambien conserva campos de auditoria ya existentes: `tool_calls`, `status`,
`data`, `fallbacks`, `confidence` y `failure_reason`. Para modos no principales
anade `metadata.experimental=true`.

### Chainlit

`chainlit_app/main.py` llama al mismo endpoint `POST /api/query` mediante
`BackendClient`. Por defecto envia `mode=deepagent`, usando `AGENT_MODE` solo
como override explicito de desarrollo.

### Tools

Las tools son deterministas, separadas por dominio y devuelven datos
estructurados:

- `ERPTool` y `ERPQueryTool`: clientes, pedidos e importes de Northwind.
- `ProductionAPITool` y `ProductionQueryTool`: estados, bloqueos y retrasos de
  la API REST de produccion.
- `DocumentRAGTool`: busqueda y respuesta grounded sobre PDFs indexados.
- `MemoryTool`: contexto conversacional por `conversation_id`.

La Query DSL segura de `app/tools/query_dsl.py` permite consultas flexibles a
ERP y Produccion con filtros allowlist, sin SQL libre ni rutas HTTP generadas
por el modelo.

## RAG

RAG se implementa como tool, no como agente autonomo:

```text
PDF -> texto -> chunks -> embeddings -> vector store -> retrieval -> respuesta con fuentes
```

Cada chunk conserva `document_id`, `filename`, `page`, `chunk_id` y
`uploaded_at`. Si no hay contexto suficiente, el sistema devuelve
`insufficient_context`.

El vector store objetivo es ChromaDB. El codigo soporta
`CHROMA_MODE=persistent` y `CHROMA_MODE=http`; si Chroma no esta disponible, usa
fallback en memoria para que la POC siga siendo validable.

## Trazabilidad

Cada respuesta debe indicar:

- fuentes consultadas;
- pasos ejecutados;
- tool calls;
- razonamiento visible resumido;
- estado final.

No se expone chain-of-thought interno. `TraceService` registra eventos
auditables y `ResponseNormalizer` reconstruye `sources` y `reasoning` desde
tool calls cuando el agente no los devuelve explicitamente.

## Configuracion

Variables clave:

- `AGENT_MODE=deepagent` por defecto.
- `DEEPAGENTS_MODEL=google_genai:gemini-3.5-flash` o modelo compatible.
- `OPENAI_API_KEY` o `GEMINI_API_KEY` para ejecucion real del DeepAgent.
- `PRODUCTION_API_BASE_URL` para la API REST de produccion.
- `CHROMA_MODE`, `CHROMA_HOST`, `CHROMA_PORT` o `CHROMA_PERSIST_DIRECTORY` para
  ChromaDB.

Docker Compose arranca backend, mock de produccion, Chainlit y ChromaDB con
`AGENT_MODE=deepagent` salvo override explicito.

## Decisiones Tecnicas

- LangChain DeepAgents como framework principal de orquestacion agentic.
- FastAPI para contrato HTTP y separacion de rutas.
- LangChain para tools, modelo y RAG.
- LangGraph solo como implementacion legacy/comparativa.
- ChromaDB como vector store objetivo.
- Pydantic para contratos estables.
- pytest con mocks/datos deterministas para no depender de LLM pagado en tests
  principales.

## Estado Actual

Implementado y cubierto por tests:

- `POST /api/query` usa `AgentRouter` y `deepagent` por defecto.
- Chainlit usa `deepagent` por defecto y reutiliza el endpoint publico.
- Modo principal DeepAgents con tools ERP, Produccion, RAG y Memoria.
- Modos `deepagent_sidecar` y `legacy_langgraph` encapsulados como
  experimentales.
- Response normalizada con `answer`, `sources`, `reasoning` y metadata.
- Upload/listado documental PDF.
- Mock API de produccion.
- ERP Northwind reducido con SQLite en memoria y seed controlado.
- RAG PDF con ChromaDB o fallback en memoria.
- Docker Compose reproducible con backend, mock, Chainlit y ChromaDB.

## Fuera de Alcance Consciente

- Autenticacion avanzada.
- Multi-tenant.
- Observabilidad productiva completa.
- Despliegue cloud.
- Vector stores alternativos.
- Agentes autonomos libres con acceso a filesystem o shell.
- SQL generado libremente por el LLM.
