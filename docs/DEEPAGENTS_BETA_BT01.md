## Validacion beta obligatoria automatizada

Fecha de ejecucion: 2026-05-22 20:20:16

- Resultado global: PASS=1, PARTIAL=0, FAIL=0, BLOCKER=0.
Runtime:

- Flujo experimental Deep Agents direct-tools con `DeepAgentsToolsQueryService`.
- Deep Agents recibe tools individuales y compuestas de ERP, Produccion, RAG y Memoria.
- `write_todos` queda disponible; filesystem, shell y subagentes quedan excluidos.
- LLM real configurado via `.env` y modelo Deep Agents via `DEEPAGENTS_MODEL`.
- Embeddings reales del proveedor configurado via `.env`.
- ChromaDB persistente local obligatorio para el espacio documental.
- ERP SQLite seed en memoria con `check_same_thread=False`.
- Production API mockeada en proceso.
- PDFs v2 generados desde `scripts/generate_sample_pdfs.py`.

### BT-01 - PASS - ERP + produccion: pendientes ALFKI

Pregunta ejecutada: `Que pedidos pendientes tiene el cliente ALFKI y en que estado de produccion estan?`

Resultado esperado desde el evaluador: Debe listar pedidos pendientes de ALFKI y sus estados de produccion.

Respuesta exacta visible en Chainlit:

```markdown
El cliente **ALFKI** (Alfreds Futterkiste) tiene actualmente **2 pedidos pendientes** en el ERP. A continuación se detalla su estado de producción:

### 1. Pedido ID: 10248
* **Fecha de Pedido:** 2026-05-02
* **Fecha Requerida:** 2026-05-20
* **Importe:** 440.00
* **Estado ERP:** Pendiente (`pending`)
* **Estado de Producción:** En progreso (`in_progress`)
* **Fecha Estimada de Fin:** 2026-05-22

### 2. Pedido ID: 10252
* **Fecha de Pedido:** 2026-05-07
* **Fecha Requerida:** 2026-05-25
* **Importe:** 1863.00
* **Estado ERP:** Pendiente (`pending`)
* **Estado de Producción:** Bloqueado (`blocked`)
* **Motivo del Bloqueo:** Falta de material
* **Fecha Estimada de Fin:** 2026-05-30

Estado: `completed` | confianza: `0.75`

**Fuentes**
- ERP
- Produccion

**Pasos ejecutados**
1. Consulta ERP de pedidos pendientes
2. Consulta API de produccion para pedidos referenciados

**Tool calls**
- `ERPTool.get_pending_orders_by_customer` [success]: 2 pedidos pendientes encontrados
- `ProductionAPITool.get_status_for_order_ids` [success]: 2 pedidos de produccion encontrados por ids
```

Evidencia tecnica resumida:

```json
{
  "status": "completed",
  "sources": [
    "ERP",
    "Produccion"
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
        "status": null
      },
      "output_summary": "2 pedidos de produccion encontrados por ids",
      "error": null
    }
  ],
  "fallbacks": [],
  "data": {
    "erp_orders_count": 2,
    "erp_order_ids": [
      10248,
      10252
    ],
    "production_orders_count": 2,
    "production_order_ids": [
      10248,
      10252
    ],
    "production_statuses_count": 2,
    "deepagents_planning": {
      "todos_used": true,
      "todo_tool_calls_count": 3
    }
  },
  "failure_reason": null
}
```

Veredicto: `PASS`
