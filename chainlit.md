# nunsysIA

Interfaz conversacional de la POC agentic empresarial.

Permite consultar el backend `POST /api/query`, adjuntar PDFs al espacio documental y revisar fuentes, pasos ejecutados, tool calls, citas documentales y fallbacks.

Comandos utiles:

- `/documentos`: lista los documentos indexados en el backend.

La memoria conversacional se mantiene por sesion de Chainlit mediante `conversation_id` y conserva las ultimas 5 interacciones del proceso FastAPI actual.
