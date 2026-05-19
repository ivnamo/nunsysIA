# Arquitectura de la POC

## Objetivo

Construir una POC agentic empresarial capaz de responder preguntas de negocio en lenguaje natural combinando ERP Northwind, una API REST de produccion y documentos PDF consultables mediante RAG.

La prioridad es demostrar integracion real, trazabilidad y control del flujo, no construir una plataforma generica.

## Flujo General

```text
Usuario
-> Chainlit o POST /api/query
-> FastAPI
-> LangGraph StateGraph
-> Planner Agent
-> Reasoner / Executor Agent
-> Validator Node
-> FinalResponseBuilder
-> Respuesta estructurada
```

## LangGraph y LangChain

- LangGraph orquesta el workflow: estado, nodos, edges, validacion y replanning.
- LangChain aporta herramientas: tools, prompts, retrievers, embeddings, parsers y llamadas al LLM.

LangGraph decide el recorrido. LangChain ejecuta capacidades concretas.

## Componentes

### FastAPI

Expone la API del sistema:

- `GET /health`
- `POST /api/query`
- `POST /api/documents/upload`
- `GET /api/documents`

Las rutas deben ser finas y delegar la logica en servicios, tools o el grafo.

### Chainlit

Interfaz conversacional para demo y pruebas manuales. Debe mostrar respuesta, fuentes, reasoning visible, tool calls y estado.

### Planner Agent

Clasifica la intencion de la pregunta y genera un plan estructurado. No ejecuta tools ni inventa datos.

### Reasoner / Executor Agent

Ejecuta el plan usando tools deterministas. Fusiona resultados de ERP, produccion y RAG.

### Validator Node

Comprueba si hay datos suficientes, fuentes requeridas, schema valido y trazabilidad. Puede pedir replanning hasta `MAX_REPLANS = 2`.

### FinalResponseBuilder

Construye la respuesta final con `answer`, `sources`, `reasoning`, `tool_calls`, `status` y `confidence` cuando sea posible.

## Tools

Las tools son deterministas y devuelven datos estructurados:

- `ERPTool`: consulta Northwind.
- `ProductionAPITool`: consulta la API mock de produccion.
- `DocumentRAGTool`: consulta documentos indexados en ChromaDB.
- `MemoryTool`: recupera las ultimas interacciones si existe memoria.

## RAG

RAG se implementa como tool, no como agente autonomo.

Pipeline:

```text
PDF -> texto -> chunks -> embeddings -> ChromaDB -> retrieval -> respuesta con fuentes
```

Cada chunk debe conservar `document_id`, `filename`, `page`, `chunk_id` y `uploaded_at`.

Si no hay contexto documental suficiente, el sistema debe devolver `insufficient_context`.

## Trazabilidad

Cada respuesta debe indicar:

- fuentes consultadas;
- pasos ejecutados;
- tool calls;
- razonamiento visible resumido;
- estado final.

No se debe exponer chain-of-thought interno.

## Decisiones Tecnicas

- FastAPI por simplicidad, rendimiento y ecosistema Python.
- LangGraph para hacer explicito el flujo agentic.
- LangChain para tools y RAG.
- ChromaDB como vector store inicial por velocidad de implementacion.
- Pydantic para contratos estables.
- pytest para pruebas deterministas.
- Docker Compose para reproducibilidad.

## Por Que Encaja con una POC Senior

La arquitectura separa responsabilidades, controla los loops agentic, obliga a trazabilidad y permite probar cada pieza de forma aislada. Es suficientemente expresiva para demostrar criterio senior sin sobredimensionar.

## Fuera de Alcance Consciente

- Autenticacion avanzada.
- Multi-tenant.
- Observabilidad productiva completa.
- Despliegue cloud.
- Vector stores alternativos.
- Agentes autonomos libres.
- SQL generado libremente por el LLM.
