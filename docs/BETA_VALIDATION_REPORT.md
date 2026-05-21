# Informe vivo de beta testing evaluador

Fecha de ejecucion: 2026-05-21

## Alcance

Este informe registra una pasada de validacion beta desde el punto de vista de un usuario final evaluador. Las respuestas visibles se han capturado con `chainlit_app.formatting.format_query_response`, la misma funcion que usa Chainlit para mostrar la respuesta final al usuario.

La ejecucion usa proveedores externos configurados en `.env` para LLM y embeddings, de acuerdo con la regla de validacion beta documentada en `docs/MANUAL_VALIDATION.md`. No se documentan claves, tokens ni secretos.

## Resumen ejecutivo

- Resultado global: PASS=13, PARTIAL=0, FAIL=0, BLOCKER=0.
- Suite automatizada previa: `124 passed, 2 warnings`.
- LLM provider: `gemini`; modelo Gemini: `gemini-2.5-flash`.
- Embedding provider: `gemini`; modelo embeddings Gemini: `gemini-embedding-001`.
- Chroma mode: `persistent`; coleccion aislada: `beta_validation_20260521_hardened_final_122123`.
- API de produccion mock validada en proceso con seed `data/production_seed.json`.
- Gap de entrega vigente: Docker Compose sigue pendiente hasta P10.

Lectura critica: la bateria beta queda superada; mantener estos casos como regresion antes de la demo final.

## Preparacion documental

- `contrato_marco_logistica_2026.pdf`: indexado con 2 chunks. Fallbacks: sin fallbacks.
- `anexo_penalizaciones_sla.pdf`: indexado con 2 chunks. Fallbacks: sin fallbacks.
- `procedimiento_produccion_bloqueos.pdf`: indexado con 2 chunks. Fallbacks: sin fallbacks.
- `politica_calidad_entregas.pdf`: indexado con 1 chunks. Fallbacks: sin fallbacks.
- `condiciones_comerciales_northwind.pdf`: indexado con 2 chunks. Fallbacks: sin fallbacks.

Listado visible de documentos:

```markdown
**Espacio documental**
- `condiciones_comerciales_northwind.pdf` (2 chunks)
- `contrato_marco_logistica_2026.pdf` (2 chunks)
- `politica_calidad_entregas.pdf` (1 chunks)
- `procedimiento_produccion_bloqueos.pdf` (2 chunks)
- `anexo_penalizaciones_sla.pdf` (2 chunks)
```

## Casos ejecutados

### BT-01 - PASS - ERP + produccion

Pregunta ejecutada: `Que pedidos pendientes tiene el cliente ALFKI y en que estado de produccion estan?`

Resultado esperado desde el evaluador: Debe listar pedidos pendientes de ALFKI y sus estados de produccion.

Respuesta exacta visible en Chainlit:

```markdown
Pedidos del cliente ALFKI: 10248: ERP pendiente, producción en curso; 10252: ERP pendiente, producción bloqueado (Falta de material).

Estado: `completed` | confianza: `0.90`

**Fuentes**
- ERP
- Produccion

**Pasos ejecutados**
1. Consulta ERP de pedidos pendientes
2. Consulta API de produccion para pedido 10248
3. Consulta API de produccion para pedido 10252

**Tool calls**
- `ERPTool` [success]: 2 pedidos pendientes encontrados
- `ProductionAPITool` [success]: Estado de produccion in_progress
- `ProductionAPITool` [success]: Estado de produccion blocked
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
      "action": null,
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
      "action": null,
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
      "action": null,
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

Observaciones criticas: Cumple la pregunta obligatoria de cliente X usando ALFKI como cliente seed.
Mejora recomendada: Sin mejora obligatoria antes de la demo.

### BT-02 - PASS - ERP + produccion

Pregunta ejecutada: `Que pedidos estan bloqueados y cual es el motivo?`

Resultado esperado desde el evaluador: Debe listar pedidos bloqueados y motivo, cruzando produccion con ERP.

Respuesta exacta visible en Chainlit:

```markdown
Pedidos bloqueados en producción: 10252 (ALFKI - Alfreds Futterkiste) está bloqueado por Falta de material; 10312 (BONAP - Bon app) está bloqueado por Falta de capacidad.

Estado: `completed` | confianza: `0.90`

**Fuentes**
- Produccion
- ERP

**Pasos ejecutados**
1. Consulta API de produccion por estado
2. Consulta ERP de cliente para pedido 10252
3. Consulta ERP de cliente para pedido 10312

