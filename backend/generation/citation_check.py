import logging

logger = logging.getLogger(__name__)

REFUSAL_PHRASES = [
    "i couldn't find sufficient information",
    "the documents provided do not contain",
    "i don't have enough information",
    "not mentioned in the provided",
    "cannot be found in the documents",
]


def is_refusal(answer: str) -> bool:
    """Check if the LLM already refused to answer."""
    lower = answer.lower()
    return any(phrase in lower for phrase in REFUSAL_PHRASES)


def check_citations_present(answer: str) -> bool:
    """
    Heuristic check: does the answer contain at least one citation?
    Checks for multiple formats since smaller LLMs sometimes deviate
    from the exact [Source: file_name] format.
    """
    citation_patterns = [
        "[Source:",       # primary format from prompt
        "(Source:",       # parenthesized variant
        "[source:",       # lowercase variant
        "[Excerpt ",      # excerpt reference from context headers
    ]
    found = any(pattern in answer for pattern in citation_patterns)
    if not found:
        logger.debug(
            "No citation patterns found in answer. "
            f"First 300 chars: {answer[:300]}"
        )
    return found


def enforce_citations(answer: str, chunks: list[dict]) -> tuple[str, bool]:
    """
    Post-generation citation enforcement.

    Returns (final_answer, was_refused).

    Logic order:
    1. If the answer contains [Source:] citations, it is substantive — treat
       as valid even if the LLM added hedging/disclaimer language.
    2. If no citations and the LLM used refusal language, honour the refusal.
    3. If no citations and no refusal language, the LLM likely drifted into
       prior knowledge — replace with a refusal to prevent unsupported answers.
    """
    has_citations = check_citations_present(answer)
    has_refusal_language = is_refusal(answer)

    # Citations present → substantive answer, not a refusal
    if has_citations:
        if has_refusal_language:
            logger.info(
                "Answer contains refusal-like language but also has citations — "
                "treating as valid answer (hedging, not a true refusal)"
            )
        return answer, False

    # No citations + refusal language → genuine self-refusal
    if has_refusal_language:
        logger.info("LLM self-refused — answer is a refusal with no citations")
        return answer, True

    # No citations + no refusal language → LLM drifted, enforce refusal
    logger.warning(
        "Citation enforcement triggered — LLM answer had no [Source:] citations. "
        "Replacing with refusal."
    )
    refusal = (
        "The documents provided do not contain sufficient information "
        "to answer this question with confidence."
    )
    return refusal, True
