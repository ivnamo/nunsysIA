# Trazabilidad

## Que es una traza

Una traza es el registro estructurado de lo que hizo el sistema para responder una pregunta: fuentes consultadas, tools ejecutadas, argumentos principales, resultado resumido, errores y estado final.

La traza debe servir para auditar el comportamiento sin exponer razonamiento interno sensible.

## Campos por Tool Call

Cada llamada a tool debe guardar:

- `tool`: nombre de la tool.
- `action`: accion interna ejecutada cuando conviene exponerla para auditoria; puede ser `null` en llamadas simples.
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
- `failure_reason` cuando el estado final explique una salida parcial, fallo o contexto insuficiente

Cuando el grafo solicita replanning, `data.replanning` debe resumirlo de forma
auditable sin exponer planes raw, prompts ni razonamiento interno.

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
      "action": null,
      "args": {"customer_id": "ALFKI"},
      "status": "success",
      "output_summary": "2 pedidos pendientes encontrados",
      "source": "ERP"
    },
    {
      "tool": "ProductionAPITool",
      "action": null,
      "args": {"order_id": 10248},
      "status": "success",
      "output_summary": "Estado de produccion in_progress",
      "source": "Produccion"
    },
    {
      "tool": "ProductionAPITool",
      "action": null,
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
      "action": null,
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

## Ejemplo Memoria Conversacional

```json
{
  "sources": ["Memoria", "ERP", "Produccion"],
  "reasoning": [
    "Consulta memoria conversacional",
    "Consulta ERP de pedidos pendientes",
    "Consulta API de produccion para pedido 10248",
    "Consulta API de produccion para pedido 10252"
  ],
  "tool_calls": [
    {
      "tool": "MemoryTool",
      "action": null,
      "args": {"query": "Y en que estado estan?", "max_turns": 5},
      "status": "success",
      "output_summary": "Memoria conversacional: 1 interacciones recuperadas",
      "source": "Memoria"
    }
  ],
  "status": "completed"
}
```

La memoria solo resuelve referencias conversacionales. Si la respuesta requiere datos de negocio actuales, deben aparecer tambien las tools deterministas correspondientes.

## Ejemplo Follow-Up Economico

```json
{
  "sources": ["Memoria", "ERP"],
  "reasoning": [
    "Consulta memoria conversacional",
    "Calcula importe ERP para pedido 10252"
  ],
  "tool_calls": [
    {
      "tool": "MemoryTool",
      "action": null,
      "args": {"query": "Cual es el impacto economico de esos?", "max_turns": 5},
      "status": "success",
      "output_summary": "Memoria conversacional: 1 interacciones recuperadas",
      "source": "Memoria"
    },
    {
      "tool": "ERPTool",
      "action": "calculate_order_amount",
      "args": {"order_id": 10252},
      "status": "success",
      "output_summary": "Importe del pedido 10252: 1863.00",
      "source": "ERP"
    }
  ],
  "data": {
    "memory": {
      "status": "found",
      "turns_count": 1,
      "customer_id": "ALFKI",
      "order_ids": [10252]
    },
    "order_amounts_count": 1,
    "order_amount_order_ids": [10252],
    "economic_impact_total": "1863.00"
  },
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
- `needs_clarification`: pregunta de dominio con datos insuficientes para
  consultar sin inventar. No debe ejecutar tools; debe pedir una aclaracion
  concreta.

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
- `rag.citations[].text_preview` solo cuando la UI lo pide explicitamente,
  como vista previa truncada para auditoria visual
- `rag.fallbacks`
- `memory.status`
- `memory.turns_count`
- `memory.customer_id`
- `memory.order_ids`
- `order_amounts_count`
- `order_amount_order_ids`
- `economic_impact_total`
- `replanning.replans_count`
- `replanning.max_replans`
- `replanning.events[]` con `attempt`, `decision`, `status`, `failure_reason`
  sanitizado y `max_replans`

No debe contener lineas raw de pedido, textos completos de chunks, connection strings, errores raw, prompts ni objetos internos. Para impacto economico se permiten IDs de pedido, conteos y total agregado como evidencia publica.

Las citas documentales por chunk se devuelven en `data.rag.citations`. Por defecto no deben incluir texto del chunk: solo metadatos publicos y score para auditoria. La UI puede solicitar `text_preview` truncado para desplegar una evidencia verificable sin convertir `data` en un volcado raw.

Los eventos de replanning deben explicar que hubo un replan y por que, pero no
deben incluir el plan completo, inputs raw de tools, prompts ni deliberacion del
modelo.
