from dataclasses import dataclass
from io import BytesIO

from pypdf import PdfReader


class PDFExtractionError(RuntimeError):
    pass


@dataclass(frozen=True)
class DocumentPage:
    page: int
    text: str


class PDFLoader:
    def load(self, content: bytes) -> list[DocumentPage]:
        try:
            reader = PdfReader(BytesIO(content))
        except Exception as exc:
            raise PDFExtractionError("No se pudo leer el PDF.") from exc

        pages: list[DocumentPage] = []
        for index, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            if text.strip():
                pages.append(DocumentPage(page=index, text=text.strip()))

        return pages
