"""Utility functions for Embedding and Text Generation with AI models and APIs."""
from typing import Type

from app.core.config import app_config
from openai import OpenAI
from pydantic import BaseModel

openai_client = OpenAI()


def embed_text(text: str, model: str = app_config.OPENAI_EMBEDDING_MODEL):
    """Return the embedding vector for the given text."""
    response = openai_client.embeddings.create(input=text, model=model)
    return response.data[0].embedding


def get_answer_from_llm(
    system_prompt: str,
    user_prompt: str,
    model: str = app_config.OPENAI_TEXT_GENERATION_MODEL,
    llm_response_model: Type[BaseModel] | None = None,
):
    """Generate an answer from LLM."""
    kwargs = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.0,
    }
    if llm_response_model:
        kwargs["response_format"] = llm_response_model

    response = openai_client.beta.chat.completions.parse(**kwargs)
    return response.choices[0].message.content
