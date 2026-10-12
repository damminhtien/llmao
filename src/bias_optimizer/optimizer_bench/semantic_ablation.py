"""Protocol-bound lexical ablation for V3.2 iterative LLM search."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any

from bias_optimizer.dsl.primitives import PRIMITIVES
from bias_optimizer.llm.ollama_client import OllamaLLMClient
from bias_optimizer.novelty.descriptors import MECHANISM_FAMILIES
from bias_optimizer.optimizer_bench.runner import verify_protocol

_PARAMETER_NAMES = (
    "axis",
    "bins",
    "bins_x",
    "bins_y",
    "cols",
    "epsilon",
    "high",
    "high_x",
    "high_y",
    "lags",
    "low",
    "low_x",
    "low_y",
    "measure",
    "orders",
    "quantiles",
    "regions",
    "rows",
    "threshold",
    "value",
)
_ENUM_VALUES = (
    "branch_endpoints",
    "centroid_x",
    "centroid_y",
    "horizontal",
    "is_loop",
    "length",
    "vertical",
)
_VISION_TERMS = (
    "angle",
    "angles",
    "boundary",
    "branch",
    "centroid",
    "component",
    "contour",
    "cycle",
    "direction",
    "edge",
    "event",
    "gradient",
    "histogram",
    "local",
    "order",
    "path",
    "pixel",
    "region",
    "shape",
    "skeleton",
    "spatial",
    "stroke",
    "topology",
    "turn",
)
_BATCH_PATTERN = re.compile(r"This is proposal batch (\d+)")
_COUNT_PATTERN = re.compile(r"Propose exactly (\d+) distinct representation programs\.")


@dataclass(frozen=True, slots=True)
class LexicalMap:
    """Reversible names used only at the LLM prompt boundary."""

    pairs: tuple[tuple[str, str], ...]

    @classmethod
    def frozen_default(cls) -> LexicalMap:
        pairs: list[tuple[str, str]] = []
        pairs.extend(
            (name, f"op_{index:02d}")
            for index, name in enumerate(sorted(PRIMITIVES), start=1)
        )
        sources = {name for name, _ in pairs}
        pairs.extend(
            (name, f"param_{index:02d}")
            for index, name in enumerate(
                (name for name in _PARAMETER_NAMES if name not in sources), start=1
            )
        )
        pairs.extend(
            (name, f"value_{index:02d}")
            for index, name in enumerate(_ENUM_VALUES, start=1)
        )
        pairs.extend(
            (name, f"family_{index:02d}")
            for index, name in enumerate(MECHANISM_FAMILIES, start=1)
        )
        existing = {name for name, _ in pairs}
        concepts = sorted(set(_VISION_TERMS) - existing)
        pairs.extend(
            (name, f"concept_{index:02d}")
            for index, name in enumerate(concepts, start=1)
        )
        if len({target for _, target in pairs}) != len(pairs):
            raise ValueError("lexical anonymization identifiers must be unique")
        return cls(tuple(pairs))

    @classmethod
    def from_pairs(cls, pairs: list[list[str]]) -> LexicalMap:
        normalized = tuple((str(source), str(target)) for source, target in pairs)
        if not normalized or len({source for source, _ in normalized}) != len(normalized):
            raise ValueError("invalid frozen lexical map")
        if len({target for _, target in normalized}) != len(normalized):
            raise ValueError("frozen lexical map targets must be unique")
        return cls(normalized)

    def anonymize(self, text: str) -> str:
        return _replace_tokens(text, dict(self.pairs))

    def restore(self, text: str) -> str:
        return _replace_tokens(text, {target: source for source, target in self.pairs})

    def transform_json(self, value: Any, *, restore: bool = False) -> Any:
        mapping = (
            {target: source for source, target in self.pairs}
            if restore
            else dict(self.pairs)
        )
        if isinstance(value, str):
            return _replace_tokens(value, mapping)
        if isinstance(value, list):
            return [self.transform_json(item, restore=restore) for item in value]
        if isinstance(value, dict):
            return {
                _replace_tokens(str(key), mapping): self.transform_json(
                    item, restore=restore
                )
                for key, item in value.items()
            }
        return value

    def to_dict(self) -> dict[str, list[list[str]]]:
        return {"token_map": [[source, target] for source, target in self.pairs]}


def _replace_tokens(text: str, mapping: dict[str, str]) -> str:
    if not mapping:
        return text
    ordered = sorted(mapping, key=len, reverse=True)
    pattern = re.compile(
        r"(?<![A-Za-z0-9_])(" + "|".join(re.escape(item) for item in ordered) + r")(?![A-Za-z0-9_])"
    )
    return pattern.sub(lambda match: mapping[match.group(1)], text)


def freeze_semantic_protocol(root: Path) -> tuple[Path, str]:
    """Write the secondary protocol and hash before any ablation run starts."""
    root = Path(root)
    parent = verify_protocol(root)
    lexical_map = LexicalMap.frozen_default()
    payload = {
        "schema_version": 1,
        "study_id": "v3.2-semantic-ablation",
        "parent_protocol_sha256": parent["protocol_sha256"],
        "optimizer": "llm_iterative",
        "conditions": ["semantic_dsl", "anonymized_dsl"],
        "optimizer_seeds": parent["secondary_semantic_ablation"]["optimizer_seeds"],
        "total_unique_evaluations_per_run": parent["secondary_semantic_ablation"][
            "evaluations_per_run"
        ],
        "shared_seed_program_count": parent["budget"]["seed_evaluations"],
        "max_proposal_attempts_per_run": parent["budget"][
            "max_proposal_attempts_per_run"
        ],
        "model": "qwen3.5:35b-mlx",
        "temperature": 0.65,
        "generation_seed_rule": "proposal batch number plus repair attempt offset, matching V3 ProgramProposer",
        "anonymization": {
            "description": "Names and selected lexical labels are anonymized only at the LLM prompt and schema boundary. AST identifiers are restored before existing V3 parsing, validation, compilation, and evaluation.",
            **lexical_map.to_dict(),
            "preserved": [
                "operator count and mathematical implementations",
                "input and output types",
                "parameter constraints and numeric ranges",
                "AST depth, node, and dimension constraints",
                "candidate evaluator and training/validation data",
                "initial seed programs and candidate budget",
            ],
            "interpretation": "lexical-semantic ablation only; pretrained knowledge is not removed",
        },
    }
    encoded = (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
    digest = hashlib.sha256(encoded).hexdigest()
    payload["protocol_sha256"] = digest
    output = root / "results/v32/semantic_ablation_protocol.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output.parent / "semantic_ablation_protocol.sha256").write_text(
        f"{digest}  semantic_ablation_protocol.json\n", encoding="ascii"
    )
    return output, digest


def load_semantic_protocol(root: Path) -> tuple[dict[str, Any], LexicalMap]:
    root = Path(root)
    path = root / "results/v32/semantic_ablation_protocol.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    digest = payload.pop("protocol_sha256")
    encoded = (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
    actual = hashlib.sha256(encoded).hexdigest()
    checksum = (path.parent / "semantic_ablation_protocol.sha256").read_text(
        encoding="ascii"
    ).strip()
    parent = verify_protocol(root)
    if digest != actual or checksum != f"{digest}  semantic_ablation_protocol.json":
        raise ValueError("semantic ablation protocol hash mismatch")
    if payload["parent_protocol_sha256"] != parent["protocol_sha256"]:
        raise ValueError("semantic ablation protocol parent hash mismatch")
    lexical_map = LexicalMap.from_pairs(payload["anonymization"]["token_map"])
    payload["protocol_sha256"] = digest
    return payload, lexical_map


class AnonymizedOllamaClient:
    """Apply a reversible lexical map while preserving frozen V3 generation settings."""

    model = "qwen3.5:35b-mlx"

    def __init__(
        self,
        client: OllamaLLMClient,
        lexical_map: LexicalMap,
        interaction_path: Path,
    ) -> None:
        if client.model != self.model:
            raise ValueError(f"semantic ablation requires {self.model}")
        self._client = client
        self._lexical_map = lexical_map
        self._interaction_path = Path(interaction_path)
        self._calls_by_batch: dict[int, int] = {}

    @property
    def last_usage(self):
        return self._client.last_usage

    def generate_structured(self, prompt: str, schema: dict[str, object]) -> str:
        match = _BATCH_PATTERN.search(prompt)
        if match is None:
            raise ValueError("V3 prompt did not contain its proposal batch index")
        batch = int(match.group(1))
        count_match = _COUNT_PATTERN.search(prompt)
        if count_match is None:
            raise ValueError("V3 prompt did not contain its requested proposal count")
        proposal_count = int(count_match.group(1))
        attempt_index = self._calls_by_batch.get(batch, 0)
        self._calls_by_batch[batch] = attempt_index + 1
        seed = batch + attempt_index
        anonymized_prompt = self._lexical_map.anonymize(prompt)
        anonymized_schema = self._lexical_map.transform_json(schema)
        started = perf_counter()
        response = ""
        error = None
        try:
            response = self._client.generate_structured(
                anonymized_prompt,
                anonymized_schema,
                temperature=0.65,
                seed=seed,
                timeout_seconds=600.0,
                num_predict=6_000,
            )
            restored = self._restore_response(response)
            return restored
        except Exception as exc:
            error = str(exc)[:500]
            raise
        finally:
            usage = self._client.last_usage if error is None else None
            self._interaction_path.parent.mkdir(parents=True, exist_ok=True)
            record = {
                "model": self.model,
                "proposal_batch": batch,
                "proposal_count": proposal_count,
                "repair_attempt": attempt_index + 1,
                "seed": seed,
                "temperature": 0.65,
                "prompt_tokens": getattr(usage, "prompt_tokens", None),
                "response_tokens": getattr(usage, "response_tokens", None),
                "elapsed_ms": (perf_counter() - started) * 1_000,
                "prompt": anonymized_prompt,
                "schema_sha256": hashlib.sha256(
                    json.dumps(anonymized_schema, sort_keys=True).encode()
                ).hexdigest(),
                "response": response,
                "error": error,
            }
            with self._interaction_path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(record, ensure_ascii=False) + "\n")

    def _restore_response(self, response: str) -> str:
        try:
            payload = json.loads(response)
        except json.JSONDecodeError:
            return response
        restored = self._lexical_map.transform_json(payload, restore=True)
        return json.dumps(restored, ensure_ascii=False, separators=(",", ":"))
