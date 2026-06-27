import logging
from ddgs import DDGS

logger = logging.getLogger(__name__)


def search_web(query: str, max_results: int = 5) -> str:
    """
    Queries DuckDuckGo Search and formats the results into a string block.
    """
    if not query.strip():
        return "Error: Search query is empty."

    logger.info(f"Executing web search for: '{query}'")
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))

        if not results:
            return f"No web search results found for query: '{query}'"

        formatted = []
        for i, res in enumerate(results):
            title = res.get("title", "No Title")
            body = res.get("body", "No Description")
            href = res.get("href", "No URL")
            formatted.append(
                f"[{i + 1}] Title: {title}\n    Snippet: {body}\n    URL: {href}"
            )

        return "\n\n".join(formatted)

    except Exception as e:
        logger.error(f"DuckDuckGo search error: {e}")
        return f"Error executing web search: {str(e)}"
