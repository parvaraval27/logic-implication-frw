"""
Tests for FRW Addition (Algorithms 2 & 3).

Functional-equivalence regression: after adding an FRW, simulate
random vectors pre/post mutation and verify POs match.
"""

import os
import sys
import random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.netlist_graph import (
    parse_netlist, levelize, simulate, clone_circuit, Implication,
)
from src.implications.frw_addition import add_frw


EXAMPLES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples")


def _simulate_and_collect(circuit, patterns):
    """Simulate all patterns and collect PO values."""
    results = []
    for vec in patterns:
        for pi in circuit.PIs:
            pi.value = vec[pi.name]
        simulate(circuit)
        po_vals = {po.name: po.value for po in circuit.POs}
        results.append(po_vals)
    return results


class TestFRWFunctionalEquivalence:
    """
    After adding a FRW, the circuit must remain functionally equivalent.
    We test this by simulating random patterns before and after the mutation.
    """

    def test_frw_v0_and_masking(self):
        """
        Fig. 4: G4(=0) => G3(=0), masking gate O1 is AND.
        Paper says: add FRW to masking gate (AND gets extra input G4).
        """
        path = os.path.join(EXAMPLES_DIR, "fig4.txt")
        original = parse_netlist(path)
        levelize(original)

        modified = clone_circuit(original)
        levelize(modified)

        # Create implication
        impl = Implication(
            modified.nodes["G4"], '0',
            modified.nodes["G3"], '0'
        )

        # Add FRW
        result = add_frw(modified, impl)
        levelize(modified)

        assert result['action'] is not None, "FRW addition should produce an action"

        # Generate random test patterns
        random.seed(42)
        patterns = []
        for _ in range(5000):
            vec = {pi.name: random.choice(['0', '1']) for pi in original.PIs}
            patterns.append(vec)

        # Simulate both
        orig_results = _simulate_and_collect(original, patterns)
        mod_results = _simulate_and_collect(modified, patterns)

        # Compare
        mismatches = 0
        for i, (orig, mod) in enumerate(zip(orig_results, mod_results)):
            if orig != mod:
                mismatches += 1

        assert mismatches == 0, (
            f"{mismatches}/{len(patterns)} patterns produced different outputs "
            f"after FRW addition"
        )


class TestFRWGateTypeChanges:
    """Test specific gate type transformation rules."""

    def test_not_to_nand(self):
        """Algorithm 2: NOT target → NAND(Ti, S⊕u) when v=1."""
        from src.core.netlist_graph import Node, Circuit
        circuit = Circuit()

        a = Node("a", "PI"); a.role = "PI"; a.level = 0
        b = Node("b", "PI"); b.role = "PI"; b.level = 0
        inv = Node("inv", "NOT"); inv.level = 1
        inv.fanins = [a]; a.fanouts = [inv]
        out = Node("out", "AND"); out.level = 2; out.role = "PO"
        out.fanins = [inv, b]; inv.fanouts = [out]; b.fanouts = [out]

        circuit.nodes = {"a": a, "b": b, "inv": inv, "out": out}
        circuit.PIs = [a, b]
        circuit.POs = [out]

        # Implication: b(=1) => inv(=1) [when a=0, inv=1, so b=1 is consistent]
        impl = Implication(b, '1', inv, '1')
        result = add_frw(circuit, impl)

        # Target has AND masking gate and v=1 → should add to target
        # NOT should become NAND
        assert inv.type == "NAND", f"Expected NAND, got {inv.type}"
