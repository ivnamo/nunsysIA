# Validacion de entrega Docker/API

Fecha de ejecucion: 2026-05-23 22:54:14
Endpoint validado: `http://localhost:8000/api/query`
Modo agentic: `deepagent`

Resultado global: PASS=18, FAIL=0, casos=18.

## Servicios

| Servicio | Estado |
| --- | --- |
| backend | OK HTTP 200 |
| production-api | OK HTTP 200 |
| chainlit | OK HTTP 200 |
| chromadb | OK HTTP 200 |

## Reset RAG

| HTTP | Estado | Chunks eliminados | Fallbacks | Detail |
| ---: | --- | ---: | --- | --- |
| 200 | cleared | 38 | [] |  |

## PDFs indexados

| PDF | HTTP | Estado | Chunks | Fallbacks |
| --- | ---: | --- | ---: | --- |
| v2_contrato_marco_logistica_2026.pdf | 201 | indexed | 8 | [] |
| v2_anexo_penalizaciones_sla.pdf | 201 | indexed | 8 | [] |
| v2_procedimiento_produccion_bloqueos.pdf | 201 | indexed | 8 | [] |
| v2_politica_calidad_entregas.pdf | 201 | indexed | 6 | [] |
| v2_condiciones_comerciales_northwind.pdf | 201 | indexed | 8 | [] |

## Tabla resumen

| ID | Capa | Fuente | Veredicto | HTTP/status | Fuentes | Tools |
| --- | --- | --- | --- | --- | --- | --- |
| F-ERP-01 | OBLIGATORIO | PDF 2.1 | PASS | 200/completed | ERP, Produccion | ERPTool, ProductionAPITool |
| F-ERP-02 | OBLIGATORIO | PDF 2.1 | PASS | 200/completed | Produccion, ERP | ProductionAPITool, ERPQueryTool, ERPTool |
| F-ERP-03 | OBLIGATORIO | PDF 2.1 | PASS | 200/completed | Produccion, ERP | ProductionAPITool, ERPTool |
| F-ERP-04 | OBLIGATORIO | PDF 2.1 | PASS | 200/completed | ERP, Produccion | ERPTool, ProductionAPITool |
| F-RAG-01 | OBLIGATORIO | PDF 2.2 | PASS | 200/completed | Documentos | DocumentRAGTool |
| F-RAG-02 | OBLIGATORIO | PDF 2.2 | PASS | 200/completed | Documentos | DocumentRAGTool |
| F-RAG-03 | OBLIGATORIO | PDF 2.2 | PASS | 200/completed | Documentos, Produccion | DocumentRAGTool, ProductionQueryTool |
| BT-08 | ADICIONAL | Beta validation | PASS | 200/completed | ERP, Produccion, Documentos | ERPTool, ProductionAPITool, DocumentRAGTool |
| BT-09 | ADICIONAL | Beta validation | PASS | 200/completed<br>200/completed<br>200/completed | ERP, Memoria, Produccion | ERPTool, MemoryTool, ProductionAPITool |
| BT-10 | ADICIONAL | Beta validation | PASS | 200/insufficient_context | Documentos | DocumentRAGTool |
| BT-11 | ADICIONAL | Beta validation | PASS | 200/needs_clarification | - | - |
| BT-V2-01 | ADICIONAL | Beta validation | PASS | 200/completed | Documentos | DocumentRAGTool |
| BT-V2-02 | ADICIONAL | Beta validation | PASS | 200/completed | Documentos | DocumentRAGTool |
| BT-V2-03 | ADICIONAL | Beta validation | PASS | 200/completed | Documentos | DocumentRAGTool |
| BT-V2-04 | ADICIONAL | Beta validation | PASS | 200/completed | Documentos | DocumentRAGTool |
| BT-V2-05 | ADICIONAL | Beta validation | PASS | 200/completed | Documentos | DocumentRAGTool |
| BT-V2-06 | ADICIONAL | Beta validation | PASS | 200/completed | Documentos | DocumentRAGTool |
| BT-V2-07 | ADICIONAL | Beta validation | PASS | 200/insufficient_context | Documentos | DocumentRAGTool |

## Respuestas

### F-ERP-01 - PASS - Pedidos pendientes de cliente y estado de produccion

