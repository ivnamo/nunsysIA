# Plan de Tareas

Este plan guia la implementacion por fases. No se debe avanzar a la siguiente fase si la actual no tiene criterio de aceptacion cumplido o documentado como pendiente.

## Estado actual

El repositorio ya ha superado las fases 0 a 10 a nivel funcional. **P10 -
Docker Compose** queda validada con backend FastAPI, API mock de produccion,
Chainlit y ChromaDB HTTP real. P9/P10 quedan cubiertas con los comportamientos
evaluables de demo:

- Planner hibrido con LLM opcional y fallback determinista.
- RAG multi-documento con PDFs mock realistas.
- Chainlit con subida de documentos al espacio documental.
- Validacion manual reproducible.
- Guardrails para no inventar y devolver `insufficient_context`.
- Memoria conversacional simple de ultimas 5 interacciones por `conversation_id`.
- Clarificaciones controladas con `needs_clarification` cuando una pregunta de
  dominio necesita cliente, pedido o contexto previo.
- Planner flexible para sinonimos operativos, cliente en minusculas y pedidos
  explicitos sin introducir Query DSL.

Pendiente antes del cierre final:

- sin pendientes tecnicos obligatorios para la revision.
- ejecutar la demo con `docs/DEMO_SCRIPT.md`.

Extension opcional post-cierre:

- R14-R18 en `docs/plan_implementacion_vivo.md`: Query DSL segura, joins
  controlados y tests reales opt-in con LLM. No bloquea la revision actual.

## Fase 0: Setup y estructura

Estado: completada.

Objetivo: preparar el repositorio sin logica funcional.

Tareas:

- Crear estructura base de carpetas.
- Crear requirements.
- Crear `.env.example`.
- Configurar pytest.
- Preparar README inicial.

Criterio de aceptacion:

- El repo instala dependencias.
- `pytest` puede ejecutarse.
- La estructura coincide con la arquitectura acordada.

Riesgos:

- Crear logica antes de tiempo.
- Introducir frameworks no acordados.

## Fase 1: FastAPI base + schemas + health

Estado: completada.

Objetivo: tener backend minimo ejecutable.

Tareas:

- Crear `app/main.py`.
- Crear `GET /health`.
- Crear schemas Pydantic base.
- Crear test de health.

Criterio de aceptacion:

- `/health` responde `200`.
- El test de health pasa.

Riesgos:

- Meter logica de negocio en rutas.

## Fase 2: ERP Northwind

Estado: completada con Northwind reducido y SQLite en memoria para tests/demo. PostgreSQL queda fuera del runtime actual y solo seria una mejora posterior si se decide endurecer persistencia.

Objetivo: preparar ERP simulado con datos controlados.

Tareas:

- Crear modelo/seed Northwind minimo.
- Preparar conexion a base.
- Crear repositorios ERP.
- Crear tests de consultas ERP.

Criterio de aceptacion:

- Se pueden consultar clientes, pedidos e importes.
- Los datos son deterministas.

Riesgos:

- Importar Northwind completo y retrasar la POC.

## Fase 3: API mock de produccion

Estado: completada.

Objetivo: simular sistema externo de produccion.

Tareas:

- Crear servicio mock FastAPI.
- Exponer estados de pedidos.
- Incluir bloqueos, retrasos y motivos.
- Crear tests o pruebas HTTP basicas.

Criterio de aceptacion:

- La API devuelve estados por pedido.
- Hay datos coherentes con ERP.

Riesgos:

- Acoplar produccion directamente a la base ERP.

## Fase 4: Tools ERP y produccion

Estado: completada.

Objetivo: encapsular integraciones como tools deterministas.

Tareas:

- Crear `ERPTool`.
- Crear `ProductionAPITool`.
- Definir input/output con Pydantic.
- Registrar tool calls.
- Crear tests unitarios.

Criterio de aceptacion:

- Las tools devuelven JSON estructurado.
- No devuelven texto narrativo.

Riesgos:

- Permitir que el LLM invente datos de tool.

## Fase 5: LangGraph basico con Planner/Reasoner/Validator

Estado: completada. El Planner se ha reforzado en P9 como hibrido LLM + fallback determinista.

Objetivo: montar el workflow agentic minimo.

Tareas:

- Definir `AgentState`.
- Crear Planner con plan estructurado.
- Crear Reasoner/Executor.
- Crear Validator Node.
- Crear FinalResponseBuilder.
- Limitar replanning con `MAX_REPLANS = 2`.

Criterio de aceptacion:

- Una consulta ERP + produccion pasa por el grafo.
- La respuesta incluye sources, reasoning y tool calls.

Riesgos:

- Crear agentes demasiado autonomos.
- No controlar loops.

## Fase 6: RAG con subida de PDFs

Estado: completada en version funcional. P9 ya expone citas visibles por chunk; queda mejora futura de retrieval/evidencias si se endurece la demo.

Objetivo: permitir consultas documentales.

Tareas:

- Crear upload de PDF.
- Extraer texto.
- Crear chunks.
- Crear embeddings.
- Guardar en vector store documental. ChromaDB es el objetivo; en local existe fallback en memoria si ChromaDB no esta instalado o disponible.
- Crear `DocumentRAGTool`.
- Crear tests de ingestion y retrieval.

Criterio de aceptacion:

- Un PDF se indexa.
- Una pregunta documental recupera chunks.
- Sin contexto, devuelve `insufficient_context`.

Riesgos:

- Responder desde conocimiento general del modelo.

## Fase 7: Chainlit

Estado: completada en version funcional.

Objetivo: preparar interfaz de demo.

Tareas:

- Crear app Chainlit.
- Conectar con `/api/query`.
- Mostrar respuesta, fuentes, reasoning y tool calls.
- Permitir upload PDF al espacio documental.

Criterio de aceptacion:

- La demo puede hacerse desde navegador.

Riesgos:

- Dedicar demasiado tiempo a UI antes de estabilizar API.

## Fase 8: Trazabilidad y respuesta estructurada

Estado: completada.

Objetivo: endurecer contrato de salida.

Tareas:

- Estandarizar `tool_calls` y `fallbacks`.
- Estandarizar estados.
- Sanitizar errores.
- Documentar trazas.
- Validar schema final.

Criterio de aceptacion:

- Toda respuesta de `/api/query` tiene trazabilidad.

Riesgos:

- Exponer chain-of-thought o secretos.

## Fase P9: Funcionalidad evaluable de la POC

Estado: completada a nivel funcional.

Objetivo: convertir la POC en una demo funcional, trazable y reproducible, ademas de una arquitectura minima.

Tareas:

- Integrar proveedor LLM real con Gemini y soporte alternativo OpenAI.
- Mantener fallback determinista para tests y demo sin proveedor, siempre marcado con `FALLBACK_*`.
- Endurecer Planner con schema Pydantic, timeout y lista cerrada de actions.
- Crear PDFs mock realistas para RAG.
- Probar upload + query documental desde API y Chainlit.
- Documentar validacion manual exacta.
- Mejorar respuesta final con LLM controlado. Estado: completada.
- Incluir citas documentales visibles por chunk. Estado: completada.
- Alinear documentacion principal con el estado real del repo. Estado: completada.
- Implementar memoria conversacional simple. Estado: completada.

Criterio de aceptacion:

- Las preguntas obligatorias ERP/produccion/documentos funcionan en API y Chainlit.
- `pytest` pasa sin llamadas pagadas.
- Las respuestas incluyen trazabilidad.
- Las consultas sin evidencia documental devuelven `insufficient_context`.
- Los follow-ups simples por `conversation_id` recuperan contexto con fuente `Memoria`.

Riesgos:

- LLM lento o modelo invalido bloqueando la demo.
- RAG con falsos positivos.
- Redaccion final demasiado tecnica.

## Fase P10: Docker Compose

Estado: completada y validada.

Objetivo: levantar la POC completa.

Tareas:

- Crear Dockerfile.
- Crear docker-compose.
- Incluir backend, produccion mock, ChromaDB y UI.
- Documentar variables.

Criterio de aceptacion:

- `docker compose up --build` levanta el sistema.
- Docker Compose con `docker-compose.secrets.yml` usa API key por archivo, no
  como variable directa del contenedor.
- ChromaDB HTTP queda `healthy` y no cae a memoria.
- Smoke beta con LLM/embeddings reales pasa en Docker.

Evidencia 2026-05-21:

- `python -m pytest`: `136 passed, 2 warnings`.
- Coleccion Chroma Docker aislada: `beta_docker_baseline_20260521_r10b`.
- 5 PDFs v2 indexados con `fallbacks=[]`.
- Casos Docker baseline: ERP+produccion, RAG, mixto, memoria conversacional y
  guardrail documental en `PASS`.
- Incidencia beta corregida: falso positivo RAG por solape debil con `receta`;
  el filtro documental exige mas evidencia cuando la pregunta contiene varios
  conceptos.

Riesgos:

- Problemas de red entre servicios.

## Fase P11: Hardening final de tests

Objetivo: consolidar cobertura y estabilidad antes de entrega.

Tareas:

- Mantener suite automatizada versionada actual (`156 passed, 2 warnings`).
- Agregar regresiones para cualquier ajuste de memoria o Docker.
- Revisar casos de error de servicios externos.
- Validar que los tests no requieren llamadas pagadas.

Criterio de aceptacion:

- `pytest` pasa sin llamadas pagadas obligatorias.

Riesgos:

- Tests fragiles dependientes del LLM.

## Fase P12: README y demo final

Objetivo: dejar la entrega documentada y reproducible.

Tareas:

- Completar README.
- Documentar arquitectura.
- Documentar decisiones.
- Documentar ejecucion.
- Preparar demo de 3-5 minutos.

Criterio de aceptacion:

- Una persona externa puede levantar y probar la POC.

Riesgos:

- Documentar tarde y olvidar decisiones clave.

## Fase P13: Flexibilidad conversacional + Query DSL segura

Estado: planificada como extension opcional.

Objetivo: ampliar la POC sin cambiar el stack ni el flujo agentic aprobado,
permitiendo preguntas mas abiertas, aclaraciones utiles y consultas flexibles a
ERP/Produccion mediante una DSL validada.

Tareas:

- Mantener `needs_clarification` ya incorporado en R12 para ambiguedades de dominio.
- Ampliar routing del planner con sinonimos de negocio y normalizacion de
  cliente/pedido.
- Crear modelos y validadores de Query DSL antes de ejecutar nada.
- Crear `ERPQueryTool` y `ProductionQueryTool` con allowlists.
- Ejecutar cruces ERP-Produccion solo en el reasoner y por `order_id`.
- Mejorar respuesta final manteniendo grounding estricto.
- Anadir tests `real_llm` opt-in con `RUN_REAL_LLM_TESTS=1`.

Criterio de aceptacion:

- Suite rapida sigue siendo determinista.
- No hay SQL, HTTP ni joins libres generados por LLM.
- Las tools especificas siguen teniendo prioridad para casos criticos.
- La beta real queda registrada en `docs/BETA_VALIDATION_REPORT.md`.

Riesgos:

- Cambiar contrato y comportamiento visible demasiado cerca de una demo.
- Abrir una superficie agentic nueva sin validadores suficientes.
