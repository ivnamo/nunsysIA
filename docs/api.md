# API

## `GET /health`

Comprueba que el backend esta vivo.

Response `200`:

```json
{
  "status": "ok"
}
```

## `GET /health/ready`

Comprueba que las dependencias minimas de entrega estan disponibles:

- API mock de produccion.
- ChromaDB o vector store persistente configurado.
- proveedor LLM configurado.
- proveedor de embeddings configurado.

Response `200` si todo esta listo:

```json
{
  "status": "ok",
  "checks": {
    "production_api": {"status": "ok", "detail": "HTTP 200"},
    "chroma": {"status": "ok", "detail": "HTTP 200"},
    "llm_provider": {"status": "ok", "detail": "gemini"},
    "embedding_provider": {"status": "ok", "detail": "gemini"}
  }
}
```

Response `503` si falta alguna dependencia o credencial requerida. La respuesta
mantiene la misma forma con `status="degraded"` y el detalle del check fallido,
sin exponer secretos.

## `POST /api/query`

Endpoint principal de consulta en lenguaje natural.

Request:

```json
{
  "question": "Que pedidos pendientes tiene el cliente ALFKI y en que estado de produccion estan?",
  "conversation_id": "demo-001",
  "mode": "deepagent",
  "include_citation_previews": false
}
```

Campos:

- `question`: obligatorio.
- `conversation_id`: opcional. Permite memoria conversacional in-memory.
- `mode`: opcional. Valores: `deepagent`, `deepagent_sidecar`,
  `legacy_langgraph`. Si se omite, se usa `AGENT_MODE` y su valor por defecto
  es `deepagent`.
- `include_citation_previews`: opcional. Usado por Chainlit para mostrar
  previews truncadas de citas documentales.

Para entrega se debe dejar `AGENT_MODE=deepagent`; los otros modos son
comparativos o legacy.

Response `200`:

```json
{
  "answer": "El cliente ALFKI tiene 2 pedidos pendientes: 10248 en curso y 10252 bloqueado por falta de material.",
  "sources": ["ERP", "Produccion"],
  "reasoning": [
    "Consulta ERP de pedidos pendientes",
    "Consulta API de produccion para pedidos referenciados",
    "Fusion de resultados por order_id"
  ],
  "metadata": {
    "agent_mode": "deepagent",
    "agent_framework": "LangChain DeepAgents"
  },
  "tool_calls": [
    {
      "tool": "ERPTool",
      "action": "get_pending_orders_by_customer",
      "args": {
        "customer_id": "ALFKI"
      },
      "status": "success",
      "output_summary": "2 pedidos pendientes encontrados",
      "error": null,
      "duration_ms": 0,
      "source": "ERP"
    }
  ],
  "fallbacks": [],
  "confidence": 0.75,
  "status": "completed",
  "data": {
    "erp_orders_count": 2,
    "erp_order_ids": [10248, 10252]
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

Errores HTTP principales:

- `400`: modo no soportado o request invalido.
- `422`: validacion Pydantic.
- `502`: fallo de ejecucion DeepAgents.
- `503`: dependencia DeepAgents o proveedor no disponible.
- `500`: error no esperado controlado por el backend.

## `POST /api/documents/upload`

Sube un PDF e indexa sus chunks para RAG.

Request multipart:

```powershell
curl.exe -X POST "http://localhost:8000/api/documents/upload" `
  -F "file=@data/sample_docs/v2_contrato_marco_logistica_2026.pdf;type=application/pdf"
```

Response `201`:

```json
{
  "document_id": "doc_...",
  "filename": "v2_contrato_marco_logistica_2026.pdf",
  "status": "indexed",
  "chunks_indexed": 4,
  "fallbacks": []
}
```

Errores:

- `400`: fichero invalido o no PDF.
- `413`: fichero demasiado grande.
- `422`: PDF sin texto util.
- `500`: error de vector store o embeddings.

## `GET /api/documents`

Lista documentos indexados.

Response `200`:

```json
{
  "documents": [
    {
      "document_id": "doc_...",
      "filename": "v2_contrato_marco_logistica_2026.pdf",
      "uploaded_at": "2026-05-22T20:00:00Z",
      "chunks_indexed": 4
    }
  ],
  "fallbacks": []
}
```

## Endpoints experimentales

Solo para diagnostico y comparativa:

- `POST /api/experimental/deepagents/query`
- `POST /api/experimental/deepagents/tools/query`

Estan deshabilitados por defecto. Para activarlos:

```env
ENABLE_DEEPAGENTS_EXPERIMENT=true
```

No forman parte del flujo principal de entrega.
