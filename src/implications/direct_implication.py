"""
Direct implication learning using FAN-style forward/backward propagation.

Reference: Paper §3.2.1, Algorithm 1 line 10.
  "Direct implications are identified by assigning a value at a gate and
   iteratively performing backward justification and forward propagation
   until every unjustified gate is either justified, or there exist more
   than one possible justification for it."

Uses FAN [24] (Fujiwara & Shimono) style constant propagation:
  Forward: compute gate outputs from known inputs
  Backward: if output is controlling value → force inputs to non-controlling
             if gate is NOT/BUF → input is determined
"""

from collections import deque
from src.core.netlist_graph import Implication, reset_values
from src.core.gate_lib import get_controlling_value, get_non_controlling_value, is_inverting


def _invert(v):
    """Invert a binary value string."""
    return '1' if v == '0' else '0'


def _forward_eval(node, assigned):
    """
    Try to determine the output of `node` from its assigned fanin values.
    Returns the output value ('0'/'1') or None if indeterminate.
    """
    vals = [assigned.get(inp.name) for inp in node.fanins]

    gt = node.type

    if gt == "AND":
        if '0' in vals:
            return '0'
        if all(v == '1' for v in vals):
            return '1'
        return None

    elif gt == "OR":
        if '1' in vals:
            return '1'
        if all(v == '0' for v in vals):
            return '0'
        return None

    elif gt == "NAND":
        if '0' in vals:
            return '1'
        if all(v == '1' for v in vals):
            return '0'
        return None

    elif gt == "NOR":
        if '1' in vals:
            return '0'
        if all(v == '0' for v in vals):
            return '1'
        return None

    elif gt == "NOT":
        if vals and vals[0] is not None:
            return _invert(vals[0])
        return None

    elif gt in ("BUF", "WIRE"):
        if vals and vals[0] is not None:
            return vals[0]
        return None

    elif gt == "XOR":
        if all(v is not None for v in vals):
            ones = sum(1 for v in vals if v == '1')
            return '1' if ones % 2 == 1 else '0'
        return None

    elif gt == "XNOR":
        if all(v is not None for v in vals):
            ones = sum(1 for v in vals if v == '1')
            return '0' if ones % 2 == 1 else '1'
        return None

    return None


def _backward_justify(node, assigned):
    """
    Given that node's output is assigned, try to determine input values.

    Backward justification rules:
      AND out=1  → all inputs = 1
      OR  out=0  → all inputs = 0
      NAND out=0 → all inputs = 1
      NOR out=1  → all inputs = 0
      NOT        → input = inverted output
      BUF/WIRE   → input = output

    For controlling output (AND out=0, OR out=1), we cannot uniquely
    determine inputs → return empty (no new assignments).

    Returns: dict of {input_name: value} for newly determined inputs.
    """
    out_val = assigned.get(node.name)
    if out_val is None:
        return {}

    gt = node.type
    new_assignments = {}

    if gt == "AND":
        if out_val == '1':
            # All inputs must be 1
            for inp in node.fanins:
                if assigned.get(inp.name) is None:
                    new_assignments[inp.name] = '1'

    elif gt == "OR":
        if out_val == '0':
            # All inputs must be 0
            for inp in node.fanins:
                if assigned.get(inp.name) is None:
                    new_assignments[inp.name] = '0'

    elif gt == "NAND":
        if out_val == '0':
            # All inputs must be 1
            for inp in node.fanins:
                if assigned.get(inp.name) is None:
                    new_assignments[inp.name] = '1'

    elif gt == "NOR":
        if out_val == '1':
            # All inputs must be 0
            for inp in node.fanins:
                if assigned.get(inp.name) is None:
                    new_assignments[inp.name] = '0'

    elif gt == "NOT":
        if node.fanins:
            inp = node.fanins[0]
            if assigned.get(inp.name) is None:
                new_assignments[inp.name] = _invert(out_val)

    elif gt in ("BUF", "WIRE"):
        if node.fanins:
            inp = node.fanins[0]
            if assigned.get(inp.name) is None:
                new_assignments[inp.name] = out_val

    return new_assignments


def _propagate(circuit, assigned):
    """
    Iteratively apply forward propagation and backward justification
    until no new values can be determined.

    Returns the final assigned dict (name -> '0'/'1').
    """
    changed = True
    while changed:
        changed = False

        # Forward pass: for gates whose output is not yet assigned,
        # try to compute it from known inputs
        for node in circuit.nodes.values():
            if node.name in assigned:
                continue
            if node.role in ("PI", "CONST"):
                continue
            if not node.fanins:
                continue
            result = _forward_eval(node, assigned)
            if result is not None:
                assigned[node.name] = result
                changed = True

        # Backward pass: for gates whose output is assigned,
        # try to determine unknown inputs
        for node in circuit.nodes.values():
            if node.name not in assigned:
                continue
            if node.role in ("PI", "CONST"):
                continue
            new_vals = _backward_justify(node, assigned)
            for inp_name, val in new_vals.items():
                if inp_name not in assigned:
                    assigned[inp_name] = val
                    changed = True

    return assigned


def learn_direct_implications(circuit, sources, targets):
    """
    Learn direct implications between source and target gates using
    FAN-style forward/backward constant propagation.

    Args:
        circuit: Circuit object (values will be reset after)
        sources: list of (node, value) from candidate_selection
        targets: list of target nodes from candidate_selection

    Returns:
        list of Implication objects
    """
    target_names = {t.name for t in targets}
    implications = []

    for source_node, u in sources:
        # Start with just the source assignment
        assigned = {}

        # Include constant nodes
        for node in circuit.nodes.values():
            if node.role == "CONST":
                assigned[node.name] = node.value

        # Assign source value
        assigned[source_node.name] = u

        # Propagate
        assigned = _propagate(circuit, assigned)

        # Check which targets have been forced
        for target_node in targets:
            if target_node.name == source_node.name:
                continue  # Skip self-implications
            if target_node.name in assigned:
                v = assigned[target_node.name]
                impl = Implication(source_node, u, target_node, v)
                implications.append(impl)

    return implications
