## Validacion beta obligatoria automatizada

Fecha de ejecucion: 2026-05-22 17:40:24

- Resultado global: PASS=18, PARTIAL=0, FAIL=0, BLOCKER=0.
Runtime:

- Flujo en proceso con `QueryWorkflowService`.
- LLM real configurado via `.env`.
- Embeddings reales del proveedor configurado via `.env`.
- ChromaDB persistente local obligatorio para el espacio documental.
- ERP SQLite seed en memoria.
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
| 10248 | Pendiente | En curso | Sin bloqueo informado |
| 10252 | Pendiente | Bloqueado | Falta de material |

El punto de atencion es el pedido 10252, porque requiere seguimiento operativo desde produccion.

Estado: `completed` | confianza: `0.90`

**Fuentes**
- ERP
- Produccion

**Pasos ejecutados**
1. Consulta ERP de pedidos pendientes
2. Consulta API de produccion para pedido 10248
3. Consulta API de produccion para pedido 10252

**Tool calls**
- `ERPTool.get_pending_orders_by_customer` [success]: 2 pedidos pendientes encontrados
- `ProductionAPITool.get_status_for_erp_orders` [success]: Estado de produccion in_progress
- `ProductionAPITool.get_status_for_erp_orders` [success]: Estado de produccion blocked
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
    }
  ],
  "fallbacks": [],
  "data": {
    "erp_orders_count": 2,
    "erp_order_ids": [
      10248,
      10252
    ],
    "production_statuses_count": 2
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
Hay clientes afectados por bloqueos de produccion: 2.

| Cliente | Pedido | Motivo |
| --- | --- | --- |
| ALFKI - Alfreds Futterkiste | 10252 | Falta de material |
| BONAP - Bon app | 10312 | Falta de capacidad |

El siguiente punto de atencion es resolver estos bloqueos desde produccion.

Estado: `completed` | confianza: `0.90`

**Fuentes**
- Produccion
- ERP

**Pasos ejecutados**
1. Consulta API de produccion por estado
2. Consulta ERP de cliente para pedido 10252
3. Consulta ERP de cliente para pedido 10312

**Tool calls**
- `ProductionAPITool.list_orders` [success]: 2 pedidos de produccion encontrados con estado blocked
- `ERPTool.get_customers_for_production_orders` [success]: Cliente ALFKI encontrado
- `ERPTool.get_customers_for_production_orders` [success]: Cliente BONAP encontrado
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
    }
  ],
  "fallbacks": [],
  "data": {
    "production_orders_count": 2,
    "production_order_ids": [
      10252,
      10312
    ],
    "customers_resolved_count": 2
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
Hay pedidos retrasados en producción:

| Pedido | Cliente | Estado producción | Motivo |
| --- | --- | --- | --- |
| 10301 | ANATR - Ana Trujillo Emparedados y helados | Retrasado | Avería en línea de producción |

El siguiente punto de atención es el pedido 10301.

Estado: `completed` | confianza: `0.90`

**Fuentes**
- Produccion
- ERP

**Pasos ejecutados**
1. Consulta API de produccion por estado
2. Consulta ERP de cliente para pedido 10301

**Tool calls**
- `ProductionAPITool.list_orders` [success]: 1 pedidos de produccion encontrados con estado delayed
- `ERPTool.get_customers_for_production_orders` [success]: Cliente ANATR encontrado
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
    }
  ],
  "fallbacks": [],
  "data": {
    "production_orders_count": 1,
    "production_order_ids": [
      10301
    ],
    "customers_resolved_count": 1
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
En 2026-05 hay 5 pedidos ERP. Distribucion por estado de produccion: bloqueado: 2, en curso: 1, finalizado: 1, retrasado: 1.

Estado: `completed` | confianza: `0.90`

**Fuentes**
- ERP
- Produccion

**Pasos ejecutados**
1. Consulta ERP de pedidos por mes
2. Consulta API de produccion para pedido 10248
3. Consulta API de produccion para pedido 10252
4. Consulta API de produccion para pedido 10255
5. Consulta API de produccion para pedido 10301
6. Consulta API de produccion para pedido 10312

**Tool calls**
- `ERPTool.get_orders_by_month` [success]: 5 pedidos encontrados para el mes
- `ProductionAPITool.get_status_for_erp_orders` [success]: Estado de produccion in_progress
- `ProductionAPITool.get_status_for_erp_orders` [success]: Estado de produccion blocked
- `ProductionAPITool.get_status_for_erp_orders` [success]: Estado de produccion finished
- `ProductionAPITool.get_status_for_erp_orders` [success]: Estado de produccion delayed
- `ProductionAPITool.get_status_for_erp_orders` [success]: Estado de produccion blocked
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
Los pedidos estándar deben entregarse en un plazo máximo de 5 días laborables desde la liberación de producción. Para los pedidos urgentes, el plazo máximo es de 48 horas. Es importante destacar que la penalización por incumplimiento de plazo solo aplica si la causa es imputable al operador logístico y existe evidencia completa en ERP, producción y prueba de entrega.

Estado: `completed` | confianza: `0.90`

**Fuentes**
- Documentos

**Citas documentales**
- `v2_contrato_marco_logistica_2026.pdf` - pagina `2` - chunk `doc_dbae4fa99803_p2_c1` - score `0.8323`
- `v2_anexo_penalizaciones_sla.pdf` - pagina `1` - chunk `doc_3f17e2e37c34_p1_c1` - score `0.8156`
- `v2_contrato_marco_logistica_2026.pdf` - pagina `2` - chunk `doc_dbae4fa99803_p2_c2` - score `0.8079`

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
        "query": "plazos de entrega standard",
        "top_k": 5,
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
          "chunk_id": "doc_dbae4fa99803_p2_c1",
          "score": 0.8323
        },
        {
          "filename": "v2_anexo_penalizaciones_sla.pdf",
          "page": 1,
          "chunk_id": "doc_3f17e2e37c34_p1_c1",
          "score": 0.8156
        },
        {
          "filename": "v2_contrato_marco_logistica_2026.pdf",
          "page": 2,
          "chunk_id": "doc_dbae4fa99803_p2_c2",
          "score": 0.8079
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
El Contrato Marco de Logística 2026 regula la preparación, expedición, entrega y cierre documental de pedidos comerciales durante el año. Establece plazos de entrega de 5 días laborables para pedidos estándar y 48 horas para urgentes, con el plazo iniciando al liberar producción y tener dirección completa. Define pedidos estándar, urgentes y bloqueados (detenidos por producción). Requiere cinco hitos obligatorios de trazabilidad por expedición y evidencia mínima para auditorías. En caso de retrasos, la responsabilidad logística se analiza si el pedido está liberado y el transportista confirma recogida. Si un pedido está bloqueado por falta de material, logística no debe prometer fecha de entrega hasta tener la fecha estimada de desbloqueo. Para adelantar un cliente prioritario, producción debe confirmar capacidad y calidad el lote liberado.

Estado: `completed` | confianza: `0.90`

**Fuentes**
- Documentos

**Citas documentales**
- `v2_contrato_marco_logistica_2026.pdf` - pagina `1` - chunk `doc_dbae4fa99803_p1_c1` - score `0.7617`
- `v2_contrato_marco_logistica_2026.pdf` - pagina `3` - chunk `doc_dbae4fa99803_p3_c1` - score `0.7570`
- `v2_contrato_marco_logistica_2026.pdf` - pagina `2` - chunk `doc_dbae4fa99803_p2_c1` - score `0.7554`
- `v2_contrato_marco_logistica_2026.pdf` - pagina `4` - chunk `doc_dbae4fa99803_p4_c1` - score `0.7404`
- `v2_contrato_marco_logistica_2026.pdf` - pagina `2` - chunk `doc_dbae4fa99803_p2_c2` - score `0.7328`

**Pasos ejecutados**
1. Consulta RAG documental con chunks recuperados

**Tool calls**
- `DocumentRAGTool.query` [success]: 5 chunks recuperados de v2_contrato_marco_logistica_2026.pdf
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
        "top_k": 5,
        "min_score": 0.2,
        "filename": null
      },
      "output_summary": "5 chunks recuperados de v2_contrato_marco_logistica_2026.pdf",
      "error": null
    }
  ],
  "fallbacks": [],
  "data": {
    "rag": {
      "status": "completed",
      "chunks_count": 5,
      "documents": [
        "v2_contrato_marco_logistica_2026.pdf"
      ],
      "citations": [
        {
          "filename": "v2_contrato_marco_logistica_2026.pdf",
          "page": 1,
          "chunk_id": "doc_dbae4fa99803_p1_c1",
          "score": 0.7617
        },
        {
          "filename": "v2_contrato_marco_logistica_2026.pdf",
          "page": 3,
          "chunk_id": "doc_dbae4fa99803_p3_c1",
          "score": 0.757
        },
        {
          "filename": "v2_contrato_marco_logistica_2026.pdf",
          "page": 2,
          "chunk_id": "doc_dbae4fa99803_p2_c1",
          "score": 0.7554
        },
        {
          "filename": "v2_contrato_marco_logistica_2026.pdf",
          "page": 4,
          "chunk_id": "doc_dbae4fa99803_p4_c1",
          "score": 0.7404
        },
        {
          "filename": "v2_contrato_marco_logistica_2026.pdf",
          "page": 2,
          "chunk_id": "doc_dbae4fa99803_p2_c2",
          "score": 0.7328
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
Sí, existen penalizaciones por retrasos según el tipo de pedido:

* **Pedidos estándar:** Tienen una penalización del 2% si el retraso imputable supera los 2 días laborables. Si el retraso excede los 5 días laborables, la penalización sube al 5%.
* **Pedidos urgentes:** Tienen una penalización del 3% desde el primer día de retraso imputable.

Estado: `completed` | confianza: `0.90`

**Fuentes**
- Documentos

**Citas documentales**
- `v2_anexo_penalizaciones_sla.pdf` - pagina `1` - chunk `doc_3f17e2e37c34_p1_c2` - score `0.8276`
- `v2_anexo_penalizaciones_sla.pdf` - pagina `1` - chunk `doc_3f17e2e37c34_p1_c1` - score `0.8076`
- `v2_anexo_penalizaciones_sla.pdf` - pagina `2` - chunk `doc_3f17e2e37c34_p2_c1` - score `0.7974`
- `v2_anexo_penalizaciones_sla.pdf` - pagina `3` - chunk `doc_3f17e2e37c34_p3_c1` - score `0.7953`
- `v2_anexo_penalizaciones_sla.pdf` - pagina `4` - chunk `doc_3f17e2e37c34_p4_c1` - score `0.7859`

**Pasos ejecutados**
1. Consulta RAG documental con chunks recuperados

**Tool calls**
- `DocumentRAGTool.query` [success]: 5 chunks recuperados de v2_anexo_penalizaciones_sla.pdf
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
        "query": "penalizacion por retrasos",
        "top_k": 5,
        "min_score": 0.2,
        "filename": null
      },
      "output_summary": "5 chunks recuperados de v2_anexo_penalizaciones_sla.pdf",
      "error": null
    }
  ],
  "fallbacks": [],
  "data": {
    "rag": {
      "status": "completed",
      "chunks_count": 5,
      "documents": [
        "v2_anexo_penalizaciones_sla.pdf"
      ],
      "citations": [
        {
          "filename": "v2_anexo_penalizaciones_sla.pdf",
          "page": 1,
          "chunk_id": "doc_3f17e2e37c34_p1_c2",
          "score": 0.8276
        },
        {
          "filename": "v2_anexo_penalizaciones_sla.pdf",
          "page": 1,
          "chunk_id": "doc_3f17e2e37c34_p1_c1",
          "score": 0.8076
        },
        {
          "filename": "v2_anexo_penalizaciones_sla.pdf",
          "page": 2,
          "chunk_id": "doc_3f17e2e37c34_p2_c1",
          "score": 0.7974
        },
        {
          "filename": "v2_anexo_penalizaciones_sla.pdf",
          "page": 3,
          "chunk_id": "doc_3f17e2e37c34_p3_c1",
          "score": 0.7953
        },
        {
          "filename": "v2_anexo_penalizaciones_sla.pdf",
          "page": 4,
          "chunk_id": "doc_3f17e2e37c34_p4_c1",
          "score": 0.7859
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

Estado: `completed` | confianza: `0.90`

**Fuentes**
- ERP
- Produccion
- Documentos

**Citas documentales**
- `v2_procedimiento_produccion_bloqueos.pdf` - pagina `2` - chunk `doc_e337740a84aa_p2_c1` - score `0.8223`
- `v2_anexo_penalizaciones_sla.pdf` - pagina `3` - chunk `doc_3f17e2e37c34_p3_c1` - score `0.8180`
- `v2_contrato_marco_logistica_2026.pdf` - pagina `2` - chunk `doc_dbae4fa99803_p2_c2` - score `0.8089`
- `v2_procedimiento_produccion_bloqueos.pdf` - pagina `1` - chunk `doc_e337740a84aa_p1_c1` - score `0.8026`
- `v2_anexo_penalizaciones_sla.pdf` - pagina `2` - chunk `doc_3f17e2e37c34_p2_c1` - score `0.7992`

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
          "filename": "v2_procedimiento_produccion_bloqueos.pdf",
          "page": 2,
          "chunk_id": "doc_e337740a84aa_p2_c1",
          "score": 0.8223
        },
        {
          "filename": "v2_anexo_penalizaciones_sla.pdf",
          "page": 3,
          "chunk_id": "doc_3f17e2e37c34_p3_c1",
          "score": 0.818
        },
        {
          "filename": "v2_contrato_marco_logistica_2026.pdf",
          "page": 2,
          "chunk_id": "doc_dbae4fa99803_p2_c2",
          "score": 0.8089
        },
        {
          "filename": "v2_procedimiento_produccion_bloqueos.pdf",
          "page": 1,
          "chunk_id": "doc_e337740a84aa_p1_c1",
          "score": 0.8026
        },
        {
          "filename": "v2_anexo_penalizaciones_sla.pdf",
          "page": 2,
          "chunk_id": "doc_3f17e2e37c34_p2_c1",
          "score": 0.7992
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
El pedido 10252 está bloqueado en producción debido a falta de material. El siguiente punto de atención es el pedido 10252.

| Pedido | Cliente | Estado producción | Motivo |
| --- | --- | --- | --- |
| 10252 | ALFKI - Alfreds Futterkiste | Bloqueado | Falta de material |

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
Con los datos disponibles, el impacto económico del pedido referenciado es 10252: 1863.00.

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

### BT-V2-01 - PASS - V2: hitos y evidencias minimas

Pregunta ejecutada: `Segun v2_contrato_marco_logistica_2026.pdf, que hitos obligatorios debe conservar cada expedicion?`

Resultado esperado desde el evaluador: Debe recuperar el contrato v2 y citar la pagina donde estan los hitos y evidencias minimas.

Respuesta exacta visible en Chainlit:

```markdown
Según el v2_contrato_marco_logistica_2026.pdf, cada expedición debe conservar cinco hitos obligatorios: liberación de producción, preparación de almacén, salida de muelle, entrega al transportista y confirmación de entrega. Cada uno de estos hitos debe registrar la fecha, el usuario o sistema de origen, el estado anterior, el estado nuevo y una observación de negocio si el cambio afecta al cliente.

Estado: `completed` | confianza: `0.90`

**Fuentes**
- Documentos

**Citas documentales**
- `v2_contrato_marco_logistica_2026.pdf` - pagina `3` - chunk `doc_dbae4fa99803_p3_c1` - score `0.8547`
- `v2_contrato_marco_logistica_2026.pdf` - pagina `1` - chunk `doc_dbae4fa99803_p1_c1` - score `0.8118`
- `v2_contrato_marco_logistica_2026.pdf` - pagina `4` - chunk `doc_dbae4fa99803_p4_c1` - score `0.7876`
- `v2_contrato_marco_logistica_2026.pdf` - pagina `3` - chunk `doc_dbae4fa99803_p3_c2` - score `0.7867`

**Pasos ejecutados**
1. Consulta RAG documental con chunks recuperados

**Tool calls**
- `DocumentRAGTool.query` [success]: 4 chunks recuperados de v2_contrato_marco_logistica_2026.pdf
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
        "query": "Según v2_contrato_marco_logistica_2026.pdf, qué hitos obligatorios debe conservar cada expedición?",
        "top_k": 5,
        "min_score": 0.2,
        "filename": null
      },
      "output_summary": "4 chunks recuperados de v2_contrato_marco_logistica_2026.pdf",
      "error": null
    }
  ],
  "fallbacks": [],
  "data": {
    "rag": {
      "status": "completed",
      "chunks_count": 4,
      "documents": [
        "v2_contrato_marco_logistica_2026.pdf"
      ],
      "citations": [
        {
          "filename": "v2_contrato_marco_logistica_2026.pdf",
          "page": 3,
          "chunk_id": "doc_dbae4fa99803_p3_c1",
          "score": 0.8547
        },
        {
          "filename": "v2_contrato_marco_logistica_2026.pdf",
          "page": 1,
          "chunk_id": "doc_dbae4fa99803_p1_c1",
          "score": 0.8118
        },
        {
          "filename": "v2_contrato_marco_logistica_2026.pdf",
          "page": 4,
          "chunk_id": "doc_dbae4fa99803_p4_c1",
          "score": 0.7876
        },
        {
          "filename": "v2_contrato_marco_logistica_2026.pdf",
          "page": 3,
          "chunk_id": "doc_dbae4fa99803_p3_c2",
          "score": 0.7867
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
Para aplicar una penalización, es obligatorio que consten el order_id, customer_id, importe del pedido, fecha prometida, fecha real de entrega, fecha de liberación, transportista, causa del retraso y la fuente responsable. Además, la penalización solo procede si hay evidencia completa en ERP, producción y prueba de entrega.

Si no se puede demostrar la causa del retraso, el sistema debe informar que no hay evidencia suficiente para asignar responsabilidad y, por lo tanto, no se aplicará ninguna penalización.

Estado: `completed` | confianza: `0.90`

**Fuentes**
- Documentos

**Citas documentales**
- `v2_anexo_penalizaciones_sla.pdf` - pagina `2` - chunk `doc_3f17e2e37c34_p2_c1` - score `0.8859`
- `v2_anexo_penalizaciones_sla.pdf` - pagina `1` - chunk `doc_3f17e2e37c34_p1_c2` - score `0.8590`
- `v2_anexo_penalizaciones_sla.pdf` - pagina `1` - chunk `doc_3f17e2e37c34_p1_c1` - score `0.8536`
- `v2_anexo_penalizaciones_sla.pdf` - pagina `2` - chunk `doc_3f17e2e37c34_p2_c2` - score `0.8496`
- `v2_anexo_penalizaciones_sla.pdf` - pagina `3` - chunk `doc_3f17e2e37c34_p3_c1` - score `0.8456`

**Pasos ejecutados**
1. Consulta RAG documental con chunks recuperados

**Tool calls**
- `DocumentRAGTool.query` [success]: 5 chunks recuperados de v2_anexo_penalizaciones_sla.pdf
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
        "top_k": 5,
        "min_score": 0.2,
        "filename": null
      },
      "output_summary": "5 chunks recuperados de v2_anexo_penalizaciones_sla.pdf",
      "error": null
    }
  ],
  "fallbacks": [],
  "data": {
    "rag": {
      "status": "completed",
      "chunks_count": 5,
      "documents": [
        "v2_anexo_penalizaciones_sla.pdf"
      ],
      "citations": [
        {
          "filename": "v2_anexo_penalizaciones_sla.pdf",
          "page": 2,
          "chunk_id": "doc_3f17e2e37c34_p2_c1",
          "score": 0.8859
        },
        {
          "filename": "v2_anexo_penalizaciones_sla.pdf",
          "page": 1,
          "chunk_id": "doc_3f17e2e37c34_p1_c2",
          "score": 0.859
        },
        {
          "filename": "v2_anexo_penalizaciones_sla.pdf",
          "page": 1,
          "chunk_id": "doc_3f17e2e37c34_p1_c1",
          "score": 0.8536
        },
        {
          "filename": "v2_anexo_penalizaciones_sla.pdf",
          "page": 2,
          "chunk_id": "doc_3f17e2e37c34_p2_c2",
          "score": 0.8496
        },
        {
          "filename": "v2_anexo_penalizaciones_sla.pdf",
          "page": 3,
          "chunk_id": "doc_3f17e2e37c34_p3_c1",
          "score": 0.8456
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
Según el documento v2_anexo_penalizaciones_sla.pdf, las exclusiones de penalización se aplican cuando el retraso se debe a: bloqueo de producción, falta de material, falta de capacidad, avería de línea, retrabajo por calidad, espera de validación técnica, fuerza mayor, error de dirección aportado por el cliente o cambio de prioridad aprobado por dirección comercial.

Las pausas del contador de SLA ocurren desde la fecha de bloqueo hasta la fecha de desbloqueo registrada por producción. En el caso de exportaciones, también puede pausarse por documentación aduanera o sanitaria incompleta, siempre que el expediente contenga el evento, responsable y fecha de resolución.

Estado: `completed` | confianza: `0.90`

**Fuentes**
- Documentos

**Citas documentales**
- `v2_anexo_penalizaciones_sla.pdf` - pagina `3` - chunk `doc_3f17e2e37c34_p3_c1` - score `0.8661`
- `v2_anexo_penalizaciones_sla.pdf` - pagina `1` - chunk `doc_3f17e2e37c34_p1_c2` - score `0.8390`
- `v2_anexo_penalizaciones_sla.pdf` - pagina `1` - chunk `doc_3f17e2e37c34_p1_c1` - score `0.8286`
- `v2_anexo_penalizaciones_sla.pdf` - pagina `3` - chunk `doc_3f17e2e37c34_p3_c2` - score `0.8260`
- `v2_anexo_penalizaciones_sla.pdf` - pagina `4` - chunk `doc_3f17e2e37c34_p4_c1` - score `0.8187`

**Pasos ejecutados**
1. Consulta RAG documental con chunks recuperados

**Tool calls**
- `DocumentRAGTool.query` [success]: 5 chunks recuperados de v2_anexo_penalizaciones_sla.pdf
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
        "top_k": 5,
        "min_score": 0.2,
        "filename": null
      },
      "output_summary": "5 chunks recuperados de v2_anexo_penalizaciones_sla.pdf",
      "error": null
    }
  ],
  "fallbacks": [],
  "data": {
    "rag": {
      "status": "completed",
      "chunks_count": 5,
      "documents": [
        "v2_anexo_penalizaciones_sla.pdf"
      ],
      "citations": [
        {
          "filename": "v2_anexo_penalizaciones_sla.pdf",
          "page": 3,
          "chunk_id": "doc_3f17e2e37c34_p3_c1",
          "score": 0.8661
        },
        {
          "filename": "v2_anexo_penalizaciones_sla.pdf",
          "page": 1,
          "chunk_id": "doc_3f17e2e37c34_p1_c2",
          "score": 0.839
        },
        {
          "filename": "v2_anexo_penalizaciones_sla.pdf",
          "page": 1,
          "chunk_id": "doc_3f17e2e37c34_p1_c1",
          "score": 0.8286
        },
        {
          "filename": "v2_anexo_penalizaciones_sla.pdf",
          "page": 3,
          "chunk_id": "doc_3f17e2e37c34_p3_c2",
          "score": 0.826
        },
        {
          "filename": "v2_anexo_penalizaciones_sla.pdf",
          "page": 4,
          "chunk_id": "doc_3f17e2e37c34_p4_c1",
          "score": 0.8187
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
Según el documento v2_procedimiento_produccion_bloqueos.pdf, los motivos de bloqueo válidos son: falta de material, falta de capacidad, incidencia de calidad, mantenimiento no planificado, aprobación técnica pendiente y discrepancia de receta o especificación. Para cada bloqueo, los campos obligatorios a registrar son: order_id, línea de producción, motivo, responsable, fecha de inicio, fecha estimada de desbloqueo, impacto en cliente y comentario operativo.

Estado: `completed` | confianza: `0.90`

**Fuentes**
- Documentos

**Citas documentales**
- `v2_procedimiento_produccion_bloqueos.pdf` - pagina `2` - chunk `doc_e337740a84aa_p2_c1` - score `0.8660`
- `v2_procedimiento_produccion_bloqueos.pdf` - pagina `4` - chunk `doc_e337740a84aa_p4_c1` - score `0.8204`
- `v2_procedimiento_produccion_bloqueos.pdf` - pagina `1` - chunk `doc_e337740a84aa_p1_c1` - score `0.8133`
- `v2_procedimiento_produccion_bloqueos.pdf` - pagina `2` - chunk `doc_e337740a84aa_p2_c2` - score `0.8066`

**Pasos ejecutados**
1. Consulta RAG documental con chunks recuperados

**Tool calls**
- `DocumentRAGTool.query` [success]: 4 chunks recuperados de v2_procedimiento_produccion_bloqueos.pdf
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
        "top_k": 5,
        "min_score": 0.2,
        "filename": null
      },
      "output_summary": "4 chunks recuperados de v2_procedimiento_produccion_bloqueos.pdf",
      "error": null
    }
  ],
  "fallbacks": [],
  "data": {
    "rag": {
      "status": "completed",
      "chunks_count": 4,
      "documents": [
        "v2_procedimiento_produccion_bloqueos.pdf"
      ],
      "citations": [
        {
          "filename": "v2_procedimiento_produccion_bloqueos.pdf",
          "page": 2,
          "chunk_id": "doc_e337740a84aa_p2_c1",
          "score": 0.866
        },
        {
          "filename": "v2_procedimiento_produccion_bloqueos.pdf",
          "page": 4,
          "chunk_id": "doc_e337740a84aa_p4_c1",
          "score": 0.8204
        },
        {
          "filename": "v2_procedimiento_produccion_bloqueos.pdf",
          "page": 1,
          "chunk_id": "doc_e337740a84aa_p1_c1",
          "score": 0.8133
        },
        {
          "filename": "v2_procedimiento_produccion_bloqueos.pdf",
          "page": 2,
          "chunk_id": "doc_e337740a84aa_p2_c2",
          "score": 0.8066
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
Según la política de calidad para entregas, una incidencia de calidad bloquea el pedido hasta que el departamento de Calidad registra una resolución, indicando si el lote se libera, sustituye, reprocesa o rechaza. Producción no puede desbloquear una retención de calidad sin la aprobación de Calidad.

Las entregas parciales requieren aprobación comercial y validación de calidad para cada lote entregado. Si una parte del pedido queda retenida, el albarán debe explicar la parte enviada, la parte pendiente y el motivo de la retención. Además, tanto las incidencias de calidad como las entregas parciales son indicadores que se registran mensualmente.

Estado: `completed` | confianza: `0.90`

**Fuentes**
- Documentos

**Citas documentales**
- `v2_politica_calidad_entregas.pdf` - pagina `2` - chunk `doc_1ffd7b0a8c16_p2_c1` - score `0.8673`
- `v2_politica_calidad_entregas.pdf` - pagina `2` - chunk `doc_1ffd7b0a8c16_p2_c2` - score `0.8424`
- `v2_politica_calidad_entregas.pdf` - pagina `1` - chunk `doc_1ffd7b0a8c16_p1_c1` - score `0.8420`
- `v2_politica_calidad_entregas.pdf` - pagina `3` - chunk `doc_1ffd7b0a8c16_p3_c1` - score `0.8387`
- `v2_politica_calidad_entregas.pdf` - pagina `1` - chunk `doc_1ffd7b0a8c16_p1_c2` - score `0.8122`

**Pasos ejecutados**
1. Consulta RAG documental con chunks recuperados

**Tool calls**
- `DocumentRAGTool.query` [success]: 5 chunks recuperados de v2_politica_calidad_entregas.pdf
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
        "top_k": 5,
        "min_score": 0.2,
        "filename": null
      },
      "output_summary": "5 chunks recuperados de v2_politica_calidad_entregas.pdf",
      "error": null
    }
  ],
  "fallbacks": [],
  "data": {
    "rag": {
      "status": "completed",
      "chunks_count": 5,
      "documents": [
        "v2_politica_calidad_entregas.pdf"
      ],
      "citations": [
        {
          "filename": "v2_politica_calidad_entregas.pdf",
          "page": 2,
          "chunk_id": "doc_1ffd7b0a8c16_p2_c1",
          "score": 0.8673
        },
        {
          "filename": "v2_politica_calidad_entregas.pdf",
          "page": 2,
          "chunk_id": "doc_1ffd7b0a8c16_p2_c2",
          "score": 0.8424
        },
        {
          "filename": "v2_politica_calidad_entregas.pdf",
          "page": 1,
          "chunk_id": "doc_1ffd7b0a8c16_p1_c1",
          "score": 0.842
        },
        {
          "filename": "v2_politica_calidad_entregas.pdf",
          "page": 3,
          "chunk_id": "doc_1ffd7b0a8c16_p3_c1",
          "score": 0.8387
        },
        {
          "filename": "v2_politica_calidad_entregas.pdf",
          "page": 1,
          "chunk_id": "doc_1ffd7b0a8c16_p1_c2",
          "score": 0.8122
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
El impacto económico se calcula uniendo el importe del ERP, el porcentaje contractual y la causa documentada. Si falta alguno de estos tres elementos, no se puede determinar un impacto definitivo. En cuanto a la trazabilidad, toda respuesta de negocio debe especificar las fuentes consultadas (citando el nombre del archivo y la página si es RAG, o la entidad consultada si es ERP, o el order_id y estado operativo si es producción), los pasos ejecutados y las herramientas utilizadas. Además, el razonamiento visible debe ser un resumen auditable que separe los hechos del ERP, las reglas documentales y las conclusiones.

Estado: `completed` | confianza: `0.90`

**Fuentes**
- Documentos

**Citas documentales**
- `v2_condiciones_comerciales_northwind.pdf` - pagina `2` - chunk `doc_32c8bae5e37a_p2_c1` - score `0.8682`
- `v2_condiciones_comerciales_northwind.pdf` - pagina `4` - chunk `doc_32c8bae5e37a_p4_c1` - score `0.8516`
- `v2_condiciones_comerciales_northwind.pdf` - pagina `1` - chunk `doc_32c8bae5e37a_p1_c1` - score `0.8351`
- `v2_condiciones_comerciales_northwind.pdf` - pagina `3` - chunk `doc_32c8bae5e37a_p3_c1` - score `0.8232`
- `v2_condiciones_comerciales_northwind.pdf` - pagina `2` - chunk `doc_32c8bae5e37a_p2_c2` - score `0.7960`

**Pasos ejecutados**
1. Consulta RAG documental con chunks recuperados

**Tool calls**
- `DocumentRAGTool.query` [success]: 5 chunks recuperados de v2_condiciones_comerciales_northwind.pdf
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
        "query": "Según v2_condiciones_comerciales_northwind.pdf, cómo se calcula el impacto económico y qué trazabilidad se exige?",
        "top_k": 5,
        "min_score": 0.2,
        "filename": null
      },
      "output_summary": "5 chunks recuperados de v2_condiciones_comerciales_northwind.pdf",
      "error": null
    }
  ],
  "fallbacks": [],
  "data": {
    "rag": {
      "status": "completed",
      "chunks_count": 5,
      "documents": [
        "v2_condiciones_comerciales_northwind.pdf"
      ],
      "citations": [
        {
          "filename": "v2_condiciones_comerciales_northwind.pdf",
          "page": 2,
          "chunk_id": "doc_32c8bae5e37a_p2_c1",
          "score": 0.8682
        },
        {
          "filename": "v2_condiciones_comerciales_northwind.pdf",
          "page": 4,
          "chunk_id": "doc_32c8bae5e37a_p4_c1",
          "score": 0.8516
        },
        {
          "filename": "v2_condiciones_comerciales_northwind.pdf",
          "page": 1,
          "chunk_id": "doc_32c8bae5e37a_p1_c1",
          "score": 0.8351
        },
        {
          "filename": "v2_condiciones_comerciales_northwind.pdf",
          "page": 3,
          "chunk_id": "doc_32c8bae5e37a_p3_c1",
          "score": 0.8232
        },
        {
          "filename": "v2_condiciones_comerciales_northwind.pdf",
          "page": 2,
          "chunk_id": "doc_32c8bae5e37a_p2_c2",
          "score": 0.796
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
