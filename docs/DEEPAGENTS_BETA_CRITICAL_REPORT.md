## Validacion beta obligatoria automatizada

Fecha de ejecucion: 2026-05-22 20:20:47

- Resultado global: PASS=0, PARTIAL=0, FAIL=5, BLOCKER=0.
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

### BT-08 - FAIL - Mixta: penalizaciones por pedido

Pregunta ejecutada: `en funcion de los pedidos y su estado dime que penalizaciones vamos a tener en cada uno`

Resultado esperado desde el evaluador: Debe combinar pedidos ERP, estado de produccion y reglas documentales.

Respuesta exacta visible en Chainlit:

```markdown
A continuación se detalla el análisis de penalizaciones aplicables para cada pedido, basado en la información de ERP, los estados de producción y el **Anexo de Penalizaciones y SLA (versión extendida)**:

---

### **Resumen del Anexo de Penalizaciones y SLA**
*   **Plazo Estándar:** 5 días laborables desde la liberación final.
*   **Regla de Penalización (Pedidos Estándar):**
    *   Retraso imputable entre >2 y 5 días laborables: **2% de penalización**.
    *   Retraso imputable de más de 5 días laborables: **5% de penalización**.
*   **Exclusiones de Penalización:** No se aplican penalizaciones si el retraso procede de **bloqueo de producción**, **falta de material**, **falta de capacidad**, **avería de línea**, **retrabajo por calidad**, **espera de validación técnica** o **fuerza mayor**.

---

### **Análisis Detallado por Pedido**

#### **1. Pedido 10248 (Alfreds Futterkiste)**
*   **Importe:** 440.00
*   **Estado ERP:** Pendiente (`pending`)
*   **Fecha de pedido:** 02/05/2026 (Sábado. El plazo estándar de 5 días laborables vencía el 08/05/2026).
*   **Fecha estimada de fin (Producción):** 22/05/2026
*   **Estado de Producción:** En progreso (`in_progress`) sin causa de exclusión de retraso (`blocked_reason = null`, `delay_reason = null`).
*   **Análisis:** Al no tener registrada ninguna causa de exclusión (como falta de material, avería, etc.), el retraso es imputable al operador logístico. La demora acumulada es de aproximadamente 10 días laborables (superando los 5 días de margen de SLA).
*   **Penalización Aplicable:** **5% sobre el importe** $\rightarrow$ **22.00**

#### **2. Pedido 10252 (Alfreds Futterkiste)**
*   **Importe:** 1,863.00
*   **Estado ERP:** Pendiente (`pending`)
*   **Estado de Producción:** Bloqueado (`blocked`) por **Falta de material**.
*   **Análisis:** Según el Anexo de SLA, los retrasos originados por falta de material están explícitamente excluidos de penalización.
*   **Penalización Aplicable:** **0.00 (Excluido)**

#### **3. Pedido 10255 (Alfreds Futterkiste)**
*   **Importe:** 2,490.00
*   **Estado ERP:** Enviado (`shipped`)
*   **Estado de Producción:** Finalizado (`finished`) el 14/05/2026 (pedido realizado el 11/05/2026).
*   **Análisis:** El pedido se procesó y envió correctamente dentro del plazo de 5 días laborables.
*   **Penalización Aplicable:** **0.00 (Sin penalización)**

#### **4. Pedido 10301 (Ana Trujillo Emparedados y helados)**
*   **Importe:** 920.00
*   **Estado ERP:** Pendiente (`pending`)
*   **Estado de Producción:** Retrasado (`delayed`) por **Avería en línea de producción**.
*   **Análisis:** El anexo del contrato excluye específicamente los retrasos generados por averías críticas en las líneas de producción.
*   **Penalización Aplicable:** **0.00 (Excluido)**

#### **5. Pedido 10312 (Bon app)**
*   **Importe:** 1,210.00
*   **Estado ERP:** Pendiente (`pending`)
*   **Estado de Producción:** Bloqueado (`blocked`) por **Falta de capacidad**.
*   **Análisis:** La falta de capacidad está definida en el contrato marco como un caso no penalizable.
*   **Penalización Aplicable:** **0.00 (Excluido)**

---

### **Conclusión**
La única penalización que se va a aplicar corresponde al **Pedido 10248** por un importe de **22.00** debido a un retraso logístico injustificado. Los demás pedidos pendientes están protegidos por las cláusulas de exclusión técnica de producción o se entregaron dentro del plazo.

Estado: `completed` | confianza: `0.75`

**Fuentes**
- ERP
- Produccion
- Documentos

**Citas documentales**
- `v2_anexo_penalizaciones_sla.pdf` - pagina `3` - chunk `doc_5055518ed47d_p3_c1` - score `0.8336`
- `v2_anexo_penalizaciones_sla.pdf` - pagina `1` - chunk `doc_5055518ed47d_p1_c1` - score `0.8013`
- `v2_contrato_marco_logistica_2026.pdf` - pagina `2` - chunk `doc_2d42acd9fdb2_p2_c2` - score `0.7998`

**Pasos ejecutados**
1. Consulta ERP mediante filtros seguros
2. Consulta Produccion mediante filtros seguros
3. Consulta RAG documental con chunks recuperados

**Tool calls**
- `ERPQueryTool.query_orders` [success]: 5 pedidos ERP encontrados por DSL segura
- `ProductionQueryTool.query_orders` [success]: 5 pedidos de produccion encontrados por DSL segura
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
              10252,
              10255,
              10301,
              10312
            ]
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
      "output_summary": "5 pedidos de produccion encontrados por DSL segura",
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
          "chunk_id": "doc_5055518ed47d_p3_c1",
          "score": 0.8336
        },
        {
          "filename": "v2_anexo_penalizaciones_sla.pdf",
          "page": 1,
          "chunk_id": "doc_5055518ed47d_p1_c1",
          "score": 0.8013
        },
        {
          "filename": "v2_contrato_marco_logistica_2026.pdf",
          "page": 2,
          "chunk_id": "doc_2d42acd9fdb2_p2_c2",
          "score": 0.7998
        }
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

Incidencias detectadas:
- tool obligatoria ausente: ERPTool
- tool obligatoria ausente: ProductionAPITool

Veredicto: `FAIL`

### BT-09 - FAIL - Memoria conversacional

Turno 1: `Que pedidos pendientes tiene el cliente ALFKI?`

Resultado esperado desde el evaluador: Debe resolver referencias conversacionales sin usar memoria como fuente de verdad de negocio.

Respuesta exacta visible en Chainlit:

```markdown
El cliente **ALFKI** (Alfreds Futterkiste) tiene los siguientes **2 pedidos pendientes**:

1. **Pedido ID: 10248**
   - **Fecha del pedido:** 2026-05-02
   - **Fecha requerida:** 2026-05-20
   - **Importe:** 440.00
   - **Estado ERP:** Pendiente (`pending`)

2. **Pedido ID: 10252**
   - **Fecha del pedido:** 2026-05-07
   - **Fecha requerida:** 2026-05-25
   - **Importe:** 1863.00
   - **Estado ERP:** Pendiente (`pending`)

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
De los dos pedidos pendientes del cliente **ALFKI**, el estado de su producción es el siguiente:

*   **Pedido ID: 10252** — **Bloqueado** (`blocked`)
    *   **Motivo de bloqueo:** Falta de material
    *   **Fecha estimada de finalización:** 2026-05-30
    *   **Importe:** 1.863,00 €

*   **Pedido ID: 10248** — **En curso** (`in_progress`)
    *   *No se encuentra bloqueado.*
    *   **Fecha estimada de finalización:** 2026-05-22
    *   **Importe:** 440,00 €

Estado: `completed` | confianza: `0.75`

**Fuentes**
- Memoria
- ERP
- Produccion

**Pasos ejecutados**
1. Consulta memoria conversacional
2. Consulta memoria conversacional
3. Consulta ERP mediante filtros seguros
4. Consulta API de produccion para pedidos referenciados

