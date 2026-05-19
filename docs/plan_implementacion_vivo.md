# Plan vivo de implementacion - POC agentes IA Nunsys

Fecha de creacion: 2026-05-18
Ultima actualizacion: 2026-05-19

Este documento es la hoja de ruta viva del proyecto. Debe actualizarse al cerrar cada fase con:

- decisiones tomadas o cambiadas;
- tareas completadas;
- pruebas ejecutadas;
- desviaciones respecto al plan;
- riesgos nuevos detectados.

Estado del repositorio al crear la primera version:

- Solo existe documentacion en `docs/`.
- No hay todavia codigo fuente, `README.md`, `Dockerfile` ni `docker-compose.yml`.
- La fuente funcional principal es `docs/Prueba-Tecnica-IA-Agentes.pdf`.

## 1. Objetivo

Construir una POC empresarial de sistema agentic/multi-agente capaz de responder preguntas de negocio en lenguaje natural combinando:

- ERP basado en Northwind.
- Sistema de produccion accesible mediante API REST.
- Documentos PDF indexados mediante RAG.
- API principal `POST /api/query`.
- Interfaz grafica en Chainlit o tecnologia similar.
- Trazabilidad obligatoria de fuentes, pasos, tools y logica seguida.
- Memoria conversacional opcional con al menos las ultimas 5 interacciones.
- Entrega reproducible con codigo fuente, README, Dockerfile y `docker-compose.yml`.

El foco de evaluacion no es que el chat "hable bonito". El foco es demostrar que el sistema consulta fuentes reales de la POC, planifica acciones, ejecuta tools, fusiona resultados, reconoce incertidumbre y deja evidencia auditable de lo que hizo.

## 2. Stack objetivo

### Stack base

- Python.
- FastAPI para APIs.
- Chainlit para UI conversacional.
- Docker Compose para levantar todo.
- PostgreSQL como base empresarial principal.
- Northwind reducido como simulacion de ERP.
- API mock de produccion con FastAPI.
- LangGraph como orquestador principal del flujo agentic.
- LangChain para tools, prompts, retrievers, embeddings, llamadas al LLM y utilidades RAG.
- Pydantic para contratos, estado validado, respuestas estructuradas y planes.

### Stack RAG y evaluacion

- ChromaDB como vector store inicial decidido para la POC.

### Stack de arquitectura y control

- Diagramas C4 para documentar contexto, contenedores y componentes.
- Guardrails eticos y de seguridad:
  - no inventar datos;
  - responder `insufficient_context` cuando falte evidencia;
  - no exponer secretos;
  - no mostrar razonamiento interno completo, solo reasoning resumido/auditable;
  - distinguir datos consultados de inferencias;
  - controlar prompts, uploads y errores.

## 3. Requisitos extraidos del PDF

### Obligatorios

- Responder preguntas en lenguaje natural sobre ERP y produccion.
- Consultar datos ERP: clientes, pedidos e importes.
- Consultar sistema de produccion mediante API REST.
- Combinar informacion de ERP y produccion.
- Subir documentos PDF.
- Indexar documentos en una base vectorial.
- Responder preguntas sobre documentos mediante RAG.
- Exponer `POST /api/query`.
- Devolver respuesta estructurada con `answer`, `sources` y `reasoning`.
- Incluir explicabilidad y trazabilidad en cada respuesta.
- Usar LangChain Deep Agents o un workflow agentic equivalente defendible.
- Incluir interfaz grafica en Chainlit o similar.
- Entregar codigo fuente completo.
- Entregar instrucciones claras de configuracion y ejecucion.
- Entregar `README.md`.
- Entregar `Dockerfile`.
- Entregar `docker-compose.yml`.

### Opcionales, pero recomendados

- Memoria conversacional con al menos las ultimas 5 interacciones.
- Video o demo breve mostrando la aplicacion funcionando.
- Diagramas C4 en `docs/architecture/`.

### Preguntas minimas que debe cubrir

- "Que pedidos pendientes tiene el cliente X y en que estado de produccion estan?"
- "Que pedidos estan bloqueados y cual es el motivo?"
- "Que clientes tienen pedidos retrasados por problemas de produccion?"
- "Dame un resumen del estado de los pedidos de este mes"
- "Que dice este documento sobre plazos de entrega?"
- "Resume los puntos clave del contrato"
- "Hay alguna penalizacion por retrasos?"

