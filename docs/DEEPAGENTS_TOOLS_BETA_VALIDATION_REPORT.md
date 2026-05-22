## Validacion beta obligatoria automatizada

Fecha de ejecucion: 2026-05-22 20:59:21

- Resultado global: PASS=18, PARTIAL=0, FAIL=0, BLOCKER=0.
Runtime:

- Flujo DeepAgents direct-tools con `DeepAgentsToolsQueryService` (base del modo
  principal `deepagent` tras el refactor de router).
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
El cliente ALFKI tiene 2 pedidos pendientes:

| Pedido | Estado ERP | Estado produccion | Observacion |
| --- | --- | --- | --- |
| 10248 | pendiente | en curso | sin bloqueo informado |
| 10252 | pendiente | bloqueado | Falta de material |

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
      "todo_tool_calls_count": 2
    }
  },
  "failure_reason": null
}
```

Veredicto: `PASS`

### BT-02 - PASS - ERP + produccion: bloqueos

Pregunta ejecutada: `Que pedidos estan bloqueados y cual es el motivo?`

Resultado esperado desde el evaluador: Debe listar pedidos bloqueados y motivo, cruzando produccion con ERP.

Respuesta exacta visible en Chainlit:

```markdown
Estos son los estados de produccion de los pedidos referenciados:

| Pedido | Cliente | Estado | Motivo |
| --- | --- | --- | --- |
| 10252 | ALFKI - Alfreds Futterkiste | bloqueado | Falta de material |
| 10312 | BONAP - Bon app | bloqueado | Falta de capacidad |
| 10248 | cliente ERP no resuelto | en curso | sin motivo informado |
| 10255 | cliente ERP no resuelto | finalizado | sin motivo informado |
| 10301 | cliente ERP no resuelto | retrasado | Averia en linea de produccion |

Estado: `completed` | confianza: `0.75`

**Fuentes**
- Produccion
- ERP

**Pasos ejecutados**
1. Consulta API de produccion por estado
2. Consulta ERP de cliente para pedido 10252
3. Consulta ERP de cliente para pedido 10312
4. Consulta API de produccion por estado
5. Consulta ERP mediante filtros seguros

**Tool calls**
- `ProductionAPITool.list_orders` [success]: 2 pedidos de produccion encontrados con estado blocked
- `ERPTool.get_customers_for_production_orders` [success]: Cliente ALFKI encontrado
- `ERPTool.get_customers_for_production_orders` [success]: Cliente BONAP encontrado
- `ProductionAPITool.list_orders` [success]: 5 pedidos de produccion encontrados
- `ERPQueryTool.query_orders` [success]: 2 pedidos ERP encontrados por DSL segura
```

Evidencia tecnica resumida:

```json
{
  "status": "completed",
  "sources": [
    "Produccion",
    "ERP"
  ],
  "tool_calls": [
    {
      "tool": "ProductionAPITool",
      "action": "list_orders",
      "status": "success",
      "source": "Produccion",
      "args": {
        "status": "blocked"
      },
      "output_summary": "2 pedidos de produccion encontrados con estado blocked",
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
    },
    {
      "tool": "ERPTool",
      "action": "get_customers_for_production_orders",
      "status": "success",
      "source": "ERP",
      "args": {
        "order_id": 10312
      },
      "output_summary": "Cliente BONAP encontrado",
      "error": null
    },
    {
      "tool": "ProductionAPITool",
      "action": "list_orders",
      "status": "success",
      "source": "Produccion",
      "args": {
        "status": null
      },
      "output_summary": "5 pedidos de produccion encontrados",
      "error": null
    },
    {
      "tool": "ERPQueryTool",
      "action": "query_orders",
      "status": "success",
      "source": "ERP",
      "args": {
        "entity": "orders",
        "filters": [
          {
            "field": "order_id",
            "operator": "in",
            "value": [
              10252,
              10312
            ]
          }
        ],
        "select": [
          "order_id",
          "customer_id",
          "customer_name",
          "erp_status",
          "order_date",
          "amount"
        ],
        "limit": 20,
        "order_by": null
      },
      "output_summary": "2 pedidos ERP encontrados por DSL segura",
      "error": null
    }
  ],
  "fallbacks": [],
  "data": {
    "erp_query_orders_count": 2,
    "erp_query_order_ids": [
      10252,
      10312
    ],
    "production_orders_count": 5,
    "production_order_ids": [
      10252,
      10312,
      10248,
      10255,
      10301
    ],
    "customers_resolved_count": 2,
    "deepagents_planning": {
      "todos_used": true,
      "todo_tool_calls_count": 3
    }
  },
  "failure_reason": null
}
```

Veredicto: `PASS`

### BT-03 - PASS - ERP + produccion: retrasos

Pregunta ejecutada: `Que clientes tienen pedidos retrasados por problemas de produccion?`

Resultado esperado desde el evaluador: Debe identificar pedidos delayed y cliente ERP asociado.

Respuesta exacta visible en Chainlit:

```markdown
Estos son los estados de produccion de los pedidos referenciados:

| Pedido | Cliente | Estado | Motivo |
| --- | --- | --- | --- |
| 10301 | ANATR - Ana Trujillo Emparedados y helados | retrasado | Averia en linea de produccion |
| 10252 | cliente ERP no resuelto | bloqueado | Falta de material |
| 10312 | cliente ERP no resuelto | bloqueado | Falta de capacidad |

Estado: `completed` | confianza: `0.75`

**Fuentes**
- Produccion
- ERP

**Pasos ejecutados**
1. Consulta API de produccion por estado
2. Consulta ERP de cliente para pedido 10301
3. Consulta Produccion mediante filtros seguros
4. Consulta ERP mediante filtros seguros

