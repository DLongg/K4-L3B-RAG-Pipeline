"""Reproducible A/B evaluation for dense-only versus hybrid + RRF.

The script writes a checkpoint after every generated answer and every metric so a
Gemini quota/network error does not discard completed work.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
import sys
import time
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from src.task10_generation import SYSTEM_PROMPT, call_llm, format_context, reorder_for_llm
from src.task5_semantic_search import semantic_search
from src.task6_lexical_search import lexical_search
from src.task7_reranking import rerank_rrf

GOLDEN_PATH = ROOT / "group_project/evaluation/golden_dataset.json"
DEFAULT_OUTPUT = ROOT / "group_project/evaluation/evaluation_results.json"


def retrieve_config(question: str, config: str, top_k: int = 5) -> list[dict]:
    dense = semantic_search(question, top_k=top_k * 2)
    if config == "dense":
        return dense[:top_k]
    sparse = lexical_search(question, top_k=top_k * 2)
    return rerank_rrf([dense, sparse], top_k=top_k)


def generate_answer(question: str, chunks: list[dict]) -> str:
    labelled = [{**chunk, "_citation_index": i} for i, chunk in enumerate(chunks, 1)]
    context = format_context(reorder_for_llm(labelled))
    message = f"Context:\n{context}\n\nQuestion: {question}"
    last_error = None
    for attempt in range(2):
        try:
            return call_llm(SYSTEM_PROMPT, message).strip()
        except Exception as error:
            last_error = error
            if attempt == 0:
                time.sleep(2)
    raise last_error


def save(payload: dict, path: Path) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def make_metrics():
    """Create Ragas 0.4 metrics with a compatibility bridge for sync Gemini.

    Ragas collection metrics call ``agenerate``. The google-genai Instructor
    adapter in Ragas 0.4.3 detects a sync client, so its sync ``generate`` is
    safely dispatched to a worker thread.
    """
    from google import genai
    from ragas.embeddings import HuggingFaceEmbeddings
    from ragas.llms import llm_factory
    from ragas.metrics.collections import (
        AnswerRelevancy,
        ContextPrecisionWithReference,
        ContextRecall,
        Faithfulness,
    )

    api_key = os.environ["GEMINI_API_KEY"]
    model = os.environ["LLM_MODEL"]
    llm = llm_factory(model, provider="google", client=genai.Client(api_key=api_key))
    sync_generate = llm.generate

    async def agenerate(self, prompt, response_model):
        return await asyncio.to_thread(sync_generate, prompt, response_model)

    llm.agenerate = types.MethodType(agenerate, llm)
    embeddings = HuggingFaceEmbeddings(
        os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3"), device="cpu"
    )
    return {
        "faithfulness": Faithfulness(llm=llm),
        "answer_relevance": AnswerRelevancy(llm=llm, embeddings=embeddings, strictness=1),
        "context_recall": ContextRecall(llm=llm),
        "context_precision": ContextPrecisionWithReference(llm=llm),
    }


async def score_case(metrics: dict, row: dict, checkpoint, metric_delay: float) -> None:
    common = {
        "user_input": row["question"],
        "response": row["answer"],
        "retrieved_contexts": row["contexts"],
        "reference": row["reference"],
    }
    arguments = {
        "faithfulness": {k: common[k] for k in ("user_input", "response", "retrieved_contexts")},
        "answer_relevance": {k: common[k] for k in ("user_input", "response")},
        "context_recall": {k: common[k] for k in ("user_input", "retrieved_contexts", "reference")},
        "context_precision": {k: common[k] for k in ("user_input", "retrieved_contexts", "reference")},
    }
    row.setdefault("metrics", {})
    row.setdefault("metric_errors", {})
    for name, metric in metrics.items():
        if row["metrics"].get(name) is not None:
            continue
        try:
            result = await metric.ascore(**arguments[name])
            row["metrics"][name] = float(result.value)
            row["metric_errors"].pop(name, None)
        except Exception as error:  # persist provider/quota failures for audit
            row["metrics"][name] = None
            row["metric_errors"][name] = f"{type(error).__name__}: {error}"
        checkpoint()
        if metric_delay:
            await asyncio.sleep(metric_delay)


def aggregate(payload: dict) -> None:
    summary = {}
    for config, rows in payload["results"].items():
        if not rows:
            summary[config] = {
                "case_count": 0,
                "metric_means": {},
                "macro_average": None,
                "mean_retrieval_ms": None,
                "mean_generation_ms": None,
            }
            continue
        values = {name: [] for name in ("faithfulness", "answer_relevance", "context_recall", "context_precision")}
        for row in rows:
            for name, value in row.get("metrics", {}).items():
                if value is not None:
                    values[name].append(value)
        metric_means = {
            name: (statistics.fmean(scores) if scores else None)
            for name, scores in values.items()
        }
        completed = [value for value in metric_means.values() if value is not None]
        summary[config] = {
            "case_count": len(rows),
            "metric_means": metric_means,
            "macro_average": statistics.fmean(completed) if completed else None,
            "mean_retrieval_ms": statistics.fmean(row["retrieval_ms"] for row in rows),
            "mean_generation_ms": statistics.fmean(row["generation_ms"] for row in rows),
        }
    payload["summary"] = summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--skip-metrics", action="store_true")
    parser.add_argument(
        "--generation-delay", type=float, default=4.2,
        help="Seconds between generated answers; default respects 15 RPM.",
    )
    parser.add_argument(
        "--metric-delay", type=float, default=8.0,
        help="Seconds between metrics; default respects Gemini free-tier RPM.",
    )
    args = parser.parse_args()

    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    if args.limit:
        golden = golden[: args.limit]
    payload = {
        "run": {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "ragas_version": __import__("ragas").__version__,
            "generator_and_evaluator": os.getenv("LLM_MODEL"),
            "embedding_model": os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3"),
            "top_k": 5,
            "answer_relevance_strictness": 1,
        },
        "results": {"dense": [], "hybrid_rrf": []},
    }
    if args.output.exists():
        existing = json.loads(args.output.read_text(encoding="utf-8"))
        if existing.get("run", {}).get("generator_and_evaluator") == payload["run"]["generator_and_evaluator"]:
            payload = existing

    def checkpoint():
        aggregate(payload)
        save(payload, args.output)

    for config in ("dense", "hybrid_rrf"):
        rows = payload["results"][config]
        existing_rows = {row["question"]: row for row in rows}
        for case in golden:
            existing = existing_rows.get(case["question"])
            if existing and existing.get("answer") and not existing.get("generation_error"):
                continue
            start = time.perf_counter()
            chunks = retrieve_config(case["question"], config)
            retrieval_ms = (time.perf_counter() - start) * 1000
            start = time.perf_counter()
            generation_error = None
            try:
                answer = generate_answer(case["question"], chunks)
            except Exception as error:
                answer = ""
                generation_error = f"{type(error).__name__}: {error}"
            generation_ms = (time.perf_counter() - start) * 1000
            updated = {
                "question": case["question"],
                "reference": case["expected_answer"],
                "expected_context": case["expected_context"],
                "answer": answer,
                "contexts": [chunk["content"] for chunk in chunks],
                "sources": [chunk.get("metadata", {}).get("source") for chunk in chunks],
                "retrieval_ms": retrieval_ms,
                "generation_ms": generation_ms,
                "generation_error": generation_error,
            }
            if existing:
                existing.update(updated)
            else:
                rows.append(updated)
            checkpoint()
            print(f"generated {config}: {len(rows)}/{len(golden)}", flush=True)
            if args.generation_delay:
                time.sleep(args.generation_delay)

    if not args.skip_metrics:
        metrics = make_metrics()

        async def evaluate_all():
            for config, rows in payload["results"].items():
                for index, row in enumerate(rows, 1):
                    if not row.get("answer"):
                        continue
                    await score_case(metrics, row, checkpoint, args.metric_delay)
                    print(f"scored {config}: {index}/{len(rows)}", flush=True)

        asyncio.run(evaluate_all())
    checkpoint()
    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
