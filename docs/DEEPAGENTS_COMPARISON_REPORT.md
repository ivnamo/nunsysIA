# Deep Agents Comparison Report

Fecha de ejecucion: 2026-05-22 19:25:56

Resultado global: PASS=5, PARTIAL=0, FAIL=0, BLOCKER=0.

Runtime:

- Workflow estable: `QueryWorkflowService`.
- Flujo sidecar: `DeepAgentsQueryService`.
- Flujo tools: `DeepAgentsToolsQueryService`.
- Sidecar usa el workflow estable como tool auditable.
- Tools expone ERP, Produccion, RAG y Memoria como tools individuales.
- El veredicto separa incidencias semanticas/eficiencia de diferencias de traza.
- Modelo Deep Agents: `DEEPAGENTS_MODEL` o valor por defecto.

## DA-01 - ALFKI pendientes y estado de produccion

Veredicto: **PASS**

Preguntas:

- Que pedidos pendientes tiene el cliente ALFKI y en que estado de produccion estan?

Incidencias:

- TRACE tools: tool_calls distintas: estable=['ERPTool', 'ProductionAPITool', 'ProductionAPITool'], tools=['ERPTool', 'ProductionAPITool']

Respuesta estable:

- status: `completed`
- sources: `['ERP', 'Produccion']`
- tools: `['ERPTool', 'ProductionAPITool', 'ProductionAPITool']`
- fallbacks: `[]`
- answer: El cliente ALFKI tiene 2 pedidos pendientes:

| Pedido | Estado ERP | Estado produccion | Observacion |
| --- | --- | --- | --- |
| 10248 | Pendiente | En curso | Sin bloqueo informado |
| 10252 | Pendiente | Bloqueado | Falta de material |

El punto de atencion es el pedido 10252, porque requiere seguimiento operativo desde produccion.

Respuesta Deep Agents sidecar:

- status: `completed`
- sources: `['ERP', 'Produccion']`
- tools: `['ERPTool', 'ProductionAPITool', 'ProductionAPITool']`
- fallbacks: `[]`
- answer: El cliente ALFKI tiene 2 pedidos pendientes:

| Pedido | Estado ERP | Estado produccion | Observacion |
| --- | --- | --- | --- |
| 10248 | Pendiente | En curso | Sin bloqueo informado |
| 10252 | Pendiente | Bloqueado | Falta de material |

El punto de atencion es el pedido 10252, porque requiere seguimiento operativo desde produccion.

Respuesta Deep Agents tools:

- status: `completed`
- sources: `['ERP', 'Produccion']`
- tools: `['ERPTool', 'ProductionAPITool']`
- fallbacks: `[]`
- answer: El cliente **ALFKI** (Alfreds Futterkiste) tiene **2 pedidos pendientes**:

1. **Pedido ID: 10248**
   - **Importe:** 440.00 €
   - **Fecha de pedido:** 2026-05-02 (Fecha requerida: 2026-05-20)
   - **Estado de producción:** `in_progress` (En progreso)
   - **Fecha estimada de finalización:** 2026-05-22

2. **Pedido ID: 10252**
   - **Importe:** 1,863.00 €
   - **Fecha de pedido:** 2026-05-07 (Fecha requerida: 2026-05-25)
   - **Estado de producción:** `blocked` (Bloqueado)
   - **Motivo de bloqueo:** Falta de material
   - **Fecha estimada de finalización:** 2026-05-30

## DA-02 - Bloqueos de produccion cruzados con ERP

Veredicto: **PASS**

Preguntas:

- Cruza produccion con ERP y dime clientes afectados por bloqueos.

Incidencias:

- Sin divergencias criticas.

Respuesta estable:

- status: `completed`
- sources: `['Produccion', 'ERP']`
- tools: `['ProductionQueryTool', 'ERPQueryTool']`
- fallbacks: `[]`
- answer: Hay 2 clientes afectados por bloqueos de produccion.

| Cliente | Pedido | Motivo |
| --- | --- | --- |
| ALFKI - Alfreds Futterkiste | 10252 | Falta de material |
| BONAP - Bon app | 10312 | Falta de capacidad |

