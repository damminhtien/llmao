from __future__ import annotations

import gzip
import hashlib
import struct
from pathlib import Path

import numpy as np
import pytest

import bias_optimizer.data.mnist as legacy_mnist
from bias_optimizer.data import mnist_e1


def _write_synthetic_train_files(root: Path, *, count: int = 100):
    root.mkdir(parents=True, exist_ok=True)
    images = np.arange(count * 28 * 28, dtype=np.uint8).reshape(count, 28, 28)
    labels = np.arange(count, dtype=np.uint8) % 10
    image_idx = struct.pack(">IIII", 2051, count, 28, 28) + images.tobytes()
    label_idx = struct.pack(">II", 2049, count) + labels.tobytes()
    image_archive = gzip.compress(image_idx, mtime=0)
    label_archive = gzip.compress(label_idx, mtime=0)
    image_name = "train-images-idx3-ubyte.gz"
    label_name = "train-labels-idx1-ubyte.gz"
    (root / image_name).write_bytes(image_archive)
    (root / label_name).write_bytes(label_archive)
    source = mnist_e1._TrainPartition(
        images=mnist_e1._TrainSource(
            image_name,
            hashlib.md5(image_archive).hexdigest(),
            hashlib.sha256(image_archive).hexdigest(),
            "https://example.invalid/train-images-idx3-ubyte.gz",
        ),
        labels=mnist_e1._TrainSource(
            label_name,
            hashlib.md5(label_archive).hexdigest(),
            hashlib.sha256(label_archive).hexdigest(),
            "https://example.invalid/train-labels-idx1-ubyte.gz",
        ),
        row_count=count,
    )
    return source, images, labels


def test_e1_loader_uses_only_pinned_train_idx_and_never_calls_legacy_or_test_loaders(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, images, labels = _write_synthetic_train_files(tmp_path)

    def forbidden(*args, **kwargs):
        raise AssertionError("E1 touched a legacy OpenML or final-data loader")

    monkeypatch.setattr(mnist_e1, "_OFFICIAL_TRAIN_PARTITION", source)
    monkeypatch.setattr(legacy_mnist, "_load_openml_arrays", forbidden)
    monkeypatch.setattr(legacy_mnist, "fetch_openml", forbidden)
    monkeypatch.setattr(legacy_mnist, "load_mnist_final_data", forbidden)
    original_read_bytes = Path.read_bytes
    accessed_files: list[str] = []

    def guarded_read_bytes(path: Path) -> bytes:
        accessed_files.append(path.name)
        if path.name.startswith("test-"):
            raise AssertionError("E1 attempted to read a test-partition file")
        return original_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", guarded_read_bytes)

    config = mnist_e1.E1MNISTDataConfig(
        cache_dir=tmp_path,
        seed=42,
        validation_size=20,
    )
    loaded = mnist_e1.load_mnist_e1_search_data(config)
    reference = legacy_mnist.split_search_data(
        images.astype(np.float32) / np.float32(255),
        labels.astype(np.int64),
        validation_size=20,
        seed=42,
    )

    assert np.array_equal(loaded.train_images, reference.train_images)
    assert np.array_equal(loaded.train_labels, reference.train_labels)
    assert np.array_equal(loaded.validation_images, reference.validation_images)
    assert np.array_equal(loaded.validation_labels, reference.validation_labels)
    manifest = tmp_path / "e1_search_data_manifest.json"
    assert manifest.is_file()
    assert set(accessed_files) == {
        "train-images-idx3-ubyte.gz",
        "train-labels-idx1-ubyte.gz",
    }
    assert len(loaded.train_labels) == 80
    assert len(loaded.validation_labels) == 20
    assert not (tmp_path / "test-images-idx3-ubyte.gz").exists()


def test_e1_loader_fails_closed_on_changed_training_archive(tmp_path: Path) -> None:
    source, _, _ = _write_synthetic_train_files(tmp_path)
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(mnist_e1, "_OFFICIAL_TRAIN_PARTITION", source)
    image_path = tmp_path / source.images.filename
    image_path.write_bytes(image_path.read_bytes() + b"tamper")
    try:
        with pytest.raises(ValueError, match="checksum mismatch"):
            mnist_e1.load_mnist_e1_search_data(
                mnist_e1.E1MNISTDataConfig(cache_dir=tmp_path, validation_size=20)
            )
    finally:
        monkeypatch.undo()
