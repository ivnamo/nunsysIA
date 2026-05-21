from __future__ import annotations

import textwrap
from pathlib import Path


PAGE_BREAK = "---PAGE_BREAK---"


SAMPLE_DOCUMENTS: dict[str, str] = {
    "contrato_marco_logistica_2026.pdf": """
Contrato marco de logistica 2026

Objeto del contrato:
Este contrato regula la preparacion, expedicion y entrega de pedidos comerciales
para clientes ERP durante el ejercicio 2026. El operador logistico debe coordinar
su actividad con el estado de produccion y con la fecha requerida del pedido.

Plazos de entrega:
Los pedidos standard deben entregarse en un plazo maximo de 5 dias laborables
desde la liberacion de produccion. Los pedidos urgentes deben entregarse en un
plazo maximo de 48 horas desde la liberacion. Si el pedido esta bloqueado por
falta de material, el plazo no empieza a contar hasta que produccion desbloquee
la orden.

Trazabilidad:
Cada expedicion debe conservar referencia a order_id, cliente, fecha de salida,
transportista y estado final de entrega. El informe mensual debe separar pedidos
en curso, pedidos bloqueados, pedidos retrasados y pedidos finalizados.

Exclusiones:
El proveedor logistico no sera responsable de retrasos causados por fuerza mayor,
averia critica comunicada por produccion o datos ERP incompletos.
""",
    "anexo_penalizaciones_sla.pdf": """
Anexo de penalizaciones y SLA

Alcance:
Este anexo complementa el contrato marco de logistica 2026 y define penalizaciones
por incumplimiento de plazos de entrega cuando existe evidencia suficiente.

Penalizacion por retrasos:
Si un pedido standard se entrega mas de 2 dias laborables tarde por causa imputable
al operador logistico, se aplica una penalizacion del 2 por ciento del importe del
pedido. Si el retraso supera 5 dias laborables, la penalizacion sube al 5 por ciento.
Los pedidos urgentes tienen penalizacion del 3 por ciento desde el primer dia de
retraso imputable.

No aplicacion:
No se aplican penalizaciones cuando el retraso procede de bloqueo de produccion,
falta de material, falta de capacidad, averia de linea o cambios de prioridad
aprobados por direccion comercial.

Evidencia necesaria:
Para aplicar una penalizacion deben constar order_id, cliente, fecha prometida,
fecha real de entrega, causa del retraso y fuente responsable.
""",
    "procedimiento_produccion_bloqueos.pdf": """
Procedimiento operativo de produccion

Estados de produccion:
Una orden puede estar en in_progress, blocked, delayed o finished. El estado blocked
se usa cuando la orden no puede continuar por falta de material, falta de capacidad,
incidencia de calidad o aprobacion pendiente. El estado delayed se usa cuando la
orden continua abierta pero no llegara a la fecha estimada.

Motivos habituales de bloqueo:
Los motivos mas frecuentes son falta de material, falta de capacidad, incidencia
de calidad y mantenimiento no planificado. Cada bloqueo debe incluir order_id,
motivo, responsable y fecha estimada de desbloqueo.

Motivos habituales de retraso:
Los retrasos se clasifican como averia en linea de produccion, cambio de prioridad,
retrabajo por calidad o espera de validacion tecnica. El equipo de produccion debe
informar al ERP cuando el retraso afecta a un cliente prioritario.

Escalado:
Un pedido bloqueado mas de 72 horas debe escalarse a operaciones. Un pedido retrasado
con impacto en cliente debe comunicarse a comercial y logistica.
""",
    "politica_calidad_entregas.pdf": """
Politica de calidad para entregas a cliente

Objetivo:
Garantizar que los pedidos enviados al cliente cumplen calidad documental, calidad
de preparacion y trazabilidad de lote. La politica aplica a todos los pedidos ERP
con salida desde almacen central.

Control previo:
Antes de liberar un pedido, calidad valida lote, cantidad, documentacion y etiquetado.
Si aparece una incidencia de calidad, el pedido debe quedar bloqueado hasta que
produccion o calidad registren una resolucion.

Entrega y documentacion:
Cada entrega debe incluir albaran, referencia order_id y nombre de cliente. Las
entregas parciales requieren aprobacion comercial previa y deben quedar explicadas
en la traza de la respuesta.

Indicadores:
Los indicadores mensuales separan pedidos entregados a tiempo, pedidos retrasados,
pedidos bloqueados y pedidos con incidencia de calidad.
""",
    "condiciones_comerciales_northwind.pdf": """
Condiciones comerciales Northwind

Clientes y pedidos:
Cada cliente se identifica mediante customer_id ERP. Las consultas de negocio deben
usar datos del ERP para clientes, pedidos, fechas, estado ERP e importes. No se debe
inventar un cliente o pedido si no aparece en la base de datos.

Importes:
El importe de un pedido se calcula desde las lineas de pedido usando precio unitario,
cantidad y descuento. Las respuestas que hablen de impacto economico deben indicar
si el importe procede del ERP o si no existe evidencia suficiente.

Prioridad comercial:
Los pedidos de clientes prioritarios pueden adelantarse si produccion confirma
capacidad. Un pedido bloqueado por material no debe prometerse al cliente sin una
fecha estimada validada por produccion.

Trazabilidad obligatoria:
Toda respuesta de negocio debe indicar fuentes consultadas, pasos ejecutados y
tools utilizadas. El razonamiento visible debe ser un resumen auditable, no un
razonamiento interno sensible.
""",
    "v2_contrato_marco_logistica_2026.pdf": """
Contrato marco de logistica 2026 - version extendida
Pagina 1 de 4 - Alcance, definiciones y reglas base

Objeto:
Este documento regula la preparacion, expedicion, entrega y cierre documental de
pedidos comerciales durante 2026. Aplica a pedidos standard, pedidos urgentes,
entregas parciales y pedidos con salida desde almacen central o almacen externo.

Definiciones:
Pedido standard significa una orden ERP liberada por produccion sin prioridad
comercial especial. Pedido urgente significa una orden marcada por direccion
comercial con prioridad alta y fecha requerida menor o igual a 48 horas. Pedido
bloqueado significa que produccion ha detenido la orden por falta de material,
falta de capacidad, incidencia de calidad o aprobacion pendiente.

Regla de inicio de plazo:
El plazo logistico empieza cuando produccion registra la liberacion final y el ERP
contiene direccion de entrega, contacto de cliente, lineas preparables y fecha
requerida. Si falta cualquiera de estos datos, el plazo queda en espera documental.

Marcador de validacion: CM-V2-P01. Esta pagina debe recuperarse para preguntas
sobre alcance, definiciones o inicio del plazo logistico.
---PAGE_BREAK---
Contrato marco de logistica 2026 - version extendida
Pagina 2 de 4 - Plazos, calendarios y excepciones operativas

Plazos ordinarios:
Los pedidos standard deben entregarse en un plazo maximo de 5 dias laborables
desde la liberacion de produccion. Los pedidos urgentes deben entregarse en un
plazo maximo de 48 horas. Las entregas parciales solo computan como cumplimiento
si comercial aprueba la parcialidad y el cliente acepta la documentacion.

Calendario aplicable:
El calculo de dias laborables excluye sabados, domingos, festivos nacionales y
festivos de la provincia de destino cuando el transportista no presta servicio.
Si el pedido sale despues de las 14:00, el primer dia computable sera el siguiente
dia laborable. En exportacion, aduanas y documentacion sanitaria pueden pausar el
contador si queda evidencia en el expediente.

Excepciones:
No existe incumplimiento logistico cuando el retraso procede de falta de material,
averia critica de linea, cambio de prioridad aprobado o datos ERP incompletos.
La excepcion debe citar order_id, causa, responsable y fecha de resolucion.

Marcador de validacion: CM-V2-P02. Esta pagina debe recuperarse para preguntas
sobre plazos standard, urgentes, calendarios y pausas del contador.
---PAGE_BREAK---
Contrato marco de logistica 2026 - version extendida
Pagina 3 de 4 - Trazabilidad por hitos y evidencias minimas

Hitos obligatorios:
Cada expedicion debe conservar cinco hitos: liberacion de produccion, preparacion
de almacen, salida de muelle, entrega al transportista y confirmacion de entrega.
Cada hito debe registrar fecha, usuario o sistema origen, estado anterior, estado
nuevo y observacion de negocio cuando el cambio afecte al cliente.

Evidencia minima:
Para responder consultas de auditoria deben constar order_id, customer_id,
cliente, fecha prometida, fecha real, transportista, estado ERP, estado de
produccion y causa de desviacion. Si una evidencia falta, la respuesta debe indicar
insufficient_context para esa parte y no completar el dato desde memoria.

Informe mensual:
El informe separa pedidos en curso, bloqueados, retrasados, finalizados, urgentes
y entregas parciales. Los pedidos con incidencia de calidad deben aparecer tanto
en el bloque logistico como en el bloque de calidad para conservar trazabilidad.

Marcador de validacion: CM-V2-P03. Esta pagina debe recuperarse para preguntas
sobre hitos, evidencias minimas o informes mensuales.
---PAGE_BREAK---
Contrato marco de logistica 2026 - version extendida
Pagina 4 de 4 - Casos de decision y resolucion de conflictos

Caso A:
Si el pedido esta liberado, tiene direccion completa y el transportista confirma
recogida, cualquier retraso posterior se analiza como responsabilidad logistica
salvo prueba de fuerza mayor. El responsable debe documentar la causa antes del
cierre mensual.

Caso B:
Si el pedido figura como blocked por falta de material, logistica no debe prometer
fecha de entrega. La fecha comunicable sera la fecha estimada de desbloqueo mas el
plazo logistico aplicable. Si no hay fecha estimada, se debe contestar que falta
contexto operacional suficiente.

Caso C:
Si comercial solicita adelantar un cliente prioritario, produccion debe confirmar
capacidad y calidad debe confirmar lote liberado. Sin ambas confirmaciones, el
cambio de prioridad no modifica el SLA ni genera penalizacion al operador.

Marcador de validacion: CM-V2-P04. Esta pagina debe recuperarse para preguntas
sobre responsabilidad, promesas al cliente o conflictos entre comercial,
produccion y logistica.
""",
    "v2_anexo_penalizaciones_sla.pdf": """
Anexo de penalizaciones y SLA - version extendida
Pagina 1 de 4 - Matriz de SLA y tipos de pedido

Alcance:
Este anexo complementa el contrato marco de logistica 2026 y define cuando puede
aplicarse una penalizacion economica. La penalizacion solo procede cuando existe
incumplimiento de plazo, causa imputable al operador logistico y evidencia completa
en ERP, produccion y prueba de entrega.

Matriz de SLA:
Pedido standard: 5 dias laborables desde liberacion final. Pedido urgente: 48
horas desde liberacion final. Entrega parcial aprobada: cumple solo la parte
aceptada por comercial. Entrega parcial no aprobada: se considera pendiente hasta
la entrega total o hasta que el cliente acepte el cambio por escrito.

Umbral economico:
Pedidos standard con mas de 2 dias laborables de retraso imputable tienen
penalizacion del 2 por ciento. Si superan 5 dias laborables, la penalizacion sube
al 5 por ciento. Pedidos urgentes tienen penalizacion del 3 por ciento desde el
primer dia de retraso imputable.

Marcador de validacion: SLA-V2-P01. Esta pagina debe recuperarse para preguntas
sobre matriz de SLA, tipos de pedido o porcentajes base.
---PAGE_BREAK---
Anexo de penalizaciones y SLA - version extendida
Pagina 2 de 4 - Evidencia necesaria y carga de la prueba

Evidencia obligatoria:
Para aplicar una penalizacion deben constar order_id, customer_id, importe del
pedido, fecha prometida, fecha real de entrega, fecha de liberacion, transportista,
causa del retraso y fuente responsable. El importe debe proceder de lineas ERP y
no de una estimacion manual.

Carga de la prueba:
El solicitante de la penalizacion debe aportar la prueba de entrega y el registro
de promesa de fecha. Logistica debe aportar tracking del transportista y eventos
de muelle. Produccion debe aportar estado de orden si hubo bloqueo, retraso,
retrabajo o incidencia de calidad.

Regla de insuficiencia:
Si no se puede demostrar la causa del retraso, el sistema debe informar que no hay
evidencia suficiente para asignar responsabilidad. No se debe aplicar penalizacion
solo porque la fecha real sea posterior a la fecha prometida.

Marcador de validacion: SLA-V2-P02. Esta pagina debe recuperarse para preguntas
sobre evidencia, carga de la prueba o insufficient_context.
---PAGE_BREAK---
Anexo de penalizaciones y SLA - version extendida
Pagina 3 de 4 - Exclusiones, pausas y casos no penalizables

Exclusiones:
No se aplican penalizaciones cuando el retraso procede de bloqueo de produccion,
falta de material, falta de capacidad, averia de linea, retrabajo por calidad,
espera de validacion tecnica, fuerza mayor, error de direccion aportado por el
cliente o cambio de prioridad aprobado por direccion comercial.

Pausas:
El contador de SLA queda pausado desde la fecha de bloqueo hasta la fecha de
desbloqueo registrada por produccion. En exportacion tambien puede pausarse por
documentacion aduanera o sanitaria incompleta, siempre que el expediente contenga
evento, responsable y fecha de resolucion.

Casos no penalizables:
Un pedido urgente no genera penalizacion si fue marcado urgente despues de la
liberacion y logistica ya habia planificado ruta standard. Una entrega rechazada
por el cliente por ausencia en domicilio no penaliza al operador si habia cita
confirmada.

Marcador de validacion: SLA-V2-P03. Esta pagina debe recuperarse para preguntas
sobre exclusiones, pausas de SLA o casos no penalizables.
---PAGE_BREAK---
Anexo de penalizaciones y SLA - version extendida
Pagina 4 de 4 - Calculo, aprobacion y auditoria mensual

Calculo:
La base de calculo es el importe neto del pedido despues de descuento comercial y
antes de impuestos. Si hay entrega parcial aprobada, la penalizacion se calcula
solo sobre la parte retrasada. Si el ERP no permite separar lineas entregadas y
pendientes, debe pedirse revision manual y no automatizar el importe.

Aprobacion:
Operaciones prepara la propuesta, comercial valida impacto en cliente y finanzas
aprueba la nota de cargo. Ninguna penalizacion se comunica al proveedor sin anexo
de evidencias, resumen de dias de retraso y causa imputable.

Auditoria:
El cierre mensual debe listar pedidos penalizados, pedidos descartados por
exclusion, pedidos sin evidencia suficiente y pedidos pendientes de aprobacion.
Cada fila debe enlazar con las fuentes consultadas.

Marcador de validacion: SLA-V2-P04. Esta pagina debe recuperarse para preguntas
sobre calculo economico, aprobacion o auditoria mensual.
""",
    "v2_procedimiento_produccion_bloqueos.pdf": """
Procedimiento operativo de produccion - version extendida
Pagina 1 de 4 - Estados, transiciones y propietarios

Estados:
Una orden puede estar en planned, in_progress, blocked, delayed, quality_hold,
released o finished. El estado blocked se usa cuando la orden no puede avanzar. El
estado delayed se usa cuando la orden sigue abierta pero no llegara a la fecha
estimada. El estado quality_hold se reserva para lote retenido por calidad.

Transiciones:
planned pasa a in_progress cuando se asigna linea. in_progress pasa a blocked si
falta material, capacidad o aprobacion. in_progress pasa a delayed cuando existe
riesgo confirmado de fecha. blocked solo puede pasar a in_progress o released con
fecha y responsable de desbloqueo.

Propietarios:
Produccion posee estados operativos, calidad posee quality_hold, comercial posee
prioridad de cliente y logistica consume la fecha liberada para calcular entrega.

Marcador de validacion: PROD-V2-P01. Esta pagina debe recuperarse para preguntas
sobre estados de produccion, transiciones o propietarios.
---PAGE_BREAK---
Procedimiento operativo de produccion - version extendida
Pagina 2 de 4 - Bloqueos y campos obligatorios

Motivos de bloqueo:
Los motivos validos son falta de material, falta de capacidad, incidencia de
calidad, mantenimiento no planificado, aprobacion tecnica pendiente y discrepancia
de receta o especificacion. No se debe usar blocked para retrasos menores si la
orden puede continuar fabricandose.

Campos obligatorios:
Cada bloqueo debe incluir order_id, linea de produccion, motivo, responsable,
fecha de inicio, fecha estimada de desbloqueo, impacto en cliente y comentario
operativo. Si falta fecha estimada, el sistema debe responder que no existe fecha
comunicable.

Actualizacion:
El responsable revisa bloqueos cada turno. Si la fecha estimada cambia, se registra
un nuevo evento en la traza y no se sobrescribe el evento anterior. La historia de
eventos debe permitir reconstruir la decision de cada dia.

Marcador de validacion: PROD-V2-P02. Esta pagina debe recuperarse para preguntas
sobre motivos de bloqueo, campos obligatorios o fecha comunicable.
---PAGE_BREAK---
Procedimiento operativo de produccion - version extendida
Pagina 3 de 4 - Retrasos, prioridades y comunicacion

Motivos de retraso:
Los retrasos se clasifican como averia en linea, cambio de prioridad, retrabajo
por calidad, espera de validacion tecnica, falta temporal de capacidad o secuencia
de fabricacion alterada. Delayed no implica que la orden este parada.

Prioridades:
Un cliente prioritario puede adelantar secuencia solo si produccion confirma
capacidad y calidad confirma lote liberable. Si adelantar un pedido retrasa otro
cliente, comercial debe aceptar el impacto y dejar rastro en el ERP.

Comunicacion:
Cuando delayed afecta a un cliente prioritario, produccion avisa a comercial y
logistica antes del cierre del turno. La comunicacion debe incluir nueva fecha
estimada, motivo y si el pedido puede enviarse parcial.

Marcador de validacion: PROD-V2-P03. Esta pagina debe recuperarse para preguntas
sobre delayed, prioridades o comunicacion a comercial y logistica.
---PAGE_BREAK---
Procedimiento operativo de produccion - version extendida
Pagina 4 de 4 - Escalado, informes y cierre

Escalado:
Un pedido bloqueado mas de 72 horas se escala a operaciones. Un pedido retrasado
con impacto en cliente prioritario se escala a operaciones y comercial. Un bloqueo
por calidad con riesgo sanitario se escala tambien a direccion tecnica.

Informes:
El informe diario agrupa ordenes por estado, motivo, cliente afectado y fecha
estimada. El informe semanal muestra bloqueos recurrentes, retrasos por linea,
tiempo medio de desbloqueo y pedidos que han cambiado de prioridad.

Cierre:
Una orden finished debe conservar todos los eventos previos. No se eliminan
bloqueos cerrados porque pueden justificar pausas de SLA, exclusiones de
penalizacion o respuestas de auditoria documental.

Marcador de validacion: PROD-V2-P04. Esta pagina debe recuperarse para preguntas
sobre escalado, informes de produccion o conservacion de eventos.
""",
    "v2_politica_calidad_entregas.pdf": """
Politica de calidad para entregas a cliente - version extendida
Pagina 1 de 3 - Objetivo, alcance y principios

Objetivo:
Garantizar que los pedidos enviados al cliente cumplen calidad documental, calidad
de preparacion, trazabilidad de lote y condiciones acordadas. La politica aplica a
pedidos ERP con salida desde almacen central, almacen externo o expedicion directa
desde fabrica.

Principios:
Ningun pedido sale sin lote validado, cantidad conciliada, documentacion preparada
y etiqueta legible. Calidad puede retener un pedido aunque produccion lo haya
terminado si detecta incidencia documental, riesgo de lote o falta de evidencia.

Alcance documental:
El expediente de entrega debe contener albaran, order_id, cliente, lote, cantidad,
transportista y fecha de salida. Si el cliente requiere certificado especifico, la
salida queda condicionada a que el certificado este adjunto.

Marcador de validacion: CAL-V2-P01. Esta pagina debe recuperarse para preguntas
sobre objetivo, alcance de calidad o documentos de salida.
---PAGE_BREAK---
Politica de calidad para entregas a cliente - version extendida
Pagina 2 de 3 - Control previo y gestion de incidencias

Control previo:
Antes de liberar un pedido, calidad valida lote, cantidad, documentacion,
etiquetado y compatibilidad con condiciones de transporte. Si el pedido requiere
temperatura controlada, el transportista debe confirmar capacidad antes de salida.

Incidencias:
Una incidencia de calidad bloquea el pedido hasta que calidad registre resolucion.
La resolucion debe indicar si el lote se libera, se sustituye, se reprocesa o se
rechaza. Produccion no puede desbloquear una retencion de calidad sin aprobacion
de calidad.

Entregas parciales:
Las entregas parciales requieren aprobacion comercial y validacion de calidad para
cada lote entregado. Si una parte queda retenida, el albaran debe explicar la parte
enviada, la parte pendiente y el motivo de retencion.

Marcador de validacion: CAL-V2-P02. Esta pagina debe recuperarse para preguntas
sobre control previo, incidencia de calidad o entregas parciales.
---PAGE_BREAK---
Politica de calidad para entregas a cliente - version extendida
Pagina 3 de 3 - Indicadores, auditoria y respuesta RAG

Indicadores:
Los indicadores mensuales separan pedidos entregados a tiempo, pedidos retrasados,
pedidos bloqueados, pedidos con incidencia de calidad, entregas parciales y
devoluciones por documentacion incompleta. Cada indicador debe permitir navegar al
order_id que lo justifica.

Auditoria:
La auditoria revisa una muestra de expedientes y comprueba lote, albaran,
certificado, fecha de salida, transportista y aceptacion del cliente. Si falta una
evidencia, el hallazgo queda abierto aunque el pedido figure como delivered.

Respuesta documental:
Cuando se consulte por calidad, la respuesta debe citar la pagina y el documento
usado. Si el texto no contiene evidencia suficiente para lote, certificado o
retencion, debe devolver insufficient_context.

Marcador de validacion: CAL-V2-P03. Esta pagina debe recuperarse para preguntas
sobre indicadores, auditoria o respuesta documental con fuentes.
""",
    "v2_condiciones_comerciales_northwind.pdf": """
Condiciones comerciales Northwind - version extendida
Pagina 1 de 4 - Datos maestros y fuente ERP

Clientes:
Cada cliente se identifica mediante customer_id ERP y nombre comercial. Las
consultas de negocio deben usar datos del ERP para clientes, pedidos, fechas,
estado e importes. No se debe inventar un cliente, pedido o descuento si no aparece
en la base de datos o en un documento cargado.

Pedidos:
Un pedido comercial contiene cabecera, lineas, fecha de pedido, fecha requerida,
estado ERP e importe calculable desde lineas. La cabecera no basta para calcular
impacto economico si faltan precios, cantidades o descuentos.

Fuente preferente:
Para importes y estados comerciales manda el ERP. Para reglas de SLA o calidad
manda el documento contractual correspondiente. Si las fuentes entran en conflicto,
la respuesta debe explicarlo y pedir validacion humana.

Marcador de validacion: COM-V2-P01. Esta pagina debe recuperarse para preguntas
sobre clientes, pedidos o fuente ERP preferente.
---PAGE_BREAK---
Condiciones comerciales Northwind - version extendida
Pagina 2 de 4 - Importes, descuentos e impacto economico

Calculo de importe:
El importe de un pedido se calcula desde las lineas usando precio unitario,
cantidad y descuento. El resultado debe indicar si procede del ERP, de un calculo
sobre lineas ERP o si no existe evidencia suficiente.

Descuentos:
Los descuentos comerciales se aplican por linea. No se debe aplicar un descuento
global inventado si las lineas no lo contienen. Si un pedido tiene lineas con
descuentos distintos, la respuesta debe explicar el calculo agregado.

Impacto economico:
Cuando una penalizacion o retraso tenga impacto economico, la respuesta debe unir
importe ERP, porcentaje contractual y causa documentada. Si cualquiera de esos tres
elementos falta, no se calcula impacto definitivo.

Marcador de validacion: COM-V2-P02. Esta pagina debe recuperarse para preguntas
sobre calculo de importes, descuentos o impacto economico.
---PAGE_BREAK---
Condiciones comerciales Northwind - version extendida
Pagina 3 de 4 - Prioridad comercial y promesas al cliente

Prioridad:
Los pedidos de clientes prioritarios pueden adelantarse si produccion confirma
capacidad y calidad confirma lote liberado. La prioridad comercial no elimina
bloqueos de material ni incidencias de calidad.

Promesas:
Un pedido bloqueado por material no debe prometerse al cliente sin fecha estimada
validada por produccion. Si la pregunta solicita una fecha y no hay fecha estimada,
la respuesta debe indicar que falta contexto operativo suficiente.

Cambios:
Todo cambio de prioridad debe registrar quien lo aprueba, motivo comercial, pedido
afectado y posible impacto en otros clientes. Los cambios sin rastro no deben
usarse para justificar retrasos ni penalizaciones.

Marcador de validacion: COM-V2-P03. Esta pagina debe recuperarse para preguntas
sobre prioridad comercial, promesas al cliente o cambios de prioridad.
---PAGE_BREAK---
Condiciones comerciales Northwind - version extendida
Pagina 4 de 4 - Trazabilidad y forma de respuesta

Trazabilidad:
Toda respuesta de negocio debe indicar fuentes consultadas, pasos ejecutados y
tools utilizadas. El razonamiento visible debe ser un resumen auditable y no un
razonamiento interno sensible. La respuesta debe separar hechos ERP, reglas
documentales y conclusiones.

Fuentes:
Si se usa RAG, se debe citar filename y pagina. Si se usa ERP, se debe indicar la
entidad consultada. Si se usa produccion, se debe indicar order_id y estado
operativo. Una respuesta con documentos pero sin pagina no cumple la regla.

Insuficiencia:
Cuando la evidencia documental o ERP sea parcial, la respuesta debe limitarse a lo
demostrado y marcar insufficient_context para el resto. No se completan huecos por
memoria del modelo.

Marcador de validacion: COM-V2-P04. Esta pagina debe recuperarse para preguntas
sobre trazabilidad, fuentes, tools o formato de respuesta.
""",
}


