import logging
from app.rag.service import search_similar

logger = logging.getLogger(__name__)


def search_knowledge_base(query: str, top_k: int = 4) -> str:
    """
    Searches the internal Pinecone knowledge base for semantically similar passages
    and returns a formatted string block of matching results.
    """
    if not query.strip():
        return "Error: KB search query is empty."

    logger.info(f"Executing KB search for: '{query}'")
    try:
        results = search_similar(query=query, top_k=top_k)

        if not results:
            return f"No relevant information found in the knowledge base for query: '{query}'"

        formatted = []
        for i, match in enumerate(results):
            score = match.get("score", 0.0)
            text = match.get("text", "No Content")
            doc_id = match.get("metadata", {}).get("doc_id", "unknown_doc")
            formatted.append(
                f"Result [{i + 1}] (Document: {doc_id}, Similarity: {score:.4f}):\n{text}"
            )

        return "\n\n".join(formatted)

    except ValueError as ve:
        # e.g., missing API keys
        return f"KB Search Error: Configuration issue. Details: {str(ve)}"
    except Exception as e:
        logger.error(f"Knowledge base search error: {e}")
        return f"Error executing KB search: {str(e)}"
