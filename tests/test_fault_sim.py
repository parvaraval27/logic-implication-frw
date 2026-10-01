"""Tests for fault simulation: P0/P1 and Pdet estimation."""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.netlist_graph import parse_netlist, levelize, Node, Circuit
from src.faultsim.random_pattern_sim import (
    estimate_signal_probabilities,
    estimate_detection_probabilities,
)


EXAMPLES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples")


class TestSignalProbabilities:
    def test_simple_and_gate(self):
        """AND gate with 2 random inputs: P1 ≈ 0.25."""
        circuit = Circuit()
        a = Node("a", "PI"); a.role = "PI"; a.level = 0
        b = Node("b", "PI"); b.role = "PI"; b.level = 0
        out = Node("out", "AND"); out.level = 1
        out.fanins = [a, b]
        a.fanouts = [out]
        b.fanouts = [out]
        out.role = "PO"
        circuit.nodes = {"a": a, "b": b, "out": out}
        circuit.PIs = [a, b]
        circuit.POs = [out]

        estimate_signal_probabilities(circuit, num_patterns=10000, seed=42)

        # P1 for AND(random, random) ≈ 0.25
        assert 0.20 <= out.P1 <= 0.30, f"AND P1={out.P1}, expected ≈0.25"
        assert 0.70 <= out.P0 <= 0.80, f"AND P0={out.P0}, expected ≈0.75"

    def test_simple_or_gate(self):
        """OR gate with 2 random inputs: P1 ≈ 0.75."""
        circuit = Circuit()
        a = Node("a", "PI"); a.role = "PI"; a.level = 0
        b = Node("b", "PI"); b.role = "PI"; b.level = 0
        out = Node("out", "OR"); out.level = 1
        out.fanins = [a, b]
        a.fanouts = [out]
        b.fanouts = [out]
        out.role = "PO"
        circuit.nodes = {"a": a, "b": b, "out": out}
        circuit.PIs = [a, b]
        circuit.POs = [out]

        estimate_signal_probabilities(circuit, num_patterns=10000, seed=42)

        assert 0.70 <= out.P1 <= 0.80, f"OR P1={out.P1}, expected ≈0.75"

    def test_fig4_probabilities(self):
        """Signal probabilities for Fig. 4 circuit should be reasonable."""
        path = os.path.join(EXAMPLES_DIR, "fig4.txt")
        circuit = parse_netlist(path)
        levelize(circuit)

        estimate_signal_probabilities(circuit, num_patterns=5000, seed=42)

        # All P0 + P1 should sum to ≈1.0
        for node in circuit.nodes.values():
            total = node.P0 + node.P1
            assert 0.99 <= total <= 1.01, f"{node.name}: P0+P1={total}"


class TestDetectionProbabilities:
    def test_simple_detectable_fault(self):
        """SA0 on the output of a single AND gate should be detectable."""
        circuit = Circuit()
        a = Node("a", "PI"); a.role = "PI"; a.level = 0
        b = Node("b", "PI"); b.role = "PI"; b.level = 0
        out = Node("out", "AND"); out.level = 1
        out.fanins = [a, b]
        a.fanouts = [out]
        b.fanouts = [out]
        out.role = "PO"
        circuit.nodes = {"a": a, "b": b, "out": out}
        circuit.PIs = [a, b]
        circuit.POs = [out]

        estimate_detection_probabilities(circuit, num_patterns=5000, seed=42)

        # SA0 on AND output: detectable when both inputs = 1 (P ≈ 0.25)
        assert out.Pdet_sa0 > 0.15, f"AND SA0 Pdet={out.Pdet_sa0}, expected >0.15"
        # SA1 on AND output: detectable when any input = 0 (P ≈ 0.75)
        assert out.Pdet_sa1 > 0.50, f"AND SA1 Pdet={out.Pdet_sa1}, expected >0.50"
