"""Endpoint for querying the database."""
import json
from logging import getLogger
from typing import List, Optional

import app.utils.ai_prompts as ai_prompts
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
    1. Context Retrieval
    2. Answer Generation
    """
    logger.info(f"Received query: {req.query}")

    # 1. Context Retrieval
    # 1.1 Generate query
    user_question = req.query
    conversation = [
        {
            "role": "user",
            "message": user_question,
        }
    ]
    system_prompt = ai_prompts.QUERY_GENERATION_SYSTEM_PROMPT
    user_prompt = ai_prompts.QUERY_GENERATION_USER_PROMPT_TEMPLATE.format(
        conversation=json.dumps(conversation, indent=2)
    )
    try:
        retriever_query = await get_answer_from_llm(
            system_prompt, user_prompt, llm_response_model=None
        )
        logger.info(f"Generated query for retriever: {retriever_query}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error calling GPT model: {str(e)}")

    # 1.2 Embed the query
    try:
        retriever_query_embedding = await embed_text(retriever_query)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error embedding query: {str(e)}")

    # 2.2 Search vector database using the query embedding
    # We'll use .l2_distance(query_embedding) and order_by ascending
    distance = Chunk.embedding.l2_distance(retriever_query_embedding)
    select_query = (
        select(Chunk, distance.label("l2_distance")).order_by(distance.asc()).limit(req.top_k)
    )
    result = await db.execute(select_query)
    top_distance_contexts = result.all()

    if not top_distance_contexts:
        logger.warning(f"No contexts found for query: {req.query}")
        logger.warning(f"result: {vars(result)}")
        return QueryResponse(
            answer_text="UNANSWERABLE [No contexts found by Retriever]",
            answer_sources=[],
            top_k_retrieved=0,
        )

    # 2. Answer Generation
    # 2.1 Format context
    contexts = []
    for i, (chunk, l2_dist) in enumerate(top_distance_contexts, start=1):
        # Convert L2 distance to cosine similarity
        # || a - b ||^2 = || a ||^2 + || b ||^2 - 2 * <a, b>
        # And since we have normalized embeddings, || a || = || b || = 1, so:
        # || a - b ||^2 = 2 - 2 * <a, b>
        # And finally, notice that <a, b> = cosine similarity if a and b are normalized!
        cosine_sim = 1 - l2_dist**2 / 2
        snippet = (
            f"Doc Name: {chunk.doc_name}, ChunkID: {chunk.chunk_id}, "
            f"Headers: {chunk.section_headers}, Pages: {chunk.pages}\n"
            f"{chunk.serialized_chunk}"
        )
        logger.info(
            f"Retrieved top-{i} context "
            f"[L2-dist={l2_dist:.2f}; Cosine-sim={cosine_sim:.2f}]:\n{snippet}"
        )
        contexts.append(snippet)

    logger.info(f"Done retrieving top-k (k={len(contexts)}) contexts")

    # 2.2 Create prompt for LLM
    system_prompt = ai_prompts.QUESTION_ANSWERING_SYSTEM_PROMPT
    user_prompt = ai_prompts.QUESTION_ANSWERING_USER_PROMPT_TEMPLATE.format(
        question=req.query, context="\n---------------------------------\n".join(contexts)
    )

    # 2.3 Send request to LLM
    try:
        answer = await get_answer_from_llm(
            system_prompt, user_prompt, llm_response_model=LLMResponseModel
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error calling GPT model: {str(e)}")

    logger.info(f"Raw answer from LLM: {answer}")

    llm_answer = LLMResponseModel(**json.loads(answer))
    answer_text = f"[RAG QUERY] {retriever_query}\n[ANSWER] {llm_answer.answer_text}"

    return QueryResponse(
        answer_text=answer_text,
        answer_sources=llm_answer.answer_sources,
        top_k_retrieved=len(top_distance_contexts),
    )
