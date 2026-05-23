from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import get_settings
from app.rag.factory import create_document_service


DELIVERY_PDFS = (
    "v2_contrato_marco_logistica_2026.pdf",
    "v2_anexo_penalizaciones_sla.pdf",
    "v2_procedimiento_produccion_bloqueos.pdf",
    "v2_politica_calidad_entregas.pdf",
    "v2_condiciones_comerciales_northwind.pdf",
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Limpia el indice RAG y carga los PDFs oficiales de entrega."
    )
    parser.add_argument(
        "--docs-dir",
        type=Path,
        default=ROOT / "data" / "sample_docs",
    )
    parser.add_argument(
        "--keep-existing",
        action="store_true",
        help="No limpia la coleccion antes de indexar. La ingesta sigue siendo idempotente por filename/hash.",
    )
    args = parser.parse_args()

    service = create_document_service(get_settings())
    if not args.keep_existing:
        removed = service.clear_documents()
        print(f"RAG reset: {removed} chunks eliminados.")

    for filename in DELIVERY_PDFS:
        path = args.docs_dir / filename
        response = service.ingest_pdf_path(path)
        print(
            f"{response.filename}: {response.status}, "
            f"{response.chunks_indexed} chunks, document_id={response.document_id}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
