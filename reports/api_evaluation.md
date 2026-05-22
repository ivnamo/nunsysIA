# Evaluación automática Docker/API

## Configuración
- Fecha: 2026-05-22 20:53:54
- Comando Docker usado: `docker compose -f docker-compose.yml -f docker-compose.secrets.yml --profile eval up --build evaluator`
- Base URL: `http://backend:8000`
- Endpoint: `/api/query`
- Mode: `deepagent`
- Servicios Docker levantados: `backend`, `production-api`, `chromadb` y servicio `evaluator` con profile `eval`; `chainlit` no se usa en esta evaluación.
- Total preguntas: 10
- Respuestas crudas: `reports/raw_responses.json`

## Resumen ejecutivo
- Puntuación media: 24.3/25
- Veredicto global: Excelente: entrega solida para evaluacion tecnica.
- Riesgos principales:
  - Pregunta 6: punto mas debil relativo con 22/25.
  - Pregunta 7: punto mas debil relativo con 22/25.
  - Pregunta 5: punto mas debil relativo con 24/25.
- Mejoras prioritarias:
  - Ampliar el reasoning de respuestas RAG para explicar pasos y logica, no solo la fuente consultada.
  - Revisar prompts/casos RAG para cubrir todos los conceptos esperados en contrato y penalizaciones.

## Estado Docker
- Resultado de docker compose config: OK: salida disponible en `reports/docker_compose_config.txt` (383 lineas).
- Resultado de healthcheck: OK HTTP 200 en http://backend:8000/health tras 1 intento(s).
- Errores relevantes de logs si existen: No se detectan errores HTTP/logicos graves en la ejecucion HTTP.

## Tabla resumen
| ID | Pregunta | HTTP | Score | Veredicto breve |
|----|----------|------|-------|-----------------|
| 1 | ¿Qué pedidos pendientes tiene el cliente ALFKI y en qué estado de producción están? | 200 | 25/25 | Excelente, nivel entrega solida |
| 2 | ¿Qué pedidos están bloqueados y cuál es el motivo? | 200 | 25/25 | Excelente, nivel entrega solida |
| 3 | ¿Qué clientes tienen pedidos retrasados por problemas de producción? | 200 | 25/25 | Excelente, nivel entrega solida |
| 4 | Dame un resumen del estado de los pedidos de este mes | 200 | 25/25 | Excelente, nivel entrega solida |
| 5 | ¿Qué dice este documento sobre plazos de entrega? | 200 | 24/25 | Excelente, nivel entrega solida |
| 6 | Resume los puntos clave del contrato | 200 | 22/25 | Excelente, nivel entrega solida |
| 7 | ¿Hay alguna penalización por retrasos? | 200 | 22/25 | Excelente, nivel entrega solida |
| 8a | ¿Qué pedidos pendientes tiene el cliente ALFKI y en qué estado de producción están? | 200 | 25/25 | Excelente, nivel entrega solida |
| 8b | ¿Y cuáles de esos pedidos están bloqueados? | 200 | 25/25 | Excelente, nivel entrega solida |
| 8c | ¿Cuál es el impacto económico de esos? | 200 | 25/25 | Excelente, nivel entrega solida |

## Evaluación detallada

### Pregunta 1
**Pregunta enviada:**

¿Qué pedidos pendientes tiene el cliente ALFKI y en qué estado de producción están?

**Payload:**

```json
{
  "question": "¿Qué pedidos pendientes tiene el cliente ALFKI y en qué estado de producción están?",
  "conversation_id": "eval-1-a5b869c5",
  "mode": "deepagent"
}
```

**Respuesta visible para usuario (extracto):**

El cliente ALFKI tiene 2 pedidos pendientes:

| Pedido | Estado ERP | Estado produccion | Observacion |
| --- | --- | --- | --- |
| 10248 | pendiente | en curso | sin bloqueo informado |
| 10252 | pendiente | bloqueado | Falta de material |

**Fuentes devueltas:**

ERP, Produccion

**Reasoning devuelto:**

- Consulta ERP de pedidos pendientes
- Consulta API de produccion para pedidos referenciados

**Puntuación:**

- Cumplimiento funcional: 5/5
- Calidad de información: 5/5
- Trazabilidad: 5/5
- Redacción humana: 5/5
- Robustez técnica: 5/5
- Total: 25/25 (Excelente, nivel entrega solida)

**Problemas detectados:**

- Sin problemas graves detectados por heuristica.

**Criterio esperado por evaluador:**

Debe listar pedidos pendientes de ALFKI y cruzarlos con estado de produccion.

### Pregunta 2
**Pregunta enviada:**

¿Qué pedidos están bloqueados y cuál es el motivo?

**Payload:**

```json
{
  "question": "¿Qué pedidos están bloqueados y cuál es el motivo?",
  "conversation_id": "eval-2-168f2f62",
  "mode": "deepagent"
}
```

