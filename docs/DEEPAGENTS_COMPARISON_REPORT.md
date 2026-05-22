# Deep Agents Comparison Report

Fecha de ejecucion: 2026-05-22 19:00:15

Resultado global: PASS=0, PARTIAL=5, FAIL=0, BLOCKER=0.

Runtime:

- Workflow estable: `QueryWorkflowService`.
- Flujo sidecar: `DeepAgentsQueryService`.
- Flujo tools: `DeepAgentsToolsQueryService`.
- Sidecar usa el workflow estable como tool auditable.
- Tools expone ERP, Produccion, RAG y Memoria como tools individuales.
- Modelo Deep Agents: `DEEPAGENTS_MODEL` o valor por defecto.

## DA-01 - ALFKI pendientes y estado de produccion

Veredicto: **PARTIAL**

Preguntas:

- Que pedidos pendientes tiene el cliente ALFKI y en que estado de produccion estan?

Incidencias:

- tools: tool_calls distintas: estable=['ERPTool', 'ProductionAPITool', 'ProductionAPITool'], tools=['ERPTool', 'ProductionAPITool']

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
- answer: El cliente **ALFKI** (Alfreds Futterkiste) tiene **2 pedidos pendientes** en el ERP. A continuación se detalla su estado de producción correspondiente:

1. **Pedido ID: 10248**
   - **Estado ERP**: Pendiente
   - **Importe**: 440.00
   - **Fecha de Pedido**: 2026-05-02
   - **Fecha Requerida**: 2026-05-20
   - **Estado de Producción**: En progreso (`in_progress`)
   - **Fecha Estimada de Finalización**: 2026-05-22

2. **Pedido ID: 10252**
   - **Estado ERP**: Pendiente
   - **Importe**: 1863.00
   - **Fecha de Pedido**: 2026-05-07
   - **Fecha Requerida**: 2026-05-25
   - **Estado de Producción**: Bloqueado (`blocked`)
   - **Motivo de Bloqueo**: Falta de material
   - **Fecha Estimada de Finalización**: 2026-05-30

## DA-02 - Bloqueos de produccion cruzados con ERP

Veredicto: **PARTIAL**

Preguntas:

- Cruza produccion con ERP y dime clientes afectados por bloqueos.

Incidencias:

- tools: tool_calls distintas: estable=['ProductionQueryTool', 'ERPQueryTool'], tools=['ProductionAPITool', 'ERPQueryTool']

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
- tools: `['ProductionAPITool', 'ERPQueryTool']`
- fallbacks: `[]`
- answer: Los clientes afectados por bloqueos en producción son los siguientes:

1. **Alfreds Futterkiste** (`ALFKI`)
   - **ID de Pedido:** 10252
   - **Importe:** 1.863,00 €
   - **Estado ERP:** pending
   - **Estado de Producción:** Bloqueado (`blocked`)
   - **Motivo del Bloqueo:** Falta de material
   - **Fecha Estimada de Finalización:** 2026-05-30

2. **Bon app** (`BONAP`)
   - **ID de Pedido:** 10312
   - **Importe:** 1.210,00 €
   - **Estado ERP:** pending
   - **Estado de Producción:** Bloqueado (`blocked`)
   - **Motivo del Bloqueo:** Falta de capacidad
   - **Fecha Estimada de Finalización:** 2026-06-02

## DA-03 - Penalizacion potencial con documento contractual

Veredicto: **PARTIAL**

Preguntas:

- Dame los pedidos que puedan generar penalizacion y dime por que.

Incidencias:

- tools: sources distintas: estable=['ERP', 'Produccion', 'Documentos'], tools=['Documentos', 'Produccion', 'ERP', 'Memoria']
- tools: tool_calls distintas: estable=['ERPTool', 'ProductionAPITool', 'ProductionAPITool', 'ProductionAPITool', 'ProductionAPITool', 'ProductionAPITool', 'DocumentRAGTool'], tools=['DocumentRAGTool', 'ProductionAPITool', 'ProductionAPITool', 'ProductionQueryTool', 'ERPQueryTool', 'DocumentRAGTool', 'DocumentRAGTool', 'DocumentRAGTool', 'MemoryTool', 'ERPTool', 'DocumentRAGTool', 'DocumentRAGTool', 'DocumentRAGTool', 'ERPQueryTool', 'ERPQueryTool', 'ERPQueryTool']

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
| 10252 | Alfreds Futterkiste | bloqueado (Falta de material) | No aplicable segun la documentacion consultada, ya que la falta de material es una exclusion de penalizacion. |
| 10255 | Alfreds Futterkiste | finalizado | No aplicable; consta enviado antes del plazo requerido. |
| 10301 | Ana Trujillo Emparedados y helados | retrasado (Averia en linea de produccion) | No aplicable segun la documentacion consultada, ya que una averia en linea de produccion es una exclusion de penalizacion. |
| 10312 | Bon app | bloqueado (Falta de capacidad) | No aplicable segun la documentacion consultada, ya que la falta de capacidad es una exclusion de penalizacion. |