## 4. Evaluacion critica de la arquitectura propuesta

### Evaluacion general

La arquitectura propuesta es buena para una prueba senior si se mantiene disciplinada. LangGraph con Planner, Reasoner/Executor y Validator tiene sentido porque el requisito clave es trazabilidad y orquestacion de fuentes, no solo un chatbot. El mayor peligro es convertir una POC de 3 integraciones en una plataforma agentic sobredisenada.

La version defendible debe tener un grafo pequeno, tools deterministas, contratos Pydantic estrictos y trazas claras. No hace falta crear muchos agentes autonomos. Dos roles son suficientes:

- Planner Agent: clasifica intencion y genera plan estructurado.
- Reasoner/Executor Agent: ejecuta tools, fusiona datos y construye respuesta.

El Validator puede ser un nodo determinista, no necesariamente otro agente LLM. Esto reduce coste, latencia, variabilidad y riesgo de loops.

### Partes bien planteadas

- Separar Planner y Reasoner/Executor.
- Usar LangGraph para estado compartido y edges condicionales.
- Mantener las tools deterministas.
- Usar `MAX_REPLANS` para evitar bucles infinitos.
- Tratar RAG como `DocumentRAGTool`, no como tercer agente autonomo.
- Devolver `tool_calls`, `sources`, `reasoning`, `confidence` y `status`.
- Incluir memoria como capability acotada, no como requisito central del MVP.
- Dejar FastAPI como frontera estable entre UI, tests y orquestador.

### Partes sobredimensionadas para una POC

- Meter Planner, Reasoner, Validator LLM, FinalResponseBuilder LLM, memoria, Chainlit, ChromaDB y C4 desde el primer sprint.
- Hacer un sistema multi-agent real con agentes que se llamen entre ellos libremente.
- Cambiar ChromaDB por otro vector store sin permiso.
- Crear un motor generico de planificacion cuando solo hay 4 casos de negocio y RAG documental.

### Riesgos tecnicos

| Riesgo | Impacto | Mitigacion |
| --- | --- | --- |
| Requisito "Deep Agents" interpretado literalmente | Alto | Documentar que LangGraph + LangChain implementa workflow agentic; opcionalmente hacer spike con `deepagents` si el evaluador lo exige |
| Planner genera planes imposibles | Alto | Plan schema Pydantic cerrado y lista fija de actions permitidas |
| El LLM inventa datos | Alto | Tools deterministas, datos estructurados, validator y respuesta `insufficient_context` |
| Loop Planner-Reasoner inestable | Alto | `MAX_REPLANS=2`, failure reasons tipados y salida parcial controlada |
| RAG da contexto irrelevante | Medio | Retrieval top-k, thresholds simples y validacion de contexto |
| ChromaDB no persiste correctamente | Medio | Configurar volumen Docker y pruebas de ingestion/retrieval |
| Chainlit upload complica demo | Medio | Implementar primero upload por API; conectar Chainlit despues |
| Trazabilidad expone datos sensibles | Alto | Sanitizar args, outputs y errores antes de devolverlos |

### Que simplificar para entregar solido

- Un solo grafo LangGraph pequeno.
- Dos agentes conceptuales: Planner y Reasoner/Executor.
- Validator determinista.
- ChromaDB como vector store unico inicial.
- Memoria conversacional simple en memoria o Postgres, limitada a 5 turnos.

### Que mejorar para parecer solucion senior

- Contratos Pydantic estrictos para plan, tool calls, response y state.
- Tools con entradas/salidas JSON, sin texto narrativo.
- Trazabilidad estructurada desde el dia 1 del endpoint.
- Diagramas C4 simples y actualizados.
- Dataset de demo controlado.
- Tests que no dependan del LLM.
- Documentar decisiones y tradeoffs, no solo listar tecnologias.
- Manejar errores parciales: ERP disponible pero produccion caida, PDF sin contexto, cliente inexistente.
- Medir latencia y numero de tool calls por request.

## 5. Decisiones tecnicas defendibles

