# Plan de implementacion vivo

Este documento convierte la auditoria tecnica en un plan de refactor incremental.
La idea es avanzar por fases pequenas, validar cada fase con tests y cerrar cada
bloque con un commit unico y defendible.

Para el historico de construccion por fases, ver `docs/TASK_PLAN.md`.

## Estado base

Fecha base: 2026-05-21.

La POC tiene **P9 cerrada a nivel funcional**. El siguiente bloque de entrega
sigue siendo **P10 - Docker Compose**, pero antes conviene reducir riesgos
arquitectonicos detectados en auditoria.

Estado declarado y versionado:

- Flujo LangGraph real: Planner -> Reasoner/Executor -> Validator -> FinalResponseBuilder.
- Backend FastAPI con `GET /health`, `POST /api/query`, `POST /api/documents/upload` y `GET /api/documents`.
- ERP Northwind reducido con SQLite en memoria.
- API mock de produccion en `production_mock/`.
- RAG documental con ChromaDB como objetivo y fallback en memoria.
- Chainlit como UI de demo.
- Memoria conversacional in-memory de 5 turnos por `conversation_id`.
- Trazabilidad publica con fuentes, pasos, tool calls, fallbacks, estado, confianza y `data`.
- Suite automatizada declarada: `124 passed, 2 warnings`.

## Objetivo del refactor

Endurecer la POC sin cambiar el stack ni sustituir el flujo agentic aprobado.

No se busca reescribir el proyecto. Se busca:

- cerrar riesgos que un experto preguntaria en revision oral;
- reducir hotspots (`planner.py`, `final_response.py`, `rag_tool.py`);
- mantener respuestas trazables;
- sostener cada cambio con tests;
- hacer commits pequenos, reversibles y con sentido tecnico.

## Reglas de trabajo por fase

Cada fase debe seguir este protocolo:

1. Revisar alcance y archivos permitidos.
2. Ejecutar tests focalizados antes si el cambio es delicado.
3. Implementar el minimo cambio necesario.
4. Ejecutar tests focalizados.
5. Ejecutar validacion beta con LLM real cuando la fase cambie comportamiento visible.
6. Ejecutar `pytest` completo antes de cerrar fases criticas o antes de demo.
7. Actualizar documentacion si cambia contrato, trazabilidad o validacion manual.
8. Hacer un commit unico con mensaje claro.

Formato sugerido de commit:

```text
tipo(area): descripcion breve
```

Ejemplos:

```text
fix(agents): enforce document evidence in mixed plans
refactor(final-response): extract penalty policy
test(rag): cover mixed insufficient context
docs(demo): update validation checklist
```

## Estados

Usar estos estados para mantener vivo este documento:

- `pendiente`: no iniciado.
- `en curso`: hay cambios locales o fase abierta.
- `validado`: tests focalizados pasan.
- `cerrado`: commit realizado.
- `pospuesto`: deuda aceptada con motivo.

## Validacion beta con LLM real

Los tests automatizados siguen siendo obligatorios, pero no sustituyen la beta
con LLM y embeddings reales. La prueba tecnica se defiende por comportamiento
visible, calidad de retrieval, grounding y trazabilidad, asi que
`docs/BETA_VALIDATION_REPORT.md` forma parte del criterio de aceptacion.

Regla general:

- `pytest` protege contratos, regresiones y determinismo.
- La beta real valida planner LLM, final response LLM, embeddings externos,
  Chroma persistente, ranking documental y salida visible en Chainlit.
- Los tests basicos no deben depender de LLM pagados.
- Las pasadas beta usan `.env` local autorizado segun `docs/MANUAL_VALIDATION.md`.
- No se documentan secretos, tokens ni valores de entorno sensibles.

### Niveles de beta

