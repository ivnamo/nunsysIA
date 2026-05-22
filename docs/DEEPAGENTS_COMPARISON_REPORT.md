# Deep Agents Comparison Report

Fecha de ejecucion: 2026-05-22 18:46:00

Resultado global: PASS=5, PARTIAL=0, FAIL=0, BLOCKER=0.

Runtime:

- Workflow estable: `QueryWorkflowService`.
- Flujo experimental: `DeepAgentsQueryService`.
- Deep Agents usa el workflow estable como tool auditable.
- Modelo Deep Agents: `DEEPAGENTS_MODEL` o valor por defecto.

## DA-01 - ALFKI pendientes y estado de produccion

Veredicto: **PASS**

Preguntas:

- Que pedidos pendientes tiene el cliente ALFKI y en que estado de produccion estan?

Incidencias:

- Sin divergencias criticas.

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

Respuesta Deep Agents:

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

Respuesta Deep Agents:

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

## DA-03 - Penalizacion potencial con documento contractual

Veredicto: **PASS**

Preguntas:

- Dame los pedidos que puedan generar penalizacion y dime por que.

Incidencias:

- Sin divergencias criticas.

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

Respuesta Deep Agents:

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

## DA-04 - Follow-up conversacional con conversation_id

Veredicto: **PASS**

Preguntas:

- Que pedidos pendientes tiene el cliente ALFKI?
- Y en que estado estan?

Incidencias:

- Sin divergencias criticas.

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

Respuesta Deep Agents:

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

Respuesta Deep Agents:

- status: `completed`
- sources: `['Documentos']`
- tools: `['DocumentRAGTool']`
- fallbacks: `[]`
- answer: Con los datos disponibles, el contrato marco de logística 2026 y su anexo de penalizaciones no mencionan información sobre criptomonedas.
