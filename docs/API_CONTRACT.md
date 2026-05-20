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

La respuesta puede estar redactada por el `FinalResponseBuilder` con LLM controlado, pero siempre debe respetar el mismo schema y usar solo evidencias devueltas por tools. Si el LLM no es seguro, se devuelve la respuesta determinista y el campo `fallbacks` debe indicar `FALLBACK`.

Request:

```json
{
  "question": "Que pedidos pendientes tiene el cliente ALFKI y en que estado de produccion estan?",
  "conversation_id": "demo-001"
}
```

El repositorio mantiene este request de demo en `query.json`.

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

## `POST /api/documents/upload`

Descripcion: sube un PDF para indexarlo en el vector store documental. En local puede usarse el fallback en memoria si ChromaDB no esta instalado o disponible.

Request principal: `multipart/form-data`.

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
- En respuestas RAG, `data.rag.documents` resume los documentos usados y `data.rag.citations` expone `filename`, `page`, `chunk_id` y `score` por chunk recuperado.
- No devolver secretos.
- Mantener respuestas compatibles con Pydantic.
- Los errores deben ser comprensibles y trazables.