| Nivel | Cuando se ejecuta | Casos minimos | Evidencia |
|---|---|---|---|
| `BT-smoke` | Despues de cada fase que toque planner, validator, final response, RAG o tools | 1 ERP+produccion, 1 RAG, 1 mixta, 1 guardrail | Resumen en el registro vivo o en `BETA_VALIDATION_REPORT.md` si cambia respuesta visible |
| `BT-parcial` | Antes de cerrar R1, R4, R7 y R10 | BT-05 a BT-10 + BT-V2-LLM-02/03/06/07 | Nueva iteracion en `BETA_VALIDATION_REPORT.md` |
| `BT-completa` | Antes de demo final o entrega | BT-01 a BT-11 + BT-V2-LLM-01 a BT-V2-LLM-07 | Informe completo actualizado |

### Configuracion beta esperada

- `LLM_PROVIDER=gemini` u otro proveedor real configurado y autorizado.
- `EMBEDDING_PROVIDER=gemini` u otro proveedor real configurado y autorizado.
- `LLM_TEMPERATURE=0`.
- `LLM_TIMEOUT_SECONDS=45` salvo motivo documentado.
- Chroma persistente con coleccion aislada por fase, por ejemplo:
  `beta_validation_YYYYMMDD_R1_HHMMSS`.
- PDFs seed de `data/sample_docs/`, incluyendo `v2_*.pdf` para validar
  retrieval multipagina.

### Casos smoke obligatorios

Estos cuatro casos se repiten tras cambios de comportamiento visible:

1. ERP + produccion: `Que pedidos pendientes tiene el cliente ALFKI y en que estado de produccion estan?`
2. RAG documental: `Hay alguna penalizacion por retrasos?`
3. Mixto ERP + produccion + RAG: pregunta de penalizaciones con pedido/cliente y causa de produccion.
4. Guardrail: pregunta ajena al dominio o documental sin evidencia, como receta de cocina vegana.

### Criterio de parada

- Un `FAIL` en guardrail, trazabilidad, respuesta mixta o RAG documental bloquea
  el commit funcional hasta corregirlo.
- Un `PARTIAL` puede documentarse durante refactor interno, pero no debe quedar
  en la beta final si afecta a los casos de demo.
- Si aparece fallback en una pasada que esperaba proveedor real, se investiga y
  se documenta la causa antes de cerrar la fase.
- Si el fallo se debe a proveedor externo intermitente, se repite una vez con
  coleccion nueva y se registra el resultado.

### Registro minimo por pasada beta

Cada iteracion real debe anotar en `docs/BETA_VALIDATION_REPORT.md`:

- fecha, fase y commit o rama evaluada;
- proveedor/modelo LLM y proveedor/modelo de embeddings;
- modo Chroma y nombre de coleccion;
- documentos cargados y numero de chunks;
- PASS/PARTIAL/FAIL por caso;
- respuesta visible resumida o completa para fallos y parciales;
- citas, fallbacks, `status`, `sources`, `tool_calls` y `failure_reason`;
- decision: continuar, corregir o aceptar deuda consciente.

## Roadmap de fases

| Fase | Estado | Objetivo | Riesgo que reduce | Commit sugerido |
|---|---|---|---|---|
| R0 | en curso | Crear este plan vivo | Evitar refactor improvisado | `docs(refactor): add phased implementation plan` |
| R1 | validado en tests / beta pendiente | Guardrail documental en planes mixtos | Responder penalizaciones sin evidencia RAG | `fix(agents): enforce document evidence in mixed plans` |
| R2 | validado en tests / beta pendiente | Planner sin defaults silenciosos | Responder ALFKI cuando falta cliente | `fix(planner): avoid implicit customer defaults` |
| R3 | validado en tests / beta pendiente | Trazabilidad de actions y fallbacks | Tool calls poco explicitas | `fix(traceability): expose tool actions consistently` |
| R4 | pendiente | Extraer politica de penalizaciones | Logica documental hardcodeada en builder | `refactor(final-response): extract penalty policy` |
| R5 | pendiente | Dividir FinalResponseBuilder | God object de respuesta final | `refactor(final-response): split answer builders` |
| R6 | pendiente | Dividir Planner | God object de planificacion | `refactor(planner): split rule planner from llm planner` |
| R7 | pendiente | Dividir DocumentRAGTool | Tool demasiado amplia | `refactor(rag): extract relevance and answer building` |
| R8 | pendiente | Endurecer upload PDF | Parser multipart manual fragil | `refactor(api): use uploadfile for pdf ingestion` |
| R9 | pendiente | Trazabilidad de replanning | Se pierde historia de intentos | `feat(agents): retain replan attempt traces` |
| R10 | validado en Docker / beta parcial pendiente | Docker Compose | P10 pendiente | `feat(runtime): add docker compose stack` |
| R11 | pendiente | Guion demo y cierre | Demo no completamente paquetizada | `docs(demo): add final review script` |

