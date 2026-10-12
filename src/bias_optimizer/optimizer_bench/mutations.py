"""Type-preserving mutation and crossover for GP over V3 expression trees."""

from __future__ import annotations

import random

from bias_optimizer.dsl.ast import Expr
from bias_optimizer.dsl.compiler import ProgramCompiler
from bias_optimizer.dsl.types import ValueType
from bias_optimizer.dsl.validator import ProgramConstraints, infer_type
from bias_optimizer.optimizer_bench.random_ast import (
    SamplingFailure,
    parameter_presets,
    sample_typed_subtree,
)

Path = tuple[int, ...]


def _nodes(program: Expr, path: Path = ()) -> tuple[tuple[Path, Expr, ValueType], ...]:
    rows = [(path, program, infer_type(program).value_type)]
    for index, child in enumerate(program.args):
        rows.extend(_nodes(child, (*path, index)))
    return tuple(rows)


def _replace(program: Expr, path: Path, replacement: Expr) -> Expr:
    if not path:
        return replacement
    index, *tail = path
    args = list(program.args)
    args[index] = _replace(args[index], tuple(tail), replacement)
    return Expr(program.op, tuple(args), program.parameter_values)


def _parameter_mutation(program: Expr, rng: random.Random) -> Expr | None:
    choices = []
    for path, node, _ in _nodes(program):
        options = [
            value
            for value in parameter_presets(node.op)
            if value != node.parameter_values
        ]
        if options:
            choices.append((path, node, options))
    if not choices:
        return None
    path, node, options = rng.choice(choices)
    replacement = Expr(node.op, node.args, rng.choice(options))
    return _replace(program, path, replacement)


def typed_mutation(
    program: Expr,
    rng: random.Random,
    *,
    constraints: ProgramConstraints,
) -> Expr:
    """Choose parameter or same-output-type subtree mutation with equal odds."""
    compiler = ProgramCompiler(constraints)
    sites = _nodes(program)
    for _ in range(32):
        if rng.random() < 0.5:
            candidate = _parameter_mutation(program, rng)
        else:
            path, _, value_type = rng.choice(sites)
            try:
                replacement = sample_typed_subtree(
                    rng,
                    value_type,
                    constraints=constraints,
                    target_depth=rng.randint(1, constraints.max_depth),
                )
                candidate = _replace(program, path, replacement)
            except SamplingFailure:
                continue
        if candidate is None or candidate.to_json() == program.to_json():
            continue
        try:
            compiler.compile(candidate)
        except TypeError, ValueError:
            continue
        return candidate
    raise SamplingFailure("no valid typed mutation found within 32 attempts")


def typed_crossover(
    left: Expr,
    right: Expr,
    rng: random.Random,
    *,
    constraints: ProgramConstraints,
) -> Expr:
    """Swap same-type subtrees, then validate the complete offspring."""
    left_nodes = _nodes(left)
    right_nodes = _nodes(right)
    compatible = [
        (left_path, right_path, left_node, right_node)
        for left_path, left_node, left_type in left_nodes
        for right_path, right_node, right_type in right_nodes
        if left_type is right_type
    ]
    rng.shuffle(compatible)
    for left_path, _, _, right_node in compatible:
        offspring = _replace(left, left_path, right_node)
        try:
            ProgramCompiler(constraints).compile(offspring)
        except TypeError, ValueError:
            continue
        if offspring.to_json() != left.to_json():
            return offspring
    raise SamplingFailure("no valid same-type subtree crossover found")
