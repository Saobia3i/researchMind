from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from app.rag.service import ingest_document, search_similar

router = APIRouter()


class IngestRequest(BaseModel):
    text: str = Field(
        ..., min_length=1, description="The text content of the document to ingest."
    )
    doc_id: str = Field(
        ...,
        min_length=1,
        description="A unique identifier for the document.",
    )
    metadata: dict | None = Field(
        None, description="Optional metadata key-value pairs."
    )


class IngestResponse(BaseModel):
    doc_id: str
    chunks_ingested: int
    status: str


class SearchRequest(BaseModel):
    query: str = Field(
        ..., min_length=1, description="The query to search for matches."
    )
    top_k: int = Field(5, ge=1, le=50, description="Number of results to return.")


class SearchResponseItem(BaseModel):
    id: str
    score: float
    text: str
    metadata: dict


class SearchResponse(BaseModel):
    matches: list[SearchResponseItem]


@router.post(
    "/rag/ingest",
    response_model=IngestResponse,
    status_code=status.HTTP_201_CREATED,
)
def ingest_text(request: IngestRequest):
    """
    Ingests a document, chunks it, embeds it using Pinecone Inference, and saves to Pinecone DB.
    """
    try:
        result = ingest_document(
            text=request.text, doc_id=request.doc_id, metadata=request.metadata
        )
        return IngestResponse(**result)
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve)
        )
    except RuntimeError as re:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(re)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during ingestion: {str(e)}",
        )


@router.post("/rag/search", response_model=SearchResponse)
def search_text(request: SearchRequest):
    """
    Queries Pinecone vector database using embedding search and returns the top-k matches.
    """
    try:
        matches = search_similar(query=request.query, top_k=request.top_k)
        return SearchResponse(matches=matches)
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve)
        )
    except RuntimeError as re:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(re)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during search: {str(e)}",
        )
