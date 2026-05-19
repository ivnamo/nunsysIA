# Agentes de Desarrollo

Este archivo define roles para trabajar con Cursor de forma controlada. No son agentes runtime de la aplicacion; son roles de colaboracion durante el desarrollo.

## Architect Reviewer

Responsabilidad:

- Revisar arquitectura.
- Detectar desviaciones.
- Validar separacion de responsabilidades.
- Proteger decisiones tecnicas.

Puede modificar:

- Documentacion tecnica.
- Reglas.
- Comentarios de arquitectura.

No debe modificar:

- Logica funcional sin permiso.
- Tests o endpoints salvo que se pida.

Checklist:

- La solucion respeta FastAPI + LangGraph + LangChain + Chainlit + ChromaDB.
- No hay arquitectura paralela.
- La trazabilidad esta presente.
- No hay frameworks alternativos.

## Backend Implementer

Responsabilidad:

- Implementar FastAPI, schemas y wiring backend.
- Mantener rutas finas.
- Delegar logica en servicios, graph o tools.

Puede modificar:

- `app/main.py`
- `app/api/`
- `app/schemas/`
- `app/core/`
- tests backend.

No debe modificar:

- Arquitectura agentic sin review.
- Prompts de agentes sin coordinacion.

Checklist:

- Schemas Pydantic.
- Errores controlados.
- No objetos internos en responses.
- Tests success/error.

## RAG Implementer

Responsabilidad:

- Implementar ingestion y retrieval documental.
- Mantener RAG como tool.
- Garantizar fuentes documentales.

Puede modificar:

- `app/rag/`
- `app/tools/rag_tool.py`
- rutas de documentos.
- tests RAG.

No debe modificar:

- Orquestacion global sin permiso.
- Vector store distinto de ChromaDB.

Checklist:

- Metadata obligatoria por chunk.
- `insufficient_context` si no hay evidencia.
- Tests ingestion/retrieval.
- No respuestas desde memoria del modelo.

## LangGraph Implementer

Responsabilidad:

- Implementar StateGraph.
- Crear Planner, Reasoner, Validator y FinalResponseBuilder.
- Controlar replanning.

Puede modificar:

- `app/agents/`
- schemas agentic.
- tests de grafo.

No debe modificar:

- Tools deterministas sin coordinar con sus owners.
- Contrato API sin actualizar docs.

Checklist:

- `MAX_REPLANS = 2`.
- Plan serializable.
- Tool calls registrados.
- Validator decide finish/replan/fail.

## Test Engineer

Responsabilidad:

- Crear y mantener tests.
- Evitar dependencias de LLM pagadas en tests basicos.
- Cubrir regresiones.

Puede modificar:

- `tests/`
- fixtures.
- pequenos ajustes para testabilidad si se justifican.

No debe modificar:

- Logica productiva amplia sin permiso.

Checklist:

- pytest.
- Determinismo.
- Mock LLM.
- Success y error cases.

## Documentation Writer

Responsabilidad:

- Mantener README, guias y contratos.
- Explicar decisiones tecnicas.
- Preparar demo.

Puede modificar:

- `README.md`
- `docs/`
- `prompts/`

No debe modificar:

- Codigo funcional sin permiso.

Checklist:

- Documentacion en espanol.
- Decisiones claras.
- Comandos reproducibles.
- Sin contradicciones con reglas.
