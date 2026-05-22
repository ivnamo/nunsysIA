# Guia de Desarrollo con Cursor

## Principio Principal

No solicitar a Cursor una implementacion completa sin desglose. Trabajar por fases pequenas, verificables y alineadas con las reglas del proyecto.

## Antes de Implementar

Leer siempre:

- `.cursor/rules/project.mdc`
- `.cursor/rules/architecture.mdc`
- `.cursor/rules/backend.mdc`
- `.cursor/rules/agents.mdc`
- `.cursor/rules/rag.mdc`
- `.cursor/rules/testing.mdc`
- `.cursor/rules/git-workflow.mdc`
- `docs/ARCHITECTURE.md`
- `docs/TASK_PLAN.md`
- `docs/API_CONTRACT.md`
- `docs/TRACEABILITY.md`
- `docs/MANUAL_VALIDATION.md`

## Forma Correcta de Pedir Trabajo

Cada prompt debe indicar:

- fase concreta;
- objetivo;
- archivos esperados;
- tests esperados;
- que no se cambie la arquitectura;
- que se resuman cambios y como probar.

## Flujo Git (main + develop)

Repositorio en la nube: [ivnamo/nunsysIA](https://github.com/ivnamo/nunsysIA).

| Rama | Uso |
|------|-----|
| `develop` | Trabajo diario e integracion por fases |
| `main` | Estado estable, demo y entregas |
| `feature/*` | Tareas acotadas desde `develop` |

Flujo: `feature/*` -> `develop` -> `main` (solo cuando la fase cumpla criterios o se acuerde entrega).

Detalle completo en `.cursor/rules/git-workflow.mdc`.

## Despues de Cada Fase

- Ejecutar tests relevantes.
- Resultado actual de la suite versionada: `175 passed, 2 warnings`.
- Revisar archivos tocados.
- Confirmar que no se agregaron frameworks alternativos.
- Confirmar que no se mezclo logica de negocio en routes.
- Actualizar README o docs si hay decisiones nuevas.

## Reviews

Solicitar revisiones criticas, no solo validaciones superficiales.

El review debe comprobar:

- separacion de responsabilidades;
- trazabilidad;
- schemas;
- tests;
- errores controlados;
- desviaciones de arquitectura.

## Debugging

Al depurar:

- leer el error completo;
- identificar causa raiz;
- aplicar fix minimo;
- no refactorizar modulos no relacionados;
- agregar test de regresion si procede.

## Cambios Masivos

No aceptar cambios masivos sin revisar. Si Cursor propone reescrituras grandes, pedir que divida en pasos pequenos.

## Documentacion

Mantener decisiones en README o docs. La prueba tecnica evalua tambien criterio arquitectonico, no solo codigo.
