from dataclasses import dataclass
from email.message import Message
from email.parser import Parser

from fastapi import Request


class UploadParseError(ValueError):
    pass


class UploadTooLargeError(ValueError):
    pass


@dataclass(frozen=True)
class UploadedDocument:
    filename: str
    content: bytes
    content_type: str


async def read_pdf_upload(request: Request, max_bytes: int) -> UploadedDocument:
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > max_bytes:
        raise UploadTooLargeError("El archivo supera el tamano maximo permitido.")

    body = await request.body()
    if len(body) > max_bytes:
        raise UploadTooLargeError("El archivo supera el tamano maximo permitido.")

    content_type = request.headers.get("content-type", "")
    if content_type.startswith("application/pdf"):
        filename = request.query_params.get("filename", "document.pdf")
        return UploadedDocument(
            filename=filename,
            content=body,
            content_type="application/pdf",
        )

    if content_type.startswith("multipart/form-data"):
        return _parse_multipart_pdf(body=body, content_type=content_type)

    raise UploadParseError("El request debe ser multipart/form-data o application/pdf.")


def _parse_multipart_pdf(body: bytes, content_type: str) -> UploadedDocument:
    boundary = _get_boundary(content_type)
    boundary_bytes = f"--{boundary}".encode("utf-8")

    for raw_part in body.split(boundary_bytes):
        part = raw_part.strip(b"\r\n")
        if not part or part == b"--":
            continue
        if part.endswith(b"--"):
            part = part[:-2].strip(b"\r\n")

        header_bytes, separator, content = part.partition(b"\r\n\r\n")
        if not separator:
            continue

        headers = _parse_headers(header_bytes)
        disposition = headers.get("content-disposition", "")
        if "name=\"file\"" not in disposition:
            continue

        filename = _extract_disposition_value(disposition, "filename")
        if not filename:
            raise UploadParseError("El campo file debe incluir filename.")

        return UploadedDocument(
            filename=filename,
            content=content.rstrip(b"\r\n"),
            content_type=headers.get("content-type", "application/octet-stream"),
        )

    raise UploadParseError("No se encontro el campo file en el multipart.")


def _get_boundary(content_type: str) -> str:
    for part in content_type.split(";"):
        key, _, value = part.strip().partition("=")
        if key.lower() == "boundary" and value:
            return value.strip('"')
    raise UploadParseError("No se encontro boundary en multipart/form-data.")


def _parse_headers(header_bytes: bytes) -> Message:
    header_text = header_bytes.decode("utf-8", errors="replace")
    return Parser().parsestr(header_text)


def _extract_disposition_value(disposition: str, key: str) -> str | None:
    prefix = f'{key}="'
    start = disposition.find(prefix)
    if start == -1:
        return None
    start += len(prefix)
    end = disposition.find('"', start)
    return disposition[start:end] if end != -1 else None