def generate_sample_pdfs(output_dir: Path | None = None) -> list[Path]:
    target_dir = output_dir or Path("data/sample_docs")
    target_dir.mkdir(parents=True, exist_ok=True)

    generated_files = []
    for filename, content in SAMPLE_DOCUMENTS.items():
        path = target_dir / filename
        path.write_bytes(build_pdf_bytes(content))
        generated_files.append(path)

    return generated_files


def build_pdf_bytes(text: str) -> bytes:
    pages = _paginate(text)
    objects: list[bytes] = [
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n",
        _pages_object(page_count=len(pages)),
        b"3 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n",
    ]

    for index, lines in enumerate(pages):
        page_object_id = 4 + index * 2
        content_object_id = page_object_id + 1
        stream = _content_stream(lines)
        objects.append(
            (
                f"{page_object_id} 0 obj << /Type /Page /Parent 2 0 R "
                "/MediaBox [0 0 612 792] "
                "/Resources << /Font << /F1 3 0 R >> >> "
                f"/Contents {content_object_id} 0 R >> endobj\n"
            ).encode("ascii")
        )
        objects.append(
            (
                f"{content_object_id} 0 obj << /Length {len(stream)} >> stream\n"
            ).encode("ascii")
            + stream
            + b"\nendstream endobj\n"
        )

    return _assemble_pdf(objects)


