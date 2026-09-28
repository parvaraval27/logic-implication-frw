"""
Area computation using transistor-count proxy.

The paper uses PTM 130nm drain widths for area, but since STR/sizing
is out of scope, we use a simpler transistor-count proxy.

Reference: Paper §5, Table 1 "Area" column.
"""

from src.core.gate_lib import get_transistor_count, get_gate_area_ptm130


def compute_area(circuit):
    """
    Compute total area of a circuit as a transistor count.

    Sums the transistor count for each gate based on its type
    and number of inputs.
    """
    total = 0
    for node in circuit.nodes.values():
        if node.role in ("PI", "CONST"):
            continue
        if node.type in ("PI", "WIRE"):
            continue
        total += get_gate_area_ptm130(node.type, len(node.fanins))
    return total


def compute_transistor_count(circuit):
    """
    Compute total number of CMOS transistors in the circuit.
    """
    total = 0
    for node in circuit.nodes.values():
        if node.role in ("PI", "CONST"):
            continue
        if node.type in ("PI", "WIRE"):
            continue
        total += get_transistor_count(node.type, len(node.fanins))
    return total


def compute_area_overhead(original_area, new_area):
    """
    Compute area overhead percentage.

    OH = ((new_area / original_area) - 1) × 100
    """
    if original_area == 0:
        return 0.0
    return ((new_area / original_area) - 1.0) * 100.0
