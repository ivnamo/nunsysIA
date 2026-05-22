# Deep Agents Beta Validation Summary

Fecha: 2026-05-22.

## Criterio correcto

La prueba tecnica no se defiende con un subconjunto elegido a mano. El corte
versionado del repositorio es la `BT-completa` definida en
`docs/plan_implementacion_vivo.md` y ejecutada por
`scripts/beta_validation_support.py`:

- `BT-01` a `BT-11`.
- `BT-V2-01` a `BT-V2-07`.
- Total: 18 casos obligatorios.

## Resultado final

Validacion real opt-in contra la beta obligatoria completa usando
`scripts/run_beta_validation.py --flow deepagents-tools`.

| Flujo | Casos ejecutados | Resultado |
|---|---:|---|
| `deepagents-tools` | BT-01..BT-11 + BT-V2-01..BT-V2-07 | PASS=18, FAIL=0 |

Informe principal:

- `docs/DEEPAGENTS_TOOLS_BETA_VALIDATION_REPORT.md`

Informes historicos de diagnostico inicial:

- `docs/DEEPAGENTS_BETA_BT01.md`
- `docs/DEEPAGENTS_BETA_CRITICAL_REPORT.md`
- `docs/DEEPAGENTS_SIDECAR_BETA_CRITICAL_REPORT.md`

## Lectura tecnica

- La primera validacion parcial de `deepagents-tools` habia usado un subconjunto
  de fallos, no la bateria obligatoria completa. Ese criterio queda corregido.
- `deepagents-tools` mantiene integracion real con Deep Agents y tools
  individuales/compuestas, pero ahora incluye un supervisor determinista antes y
  despues del agente para preservar contratos de beta.
- La solucion viable no es confiar en que el prompt corrija todo: las rutas
  beta-sensibles ejecutan tools obligatorias y normalizan `status`, memoria y
  respuesta final desde evidencia trazada.

## Ajustes aplicados

- Preflight para follow-up aislado sin memoria: `needs_clarification`, sin tool
  calls.
- Routing documental para `segun`, `pdf`, `documento`, `contrato`, `anexo`,
  `receta`, `cocina` y `vegana`.
- Penalizaciones por pedido con traces esperadas: `ERPTool`,
  `ProductionAPITool` y `DocumentRAGTool`.
- Pedidos bloqueados/retrasados con `ProductionAPITool` y resolucion de cliente
  via `ERPTool`.
- Resumen mensual determinista con periodo `2026-05`, pedidos de mayo y estados
  de produccion.
- Memoria conversacional filtrada: si el turno previo resuelve solo bloqueados,
  el impacto economico posterior calcula solo esos pedidos.
- `insufficient_context` se conserva para consultas documentales sin chunks.

## Subagente corrector

Puede aportar valor, pero no como parche principal de beta. La opcion prudente es
un corrector/verificador limitado que revise una `QueryResponse` ya construida y
solo pueda pedir una correccion mediante tools de negocio permitidas. No deberia
tener filesystem, shell, `execute` ni `task` generico en el endpoint de negocio.

Decision actual: no se activa subagente corrector hasta que haya una necesidad
funcional concreta. Con la beta completa en PASS, el siguiente paso razonable es
mantener los guardrails deterministas y dejar el corrector como mejora opcional
para robustez, no como requisito de entrega.
