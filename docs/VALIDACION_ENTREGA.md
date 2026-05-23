# Validacion de entrega Docker/API

Fecha de ejecucion: 2026-05-23 21:55:06
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
| F-ERP-03 | OBLIGATORIO | PDF 2.1 | PASS | 200/completed | Produccion, ERP | ProductionQueryTool, ERPQueryTool, ProductionAPITool, ERPTool |
| F-ERP-04 | OBLIGATORIO | PDF 2.1 | PASS | 200/completed | ERP, Produccion | ERPTool, ProductionAPITool |
| F-RAG-01 | OBLIGATORIO | PDF 2.2 | PASS | 200/completed | Documentos | DocumentRAGTool |
| F-RAG-02 | OBLIGATORIO | PDF 2.2 | PASS | 200/completed | Documentos | DocumentRAGTool |
| F-RAG-03 | OBLIGATORIO | PDF 2.2 | PASS | 200/completed | Documentos, Produccion | DocumentRAGTool, ProductionAPITool |
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

*   **Pedido 10248**:
    *   Importe: 440.00
    *   Fecha de pedido: 2026-05-02
    *   Estado de producción: En progreso (in_progress)
    *   Fecha estimada de finalización: 2026-05-22

*   **Pedido 10252**:
    *   Importe: 1863.00
    *   Fecha de pedido: 2026-05-07
    *   Estado de producción: Bloqueado (blocked)
    *   Razón del bloqueo: Falta de material
    *   Fecha estimada de finalización: 2026-05-30
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
Los siguientes pedidos están bloqueados:
- Pedido 10252: Bloqueado por 'Falta de material'.
- Pedido 10312: Bloqueado por 'Falta de capacidad'.
```

Pasos:

- Consulta API de produccion por estado
- Consulta ERP de cliente para pedido 10252
- Consulta ERP de cliente para pedido 10312

### F-ERP-03 - PASS - Clientes con pedidos retrasados por produccion

Pregunta 1: `Que clientes tienen pedidos retrasados por problemas de produccion?`

HTTP: `200` | status: `completed`
Fuentes: `["Produccion", "ERP"]`
Tools: `["ProductionQueryTool", "ERPQueryTool", "ProductionAPITool", "ERPTool"]`
Fallbacks: `[]`

Respuesta:

```markdown
El cliente 'Ana Trujillo Emparedados y helados' (ID: ANATR) tiene un pedido retrasado (ID: 10301) debido a una avería en la línea de producción.
```

Pasos:

- Consulta Produccion mediante filtros seguros
- Consulta ERP mediante filtros seguros
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
Updated todo list to [{'content': 'Obtener el año y mes actuales.', 'status': 'in_progress'}, {'content': 'Consultar pedidos ERP del mes actual.', 'status': 'pending'}, {'content': 'Extraer order_id de los resultados de ERP.', 'status': 'pending'}, {'content': 'Consultar el estado de producción de los order_id obtenidos.', 'status': 'pending'}, {'content': 'Combinar y resumir la información de ERP y producción.', 'status': 'pending'}]
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
Según el documento, los pedidos estándar deben entregarse en un plazo máximo de 5 días laborables desde la liberación de producción. Los pedidos urgentes tienen un plazo máximo de 48 horas. Las entregas parciales solo se consideran cumplimiento si son aprobadas por comercial y el cliente acepta la documentación.
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
El contrato marco de logística para 2026 regula la preparación, expedición, entrega y cierre documental de pedidos comerciales. Un "pedido bloqueado" se define como una orden detenida en producción por falta de material, capacidad, incidencia de calidad o aprobación pendiente. Para auditorías, se requiere un registro mínimo que incluya order_id, customer_id, cliente, fecha prometida, fecha real, transportista, estado ERP, estado de producción y causa de desviación.
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
Tools: `["DocumentRAGTool", "ProductionAPITool"]`
Fallbacks: `[]`

Respuesta:

```markdown
Sí, existen penalizaciones por retrasos. Para pedidos estándar, se aplica una penalización del 2% si el retraso imputable supera los 2 días laborables, y del 5% si excede los 5 días laborables. Los pedidos urgentes tienen una penalización del 3% desde el primer día de retraso imputable [1, 2].

