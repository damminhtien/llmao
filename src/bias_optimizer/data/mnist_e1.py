"""Train-only MNIST input for the exploratory E1 search."""

from __future__ import annotations

import gzip
import hashlib
import json
import struct
import tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.request import urlopen

import numpy as np
from numpy.typing import NDArray
from sklearn.model_selection import train_test_split

from bias_optimizer.data.mnist import MNISTSearchData, split_search_data

_MNIST_TRAIN_MIRROR = "https://ossci-datasets.s3.amazonaws.com/mnist/"
_MANIFEST_NAME = "e1_search_data_manifest.json"


@dataclass(frozen=True, slots=True)
class _TrainSource:
    filename: str
    md5: str
    sha256: str
    source_url: str


@dataclass(frozen=True, slots=True)
class _TrainPartition:
    images: _TrainSource
    labels: _TrainSource
    row_count: int = 60_000


_OFFICIAL_TRAIN_PARTITION = _TrainPartition(
    images=_TrainSource(
        filename="train-images-idx3-ubyte.gz",
        md5="f68b3c2dcbeaaa9fbdd348bbdeb94873",
        sha256="440fcabf73cc546fa21475e81ea370265605f56be210a4024d2ca8f203523609",
        source_url=f"{_MNIST_TRAIN_MIRROR}train-images-idx3-ubyte.gz",
    ),
    labels=_TrainSource(
        filename="train-labels-idx1-ubyte.gz",
        md5="d53e105ee54ea40749a09fcbcd1e9432",
        sha256="3552534a0a558bbed6aed32b30c495cca23d567ec52cac8be1a0730e8010255c",
        source_url=f"{_MNIST_TRAIN_MIRROR}train-labels-idx1-ubyte.gz",
    ),
)


@dataclass(frozen=True, slots=True)
class E1MNISTDataConfig:
    """Train-only IDX cache and the V3.2-compatible search split."""

    cache_dir: Path = Path("results/v4/e1/data/mnist/raw")
    seed: int = 42
    validation_size: int = 2_000

    def __post_init__(self) -> None:
        object.__setattr__(self, "cache_dir", Path(self.cache_dir))
        if type(self.seed) is not int or not 0 <= self.seed <= np.iinfo(np.uint32).max:
            raise ValueError("seed must fit in an unsigned 32-bit integer")
        if type(self.validation_size) is not int or self.validation_size <= 0:
            raise ValueError("validation_size must be positive")


def _file_hashes(path: Path) -> tuple[str, str]:
    payload = path.read_bytes()
    return hashlib.md5(payload).hexdigest(), hashlib.sha256(payload).hexdigest()


def _verify_cached_file(path: Path, source: _TrainSource) -> None:
    if not path.is_file():
        raise FileNotFoundError(
            f"pinned E1 MNIST training file is missing: {path}; "
            "run the explicit train-only cache preparation command"
        )
    md5_digest, sha256_digest = _file_hashes(path)
    if md5_digest != source.md5 or sha256_digest != source.sha256:
        raise ValueError(f"pinned E1 MNIST training checksum mismatch: {path.name}")


def prepare_mnist_e1_train_source(cache_dir: Path) -> tuple[Path, Path]:
    """Fetch and verify only the two official training IDX archives."""
    root = Path(cache_dir)
    root.mkdir(parents=True, exist_ok=True)
    paths = (root / _OFFICIAL_TRAIN_PARTITION.images.filename,
             root / _OFFICIAL_TRAIN_PARTITION.labels.filename)
    sources = (_OFFICIAL_TRAIN_PARTITION.images, _OFFICIAL_TRAIN_PARTITION.labels)
    for path, source in zip(paths, sources, strict=True):
        if path.exists():
            _verify_cached_file(path, source)
            continue
        with urlopen(source.source_url, timeout=60) as response:
            if response.geturl() != source.source_url:
                raise ValueError("E1 MNIST source redirected away from the pinned URL")
            payload = response.read()
        if hashlib.md5(payload).hexdigest() != source.md5:
            raise ValueError(f"downloaded E1 MNIST checksum mismatch: {path.name}")
        if hashlib.sha256(payload).hexdigest() != source.sha256:
            raise ValueError(f"downloaded E1 MNIST SHA-256 mismatch: {path.name}")
        with tempfile.NamedTemporaryFile(dir=root, delete=False) as temporary:
            temporary.write(payload)
            temporary_path = Path(temporary.name)
        temporary_path.replace(path)
    return paths


