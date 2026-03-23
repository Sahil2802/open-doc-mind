import json
import logging
from typing import AsyncIterator
from groq import Groq
from backend.config.settings import settings
from backend.generation.prompt_loader import get_active_prompt
from backend.generation.context_builder import build_context_block

logger = logging.getLogger(__name__)

_client = Groq(api_key=settings.GROQ_API_KEY)

MODEL = "llama-3.1-8b-instant"
MAX_TOKENS = 1024
TEMPERATURE = 0.1  # Low temperature for factual RAG — less creative drift


async def generate_answer_stream(
    query: str,
    chunks: list[dict],
) -> AsyncIterator[str]:
    """
    Stream the LLM answer token by token via Groq.

    Yields raw text tokens for SSE streaming to the frontend.
    After all content tokens, yields a special [CITATIONS]...[/CITATIONS]
    JSON block containing citation metadata.

    Args:
        query: The user's question.
        chunks: Enriched chunk dicts from retrieve_chunks().
    """
    prompt_config = get_active_prompt()
    # Build context block from chunks
    context_str, citation_map = build_context_block(chunks)

    user_message = f"""Context documents:

{context_str}

---

Question: {query}

Remember: After every factual claim, cite the source using [Source: file_name]. If the context does not support an answer, use the mandatory refusal phrase."""

    logger.info(
        f"Generating answer with prompt={prompt_config['key']} "
        f"v{prompt_config['version']}, model={MODEL}, chunks={len(chunks)}"
    )

    try:
        # Groq SDK's create() with stream=True returns a synchronous iterator.
        # We iterate synchronously and yield from the async generator.
        stream = _client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": prompt_config["system"]},
                {"role": "user", "content": user_message},
            ],
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
            stream=True,
        )
        # Stream the LLM answer token by token
        full_answer = ""
        for chunk in stream:
            token = chunk.choices[0].delta.content or ""
            if token:
                full_answer += token
                yield token

        logger.info(f"LLM generated {len(full_answer)} chars")

        # Yield citation metadata as a special tagged block
        yield f"\n\n[CITATIONS]{json.dumps(citation_map)}[/CITATIONS]"

    except Exception as e:
        logger.error(f"Groq LLM call failed: {e}", exc_info=True)
        yield f"\n\n[ERROR]{str(e)[:200]}[/ERROR]"
