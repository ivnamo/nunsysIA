from __future__ import annotations

import textwrap
from pathlib import Path


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
    lines: list[str] = []
    for paragraph in text.strip().splitlines():
        paragraph = paragraph.strip()
        if not paragraph:
            lines.append("")
            continue
        lines.extend(textwrap.wrap(paragraph, width=88) or [""])

    pages = []
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