**Tool calls**
- `ProductionAPITool` [success]: 2 pedidos de produccion encontrados con estado blocked
- `ERPTool` [success]: Cliente ALFKI encontrado
- `ERPTool` [success]: Cliente BONAP encontrado
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
      "action": null,
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
      "action": null,
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
      "action": null,
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

Observaciones criticas: Cruza correctamente produccion con ERP para explicar bloqueos.
Mejora recomendada: Sin mejora obligatoria antes de la demo.

### BT-03 - PASS - ERP + produccion

Pregunta ejecutada: `Que clientes tienen pedidos retrasados por problemas de produccion?`

Resultado esperado desde el evaluador: Debe identificar pedidos delayed y cliente ERP asociado.

Respuesta exacta visible en Chainlit:

```markdown
Pedidos retrasados en producción: 10301 (ANATR - Ana Trujillo Emparedados y helados) está retrasado debido a una avería en la línea de producción.

Estado: `completed` | confianza: `0.90`

**Fuentes**
- Produccion
- ERP

**Pasos ejecutados**
1. Consulta API de produccion por estado
2. Consulta ERP de cliente para pedido 10301

**Tool calls**
- `ProductionAPITool` [success]: 1 pedidos de produccion encontrados con estado delayed
- `ERPTool` [success]: Cliente ANATR encontrado
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
      "action": null,
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
      "action": null,
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

Observaciones criticas: Identifica el pedido retrasado, cliente ERP y motivo. La respuesta usa la forma acentuada `avería`, equivalente al criterio esperado.
Mejora recomendada: Sin mejora obligatoria antes de la demo.

### BT-04 - PASS - ERP + produccion

Pregunta ejecutada: `Dame un resumen del estado de los pedidos de este mes`

Resultado esperado desde el evaluador: Debe resumir pedidos de mayo de 2026 y su distribucion de estados.

Respuesta exacta visible en Chainlit:

```markdown
En 2026-05 hay 5 pedidos ERP. Estados de produccion: bloqueado: 2, en curso: 1, finalizado: 1, retrasado: 1.

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
- `ERPTool` [success]: 5 pedidos encontrados para el mes
- `ProductionAPITool` [success]: Estado de produccion in_progress
- `ProductionAPITool` [success]: Estado de produccion blocked
- `ProductionAPITool` [success]: Estado de produccion finished
- `ProductionAPITool` [success]: Estado de produccion delayed
- `ProductionAPITool` [success]: Estado de produccion blocked
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
      "action": null,
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
      "action": null,
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
      "action": null,
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
      "action": null,
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
      "action": null,
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
      "action": null,
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

Observaciones criticas: Resume el mes de demo y muestra distribucion de estados.
Mejora recomendada: Sin mejora obligatoria antes de la demo.

### BT-05 - PASS - RAG documentos

Pregunta ejecutada: `Que dice este documento sobre plazos de entrega?`

Resultado esperado desde el evaluador: Debe recuperar reglas documentales de plazos de entrega.

Respuesta exacta visible en Chainlit:

