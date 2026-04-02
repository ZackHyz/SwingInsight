from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from swinginsight.domain.prediction.similarity import bar_count_similarity, trajectory_similarity


def test_bar_count_similarity_prefers_same_length_segments() -> None:
    assert bar_count_similarity(21, 21) == 1.0
    assert bar_count_similarity(21, 24) > bar_count_similarity(21, 34)
    assert bar_count_similarity(21, 34) > bar_count_similarity(21, 43)


def test_bar_count_similarity_is_symmetric() -> None:
    assert bar_count_similarity(21, 34) == bar_count_similarity(34, 21)


def test_trajectory_similarity_prefers_closer_full_path_even_when_lengths_differ() -> None:
    current = [0.0, -0.03, -0.07, -0.12, -0.16, -0.19]
    shallow = [0.0, -0.01, -0.02, -0.03, -0.05, -0.08]
    close_match = [0.0, -0.02, -0.05, -0.09, -0.12, -0.15, -0.17, -0.2]

    assert trajectory_similarity(current, close_match) > trajectory_similarity(current, shallow)
