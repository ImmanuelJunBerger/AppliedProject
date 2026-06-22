from crypto_mlsystem.cpcv import (
    LabelInterval,
    assert_no_leakage,
    combinatorial_purged_splits,
    contiguous_groups,
    embargo_train_indices,
    purge_train_indices,
)


def test_cpcv_split_generation_count_and_coverage():
    splits = combinatorial_purged_splits(60, n_groups=5, n_test_groups=2, label_horizon=3, embargo=2)
    assert len(splits) == 10
    assert all(s.test_indices for s in splits)
    assert all(set(s.train_indices).isdisjoint(s.test_indices) for s in splits)


def test_purging_removes_overlapping_label_intervals():
    intervals = [LabelInterval(i, i + 2) for i in range(10)]
    kept = purge_train_indices(range(10), [4], intervals)
    assert 2 not in kept and 3 not in kept and 4 not in kept and 5 not in kept and 6 not in kept
    assert 1 in kept and 7 in kept


def test_embargo_removes_samples_after_test_observations():
    kept = embargo_train_indices(range(10), [4], n_samples=10, embargo=3)
    assert 5 not in kept and 6 not in kept and 7 not in kept
    assert 3 in kept and 8 in kept


def test_no_future_leakage_from_cpcv_splits():
    splits = combinatorial_purged_splits(90, n_groups=6, n_test_groups=1, label_horizon=5, embargo=4)
    assert all(assert_no_leakage(split, label_horizon=5, embargo=4, n_samples=90) for split in splits)


def test_groups_are_chronological_and_inside_training_window():
    groups = contiguous_groups(12, 3)
    assert groups == [tuple(range(0, 4)), tuple(range(4, 8)), tuple(range(8, 12))]
    splits = combinatorial_purged_splits(12, n_groups=3, n_test_groups=1, label_horizon=1, embargo=1)
    assert all(max(split.test_indices) < 12 and min(split.test_indices) >= 0 for split in splits)
