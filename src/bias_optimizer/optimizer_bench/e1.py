"""Small E1 adapter over the frozen V3.2 optimizer and V4 language checks."""

from __future__ import annotations

import copy
import hashlib
import json
import time
from dataclasses import dataclass, replace
from math import isfinite
from pathlib import Path
from typing import Any

from bias_optimizer.domain.program import ProgramBiasSpec
from bias_optimizer.dsl.ast import Expr
from bias_optimizer.dsl.compiler import ProgramCompiler
from bias_optimizer.dsl.types import ValueType
from bias_optimizer.dsl.validator import ProgramConstraints, SearchTrack
from bias_optimizer.llm.ollama_client import OllamaClientError
from bias_optimizer.llm.program_proposer import (
    ProgramProposalError,
    ProgramProposer,
    ProgramSearchContext,
    _program_output_schema,
    build_program_prompt,
)
from bias_optimizer.llm.response_archive import JsonlResponseArchive, LLMResponseRecord
from bias_optimizer.novelty.descriptors import mechanism_family
from bias_optimizer.optimizer_bench.objective import ast_hash
from bias_optimizer.optimizer_bench.optimizers.base import (
    OptimizationContext,
    ProposalBatch,
)
from bias_optimizer.optimizer_bench.optimizers.llm_common import (
    LLMIterativeOptimizer,
    _family_quotas,
)
from bias_optimizer.optimizer_bench.schema import CandidateEvaluation, CandidateProposal
from bias_optimizer.v4.candidate.schema import load_macro_language
from bias_optimizer.v4.language import G0_LANGUAGE, MacroLanguage, expand_candidate
from bias_optimizer.v4.language.base_language import EXCLUDED_V3_OPERATIONS
from bias_optimizer.v4.language.validator import macro_behavior_hash

_ROOT = Path(__file__).resolve().parents[3]
_PILOT_PATH = Path("results/v4/languages/g_pilot_e1.json")
_PILOT_SIDECAR = Path("results/v4/languages/g_pilot_e1.json.sha256")
_G0_PATH = Path("results/v4/languages/g0.json")
_G0_SIDECAR = Path("results/v4/languages/g0.json.sha256")
_EXPECTED_MACRO_NAMES = frozenset(
    {
        "stroke_degree_profile",
        "multiscale_spatial_profile",
        "multiscale_spatial_degree_profile",
    }
)
# The other V3.2 labels depend on spatial_condition/path_summary/cross_histogram,
# which the frozen E1 G0 grammar excludes.
E1_REACHABLE_MECHANISM_FAMILIES = ("order_sensitive", "free_exploration")
_G0_OPERATIONS = frozenset(
    signature.name
    for signature in G0_LANGUAGE.primitives
    if signature.name != "flatten_pixels"
)
_CONSTRAINTS = ProgramConstraints(
    track=SearchTrack.DISCOVERY,
    max_feature_dim=128,
    max_depth=6,
    max_nodes=127,
    forbid_raw_pixels=True,
    require_vector_root=False,
)


@dataclass(frozen=True, slots=True)
class E1ResourceCaps:
    """Fixed request, turn, token, and proposal limits for either condition."""

    max_attempts: int = 20
    max_requests: int = 40
    request_timeout_seconds: float = 120.0
    max_output_tokens: int = 2_500
    max_total_tokens: int = 750_000

    def __post_init__(self) -> None:
        for name in ("max_attempts", "max_requests", "max_output_tokens", "max_total_tokens"):
            if type(getattr(self, name)) is not int or getattr(self, name) <= 0:
                raise ValueError(f"{name} must be a positive integer")
        if self.max_requests < 2 * self.max_attempts:
            raise ValueError("max_requests must cover the proposer's single repair retry")
        if (
            isinstance(self.request_timeout_seconds, bool)
            or not isinstance(self.request_timeout_seconds, (int, float))
            or not isfinite(self.request_timeout_seconds)
            or self.request_timeout_seconds <= 0
        ):
            raise ValueError("request_timeout_seconds must be finite and positive")


DEFAULT_E1_RESOURCE_CAPS = E1ResourceCaps()


class E1BudgetExceeded(RuntimeError):
    """Raised before a model request when a hard E1 cap would be exceeded."""


class E1TokenAccountingError(RuntimeError):
    """Raised when Ollama cannot report usage for a successful response."""


