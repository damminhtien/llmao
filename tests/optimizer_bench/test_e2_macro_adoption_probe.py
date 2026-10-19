from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

from bias_optimizer.domain.program import ProgramBiasSpec
from bias_optimizer.dsl.ast import Expr
from bias_optimizer.optimizer_bench.e1 import load_e1_pilot_language

ROOT = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location(
    "llmao_e2_macro_probe", ROOT / "experiments/e2_macro_adoption_probe.py"
)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError("cannot load E2 macro probe for its focused tests")
e2_probe = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = e2_probe
_SPEC.loader.exec_module(e2_probe)


def _raw_macro_response(macro_name: str) -> str:
    language, _ = load_e1_pilot_language(ROOT)
    macro = language.macro_map[macro_name]
    bias = ProgramBiasSpec(
        name=f"probe {macro_name}",
        hypothesis="A frozen typed abstraction can form a representation.",
        mechanism="explicit macro construction",
        program=Expr(
            macro_name,
            tuple(Expr("image") for _ in macro.input_types),
            {},
        ),
        prediction="The candidate is structurally valid.",
        falsification="The typed expression fails validation.",
    )
    return json.dumps({"proposals": [bias.to_dict()]}, separators=(",", ":"))


def test_requests_have_fixed_targets_seeds_and_example_free_prompt() -> None:
    language, _ = load_e1_pilot_language(ROOT)
    requests = e2_probe.planned_requests()
    schema = e2_probe.e1_output_schema(language, count=1)

    assert len(requests) == 6
    assert [request.macro for request in requests] == [
        macro for macro in e2_probe.EXPECTED_MACROS for _ in (1, 2)
    ]
    assert [request.seed for request in requests] == list(range(21_001, 21_007))
    assert len({request.seed for request in requests}) == 6
    assert schema["properties"]["proposals"]["maxItems"] == 1
    for request in requests:
        prompt = e2_probe._prompt(request.macro, language)
        assert "Fixed mechanism focus: free_exploration" in prompt
        assert f"Requested macro: {request.macro}" in prompt
        assert request.macro in prompt
        assert "stroke_degree_profile(" in prompt
        assert "multiscale_spatial_profile(" in prompt
        assert "multiscale_spatial_degree_profile(" in prompt
        assert "cycle_rank(graph(" not in prompt
        assert "Example solution" not in prompt


def test_raw_macro_invocation_expands_and_deduplicates_canonically() -> None:
    language, _ = load_e1_pilot_language(ROOT)
    seen: set[str] = set()

    for index, macro in enumerate(e2_probe.EXPECTED_MACROS, start=1):
        request = e2_probe.ProbeRequest(index, macro, 1, 21_000 + index)
        raw = _raw_macro_response(macro)
        first = e2_probe.inspect_response(request, raw, language, seen)
        repeated = e2_probe.inspect_response(request, raw, language, seen)

        assert first["json_valid"] is True
        assert first["e1_response_schema_valid"] is True
        assert first["typed_program_schema_valid"] is True
        assert first["raw_ast_invokes_requested_macro"] is True
        assert first["macro_expansion_success"] is True
        assert first["typed_structural_valid"] is True
        assert isinstance(first["expanded_ast_identity"], str)
        assert first["duplicate_expanded_ast"] is False
        assert repeated["duplicate_expanded_ast"] is True
        assert "duplicate_expanded_ast" in repeated["failure_reasons"]


def test_invalid_json_and_valid_program_without_target_are_recorded_as_failures() -> (
    None
):
    language, _ = load_e1_pilot_language(ROOT)
    request = e2_probe.planned_requests()[0]
    seen: set[str] = set()

    invalid = e2_probe.inspect_response(request, "{bad json", language, seen)
    assert invalid["json_valid"] is False
    assert invalid["failure_reasons"] == ["invalid_json"]

    non_target = _raw_macro_response("multiscale_spatial_profile")
    row = e2_probe.inspect_response(request, non_target, language, seen)
    assert row["json_valid"] is True
    assert row["typed_structural_valid"] is True
    assert row["raw_ast_invokes_requested_macro"] is False
    assert "requested_macro_not_invoked" in row["failure_reasons"]


def test_run_uses_one_capped_request_per_slot_and_freezes_raw_archive(
    tmp_path: Path,
) -> None:
    class FakeClient:
        model = "qwen3.5:35b-mlx"

        def __init__(self) -> None:
            self._last_usage = None
            self.calls = []

        @property
        def last_usage(self):
            return self._last_usage

        def generate_structured(self, prompt, schema, **kwargs):
            index = len(self.calls)
            macro = e2_probe.EXPECTED_MACROS[index // 2]
            self.calls.append((prompt, schema, kwargs))
            self._last_usage = SimpleNamespace(prompt_tokens=800, response_tokens=250)
            return _raw_macro_response(macro)

    fake = FakeClient()
    output_root = tmp_path / "e2"
    summary = e2_probe.run_probe(output_root=output_root, client=fake)

    assert len(fake.calls) == 6
    assert [call[2]["seed"] for call in fake.calls] == list(range(21_001, 21_007))
    assert all(
        call[2]
        == {
            "temperature": 0.65,
            "seed": 21_001 + index,
            "timeout_seconds": 120.0,
            "num_predict": 2_500,
        }
        for index, call in enumerate(fake.calls)
    )
    assert summary["status"] == "completed"
    assert summary["requests_issued"] == 6
    assert summary["scores_requested"] is False
    assert summary["mnist_loaded"] is False
    assert summary["official_test_partition_accessed"] is False
    for macro in e2_probe.EXPECTED_MACROS:
        row = summary["per_macro"][macro]
        assert row["raw_invocations"] == 2
        assert row["structurally_valid_invocations"] == 2
        assert row["canonical_expansion_successes"] == 2
        assert row["distinct_expanded_programs"] == 1
        assert row["failure_categories"] == {"duplicate_expanded_ast": 1}

    calls = [
        json.loads(line)
        for line in (output_root / "model_calls.jsonl").read_text().splitlines()
    ]
    assert len(calls) == 6
    assert all(isinstance(row["raw_response"], str) for row in calls)
    assert (output_root / "model_calls.jsonl").stat().st_mode & 0o222 == 0
    assert (output_root / "summary.json").exists()
