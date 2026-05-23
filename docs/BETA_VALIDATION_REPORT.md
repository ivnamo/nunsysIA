## Validacion beta obligatoria automatizada

Fecha de ejecucion: 2026-05-23 09:06:10

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
Hay pedidos retrasados en produccion:

| Pedido | Cliente | Estado produccion | Motivo |
| --- | --- | --- | --- |
| 10301 | ANATR - Ana Trujillo Emparedados y helados | Retrasado | Averia en linea de produccion |

El siguiente punto de atencion es el pedido 10301.

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
Para el mes de mayo de 2026, se han identificado 5 pedidos en el ERP. Su estado de producción actual es: 2 pedidos bloqueados, 1 en curso, 1 finalizado y 1 retrasado.

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
Los pedidos standard deben entregarse en un plazo maximo de 5 dias laborables desde la liberacion de produccion. Los pedidos urgentes deben entregarse en un plazo maximo de 48 horas. La penalizacion solo procede cuando existe incumplimiento de plazo, causa imputable al operador logistico y evidencia completa en ERP, produccion y prueba de entrega.

Estado: `completed` | confianza: `0.90`

**Fuentes**
- Documentos

**Citas documentales**
- `v2_contrato_marco_logistica_2026.pdf` - pagina `2` - chunk `doc_b7dc66a61c2f_p2_c1` - score `0.7518`
- `v2_anexo_penalizaciones_sla.pdf` - pagina `1` - chunk `doc_422e41743eb4_p1_c1` - score `0.7401`
- `v2_contrato_marco_logistica_2026.pdf` - pagina `2` - chunk `doc_b7dc66a61c2f_p2_c2` - score `0.7239`
- `v2_contrato_marco_logistica_2026.pdf` - pagina `1` - chunk `doc_b7dc66a61c2f_p1_c1` - score `0.7209`

**Pasos ejecutados**
1. Consulta RAG documental con chunks recuperados

