from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.session import SessionLocal
from app.db.models import Chunk
from app.utils.ai_utils import embed_text, get_answer_from_llm
from app.core.log_config import set_logging_options
from app.core.config import app_config
from logging import getLogger

import json

set_logging_options(level=app_config.LOGGING_LEVEL)
logger = getLogger(__name__)


query_router = APIRouter()

class QueryRequest(BaseModel):
    query: str
    top_k: Optional[int] = 10


class QueryResponse(BaseModel):
    answer_text: str
    answer_sources: List[str]
    top_k_retrieved: int


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@query_router.post("/v1/query", response_model=QueryResponse)
def query_documents(req: QueryRequest, db: Session = Depends(get_db)):
    """
    1) Embeds the query
    2) Vector search in 'chunks' table
    3) Calls GPT with the top_k context
    4) Returns the answer
    """
    logger.info(f"Received query: {req.query}")

    # 1) embed the query
    try:
        query_embedding = embed_text(req.query)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error embedding query: {str(e)}")

    # 2) vector search using pgvector & SQLAlchemy
    # We'll use .l2_distance(query_embedding) and order_by ascending
    distance = Chunk.embedding.l2_distance(query_embedding)
    stmt = (
        select(Chunk)
        .order_by(distance.asc())  # smallest distance first
        .limit(req.top_k)
    )
    top_contexts = db.execute(stmt).scalars().all()

    if not top_contexts:
        return {"answer": "UNANSWERABLE", "reason": "No context found in DB."}

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
        "Otherwise, provide the best possible answer AND provide one or more verbatim source quotes "
        "from the context that justify the answer."
        "Output format should be a JSON in the following format:"
        "{'answer': '...', 'sources': ['...', '...']}"
    )
    user_prompt = f"QUESTION: {req.query}\n\nCONTEXT:\n" + "\n\n---\n\n".join(contexts)

    # 4) call GPT
    try:
        answer = get_answer_from_llm(system_prompt, user_prompt)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error calling GPT model: {str(e)}")

    logger.info(f"Raw answer from LLM: {answer}")

    answer = json.loads(answer)
    answer_text, answer_sources = answer["answer"], answer["sources"]

    return QueryResponse(
        answer_text=answer_text,
        answer_sources=answer_sources,
        top_k_retrieved=len(top_contexts)
    )