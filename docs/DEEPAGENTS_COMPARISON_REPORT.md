# Deep Agents Comparison Report

Fecha de ejecucion: 2026-05-22 19:39:54

Resultado global: PASS=5, PARTIAL=0, FAIL=0, BLOCKER=0.

Runtime:

- Workflow estable: `QueryWorkflowService`.
- Flujo sidecar: `DeepAgentsQueryService`.
- Flujo tools: `DeepAgentsToolsQueryService`.
- Sidecar usa el workflow estable como tool auditable.
- Tools expone ERP, Produccion, RAG y Memoria como tools individuales.
- Tools conserva `write_todos` y excluye filesystem, shell y subagentes.
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
- deepagents_planning: `{'todos_used': True, 'todo_tool_calls_count': 3}`
- answer: El cliente **ALFKI** (Alfreds Futterkiste) tiene **2 pedidos pendientes** en el ERP, cuyos estados de producción son los siguientes:

1. **Pedido ID 10248**
   - **Importe:** 440.00
   - **Fecha de pedido:** 2026-05-02 (Requerido para el 2026-05-20)
   - **Estado de producción:** `in_progress` (En proceso)
   - **Fecha estimada de finalización:** 2026-05-22

2. **Pedido ID 10252**
   - **Importe:** 1863.00
   - **Fecha de pedido:** 2026-05-07 (Requerido para el 2026-05-25)
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
- answer: Hay 2 clientes afectados por bloqueos de produccion.

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
- deepagents_planning: `{'todos_used': True, 'todo_tool_calls_count': 3}`
- answer: Los clientes afectados por bloqueos en producción, obtenidos tras cruzar las órdenes de producción bloqueadas con los datos de pedidos del ERP, son los siguientes:

### 1. **Alfreds Futterkiste** (ID: `ALFKI`)
* **Pedido ERP:** ID `10252` (Importe: 1863.00, Estado ERP: `pending`, Fecha: 2026-05-07)
* **Estado de producción:** Bloqueado (`blocked`)
* **Motivo del bloqueo:** Falta de material
* **Fecha estimada de finalización:** 2026-05-30

### 2. **Bon app** (ID: `BONAP`)
* **Pedido ERP:** ID `10312` (Importe: 1210.00, Estado ERP: `pending`, Fecha: 2026-05-18)
* **Estado de producción:** Bloqueado (`blocked`)
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
- deepagents_planning: `{'todos_used': True, 'todo_tool_calls_count': 3}`
- answer: Basándome en los datos obtenidos de la herramienta compuesta de ERP, producción y contratos, el análisis de los pedidos y su riesgo de penalización es el siguiente:

### **Pedido con riesgo de generar penalización**

*   **Pedido 10248 (Cliente: Alfreds Futterkiste)**
    *   **Importe:** 440.00 €
    *   **Fecha de pedido (ERP):** 2026-05-02 (Estado ERP: *Pending*)
    *   **Estado de producción:** *In Progress* (Fecha estimada de finalización: 2026-05-22)
    *   **Motivo de penalización:** El pedido acumula un retraso significativo (20 días desde la fecha de pedido, superando con creces el límite contractual de 5 días laborables para pedidos estándar). Al revisar la producción, **no consta ningún motivo de bloqueo o retraso justificado** (`blocked_reason: null`, `delay_reason: null`). Por lo tanto, el retraso se considera imputable y generará la penalización correspondiente según la matriz de SLA (5% al superar los 5 días laborables de retraso).

---

### **Pedidos excluidos de penalización (No generan riesgo)**

De acuerdo con el **Anexo de penalizaciones y SLA (v2_anexo_penalizaciones_sla.pdf)**, no se aplican penalizaciones cuando el retraso procede de causas como falta de material, falta de capacidad o averías de línea. Los siguientes pedidos están exentos:

1.  **Pedido 10252 (Alfreds Futterkiste)**
    *   **Estado:** Bloqueado (*Blocked*)
    *   **Motivo de exclusión:** Registra bloqueo por **"Falta de material"**, causa excluida explícitamente en el contrato.
2.  **Pedido 10301 (Ana Trujillo Emparedados y helados)**
    *   **Estado:** Retrasado (*Delayed*)
    *   **Motivo de exclusión:** El retraso se debe a una **"Avería en línea de producción"**, contemplada como caso no penalizable.
3.  **Pedido 10312 (Bon app)**
    *   **Estado:** Bloqueado (*Blocked*)
    *   **Motivo de exclusión:** Registra bloqueo por **"Falta de capacidad"**, que también es una exclusión válida según los términos de SLA.
4.  **Pedido 10255 (Alfreds Futterkiste)**
    *   **Estado:** Finalizado y enviado (*Shipped* / *Finished*). No presenta demoras ni riesgos de penalización activos.

## DA-04 - Follow-up conversacional con conversation_id

Veredicto: **PASS**

Preguntas:

- Que pedidos pendientes tiene el cliente ALFKI?
- Y en que estado estan?

Incidencias:

- TRACE tools: tool_calls distintas: estable=['MemoryTool', 'ERPTool', 'ProductionAPITool', 'ProductionAPITool'], tools=['MemoryTool', 'MemoryTool', 'ERPQueryTool', 'ProductionAPITool']

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
- tools: `['MemoryTool', 'MemoryTool', 'ERPQueryTool', 'ProductionAPITool']`
- fallbacks: `[]`
- answer: Los pedidos pendientes del cliente **ALFKI** presentan el siguiente estado de producción:

1. **Pedido ID 10248**
   - **Estado ERP:** Pendiente (`pending`)
   - **Estado de Producción:** En progreso (`in_progress`)
   - **Fecha estimada de finalización:** 2026-05-22
   - **Observaciones:** No presenta bloqueos ni retrasos.

2. **Pedido ID 10252**
   - **Estado ERP:** Pendiente (`pending`)
   - **Estado de Producción:** Bloqueado (`blocked`)
   - **Motivo del bloqueo:** Falta de material
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
- answer: Con los datos disponibles, el contrato marco de logística 2026 y su anexo de penalizaciones no mencionan nada sobre criptomonedas.

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
- answer: Tras realizar las consultas pertinentes en el sistema documental mediante las herramientas disponibles para términos como "criptomonedas", "criptomoneda", "contrato", "crypto", "blockchain" y "moneda", el sistema indica que no hay contexto documental suficiente para responder a la pregunta. Por lo tanto, no se dispone de información contractual sobre criptomonedas en los documentos registrados.
