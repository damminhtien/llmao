"""V3 prompt and model adapter shared by one-shot and iterative LLM search."""

from __future__ import annotations

import json
from pathlib import Path

from bias_optimizer.domain.program import ProgramBiasSpec
from bias_optimizer.dsl.compiler import ProgramCompiler
from bias_optimizer.dsl.validator import ProgramConstraints, SearchTrack
from bias_optimizer.llm.ollama_client import OllamaLLMClient
from bias_optimizer.llm.program_proposer import (
    ProgramProposalError,
    ProgramProposer,
    ProgramSearchContext,
)
from bias_optimizer.llm.response_archive import JsonlResponseArchive
from bias_optimizer.novelty import DESCRIPTOR_TARGET_CELLS, MapElitesArchive
from bias_optimizer.novelty.descriptors import MECHANISM_FAMILIES, mechanism_family
from bias_optimizer.optimizer_bench.optimizers.base import (
    OptimizationContext,
    ProposalBatch,
)
from bias_optimizer.optimizer_bench.oracle import evaluation_record
from bias_optimizer.optimizer_bench.schema import CandidateEvaluation, CandidateProposal

_GENERATION_SIZE = 18
_PROPOSAL_BATCH_SIZE = 4


def _family_quotas() -> dict[str, int]:
    base, extra = divmod(_GENERATION_SIZE, len(MECHANISM_FAMILIES))
    return {
        family: base + (index < extra)
        for index, family in enumerate(MECHANISM_FAMILIES)
    }


def _fixed_family_schedule() -> tuple[str, ...]:
    quotas = _family_quotas()
    return tuple(family for family in MECHANISM_FAMILIES for _ in range(quotas[family]))


def _family_focus(accepted: dict[str, int]) -> str:
    quotas = _family_quotas()
    return next(
        (
            family
            for family in MECHANISM_FAMILIES
            if accepted.get(family, 0) < quotas[family]
        ),
        MECHANISM_FAMILIES[-1],
    )


def _program_biases(
    rows: tuple[CandidateEvaluation, ...],
) -> tuple[ProgramBiasSpec, ...]:
    biases = []
    for row in rows:
        if row.program is None:
            continue
        metadata = row.metadata or {}
        biases.append(
            ProgramBiasSpec(
                name=str(metadata.get("name", f"candidate_{row.candidate_id[:12]}")),
                hypothesis=str(
                    metadata.get(
                        "hypothesis",
                        "A typed program may encode a useful structural cue.",
                    )
                ),
                mechanism=str(metadata.get("mechanism", "V3 typed program")),
                program=row.program,
                prediction=str(
                    metadata.get("prediction", "Validation fitness will improve.")
                ),
                falsification=str(
                    metadata.get("falsification", "Reject if the score is poor.")
                ),
            )
        )
    return tuple(biases)


