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

Interfaz conversacional para demo y pruebas manuales. Muestra respuesta, fuentes, reasoning visible, tool calls y estado. Permite adjuntar PDFs al espacio documental del backend y listar documentos con `/documentos`.

### Planner Agent

Clasifica la intencion de la pregunta y genera un plan estructurado. En la fase actual es hibrido: puede usar Gemini/OpenAI si estan configurados, pero solo acepta planes que cumplan el schema Pydantic y una lista cerrada de tools/actions. Si el LLM falla, tarda demasiado o propone una accion no permitida, cae al planner determinista. No ejecuta tools ni inventa datos.

### Reasoner / Executor Agent

Ejecuta el plan usando tools deterministas. Fusiona resultados de ERP, produccion y RAG.

### Validator Node

Comprueba si hay datos suficientes, fuentes requeridas, schema valido y trazabilidad. Puede pedir replanning hasta `MAX_REPLANS = 2`.

### FinalResponseBuilder

Construye la respuesta final con `answer`, `sources`, `reasoning`, `tool_calls`, `fallbacks`, `status` y `confidence` cuando sea posible. Los fallbacks no deben ocultarse: si el planner cae a reglas, si la respuesta final cae a determinista, si ChromaDB no esta disponible o si se usan embeddings deterministas, debe quedar visible.

En el estado actual puede usar LLM controlado para redactar en espanol de negocio solo sobre datos ya devueltos por tools. Si el LLM falla, tarda demasiado o introduce identificadores/numeros que no aparecen en las evidencias, se descarta y se usa la respuesta determinista.

## Tools

Las tools son deterministas y devuelven datos estructurados:

- `ERPTool`: consulta Northwind.
- `ProductionAPITool`: consulta la API mock de produccion.
- `DocumentRAGTool`: consulta documentos indexados en el vector store documental.
- `MemoryTool`: previsto para recuperar las ultimas interacciones; todavia no esta implementado como memoria conversacional completa.

## RAG

RAG se implementa como tool, no como agente autonomo.

Pipeline:

```text
PDF -> texto -> chunks -> embeddings -> vector store -> retrieval -> respuesta con fuentes
```

Cada chunk debe conservar `document_id`, `filename`, `page`, `chunk_id` y `uploaded_at`.

Si no hay contexto documental suficiente, el sistema debe devolver `insufficient_context`.

El vector store objetivo es ChromaDB. En local, si ChromaDB no esta instalado o no responde, la app usa un fallback en memoria para que la POC siga siendo validable sin Docker.

La fase actual devuelve documentos usados en `data.rag.documents`; las citas visibles por chunk con `filename`, `page`, `chunk_id` y `score` son la siguiente mejora P9.

## LLM y proveedores

- Proveedor por defecto para pruebas reales: Gemini.
- Modelo Gemini actual configurado: `gemini-2.5-flash`.
- OpenAI queda soportado por variables de entorno sin cambiar el grafo ni las tools.
- Los tests basicos no dependen de llamadas pagadas.
- El Planner y el FinalResponseBuilder tienen timeout y retries desactivados para evitar bloqueos largos por modelos invalidos.

## Configuracion de base de datos

- El backend lee `ERP_DATABASE_URL` para la base ERP.
- `DATABASE_URL` no debe usarse para el ERP en local, porque Chainlit la reserva para su propio data layer con `asyncpg`.
- `DATABASE_URL` queda soportada solo como fallback legacy en `app.core.config`.

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

## Estado Actual de Implementacion

Implementado y validado manualmente:

- FastAPI con endpoints principales.
- Mock API de produccion.
- ERP Northwind reducido con SQLite local y seed controlado.
- LangGraph con Planner, Reasoner/Executor, Validator y FinalResponseBuilder.
- RAG PDF con documentos mock de demo.
- Chainlit con subida de PDFs.
- Trazabilidad estructurada y sanitizada.
- Planner hibrido con LLM opcional.
- Respuesta final con LLM controlado y fallback determinista.

Pendiente para cierre de producto:

- memoria conversacional de 5 interacciones;
- citas documentales visibles por chunk;
- Docker Compose completo.

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
