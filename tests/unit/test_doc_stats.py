import json
import pytest
from analysis import data_stats, render_docs


class TestDocStats:
    """DOC STATS"""

    @pytest.mark.slow
    def test_data_stats_current(self):
        """should match data_stats.json to the shipped data, reconciled"""
        assert data_stats.compute() == json.loads(
            data_stats.OUTPUT_PATH.read_text(encoding="utf-8")
        ), "RUN: poe analysis"

    def test_markers_current(self):
        """should match every deterministic stat marker in the docs to data_stats.json"""
        assert render_docs.check() == [], "RUN: poe analysis"