Pregunta 1: `Que pedidos pendientes tiene el cliente ALFKI y en que estado de produccion estan?`

HTTP: `200` | status: `completed`
Fuentes: `["ERP", "Produccion"]`
Tools: `["ERPTool", "ProductionAPITool"]`
Fallbacks: `[]`

Respuesta:

```markdown
El cliente ALFKI tiene los siguientes pedidos pendientes:

*   **Pedido 10248:** Importe: 440.00, Fecha de pedido: 2026-05-02, Estado ERP: pendiente, Estado de producción: en progreso, Fecha estimada de finalización: 2026-05-22.
*   **Pedido 10252:** Importe: 1863.00, Fecha de pedido: 2026-05-07, Estado ERP: pendiente, Estado de producción: bloqueado (Motivo de bloqueo: Falta de material), Fecha estimada de finalización: 2026-05-30.

Fuentes consultadas:
*   ERP/Northwind
*   API de producción

Pasos ejecutados:
1.  Se consultó la herramienta compuesta `get_customer_pending_orders_with_production` con el `customer_id` "ALFKI" para obtener los pedidos pendientes y su estado de producción.
```

Pasos:

- Consulta ERP de pedidos pendientes
- Consulta API de produccion para pedidos referenciados

### F-ERP-02 - PASS - Pedidos bloqueados y motivo

Pregunta 1: `Que pedidos estan bloqueados y cual es el motivo?`

HTTP: `200` | status: `completed`
Fuentes: `["Produccion", "ERP"]`
Tools: `["ProductionAPITool", "ERPQueryTool", "ERPTool", "ERPTool"]`
Fallbacks: `[]`

Respuesta:

```markdown
Los siguientes pedidos se encuentran bloqueados:

*   **Pedido 10252:**
    *   Cliente: Alfreds Futterkiste
    *   Importe: 1863.00
    *   Estado ERP: pending
    *   Estado Producción: blocked
    *   Motivo del bloqueo: Falta de material
*   **Pedido 10312:**
    *   Cliente: Bon app
    *   Importe: 1210.00
    *   Estado ERP: pending
    *   Estado Producción: blocked
    *   Motivo del bloqueo: Falta de capacidad
```

Pasos:

- Consulta API de produccion por estado
- Consulta ERP mediante filtros seguros
- Consulta ERP de cliente para pedido 10252
- Consulta ERP de cliente para pedido 10312

### F-ERP-03 - PASS - Clientes con pedidos retrasados por produccion

Pregunta 1: `Que clientes tienen pedidos retrasados por problemas de produccion?`

HTTP: `200` | status: `completed`
Fuentes: `["Produccion", "ERP"]`
Tools: `["ProductionAPITool", "ERPTool"]`
Fallbacks: `[]`

Respuesta:

```markdown
Estos son los estados de produccion de los pedidos referenciados:

| Pedido | Cliente | Estado | Motivo |
| --- | --- | --- | --- |
| 10301 | ANATR - Ana Trujillo Emparedados y helados | retrasado | Averia en linea de produccion |
```

Pasos:

- Consulta API de produccion por estado
- Consulta ERP de cliente para pedido 10301

### F-ERP-04 - PASS - Resumen mensual de pedidos

Pregunta 1: `Dame un resumen del estado de los pedidos de este mes`

HTTP: `200` | status: `completed`
Fuentes: `["ERP", "Produccion"]`
Tools: `["ERPTool", "ProductionAPITool"]`
Fallbacks: `[]`

Respuesta:

```markdown
En mayo de 2026 hay 5 pedidos ERP. Distribucion por estado de produccion: bloqueado: 2, en curso: 1, finalizado: 1, retrasado: 1.

| Pedido | Estado ERP | Estado produccion |
| --- | --- | --- |
| 10248 | pendiente | en curso |
| 10252 | pendiente | bloqueado |
| 10255 | enviado | finalizado |
| 10301 | pendiente | retrasado |
| 10312 | pendiente | bloqueado |

Periodo auditado: 2026-05.
```

Pasos:

- Consulta ERP de pedidos por mes
- Consulta API de produccion para pedidos referenciados

### F-RAG-01 - PASS - Plazos de entrega en documento

