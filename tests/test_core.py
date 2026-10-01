"""Tests for core module: parsing, levelization, gate evaluation, logic cones."""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.netlist_graph import (
    parse_netlist, levelize, eval_gate, simulate,
    compute_logic_cone, compute_fanout_cone, count_paths,
    count_paths_to_any_po, clone_circuit, Node,
)
from src.core.gate_lib import (
    get_controlling_value, get_non_controlling_value, get_IP,
    get_transistor_count, is_inverting,
)


EXAMPLES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples")


class TestGateLib:
    def test_controlling_values(self):
        assert get_controlling_value("AND") == "0"
        assert get_controlling_value("OR") == "1"
        assert get_controlling_value("NAND") == "0"
        assert get_controlling_value("NOR") == "1"
        assert get_controlling_value("NOT") is None

    def test_non_controlling_values(self):
        assert get_non_controlling_value("AND") == "1"
        assert get_non_controlling_value("OR") == "0"
        assert get_non_controlling_value("NAND") == "1"
        assert get_non_controlling_value("NOR") == "0"

    def test_IP_flag(self):
        assert get_IP("AND") == 0
        assert get_IP("OR") == 0
        assert get_IP("NAND") == 1
        assert get_IP("NOR") == 1
        assert get_IP("NOT") == 1
        assert get_IP("BUF") == 0

    def test_is_inverting(self):
        assert is_inverting("NOT") is True
        assert is_inverting("NAND") is True
        assert is_inverting("NOR") is True
        assert is_inverting("AND") is False
        assert is_inverting("OR") is False

    def test_transistor_count(self):
        assert get_transistor_count("NOT", 1) == 2
        assert get_transistor_count("NAND", 2) == 4
        assert get_transistor_count("NAND", 3) == 6
        assert get_transistor_count("AND", 2) == 6  # 4 + 2


class TestParsing:
    def test_parse_c17(self):
        """Test parsing the ISCAS c17 benchmark."""
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "benchmarks", "c17.txt"
        )
        if not os.path.exists(path):
            return  # Skip if sample not available
        circuit = parse_netlist(path)
        assert len(circuit.PIs) == 5
        assert len(circuit.POs) == 2
        # c17 has 6 NAND gates + PIs + POs
        gates = [n for n in circuit.nodes.values()
                 if n.type == "NAND"]
        assert len(gates) == 6

    def test_parse_fig4(self):
        """Test parsing the Fig. 4 example."""
        path = os.path.join(EXAMPLES_DIR, "fig4.txt")
        circuit = parse_netlist(path)
        assert len(circuit.PIs) == 8  # a,b,c,d,e,f,g,h
        assert len(circuit.POs) == 1  # O1
        # Gates: G1(OR), G2(OR), G3(NAND), G4(NAND), G5(OR),
        #        G6(AND), G7(AND), G8(OR), G9(AND), G10(AND)
        gate_nodes = [n for n in circuit.nodes.values()
                      if n.type not in ("PI", "WIRE") and n.role != "PI"]
        assert len(gate_nodes) == 10

    def test_parse_fig5(self):
        """Test parsing Fig. 5 (same topology as Fig. 4)."""
        path = os.path.join(EXAMPLES_DIR, "fig5.txt")
        circuit = parse_netlist(path)
        assert len(circuit.PIs) == 8
        assert len(circuit.POs) == 1


class TestLevelize:
    def test_levelize_fig4(self):
        path = os.path.join(EXAMPLES_DIR, "fig4.txt")
        circuit = parse_netlist(path)
        levelize(circuit)

        # PIs should be level 0
        for pi in circuit.PIs:
            assert pi.level == 0

        # All gates should have level > 0
        for node in circuit.nodes.values():
            if node.role not in ("PI", "CONST"):
                assert node.level > 0, f"{node.name} has level {node.level}"


class TestEvalGate:
    def test_and_gate(self):
        out = Node("out", "AND")
        a = Node("a", "PI"); a.value = '1'
        b = Node("b", "PI"); b.value = '1'
        out.fanins = [a, b]
        assert eval_gate(out) == '1'

        a.value = '0'
        assert eval_gate(out) == '0'

    def test_nand_gate(self):
        out = Node("out", "NAND")
        a = Node("a", "PI"); a.value = '1'
        b = Node("b", "PI"); b.value = '1'
        out.fanins = [a, b]
        assert eval_gate(out) == '0'

        a.value = '0'
        assert eval_gate(out) == '1'

    def test_or_gate(self):
        out = Node("out", "OR")
        a = Node("a", "PI"); a.value = '0'
        b = Node("b", "PI"); b.value = '0'
        out.fanins = [a, b]
        assert eval_gate(out) == '0'

        a.value = '1'
        assert eval_gate(out) == '1'

    def test_not_gate(self):
        out = Node("out", "NOT")
        a = Node("a", "PI"); a.value = '0'
        out.fanins = [a]
        assert eval_gate(out) == '1'

        a.value = '1'
        assert eval_gate(out) == '0'


class TestLogicCone:
    def test_fanin_cone(self):
        path = os.path.join(EXAMPLES_DIR, "fig4.txt")
        circuit = parse_netlist(path)
        levelize(circuit)

        # Logic cone of O1 should include everything
        po = circuit.POs[0]
        cone = compute_logic_cone(circuit, po)
        # All nodes should be in the cone of the PO
        assert len(cone) > 0

    def test_fanout_cone(self):
        path = os.path.join(EXAMPLES_DIR, "fig4.txt")
        circuit = parse_netlist(path)
        levelize(circuit)

        # Fanout cone of a PI should eventually reach POs
        pi = circuit.PIs[0]
        cone = compute_fanout_cone(circuit, pi)
        assert any(po in cone for po in circuit.POs)


class TestCloneCircuit:
    def test_clone_preserves_structure(self):
        path = os.path.join(EXAMPLES_DIR, "fig4.txt")
        circuit = parse_netlist(path)
        levelize(circuit)

        cloned = clone_circuit(circuit)

        assert len(cloned.nodes) == len(circuit.nodes)
        assert len(cloned.PIs) == len(circuit.PIs)
        assert len(cloned.POs) == len(circuit.POs)

        # Nodes should be different objects
        for name in circuit.nodes:
            assert cloned.nodes[name] is not circuit.nodes[name]
            assert cloned.nodes[name].type == circuit.nodes[name].type
            assert len(cloned.nodes[name].fanins) == len(circuit.nodes[name].fanins)
