# Contrato API

Este documento define los endpoints previstos. Los ejemplos son contratos objetivo y deben mantenerse alineados con los schemas Pydantic.

## `GET /health`

Descripcion: comprueba que el backend esta vivo.

Request: sin body.

Response `200`:

```json
{
  "status": "ok"
}
```

Errores posibles:

- `500`: error interno no esperado.

## `POST /api/query`

Descripcion: recibe una pregunta en lenguaje natural y la procesa mediante el workflow agentic.

La respuesta puede estar redactada por el `FinalResponseBuilder` con LLM controlado, pero siempre debe respetar el mismo schema y usar solo evidencias devueltas por tools. Si la salida del LLM no supera las validaciones de grounding, se devuelve la respuesta determinista y el campo `fallbacks` debe indicar el marcador `FALLBACK_*` correspondiente.

Request:

```json
{
  "question": "Que pedidos pendientes tiene el cliente ALFKI y en que estado de produccion estan?",
  "conversation_id": "demo-001",
  "include_citation_previews": false
}
```

El repositorio mantiene este request de demo en `query.json`.

`conversation_id` permite memoria conversacional en memoria de proceso. El backend conserva las ultimas 5 interacciones de cada conversacion y puede usarlas para resolver follow-ups breves. Si la memoria se consulta, la respuesta incluye fuente `Memoria` y una tool call `MemoryTool`; la memoria no sustituye a ERP, Produccion o Documentos como fuente de datos de negocio actuales.

`include_citation_previews` es opcional y por defecto `false`. La UI Chainlit lo usa para pedir una vista previa truncada del texto de cada chunk citado y poder desplegarla al revisar evidencias. Los clientes API normales deben mantenerlo en `false` salvo que necesiten esa experiencia de auditoria visual.

Los follow-ups con referencias a pedidos concretos pueden generar tool calls internas especializadas, por ejemplo `ProductionAPITool.get_status_for_order_ids` para consultar estados productivos por IDs ya resueltos y `ERPTool.calculate_order_amount` para calcular importes ERP. El contrato mantiene compatibilidad: `tool_calls.action` es opcional, los argumentos se sanitizan y `data` mantiene solo un resumen auditable.

Response `200`:

```json
{
  "answer": "Pedidos del cliente ALFKI: 10248: ERP pendiente, produccion en curso; 10252: ERP pendiente, produccion bloqueado (Falta de material).",
  "sources": ["ERP", "Produccion"],
  "reasoning": [
    "Consulta ERP de pedidos pendientes",
    "Consulta API de produccion para pedido 10248",
    "Consulta API de produccion para pedido 10252"
  ],
  "tool_calls": [
    {
      "tool": "ERPTool",
      "action": null,
      "args": {
        "customer_id": "ALFKI"
      },
      "status": "success",
      "output_summary": "2 pedidos pendientes encontrados",
      "error": null,
      "duration_ms": 0,
      "source": "ERP"
    },
    {
      "tool": "ProductionAPITool",
      "action": null,
      "args": {
        "order_id": 10248
      },
      "status": "success",
      "output_summary": "Estado de produccion in_progress",
      "error": null,
      "duration_ms": 0,
      "source": "Produccion"
    },
    {
      "tool": "ProductionAPITool",
      "action": null,
      "args": {
        "order_id": 10252
      },
      "status": "success",
      "output_summary": "Estado de produccion blocked",
      "error": null,
      "duration_ms": 0,
      "source": "Produccion"
    }
  ],
  "fallbacks": [
    "FALLBACK_PLANNER_RULE_BASED: LLM planner no configurado; plan creado por reglas.",
    "FALLBACK_FINAL_RESPONSE_DETERMINISTIC: LLM final no configurado; respuesta construida por reglas."
  ],
  "confidence": 0.9,
  "status": "completed",
  "data": {
    "erp_orders_count": 2,
    "erp_order_ids": [10248, 10252],
    "production_statuses_count": 2
  },
  "failure_reason": null
}
```

Estados posibles:

- `completed`
- `partial_answer`
- `insufficient_context`
- `tool_error`
- `failed`
- `unsupported`
- `needs_clarification`

`needs_clarification` se usa cuando la pregunta es de dominio, pero falta un
dato imprescindible para consultar sin inventar, por ejemplo cliente, pedido,
periodo o contexto conversacional previo. En ese caso no se ejecutan tools y la
respuesta debe pedir una aclaracion concreta.

Errores posibles:

- `422`: validacion Pydantic.
- `500`: error interno controlado.

En respuestas RAG completadas, `data.rag` debe incluir citas documentales por chunk sin exponer el texto completo del chunk:

```json
{
  "rag": {
    "status": "completed",
    "chunks_count": 2,
    "documents": ["contrato.pdf"],
    "citations": [
      {
        "filename": "contrato.pdf",
        "page": 1,
        "chunk_id": "doc_123_p1_c1",
        "score": 0.9123
      }
    ]
  }
}
```

Si `include_citation_previews=true`, cada cita puede incluir ademas `text_preview`, siempre como vista previa truncada para UI, no como volcado raw del chunk:

```json
{
  "filename": "contrato.pdf",
  "page": 1,
  "chunk_id": "doc_123_p1_c1",
  "score": 0.9123,
  "text_preview": "Fragmento documental truncado usado para verificar la cita..."
}
```

En respuestas que usen memoria conversacional, `data.memory` debe resumir solo metadatos publicos:

```json
{
  "memory": {
    "status": "found",
    "turns_count": 1,
    "customer_id": "ALFKI",
    "order_ids": [10248, 10252]
  }
}
```

En respuestas de impacto economico, `data` puede incluir un resumen publico sin lineas raw de pedido:

```json
{
  "order_amounts_count": 1,
  "order_amount_order_ids": [10252],
  "economic_impact_total": "1863.00"
}
```

Si el grafo solicita replanning, `data.replanning` debe exponer solo un resumen
sanitizado de los intentos:

```json
{
  "replanning": {
    "replans_count": 1,
    "max_replans": 2,
    "events": [
      {
        "attempt": 1,
        "decision": "replan",
        "status": "partial_answer",
        "failure_reason": "Faltan fuentes obligatorias: Produccion.",
        "max_replans": 2
      }
    ]
  }
}
```

No debe incluir planes completos, prompts, chain-of-thought ni payloads raw de
tools.

## `POST /api/documents/upload`

Descripcion: sube un PDF para indexarlo en el vector store documental. En local puede usarse el fallback en memoria si ChromaDB no esta instalado o disponible.

Request principal: `multipart/form-data`, procesado con `UploadFile` de FastAPI.

Campo esperado:

- `file`: documento PDF.

Tambien se acepta un upload directo con `Content-Type: application/pdf`; en ese caso el nombre se puede pasar con `?filename=contrato.pdf` y, si se omite, se usa `document.pdf`.

Response `201`:

```json
{
  "document_id": "doc_123",
  "filename": "contrato.pdf",
  "status": "indexed",
  "chunks_indexed": 24,
  "fallbacks": [
    "FALLBACK_VECTOR_STORE_IN_MEMORY: ChromaDB no disponible o no usado; documentos en memoria del proceso.",
    "FALLBACK_EMBEDDINGS_DETERMINISTIC: embeddings locales deterministas; no se esta usando proveedor externo."
  ]
}
```

Errores posibles:

- `400`: archivo ausente o no PDF.
- `413`: archivo demasiado grande.
- `422`: no se pudo extraer texto util.
- `500`: error de indexacion.

## `GET /api/documents`

Descripcion: lista documentos indexados.

Request: sin body.

Response `200`:

```json
{
  "documents": [
    {
      "document_id": "doc_123",
      "filename": "contrato.pdf",
      "uploaded_at": "2026-05-19T10:30:00Z",
      "chunks_indexed": 24
    }
  ],
  "fallbacks": [
    "FALLBACK_VECTOR_STORE_IN_MEMORY: ChromaDB no disponible o no usado; documentos en memoria del proceso.",
    "FALLBACK_EMBEDDINGS_DETERMINISTIC: embeddings locales deterministas; no se esta usando proveedor externo."
  ]
}
```

Errores posibles:

- `500`: error interno controlado.

## Reglas Generales

- No devolver objetos internos de LangChain, LangGraph o ChromaDB.
- No devolver filas raw de ERP, respuestas raw de produccion ni chunks completos en `data`.
- `data` debe ser un resumen publico de evidencias para auditoria y demo.
- `fallbacks` debe listar cualquier ruta alternativa usada: planner por reglas, respuesta determinista, embeddings deterministas o vector store en memoria.
- En respuestas RAG, `data.rag.documents` resume los documentos usados y `data.rag.citations` expone `filename`, `page`, `chunk_id` y `score` por chunk recuperado. Si `include_citation_previews=true`, puede incluir tambien `text_preview` truncado para la UI.
- En respuestas con memoria, `data.memory` resume conteos e identificadores; no debe exponer todo el historial.
- En respuestas de impacto economico, `data` puede exponer conteos, IDs de pedido y total agregado; no debe exponer lineas raw ni objetos ERP internos.
- No devolver secretos.
- Mantener respuestas compatibles con Pydantic.
- Los errores deben ser comprensibles y trazables.

## Query DSL interna

La Query DSL segura no es un endpoint publico. Existe como contrato interno
validado en `app/tools/query_dsl.py` y como ejecucion aislada en
`ERPQueryTool` / `ProductionQueryTool`. Desde R16 puede ejecutarse dentro de
`POST /api/query` solo cuando el planner produce un plan validado y el reasoner
controla el cruce por `order_id`.

Restricciones actuales:

- ERP: solo `entity="orders"`, filtros `customer_id`, `order_id`,
  `erp_status`, `year`, `month`, y selects publicos `order_id`,
  `customer_id`, `customer_name`, `erp_status`, `order_date`, `amount`.
- Produccion: solo `entity="production_orders"`, filtros `order_id`,
  `production_status`, y selects publicos `order_id`, `production_status`,
  `blocked_reason`, `delay_reason`, `estimated_finish_date`.
- Operadores permitidos: `eq` e `in`.
- `limit` maximo: `50`.
- `order_by` solo puede usar campos allowlist.
- Se rechazan claves extra como `joins`, campos internos, entidades no
  permitidas, operadores desconocidos y valores enumerados invalidos.
- En R16 las consultas DSL se pueden ejecutar desde el flujo agentic con specs
  Pydantic ya validadas. No se anade ningun endpoint publico nuevo ni se
  permite SQL/HTTP libre.
- Las tools DSL devuelven proyecciones de campos publicos seleccionados y tool
  calls trazables; no devuelven filas raw internas.
- Los joins no forman parte de la DSL: el reasoner puede aplicar `join_from`
  como metadato controlado del plan y filtrar la segunda consulta por los
  `order_id` obtenidos de la primera fuente.
