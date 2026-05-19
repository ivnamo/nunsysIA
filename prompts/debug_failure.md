# Prompt: Depurar fallo

Actua como debugger senior.

Contexto:

- Proyecto FastAPI + LangGraph + LangChain + Chainlit + ChromaDB.
- No refactorices partes no relacionadas.
- No cambies arquitectura.

Entrada:

Pego a continuacion error, logs o test fallido:

```text
[PEGAR ERROR]
```

Tarea:

- Lee el error completo.
- Identifica causa raiz probable.
- Propone el fix minimo.
- Aplica solo el cambio necesario si se autoriza.
- Anade test de regresion si procede.
- Explica como validar.

Restricciones:

- No reescribas media app.
- No ocultes errores con try/except genericos.
- No elimines trazabilidad.
- No introduzcas llamadas pagadas en tests basicos.
