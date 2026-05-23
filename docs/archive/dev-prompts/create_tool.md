# Prompt: Crear una LangChain Tool

Actua como especialista en LangChain tools.

Objetivo:

Crear la tool: `[NOMBRE_TOOL]`.

Antes de implementar, lee:

- `.cursor/rules/project.mdc`
- `.cursor/rules/agents.mdc`
- `.cursor/rules/testing.mdc`
- `docs/TRACEABILITY.md`

Requisitos:

- Interfaz clara.
- Input con Pydantic.
- Output con Pydantic o dict serializable.
- No inventar datos.
- No devolver texto narrativo si la tool debe devolver datos.
- Registrar tool call para trazabilidad.
- Manejar errores controlados.
- Crear tests success/error.

Entrega:

- Archivos tocados.
- Schema de input/output.
- Ejemplo de uso.
- Tests creados.
- Como probar.