```markdown
Los pedidos standard deben entregarse en un plazo maximo de 5 dias laborables desde la liberacion de produccion. Los pedidos urgentes deben entregarse en un plazo maximo de 48 horas desde la liberacion. Este anexo complementa el contrato marco de logistica 2026 y define penalizaciones por incumplimiento de plazos de entrega cuando existe evidencia suficiente.

Estado: `completed` | confianza: `0.90`

**Fuentes**
- Documentos

**Citas documentales**
- `anexo_penalizaciones_sla.pdf`, pagina `1`, chunk `doc_d32d0989022b_p1_c2`, score `0.8274`
- `contrato_marco_logistica_2026.pdf`, pagina `1`, chunk `doc_839c1b74ca7a_p1_c1`, score `0.8209`
- `anexo_penalizaciones_sla.pdf`, pagina `1`, chunk `doc_d32d0989022b_p1_c1`, score `0.8132`
- `politica_calidad_entregas.pdf`, pagina `1`, chunk `doc_8742cee95db6_p1_c1`, score `0.8124`

**Pasos ejecutados**
1. Consulta RAG documental con chunks recuperados

**Tool calls**
- `DocumentRAGTool` [success]: 4 chunks recuperados de anexo_penalizaciones_sla.pdf, contrato_marco_logistica_2026.pdf, politica_calidad_entregas.pdf
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
      "action": null,
      "status": "success",
      "source": "Documentos",
      "args": {
        "query": "plazos de entrega",
        "top_k": 5,
        "min_score": 0.2,
        "filename": null
      },
      "output_summary": "4 chunks recuperados de anexo_penalizaciones_sla.pdf, contrato_marco_logistica_2026.pdf, politica_calidad_entregas.pdf",
      "error": null
    }
  ],
  "fallbacks": [],
  "data": {
    "rag": {
      "status": "completed",
      "chunks_count": 4,
      "documents": [
        "anexo_penalizaciones_sla.pdf",
        "contrato_marco_logistica_2026.pdf",
        "politica_calidad_entregas.pdf"
      ],
      "citations": [
        {
          "filename": "anexo_penalizaciones_sla.pdf",
          "page": 1,
          "chunk_id": "doc_d32d0989022b_p1_c2",
          "score": 0.8274
        },
        {
          "filename": "contrato_marco_logistica_2026.pdf",
          "page": 1,
          "chunk_id": "doc_839c1b74ca7a_p1_c1",
          "score": 0.8209
        },
        {
          "filename": "anexo_penalizaciones_sla.pdf",
          "page": 1,
          "chunk_id": "doc_d32d0989022b_p1_c1",
          "score": 0.8132
        },
        {
          "filename": "politica_calidad_entregas.pdf",
          "page": 1,
          "chunk_id": "doc_8742cee95db6_p1_c1",
          "score": 0.8124
        }
      ]
    }
  },
  "failure_reason": null
}
```

Veredicto: `PASS`

Observaciones criticas: Recupera evidencia documental y muestra citas visibles.
Mejora recomendada: Sin mejora obligatoria antes de la demo.

### BT-06 - PASS - RAG documentos

Pregunta ejecutada: `Resume los puntos clave del contrato`

Resultado esperado desde el evaluador: Debe resumir contrato con citas documentales.

Respuesta exacta visible en Chainlit:

```markdown
El contrato marco de logística 2026 regula la preparación, expedición y entrega de pedidos comerciales para clientes ERP durante el año 2026. Establece plazos de entrega de hasta 5 días laborables para pedidos estándar y 48 horas para urgentes desde la liberación de producción. El operador logístico debe coordinar con producción y el informe mensual debe detallar pedidos en curso, bloqueados, retrasados y finalizados. Se aplican penalizaciones por retrasos imputables al operador, pero no cuando el retraso se debe a bloqueo de producción, falta de material o capacidad, avería de línea o cambios de prioridad aprobados por dirección comercial.

Estado: `completed` | confianza: `0.90`

**Fuentes**
- Documentos

**Citas documentales**
- `contrato_marco_logistica_2026.pdf`, pagina `1`, chunk `doc_839c1b74ca7a_p1_c1`, score `0.7862`
- `anexo_penalizaciones_sla.pdf`, pagina `1`, chunk `doc_d32d0989022b_p1_c1`, score `0.7559`

**Pasos ejecutados**
1. Consulta RAG documental con chunks recuperados

**Tool calls**
- `DocumentRAGTool` [success]: 2 chunks recuperados de anexo_penalizaciones_sla.pdf, contrato_marco_logistica_2026.pdf
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
      "action": null,
      "status": "success",
      "source": "Documentos",
      "args": {
        "query": "Resume los puntos clave del contrato",
        "top_k": 5,
        "min_score": 0.2,
        "filename": null
      },
      "output_summary": "2 chunks recuperados de anexo_penalizaciones_sla.pdf, contrato_marco_logistica_2026.pdf",
      "error": null
    }
  ],
  "fallbacks": [],
  "data": {
    "rag": {
      "status": "completed",
      "chunks_count": 2,
      "documents": [
        "anexo_penalizaciones_sla.pdf",
        "contrato_marco_logistica_2026.pdf"
      ],
      "citations": [
        {
          "filename": "contrato_marco_logistica_2026.pdf",
          "page": 1,
          "chunk_id": "doc_839c1b74ca7a_p1_c1",
          "score": 0.7862
        },
        {
          "filename": "anexo_penalizaciones_sla.pdf",
          "page": 1,
          "chunk_id": "doc_d32d0989022b_p1_c1",
          "score": 0.7559
        }
      ]
    }
  },
  "failure_reason": null
}
```

Veredicto: `PASS`

Observaciones criticas: Devuelve resumen con citas documentales.
Mejora recomendada: Sin mejora obligatoria antes de la demo.

### BT-07 - PASS - RAG documentos

