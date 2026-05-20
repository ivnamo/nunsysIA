# Trazabilidad

## Que es una traza

Una traza es el registro estructurado de lo que hizo el sistema para responder una pregunta: fuentes consultadas, tools ejecutadas, argumentos principales, resultado resumido, errores y estado final.

La traza debe servir para auditar el comportamiento sin exponer razonamiento interno sensible.

## Campos por Tool Call

Cada llamada a tool debe guardar:

- `tool`: nombre de la tool.
- `args`: argumentos relevantes y sanitizados.
- `status`: `success`, `error` o `skipped`.
- `output_summary`: resumen breve del resultado.
- `error`: resumen del error si aplica.
- `duration_ms`: duracion si esta disponible.
- `source`: fuente asociada: `ERP`, `Produccion`, `Documentos` o `Memoria`.

## Campos Devueltos al Usuario

La API debe devolver:

- `answer`
- `sources`
- `reasoning`
- `tool_calls`
- `fallbacks`: lista explicita de rutas `FALLBACK_*` usadas durante la ejecucion
- `status`
- `confidence` cuando sea posible
- `data` opcional como resumen publico de evidencias, nunca como volcado raw de filas internas

## Reasoning Visible vs Razonamiento Interno

Reasoning visible:

- resumen corto de pasos ejecutados;
- fuentes usadas;
- logica de combinacion de datos;
- apto para auditoria.

Razonamiento interno:

- deliberacion paso a paso del modelo;
- chain-of-thought;
- prompts internos;
- contenido sensible.

El razonamiento interno no debe devolverse al usuario.

## Ejemplo ERP + Produccion

```json
{
  "sources": ["ERP", "Produccion"],
  "reasoning": [
    "Se consulto ERP para obtener pedidos pendientes del cliente ALFKI.",
    "Se consulto produccion para obtener el estado de esos pedidos.",
    "Se fusionaron pedidos ERP con estados productivos."
  ],
  "tool_calls": [
    {
      "tool": "ERPTool",
      "args": {"customer_id": "ALFKI"},
      "status": "success",
      "output_summary": "2 pedidos pendientes encontrados",
      "source": "ERP"
    },
    {
      "tool": "ProductionAPITool",
      "args": {"order_id": 10248},
      "status": "success",
      "output_summary": "Estado de produccion in_progress",
      "source": "Produccion"
    },
    {
      "tool": "ProductionAPITool",
      "args": {"order_id": 10252},
      "status": "success",
      "output_summary": "Estado de produccion blocked",
      "source": "Produccion"
    }
  ],
  "fallbacks": [
    "FALLBACK_PLANNER_RULE_BASED: LLM planner no configurado; plan creado por reglas.",
    "FALLBACK_FINAL_RESPONSE_DETERMINISTIC: LLM final no configurado; respuesta construida por reglas."
  ],
  "status": "completed"
}
```

## Ejemplo RAG

```json
{
  "sources": ["Documentos"],
  "reasoning": [
    "Se recuperaron chunks relevantes del documento contrato.pdf.",
    "La respuesta se genero solo con el contexto recuperado."
  ],
  "tool_calls": [
    {
      "tool": "DocumentRAGTool",
      "args": {"query": "penalizacion por retrasos"},
      "status": "success",
      "output_summary": "3 chunks recuperados de contrato.pdf",
      "source": "Documentos"
    }
  ],
  "fallbacks": [
    "FALLBACK_VECTOR_STORE_IN_MEMORY: ChromaDB no disponible o no usado; retrieval en memoria del proceso.",
    "FALLBACK_EMBEDDINGS_DETERMINISTIC: embeddings locales deterministas; no se esta usando proveedor externo."
  ],
  "status": "completed"
}
```

## Estados Posibles

- `completed`: respuesta completa.
- `partial_answer`: respuesta parcial por fuente no disponible o informacion incompleta.
- `insufficient_context`: no hay contexto suficiente para responder sin inventar.
- `tool_error`: fallo controlado de una tool.
- `failed`: fallo no recuperable.
- `unsupported`: pregunta fuera del alcance de la POC actual.

## Reglas de Seguridad

- No ocultar fallbacks: si se usa una ruta alternativa, debe aparecer en `fallbacks` o en la salida visible de Chainlit.
- Sanitizar argumentos y errores.
- No incluir credenciales.
- No incluir connection strings.
- No incluir prompts internos.
- No incluir chain-of-thought.
- No devolver filas raw, objetos internos de LangChain/LangGraph/ChromaDB ni respuestas completas de servicios internos en `data`.
- Limitar `reasoning` a pasos visibles auditables: fuente consultada, accion ejecutada y criterio de combinacion de datos.

## Resumen Publico de Evidencias

El campo `data` puede usarse para facilitar demo y auditoria, pero debe contener solo contadores e identificadores no sensibles. Ejemplos permitidos:

- `erp_orders_count`
- `erp_order_ids`
- `production_statuses_count`
- `production_order_ids`
- `customers_resolved_count`
- `period`
- `rag.status`
- `rag.chunks_count`
- `rag.documents`
- `rag.citations` con `filename`, `page`, `chunk_id` y `score`
- `rag.fallbacks`

No debe contener importes detallados, textos completos de chunks, connection strings, errores raw, prompts ni objetos internos.

Las citas documentales por chunk se devuelven en `data.rag.citations`. No deben incluir texto completo del chunk: solo metadatos publicos y score para auditoria.
