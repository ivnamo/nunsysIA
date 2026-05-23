# Validacion de entrega Docker/API

Fecha de ejecucion: 2026-05-23 10:23:35
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
| F-ERP-02 | OBLIGATORIO | PDF 2.1 | PASS | 200/completed | Produccion, ERP | ProductionAPITool, ERPTool, ProductionQueryTool |
| F-ERP-03 | OBLIGATORIO | PDF 2.1 | PASS | 200/completed | Produccion, ERP | ProductionAPITool, ERPTool, ProductionQueryTool, ERPQueryTool |
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
Tools: `["ProductionAPITool", "ERPTool", "ERPTool", "ProductionQueryTool"]`
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
- Consulta Produccion mediante filtros seguros

### F-ERP-03 - PASS - Clientes con pedidos retrasados por produccion

Pregunta 1: `Que clientes tienen pedidos retrasados por problemas de produccion?`

HTTP: `200` | status: `completed`
Fuentes: `["Produccion", "ERP"]`
Tools: `["ProductionAPITool", "ERPTool", "ProductionQueryTool", "ERPQueryTool"]`
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
- Consulta Produccion mediante filtros seguros
- Consulta ERP mediante filtros seguros

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
Aquí está un resumen de los plazos de entrega según el documento proporcionado:

**Plazos de entrega:**
*   **Pedidos estándar:** Deben entregarse en un plazo máximo de 5 días laborables desde la liberación de producción.
*   **Pedidos urgentes:** Deben entregarse en un plazo máximo de 48 horas desde la liberación de producción.

**Consideraciones para el cálculo de días laborables:**
*   Se excluyen sábados, domingos, festivos nacionales y festivos de la provincia de destino donde el transportista no preste servicio.
*   Si un pedido sale después de las 14:00, el primer día computable será el siguiente día laborable.
*   En exportación, aduanas y la documentación sanitaria pueden pausar el contador si hay evidencia en el expediente.

**Excepciones (no hay incumplimiento logístico):**
*   No se considera incumplimiento si el retraso se debe a falta de material, avería crítica de línea, cambio de prioridad aprobado o datos ERP incompletos. Estas excepciones deben estar documentadas con el `order_id`, causa, responsable y fecha de resolución.

**Penalizaciones:**
*   Se pueden aplicar penalizaciones económicas si hay incumplimiento de plazo, la causa es imputable al operador logístico y existe evidencia completa en ERP, producción y prueba de entrega.
*   Para pedidos estándar con más de 2 días laborables de retraso imputable, la penalización es del 2%. Si superan los 5 días laborables, la penalización sube al 5%.

---
**Fuentes consultadas:**
*   v2_contrato_marco_logistica_2026.pdf [1, 2]
*   v2_anexo_penalizaciones_sla.pdf [3]

**Pasos ejecutados:**
1.  Se analizó el contexto documental proporcionado para identificar la información relevante sobre plazos de entrega, calendarios, excepciones y penalizaciones.
2.  Se extrajeron los puntos clave de cada sección para sintetizar la respuesta.
3.  Se citaron las fuentes correspondientes a cada fragmento de información.
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
El contrato marco de logística 2026 regula la preparación, expedición, entrega y cierre documental de pedidos comerciales durante el año 2026, abarcando pedidos estándar, urgentes, entregas parciales y salidas desde almacenes centrales o externos [1].

**Definiciones Clave:**
*   **Pedido estándar:** Orden ERP liberada por producción sin prioridad comercial especial [1].
*   **Pedido urgente:** Orden con alta prioridad de dirección comercial y fecha requerida igual o menor a 48 horas [1].
*   **Pedido bloqueado:** Orden detenida por producción debido a falta de material, capacidad, incidencia de calidad o aprobación pendiente [1].

**Plazos de Entrega:**
*   **Pedidos estándar:** Máximo 5 días laborables desde la liberación de producción [3].
*   **Pedidos urgentes:** Máximo 48 horas [3].
*   Las entregas parciales solo cumplen si son aprobadas por comercial y el cliente acepta la documentación [3].

**Cálculo de Plazos:**
*   Excluye sábados, domingos, festivos nacionales y festivos de la provincia de destino [3].
*   Si el pedido sale después de las 14:00, el primer día computable es el siguiente día laborable [3].
*   En exportación, aduanas y documentación sanitaria pueden pausar el contador si hay evidencia [3].

