from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

from bias_optimizer.dsl.ast import Expr
from bias_optimizer.dsl.validator import ProgramConstraints, SearchTrack
from bias_optimizer.llm.ollama_client import LLMTokenUsage, OllamaClientError
from bias_optimizer.optimizer_bench.budget import SearchBudget
from bias_optimizer.optimizer_bench.e1 import (
    DEFAULT_E1_RESOURCE_CAPS,
    E1BudgetedClient,
    E1BudgetExceeded,
    E1IterativeOptimizer,
    E1ResourceCaps,
    E1TokenLedger,
    canonical_e1_program,
    e1_output_schema,
    load_e1_pilot_language,
    verify_e1_grammar,
)
from bias_optimizer.optimizer_bench.objective import ast_hash
from bias_optimizer.optimizer_bench.optimizers.base import OptimizationContext
from bias_optimizer.v4.language import expand_candidate
from bias_optimizer.v4.language.base_language import EXCLUDED_V3_OPERATIONS

ROOT = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location("llmao_e1_runner", ROOT / "experiments/e1.py")
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError("cannot load E1 command module for its helper tests")
e1_runner = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = e1_runner
_SPEC.loader.exec_module(e1_runner)


def _operation_constants(value) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        properties = value.get("properties")
        operation = properties.get("op") if isinstance(properties, dict) else None
        if isinstance(operation, dict) and isinstance(operation.get("const"), str):
            found.add(operation["const"])
        for child in value.values():
            found.update(_operation_constants(child))
    elif isinstance(value, list):
        for child in value:
            found.update(_operation_constants(child))
    return found


def test_e1_grammars_expose_g0_only_and_frozen_pilot_macros() -> None:
    language, manifest = load_e1_pilot_language(ROOT)
    g0_grammar = verify_e1_grammar(None)
    pilot_grammar = verify_e1_grammar(language)
    g0_ops = _operation_constants(e1_output_schema(None))
    pilot_ops = _operation_constants(e1_output_schema(language))

    assert not g0_ops.intersection(EXCLUDED_V3_OPERATIONS)
    assert g0_ops == set(g0_grammar["g0_operations"])
    assert pilot_ops == set(pilot_grammar["g0_operations"]) | set(language.macro_map)
    assert pilot_ops - set(g0_grammar["g0_operations"]) == {
        "stroke_degree_profile",
        "multiscale_spatial_profile",
        "multiscale_spatial_degree_profile",
    }
    assert manifest["official_G_star"] is False


def test_frozen_macros_expand_deterministically_with_g0_limits_and_canonical_identity() -> None:
    language, _ = load_e1_pilot_language(ROOT)
    g0_ops = set(verify_e1_grammar(None)["g0_operations"])
    for macro in language.macros:
        call = Expr(macro.name, tuple(Expr("image") for _ in macro.input_types), {})
        expanded_a, used = canonical_e1_program(call, language)
        expanded_b, _ = canonical_e1_program(call, language)
        checked = expand_candidate(call, language, introduced_macros=())
        direct, no_macros = canonical_e1_program(expanded_a, None)

        assert used == (macro.name,)
        assert not no_macros
        assert expanded_a.to_json() == expanded_b.to_json()
        assert set(checked.info.operations) <= g0_ops
        assert checked.info.depth <= 6
        assert checked.info.node_count <= 127
        assert checked.info.dimension is None or checked.info.dimension <= 128
        assert ast_hash(expanded_a) == ast_hash(direct)


def test_pilot_prompt_lists_only_g0_and_its_three_macro_signatures() -> None:
    from bias_optimizer.dsl.validator import SearchTrack
    from bias_optimizer.llm.program_proposer import (
        ProgramSearchContext,
        build_program_prompt,
    )
    from bias_optimizer.optimizer_bench.e1 import _e1_prompt

    language, _ = load_e1_pilot_language(ROOT)
    context = ProgramSearchContext(
        generation=1,
        track=SearchTrack.DISCOVERY,
        max_feature_dim=128,
        top_candidates=(),
        underexplored_cells=(),
        mechanism_focus="free_exploration",
    )
    g0_prompt = _e1_prompt(context, 1, None, 1)
    pilot_prompt = _e1_prompt(context, 1, language, 1)
    base_prompt = build_program_prompt(context, 1)
    assert not any(operation in g0_prompt for operation in EXCLUDED_V3_OPERATIONS)
    assert all(macro.name in pilot_prompt for macro in language.macros)
    assert not any(operation in pilot_prompt for operation in EXCLUDED_V3_OPERATIONS)
    assert base_prompt != g0_prompt