**Tool calls**
- `ProductionAPITool.list_orders` [success]: 1 pedidos de produccion encontrados con estado delayed
- `ERPTool.get_customers_for_production_orders` [success]: Cliente ANATR encontrado
- `ProductionQueryTool.query_orders` [success]: 2 pedidos de produccion encontrados por DSL segura
- `ERPQueryTool.query_orders` [success]: 2 pedidos ERP encontrados por DSL segura
```

Evidencia tecnica resumida:

```json
{
  "status": "completed",
  "sources": [
    "Produccion",
    "ERP"
  ],
  "tool_calls": [
    {
      "tool": "ProductionAPITool",
      "action": "list_orders",
      "status": "success",
      "source": "Produccion",
      "args": {
        "status": "delayed"
      },
      "output_summary": "1 pedidos de produccion encontrados con estado delayed",
      "error": null
    },
    {
      "tool": "ERPTool",
      "action": "get_customers_for_production_orders",
      "status": "success",
      "source": "ERP",
      "args": {
        "order_id": 10301
      },
      "output_summary": "Cliente ANATR encontrado",
      "error": null
    },
    {
      "tool": "ProductionQueryTool",
      "action": "query_orders",
      "status": "success",
      "source": "Produccion",
      "args": {
        "entity": "production_orders",
        "filters": [
          {
            "field": "production_status",
            "operator": "eq",
            "value": "blocked"
          }
        ],
        "select": [
          "order_id",
          "production_status",
          "blocked_reason",
          "delay_reason",
          "estimated_finish_date"
        ],
        "limit": 20,
        "order_by": null
      },
      "output_summary": "2 pedidos de produccion encontrados por DSL segura",
      "error": null
    },
    {
      "tool": "ERPQueryTool",
      "action": "query_orders",
      "status": "success",
      "source": "ERP",
      "args": {
        "entity": "orders",
        "filters": [
          {
            "field": "order_id",
            "operator": "in",
            "value": [
              10252,
              10312
            ]
          }
        ],
        "select": [
          "order_id",
          "customer_id",
          "customer_name",
          "erp_status",
          "order_date",
          "amount"
        ],
        "limit": 20,
        "order_by": null
      },
      "output_summary": "2 pedidos ERP encontrados por DSL segura",
      "error": null
    }
  ],
  "fallbacks": [],
  "data": {
    "erp_query_orders_count": 2,
    "erp_query_order_ids": [
      10252,
      10312
    ],
    "production_orders_count": 3,
    "production_order_ids": [
      10301,
      10252,
      10312
    ],
    "production_statuses_count": 2,
    "customers_resolved_count": 1,
    "deepagents_planning": {
      "todos_used": true,
      "todo_tool_calls_count": 3
    }
  },
  "failure_reason": null
}
```

Veredicto: `PASS`

### BT-04 - PASS - ERP + produccion: resumen mensual

Pregunta ejecutada: `Dame un resumen del estado de los pedidos de este mes`

Resultado esperado desde el evaluador: Debe resumir pedidos de mayo de 2026 y su distribucion de estados.

Respuesta exacta visible en Chainlit:

```markdown
En mayo de 2026 hay 5 pedidos ERP. Distribucion por estado de produccion: bloqueado: 2, en curso: 1, finalizado: 1, retrasado: 1.

| Pedido | Estado ERP | Estado produccion |
| --- | --- | --- |
| 10248 | pendiente | en curso |
| 10252 | pendiente | bloqueado |
| 10255 | shipped | finalizado |
| 10301 | pendiente | retrasado |
| 10312 | pendiente | bloqueado |

Periodo auditado: 2026-05.

Estado: `completed` | confianza: `0.75`

**Fuentes**
- ERP
- Produccion

**Pasos ejecutados**
1. Consulta ERP de pedidos por mes
2. Consulta API de produccion para pedidos referenciados
3. Consulta ERP mediante filtros seguros
4. Consulta ERP mediante filtros seguros

**Tool calls**
- `ERPTool.get_orders_by_month` [success]: 5 pedidos encontrados para el mes
- `ProductionAPITool.get_status_for_order_ids` [success]: 5 pedidos de produccion encontrados por ids
- `ERPQueryTool.query_orders` [success]: 5 pedidos ERP encontrados por DSL segura
- `ERPQueryTool.query_orders` [success]: 5 pedidos ERP encontrados por DSL segura
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
      "action": "get_status_for_order_ids",
      "status": "success",
      "source": "Produccion",
      "args": {
        "order_ids": [
          10248,
          10252,
          10255,
          10301,
          10312
        ],
        "status": null
      },
      "output_summary": "5 pedidos de produccion encontrados por ids",
      "error": null
    },
    {
      "tool": "ERPQueryTool",
      "action": "query_orders",
      "status": "success",
      "source": "ERP",
      "args": {
        "entity": "orders",
        "filters": [],
        "select": [
          "order_id",
          "customer_id",
          "customer_name",
          "erp_status",
          "order_date",
          "amount"
        ],
        "limit": 20,
        "order_by": null
      },
      "output_summary": "5 pedidos ERP encontrados por DSL segura",
      "error": null
    },
    {
      "tool": "ERPQueryTool",
      "action": "query_orders",
      "status": "success",
      "source": "ERP",
      "args": {
        "entity": "orders",
        "filters": [
          {
            "field": "year",
            "operator": "eq",
            "value": 2026
          },
          {
            "field": "month",
            "operator": "eq",
            "value": 5
          }
        ],
        "select": [
          "order_id",
          "customer_id",
          "customer_name",
          "erp_status",
          "order_date",
          "amount"
        ],
        "limit": 20,
        "order_by": null
      },
      "output_summary": "5 pedidos ERP encontrados por DSL segura",
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
    "erp_query_orders_count": 5,
    "erp_query_order_ids": [
      10248,
      10252,
      10255,
      10301,
      10312
    ],
    "production_orders_count": 5,
    "production_order_ids": [
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
    "deepagents_planning": {
      "todos_used": true,
      "todo_tool_calls_count": 4
    }
  },
  "failure_reason": null
}
```

Veredicto: `PASS`

### BT-05 - PASS - RAG: plazos de entrega

Pregunta ejecutada: `Que dice el documento sobre plazos de entrega standard?`

Resultado esperado desde el evaluador: Debe recuperar reglas documentales de plazos de entrega.

Respuesta exacta visible en Chainlit:

```markdown
Contrato marco de logistica 2026 - version extendida Pagina 2 de 4 - Plazos, calendarios y excepciones operativas Plazos ordinarios: Los pedidos standard deben entregarse en un plazo maximo de 5 dias laborables desde la liberacion de produccion. Los pedidos urgentes deben entregarse en un plazo maximo de 48 horas. La penalizacion solo procede cuando existe incumplimiento de plazo, causa imputable al operador logistico y evidencia completa en ERP, produccion y prueba de entrega.

