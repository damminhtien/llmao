"""Predeclared search-curve and small-sample paired-bootstrap summaries."""

from __future__ import annotations

import statistics
from pathlib import Path
from typing import Any

import numpy as np

from bias_optimizer.dsl.validator import infer_type
from bias_optimizer.optimizer_bench.schema import CandidateEvaluation, SearchTrace


def _distribution(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {
            "n": 0,
            "mean": None,
            "median": None,
            "sd": None,
            "min": None,
            "max": None,
        }
    return {
        "n": len(values),
        "mean": float(statistics.mean(values)),
        "median": float(statistics.median(values)),
        "sd": float(statistics.stdev(values)) if len(values) > 1 else 0.0,
        "min": float(min(values)),
        "max": float(max(values)),
    }


def _curve_for_run(
    rows: tuple[CandidateEvaluation, ...], indices: tuple[int, ...]
) -> list[float | None]:
    ordered = sorted(rows, key=lambda row: row.evaluation_index)
    best = float("-inf")
    result: list[float | None] = []
    cursor = 0
    for index in indices:
        while cursor < len(ordered) and ordered[cursor].evaluation_index <= index:
            best = max(best, ordered[cursor].fitness)
            cursor += 1
        result.append(best if index <= len(ordered) else None)
    return result


def _auc(indices: tuple[int, ...], curve: list[float]) -> float:
    if len(indices) != len(curve) or len(indices) < 2:
        raise ValueError("AUC requires an aligned curve with at least two points")
    return float(
        sum(
            (curve[index] + curve[index - 1])
            * 0.5
            * (indices[index] - indices[index - 1])
            for index in range(1, len(indices))
        )
    )


def _first_hit(rows: tuple[CandidateEvaluation, ...], threshold: float) -> int | None:
    best = float("-inf")
    for row in sorted(rows, key=lambda item: item.evaluation_index):
        best = max(best, row.fitness)
        if row.evaluation_index >= 20 and best >= threshold:
            return row.evaluation_index
    return None


def _paired_bootstrap(
    left: dict[int, float],
    right: dict[int, float],
    *,
    seed: int,
    resamples: int = 10_000,
) -> dict[str, Any]:
    shared = sorted(set(left) & set(right))
    if not shared:
        return {"n": 0, "mean_delta": None, "median_delta": None, "ci_95": None}
    differences = np.asarray(
        [left[index] - right[index] for index in shared], dtype=np.float64
    )
    rng = np.random.default_rng(seed)
    draw_indices = rng.integers(0, len(differences), size=(resamples, len(differences)))
    draws = differences[draw_indices].mean(axis=1)
    return {
        "n": len(shared),
        "mean_delta": float(differences.mean()),
        "median_delta": float(np.median(differences)),
        "ci_95": [float(value) for value in np.quantile(draws, (0.025, 0.975))],
        "paired_seed_indices": shared,
        "resamples": resamples,
        "bootstrap_seed": seed,
    }


def _run_summary(
    trace: SearchTrace,
    indices: tuple[int, ...],
    thresholds: dict[str, float],
) -> dict[str, Any]:
    rows = trace.evaluated_candidates
    curve = _curve_for_run(rows, indices)
    top = sorted((row.fitness for row in rows), reverse=True)[:5]
    depths = [infer_type(row.program).depth for row in rows if row.program is not None]
    nodes = [
        infer_type(row.program).node_count for row in rows if row.program is not None
    ]
    dimensions = [row.feature_dim for row in rows]
    cells = ["/".join(row.structural_descriptor) for row in rows]
    novelty = [
        float(row.metadata["structural_novelty"])
        for row in rows
        if row.metadata is not None and "structural_novelty" in row.metadata
    ]
    hits = {name: _first_hit(rows, value) for name, value in thresholds.items()}
    return {
        "optimizer": trace.optimizer,
        "optimizer_seed": trace.optimizer_seed,
        "complete": trace.complete,
        "evaluated_candidates": len(rows),
        "final_best_fitness": (
            max((row.fitness for row in rows), default=None) if trace.complete else None
        ),
        "last_observed_best_fitness": max((row.fitness for row in rows), default=None),
        "last_observed_evaluation_index": len(rows),
        "search_curve_auc": (
            _auc(indices, [float(value) for value in curve])
            if trace.complete and all(value is not None for value in curve)
            else None
        ),
        "best_so_far": curve,
        "evaluations_to_threshold": hits,
        "probability_threshold_reached": {
            name: hit is not None for name, hit in hits.items()
        },
        "top_5_mean_fitness": (
            float(statistics.mean(top)) if top and trace.complete else None
        ),
        "descriptor_cell_coverage": len(set(cells)),
        "structural_novelty_mean": float(statistics.mean(novelty)) if novelty else None,
        "feature_dimension": _distribution([float(value) for value in dimensions]),
        "ast_depth": _distribution([float(value) for value in depths]),
        "ast_node_count": _distribution([float(value) for value in nodes]),
        "overhead": {
            "proposal_attempts": trace.proposal_attempts,
            "valid_proposals": trace.valid_proposal_count,
            "invalid": trace.invalid_count,
            "duplicates": trace.duplicate_count,
            "rejected_by_constraint": trace.rejected_by_constraint_count,
            "valid_proposal_rate": (
                trace.valid_proposal_count / trace.proposal_attempts
                if trace.proposal_attempts
                else 0.0
            ),
            "duplicate_rate": (
                trace.duplicate_count / trace.proposal_attempts
                if trace.proposal_attempts
                else 0.0
            ),
            "llm_calls": trace.llm_calls,
            "llm_tokens": trace.llm_tokens,
            "proposal_time_ms": trace.proposal_time_ms,
            "evaluation_time_ms": trace.evaluation_time_ms,
            "total_wall_time_ms": trace.total_wall_time_ms,
            "termination_reason": trace.termination_reason,
        },
    }


def summarize_primary(
    traces: tuple[SearchTrace, ...], protocol: dict[str, Any]
) -> dict[str, Any]:
    if not traces:
        raise ValueError("primary traces cannot be empty")
    indices = tuple(protocol["primary_metrics"]["search_curve_indices"])
    thresholds = {
        name: float(value["value"])
        for name, value in protocol["primary_metrics"]["thresholds"].items()
    }
    runs = [_run_summary(trace, indices, thresholds) for trace in traces]
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in runs:
        grouped.setdefault(row["optimizer"], []).append(row)
    summaries: dict[str, Any] = {}
    for optimizer, rows in sorted(grouped.items()):
        complete_rows = [row for row in rows if row["complete"]]
        curve_matrix = np.asarray(
            [
                [np.nan if value is None else value for value in row["best_so_far"]]
                for row in rows
            ],
            dtype=np.float64,
        )
        counts_by_index = np.isfinite(curve_matrix).sum(axis=0)
        curve_mean: list[float | None] = []
        curve_min: list[float | None] = []
        curve_max: list[float | None] = []
        for index, count in enumerate(counts_by_index):
            if count == 0:
                curve_mean.append(None)
                curve_min.append(None)
                curve_max.append(None)
                continue
            values = curve_matrix[np.isfinite(curve_matrix[:, index]), index]
            curve_mean.append(float(values.mean()))
            curve_min.append(float(values.min()))
            curve_max.append(float(values.max()))
        metrics = {
            "final_best_fitness": [row["final_best_fitness"] for row in complete_rows],
            "incomplete_last_observed_best_fitness": [
                row["last_observed_best_fitness"] for row in rows if not row["complete"]
            ],
            "incomplete_descriptor_cell_coverage": [
                float(row["descriptor_cell_coverage"])
                for row in rows
                if not row["complete"]
            ],
            "incomplete_structural_novelty_mean": [
                row["structural_novelty_mean"]
                for row in rows
                if not row["complete"] and row["structural_novelty_mean"] is not None
            ],
            "search_curve_auc": [row["search_curve_auc"] for row in complete_rows],
            "top_5_mean_fitness": [row["top_5_mean_fitness"] for row in complete_rows],
            "descriptor_cell_coverage": [
                float(row["descriptor_cell_coverage"]) for row in complete_rows
            ],
            "structural_novelty_mean": [
                row["structural_novelty_mean"]
                for row in complete_rows
                if row["structural_novelty_mean"] is not None
            ],
            "feature_dimension_mean": [
                row["feature_dimension"]["mean"] for row in complete_rows
            ],
            "ast_depth_mean": [row["ast_depth"]["mean"] for row in complete_rows],
            "ast_node_count_mean": [
                row["ast_node_count"]["mean"] for row in complete_rows
            ],
            "valid_proposal_rate": [
                row["overhead"]["valid_proposal_rate"] for row in rows
            ],
            "duplicate_rate": [row["overhead"]["duplicate_rate"] for row in rows],
            "proposal_time_ms": [row["overhead"]["proposal_time_ms"] for row in rows],
            "evaluation_time_ms": [
                row["overhead"]["evaluation_time_ms"] for row in rows
            ],
            "total_wall_time_ms": [
                row["overhead"]["total_wall_time_ms"] for row in rows
            ],
            "llm_tokens": [float(row["overhead"]["llm_tokens"]) for row in rows],
        }
        threshold_metrics = {}
        for threshold in thresholds:
            reached = [
                row["evaluations_to_threshold"][threshold]
                for row in complete_rows
                if row["evaluations_to_threshold"][threshold] is not None
            ]
            incomplete_reached = sum(
                row["evaluations_to_threshold"][threshold] is not None
                for row in rows
                if not row["complete"]
            )
            incomplete_hits = [
                row["evaluations_to_threshold"][threshold]
                for row in rows
                if not row["complete"]
                and row["evaluations_to_threshold"][threshold] is not None
            ]
            threshold_metrics[threshold] = {
                "reached_count": len(reached),
                "run_count": len(complete_rows),
                "probability_reached": (
                    len(reached) / len(complete_rows) if complete_rows else None
                ),
                "evaluations_to_threshold": _distribution(
                    [float(value) for value in reached]
                ),
                "complete_runs_not_reached": len(complete_rows) - len(reached),
                "incomplete_run_count": len(rows) - len(complete_rows),
                "incomplete_runs_that_reached": incomplete_reached,
                "incomplete_evaluations_to_threshold": _distribution(
                    [float(value) for value in incomplete_hits]
                ),
            }
        summaries[optimizer] = {
            "run_count": len(rows),
            "complete_run_count": len(complete_rows),
            "incomplete_run_count": len(rows) - len(complete_rows),
            "metrics": {
                name: _distribution(
                    [float(value) for value in values if value is not None]
                )
                for name, values in metrics.items()
            },
            "thresholds": threshold_metrics,
            "curve": {
                "evaluation_indices": list(indices),
                "mean": curve_mean,
                "min": curve_min,
                "max": curve_max,
                "n_at_evaluation": counts_by_index.astype(int).tolist(),
            },
            "mean_overhead_counts": {
                field: float(
                    statistics.mean(float(row["overhead"][field]) for row in rows)
                )
                for field in (
                    "proposal_attempts",
                    "valid_proposals",
                    "invalid",
                    "duplicates",
                    "rejected_by_constraint",
                    "llm_calls",
                    "llm_tokens",
                )
            },
        }

    paired = {}
    metric_names = ("final_best_fitness", "search_curve_auc", "top_5_mean_fitness")
    optimizer_names = sorted(grouped)
    for left_index, left_name in enumerate(optimizer_names):
        for right_name in optimizer_names[left_index + 1 :]:
            left_rows = [row for row in grouped[left_name] if row["complete"]]
            right_rows = [row for row in grouped[right_name] if row["complete"]]
            left = {
                row["optimizer_seed"]: float(row["final_best_fitness"])
                for row in left_rows
            }
            right = {
                row["optimizer_seed"]: float(row["final_best_fitness"])
                for row in right_rows
            }
            pair = {}
            for metric in metric_names:
                left_metric = {
                    row["optimizer_seed"]: float(row[metric])
                    for row in left_rows
                    if row[metric] is not None
                }
                right_metric = {
                    row["optimizer_seed"]: float(row[metric])
                    for row in right_rows
                    if row[metric] is not None
                }
                pair[metric] = _paired_bootstrap(
                    left_metric,
                    right_metric,
                    seed=int(protocol["primary_metrics"]["paired_bootstrap"]["seed"]),
                    resamples=int(
                        protocol["primary_metrics"]["paired_bootstrap"]["resamples"]
                    ),
                )
            pair["left_fitness_wins"] = sum(
                left[seed] > right[seed] for seed in set(left) & set(right)
            )
            pair["paired_runs"] = len(set(left) & set(right))
            paired[f"{left_name}_vs_{right_name}"] = pair

    return {
        "schema_version": 1,
        "study_id": protocol["study_id"],
        "protocol_sha256": protocol.get("protocol_sha256"),
        "evaluation_indices": list(indices),
        "thresholds": thresholds,
        "run_count": len(runs),
        "complete_runs": sum(row["complete"] for row in runs),
        "runs": runs,
        "optimizers": summaries,
        "paired_bootstrap": paired,
        "statistical_note": "Complete runs receive full-budget summaries. Incomplete runs are retained as censored observations and contribute only to curves through their last evaluation, overhead, diversity, and explicitly labeled last-observed fitness. Paired bootstrap comparisons use only seed indices where both runs completed the full budget; no normal-theory t-test is used.",
    }


def plot_primary(summary: dict[str, Any], output_path: Path) -> None:
    import matplotlib.pyplot as plt

    names = tuple(summary["optimizers"])
    colors = {
        "typed_random": "#4c78a8",
        "genetic_programming": "#f58518",
        "llm_one_shot": "#54a24b",
        "llm_iterative": "#e45756",
    }
    figure = plt.figure(figsize=(17, 14), constrained_layout=True)
    grid = figure.add_gridspec(3, 2)

    axis = figure.add_subplot(grid[0, 0])
    for name in names:
        curve = summary["optimizers"][name]["curve"]
        x = curve["evaluation_indices"]
        run_count = summary["optimizers"][name]["run_count"]
        shared_counts = [
            count == run_count for count in curve["n_at_evaluation"]
        ]
        mean = np.asarray(
            [
                np.nan if value is None or not shared else value
                for value, shared in zip(curve["mean"], shared_counts, strict=True)
            ],
            dtype=np.float64,
        )
        lower = np.asarray(
            [
                np.nan if value is None or not shared else value
                for value, shared in zip(curve["min"], shared_counts, strict=True)
            ],
            dtype=np.float64,
        )
        upper = np.asarray(
            [
                np.nan if value is None or not shared else value
                for value, shared in zip(curve["max"], shared_counts, strict=True)
            ],
            dtype=np.float64,
        )
        axis.plot(x, mean, label=name, color=colors.get(name))
        axis.fill_between(x, lower, upper, color=colors.get(name), alpha=0.16)
    axis.set_title(
        "A. Best-so-far fitness; mean and min–max over runs at every shown count"
    )
    axis.set_xlabel("Unique evaluated candidates")
    axis.set_ylabel("V3 stage-one ranking score")
    axis.set_xlim(20, 200)
    axis.legend(frameon=False)
    axis.grid(alpha=0.2)

    axis = figure.add_subplot(grid[0, 1])
    threshold_names = tuple(summary["thresholds"])
    x = np.arange(len(threshold_names))
    width = 0.8 / max(1, len(names))
    incomplete_hit_legend_added = False
    for index, name in enumerate(names):
        values = []
        for threshold in threshold_names:
            details = summary["optimizers"][name]["thresholds"][threshold]
            if details["run_count"] == 0:
                values.append(np.nan)
            else:
                values.append(
                    details["evaluations_to_threshold"]["mean"]
                    if details["reached_count"]
                    else 201
                )
        axis.bar(x + index * width, values, width, label=name, color=colors.get(name))
        for threshold_index, threshold in enumerate(threshold_names):
            incomplete_hits = [
                row["evaluations_to_threshold"][threshold]
                for row in summary["runs"]
                if row["optimizer"] == name
                and not row["complete"]
                and row["evaluations_to_threshold"][threshold] is not None
            ]
            if incomplete_hits:
                axis.scatter(
                    [x[threshold_index] + index * width + width / 2]
                    * len(incomplete_hits),
                    incomplete_hits,
                    color="black",
                    marker="x",
                    s=45,
                    zorder=4,
                    label=("incomplete run observed hit" if not incomplete_hit_legend_added else None),
                )
                incomplete_hit_legend_added = True
    axis.set_title("B. Threshold evaluations; × marks incomplete-run hits")
    axis.set_xlabel("Threshold from frozen V2/V3 results")
    axis.set_ylabel("Evaluations (201 = not reached in a complete run)")
    axis.set_xticks(x + width * (len(names) - 1) / 2, threshold_names, rotation=15)
    axis.set_ylim(0, 210)
    axis.legend(frameon=False, fontsize=8)
    axis.grid(axis="y", alpha=0.2)

    axis = figure.add_subplot(grid[1, 0])
    complete_values = {
        name: [
            row["final_best_fitness"]
            for row in summary["runs"]
            if row["optimizer"] == name and row["final_best_fitness"] is not None
        ]
        for name in names
    }
    positions = [
        index for index, name in enumerate(names, start=1) if complete_values[name]
    ]
    if positions:
        box = axis.boxplot(
            [complete_values[name] for name in names if complete_values[name]],
            positions=positions,
            patch_artist=True,
        )
        for patch, index in zip(box["boxes"], positions, strict=True):
            patch.set_facecolor(colors.get(names[index - 1]))
            patch.set_alpha(0.55)
    for index, name in enumerate(names, start=1):
        axis.scatter(
            [index] * len(complete_values[name]),
            complete_values[name],
            color=colors.get(name),
            edgecolor="black",
            zorder=3,
        )
        incomplete = [
            row["last_observed_best_fitness"]
            for row in summary["runs"]
            if row["optimizer"] == name and not row["complete"]
        ]
        axis.scatter(
            [index] * len(incomplete),
            incomplete,
            color=colors.get(name),
            marker="x",
            s=55,
            zorder=4,
        )
    axis.set_xticks(range(1, len(names) + 1), names, rotation=15)
    axis.set_title("C. Best fitness at 200; × marks incomplete last result")
    axis.set_ylabel("V3 stage-one ranking score")
    axis.grid(axis="y", alpha=0.2)

    axis = figure.add_subplot(grid[1, 1])
    coverage = [
        [
            row["descriptor_cell_coverage"]
            for row in summary["runs"]
            if row["optimizer"] == name and row["complete"]
        ]
        for name in names
    ]
    means = [statistics.mean(values) if values else 0 for values in coverage]
    errors = [statistics.stdev(values) if len(values) > 1 else 0 for values in coverage]
    axis.bar(
        names, means, yerr=errors, color=[colors.get(name) for name in names], capsize=4
    )
    for index, name in enumerate(names):
        incomplete_coverage = [
            row["descriptor_cell_coverage"]
            for row in summary["runs"]
            if row["optimizer"] == name and not row["complete"]
        ]
        axis.scatter(
            [index] * len(incomplete_coverage),
            incomplete_coverage,
            color=colors.get(name),
            marker="x",
            s=55,
            zorder=3,
        )
    axis.set_title("D. Descriptor cells in complete runs; × incomplete")
    axis.set_ylabel("Unique cells per run")
    axis.tick_params(axis="x", rotation=15)
    axis.grid(axis="y", alpha=0.2)

    counts_axis = figure.add_subplot(grid[2, 0])
    fields = ("proposal_attempts", "invalid", "duplicates", "rejected_by_constraint")
    x = np.arange(len(names))
    width = 0.18
    for index, field in enumerate(fields):
        values = [
            summary["optimizers"][name]["mean_overhead_counts"][field] for name in names
        ]
        counts_axis.bar(x + (index - 1.5) * width, values, width, label=field)
    counts_axis.set_title("E. Proposal overhead per run")
    counts_axis.set_ylabel("Mean proposal attempts / outcomes")
    counts_axis.set_xticks(x, names, rotation=15)
    counts_axis.legend(frameon=False, fontsize=8)
    counts_axis.grid(axis="y", alpha=0.2)

    cost_grid = grid[2, 1].subgridspec(1, 2)
    tokens_axis = figure.add_subplot(cost_grid[0, 0])
    runtime_axis = figure.add_subplot(cost_grid[0, 1])
    tokens = [
        summary["optimizers"][name]["mean_overhead_counts"]["llm_tokens"]
        for name in names
    ]
    runtime = [
        summary["optimizers"][name]["metrics"]["total_wall_time_ms"]["mean"]
        for name in names
    ]
    tokens_axis.bar(names, tokens, color=[colors.get(name) for name in names])
    tokens_axis.set_title("LLM tokens")
    tokens_axis.set_ylabel("Tokens per run")
    tokens_axis.tick_params(axis="x", rotation=60, labelsize=7)
    tokens_axis.grid(axis="y", alpha=0.2)
    runtime_axis.bar(
        names,
        [value / 60_000 for value in runtime],
        color=[colors.get(name) for name in names],
    )
    runtime_axis.set_title("Total wall time")
    runtime_axis.set_ylabel("Minutes per run")
    runtime_axis.tick_params(axis="x", rotation=60, labelsize=7)
    runtime_axis.grid(axis="y", alpha=0.2)

    figure.suptitle("V3.2 primary optimizer benchmark", fontsize=16)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=180)
    plt.close(figure)