El siguiente punto de atencion es resolver estos bloqueos desde produccion.

Respuesta Deep Agents sidecar:

- status: `completed`
- sources: `['Produccion', 'ERP']`
- tools: `['ProductionQueryTool', 'ERPQueryTool']`
- fallbacks: `[]`
- answer: Hay clientes afectados por bloqueos de produccion: 2.

| Cliente | Pedido | Motivo |
| --- | --- | --- |
| ALFKI - Alfreds Futterkiste | 10252 | Falta de material |
| BONAP - Bon app | 10312 | Falta de capacidad |

El siguiente punto de atencion es resolver estos bloqueos desde produccion.

Respuesta Deep Agents tools:

- status: `completed`
- sources: `['Produccion', 'ERP']`
- tools: `['ProductionQueryTool', 'ERPQueryTool']`
- fallbacks: `[]`
- answer: Los clientes afectados por bloqueos en producción son:

1. **Alfreds Futterkiste** (ID Cliente: `ALFKI`)
   * **Pedido ID:** 10252
   * **Importe:** 1.863,00 €
   * **Estado ERP:** pending
   * **Motivo del bloqueo:** Falta de material
   * **Fecha estimada de finalización:** 2026-05-30

2. **Bon app** (ID Cliente: `BONAP`)
   * **Pedido ID:** 10312
   * **Importe:** 1.210,00 €
   * **Estado ERP:** pending
   * **Motivo del bloqueo:** Falta de capacidad
   * **Fecha estimada de finalización:** 2026-06-02

## DA-03 - Penalizacion potencial con documento contractual

Veredicto: **PASS**

Preguntas:

- Dame los pedidos que puedan generar penalizacion y dime por que.

Incidencias:

- TRACE tools: tool_calls distintas: estable=['ERPTool', 'ProductionAPITool', 'ProductionAPITool', 'ProductionAPITool', 'ProductionAPITool', 'ProductionAPITool', 'DocumentRAGTool'], tools=['ERPQueryTool', 'ProductionQueryTool', 'DocumentRAGTool']

Respuesta estable:

- status: `completed`
- sources: `['ERP', 'Produccion', 'Documentos']`
- tools: `['ERPTool', 'ProductionAPITool', 'ProductionAPITool', 'ProductionAPITool', 'ProductionAPITool', 'ProductionAPITool', 'DocumentRAGTool']`
- fallbacks: `[]`
- answer: Con los datos disponibles, esta es la evaluacion de penalizaciones por pedido:

| Pedido | Cliente | Estado | Penalizacion |
| --- | --- | --- | --- |
| 10248 | Alfreds Futterkiste | en curso | No aplicable con los datos disponibles |
| 10252 | Alfreds Futterkiste | bloqueado (Falta de material) | No aplicable segun la documentacion consultada |
| 10255 | Alfreds Futterkiste | finalizado | No aplicable; consta enviado antes del plazo requerido |
| 10301 | Ana Trujillo Emparedados y helados | retrasado (Averia en linea de produccion) | No aplicable segun la documentacion consultada |
| 10312 | Bon app | bloqueado (Falta de capacidad) | No aplicable segun la documentacion consultada |

El principal punto de atencion es el seguimiento operativo de los pedidos bloqueados, retrasados o pendientes de datos antes de comunicar una penalizacion.

Respuesta Deep Agents sidecar:

- status: `completed`
- sources: `['ERP', 'Produccion', 'Documentos']`
- tools: `['ERPTool', 'ProductionAPITool', 'ProductionAPITool', 'ProductionAPITool', 'ProductionAPITool', 'ProductionAPITool', 'DocumentRAGTool']`
- fallbacks: `[]`
- answer: Con los datos disponibles, esta es la evaluacion de penalizaciones por pedido:

| Pedido | Cliente | Estado | Penalizacion |
| --- | --- | --- | --- |
| 10248 | Alfreds Futterkiste | en curso | No aplicable con los datos disponibles |
| 10252 | Alfreds Futterkiste | bloqueado (Falta de material) | No aplicable segun la documentacion consultada |
| 10255 | Alfreds Futterkiste | finalizado | No aplicable; consta enviado antes del plazo requerido |
| 10301 | Ana Trujillo Emparedados y helados | retrasado (Averia en linea de produccion) | No aplicable segun la documentacion consultada |
| 10312 | Bon app | bloqueado (Falta de capacidad) | No aplicable segun la documentacion consultada |