## Fase R1 - Guardrail documental en planes mixtos

Prioridad: **antes de demo**.

Problema:

- `ValidatorNode` trata `data.rag.status == insufficient_context` solo cuando `plan.intent == "rag"`.
- En un plan `mixed`, una consulta documental insuficiente puede quedar como fuente consultada y permitir respuesta final.
- `FinalResponseBuilder._answer_order_penalties()` puede responder penalizaciones aunque la evidencia documental no sea suficiente.

Archivos previstos:

- `app/agents/validator.py`
- `app/agents/final_response.py`
- `tests/unit/test_validator.py`
- `tests/integration/test_agent_graph.py`

Cambio esperado:

- Si un plan requiere `Documentos` y `data.rag.status == insufficient_context`, devolver estado controlado.
- No construir respuesta de penalizaciones si falta evidencia documental util.
- Mantener `tool_calls`, `sources`, `fallbacks` y `failure_reason` visibles.

Tests minimos:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_validator.py
.\.venv\Scripts\python.exe -m pytest tests\integration\test_agent_graph.py
```

Beta real:

- Ejecutar `BT-parcial` porque esta fase toca el guardrail mixto mas sensible.
- Casos obligatorios: BT-08, BT-10, BT-V2-LLM-02, BT-V2-LLM-03, BT-V2-LLM-06 y BT-V2-LLM-07.
- Registrar coleccion Chroma aislada y fallbacks en `docs/BETA_VALIDATION_REPORT.md`.

Criterio de aceptacion:

- RAG puro sigue devolviendo `insufficient_context`.
- Mixto ERP + Produccion + Documentos no completa penalizaciones si RAG no aporta contexto.
- Casos positivos de penalizaciones siguen pasando cuando hay documento valido.
- Beta real sin `FAIL` en mixto, RAG documental ni guardrails.

Estado 2026-05-21:

- Implementado en `app/agents/validator.py` con deteccion de planes que requieren contexto documental, tambien si `intent == mixed`.
- Agregadas regresiones en `tests/unit/test_validator.py` y `tests/integration/test_agent_graph.py`.
- Validado con pytest focalizado:
  - `tests/unit/test_validator.py`: 6 passed.
  - `tests/integration/test_agent_graph.py`: 11 passed, 1 warning externa de LangGraph.
- Pendiente antes de cerrar fase: `BT-parcial` con LLM real y registro en `docs/BETA_VALIDATION_REPORT.md`.

## Fase R2 - Planner sin defaults silenciosos

Prioridad: **antes de demo**.

Problema:

- `PlannerAgent` usa `ALFKI` por defecto cuando detecta pedidos pendientes sin cliente explicito.
- En demo es comodo, pero en revision puede interpretarse como dato inventado.

Archivos previstos:

- `app/agents/planner.py`
- `tests/unit/test_planner.py`
- `tests/integration/test_query_endpoint.py`

Cambio esperado:

- Si la pregunta requiere cliente y no hay `customer_id` explicito ni memoria que lo resuelva, devolver `unsupported` o pedir concrecion en la respuesta final.
- Mantener los casos de demo con `ALFKI` explicito.
- Marcar como fallback visible el planner determinista cuando no hay LLM, tambien para rutas especiales.

Tests minimos:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_planner.py
.\.venv\Scripts\python.exe -m pytest tests\integration\test_query_endpoint.py
```

