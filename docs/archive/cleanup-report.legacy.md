# Informe de limpieza documental

Fecha: 2026-05-22

## Criterio aplicado

La documentacion principal debe explicar el estado real del repositorio para una
evaluacion tecnica. El flujo principal actual es:

```text
POST /api/query
-> AgentRouter
-> mode=deepagent
-> DeepAgentService
-> LangChain DeepAgents con tools de negocio
-> ResponseNormalizer
-> QueryResponse
```

LangGraph existe en el codigo, pero queda como flujo legacy/experimental. La
documentacion que lo presenta como arquitectura principal debe reescribirse o
archivarse.

## Resumen ejecutivo

- Mantener visible solo documentacion operativa y evaluable.
- Reescribir `README.md`, `docs/architecture.md`, `docs/api.md` y
  `docs/validation.md`.
- Archivar planes, informes beta, comparativas y guiones historicos en
  `docs/archive/`.
- Mover prompts antiguos de desarrollo a `docs/archive/dev-prompts/`.
- Eliminar unicamente basura clara: informe temporal `.tmp_*` y logs locales.
- Actualizar reglas de Cursor que siguen declarando LangGraph como orquestador
  principal.

## Auditoria por archivo

| Archivo revisado | Problema detectado | Accion propuesta | Riesgo de eliminarlo | Recomendacion final |
|---|---|---|---|---|
| `README.md` | Parcialmente actual, pero no cubre todas las secciones exigidas para evaluacion, mezcla detalles historicos y no expone limitaciones/mejoras con suficiente claridad. | REESCRIBIR | Alto: es la entrada principal del evaluador. | Reescribir completo y enlazar solo docs actuales. |
| `AGENTS.md` | Reglas de colaboracion utiles, pero el checklist menciona LangGraph como parte central sin distinguir DeepAgents como flujo principal. | REESCRIBIR | Medio: afecta instrucciones de futuros agentes, no runtime. | Actualizar stack y responsabilidades sin eliminar roles. |
| `chainlit.md` | Documento breve usado por Chainlit como pagina inicial. Esta alineado con `/api/query` y subida de PDFs. | CONSERVAR | Medio: Chainlit puede mostrarlo en la UI. | Conservar, sin convertirlo en doc principal. |
| `.env.example` | Es util y no contiene secretos. Explica claves por variable o archivo. | CONSERVAR | Alto: guia configuracion reproducible. | Conservar y referenciar desde README. |
| `docker-compose.yml` | Configuracion necesaria y coherente con demo determinista. | CONSERVAR | Alto: necesario para arranque Docker. | Conservar. |
| `docker-compose.secrets.yml` | Override util para secretos por archivo. | CONSERVAR | Medio: no es obligatorio, pero evita documentar claves en claro. | Conservar. |
| `Dockerfile` | Configuracion necesaria para backend, API mock y Chainlit. | CONSERVAR | Alto: necesario para Docker Compose. | Conservar. |
| `query.json` | Ejemplo simple de request contra `/api/query`. | CONSERVAR | Bajo: se puede recrear, pero es util para demo. | Conservar. |
| `requirements.txt` | Manifiesto de dependencias, no documentacion de producto. | CONSERVAR | Alto: necesario para instalacion. | Conservar. |
| `requirements-chroma.txt` | Manifiesto de dependencias con ChromaDB. | MOVER A `docs/archive/dependencies` | Bajo: ChromaDB queda integrado en `requirements.txt`. | Archivado por la limpieza de dependencias posterior. |
| `requirements-dev.txt` | Manifiesto de dependencias de test. | CONSERVAR | Alto: necesario para validacion. | Conservar. |
| `requirements-deepagents.txt` | Compatibilidad historica que remite a `requirements.txt`. | MOVER A `docs/archive/dependencies` | Bajo: duplicaba `requirements.txt`. | Archivado por la limpieza de dependencias posterior. |
| `.tmp_beta_validation_report.md` | Informe temporal duplicado, ignorado por `.gitignore`, no debe estar visible. | ELIMINAR | Bajo: existe informacion equivalente en informes versionados. | Eliminar. |
| `beta_prod_stdout.log` | Log local temporal. | ELIMINAR | Bajo: artefacto de ejecucion local. | Eliminar. |
| `beta_prod_stderr.log` | Log local temporal. | ELIMINAR | Bajo: artefacto de ejecucion local. | Eliminar. |
| `docs/ARCHITECTURE.md` | Contiene partes validas, pero esta sobredimensionado y usa nombre antiguo en mayusculas. | REESCRIBIR | Alto si se elimina sin sustituto. | Archivar version completa y crear `docs/architecture.md` conciso. |
| `docs/API_CONTRACT.md` | Contrato util, demasiado extenso para doc principal y con detalles historicos. | REESCRIBIR | Alto si se elimina sin sustituto. | Archivar version completa y crear `docs/api.md` actual. |
| `docs/TRACEABILITY.md` | Contenido valido, pero duplicado con README/API/arquitectura. | MOVER A `docs/archive` | Bajo: la informacion esencial se fusionara en docs actuales. | Archivar tras fusionar trazabilidad esencial. |
| `docs/MANUAL_VALIDATION.md` | Util pero mezcla autorizacion historica de beta, conteos de tests y una nota ya desactualizada sobre embeddings en Compose. | REESCRIBIR | Medio: contiene comandos utiles. | Archivar original y crear `docs/validation.md` limpio. |
| `docs/DEMO_SCRIPT.md` | Guion de demo valioso como historico, pero contiene conteos fijos, beta real y narrativa de defensa que puede distraer. | MOVER A `docs/archive` | Bajo: no es contrato operativo. | Archivar. |
| `docs/DEVELOPMENT_GUIDE.md` | Guia de Cursor y git, no necesaria para evaluador; referencia docs antiguas y conteos fijos. | MOVER A `docs/archive` | Bajo. | Archivar. |
| `docs/TASK_PLAN.md` | Plan por fases ya cerrado; util solo como historico. | MOVER A `docs/archive` | Bajo. | Archivar. |
| `docs/plan_implementacion_vivo.md` | Documento vivo muy largo con historia de refactor, conteos y estados anteriores. | MOVER A `docs/archive` | Bajo/medio: conserva decisiones historicas. | Archivar. |
| `docs/resumen_chat_prueba_tecnica_agentes_ia.txt` | Resumen antiguo que declara LangGraph como arquitectura acordada principal. | MOVER A `docs/archive` | Bajo: historico de requisitos. | Archivar. |
| `docs/Prueba-Tecnica-IA-Agentes.pdf` | Enunciado o material de prueba. No debe competir con documentacion principal. | MOVER A `docs/archive` | Medio: puede ser fuente historica del alcance. | Archivar como especificacion historica. |
| `docs/BETA_VALIDATION_REPORT.md` | Informe beta previo del flujo `QueryWorkflowService`; no representa el flujo principal actual. | MOVER A `docs/archive/validation` | Bajo: conservar como evidencia historica. | Archivar. |
| `docs/DEEPAGENTS_TOOLS_BETA_VALIDATION_REPORT.md` | Informe final valioso, pero demasiado largo para documentacion principal. | MOVER A `docs/archive/validation` | Medio: evidencia de validacion real. | Archivar y resumir en `docs/validation.md`. |
| `docs/DEEPAGENTS_BETA_VALIDATION_SUMMARY.md` | Resumen historico util, duplicado con informe final y futuro `docs/validation.md`. | MOVER A `docs/archive/validation` | Bajo. | Archivar. |
| `docs/DEEPAGENTS_COMPARISON_REPORT.md` | Comparativa historica con sidecar y legacy. Puede confundir si queda principal. | MOVER A `docs/archive/validation` | Bajo. | Archivar. |
| `docs/DEEPAGENTS_BETA_BT01.md` | Validacion parcial de un unico caso. | MOVER A `docs/archive/validation` | Bajo. | Archivar. |
| `docs/DEEPAGENTS_BETA_CRITICAL_REPORT.md` | Informe de fallos ya superado. | MOVER A `docs/archive/validation` | Bajo. | Archivar. |
| `docs/DEEPAGENTS_SIDECAR_BETA_CRITICAL_REPORT.md` | Informe de flujo experimental sidecar. | MOVER A `docs/archive/validation` | Bajo. | Archivar. |
| `data/sample_docs/README.md` | Describe PDFs mock versionados y como regenerarlos. | CONSERVAR | Medio: ayuda a validar RAG. | Conservar. |
| `prompts/create_endpoint.md` | Prompt antiguo de trabajo con Cursor, no documentacion del producto. | MOVER A `docs/archive/dev-prompts` | Bajo. | Archivar con el resto de prompts. |
| `prompts/create_test.md` | Prompt antiguo de trabajo con Cursor. | MOVER A `docs/archive/dev-prompts` | Bajo. | Archivar. |
| `prompts/create_tool.md` | Prompt antiguo de trabajo con Cursor. | MOVER A `docs/archive/dev-prompts` | Bajo. | Archivar. |
| `prompts/debug_failure.md` | Prompt antiguo de trabajo con Cursor. | MOVER A `docs/archive/dev-prompts` | Bajo. | Archivar. |
| `prompts/implement_feature.md` | Prompt antiguo de trabajo con Cursor. | MOVER A `docs/archive/dev-prompts` | Bajo. | Archivar. |
| `prompts/review_code.md` | Prompt antiguo de trabajo con Cursor. | MOVER A `docs/archive/dev-prompts` | Bajo. | Archivar. |
| `reports/api_evaluation.md` | Reporte generado de evaluacion. Util como evidencia, pero no documentacion principal. | MOVER A `docs/archive/reports` | Bajo/medio. | Archivar. |
| `reports/docker_compose_config.txt` | Salida generada de `docker compose config` con rutas absolutas locales. | ELIMINAR | Bajo: se regenera con `docker compose config`. | Eliminar para no conservar rutas locales en el repo. |
| `reports/raw_responses.json` | Artefacto generado con respuestas raw. | MOVER A `docs/archive/reports` | Bajo. | Archivar o regenerar cuando se ejecute evaluador. |
| `tests/fixtures/dummy_gemini_secret.txt` | Fixture de tests con valor dummy, no secreto real ni documentacion. | CONSERVAR | Medio: puede romper tests si se elimina. | Conservar. |
| `.cursor/rules/project.mdc` | Declara LangGraph como orquestador principal. | REESCRIBIR | Medio: regla de desarrollo, no runtime. | Actualizar a DeepAgents principal y LangGraph legacy. |
| `.cursor/rules/architecture.mdc` | Declara flujo fijo LangGraph Planner/Reasoner/Validator como principal. | REESCRIBIR | Medio. | Actualizar a AgentRouter + DeepAgents como flujo principal. |
| `.cursor/rules/agents.mdc` | Regla util, pero centrada en Planner/Reasoner/Validator como flujo principal. | REESCRIBIR | Medio. | Ajustar a tools de negocio y modos legacy. |
| `.cursor/rules/backend.mdc` | Regla util; menciona entrypoint del grafo y nodos LangGraph en rutas. | REESCRIBIR | Bajo. | Ajustar a servicios/AgentRouter. |
| `.cursor/rules/rag.mdc` | Alineada con RAG como tool y ChromaDB. | CONSERVAR | Medio. | Conservar. |
| `.cursor/rules/testing.mdc` | Alineada en general, aunque menciona Planner/Validator por legado. | REESCRIBIR | Bajo. | Ajustar cobertura a router, DeepAgents y legacy. |
| `.cursor/rules/git-workflow.mdc` | Guia de ramas. No contradice arquitectura. | CONSERVAR | Bajo. | Conservar. |

## Comentarios largos, TODOs y notas obsoletas en codigo

Se ha buscado `TODO`, `FIXME`, `HACK`, `XXX`, referencias a prompts antiguos y
comentarios generados por IA en `app/`, `chainlit_app/`, `production_mock/`,
`scripts/` y `tests/`. No se detectan TODOs obsoletos ni comentarios largos que
deban eliminarse para esta entrega. Las referencias a `legacy` y `experimental`
en codigo corresponden a modos reales soportados o tests de compatibilidad.

## Estructura documental propuesta

```text
README.md
chainlit.md
data/sample_docs/README.md
docs/
  api.md
  architecture.md
  validation.md
  cleanup-report.md
  archive/
    dev-prompts/
    reports/
    validation/
```

## Riesgos aceptados

- Se conserva documentacion historica en `docs/archive/` para no perder
  contexto de decisiones y validaciones previas.
- Se eliminan solo artefactos temporales locales no versionados o claramente
  regenerables.
- Las reglas `.cursor` se actualizan porque, aunque no son runtime, podrian
  inducir a futuros cambios contra la arquitectura real.
