"""Run a six-request, no-score probe of the frozen E1 G_pilot macros."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import urlopen

from bias_optimizer.domain.program import ProgramBiasSpec
from bias_optimizer.llm.ollama_client import OllamaClientError, OllamaLLMClient
from bias_optimizer.optimizer_bench.e1 import (
    E1BudgetedClient,
    E1BudgetExceeded,
    E1ResourceCaps,
    E1TokenAccountingError,
    E1TokenLedger,
    _format_e1_grammar,
    _response_items,
    canonical_e1_program,
    e1_output_schema,
    load_e1_pilot_language,
    verify_e1_grammar,
)
from bias_optimizer.optimizer_bench.objective import ast_hash
from bias_optimizer.v4.language import MacroLanguage, expand_candidate

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "results/v4/e2/macro_adoption_probe_2026-10-19"
EXPECTED_MACROS = (
    "stroke_degree_profile",
    "multiscale_spatial_profile",
    "multiscale_spatial_degree_profile",
)
REQUEST_SEED_START = 21_001
REQUEST_COUNT = 6
FOCUS = "free_exploration"
TEMPERATURE = 0.65
RESOURCE_CAPS = E1ResourceCaps(
    # E1 requires this legacy field to be positive. E2 makes one direct call
    # per request and never invokes E1ProgramProposer's repair loop.
    max_attempts=1,
    max_requests=REQUEST_COUNT,
    request_timeout_seconds=120.0,
    max_output_tokens=2_500,
    max_total_tokens=400_000,
)


@dataclass(frozen=True, slots=True)
class ProbeRequest:
    index: int
    macro: str
    replicate: int
    seed: int


def planned_requests() -> tuple[ProbeRequest, ...]:
    """Return the frozen two-request-per-macro schedule and Ollama seeds."""
    requests = tuple(
        ProbeRequest(
            index=index,
            macro=macro,
            replicate=replicate,
            seed=REQUEST_SEED_START + index - 1,
        )
        for index, (macro, replicate) in enumerate(
            ((name, replicate) for name in EXPECTED_MACROS for replicate in (1, 2)),
            start=1,
        )
    )
    if len(requests) != REQUEST_COUNT:
        raise RuntimeError("E2 must contain exactly six planned requests")
    if len({item.seed for item in requests}) != REQUEST_COUNT:
        raise RuntimeError("E2 request seeds must be unique")
    return requests


def _prompt(macro: str, language: MacroLanguage) -> str:
    if macro not in language.macro_map:
        raise ValueError(f"requested macro is absent from G_pilot: {macro}")
    return "\n".join(
        (
            "LLMAO E2 capability probe. Return exactly one typed image-",
            "representation proposal that invokes the requested frozen macro",
            "at least once in its raw program AST.",
            f"Requested macro: {macro}",
            f"Fixed mechanism focus: {FOCUS}",
            "Use only the permitted operations and signatures listed below.",
            "Use G0 operations to provide arguments with the required types.",
            "The structured-output schema requires one ProgramBiasSpec in a",
            "proposals array. Return JSON only, with no prose or code fence.",
            "Keep the expression within discovery constraints: depth at most 6,",
            "at most 127 AST nodes, feature width at most 128, no raw-pixel",
            "features, and no vector-root requirement.",
            "Do not define new macros or return an expanded replacement for the",
            "requested macro. This request is only a construction check; no score",
            "or search history is provided.",
            "",
            "Permitted signatures:",
            _format_e1_grammar(language),
        )
    )


def _schema_hash(schema: dict[str, object]) -> str:
    encoded = json.dumps(
        schema, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _macro_operations(
    raw: str, language: MacroLanguage
) -> tuple[bool | None, tuple[str, ...]]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError, TypeError:
        return None, ()

    program_values: list[object] = []
    if isinstance(payload, dict):
        proposals = payload.get("proposals")
        if isinstance(proposals, list):
            program_values.extend(
                item.get("program")
                for item in proposals
                if isinstance(item, dict) and "program" in item
            )
        elif "program" in payload:
            program_values.append(payload["program"])

    operations: set[str] = set()

    def visit(value: object) -> None:
        if isinstance(value, dict):
            operation = value.get("op")
            if isinstance(operation, str):
                operations.add(operation)
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    for program in program_values:
        visit(program)
    macros = tuple(sorted(operations.intersection(language.macro_map)))
    return True, macros


def inspect_response(
    request: ProbeRequest,
    raw: str,
    language: MacroLanguage,
    seen_expanded_ids: set[str],
    *,
    request_error: str | None = None,
    call_record: dict[str, object] | None = None,
) -> dict[str, object]:
    """Apply the existing E1 parsing, expansion, and strict structural checks."""
    macros_present: tuple[str, ...] = ()
    if request_error is None:
        parsed, macros_present = _macro_operations(raw, language)
        json_valid = parsed is True
    else:
        json_valid = None
    invokes_requested = (
        request.macro in macros_present if json_valid is not None else False
    )
    result: dict[str, object] = {
        "request": request.index,
        "requested_macro": request.macro,
        "replicate": request.replicate,
        "seed": request.seed,
        "fixed_focus": FOCUS,
        "raw_ast_invokes_requested_macro": invokes_requested,
        "raw_ast_macro_operations": list(macros_present),
        "json_valid": json_valid,
        "e1_response_schema_valid": None,
        "typed_program_schema_valid": None,
        "typed_structural_valid": None,
        "macro_expansion_success": None,
        "expanded_ast_identity": None,
        "duplicate_expanded_ast": None,
        "input_tokens": call_record.get("prompt_tokens") if call_record else None,
        "output_tokens": call_record.get("response_tokens") if call_record else None,
        "request_duration_ms": call_record.get("elapsed_ms") if call_record else None,
        "failure_reasons": [],
    }
    failures: list[str] = []
    if request_error is not None:
        failures.append("request_failed")
        result["request_error"] = request_error
        result["failure_reasons"] = failures
        return result

    if json_valid is not True:
        failures.append("invalid_json")
        result["failure_reasons"] = failures
        return result

    try:
        items = _response_items(raw, 1)
    except (json.JSONDecodeError, RecursionError, TypeError, ValueError) as exc:
        result["e1_response_schema_valid"] = False
        failures.append(f"invalid_e1_response_schema: {str(exc)[:200]}")
        if not invokes_requested:
            failures.append("requested_macro_not_invoked")
        result["failure_reasons"] = failures
        return result

    result["e1_response_schema_valid"] = True
    try:
        bias = ProgramBiasSpec.from_dict(items[0])
    except (KeyError, RecursionError, TypeError, ValueError) as exc:
        result["typed_program_schema_valid"] = False
        failures.append(f"invalid_typed_program_schema: {str(exc)[:200]}")
        if not invokes_requested:
            failures.append("requested_macro_not_invoked")
        result["failure_reasons"] = failures
        return result

    result["typed_program_schema_valid"] = True
    if not invokes_requested:
        failures.append("requested_macro_not_invoked")

    try:
        expansion = expand_candidate(bias.program, language, introduced_macros=())
    except (RecursionError, TypeError, ValueError) as exc:
        result["macro_expansion_success"] = False
        result["typed_structural_valid"] = False
        failures.append(f"macro_expansion_failed: {str(exc)[:200]}")
        result["failure_reasons"] = failures
        return result

    result["macro_expansion_success"] = True
    expanded_id = ast_hash(expansion.expanded_ast)
    result["expanded_ast_identity"] = expanded_id
    try:
        canonical, _ = canonical_e1_program(bias.program, language)
        if canonical.to_json() != expansion.expanded_ast.to_json():
            raise ValueError("E1 canonical expansion differs from macro expansion")
    except (RecursionError, TypeError, ValueError) as exc:
        result["typed_structural_valid"] = False
        failures.append(f"typed_structural_validation_failed: {str(exc)[:200]}")
        result["failure_reasons"] = failures
        return result

    result["typed_structural_valid"] = True
    duplicate = expanded_id in seen_expanded_ids
    result["duplicate_expanded_ast"] = duplicate
    seen_expanded_ids.add(expanded_id)
    if duplicate:
        failures.append("duplicate_expanded_ast")
    result["failure_reasons"] = failures
    return result


def _verify_local_model(client: OllamaLLMClient) -> dict[str, str]:
    host = urlsplit(client.base_url).hostname
    if client.model != "qwen3.5:35b-mlx":
        raise ValueError("E2 requires local qwen3.5:35b-mlx")
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("E2 requires a local Ollama endpoint")
    with urlopen(f"{client.base_url}/api/tags", timeout=3) as response:
        tags = json.loads(response.read())
    names = {
        item.get("name") for item in tags.get("models", []) if isinstance(item, dict)
    }
    if client.model not in names:
        raise ValueError(f"pinned local Ollama model is unavailable: {client.model}")
    return {"model": client.model, "base_url": client.base_url}


def _append_jsonl(path: Path, value: dict[str, object]) -> None:
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")
        stream.flush()


def _last_call_record(path: Path) -> dict[str, object]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines:
        raise RuntimeError("E1 client did not archive its model response")
    record = json.loads(lines[-1])
    if not isinstance(record, dict):
        raise TypeError("E1 client archive record is not an object")
    return record


def _summary(
    rows: list[dict[str, object]],
    requests_issued: int,
    ledger: E1TokenLedger,
    model: str,
) -> dict[str, object]:
    by_macro: dict[str, object] = {}
    for macro in EXPECTED_MACROS:
        group = [row for row in rows if row["requested_macro"] == macro]
        target_valid = [
            row
            for row in group
            if row["raw_ast_invokes_requested_macro"]
            and row["typed_structural_valid"] is True
        ]
        identities = {
            row["expanded_ast_identity"]
            for row in target_valid
            if isinstance(row["expanded_ast_identity"], str)
        }
        categories = Counter(
            str(reason).split(":", 1)[0]
            for row in group
            for reason in row["failure_reasons"]
        )
        by_macro[macro] = {
            "requests_planned": 2,
            "requests_issued": sum(row["request"] <= requests_issued for row in group),
            "raw_invocations": sum(
                row["raw_ast_invokes_requested_macro"] is True for row in group
            ),
            "raw_invocation_rate": sum(
                row["raw_ast_invokes_requested_macro"] is True for row in group
            )
            / 2,
            "structurally_valid_invocations": len(target_valid),
            "structurally_valid_invocation_rate": len(target_valid) / 2,
            "canonical_expansion_successes": sum(
                row["raw_ast_invokes_requested_macro"] is True
                and row["macro_expansion_success"] is True
                for row in group
            ),
            "distinct_expanded_programs": len(identities),
            "failure_categories": dict(sorted(categories.items())),
        }

    return {
        "experiment": "LLMAO E2 minimal macro adoption capability probe",
        "status": "completed" if requests_issued == REQUEST_COUNT else "incomplete",
        "model": model,
        "fixed_focus": FOCUS,
        "requests_planned": REQUEST_COUNT,
        "requests_issued": requests_issued,
        "scores_requested": False,
        "mnist_loaded": False,
        "official_test_partition_accessed": False,
        "reported_input_tokens": sum(
            row["input_tokens"] for row in rows if isinstance(row["input_tokens"], int)
        ),
        "reported_output_tokens": sum(
            row["output_tokens"]
            for row in rows
            if isinstance(row["output_tokens"], int)
        ),
        "reported_wall_seconds": round(
            sum(
                row["request_duration_ms"]
                for row in rows
                if isinstance(row["request_duration_ms"], (int, float))
            )
            / 1_000,
            3,
        ),
        "token_ledger": ledger.to_dict(),
        "per_macro": by_macro,
    }


def _write_once(path: Path, value: dict[str, object]) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write("\n")


def run_probe(
    *,
    output_root: Path = OUTPUT_ROOT,
    client: object | None = None,
) -> dict[str, object]:
    """Run exactly six direct requests; no evaluator, dataset, or repair path."""
    language, pilot_manifest = load_e1_pilot_language(ROOT)
    if tuple(sorted(language.macro_map)) != tuple(sorted(EXPECTED_MACROS)):
        raise ValueError("verified G_pilot does not contain the three E2 target macros")
    grammar = verify_e1_grammar(language)
    if set(grammar["macro_operations"]) != set(EXPECTED_MACROS):
        raise ValueError(
            "E1 grammar does not expose the complete frozen G_pilot vocabulary"
        )
    schema = e1_output_schema(language, count=1)
    prepared = []
    for request in planned_requests():
        prompt = _prompt(request.macro, language)
        prepared.append((request, prompt))

    schema_bytes = json.dumps(
        schema, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    reserved_tokens = sum(
        len(prompt.encode("utf-8"))
        + len(schema_bytes)
        + 1_024
        + RESOURCE_CAPS.max_output_tokens
        for _, prompt in prepared
    )
    if reserved_tokens > RESOURCE_CAPS.max_total_tokens:
        raise ValueError("six E2 requests exceed the conservative total-token cap")
    root = Path(output_root)
    if root.exists():
        raise FileExistsError(f"E2 output directory must be fresh: {root}")

    real_client = client is None
    if client is None:
        client = OllamaLLMClient.from_environment()
        model_manifest = _verify_local_model(client)
    else:
        model_manifest = {
            "model": str(getattr(client, "model", "")),
            "injected_test_client": "true",
        }
    if getattr(client, "model", None) != "qwen3.5:35b-mlx":
        raise ValueError("E2 client model must be qwen3.5:35b-mlx")

    root.mkdir(parents=True, exist_ok=False)
    calls_path = root / "model_calls.jsonl"
    results_path = root / "request_results.jsonl"
    plan_requests: list[dict[str, object]] = []
    for request, prompt in prepared:
        plan_requests.append(
            {
                "request": request.index,
                "requested_macro": request.macro,
                "replicate": request.replicate,
                "seed": request.seed,
                "focus": FOCUS,
                "prompt": prompt,
                "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
                "schema_sha256": _schema_hash(schema),
            }
        )
    _write_once(
        root / "request_plan.json",
        {
            "model": model_manifest,
            "temperature": TEMPERATURE,
            "timeout_seconds": RESOURCE_CAPS.request_timeout_seconds,
            "output_tokens_per_request": RESOURCE_CAPS.max_output_tokens,
            "max_model_requests": RESOURCE_CAPS.max_requests,
            "conservative_total_token_cap": RESOURCE_CAPS.max_total_tokens,
            "conservative_reserved_tokens_for_six_requests": reserved_tokens,
            "g_pilot_manifest_sha256": hashlib.sha256(
                (ROOT / "results/v4/languages/g_pilot_e1.json").read_bytes()
            ).hexdigest(),
            "g_pilot_language_sha256": language.sha256,
            "g_pilot_status": pilot_manifest["status"],
            "e1_schema_sha256": _schema_hash(schema),
            "requests": plan_requests,
        },
    )

    ledger = E1TokenLedger(RESOURCE_CAPS)
    budgeted = E1BudgetedClient(
        client,
        ledger,
        calls_path,
        seed=REQUEST_SEED_START,
    )
    seen_expanded_ids: set[str] = set()
    rows: list[dict[str, object]] = []
    stop_reason: str | None = None
    for request, prompt in prepared:
        request_error = None
        try:
            budgeted.generate_structured(prompt, schema)
        except (OllamaClientError, E1TokenAccountingError) as exc:
            request_error = str(exc)[:500]
        except E1BudgetExceeded as exc:
            stop_reason = str(exc)
            row = {
                "request": request.index,
                "requested_macro": request.macro,
                "replicate": request.replicate,
                "seed": request.seed,
                "fixed_focus": FOCUS,
                "request_issued": False,
                "raw_ast_invokes_requested_macro": False,
                "raw_ast_macro_operations": [],
                "json_valid": None,
                "e1_response_schema_valid": None,
                "typed_program_schema_valid": None,
                "typed_structural_valid": None,
                "macro_expansion_success": None,
                "expanded_ast_identity": None,
                "duplicate_expanded_ast": None,
                "input_tokens": None,
                "output_tokens": None,
                "request_duration_ms": None,
                "failure_reasons": ["request_not_issued_budget_refusal"],
            }
            rows.append(row)
            _append_jsonl(results_path, row)
            break

        if not calls_path.exists():
            raise RuntimeError(
                "E1 client returned without writing its raw-call archive"
            )
        call_record = _last_call_record(calls_path)
        raw_response = call_record.get("raw_response")
        if not isinstance(raw_response, str):
            raw_response = ""
        row = inspect_response(
            request,
            raw_response,
            language,
            seen_expanded_ids,
            request_error=request_error,
            call_record=call_record,
        )
        row["request_issued"] = True
        rows.append(row)
        _append_jsonl(results_path, row)
        if ledger.accounting_error:
            stop_reason = ledger.accounting_error
            break

    requests_issued = ledger.requests
    summary = _summary(rows, requests_issued, ledger, budgeted.model)
    summary["stop_reason"] = stop_reason
    summary["g_pilot_manifest_sha256"] = hashlib.sha256(
        (ROOT / "results/v4/languages/g_pilot_e1.json").read_bytes()
    ).hexdigest()
    if calls_path.exists():
        summary["raw_response_archive_sha256"] = hashlib.sha256(
            calls_path.read_bytes()
        ).hexdigest()
        os.chmod(calls_path, 0o444)
    _write_once(root / "summary.json", summary)
    os.chmod(root / "request_plan.json", 0o444)
    os.chmod(results_path, 0o444)
    os.chmod(root / "summary.json", 0o444)
    if real_client and summary["status"] != "completed":
        raise RuntimeError("E2 stopped before completing its six-request plan")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--preflight-only",
        action="store_true",
        help="verify the frozen language, local model, caps, and fresh output path",
    )
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    args = parser.parse_args()

    if args.preflight_only:
        language, _ = load_e1_pilot_language(ROOT)
        verify_e1_grammar(language)
        if args.output_root.exists():
            raise FileExistsError(
                f"E2 output directory must be fresh: {args.output_root}"
            )
        model = _verify_local_model(OllamaLLMClient.from_environment())
        schema = e1_output_schema(language, count=1)
        prepared = [
            (request, _prompt(request.macro, language))
            for request in planned_requests()
        ]
        reserved = sum(
            len(prompt.encode("utf-8"))
            + len(
                json.dumps(
                    schema,
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=False,
                ).encode("utf-8")
            )
            + 1_024
            + RESOURCE_CAPS.max_output_tokens
            for _, prompt in prepared
        )
        if reserved > RESOURCE_CAPS.max_total_tokens:
            raise ValueError("six E2 requests exceed the conservative total-token cap")
        print(
            json.dumps(
                {
                    "preflight": "passed",
                    "model": model,
                    "requests": [
                        {
                            "request": item.index,
                            "macro": item.macro,
                            "replicate": item.replicate,
                            "seed": item.seed,
                        }
                        for item, _ in prepared
                    ],
                    "focus": FOCUS,
                    "temperature": TEMPERATURE,
                    "timeout_seconds": RESOURCE_CAPS.request_timeout_seconds,
                    "output_tokens_per_request": RESOURCE_CAPS.max_output_tokens,
                    "max_model_requests": RESOURCE_CAPS.max_requests,
                    "reserved_tokens_for_six_requests": reserved,
                    "max_total_token_reservation": RESOURCE_CAPS.max_total_tokens,
                },
                indent=2,
            )
        )
        return 0

    result = run_probe(output_root=args.output_root)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
