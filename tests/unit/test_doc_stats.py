import json
import pytest
from analysis import data_stats, render_docs


@pytest.mark.slow
def test_data_stats_current():
    """data_stats.json matches the shipped data and reconciles."""
    assert data_stats.compute() == json.loads(data_stats.OUTPUT_PATH.read_text(encoding="utf-8"))


def test_doc_stat_markers_current():
    """Every deterministic stat marker in the docs matches data_stats.json."""
    assert render_docs.check() == []
