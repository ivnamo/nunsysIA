## Validacion beta obligatoria automatizada

Fecha de ejecucion: 2026-05-22 20:27:22

- Resultado global: PASS=5, PARTIAL=0, FAIL=0, BLOCKER=0.
Runtime:

- Flujo experimental DeepAgents sidecar con `DeepAgentsQueryService`.
- DeepAgents invoca el workflow legacy como tool unica auditable.
- LLM real configurado via `.env` y modelo Deep Agents via `DEEPAGENTS_MODEL`.
- Embeddings reales del proveedor configurado via `.env`.
- ChromaDB persistente local obligatorio para el espacio documental.
- ERP SQLite seed en memoria con `check_same_thread=False`.
- Production API mockeada en proceso.
- PDFs v2 generados desde `scripts/generate_sample_pdfs.py`.

### BT-08 - PASS - Mixta: penalizaciones por pedido

Pregunta ejecutada: `en funcion de los pedidos y su estado dime que penalizaciones vamos a tener en cada uno`

Resultado esperado desde el evaluador: Debe combinar pedidos ERP, estado de produccion y reglas documentales.

Respuesta exacta visible en Chainlit:

```markdown
Con los datos disponibles, esta es la evaluacion de penalizaciones por pedido:

| Pedido | Cliente | Estado | Penalizacion |
| --- | --- | --- | --- |
| 10248 | Alfreds Futterkiste | en curso | No aplicable con los datos disponibles |
| 10252 | Alfreds Futterkiste | bloqueado (Falta de material) | No aplicable segun la documentacion consultada |
| 10255 | Alfreds Futterkiste | finalizado | No aplicable; consta enviado antes del plazo requerido |
| 10301 | Ana Trujillo Emparedados y helados | retrasado (Averia en linea de produccion) | No aplicable segun la documentacion consultada |
| 10312 | Bon app | bloqueado (Falta de capacidad) | No aplicable segun la documentacion consultada |

El principal punto de atencion es el seguimiento operativo de los pedidos bloqueados, retrasados o pendientes de datos antes de comunicar una penalizacion.

Estado: `completed` | confianza: `0.90`

**Fuentes**
- ERP
- Produccion
- Documentos

**Citas documentales**
- `v2_anexo_penalizaciones_sla.pdf` - pagina `3` - chunk `doc_62fde8b1bfc3_p3_c1` - score `0.7716`
- `v2_contrato_marco_logistica_2026.pdf` - pagina `2` - chunk `doc_500273279949_p2_c2` - score `0.7641`
- `v2_procedimiento_produccion_bloqueos.pdf` - pagina `2` - chunk `doc_d1521faeb9fd_p2_c1` - score `0.7598`
- `v2_anexo_penalizaciones_sla.pdf` - pagina `2` - chunk `doc_62fde8b1bfc3_p2_c1` - score `0.7591`
- `v2_anexo_penalizaciones_sla.pdf` - pagina `1` - chunk `doc_62fde8b1bfc3_p1_c1` - score `0.7542`

**Pasos ejecutados**
1. Consulta ERP de pedidos por mes
2. Consulta API de produccion para pedido 10248
3. Consulta API de produccion para pedido 10252
4. Consulta API de produccion para pedido 10255
5. Consulta API de produccion para pedido 10301
6. Consulta API de produccion para pedido 10312
7. Consulta RAG documental con chunks recuperados

**Tool calls**
- `ERPTool.get_orders_by_month` [success]: 5 pedidos encontrados para el mes
- `ProductionAPITool.get_status_for_erp_orders` [success]: Estado de produccion in_progress
- `ProductionAPITool.get_status_for_erp_orders` [success]: Estado de produccion blocked
- `ProductionAPITool.get_status_for_erp_orders` [success]: Estado de produccion finished
- `ProductionAPITool.get_status_for_erp_orders` [success]: Estado de produccion delayed
- `ProductionAPITool.get_status_for_erp_orders` [success]: Estado de produccion blocked
- `DocumentRAGTool.query` [success]: 5 chunks recuperados de v2_anexo_penalizaciones_sla.pdf, v2_contrato_marco_logistica_2026.pdf, v2_procedimiento_produccion_bloqueos.pdf
```

Evidencia tecnica resumida:

```json
{
  "status": "completed",
  "sources": [
    "ERP",
    "Produccion",
    "Documentos"
  ],
  "tool_calls": [
    {
      "tool": "ERPTool",
      "action": "get_orders_by_month",
      "status": "success",
      "source": "ERP",
      "args": {
        "year": 2026,
        "month": 5
      },
      "output_summary": "5 pedidos encontrados para el mes",
      "error": null
    },
    {
      "tool": "ProductionAPITool",
      "action": "get_status_for_erp_orders",
      "status": "success",
      "source": "Produccion",
      "args": {
        "order_id": 10248
      },
      "output_summary": "Estado de produccion in_progress",
      "error": null
    },
    {
      "tool": "ProductionAPITool",
      "action": "get_status_for_erp_orders",
      "status": "success",
      "source": "Produccion",
      "args": {
        "order_id": 10252
      },
      "output_summary": "Estado de produccion blocked",
      "error": null
    },
    {
      "tool": "ProductionAPITool",
      "action": "get_status_for_erp_orders",
      "status": "success",
      "source": "Produccion",
      "args": {
        "order_id": 10255
      },
      "output_summary": "Estado de produccion finished",
      "error": null
    },
    {
      "tool": "ProductionAPITool",
      "action": "get_status_for_erp_orders",
      "status": "success",
      "source": "Produccion",
      "args": {
        "order_id": 10301
      },
      "output_summary": "Estado de produccion delayed",
      "error": null
    },
    {
      "tool": "ProductionAPITool",
      "action": "get_status_for_erp_orders",
      "status": "success",
      "source": "Produccion",
      "args": {
        "order_id": 10312
      },
      "output_summary": "Estado de produccion blocked",
      "error": null
    },
    {
      "tool": "DocumentRAGTool",
      "action": "query",
      "status": "success",
      "source": "Documentos",
      "args": {
        "query": "penalizaciones por retrasos no aplicacion bloqueo produccion falta material falta capacidad averia linea",
        "top_k": 5,
        "min_score": 0.2,
        "filename": null
      },
      "output_summary": "5 chunks recuperados de v2_anexo_penalizaciones_sla.pdf, v2_contrato_marco_logistica_2026.pdf, v2_procedimiento_produccion_bloqueos.pdf",
      "error": null
    }
  ],
  "fallbacks": [],
  "data": {
    "erp_orders_count": 5,
    "erp_order_ids": [
      10248,
      10252,
      10255,
      10301,
      10312
    ],
    "production_statuses_count": 5,
    "period": {
      "year": 2026,
      "month": 5
    },
    "rag": {
      "status": "completed",
      "chunks_count": 5,
      "documents": [
        "v2_anexo_penalizaciones_sla.pdf",
        "v2_contrato_marco_logistica_2026.pdf",
        "v2_procedimiento_produccion_bloqueos.pdf"
      ],
      "citations": [
        {
          "filename": "v2_anexo_penalizaciones_sla.pdf",
          "page": 3,
          "chunk_id": "doc_62fde8b1bfc3_p3_c1",
          "score": 0.7716
        },
        {
          "filename": "v2_contrato_marco_logistica_2026.pdf",
          "page": 2,
          "chunk_id": "doc_500273279949_p2_c2",
          "score": 0.7641
        },
        {
          "filename": "v2_procedimiento_produccion_bloqueos.pdf",
          "page": 2,
          "chunk_id": "doc_d1521faeb9fd_p2_c1",
          "score": 0.7598
        },
        {
          "filename": "v2_anexo_penalizaciones_sla.pdf",
          "page": 2,
          "chunk_id": "doc_62fde8b1bfc3_p2_c1",
          "score": 0.7591
        },
        {
          "filename": "v2_anexo_penalizaciones_sla.pdf",
          "page": 1,
          "chunk_id": "doc_62fde8b1bfc3_p1_c1",
          "score": 0.7542
        }
      ]
    }
  },
  "failure_reason": null
}
```

Veredicto: `PASS`

### BT-09 - PASS - Memoria conversacional

Turno 1: `Que pedidos pendientes tiene el cliente ALFKI?`

Resultado esperado desde el evaluador: Debe resolver referencias conversacionales sin usar memoria como fuente de verdad de negocio.

Respuesta exacta visible en Chainlit:

```markdown
El cliente ALFKI tiene 2 pedidos pendientes:

| Pedido | Estado ERP |
| --- | --- |
| 10248 | Pendiente |
| 10252 | Pendiente |

Estado: `completed` | confianza: `0.90`

**Fuentes**
- ERP

**Pasos ejecutados**
1. Consulta ERP de pedidos pendientes

**Tool calls**
- `ERPTool.get_pending_orders_by_customer` [success]: 2 pedidos pendientes encontrados
```

