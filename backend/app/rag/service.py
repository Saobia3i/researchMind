import logging
from app.rag.pinecone_client import get_pinecone_client, get_or_create_index
from app.rag.text_splitter import chunk_text

logger = logging.getLogger(__name__)


def ingest_document(text: str, doc_id: str, metadata: dict = None) -> dict:
    """
    Splits the input document into chunks, generates embeddings using Pinecone Inference API,
    and upserts the vectors into Pinecone.
    """
    if not text.strip():
        raise ValueError("Input text cannot be empty.")

    # 1. Initialize/Retrieve Index
    index = get_or_create_index()
    pc = get_pinecone_client()

    # 2. Chunk Text
    chunks = chunk_text(text, chunk_size=500, chunk_overlap=50)
    if not chunks:
        return {"doc_id": doc_id, "chunks_ingested": 0, "status": "no_chunks_created"}

    # 3. Generate Embeddings for all chunks
    logger.info(
        f"Generating embeddings for {len(chunks)} chunks using Pinecone Inference..."
    )
    try:
        response = pc.inference.embed(
            model="multilingual-e5-large",
            inputs=chunks,
            parameters={"input_type": "passage", "truncate": "END"},
        )
    except Exception as e:
        logger.error(f"Error generating embeddings from Pinecone: {e}")
        raise RuntimeError(f"Embedding generation failed: {e}")

    # 4. Prepare vectors for upsertion
    vectors = []
    for i, (chunk, embed_data) in enumerate(zip(chunks, response)):
        # Construct a unique ID for each chunk
        chunk_id = f"{doc_id}_chunk_{i}"

        # Merge text with additional metadata
        chunk_metadata = {"text": chunk, "doc_id": doc_id}
        if metadata:
            chunk_metadata.update(metadata)

        vectors.append(
            {"id": chunk_id, "values": embed_data["values"], "metadata": chunk_metadata}
        )

    # 5. Upsert to Pinecone in batches to be safe (Pinecone recommended batch size is ~100)
    batch_size = 100
    for i in range(0, len(vectors), batch_size):
        batch = vectors[i : i + batch_size]
        try:
            index.upsert(vectors=batch)
        except Exception as e:
            logger.error(f"Error upserting vectors to Pinecone: {e}")
            raise RuntimeError(f"Pinecone upsert failed: {e}")

    logger.info(
        f"Successfully ingested document '{doc_id}' split into {len(chunks)} chunks."
    )
    return {
        "doc_id": doc_id,
        "chunks_ingested": len(chunks),
        "status": "success",
    }


def search_similar(query: str, top_k: int = 5) -> list[dict]:
    """
    Generates an embedding for the query, searches Pinecone, and returns matching passages.
    """
    if not query.strip():
        raise ValueError("Search query cannot be empty.")

    # 1. Retrieve Index
    index = get_or_create_index()
    pc = get_pinecone_client()

    # 2. Generate Query Embedding
    logger.info(f"Generating embedding for query: '{query}'")
    try:
        response = pc.inference.embed(
            model="multilingual-e5-large",
            inputs=[query],
            parameters={"input_type": "query", "truncate": "END"},
        )
        query_vector = response[0]["values"]
    except Exception as e:
        logger.error(f"Error generating query embedding: {e}")
        raise RuntimeError(f"Query embedding generation failed: {e}")

    # 3. Search Index
    try:
        results = index.query(
            vector=query_vector, top_k=top_k, include_metadata=True
        )
    except Exception as e:
        logger.error(f"Error querying Pinecone index: {e}")
        raise RuntimeError(f"Pinecone query execution failed: {e}")

    # 4. Format Results
    matches = []
    for match in results.get("matches", []):
        matches.append(
            {
                "id": match.get("id"),
                "score": match.get("score"),
                "text": match.get("metadata", {}).get("text", ""),
                "metadata": {
                    k: v
                    for k, v in match.get("metadata", {}).items()
                    if k != "text"
                },
            }
        )

    return matches