Pregunta 1: `Que dice este documento sobre plazos de entrega?`

HTTP: `200` | status: `completed`
Fuentes: `["Documentos"]`
Tools: `["DocumentRAGTool"]`
Fallbacks: `[]`

Respuesta:

```markdown
Según el documento, los plazos de entrega son los siguientes: los pedidos estándar deben entregarse en un plazo máximo de 5 días laborables desde la liberación de producción, y los pedidos urgentes en un plazo máximo de 48 horas. Las entregas parciales solo se consideran cumplimiento si comercial las aprueba y el cliente acepta la documentación.
```

Pasos:

- Consulta RAG documental para localizar evidencia verificable sobre la pregunta
- Selecciona 1 chunk(s) relevante(s) de v2_contrato_marco_logistica_2026.pdf como base de evidencia
- Sintetiza la respuesta final usando solo el contexto recuperado y deja las citas documentales auditables en data.rag.citations

Evidencia RAG:

- documentos: `["v2_contrato_marco_logistica_2026.pdf"]`
- chunks_count: `1`

### F-RAG-02 - PASS - Resumen de puntos clave del contrato

Pregunta 1: `Resume los puntos clave del contrato`

HTTP: `200` | status: `completed`
Fuentes: `["Documentos"]`
Tools: `["DocumentRAGTool"]`
Fallbacks: `[]`

Respuesta:

```markdown
El contrato marco de logística para 2026 regula la preparación, expedición, entrega y cierre documental de pedidos comerciales. Define un 'pedido bloqueado' como una orden detenida por producción debido a falta de material, capacidad, incidencia de calidad o aprobación pendiente. Para auditorías, se requiere evidencia mínima que incluya order_id, customer_id, cliente, fecha prometida, fecha real, transportista, estado ERP, estado de producción y causa de desviación.

**Fuentes:**
- v2_contrato_marco_logistica_2026.pdf

**Pasos Ejecutados:**
1. Se ha utilizado la herramienta `answer_document_question_with_citations` para consultar el documento y obtener un resumen de los puntos clave.
2. La respuesta ha sido revisada y aprobada por el `answer_auditor`.
```

Pasos:

- Consulta RAG documental para localizar evidencia verificable sobre la pregunta
- Selecciona 3 chunk(s) relevante(s) de v2_contrato_marco_logistica_2026.pdf como base de evidencia
- Sintetiza la respuesta final usando solo el contexto recuperado y deja las citas documentales auditables en data.rag.citations

Evidencia RAG:

- documentos: `["v2_contrato_marco_logistica_2026.pdf"]`
- chunks_count: `3`

### F-RAG-03 - PASS - Penalizaciones por retrasos

Pregunta 1: `Hay alguna penalizacion por retrasos?`

HTTP: `200` | status: `completed`
Fuentes: `["Documentos", "Produccion"]`
Tools: `["DocumentRAGTool", "ProductionQueryTool"]`
Fallbacks: `[]`

Respuesta:

```markdown
Sí, existen penalizaciones por retrasos en la entrega de pedidos. La penalización se aplica si hay un incumplimiento de plazo, la causa es imputable al operador logístico y se dispone de evidencia completa del ERP, producción y prueba de entrega. Se ha identificado un pedido con retraso en producción (Order ID: 10301) debido a una "Avería en línea de producción".

Para pedidos estándar, la penalización es del 2% si el retraso imputable es de más de 2 días laborables, y sube al 5% si supera los 5 días laborables. Para pedidos urgentes, la penalización es del 3% desde el primer día de retraso imputable.
```

Pasos:

- Consulta RAG documental para localizar evidencia verificable sobre la pregunta
- Selecciona 3 chunk(s) relevante(s) de v2_anexo_penalizaciones_sla.pdf como base de evidencia
- Sintetiza la respuesta final usando solo el contexto recuperado y deja las citas documentales auditables en data.rag.citations
- Consulta Produccion mediante filtros seguros

Evidencia RAG:

- documentos: `["v2_anexo_penalizaciones_sla.pdf"]`
- chunks_count: `3`

### BT-08 - PASS - Mixta: penalizaciones por pedido

Pregunta 1: `en funcion de los pedidos y su estado dime que penalizaciones vamos a tener en cada uno`

