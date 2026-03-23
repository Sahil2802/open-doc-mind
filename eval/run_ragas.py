#!/usr/bin/env python3
"""
Run RAGAS evaluation against the golden set.
Uses the live RAG backend to generate answers, then evaluates with RAGAS.

Compatible with RAGAS >=0.4.x (uses llm_factory + instantiated metric objects).

Usage:
    python eval/run_ragas.py
    python eval/run_ragas.py --output eval/results/latest.json
"""
import json
import os
import argparse
import asyncio
import logging
import math
from pathlib import Path
from datetime import datetime, timezone

import httpx
from dotenv import load_dotenv

EVAL_DIR = Path(__file__).resolve().parent
REPO_ROOT = EVAL_DIR.parent

# Load environment variables from backend/.env or .env
load_dotenv(REPO_ROOT / "backend" / ".env")
load_dotenv(REPO_ROOT / ".env")

# RAGAS imports (0.4.x API)
from openai import AsyncOpenAI
from ragas.llms import llm_factory
from langchain_community.embeddings import HuggingFaceEmbeddings as LCHuggingFaceEmbeddings
from ragas.metrics import faithfulness, answer_relevancy, context_precision
from ragas import evaluate
from ragas.run_config import RunConfig
from datasets import Dataset

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

GOLDEN_SET_PATH = EVAL_DIR / "golden_set.json"
API_BASE = "http://localhost:8000"

# Groq is OpenAI-compatible — use its base URL with the OpenAI client
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_MODEL = "llama-3.1-8b-instant"

REFUSAL_PHRASES = [
    "i couldn't find sufficient information",
    "the documents provided do not contain",
    "i don't have enough information",
    "not mentioned in the provided",
    "cannot be found in the documents",
]


def _looks_like_refusal(answer: str) -> bool:
    lower = answer.lower()
    return any(phrase in lower for phrase in REFUSAL_PHRASES)


def _build_eval_embeddings():
    """Create embeddings compatible with legacy answer_relevancy metric APIs."""
    return LCHuggingFaceEmbeddings(model_name="BAAI/bge-small-en-v1.5")


