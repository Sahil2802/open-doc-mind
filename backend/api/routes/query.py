import json
import time
import logging
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from backend.api.models import QueryRequest
from backend.retrieval import retrieve_chunks
from backend.generation.llm import generate_answer_stream
from backend.generation.citation_check import enforce_citations

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/query")
async def query_documents(request: QueryRequest):
    """
    Streaming query endpoint. Retrieves relevant chunks via vector search,
    generates an answer using Groq LLM, and streams tokens as SSE events.

    SSE event types:
        - token: partial answer text {"text": "..."}
        - replace: citation enforcement replaced the answer {"text": "..."}
        - citations: citation metadata array
        - error: retrieval/generation error {"message": "..."}
        - done: stream complete {}
    """

    async def event_stream():
        start_ms = int(time.time() * 1000)

        try:
            # Retrieve relevant chunks — vector search only (Phase 1)
            chunks = retrieve_chunks(
                query=request.query,
                filter_document_id=request.document_id,
            )
        except Exception as e:
            logger.error(f"Retrieval failed: {e}", exc_info=True)
            yield f"event: error\ndata: {json.dumps({'message': f'Retrieval failed: {str(e)[:200]}'})}\n\n"
            return

        if not chunks:
            yield f"event: error\ndata: {json.dumps({'message': 'No relevant documents found. Please upload documents first.'})}\n\n"
            return

        # Generate answer with streaming
        full_answer = ""
        citation_map = []
        had_error = False

        try:
            async for token in generate_answer_stream(request.query, chunks):
                # Check for special tagged blocks
                if token.startswith("\n\n[CITATIONS]"):
                    citation_json = (
                        token.replace("\n\n[CITATIONS]", "")
                        .replace("[/CITATIONS]", "")
                    )
                    try:
                        citation_map = json.loads(citation_json)
                    except json.JSONDecodeError:
                        logger.error(f"Failed to parse citation JSON: {citation_json[:200]}")
                    continue

                if token.startswith("\n\n[ERROR]"):
                    error_msg = (
                        token.replace("\n\n[ERROR]", "")
                        .replace("[/ERROR]", "")
                    )
                    yield f"event: error\ndata: {json.dumps({'message': f'LLM error: {error_msg}'})}\n\n"
                    had_error = True
                    continue

                # Regular token — stream to client
                full_answer += token
                yield f"event: token\ndata: {json.dumps({'text': token})}\n\n"

        except Exception as e:
            logger.error(f"Streaming generation failed: {e}", exc_info=True)
            yield f"event: error\ndata: {json.dumps({'message': f'Generation failed: {str(e)[:200]}'})}\n\n"
            had_error = True

        if had_error:
            yield f"event: done\ndata: {{}}\n\n"
            return

        # Citation enforcement — refuse if LLM drifted into unsupported claims
        final_answer, was_refused = enforce_citations(full_answer, chunks)

        if was_refused and final_answer != full_answer:
            yield f"event: replace\ndata: {json.dumps({'text': final_answer})}\n\n"

        # Send citation metadata or clear them if refused
        if was_refused:
            yield f"event: refused\ndata: {json.dumps({'text': final_answer})}\n\n"
            yield f"event: citations\ndata: {json.dumps([])}\n\n"
        else:
            # Filter citation_map to only include documents the LLM actually cited
            import re
            cited_files = set(re.findall(r"\[Source:\s*([^,\]\n]+)", final_answer))
            filtered_citations = [
                c for c in citation_map 
                if c.get("file_name") in cited_files
            ]
            yield f"event: citations\ndata: {json.dumps(filtered_citations)}\n\n"

        latency_ms = int(time.time() * 1000) - start_ms
        logger.info(
            f"Query completed in {latency_ms}ms — "
            f"refused={was_refused}, chunks={len(chunks)}, "
            f"answer_len={len(final_answer)}"
        )

        yield f"event: done\ndata: {{}}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable Nginx buffering for SSE
        },
    )