**Respuesta visible para usuario (extracto):**

Estos son los estados de produccion de los pedidos referenciados:

| Pedido | Cliente | Estado | Motivo |
| --- | --- | --- | --- |
| 10252 | ALFKI - Alfreds Futterkiste | bloqueado | Falta de material |
| 10312 | BONAP - Bon app | bloqueado | Falta de capacidad |

**Fuentes devueltas:**

Produccion, ERP

**Reasoning devuelto:**

- Consulta API de produccion por estado
- Consulta ERP de cliente para pedido 10252
- Consulta ERP de cliente para pedido 10312
- Consulta Produccion mediante filtros seguros
- Consulta API de produccion para pedidos referenciados
- Consulta ERP mediante filtros seguros

**Puntuación:**

- Cumplimiento funcional: 5/5
- Calidad de información: 5/5
- Trazabilidad: 5/5
- Redacción humana: 5/5
- Robustez técnica: 5/5
- Total: 25/25 (Excelente, nivel entrega solida)

**Problemas detectados:**

- Sin problemas graves detectados por heuristica.

**Criterio esperado por evaluador:**

Debe listar pedidos bloqueados, motivo y contexto ERP del pedido/cliente.

### Pregunta 3
**Pregunta enviada:**

¿Qué clientes tienen pedidos retrasados por problemas de producción?

**Payload:**

```json
{
  "question": "¿Qué clientes tienen pedidos retrasados por problemas de producción?",
  "conversation_id": "eval-3-49ca4b64",
  "mode": "deepagent"
}
```

**Respuesta visible para usuario (extracto):**

Estos son los estados de produccion de los pedidos referenciados:

| Pedido | Cliente | Estado | Motivo |
| --- | --- | --- | --- |
| 10301 | ANATR - Ana Trujillo Emparedados y helados | retrasado | Averia en linea de produccion |

**Fuentes devueltas:**

Produccion, ERP

**Reasoning devuelto:**

- Consulta API de produccion por estado
- Consulta ERP de cliente para pedido 10301
- Consulta ERP mediante filtros seguros

**Puntuación:**

- Cumplimiento funcional: 5/5
- Calidad de información: 5/5
- Trazabilidad: 5/5
- Redacción humana: 5/5
- Robustez técnica: 5/5
- Total: 25/25 (Excelente, nivel entrega solida)

**Problemas detectados:**

- Sin problemas graves detectados por heuristica.

**Criterio esperado por evaluador:**

Debe identificar pedidos retrasados y clientes ERP asociados.

### Pregunta 4
**Pregunta enviada:**

Dame un resumen del estado de los pedidos de este mes

**Payload:**

```json
{
  "question": "Dame un resumen del estado de los pedidos de este mes",
  "conversation_id": "eval-4-02bb9fd2",
  "mode": "deepagent"
}
```

**Respuesta visible para usuario (extracto):**

En mayo de 2026 hay 5 pedidos ERP. Distribucion por estado de produccion: bloqueado: 2, en curso: 1, finalizado: 1, retrasado: 1.

| Pedido | Estado ERP | Estado produccion |
| --- | --- | --- |
| 10248 | pendiente | en curso |
| 10252 | pendiente | bloqueado |
| 10255 | enviado | finalizado |
| 10301 | pendiente | retrasado |
| 10312 | pendiente | bloqueado |

Periodo auditado: 2026-05.

**Fuentes devueltas:**

ERP, Produccion

**Reasoning devuelto:**

- Consulta ERP de pedidos por mes
- Consulta API de produccion para pedidos referenciados
- Consulta ERP mediante filtros seguros
- Consulta ERP mediante filtros seguros

**Puntuación:**

- Cumplimiento funcional: 5/5
- Calidad de información: 5/5
- Trazabilidad: 5/5
- Redacción humana: 5/5
- Robustez técnica: 5/5
- Total: 25/25 (Excelente, nivel entrega solida)

**Problemas detectados:**

- Sin problemas graves detectados por heuristica.

**Criterio esperado por evaluador:**

Debe resumir pedidos del mes actual de prueba y distribucion de estados.

### Pregunta 5
**Pregunta enviada:**

¿Qué dice este documento sobre plazos de entrega?

**Payload:**

```json
{
  "question": "¿Qué dice este documento sobre plazos de entrega?",
  "conversation_id": "eval-5-194e415b",
  "mode": "deepagent"
}
```

**Respuesta visible para usuario (extracto):**

De acuerdo con la documentación contractual de logística para 2026, las condiciones relativas a los plazos de entrega se estructuran de la siguiente manera:

* **Plazos de Entrega Ordinarios:**
  * **Pedidos estándar:** Deben entregarse en un plazo máximo de **5 días laborables** a partir de la liberación de producción.
  * **Pedidos urgentes:** El plazo máximo de entrega es de **48 horas** desde su liberación.

