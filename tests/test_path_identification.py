"""
Tests for Implication Path Identification (Algorithm 5).

Validates PathG against paper's Fig. 4 and Fig. 5 examples.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.netlist_graph import parse_netlist, levelize
from src.implications.value_propagation import mark_gates_vp
from src.implications.path_identification import identify_path


EXAMPLES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples")


class TestIPIFig4:
    """
    Fig. 4: Implication G4(=0) => G3(=0), masking gate G10.

    Paper (§4, page 41):
    PathG = {G6, G8, G1, G2, G3}
    (i.e., G6 → G8 → (G1, G2) → G3)
    """

    def setup_method(self):
        path = os.path.join(EXAMPLES_DIR, "fig4.txt")
        self.circuit = parse_netlist(path)
        levelize(self.circuit)
        self.source = self.circuit.nodes["G4"]
        self.target = self.circuit.nodes["G3"]

    def test_path_gates(self):
        markings = mark_gates_vp(self.circuit, self.source, '0', self.target)
        path_gates = identify_path(self.circuit, self.source, self.target, markings)

        path_names = {g.name for g in path_gates}

        # Paper says PathG should include G3 and G8 at minimum
        # Full expected: {G6, G8, G1, G2, G3}
        assert "G3" in path_names, f"G3 missing from PathG: {path_names}"
        assert "G8" in path_names, f"G8 missing from PathG: {path_names}"

        # G6 should be in the path (feeds into G8)
        # G1 and G2 should be in the path (between G8 and G3)
        assert len(path_gates) >= 3, f"PathG too short: {path_names}"


class TestIPIFig5:
    """
    Fig. 5: Implication h(=0) => G3(=0), masking gate G10.

    Paper (§4, page 41):
    PathG = {G5, G7, G8, G1, G2, G3}
    """

    def setup_method(self):
        path = os.path.join(EXAMPLES_DIR, "fig5.txt")
        self.circuit = parse_netlist(path)
        levelize(self.circuit)
        self.source = self.circuit.nodes["h"]
        self.target = self.circuit.nodes["G3"]

    def test_path_gates(self):
        markings = mark_gates_vp(self.circuit, self.source, '0', self.target)
        path_gates = identify_path(self.circuit, self.source, self.target, markings)

        path_names = {g.name for g in path_gates}

        # G3 must be in path
        assert "G3" in path_names, f"G3 missing from PathG: {path_names}"

        # Should have several gates in the path
        assert len(path_gates) >= 2, f"PathG too short: {path_names}"