| ID | Decision | Motivo | Impacto | Estado |
| --- | --- | --- | --- | --- |
| D01 | Backend en Python + FastAPI | Encaja con LangChain, LangGraph, Chainlit y tests | Base simple y evaluable | Decidida |
| D02 | LangGraph como orquestador principal | Modela estado, nodos, edges y replanning de forma explicita | Mayor trazabilidad que un agente libre | Decidida |
| D03 | LangChain para tools, prompts, retrievers y LLM | Ecosistema natural de LangGraph y RAG | Evita construir infraestructura propia | Decidida |
| D04 | Planner + Reasoner/Executor + Validator | Separa planificacion, ejecucion y control de calidad | Evita mezclar razonamiento y llamadas externas | Decidida |
| D05 | Validator determinista inicialmente | Reduce coste y variabilidad | Menos "agentic", mas robusto para POC | Decidida |
| D06 | Pydantic para contratos | Hace planes y respuestas testeables | Menos riesgo de JSON libre roto | Decidida |
| D07 | PostgreSQL + Northwind reducido para ERP | Realista y controlable | Datos previsibles para demo | Decidida |
| D08 | ChromaDB como vector store inicial | Rapido de montar y suficiente para POC documental | Requiere servicio o persistencia en Docker | Decidida |
| D09 | No introducir vector stores alternativos sin permiso | Evita bifurcar arquitectura | Mantiene foco en entrega | Decidida |
| D10 | Guardrails eticos y de seguridad | Evita alucinaciones y exposicion de datos | Requiere validator y prompts estrictos | Decidida |
| D14 | Chainlit como UI | Cumple requisito de interfaz grafica | Demo rapida | Decidida |
| D15 | Docker Compose como experiencia principal | Entrega reproducible | Facilita evaluacion | Decidida |
| D16 | Diagramas C4 en docs | Explica arquitectura de forma senior | No afecta runtime | Recomendada |

## 6. Arquitectura final recomendada

```text
Usuario
  |
  +--> Chainlit UI
  |       |
  |       +--> upload PDF
  |       +--> preguntas NL
  |
  +--> clientes HTTP / curl / tests
          |
          v
FastAPI
  |
  +-- GET  /health
  +-- POST /api/query
  +-- POST /api/documents/upload
  +-- GET  /api/documents
  |
  v
LangGraph Agentic Workflow
  |
  +-- Planner Agent
  |     +-- clasifica intencion
  |     +-- genera Plan Pydantic
  |
  +-- Reasoner / Executor Agent
  |     +-- ejecuta tools deterministas
  |     +-- fusiona resultados
  |
  +-- Validator Node
  |     +-- valida fuentes, trazas, suficiencia y formato
  |
  +-- FinalResponseBuilder
        +-- respuesta estructurada
        +-- confidence
        +-- status

Tools
  |
  +-- ERPTool              -> PostgreSQL / Northwind
  +-- ProductionAPITool    -> FastAPI mock produccion
  +-- DocumentRAGTool      -> PDF chunks + ChromaDB
  +-- MemoryTool           -> ultimas 5 interacciones

Evaluacion y documentacion
  |
  +-- tests pytest
  +-- diagramas C4
```

## 7. Diseno LangGraph

### Nodos recomendados

| Nodo | Tipo | Responsabilidad |
| --- | --- | --- |
| `load_context` | Determinista | Cargar memoria, config y request metadata |
| `planner` | LLM + Pydantic | Clasificar intencion y generar plan cerrado |
| `execute_plan` | LLM controlado + codigo | Ejecutar steps con tools permitidas |
| `validate_result` | Determinista | Validar trazabilidad, fuentes, suficiencia y errores |
| `final_response` | Determinista/LLM controlado | Construir respuesta final estructurada |
| `replan_or_fail` | Determinista | Decidir si replanificar o devolver fallo parcial |
| `save_memory` | Determinista | Guardar ultimas 5 interacciones |

### Estado compartido

Usar `TypedDict` o modelo Pydantic segun convenga. Para la frontera API, Pydantic. Para LangGraph, un `TypedDict` con estructuras validadas antes/despues de nodos es suficiente.

```python
class AgentState(TypedDict):
    question: str
    conversation_id: str | None
    conversation_history: list[dict]
    intent: Literal["erp", "production", "rag", "mixed", "conversation", "unsupported"] | None
    plan: dict | None
    tool_results: list[dict]
    sources: list[str]
    reasoning_trace: list[str]
    tool_calls: list[dict]
    attempts: int
    status: Literal["planning", "executing", "validating", "completed", "partial", "failed"]
    final_answer: str | None
    failure_reason: str | None
    confidence: float | None
```

### Plan Pydantic