Evidencia tecnica resumida:

```json
{
  "status": "completed",
  "sources": [
    "ERP"
  ],
  "tool_calls": [
    {
      "tool": "ERPTool",
      "action": "get_pending_orders_by_customer",
      "status": "success",
      "source": "ERP",
      "args": {
        "customer_id": "ALFKI"
      },
      "output_summary": "2 pedidos pendientes encontrados",
      "error": null
    }
  ],
  "fallbacks": [],
  "data": {
    "erp_orders_count": 2,
    "erp_order_ids": [
      10248,
      10252
    ]
  },
  "failure_reason": null
}
```

Turno 2: `Y cuales de esos pedidos estan bloqueados?`

Resultado esperado desde el evaluador: Debe resolver referencias conversacionales sin usar memoria como fuente de verdad de negocio.

Respuesta exacta visible en Chainlit:

```markdown
Hay pedidos bloqueados en produccion:

| Pedido | Cliente | Estado produccion | Motivo |
| --- | --- | --- | --- |
| 10252 | ALFKI - Alfreds Futterkiste | Bloqueado | Falta de material |

El siguiente punto de atencion es el pedido 10252.

Estado: `completed` | confianza: `0.90`

**Fuentes**
- Memoria
- Produccion
- ERP

**Pasos ejecutados**
1. Consulta memoria conversacional
2. Consulta API de produccion para pedidos referenciados
3. Consulta ERP de cliente para pedido 10252

**Tool calls**
- `MemoryTool.recall` [success]: Memoria conversacional: 1 interacciones recuperadas
- `ProductionAPITool.get_status_for_order_ids` [success]: 1 pedidos de produccion encontrados por ids con estado blocked
- `ERPTool.get_customers_for_production_orders` [success]: Cliente ALFKI encontrado
```

Evidencia tecnica resumida:

```json
{
  "status": "completed",
  "sources": [
    "Memoria",
    "Produccion",
    "ERP"
  ],
  "tool_calls": [
    {
      "tool": "MemoryTool",
      "action": "recall",
      "status": "success",
      "source": "Memoria",
      "args": {
        "query": "Y cuales de esos pedidos estan bloqueados?",
        "max_turns": 5
      },
      "output_summary": "Memoria conversacional: 1 interacciones recuperadas",
      "error": null
    },
    {
      "tool": "ProductionAPITool",
      "action": "get_status_for_order_ids",
      "status": "success",
      "source": "Produccion",
      "args": {
        "order_ids": [
          10248,
          10252
        ],
        "status": "blocked"
      },
      "output_summary": "1 pedidos de produccion encontrados por ids con estado blocked",
      "error": null
    },
    {
      "tool": "ERPTool",
      "action": "get_customers_for_production_orders",
      "status": "success",
      "source": "ERP",
      "args": {
        "order_id": 10252
      },
      "output_summary": "Cliente ALFKI encontrado",
      "error": null
    }
  ],
  "fallbacks": [],
  "data": {
    "production_orders_count": 1,
    "production_order_ids": [
      10252
    ],
    "customers_resolved_count": 1,
    "memory": {
      "status": "found",
      "turns_count": 1,
      "customer_id": "ALFKI",
      "order_ids": [
        10248,
        10252
      ]
    }
  },
  "failure_reason": null
}
```

Turno 3: `Cual es el impacto economico de esos?`

Resultado esperado desde el evaluador: Debe resolver referencias conversacionales sin usar memoria como fuente de verdad de negocio.

Respuesta exacta visible en Chainlit:

```markdown
Con los datos disponibles, el impacto economico del pedido referenciado es 10252: 1863.00.

Estado: `completed` | confianza: `0.90`

**Fuentes**
- Memoria
- ERP

**Pasos ejecutados**
1. Consulta memoria conversacional
2. Consulta ERP de importe para pedido 10252

**Tool calls**
- `MemoryTool.recall` [success]: Memoria conversacional: 2 interacciones recuperadas
- `ERPTool.calculate_order_amount` [success]: Importe calculado
```

Evidencia tecnica resumida:

```json
{
  "status": "completed",
  "sources": [
    "Memoria",
    "ERP"
  ],
  "tool_calls": [
    {
      "tool": "MemoryTool",
      "action": "recall",
      "status": "success",
      "source": "Memoria",
      "args": {
        "query": "Cual es el impacto economico de esos?",
        "max_turns": 5
      },
      "output_summary": "Memoria conversacional: 2 interacciones recuperadas",
      "error": null
    },
    {
      "tool": "ERPTool",
      "action": "calculate_order_amount",
      "status": "success",
      "source": "ERP",
      "args": {
        "order_id": 10252
      },
      "output_summary": "Importe calculado",
      "error": null
    }
  ],
  "fallbacks": [],
  "data": {
    "order_amounts_count": 1,
    "order_amount_order_ids": [
      10252
    ],
    "economic_impact_total": "1863.00",
    "memory": {
      "status": "found",
      "turns_count": 2,
      "customer_id": "ALFKI",
      "order_ids": [
        10252
      ]
    }
  },
  "failure_reason": null
}
```

Veredicto: `PASS`

### BT-10 - PASS - Guardrail RAG

Pregunta ejecutada: `Segun el PDF, que receta de cocina vegana recomienda?`

Resultado esperado desde el evaluador: Debe rechazar por contexto documental insuficiente y no inventar.

Respuesta exacta visible en Chainlit:

```markdown
No he encontrado informacion en los documentos disponibles para responder a esa pregunta con fiabilidad.

Estado: `insufficient_context` | confianza: `0.45`

**Fuentes**
- Documentos

**Pasos ejecutados**
1. Consulta RAG documental con chunks recuperados

**Tool calls**
- `DocumentRAGTool.query` [success]: 0 chunks relevantes recuperados

**Motivo**
No hay chunks documentales relevantes.
```

Evidencia tecnica resumida:

```json
{
  "status": "insufficient_context",
  "sources": [
    "Documentos"
  ],
  "tool_calls": [
    {
      "tool": "DocumentRAGTool",
      "action": "query",
      "status": "success",
      "source": "Documentos",
      "args": {
        "query": "receta de cocina vegana",
        "top_k": 5,
        "min_score": 0.2,
        "filename": null
      },
      "output_summary": "0 chunks relevantes recuperados",
      "error": null
    }
  ],
  "fallbacks": [],
  "data": {
    "rag": {
      "status": "insufficient_context",
      "chunks_count": 0,
      "documents": [],
      "citations": []
    }
  },
  "failure_reason": "No hay chunks documentales relevantes."
}
```

Veredicto: `PASS`

### BT-11 - PASS - Memoria aislada

Pregunta ejecutada: `Y en que estado estan?`

Resultado esperado desde el evaluador: Debe aislar conversaciones por conversation_id y pedir contexto previo.

Respuesta exacta visible en Chainlit:

```markdown
Para resolver a que pedidos te refieres necesito que me indiques el cliente o los numeros de pedido concretos.

Estado: `needs_clarification` | confianza: `0.60`

**Motivo**
Falta informacion concreta para responder sin inventar.
```

Evidencia tecnica resumida:

```json
{
  "status": "needs_clarification",
  "sources": [],
  "tool_calls": [],
  "fallbacks": [],
  "data": null,
  "failure_reason": "Falta informacion concreta para responder sin inventar."
}
```

Veredicto: `PASS`

### BT-V2-07 - PASS - V2: guardrail documental multipagina

Pregunta ejecutada: `Segun los documentos v2, que receta de cocina vegana recomienda para un cliente premium?`

Resultado esperado desde el evaluador: Debe rechazar por contexto documental insuficiente y no inventar.

Respuesta exacta visible en Chainlit:

```markdown
No he encontrado informacion en los documentos disponibles para responder a esa pregunta con fiabilidad.

Estado: `insufficient_context` | confianza: `0.45`

**Fuentes**
- Documentos

**Pasos ejecutados**
1. Consulta RAG documental con chunks recuperados

**Tool calls**
- `DocumentRAGTool.query` [success]: 0 chunks relevantes recuperados

**Motivo**
No hay chunks documentales relevantes.
```

Evidencia tecnica resumida:

```json
{
  "status": "insufficient_context",
  "sources": [
    "Documentos"
  ],
  "tool_calls": [
    {
      "tool": "DocumentRAGTool",
      "action": "query",
      "status": "success",
      "source": "Documentos",
      "args": {
        "query": "receta de cocina vegana para un cliente premium segun los documentos v2",
        "top_k": 5,
        "min_score": 0.2,
        "filename": null
      },
      "output_summary": "0 chunks relevantes recuperados",
      "error": null
    }
  ],
  "fallbacks": [],
  "data": {
    "rag": {
      "status": "insufficient_context",
      "chunks_count": 0,
      "documents": [],
      "citations": []
    }
  },
  "failure_reason": "No hay chunks documentales relevantes."
}
```

Veredicto: `PASS`