def _paginate(text: str) -> list[list[str]]:
    pages = []
    for section in text.strip().split(PAGE_BREAK):
        lines: list[str] = []
        for paragraph in section.strip().splitlines():
            paragraph = paragraph.strip()
            if not paragraph:
                lines.append("")
                continue
            lines.extend(textwrap.wrap(paragraph, width=88) or [""])

        if not lines:
            continue

        for index in range(0, len(lines), 42):
            pages.append(lines[index : index + 42])

    return pages or [["Documento sin contenido."]]


def _pages_object(page_count: int) -> bytes:
    page_ids = " ".join(f"{4 + index * 2} 0 R" for index in range(page_count))
    return (
        f"2 0 obj << /Type /Pages /Kids [{page_ids}] /Count {page_count} >> endobj\n"
    ).encode("ascii")


def _content_stream(lines: list[str]) -> bytes:
    commands = ["BT", "/F1 10 Tf", "72 760 Td", "14 TL"]
    for line in lines:
        commands.append(f"({_escape_pdf_text(line)}) Tj")
        commands.append("T*")
    commands.append("ET")
    return "\n".join(commands).encode("ascii")


def _escape_pdf_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _assemble_pdf(objects: list[bytes]) -> bytes:
    body = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for pdf_object in objects:
        offsets.append(len(body))
        body.extend(pdf_object)

    xref = len(body)
    body.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    body.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        body.extend(f"{offset:010d} 00000 n \n".encode("ascii"))

    body.extend(
        (
            f"trailer << /Root 1 0 R /Size {len(objects) + 1} >>\n"
            f"startxref\n{xref}\n%%EOF\n"
        ).encode("ascii")
    )
    return bytes(body)


if __name__ == "__main__":
    for generated in generate_sample_pdfs():
        print(generated)
