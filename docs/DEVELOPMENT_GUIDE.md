# Guia de Desarrollo con Cursor

## Principio Principal

No pedir a Cursor "haz toda la app". Trabajar por fases pequenas, verificables y alineadas con las reglas del proyecto.

## Antes de Implementar

Leer siempre:

- `.cursor/rules/project.mdc`
- `.cursor/rules/architecture.mdc`
- `.cursor/rules/backend.mdc`
- `.cursor/rules/agents.mdc`
- `.cursor/rules/rag.mdc`
- `.cursor/rules/testing.mdc`
- `docs/ARCHITECTURE.md`
- `docs/TASK_PLAN.md`
- `docs/API_CONTRACT.md`
- `docs/TRACEABILITY.md`

## Forma Correcta de Pedir Trabajo

Cada prompt debe indicar:

- fase concreta;
- objetivo;
- archivos esperados;
- tests esperados;
- que no se cambie la arquitectura;
- que se resuman cambios y como probar.

## Despues de Cada Fase

- Ejecutar tests relevantes.
- Revisar archivos tocados.
- Confirmar que no se agregaron frameworks alternativos.
- Confirmar que no se mezclo logica de negocio en routes.
- Actualizar README o docs si hay decisiones nuevas.

## Reviews

Pedir reviews criticos, no solo validaciones superficiales.

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
- no refactorizar media app;
- agregar test de regresion si procede.

## Cambios Masivos

No aceptar cambios masivos sin revisar. Si Cursor propone reescrituras grandes, pedir que divida en pasos pequenos.

## Documentacion

Mantener decisiones en README o docs. La prueba tecnica evalua tambien criterio arquitectonico, no solo codigo.