* **Cálculo de Plazos y Calendario:**
  * Se excluyen del cómputo de días laborables los sábados, domingos, festivos nacionales y festivos de la provincia de destino donde el transportista no ofrezca servicio.
  * Si la salida del pedido ocurre después de las **14:00 horas**, el cómputo se iniciará el siguiente día laborable.
  * En envíos de exportación, la tramitación de aduanas y documentación sanitaria puede pausar temporalmente el contador de días, siempre que quede debidamente registrado en el expediente.

* **Entregas Parciales:**
  * Solo se consideran válidas para el cumplimiento del plazo si comercial aprueba la parcialidad y el cliente acepta la documentación por escrito. En caso contrario, el pedido se considerará pendiente hasta que se complete la entrega total

**Fuentes devueltas:**

Documentos

**Reasoning devuelto:**

- Consulta RAG documental con chunks recuperados

**Puntuación:**

- Cumplimiento funcional: 5/5
- Calidad de información: 5/5
- Trazabilidad: 4/5
- Redacción humana: 5/5
- Robustez técnica: 5/5
- Total: 24/25 (Excelente, nivel entrega solida)

**Problemas detectados:**

- reasoning minimo: explica la fuente, pero no desarrolla pasos/lógica con suficiente detalle.

**Criterio esperado por evaluador:**

Debe usar RAG y redactar una respuesta humana sobre plazos documentales.

### Pregunta 6
**Pregunta enviada:**

Resume los puntos clave del contrato

**Payload:**

```json
{
  "question": "Resume los puntos clave del contrato",
  "conversation_id": "eval-6-51d33203",
  "mode": "deepagent"
}
```

**Respuesta visible para usuario (extracto):**

A continuación se presentan los puntos clave regulados en el Contrato Marco de Logística 2026:

*   **Objeto del contrato**: Regula los procesos de preparación, expedición, entrega y cierre documental de todos los pedidos comerciales durante el año 2026 (estándar, urgentes, entregas parciales y con salidas desde almacenes centrales o externos).
*   **Definición de pedidos**:
    *   **Estándar**: Orden ERP liberada por producción sin prioridad comercial especial.
    *   **Urgente**: Orden de prioridad alta que debe entregarse en un plazo máximo de 48 horas.
    *   **Bloqueado**: Detenido temporalmente por producción debido a fallas de material, capacidad, control de calidad o aprobaciones pendientes.
*   **Inicio del plazo logístico**: Comienza una vez que producción registra la liberación final y el ERP tiene la dirección de entrega y el contacto registrados.
*   **Plazos ordinarios de entrega**:
    *   **Pedidos estándar**: Máximo 5 días laborables desde la liberación.
    *   **Pedidos urgentes**: Máximo 48 horas.
    *   **Entregas parciales**: Computan como cumplimiento solo si el área comercial las aprueba y el cliente acepta la documentación.
*   **Reglas del calendario a

**Fuentes devueltas:**

Documentos

**Reasoning devuelto:**

- Consulta RAG documental con chunks recuperados

**Puntuación:**

- Cumplimiento funcional: 4/5
- Calidad de información: 4/5
- Trazabilidad: 4/5
- Redacción humana: 5/5
- Robustez técnica: 5/5
- Total: 22/25 (Excelente, nivel entrega solida)

**Problemas detectados:**

- Solo se cumplen parcialmente los terminos funcionales esperados.
- La informacion concreta esperada aparece solo de forma parcial.
- reasoning minimo: explica la fuente, pero no desarrolla pasos/lógica con suficiente detalle.

**Criterio esperado por evaluador:**

Debe resumir el contrato con evidencia documental y sin pegar chunks.

### Pregunta 7
**Pregunta enviada:**

¿Hay alguna penalización por retrasos?

**Payload:**

```json
{
  "question": "¿Hay alguna penalización por retrasos?",
  "conversation_id": "eval-7-ee9082a9",
  "mode": "deepagent"
}
```

**Respuesta visible para usuario (extracto):**

Sí, existen penalizaciones por retrasos bajo condiciones específicas y según el tipo de pedido:

* **Pedidos Estándar** (plazo de entrega de 5 días laborables desde la liberación): Se aplica una penalización del 2% si el retraso imputable supera los 2 días laborables, la cual asciende al 5% si el retraso es superior a 5 días laborables.
* **Pedidos Urgentes** (plazo de entrega de 48 horas desde la liberación): Se aplica una penalización del 3% desde el primer día de retraso imputable.