def _build_eval_llm(max_tokens: int):
    """Create a RAGAS-compatible LLM using Groq's OpenAI-compatible API."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Add it to backend/.env or export it."
        )
    client = AsyncOpenAI(
        api_key=api_key,
        base_url=GROQ_BASE_URL,
    )
    return llm_factory(
        GROQ_MODEL,
        client=client,
        temperature=0.0,
        max_tokens=max_tokens,
    )


def load_golden_set() -> list[dict]:
    """Load and validate the golden set JSON file."""
    if not GOLDEN_SET_PATH.exists():
        raise FileNotFoundError(
            f"Golden set not found at {GOLDEN_SET_PATH}. "
            "Create it before running evaluation."
        )
    with open(GOLDEN_SET_PATH, encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list) or len(data) == 0:
        raise ValueError("Golden set must be a non-empty JSON array.")

    # Basic schema validation
    required_keys = {"id", "question", "ground_truth"}
    for i, item in enumerate(data):
        missing = required_keys - set(item.keys())
        if missing:
            raise ValueError(
                f"Golden set item {i} (id={item.get('id', '?')}) "
                f"missing required keys: {missing}"
            )
    return data


async def get_rag_response(
    question: str, client: httpx.AsyncClient
) -> dict:
    """Call the RAG API and collect the full streamed response."""
    answer_parts: list[str] = []
    contexts: list[str] = []
    was_refused = False

    async with client.stream(
        "POST",
        f"{API_BASE}/api/query",
        json={"query": question},
        timeout=60.0,
    ) as response:
        response.raise_for_status()
        current_event = ""
        async for line in response.aiter_lines():
            if line.startswith("event: "):
                current_event = line[7:].strip()
            elif line.startswith("data: "):
                data_str = line[6:].strip()
                try:
                    data = json.loads(data_str)
                    if current_event == "token":
                        answer_parts.append(data["text"])
                    elif current_event == "replace":
                        answer_parts = [data["text"]]
                        was_refused = True
                    elif current_event == "refused":
                        answer_parts = [data.get("text", "")]
                        was_refused = True
                    elif current_event == "citations":
                        # Prefer full retrieved chunk text for RAGAS context metrics.
                        extracted_contexts: list[str] = []
                        for citation in data:
                            chunk_text = (citation.get("chunk_text") or "").strip()
                            if chunk_text:
                                extracted_contexts.append(chunk_text)
                                continue
                            file_name = citation.get("file_name", "unknown")
                            page_number = citation.get("page_number", "N/A")
                            extracted_contexts.append(
                                f"[Source: {file_name}, p.{page_number}]"
                            )
                        # Deduplicate while preserving order.
                        contexts = list(dict.fromkeys(extracted_contexts))
                except (json.JSONDecodeError, KeyError) as exc:
                    logger.debug("Skipping unparseable SSE data: %s", exc)

    full_answer = "".join(answer_parts)
    if not was_refused and _looks_like_refusal(full_answer):
        was_refused = True

    return {
        "answer": full_answer,
        "contexts": contexts,
        "was_refused": was_refused,
    }


async def collect_responses(golden_set: list[dict]) -> list[dict]:
    """Run all golden questions through the RAG system."""
    results: list[dict] = []
    async with httpx.AsyncClient() as client:
        for item in golden_set:
            question_preview = item["question"][:60]
            logger.info("  Running: %s — %s...", item["id"], question_preview)
            try:
                response = await get_rag_response(item["question"], client)
                results.append(
                    {
                        "id": item["id"],
                        "question": item["question"],
                        "ground_truth": item["ground_truth"],
                        "answer": response["answer"],
                        "contexts": response["contexts"],
                        "was_refused": response["was_refused"],
                        "category": item.get("category", "unknown"),
                        "difficulty": item.get("difficulty", "unknown"),
                        "should_refuse": item["ground_truth"] == "UNANSWERABLE",
                    }
                )
            except Exception as exc:
                logger.error("  ERROR on %s: %s", item["id"], exc)
                results.append(
                    {
                        "id": item["id"],
                        "question": item["question"],
                        "ground_truth": item["ground_truth"],
                        "answer": f"ERROR: {exc}",
                        "contexts": [],
                        "was_refused": False,
                        "category": item.get("category", "unknown"),
                        "difficulty": item.get("difficulty", "unknown"),
                        "should_refuse": item["ground_truth"] == "UNANSWERABLE",
                    }
                )
    return results


def run_ragas_evaluation(
    responses: list[dict],
    eval_max_workers: int,
    eval_max_retries: int,
    eval_max_wait: int,
    eval_max_tokens: int,
) -> dict:
    """Compute RAGAS metrics on the collected responses (RAGAS 0.4.x API)."""
    # Filter out questions that should trigger refusals — RAGAS can't evaluate these
    evaluable = [r for r in responses if not r["should_refuse"]]

    if not evaluable:
        logger.warning("No evaluable responses (all were expected refusals)")
        return {}

    dataset = Dataset.from_dict(
        {
            "user_input": [r["question"] for r in evaluable],
            "response": [r["answer"] for r in evaluable],
            "retrieved_contexts": [r["contexts"] for r in evaluable],
            "reference": [r["ground_truth"] for r in evaluable],
        }
    )

    # Build the eval LLM via Groq's OpenAI-compatible endpoint
    eval_llm = _build_eval_llm(max_tokens=eval_max_tokens)
    eval_embeddings = _build_eval_embeddings()
    run_config = RunConfig(
        max_workers=eval_max_workers,
        max_retries=eval_max_retries,
        max_wait=eval_max_wait,
    )

    # Use legacy metric instances that are compatible with evaluate() in this RAGAS version
    metrics = [
        faithfulness,
        answer_relevancy,
        context_precision,
    ]
    # Reduce generations per sample for lower TPM usage and fewer truncation failures.
    answer_relevancy.strictness = 1

    result = evaluate(
        dataset=dataset,
        metrics=metrics,
        llm=eval_llm,
        embeddings=eval_embeddings,
        run_config=run_config,
        batch_size=1,
        raise_exceptions=False,
    )

    # RAGAS can return either an aggregate dict (older behavior) or an EvaluationResult
    # object with per-sample `scores` rows. Normalize both into metric -> float.
    if hasattr(result, "scores") and isinstance(result.scores, list):
        aggregated: dict[str, float] = {}
        if result.scores:
            metric_names = result.scores[0].keys()
            for metric_name in metric_names:
                values = [
                    row.get(metric_name)
                    for row in result.scores
                    if isinstance(row.get(metric_name), (int, float))
                    and not math.isnan(float(row.get(metric_name)))
                ]
                aggregated[metric_name] = (
                    float(sum(values) / len(values)) if values else None
                )
        result_dict = aggregated
    elif isinstance(result, dict):
        result_dict = result
    else:
        raise TypeError(
            f"Unsupported RAGAS evaluation result type: {type(result).__name__}"
        )

    # Normalize keys for downstream compatibility
    scores = {}
    for key, value in result_dict.items():
        if key == "faithfulness":
            scores["faithfulness"] = value
        elif key in ("answer_relevancy", "response_relevancy"):
            scores["answer_relevancy"] = value
        elif "context_precision" in key:
            scores["context_precision"] = value
        else:
            scores[key] = value

    return scores


def compute_refusal_accuracy(responses: list[dict]) -> dict:
    """
    Measure how accurately the system handles out-of-scope questions.
    Correct: should_refuse=True AND was_refused=True
    """
    should_refuse = [r for r in responses if r["should_refuse"]]
    if not should_refuse:
        return {"refusal_accuracy": None, "refusal_total": 0}

    correct_refusals = sum(1 for r in should_refuse if r["was_refused"])
    return {
        "refusal_accuracy": correct_refusals / len(should_refuse),
        "correct_refusals": correct_refusals,
        "refusal_total": len(should_refuse),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run RAGAS evaluation against the golden set."
    )
    parser.add_argument(
        "--output",
        default=str(EVAL_DIR / "results" / "latest.json"),
        help="Path to write the evaluation results JSON.",
    )
    parser.add_argument(
        "--eval-max-workers",
        type=int,
        default=1,
        help="Max concurrent RAGAS workers (lower reduces rate-limit pressure).",
    )
    parser.add_argument(
        "--eval-max-retries",
        type=int,
        default=8,
        help="Max retries per RAGAS LLM call.",
    )
    parser.add_argument(
        "--eval-max-wait",
        type=int,
        default=30,
        help="Max exponential backoff wait in seconds for RAGAS retries.",
    )
    parser.add_argument(
        "--eval-max-tokens",
        type=int,
        default=256,
        help="Max completion tokens per RAGAS LLM call.",
    )
    args = parser.parse_args()

    logger.info("Loading golden set...")
    golden_set = load_golden_set()
    logger.info("  %d questions loaded", len(golden_set))

    logger.info("Collecting RAG responses...")
    responses = asyncio.run(collect_responses(golden_set))

    logger.info("Running RAGAS evaluation...")
    ragas_scores = run_ragas_evaluation(
        responses,
        eval_max_workers=args.eval_max_workers,
        eval_max_retries=args.eval_max_retries,
        eval_max_wait=args.eval_max_wait,
        eval_max_tokens=args.eval_max_tokens,
    )

    refusal_stats = compute_refusal_accuracy(responses)

    results = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_questions": len(golden_set),
        "evaluable_questions": len(
            [r for r in responses if not r["should_refuse"]]
        ),
        "ragas": ragas_scores,
        "refusal": refusal_stats,
        "responses": responses,
    }

    print("\n── Results ───────────────────────────")
    for metric in ("faithfulness", "context_precision", "answer_relevancy"):
        score = ragas_scores.get(metric)
        print(f"  {metric}: {score:.3f}" if score is not None else f"  {metric}: N/A")
    if refusal_stats["refusal_total"] > 0:
        print(
            f"  Refusal Accuracy:  {refusal_stats['refusal_accuracy']:.3f} "
            f"({refusal_stats['correct_refusals']}/{refusal_stats['refusal_total']})"
        )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    logger.info("Full results saved to: %s", args.output)


if __name__ == "__main__":
    main()