Beta real:

- Ejecutar `BT-smoke`.
- Incluir memoria conversacional si se toca resolucion por contexto: BT-09A, BT-09B y BT-09C.
- Verificar que una pregunta sin cliente explicito no queda maquillada como ALFKI salvo que la memoria lo soporte.

Criterio de aceptacion:

- `Que pedidos pendientes tiene el cliente ALFKI?` funciona.
- `Que pedidos pendientes tiene el cliente?` no asume ALFKI.
- Follow-ups con memoria siguen resolviendo cliente desde `conversation_id`.

Estado 2026-05-21:

- Eliminado el default silencioso a `ALFKI` en reglas deterministas del planner.
- Eliminado el default silencioso a `ALFKI` al normalizar planes LLM con `customer_id` ausente o invalido.
- La respuesta final `unsupported` pide cliente concreto o contexto conversacional previo.
- Agregadas regresiones en `tests/unit/test_planner.py` y `tests/integration/test_query_endpoint.py`.
- Validado con pytest focalizado:
  - `tests/unit/test_planner.py`: 15 passed.
  - `tests/integration/test_query_endpoint.py`: 7 passed, 1 warning externa de LangGraph.
  - `tests/integration/test_agent_graph.py`: 11 passed, 1 warning externa de LangGraph.
- Pendiente antes de cerrar fase: `BT-smoke` con LLM real.

## Fase R3 - Trazabilidad de actions y fallbacks

Prioridad: **quick win antes de demo**.

Problema:

- Varias tools dejan `tool_calls.action = null` aunque el plan ejecuta acciones concretas.
- El fallback a Chroma/embeddings se ve, pero la causa tecnica queda poco explicita para diagnostico.

Archivos previstos:

- `app/tools/erp_tool.py`
- `app/tools/production_tool.py`
- `app/tools/rag_tool.py`
- `app/core/traceability.py`
- `tests/unit/test_erp_tool.py`
- `tests/unit/test_production_tool.py`
- `tests/unit/test_rag_tool.py`
- `tests/unit/test_traceability.py`

Cambio esperado:

- Propagar `action` en todas las tool calls relevantes.
- Mantener argumentos sanitizados.
- No exponer secretos ni errores raw.

Tests minimos:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_erp_tool.py tests\unit\test_production_tool.py tests\unit\test_rag_tool.py tests\unit\test_traceability.py
```

Beta real:

- Ejecutar `BT-smoke`.
- Revisar en Chainlit que `tool_calls` muestre tool y accion de forma auditable.
- Registrar cualquier cambio visible en `docs/BETA_VALIDATION_REPORT.md`.

Criterio de aceptacion:

- `tool_calls` permite auditar tool + action sin depender solo de `output_summary`.
- Chainlit muestra labels como `ERPTool.get_pending_orders_by_customer` cuando aplique.

Estado 2026-05-21:

- `ERPTool`, `ProductionAPITool`, `DocumentRAGTool` y `MemoryTool` declaran `tool_call.action`.
- `ReasonerExecutorAgent` completa `action` desde el `PlanStep` cuando una tool o skipped no lo aporta.
- Agregadas/regresadas aserciones de `action` en tests de tools, endpoint y grafo.
- Validado con pytest focalizado:
  - `tests/unit/test_erp_tool.py tests/unit/test_production_tool.py tests/unit/test_rag_tool.py tests/unit/test_memory_tool.py tests/unit/test_traceability.py`: 25 passed.
  - `tests/integration/test_query_endpoint.py`: 7 passed, 1 warning externa de LangGraph.
  - `tests/integration/test_agent_graph.py`: 11 passed, 1 warning externa de LangGraph.
- Pendiente antes de cerrar fase: `BT-smoke` con LLM real y revision visual en Chainlit.

## Fase R4 - Extraer politica de penalizaciones

Prioridad: **antes de una revision exigente**.

Problema:

- `FinalResponseBuilder._penalty_assessment()` mezcla redaccion final con reglas de negocio documentales.
- Un experto puede preguntar por que una clausula documental esta hardcodeada en el builder.

Archivos previstos:

- Nuevo modulo posible: `app/agents/penalty_policy.py`
- `app/agents/final_response.py`
- `tests/unit/test_final_response.py`
- Nuevo test posible: `tests/unit/test_penalty_policy.py`

Cambio esperado:

- Extraer una politica pequena y testeable.
- Hacer explicita la entrada: pedidos ERP, estados de produccion y evidencia RAG.
- Si no hay evidencia documental suficiente, no calcular penalizacion.

Tests minimos:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_final_response.py
.\.venv\Scripts\python.exe -m pytest tests\integration\test_agent_graph.py
```