```python
class PlanStep(BaseModel):
    step_id: int
    tool: Literal["ERPTool", "ProductionAPITool", "DocumentRAGTool", "MemoryTool"]
    action: str
    args: dict[str, Any]
    required: bool = True

class ExecutionPlan(BaseModel):
    intent: Literal["erp", "production", "rag", "mixed", "conversation", "unsupported"]
    steps: list[PlanStep]
    expected_sources: list[Literal["ERP", "Produccion", "Documentos", "Memoria"]]
    needs_retrieval: bool = False
    answer_requirements: list[str]
```

### Edges recomendados

```text
START
  -> load_context
  -> planner
  -> execute_plan
  -> validate_result

validate_result -- valid --> final_response -> save_memory -> END
validate_result -- invalid and attempts < MAX_REPLANS --> planner
validate_result -- invalid and attempts >= MAX_REPLANS --> final_response -> save_memory -> END
```

### Condiciones de replanning

Replanificar solo si:

- una tool requerida falla y existe una ruta alternativa;
- faltan fuentes obligatorias para la intencion;
- el RAG no supera umbral minimo de contexto pero se puede reformular query;
- el plan no cumple el schema;
- el validator detecta respuesta sin trazabilidad.

No replanificar si:

- el cliente no existe;
- el pedido no existe;
- no hay documentos cargados;
- el usuario pregunta algo fuera de alcance;
- se alcanzo `MAX_REPLANS`.

Valor recomendado:

```python
MAX_REPLANS = 2
```

## 8. Diseno RAG

### Vector store

Decision recomendada: ChromaDB.

Motivo:

- encaja con la arquitectura decidida;
- es rapido de levantar para una POC;
- se integra de forma directa con LangChain;
- permite persistencia local o por volumen Docker.

Plan B:

- No hay plan B tecnico por defecto. Cambiar de vector store requiere permiso explicito.

### Ingestion

Pipeline:

```text
PDF upload
  -> validar extension, MIME y tamano
  -> extraer texto con pypdf
  -> dividir con RecursiveCharacterTextSplitter
  -> generar metadata
  -> embeddings
  -> guardar chunks + embeddings en ChromaDB
```

Metadata minima por chunk:

- `document_id`
- `filename`
- `page`
- `chunk_id`
- `chunk_index`
- `uploaded_at`
- `content_hash`
- `source_type`

### Chunking

Configuracion inicial:

- `chunk_size`: 800-1200 caracteres.
- `chunk_overlap`: 100-200 caracteres.
- Splitter: `RecursiveCharacterTextSplitter`.
- Ajustar despues con pruebas, no por intuicion.

### Retrieval

MVP:

- similarity search top-k en ChromaDB.
- `top_k=5`.
- umbral minimo de similitud.

Version defendible:

- retrieval top-k con metadata completa.
- threshold minimo de relevancia.
- deduplicacion por `chunk_id`.
- contexto final limitado y auditable.

### Validacion de contexto

Antes de responder sobre documentos:

- comprobar que hay chunks;
- comprobar score/umbral minimo;
- comprobar que al menos un chunk tiene contenido directamente relacionado;
- si no hay evidencia suficiente, devolver `status="insufficient_context"`;
- generar respuesta usando solo chunks recuperados;
- incluir paginas/metadatos en `sources` o `citations`.

## 9. Guardrails eticos y de seguridad

Guardrails minimos:

- No inventar clientes, pedidos, importes, estados ni clausulas documentales.
- Si falta evidencia, responder con `insufficient_context` o `partial`.
- No exponer variables de entorno, credenciales ni cadenas de conexion.
- No devolver chain-of-thought interno; devolver `reasoning` resumido y auditable.
- No ejecutar tools fuera de la lista permitida.
- Sanitizar uploads y limitar tamano de PDF.
- Registrar errores sin filtrar datos sensibles.
- Indicar cuando una respuesta es parcial por fallo de una fuente.
- Mantener datos de demo separados de datos reales.

Validator minimo:

```text
Entrada: state
Comprueba:
  - response schema valido
  - sources no vacio
  - tool_calls coherentes con sources
  - reasoning_trace no vacio
  - si intent=rag, citations/context no vacio o insufficient_context
  - si intent=mixed, ERP y Produccion aparecen cuando proceda
Salida:
  - valid=true/false
  - failure_reason
  - can_replan=true/false
```

## 10. Contrato API

### `POST /api/query`

Request:

```json
{
  "question": "Que pedidos pendientes tiene el cliente ALFKI y en que estado de produccion estan?",
  "conversation_id": "demo-001"
}
```

Response recomendada:

```json
{
  "answer": "El cliente ALFKI tiene 2 pedidos pendientes: 10248 esta en fabricacion y 10252 esta bloqueado por falta de material.",
  "sources": ["ERP", "Produccion"],
  "reasoning": [
    "Consulta ERP para pedidos pendientes del cliente ALFKI.",
    "Consulta API de produccion usando los order_ids recuperados.",
    "Fusion de resultados ERP + produccion."
  ],
  "tool_calls": [
    {
      "tool": "ERPTool",
      "action": "get_pending_orders_by_customer",
      "args": {"customer_id": "ALFKI"},
      "status": "success",
      "duration_ms": 35,
      "output_summary": "2 pedidos pendientes"
    },
    {
      "tool": "ProductionAPITool",
      "action": "get_orders_status",
      "args": {"order_ids": ["10248", "10252"]},
      "status": "success",
      "duration_ms": 48,
      "output_summary": "1 en fabricacion, 1 bloqueado"
    }
  ],
  "confidence": 0.86,
  "status": "completed",
  "data": {
    "customer_id": "ALFKI",
    "orders": [
      {
        "order_id": "10248",
        "amount": 440.0,
        "erp_status": "pending",
        "production_status": "in_progress",
        "blocked_reason": null
      },
      {
        "order_id": "10252",
        "amount": 1863.0,
        "erp_status": "pending",
        "production_status": "blocked",
        "blocked_reason": "Falta de material"
      }
    ]
  },
  "failure_reason": null
}
```

Estados permitidos:

- `completed`
- `partial`
- `failed`
- `insufficient_context`
- `unsupported`

### Endpoints

| Endpoint | Obligatorio | Fase | Comentario |
| --- | --- | --- | --- |
| `GET /health` | No, pero necesario | MVP | Healthcheck |
| `POST /api/query` | Si | MVP | Endpoint principal |
| `POST /api/documents/upload` | Si para RAG | Defendible | Upload PDF |
| `GET /api/documents` | Recomendado | Defendible | Listado documentos |
| `POST /api/documents/query` | Opcional | Defendible | Test directo del RAG |

## 11. Estructura de carpetas recomendada

```text
app/
  main.py
  api/
    routes_query.py
    routes_documents.py
  agents/
    planner.py
    reasoner.py
    validator.py
    final_response.py
    state.py
    graph.py
    prompts.py
  tools/
    erp_tool.py
    production_tool.py
    rag_tool.py
    memory_tool.py
  rag/
    loader.py
    splitter.py
    embeddings.py
    vector_store.py
    ingestion.py
  erp/
    database.py
    repositories.py
    schemas.py
  production/
    client.py
    schemas.py
  memory/
    service.py
  core/
    config.py
    logging.py
    tracing.py
    guardrails.py
  schemas/
    query.py
    documents.py
    agent.py
production_mock/
  main.py
  seed.py
chainlit_app/
  app.py
data/
  northwind_seed.sql
  production_seed.json
  sample_docs/
docs/
  architecture/
    c4_context.md
    c4_container.md
    c4_component.md
  plan_implementacion_vivo.md
tests/
  unit/
  integration/
  e2e/
  fixtures/
README.md
Dockerfile
docker-compose.yml
requirements.txt
requirements-dev.txt
.env.example
```

## 12. Datos controlados para demo

### ERP

| customer_id | customer_name | order_id | order_date | erp_status | amount |
| --- | --- | --- | --- | --- | --- |
| ALFKI | Alfreds Futterkiste | 10248 | Mes actual | pending | 440.00 |
| ALFKI | Alfreds Futterkiste | 10252 | Mes actual | pending | 1863.00 |
| ALFKI | Alfreds Futterkiste | 10255 | Mes actual | shipped | 2490.00 |
| ANATR | Ana Trujillo Emparedados | 10301 | Mes actual | pending | 920.00 |
| BONAP | Bon app | 10312 | Mes actual | pending | 1210.00 |

### Produccion

| order_id | production_status | blocked_reason | delay_reason | estimated_finish_date |
| --- | --- | --- | --- | --- |
| 10248 | in_progress | null | null | Fecha + 3 dias |
| 10252 | blocked | Falta de material | null | Fecha + 10 dias |
| 10255 | finished | null | null | Fecha - 1 dia |
| 10301 | delayed | null | Averia en linea de produccion | Fecha + 14 dias |
| 10312 | blocked | Falta de capacidad | null | Fecha + 8 dias |