class E1TokenLedger:
    """Reserve a conservative per-request token bound, including failed calls."""

    def __init__(self, caps: E1ResourceCaps = DEFAULT_E1_RESOURCE_CAPS) -> None:
        self.caps = caps
        self.requests = 0
        self.reserved_tokens = 0
        self.reported_tokens = 0
        self.unknown_failed_calls = 0
        self.accounting_error: str | None = None

    def reserve(self, prompt: str, schema: dict[str, object]) -> int:
        if self.requests >= self.caps.max_requests:
            raise E1BudgetExceeded("E1 model-request cap reached")
        schema_bytes = json.dumps(
            schema, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        # UTF-8 bytes upper-bound ordinary tokenizer pieces; reserve output and
        # chat framing too, even when a call later fails or returns a duplicate.
        reservation = (
            len(prompt.encode("utf-8"))
            + len(schema_bytes)
            + 1_024
            + self.caps.max_output_tokens
        )
        if self.reserved_tokens + reservation > self.caps.max_total_tokens:
            raise E1BudgetExceeded("E1 total-token reservation cap reached")
        self.requests += 1
        self.reserved_tokens += reservation
        return reservation

    def record_usage(self, prompt_tokens: int | None, output_tokens: int | None) -> None:
        if prompt_tokens is None or output_tokens is None:
            self.unknown_failed_calls += 1
            return
        self.reported_tokens += prompt_tokens + output_tokens

    def to_dict(self) -> dict[str, int | str | None]:
        return {
            "requests": self.requests,
            "max_requests": self.caps.max_requests,
            "reserved_tokens": self.reserved_tokens,
            "reported_tokens": self.reported_tokens,
            "unknown_failed_calls": self.unknown_failed_calls,
            "accounting_error": self.accounting_error,
            "max_total_tokens": self.caps.max_total_tokens,
            "request_timeout_seconds": int(self.caps.request_timeout_seconds),
            "max_output_tokens_per_request": self.caps.max_output_tokens,
        }


class E1BudgetedClient:
    """Enforce identical local Ollama limits and archive each raw response."""

    def __init__(
        self,
        client: object,
        ledger: E1TokenLedger,
        call_log_path: Path,
        *,
        seed: int = 101,
    ) -> None:
        if not callable(getattr(client, "generate_structured", None)):
            raise TypeError("E1 requires a structured-generation Ollama client")
        self._client = client
        self.ledger = ledger
        self._call_log_path = Path(call_log_path)
        self._seed = seed

    @property
    def model(self) -> str:
        value = getattr(self._client, "model", "")
        return value if isinstance(value, str) else ""

    @property
    def last_usage(self) -> object | None:
        return getattr(self._client, "last_usage", None)

    def generate_structured(
        self, prompt: str, schema: dict[str, object]
    ) -> str:
        reservation = self.ledger.reserve(prompt, schema)
        request_number = self.ledger.requests
        reset = getattr(self._client, "_last_usage", None)
        if reset is not None:
            object.__setattr__(self._client, "_last_usage", None)
        started = time.perf_counter()
        raw_response = ""
        error: str | None = None
        try:
            raw_response = self._client.generate_structured(
                prompt,
                schema,
                temperature=0.65,
                seed=self._seed + request_number - 1,
                timeout_seconds=self.ledger.caps.request_timeout_seconds,
                num_predict=self.ledger.caps.max_output_tokens,
            )
        except OllamaClientError as exc:
            error = str(exc)[:500]
            usage = self.last_usage
            prompt_tokens, response_tokens = _usage_tokens(usage)
            self.ledger.record_usage(prompt_tokens, response_tokens)
            self._record_call(
                prompt, schema, raw_response, error, reservation, started,
                prompt_tokens, response_tokens,
            )
            raise

        usage = self.last_usage
        prompt_tokens, response_tokens = _usage_tokens(usage)
        self.ledger.record_usage(prompt_tokens, response_tokens)
        self._record_call(
            prompt, schema, raw_response, error, reservation, started,
            prompt_tokens, response_tokens,
        )
        if prompt_tokens is None or response_tokens is None:
            raise E1TokenAccountingError(
                "Ollama omitted successful-request token usage; stopping E1"
            )
        if response_tokens > self.ledger.caps.max_output_tokens:
            self.ledger.accounting_error = "Ollama exceeded the requested output-token cap"
            raise E1TokenAccountingError(self.ledger.accounting_error)
        if prompt_tokens + response_tokens > reservation:
            self.ledger.accounting_error = "Ollama usage exceeded its reserved token bound"
            raise E1TokenAccountingError(self.ledger.accounting_error)
        return raw_response

    def _record_call(
        self,
        prompt: str,
        schema: dict[str, object],
        raw_response: str,
        error: str | None,
        reservation: int,
        started: float,
        prompt_tokens: int | None,
        response_tokens: int | None,
    ) -> None:
        proposal_schema = schema.get("properties", {}).get("proposals", {})
        requested_proposals = (
            proposal_schema.get("maxItems")
            if isinstance(proposal_schema, dict)
            else None
        )
        record = {
            "request": self.ledger.requests,
            "model": self.model,
            "temperature": 0.65,
            "seed": self._seed + self.ledger.requests - 1,
            "timeout_seconds": self.ledger.caps.request_timeout_seconds,
            "max_output_tokens": self.ledger.caps.max_output_tokens,
            "requested_proposal_slots": requested_proposals,
            "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
            "schema_sha256": hashlib.sha256(
                json.dumps(schema, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest(),
            "prompt_tokens": prompt_tokens,
            "response_tokens": response_tokens,
            "reserved_tokens": reservation,
            "elapsed_ms": (time.perf_counter() - started) * 1_000,
            "raw_response": raw_response,
            "error": error,
        }
        self._call_log_path.parent.mkdir(parents=True, exist_ok=True)
        with self._call_log_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
            stream.flush()


def _usage_tokens(usage: object | None) -> tuple[int | None, int | None]:
    prompt = getattr(usage, "prompt_tokens", None)
    response = getattr(usage, "response_tokens", None)
    return (
        prompt if type(prompt) is int and prompt >= 0 else None,
        response if type(response) is int and response >= 0 else None,
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_e1_pilot_language(root: Path = _ROOT) -> tuple[MacroLanguage, dict[str, Any]]:
    """Verify the frozen G_pilot sidecar, V10 provenance, and strict macro lineage."""
    root = Path(root)
    manifest_path = root / _PILOT_PATH
    sidecar_path = root / _PILOT_SIDECAR
    expected_line = f"{_sha256(manifest_path)}  {_PILOT_PATH.name}"
    if sidecar_path.read_text(encoding="ascii").strip() != expected_line:
        raise ValueError("G_pilot E1 manifest checksum is invalid")
    g0_path = root / _G0_PATH
    g0_expected = f"{_sha256(g0_path)}  {_G0_PATH.name}"
    if (root / _G0_SIDECAR).read_text(encoding="ascii").strip() != g0_expected:
        raise ValueError("G0 language checksum is invalid")
    g0_value = json.loads(g0_path.read_text(encoding="utf-8"))
    if g0_value != G0_LANGUAGE.to_dict():
        raise ValueError("G0 language manifest differs from the current V4 validator")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "frozen_exploratory_language":
        raise ValueError("G_pilot is not frozen as exploratory")
    if manifest.get("official_G_star") is not False:
        raise ValueError("G_pilot must not be promoted to official G_star")
    pilot = manifest.get("g_pilot")
    if not isinstance(pilot, dict) or pilot.get("base_language_sha256") != G0_LANGUAGE.sha256:
        raise ValueError("G_pilot provenance does not name the current G0 base")
    selection = manifest.get("selection_rule", {})
    scope = selection.get("selection_scope", "")
    if "no V14" not in scope or "fresh-search" not in scope:
        raise ValueError("G_pilot selection provenance does not exclude V14 and fresh search")
    source_roots = manifest.get("source_evidence", {}).get("roots", [])
    if {item.get("seed") for item in source_roots} != {1101, 1202, 1303, 1404, 1505}:
        raise ValueError("G_pilot provenance must use exactly the five V10 discovery roots")
    if any(
        item.get("protocol_sha256") != "ef4050aa854baa0aefd0273c5ed5077b2f9ba6e4200dff7084d10668da54610d"
        or "/phase12/runs/discovery-" not in item.get("run_root", "")
        for item in source_roots
    ):
        raise ValueError("G_pilot source roots do not match the preserved V10 discovery")

    lineage = pilot.get("language_lineage")
    if not isinstance(lineage, list) or len(lineage) != 3:
        raise ValueError("G_pilot must contain three sequential language snapshots")
    parent: Any = G0_LANGUAGE
    loaded_lineage = []
    for snapshot in lineage:
        parent = load_macro_language(snapshot, parent)
        loaded_lineage.append(parent)
    language = loaded_lineage[-1]
    if language.to_dict() != pilot.get("language_snapshot"):
        raise ValueError("G_pilot final snapshot differs from the validated lineage")
    if language.sha256 != pilot.get("language_sha256"):
        raise ValueError("G_pilot language hash does not match its validated snapshot")
    macros = {macro.name: macro for macro in language.macros}
    if frozenset(macros) != _EXPECTED_MACRO_NAMES or pilot.get("macro_count") != 3:
        raise ValueError("G_pilot must contain exactly its three frozen macros")
    selected = {item["macro"]["name"]: item for item in pilot.get("macros", [])}
    if frozenset(selected) != _EXPECTED_MACRO_NAMES:
        raise ValueError("G_pilot selected-macro provenance is incomplete")
    behavior_ids: set[str] = set()
    for name, macro in macros.items():
        evidence = selected[name]
        if evidence.get("definition_sha256") != macro.sha256:
            raise ValueError(f"G_pilot macro identity mismatch for {name}")
        behavior = macro_behavior_hash(macro, language)
        if evidence.get("behavior_sha256") != behavior:
            raise ValueError(f"G_pilot macro behavior mismatch for {name}")
        if evidence.get("descendant_scored_candidates", 0) < 3:
            raise ValueError(f"G_pilot macro lacks the frozen descendant-use minimum: {name}")
        behavior_ids.add(behavior)
    if len(behavior_ids) != 3:
        raise ValueError("G_pilot macros do not have three distinct expanded behaviors")
    return language, manifest


def e1_output_schema(language: MacroLanguage | None, count: int = 1) -> dict[str, object]:
    """Build the existing typed program schema with only E1 G0 ops and macros."""
    schema = copy.deepcopy(_program_output_schema(count, track=SearchTrack.DISCOVERY))
    definitions = schema["$defs"]
    if not isinstance(definitions, dict):
        raise TypeError("V3.2 program schema is missing definitions")

    def prune(value: Any) -> Any:
        if isinstance(value, dict):
            properties = value.get("properties")
            operation = properties.get("op") if isinstance(properties, dict) else None
            if (
                isinstance(operation, dict)
                and "const" in operation
                and operation["const"] not in _G0_OPERATIONS
            ):
                return None
            if "$ref" in value and value["$ref"].startswith("#/$defs/"):
                key = value["$ref"].removeprefix("#/$defs/")
                if key not in definitions:
                    return None
            result: dict[str, Any] = {}
            for key, item in value.items():
                filtered = prune(item)
                if filtered is not None:
                    result[key] = filtered
            for key in ("anyOf", "oneOf"):
                if key in result and not result[key]:
                    return None
            return result
        if isinstance(value, list):
            return [item for child in value if (item := prune(child)) is not None]
        return value

    # Remove excluded branches bottom-up so references to empty types disappear.
    for depth in reversed(range(7)):
        for value_type in ValueType:
            key = f"expr_{value_type.value.lower()}_{depth}"
            if key in definitions:
                filtered = prune(definitions[key])
                if filtered is None:
                    del definitions[key]
                else:
                    definitions[key] = filtered
    filtered_root = prune(schema)
    if not isinstance(filtered_root, dict):
        raise TypeError("G0 grammar removed the complete proposal schema")
    schema = filtered_root
    definitions = schema["$defs"]

    if language is not None:
        for depth in range(1, 7):
            for macro in language.macros:
                children = [
                    {"$ref": f"#/$defs/expr_{value_type.value.lower()}_{depth - 1}"}
                    for value_type in macro.input_types
                ]
                if any(
                    child["$ref"].removeprefix("#/$defs/") not in definitions
                    for child in children
                ):
                    continue
                key = f"expr_{macro.output_type.value.lower()}_{depth}"
                target = definitions.get(key)
                if not isinstance(target, dict) or not isinstance(target.get("anyOf"), list):
                    continue
                parameter_schema = macro.to_dict()["parameters"]
                target["anyOf"].append(
                    {
                        "type": "object",
                        "properties": {
                            "op": {"const": macro.name},
                            "args": {
                                "type": "array",
                                "prefixItems": children,
                                "items": False,
                                "minItems": len(children),
                                "maxItems": len(children),
                            },
                            "params": parameter_schema,
                        },
                        "required": ["op", "args", "params"],
                        "additionalProperties": False,
                    }
                )
    return schema


def _format_e1_grammar(language: MacroLanguage | None) -> str:
    signatures = {item.name: item for item in G0_LANGUAGE.primitives}
    lines = ["Permitted G0 operations (flatten_pixels is forbidden by search constraints):"]
    for name in sorted(_G0_OPERATIONS):
        signature = signatures[name]
        inputs = ["|".join(value_types) for value_types in signature.input_types]
        if signature.variadic_input_types is not None:
            inputs.append("|".join(signature.variadic_input_types) + "...")
        params = json.loads(signature.parameters_json)
        lines.append(f"- {name}({', '.join(inputs)}) -> {signature.output_type}; params={json.dumps(params, sort_keys=True)}")
    if language is not None:
        lines.append("Frozen G_pilot macros (use these names as typed operations; no new macros):")
        for macro in language.macros:
            lines.append(
                f"- {macro.name}({', '.join(item.value for item in macro.input_types)}) "
                f"-> {macro.output_type.value}; {macro.description}; "
                f"params={json.dumps(macro.to_dict()['parameters'], sort_keys=True)}"
            )
    return "\n".join(lines)


def _e1_prompt(
    context: ProgramSearchContext,
    count: int,
    language: MacroLanguage | None,
    batch: int,
    prompt_guidance: str | None = None,
) -> str:
    prompt = build_program_prompt(context, count, proposal_batch=batch)
    start_marker = "The program is a typed expression tree. These are the only primitives and signatures:\n"
    end_marker = "\nTrack constraints:"
    if prompt.count(start_marker) != 1 or prompt.count(end_marker) != 1:
        raise RuntimeError("V3.2 prompt structure changed; update the E1 adapter explicitly")
    before, remainder = prompt.split(start_marker, 1)
    _, after = remainder.split(end_marker, 1)
    grammar = _format_e1_grammar(language)
    if prompt_guidance is not None:
        guidance = prompt_guidance.strip()
        if not guidance:
            raise ValueError("E1 prompt guidance must be non-empty when provided")
        grammar += "\n\n" + guidance
    prompt = before + start_marker + grammar + end_marker + after
    legacy_parameter_line = (
        "- Put parameters on their owning operation: measure on path_summary; "
        "axis/regions/bins/range on spatial_condition; bins_x/bins_y and ranges "
        "on cross_histogram; bins/orders/quantiles/lags/epsilon on their "
        "corresponding operations."
    )
    e1_parameter_line = (
        "- Put parameters on their owning permitted operation: threshold value; "
        "skeletonize threshold; histogram bins/range; moments orders; quantiles; "
        "autocorrelation lags; spatial_split rows/cols; sign epsilon; ratio epsilon."
    )
    if prompt.count(legacy_parameter_line) != 1:
        raise RuntimeError("V3.2 prompt parameter guidance changed; update E1 explicitly")
    prompt = prompt.replace(legacy_parameter_line, e1_parameter_line, 1)
    focus_marker = f"Requested mechanism family for this batch: {context.mechanism_focus}. "
    focus_text = {
        "order_sensitive": "Use a permitted order-sensitive operation such as delta, delta_angle, run_length_encode, or autocorrelation.",
        "spatial_relational": "Use spatial_split and combine its localized features with a second permitted structural summary.",
        "graph_relational": "Use graph, degree_sequence, paths, count, cycle_rank, moments, or histogram to express a graph-derived relation.",
        "free_exploration": "Prefer a global order-insensitive G0 structure such as cycle_rank(graph(skeletonize(image))) or moments(degree_sequence(graph(skeletonize(image)))).",
    }[context.mechanism_focus]
    if prompt.count(focus_marker) != 1:
        raise RuntimeError("V3.2 prompt focus structure changed; update the E1 adapter explicitly")
    before, after = prompt.split(focus_marker, 1)
    return before + focus_marker + focus_text + after.split("\n", 1)[1]


def _operations(program: Expr) -> frozenset[str]:
    return frozenset({program.op}.union(*(set(_operations(arg)) for arg in program.args)))


def canonical_e1_program(
    program: Expr, language: MacroLanguage | None
) -> tuple[Expr, tuple[str, ...]]:
    """Validate a G0/G_pilot AST and return its canonical expanded G0 form."""
    allowed = _G0_OPERATIONS | (frozenset(language.macro_map) if language else frozenset())
    if not _operations(program) <= allowed:
        raise ValueError("candidate uses an operation outside E1's permitted vocabulary")
    macro_names: tuple[str, ...] = ()
    if language is None:
        expanded = program
    else:
        expansion = expand_candidate(program, language, introduced_macros=())
        expanded = expansion.expanded_ast
        macro_names = expansion.used_macros
    if not _operations(expanded) <= _G0_OPERATIONS:
        raise ValueError("expanded candidate contains an operation outside E1 G0")
    ProgramCompiler(_CONSTRAINTS).compile(expanded)
    return expanded, macro_names


@dataclass(frozen=True, slots=True)
class _E1ProposedProgram:
    bias: ProgramBiasSpec
    model: str
    prompt: str
    raw_response: str
    macro_names: tuple[str, ...]


class E1ProgramProposer:
    """Minimal grammar-aware proposer that retains V3.2 prompts and archive IO."""

    def __init__(
        self,
        client: object,
        response_archive: JsonlResponseArchive,
        language: MacroLanguage | None,
        prompt_guidance: str | None = None,
    ) -> None:
        self._client = client
        self._response_archive = response_archive
        self._language = language
        self._prompt_guidance = prompt_guidance
        self._macro_names_by_program: dict[str, tuple[str, ...]] = {}
        self._proposal_slots_by_program: dict[str, int] = {}
        self._model = str(getattr(client, "model", "unspecified"))

    def propose(
        self,
        context: ProgramSearchContext,
        *,
        previous_biases: tuple[ProgramBiasSpec, ...] = (),
        count: int = 4,
    ) -> tuple[_E1ProposedProgram, ...]:
        prompt = _e1_prompt(
            context,
            count,
            self._language,
            self._response_archive.record_count() + 1,
            self._prompt_guidance,
        )
        schema = e1_output_schema(self._language, count)
        seen = {item.program.to_json() for item in previous_biases}
        archive_start = self._response_archive.record_count()
        previous_error = ""
        for attempt in (1, 2):
            request_prompt = (
                prompt if attempt == 1 else ProgramProposer._repair_prompt(prompt, previous_error)
            )
            try:
                raw_response = self._client.generate_structured(request_prompt, schema)
            except E1BudgetExceeded as exc:
                if self._response_archive.record_count() > archive_start:
                    raise ProgramProposalError(str(exc)) from exc
                raise
            except E1TokenAccountingError as exc:
                prompt_tokens, response_tokens = _usage_tokens(
                    getattr(self._client, "last_usage", None)
                )
                self._response_archive.record(
                    LLMResponseRecord(
                        prompt=request_prompt,
                        response="",
                        model=self._model,
                        attempt=attempt,
                        accepted=False,
                        error=str(exc)[:500],
                        prompt_tokens=prompt_tokens,
                        response_tokens=response_tokens,
                    )
                )
                raise ProgramProposalError(str(exc)) from exc
            except OllamaClientError as exc:
                self._response_archive.record(
                    LLMResponseRecord(
                        prompt=request_prompt,
                        response="",
                        model=self._model,
                        attempt=attempt,
                        accepted=False,
                        error=str(exc)[:500],
                    )
                )
                if attempt == 2:
                    raise ProgramProposalError("E1 model request failed after one retry") from exc
                previous_error = str(exc)
                continue

            usage = getattr(self._client, "last_usage", None)
            prompt_tokens, response_tokens = _usage_tokens(usage)
            try:
                raw_items = _response_items(raw_response, count)
                normalized_items: list[dict[str, object]] = []
                candidates: list[tuple[ProgramBiasSpec, tuple[str, ...], int]] = []
                errors: list[str] = []
                for index, item in enumerate(raw_items):
                    try:
                        bias = ProgramBiasSpec.from_dict(item)
                        expanded, macros = canonical_e1_program(bias.program, self._language)
                        normalized = replace(bias, program=expanded)
                        normalized_items.append(normalized.to_dict())
                        candidates.append((normalized, macros, index))
                    except (KeyError, RecursionError, TypeError, ValueError) as exc:
                        errors.append(f"proposal[{index}]: {str(exc)[:160]}")
                        normalized_items.append(_invalid_item(item))

                normalized_response = json.dumps(
                    {"proposals": normalized_items},
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=False,
                )
                accepted: list[_E1ProposedProgram] = []
                for bias, macros, proposal_slot in candidates:
                    signature = bias.program.to_json()
                    if signature in seen:
                        errors.append(f"{bias.name}: duplicate expanded program")
                        continue
                    seen.add(signature)
                    self._macro_names_by_program[signature] = macros
                    self._proposal_slots_by_program[signature] = proposal_slot
                    accepted.append(
                        _E1ProposedProgram(
                            bias=bias,
                            model=self._model,
                            prompt=request_prompt,
                            raw_response=raw_response,
                            macro_names=macros,
                        )
                    )
                error = "; ".join(errors[:8])[:500] or None
                self._response_archive.record(
                    LLMResponseRecord(
                        prompt=request_prompt,
                        response=normalized_response,
                        model=self._model,
                        attempt=attempt,
                        accepted=bool(accepted),
                        error=error,
                        prompt_tokens=prompt_tokens,
                        response_tokens=response_tokens,
                    )
                )
                if accepted:
                    return tuple(accepted)
                previous_error = error or "all E1 proposals were invalid or duplicates"
            except (json.JSONDecodeError, RecursionError, TypeError, ValueError) as exc:
                self._response_archive.record(
                    LLMResponseRecord(
                        prompt=request_prompt,
                        response=raw_response,
                        model=self._model,
                        attempt=attempt,
                        accepted=False,
                        error=str(exc)[:500],
                        prompt_tokens=prompt_tokens,
                        response_tokens=response_tokens,
                    )
                )
                previous_error = str(exc)
            if attempt == 2:
                raise ProgramProposalError("E1 response failed validation after one retry")
        raise ProgramProposalError("E1 response failed validation")

    def macro_names(self, program: Expr) -> tuple[str, ...]:
        return self._macro_names_by_program.get(program.to_json(), ())

    def proposal_slot(self, program: Expr) -> int:
        return self._proposal_slots_by_program[program.to_json()]


def _response_items(raw: str, count: int) -> list[dict[str, object]]:
    if not isinstance(raw, str) or len(raw) > 500_000:
        raise ValueError("E1 response is invalid or exceeds 500 KB")
    payload = json.loads(raw)
    if not isinstance(payload, dict) or set(payload) != {"proposals"}:
        raise ValueError("E1 response must contain only a proposals array")
    items = payload["proposals"]
    if not isinstance(items, list) or not items or len(items) > count:
        raise ValueError("E1 response proposal count is invalid")
    return items


def _invalid_item(item: object) -> dict[str, object]:
    if isinstance(item, dict):
        result = dict(item)
        result["program"] = {"op": "e1_invalid", "args": [], "params": {}}
        return result
    return {
        "name": "invalid_candidate",
        "hypothesis": "Invalid output is counted against the proposal budget.",
        "mechanism": "invalid output",
        "program": {"op": "e1_invalid", "args": [], "params": {}},
        "prediction": "No score is produced.",
        "falsification": "Validation rejects this placeholder.",
    }


class E1IterativeOptimizer(LLMIterativeOptimizer):
    """V3.2 adaptive selection with only the E1 grammar/proposer substituted."""

    def __init__(
        self,
        seed: int,
        constraints: ProgramConstraints,
        response_path: Path,
        *,
        client: object,
        language: MacroLanguage | None,
        prompt_guidance: str | None = None,
    ) -> None:
        super().__init__(seed, constraints, response_path, client=client)
        self._e1_proposer = E1ProgramProposer(
            client, self._response_archive, language, prompt_guidance
        )
        self._proposer = self._e1_proposer
        self._e1_focus_counts: dict[int, dict[str, int]] = {}

    def propose(self, context: OptimizationContext) -> ProposalBatch:
        focus_counts = self._e1_focus_counts.setdefault(context.generation, {})
        quotas = _family_quotas()
        if all(
            focus_counts.get(family, 0) >= quotas[family]
            for family in E1_REACHABLE_MECHANISM_FAMILIES
        ):
            focus_counts.clear()

        actual_counts = self._family_counts.setdefault(context.generation, {})
        saved_actual_counts = actual_counts.copy()
        actual_counts.clear()
        actual_counts.update(
            {
                family: (
                    focus_counts.get(family, 0)
                    if family in E1_REACHABLE_MECHANISM_FAMILIES
                    else quota
                )
                for family, quota in quotas.items()
            }
        )
        try:
            batch = super().propose(context)
        finally:
            actual_counts.clear()
            actual_counts.update(saved_actual_counts)
        if batch.llm_calls == 0 and batch.attempts == 0 and not batch.proposals:
            return batch
        if batch.llm_calls <= 0 or batch.attempts % batch.llm_calls:
            raise RuntimeError("E1 proposal attempts do not match archived response batches")
        batch_size = batch.attempts // batch.llm_calls
        last_response_start = context.proposal_attempt_start + batch.attempts - batch_size
        proposals = tuple(
            replace(
                proposal,
                proposal_attempt=(
                    last_response_start + self._e1_proposer.proposal_slot(proposal.program)
                ),
                mechanism_metadata={
                    **(proposal.mechanism_metadata or {}),
                    "actual_mechanism_family": mechanism_family(proposal.program),
                    "actual_candidate_operations": sorted(_operations(proposal.program)),
                    "g_pilot_macros_used": list(
                        self._e1_proposer.macro_names(proposal.program)
                    ),
                },
            )
            for proposal in batch.proposals
        )
        return replace(batch, proposals=proposals)

    def on_evaluation(
        self, proposal: CandidateProposal, evaluation: CandidateEvaluation
    ) -> None:
        super().on_evaluation(proposal, evaluation)
        requested = (proposal.mechanism_metadata or {}).get(
            "requested_mechanism_family"
        )
        if requested in E1_REACHABLE_MECHANISM_FAMILIES:
            counts = self._e1_focus_counts.setdefault(proposal.generation or 0, {})
            counts[requested] = counts.get(requested, 0) + 1


def common_seed_proposals(
    biases: tuple[ProgramBiasSpec, ...], seed: int = 101
) -> tuple[CandidateProposal, ...]:
    """Create one shared seed proposal tuple for both conditions."""
    return tuple(
        CandidateProposal(
            program=bias.program,
            proposal_id=f"e1-seed:{index}:{ast_hash(bias.program)}",
            optimizer="llm_iterative",
            optimizer_seed=seed,
            generation=0,
            parent_ids=(),
            mechanism_metadata={
                "name": bias.name,
                "hypothesis": bias.hypothesis,
                "mechanism": bias.mechanism,
                "prediction": bias.prediction,
                "falsification": bias.falsification,
                "seed_candidate": True,
            },
            proposal_attempt=1,
        )
        for index, bias in enumerate(biases, start=1)
    )


def verify_e1_grammar(language: MacroLanguage | None) -> dict[str, object]:
    """Return checks used by preflight; no data or model call is performed."""
    if _G0_OPERATIONS.intersection(EXCLUDED_V3_OPERATIONS):
        raise ValueError("G0 grammar contains an excluded V3 operation")
    if "flatten_pixels" in _G0_OPERATIONS:
        raise ValueError("raw pixels must remain forbidden by V3.2 search constraints")
    schema = e1_output_schema(language)
    op_constants: set[str] = set()

    def collect(value: Any) -> None:
        if isinstance(value, dict):
            properties = value.get("properties")
            op = properties.get("op") if isinstance(properties, dict) else None
            if isinstance(op, dict) and isinstance(op.get("const"), str):
                op_constants.add(op["const"])
            for item in value.values():
                collect(item)
        elif isinstance(value, list):
            for item in value:
                collect(item)

    collect(schema)
    expected = set(_G0_OPERATIONS) | (set(language.macro_map) if language else set())
    if op_constants != expected:
        raise ValueError(f"E1 proposal schema vocabulary mismatch: {sorted(op_constants ^ expected)}")
    return {
        "g0_operations": sorted(_G0_OPERATIONS),
        "macro_operations": sorted(language.macro_map) if language else [],
        "schema_operation_count": len(op_constants),
    }


__all__ = [
    "DEFAULT_E1_RESOURCE_CAPS",
    "E1BudgetExceeded",
    "E1BudgetedClient",
    "E1IterativeOptimizer",
    "E1ResourceCaps",
    "E1TokenAccountingError",
    "E1TokenLedger",
    "canonical_e1_program",
    "common_seed_proposals",
    "e1_output_schema",
    "load_e1_pilot_language",
    "verify_e1_grammar",
]