Estado: `completed` | confianza: `0.75`

**Fuentes**
- Documentos

**Citas documentales**
- `v2_contrato_marco_logistica_2026.pdf` - pagina `2` - chunk `doc_e17a67f7871f_p2_c1` - score `0.7769`
- `v2_anexo_penalizaciones_sla.pdf` - pagina `1` - chunk `doc_53cc860b79e3_p1_c1` - score `0.7646`
- `v2_contrato_marco_logistica_2026.pdf` - pagina `2` - chunk `doc_e17a67f7871f_p2_c2` - score `0.7544`

**Pasos ejecutados**
1. Consulta RAG documental con chunks recuperados

**Tool calls**
- `DocumentRAGTool.query` [success]: 3 chunks recuperados de v2_anexo_penalizaciones_sla.pdf, v2_contrato_marco_logistica_2026.pdf
```

Evidencia tecnica resumida:

```json
{
  "status": "completed",
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
        "query": "Que dice el documento sobre plazos de entrega standard?",
        "top_k": 3,
        "min_score": 0.2,
        "filename": null
      },
      "output_summary": "3 chunks recuperados de v2_anexo_penalizaciones_sla.pdf, v2_contrato_marco_logistica_2026.pdf",
      "error": null
    }
  ],
  "fallbacks": [],
  "data": {
    "rag": {
      "status": "completed",
      "chunks_count": 3,
      "documents": [
        "v2_anexo_penalizaciones_sla.pdf",
        "v2_contrato_marco_logistica_2026.pdf"
      ],
      "citations": [
        {
          "filename": "v2_contrato_marco_logistica_2026.pdf",
          "page": 2,
          "chunk_id": "doc_e17a67f7871f_p2_c1",
          "score": 0.7769
        },
        {
          "filename": "v2_anexo_penalizaciones_sla.pdf",
          "page": 1,
          "chunk_id": "doc_53cc860b79e3_p1_c1",
          "score": 0.7646
        },
        {
          "filename": "v2_contrato_marco_logistica_2026.pdf",
          "page": 2,
          "chunk_id": "doc_e17a67f7871f_p2_c2",
          "score": 0.7544
        }
      ]
    }
  },
  "failure_reason": null
}
```

Veredicto: `PASS`

### BT-06 - PASS - RAG: resumen del contrato

Pregunta ejecutada: `Resume los puntos clave del contrato`

Resultado esperado desde el evaluador: Debe resumir contrato con citas documentales.

Respuesta exacta visible en Chainlit:

```markdown
Contrato marco de logistica 2026 - version extendida Pagina 1 de 4 - Alcance, definiciones y reglas base Objeto: Este documento regula la preparacion, expedicion, entrega y cierre documental de pedidos comerciales durante 2026. Pedido bloqueado significa que produccion ha detenido la orden por falta de material, falta de capacidad, incidencia de calidad o aprobacion pendiente; para responder consultas de auditoria deben constar order_id, customer_id, cliente, fecha prometida, fecha real, transportista, estado ERP, estado de produccion y causa de desviacion.

Estado: `completed` | confianza: `0.75`

**Fuentes**
- Documentos

**Citas documentales**
- `v2_contrato_marco_logistica_2026.pdf` - pagina `1` - chunk `doc_e17a67f7871f_p1_c1` - score `0.7133`
- `v2_contrato_marco_logistica_2026.pdf` - pagina `3` - chunk `doc_e17a67f7871f_p3_c1` - score `0.7107`
- `v2_contrato_marco_logistica_2026.pdf` - pagina `2` - chunk `doc_e17a67f7871f_p2_c1` - score `0.7053`

**Pasos ejecutados**
1. Consulta RAG documental con chunks recuperados

**Tool calls**
- `DocumentRAGTool.query` [success]: 3 chunks recuperados de v2_contrato_marco_logistica_2026.pdf
```

Evidencia tecnica resumida:

```json
{
  "status": "completed",
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
        "query": "Resume los puntos clave del contrato",
        "top_k": 3,
        "min_score": 0.2,
        "filename": null
      },
      "output_summary": "3 chunks recuperados de v2_contrato_marco_logistica_2026.pdf",
      "error": null
    }
  ],
  "fallbacks": [],
  "data": {
    "rag": {
      "status": "completed",
      "chunks_count": 3,
      "documents": [
        "v2_contrato_marco_logistica_2026.pdf"
      ],
      "citations": [
        {
          "filename": "v2_contrato_marco_logistica_2026.pdf",
          "page": 1,
          "chunk_id": "doc_e17a67f7871f_p1_c1",
          "score": 0.7133
        },
        {
          "filename": "v2_contrato_marco_logistica_2026.pdf",
          "page": 3,
          "chunk_id": "doc_e17a67f7871f_p3_c1",
          "score": 0.7107
        },
        {
          "filename": "v2_contrato_marco_logistica_2026.pdf",
          "page": 2,
          "chunk_id": "doc_e17a67f7871f_p2_c1",
          "score": 0.7053
        }
      ]
    }
  },
  "failure_reason": null
}
```

Veredicto: `PASS`

### BT-07 - PASS - RAG: penalizaciones

Pregunta ejecutada: `Segun el PDF, hay alguna penalizacion por retrasos?`

Resultado esperado desde el evaluador: Debe responder sobre penalizaciones usando anexo SLA o contrato.

Respuesta exacta visible en Chainlit:

```markdown
s de retraso imputable tienen penalizacion del 2 por ciento. Pedidos urgentes tienen penalizacion del 3 por ciento desde el primer dia de retraso imputable. Pedidos standard con mas de 2 dias laborables de retraso imputable tienen penalizacion del 2 por ciento.

