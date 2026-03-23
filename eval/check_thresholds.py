#!/usr/bin/env python3
"""
CI gate: fail with exit code 1 if any metric is below threshold.
Usage: python eval/check_thresholds.py eval/results/latest.json
"""
import json
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

THRESHOLDS = {
    "faithfulness": 0.75,
    "context_precision": 0.75,
    "answer_relevancy": 0.75,
    "refusal_accuracy": 0.85,
}


def main() -> None:
    results_path = (
        Path(sys.argv[1])
        if len(sys.argv) > 1
        else Path("eval/results/latest.json")
    )

    if not results_path.exists():
        logger.error("Results file not found: %s", results_path)
        sys.exit(2)

    with open(results_path, encoding="utf-8") as f:
        results = json.load(f)

    ragas = results.get("ragas", {})
    refusal = results.get("refusal", {})

    scores = {
        "faithfulness": ragas.get("faithfulness"),
        "context_precision": ragas.get("context_precision"),
        "answer_relevancy": ragas.get("answer_relevancy"),
        "refusal_accuracy": refusal.get("refusal_accuracy"),
    }

    print("\n── Threshold Check ───────────────────")
    failed = False
    for metric, threshold in THRESHOLDS.items():
        score = scores.get(metric)
        if score is None:
            print(f"  {metric}: SKIP (no data)")
            continue
        status = "PASS ✓" if score >= threshold else "FAIL ✗"
        print(f"  {metric}: {score:.3f} (threshold: {threshold}) — {status}")
        if score < threshold:
            failed = True

    if failed:
        print("\nEvaluation FAILED — metrics below threshold. Blocking PR.")
        sys.exit(1)
    else:
        print("\nAll thresholds passed.")
        sys.exit(0)


if __name__ == "__main__":
    main()