Beta real:

- Ejecutar `BT-parcial`.
- Casos obligatorios: BT-07, BT-08, BT-V2-LLM-02, BT-V2-LLM-03 y BT-V2-LLM-06.
- Verificar que la redaccion final no calcula ni sugiere penalizacion sin evidencia documental suficiente.

Criterio de aceptacion:

- La respuesta mixta sigue funcionando para el caso demo.
- La politica no depende de memoria del modelo.
- Las reglas documentales quedan aisladas y explicables.
- Beta real sin `PARTIAL` en impacto economico y trazabilidad.

## Fase R5 - Dividir FinalResponseBuilder

Prioridad: **post guardrails, antes de hardening final**.

Problema:

- `app/agents/final_response.py` concentra redaccion determinista, prompt final, validacion de grounding, sanitizacion auxiliar y reglas de negocio.

Archivos previstos:

- `app/agents/final_response.py`
- Modulos nuevos posibles:
  - `app/agents/final_answer_templates.py`
  - `app/agents/final_grounding.py`
  - `app/agents/final_prompt.py`

Cambio esperado:

- Refactor sin cambio de comportamiento.
- Mantener `FinalResponseBuilder` como fachada del nodo LangGraph.
- Extraer funciones puras testeables.

Tests minimos:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_final_response.py
.\.venv\Scripts\python.exe -m pytest tests\integration\test_agent_graph.py
```

Beta real:

- Ejecutar `BT-smoke` si cambia cualquier salida visible.
- Si el refactor es mecanico y los snapshots/respuestas no cambian, basta con dejarlo documentado en el registro vivo.

Criterio de aceptacion:

- Mismos outputs en tests existentes.
- Menos responsabilidades por archivo.
- Ningun cambio de contrato API.

## Fase R6 - Dividir Planner

Prioridad: **post guardrails**.

Problema:

- `app/agents/planner.py` concentra schema, prompt, parser JSON, planner LLM, planner por reglas, memoria y normalizacion de args.

Archivos previstos:

- `app/agents/planner.py`
- Modulos nuevos posibles:
  - `app/agents/plan_models.py`
  - `app/agents/rule_planner.py`
  - `app/agents/llm_planner.py`
  - `app/agents/plan_normalization.py`

Cambio esperado:

- Mantener `PlannerAgent` como fachada del nodo.
- Extraer reglas deterministas y modelos Pydantic.
- Mantener lista cerrada de tools/actions.

Tests minimos:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_planner.py
.\.venv\Scripts\python.exe -m pytest tests\integration\test_agent_graph.py
```

Beta real:

- Ejecutar `BT-smoke`.
- Repetir BT-09A/BT-09B/BT-09C si se toca memoria o resolucion contextual.

Criterio de aceptacion:

- No cambia el grafo.
- No aparecen tools nuevas.
- Fallbacks siguen visibles.

## Fase R7 - Dividir DocumentRAGTool

Prioridad: **post-POC o antes si RAG domina la demo**.

Problema:

- `DocumentRAGTool` hace retrieval, filtrado, resolucion de filenames, seleccion de frases y construccion de respuesta.

