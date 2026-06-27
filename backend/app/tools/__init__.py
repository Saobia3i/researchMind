from app.tools.web_search import search_web
from app.tools.calculator import calculate
from app.tools.kb_search import search_knowledge_base

# Unified registry of executable tool functions
TOOLS = {
    "web_search": search_web,
    "calculate": calculate,
    "kb_search": search_knowledge_base,
}

# Clean descriptions supplied to the ReAct agent in the system prompt
TOOL_DESCRIPTIONS = """
- web_search: Use this tool to search the web for up-to-date, real-time, or general-knowledge information.
  Format: web_search(your search query)
- calculate: Use this tool to solve math/arithmetic problems. Supports +, -, *, /, ** (exponentiation), and parentheses.
  Format: calculate(mathematical expression)
- kb_search: Use this tool to query the internal research knowledge base for previous findings or specific uploaded papers.
  Format: kb_search(semantic search query)
"""
