from __future__ import annotations

from bias_optimizer.dsl.primitives import PRIMITIVES
from bias_optimizer.optimizer_bench.semantic_ablation import LexicalMap


def test_lexical_map_is_reversible_and_preserves_types() -> None:
    lexical_map = LexicalMap.frozen_default()
    prompt = (
        "skeletonize: Image or BinaryImage -> Skeleton; "
        "spatial_split(Image)->Vector with rows=2, cols=3; "
        "measure=centroid_x"
    )
    anonymized = lexical_map.anonymize(prompt)
    assert "skeletonize" not in anonymized
    assert "spatial_split" not in anonymized
    assert "Image or BinaryImage -> Skeleton" in anonymized
    assert "Vector" in anonymized
    assert lexical_map.restore(anonymized) == prompt


def test_lexical_map_covers_every_v3_primitive_without_identifier_collisions() -> None:
    lexical_map = LexicalMap.frozen_default()
    token_map = dict(lexical_map.pairs)
    assert set(PRIMITIVES).issubset(token_map)
    assert len(token_map) == len(lexical_map.pairs)
    assert len(set(token_map.values())) == len(token_map)
    assert token_map["threshold"] != token_map["skeletonize"]


def test_lexical_map_round_trips_schema_keys_enums_and_constraints() -> None:
    lexical_map = LexicalMap.frozen_default()
    schema = {
        "properties": {
            "op": {"enum": ["spatial_split", "skeletonize"]},
            "params": {
                "rows": {"type": "integer", "minimum": 1, "maximum": 7},
                "measure": {"enum": ["length", "centroid_x"]},
            },
        }
    }
    anonymized = lexical_map.transform_json(schema)
    restored = lexical_map.transform_json(anonymized, restore=True)
    rows_key = dict(lexical_map.pairs)["rows"]
    assert restored == schema
    assert anonymized["properties"]["op"]["enum"] != [
        "spatial_split",
        "skeletonize",
    ]
    assert anonymized["properties"]["params"][rows_key]["minimum"] == 1
