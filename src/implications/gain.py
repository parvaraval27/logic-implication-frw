"""
Gain computation for implication FRW addition.

Reference: Paper §3.2.4, Equations 1-3.

Eq. 1: G'_isa = G_isa × (1 - P_u) × PRP
Eq. 2: PRP = #paths(G_i → T) / #paths(G_i → PO)
Eq. 3: Gain = Σ(G_isa_old - G_isa_new) for all gates in PathG
"""

from src.core.netlist_graph import count_paths, count_paths_to_any_po


def compute_PRP(circuit, gate, target):
    """
    Compute the Path Ratio Percentage (PRP) for a gate relative to a target.

    PRP = #paths(gate → target) / #paths(gate → any PO)

    Paper Eq. 2: Used to estimate the fraction of fault propagation
    paths that go through the target gate.
    """
    paths_to_target = count_paths(gate, target)
    paths_to_po = count_paths_to_any_po(circuit, gate)

    if paths_to_po == 0:
        return 0.0
    return paths_to_target / paths_to_po


def update_detection_prob(old_prob, P_u, PRP):
    """
    Compute the updated detection probability after adding an FRW.

    Paper Eq. 1: G'_isa = G_isa × (1 - P_u) × PRP

    The new detection probability accounts for the fact that when the
    source has value u (probability P_u), faults along the implication
    path are masked, but only for the fraction of paths going through T (PRP).

    Args:
        old_prob: current detection probability (G_isa)
        P_u: probability that source has value u
        PRP: path ratio percentage

    Returns:
        new detection probability (G'_isa)
    """
    reduction = old_prob * P_u * PRP
    return old_prob - reduction


def compute_gain(circuit, path_gates, target, source, u, markings):
    """
    Compute the total gain for an implication S(=u) => T(=v).

    Paper Eq. 3: Gain = Σ(G_isa_old - G_isa_new) for all gates in PathG.

    For each gate in PathG:
      - If the gate's marking value is '0', sa1 detection probability is reduced
      - If the gate's marking value is '1', sa0 detection probability is reduced

    Args:
        circuit: Circuit object
        path_gates: list of Nodes in PathG
        target: target Node
        source: source Node
        u: source value ('0' or '1')
        markings: dict from VP algorithm

    Returns:
        float: the total gain
    """
    # P_u: probability that source has value u
    if u == '0':
        P_u = source.P0
    else:
        P_u = source.P1

    total_gain = 0.0

    for gate in path_gates:
        marking = markings.get(gate.name)
        if marking is None:
            continue

        # Determine which fault type is impacted
        gate_val = marking[-1]  # '0' or '1'

        # PRP for this gate
        prp = compute_PRP(circuit, gate, target)

        if gate_val == '0':
            # Gate value is 0 along implication path → sa1 detection reduced
            old_prob = gate.Pdet_sa1
            new_prob = update_detection_prob(old_prob, P_u, prp)
            total_gain += (old_prob - new_prob)
        else:
            # Gate value is 1 along implication path → sa0 detection reduced
            old_prob = gate.Pdet_sa0
            new_prob = update_detection_prob(old_prob, P_u, prp)
            total_gain += (old_prob - new_prob)

    return total_gain


def compute_gain_simple(path_gates, old_probs, new_probs):
    """
    Simplified gain computation when probabilities are provided directly.
    Used for testing against paper's exact numbers.

    Eq. 3: Gain = Σ(old_i - new_i)
    """
    return sum(old - new for old, new in zip(old_probs, new_probs))
