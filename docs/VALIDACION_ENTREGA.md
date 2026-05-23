# Validacion de entrega Docker/API

Fecha de ejecucion: 2026-05-23 11:15:22
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
| F-ERP-02 | OBLIGATORIO | PDF 2.1 | PASS | 200/completed | Produccion, ERP | ProductionAPITool, ERPTool |
| F-ERP-03 | OBLIGATORIO | PDF 2.1 | PASS | 200/completed | Produccion, ERP | ProductionAPITool, ERPTool |
| F-ERP-04 | OBLIGATORIO | PDF 2.1 | PASS | 200/completed | ERP, Produccion | ERPTool, ProductionAPITool |
| F-RAG-01 | OBLIGATORIO | PDF 2.2 | PASS | 200/completed | Documentos | DocumentRAGTool |
| F-RAG-02 | OBLIGATORIO | PDF 2.2 | PASS | 200/completed | Documentos | DocumentRAGTool |
| F-RAG-03 | OBLIGATORIO | PDF 2.2 | PASS | 200/completed | Documentos | DocumentRAGTool |
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
El cliente ALFKI tiene 2 pedidos pendientes:

| Pedido | Estado ERP | Estado produccion | Observacion |
| --- | --- | --- | --- |
| 10248 | pendiente | en curso | sin bloqueo informado |
| 10252 | pendiente | bloqueado | Falta de material |
```

Pasos:

- Consulta ERP de pedidos pendientes
- Consulta API de produccion para pedidos referenciados

### F-ERP-02 - PASS - Pedidos bloqueados y motivo

Pregunta 1: `Que pedidos estan bloqueados y cual es el motivo?`

HTTP: `200` | status: `completed`
Fuentes: `["Produccion", "ERP"]`
Tools: `["ProductionAPITool", "ERPTool", "ERPTool"]`
Fallbacks: `[]`

Respuesta:

```markdown
Estos son los estados de produccion de los pedidos referenciados:

| Pedido | Cliente | Estado | Motivo |
| --- | --- | --- | --- |
| 10252 | ALFKI - Alfreds Futterkiste | bloqueado | Falta de material |
| 10312 | BONAP - Bon app | bloqueado | Falta de capacidad |
```

Pasos:

- Consulta API de produccion por estado
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
El documento establece que, para pedidos standard, el plazo maximo de entrega es de 5 dias laborables desde la liberacion de produccion. Tambien fija un plazo maximo de 48 horas para pedidos urgentes. Para aplicar una penalizacion, no basta con que haya retraso: debe existir incumplimiento de plazo, causa imputable al operador logistico y evidencia completa en ERP, produccion y prueba de entrega.
```

Pasos:

- Consulta RAG documental para localizar evidencia verificable sobre la pregunta
- Selecciona 3 chunk(s) relevante(s) de v2_contrato_marco_logistica_2026.pdf, v2_anexo_penalizaciones_sla.pdf como base de evidencia
- Sintetiza la respuesta final usando solo el contexto recuperado y deja las citas documentales auditables en data.rag.citations

Evidencia RAG:

- documentos: `["v2_anexo_penalizaciones_sla.pdf", "v2_contrato_marco_logistica_2026.pdf"]`
- chunks_count: `3`

### F-RAG-02 - PASS - Resumen de puntos clave del contrato

Pregunta 1: `Resume los puntos clave del contrato`

HTTP: `200` | status: `completed`
Fuentes: `["Documentos"]`
Tools: `["DocumentRAGTool"]`
Fallbacks: `[]`

Respuesta:

```markdown
El contrato marco de logística 2026, válido para ese año, regula la preparación, expedición, entrega y cierre documental de pedidos comerciales. Cubre pedidos estándar, urgentes, entregas parciales y envíos desde almacenes centrales o externos [1].

**Definiciones clave:**
*   **Pedido estándar:** Orden ERP liberada por producción sin prioridad comercial especial [1].
*   **Pedido urgente:** Marcado por dirección comercial con alta prioridad y fecha requerida en 48 horas o menos [1].
*   **Pedido bloqueado:** Detenido por producción debido a falta de material, capacidad, problemas de calidad o aprobación pendiente [1].

El plazo logístico comienza cuando producción registra la liberación final y el ERP contiene la dirección de entrega y contacto [1].

**Plazos de entrega:**
*   **Pedidos estándar:** Máximo 5 días laborables desde la liberación de producción [3].
*   **Pedidos urgentes:** Máximo 48 horas [3].
*   **Entregas parciales:** Solo cumplen si comercial las aprueba y el cliente acepta la documentación [3].

El cálculo de días laborables excluye sábados, domingos, festivos nacionales y festivos de la provincia de destino. Si un pedido sale después de las 14:00, el primer día computable es el siguiente día laborable. Aduanas y documentación sanitaria pueden pausar el contador en exportación si hay evidencia [3].

**Trazabilidad y evidencia:**
Cada expedición debe tener cinco hitos obligatorios: liberación de producción, preparación de almacén, salida de muelle, entrega al transportista y confirmación de entrega. Cada hito debe registrar fecha, origen, estados y observaciones [2]. Para auditorías, se requiere información como order\_id, customer\_id, cliente, fechas (prometida y real), transportista, estado ERP y de producción, y la causa de cualquier desviación. Si falta evidencia, debe indicarse "insufficient\_context" [2]. Un informe mensual categoriza los pedidos por estado (en curso, bloqueados, retrasados, finalizados, urgentes y parciales) [2].

**Fuentes:**
*   v2\_contrato\_marco\_logistica\_2026.pdf, página 1 [1]
*   v2\_contrato\_marco\_logistica\_2026.pdf, página 2 [3]
*   v2\_contrato\_marco\_logistica\_2026.pdf, página 3 [2]
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
Fuentes: `["Documentos"]`
Tools: `["DocumentRAGTool"]`
Fallbacks: `[]`

Respuesta:

```markdown
Sí, existen penalizaciones por retrasos. Por un retraso imputable, se aplica una penalización del 2%. Si el retraso supera los 5 días laborables, la penalización aumenta al 5%. Para pedidos urgentes, la penalización es del 3% desde el primer día de retraso imputable.
```

Pasos:

- Consulta RAG documental para localizar evidencia verificable sobre la pregunta
- Selecciona 3 chunk(s) relevante(s) de v2_anexo_penalizaciones_sla.pdf como base de evidencia
- Sintetiza la respuesta final usando solo el contexto recuperado y deja las citas documentales auditables en data.rag.citations

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
Con los datos disponibles, esta es la evaluacion de penalizaciones por pedido:

| Pedido | Cliente | Estado | Penalizacion |
| --- | --- | --- | --- |
| 10248 | Alfreds Futterkiste | en curso | No aplicable con los datos disponibles |
| 10252 | Alfreds Futterkiste | bloqueado (Falta de material) | No aplicable segun la documentacion consultada |
| 10255 | Alfreds Futterkiste | finalizado | No aplicable; consta enviado antes del plazo requerido |
| 10301 | Ana Trujillo Emparedados y helados | retrasado (Averia en linea de produccion) | No aplicable segun la documentacion consultada |
| 10312 | Bon app | bloqueado (Falta de capacidad) | No aplicable segun la documentacion consultada |

El principal punto de atencion es el seguimiento operativo de los pedidos bloqueados, retrasados o pendientes de datos antes de comunicar una penalizacion.
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

| Pedido | Estado ERP |
| --- | --- |
| 10248 | pendiente |
| 10252 | pendiente |
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
Con los datos disponibles, el impacto economico del pedido referenciado es 10252: 1863.00.
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
Según el documento v2_contrato_marco_logistica_2026.pdf, cada expedición debe conservar cinco hitos obligatorios: liberación de producción, preparación de almacén, salida de muelle, entrega al transportista y confirmación de entrega. Cada uno de estos hitos debe registrar la fecha, el usuario o sistema de origen, el estado anterior, el estado nuevo y una observación de negocio si el cambio afecta al cliente.
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
Según el documento v2_anexo_penalizaciones_sla.pdf, la evidencia obligatoria para aplicar una penalización debe incluir el ID del pedido (`order_id`), el ID del cliente (`customer_id`), el importe del pedido (procedente de líneas ERP), la fecha prometida, la fecha real de entrega, la fecha de liberación, el transportista, la causa del retraso y la fuente responsable.

Si no se puede demostrar la causa del retraso, el sistema debe informar que no hay evidencia suficiente para asignar responsabilidad, y no se debe aplicar una penalización solo porque la fecha real sea posterior a la fecha prometida.
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
Según el documento v2_anexo_penalizaciones_sla.pdf, las exclusiones de SLA son aplicables cuando el retraso se debe a: bloqueo de producción, falta de material, falta de capacidad, avería de línea, retrabajo por calidad, espera de validación técnica, fuerza mayor, error de dirección proporcionado por el cliente o un cambio de prioridad aprobado por dirección comercial. 

En cuanto a las pausas del SLA, el contador se detiene desde la fecha de bloqueo hasta la fecha de desbloqueo registrada por producción. En casos de exportación, también puede pausarse por documentación aduanera o sanitaria incompleta, siempre y cuando el expediente contenga el evento, responsable y fecha de resolución.
```

Pasos:

- Consulta RAG documental para localizar evidencia verificable sobre la pregunta
- Selecciona 3 chunk(s) relevante(s) de v2_anexo_penalizaciones_sla.pdf como base de evidencia
- Sintetiza la respuesta final usando solo el contexto recuperado y deja las citas documentales auditables en data.rag.citations

Evidencia RAG:

- documentos: `["v2_anexo_penalizaciones_sla.pdf"]`
- chunks_count: `3`

### BT-V2-04 - PASS - V2: bloqueos de produccion

Pregunta 1: `Segun v2_procedimiento_produccion_bloqueos.pdf, que motivos de bloqueo y campos obligatorios se registran?`

HTTP: `200` | status: `completed`
Fuentes: `["Documentos"]`
Tools: `["DocumentRAGTool"]`
Fallbacks: `[]`

Respuesta:

```markdown
Según el documento v2_procedimiento_produccion_bloqueos.pdf, los motivos válidos de bloqueo en producción son falta de material, falta de capacidad, incidencia de calidad, mantenimiento no planificado, aprobación técnica pendiente y discrepancia de receta o especificación. No se debe utilizar 'blocked' para retrasos menores si la orden puede continuar fabricándose.

Los campos obligatorios que deben registrarse en cada bloqueo son: order_id, línea de producción, motivo, responsable, fecha de inicio, fecha estimada de desbloqueo, impacto en cliente y comentario operativo. Si la fecha estimada no está disponible, el sistema debe indicar que no hay una fecha comunicable.
```

Pasos:

- Consulta RAG documental para localizar evidencia verificable sobre la pregunta
- Selecciona 3 chunk(s) relevante(s) de v2_procedimiento_produccion_bloqueos.pdf como base de evidencia
- Sintetiza la respuesta final usando solo el contexto recuperado y deja las citas documentales auditables en data.rag.citations

Evidencia RAG:

- documentos: `["v2_procedimiento_produccion_bloqueos.pdf"]`
- chunks_count: `3`

### BT-V2-05 - PASS - V2: calidad y entregas parciales

Pregunta 1: `Segun v2_politica_calidad_entregas.pdf, que ocurre con incidencias de calidad y entregas parciales?`

HTTP: `200` | status: `completed`
Fuentes: `["Documentos"]`
Tools: `["DocumentRAGTool"]`
Fallbacks: `[]`

Respuesta:

```markdown
Según el documento "v2_politica_calidad_entregas.pdf":

*   **Incidencias de calidad:** Una incidencia de calidad bloquea el pedido hasta que el departamento de calidad registre una resolución. Esta resolución debe especificar si el lote se libera, se sustituye, se reprocesa o se rechaza. Producción no puede desbloquear una retención de calidad sin la aprobación de calidad [1].
*   **Entregas parciales:** Requieren aprobación comercial y validación de calidad para cada lote entregado. Si una parte del pedido se retiene, el albarán debe detallar la parte enviada, la parte pendiente y el motivo de la retención [1, 3].

Fuentes:
*   v2_politica_calidad_entregas.pdf, página 2
*   v2_politica_calidad_entregas.pdf, página 3

Razonamiento:
1.  Se identificó la pregunta sobre incidencias de calidad y entregas parciales.
2.  Se revisó el contexto documental proporcionado para extraer la información relevante.
3.  Se sintetizó la información sobre incidencias de calidad y entregas parciales, citando las páginas correspondientes.
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
Según el documento v2_condiciones_comerciales_northwind.pdf, el impacto económico se calcula al unir el importe del ERP, el porcentaje contractual aplicable y la causa documentada. Si alguno de estos tres elementos falta, no se puede determinar el impacto económico definitivo. Además, la cabecera del pedido no es suficiente para calcular el impacto económico si faltan los precios, cantidades o descuentos.

En cuanto a la trazabilidad, toda respuesta de negocio debe especificar las fuentes consultadas, los pasos ejecutados y las herramientas utilizadas. El razonamiento debe ser un resumen auditable, distinguiendo entre hechos del ERP, reglas documentales y conclusiones. Para la información obtenida mediante RAG, es obligatorio citar el nombre del archivo y el número de página. Si se consulta el ERP, se debe indicar la entidad consultada, y si se usa información de producción, se debe especificar el `order_id` y el estado operativo.
```

Pasos:

- Consulta RAG documental para localizar evidencia verificable sobre la pregunta
- Selecciona 3 chunk(s) relevante(s) de v2_condiciones_comerciales_northwind.pdf como base de evidencia
- Sintetiza la respuesta final usando solo el contexto recuperado y deja las citas documentales auditables en data.rag.citations

Evidencia RAG:

- documentos: `["v2_condiciones_comerciales_northwind.pdf"]`
- chunks_count: `3`

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

