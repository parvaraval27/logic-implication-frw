"""
Random-pattern fault simulator.

Replaces HOPE [23] from the paper - serial random-pattern simulation
using the 5-valued D/D̄ engine to estimate:
  - P0/P1 (signal probabilities) for every gate
  - Pdet_sa0/Pdet_sa1 (stuck-at fault detection probabilities) for every gate

Reference: Paper Section 3.2, Algorithm 1 line 7.
"""

import random
from src.core.netlist_graph import simulate, reset_values, Fault
from src.core.five_valued import simulate_5val, has_fault_at_po


def estimate_signal_probabilities(circuit, num_patterns=10000, seed=None):
    """
    Simulate num_patterns random input vectors and compute P0/P1
    for every gate in the circuit.

    Sets node.P0 and node.P1 for all nodes.
    """
    if seed is not None:
        random.seed(seed)

    # Tally counters
    count_1 = {name: 0 for name in circuit.nodes}

    for _ in range(num_patterns):
        # Assign random values to PIs
        for pi in circuit.PIs:
            pi.value = random.choice(['0', '1'])

        # Simulate
        simulate(circuit)

        # Tally
        for name, node in circuit.nodes.items():
            if node.value == '1':
                count_1[name] += 1

    # Compute probabilities
    for name, node in circuit.nodes.items():
        if node.role == "CONST":
            node.P1 = 1.0 if node.value == '1' else 0.0
            node.P0 = 1.0 - node.P1
        else:
            node.P1 = count_1[name] / num_patterns
            node.P0 = 1.0 - node.P1

    reset_values(circuit)


def estimate_detection_probabilities(circuit, num_patterns=10000, seed=None):
    """
    Estimate stuck-at fault detection probabilities for every gate.

    For each gate, injects SA0 and SA1 faults, simulates with random
    patterns, and checks if D/D̄ appears at any PO.

    Sets node.Pdet_sa0 and node.Pdet_sa1 for all nodes.
    """
    if seed is not None:
        random.seed(seed)

    # Pre-generate random patterns for consistency
    patterns = []
    for _ in range(num_patterns):
        vec = {pi.name: random.choice(['0', '1']) for pi in circuit.PIs}
        patterns.append(vec)

    # For each node, test SA0 and SA1
    gates = [n for n in circuit.nodes.values()
             if n.role not in ("CONST",) and n.type not in ("PI",)]

    for node in gates:
        det_sa0 = 0
        det_sa1 = 0

        fault_sa0 = Fault(node, 0)
        fault_sa1 = Fault(node, 1)

        for vec in patterns:
            # s/0
            # Assign PI values
            for pi in circuit.PIs:
                pi.value = vec[pi.name]
            # Reset internals
            for n in circuit.nodes.values():
                if n.role not in ("PI", "CONST"):
                    n.value = 'X'
            # 5-valued sim with fault
            simulate_5val(circuit, fault_sa0)
            if has_fault_at_po(circuit):
                det_sa0 += 1

            # s/1
            for pi in circuit.PIs:
                pi.value = vec[pi.name]
            for n in circuit.nodes.values():
                if n.role not in ("PI", "CONST"):
                    n.value = 'X'
            simulate_5val(circuit, fault_sa1)
            if has_fault_at_po(circuit):
                det_sa1 += 1

        node.Pdet_sa0 = det_sa0 / num_patterns
        node.Pdet_sa1 = det_sa1 / num_patterns

    # PIs get detection probabilities too
    for pi in circuit.PIs:
        det_sa0 = 0
        det_sa1 = 0
        fault_sa0 = Fault(pi, 0)
        fault_sa1 = Fault(pi, 1)

        for vec in patterns:
            for p in circuit.PIs:
                p.value = vec[p.name]
            for n in circuit.nodes.values():
                if n.role not in ("PI", "CONST"):
                    n.value = 'X'
            simulate_5val(circuit, fault_sa0)
            if has_fault_at_po(circuit):
                det_sa0 += 1

            for p in circuit.PIs:
                p.value = vec[p.name]
            for n in circuit.nodes.values():
                if n.role not in ("PI", "CONST"):
                    n.value = 'X'
            simulate_5val(circuit, fault_sa1)
            if has_fault_at_po(circuit):
                det_sa1 += 1

        pi.Pdet_sa0 = det_sa0 / num_patterns
        pi.Pdet_sa1 = det_sa1 / num_patterns

    reset_values(circuit)


def run_fault_simulation(circuit, num_patterns=10000, seed=42):
    """
    Full fault simulation: estimate both signal probabilities
    and detection probabilities.
    """
    estimate_signal_probabilities(circuit, num_patterns, seed)
    estimate_detection_probabilities(circuit, num_patterns, seed)