Regla: los tests deben validar contra estos datos, no contra respuestas generadas libremente.

## 13. Roadmap por fases

### Bloque A - MVP minimo

Objetivo: tener una POC ejecutable que demuestre ERP + produccion + API + trazabilidad.

#### Fase 0 - Base de proyecto

Tareas:

- [ ] Crear estructura de carpetas.
- [ ] Crear `README.md` inicial.
- [ ] Crear `.env.example`.
- [ ] Crear `requirements.txt` y `requirements-dev.txt`.
- [ ] Configurar pytest.
- [ ] Definir version Python.
- [ ] Definir modelos Pydantic base.

Pruebas:

```bash
python --version
pip install -r requirements-dev.txt
pytest
```

Criterio de aceptacion:

- Proyecto instalable.
- Tests ejecutan aunque haya pocos.
- README explica el objetivo y como arrancar.

#### Fase 1 - FastAPI + Docker minimo

Tareas:

- [ ] Implementar `GET /health`.
- [ ] Implementar config por entorno.
- [ ] Implementar logging basico.
- [ ] Crear `Dockerfile`.
- [ ] Crear `docker-compose.yml` con backend.
- [ ] Test de healthcheck.

Pruebas:

```bash
uvicorn app.main:app --reload --port 8000
curl http://localhost:8000/health
docker compose up --build
pytest tests/unit
```

Criterio de aceptacion:

- `/health` responde `200`.
- Backend levanta en local y Docker.

#### Fase 2 - ERP Northwind reducido

Tareas:

- [ ] Anadir Postgres para ERP.
- [ ] Crear `data/northwind_seed.sql`.
- [ ] Crear tablas `customers`, `orders`, `order_details`, `products`.
- [ ] Insertar datos controlados.
- [ ] Implementar repositorios ERP.
- [ ] Implementar `ERPTool`.

Funciones minimas:

- [ ] `get_pending_orders_by_customer(customer_id)`
- [ ] `get_orders_by_month(year, month)`
- [ ] `get_customer_by_order(order_id)`
- [ ] `calculate_order_amount(order_id)`

Pruebas:

```bash
docker compose up postgres
pytest tests/unit/test_erp_repository.py
```

Criterio de aceptacion:

- ALFKI devuelve 2 pedidos pendientes.
- Los importes se calculan desde lineas de pedido.

#### Fase 3 - API mock de produccion

Tareas:

- [ ] Crear `production_mock/main.py`.
- [ ] Crear `data/production_seed.json`.
- [ ] Implementar endpoints de produccion.
- [ ] Implementar cliente HTTP.
- [ ] Implementar `ProductionAPITool`.
- [ ] Manejar timeouts y errores.

Endpoints mock:

- [ ] `GET /production/orders/{order_id}`
- [ ] `GET /production/orders`
- [ ] `GET /production/orders?status=blocked`
- [ ] `GET /production/orders?status=delayed`

Nota: evitar rutas como `/production/orders/blocked` si tambien existe `/production/orders/{order_id}`, salvo que se controle estrictamente el orden de declaracion. Para esta POC es mas claro filtrar por query param.

Pruebas:

```bash
docker compose up production-api
curl http://localhost:8001/production/orders/10252
pytest tests/unit/test_production_client.py
```

Criterio de aceptacion:

- `10252` devuelve `blocked` y motivo.
- `/blocked` devuelve pedidos bloqueados.

#### Fase 4 - LangGraph MVP + `POST /api/query`

Tareas:

- [ ] Crear `AgentState`.
- [ ] Crear `ExecutionPlan` con Pydantic.
- [ ] Crear Planner con intents basicos.
- [ ] Crear Reasoner/Executor con ERPTool y ProductionAPITool.
- [ ] Crear Validator determinista.
- [ ] Implementar `POST /api/query`.
- [ ] Devolver `answer`, `sources`, `reasoning`, `tool_calls`, `confidence`, `status`.
- [ ] Modo test con planner determinista o LLM mock.

Pruebas:

```bash
pytest tests/integration/test_query_endpoint.py
```

Casos minimos:

- [ ] "Que pedidos pendientes tiene el cliente ALFKI?"
- [ ] "Que pedidos pendientes tiene el cliente ALFKI y en que estado de produccion estan?"
- [ ] "Que pedidos estan bloqueados y cual es el motivo?"

Criterio de aceptacion:

- Endpoint obligatorio funciona.
- Hay trazabilidad por cada tool.
- No se inventan datos fuera del seed.

### Bloque B - Version defendible para la prueba

Objetivo: cubrir documentos, UI, memoria simple, diagramas y pruebas suficientes.

#### Fase 5 - RAG con ChromaDB

Tareas:

- [ ] Configurar ChromaDB o persistencia local inicial.
- [ ] Implementar loader PDF.
- [ ] Implementar splitter.
- [ ] Implementar embeddings.
- [ ] Implementar ingestion.
- [ ] Implementar retriever vectorial top-k.
- [ ] Implementar `DocumentRAGTool`.
- [ ] Implementar `POST /api/documents/upload`.
- [ ] Implementar `GET /api/documents`.
- [ ] Integrar RAG en Planner/Reasoner.

Pruebas:

```bash
pytest tests/integration/test_document_upload.py
pytest tests/integration/test_rag_query.py
```

Criterio de aceptacion:

- Se sube PDF.
- Se indexan chunks con metadata.
- Preguntas sobre PDF devuelven fuentes documentales.
- Si no hay contexto, devuelve `insufficient_context`.

#### Fase 6 - Chainlit

Tareas:

- [ ] Crear `chainlit_app/app.py`.
- [ ] Conectar preguntas con `POST /api/query`.
- [ ] Mostrar respuesta, sources, reasoning, tool calls y status.
- [ ] Permitir upload PDF desde UI.
- [ ] Conectar upload con `/api/documents/upload`.
- [ ] Anadir servicio Chainlit a Compose.

Pruebas manuales:

- [ ] Abrir `http://localhost:8501`.
- [ ] Preguntar por ALFKI.
- [ ] Preguntar por bloqueados.
- [ ] Subir PDF.
- [ ] Preguntar por plazos de entrega.

Criterio de aceptacion:

- La demo puede hacerse desde navegador.

#### Fase 7 - Memoria conversacional simple

Tareas:

- [ ] Implementar `MemoryTool`.
- [ ] Guardar ultimas 5 interacciones por `conversation_id`.
- [ ] Pasar resumen al Planner.
- [ ] Resolver referencias simples: "esos pedidos", "cual es el impacto".

Pruebas:

```bash
pytest tests/integration/test_memory.py
```

Criterio de aceptacion:

- Preguntas encadenadas funcionan para casos de demo.

#### Fase 8 - Trazabilidad, guardrails y C4

Tareas:

- [ ] Sanitizar `tool_calls`.
- [ ] Anadir duracion por tool.
- [ ] Anadir `request_id`.
- [ ] Implementar guardrails minimos.
- [ ] Crear `docs/architecture/c4_context.md`.
- [ ] Crear `docs/architecture/c4_container.md`.
- [ ] Crear `docs/architecture/c4_component.md`.
- [ ] Documentar decisiones en README.

Pruebas:

```bash
pytest tests
```

Criterio de aceptacion:

- README y diagramas explican la arquitectura sin depender del codigo.
- Errores comunes son controlados.

### Bloque C - Mejoras opcionales si sobra tiempo

Objetivo: subir calidad sin poner en riesgo la entrega.

#### Fase 9 - Hardening de RAG y Chainlit

Tareas:

- [ ] Ajustar `top_k`.
- [ ] Ajustar thresholds de relevancia.
- [ ] Mejorar mensajes `insufficient_context`.
- [ ] Revisar persistencia de ChromaDB.

Criterio de aceptacion:

- Mejora comportamiento en preguntas documentales dificiles.
- Latencia sigue siendo aceptable para demo.

#### Fase 11 - Demo final y hardening

Tareas:

- [ ] `docker compose down -v`.
- [ ] `docker compose up --build`.
- [ ] Ejecutar tests.
- [ ] Preparar guion demo 3-5 minutos.
- [ ] Grabar video opcional.

Criterio de aceptacion:

- Entrega defendible y reproducible desde cero.

## 14. Tests minimos

### Unitarios

- [ ] ERP repository: pedidos pendientes por cliente.
- [ ] ERP repository: calculo de importes.
- [ ] Production client: estado por pedido.
- [ ] Planner: clasificacion de intenciones con planner fake.
- [ ] Validator: detecta falta de sources/tool_calls.
- [ ] RAG splitter: chunks con metadata.
- [ ] Guardrails: sanitiza secretos y devuelve `insufficient_context`.