El principal punto de atencion es el seguimiento operativo de los pedidos bloqueados, retrasados o pendientes de datos antes de comunicar una penalizacion.

Respuesta Deep Agents tools:

- status: `completed`
- sources: `['ERP', 'Produccion', 'Documentos']`
- tools: `['ERPQueryTool', 'ProductionQueryTool', 'DocumentRAGTool']`
- fallbacks: `[]`
- answer: Basándome en los datos obtenidos del ERP, los estados de producción y el anexo de penalizaciones y SLA (documento `v2_anexo_penalizaciones_sla.pdf`), a continuación se detallan los pedidos y el análisis de su riesgo de penalización:

### Pedido que **SÍ** puede generar penalización:

* **Pedido 10248** (Cliente: **Alfreds Futterkiste** - ALFKI)
  * **Importe:** 440.00 €
  * **Fecha del pedido:** 2026-05-02
  * **Estado de producción:** `in_progress` (Fecha estimada: 2026-05-22)
  * **Razón del riesgo:** Ha acumulado un retraso significativo que supera con creces el plazo de SLA estándar de 5 días laborables (20 días naturales transcurridos). Al encontrarse en estado `in_progress` sin ningún motivo de bloqueo registrado (`blocked_reason` es null) ni retraso justificado (`delay_reason` es null), no aplica ninguna de las exclusiones del contrato. Al superar los 5 días laborables de retraso imputable, se expone a la penalización máxima del **5%** del importe del pedido.

---

### Pedidos **EXCLUIDOS** de penalización (No generarán penalización):

* **Pedido 10252** (Cliente: **Alfreds Futterkiste** - ALFKI)
  * **Importe:** 1,863.00 €
  * **Estado de producción:** `blocked` (Fecha estimada: 2026-05-30)
  * **Razón de exclusión:** El motivo del bloqueo registrado es **"Falta de material"**. El anexo de penalizaciones excluye explícitamente de sanción económica los retrasos procedentes de falta de material.

* **Pedido 10255** (Cliente: **Alfreds Futterkiste** - ALFKI)
  * **Importe:** 2,490.00 €
  * **Estado de producción:** `finished` el 2026-05-14 (Estado ERP: `shipped`)
  * **Razón de exclusión:** El pedido se ha finalizado y enviado correctamente dentro de los plazos establecidos.

* **Pedido 10301** (Cliente: **Ana Trujillo Emparedados y helados** - ANATR)
  * **Importe:** 920.00 €
  * **Estado de producción:** `delayed` (Fecha estimada: 2026-06-03)
  * **Razón de exclusión:** El motivo del retraso es una **"Averia en linea de produccion"**. El contrato marco y el anexo de SLA establecen que las averías de línea son causas no penalizables al no ser imputables de forma directa al operador logístico.

* **Pedido 10312** (Cliente: **Bon app** - BONAP)
  * **Importe:** 1,210.00 €
  * **Estado de producción:** `blocked` (Fecha estimada: 2026-06-02)
  * **Razón de exclusión:** El motivo del bloqueo es **"Falta de capacidad"**. Según la sección de exclusiones del anexo de SLA, la falta de capacidad es un motivo de exclusión y no aplica penalización económica.

## DA-04 - Follow-up conversacional con conversation_id

Veredicto: **PASS**

Preguntas:

- Que pedidos pendientes tiene el cliente ALFKI?
- Y en que estado estan?

Incidencias:

- TRACE tools: tool_calls distintas: estable=['MemoryTool', 'ERPTool', 'ProductionAPITool', 'ProductionAPITool'], tools=['MemoryTool', 'ERPQueryTool', 'ProductionAPITool']

Respuesta estable:

- status: `completed`
- sources: `['Memoria', 'ERP', 'Produccion']`
- tools: `['MemoryTool', 'ERPTool', 'ProductionAPITool', 'ProductionAPITool']`
- fallbacks: `[]`
- answer: El cliente ALFKI tiene 2 pedidos pendientes:

| Pedido | Estado ERP | Estado produccion | Observacion |
| --- | --- | --- | --- |
| 10248 | Pendiente | En curso | Sin bloqueo informado |
| 10252 | Pendiente | Bloqueado | Falta de material |

El punto de atencion es el pedido 10252, porque requiere seguimiento operativo desde produccion.

Respuesta Deep Agents sidecar:

- status: `completed`
- sources: `['Memoria', 'ERP', 'Produccion']`
- tools: `['MemoryTool', 'ERPTool', 'ProductionAPITool', 'ProductionAPITool']`
- fallbacks: `[]`
- answer: El cliente ALFKI tiene 2 pedidos pendientes:

| Pedido | Estado ERP | Estado produccion | Observacion |
| --- | --- | --- | --- |
| 10248 | Pendiente | En curso | Sin bloqueo informado |
| 10252 | Pendiente | Bloqueado | Falta de material |

El punto de atencion es el pedido 10252, porque requiere seguimiento operativo desde produccion.

Respuesta Deep Agents tools:

- status: `completed`
- sources: `['Memoria', 'ERP', 'Produccion']`
- tools: `['MemoryTool', 'ERPQueryTool', 'ProductionAPITool']`
- fallbacks: `[]`
- answer: Los pedidos del cliente **Alfreds Futterkiste (ALFKI)** se encuentran en los siguientes estados:

1. **Pedido ID: 10248**
   - **Estado ERP:** pending
   - **Estado de Producción:** in_progress
   - **Fecha estimada de finalización:** 2026-05-22

2. **Pedido ID: 10252**
   - **Estado ERP:** pending
   - **Estado de Producción:** blocked
   - **Motivo de bloqueo:** Falta de material
   - **Fecha estimada de finalización:** 2026-05-30

## DA-05 - Pregunta documental sin evidencia

Veredicto: **PASS**

Preguntas:

- Que dice el contrato sobre criptomonedas?

Incidencias:

- Sin divergencias criticas.

Respuesta estable:

- status: `completed`
- sources: `['Documentos']`
- tools: `['DocumentRAGTool']`
- fallbacks: `[]`
- answer: El contrato marco de logística 2026 y su anexo de penalizaciones no mencionan las criptomonedas en ninguno de los apartados disponibles.

Respuesta Deep Agents sidecar:

- status: `completed`
- sources: `['Documentos']`
- tools: `['DocumentRAGTool']`
- fallbacks: `[]`
- answer: Con los datos disponibles, el contrato marco de logística 2026 y su anexo de penalizaciones no mencionan nada sobre criptomonedas.

Respuesta Deep Agents tools:

- status: `completed`
- sources: `['Documentos']`
- tools: `['DocumentRAGTool']`
- fallbacks: `[]`
- answer: En el documento consultado (**v2_contrato_marco_logistica_2026.pdf**, correspondiente al *"Contrato marco de logística 2026 - versión extendida"*), **no existe ninguna mención, cláusula ni referencia al término "criptomonedas"** ni a conceptos relacionados con activos digitales en las secciones indexadas (Páginas 1, 2 y 4).

Los contenidos del documento se limitan a:
* **Página 1 (Alcance, definiciones y reglas base):** Objeto del contrato (preparación, expedición, entrega y cierre de pedidos) y definiciones de pedidos (estándar, urgente, bloqueado, regla de inicio de plazo).
* **Página 2 (Plazos, calendarios y excepciones operativas):** Plazos de entrega ordinarios, cálculo de días laborables, excepciones y exclusión de incumplimiento.
* **Página 4 (Casos de decisión y resolución de conflictos):** Protocolos de actuación para pedidos liberados con retraso (Caso A), pedidos bloqueados por falta de material (Caso B) y solicitudes de adelanto de pedidos prioritarios por parte de comercial (Caso C).

*Nota: La página 3 del documento no está registrada ni se recupera en las búsquedas del sistema RAG, pero en todo el contenido disponible no figura ninguna regulación sobre criptomonedas.*