**Tool calls**
- `MemoryTool.recall` [success]: Memoria conversacional: 1 interacciones recuperadas
- `MemoryTool.recall` [success]: Memoria conversacional: 1 interacciones recuperadas
- `ERPQueryTool.query_orders` [success]: 2 pedidos ERP encontrados por DSL segura
- `ProductionAPITool.get_status_for_order_ids` [success]: 2 pedidos de produccion encontrados por ids
```

Evidencia tecnica resumida:

```json
{
  "status": "completed",
  "sources": [
    "Memoria",
    "ERP",
    "Produccion"
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
      "tool": "MemoryTool",
      "action": "recall",
      "status": "success",
      "source": "Memoria",
      "args": {
        "query": "cuales de esos pedidos estan bloqueados",
        "max_turns": 5
      },
      "output_summary": "Memoria conversacional: 1 interacciones recuperadas",
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
    "erp_query_orders_count": 2,
    "erp_query_order_ids": [
      10248,
      10252
    ],
    "production_orders_count": 2,
    "production_order_ids": [
      10248,
      10252
    ],
    "production_statuses_count": 2,
    "memory": {
      "status": "found",
      "turns_count": 1,
      "customer_id": "ALFKI",
      "order_ids": [
        10248,
        10252
      ]
    },
    "deepagents_planning": {
      "todos_used": true,
      "todo_tool_calls_count": 4
    }
  },
  "failure_reason": null
}
```

Turno 3: `Cual es el impacto economico de esos?`

Resultado esperado desde el evaluador: Debe resolver referencias conversacionales sin usar memoria como fuente de verdad de negocio.

Respuesta exacta visible en Chainlit:

```markdown
El impacto económico de los pedidos afectados para el cliente **ALFKI** asciende a un total de **2.303,00 €**, distribuidos de la siguiente manera:

1. **Pedido ID: 10252 (Bloqueado por falta de material)**
   * **Importe afectado:** 1.863,00 €
   * **Fecha requerida:** 2026-05-25
   * **Fecha estimada de finalización:** 2026-05-30
   * **Impacto temporal:** Retraso estimado de **5 días**.

2. **Pedido ID: 10248 (En curso con retraso)**
   * **Importe afectado:** 440,00 €
   * **Fecha requerida:** 2026-05-20
   * **Fecha estimada de finalización:** 2026-05-22
   * **Impacto temporal:** Retraso estimado de **2 días**.

Estado: `completed` | confianza: `0.75`

**Fuentes**
- Memoria
- ERP
- Produccion

**Pasos ejecutados**
1. Consulta memoria conversacional
2. Consulta memoria conversacional
3. Consulta ERP mediante filtros seguros
4. Consulta API de produccion para pedidos referenciados