Para que se aplique una penalización, debe haber un incumplimiento de plazo, la causa debe ser imputable al operador logístico y debe existir evidencia completa en ERP, producción y prueba de entrega [2]. La información de producción es necesaria para aportar el estado de la orden si hubo bloqueo, retraso o cualquier otra incidencia [3]. Por ejemplo, se ha identificado un pedido (ID 10301) con estado 'delayed' debido a una 'Averia en linea de produccion', lo que demuestra la existencia de retrasos en producción que pueden llevar a penalizaciones.
```

Pasos:

- Consulta RAG documental para localizar evidencia verificable sobre la pregunta
- Selecciona 3 chunk(s) relevante(s) de v2_anexo_penalizaciones_sla.pdf como base de evidencia
- Sintetiza la respuesta final usando solo el contexto recuperado y deja las citas documentales auditables en data.rag.citations
- Consulta API de produccion por estado

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
Los riesgos de penalización para los pedidos son los siguientes:

*   **Pedido 10248 (Alfreds Futterkiste):** **Potencial de penalización.** El pedido está en progreso con una fecha estimada de finalización (2026-05-22) posterior a la fecha requerida (2026-05-20). No se ha identificado ninguna razón de bloqueo o retraso que lo excluya de penalización según el anexo de penalizaciones.
*   **Pedido 10252 (Alfreds Futterkiste): No sujeto a penalización.** El pedido está bloqueado debido a "Falta de material", lo cual es una exclusión explícita para la aplicación de penalizaciones según el anexo de penalizaciones.
*   **Pedido 10255 (Alfreds Futterkiste): No sujeto a penalización.** El pedido ya ha sido enviado (2026-05-15) y finalizado, antes de la fecha requerida (2026-05-30).
*   **Pedido 10301 (Ana Trujillo Emparedados y helados): No sujeto a penalización.** El pedido está retrasado debido a "Averia en linea de produccion", lo cual es una exclusión explícita para la aplicación de penalizaciones según el anexo de penalizaciones.
*   **Pedido 10312 (Bon app): No sujeto a penalización.** El pedido está bloqueado debido a "Falta de capacidad", lo cual es una exclusión explícita para la aplicación de penalizaciones según el anexo de penalizaciones.
```json
{
  "answer": "Los riesgos de penalización para los pedidos son los siguientes:\n\n*   **Pedido 10248 (Alfreds Futterkiste):** **Potencial de penalización.** El pedido está en progreso con una fecha estimada de finalización (2026-05-22) posterior a la fecha requerida (2026-05-20). No se ha identificado ninguna razón de bloqueo o retraso que lo excluya de penalización según el anexo de penalizaciones.\n*   **Pedido 10252 (Alfreds Futterkiste): No sujeto a penalización.** El pedido está bloqueado debido a \"Falta de material\", lo cual es una exclusión explícita para la aplicación de penalizaciones según el anexo de penalizaciones.\n*   **Pedido 10255 (Alfreds Futterkiste): No sujeto a penalización.** El pedido ya ha sido enviado (2026-05-15) y finalizado, antes de la fecha requerida (2026-05-30).\n*   **Pedido 10301 (Ana Trujillo Emparedados y helados): No sujeto a penalización.** El pedido está retrasado debido a \"Averia en linea de produccion\", lo cual es una exclusión explícita para la aplicación de penalizaciones según el anexo de penalizaciones.\n*   **Pedido 10312 (Bon app): No sujeto a penalización.** El pedido está bloqueado debido a \"Falta de capacidad\", lo cual es una exclusión explícita para la aplicación de penalizaciones según el anexo de penalizaciones.",
  "sources": [
    "ERP (Pedidos 10248, 10252, 10255, 10301, 10312)",
    "Producción (Pedidos 10248, 10252, 10255, 10301, 10312)",
    "Documentos (v2_anexo_penalizaciones_sla.pdf, v2_contrato_marco_logistica_2026.pdf)"
  ],
  "reasoning": [
    "Se utilizó la tool compuesta `assess_penalty_risk_for_orders` para obtener información combinada de ERP, producción y documentos.",
    "Se analizaron los datos de cada pedido, incluyendo su estado en ERP y producción, las fechas requeridas y estimadas de finalización/envío, y las razones de bloqueo o retraso.",
    "Se consultaron los documentos `v2_anexo_penalizaciones_sla.pdf` y `v2_contrato_marco_logistica_2026.pdf` para identificar las cláusulas de penalización y las exclusiones aplicables.",
    "Se determinó el riesgo de penalización para cada pedido basándose en el cruce de la información de las tres fuentes y las reglas contractuales."
  ]
}
```
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
El cliente ALFKI (Alfreds Futterkiste) tiene los siguientes pedidos pendientes:
- **Pedido ID 10248**: Monto 440.00, Fecha de pedido 2026-05-02, Fecha requerida 2026-05-20.
- **Pedido ID 10252**: Monto 1863.00, Fecha de pedido 2026-05-07, Fecha requerida 2026-05-25.
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
De los pedidos mencionados, el Pedido ID 10252 está bloqueado por "Falta de material".
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
Según el documento v2_contrato_marco_logistica_2026.pdf, cada expedición debe conservar cinco hitos obligatorios: liberación de producción, preparación de almacén, salida de muelle, entrega al transportista y confirmación de entrega. Cada hito debe registrar la fecha, el usuario o sistema de origen, el estado anterior, el estado nuevo y una observación de negocio cuando el cambio afecte al cliente.
```