**Condiciones para su aplicación:**
* El retraso debe ser imputable al operador logístico.
* Debe existir evidencia completa registrada en el ERP (incluyendo el importe real del pedido extraído de sus líneas de detalle), datos de producción y la prueba de entrega (POD). En caso de no poder demostrarse claramente la causa y responsabilidad del retraso, se aplica la regla de insuficiencia de pruebas y no se procede con ninguna penalización.

**Fuentes devueltas:**

Documentos

**Reasoning devuelto:**

- Consulta RAG documental con chunks recuperados

**Puntuación:**

- Cumplimiento funcional: 4/5
- Calidad de información: 4/5
- Trazabilidad: 4/5
- Redacción humana: 5/5
- Robustez técnica: 5/5
- Total: 22/25 (Excelente, nivel entrega solida)

**Problemas detectados:**

- Solo se cumplen parcialmente los terminos funcionales esperados.
- La informacion concreta esperada aparece solo de forma parcial.
- reasoning minimo: explica la fuente, pero no desarrolla pasos/lógica con suficiente detalle.

**Criterio esperado por evaluador:**

Debe usar documentos para explicar condiciones de penalizacion por retrasos.

### Pregunta 8a
**Pregunta enviada:**

¿Qué pedidos pendientes tiene el cliente ALFKI y en qué estado de producción están?

**Payload:**

```json
{
  "question": "¿Qué pedidos pendientes tiene el cliente ALFKI y en qué estado de producción están?",
  "conversation_id": "eval-memory-alfki-f5f21237",
  "mode": "deepagent"
}
```

**Respuesta visible para usuario (extracto):**

El cliente ALFKI tiene 2 pedidos pendientes:

| Pedido | Estado ERP | Estado produccion | Observacion |
| --- | --- | --- | --- |
| 10248 | pendiente | en curso | sin bloqueo informado |
| 10252 | pendiente | bloqueado | Falta de material |

**Fuentes devueltas:**

ERP, Produccion

**Reasoning devuelto:**

- Consulta ERP de pedidos pendientes
- Consulta API de produccion para pedidos referenciados

**Puntuación:**

- Cumplimiento funcional: 5/5
- Calidad de información: 5/5
- Trazabilidad: 5/5
- Redacción humana: 5/5
- Robustez técnica: 5/5
- Total: 25/25 (Excelente, nivel entrega solida)

**Problemas detectados:**

- Sin problemas graves detectados por heuristica.

**Criterio esperado por evaluador:**

Primer turno de memoria: debe fijar el contexto de pedidos ALFKI.

### Pregunta 8b
**Pregunta enviada:**

¿Y cuáles de esos pedidos están bloqueados?

**Payload:**

```json
{
  "question": "¿Y cuáles de esos pedidos están bloqueados?",
  "conversation_id": "eval-memory-alfki-f5f21237",
  "mode": "deepagent"
}
```

**Respuesta visible para usuario (extracto):**

Estos son los estados de produccion de los pedidos referenciados:

| Pedido | Cliente | Estado | Motivo |
| --- | --- | --- | --- |
| 10252 | ALFKI - Alfreds Futterkiste | bloqueado | Falta de material |

**Fuentes devueltas:**

Memoria, Produccion, ERP

**Reasoning devuelto:**

- Consulta memoria conversacional
- Consulta API de produccion para pedidos referenciados
- Consulta ERP de cliente para pedido 10252
- Consulta Produccion mediante filtros seguros

**Puntuación:**

- Cumplimiento funcional: 5/5
- Calidad de información: 5/5
- Trazabilidad: 5/5
- Redacción humana: 5/5
- Robustez técnica: 5/5
- Total: 25/25 (Excelente, nivel entrega solida)

**Problemas detectados:**

- Sin problemas graves detectados por heuristica.

**Criterio esperado por evaluador:**

Segundo turno: debe resolver 'esos pedidos' usando conversation_id.

### Pregunta 8c
**Pregunta enviada:**

¿Cuál es el impacto económico de esos?

**Payload:**

```json
{
  "question": "¿Cuál es el impacto económico de esos?",
  "conversation_id": "eval-memory-alfki-f5f21237",
  "mode": "deepagent"
}
```

**Respuesta visible para usuario (extracto):**

Con los datos disponibles, el impacto economico del pedido referenciado es 10252: 1863.00.

**Fuentes devueltas:**

Memoria, ERP

**Reasoning devuelto:**

- Consulta memoria conversacional
- Consulta ERP de importe para pedido 10252
- Consulta ERP mediante filtros seguros

**Puntuación:**

- Cumplimiento funcional: 5/5
- Calidad de información: 5/5
- Trazabilidad: 5/5
- Redacción humana: 5/5
- Robustez técnica: 5/5
- Total: 25/25 (Excelente, nivel entrega solida)

**Problemas detectados:**

- Sin problemas graves detectados por heuristica.

**Criterio esperado por evaluador:**

Tercer turno: debe calcular impacto economico de los bloqueados previos.