**Trazabilidad y Evidencia:**
*   Se deben conservar cinco hitos por expedición: liberación de producción, preparación de almacén, salida de muelle, entrega al transportista y confirmación de entrega, cada uno con fecha, origen, estados y observaciones [2].
*   La evidencia mínima para auditorías incluye order_id, customer_id, cliente, fecha prometida, fecha real, transportista, estado ERP, estado de producción y causa de desviación [2].
*   El informe mensual debe separar pedidos en curso, bloqueados, retrasados, finalizados, urgentes y entregas parciales [2].
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
Sí, existen penalizaciones por retrasos. Para pedidos estándar, se aplica una penalización del 2% si el retraso imputable supera los 2 días laborables, y del 5% si excede los 5 días laborables. Para pedidos urgentes, la penalización es del 3% desde el primer día de retraso imputable.

La penalización solo procede si hay un incumplimiento de plazo, la causa es imputable al operador logístico y existe evidencia completa en el ERP, producción y prueba de entrega. Para aplicar una penalización, se requiere evidencia obligatoria como el `order_id`, `customer_id`, importe del pedido, fechas de promesa y entrega real, fecha de liberación, transportista, causa del retraso y la fuente responsable.
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
Según el documento `v2_anexo_penalizaciones_sla.pdf`:

Para aplicar una penalización, la evidencia obligatoria debe incluir el `order_id`, `customer_id`, importe del pedido, fecha prometida, fecha real de entrega, fecha de liberación, transportista, causa del retraso y la fuente responsable. El importe debe provenir de las líneas del ERP [1].

Si no se puede demostrar la causa del retraso, el sistema debe indicar que no hay evidencia suficiente para asignar responsabilidad. En este caso, no se debe aplicar una penalización solo porque la fecha real de entrega sea posterior a la fecha prometida [1, 2].

**Fuentes consultadas:**
* v2_anexo_penalizaciones_sla.pdf
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
Según el documento "v2_anexo_penalizaciones_sla.pdf", las exclusiones de penalizaciones de SLA incluyen retrasos por bloqueo de producción, falta de material, falta de capacidad, avería de línea, retrabajo por calidad, espera de validación técnica, fuerza mayor, error de dirección aportado por el cliente o cambio de prioridad aprobado por dirección comercial. Las pausas en el contador de SLA ocurren desde la fecha de bloqueo hasta la fecha de desbloqueo registrada por producción. En exportación, también puede pausarse por documentación aduanera o sanitaria incompleta, siempre que el expediente contenga evento, responsable y fecha de resolución.
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
Según el documento v2_procedimiento_produccion_bloqueos.pdf, los motivos válidos para un bloqueo son:
* Falta de material
* Falta de capacidad
* Incidencia de calidad
* Mantenimiento no planificado
* Aprobación técnica pendiente
* Discrepancia de receta o especificación

No se debe usar el estado "blocked" para retrasos menores si la orden puede continuar su fabricación.

Los campos obligatorios que se deben registrar para cada bloqueo incluyen:
* Order_id
* Línea de producción
* Motivo
* Responsable
* Fecha de inicio
* Fecha estimada de desbloqueo
* Impacto en cliente
* Comentario operativo

Si la fecha estimada de desbloqueo no está disponible, el sistema debe indicar que no existe una fecha comunicable.
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
Según el documento `v2_politica_calidad_entregas.pdf`:

*   **Incidencias de calidad:** Una incidencia de calidad bloquea el pedido hasta que el departamento de calidad registre una resolución. Esta resolución debe especificar si el lote se libera, se sustituye, se reprocesa o se rechaza. El equipo de producción no puede desbloquear una retención de calidad sin la aprobación de calidad. [1]
*   **Entregas parciales:** Requieren la aprobación comercial y la validación de calidad para cada lote entregado. Si una parte del pedido se retiene, el albarán debe detallar la parte enviada, la parte pendiente y el motivo de la retención. [1, 3]

**Fuentes:**
*   v2_politica_calidad_entregas.pdf, página 2, doc_059ef28fa502_p2_c1
*   v2_politica_calidad_entregas.pdf, página 2, doc_059ef28fa502_p2_c2
*   v2_politica_calidad_entregas.pdf, página 3, doc_059ef28fa502_p3_c1

**Razonamiento:**
Se ha sintetizado la información relevante sobre incidencias de calidad y entregas parciales directamente del contexto documental proporcionado, citando las fuentes correspondientes.
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
Según el documento v2_condiciones_comerciales_northwind.pdf:

El **impacto económico** se calcula uniendo el importe del ERP, el porcentaje contractual y la causa documentada, en caso de que una penalización o retraso tenga consecuencias económicas. Si falta alguno de estos tres elementos, no se puede determinar un impacto definitivo [1].

En cuanto a la **trazabilidad**, toda respuesta de negocio debe especificar las fuentes consultadas, los pasos ejecutados y las herramientas utilizadas. El razonamiento proporcionado debe ser un resumen auditable, distinguiendo entre hechos del ERP, reglas documentales y conclusiones. Para las consultas RAG, se debe citar el nombre del archivo y la página; para el ERP, la entidad consultada; y para producción, el order_id y el estado operativo [2].
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

