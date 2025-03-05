"""Endpoint for querying the database."""
import json
from logging import getLogger
from typing import List, Optional

from app.db.models import Chunk
from app.db.session import get_db_session
from app.utils.ai_utils import embed_text, get_answer_from_llm
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = getLogger(__name__)

query_router = APIRouter()


class QueryRequest(BaseModel):
    """Model for the request to the query endpoint."""

    query: str
    top_k: Optional[int] = 10


class QueryResponse(BaseModel):
    """Model for the response from the query endpoint."""

    answer_text: str
    answer_sources: List[str]
    top_k_retrieved: int


class LLMResponseModel(BaseModel):
    """Model for the structured JSON response from the LLM API."""

    answer_text: str
    answer_sources: List[str]


@query_router.post("/v1/query", response_model=QueryResponse)
async def query_documents(
    req: QueryRequest, db: AsyncSession = Depends(get_db_session)  # noqa: B008
):
    """Query a vector database and return an answer based on retrieved contexts.

    Breakdown:
    1) Embed the query
    2) Vector search in 'chunks' table
    3) Call LLM with the top_k context
    4) Return the answer
    """
    logger.info(f"Received query: {req.query}")

    # 1) embed the query
    try:
        query_embedding = await embed_text(req.query)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error embedding query: {str(e)}")

    # 2) vector search using pgvector & SQLAlchemy
    # We'll use .l2_distance(query_embedding) and order_by ascending
    distance = Chunk.embedding.l2_distance(query_embedding)
    select_query = select(Chunk).order_by(distance.asc()).limit(req.top_k)
    top_contexts = await (db.execute(select_query)).scalars().all()

    if not top_contexts:
        return QueryResponse(
            answer_text="UNANSWERABLE [No contexts found by Retriever]",
            answer_sources=[],
            top_k_retrieved=0,
        )

    # 3) build context
    contexts = []
    for chunk in top_contexts:
        snippet = (
            f"DocID: {chunk.doc_id}, ChunkID: {chunk.chunk_id}, "
            f"Headers: {chunk.section_headers}, Pages: {chunk.pages}\n"
            f"{chunk.serialized_chunk}"
        )
        contexts.append(snippet)

    logger.info("Retrieved top_k contexts:\n" + "\n\n---\n\n".join(contexts))

    # Create a system message
    system_prompt = (
        "You are an expert question-answering model. "
        "Given the following question and the following context, "
        "you MUST say 'UNANSWERABLE' if the question cannot be answered from the context. "
        "Otherwise, provide the best possible answer AND provide one or more verbatim "
        "source quotes from the context that justify the answer."
        "Output format should be a JSON in the following format:"
        "{'answer_text': '...', 'answer_sources': ['...', '...']}"
    )
    user_prompt = f"QUESTION: {req.query}\n\nCONTEXT:\n" + "\n\n---\n\n".join(contexts)

    # 4) call GPT
    try:
        answer = await get_answer_from_llm(
            system_prompt, user_prompt, llm_response_model=LLMResponseModel
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error calling GPT model: {str(e)}")

    logger.info(f"Raw answer from LLM: {answer}")

    # answer = json.loads(answer)
    answer: LLMResponseModel = json.loads(answer)
    answer_text, answer_sources = answer["answer_text"], answer["answer_sources"]

    return QueryResponse(
        answer_text=answer_text, answer_sources=answer_sources, top_k_retrieved=len(top_contexts)
    )