def _read_partition(
    root: Path, partition: _TrainPartition
) -> tuple[NDArray[np.uint8], NDArray[np.int64], dict[str, object]]:
    image_path = root / partition.images.filename
    label_path = root / partition.labels.filename
    _verify_cached_file(image_path, partition.images)
    _verify_cached_file(label_path, partition.labels)
    image_bytes = gzip.decompress(image_path.read_bytes())
    label_bytes = gzip.decompress(label_path.read_bytes())

    if len(image_bytes) < 16 or struct.unpack(">I", image_bytes[:4])[0] != 2051:
        raise ValueError("E1 MNIST training images have an invalid IDX header")
    _, image_count, rows, columns = struct.unpack(">IIII", image_bytes[:16])
    if (image_count, rows, columns) != (partition.row_count, 28, 28):
        raise ValueError("E1 MNIST training image shape does not match the pin")
    expected_image_bytes = 16 + image_count * rows * columns
    if len(image_bytes) != expected_image_bytes:
        raise ValueError("E1 MNIST training image payload has an invalid length")

    if len(label_bytes) < 8 or struct.unpack(">I", label_bytes[:4])[0] != 2049:
        raise ValueError("E1 MNIST training labels have an invalid IDX header")
    _, label_count = struct.unpack(">II", label_bytes[:8])
    if label_count != partition.row_count or len(label_bytes) != 8 + label_count:
        raise ValueError("E1 MNIST training label count does not match the pin")

    images = np.frombuffer(image_bytes, dtype=np.uint8, offset=16).reshape(
        partition.row_count, 28, 28
    )
    labels = np.frombuffer(label_bytes, dtype=np.uint8, offset=8).astype(np.int64)
    if np.any(labels > 9) or set(np.unique(labels)) != set(range(10)):
        raise ValueError("E1 MNIST training labels must cover digits 0 through 9")
    source_fingerprints = {
        "image_archive_md5": partition.images.md5,
        "image_archive_sha256": partition.images.sha256,
        "image_idx_sha256": hashlib.sha256(image_bytes).hexdigest(),
        "label_archive_md5": partition.labels.md5,
        "label_archive_sha256": partition.labels.sha256,
        "label_idx_sha256": hashlib.sha256(label_bytes).hexdigest(),
    }
    return images, labels, source_fingerprints


def _array_sha256(array: NDArray) -> str:
    values = np.ascontiguousarray(array)
    digest = hashlib.sha256()
    digest.update(str(values.shape).encode("ascii"))
    digest.update(values.dtype.str.encode("ascii"))
    digest.update(values.tobytes())
    return digest.hexdigest()


def _make_search_data(
    images: NDArray[np.uint8],
    labels: NDArray[np.int64],
    *,
    seed: int,
    validation_size: int,
) -> tuple[MNISTSearchData, dict[str, object]]:
    if validation_size >= len(labels):
        raise ValueError("validation_size must be smaller than the train partition")
    image_values = images.astype(np.float32) / np.float32(255)
    train_indices, validation_indices = train_test_split(
        np.arange(len(labels), dtype=np.int64),
        test_size=validation_size,
        random_state=seed,
        stratify=labels,
    )
    data = split_search_data(
        image_values,
        labels,
        validation_size=validation_size,
        seed=seed,
    )
    if not (
        np.array_equal(data.train_images, image_values[train_indices])
        and np.array_equal(data.validation_images, image_values[validation_indices])
        and np.array_equal(data.train_labels, labels[train_indices])
        and np.array_equal(data.validation_labels, labels[validation_indices])
    ):
        raise RuntimeError("E1 split differs from the existing MNIST search semantics")
    split_fingerprints: dict[str, object] = {
        "seed": seed,
        "validation_size": validation_size,
        "splitter": "sklearn.model_selection.train_test_split",
        "stratified_by": "official_training_labels",
        "train_indices_sha256": _array_sha256(train_indices),
        "validation_indices_sha256": _array_sha256(validation_indices),
        "train_images_sha256": _array_sha256(data.train_images),
        "train_labels_sha256": _array_sha256(data.train_labels),
        "validation_images_sha256": _array_sha256(data.validation_images),
        "validation_labels_sha256": _array_sha256(data.validation_labels),
    }
    return data, split_fingerprints


def _load_search_data(
    config: E1MNISTDataConfig,
    partition: _TrainPartition,
) -> MNISTSearchData:
    images, labels, source_fingerprints = _read_partition(config.cache_dir, partition)
    data, split_fingerprints = _make_search_data(
        images,
        labels,
        seed=config.seed,
        validation_size=config.validation_size,
    )
    manifest = {
        "schema_version": 1,
        "dataset": "MNIST official training partition only",
        "source": {
            "authority": "Yann LeCun MNIST, via the pinned PyTorch OSSCI mirror",
            "files": [
                {
                    "filename": partition.images.filename,
                    "url": partition.images.source_url,
                    "rows": partition.row_count,
                },
                {
                    "filename": partition.labels.filename,
                    "url": partition.labels.source_url,
                    "rows": partition.row_count,
                },
            ],
            "fingerprints": source_fingerprints,
        },
        "partition_shape": {
            "images": [partition.row_count, 28, 28],
            "labels": [partition.row_count],
        },
        "preprocessing": "uint8 pixels converted to float32 and divided by 255",
        "split": split_fingerprints,
    }
    manifest_path = config.cache_dir / _MANIFEST_NAME
    serialized = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    if manifest_path.exists():
        if manifest_path.read_text(encoding="utf-8") != serialized:
            raise ValueError("saved E1 MNIST split manifest does not match the data")
    else:
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(serialized, encoding="utf-8")
    return data


def load_mnist_e1_search_data(
    config: E1MNISTDataConfig | None = None,
) -> MNISTSearchData:
    """Load only checksum-pinned official training files and make the V3.2 split."""
    selected = config or E1MNISTDataConfig()
    return _load_search_data(selected, _OFFICIAL_TRAIN_PARTITION)


__all__ = [
    "E1MNISTDataConfig",
    "load_mnist_e1_search_data",
    "prepare_mnist_e1_train_source",
]
