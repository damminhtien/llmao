"""Summarize the frozen V3.2 benchmark and generate its final report."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from bias_optimizer.optimizer_bench.artifacts import finalize_primary_manifest
from bias_optimizer.optimizer_bench.runner import ROOT, sha256, verify_protocol
from bias_optimizer.optimizer_bench.statistics import plot_primary, summarize_primary
from bias_optimizer.optimizer_bench.trace import read_trace


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _primary_traces(root: Path, protocol: dict[str, Any]) -> tuple:
    manifest_path = root / "results/v32/manifest.json"
    manifest = _load_json(manifest_path)
    digest = sha256(root / "results/v32/protocol.json")
    if manifest["protocol"]["sha256"] != digest:
        raise ValueError("V3.2 manifest does not match the frozen protocol")
    execution = manifest.get("primary_execution", {})
    seed_ids = tuple(
        int(seed)
        for seed in execution.get(
            "matched_analysis_seeds", protocol["budget"]["optimizer_seeds"]
        )
    )
    optimizers = tuple(protocol["primary_optimizers"])
    traces = []
    expected_keys = {(optimizer, seed) for optimizer in optimizers for seed in seed_ids}
    rows = {
        (row["optimizer"], int(row["optimizer_seed"])): row
        for row in manifest.get("runs", [])
        if row.get("phase") == "primary"
        and row.get("optimizer") in optimizers
        and int(row["optimizer_seed"]) in seed_ids
    }
    if set(rows) != expected_keys:
        raise ValueError(
            f"expected {len(expected_keys)} primary runs, found {len(rows)}"
        )
    for optimizer in optimizers:
        for seed in seed_ids:
            item = rows[(optimizer, seed)]
            expected_evaluations = int(
                protocol["budget"]["total_unique_evaluations_per_run"]
            )
            evaluated = int(item["evaluated_candidates"])
            if evaluated > expected_evaluations or (
                item["complete"] and evaluated != expected_evaluations
            ):
                raise ValueError(f"invalid primary run count: {optimizer}, seed {seed}")
            trace_path = root / item["trace"]
            if sha256(trace_path) != item["trace_sha256"]:
                raise ValueError(f"trace hash mismatch: {item['trace']}")
            trace = read_trace(trace_path)
            if (
                trace.complete != item["complete"]
                or len(trace.evaluated_candidates) != evaluated
            ):
                raise ValueError(
                    f"trace status does not match manifest: {item['trace']}"
                )
            if (
                trace.budget_total_evaluations != expected_evaluations
                or trace.budget_seed_evaluations
                != int(protocol["budget"]["seed_evaluations"])
                or trace.budget_max_proposal_attempts
                != int(protocol["budget"]["max_proposal_attempts_per_run"])
                or trace.proposal_attempts > trace.budget_max_proposal_attempts
                or evaluated < int(protocol["budget"]["seed_evaluations"])
            ):
                raise ValueError(f"run violated the frozen search budget: {item['trace']}")
            traces.append(trace)
    return tuple(traces)


def _distribution_text(value: dict[str, Any], digits: int = 4) -> str:
    if value.get("n", 0) == 0:
        return "not available"
    return (
        f"{value['mean']:.{digits}f} (median {value['median']:.{digits}f}; "
        f"SD {value['sd']:.{digits}f}; range {value['min']:.{digits}f}–"
        f"{value['max']:.{digits}f})"
    )


def _primary_tables(summary: dict[str, Any]) -> list[str]:
    lines = [
        "### Final best fitness",
        "",
        "| Optimizer | Complete runs | Best fitness @200 (mean; median; SD; min–max) | Per-seed best or last observed |",
        "|---|---:|---:|---|",
    ]
    for name, optimizer in summary["optimizers"].items():
        per_seed = [
            (
                f"{row['optimizer_seed']}: @200 {row['final_best_fitness']:.4f}"
                if row["complete"]
                else f"{row['optimizer_seed']}: incomplete @ {row['evaluated_candidates']} "
                f"({row['last_observed_best_fitness']:.4f})"
            )
            for row in summary["runs"]
            if row["optimizer"] == name
        ]
        lines.append(
            f"| `{name}` | {optimizer['complete_run_count']}/{optimizer['run_count']} | "
            f"{_distribution_text(optimizer['metrics']['final_best_fitness'])} | "
            f"{'; '.join(per_seed)} |"
        )

    lines.extend(
        [
            "",
            "### Search-curve AUC and top-five mean",
            "",
            "| Optimizer | AUC (mean; SD) | Top-five mean fitness (mean; SD) |",
            "|---|---:|---:|",
        ]
    )
    for name, optimizer in summary["optimizers"].items():
        auc = optimizer["metrics"]["search_curve_auc"]
        top = optimizer["metrics"]["top_5_mean_fitness"]
        lines.append(
            f"| `{name}` | {_distribution_text(auc)} | {_distribution_text(top)} |"
        )

    return lines


def _threshold_table(summary: dict[str, Any]) -> list[str]:
    lines = [
        "For complete runs, `not reached` means no threshold hit by evaluation 200. The complete-run probability is the observed fraction of complete matched runs that reached the threshold. Incomplete-run observations are reported separately as censored hits or non-hits by the last observed evaluation.",
        "",
        "| Optimizer | Threshold | Reached within 200 / complete runs | Evaluations among complete runs that reached | Incomplete-run evidence (censored) |",
        "|---|---|---:|---:|---|",
    ]
    for name, optimizer in summary["optimizers"].items():
        for threshold, details in optimizer["thresholds"].items():
            reached = details["reached_count"]
            total = details["run_count"]
            if reached:
                hit_summary = _distribution_text(
                    details["evaluations_to_threshold"], digits=1
                )
            else:
                hit_summary = "not reached" if total else "not estimable"
            probability = (
                f"{details['probability_reached']:.0%}"
                if details["probability_reached"] is not None
                else "not estimable"
            )
            incomplete_rows = [
                row
                for row in summary["runs"]
                if row["optimizer"] == name and not row["complete"]
            ]
            incomplete_evidence = "; ".join(
                (
                    f"{row['optimizer_seed']}: hit @ {row['evaluations_to_threshold'][threshold]}"
                    if row["evaluations_to_threshold"][threshold] is not None
                    else f"{row['optimizer_seed']}: no hit by {row['last_observed_evaluation_index']}"
                )
                for row in incomplete_rows
            ) or "—"
            lines.append(
                f"| `{name}` | `{threshold}` | {reached}/{total} "
                f"({probability}) | {hit_summary} | "
                f"{incomplete_evidence} |"
            )

    return lines


def _overhead_table(summary: dict[str, Any]) -> list[str]:
    lines = [
        "| Optimizer | Attempts | Valid proposals | Valid rate | Invalid | Duplicates | Duplicate rate | Constraint rejects | LLM calls | LLM tokens | Proposal min/run | Evaluation min/run | Total min/run |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for name, optimizer in summary["optimizers"].items():
        counts = optimizer["mean_overhead_counts"]
        metrics = optimizer["metrics"]
        lines.append(
            f"| `{name}` | {counts['proposal_attempts']:.1f} | "
            f"{counts['valid_proposals']:.1f} | "
            f"{metrics['valid_proposal_rate']['mean']:.1%} | {counts['invalid']:.1f} | "
            f"{counts['duplicates']:.1f} | {metrics['duplicate_rate']['mean']:.1%} | "
            f"{counts['rejected_by_constraint']:.1f} | "
            f"{counts['llm_calls']:.1f} | {counts['llm_tokens']:.0f} | "
            f"{metrics['proposal_time_ms']['mean'] / 60_000:.2f} | "
            f"{metrics['evaluation_time_ms']['mean'] / 60_000:.2f} | "
            f"{metrics['total_wall_time_ms']['mean'] / 60_000:.2f} |"
        )
    return lines


def _paired_table(summary: dict[str, Any]) -> list[str]:
    lines = [
        "| Paired comparison | Metric | Mean difference (first optimizer minus second) | Paired bootstrap 95% interval | Seed wins / paired runs |",
        "|---|---|---:|---:|---:|",
    ]
    for label, details in summary["paired_bootstrap"].items():
        first, second = label.split("_vs_", maxsplit=1)
        for metric, result in details.items():
            if metric in {"left_fitness_wins", "paired_runs"}:
                continue
            interval = result.get("ci_95")
            interval_text = (
                f"[{interval[0]:+.4f}, {interval[1]:+.4f}]"
                if interval
                else "not available"
            )
            mean_delta = result.get("mean_delta")
            mean_text = (
                f"{mean_delta:+.4f}" if mean_delta is not None else "not available"
            )
            first_values = {
                row["optimizer_seed"]: row[metric]
                for row in summary["runs"]
                if row["optimizer"] == first
                and row["complete"]
                and row.get(metric) is not None
            }
            second_values = {
                row["optimizer_seed"]: row[metric]
                for row in summary["runs"]
                if row["optimizer"] == second
                and row["complete"]
                and row.get(metric) is not None
            }
            shared = set(first_values) & set(second_values)
            wins = (
                f"{sum(first_values[seed] > second_values[seed] for seed in shared)}"
                f"/{len(shared)}"
                if shared
                else "not estimable"
            )
            lines.append(
                f"| `{label}` | `{metric}` | {mean_text} | "
                f"{interval_text} | {wins} metric wins |"
            )
    return lines


def _paired_effect(
    summary: dict[str, Any], first: str, second: str, metric: str
) -> tuple[int, float | None, list[float] | None, int]:
    key = f"{first}_vs_{second}"
    reverse = False
    if key not in summary["paired_bootstrap"]:
        key = f"{second}_vs_{first}"
        reverse = True
    pair = summary["paired_bootstrap"].get(key)
    if pair is None:
        return 0, None, None, 0
    result = pair[metric]
    delta = result["mean_delta"]
    interval = result["ci_95"]
    if reverse and delta is not None:
        delta = -delta
    if reverse and interval is not None:
        interval = [-interval[1], -interval[0]]
    first_values = {
        row["optimizer_seed"]: row[metric]
        for row in summary["runs"]
        if row["optimizer"] == first and row["complete"]
    }
    second_values = {
        row["optimizer_seed"]: row[metric]
        for row in summary["runs"]
        if row["optimizer"] == second and row["complete"]
    }
    wins = sum(
        first_values[seed] > second_values[seed]
        for seed in set(first_values) & set(second_values)
    )
    return result["n"], delta, interval, wins


def _hypothesis_table(
    summary: dict[str, Any],
    semantic: dict[str, Any],
    characterization: dict[str, Any],
) -> list[str]:
    lines = [
        "| Hypothesis | Observed evidence |",
        "|---|---|",
    ]
    iterative = summary["optimizers"].get("llm_iterative", {})
    random = summary["optimizers"].get("typed_random", {})
    threshold = "v3_frozen_finalist_floor"
    iterative_threshold = iterative.get("thresholds", {}).get(threshold, {})
    random_threshold = random.get("thresholds", {}).get(threshold, {})

    def incomplete_hits(optimizer: str, threshold_name: str) -> str:
        rows = [
            row
            for row in summary["runs"]
            if row["optimizer"] == optimizer and not row["complete"]
        ]
        return ", ".join(
            (
                f"seed {row['optimizer_seed']} at {row['evaluations_to_threshold'][threshold_name]}"
                if row["evaluations_to_threshold"][threshold_name] is not None
                else f"seed {row['optimizer_seed']} not by {row['last_observed_evaluation_index']}"
            )
            for row in rows
        ) or "no incomplete runs"

    def complete_hit_summary(optimizer: str, threshold_name: str) -> str:
        details = summary["optimizers"][optimizer]["thresholds"][threshold_name]
        if details["reached_count"] == 0:
            return "not reached"
        return _distribution_text(details["evaluations_to_threshold"], digits=1)

    if random.get("complete_run_count", 0) == 0:
        h1 = (
            "The full-budget comparison is not estimable: typed random had "
            f"0/{random.get('run_count', 0)} complete runs. In censored traces, "
            f"random hit the V3 top-20 cutoff at {incomplete_hits('typed_random', 'v3_top_20_cutoff')} "
            f"and V2-best at {incomplete_hits('typed_random', 'v2_best')}; iterative LLM's "
            f"complete runs hit the top-20 cutoff in {complete_hit_summary('llm_iterative', 'v3_top_20_cutoff')} "
            f"and V2-best in {complete_hit_summary('llm_iterative', 'v2_best')}. The finalist floor was reached "
            f"by iterative LLM in {iterative_threshold.get('reached_count', 0)}/"
            f"{iterative_threshold.get('run_count', 0)} runs "
            f"({complete_hit_summary('llm_iterative', 'v3_frozen_finalist_floor')}); "
            f"random did not reach it before stopping ({incomplete_hits('typed_random', 'v3_frozen_finalist_floor')}). "
            "Thus observed efficiency depends on threshold stringency; censored results do not supply a full-budget random estimate."
        )
    else:
        h1 = (
            f"At the finalist-floor threshold, iterative LLM reached it in "
            f"{iterative_threshold.get('reached_count', 0)}/{iterative_threshold.get('run_count', 0)} "
            f"complete runs; random reached it in {random_threshold.get('reached_count', 0)}/"
            f"{random_threshold.get('run_count', 0)}. See the threshold table for evaluations-to-hit."
        )
    lines.append(f"| H1 — search efficiency | {h1} |")

    for hypothesis, comparator, title in (
        ("H2 — value beyond GP", "genetic_programming", "GP"),
        ("H3 — evaluator feedback", "llm_one_shot", "one-shot LLM"),
    ):
        paired_n, delta, interval, wins = _paired_effect(
            summary, "llm_iterative", comparator, "final_best_fitness"
        )
        if paired_n:
            interval_text = (
                f"[{interval[0]:+.4f}, {interval[1]:+.4f}]"
                if interval
                else "not available"
            )
            evidence = (
                f"Iterative minus {title}: mean paired @200 fitness difference "
                f"{delta:+.4f}, bootstrap 95% interval {interval_text}, "
                f"iterative wins in {wins}/{paired_n} paired seeds."
            )
        else:
            evidence = f"No paired complete 200-candidate runs against {title}; full-budget effect is not estimable."
        lines.append(f"| {hypothesis} | {evidence} |")

    semantic_delta = semantic.get("paired_difference", {})
    if semantic_delta.get("mean_delta") is None:
        h4 = "The secondary semantic ablation has no estimable paired result."
    else:
        ci = semantic_delta.get("ci_95")
        interval_text = f"[{ci[0]:+.4f}, {ci[1]:+.4f}]" if ci else "not available"
        h4 = (
            f"Semantic minus anonymized iterative search: mean paired final-fitness "
            f"difference {semantic_delta['mean_delta']:+.4f}, bootstrap 95% interval "
            f"{interval_text}, {semantic_delta.get('semantic_wins', 0)}/"
            f"{semantic_delta.get('paired_runs', 0)} semantic-condition wins."
        )
    lines.append(f"| H4 — semantic prior (secondary) | {h4} |")

    winner_rows = characterization.get("winners", {})
    h5 = (
        f"V3.1 post-search characterization was completed for {len(winner_rows)}/4 "
        "preselected optimizer representatives. See linear/RBF accuracy, HOG "
        "complementarity, dimension, and robustness results in Section 14; these "
        "metrics did not affect search or winner selection."
    )
    lines.append(f"| H5 — scientific usefulness | {h5} |")
    return lines


def _secondary_sections(
    semantic: dict[str, Any], characterization: dict[str, Any]
) -> list[str]:
    lines = [
        "## 13. Semantic ablation",
        "",
        "This secondary lexical-semantic ablation preserves operator signatures, types, parameter constraints, and mathematical behavior. It does not remove all pretrained knowledge.",
        "",
        "| Condition | Final fitness (mean; median; SD; range) | Complete runs | Per-seed outcome | Mean calls / tokens / minutes |",
        "|---|---:|---:|---|---:|",
    ]
    conditions = semantic.get("conditions", {})
    for name in ("semantic_dsl", "anonymized_dsl"):
        row = conditions.get(name, {})
        distribution = row.get("final_best_fitness", {})
        run_rows = [
            item for item in semantic.get("runs", []) if item.get("condition") == name
        ]
        per_seed_text = "; ".join(
            (
                f"{item['optimizer_seed']}: @200 {item['final_best_fitness']:.4f}"
                if item.get("complete")
                else f"{item['optimizer_seed']}: incomplete @ {item['evaluated_candidates']} "
                f"({item.get('last_observed_best_fitness', float('nan')):.4f})"
            )
            for item in sorted(run_rows, key=lambda item: item["optimizer_seed"])
        )
        mean_calls = _mean_field(run_rows, "llm_calls")
        mean_tokens = _mean_field(run_rows, "llm_tokens")
        mean_minutes = _mean_field(run_rows, "total_wall_time_ms", scale=60_000)
        lines.append(
            f"| `{name}` | {_distribution_text(distribution)} | "
            f"{row.get('complete_run_count', 0)}/{len(run_rows)} | "
            f"{per_seed_text or 'not available'} | "
            f"{mean_calls} calls / {mean_tokens} tokens / {mean_minutes} min |"
        )
    delta = semantic.get("paired_difference", {})
    if delta:
        interval = delta.get("ci_95")
        mean_delta = delta.get("mean_delta")
        interval_text = (
            f"[{interval[0]:+.4f}, {interval[1]:+.4f}]" if interval else "not available"
        )
        mean_delta_text = (
            "not available" if mean_delta is None else f"{mean_delta:+.4f}"
        )
        delta_line = (
            f"Paired semantic-minus-anonymized mean difference: `{mean_delta_text}`; "
            f"paired bootstrap interval {interval_text}; "
            f"{delta.get('semantic_wins', 0)}/{delta.get('paired_runs', 0)} seed wins."
        )
        lines.extend(
            [
                "",
                delta_line,
            ]
        )
    else:
        lines.extend(["", "Semantic-ablation paired summary is unavailable."])

    interrupted_attempts = semantic.get("interrupted_attempts", [])
    if interrupted_attempts:
        lines.extend(
            [
                "",
                "Interrupted proposal attempts are shown for cost transparency only. They produced no saved candidate trace and are excluded from fitness estimates and paired comparisons.",
                "",
                "| Condition | Seed | Status | Response records | Requested slots | Distinct ASTs in audit | LLM tokens |",
                "|---|---:|---|---:|---:|---:|---:|",
            ]
        )
        for attempt in interrupted_attempts:
            requested_slots = attempt.get(
                "requested_candidate_slots",
                attempt.get("requested_new_candidate_slots", "—"),
            )
            distinct_asts = attempt.get("distinct_proposal_ast_hashes", "—")
            lines.append(
                f"| `{attempt.get('condition', '—')}` | "
                f"{attempt.get('optimizer_seed', '—')} | "
                f"`{attempt.get('status', 'unknown')}` | "
                f"{attempt.get('response_records', '—')} | {requested_slots} | "
                f"{distinct_asts} | "
                f"{attempt.get('llm_tokens_reported', '—')} |"
            )

    lines.extend(
        [
            "",
            "## 14. V3.1 characterization of optimizer winners",
            "",
            "Each representative was frozen as the highest-primary-fitness winner among the per-run winners included in the matched analysis. Under the runtime fallback, this applies the predeclared rule to the executed matched-seed subset. If the selected run was incomplete, its winner is the best observed candidate at its stopping point, not a 200-evaluation result. Characterization outputs were not fed back into search.",
            "The robustness panel used a predeclared sample of the MNIST official test set only after optimizer search and winner freeze; it was post-search characterization and did not affect search or selection.",
            "",
            "| Optimizer | Winner seed | Search run | Primary fitness | Linear accuracy | RBF accuracy | HOG complementarity (linear) | Dimension | Robustness test |",
            "|---|---:|---|---:|---:|---:|---:|---:|---|",
        ]
    )
    winners = characterization.get("winners", {})
    for name, row in winners.items():
        core = row.get("linear_accuracy", {})
        rbf = row.get("rbf_accuracy", {})
        complementarity = row.get("hog_complementarity_linear", {})
        robustness = row.get("robustness", {})
        run_status = (
            "complete @200"
            if row.get("run_complete")
            else f"incomplete @ {row.get('evaluated_candidates', '—')}"
        )
        lines.append(
            f"| `{name}` | {row.get('optimizer_seed', '—')} | "
            f"{run_status} | "
            f"{row.get('primary_fitness', float('nan')):.4f} | "
            f"{core.get('mean', float('nan')):.4f} ± {core.get('sd', float('nan')):.4f} | "
            f"{rbf.get('mean', float('nan')):.4f} ± {rbf.get('sd', float('nan')):.4f} | "
            f"{complementarity.get('mean_delta', float('nan')):+.4f} | "
            f"{row.get('feature_dim', '—')} | "
            f"{robustness.get('transformation', 'not measured')}: "
            f"{robustness.get('accuracy_drop_mean', float('nan')):+.4f} |"
        )
    behavior = characterization.get("behavioral_diversity", {})
    if behavior:
        lines.extend(
            [
                "",
                "Candidate behavioral novelty was computed after primary search from pairwise feature-distance profiles on a fixed 128-image MNIST validation probe set; labels were not read.",
                "",
                "| Optimizer | Mean behavioral novelty | Mean structural novelty | Mean descriptor cells |",
                "|---|---:|---:|---:|",
            ]
        )
        for name, row in behavior.items():
            behavioral = row.get("behavioral_novelty_mean")
            structural = row.get("structural_novelty_mean")
            cells = row.get("descriptor_cell_coverage_mean")
            lines.append(
                f"| `{name}` | {behavioral:.4f} | "
                f"{structural:.4f} | "
                f"{cells:.1f} |"
                if behavioral is not None and structural is not None and cells is not None
                else f"| `{name}` | {_optional_metric(behavioral)} | "
                f"{_optional_metric(structural)} | {_optional_metric(cells, digits=1)} |"
            )
    return lines


def _optional_metric(value: float | None, *, digits: int = 4) -> str:
    return "not available" if value is None else f"{value:.{digits}f}"


def _mean_field(rows: list[dict[str, Any]], field: str, *, scale: float = 1) -> str:
    values = [float(row[field]) / scale for row in rows if row.get(field) is not None]
    if not values:
        return "not available"
    return f"{sum(values) / len(values):.1f}"


def summarize_primary_artifacts(root: Path = ROOT) -> dict[str, Any]:
    root = Path(root)
    protocol = verify_protocol(root)
    finalize_primary_manifest(root / "results/v32/manifest.json")
    traces = _primary_traces(root, protocol)
    summary = summarize_primary(traces, protocol)
    manifest = _load_json(root / "results/v32/manifest.json")
    execution = manifest.get("primary_execution", {})
    summary["analysis_seed_ids"] = list(
        execution.get("matched_analysis_seeds", protocol["budget"]["optimizer_seeds"])
    )
    summary["protocol_seed_ids"] = [
        int(seed) for seed in protocol["budget"]["optimizer_seeds"]
    ]
    summary["runtime_fallback"] = bool(execution.get("runtime_fallback", False))
    summary["excluded_run_statuses"] = execution.get("excluded_run_statuses", [])
    summary_dir = root / "results/v32/summary"
    summary_dir.mkdir(parents=True, exist_ok=True)
    summary_path = summary_dir / "primary_summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    plot_primary(summary, root / "reports/V3_2_SEARCH_CURVES.png")
    return summary


def generate_report(root: Path = ROOT) -> Path:
    root = Path(root)
    protocol = verify_protocol(root)
    summary_path = root / "results/v32/summary/primary_summary.json"
    figure_path = root / "reports/V3_2_SEARCH_CURVES.png"
    if not summary_path.is_file() or not figure_path.is_file():
        summarize_primary_artifacts(root)
    summary = _load_json(summary_path)
    summary_dir = summary_path.parent

    semantic_path = summary_dir / "semantic_ablation.json"
    characterization_path = summary_dir / "winner_characterization.json"
    if not semantic_path.is_file() or not characterization_path.is_file():
        missing = [
            str(path.relative_to(root))
            for path in (semantic_path, characterization_path)
            if not path.is_file()
        ]
        raise FileNotFoundError(
            "final V3.2 report requires post-search artifacts: " + ", ".join(missing)
        )
    semantic = _load_json(semantic_path)
    characterization = _load_json(characterization_path)

    optimizers = summary["optimizers"]
    score_means = {
        name: optimizer["metrics"]["final_best_fitness"]["mean"]
        for name, optimizer in optimizers.items()
    }
    observed_means = {
        name: value for name, value in score_means.items() if value is not None
    }
    ordering = (
        " > ".join(sorted(observed_means, key=observed_means.get, reverse=True))
        if observed_means
        else "no optimizer has a complete 200-candidate run"
    )
    no_complete = [name for name, value in score_means.items() if value is None]
    excluded_statuses = summary.get("excluded_run_statuses", [])
    not_run_count = sum(
        item.get("status") == "not_run_under_runtime_fallback"
        for item in excluded_statuses
    )
    retained_extra_count = sum(
        item.get("status") == "retained_outside_matched_analysis"
        for item in excluded_statuses
    )
    report_lines = [
        "# V3.2 Optimizer Value Study",
        "",
        "## 1. Research question",
        "",
        f"> {protocol['research_question']}",
        "",
        "V3.2 compares search quality over the frozen V3 typed program space. Candidate search quality is distinct from the final representation quality assessed after search.",
        "",
        "## 2. Why V3.2 followed V3 and V3.1",
        "",
        "V3 established a structured program space and selected candidate programs. V3.1 froze and evaluated those candidates across representation dimensions such as linear and nonlinear probes, HOG complementarity, and robustness. Those results answer whether the selected representations are useful; they do not isolate whether the LLM search procedure was better than conventional optimizers. V3.2 holds the V3 space and stage-one objective fixed to measure that optimizer contribution.",
        "",
        "## 3. Frozen search space and objective",
        "",
        f"- V3 typed DSL primitives and validator; maximum dimension {protocol['frozen_search_space']['constraints']['max_feature_dim']}, depth {protocol['frozen_search_space']['constraints']['max_depth']}, and {protocol['frozen_search_space']['constraints']['max_nodes']} AST nodes.",
        "- Raw-pixel features were prohibited, consistent with the V3 discovery track.",
        "- The exact V3 stage-one objective was reused unchanged: `accuracy_500 - 0.001*log1p(feature_dim) - 0.0001*log1p(runtime_ms)`, where runtime is the V3 sum of feature, training, and inference runtime.",
        "- Each candidate was evaluated on the same 500-example training subset and fixed MNIST validation partition with the same learner. The official test split was not accessed during optimizer search.",
        "- V3.1 HOG-complementarity, robustness, transfer, and multi-probe metrics were excluded from primary fitness.",
        "",
        "## 4. Optimizers",
        "",
        "| Optimizer | Search method |",
        "|---|---|",
        "| `typed_random` | Type-directed AST sampling with frozen depth, primitive, and parameter sampling rules. |",
        "| `genetic_programming` | Typed subtree mutation/crossover, tournament size 3, elitism 2, and a 0.5/0.5 crossover-or-mutation choice. |",
        "| `llm_one_shot` | Frozen local Qwen model and V3 proposal interface; receives DSL/task/constraints and seed examples but no evaluation scores or adaptive history. |",
        "| `llm_iterative` | Same local Qwen model and V3 iterative proposal logic; receives the bounded V3 evidence format and no V3.1 characterization. |",
        "",
        "## 5. Equal-budget protocol",
        "",
        f"The frozen protocol declares {protocol['budget']['seed_evaluations']} shared V3 seed programs and {protocol['budget']['adaptive_new_evaluations']} new evaluations per run, for {protocol['budget']['total_unique_evaluations_per_run']} unique valid evaluated candidates, with protocol seeds `{summary['protocol_seed_ids']}`. The matched execution used seeds `{summary['analysis_seed_ids']}`. The proposal cap was {protocol['budget']['max_proposal_attempts_per_run']} attempts per run. Invalid ASTs and duplicates did not consume evaluation budget; all were counted as overhead. Runs stopping before 200 are marked incomplete, with no increase to the cap. The protocol SHA-256 is `{protocol['protocol_sha256']}`.",
        (
            f"Runtime fallback: local qwen3.5:35b-mlx proposal throughput made the full five-seed execution prohibitive. The primary analysis is restricted to the matched seed subset shown above. Of the {len(excluded_statuses)} excluded optimizer-seed cells, {retained_extra_count} extra runs were retained outside the matched analysis and {not_run_count} runs were not started. Their per-cell statuses are in `results/v32/manifest.json`."
            if summary["runtime_fallback"]
            else "All five predeclared optimizer seeds are included in the primary analysis."
        ),
        "",
        f"Full-budget primary runs: {summary['complete_runs']}/{summary['run_count']}. Among conditions with at least one complete run, mean best-fitness ordering was `{ordering}`; it is descriptive and does not by itself establish a reliable difference.",
        (
            f"No condition-level 200-candidate estimate is available for: {', '.join(f'`{name}`' for name in no_complete)}. Incomplete runs are retained as censored observations and are not counted as full-budget threshold failures."
            if no_complete
            else "All optimizer conditions have at least one complete 200-candidate run."
        ),
        "",
        "## 6. Primary search curves",
        "",
        "The line and shaded min-to-max range are shown only through the longest candidate count reached by every run included for that optimizer; the range is not a confidence interval. This prevents the plotted mean from changing its run composition at the censoring boundary. Incomplete runs are marked at their last observed score in panel C.",
        "",
        "![V3.2 best-so-far search curves and optimizer diagnostics](V3_2_SEARCH_CURVES.png)",
        "",
        "## 7. Final best-fitness results",
        "",
        *_primary_tables(summary),
        "",
        "## 8. Evaluations-to-threshold",
        "",
        "The thresholds were computed from the protected V2/V3 artifacts and frozen before the benchmark. Hit probability uses complete 200-candidate runs. Panel B shows complete-run means as bars and observed hits from incomplete runs as black × marks; the table records incomplete hits and non-hits at their last observed evaluation.",
        "",
        *_threshold_table(summary),
        "",
        "## 9. Validity, duplicates, and cost",
        "",
        *_overhead_table(summary),
        "",
        "Proposal time is separated from oracle evaluation time. Wall time includes both plus runner overhead. This table uses all attempted runs, including incomplete runs, and reports their actual per-run cost. LLM tokens are zero for non-LLM methods and are not an evaluator cost.",
        "",
        "## 10. Diversity and novelty",
        "",
        "The required figure reports five-axis descriptor-cell coverage. The table summarizes complete 200-candidate runs only; incomplete runs are shown as last-observed crosses in the figure and remain available in the raw per-run summary. Structural novelty is the V3 normalized tree-distance score recorded against previously evaluated ASTs. Behavioral novelty is computed post-search from fixed validation probes and is reported below with winner characterization. Novelty is descriptive and is not treated as optimizer quality by itself.",
        "",
        "| Optimizer | Descriptor cells (mean; SD) | Structural novelty (mean; SD) | Feature dimension (mean; SD) | AST depth (mean; SD) | AST nodes (mean; SD) |",
        "|---|---:|---:|---:|---:|---:|",
        *[
            f"| `{name}` | {_distribution_text(optimizer['metrics']['descriptor_cell_coverage'])} | {_distribution_text(optimizer['metrics']['structural_novelty_mean'])} | {_distribution_text(optimizer['metrics']['feature_dimension_mean'])} | {_distribution_text(optimizer['metrics']['ast_depth_mean'])} | {_distribution_text(optimizer['metrics']['ast_node_count_mean'])} |"
            for name, optimizer in summary["optimizers"].items()
        ],
        "",
        "## 11. One-shot versus iterative LLM",
        "",
        f"Paired bootstrap comparisons use matching optimizer-seed indices. There are at most {len(summary['analysis_seed_ids'])} pairs, so intervals and win counts are descriptive; no normal-theory t-test is used.",
        "",
        *_paired_table(summary),
        "",
        "## 12. Random versus GP versus LLM",
        "",
        "All four conditions were assigned the same unique-candidate budget. Runs that stopped at the hard attempt cap are reported as incomplete; their last observed score is not treated as a 200-candidate result. Full-budget pairwise estimates use only paired seeds for which both optimizers completed. The observed order should also be interpreted with the small run count and proposal cost in view.",
        "",
        "Interpretation matrix:",
        "",
        "| Observed pattern | Interpretation |",
        "|---|---|",
        "| Iterative LLM > GP > random | Semantic prior plus feedback appears useful for search efficiency. |",
        "| GP ≈ iterative LLM > random | Structured adaptive search matters, with little added LLM value. |",
        "| One-shot LLM ≈ iterative LLM > GP/random | Pretrained semantic prior helps; feedback adds little. |",
        "| Iterative LLM > one-shot LLM but ≈ GP | Feedback matters, without a unique LLM advantage. |",
        "| Random ≈ GP ≈ LLM | The space may be easy or the LLM may be unnecessary. |",
        "| Random > LLM | The LLM prior may favor familiar but suboptimal regions. |",
        "",
        *_secondary_sections(semantic, characterization),
        "",
        "## 15. Threats to validity",
        "",
        f"- The matched primary analysis uses {len(summary['analysis_seed_ids'])} seed(s) per optimizer because of the recorded runtime fallback; paired bootstrap intervals are highly uncertain at this sample size.",
        "- Wall-clock cost depends on local model and hardware state. The candidate-evaluation budget is the primary fairness unit.",
        "- The fixed 500-example evaluator is a search proxy; V3.1 characterization addresses only preselected dimensions and winners.",
        "- Random sampling, GP operators, and prompt behavior each encode design choices even though their settings were frozen before outcomes.",
        "- Semantic anonymization removes lexical operator cues only as far as the preserved DSL contract allows; it does not erase all pretrained knowledge.",
        "- The study covers this V3 program space and task, not optimizers or domains in general.",
        "",
        "## 16. What the LLM actually contributed",
        "",
        "The empirical contribution is the observed difference, if any, between one-shot and feedback-guided LLM search, plus their paired differences from typed GP and typed random search. The score, overhead, and characterization tables report those outcomes directly. A negative or near-zero result is a valid answer and does not indicate a failed study.",
        "",
        *_hypothesis_table(summary, semantic, characterization),
        "",
        "## 17. Claim boundary",
        "",
        "The strongest allowed claim, if iterative LLM search consistently wins, is: **Under the frozen V3 typed program space and equal candidate-evaluation budget, iterative LLM-guided search reaches high-performing regions more efficiently than the tested random and genetic-programming baselines.**",
        "",
        "This result does not establish that LLMs are generally superior optimizers, that the LLM invented new inductive biases, or that the LLM performed scientific discovery.",
        "",
        f"Protocol: `results/v32/protocol.json` (`{protocol['protocol_sha256']}`). Primary summary: `results/v32/summary/primary_summary.json`.",
    ]
    report_path = root / "reports/V3_2_OPTIMIZER_VALUE.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    return report_path


def main() -> None:
    print(generate_report())


if __name__ == "__main__":
    main()