Pregunta ejecutada: `Hay alguna penalizacion por retrasos?`

Resultado esperado desde el evaluador: Debe responder sobre penalizaciones usando anexo SLA o contrato.

Respuesta exacta visible en Chainlit:

```markdown
Sí, existen penalizaciones por retrasos. Para pedidos estándar, se aplica un 2% si el retraso supera los 2 días laborables, y un 5% si excede los 5 días. Los pedidos urgentes tienen una penalización del 3% desde el primer día de retraso imputable. No se aplican penalizaciones por causas como bloqueo de producción, falta de material o capacidad, averías de línea, cambios de prioridad aprobados por dirección comercial, fuerza mayor o datos ERP incompletos.

Estado: `completed` | confianza: `0.90`

**Fuentes**
- Documentos

**Citas documentales**
- `anexo_penalizaciones_sla.pdf`, pagina `1`, chunk `doc_d32d0989022b_p1_c1`, score `0.8240`
- `anexo_penalizaciones_sla.pdf`, pagina `1`, chunk `doc_d32d0989022b_p1_c2`, score `0.8133`
- `contrato_marco_logistica_2026.pdf`, pagina `1`, chunk `doc_839c1b74ca7a_p1_c2`, score `0.7671`
- `procedimiento_produccion_bloqueos.pdf`, pagina `1`, chunk `doc_bc583553c43b_p1_c2`, score `0.7588`

**Pasos ejecutados**
1. Consulta RAG documental con chunks recuperados

**Tool calls**
- `DocumentRAGTool` [success]: 4 chunks recuperados de anexo_penalizaciones_sla.pdf, contrato_marco_logistica_2026.pdf, procedimiento_produccion_bloqueos.pdf
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
      "action": null,
      "status": "success",
      "source": "Documentos",
      "args": {
        "query": "Hay alguna penalizacion por retrasos?",
        "top_k": 5,
        "min_score": 0.2,
        "filename": null
      },
      "output_summary": "4 chunks recuperados de anexo_penalizaciones_sla.pdf, contrato_marco_logistica_2026.pdf, procedimiento_produccion_bloqueos.pdf",
      "error": null
    }
  ],
  "fallbacks": [],
  "data": {
    "rag": {
      "status": "completed",
      "chunks_count": 4,
      "documents": [
        "anexo_penalizaciones_sla.pdf",
        "contrato_marco_logistica_2026.pdf",
        "procedimiento_produccion_bloqueos.pdf"
      ],
      "citations": [
        {
          "filename": "anexo_penalizaciones_sla.pdf",
          "page": 1,
          "chunk_id": "doc_d32d0989022b_p1_c1",
          "score": 0.824
        },
        {
          "filename": "anexo_penalizaciones_sla.pdf",
          "page": 1,
          "chunk_id": "doc_d32d0989022b_p1_c2",
          "score": 0.8133
        },
        {
          "filename": "contrato_marco_logistica_2026.pdf",
          "page": 1,
          "chunk_id": "doc_839c1b74ca7a_p1_c2",
          "score": 0.7671
        },
        {
          "filename": "procedimiento_produccion_bloqueos.pdf",
          "page": 1,
          "chunk_id": "doc_bc583553c43b_p1_c2",
          "score": 0.7588
        }
      ]
    }
  },
  "failure_reason": null
}
```

Veredicto: `PASS`

Observaciones criticas: Recupera el anexo de penalizaciones y responde con evidencia. La respuesta expresa `2 por ciento` como `2%`, equivalente para usuario final.
Mejora recomendada: Sin mejora obligatoria antes de la demo.

### BT-08 - PASS - Mixta ERP + produccion + RAG

Pregunta ejecutada: `en funcion de los pedidos y su estado dime que penalizaciones vamos a tener en cada uno`

Resultado esperado desde el evaluador: Debe combinar pedidos ERP, estado de produccion y reglas documentales.

Respuesta exacta visible en Chainlit:

```markdown
Penalizaciones estimadas por pedido: 10248 (Alfreds Futterkiste): en curso; sin penalizacion aplicable con la evidencia actual; 10252 (Alfreds Futterkiste): bloqueado (Falta de material); sin penalizacion aplicable segun la evidencia actual por exclusion documental; 10255 (Alfreds Futterkiste): finalizado; sin penalizacion aplicable porque consta enviado antes del plazo requerido; 10301 (Ana Trujillo Emparedados y helados): retrasado (Averia en linea de produccion); sin penalizacion aplicable segun la evidencia actual por exclusion documental; 10312 (Bon app): bloqueado (Falta de capacidad); sin penalizacion aplicable segun la evidencia actual por exclusion documental.

Estado: `completed` | confianza: `0.90`

**Fuentes**
- ERP
- Produccion
- Documentos

**Citas documentales**
- `procedimiento_produccion_bloqueos.pdf`, pagina `1`, chunk `doc_bc583553c43b_p1_c1`, score `0.8412`
- `procedimiento_produccion_bloqueos.pdf`, pagina `1`, chunk `doc_bc583553c43b_p1_c2`, score `0.8209`
- `anexo_penalizaciones_sla.pdf`, pagina `1`, chunk `doc_d32d0989022b_p1_c2`, score `0.8154`
- `contrato_marco_logistica_2026.pdf`, pagina `1`, chunk `doc_839c1b74ca7a_p1_c2`, score `0.8063`
- `anexo_penalizaciones_sla.pdf`, pagina `1`, chunk `doc_d32d0989022b_p1_c1`, score `0.8017`

**Pasos ejecutados**
1. Consulta ERP de pedidos por mes
2. Consulta API de produccion para pedido 10248
3. Consulta API de produccion para pedido 10252
4. Consulta API de produccion para pedido 10255
5. Consulta API de produccion para pedido 10301
6. Consulta API de produccion para pedido 10312
7. Consulta RAG documental con chunks recuperados

**Tool calls**
- `ERPTool` [success]: 5 pedidos encontrados para el mes
- `ProductionAPITool` [success]: Estado de produccion in_progress
- `ProductionAPITool` [success]: Estado de produccion blocked
- `ProductionAPITool` [success]: Estado de produccion finished
- `ProductionAPITool` [success]: Estado de produccion delayed
- `ProductionAPITool` [success]: Estado de produccion blocked
- `DocumentRAGTool` [success]: 5 chunks recuperados de anexo_penalizaciones_sla.pdf, contrato_marco_logistica_2026.pdf, procedimiento_produccion_bloqueos.pdf
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
      "action": null,
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
      "action": null,
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
      "action": null,
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
      "action": null,
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
      "action": null,
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
      "action": null,
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
      "action": null,
      "status": "success",
      "source": "Documentos",
      "args": {
        "query": "penalizaciones por retrasos no aplicacion bloqueo produccion falta material falta capacidad averia linea",
        "top_k": 5,
        "min_score": 0.2,
        "filename": null
      },
      "output_summary": "5 chunks recuperados de anexo_penalizaciones_sla.pdf, contrato_marco_logistica_2026.pdf, procedimiento_produccion_bloqueos.pdf",
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
        "anexo_penalizaciones_sla.pdf",
        "contrato_marco_logistica_2026.pdf",
        "procedimiento_produccion_bloqueos.pdf"
      ],
      "citations": [
        {
          "filename": "procedimiento_produccion_bloqueos.pdf",
          "page": 1,
          "chunk_id": "doc_bc583553c43b_p1_c1",
          "score": 0.8412
        },
        {
          "filename": "procedimiento_produccion_bloqueos.pdf",
          "page": 1,
          "chunk_id": "doc_bc583553c43b_p1_c2",
          "score": 0.8209
        },
        {
          "filename": "anexo_penalizaciones_sla.pdf",
          "page": 1,
          "chunk_id": "doc_d32d0989022b_p1_c2",
          "score": 0.8154
        },
        {
          "filename": "contrato_marco_logistica_2026.pdf",
          "page": 1,
          "chunk_id": "doc_839c1b74ca7a_p1_c2",
          "score": 0.8063
        },
        {
          "filename": "anexo_penalizaciones_sla.pdf",
          "page": 1,
          "chunk_id": "doc_d32d0989022b_p1_c1",
          "score": 0.8017
        }
      ]
    }
  },
  "failure_reason": null
}
```

Veredicto: `PASS`

Observaciones criticas: Integra las tres fuentes en una respuesta por pedido.
Mejora recomendada: Sin mejora obligatoria antes de la demo.

### BT-09A - PASS - Memoria conversacional

Pregunta ejecutada: `Que pedidos pendientes tiene el cliente ALFKI?`

Resultado esperado desde el evaluador: Debe crear contexto de pedidos pendientes ALFKI.

Respuesta exacta visible en Chainlit:

```markdown
El cliente ALFKI tiene 2 pedidos pendientes: 10248, 10252.

Estado: `completed` | confianza: `0.90`

**Fuentes**
- ERP

**Pasos ejecutados**
1. Consulta ERP de pedidos pendientes

**Tool calls**
- `ERPTool` [success]: 2 pedidos pendientes encontrados
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
      "action": null,
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

Veredicto: `PASS`

Observaciones criticas: Crea contexto de pedidos pendientes para follow-ups.
Mejora recomendada: Sin mejora obligatoria antes de la demo.

### BT-09B - PASS - Memoria conversacional

Pregunta ejecutada: `Y cuales de esos pedidos estan bloqueados?`

Resultado esperado desde el evaluador: Debe resolver `esos` con memoria y devolver solo pedidos bloqueados del subconjunto.

Respuesta exacta visible en Chainlit:

```markdown
Pedidos bloqueados en produccion: 10252 (ALFKI - Alfreds Futterkiste): bloqueado, Falta de material.

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
- `MemoryTool` [success]: Memoria conversacional: 1 interacciones recuperadas
- `ProductionAPITool.get_status_for_order_ids` [success]: 1 pedidos de produccion encontrados por ids con estado blocked
- `ERPTool` [success]: Cliente ALFKI encontrado
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
      "action": null,
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
      "action": null,
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

Veredicto: `PASS`

Observaciones criticas: Resuelve la referencia, consulta produccion por IDs y devuelve solo el pedido bloqueado.
Mejora recomendada: Sin mejora obligatoria antes de la demo.

### BT-09C - PASS - Memoria conversacional

Pregunta ejecutada: `Cual es el impacto economico de esos?`

Resultado esperado desde el evaluador: Debe calcular impacto economico del subconjunto referenciado desde ERP.

Respuesta exacta visible en Chainlit:

```markdown
El impacto económico del pedido 10252 es de 1863.00.

Estado: `completed` | confianza: `0.90`

**Fuentes**
- Memoria
- ERP

**Pasos ejecutados**
1. Consulta memoria conversacional
2. Consulta ERP de importe para pedido 10252

**Tool calls**
- `MemoryTool` [success]: Memoria conversacional: 2 interacciones recuperadas
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
      "action": null,
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

Observaciones criticas: Calcula el impacto economico desde ERP para el subconjunto referenciado.
Mejora recomendada: Sin mejora obligatoria antes de la demo.

### BT-10 - PASS - Guardrail RAG

Pregunta ejecutada: `Segun el PDF, que receta de cocina vegana recomienda?`

Resultado esperado desde el evaluador: Debe rechazar por contexto documental insuficiente y no inventar.

Respuesta exacta visible en Chainlit:

```markdown
No hay contexto documental suficiente para responder sin inventar.

Estado: `insufficient_context` | confianza: `0.45`

**Fuentes**
- Documentos

**Pasos ejecutados**
1. Consulta RAG documental con chunks recuperados

**Tool calls**
- `DocumentRAGTool` [success]: 0 chunks relevantes recuperados

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
      "action": null,
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

Observaciones criticas: Devuelve insufficient_context y no inventa.
Mejora recomendada: Sin mejora obligatoria antes de la demo.

### BT-11 - PASS - Memoria aislada

Pregunta ejecutada: `Y en que estado estan?`

Resultado esperado desde el evaluador: Debe aislar conversaciones por conversation_id y pedir contexto previo.

Respuesta exacta visible en Chainlit:

```markdown
La pregunta necesita contexto conversacional previo; en esta conversacion no hay pedidos referenciados, asi que queda fuera del alcance actual. Indica el cliente o los pedidos concretos.

Estado: `unsupported`

**Motivo**
La pregunta queda fuera del alcance de la POC actual.
```

Evidencia tecnica resumida:

```json
{
  "status": "unsupported",
  "sources": [],
  "tool_calls": [],
  "fallbacks": [],
  "data": null,
  "failure_reason": "La pregunta queda fuera del alcance de la POC actual."
}
```

Veredicto: `PASS`

Observaciones criticas: Aisla la conversacion nueva y no reutiliza pedidos de otra conversacion.
Mejora recomendada: Sin mejora obligatoria antes de la demo.

## Riesgos y proximas mejoras

- Mantener la secuencia de memoria avanzada como regresion fija: pedidos pendientes -> bloqueados -> impacto economico.
- Mantener la pregunta mixta de penalizaciones como smoke test principal porque prueba ERP, produccion, RAG, citas y trazabilidad en un solo flujo.
- Completar P10 Docker Compose para cerrar el entregable tecnico solicitado en la prueba.