Pasos:

- Consulta RAG documental para localizar evidencia verificable sobre la pregunta
- Selecciona 3 chunk(s) relevante(s) de v2_contrato_marco_logistica_2026.pdf, v2_procedimiento_produccion_bloqueos.pdf como base de evidencia
- Sintetiza la respuesta final usando solo el contexto recuperado y deja las citas documentales auditables en data.rag.citations

Evidencia RAG:

- documentos: `["v2_contrato_marco_logistica_2026.pdf", "v2_procedimiento_produccion_bloqueos.pdf"]`
- chunks_count: `3`

### BT-V2-02 - PASS - V2: evidencia SLA

Pregunta 1: `Segun v2_anexo_penalizaciones_sla.pdf, que evidencia es obligatoria y que pasa si no se puede demostrar la causa del retraso?`

HTTP: `200` | status: `completed`
Fuentes: `["Documentos"]`
Tools: `["DocumentRAGTool"]`
Fallbacks: `[]`

Respuesta:

```markdown
Según el documento v2_anexo_penalizaciones_sla.pdf, la evidencia obligatoria para aplicar una penalización incluye: order_id, customer_id, importe del pedido, fecha prometida, fecha real de entrega, fecha de liberación, transportista, causa del retraso y fuente responsable. El importe debe proceder de líneas ERP. Específicamente, Producción debe aportar el estado de la orden si hubo bloqueo, retraso, retrabajo o incidencia de calidad. Si no se puede demostrar la causa del retraso, el sistema debe informar que no hay evidencia suficiente para asignar responsabilidad y no se aplicará penalización solo por el hecho de que la fecha real sea posterior a la prometida.
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
Según el documento v2_anexo_penalizaciones_sla.pdf, las exclusiones de penalizaciones se aplican cuando el retraso se debe a: bloqueo de producción, falta de material, falta de capacidad, avería de línea, retrabajo por calidad, espera de validación técnica, fuerza mayor, error de dirección proporcionado por el cliente o cambio de prioridad aprobado por dirección comercial.

Las pausas en el contador de SLA ocurren desde la fecha de bloqueo hasta la fecha de desbloqueo registrada por producción. En casos de exportación, también puede pausarse por documentación aduanera o sanitaria incompleta, siempre que el expediente contenga el evento, el responsable y la fecha de resolución.

Además, existen casos no penalizables como un pedido urgente marcado como tal después de la liberación y con ruta estándar ya planificada por logística, o una entrega rechazada por ausencia del cliente en domicilio con cita confirmada.
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
Según el documento "v2_procedimiento_produccion_bloqueos.pdf", los motivos de bloqueo válidos incluyen falta de material, falta de capacidad, incidencia de calidad, mantenimiento no planificado, aprobación técnica pendiente y discrepancia de receta o especificación. Los campos obligatorios para cada bloqueo son: order_id, línea de producción, motivo, responsable, fecha de inicio, fecha estimada de desbloqueo, impacto en cliente y comentario operativo. Si la fecha estimada no está disponible, el sistema debe indicar que no hay fecha comunicable.
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
Según el documento v2_politica_calidad_entregas.pdf, las incidencias de calidad bloquean un pedido hasta que Calidad registra una resolución, indicando si el lote se libera, sustituye, reprocesa o rechaza. Producción no puede desbloquear una retención de calidad sin la aprobación de Calidad. Las entregas parciales requieren aprobación comercial y validación de calidad para cada lote entregado. Si una parte del pedido queda retenida, el albarán debe especificar la parte enviada, la pendiente y el motivo de la retención. Además, los indicadores mensuales separan los pedidos con incidencia de calidad y las entregas parciales.
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
Según el documento v2_condiciones_comerciales_northwind.pdf, el impacto económico se calcula uniendo el importe del ERP, el porcentaje contractual y la causa documentada cuando una penalización o retraso tiene impacto económico. Si alguno de estos tres elementos falta, no se calcula un impacto definitivo.

En cuanto a la trazabilidad, para el cálculo del importe, el resultado debe indicar si procede del ERP, de un cálculo sobre líneas ERP o si no existe evidencia suficiente. Para el impacto económico, se exige una causa documentada.
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

