"""
Random-pattern fault simulator.

High-performance 64-bit Bit-Parallel Single Fault Propagation (PPSFP) engine
to estimate:
  - P0/P1 (signal probabilities) for every gate
  - Pdet_sa0/Pdet_sa1 (stuck-at fault detection probabilities) for every gate

Reference: Paper §3.2, Algorithm 1 line 7.
"""

import random
from src.core.netlist_graph import reset_values, compute_fanout_cone


MASK64 = (1 << 64) - 1


def _eval_gate_bp(gate_type, in_vals, mask):
    gt = gate_type.upper()
    if gt == "AND":
        res = in_vals[0]
        for v in in_vals[1:]:
            res &= v
        return res
    elif gt == "OR":
        res = in_vals[0]
        for v in in_vals[1:]:
            res |= v
        return res
    elif gt in ("NOT", "INV"):
        return (~in_vals[0]) & mask
    elif gt == "NAND":
        res = in_vals[0]
        for v in in_vals[1:]:
            res &= v
        return (~res) & mask
    elif gt == "NOR":
        res = in_vals[0]
        for v in in_vals[1:]:
            res |= v
        return (~res) & mask
    elif gt == "XOR":
        res = in_vals[0]
        for v in in_vals[1:]:
            res ^= v
        return res
    elif gt == "XNOR":
        res = in_vals[0]
        for v in in_vals[1:]:
            res ^= v
        return (~res) & mask
    elif gt in ("BUF", "WIRE"):
        return in_vals[0] if in_vals else 0
    return 0


def estimate_signal_probabilities(circuit, num_patterns=10000, seed=None):
    """
    Simulate num_patterns random input vectors using 64-bit words
    and compute P0/P1 for every gate in the circuit.

    Sets node.P0 and node.P1 for all nodes.
    """
    if seed is not None:
        random.seed(seed)

    num_words = max(1, (num_patterns + 63) // 64)
    total_patterns = num_words * 64

    nodes_sorted = sorted(circuit.nodes.values(), key=lambda n: n.level if n.level >= 0 else 999999)
    count_1 = {name: 0 for name in circuit.nodes}

    for _ in range(num_words):
        good = {}
        for node in circuit.nodes.values():
            if node.role == "CONST":
                good[node.name] = MASK64 if node.value == '1' else 0

        for pi in circuit.PIs:
            good[pi.name] = random.getrandbits(64)

        for n in nodes_sorted:
            if n.role in ("PI", "CONST") or n.level == -1:
                continue
            good[n.name] = _eval_gate_bp(n.type, [good[inp.name] for inp in n.fanins], MASK64)

        for name in circuit.nodes:
            count_1[name] += good.get(name, 0).bit_count()

    for name, node in circuit.nodes.items():
        if node.role == "CONST":
            node.P1 = 1.0 if node.value == '1' else 0.0
            node.P0 = 1.0 - node.P1
        else:
            node.P1 = count_1[name] / total_patterns
            node.P0 = 1.0 - node.P1

    reset_values(circuit)


def estimate_detection_probabilities(circuit, num_patterns=10000, seed=None):
    """
    Estimate stuck-at fault detection probabilities for every gate using PPSFP.

    Injects SA0 and SA1 faults, propagates dynamically through fanout cones
    in 64-bit parallel words, and tallies bitwise PO discrepancies.

    Sets node.Pdet_sa0 and node.Pdet_sa1 for all nodes.
    """
    if seed is not None:
        random.seed(seed)

    num_words = max(1, (num_patterns + 63) // 64)
    total_patterns = num_words * 64

    nodes_sorted = sorted(circuit.nodes.values(), key=lambda n: n.level if n.level >= 0 else 999999)
    gates = [n for n in circuit.nodes.values() if n.role != "CONST"]

    # Precompute fanout cones and topological ordering for each target
    target_info = {}
    for target in gates:
        cone = compute_fanout_cone(circuit, target)
        pos_in_cone = [po for po in circuit.POs if po in cone]
        fout_gates = sorted([n for n in cone if n is not target], key=lambda n: n.level)
        target_info[target.name] = (target, fout_gates, pos_in_cone)

    det_sa0 = {n.name: 0 for n in gates}
    det_sa1 = {n.name: 0 for n in gates}

    for _ in range(num_words):
        good = {}
        for node in circuit.nodes.values():
            if node.role == "CONST":
                good[node.name] = MASK64 if node.value == '1' else 0

        for pi in circuit.PIs:
            good[pi.name] = random.getrandbits(64)

        for n in nodes_sorted:
            if n.role in ("PI", "CONST") or n.level == -1:
                continue
            good[n.name] = _eval_gate_bp(n.type, [good.get(inp.name, 0) for inp in n.fanins], MASK64)

        for target in gates:
            tgt, fout, pos = target_info[target.name]
            if not pos:
                continue

            # SA0
            act0 = good.get(target.name, 0)
            if act0:
                f0 = {target.name: 0}
                for n in fout:
                    f0[n.name] = _eval_gate_bp(n.type, [f0.get(inp.name, good.get(inp.name, 0)) for inp in n.fanins], MASK64)
                diff0 = 0
                for po in pos:
                    diff0 |= (good.get(po.name, 0) ^ f0.get(po.name, 0))
                det_sa0[target.name] += (diff0 & act0).bit_count()

            # SA1
            act1 = (~good.get(target.name, 0)) & MASK64
            if act1:
                f1 = {target.name: MASK64}
                for n in fout:
                    f1[n.name] = _eval_gate_bp(n.type, [f1.get(inp.name, good.get(inp.name, 0)) for inp in n.fanins], MASK64)
                diff1 = 0
                for po in pos:
                    diff1 |= (good.get(po.name, 0) ^ f1.get(po.name, 0))
                det_sa1[target.name] += (diff1 & act1).bit_count()

    for node in gates:
        node.Pdet_sa0 = det_sa0[node.name] / total_patterns
        node.Pdet_sa1 = det_sa1[node.name] / total_patterns

    reset_values(circuit)


def run_fault_simulation(circuit, num_patterns=10000, seed=42):
    """
    Full fault simulation: estimate both signal probabilities
    and detection probabilities.
    """
    estimate_signal_probabilities(circuit, num_patterns, seed)
    estimate_detection_probabilities(circuit, num_patterns, seed)