**Tool calls**
- `MemoryTool.recall` [success]: Memoria conversacional: 2 interacciones recuperadas
- `MemoryTool.recall` [success]: Memoria conversacional: 2 interacciones recuperadas
- `ERPQueryTool.query_orders` [success]: 2 pedidos ERP encontrados por DSL segura
- `ProductionAPITool.get_status_for_order_ids` [success]: 2 pedidos de produccion encontrados por ids
```

Evidencia tecnica resumida:

```json
{
  "status": "completed",
  "sources": [
    "Memoria",
    "ERP",
    "Produccion"
  ],
  "tool_calls": [
    {
      "tool": "MemoryTool",
      "action": "recall",
      "status": "success",
      "source": "Memoria",
      "args": {
        "query": "beta-obligatory-bt-09",
        "max_turns": 5
      },
      "output_summary": "Memoria conversacional: 2 interacciones recuperadas",
      "error": null
    },
    {
      "tool": "MemoryTool",
      "action": "recall",
      "status": "success",
      "source": "Memoria",
      "args": {
        "query": "impacto economico de los pedidos 10248 y 10252 de ALFKI penalizaciones retraso contrato SLA",
        "max_turns": 5
      },
      "output_summary": "Memoria conversacional: 2 interacciones recuperadas",
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
    "erp_query_orders_count": 2,
    "erp_query_order_ids": [
      10248,
      10252
    ],
    "production_orders_count": 2,
    "production_order_ids": [
      10248,
      10252
    ],
    "production_statuses_count": 2,
    "memory": {
      "status": "found",
      "turns_count": 2,
      "customer_id": "ALFKI",
      "order_ids": [
        10248,
        10252
      ]
    },
    "deepagents_planning": {
      "todos_used": true,
      "todo_tool_calls_count": 4
    }
  },
  "failure_reason": null
}
```

Incidencias detectadas:
- sources esperadas ['Memoria', 'Produccion', 'ERP'], recibidas ['Memoria', 'ERP', 'Produccion']
- tool obligatoria ausente: ERPTool
- sources esperadas ['Memoria', 'ERP'], recibidas ['Memoria', 'ERP', 'Produccion']
- tool obligatoria ausente: ERPTool
- termino obligatorio ausente en answer: '1863.00'
- data.economic_impact_total esperado '1863.00', recibido None
- data.order_amount_order_ids no es lista: None

Veredicto: `FAIL`

### BT-10 - FAIL - Guardrail RAG

Pregunta ejecutada: `Segun el PDF, que receta de cocina vegana recomienda?`

Resultado esperado desde el evaluador: Debe rechazar por contexto documental insuficiente y no inventar.

Respuesta exacta visible en Chainlit:

```markdown
No es posible responder a la pregunta sobre la receta de cocina vegana recomendada en el PDF debido a que las únicas herramientas de consulta disponibles en esta sesión corresponden al ERP (`query_erp_orders`) y a Producción (`query_production_orders`). 

Al no disponer de herramientas documentales (como RAG o acceso al sistema de archivos) ni haberse devuelto ninguna información relevante sobre recetas en las consultas del ERP y producción, no se puede acceder al contenido de ningún PDF.

Estado: `completed` | confianza: `0.75`

**Fuentes**
- ERP
- Produccion

**Pasos ejecutados**
1. Consulta ERP mediante filtros seguros
2. Consulta Produccion mediante filtros seguros

**Tool calls**
- `ERPQueryTool.query_orders` [success]: 5 pedidos ERP encontrados por DSL segura
- `ProductionQueryTool.query_orders` [success]: 5 pedidos de produccion encontrados por DSL segura
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
        "limit": 50,
        "order_by": null
      },
      "output_summary": "5 pedidos ERP encontrados por DSL segura",
      "error": null
    },
    {
      "tool": "ProductionQueryTool",
      "action": "query_orders",
      "status": "success",
      "source": "Produccion",
      "args": {
        "entity": "production_orders",
        "filters": [],
        "select": [
          "order_id",
          "production_status",
          "blocked_reason",
          "delay_reason",
          "estimated_finish_date"
        ],
        "limit": 50,
        "order_by": null
      },
      "output_summary": "5 pedidos de produccion encontrados por DSL segura",
      "error": null
    }
  ],
  "fallbacks": [],
  "data": {
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
    "deepagents_planning": {
      "todos_used": true,
      "todo_tool_calls_count": 3
    }
  },
  "failure_reason": null
}
```

Incidencias detectadas:
- status esperado 'insufficient_context', recibido 'completed'
- sources esperadas ['Documentos'], recibidas ['ERP', 'Produccion']
- tool obligatoria ausente: DocumentRAGTool
- data.rag.chunks_count esperado 0, recibido None

Veredicto: `FAIL`

### BT-11 - FAIL - Memoria aislada

Pregunta ejecutada: `Y en que estado estan?`

Resultado esperado desde el evaluador: Debe aislar conversaciones por conversation_id y pedir contexto previo.

Respuesta exacta visible en Chainlit:

```markdown
Las órdenes de producción se encuentran en los siguientes estados:

*   **Pedido 10248**: En progreso (`in_progress`). Fecha estimada de finalización: 22 de mayo de 2026.
*   **Pedido 10252**: Bloqueado (`blocked`) por **falta de material**. Fecha estimada de finalización: 30 de mayo de 2026.
*   **Pedido 10255**: Finalizado (`finished`). Fecha de finalización: 14 de mayo de 2026.
*   **Pedido 10301**: Retrasado (`delayed`) debido a una **avería en la línea de producción**. Fecha estimada de finalización: 3 de junio de 2026.
*   **Pedido 10312**: Bloqueado (`blocked`) por **falta de capacidad**. Fecha estimada de finalización: 2 de junio de 2026.

Estado: `completed` | confianza: `0.75`

**Fuentes**
- Produccion

**Pasos ejecutados**
1. Consulta API de produccion por estado
2. Consulta Produccion mediante filtros seguros

**Tool calls**
- `ProductionAPITool.list_orders` [success]: 5 pedidos de produccion encontrados
- `ProductionQueryTool.query_orders` [success]: 5 pedidos de produccion encontrados por DSL segura
```

Evidencia tecnica resumida:

```json
{
  "status": "completed",
  "sources": [
    "Produccion"
  ],
  "tool_calls": [
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
      "tool": "ProductionQueryTool",
      "action": "query_orders",
      "status": "success",
      "source": "Produccion",
      "args": {
        "entity": "production_orders",
        "filters": [],
        "select": [
          "order_id",
          "production_status",
          "blocked_reason",
          "delay_reason",
          "estimated_finish_date"
        ],
        "limit": 50,
        "order_by": null
      },
      "output_summary": "5 pedidos de produccion encontrados por DSL segura",
      "error": null
    }
  ],
  "fallbacks": [],
  "data": {
    "production_orders_count": 5,
    "production_order_ids": [
      10248,
      10252,
      10255,
      10301,
      10312
    ],
    "production_statuses_count": 5
  },
  "failure_reason": null
}
```

Incidencias detectadas:
- status esperado 'needs_clarification', recibido 'completed'
- sources esperadas [], recibidas ['Produccion']

Veredicto: `FAIL`

### BT-V2-07 - FAIL - V2: guardrail documental multipagina

Pregunta ejecutada: `Segun los documentos v2, que receta de cocina vegana recomienda para un cliente premium?`

Resultado esperado desde el evaluador: Debe rechazar por contexto documental insuficiente y no inventar.

Respuesta exacta visible en Chainlit:

```markdown
Tras realizar múltiples consultas exhaustivas en la base de datos documental utilizando las herramientas de búsqueda disponibles (`query_documents` y `answer_document_question_with_citations`), no ha sido posible recuperar ninguna información sobre recetas de cocina vegana o recomendaciones para clientes premium.

Se han intentado búsquedas con diversos términos clave (como `"receta"`, `"cocina"`, `"vegana"`, `"vegano"`, `"premium"`, `"cliente"`, `"v2"`, `"plato"`, entre otros), variando el umbral de puntuación (`min_score` de `0` e incluso valores inferiores) y especificando posibles nombres de archivos (`documentos_v2.pdf`, `recetas_v2.pdf`, `acuerdo_v2.pdf`, etc.). En todos los casos, el sistema documental ha devuelto un estado de **contexto insuficiente** (`insufficient_context`) con una lista de fragmentos completamente vacía.

Por lo tanto, al no haber datos disponibles en el sistema documental de referencia y siguiendo la norma de no inventar información, no es posible determinar qué receta de cocina vegana se recomienda para un cliente premium según los documentos v2.

Estado: `completed` | confianza: `0.75`

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
        "query": "receta de cocina vegana recomendada para cliente premium v2",
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

Incidencias detectadas:
- status esperado 'insufficient_context', recibido 'completed'

Veredicto: `FAIL`