Archivos previstos:

- `app/tools/rag_tool.py`
- Modulos nuevos posibles:
  - `app/rag/relevance.py`
  - `app/rag/answer_builder.py`
  - `app/rag/document_filters.py`

Cambio esperado:

- Mantener RAG como tool determinista.
- Separar relevancia y redaccion grounded.
- No exponer texto completo de chunks en `data`.

Tests minimos:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_rag_tool.py tests\unit\test_rag_ingestion.py
.\.venv\Scripts\python.exe -m pytest tests\integration\test_api_document_demo_flow.py
```

Beta real:

- Ejecutar `BT-parcial`.
- Casos obligatorios: BT-05, BT-06, BT-07, BT-10 y BT-V2-LLM-01 a BT-V2-LLM-07.
- Validar ranking de paginas esperadas, no solo respuesta textual.

Criterio de aceptacion:

- Respuestas RAG positivas siguen citando `filename`, `page`, `chunk_id`, `score`.
- Preguntas sin evidencia siguen devolviendo `insufficient_context`.
- No se mezclan documentos cuando se pregunta por un filename concreto.

## Fase R8 - Endurecer upload PDF

Prioridad: **quick win post-demo o antes si se hara upload en vivo**.

Problema:

- `app/api/upload_parser.py` parsea multipart manualmente aunque el stack ya incluye `python-multipart`.

Archivos previstos:

- `app/api/routes_documents.py`
- `app/api/upload_parser.py`
- `tests/integration/test_documents_api.py`
- `tests/unit/test_chainlit_client.py`

Cambio esperado:

- Usar `UploadFile` de FastAPI para multipart.
- Mantener soporte de `application/pdf` directo solo si sigue siendo necesario.
- Mantener limite de tamano y errores 400/413/422.

Tests minimos:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\integration\test_documents_api.py tests\unit\test_chainlit_client.py
```

Criterio de aceptacion:

- Upload desde Chainlit sigue funcionando.
- Upload por API sigue funcionando.
- No se aceptan ficheros no PDF.

## Fase R9 - Trazabilidad de replanning

Prioridad: **post-POC**.

Problema:

- El replanning existe y respeta `MAX_REPLANS = 2`, pero la traza publica se centra en el intento final.

Archivos previstos:

- `app/agents/state.py`
- `app/agents/reasoner.py`
- `app/agents/validator.py`
- `app/core/traceability.py`
- `tests/unit/test_validator.py`
- `tests/integration/test_agent_graph.py`

Cambio esperado:

- Conservar resumen publico de intentos, sin exponer chain-of-thought.
- Evitar duplicar datos raw.

