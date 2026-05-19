# Prompt: Review critico de codigo

Actua como arquitecto senior y reviewer critico.

Lee:

- `.cursor/rules/project.mdc`
- `.cursor/rules/architecture.mdc`
- `.cursor/rules/backend.mdc`
- `.cursor/rules/agents.mdc`
- `.cursor/rules/rag.mdc`
- `.cursor/rules/testing.mdc`
- `docs/ARCHITECTURE.md`
- `docs/API_CONTRACT.md`
- `docs/TRACEABILITY.md`

Revisa el codigo actual sin modificarlo salvo que se pida explicitamente.

Evalua:

- desviaciones de arquitectura;
- separacion de responsabilidades;
- uso correcto de FastAPI, LangGraph, LangChain y Pydantic;
- trazabilidad;
- manejo de errores;
- tests;
- riesgo de alucinacion o datos inventados;
- acoplamientos innecesarios.

Formato de respuesta:

1. Hallazgos criticos.
2. Hallazgos medios.
3. Mejoras recomendadas.
4. Tests faltantes.
5. Veredicto: listo / no listo para continuar.
