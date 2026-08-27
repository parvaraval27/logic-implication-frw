"""
Reference: Paper Section 3.2, Algorithm 1 lines 8-9.
  - Source gates S: gates with P0 >= Th1 OR P1 >= Th1
  - Target gates T: gates with max(Pdet_sa0, Pdet_sa1) >= Th2
"""


def select_sources(circuit, Th1=0.3):
    sources = []
    for node in circuit.nodes.values():
        if node.role == "CONST":
            continue
        if node.P0 >= Th1:
            sources.append((node, '0'))
        if node.P1 >= Th1:
            sources.append((node, '1'))
    return sources


def select_targets(circuit, Th2=0.4):
    targets = []
    for node in circuit.nodes.values():
        if node.role in ("PI", "CONST"):
            continue
        if node.type in ("PI", "WIRE"):
            continue
        max_pdet = max(node.Pdet_sa0, node.Pdet_sa1)
        if max_pdet >= Th2:
            targets.append(node)
    return targets