El principal punto de atencion es el seguimiento operativo de los pedidos bloqueados, retrasados o pendientes de datos antes de comunicar una penalizacion.

Respuesta Deep Agents tools:

- status: `completed`
- sources: `['Documentos', 'Produccion', 'ERP', 'Memoria']`
- tools: `['DocumentRAGTool', 'ProductionAPITool', 'ProductionAPITool', 'ProductionQueryTool', 'ERPQueryTool', 'DocumentRAGTool', 'DocumentRAGTool', 'DocumentRAGTool', 'MemoryTool', 'ERPTool', 'DocumentRAGTool', 'DocumentRAGTool', 'DocumentRAGTool', 'ERPQueryTool', 'ERPQueryTool', 'ERPQueryTool']`
- fallbacks: `[]`
- answer: Basándome en las consultas realizadas en el ERP, el sistema de producción y los documentos contractuales indexados (*Contrato marco de logística 2026* y *Anexo de penalizaciones y SLA*), **ninguno de los pedidos actuales puede generar una penalización económica**.

A continuación se detalla el análisis de cada uno de los 5 pedidos registrados en el sistema:

---

### 1. Pedido 10248
* **Cliente:** Alfreds Futterkiste (`ALFKI`)
* **Importe:** 440.00 €
* **Fecha Requerida (ERP):** 2026-05-20
* **Estado ERP:** Pendiente (`pending`)
* **Estado de Producción:** En curso (`in_progress`) sin incidencias registradas, con fecha estimada de finalización para el **2026-05-22**.
* **Análisis Contractual:** Aunque la fecha requerida por el cliente era el 20 de mayo de 2026, el pedido todavía se encuentra en proceso de fabricación. Según el *Contrato marco de logística 2026 (Página 1)*: *"El plazo logístico empieza cuando producción registra la liberación final"*. Al no haberse producido la liberación de producción, el plazo del operador logístico no ha comenzado a computar. Por ende, no es un retraso imputable a logística y **no genera penalización**.

### 2. Pedido 10252
* **Cliente:** Alfreds Futterkiste (`ALFKI`)
* **Importe:** 1.863.00 €
* **Fecha Requerida (ERP):** 2026-05-25
* **Estado ERP:** Pendiente (`pending`)
* **Estado de Producción:** Bloqueado (`blocked`) con fecha estimada de finalización para el **2026-05-30**.
* **Motivo de Bloqueo:** Falta de material.
* **Análisis Contractual:** El *Anexo de penalizaciones y SLA (Página 3 - Exclusiones)* especifica de forma explícita: *"No se aplican penalizaciones cuando el retraso procede de bloqueo de producción, falta de material..."*. Al estar el retraso justificado por una rotura de stock de materias primas en la planta, el pedido queda exento y **no genera penalización**.

### 3. Pedido 10255
* **Cliente:** Alfreds Futterkiste (`ALFKI`)
* **Importe:** 2.490.00 €
* **Fecha Requerida (ERP):** 2026-05-30
* **Estado ERP:** Enviado (`shipped`) el **2026-05-15**.
* **Estado de Producción:** Finalizado (`finished`) el 2026-05-14.
* **Análisis Contractual:** El pedido fue entregado y procesado mucho antes del límite acordado con el cliente (30 de mayo de 2026). Cumple plenamente con el SLA, por lo que **no genera penalización**.

### 4. Pedido 10301
* **Cliente:** Ana Trujillo Emparedados y helados (`ANATR`)
* **Importe:** 920.00 €
* **Fecha Requerida (ERP):** 2026-06-01
* **Estado ERP:** Pendiente (`pending`)
* **Estado de Producción:** Retrasado (`delayed`) con fecha estimada de finalización para el **2026-06-03**.
* **Motivo de Retraso:** Avería en línea de producción.
* **Análisis Contractual:** Tanto el *Anexo de penalizaciones y SLA (Página 3)* como el *Contrato marco de logística 2026 (Página 2)* contemplan las averías mecánicas como eximentes de responsabilidad: *"No se aplican penalizaciones cuando el retraso procede de... avería de línea"*. Al ser una incidencia técnica interna del proceso productivo, **no genera penalización**.

