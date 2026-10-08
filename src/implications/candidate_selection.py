"""
Candidate selection for source and target gates.

Reference: Paper §3.2, Algorithm 1 lines 8-9.
  - Source gates S: gates with P0 >= Th1 OR P1 >= Th1
  - Target gates T: gates with max(Pdet_sa0, Pdet_sa1) >= Th2
"""


def select_sources(circuit, Th1=0.3, limit=100):
    """
    Select source gate candidates: gates whose P0 or P1 >= Th1.
    Primary inputs are explicitly included so that internal gates with high P0/P1
    do not crowd them out.
    """
    pi_sources = []
    other_sources = []

    for pi in circuit.PIs:
        if pi.P0 >= Th1:
            pi_sources.append((pi, '0', pi.P0))
        if pi.P1 >= Th1:
            pi_sources.append((pi, '1', pi.P1))

    for node in circuit.nodes.values():
        if node.role in ("CONST", "PO", "PI"):
            continue
        if node.P0 >= Th1:
            other_sources.append((node, '0', node.P0))
        if node.P1 >= Th1:
            other_sources.append((node, '1', node.P1))

    other_sources.sort(key=lambda x: x[2], reverse=True)

    if limit is not None:
        remaining_slots = max(0, limit - len(pi_sources))
        combined = pi_sources + other_sources[:remaining_slots]
    else:
        combined = pi_sources + other_sources

    return [(n, v) for n, v, p in combined]


def select_targets(circuit, Th2=0.4, limit=50):
    """
    Select target gate candidates: gates with detection probability >= Th2.
    Sorts by highest detection probability and limits to top `limit`.
    """
    targets = []
    for node in circuit.nodes.values():
        if node.role in ("PI", "CONST") or node.type in ("PI", "WIRE"):
            continue
        max_pdet = max(node.Pdet_sa0, node.Pdet_sa1)
        if max_pdet >= Th2:
            targets.append((node, max_pdet))
            
    targets.sort(key=lambda x: x[1], reverse=True)
    return [n for n, p in targets[:limit]]
