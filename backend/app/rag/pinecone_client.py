import logging
from pinecone import Pinecone, ServerlessSpec
from app.core.config import settings

logger = logging.getLogger(__name__)

_pc_client = None


def get_pinecone_client() -> Pinecone:
    """
    Initializes and returns the singleton Pinecone client instance.
    Raises ValueError if PINECONE_API_KEY is not configured.
    """
    global _pc_client
    if _pc_client is not None:
        return _pc_client

    if not settings.pinecone_api_key:
        raise ValueError(
            "PINECONE_API_KEY is not configured. Please add it to your .env file."
        )

    # Initialize Pinecone client (v5+)
    _pc_client = Pinecone(api_key=settings.pinecone_api_key)
    return _pc_client


def get_or_create_index():
    """
    Retrieves the configured Pinecone index, creating it first if it doesn't exist.
    """
    pc = get_pinecone_client()
    index_name = settings.pinecone_index_name

    try:
        existing_indexes = pc.list_indexes().names()
    except Exception as e:
        logger.error(f"Failed to connect to Pinecone: {e}")
        raise RuntimeError(
            f"Failed to authenticate or connect to Pinecone. Please check your PINECONE_API_KEY. Details: {e}"
        )

    if index_name not in existing_indexes:
        logger.info(f"Creating new serverless Pinecone index: '{index_name}'...")
        try:
            pc.create_index(
                name=index_name,
                dimension=1024,  # Dimension for multilingual-e5-large
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1"),
            )
            logger.info(f"Index '{index_name}' created successfully.")
        except Exception as e:
            logger.error(f"Error creating Pinecone index: {e}")
            raise RuntimeError(f"Could not create Pinecone index '{index_name}': {e}")

    return pc.Index(index_name)
