"""Freeze or run the predeclared V3.2 LLM lexical-semantic ablation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from bias_optimizer.llm.ollama_client import OllamaLLMClient
from bias_optimizer.optimizer_bench.runner import ROOT, run_optimizer, verify_protocol
from bias_optimizer.optimizer_bench.semantic_ablation import (
    AnonymizedOllamaClient,
    freeze_semantic_protocol,
    load_semantic_protocol,
)


def _primary_is_frozen(root: Path) -> None:
    verify_protocol(root)
    manifest = json.loads((root / "results/v32/manifest.json").read_text())
    if manifest.get("status") not in {
        "primary_complete",
        "primary_finished_with_incomplete_runs",
        "primary_finished_with_runtime_fallback",
    }:
        raise ValueError("semantic ablation can start only after primary runs freeze")


def run_ablation(root: Path = ROOT) -> list[dict[str, object]]:
    root = Path(root)
    _primary_is_frozen(root)
    protocol, lexical_map = load_semantic_protocol(root)
    manifest_path = root / "results/v32/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    completed = {
        (row.get("condition"), int(row["optimizer_seed"]))
        for row in manifest.get("runs", [])
        if row.get("phase") == "semantic_ablation" and row.get("trace")
    }
    results: list[dict[str, object]] = []
    for condition in protocol["conditions"]:
        output_root = root / "results/v32/runs/semantic_ablation" / condition
        for seed in protocol["optimizer_seeds"]:
            key = (condition, int(seed))
            if key in completed:
                results.append(
                    {"condition": condition, "seed": seed, "status": "already_recorded"}
                )
                continue
            run_dir = output_root / "llm_iterative" / f"seed_{seed}"
            if condition == "semantic_dsl":
                client = OllamaLLMClient.from_environment()
            else:
                interactions = run_dir / "actual_llm_interactions.jsonl"
                if interactions.exists():
                    interactions.unlink()
                client = AnonymizedOllamaClient(
                    OllamaLLMClient.from_environment(), lexical_map, interactions
                )
            trace = run_optimizer(
                "llm_iterative",
                int(seed),
                output_root=output_root,
                phase="semantic_ablation",
                condition=condition,
                client=client,
            )
            results.append(
                {
                    "condition": condition,
                    "seed": seed,
                    "status": "complete" if trace.complete else "incomplete",
                    "evaluated_candidates": len(trace.evaluated_candidates),
                    "proposal_attempts": trace.proposal_attempts,
                }
            )
    print(json.dumps(results, indent=2))
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--freeze-only", action="store_true")
    group.add_argument("--run", action="store_true")
    args = parser.parse_args()
    if args.freeze_only:
        _primary_is_frozen(args.root)
        path, digest = freeze_semantic_protocol(args.root)
        print(json.dumps({"protocol": str(path), "sha256": digest}, indent=2))
    else:
        run_ablation(args.root)


if __name__ == "__main__":
    main()
