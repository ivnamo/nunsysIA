# Validacion de entrega Docker/API

Fecha de ejecucion: 2026-05-23 09:14:02
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
| F-ERP-03 | OBLIGATORIO | PDF 2.1 | PASS | 200/completed | Produccion, ERP | ProductionAPITool, ERPTool |
| F-ERP-04 | OBLIGATORIO | PDF 2.1 | PASS | 200/completed | ERP, Produccion | ERPTool, ProductionAPITool, ERPQueryTool |
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
Tools: `["ERPTool", "ProductionAPITool", "ERPQueryTool"]`
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
- Consulta ERP mediante filtros seguros

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
El contrato marco de logística 2026 regula la preparación, expedición, entrega y cierre documental de pedidos comerciales para el año 2026, abarcando pedidos estándar, urgentes, entregas parciales y aquellos con salida desde almacén central o externo [1].

**Definiciones clave:**
*   **Pedido estándar:** Orden ERP liberada por producción sin prioridad comercial especial [1].
*   **Pedido urgente:** Orden con alta prioridad y fecha requerida menor o igual a 48 horas, marcada por dirección comercial [1].
*   **Pedido bloqueado:** Orden detenida por producción debido a falta de material, capacidad, incidencia de calidad o aprobación pendiente [1].

**Plazos y calendario:**
*   El plazo logístico comienza cuando producción registra la liberación final y el ERP contiene la dirección de entrega y contacto [1].
*   Los pedidos estándar deben entregarse en un máximo de 5 días laborables desde la liberación de producción [3].
*   Los pedidos urgentes tienen un plazo máximo de 48 horas [3].
*   El cálculo de días laborables excluye sábados, domingos, festivos nacionales y festivos de la provincia de destino. Si un pedido sale después de las 14:00, el primer día computable es el siguiente día laborable [3].

**Trazabilidad y evidencia:**
*   Cada expedición debe registrar cinco hitos obligatorios: liberación de producción, preparación de almacén, salida de muelle, entrega al transportista y confirmación de entrega [2].
*   Para auditorías, se requiere evidencia mínima que incluya `order_id`, `customer_id`, cliente, fecha prometida, fecha real, transportista, estado ERP, estado de producción y causa de desviación [2].
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
Sí, existen penalizaciones por retrasos. Para pedidos estándar, se aplica una penalización del 2% si el retraso imputable supera los 2 días laborables, y sube al 5% si supera los 5 días laborables. Para pedidos urgentes, la penalización es del 3% desde el primer día de retraso imputable. Estas penalizaciones solo proceden si hay un incumplimiento de plazo imputable al operador logístico y evidencia completa en ERP, producción y prueba de entrega. Es necesario que consten datos como el order_id, customer_id, importe del pedido, fechas de entrega y liberación, transportista, causa del retraso y fuente responsable para aplicar una penalización.
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
Según el documento "v2_anexo_penalizaciones_sla.pdf":

La evidencia obligatoria para aplicar una penalización incluye: order_id, customer_id, importe del pedido (debe proceder de líneas ERP), fecha prometida, fecha real de entrega, fecha de liberación, transportista, causa del retraso y fuente responsable [1].

Si no se puede demostrar la causa del retraso, el sistema debe informar que no existe evidencia suficiente para asignar responsabilidad, y no se debe aplicar la penalización basándose únicamente en que la fecha real sea posterior a la prometida [1, 2].

Fuentes:
*   [1] v2_anexo_penalizaciones_sla.pdf, página 2
*   [2] v2_anexo_penalizaciones_sla.pdf, página 2
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
Según el documento v2_anexo_penalizaciones_sla.pdf, las exclusiones de SLA se aplican cuando el retraso se debe a: bloqueo de producción, falta de material, falta de capacidad, avería de línea, retrabajo por calidad, espera de validación técnica, fuerza mayor, error de dirección aportado por el cliente o cambio de prioridad aprobado por dirección comercial. Las pausas de SLA ocurren cuando el contador se detiene desde la fecha de bloqueo hasta la fecha de desbloqueo registrada por producción. En casos de exportación, también puede pausarse por documentación aduanera o sanitaria incompleta, siempre que el expediente contenga el evento, responsable y fecha de resolución.
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
Según el documento "v2_procedimiento_produccion_bloqueos.pdf", los motivos de bloqueo y los campos obligatorios que se registran son los siguientes:

**Motivos de bloqueo:**
Los motivos válidos para un bloqueo incluyen falta de material, falta de capacidad, incidencia de calidad, mantenimiento no planificado, aprobación técnica pendiente y discrepancia de receta o especificación [1].

**Campos obligatorios:**
Cada bloqueo debe registrar los siguientes campos: order_id, línea de producción, motivo, responsable, fecha de inicio, fecha estimada de desbloqueo, impacto en cliente y comentario operativo [1].

**Fuentes:**
*   v2_procedimiento_produccion_bloqueos.pdf, página 2, doc_797ae319cef6_p2_c1

**Razonamiento:**
1.  Se identificó que la pregunta solicitaba información sobre motivos de bloqueo y campos obligatorios de registro.
2.  Se consultó el contexto documental proporcionado, específicamente el chunk [1], que contenía ambas piezas de información directamente.
3.  Se extrajeron los motivos de bloqueo y los campos obligatorios del texto.
4.  Se construyó la respuesta utilizando solo la información del contexto y se citó la fuente.
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
Según la política de calidad para entregas a cliente (v2_politica_calidad_entregas.pdf), una incidencia de calidad bloquea el pedido hasta que el departamento de calidad registre una resolución. Esta resolución debe especificar si el lote se libera, se sustituye, se reprocesa o se rechaza, y Producción no puede desbloquear una retención de calidad sin la aprobación de Calidad.

En cuanto a las entregas parciales, estas requieren la aprobación comercial y la validación de calidad para cada lote entregado. Si una parte del pedido queda retenida, el albarán debe detallar la parte enviada, la parte pendiente y el motivo de la retención.
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

El **impacto económico** se calcula uniendo el importe del ERP, el porcentaje contractual y la causa documentada, siempre que una penalización o retraso tenga dicho impacto. Si alguno de estos tres elementos no está disponible, no se calcula un impacto definitivo.

La **trazabilidad** exige que toda respuesta de negocio indique las fuentes consultadas, los pasos ejecutados y las herramientas utilizadas. El razonamiento debe ser un resumen auditable que separe los hechos del ERP, las reglas documentales y las conclusiones. Si se utiliza RAG, se debe citar el nombre del archivo y la página; si se usa ERP, la entidad consultada; y si se usa producción, el `order_id` y el estado operativo.
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

