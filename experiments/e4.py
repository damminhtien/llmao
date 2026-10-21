"""Run the bounded E4 comparison using the existing E1 optimizer and evaluator."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from collections import Counter
from contextlib import ExitStack
from pathlib import Path
from statistics import mean
from unittest.mock import patch

from bias_optimizer.data import mnist as legacy_mnist
from bias_optimizer.data.mnist_e1 import E1MNISTDataConfig, load_mnist_e1_search_data
from bias_optimizer.domain.program import ProgramBiasSpec
from bias_optimizer.dsl.ast import Expr
from bias_optimizer.dsl.compiler import ProgramCompiler
from bias_optimizer.dsl.validator import ProgramConstraints, SearchTrack
from bias_optimizer.evaluation.protocol import EvaluationDataset
from bias_optimizer.optimizer_bench.e1 import (
    DEFAULT_E1_RESOURCE_CAPS,
    E1_REACHABLE_MECHANISM_FAMILIES,
    E1TokenLedger,
    canonical_e1_program,
    e1_output_schema,
    load_e1_pilot_language,
    verify_e1_grammar,
)
from bias_optimizer.optimizer_bench.objective import ast_hash
from bias_optimizer.optimizer_bench.schema import CandidateEvaluation, SearchTrace
from bias_optimizer.optimizer_bench.trace import read_trace
from bias_optimizer.v4.language import G0_LANGUAGE, MacroLanguage, expand_candidate
from experiments import e1 as e1_runner

ROOT = Path(__file__).resolve().parents[1]
SEED = 202
OUTPUT_ROOT = ROOT / "results/v4/e4/seed_202"
E1_COMMON_PATH = ROOT / "results/v4/e1/runs/seed_101/common_initial_evaluations.json"
E1_SUMMARY_PATH = ROOT / "results/v4/e1/runs/seed_101/e1_summary.json"
E1_DATA_MANIFEST = ROOT / "results/v4/e1/data/mnist/raw/e1_search_data_manifest.json"
E2_RESULTS_PATH = ROOT / "results/v4/e2/macro_adoption_probe_2026-10-19/request_results.jsonl"
E3_RESULTS_PATH = ROOT / "results/v4/e3/e2_macro_program_evaluation_2026-10-20/e3_results.json"
CONDITIONS = ("g0_recipes", "g_pilot_macros")
_CONSTRAINTS = ProgramConstraints(
    track=SearchTrack.DISCOVERY,
    max_feature_dim=128,
    max_depth=6,
    max_nodes=127,
    forbid_raw_pixels=True,
    require_vector_root=False,
)
_RECIPE_LABELS = {
    "stroke_degree_profile": "skeleton graph degree summary",
    "multiscale_spatial_profile": "coarse-to-fine image occupancy",
    "multiscale_spatial_degree_profile": "spatial occupancy plus graph degrees",
}


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _load_shared_initial_scores(seeds: tuple) -> tuple[CandidateEvaluation, ...]:
    payload = json.loads(E1_COMMON_PATH.read_text(encoding="utf-8"))
    if payload.get("seed") != 101 or payload.get("schema_version") != 1:
        raise ValueError("E4 must reuse the frozen E1 common initial evaluation artifact")
    if payload.get("programs") != [seed.program.to_dict() for seed in seeds]:
        raise ValueError("E1 initial programs do not match the frozen V3.2 G0 seed set")
    scores = payload.get("scores")
    if not isinstance(scores, list) or len(scores) != len(seeds) or len(scores) != 20:
        raise ValueError("E1 common initial artifact must contain 20 score records")
    score_bytes = json.dumps(scores, sort_keys=True, separators=(",", ":")).encode()
    if _sha256_bytes(score_bytes) != payload.get("sha256"):
        raise ValueError("E1 common initial score record checksum is invalid")
    rows: list[CandidateEvaluation] = []
    compiler = ProgramCompiler(_CONSTRAINTS)
    for index, (score, seed) in enumerate(zip(scores, seeds, strict=True), start=1):
        program = Expr.from_dict(score["program"])
        compiler.compile(program)
        if program.to_dict() != seed.program.to_dict():
            raise ValueError(f"E1 common initial program {index} differs from frozen G0")
        if score.get("candidate_id") != ast_hash(program):
            raise ValueError(f"E1 common initial program {index} has a mismatched AST hash")
        if score.get("evaluation_index") != index:
            raise ValueError("E1 initial score order is not the frozen 20-program order")
        rows.append(
            CandidateEvaluation(
                candidate_id=score["candidate_id"],
                evaluation_index=score["evaluation_index"],
                fitness=score["fitness"],
                accuracy=score["accuracy"],
                feature_dim=score["feature_dim"],
                runtime_ms=score["runtime_ms"],
                structural_descriptor=tuple(score["structural_descriptor"]),
                behavioral_novelty=score["behavioral_novelty"],
                program=program,
                metadata=score["metadata"],
            )
        )
    if len({row.candidate_id for row in rows}) != 20:
        raise ValueError("E1 shared initial score records are not unique")
    return tuple(rows)


def _load_train_data_with_boundary_guard(config: E1MNISTDataConfig):
    accessed: set[str] = set()
    original_read_bytes = Path.read_bytes

    def guarded_read_bytes(path: Path) -> bytes:
        resolved = path.resolve()
        names = {part.lower() for part in resolved.parts}
        if any("test" in part or "t10k" in part for part in names):
            raise AssertionError(f"E4 attempted to read a test-partition path: {resolved}")
        accessed.add(path.name)
        return original_read_bytes(path)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("E4 attempted to access the legacy or final MNIST loader")

    with ExitStack() as stack:
        for name in dir(legacy_mnist):
            if (
                name in {"_load_openml_arrays", "fetch_openml"}
                or name.startswith(("load_mnist_final", "load_mnist_test"))
            ):
                stack.enter_context(patch.object(legacy_mnist, name, side_effect=forbidden))
        stack.enter_context(patch.object(Path, "read_bytes", guarded_read_bytes))
        search_data = load_mnist_e1_search_data(config)
    if accessed != {"train-images-idx3-ubyte.gz", "train-labels-idx1-ubyte.gz"}:
        raise ValueError(f"E4 train-only loader read unexpected files: {sorted(accessed)}")
    return search_data


def _macro_default_expansions(language: MacroLanguage) -> dict[str, Expr]:
    expansions: dict[str, Expr] = {}
    compiler = ProgramCompiler(_CONSTRAINTS)
    for name in sorted(language.macro_map):
        macro = language.macro_map[name]
        call = Expr(macro.name, tuple(Expr("image") for _ in macro.input_types), {})
        first = expand_candidate(call, language, introduced_macros=())
        second = expand_candidate(call, language, introduced_macros=())
        if first.expanded_ast.to_json() != second.expanded_ast.to_json():
            raise ValueError(f"frozen macro expansion is nondeterministic: {name}")
        compiler.compile(first.expanded_ast)
        if not set(first.info.operations) <= {
            primitive.name for primitive in G0_LANGUAGE.primitives
        }:
            raise ValueError(f"frozen macro {name} expands outside G0")
        if first.info.depth > 6 or first.info.node_count > 127:
            raise ValueError(f"frozen macro {name} exceeds E1 structure limits")
        if first.info.dimension is not None and first.info.dimension > 128:
            raise ValueError(f"frozen macro {name} exceeds E1 feature-width limit")
        canonical, used = canonical_e1_program(call, language)
        direct, direct_macros = canonical_e1_program(canonical, None)
        if used != (name,) or direct_macros or ast_hash(canonical) != ast_hash(direct):
            raise ValueError(f"macro and expanded G0 identity differ for {name}")
        expansions[name] = canonical
    if set(expansions) != set(_RECIPE_LABELS):
        raise ValueError("E4 expects exactly the three frozen G_pilot macros")
    return expansions


def _recipe_guidance(expansions: dict[str, Expr], *, macros_enabled: bool) -> str:
    lines = []
    if macros_enabled:
        lines.append(
            "The following are the same three frozen structural recipes, exposed "
            "as typed G_pilot operations in the schema. Each compact JSON tree "
            "shows its expanded G0 behavior. Use the named operation when useful; "
            "do not invent macros."
        )
    else:
        lines.append(
            "The following are three reusable compositions using only permitted "
            "G0 operations. The labels are explanatory descriptions, not AST "
            "operations. Emit ordinary nested G0 expressions; do not invent or "
            "emit macro operations."
        )
    for index, name in enumerate(sorted(expansions), start=1):
        tree = json.dumps(expansions[name].to_dict(), sort_keys=True, separators=(",", ":"))
        label = _RECIPE_LABELS[name]
        if macros_enabled:
            prefix = f"{index}. {name}(image) expands to"
        else:
            prefix = f"{index}. {label} recipe"
        lines.append(f"{prefix}: {tree}")
    return "\n".join(lines)


def _verify_e3_data_provenance(
    search_data,
    dataset: EvaluationDataset,
    *,
    initial_scores_sha256: str,
    data_manifest_sha256: str,
    pilot_manifest_sha256: str,
) -> dict[str, object]:
    e3 = json.loads(E3_RESULTS_PATH.read_text(encoding="utf-8"))
    dataset_record = e3.get("dataset", {})
    input_hashes = e3.get("inputs", {}).get("artifact_sha256", {})
    if dataset_record.get("official_test_partition_used") is not False:
        raise ValueError("saved E1/E3 provenance does not exclude the official test partition")
    if dataset_record.get("fingerprint") != dataset.fingerprint:
        raise ValueError("current train-only data fingerprint differs from the saved E1/E3 split")
    expected_hashes = {
        "e1_common_initial_evaluations_sha256": initial_scores_sha256,
        "e1_train_only_manifest_sha256": data_manifest_sha256,
        "g_pilot_manifest_sha256": pilot_manifest_sha256,
    }
    if any(input_hashes.get(key) != value for key, value in expected_hashes.items()):
        raise ValueError("E1/E3 saved provenance does not match the E4 inputs")
    return {
        "fingerprint": dataset.fingerprint,
        "split_id": dataset_record["split_id"],
        "train_shape": list(search_data.train_images.shape),
        "validation_shape": list(search_data.validation_images.shape),
        "train_only_provenance_matches_e1_e3": True,
    }


def _verify_policy_and_caps(language: MacroLanguage, expansions: dict[str, Expr]) -> dict[str, object]:
    g0 = verify_e1_grammar(None)
    pilot = verify_e1_grammar(language)
    g0_ops = set(g0["g0_operations"])
    pilot_ops = set(pilot["g0_operations"]) | set(language.macro_map)
    if g0_ops.intersection(language.macro_map) or pilot_ops != g0_ops | set(language.macro_map):
        raise ValueError("G0 and G_pilot operation vocabularies are not properly isolated")
    for name, expanded in expansions.items():
        direct, _ = canonical_e1_program(expanded, None)
        if direct.to_json() != expanded.to_json():
            raise ValueError(f"recipe for {name} is not a canonical G0 program")
    compiler = ProgramCompiler(_CONSTRAINTS)
    valid_program = next(iter(expansions.values()))
    rejection, candidate_id = e1_runner._e1_candidate_eligibility(
        valid_program, compiler, set()
    )
    duplicate_reason, _ = e1_runner._e1_candidate_eligibility(
        valid_program, compiler, {candidate_id} if candidate_id else set()
    )
    invalid_program = Expr("spatial_split", (Expr("image"),), {"rows": 0, "cols": 2})
    invalid_reason, _ = e1_runner._e1_candidate_eligibility(
        invalid_program, compiler, set()
    )
    excluded_reason, _ = e1_runner._e1_candidate_eligibility(
        Expr("cross_histogram"), compiler, set()
    )
    if (
        rejection is not None
        or not candidate_id
        or duplicate_reason != "duplicate"
        or invalid_reason != "constraint"
        or excluded_reason != "constraint"
    ):
        raise ValueError("E1 candidate structure, excluded-operation, or deduplication checks changed")
    if tuple(E1_REACHABLE_MECHANISM_FAMILIES) != ("order_sensitive", "free_exploration"):
        raise ValueError("E1 focus scheduler includes an unreachable mechanism family")
    caps = DEFAULT_E1_RESOURCE_CAPS
    if (caps.max_attempts, caps.max_requests, caps.max_output_tokens, caps.max_total_tokens) != (
        20,
        40,
        2_500,
        750_000,
    ):
        raise ValueError("E4 requires the frozen E1 attempt and token caps")
    if caps.request_timeout_seconds != 120:
        raise ValueError("E4 requires the frozen E1 per-request timeout")

    # A fake request exercises the exact ledger boundary without contacting Ollama.
    ledger = E1TokenLedger(caps)
    schema = e1_output_schema(language, count=1)
    reservation = ledger.reserve("preflight", schema)
    if reservation <= 0 or ledger.requests != 1:
        raise ValueError("E1 total-token reservation did not account for a request")
    return {
        "g0_operation_count": len(g0_ops),
        "g0_excludes_pilot_macros": True,
        "g_pilot_macro_operations": sorted(language.macro_map),
        "canonical_macro_expansions": sorted(expansions),
        "focus_families": list(E1_REACHABLE_MECHANISM_FAMILIES),
        "focus_is_guidance_only": True,
        "strict_structure_and_duplicate_checks": True,
        "resource_caps": {
            "attempts_per_condition": caps.max_attempts,
            "requests_per_condition": caps.max_requests,
            "timeout_seconds": caps.request_timeout_seconds,
            "output_tokens_per_request": caps.max_output_tokens,
            "total_reserved_tokens_per_condition": caps.max_total_tokens,
        },
    }


def _preserved_artifact_hashes() -> dict[str, str]:
    paths = {
        "e1_common_initial_evaluations": E1_COMMON_PATH,
        "e1_summary": E1_SUMMARY_PATH,
        "e1_train_only_manifest": E1_DATA_MANIFEST,
        "e2_request_results": E2_RESULTS_PATH,
        "e3_results": E3_RESULTS_PATH,
        "g_pilot_manifest": ROOT / "results/v4/languages/g_pilot_e1.json",
        "g_pilot_manifest_sidecar": ROOT / "results/v4/languages/g_pilot_e1.json.sha256",
    }
    return {name: _sha256(path) for name, path in paths.items()}


def run_preflight(
    *,
    data_config: E1MNISTDataConfig | None = None,
    output_root: Path = OUTPUT_ROOT,
    check_model_server: bool = True,
) -> dict[str, object]:
    """Verify frozen inputs and bounded train-only execution without a model call."""
    data_config = data_config or E1MNISTDataConfig()
    if Path(output_root).exists():
        raise FileExistsError(f"E4 output root must be fresh: {output_root}")
    protocol, seeds = e1_runner._verified_protocol_and_seeds()
    if len(seeds) != 20:
        raise ValueError("E4 requires the same 20 frozen G0 seed programs")
    language, pilot_manifest = load_e1_pilot_language(ROOT)
    initial_rows = _load_shared_initial_scores(seeds)
    common_sha256 = _sha256(E1_COMMON_PATH)
    initial_hashes = json.loads(E1_SUMMARY_PATH.read_text(encoding="utf-8"))
    if initial_hashes.get("common_initial_scores_sha256") != common_sha256:
        raise ValueError("E1 summary does not match its common score artifact")
    pilot_sha256 = _sha256(ROOT / "results/v4/languages/g_pilot_e1.json")
    data_manifest_sha256 = _sha256(E1_DATA_MANIFEST)
    search_data = _load_train_data_with_boundary_guard(data_config)
    dataset = EvaluationDataset.from_mnist_search(search_data)
    if dataset.evaluation_partition != "official_train_validation":
        raise ValueError("E4 data is not restricted to the official-training-derived split")
    if len(search_data.train_labels) != 58_000 or len(search_data.validation_labels) != 2_000:
        raise ValueError("E4 train-only split differs from the frozen E1 split sizes")
    e3_data = _verify_e3_data_provenance(
        search_data,
        dataset,
        initial_scores_sha256=common_sha256,
        data_manifest_sha256=data_manifest_sha256,
        pilot_manifest_sha256=pilot_sha256,
    )
    expansions = _macro_default_expansions(language)
    policy = _verify_policy_and_caps(language, expansions)
    recipe_guidance = _recipe_guidance(expansions, macros_enabled=False)
    macro_guidance = _recipe_guidance(expansions, macros_enabled=True)
    if any(name in recipe_guidance for name in language.macro_map):
        raise ValueError("G0 recipe condition exposes a frozen macro operation name")
    if not all(name in macro_guidance for name in language.macro_map):
        raise ValueError("G_pilot guidance omits a frozen macro operation name")
    active_runs = e1_runner._active_v4_conflicts()
    if active_runs:
        raise RuntimeError("an active V4 worker conflicts with E4: " + "; ".join(active_runs))
    model = e1_runner._verify_local_model(check_server=check_model_server)
    return {
        "preflight": "passed",
        "llm_requests_made": 0,
        "seed": SEED,
        "protocol_sha256": protocol["protocol_sha256"],
        "shared_initial_program_count": len(seeds),
        "shared_initial_score_count": len(initial_rows),
        "shared_initial_scores_sha256": common_sha256,
        "shared_initial_score_records_reused_without_rescoring": True,
        "g_pilot_manifest_sha256": pilot_sha256,
        "g_pilot_language_sha256": language.sha256,
        "g_pilot_official_star": pilot_manifest["official_G_star"],
        "macro_expanded_ast_sha256": {name: ast_hash(ast) for name, ast in expansions.items()},
        "recipe_guidance_sha256": {
            "g0_recipes": _sha256_bytes(recipe_guidance.encode()),
            "g_pilot_macros": _sha256_bytes(macro_guidance.encode()),
        },
        "recipe_guidance_bytes": {
            "g0_recipes": len(recipe_guidance.encode()),
            "g_pilot_macros": len(macro_guidance.encode()),
        },
        "data_manifest_sha256": data_manifest_sha256,
        "data": e3_data,
        "data_boundary": "Only pinned train-images/train-labels IDX archives were read; legacy OpenML, final, and test loaders were blocked.",
        "policy": policy,
        "model": model,
        "active_conflicts": [],
        "outputs_are_fresh": True,
    }


def _walk(program: Expr):
    yield program
    for argument in program.args:
        yield from _walk(argument)


def _subtree_hashes(program: Expr) -> set[str]:
    return {ast_hash(node) for node in _walk(program)}


def _parse_raw_proposals(
    calls: list[dict[str, object]],
    responses: list[dict[str, object]],
    trace: SearchTrace,
    language: MacroLanguage | None,
    initial_ids: set[str],
    expansions: dict[str, Expr],
) -> dict[str, object]:
    if len(calls) != len(responses):
        raise ValueError("raw model calls and response archive rows do not align")
    scored_rows = {row.candidate_id: row for row in trace.evaluated_candidates[20:]}
    seen = set(initial_ids)
    entries: list[dict[str, object]] = []
    raw_macro_proposal_counts: Counter[str] = Counter()
    raw_macro_invocations: Counter[str] = Counter()
    typed_macro_proposal_counts: Counter[str] = Counter()
    raw_pattern_proposal_counts: Counter[str] = Counter()
    attempt_offset = 0
    raw_proposal_count = 0
    macro_names = set(language.macro_map) if language else set()

    def macro_ops_for(raw_item: object) -> list[str]:
        if not isinstance(raw_item, dict) or not isinstance(raw_item.get("program"), dict):
            return []
        try:
            return [
                node.op
                for node in _walk(Expr.from_dict(raw_item["program"]))
                if node.op in macro_names
            ]
        except (KeyError, RecursionError, TypeError, ValueError):
            return []

    def count_raw_macro_ops(operations: list[str]) -> None:
        for name in set(operations):
            raw_macro_proposal_counts[name] += 1
        raw_macro_invocations.update(operations)

    for request_index, (call, archive) in enumerate(zip(calls, responses, strict=True), start=1):
        prompt = archive.get("prompt")
        if not isinstance(prompt, str) or _sha256_bytes(prompt.encode()) != call.get("prompt_sha256"):
            raise ValueError(f"E4 request {request_index} prompt archive hash does not match")
        slots = call.get("requested_proposal_slots")
        if type(slots) is not int or slots <= 0:
            raise ValueError(f"E4 request {request_index} is missing its requested slot count")
        raw = call.get("raw_response")
        try:
            payload = json.loads(raw) if isinstance(raw, str) and raw else None
            items = payload.get("proposals") if isinstance(payload, dict) else None
            if not isinstance(items, list):
                items = []
                response_error = "invalid_response_json_or_schema"
            elif len(items) > slots:
                response_error = "too_many_proposals_for_request_schema"
            else:
                response_error = None
        except (json.JSONDecodeError, TypeError):
            items = []
            response_error = "invalid_response_json_or_schema"
        raw_proposal_count += len(items)

        for slot in range(slots):
            attempt = attempt_offset + slot + 1
            raw_item = items[slot] if slot < len(items) else None
            raw_macro_ops = macro_ops_for(raw_item)
            count_raw_macro_ops(raw_macro_ops)
            if response_error:
                entries.append(
                    {
                        "request": request_index,
                        "attempt": attempt,
                        "slot": slot,
                        "status": response_error,
                        "macro_operations": raw_macro_ops,
                    }
                )
                continue
            if slot >= len(items):
                entries.append(
                    {
                        "request": request_index,
                        "attempt": attempt,
                        "slot": slot,
                        "status": "missing_proposal",
                        "macro_operations": [],
                    }
                )
                continue
            raw_program = raw_item.get("program") if isinstance(raw_item, dict) else None
            candidate_id: str | None = None
            used_macros: tuple[str, ...] = ()
            try:
                if not isinstance(raw_item, dict):
                    raise TypeError("proposal must be an object")
                bias = ProgramBiasSpec.from_dict(raw_item)
                raw_ops = [node.op for node in _walk(bias.program)]
                used_macros = tuple(sorted({op for op in raw_ops if op in macro_names}))
                expanded, validated_macros = canonical_e1_program(bias.program, language)
                if used_macros != tuple(sorted(validated_macros)):
                    raise ValueError("raw macro operations differ from validated expansion provenance")
                expanded_subtrees = _subtree_hashes(expanded)
                for name, recipe in expansions.items():
                    if ast_hash(recipe) in expanded_subtrees:
                        raw_pattern_proposal_counts[name] += 1
                candidate_id = ast_hash(expanded)
                duplicate = candidate_id in seen
                if duplicate:
                    status = "duplicate"
                else:
                    seen.add(candidate_id)
                if used_macros:
                    for name in used_macros:
                        typed_macro_proposal_counts[name] += 1
                score = scored_rows.get(candidate_id)
                if score is not None and not duplicate:
                    status = "scored"
                elif not duplicate:
                    status = "valid_not_scored"
                entries.append(
                    {
                        "request": request_index,
                        "attempt": attempt,
                        "slot": slot,
                        "status": status,
                        "candidate_id": candidate_id,
                        "macro_operations": raw_macro_ops,
                        "raw_ast_sha256": _sha256_bytes(
                            json.dumps(raw_program, sort_keys=True, separators=(",", ":")).encode()
                        ),
                        "score_evaluation_index": score.evaluation_index if score is not None else None,
                    }
                )
            except (KeyError, RecursionError, TypeError, ValueError) as exc:
                entries.append(
                    {
                        "request": request_index,
                        "attempt": attempt,
                        "slot": slot,
                        "status": "invalid",
                        "macro_operations": raw_macro_ops,
                        "failure_reason": str(exc)[:240],
                    }
                )
        if len(items) > slots:
            for extra_index, raw_item in enumerate(items[slots:], start=slots):
                raw_macro_ops = macro_ops_for(raw_item)
                count_raw_macro_ops(raw_macro_ops)
                entries.append(
                    {
                        "request": request_index,
                        "attempt": None,
                        "slot": extra_index,
                        "status": "unrequested_extra_proposal",
                        "macro_operations": raw_macro_ops,
                    }
                )
        attempt_offset += slots

    if attempt_offset != trace.proposal_attempts:
        raise ValueError(
            f"raw request slots ({attempt_offset}) differ from trace attempts ({trace.proposal_attempts})"
        )
    scored_candidate_ids = set(scored_rows)
    scored_pattern_use: dict[str, int] = {name: 0 for name in expansions}
    scored_macro_use: Counter[str] = Counter()
    composite_ids: set[str] = set()
    scored_seen: set[str] = set()
    for entry in entries:
        if entry.get("status") != "scored":
            continue
        candidate_id = str(entry["candidate_id"])
        if candidate_id in scored_seen or candidate_id not in scored_candidate_ids:
            continue
        scored_seen.add(candidate_id)
        row = scored_rows[candidate_id]
        program = row.program
        if program is None:
            continue
        candidate_subtrees = _subtree_hashes(program)
        matched = [
            name
            for name, recipe in expansions.items()
            if ast_hash(recipe) in candidate_subtrees
        ]
        for name in matched:
            scored_pattern_use[name] += 1
        for name in entry.get("macro_operations", []):
            scored_macro_use[name] += 1
        if candidate_id not in {ast_hash(program) for program in expansions.values()} and matched:
            composite_ids.add(candidate_id)
    prompt_bytes = [len(str(row.get("prompt", "")).encode()) for row in responses]
    prompt_tokens = [call.get("prompt_tokens") for call in calls if type(call.get("prompt_tokens")) is int]
    output_tokens = [call.get("response_tokens") for call in calls if type(call.get("response_tokens")) is int]
    return {
        "raw_proposals": raw_proposal_count,
        "attempt_slots": attempt_offset,
        "raw_macro_proposals_by_name": {
            name: raw_macro_proposal_counts.get(name, 0) for name in sorted(_RECIPE_LABELS)
        },
        "raw_macro_invocations_by_name": {
            name: raw_macro_invocations.get(name, 0) for name in sorted(_RECIPE_LABELS)
        },
        "typed_valid_macro_proposals_by_name": {
            name: typed_macro_proposal_counts.get(name, 0) for name in sorted(_RECIPE_LABELS)
        },
        "raw_structural_pattern_proposals_by_name": {
            name: raw_pattern_proposal_counts.get(name, 0) for name in sorted(_RECIPE_LABELS)
        },
        "scored_macro_invocations_by_name": {
            name: scored_macro_use.get(name, 0) for name in sorted(_RECIPE_LABELS)
        },
        "scored_structural_pattern_use_by_name": scored_pattern_use,
        "novel_composite_program_count": len(composite_ids),
        "novel_composite_candidate_ids": sorted(composite_ids),
        "proposal_slots": entries,
        "prompt_bytes": {
            "minimum": min(prompt_bytes) if prompt_bytes else 0,
            "maximum": max(prompt_bytes) if prompt_bytes else 0,
            "mean": mean(prompt_bytes) if prompt_bytes else 0,
        },
        "input_tokens_reported": sum(prompt_tokens),
        "output_tokens_reported": sum(output_tokens),
        "model_requests": len(calls),
        "model_request_time_ms": sum(
            float(call["elapsed_ms"])
            for call in calls
            if isinstance(call.get("elapsed_ms"), (int, float))
        ),
        "prompt_hashes": sorted({str(call.get("prompt_sha256")) for call in calls}),
        "schema_hashes": sorted({str(call.get("schema_sha256")) for call in calls}),
        "request_seeds": [call.get("seed") for call in calls],
    }


def _analyze_condition(
    condition: str,
    output_dir: Path,
    trace: SearchTrace,
    initial_rows: tuple[CandidateEvaluation, ...],
    language: MacroLanguage | None,
    expansions: dict[str, Expr],
    *,
    standalone_ids: set[str],
) -> dict[str, object]:
    calls = _read_jsonl(output_dir / "model_calls.jsonl")
    responses = _read_jsonl(output_dir / "llm_responses.jsonl")
    for request_index, call in enumerate(calls, start=1):
        expected = {
            "model": "qwen3.5:35b-mlx",
            "temperature": 0.65,
            "seed": SEED + request_index - 1,
            "timeout_seconds": 120,
            "max_output_tokens": 2_500,
        }
        if any(call.get(name) != value for name, value in expected.items()):
            raise ValueError(f"request {request_index} differs from the frozen E4 model policy")
    raw = _parse_raw_proposals(
        calls,
        responses,
        trace,
        language,
        {row.candidate_id for row in initial_rows},
        expansions,
    )
    adaptive = list(trace.evaluated_candidates[20:])
    metrics = json.loads((output_dir / "e4_metrics.json").read_text(encoding="utf-8"))
    attempt_curve_rows = metrics.get("attempt_best_so_far", [])
    attempt_best = {int(item["attempt"]): float(item["best_fitness"]) for item in attempt_curve_rows}
    current_best = max(row.fitness for row in trace.evaluated_candidates[:20])
    attempt_curve: list[float] = []
    area = 0.0
    for attempt in range(1, 21):
        if attempt in attempt_best:
            current_best = max(current_best, attempt_best[attempt])
        attempt_curve.append(current_best)
        area += current_best
    candidate_curve = [max(row.fitness for row in trace.evaluated_candidates[:20])]
    for row in adaptive:
        candidate_curve.append(max(candidate_curve[-1], row.fitness))
    best_adaptive = max(adaptive, key=lambda row: row.fitness) if adaptive else None
    raw_slots = raw["proposal_slots"]
    raw_by_id = {
        str(entry.get("candidate_id")): entry
        for entry in raw_slots
        if entry.get("candidate_id") and entry.get("status") == "scored"
    }
    best_provenance = None
    if best_adaptive is not None:
        best_provenance = raw_by_id.get(best_adaptive.candidate_id)
    best_adaptive_ast = (
        best_adaptive.program.to_dict()
        if best_adaptive is not None and best_adaptive.program is not None
        else None
    )
    novel = {
        row.candidate_id
        for row in adaptive
        if row.program is not None
        and row.candidate_id not in standalone_ids
        and any(
            ast_hash(expansion) in _subtree_hashes(row.program)
            for expansion in expansions.values()
        )
    }
    valid_rate = trace.valid_proposal_count / trace.proposal_attempts if trace.proposal_attempts else 0.0
    return {
        "condition": condition,
        "status": "completed" if trace.complete else "incomplete",
        "termination_reason": trace.termination_reason,
        "counts": {
            "raw_proposals": raw["raw_proposals"],
            "attempt_slots": trace.proposal_attempts,
            "valid_proposals_including_duplicates": trace.valid_proposal_count,
            "invalid_proposals": trace.invalid_count,
            "constraint_rejections": trace.rejected_by_constraint_count,
            "duplicates": trace.duplicate_count,
            "scored_adaptive_candidates": len(adaptive),
            "valid_rate_per_attempt": valid_rate,
            "duplicate_rate_per_attempt": trace.duplicate_count / trace.proposal_attempts if trace.proposal_attempts else 0.0,
        },
        "fitness": {
            "initial_best": max(row.fitness for row in trace.evaluated_candidates[:20]),
            "best_overall": max(row.fitness for row in trace.evaluated_candidates),
            "best_adaptive": best_adaptive.fitness if best_adaptive else None,
            "attempt_budget_auc": area,
            "attempt_budget_mean_best_fitness": area / 20,
            "attempt_budget_curve": attempt_curve,
            "adaptive_unique_candidate_curve": candidate_curve,
            "comparable_adaptive_evaluation_range": None,
            "adaptive_candidate_auc_trapezoid": None,
            "adaptive_candidate_auc_mean": None,
        },
        "cost": {
            "reported_input_tokens": raw["input_tokens_reported"],
            "reported_output_tokens": raw["output_tokens_reported"],
            "reported_total_tokens": raw["input_tokens_reported"] + raw["output_tokens_reported"],
            "model_requests": raw["model_requests"],
            "model_request_time_ms": raw["model_request_time_ms"],
            "search_wall_time_ms": trace.total_wall_time_ms,
            "reserved_tokens": metrics["token_budget"]["reserved_tokens"],
            "token_limit": metrics["token_budget"]["max_total_tokens"],
            "unknown_failed_calls": metrics["token_budget"]["unknown_failed_calls"],
        },
        "structural_reuse": {
            "raw_structural_pattern_proposals_by_name": raw[
                "raw_structural_pattern_proposals_by_name"
            ],
            "raw_macro_proposals_by_name": raw["raw_macro_proposals_by_name"],
            "raw_macro_invocations_by_name": raw["raw_macro_invocations_by_name"],
            "typed_valid_macro_proposals_by_name": raw["typed_valid_macro_proposals_by_name"],
            "scored_macro_invocations_by_name": raw["scored_macro_invocations_by_name"],
            "scored_structural_pattern_use_by_name": raw["scored_structural_pattern_use_by_name"],
            "novel_composite_program_count": len(novel),
            "novel_composite_candidate_ids": sorted(novel),
            "standalone_e2_e3_candidate_ids": sorted(standalone_ids),
        },
        "prompt_and_schema": {
            "prompt_bytes": raw["prompt_bytes"],
            "prompt_hashes": raw["prompt_hashes"],
            "schema_hashes": raw["schema_hashes"],
            "request_seeds": raw["request_seeds"],
        },
        "best_adaptive_candidate": {
            "candidate_id": best_adaptive.candidate_id,
            "fitness": best_adaptive.fitness,
            "accuracy": best_adaptive.accuracy,
            "feature_dim": best_adaptive.feature_dim,
            "runtime_ms": best_adaptive.runtime_ms,
            "proposal_attempt": (best_adaptive.metadata or {}).get("proposal_attempt"),
            "macro_metadata": (best_adaptive.metadata or {}).get("g_pilot_macros_used", []),
            "raw_request_provenance": best_provenance,
            "expanded_ast": best_adaptive_ast,
        } if best_adaptive else None,
        "raw_proposal_slots": raw_slots,
        "trace": {
            "complete": trace.complete,
            "proposal_attempts": trace.proposal_attempts,
            "valid_proposal_count": trace.valid_proposal_count,
            "invalid_count": trace.invalid_count,
            "duplicate_count": trace.duplicate_count,
            "rejected_by_constraint_count": trace.rejected_by_constraint_count,
            "llm_calls": trace.llm_calls,
            "llm_tokens": trace.llm_tokens,
        },
    }


def _set_comparable_candidate_auc(conditions: dict[str, object]) -> None:
    rows = [conditions.get(name) for name in CONDITIONS]
    if not all(isinstance(row, dict) and "fitness" in row for row in rows):
        return
    comparable_n = min(
        int(row["counts"]["scored_adaptive_candidates"]) for row in rows
    )
    for row in rows:
        values = row["fitness"]["adaptive_unique_candidate_curve"][: comparable_n + 1]
        area = sum(
            (values[index - 1] + values[index]) / 2
            for index in range(1, len(values))
        )
        row["fitness"]["comparable_adaptive_evaluation_range"] = comparable_n
        row["fitness"]["adaptive_candidate_auc_trapezoid"] = area
        row["fitness"]["adaptive_candidate_auc_mean"] = area / comparable_n if comparable_n else None


def _standalone_e2_ids() -> set[str]:
    identities = {}
    for row in _read_jsonl(E2_RESULTS_PATH):
        name = row.get("requested_macro")
        identity = row.get("expanded_ast_identity")
        if name and identity and not row.get("duplicate_expanded_ast"):
            identities.setdefault(str(name), str(identity))
    if set(identities) != set(_RECIPE_LABELS) or len(set(identities.values())) != 3:
        raise ValueError("preserved E2 results do not contain three distinct standalone programs")
    return set(identities.values())


def _curve_segments(
    values: list[float], *, label: str, first_index: int
) -> str:
    if not values:
        return "no observations"
    segments: list[str] = []
    segment_start = 0
    current = values[0]
    for index, value in enumerate(values[1:], start=1):
        if value != current:
            start = first_index + segment_start
            end = first_index + index - 1
            segments.append(f"{label} {start}–{end}: {current:.6f}")
            segment_start = index
            current = value
    start = first_index + segment_start
    end = first_index + len(values) - 1
    segments.append(f"{label} {start}–{end}: {current:.6f}")
    return "; ".join(segments)


def _write_report(path: Path, results: dict[str, object], preflight: dict[str, object]) -> None:
    conditions = results["conditions"]
    lines = [
        "# LLMAO E4 — Controlled Abstraction Reuse Experiment",
        "",
        "Exploratory, single-seed comparison of three frozen structural behaviors as ordinary G0 recipes versus typed G_pilot macros. Both conditions reused the same 20 E1 initial score records, seed 202, E1 train-only split, guidance policy, evaluator, model configuration, and per-condition caps. No E2/E3 fitness or candidate was supplied to either optimizer. The fixed policy used Qwen `qwen3.5:35b-mlx`, temperature 0.65, at most 20 proposal attempts, 40 requests, 120 seconds per request, 2,500 output tokens per request, and 750,000 reserved tokens per condition.",
        "",
        "## Conditions and outcomes",
        "",
        "| Condition | Raw proposals | Attempts | Structurally valid | Duplicates | Adaptive scores | Best overall | Best adaptive | Attempt AUC mean (sum/20) | Unique-score AUC, k=0–14 (mean) |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for key in CONDITIONS:
        row = conditions[key]
        if "counts" not in row:
            label = "G0 + recipes" if key == "g0_recipes" else "G_pilot + macros"
            lines.append(f"| {label} | — | — | — | — | — | — | — | — | incomplete |")
            continue
        counts = row["counts"]
        fit = row["fitness"]
        label = "G0 + recipes" if key == "g0_recipes" else "G_pilot + macros"
        lines.append(
            f"| {label} | {counts['raw_proposals']} | {counts['attempt_slots']} | "
            f"{counts['valid_proposals_including_duplicates']} | {counts['duplicates']} | "
            f"{counts['scored_adaptive_candidates']} | {fit['best_overall']:.6f} | "
            f"{fit['best_adaptive'] if fit['best_adaptive'] is not None else '—'} | "
            f"{fit['attempt_budget_mean_best_fitness']:.6f} "
            f"(sum={fit['attempt_budget_auc']:.6f}) | "
            f"{fit['adaptive_candidate_auc_trapezoid']:.6f} "
            f"(mean={fit['adaptive_candidate_auc_mean']:.6f}) |"
        )
    lines += [
        "",
        "Attempt AUC is the right-endpoint sum of best-so-far fitness after attempts 1–20, divided by 20; unused authorized attempts hold the last best after a graceful cap stop. Unique-score AUC is the trapezoidal area over the shared range `k=0..14`, where `k=0` is the common initial best and `k=1..14` are the first 14 unique adaptive scores in each condition. The table shows the area and area divided by 14. Exact arrays remain in `e4_results.json`.",
        "",
        "## Best-so-far trajectories",
        "",
    ]
    for key in CONDITIONS:
        row = conditions[key]
        if "fitness" not in row:
            continue
        label = "G0 + recipes" if key == "g0_recipes" else "G_pilot + macros"
        attempt_curve = row["fitness"]["attempt_budget_curve"]
        score_curve = row["fitness"]["adaptive_unique_candidate_curve"][:15]
        lines.append(
            f"- **{label}:** {_curve_segments(attempt_curve, label='attempt', first_index=1)}. "
            f"Unique-score index (`k=0` is the common initial best): "
            f"{_curve_segments(score_curve, label='k', first_index=0)}."
        )
    lines += [
        "",
        "## Adoption and costs",
        "",
    ]
    for key in CONDITIONS:
        row = conditions[key]
        if "structural_reuse" not in row:
            lines.append(f"- **{key}:** incomplete; see `run_status.json` and preserved partial logs.")
            continue
        label = "G0 + recipes" if key == "g0_recipes" else "G_pilot + macros"
        reuse = row["structural_reuse"]
        cost = row["cost"]
        prompt = row["prompt_and_schema"]
        invalid_statuses = Counter(
            entry.get("status", "unknown")
            for entry in row["raw_proposal_slots"]
            if entry.get("status") not in {"scored", "duplicate"}
        )
        lines.append(
            f"- **{label}:** raw exact recipe-subtree proposals `"
            f"{reuse['raw_structural_pattern_proposals_by_name']}`; scored exact recipe-subtree use `"
            f"{reuse['scored_structural_pattern_use_by_name']}`; raw macro proposals `"
            f"{reuse['raw_macro_proposals_by_name']}`; typed-valid macro proposals `"
            f"{reuse['typed_valid_macro_proposals_by_name']}`; scored macro invocations `"
            f"{reuse['scored_macro_invocations_by_name']}`; "
            f"{row['counts']['invalid_proposals']} invalid attempts by status `{dict(invalid_statuses)}`; "
            f"{row['counts']['constraint_rejections']} structural/constraint rejections; "
            f"{cost['reported_total_tokens']} reported tokens "
            f"({cost['reported_input_tokens']} input, {cost['reported_output_tokens']} output) "
            f"over {cost['model_requests']} requests, reserved {cost['reserved_tokens']:,}/"
            f"{cost['token_limit']:,}; "
            f"{cost['search_wall_time_ms'] / 1000:.1f}s search wall time "
            f"({cost['model_request_time_ms'] / 1000:.1f}s summed request time); "
            f"mean prompt {prompt['prompt_bytes']['mean']:.0f} bytes "
            f"(max {prompt['prompt_bytes']['maximum']}); "
            f"{len(prompt['schema_hashes'])} schema variants; "
            f"{reuse['novel_composite_program_count']} novel scored composites beyond the three standalone E2/E3 ASTs, requiring a full recipe subtree."
        )
    lines += [
        "",
        "Both conditions received the same three expanded G0 recipe trees and the same focus-selection policy; mechanism focus remained guidance rather than an eligibility gate. The recipe text and focus policy were fixed, while the E1 iterative prompt naturally summarized each run's own fresh scored candidates. G0 presented ordinary-language labels and G0 compositions. G_pilot presented the macro names and enabled their typed AST operations. Naming, AST syntax availability, and resulting prompt/schema length are the intended packaging differences. The exact-subtree adoption count requires the complete canonical recipe tree to occur under the scored AST; partial use of individual primitives is not counted as recipe adoption.",
        "",
        "## Best adaptive candidates",
        "",
    ]
    for key in CONDITIONS:
        row = conditions[key]
        best = row.get("best_adaptive_candidate")
        label = "G0 + recipes" if key == "g0_recipes" else "G_pilot + macros"
        if best is None:
            lines.append(f"- **{label}:** no adaptive candidate reached scoring.")
        else:
            lines.append(
                f"- **{label}:** candidate `{best['candidate_id']}` at proposal attempt "
                f"{best['proposal_attempt']}, fitness {best['fitness']:.6f}, accuracy "
                f"{best['accuracy']:.4f}, {best['feature_dim']} features, measured feature "
                f"runtime {best['runtime_ms']:.2f} ms. Raw proposal provenance and the full "
                f"expanded AST are stored in `e4_results.json`."
            )
    lines += [
        "",
        "## Interpretation and limits",
        "",
        "This one-seed run describes adoption and search behavior under these fixed prompts. Any score difference is not a general causal estimate: the conditions differ in operation names, AST syntax, schema vocabulary, and prompt length. Fitness includes measured runtime, which varies with local execution and cache state. It does not establish transfer or cross-task generalization.",
        "",
        "Seed provenance audit: each run trace, optimizer instance, and model request sequence used seed 202 (requests began 202, 203, and so on). A leftover constant stamped proposal IDs as `llm_iterative:101:<attempt>` through the optimizer context. This value only labels proposal IDs/metadata in the iterative optimizer and did not enter the prompt or model sampling seed; the adapter now propagates the requested seed. The completed searches were not rerun.",
        "",
        f"Data: split fingerprint `{preflight['data']['fingerprint']}`; train-only manifest SHA-256 `{preflight['data_manifest_sha256']}`. The official test partition was blocked at the data-access boundary.",
        "",
        (
            "Both conditions terminated within their frozen caps; no additional seed or search was run."
            if results["status"] == "completed_exploratory_e4"
            else "At least one condition is incomplete; partial evidence is preserved and no retry or additional seed was launched."
        ),
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_e4(
    *,
    data_config: E1MNISTDataConfig | None = None,
    output_root: Path = OUTPUT_ROOT,
) -> dict[str, object]:
    data_config = data_config or E1MNISTDataConfig()
    preflight = run_preflight(data_config=data_config, output_root=output_root)
    protocol, seeds = e1_runner._verified_protocol_and_seeds()
    language, _ = load_e1_pilot_language(ROOT)
    initial_rows = _load_shared_initial_scores(seeds)
    search_data = _load_train_data_with_boundary_guard(data_config)
    expansions = _macro_default_expansions(language)
    guidance = {
        "g0": _recipe_guidance(expansions, macros_enabled=False),
        "g_pilot": _recipe_guidance(expansions, macros_enabled=True),
    }
    preserved_hashes = _preserved_artifact_hashes()
    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(E1_COMMON_PATH, output_root / "common_initial_evaluations.json")
    _write_json(output_root / "preflight.json", preflight)
    _write_json(
        output_root / "e4_manifest.json",
        {
            "schema_version": 1,
            "experiment": "exploratory G0 recipe versus typed G_pilot packaging comparison",
            "seed": SEED,
            "protocol_sha256": protocol["protocol_sha256"],
            "conditions": {
                "g0_recipes": {
                    "grammar": "G0 operations only",
                    "prompt_guidance_sha256": preflight["recipe_guidance_sha256"]["g0_recipes"],
                },
                "g_pilot_macros": {
                    "grammar": "G0 operations plus exactly the three frozen G_pilot macros",
                    "prompt_guidance_sha256": preflight["recipe_guidance_sha256"]["g_pilot_macros"],
                },
            },
            "structural_recipes": {
                name: {
                    "description": _RECIPE_LABELS[name],
                    "expanded_ast_sha256": ast_hash(ast),
                    "expanded_g0_ast": ast.to_dict(),
                }
                for name, ast in expansions.items()
            },
            "condition_prompt_guidance": guidance,
            "shared_initial_score_sha256": preflight["shared_initial_scores_sha256"],
            "data_fingerprint": preflight["data"]["fingerprint"],
            "g_pilot_manifest_sha256": preflight["g_pilot_manifest_sha256"],
            "resource_caps": preflight["policy"]["resource_caps"],
            "attempt_accounting": "Every requested proposal slot in each model response consumes an attempt; validation retries consume additional attempts.",
            "fixed_model_policy": {
                "model": preflight["model"]["model"],
                "temperature": 0.65,
                "first_request_seed": SEED,
                "optimizer_guidance_evolved": False,
            },
            "preserved_e1_e2_e3_artifact_sha256": preserved_hashes,
            "e2_e3_fitness_exposed_to_optimizers": False,
            "e2_e3_candidates_used_as_initial_programs": False,
        },
    )
    statuses: dict[str, object] = {
        "seed": SEED,
        "status": "running",
        "conditions": {name: "pending" for name in CONDITIONS},
    }
    _write_json(output_root / "run_status.json", statuses)
    traces: dict[str, SearchTrace | None] = {name: None for name in CONDITIONS}
    condition_specs = (
        ("g0", "g0_recipes", None),
        ("g_pilot", "g_pilot_macros", language),
    )
    for optimizer_condition, output_name, condition_language in condition_specs:
        if e1_runner._active_v4_conflicts():
            statuses["conditions"][output_name] = "blocked_by_active_v4_run"
            statuses["status"] = "incomplete"
            _write_json(output_root / "run_status.json", statuses)
            continue
        statuses["conditions"][output_name] = "running"
        _write_json(output_root / "run_status.json", statuses)
        try:
            trace = e1_runner._run_condition(
                optimizer_condition,
                seeds,
                initial_rows,
                search_data,
                condition_language,
                output_root / output_name,
                seed=SEED,
                prompt_guidance=guidance[optimizer_condition],
                metrics_filename="e4_metrics.json",
                checkpoint_progress=True,
            )
            if trace.proposal_attempts > 20 or trace.llm_calls > 40:
                raise RuntimeError("E4 condition exceeded its frozen attempt or request cap")
            traces[output_name] = trace
            statuses["conditions"][output_name] = "completed" if trace.complete else "incomplete"
        except Exception as exc:  # noqa: BLE001 - persist a partial bounded run and continue the paired condition
            statuses["conditions"][output_name] = {
                "status": "incomplete",
                "error": f"{type(exc).__name__}: {exc}",
            }
            statuses["status"] = "incomplete"
        _write_json(output_root / "run_status.json", statuses)

    after_hashes = _preserved_artifact_hashes()
    if after_hashes != preserved_hashes:
        raise RuntimeError("E1/E2/E3 evidence changed during E4")
    standalone_ids = _standalone_e2_ids()
    analyzed: dict[str, object] = {}
    for output_name, trace in traces.items():
        if trace is None:
            trace_path = output_root / output_name / "trace.json"
            if not trace_path.exists():
                analyzed[output_name] = {"status": "incomplete", "reason": "no trace was written"}
                continue
            trace = read_trace(trace_path)
        condition_language = None if output_name == "g0_recipes" else language
        try:
            analyzed[output_name] = _analyze_condition(
                output_name,
                output_root / output_name,
                trace,
                initial_rows,
                condition_language,
                expansions,
                standalone_ids=standalone_ids,
            )
        except Exception as exc:  # noqa: BLE001 - retain raw artifacts and report analysis failure
            analyzed[output_name] = {
                "status": "incomplete",
                "analysis_error": f"{type(exc).__name__}: {exc}",
            }
    _set_comparable_candidate_auc(analyzed)
    completed = all(
        isinstance(analyzed.get(name), dict)
        and analyzed[name].get("status") == "completed"
        for name in CONDITIONS
    )
    results = {
        "schema_version": 1,
        "status": "completed_exploratory_e4" if completed else "incomplete_exploratory_e4",
        "seed": SEED,
        "definition": {
            "condition_a": "G0 plus the frozen structural behaviors expressed as ordinary G0 recipe compositions",
            "condition_b": "G_pilot plus the same frozen behaviors exposed as typed macro operations",
            "maximum_adaptive_attempts_per_condition": 20,
            "shared_initial_programs": 20,
        },
        "interpretation_boundary": "One-seed descriptive comparison; no causal generalization, cross-task transfer, or utility claim.",
        "initial_best_fitness": max(row.fitness for row in initial_rows),
        "data_fingerprint": preflight["data"]["fingerprint"],
        "data_manifest_sha256": preflight["data_manifest_sha256"],
        "g_pilot_manifest_sha256": preflight["g_pilot_manifest_sha256"],
        "preflight": preflight,
        "conditions": analyzed,
        "preserved_evidence_hashes_unchanged": True,
    }
    _write_json(output_root / "e4_results.json", results)
    _write_report(output_root / "REPORT.md", results, preflight)
    statuses["status"] = "completed" if completed else "incomplete"
    _write_json(output_root / "run_status.json", statuses)
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--run", action="store_true")
    parser.add_argument("--data-dir", type=Path, default=E1MNISTDataConfig().cache_dir)
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    args = parser.parse_args(argv)
    config = E1MNISTDataConfig(cache_dir=args.data_dir)
    result = (
        run_preflight(data_config=config, output_root=args.output_root)
        if args.preflight
        else run_e4(data_config=config, output_root=args.output_root)
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
