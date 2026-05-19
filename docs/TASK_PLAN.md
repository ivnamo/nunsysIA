# Plan de Tareas

Este plan guia la implementacion por fases. No se debe avanzar a la siguiente fase si la actual no tiene criterio de aceptacion cumplido o documentado como pendiente.

## Fase 0: Setup y estructura

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

Objetivo: permitir consultas documentales.

Tareas:

- Crear upload de PDF.
- Extraer texto.
- Crear chunks.
- Crear embeddings.
- Guardar en ChromaDB.
- Crear `DocumentRAGTool`.
- Crear tests de ingestion y retrieval.

Criterio de aceptacion:

- Un PDF se indexa.
- Una pregunta documental recupera chunks.
- Sin contexto, devuelve `insufficient_context`.

Riesgos:

- Responder desde conocimiento general del modelo.

## Fase 7: Chainlit

Objetivo: preparar interfaz de demo.

Tareas:

- Crear app Chainlit.
- Conectar con `/api/query`.
- Mostrar respuesta, fuentes, reasoning y tool calls.
- Permitir upload PDF si el tiempo lo permite.

Criterio de aceptacion:

- La demo puede hacerse desde navegador.

Riesgos:

- Dedicar demasiado tiempo a UI antes de estabilizar API.

## Fase 8: Trazabilidad y respuesta estructurada

Objetivo: endurecer contrato de salida.

Tareas:

- Estandarizar `tool_calls`.
- Estandarizar estados.
- Sanitizar errores.
- Documentar trazas.
- Validar schema final.

Criterio de aceptacion:

- Toda respuesta de `/api/query` tiene trazabilidad.

Riesgos:

- Exponer chain-of-thought o secretos.

## Fase 9: Docker Compose

Objetivo: levantar la POC completa.

Tareas:

- Crear Dockerfile.
- Crear docker-compose.
- Incluir backend, produccion mock, ChromaDB y UI.
- Documentar variables.

Criterio de aceptacion:

- `docker compose up --build` levanta el sistema.

Riesgos:

- Problemas de red entre servicios.

## Fase 10: Tests minimos

Objetivo: asegurar comportamiento clave.

Tareas:

- Tests de health.
- Tests de schemas.
- Tests de Planner.
- Tests de Validator.
- Tests de tools.
- Tests de RAG.

Criterio de aceptacion:

- `pytest` pasa sin llamadas pagadas obligatorias.

Riesgos:

- Tests fragiles dependientes del LLM.

## Fase 11: README y demo

Objetivo: dejar entrega defendible.

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
