from dataclasses import dataclass

from fastapi import Request, UploadFile


_UPLOAD_READ_CHUNK_BYTES = 1024 * 1024


class UploadParseError(ValueError):
    pass


class UploadTooLargeError(ValueError):
    pass


@dataclass(frozen=True)
class UploadedDocument:
    filename: str
    content: bytes
    content_type: str


async def read_pdf_upload(
    request: Request,
    max_bytes: int,
    file: UploadFile | None = None,
) -> UploadedDocument:
    content_length = request.headers.get("content-length")
    if _content_length_exceeds_limit(content_length, max_bytes):
        raise UploadTooLargeError("El archivo supera el tamano maximo permitido.")

    if file is not None:
        return await _read_multipart_pdf(file=file, max_bytes=max_bytes)

    content_type = request.headers.get("content-type", "")
    if content_type.startswith("application/pdf"):
        body = await _read_direct_pdf_body(request=request, max_bytes=max_bytes)
        return UploadedDocument(
            filename=request.query_params.get("filename", "document.pdf"),
            content=body,
            content_type="application/pdf",
        )

    if content_type.startswith("multipart/form-data"):
        raise UploadParseError("No se encontro el campo file en el multipart.")

    raise UploadParseError("El request debe ser multipart/form-data o application/pdf.")


async def _read_multipart_pdf(
    file: UploadFile,
    max_bytes: int,
) -> UploadedDocument:
    if not file.filename:
        raise UploadParseError("El campo file debe incluir filename.")

    content = bytearray()
    while chunk := await file.read(_UPLOAD_READ_CHUNK_BYTES):
        if len(content) + len(chunk) > max_bytes:
            raise UploadTooLargeError("El archivo supera el tamano maximo permitido.")
        content.extend(chunk)

    return UploadedDocument(
        filename=file.filename,
        content=bytes(content),
        content_type=file.content_type or "application/octet-stream",
    )


async def _read_direct_pdf_body(request: Request, max_bytes: int) -> bytes:
    body = await request.body()
    if len(body) > max_bytes:
        raise UploadTooLargeError("El archivo supera el tamano maximo permitido.")
    return body


def _content_length_exceeds_limit(content_length: str | None, max_bytes: int) -> bool:
    if not content_length:
        return False
    try:
        return int(content_length) > max_bytes
    except ValueError:
        return False
