"""
Leakage-Safe Dataset Splitting Utility
======================================
Provides verifiable chronological and grouped train/val/test partitioning.
Ensures zero temporal or spatial leakage between splits, validating disjointness.
"""

from typing import Any, Callable, Dict, List, Set, Tuple


def chronological_split(
    records: List[Dict[str, Any]],
    date_key: str = "record_date",
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Partitions time-series records into train, validation, and test splits strictly
    in chronological order to prevent forward-looking temporal leakage.
    """
    if not (0.0 < train_ratio < 1.0 and 0.0 <= val_ratio < 1.0 and (train_ratio + val_ratio) < 1.0):
        raise ValueError("Invalid split ratios. train + val must be < 1.0.")

    # Sort strictly by date_key
    sorted_records = sorted(records, key=lambda x: str(x[date_key]))
    n = len(sorted_records)
    if n == 0:
        return [], [], []

    train_end = int(n * train_ratio)
    val_end = int(n * (train_ratio + val_ratio))

    train_split = sorted_records[:train_end]
    val_split = sorted_records[train_end:val_end]
    test_split = sorted_records[val_end:]

    return train_split, val_split, test_split


def group_split(
    records: List[Dict[str, Any]],
    group_key: str = "farm_id",
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    seed: int = 42,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Partitions records by unique entities (e.g., farm_id, plot_id, field) such that
    no group entity is shared across train, validation, or test partitions.
    """
    import random

    unique_groups = sorted(list(set(r[group_key] for r in records if group_key in r)))
    rng = random.Random(seed)
    rng.shuffle(unique_groups)

    n_groups = len(unique_groups)
    train_end = max(1, int(n_groups * train_ratio))
    val_end = max(train_end + 1, int(n_groups * (train_ratio + val_ratio)))

    train_groups = set(unique_groups[:train_end])
    val_groups = set(unique_groups[train_end:val_end])
    test_groups = set(unique_groups[val_end:])

    # Edge case: small group count adjustments
    if not test_groups and len(val_groups) > 1:
        test_groups.add(val_groups.pop())

    train_split = [r for r in records if r.get(group_key) in train_groups]
    val_split = [r for r in records if r.get(group_key) in val_groups]
    test_split = [r for r in records if r.get(group_key) in test_groups]

    return train_split, val_split, test_split


def verify_split_disjointness(
    train_split: List[Dict[str, Any]],
    val_split: List[Dict[str, Any]],
    test_split: List[Dict[str, Any]],
    key_func: Callable[[Dict[str, Any]], Any],
) -> Dict[str, Any]:
    """
    Verifies that train, val, and test partitions have zero overlap on the extracted key.
    Returns status and overlap sets.
    """
    train_keys: Set[Any] = set(key_func(r) for r in train_split)
    val_keys: Set[Any] = set(key_func(r) for r in val_split)
    test_keys: Set[Any] = set(key_func(r) for r in test_split)

    train_val_overlap = train_keys & val_keys
    train_test_overlap = train_keys & test_keys
    val_test_overlap = val_keys & test_keys

    is_disjoint = not (train_val_overlap or train_test_overlap or val_test_overlap)

    return {
        "is_disjoint": is_disjoint,
        "train_count": len(train_split),
        "val_count": len(val_split),
        "test_count": len(test_split),
        "train_val_overlap": list(train_val_overlap),
        "train_test_overlap": list(train_test_overlap),
        "val_test_overlap": list(val_test_overlap),
    }


def verify_chronological_integrity(
    train_split: List[Dict[str, Any]],
    val_split: List[Dict[str, Any]],
    test_split: List[Dict[str, Any]],
    date_key: str = "record_date",
) -> Dict[str, Any]:
    """
    Verifies that max(train_date) <= min(val_date) <= min(test_date).
    """
    if not train_split or not test_split:
        return {"has_leakage": False, "message": "One or more splits are empty"}

    max_train = max(str(r[date_key]) for r in train_split)
    min_test = min(str(r[date_key]) for r in test_split)
    max_val = max(str(r[date_key]) for r in val_split) if val_split else max_train
    min_val = min(str(r[date_key]) for r in val_split) if val_split else max_train

    has_leakage = (max_train > min_val) or (max_val > min_test)

    return {
        "has_leakage": has_leakage,
        "max_train_date": max_train,
        "min_val_date": min_val,
        "max_val_date": max_val,
        "min_test_date": min_test,
    }