def test_bounded_client_enforces_timeout_output_and_total_token_reservation(
    tmp_path: Path,
) -> None:
    class FakeClient:
        model = "qwen3.5:35b-mlx"
        _last_usage = None

        def __init__(self) -> None:
            self.calls = []

        @property
        def last_usage(self):
            return self._last_usage

        def generate_structured(self, prompt, schema, **kwargs):
            self.calls.append((prompt, schema, kwargs))
            self._last_usage = LLMTokenUsage(prompt_tokens=40, response_tokens=8)
            return '{"proposals": []}'

    caps = E1ResourceCaps(
        max_attempts=1,
        max_requests=2,
        request_timeout_seconds=12,
        max_output_tokens=100,
        max_total_tokens=10_000,
    )
    fake = FakeClient()
    ledger = E1TokenLedger(caps)
    client = E1BudgetedClient(fake, ledger, tmp_path / "calls.jsonl", seed=101)
    schema = {"type": "object"}
    first = client.generate_structured("prompt", schema)
    second = client.generate_structured("prompt", schema)

    assert first == second
    assert len(fake.calls) == 2
    assert fake.calls[0][2] == {
        "temperature": 0.65,
        "seed": 101,
        "timeout_seconds": 12,
        "num_predict": 100,
    }
    assert fake.calls[1][2]["seed"] == 102
    assert ledger.requests == 2
    assert ledger.reported_tokens == 96
    assert ledger.reserved_tokens <= caps.max_total_tokens
    assert len((tmp_path / "calls.jsonl").read_text().splitlines()) == 2


def test_failed_and_duplicate_request_outputs_still_consume_the_hard_budget(
    tmp_path: Path,
) -> None:
    class FakeClient:
        model = "qwen3.5:35b-mlx"
        _last_usage = None

        @property
        def last_usage(self):
            return self._last_usage

        def generate_structured(self, prompt, schema, **kwargs):
            raise OllamaClientError("timed out")

    caps = E1ResourceCaps(
        max_attempts=1,
        max_requests=2,
        request_timeout_seconds=2,
        max_output_tokens=100,
        max_total_tokens=10_000,
    )
    ledger = E1TokenLedger(caps)
    client = E1BudgetedClient(FakeClient(), ledger, tmp_path / "calls.jsonl")
    for _ in range(2):
        with pytest.raises(OllamaClientError):
            client.generate_structured("same prompt", {"type": "object"})
    assert ledger.requests == 2
    assert ledger.reserved_tokens > 0
    assert ledger.unknown_failed_calls == 2
    assert len((tmp_path / "calls.jsonl").read_text().splitlines()) == 2


def test_request_is_refused_before_total_token_reservation_cap(tmp_path: Path) -> None:
    class FakeClient:
        model = "qwen3.5:35b-mlx"
        _last_usage = LLMTokenUsage(prompt_tokens=1, response_tokens=1)
        calls = 0

        @property
        def last_usage(self):
            return self._last_usage

        def generate_structured(self, prompt, schema, **kwargs):
            self.calls += 1
            return "{}"

    caps = E1ResourceCaps(
        max_attempts=1,
        max_requests=2,
        request_timeout_seconds=2,
        max_output_tokens=100,
        max_total_tokens=2_000,
    )
    fake = FakeClient()
    client = E1BudgetedClient(fake, E1TokenLedger(caps), tmp_path / "calls.jsonl")
    with pytest.raises(E1BudgetExceeded, match="token reservation"):
        client.generate_structured("x" * 2_000, {"type": "object"})
    assert fake.calls == 0


def test_resource_caps_reject_unbounded_request_timeouts() -> None:
    with pytest.raises(ValueError, match="finite and positive"):
        E1ResourceCaps(request_timeout_seconds=float("inf"))
    with pytest.raises(ValueError, match="finite and positive"):
        E1ResourceCaps(request_timeout_seconds=True)


