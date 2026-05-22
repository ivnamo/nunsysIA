from app.rag.ingestion import DocumentIngestionService
from app.tools.rag_tool import DocumentRAGTool


def create_rag_tool(document_service: DocumentIngestionService) -> DocumentRAGTool:
    return DocumentRAGTool(
        vector_store=document_service.vector_store,
        embedding_model=document_service.embedding_model,
    )