HTTP: `200` | status: `completed`
Fuentes: `["ERP", "Produccion", "Documentos"]`
Tools: `["ERPTool", "ProductionAPITool", "DocumentRAGTool"]`
Fallbacks: `[]`

Respuesta:

```markdown
No se han identificado penalizaciones aplicables a los pedidos actuales, basándonos en la información de ERP, el estado de producción y las cláusulas de penalización de los documentos.

**Detalle por pedido:**

*   **Pedido 10248 (Alfreds Futterkiste):** Aunque el `estimated_finish_date` (2026-05-22) es 2 días posterior al `required_date` (2026-05-20), las cláusulas indican que la penalización del 2% se aplica a retrasos "más de 2 días laborables". Por lo tanto, este pedido no incurre en penalización.
*   **Pedido 10252 (Alfreds Futterkiste):** Está bloqueado por "Falta de material". La falta de material es una causa de exclusión de penalización.
*   **Pedido 10255 (Alfreds Futterkiste):** Fue entregado (`shipped_date`: 2026-05-15) antes de su `required_date` (2026-05-30). No hay retraso, por lo tanto, no hay penalización.
*   **Pedido 10301 (Ana Trujillo Emparedados y helados):** Está retrasado por "Averia en linea de produccion". Una avería de línea es una causa de exclusión de penalización.
*   **Pedido 10312 (Bon app):** Está bloqueado por "Falta de capacidad". La falta de capacidad es una causa de exclusión de penalización.
```

Pasos:

- Consulta ERP de pedidos por mes
- Consulta API de produccion para pedidos referenciados
- Consulta RAG documental para localizar evidencia verificable sobre la pregunta
- Selecciona 3 chunk(s) relevante(s) de v2_anexo_penalizaciones_sla.pdf, v2_contrato_marco_logistica_2026.pdf como base de evidencia
- Sintetiza la respuesta final usando solo el contexto recuperado y deja las citas documentales auditables en data.rag.citations

Evidencia RAG:

- documentos: `["v2_anexo_penalizaciones_sla.pdf", "v2_contrato_marco_logistica_2026.pdf"]`
- chunks_count: `3`

### BT-09 - PASS - Memoria conversacional

Pregunta 1: `Que pedidos pendientes tiene el cliente ALFKI?`

HTTP: `200` | status: `completed`
Fuentes: `["ERP"]`
Tools: `["ERPTool"]`
Fallbacks: `[]`

Respuesta:

```markdown
El cliente ALFKI tiene 2 pedidos pendientes:
- Pedido 10248, con un importe de 440.00, fecha de pedido 2026-05-02 y fecha requerida 2026-05-20.
- Pedido 10252, con un importe de 1863.00, fecha de pedido 2026-05-07 y fecha requerida 2026-05-25.
```

Pasos:

- Consulta ERP de pedidos pendientes

Pregunta 2: `Y cuales de esos pedidos estan bloqueados?`

HTTP: `200` | status: `completed`
Fuentes: `["Memoria", "Produccion", "ERP"]`
Tools: `["MemoryTool", "ProductionAPITool", "ERPTool"]`
Fallbacks: `[]`

Respuesta:

```markdown
Estos son los estados de produccion de los pedidos referenciados:

| Pedido | Cliente | Estado | Motivo |
| --- | --- | --- | --- |
| 10252 | ALFKI - Alfreds Futterkiste | bloqueado | Falta de material |
```

Pasos:

- Consulta memoria conversacional
- Consulta API de produccion para pedidos referenciados
- Consulta ERP de cliente para pedido 10252

Pregunta 3: `Cual es el impacto economico de esos?`

HTTP: `200` | status: `completed`
Fuentes: `["Memoria", "ERP"]`
Tools: `["MemoryTool", "ERPTool"]`
Fallbacks: `[]`

Respuesta:

```markdown
El impacto económico del pedido bloqueado (ID 10252) es de 1863.00.

**Fuentes:**
* Memoria conversacional
* ERP

**Razonamiento:**
1. Se consultó la memoria conversacional para identificar el pedido al que se refería la pregunta ("esos").
2. La memoria indicó que el pedido 10252, con un importe de 1863.00, estaba bloqueado.
3. Se determinó que el impacto económico se corresponde con el valor de dicho pedido.
```