### 5. Pedido 10312
* **Cliente:** Bon app (`BONAP`)
* **Importe:** 1.210.00 €
* **Fecha Requerida (ERP):** 2026-06-08
* **Estado ERP:** Pendiente (`pending`)
* **Estado de Producción:** Bloqueado (`blocked`) con fecha estimada de finalización para el **2026-06-02**.
* **Motivo de Bloqueo:** Falta de capacidad.
* **Análisis Contractual:** Al igual que en los casos anteriores, las limitaciones de capacidad industrial de la fábrica se encuentran excluidas de las penalizaciones comerciales. El *Anexo de penalizaciones y SLA (Página 3)* determina que: *"No se aplican penalizaciones cuando el retraso procede de... falta de capacidad"*. Por consiguiente, **no genera penalización**.

## DA-04 - Follow-up conversacional con conversation_id

Veredicto: **PARTIAL**

Preguntas:

- Que pedidos pendientes tiene el cliente ALFKI?
- Y en que estado estan?

Incidencias:

- tools: tool_calls distintas: estable=['MemoryTool', 'ERPTool', 'ProductionAPITool', 'ProductionAPITool'], tools=['MemoryTool', 'ERPQueryTool', 'ProductionAPITool']

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
- answer: Los pedidos pendientes del cliente **Alfreds Futterkiste (ALFKI)** se encuentran en los siguientes estados:

*   **Pedido ID: 10248**
    *   **Estado ERP:** `pending` (Pendiente)
    *   **Estado de Producción:** `in_progress` (En curso)
    *   **Fecha estimada de finalización de producción:** 2026-05-22
    *   **Importe:** 440.00 €

*   **Pedido ID: 10252**
    *   **Estado ERP:** `pending` (Pendiente)
    *   **Estado de Producción:** `blocked` (Bloqueado)
    *   **Motivo de bloqueo:** Falta de material
    *   **Fecha estimada de finalización de producción:** 2026-05-30
    *   **Importe:** 1863.00 €

## DA-05 - Pregunta documental sin evidencia

Veredicto: **PARTIAL**

Preguntas:

- Que dice el contrato sobre criptomonedas?

Incidencias:

- tools: tool_calls distintas: estable=['DocumentRAGTool'], tools=['DocumentRAGTool', 'DocumentRAGTool', 'DocumentRAGTool', 'DocumentRAGTool', 'DocumentRAGTool', 'DocumentRAGTool', 'DocumentRAGTool', 'DocumentRAGTool', 'DocumentRAGTool', 'DocumentRAGTool', 'DocumentRAGTool', 'DocumentRAGTool', 'DocumentRAGTool', 'DocumentRAGTool', 'DocumentRAGTool']

Respuesta estable:

- status: `completed`
- sources: `['Documentos']`
- tools: `['DocumentRAGTool']`
- fallbacks: `[]`
- answer: Con los datos disponibles, el contrato no menciona nada sobre criptomonedas.

Respuesta Deep Agents sidecar:

- status: `completed`
- sources: `['Documentos']`
- tools: `['DocumentRAGTool']`
- fallbacks: `[]`
- answer: Con los datos disponibles, el contrato marco de logística 2026 y su anexo de penalizaciones no mencionan nada sobre criptomonedas.

Respuesta Deep Agents tools:

- status: `completed`
- sources: `['Documentos']`
- tools: `['DocumentRAGTool', 'DocumentRAGTool', 'DocumentRAGTool', 'DocumentRAGTool', 'DocumentRAGTool', 'DocumentRAGTool', 'DocumentRAGTool', 'DocumentRAGTool', 'DocumentRAGTool', 'DocumentRAGTool', 'DocumentRAGTool', 'DocumentRAGTool', 'DocumentRAGTool', 'DocumentRAGTool', 'DocumentRAGTool']`
- fallbacks: `[]`
- answer: Tras realizar una búsqueda exhaustiva en los documentos disponibles a través de las consultas documentales, se han analizado las siguientes fuentes:

* **v2_contrato_marco_logistica_2026.pdf** (Páginas 1, 2, 3 y 4)
* **v2_anexo_penalizaciones_sla.pdf** (Páginas 1, 2, 3 y 4)
* **v2_procedimiento_produccion_bloqueos.pdf** (Páginas 1, 2, 3 y 4)
* **v2_condiciones_comerciales_northwind.pdf** (Páginas 1, 2, 3 y 4)

**Resultado:**
Ninguno de los documentos mencionados contiene referencias, cláusulas o menciones sobre "criptomonedas", "cripto", "bitcoin", "divisas" u otros medios de pago digitales similares.

**Conclusión:**
De acuerdo con las reglas de trazabilidad e insuficiencia de información especificadas en el documento *v2_condiciones_comerciales_northwind.pdf* (Página 4, Marcador de validación: `COM-V2-P04`), al no existir evidencia contractual o documental sobre esta materia en el repositorio, se declara la respuesta como:

**insufficient_context**