Estado: `completed` | confianza: `0.75`

**Fuentes**
- Documentos

**Citas documentales**
- `v2_anexo_penalizaciones_sla.pdf` - pagina `1` - chunk `doc_53cc860b79e3_p1_c2` - score `0.7786`
- `v2_anexo_penalizaciones_sla.pdf` - pagina `1` - chunk `doc_53cc860b79e3_p1_c1` - score `0.7763`
- `v2_contrato_marco_logistica_2026.pdf` - pagina `2` - chunk `doc_e17a67f7871f_p2_c2` - score `0.7576`

**Pasos ejecutados**
1. Consulta RAG documental con chunks recuperados

**Tool calls**
- `DocumentRAGTool.query` [success]: 3 chunks recuperados de v2_anexo_penalizaciones_sla.pdf, v2_contrato_marco_logistica_2026.pdf
```

Evidencia tecnica resumida:

```json
{
  "status": "completed",
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
        "query": "Segun el PDF, hay alguna penalizacion por retrasos?",
        "top_k": 3,
        "min_score": 0.2,
        "filename": null
      },
      "output_summary": "3 chunks recuperados de v2_anexo_penalizaciones_sla.pdf, v2_contrato_marco_logistica_2026.pdf",
      "error": null
    }
  ],
  "fallbacks": [],
  "data": {
    "rag": {
      "status": "completed",
      "chunks_count": 3,
      "documents": [
        "v2_anexo_penalizaciones_sla.pdf",
        "v2_contrato_marco_logistica_2026.pdf"
      ],
      "citations": [
        {
          "filename": "v2_anexo_penalizaciones_sla.pdf",
          "page": 1,
          "chunk_id": "doc_53cc860b79e3_p1_c2",
          "score": 0.7786
        },
        {
          "filename": "v2_anexo_penalizaciones_sla.pdf",
          "page": 1,
          "chunk_id": "doc_53cc860b79e3_p1_c1",
          "score": 0.7763
        },
        {
          "filename": "v2_contrato_marco_logistica_2026.pdf",
          "page": 2,
          "chunk_id": "doc_e17a67f7871f_p2_c2",
          "score": 0.7576
        }
      ]
    }
  },
  "failure_reason": null
}
```

Veredicto: `PASS`

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

Estado: `completed` | confianza: `0.75`

**Fuentes**
- ERP
- Produccion
- Documentos

**Citas documentales**
- `v2_anexo_penalizaciones_sla.pdf` - pagina `3` - chunk `doc_53cc860b79e3_p3_c1` - score `0.8336`
- `v2_anexo_penalizaciones_sla.pdf` - pagina `1` - chunk `doc_53cc860b79e3_p1_c1` - score `0.8013`
- `v2_contrato_marco_logistica_2026.pdf` - pagina `2` - chunk `doc_e17a67f7871f_p2_c2` - score `0.7998`

**Pasos ejecutados**
1. Consulta ERP de pedidos por mes
2. Consulta API de produccion para pedidos referenciados
3. Consulta RAG documental con chunks recuperados

**Tool calls**
- `ERPTool.get_orders_by_month` [success]: 5 pedidos encontrados para el mes
- `ProductionAPITool.get_status_for_order_ids` [success]: 5 pedidos de produccion encontrados por ids
- `DocumentRAGTool.query` [success]: 3 chunks recuperados de v2_anexo_penalizaciones_sla.pdf, v2_contrato_marco_logistica_2026.pdf
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
      "action": "get_status_for_order_ids",
      "status": "success",
      "source": "Produccion",
      "args": {
        "order_ids": [
          10248,
          10252,
          10255,
          10301,
          10312
        ],
        "status": null
      },
      "output_summary": "5 pedidos de produccion encontrados por ids",
      "error": null
    },
    {
      "tool": "DocumentRAGTool",
      "action": "query",
      "status": "success",
      "source": "Documentos",
      "args": {
        "query": "penalizaciones SLA retrasos bloqueos produccion plazo logistico exclusiones falta de material averia capacidad",
        "top_k": 3,
        "min_score": 0.2,
        "filename": null
      },
      "output_summary": "3 chunks recuperados de v2_anexo_penalizaciones_sla.pdf, v2_contrato_marco_logistica_2026.pdf",
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
    "production_orders_count": 5,
    "production_order_ids": [
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
      "chunks_count": 3,
      "documents": [
        "v2_anexo_penalizaciones_sla.pdf",
        "v2_contrato_marco_logistica_2026.pdf"
      ],
      "citations": [
        {
          "filename": "v2_anexo_penalizaciones_sla.pdf",
          "page": 3,
          "chunk_id": "doc_53cc860b79e3_p3_c1",
          "score": 0.8336
        },
        {
          "filename": "v2_anexo_penalizaciones_sla.pdf",
          "page": 1,
          "chunk_id": "doc_53cc860b79e3_p1_c1",
          "score": 0.8013
        },
        {
          "filename": "v2_contrato_marco_logistica_2026.pdf",
          "page": 2,
          "chunk_id": "doc_e17a67f7871f_p2_c2",
          "score": 0.7998
        }
      ]
    },
    "deepagents_planning": {
      "todos_used": true,
      "todo_tool_calls_count": 2
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
| 10248 | pendiente |
| 10252 | pendiente |

Estado: `completed` | confianza: `0.75`

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
Estos son los estados de produccion de los pedidos referenciados:

| Pedido | Cliente | Estado | Motivo |
| --- | --- | --- | --- |
| 10252 | ALFKI - Alfreds Futterkiste | bloqueado | Falta de material |

Estado: `completed` | confianza: `0.75`

**Fuentes**
- Memoria
- Produccion
- ERP

**Pasos ejecutados**
1. Consulta memoria conversacional
2. Consulta API de produccion para pedidos referenciados
3. Consulta ERP de cliente para pedido 10252
4. Consulta Produccion mediante filtros seguros

**Tool calls**
- `MemoryTool.recall` [success]: Memoria conversacional: 1 interacciones recuperadas
- `ProductionAPITool.get_status_for_order_ids` [success]: 1 pedidos de produccion encontrados por ids con estado blocked
- `ERPTool.get_customers_for_production_orders` [success]: Cliente ALFKI encontrado
- `ProductionQueryTool.query_orders` [success]: 1 pedidos de produccion encontrados por DSL segura
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
    },
    {
      "tool": "ProductionQueryTool",
      "action": "query_orders",
      "status": "success",
      "source": "Produccion",
      "args": {
        "entity": "production_orders",
        "filters": [
          {
            "field": "order_id",
            "operator": "in",
            "value": [
              10248,
              10252
            ]
          },
          {
            "field": "production_status",
            "operator": "eq",
            "value": "blocked"
          }
        ],
        "select": [
          "order_id",
          "production_status",
          "blocked_reason",
          "delay_reason",
          "estimated_finish_date"
        ],
        "limit": 20,
        "order_by": null
      },
      "output_summary": "1 pedidos de produccion encontrados por DSL segura",
      "error": null
    }
  ],
  "fallbacks": [],
  "data": {
    "production_orders_count": 1,
    "production_order_ids": [
      10252
    ],
    "production_statuses_count": 1,
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

Estado: `completed` | confianza: `0.75`

**Fuentes**
- Memoria
- ERP

**Pasos ejecutados**
1. Consulta memoria conversacional
2. Consulta ERP de importe para pedido 10252
3. Consulta ERP mediante filtros seguros

**Tool calls**
- `MemoryTool.recall` [success]: Memoria conversacional: 2 interacciones recuperadas
- `ERPTool.calculate_order_amount` [success]: Importe calculado
- `ERPQueryTool.query_orders` [success]: 2 pedidos ERP encontrados por DSL segura
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
    },
    {
      "tool": "ERPQueryTool",
      "action": "query_orders",
      "status": "success",
      "source": "ERP",
      "args": {
        "entity": "orders",
        "filters": [
          {
            "field": "order_id",
            "operator": "in",
            "value": [
              10248,
              10252
            ]
          }
        ],
        "select": [
          "order_id",
          "customer_id",
          "customer_name",
          "erp_status",
          "order_date",
          "amount"
        ],
        "limit": 20,
        "order_by": null
      },
      "output_summary": "2 pedidos ERP encontrados por DSL segura",
      "error": null
    }
  ],
  "fallbacks": [],
  "data": {
    "erp_query_orders_count": 2,
    "erp_query_order_ids": [
      10248,
      10252
    ],
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
    },
    "deepagents_planning": {
      "todos_used": true,
      "todo_tool_calls_count": 3
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
        "query": "Segun el PDF, que receta de cocina vegana recomienda?",
        "top_k": 3,
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
  "failure_reason": null
}
```