Pasos:

- Consulta memoria conversacional
- Consulta ERP de importe para pedido 10252

### BT-10 - PASS - Guardrail RAG

Pregunta 1: `Segun el PDF, que receta de cocina vegana recomienda?`

HTTP: `200` | status: `insufficient_context`
Fuentes: `["Documentos"]`
Tools: `["DocumentRAGTool"]`
Fallbacks: `[]`

Respuesta:

```markdown
No he encontrado informacion en los documentos disponibles para responder a esa pregunta con fiabilidad.
```

Pasos:

- Consulta RAG documental para buscar evidencia; no se recuperan chunks relevantes suficientes
- Valida que no hay evidencia documental suficiente y evita completar con conocimiento del modelo

Evidencia RAG:

- documentos: `[]`
- chunks_count: `0`

### BT-11 - PASS - Memoria aislada

Pregunta 1: `Y en que estado estan?`

HTTP: `200` | status: `needs_clarification`
Fuentes: `[]`
Tools: `[]`
Fallbacks: `[]`

Respuesta:

```markdown
Necesito contexto previo o que me indiques el cliente, pedido o periodo concreto para saber a que te refieres.
```

### BT-V2-01 - PASS - V2: hitos y evidencias minimas

Pregunta 1: `Segun v2_contrato_marco_logistica_2026.pdf, que hitos obligatorios debe conservar cada expedicion?`

HTTP: `200` | status: `completed`
Fuentes: `["Documentos"]`
Tools: `["DocumentRAGTool"]`
Fallbacks: `[]`

Respuesta:

```markdown
Según el documento `v2_contrato_marco_logistica_2026.pdf`, cada expedición debe conservar cinco hitos obligatorios:
1.  **Liberación de producción**
2.  **Preparación de almacén**
3.  **Salida de muelle**
4.  **Entrega al transportista**
5.  **Confirmación de entrega**

Cada uno de estos hitos debe registrar la fecha, el usuario o sistema de origen, el estado anterior, el estado nuevo y una observación de negocio cuando el cambio afecte al cliente.

**Fuentes:**
*   v2_contrato_marco_logistica_2026.pdf

**Razonamiento:**
1.  Se utilizó la herramienta `answer_document_question_with_citations` para consultar el documento `v2_contrato_marco_logistica_2026.pdf` y extraer la información relevante sobre los hitos obligatorios.
2.  La respuesta obtenida fue auditada por el `answer_auditor` y aprobada.
```

Pasos:

- Consulta RAG documental para localizar evidencia verificable sobre la pregunta
- Selecciona 2 chunk(s) relevante(s) de v2_contrato_marco_logistica_2026.pdf como base de evidencia
- Sintetiza la respuesta final usando solo el contexto recuperado y deja las citas documentales auditables en data.rag.citations

Evidencia RAG:

- documentos: `["v2_contrato_marco_logistica_2026.pdf"]`
- chunks_count: `2`

### BT-V2-02 - PASS - V2: evidencia SLA

Pregunta 1: `Segun v2_anexo_penalizaciones_sla.pdf, que evidencia es obligatoria y que pasa si no se puede demostrar la causa del retraso?`

HTTP: `200` | status: `completed`
Fuentes: `["Documentos"]`
Tools: `["DocumentRAGTool"]`
Fallbacks: `[]`

Respuesta:

```markdown
Según el documento v2_anexo_penalizaciones_sla.pdf, la evidencia obligatoria para aplicar una penalización debe incluir el `order_id`, `customer_id`, el importe del pedido, la fecha prometida, la fecha real de entrega, la fecha de liberación, el transportista, la causa del retraso y la fuente responsable. Es crucial que el importe provenga de líneas ERP.

Si no se puede demostrar la causa del retraso, el sistema debe informar que no hay evidencia suficiente para asignar responsabilidad. En este caso, no se debe aplicar una penalización basándose únicamente en que la fecha real de entrega sea posterior a la fecha prometida.

**Fuentes:**
[1] v2_anexo_penalizaciones_sla.pdf, página 2, doc_b1a84a0b37b5_p2_c1
[2] v2_anexo_penalizaciones_sla.pdf, página 2, doc_b1a84a0b37b5_p2_c2

**Razonamiento:**
1. Se ha identificado que la pregunta se refiere a información contenida en el documento "v2_anexo_penalizaciones_sla.pdf".
2. Se ha utilizado el contexto documental recuperado para extraer la información sobre la evidencia obligatoria y las consecuencias de no poder demostrar la causa del retraso.
3. Se ha redactado una respuesta concisa y clara basada en la información extraída, citando las fuentes correspondientes.
```