### Integracion

- [ ] `GET /health`.
- [ ] `POST /api/query` solo ERP.
- [ ] `POST /api/query` ERP + produccion.
- [ ] `POST /api/query` produccion -> ERP.
- [ ] Upload PDF.
- [ ] Query RAG con contexto suficiente.
- [ ] Query RAG sin contexto suficiente.
- [ ] Memoria conversacional con 2 turnos.

### E2E/manual

- [ ] Demo Chainlit completa.
- [ ] Docker Compose desde cero.
- [ ] Produccion caida: respuesta parcial o error controlado.
- [ ] Cliente inexistente: respuesta clara sin 500.

## 15. Demo de 3-5 minutos

Guion recomendado:

1. Levantar con `docker compose up --build`.
2. Mostrar README y diagrama C4 container en 20 segundos.
3. Abrir Chainlit.
4. Preguntar: "Que pedidos pendientes tiene el cliente ALFKI y en que estado de produccion estan?"
5. Mostrar respuesta, `sources`, `reasoning` y `tool_calls`.
6. Preguntar: "Que pedidos estan bloqueados y cual es el motivo?"
7. Mostrar que consulta produccion y cruza con ERP si procede.
8. Subir un PDF de contrato/condiciones.
9. Preguntar: "Hay alguna penalizacion por retrasos?"
10. Mostrar citas/metadatos o `insufficient_context` si no hay evidencia.
11. Cerrar ensenando tests o comando `pytest`.

Lo que hay que destacar:

- No responde de memoria.
- Llama a tools reales.
- Fusiona ERP + produccion.
- RAG usa chunks recuperados.
- Hay trazabilidad.
- Hay guardrails.
- Se levanta con Docker.

## 16. Errores que se deben evitar

- Presentar muchas tecnologias sin que esten integradas.
- Hacer que el LLM escriba SQL libre contra la base.
- Devolver razonamiento largo tipo chain-of-thought.
- Ocultar errores de tools.
- Responder sobre PDFs sin chunks recuperados.
- Cambiar ChromaDB por otro vector store sin permiso.
- Hacer agentes autonomos que puedan llamar cualquier cosa.
- No tener tests porque "es una POC".
- Dejar el README para el ultimo dia.

## 17. Definition of Done global

La POC se considera terminada cuando:

- [ ] `docker compose up --build` levanta backend, Postgres, ChromaDB, produccion y Chainlit.
- [ ] `POST /api/query` responde con `answer`, `sources`, `reasoning`, `tool_calls`, `confidence`, `status` y `data` cuando aplique.
- [ ] Los 4 casos ERP/produccion del PDF funcionan.
- [ ] Se puede subir un PDF y preguntar sobre su contenido.
- [ ] La UI permite ejecutar la demo completa.
- [ ] Hay tests unitarios e integracion para piezas principales.
- [ ] Hay README con arquitectura, decisiones, dependencias y ejemplos.
- [ ] Hay diagramas C4 basicos.
- [ ] No hay secretos en Git.
- [ ] Los errores comunes estan controlados.
- [ ] El plan vivo queda actualizado con el estado real.

## 18. Proxima accion sugerida

Empezar por el Bloque A, Fase 0 y Fase 1:

- Crear estructura base.
- Crear `README.md`.
- Crear `.env.example`.
- Crear requirements.
- Implementar FastAPI minimo.
- Implementar Docker Compose minimo.
- Dejar `GET /health` testeado.

Primer hito visible:

```bash
docker compose up --build
curl http://localhost:8000/health
pytest
```

Cuando ese hito funcione, seguir con ERP y produccion antes de tocar RAG o Chainlit. Esa secuencia reduce riesgo y permite tener algo demostrable pronto.

## 19. Referencias tecnicas

- LangGraph Graph API: https://docs.langchain.com/oss/python/langgraph/graph-api
- LangGraph use graph API: https://docs.langchain.com/oss/python/langgraph/use-graph-api
- LangChain retrieval: https://docs.langchain.com/oss/python/langchain/retrieval
- FastAPI testing: https://fastapi.tiangolo.com/tutorial/testing/
- Chainlit file upload/config: https://docs.chainlit.io/backend/config/features