Veredicto: `PASS`

### BT-11 - PASS - Memoria aislada

Pregunta ejecutada: `Y en que estado estan?`

Resultado esperado desde el evaluador: Debe aislar conversaciones por conversation_id y pedir contexto previo.

Respuesta exacta visible en Chainlit:

```markdown
Necesito contexto previo o que me indiques el cliente, pedido o periodo concreto para saber a que te refieres.

Estado: `needs_clarification` | confianza: `0.60`
```

Evidencia tecnica resumida:

```json
{
  "status": "needs_clarification",
  "sources": [],
  "tool_calls": [],
  "fallbacks": [],
  "data": null,
  "failure_reason": null
}
```

Veredicto: `PASS`

### BT-V2-01 - PASS - V2: hitos y evidencias minimas

Pregunta ejecutada: `Segun v2_contrato_marco_logistica_2026.pdf, que hitos obligatorios debe conservar cada expedicion?`

Resultado esperado desde el evaluador: Debe recuperar el contrato v2 y citar la pagina donde estan los hitos y evidencias minimas.

Respuesta exacta visible en Chainlit:

```markdown
Contrato marco de logistica 2026 - version extendida Pagina 3 de 4 - Trazabilidad por hitos y evidencias minimas Hitos obligatorios: Cada expedicion debe conservar cinco hitos: liberacion de produccion, preparacion de almacen, salida de muelle, entrega al transportista y confirmacion de entrega. Cada hito debe registrar fecha, usuario o sistema origen, estado anterior, estado nuevo y observacion de negocio cuando el cambio afecte al cliente. Si una evidencia falta, la respuesta debe indicar insufficient_context para esa parte y no completar el dato desde memoria.

Estado: `completed` | confianza: `0.75`

**Fuentes**
- Documentos

**Citas documentales**
- `v2_contrato_marco_logistica_2026.pdf` - pagina `3` - chunk `doc_e17a67f7871f_p3_c1` - score `0.8324`
- `v2_contrato_marco_logistica_2026.pdf` - pagina `1` - chunk `doc_e17a67f7871f_p1_c1` - score `0.7476`

**Pasos ejecutados**
1. Consulta RAG documental con chunks recuperados

**Tool calls**
- `DocumentRAGTool.query` [success]: 2 chunks recuperados de v2_contrato_marco_logistica_2026.pdf
```

