# Trazabilidad

## Que es una traza

Una traza es el registro estructurado de lo que hizo el sistema para responder una pregunta: fuentes consultadas, tools ejecutadas, argumentos principales, resultado resumido, errores y estado final.

La traza debe servir para auditar el comportamiento sin exponer razonamiento interno sensible.

## Campos por Tool Call

Cada llamada a tool debe guardar:

- `tool`: nombre de la tool.
- `args`: argumentos relevantes y sanitizados.
- `status`: `success`, `error` o `skipped`.
- `output_summary`: resumen breve del resultado.
- `error`: resumen del error si aplica.
- `duration_ms`: duracion si esta disponible.
- `source`: fuente asociada: `ERP`, `Produccion`, `Documentos` o `Memoria`.

## Campos Devueltos al Usuario

La API debe devolver:

- `answer`
- `sources`
- `reasoning`
- `tool_calls`
- `status`
- `confidence` cuando sea posible

## Reasoning Visible vs Razonamiento Interno

Reasoning visible:

- resumen corto de pasos ejecutados;
- fuentes usadas;
- logica de combinacion de datos;
- apto para auditoria.

Razonamiento interno:

- deliberacion paso a paso del modelo;
- chain-of-thought;
- prompts internos;
- contenido sensible.

El razonamiento interno no debe devolverse al usuario.

## Ejemplo ERP + Produccion

```json
{
  "sources": ["ERP", "Produccion"],
  "reasoning": [
    "Se consulto ERP para obtener pedidos pendientes del cliente ALFKI.",
    "Se consulto produccion para obtener el estado de esos pedidos.",
    "Se fusionaron importes ERP con estados productivos."
  ],
  "tool_calls": [
    {
      "tool": "ERPTool",
      "args": {"customer_id": "ALFKI"},
      "status": "success",
      "output_summary": "2 pedidos pendientes encontrados",
      "source": "ERP"
    },
    {
      "tool": "ProductionAPITool",
      "args": {"order_ids": ["10248", "10252"]},
      "status": "success",
      "output_summary": "1 pedido en fabricacion, 1 bloqueado",
      "source": "Produccion"
    }
  ],
  "status": "completed"
}
```

## Ejemplo RAG

```json
{
  "sources": ["Documentos"],
  "reasoning": [
    "Se recuperaron chunks relevantes del documento contrato.pdf.",
    "La respuesta se genero solo con el contexto recuperado."
  ],
  "tool_calls": [
    {
      "tool": "DocumentRAGTool",
      "args": {"query": "penalizacion por retrasos"},
      "status": "success",
      "output_summary": "3 chunks recuperados de contrato.pdf",
      "source": "Documentos"
    }
  ],
  "status": "completed"
}
```

## Estados Posibles

- `completed`: respuesta completa.
- `partial_answer`: respuesta parcial por fuente no disponible o informacion incompleta.
- `insufficient_context`: no hay contexto suficiente para responder sin inventar.
- `tool_error`: fallo controlado de una tool.
- `failed`: fallo no recuperable.

## Reglas de Seguridad

- Sanitizar argumentos y errores.
- No incluir credenciales.
- No incluir connection strings.
- No incluir prompts internos.
- No incluir chain-of-thought.