class LLMSearchOptimizer:
    """Base adapter that delegates parsing, validation and repair to V3 code."""

    name = "llm"
    iterative = False

    def __init__(
        self,
        seed: int,
        constraints: ProgramConstraints,
        response_path: Path,
        *,
        client: object | None = None,
    ) -> None:
        self._seed = seed
        self._constraints = constraints
        self._response_archive = JsonlResponseArchive(Path(response_path))
        selected_client = client or OllamaLLMClient.from_environment()
        if (
            isinstance(selected_client, OllamaLLMClient)
            and selected_client.model != "qwen3.5:35b-mlx"
        ):
            raise ValueError("V3.2 protocol requires the frozen qwen3.5:35b-mlx model")
        self._proposer = ProgramProposer(
            client=selected_client,  # type: ignore[arg-type]
            response_archive=self._response_archive,
        )
        self._compiler = ProgramCompiler(constraints)
        self._archive = MapElitesArchive()
        self._seed_biases: tuple[ProgramBiasSpec, ...] = ()
        self._seed_asts: set[str] = set()
        self._seen_asts: set[str] = set()
        self._family_counts: dict[int, dict[str, int]] = {}
        self._one_shot_schedule_position = 0
        self._attempts = 0
        self._llm_calls = 0
        self._llm_tokens = 0

    @property
    def llm_calls(self) -> int:
        return self._llm_calls

    @property
    def llm_tokens(self) -> int:
        return self._llm_tokens

    def on_seed_evaluations(
        self,
        proposals: tuple[CandidateProposal, ...],
        evaluations: tuple[CandidateEvaluation, ...],
    ) -> None:
        self._seed_biases = _program_biases(evaluations)
        self._seed_asts = {row.program.to_json() for row in evaluations if row.program}
        for row in evaluations:
            self._insert(row)

    def on_evaluation(
        self, proposal: CandidateProposal, evaluation: CandidateEvaluation
    ) -> None:
        self._insert(evaluation)
        family = (
            mechanism_family(evaluation.program)
            if evaluation.program
            else "free_exploration"
        )
        if self.iterative:
            counts = self._family_counts.setdefault(proposal.generation or 0, {})
            counts[family] = counts.get(family, 0) + 1

    def finish_generation(self) -> None:
        return None

    def _insert(self, row: CandidateEvaluation) -> None:
        if row.program is None:
            return
        self._seen_asts.add(row.program.to_json())
        self._archive.add(evaluation_record(row))

    def _context(
        self, context: OptimizationContext, focus: str
    ) -> ProgramSearchContext:
        if self.iterative:
            records = self._archive.top(5)
            cells = self._archive.underexplored_cells(DESCRIPTOR_TARGET_CELLS)
            explored = tuple(sorted(self._seen_asts))
            generation = context.generation
        else:
            records = ()
            cells = ()
            explored = tuple(program.to_json() for program in context.seed_programs)
            generation = 1
        return ProgramSearchContext(
            generation=generation,
            track=SearchTrack.DISCOVERY,
            max_feature_dim=128,
            top_candidates=records,
            underexplored_cells=cells,
            explored_programs=explored,
            mechanism_focus=focus,
        )

    def propose(self, context: OptimizationContext) -> ProposalBatch:
        if self.iterative:
            generation_counts = self._family_counts.setdefault(context.generation, {})
            focus = _family_focus(generation_counts)
            remaining_in_family = _family_quotas()[focus] - generation_counts.get(
                focus, 0
            )
        else:
            schedule = _fixed_family_schedule()
            position = self._one_shot_schedule_position % len(schedule)
            focus = schedule[position]
            remaining_in_family = 1
            while (
                position + remaining_in_family < len(schedule)
                and schedule[position + remaining_in_family] == focus
            ):
                remaining_in_family += 1
        count = min(
            _PROPOSAL_BATCH_SIZE,
            remaining_in_family,
            context.batch_size,
            context.remaining_attempts // 2,
        )
        if count <= 0:
            return ProposalBatch()
        if not self.iterative:
            # Advance from scheduled request slots, never from scores or accepted outputs.
            self._one_shot_schedule_position += count

        prompt_context = self._context(context, focus)
        previous = (
            _program_biases(context.evaluated) if self.iterative else self._seed_biases
        )
        before = self._response_archive.record_count()
        try:
            proposed = self._proposer.propose(
                prompt_context,
                previous_biases=previous,
                count=count,
            )
        except ProgramProposalError:
            proposed = ()
        response_rows = self._new_response_rows(before)
        duplicate_reference = self._seen_asts if self.iterative else self._seed_asts
        accounting = self._account_responses(
            response_rows,
            count,
            duplicate_reference=duplicate_reference,
        )
        self._attempts += accounting["attempts"]
        self._llm_calls += accounting["calls"]
        self._llm_tokens += accounting["tokens"]

        parent_ids = tuple(
            record.candidate_id for record in prompt_context.top_candidates
        )
        proposals = []
        for index, item in enumerate(proposed):
            metadata = {
                "name": item.bias.name,
                "hypothesis": item.bias.hypothesis,
                "mechanism": item.bias.mechanism,
                "prediction": item.bias.prediction,
                "falsification": item.bias.falsification,
                "model": item.model,
                "prompt": item.prompt,
                "requested_mechanism_family": focus,
            }
            attempt = (
                context.proposal_attempt_start + accounting["attempts"] - count + index
            )
            proposals.append(
                CandidateProposal(
                    program=item.bias.program,
                    proposal_id=f"{self.name}:{context.optimizer_seed}:{attempt}",
                    optimizer=self.name,
                    optimizer_seed=context.optimizer_seed,
                    generation=context.generation,
                    parent_ids=parent_ids,
                    mechanism_metadata=metadata,
                    proposal_attempt=attempt,
                )
            )
        valid, invalid, duplicates, constrained = accounting["validity"]
        return ProposalBatch(
            proposals=tuple(proposals),
            attempts=accounting["attempts"],
            valid_proposal_count=valid,
            invalid_count=invalid,
            duplicate_count=duplicates,
            rejected_by_constraint_count=constrained,
            llm_calls=accounting["calls"],
            llm_tokens=accounting["tokens"],
        )

    def _new_response_rows(self, before: int) -> tuple[dict[str, object], ...]:
        path = self._response_archive.path
        if not path.exists():
            return ()
        rows = [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        return tuple(rows[before:])

    def _account_responses(
        self,
        rows: tuple[dict[str, object], ...],
        requested_count: int,
        *,
        duplicate_reference: set[str],
    ) -> dict[str, object]:
        attempts = len(rows) * requested_count
        calls = len(rows)
        tokens = 0
        valid = invalid = duplicates = constrained = 0
        seen = set(duplicate_reference)
        for row in rows:
            prompt_tokens = row.get("prompt_tokens")
            response_tokens = row.get("response_tokens")
            if type(prompt_tokens) is int:
                tokens += prompt_tokens
            if type(response_tokens) is int:
                tokens += response_tokens
            raw = row.get("response")
            try:
                payload = json.loads(raw) if isinstance(raw, str) and raw else None
                items = payload.get("proposals") if isinstance(payload, dict) else None
                if not isinstance(items, list) or len(items) > requested_count:
                    raise ValueError("missing proposals array")
            except json.JSONDecodeError, TypeError, ValueError:
                invalid += requested_count
                continue
            invalid += max(0, requested_count - len(items))
            for item in items[:requested_count]:
                try:
                    bias = ProgramBiasSpec.from_dict(item)
                    self._compiler.compile(bias.program)
                except (KeyError, RecursionError, TypeError, ValueError) as exc:
                    message = str(exc)
                    if (
                        "exceeds" in message
                        or "not allowed" in message
                        or "limit" in message
                    ):
                        constrained += 1
                    else:
                        invalid += 1
                    continue
                valid += 1
                signature = bias.program.to_json()
                if signature in seen:
                    duplicates += 1
                else:
                    seen.add(signature)
        return {
            "attempts": attempts,
            "calls": calls,
            "tokens": tokens,
            "validity": (valid, invalid, duplicates, constrained),
        }


class LLMOneShotOptimizer(LLMSearchOptimizer):
    name = "llm_one_shot"
    iterative = False


class LLMIterativeOptimizer(LLMSearchOptimizer):
    name = "llm_iterative"
    iterative = True
