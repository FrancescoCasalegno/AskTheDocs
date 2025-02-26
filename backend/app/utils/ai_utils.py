from openai import OpenAI
openai_client = OpenAI()

from app.core.config import app_config


def embed_text(text: str, model: str = app_config.OPENAI_EMBEDDING_MODEL):
    """
    Return the embedding vector for the given text using OpenAI.
    """
    response = openai_client.embeddings.create(
        input=text,
        model=model
    )
    return response.data[0].embedding


def get_answer_from_llm(system_prompt: str, user_prompt: str, model: str = app_config.OPENAI_TEXT_GENERATION_MODEL):
    """Generate an answer from LLM."""
    response = openai_client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.0,
    )
    return response.choices[0].message.content
