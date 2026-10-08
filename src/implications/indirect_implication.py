"""
Indirect implication learning via bounded recursive learning.

Reference: Paper §3.2.1, references [25-27] (Kunz & Pradhan recursive learning).

Algorithm:
  For each source assignment S=u, direct propagation is applied first.
  For unresolved gates at the frontier, case-splitting is used:
    Try G=0, propagate → values_0
    Try G=1, propagate → values_1
    If both branches force the same value at a target → indirect implication.
  This recurses up to max_depth levels with bounded breadth.

This module provides a bounded-depth recursive learning approach.
"""

from src.core.netlist_graph import Implication, compute_logic_cone
from src.implications.direct_implication import _propagate


def learn_indirect_implications(circuit, sources, targets, max_depth=2):
    """
    Learn indirect implications between source and target gates using
    bounded recursive learning (Kunz-Pradhan style).

    For each source assignment, if direct propagation doesn't reach
    a target, try case-splitting on unresolved gates.

    Args:
        circuit: Circuit object
        sources: list of (node, value) from candidate_selection
        targets: list of target nodes
        max_depth: maximum recursion depth for case splitting

    Returns:
        list of Implication objects (only new ones not found by direct)
    """
    target_names = {t.name for t in targets}
    implications = []

    for source_node, u in sources:
        # Start with source assignment
        base_assigned = {}
        for node in circuit.nodes.values():
            if node.role == "CONST":
                base_assigned[node.name] = node.value
        base_assigned[source_node.name] = u
        base_assigned = _propagate(circuit, dict(base_assigned))

        # Find targets already discovered by direct propagation
        direct_targets = {t.name for t in targets if t.name in base_assigned}
        unresolved_targets = [t for t in targets if t.name not in direct_targets]
        if not unresolved_targets:
            continue

        relevant_cones = set()
        for t in unresolved_targets:
            relevant_cones.update(compute_logic_cone(circuit, t))

        candidates = []
        for node in circuit.nodes.values():
            if node in relevant_cones and node.name not in base_assigned and node.role not in ("PI", "CONST"):
                if node.type not in ("PI", "WIRE"):
                    candidates.append(node)

        # Sort by topological level (lower first) — gates closer to
        # inputs are more likely to force values across the circuit.
        candidates.sort(key=lambda n: getattr(n, 'level', 0))

        # Recursive learning: case-split on candidate gates
        found = _recursive_learn(circuit, base_assigned, candidates,
                                 targets, set(direct_targets), max_depth)

        for target_node, v in found:
            if target_node.name != source_node.name:
                impl = Implication(source_node, u, target_node, v)
                implications.append(impl)

    return implications


def _recursive_learn(circuit, base_assigned, candidates, targets,
                     already_found, depth, max_breadth=15):
    """
    Recursive case-splitting on candidate gates (Kunz-Pradhan style).

    For each candidate gate G:
      1. Try G=0, propagate → assigned_0
      2. Try G=1, propagate → assigned_1
      3. For each target T:
         a. If both branches force T to the same value → indirect implication
         b. If one branch doesn't resolve T and depth>1 → recurse deeper
         c. If deeper recursion resolves both branches to same value → indirect impl

    Args:
        circuit: Circuit object
        base_assigned: dict of currently known signal assignments
        candidates: list of unresolved gate nodes to try case-splitting on
        targets: list of target nodes to check
        already_found: set of target names already discovered
        depth: remaining recursion depth
        max_breadth: max number of candidates to try at this level

    Returns:
        list of (target_node, value) pairs for discovered indirect implications
    """
    if depth <= 0 or not candidates:
        return []

    found = []

    for gate in candidates[:max_breadth]:
        # Skip if this gate got assigned during a previous iteration
        if gate.name in base_assigned:
            continue

        # Branch 0: assign gate=0 and propagate
        assigned_0 = dict(base_assigned)
        assigned_0[gate.name] = '0'
        assigned_0 = _propagate(circuit, assigned_0)

        # Branch 1: assign gate=1 and propagate
        assigned_1 = dict(base_assigned)
        assigned_1[gate.name] = '1'
        assigned_1 = _propagate(circuit, assigned_1)

        for target in targets:
            if target.name in already_found:
                continue

            v0 = assigned_0.get(target.name)
            v1 = assigned_1.get(target.name)

            # Case 1: Both branches directly force target to the same value
            if v0 is not None and v1 is not None and v0 == v1:
                found.append((target, v0))
                already_found.add(target.name)
                continue

            # Case 2: Need deeper recursion to resolve one or both branches
            if depth > 1:
                deeper_v0 = v0  # Already known from branch 0, or None
                deeper_v1 = v1  # Already known from branch 1, or None

                # Build sub-candidates: gates not assigned in either branch,
                # excluding the gate we just split on
                sub_candidates = [
                    n for n in candidates
                    if n is not gate
                    and n.name not in assigned_0
                    and n.name not in assigned_1
                ]

                # If branch 0 didn't resolve the target, recurse into it
                if deeper_v0 is None and sub_candidates:
                    sub_found_0 = _recursive_learn(
                        circuit, assigned_0, sub_candidates,
                        [target], set(already_found),
                        depth - 1, max(max_breadth // 2, 5)
                    )
                    for t, v in sub_found_0:
                        if t.name == target.name:
                            deeper_v0 = v
                            break

                # If branch 1 didn't resolve the target, recurse into it
                if deeper_v1 is None and sub_candidates:
                    sub_found_1 = _recursive_learn(
                        circuit, assigned_1, sub_candidates,
                        [target], set(already_found),
                        depth - 1, max(max_breadth // 2, 5)
                    )
                    for t, v in sub_found_1:
                        if t.name == target.name:
                            deeper_v1 = v
                            break

                # Intersection: if both branches agree after recursion
                if (deeper_v0 is not None and deeper_v1 is not None
                        and deeper_v0 == deeper_v1):
                    found.append((target, deeper_v0))
                    already_found.add(target.name)

    return found