**Tool calls**
- `DocumentRAGTool.query` [success]: 4 chunks recuperados de v2_anexo_penalizaciones_sla.pdf, v2_contrato_marco_logistica_2026.pdf
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
      "output_summary": "4 chunks recuperados de v2_anexo_penalizaciones_sla.pdf, v2_contrato_marco_logistica_2026.pdf",
      "error": null
    }
  ],
  "fallbacks": [],
  "data": {
    "rag": {
      "status": "completed",
      "chunks_count": 4,
      "documents": [
        "v2_anexo_penalizaciones_sla.pdf",
        "v2_contrato_marco_logistica_2026.pdf"
      ],
      "citations": [
        {
          "filename": "v2_contrato_marco_logistica_2026.pdf",
          "page": 2,
          "chunk_id": "doc_b7dc66a61c2f_p2_c1",
          "score": 0.7518
        },
        {
          "filename": "v2_anexo_penalizaciones_sla.pdf",
          "page": 1,
          "chunk_id": "doc_422e41743eb4_p1_c1",
          "score": 0.7401
        },
        {
          "filename": "v2_contrato_marco_logistica_2026.pdf",
          "page": 2,
          "chunk_id": "doc_b7dc66a61c2f_p2_c2",
          "score": 0.7239
        },
        {
          "filename": "v2_contrato_marco_logistica_2026.pdf",
          "page": 1,
          "chunk_id": "doc_b7dc66a61c2f_p1_c1",
          "score": 0.7209
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
El contrato marco de logística 2026 regula la preparación, expedición, entrega y cierre documental de pedidos comerciales durante el año. Establece que los pedidos estándar deben entregarse en un máximo de 5 días laborables desde la liberación de producción, mientras que los pedidos urgentes tienen un plazo de 48 horas. Un pedido se considera bloqueado si producción lo detiene por falta de material, capacidad, incidencia de calidad o aprobación pendiente. El plazo logístico comienza cuando producción libera el pedido y el ERP contiene la dirección de entrega. No se considera incumplimiento logístico si el retraso se debe a falta de material, avería crítica, cambio de prioridad aprobado o datos ERP incompletos. Además, si comercial solicita adelantar un cliente prioritario, es indispensable que Producción confirme la capacidad y Calidad el lote liberado para que el cambio sea válido.

Estado: `completed` | confianza: `0.90`

**Fuentes**
- Documentos

**Citas documentales**
- `v2_contrato_marco_logistica_2026.pdf` - pagina `1` - chunk `doc_b7dc66a61c2f_p1_c1` - score `0.7133`
- `v2_contrato_marco_logistica_2026.pdf` - pagina `3` - chunk `doc_b7dc66a61c2f_p3_c1` - score `0.7107`
- `v2_contrato_marco_logistica_2026.pdf` - pagina `2` - chunk `doc_b7dc66a61c2f_p2_c1` - score `0.7053`
- `v2_contrato_marco_logistica_2026.pdf` - pagina `4` - chunk `doc_b7dc66a61c2f_p4_c1` - score `0.6999`
- `v2_contrato_marco_logistica_2026.pdf` - pagina `2` - chunk `doc_b7dc66a61c2f_p2_c2` - score `0.6628`

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
          "chunk_id": "doc_b7dc66a61c2f_p1_c1",
          "score": 0.7133
        },
        {
          "filename": "v2_contrato_marco_logistica_2026.pdf",
          "page": 3,
          "chunk_id": "doc_b7dc66a61c2f_p3_c1",
          "score": 0.7107
        },
        {
          "filename": "v2_contrato_marco_logistica_2026.pdf",
          "page": 2,
          "chunk_id": "doc_b7dc66a61c2f_p2_c1",
          "score": 0.7053
        },
        {
          "filename": "v2_contrato_marco_logistica_2026.pdf",
          "page": 4,
          "chunk_id": "doc_b7dc66a61c2f_p4_c1",
          "score": 0.6999
        },
        {
          "filename": "v2_contrato_marco_logistica_2026.pdf",
          "page": 2,
          "chunk_id": "doc_b7dc66a61c2f_p2_c2",
          "score": 0.6628
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
Sí, según el PDF, existen penalizaciones por retrasos. Los pedidos urgentes tienen una penalización del 3 por ciento desde el primer día de retraso imputable. Para los pedidos estándar, la penalización es del 2 por ciento si el retraso imputable supera los 2 días laborables, y sube al 5 por ciento si el retraso excede los 5 días laborables.

Estado: `completed` | confianza: `0.90`

**Fuentes**
- Documentos

**Citas documentales**
- `v2_anexo_penalizaciones_sla.pdf` - pagina `1` - chunk `doc_422e41743eb4_p1_c2` - score `0.7714`
- `v2_anexo_penalizaciones_sla.pdf` - pagina `1` - chunk `doc_422e41743eb4_p1_c1` - score `0.7545`
- `v2_anexo_penalizaciones_sla.pdf` - pagina `2` - chunk `doc_422e41743eb4_p2_c1` - score `0.7466`
- `v2_anexo_penalizaciones_sla.pdf` - pagina `3` - chunk `doc_422e41743eb4_p3_c1` - score `0.7394`
- `v2_anexo_penalizaciones_sla.pdf` - pagina `4` - chunk `doc_422e41743eb4_p4_c1` - score `0.7344`

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
          "chunk_id": "doc_422e41743eb4_p1_c2",
          "score": 0.7714
        },
        {
          "filename": "v2_anexo_penalizaciones_sla.pdf",
          "page": 1,
          "chunk_id": "doc_422e41743eb4_p1_c1",
          "score": 0.7545
        },
        {
          "filename": "v2_anexo_penalizaciones_sla.pdf",
          "page": 2,
          "chunk_id": "doc_422e41743eb4_p2_c1",
          "score": 0.7466
        },
        {
          "filename": "v2_anexo_penalizaciones_sla.pdf",
          "page": 3,
          "chunk_id": "doc_422e41743eb4_p3_c1",
          "score": 0.7394
        },
        {
          "filename": "v2_anexo_penalizaciones_sla.pdf",
          "page": 4,
          "chunk_id": "doc_422e41743eb4_p4_c1",
          "score": 0.7344
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
- `v2_anexo_penalizaciones_sla.pdf` - pagina `3` - chunk `doc_422e41743eb4_p3_c1` - score `0.7716`
- `v2_contrato_marco_logistica_2026.pdf` - pagina `2` - chunk `doc_b7dc66a61c2f_p2_c2` - score `0.7641`
- `v2_procedimiento_produccion_bloqueos.pdf` - pagina `2` - chunk `doc_b2f2bf0b785c_p2_c1` - score `0.7598`
- `v2_anexo_penalizaciones_sla.pdf` - pagina `2` - chunk `doc_422e41743eb4_p2_c1` - score `0.7591`
- `v2_anexo_penalizaciones_sla.pdf` - pagina `1` - chunk `doc_422e41743eb4_p1_c1` - score `0.7542`

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
          "chunk_id": "doc_422e41743eb4_p3_c1",
          "score": 0.7716
        },
        {
          "filename": "v2_contrato_marco_logistica_2026.pdf",
          "page": 2,
          "chunk_id": "doc_b7dc66a61c2f_p2_c2",
          "score": 0.7641
        },
        {
          "filename": "v2_procedimiento_produccion_bloqueos.pdf",
          "page": 2,
          "chunk_id": "doc_b2f2bf0b785c_p2_c1",
          "score": 0.7598
        },
        {
          "filename": "v2_anexo_penalizaciones_sla.pdf",
          "page": 2,
          "chunk_id": "doc_422e41743eb4_p2_c1",
          "score": 0.7591
        },
        {
          "filename": "v2_anexo_penalizaciones_sla.pdf",
          "page": 1,
          "chunk_id": "doc_422e41743eb4_p1_c1",
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

### BT-V2-01 - PASS - V2: hitos y evidencias minimas

Pregunta ejecutada: `Segun v2_contrato_marco_logistica_2026.pdf, que hitos obligatorios debe conservar cada expedicion?`

Resultado esperado desde el evaluador: Debe recuperar el contrato v2 y citar la pagina donde estan los hitos y evidencias minimas.

Respuesta exacta visible en Chainlit:

```markdown
Según el documento v2_contrato_marco_logistica_2026.pdf, cada expedición debe conservar cinco hitos obligatorios: liberación de producción, preparación de almacén, salida de muelle, entrega al transportista y confirmación de entrega.

Estado: `completed` | confianza: `0.90`

**Fuentes**
- Documentos

**Citas documentales**
- `v2_contrato_marco_logistica_2026.pdf` - pagina `3` - chunk `doc_b7dc66a61c2f_p3_c1` - score `0.8324`
- `v2_contrato_marco_logistica_2026.pdf` - pagina `1` - chunk `doc_b7dc66a61c2f_p1_c1` - score `0.7476`
- `v2_contrato_marco_logistica_2026.pdf` - pagina `3` - chunk `doc_b7dc66a61c2f_p3_c2` - score `0.7289`
- `v2_contrato_marco_logistica_2026.pdf` - pagina `4` - chunk `doc_b7dc66a61c2f_p4_c1` - score `0.7272`

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
        "query": "Segun v2_contrato_marco_logistica_2026.pdf, que hitos obligatorios debe conservar cada expedicion?",
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
          "chunk_id": "doc_b7dc66a61c2f_p3_c1",
          "score": 0.8324
        },
        {
          "filename": "v2_contrato_marco_logistica_2026.pdf",
          "page": 1,
          "chunk_id": "doc_b7dc66a61c2f_p1_c1",
          "score": 0.7476
        },
        {
          "filename": "v2_contrato_marco_logistica_2026.pdf",
          "page": 3,
          "chunk_id": "doc_b7dc66a61c2f_p3_c2",
          "score": 0.7289
        },
        {
          "filename": "v2_contrato_marco_logistica_2026.pdf",
          "page": 4,
          "chunk_id": "doc_b7dc66a61c2f_p4_c1",
          "score": 0.7272
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
Para aplicar una penalización, es obligatorio que consten el order_id, customer_id, importe del pedido (procedente de líneas ERP), fecha prometida, fecha real de entrega, fecha de liberación, transportista, causa del retraso y la fuente responsable. Si no se puede demostrar la causa del retraso, el sistema debe informar que no hay evidencia suficiente para asignar responsabilidad y no se aplicará la penalización. La penalización solo procede cuando hay incumplimiento de plazo, la causa es imputable al operador logístico y existe evidencia completa en ERP, producción y prueba de entrega.

Estado: `completed` | confianza: `0.90`

**Fuentes**
- Documentos

**Citas documentales**
- `v2_anexo_penalizaciones_sla.pdf` - pagina `2` - chunk `doc_422e41743eb4_p2_c1` - score `0.8335`
- `v2_anexo_penalizaciones_sla.pdf` - pagina `2` - chunk `doc_422e41743eb4_p2_c2` - score `0.8016`
- `v2_anexo_penalizaciones_sla.pdf` - pagina `3` - chunk `doc_422e41743eb4_p3_c1` - score `0.7655`
- `v2_anexo_penalizaciones_sla.pdf` - pagina `1` - chunk `doc_422e41743eb4_p1_c1` - score `0.7619`
- `v2_anexo_penalizaciones_sla.pdf` - pagina `1` - chunk `doc_422e41743eb4_p1_c2` - score `0.7549`

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
          "chunk_id": "doc_422e41743eb4_p2_c1",
          "score": 0.8335
        },
        {
          "filename": "v2_anexo_penalizaciones_sla.pdf",
          "page": 2,
          "chunk_id": "doc_422e41743eb4_p2_c2",
          "score": 0.8016
        },
        {
          "filename": "v2_anexo_penalizaciones_sla.pdf",
          "page": 3,
          "chunk_id": "doc_422e41743eb4_p3_c1",
          "score": 0.7655
        },
        {
          "filename": "v2_anexo_penalizaciones_sla.pdf",
          "page": 1,
          "chunk_id": "doc_422e41743eb4_p1_c1",
          "score": 0.7619
        },
        {
          "filename": "v2_anexo_penalizaciones_sla.pdf",
          "page": 1,
          "chunk_id": "doc_422e41743eb4_p1_c2",
          "score": 0.7549
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
Las exclusiones de SLA se aplican cuando el retraso se debe a bloqueo de producción, falta de material o capacidad, avería de línea, retrabajo por calidad, espera de validación técnica, fuerza mayor, error de dirección del cliente o cambio de prioridad aprobado por dirección comercial. Las pausas de SLA ocurren desde la fecha de bloqueo hasta la fecha de desbloqueo registrada por producción. En exportación, también puede pausarse por documentación aduanera o sanitaria incompleta, siempre que el expediente contenga evento, responsable y fecha de resolución.

Estado: `completed` | confianza: `0.90`

**Fuentes**
- Documentos

**Citas documentales**
- `v2_anexo_penalizaciones_sla.pdf` - pagina `3` - chunk `doc_422e41743eb4_p3_c1` - score `0.8320`
- `v2_anexo_penalizaciones_sla.pdf` - pagina `3` - chunk `doc_422e41743eb4_p3_c2` - score `0.7686`
- `v2_anexo_penalizaciones_sla.pdf` - pagina `1` - chunk `doc_422e41743eb4_p1_c2` - score `0.7616`
- `v2_anexo_penalizaciones_sla.pdf` - pagina `1` - chunk `doc_422e41743eb4_p1_c1` - score `0.7590`
- `v2_anexo_penalizaciones_sla.pdf` - pagina `4` - chunk `doc_422e41743eb4_p4_c1` - score `0.7541`

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
          "chunk_id": "doc_422e41743eb4_p3_c1",
          "score": 0.832
        },
        {
          "filename": "v2_anexo_penalizaciones_sla.pdf",
          "page": 3,
          "chunk_id": "doc_422e41743eb4_p3_c2",
          "score": 0.7686
        },
        {
          "filename": "v2_anexo_penalizaciones_sla.pdf",
          "page": 1,
          "chunk_id": "doc_422e41743eb4_p1_c2",
          "score": 0.7616
        },
        {
          "filename": "v2_anexo_penalizaciones_sla.pdf",
          "page": 1,
          "chunk_id": "doc_422e41743eb4_p1_c1",
          "score": 0.759
        },
        {
          "filename": "v2_anexo_penalizaciones_sla.pdf",
          "page": 4,
          "chunk_id": "doc_422e41743eb4_p4_c1",
          "score": 0.7541
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
Los motivos de bloqueo válidos, según el documento, son: falta de material, falta de capacidad, incidencia de calidad, mantenimiento no planificado, aprobación técnica pendiente y discrepancia de receta o especificación. Cada bloqueo debe registrar los siguientes campos obligatorios: order_id, línea de producción, motivo, responsable, fecha de inicio, fecha estimada de desbloqueo, impacto en cliente y comentario operativo.

Estado: `completed` | confianza: `0.90`

**Fuentes**
- Documentos

**Citas documentales**
- `v2_procedimiento_produccion_bloqueos.pdf` - pagina `2` - chunk `doc_b2f2bf0b785c_p2_c1` - score `0.8262`
- `v2_procedimiento_produccion_bloqueos.pdf` - pagina `4` - chunk `doc_b2f2bf0b785c_p4_c1` - score `0.7515`
- `v2_procedimiento_produccion_bloqueos.pdf` - pagina `1` - chunk `doc_b2f2bf0b785c_p1_c1` - score `0.7293`
- `v2_procedimiento_produccion_bloqueos.pdf` - pagina `2` - chunk `doc_b2f2bf0b785c_p2_c2` - score `0.7274`
- `v2_procedimiento_produccion_bloqueos.pdf` - pagina `3` - chunk `doc_b2f2bf0b785c_p3_c1` - score `0.7015`

**Pasos ejecutados**
1. Consulta RAG documental con chunks recuperados

**Tool calls**
- `DocumentRAGTool.query` [success]: 5 chunks recuperados de v2_procedimiento_produccion_bloqueos.pdf
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
      "output_summary": "5 chunks recuperados de v2_procedimiento_produccion_bloqueos.pdf",
      "error": null
    }
  ],
  "fallbacks": [],
  "data": {
    "rag": {
      "status": "completed",
      "chunks_count": 5,
      "documents": [
        "v2_procedimiento_produccion_bloqueos.pdf"
      ],
      "citations": [
        {
          "filename": "v2_procedimiento_produccion_bloqueos.pdf",
          "page": 2,
          "chunk_id": "doc_b2f2bf0b785c_p2_c1",
          "score": 0.8262
        },
        {
          "filename": "v2_procedimiento_produccion_bloqueos.pdf",
          "page": 4,
          "chunk_id": "doc_b2f2bf0b785c_p4_c1",
          "score": 0.7515
        },
        {
          "filename": "v2_procedimiento_produccion_bloqueos.pdf",
          "page": 1,
          "chunk_id": "doc_b2f2bf0b785c_p1_c1",
          "score": 0.7293
        },
        {
          "filename": "v2_procedimiento_produccion_bloqueos.pdf",
          "page": 2,
          "chunk_id": "doc_b2f2bf0b785c_p2_c2",
          "score": 0.7274
        },
        {
          "filename": "v2_procedimiento_produccion_bloqueos.pdf",
          "page": 3,
          "chunk_id": "doc_b2f2bf0b785c_p3_c1",
          "score": 0.7015
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
En caso de incidencias de calidad, el pedido queda bloqueado hasta que el departamento de Calidad registre una resolución que indique si el lote se libera, sustituye, reprocesa o rechaza. Producción no puede desbloquear una retención de calidad sin la aprobación de Calidad. Respecto a las entregas parciales, estas requieren aprobación comercial y validación de calidad para cada lote entregado. Si una parte del pedido se retiene, el albarán debe detallar la parte enviada, la pendiente y el motivo de la retención. Ambos escenarios, incidencias de calidad y entregas parciales, se registran como indicadores mensuales.

Estado: `completed` | confianza: `0.90`

**Fuentes**
- Documentos

**Citas documentales**
- `v2_politica_calidad_entregas.pdf` - pagina `2` - chunk `doc_49793e4d5985_p2_c1` - score `0.8227`
- `v2_politica_calidad_entregas.pdf` - pagina `3` - chunk `doc_49793e4d5985_p3_c1` - score `0.7754`
- `v2_politica_calidad_entregas.pdf` - pagina `2` - chunk `doc_49793e4d5985_p2_c2` - score `0.7738`
- `v2_politica_calidad_entregas.pdf` - pagina `1` - chunk `doc_49793e4d5985_p1_c1` - score `0.7541`
- `v2_politica_calidad_entregas.pdf` - pagina `1` - chunk `doc_49793e4d5985_p1_c2` - score `0.7027`

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
          "chunk_id": "doc_49793e4d5985_p2_c1",
          "score": 0.8227
        },
        {
          "filename": "v2_politica_calidad_entregas.pdf",
          "page": 3,
          "chunk_id": "doc_49793e4d5985_p3_c1",
          "score": 0.7754
        },
        {
          "filename": "v2_politica_calidad_entregas.pdf",
          "page": 2,
          "chunk_id": "doc_49793e4d5985_p2_c2",
          "score": 0.7738
        },
        {
          "filename": "v2_politica_calidad_entregas.pdf",
          "page": 1,
          "chunk_id": "doc_49793e4d5985_p1_c1",
          "score": 0.7541
        },
        {
          "filename": "v2_politica_calidad_entregas.pdf",
          "page": 1,
          "chunk_id": "doc_49793e4d5985_p1_c2",
          "score": 0.7027
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
Para calcular el impacto económico, el documento v2_condiciones_comerciales_northwind.pdf establece que se deben unir el importe del ERP, el porcentaje contractual y la causa documentada. Si alguno de estos tres elementos falta, no se puede calcular un impacto definitivo. Es importante destacar que la cabecera de un pedido no es suficiente para calcular el impacto económico si faltan precios, cantidades o descuentos.En cuanto a la trazabilidad, toda respuesta de negocio debe indicar las fuentes consultadas, los pasos ejecutados y las herramientas utilizadas. El razonamiento visible debe ser un resumen auditable. Las fuentes deben citarse de la siguiente manera: para RAG, se debe indicar el nombre del archivo y la página; para ERP, la entidad consultada; y para producción, el order_id y el estado operativo. Es crucial que las respuestas separen los hechos del ERP, las reglas documentales y las conclusiones.

Estado: `completed` | confianza: `0.90`

**Fuentes**
- Documentos

**Citas documentales**
- `v2_condiciones_comerciales_northwind.pdf` - pagina `2` - chunk `doc_1a4fb5d1012f_p2_c1` - score `0.8050`
- `v2_condiciones_comerciales_northwind.pdf` - pagina `4` - chunk `doc_1a4fb5d1012f_p4_c1` - score `0.7815`
- `v2_condiciones_comerciales_northwind.pdf` - pagina `1` - chunk `doc_1a4fb5d1012f_p1_c1` - score `0.7430`
- `v2_condiciones_comerciales_northwind.pdf` - pagina `3` - chunk `doc_1a4fb5d1012f_p3_c1` - score `0.7295`
- `v2_condiciones_comerciales_northwind.pdf` - pagina `2` - chunk `doc_1a4fb5d1012f_p2_c2` - score `0.7108`

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
        "query": "Segun v2_condiciones_comerciales_northwind.pdf, como se calcula el impacto economico y que trazabilidad se exige?",
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
          "chunk_id": "doc_1a4fb5d1012f_p2_c1",
          "score": 0.805
        },
        {
          "filename": "v2_condiciones_comerciales_northwind.pdf",
          "page": 4,
          "chunk_id": "doc_1a4fb5d1012f_p4_c1",
          "score": 0.7815
        },
        {
          "filename": "v2_condiciones_comerciales_northwind.pdf",
          "page": 1,
          "chunk_id": "doc_1a4fb5d1012f_p1_c1",
          "score": 0.743
        },
        {
          "filename": "v2_condiciones_comerciales_northwind.pdf",
          "page": 3,
          "chunk_id": "doc_1a4fb5d1012f_p3_c1",
          "score": 0.7295
        },
        {
          "filename": "v2_condiciones_comerciales_northwind.pdf",
          "page": 2,
          "chunk_id": "doc_1a4fb5d1012f_p2_c2",
          "score": 0.7108
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