Pasos:

- Consulta RAG documental para localizar evidencia verificable sobre la pregunta
- Selecciona 3 chunk(s) relevante(s) de v2_anexo_penalizaciones_sla.pdf como base de evidencia
- Sintetiza la respuesta final usando solo el contexto recuperado y deja las citas documentales auditables en data.rag.citations

Evidencia RAG:

- documentos: `["v2_anexo_penalizaciones_sla.pdf"]`
- chunks_count: `3`

### BT-V2-03 - PASS - V2: exclusiones y pausas SLA

Pregunta 1: `Segun v2_anexo_penalizaciones_sla.pdf, que exclusiones y pausas de SLA existen?`

HTTP: `200` | status: `completed`
Fuentes: `["Documentos"]`
Tools: `["DocumentRAGTool"]`
Fallbacks: `[]`

Respuesta:

```markdown
Según el documento v2_anexo_penalizaciones_sla.pdf, las exclusiones de penalizaciones se aplican cuando el retraso procede de bloqueo de producción, falta de material, falta de capacidad, avería de línea, retrabajo por calidad, espera de validación técnica, fuerza mayor, error de dirección aportado por el cliente o cambio de prioridad aprobado por dirección comercial. Las pausas del contador de SLA ocurren desde la fecha de bloqueo hasta la fecha de desbloqueo registrada por producción. En exportación, también puede pausarse por documentación aduanera o sanitaria incompleta, siempre que el expediente contenga evento, responsable y fecha de resolución. Los casos no penalizables incluyen un pedido urgente si fue marcado urgente después de la liberación y logística ya había planificado ruta estándar, y una entrega rechazada por el cliente por ausencia en domicilio si había cita confirmada.
```

Pasos:

- Consulta RAG documental para localizar evidencia verificable sobre la pregunta
- Selecciona 2 chunk(s) relevante(s) de v2_anexo_penalizaciones_sla.pdf como base de evidencia
- Sintetiza la respuesta final usando solo el contexto recuperado y deja las citas documentales auditables en data.rag.citations

Evidencia RAG:

- documentos: `["v2_anexo_penalizaciones_sla.pdf"]`
- chunks_count: `2`

### BT-V2-04 - PASS - V2: bloqueos de produccion

Pregunta 1: `Segun v2_procedimiento_produccion_bloqueos.pdf, que motivos de bloqueo y campos obligatorios se registran?`

HTTP: `200` | status: `completed`
Fuentes: `["Documentos"]`
Tools: `["DocumentRAGTool"]`
Fallbacks: `[]`

Respuesta:

```markdown
Según el documento "v2_procedimiento_produccion_bloqueos.pdf", los motivos de bloqueo que se registran son: falta de material, falta de capacidad, incidencia de calidad, mantenimiento no planificado, aprobación técnica pendiente y discrepancia de receta o especificación. Los campos obligatorios para cada bloqueo son: order_id, línea de producción, motivo, responsable, fecha de inicio, fecha estimada de desbloqueo, impacto en cliente y comentario operativo.

**Fuentes:**
- v2_procedimiento_produccion_bloqueos.pdf [1]

**Pasos ejecutados:**
1. Se consultó el contexto documental proporcionado sobre "v2_procedimiento_produccion_bloqueos.pdf".
2. Se extrajeron los motivos de bloqueo y los campos obligatorios mencionados en la página 2 del documento.
3. Se auditó la respuesta con el subagente `answer_auditor`.
```

Pasos:

- Consulta RAG documental para localizar evidencia verificable sobre la pregunta
- Selecciona 2 chunk(s) relevante(s) de v2_procedimiento_produccion_bloqueos.pdf como base de evidencia
- Sintetiza la respuesta final usando solo el contexto recuperado y deja las citas documentales auditables en data.rag.citations

