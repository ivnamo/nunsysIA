import re

from app.rag.vector_store import DocumentVectorStore


FILENAME_PATTERN = re.compile(r"[\w.-]+\.pdf", flags=re.IGNORECASE)


def requested_filenames(query: str, explicit_filename: str | None = None) -> set[str]:
    filenames = set()
    if explicit_filename:
        filenames.add(explicit_filename.strip())
    filenames.update(
        match.group(0).strip(".,;:()[]{}")
        for match in FILENAME_PATTERN.finditer(query)
    )
    return {filename for filename in filenames if filename}


def query_without_filenames(query: str) -> str:
    return FILENAME_PATTERN.sub(" ", query)


def is_document_wide_query(query: str) -> bool:
    normalized = query.lower()
    if " sobre " in normalized or " acerca de " in normalized:
        return any(
            marker in normalized
            for marker in (
                "resume",
                "resumir",
                "resumen",
                "resumeme",
                "sintetiza",
            )
        )
    return any(
        marker in normalized
        for marker in (
            "resume",
            "resumir",
            "resumen",
            "resumeme",
            "sintetiza",
            "de que trata",
            "que dice este documento",
            "que dice el documento",
            "que dice el pdf",
        )
    )


def resolve_requested_filenames(
    vector_store: DocumentVectorStore,
    filenames: set[str],
) -> set[str]:
    if not filenames:
        return set()
    try:
        indexed_documents = vector_store.list_documents()
    except Exception:
        return filenames

    filenames_by_lower = {
        document.filename.lower(): document.filename
        for document in indexed_documents
    }
    return {
        filenames_by_lower.get(filename.lower(), filename)
        for filename in filenames
    }