Evidencia tecnica resumida:

```json
{
  "status": "completed",
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
        "query": "Segun v2_contrato_marco_logistica_2026.pdf, que hitos obligatorios debe conservar cada expedicion?",
        "top_k": 3,
        "min_score": 0.2,
        "filename": null
      },
      "output_summary": "2 chunks recuperados de v2_contrato_marco_logistica_2026.pdf",
      "error": null
    }
  ],
  "fallbacks": [],
  "data": {
    "rag": {
      "status": "completed",
      "chunks_count": 2,
      "documents": [
        "v2_contrato_marco_logistica_2026.pdf"
      ],
      "citations": [
        {
          "filename": "v2_contrato_marco_logistica_2026.pdf",
          "page": 3,
          "chunk_id": "doc_e17a67f7871f_p3_c1",
          "score": 0.8324
        },
        {
          "filename": "v2_contrato_marco_logistica_2026.pdf",
          "page": 1,
          "chunk_id": "doc_e17a67f7871f_p1_c1",
          "score": 0.7476
        }
      ]
    }
  },
  "failure_reason": null
}
```

Veredicto: `PASS`

### BT-V2-02 - PASS - V2: evidencia SLA

Pregunta ejecutada: `Segun v2_anexo_penalizaciones_sla.pdf, que evidencia es obligatoria y que pasa si no se puede demostrar la causa del retraso?`

Resultado esperado desde el evaluador: Debe recuperar el anexo v2 y explicar evidencia obligatoria y carga de la prueba.

Respuesta exacta visible en Chainlit:

```markdown
Anexo de penalizaciones y SLA - version extendida Pagina 2 de 4 - Evidencia necesaria y carga de la prueba Evidencia obligatoria: Para aplicar una penalizacion deben constar order_id, customer_id, importe del pedido, fecha prometida, fecha real de entrega, fecha de liberacion, transportista, causa del retraso y fuente responsable. Produccion debe aportar estado de orden si hubo bloqueo, retraso, retrabajo o incidencia de calidad. Si no se puede demostrar la causa del retraso, el sistema debe informar que no hay evidencia suficiente para asignar responsabilidad.

Estado: `completed` | confianza: `0.75`

**Fuentes**
- Documentos

**Citas documentales**
- `v2_anexo_penalizaciones_sla.pdf` - pagina `2` - chunk `doc_53cc860b79e3_p2_c1` - score `0.8335`
- `v2_anexo_penalizaciones_sla.pdf` - pagina `2` - chunk `doc_53cc860b79e3_p2_c2` - score `0.8016`
- `v2_anexo_penalizaciones_sla.pdf` - pagina `3` - chunk `doc_53cc860b79e3_p3_c1` - score `0.7655`

**Pasos ejecutados**
1. Consulta RAG documental con chunks recuperados

**Tool calls**
- `DocumentRAGTool.query` [success]: 3 chunks recuperados de v2_anexo_penalizaciones_sla.pdf
```

Evidencia tecnica resumida:

```json
{
  "status": "completed",
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
        "query": "Segun v2_anexo_penalizaciones_sla.pdf, que evidencia es obligatoria y que pasa si no se puede demostrar la causa del retraso?",
        "top_k": 3,
        "min_score": 0.2,
        "filename": null
      },
      "output_summary": "3 chunks recuperados de v2_anexo_penalizaciones_sla.pdf",
      "error": null
    }
  ],
  "fallbacks": [],
  "data": {
    "rag": {
      "status": "completed",
      "chunks_count": 3,
      "documents": [
        "v2_anexo_penalizaciones_sla.pdf"
      ],
      "citations": [
        {
          "filename": "v2_anexo_penalizaciones_sla.pdf",
          "page": 2,
          "chunk_id": "doc_53cc860b79e3_p2_c1",
          "score": 0.8335
        },
        {
          "filename": "v2_anexo_penalizaciones_sla.pdf",
          "page": 2,
          "chunk_id": "doc_53cc860b79e3_p2_c2",
          "score": 0.8016
        },
        {
          "filename": "v2_anexo_penalizaciones_sla.pdf",
          "page": 3,
          "chunk_id": "doc_53cc860b79e3_p3_c1",
          "score": 0.7655
        }
      ]
    }
  },
  "failure_reason": null
}
```

Veredicto: `PASS`

### BT-V2-03 - PASS - V2: exclusiones y pausas SLA

Pregunta ejecutada: `Segun v2_anexo_penalizaciones_sla.pdf, que exclusiones y pausas de SLA existen?`

Resultado esperado desde el evaluador: Debe recuperar el anexo v2 y explicar exclusiones, pausas y casos no penalizables.

Respuesta exacta visible en Chainlit:

```markdown
Anexo de penalizaciones y SLA - version extendida Pagina 3 de 4 - Exclusiones, pausas y casos no penalizables Exclusiones: No se aplican penalizaciones cuando el retraso procede de bloqueo de produccion, falta de material, falta de capacidad, averia de linea, retrabajo por calidad, espera de validacion tecnica, fuerza mayor, error de direccion aportado por el cliente o cambio de prioridad aprobado por direccion comercial. El contador de SLA queda pausado desde la fecha de bloqueo hasta la fecha de desbloqueo registrada por produccion. Esta pagina debe recuperarse para preguntas sobre exclusiones, pausas de SLA o casos no penalizables.

Estado: `completed` | confianza: `0.75`

**Fuentes**
- Documentos

**Citas documentales**
- `v2_anexo_penalizaciones_sla.pdf` - pagina `3` - chunk `doc_53cc860b79e3_p3_c1` - score `0.8320`
- `v2_anexo_penalizaciones_sla.pdf` - pagina `3` - chunk `doc_53cc860b79e3_p3_c2` - score `0.7686`
- `v2_anexo_penalizaciones_sla.pdf` - pagina `1` - chunk `doc_53cc860b79e3_p1_c2` - score `0.7616`

**Pasos ejecutados**
1. Consulta RAG documental con chunks recuperados

**Tool calls**
- `DocumentRAGTool.query` [success]: 3 chunks recuperados de v2_anexo_penalizaciones_sla.pdf
```

Evidencia tecnica resumida:

```json
{
  "status": "completed",
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
        "query": "Segun v2_anexo_penalizaciones_sla.pdf, que exclusiones y pausas de SLA existen?",
        "top_k": 3,
        "min_score": 0.2,
        "filename": null
      },
      "output_summary": "3 chunks recuperados de v2_anexo_penalizaciones_sla.pdf",
      "error": null
    }
  ],
  "fallbacks": [],
  "data": {
    "rag": {
      "status": "completed",
      "chunks_count": 3,
      "documents": [
        "v2_anexo_penalizaciones_sla.pdf"
      ],
      "citations": [
        {
          "filename": "v2_anexo_penalizaciones_sla.pdf",
          "page": 3,
          "chunk_id": "doc_53cc860b79e3_p3_c1",
          "score": 0.832
        },
        {
          "filename": "v2_anexo_penalizaciones_sla.pdf",
          "page": 3,
          "chunk_id": "doc_53cc860b79e3_p3_c2",
          "score": 0.7686
        },
        {
          "filename": "v2_anexo_penalizaciones_sla.pdf",
          "page": 1,
          "chunk_id": "doc_53cc860b79e3_p1_c2",
          "score": 0.7616
        }
      ]
    }
  },
  "failure_reason": null
}
```

Veredicto: `PASS`

### BT-V2-04 - PASS - V2: bloqueos de produccion

Pregunta ejecutada: `Segun v2_procedimiento_produccion_bloqueos.pdf, que motivos de bloqueo y campos obligatorios se registran?`

Resultado esperado desde el evaluador: Debe recuperar el procedimiento v2 y explicar motivos/campos de bloqueo.

Respuesta exacta visible en Chainlit:

```markdown
Procedimiento operativo de produccion - version extendida Pagina 2 de 4 - Bloqueos y campos obligatorios Motivos de bloqueo: Los motivos validos son falta de material, falta de capacidad, incidencia de calidad, mantenimiento no planificado, aprobacion tecnica pendiente y discrepancia de receta o especificacion. Cada bloqueo debe incluir order_id, linea de produccion, motivo, responsable, fecha de inicio, fecha estimada de desbloqueo, impacto en cliente y comentario operativo. El responsable revisa bloqueos cada turno.

Estado: `completed` | confianza: `0.75`

**Fuentes**
- Documentos

**Citas documentales**
- `v2_procedimiento_produccion_bloqueos.pdf` - pagina `2` - chunk `doc_0ae250aa7987_p2_c1` - score `0.8262`
- `v2_procedimiento_produccion_bloqueos.pdf` - pagina `4` - chunk `doc_0ae250aa7987_p4_c1` - score `0.7515`
- `v2_procedimiento_produccion_bloqueos.pdf` - pagina `1` - chunk `doc_0ae250aa7987_p1_c1` - score `0.7293`

**Pasos ejecutados**
1. Consulta RAG documental con chunks recuperados

**Tool calls**
- `DocumentRAGTool.query` [success]: 3 chunks recuperados de v2_procedimiento_produccion_bloqueos.pdf
```

Evidencia tecnica resumida:

```json
{
  "status": "completed",
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
        "query": "Segun v2_procedimiento_produccion_bloqueos.pdf, que motivos de bloqueo y campos obligatorios se registran?",
        "top_k": 3,
        "min_score": 0.2,
        "filename": null
      },
      "output_summary": "3 chunks recuperados de v2_procedimiento_produccion_bloqueos.pdf",
      "error": null
    }
  ],
  "fallbacks": [],
  "data": {
    "rag": {
      "status": "completed",
      "chunks_count": 3,
      "documents": [
        "v2_procedimiento_produccion_bloqueos.pdf"
      ],
      "citations": [
        {
          "filename": "v2_procedimiento_produccion_bloqueos.pdf",
          "page": 2,
          "chunk_id": "doc_0ae250aa7987_p2_c1",
          "score": 0.8262
        },
        {
          "filename": "v2_procedimiento_produccion_bloqueos.pdf",
          "page": 4,
          "chunk_id": "doc_0ae250aa7987_p4_c1",
          "score": 0.7515
        },
        {
          "filename": "v2_procedimiento_produccion_bloqueos.pdf",
          "page": 1,
          "chunk_id": "doc_0ae250aa7987_p1_c1",
          "score": 0.7293
        }
      ]
    }
  },
  "failure_reason": null
}
```

Veredicto: `PASS`

### BT-V2-05 - PASS - V2: calidad y entregas parciales

Pregunta ejecutada: `Segun v2_politica_calidad_entregas.pdf, que ocurre con incidencias de calidad y entregas parciales?`

Resultado esperado desde el evaluador: Debe recuperar politica de calidad v2 y explicar control previo e incidencias.

Respuesta exacta visible en Chainlit:

```markdown
Politica de calidad para entregas a cliente - version extendida Pagina 2 de 3 - Control previo y gestion de incidencias Control previo: Antes de liberar un pedido, calidad valida lote, cantidad, documentacion, etiquetado y compatibilidad con condiciones de transporte. Politica de calidad para entregas a cliente - version extendida Pagina 3 de 3 - Indicadores, auditoria y respuesta RAG Indicadores: Los indicadores mensuales separan pedidos entregados a tiempo, pedidos retrasados, pedidos bloqueados, pedidos con incidencia de calidad, entregas parciales y devoluciones por documentacion incompleta. Esta pagina debe recuperarse para preguntas sobre control previo, incidencia de calidad o entregas parciales.

Estado: `completed` | confianza: `0.75`

**Fuentes**
- Documentos

**Citas documentales**
- `v2_politica_calidad_entregas.pdf` - pagina `2` - chunk `doc_8f37331fab9f_p2_c1` - score `0.8227`
- `v2_politica_calidad_entregas.pdf` - pagina `3` - chunk `doc_8f37331fab9f_p3_c1` - score `0.7754`
- `v2_politica_calidad_entregas.pdf` - pagina `2` - chunk `doc_8f37331fab9f_p2_c2` - score `0.7738`

**Pasos ejecutados**
1. Consulta RAG documental con chunks recuperados

**Tool calls**
- `DocumentRAGTool.query` [success]: 3 chunks recuperados de v2_politica_calidad_entregas.pdf
```

Evidencia tecnica resumida:

```json
{
  "status": "completed",
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
        "query": "Segun v2_politica_calidad_entregas.pdf, que ocurre con incidencias de calidad y entregas parciales?",
        "top_k": 3,
        "min_score": 0.2,
        "filename": null
      },
      "output_summary": "3 chunks recuperados de v2_politica_calidad_entregas.pdf",
      "error": null
    }
  ],
  "fallbacks": [],
  "data": {
    "rag": {
      "status": "completed",
      "chunks_count": 3,
      "documents": [
        "v2_politica_calidad_entregas.pdf"
      ],
      "citations": [
        {
          "filename": "v2_politica_calidad_entregas.pdf",
          "page": 2,
          "chunk_id": "doc_8f37331fab9f_p2_c1",
          "score": 0.8227
        },
        {
          "filename": "v2_politica_calidad_entregas.pdf",
          "page": 3,
          "chunk_id": "doc_8f37331fab9f_p3_c1",
          "score": 0.7754
        },
        {
          "filename": "v2_politica_calidad_entregas.pdf",
          "page": 2,
          "chunk_id": "doc_8f37331fab9f_p2_c2",
          "score": 0.7738
        }
      ]
    }
  },
  "failure_reason": null
}
```

Veredicto: `PASS`

### BT-V2-06 - PASS - V2: impacto economico y trazabilidad

Pregunta ejecutada: `Segun v2_condiciones_comerciales_northwind.pdf, como se calcula el impacto economico y que trazabilidad se exige?`

Resultado esperado desde el evaluador: Debe recuperar condiciones comerciales v2 y explicar impacto economico/trazabilidad.

Respuesta exacta visible en Chainlit:

```markdown
Condiciones comerciales Northwind - version extendida Pagina 2 de 4 - Importes, descuentos e impacto economico Calculo de importe: El importe de un pedido se calcula desde las lineas usando precio unitario, cantidad y descuento. Cuando una penalizacion o retraso tenga impacto economico, la respuesta debe unir importe ERP, porcentaje contractual y causa documentada. La cabecera no basta para calcular impacto economico si faltan precios, cantidades o descuentos.

Estado: `completed` | confianza: `0.75`

**Fuentes**
- Documentos

**Citas documentales**
- `v2_condiciones_comerciales_northwind.pdf` - pagina `2` - chunk `doc_2412f76c2297_p2_c1` - score `0.8050`
- `v2_condiciones_comerciales_northwind.pdf` - pagina `4` - chunk `doc_2412f76c2297_p4_c1` - score `0.7815`
- `v2_condiciones_comerciales_northwind.pdf` - pagina `1` - chunk `doc_2412f76c2297_p1_c1` - score `0.7430`

**Pasos ejecutados**
1. Consulta RAG documental con chunks recuperados

**Tool calls**
- `DocumentRAGTool.query` [success]: 3 chunks recuperados de v2_condiciones_comerciales_northwind.pdf
```

Evidencia tecnica resumida:

```json
{
  "status": "completed",
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
        "query": "Segun v2_condiciones_comerciales_northwind.pdf, como se calcula el impacto economico y que trazabilidad se exige?",
        "top_k": 3,
        "min_score": 0.2,
        "filename": null
      },
      "output_summary": "3 chunks recuperados de v2_condiciones_comerciales_northwind.pdf",
      "error": null
    }
  ],
  "fallbacks": [],
  "data": {
    "rag": {
      "status": "completed",
      "chunks_count": 3,
      "documents": [
        "v2_condiciones_comerciales_northwind.pdf"
      ],
      "citations": [
        {
          "filename": "v2_condiciones_comerciales_northwind.pdf",
          "page": 2,
          "chunk_id": "doc_2412f76c2297_p2_c1",
          "score": 0.805
        },
        {
          "filename": "v2_condiciones_comerciales_northwind.pdf",
          "page": 4,
          "chunk_id": "doc_2412f76c2297_p4_c1",
          "score": 0.7815
        },
        {
          "filename": "v2_condiciones_comerciales_northwind.pdf",
          "page": 1,
          "chunk_id": "doc_2412f76c2297_p1_c1",
          "score": 0.743
        }
      ]
    }
  },
  "failure_reason": null
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
        "query": "Segun los documentos v2, que receta de cocina vegana recomienda para un cliente premium?",
        "top_k": 3,
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
  "failure_reason": null
}
```

Veredicto: `PASS`