Evidencia RAG:

- documentos: `["v2_procedimiento_produccion_bloqueos.pdf"]`
- chunks_count: `2`

### BT-V2-05 - PASS - V2: calidad y entregas parciales

Pregunta 1: `Segun v2_politica_calidad_entregas.pdf, que ocurre con incidencias de calidad y entregas parciales?`

HTTP: `200` | status: `completed`
Fuentes: `["Documentos"]`
Tools: `["DocumentRAGTool"]`
Fallbacks: `[]`

Respuesta:

```markdown
Según el documento v2_politica_calidad_entregas.pdf, las incidencias de calidad bloquean el pedido hasta que Calidad registre una resolución, indicando si el lote se libera, sustituye, reprocesa o rechaza. Producción no puede desbloquear una retención de calidad sin la aprobación de Calidad. Las entregas parciales requieren aprobación comercial y validación de calidad para cada lote entregado. Si una parte queda retenida, el albarán debe explicar la parte enviada, la parte pendiente y el motivo de retención.
```

Pasos:

- Consulta RAG documental para localizar evidencia verificable sobre la pregunta
- Selecciona 3 chunk(s) relevante(s) de v2_politica_calidad_entregas.pdf como base de evidencia
- Sintetiza la respuesta final usando solo el contexto recuperado y deja las citas documentales auditables en data.rag.citations

Evidencia RAG:

- documentos: `["v2_politica_calidad_entregas.pdf"]`
- chunks_count: `3`

### BT-V2-06 - PASS - V2: impacto economico y trazabilidad

Pregunta 1: `Segun v2_condiciones_comerciales_northwind.pdf, como se calcula el impacto economico y que trazabilidad se exige?`

HTTP: `200` | status: `completed`
Fuentes: `["Documentos"]`
Tools: `["DocumentRAGTool"]`
Fallbacks: `[]`

Respuesta:

```markdown
Según el documento `v2_condiciones_comerciales_northwind.pdf`, no se calcula un impacto económico definitivo si falta alguno de los siguientes elementos: importe ERP, porcentaje contractual o causa documentada. Para calcular el impacto económico, la respuesta debe unir estos tres elementos cuando una penalización o retraso tenga dicho impacto.

**Fuentes:**
- v2_condiciones_comerciales_northwind.pdf

**Razonamiento:**
1. Se utilizó la herramienta `answer_document_question_with_citations` para buscar en el documento `v2_condiciones_comerciales_northwind.pdf` la información relacionada con el cálculo del impacto económico y la trazabilidad exigida.
2. Los resultados de la consulta indicaron que el impacto económico definitivo no se calcula si falta el importe ERP, el porcentaje contractual o la causa documentada.
3. Se confirmó que para calcular el impacto económico, se deben unir estos tres elementos en caso de penalización o retraso.
4. La respuesta fue auditada y aprobada por el `answer_auditor`.
```

Pasos:

- Consulta RAG documental para localizar evidencia verificable sobre la pregunta
- Selecciona 2 chunk(s) relevante(s) de v2_condiciones_comerciales_northwind.pdf como base de evidencia
- Sintetiza la respuesta final usando solo el contexto recuperado y deja las citas documentales auditables en data.rag.citations

Evidencia RAG:

- documentos: `["v2_condiciones_comerciales_northwind.pdf"]`
- chunks_count: `2`

### BT-V2-07 - PASS - V2: guardrail documental multipagina

Pregunta 1: `Segun los documentos v2, que receta de cocina vegana recomienda para un cliente premium?`

HTTP: `200` | status: `insufficient_context`
Fuentes: `["Documentos"]`
Tools: `["DocumentRAGTool"]`
Fallbacks: `[]`

Respuesta:

```markdown
No he encontrado informacion en los documentos disponibles para responder a esa pregunta con fiabilidad.
```

Pasos:

- Consulta RAG documental para buscar evidencia; no se recuperan chunks relevantes suficientes
- Valida que no hay evidencia documental suficiente y evita completar con conocimiento del modelo

Evidencia RAG:

- documentos: `[]`
- chunks_count: `0`