Tests minimos:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_validator.py tests\integration\test_agent_graph.py
```

Criterio de aceptacion:

- Si hay replan, queda visible que ocurrio y por que.
- No se rompe `QueryResponse`.

## Fase R10 - Docker Compose

Prioridad: **P10 de cierre tecnico**.

Problema:

- La POC aun no tiene runtime reproducible completo.

Archivos previstos:

- `Dockerfile`
- `docker-compose.yml`
- `.env.example`
- `README.md`
- `docs/MANUAL_VALIDATION.md`

Cambio esperado:

- Servicios: backend FastAPI, production mock, Chainlit y ChromaDB.
- Variables diferenciadas local vs Docker.
- Chroma HTTP real en Compose.

Tests y validacion:

```powershell
docker compose up --build
.\.venv\Scripts\python.exe -m pytest
```

Beta real:

- Ejecutar `BT-parcial` dentro del runtime Docker o contra servicios levantados con Docker.
- Si se mantiene una beta fuera de Docker por coste/tiempo, ejecutar al menos `BT-smoke` desde Chainlit contra backend dockerizado.
- Confirmar que Chroma en Compose no cae a memoria salvo fallo visible y documentado.

Validacion manual:

- `GET /health` backend.
- `GET /health` production mock.
- Upload de PDFs.
- Pregunta ERP + produccion.
- Pregunta RAG.
- Pregunta mixta.
- Follow-up con memoria.

Criterio de aceptacion:

- `docker compose up --build` levanta la POC completa.
- Chainlit puede consultar el backend por red Docker.
- Chroma no cae a memoria dentro de Compose salvo fallo documentado.
- Beta real smoke/parcial queda registrada con runtime Docker.

Estado 2026-05-21:

- Agregados `Dockerfile`, `.dockerignore` y `docker-compose.yml`.
- Compose define backend FastAPI, production mock, Chainlit y ChromaDB HTTP real.
- Backend espera a ChromaDB y production mock via healthchecks para reducir el riesgo de fallback a memoria por carrera de arranque.
- Actualizados `README.md` y `.env.example` con variables local vs Docker.
- Validacion local disponible:
  - `python -m pytest`: 130 passed, 2 warnings externas.
  - Parse estatico YAML con PyYAML: ok, servicios `backend`, `chainlit`, `chromadb`, `production-api`.
- Validado con Docker Desktop el 2026-05-21:
  - `docker compose up -d --build`: backend, production mock, Chainlit y ChromaDB levantan correctamente.
  - `docker compose ps`: backend, production mock y ChromaDB quedan `healthy`; Chainlit queda `Up`.
  - `GET /health` backend: ok.
  - `GET /health` production mock: ok.
  - `GET /api/v2/heartbeat` ChromaDB via `localhost:8003`: ok.
  - Upload `v2_anexo_penalizaciones_sla.pdf`: `indexed`, 8 chunks, `fallbacks=[]`.
  - RAG documental: `completed`, fuente `Documentos`, `fallbacks=[]`.
  - ERP + produccion ALFKI: `completed`, fuentes `ERP`, `Produccion`, `fallbacks=[]`.
  - Mixto ERP + produccion + RAG: `completed`, fuentes `ERP`, `Produccion`, `Documentos`, `fallbacks=[]`.
  - Guardrail documental sin evidencia: `insufficient_context`, `fallbacks=[]`.
- Incidencia corregida: `chromadb/chroma:1.5.0` no incluye comando `python`; el healthcheck inicial fallaba aunque el servidor Chroma escuchaba en `8000`. Se cambio a comprobacion interna de puerto `8000` via `/proc/net/tcp`.
- Endurecimiento de secretos aplicado: Compose base no pasa `GEMINI_API_KEY` ni `OPENAI_API_KEY` como variables directas; para Docker con proveedor real se usa `docker-compose.secrets.yml` y `*_API_KEY_FILE`.
- Pendiente antes de cerrar fase por completo: registrar `BT-smoke`/`BT-parcial` formal en `docs/BETA_VALIDATION_REPORT.md`.

## Fase R11 - Guion demo y cierre

Prioridad: **antes de entrega final**.

Archivos previstos:

- Nuevo doc posible: `docs/DEMO_SCRIPT.md`
- `README.md`
- `docs/MANUAL_VALIDATION.md`
- `docs/BETA_VALIDATION_REPORT.md`

Contenido esperado:

- Guion de 3-5 minutos.
- Preguntas obligatorias y orden recomendado.
- Que destacar ante revisor.
- Deuda consciente admitida.
- Plan de rollback si LLM o Chroma fallan.
- Referencia a la ultima `BT-completa` con LLM real.

Criterio de aceptacion:

- Una persona externa puede levantar, ejecutar y defender la POC.
- Las limitaciones estan explicadas sin parecer improvisadas.
- `docs/BETA_VALIDATION_REPORT.md` contiene una iteracion final sin fallos en casos de demo.

## Matriz de tests por tipo de cambio

| Cambio | Tests focalizados |
|---|---|
| Planner | `tests/unit/test_planner.py`, `tests/integration/test_agent_graph.py` |
| Validator/replanning | `tests/unit/test_validator.py`, `tests/integration/test_agent_graph.py` |
| Final response | `tests/unit/test_final_response.py`, `tests/integration/test_agent_graph.py` |
| Tools ERP | `tests/unit/test_erp_tool.py`, `tests/unit/test_erp_repository.py` |
| Tools produccion | `tests/unit/test_production_tool.py`, `tests/integration/test_production_mock_api.py` |
| RAG | `tests/unit/test_rag_tool.py`, `tests/unit/test_rag_ingestion.py`, `tests/integration/test_api_document_demo_flow.py` |
| API query | `tests/integration/test_query_endpoint.py` |
| API documentos | `tests/integration/test_documents_api.py` |
| Chainlit | `tests/unit/test_chainlit_client.py`, `tests/unit/test_chainlit_formatting.py`, `tests/unit/test_chainlit_thinking.py` |
| Trazabilidad | `tests/unit/test_traceability.py`, `tests/integration/test_query_endpoint.py` |
| Runtime Docker | `pytest` completo + checklist manual |

## Checklist antes de cada commit

- `git diff` revisado.
- No hay cambios de alcance accidental.
- Tests focalizados pasan.
- Si el cambio afecta comportamiento visible, `BT-smoke` con LLM real pasa o queda justificado.
- Si se toca contrato API, docs actualizados.
- Si se toca respuesta visible, Chainlit formatting sigue mostrando fuentes, pasos, tool calls y fallbacks.
- No hay secretos en diff.
- Commit con un solo tema.

## Checklist antes de demo

- `pytest` completo pasa.
- `docs/MANUAL_VALIDATION.md` ejecutado al menos para casos obligatorios.
- `BT-completa` con LLM real registrada en `docs/BETA_VALIDATION_REPORT.md`.
- Casos validados:
  - ERP + produccion: ALFKI pendientes y estados.
  - Produccion bloqueada con motivo y cliente ERP.
  - Produccion retrasada con cliente ERP.
  - RAG penalizaciones/plazos/resumen.
  - Mixto penalizaciones con ERP + Produccion + Documentos.
  - Memoria conversacional con `conversation_id`.
  - Pregunta documental sin evidencia.
- Fallbacks visibles si se fuerza modo deterministico o Chroma memoria.
- Sin fallbacks inesperados en la pasada beta real.
- `.env` no esta versionado.
- P10 Docker Compose cerrado o declarado explicitamente como pendiente.

## Deuda aceptada mientras se refactoriza

- ERP en SQLite en memoria es una decision consciente de POC.
- Memoria conversacional en memoria de proceso es suficiente para demo.
- Chroma fallback en memoria es valido si aparece en `fallbacks`.
- No hay autenticacion, multi-tenant ni observabilidad productiva.
- No se cambia el stack obligatorio.
- No se sustituye el flujo Planner -> Reasoner -> Validator -> FinalResponseBuilder.

## Registro vivo de avances

| Fecha | Fase | Estado | Evidencia | Commit |
|---|---|---|---|---|
| 2026-05-21 | R0 | en curso | Documento creado desde auditoria senior | pendiente |
| 2026-05-21 | Beta | en curso | Beta real integrada como criterio de aceptacion por fase | pendiente |
| 2026-05-21 | R1 | validado en tests / beta pendiente | Guardrail mixto documental implementado; unit validator 6 passed; integration agent graph 11 passed | pendiente |
| 2026-05-21 | R2 | validado en tests / beta pendiente | Planner sin default ALFKI; unit planner 15 passed; query endpoint 7 passed; agent graph 11 passed | pendiente |
| 2026-05-21 | R3 | validado en tests / beta pendiente | Tool actions visibles; unit tools/traceability 25 passed; query endpoint 7 passed; agent graph 11 passed | pendiente |
| 2026-05-21 | R10 | validado en Docker / beta parcial pendiente | Compose stack healthy; upload PDF 8 chunks; RAG/ERP/mixto/guardrail OK sin fallbacks; healthcheck Chroma corregido; secretos por archivo validados | pendiente |