def test_invalid_and_duplicate_outputs_both_consume_proposal_attempts(
    tmp_path: Path,
) -> None:
    valid = {
        "name": "valid",
        "hypothesis": "A structural cue may help.",
        "mechanism": "connected components",
        "program": {
            "op": "connected_components",
            "args": [
                {
                    "op": "threshold",
                    "args": [{"op": "image", "args": [], "params": {}}],
                    "params": {"value": 0.5},
                }
            ],
            "params": {},
        },
        "prediction": "Fitness may improve.",
        "falsification": "Reject if fitness does not improve.",
    }
    invalid = {
        **valid,
        "name": "invalid",
        "program": {"op": "excluded_v3_op", "args": [], "params": {}},
    }

    class FakeClient:
        model = "mock"

        def generate_structured(self, prompt, schema):
            return json.dumps({"proposals": [invalid, valid, valid]})

    constraints = ProgramConstraints(
        track=SearchTrack.DISCOVERY,
        max_feature_dim=128,
        max_depth=6,
        max_nodes=127,
        forbid_raw_pixels=True,
        require_vector_root=False,
    )
    optimizer = E1IterativeOptimizer(
        101,
        constraints,
        tmp_path / "responses.jsonl",
        client=FakeClient(),
        language=None,
    )
    batch = optimizer.propose(
        OptimizationContext(
            optimizer="llm_iterative",
            optimizer_seed=101,
            generation=1,
            proposal_attempt_start=1,
            remaining_attempts=6,
            batch_size=3,
            constraints=constraints,
            seed_programs=(),
            evaluated=(),
        )
    )

    assert batch.attempts == 3
    assert batch.valid_proposal_count == 2
    assert batch.duplicate_count == 1
    assert batch.invalid_count == 1
    assert len(batch.proposals) == 1
    assert batch.proposals[0].proposal_attempt == 2


def test_initial_scores_are_passed_as_the_same_tuple_to_both_conditions() -> None:
    rows = (object(), object())
    observed = []

    def run_condition(name, initial_rows):
        observed.append((name, initial_rows))
        return name

    result = e1_runner._run_pair_with_shared_scores(rows, run_condition)
    assert result == ("g0", "g_pilot")
    assert [name for name, _ in observed] == ["g0", "g_pilot"]
    assert observed[0][1] is rows
    assert observed[1][1] is rows


def test_common_initial_programs_are_scored_once_then_shared(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from bias_optimizer.optimizer_bench.schema import CandidateEvaluation

    protocol, seeds = e1_runner._verified_protocol_and_seeds()
    calls = []

    class FakeOracle:
        def __init__(self, **kwargs):
            pass

        def evaluate(self, program, *, evaluation_index, previously_evaluated, metadata):
            calls.append((program, evaluation_index, previously_evaluated))
            return CandidateEvaluation(
                candidate_id=ast_hash(program),
                evaluation_index=evaluation_index,
                fitness=0.5,
                accuracy=0.5,
                feature_dim=1,
                runtime_ms=1.0,
                structural_descriptor=("a", "b", "c", "d", "e"),
                program=program,
                metadata=metadata,
            )

    monkeypatch.setattr(e1_runner, "SearchOracle", FakeOracle)
    rows = e1_runner._score_common_initial_programs(seeds, object())
    shared = []
    e1_runner._run_pair_with_shared_scores(
        rows, lambda condition, scores: shared.append(scores) or condition
    )

    assert protocol["protocol_sha256"]
    assert len(calls) == len(rows) == 20
    assert len({row.candidate_id for row in rows}) == 20
    assert shared == [rows, rows]
    assert shared[0] is shared[1]


def test_v32_initial_programs_and_fixed_e1_budgets_remain_bounded() -> None:
    protocol, seeds = e1_runner._verified_protocol_and_seeds()
    budget = SearchBudget(total_evaluations=40, seed_evaluations=20, max_proposal_attempts=20)
    assert protocol["protocol_sha256"]
    assert len(seeds) == 20
    assert len({bias.program.to_json() for bias in seeds}) == 20
    assert budget.max_proposal_attempts == DEFAULT_E1_RESOURCE_CAPS.max_attempts
    assert DEFAULT_E1_RESOURCE_CAPS.max_requests == 2 * budget.max_proposal_attempts
