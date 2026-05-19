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

Request:

```json
{
  "question": "Que pedidos pendientes tiene el cliente ALFKI y en que estado de produccion estan?",
  "conversation_id": "demo-001"
}
```

Response `200`:

```json
{
  "answer": "El cliente ALFKI tiene 3 pedidos pendientes...",
  "sources": ["ERP", "Produccion"],
  "reasoning": [
    "Consulta ERP para pedidos pendientes",
    "Consulta API de produccion usando order_ids",
    "Fusion de resultados ERP + produccion"
  ],
  "tool_calls": [
    {
      "tool": "ERPTool",
      "args": {
        "customer_id": "ALFKI"
      },
      "status": "success",
      "output_summary": "3 pedidos encontrados"
    }
  ],
  "confidence": 0.86,
  "status": "completed"
}
```

Estados posibles:

- `completed`
- `partial_answer`
- `insufficient_context`
- `tool_error`
- `failed`

Errores posibles:

- `400`: request invalido.
- `422`: validacion Pydantic.
- `500`: error interno controlado.

## `POST /api/documents/upload`

Descripcion: sube un PDF para indexarlo en ChromaDB.

Request: `multipart/form-data`.

Campo esperado:

- `file`: documento PDF.

Response `201`:

```json
{
  "document_id": "doc_123",
  "filename": "contrato.pdf",
  "status": "indexed",
  "chunks_indexed": 24
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
  ]
}
```

Errores posibles:

- `500`: error interno controlado.

## Reglas Generales

- No devolver objetos internos de LangChain, LangGraph o ChromaDB.
- No devolver secretos.
- Mantener respuestas compatibles con Pydantic.
- Los errores deben ser comprensibles y trazables.
