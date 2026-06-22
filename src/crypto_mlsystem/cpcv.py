"""Combinatorial purged cross-validation utilities for financial time series.

The implementation is dependency-light on purpose so leakage-critical split logic can
be tested even in restricted environments where scientific packages are unavailable.
"""
from __future__ import annotations
from dataclasses import dataclass
from itertools import combinations
from typing import Iterable, Sequence

@dataclass(frozen=True)
class LabelInterval:
    """Observation label span using integer positions [start, end]."""
    start: int
    end: int

@dataclass(frozen=True)
class CPCVSplit:
    train_indices: tuple[int, ...]
    test_indices: tuple[int, ...]
    test_groups: tuple[int, ...]


def contiguous_groups(n_samples: int, n_groups: int) -> list[tuple[int, ...]]:
    if n_groups < 2 or n_groups > n_samples:
        raise ValueError("n_groups must be between 2 and n_samples")
    base, rem = divmod(n_samples, n_groups)
    groups = []
    start = 0
    for group in range(n_groups):
        size = base + (1 if group < rem else 0)
        groups.append(tuple(range(start, start + size)))
        start += size
    return groups


def default_label_intervals(n_samples: int, horizon: int) -> list[LabelInterval]:
    if horizon < 1:
        raise ValueError("horizon must be positive")
    return [LabelInterval(i, min(n_samples - 1, i + horizon)) for i in range(n_samples)]


def overlaps(a: LabelInterval, b: LabelInterval) -> bool:
    return a.start <= b.end and b.start <= a.end


def purge_train_indices(train: Iterable[int], test: Iterable[int], intervals: Sequence[LabelInterval]) -> tuple[int, ...]:
    test_intervals = [intervals[i] for i in test]
    kept = []
    for idx in train:
        if not any(overlaps(intervals[idx], test_interval) for test_interval in test_intervals):
            kept.append(idx)
    return tuple(kept)


def embargo_train_indices(train: Iterable[int], test: Iterable[int], n_samples: int, embargo: int) -> tuple[int, ...]:
    if embargo < 0:
        raise ValueError("embargo must be non-negative")
    blocked = set()
    for idx in test:
        blocked.update(range(idx + 1, min(n_samples, idx + embargo + 1)))
    return tuple(i for i in train if i not in blocked)


def combinatorial_purged_splits(
    n_samples: int,
    n_groups: int = 6,
    n_test_groups: int = 2,
    label_horizon: int = 1,
    embargo: int = 0,
) -> list[CPCVSplit]:
    """Create CPCV splits with purging and embargo.

    Splits are intended for hyperparameter tuning inside an already-fixed training
    window. Callers must pass only in-window samples; this function never reaches
    outside the provided sample count.
    """
    if n_test_groups < 1 or n_test_groups >= n_groups:
        raise ValueError("n_test_groups must be at least 1 and less than n_groups")
    groups = contiguous_groups(n_samples, n_groups)
    intervals = default_label_intervals(n_samples, label_horizon)
    all_indices = tuple(range(n_samples))
    splits = []
    for test_group_ids in combinations(range(n_groups), n_test_groups):
        test = tuple(i for gid in test_group_ids for i in groups[gid])
        train = tuple(i for i in all_indices if i not in set(test))
        train = purge_train_indices(train, test, intervals)
        train = embargo_train_indices(train, test, n_samples, embargo)
        splits.append(CPCVSplit(train, test, tuple(test_group_ids)))
    return splits


def assert_no_leakage(split: CPCVSplit, label_horizon: int, embargo: int, n_samples: int) -> bool:
    intervals = default_label_intervals(n_samples, label_horizon)
    for tr in split.train_indices:
        for te in split.test_indices:
            if overlaps(intervals[tr], intervals[te]):
                return False
            if te < tr <= te + embargo:
                return False
    return True
