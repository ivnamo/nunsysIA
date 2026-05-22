# Deep Agents Beta Validation Summary

Fecha: 2026-05-22.

## Resultado

Validacion incremental contra la beta obligatoria usando `scripts/run_beta_validation.py`
con selector de flujo y `case_id`.

| Flujo | Casos ejecutados | Resultado |
|---|---:|---|
| `deepagents-tools` | BT-01 | PASS=1, FAIL=0 |
| `deepagents-tools` | BT-08, BT-09, BT-10, BT-11, BT-V2-07 | PASS=0, FAIL=5 |
| `deepagents-sidecar` | BT-08, BT-09, BT-10, BT-11, BT-V2-07 | PASS=5, FAIL=0 |

Informes generados:

- `docs/DEEPAGENTS_BETA_BT01.md`
- `docs/DEEPAGENTS_BETA_CRITICAL_REPORT.md`
- `docs/DEEPAGENTS_SIDECAR_BETA_CRITICAL_REPORT.md`

## Lectura tecnica

- El sidecar Deep Agents cumple los casos criticos porque invoca el workflow
  estable validado como tool auditable.
- El flujo direct-tools no esta listo para sustituir al workflow estable en la
  beta obligatoria.
- El fallo inicial de la ejecucion completa fue operativo: el runner no emitia
  progreso, no permitia aislar casos y no dejaba informe parcial si se cortaba.
  Ahora acepta `--flow` y `--case-id`, imprime progreso y escribe checkpoint por
  caso cuando se usa `--output` sin `--append`.

## Fallos direct-tools detectados

- BT-08: usa `ERPQueryTool` y `ProductionQueryTool`, pero la beta espera
  `ERPTool` y `ProductionAPITool`. Ademas calcula una penalizacion para 10248
  que el workflow estable evita por falta de evidencia suficiente.
- BT-09: resuelve memoria, pero duplica `MemoryTool`, usa `ERPQueryTool` donde
  la beta espera `ERPTool` y no calcula el impacto economico del pedido bloqueado
  como `economic_impact_total`.
- BT-10: no enruta correctamente `Segun el PDF... receta...` a RAG; consulta ERP
  y Produccion y responde `completed`.
- BT-11: ante follow-up aislado sin memoria, consulta Produccion y responde datos
  globales; deberia devolver `needs_clarification`.
- BT-V2-07: consulta RAG y recupera 0 chunks, pero normaliza a `completed`;
  deberia conservar `insufficient_context`.

## Plan de mejora

- Anadir preflight determinista antes de crear Deep Agent:
  - follow-up aislado sin memoria -> `needs_clarification`;
  - consultas con `segun`, `pdf`, `documento`, `receta`, `cocina`, `vegana` ->
    RAG documental.
- Ajustar tools compuestas direct-tools para casos beta:
  - penalizaciones por pedido debe usar `ERPTool.get_orders_by_month` y
    `ProductionAPITool.get_status_for_order_ids`;
  - memoria economica debe llamar `ERPTool.calculate_order_amount` sobre los
    pedidos referenciados correctos.
- Mantener `insufficient_context` cuando una consulta documental pura recupera
  0 chunks.
- Evitar doble `MemoryTool` en tools compuestas.
- Repetir beta incremental por bloques antes de intentar la beta completa.
