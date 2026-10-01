"""
End-to-end pipeline test on paper examples and c17 benchmark.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.netlist_graph import parse_netlist, levelize, clone_circuit
from src.implications.pipeline import run_implication_pipeline
from src.reporting.area import compute_area, compute_area_overhead


EXAMPLES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples")
SAMPLE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "benchmarks")


class TestPipelineFig4:
    def test_pipeline_runs(self):
        """Pipeline should run to completion on Fig. 4 without errors."""
        path = os.path.join(EXAMPLES_DIR, "fig4.txt")
        circuit = parse_netlist(path)
        levelize(circuit)

        original_area = compute_area(circuit)

        result = run_implication_pipeline(
            circuit,
            Th1=0.3, Th2=0.4, gain_threshold=0.02,
            num_patterns=1000,  # Fewer patterns for speed
            seed=42,
            verbose=False,
        )

        assert isinstance(result, dict)
        assert 'implications_added' in result
        assert result['implications_added'] >= 0

        # Area should not decrease
        new_area = compute_area(circuit)
        assert new_area >= original_area


class TestPipelineC17:
    def test_pipeline_on_c17(self):
        """Pipeline should run on c17 benchmark."""
        path = os.path.join(SAMPLE_DIR, "c17.txt")
        if not os.path.exists(path):
            return  # Skip if sample not available

        circuit = parse_netlist(path)
        levelize(circuit)

        result = run_implication_pipeline(
            circuit,
            Th1=0.3, Th2=0.4, gain_threshold=0.02,
            num_patterns=1000,
            seed=42,
            verbose=False,
        )

        assert isinstance(result, dict)
        assert 'implications_added' in result
