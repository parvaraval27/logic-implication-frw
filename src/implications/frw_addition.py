"""
FRW Addition Rules — Algorithms 2 and 3 from the paper.

Mutates the netlist by adding a Functionally Redundant Wire (FRW)
based on a selected implication S(=u) => T(=v).

Algorithm 2: Rules for v=1 (target forced to 1)
Algorithm 3: Rules for v=0 (target forced to 0)

The FRW is added either to the target gate or its masking gate,
depending on the gate types and fanout conditions.

Reference: Paper §3.2.2, Algorithms 2 and 3.
"""

from src.core.netlist_graph import Node, get_or_create_node


def _needs_inverter(source_value):
    """
    Determine if the FRW connection needs an inverter.
    S ⊕ u: when u='1', the source itself is used (inverted via ⊕).
    When u='0', the source is used directly.

    Actually: S⊕u means XOR with u.
    If u=0: S⊕0 = S (no inversion)
    If u=1: S⊕1 = S̄ (inversion needed)
    """
    return source_value == '1'


def _get_masking_gate(target):
    """
    Get the masking gate for a target. The masking gate is a gate
    that is driven by the target gate.
    Returns the masking gate or None if target is a PO with no gate fanout.
    """
    for fout in target.fanouts:
        if fout.type not in ("PI", "WIRE") or fout.role == "PO":
            return fout
    # If target drives a PO wire
    if target.fanouts:
        return target.fanouts[0]
    return None


def _add_inverter(circuit, source, inv_name=None):
    """
    Add an inverter node for the source signal.
    If an inverter for this source already exists in the circuit, reuse it.
    Returns the inverter node.
    """
    if inv_name is None:
        inv_name = f"INV_{source.name}"

    if inv_name in circuit.nodes:
        return circuit.nodes[inv_name]

    inv_node = Node(inv_name, "NOT")
    inv_node.role = "INTERNAL"
    inv_node.level = source.level + 1 if source.level >= 0 else -1
    inv_node.fanins = [source]
    inv_node.fanouts = []
    circuit.nodes[inv_name] = inv_node

    source.fanouts.append(inv_node)

    return inv_node


def _get_frw_signal(circuit, source, u):
    """
    Get the FRW signal node: source itself or an inverted copy.
    S⊕u: if u=0, use source directly; if u=1, add inverter.
    """
    if _needs_inverter(u):
        return _add_inverter(circuit, source)
    return source


def _add_input_to_gate(gate, new_input):
    """Add a new input to a gate and update fanout links."""
    if new_input not in gate.fanins:
        gate.fanins.append(new_input)
    if gate not in new_input.fanouts:
        new_input.fanouts.append(gate)


def _change_gate_type(gate, new_type):
    """Change a gate's type (e.g., NOT -> NAND)."""
    gate.type = new_type


def add_frw(circuit, implication):
    """
    Add a Functionally Redundant Wire to the circuit based on an implication.

    Implements Algorithm 2 (v=1) and Algorithm 3 (v=0).

    Args:
        circuit: Circuit object (will be modified in-place)
        implication: Implication object with source, u, target, v

    Returns:
        dict with details of the modification made
    """
    source = implication.source
    u = implication.u
    target = implication.target
    v = implication.v

    # Find masking gate
    masking = _get_masking_gate(target)

    # Number of fanouts of target
    fo_t = len(target.fanouts)

    result = {
        'source': source.name,
        'target': target.name,
        'masking': masking.name if masking else None,
        'action': None,
    }

    if v == '1':
        return _add_frw_v1(circuit, source, u, target, masking, fo_t, result)
    else:
        return _add_frw_v0(circuit, source, u, target, masking, fo_t, result)


def _add_frw_v1(circuit, source, u, target, masking, fo_t, result):
    """
    Algorithm 2: FRW Addition Rule for S(=u) => T(=1).

    When target is forced to 1:
    - Masking gate should have T=1 at its input
    - For AND/NAND masking: T=1 is non-controlling → can't add there
    - For OR/NOR/NOT masking: T=1 can be used
    """
    frw_signal = _get_frw_signal(circuit, source, u)

    # Line 7: Check if FRW should go to target instead of masking
    add_to_target = False
    if masking is None:
        add_to_target = True
    elif masking.type in ("AND", "NAND"):
        add_to_target = True
    elif fo_t > 1:
        add_to_target = True

    if add_to_target:
        # Lines 8-14: Add FRW to target gate
        if target.type == "NOT":
            # T = NOT → T becomes NAND(Ti, S⊕u)
            _change_gate_type(target, "NAND")
            _add_input_to_gate(target, frw_signal)
            result['action'] = f"Target {target.name}: NOT -> NAND + {frw_signal.name}"

        elif target.type == "NAND":
            # T = NAND → add extra input S⊕u
            _add_input_to_gate(target, frw_signal)
            result['action'] = f"Target {target.name}: NAND + input {frw_signal.name}"

        elif target.type == "OR":
            # T = OR → add extra input S⊕u
            _add_input_to_gate(target, frw_signal)
            result['action'] = f"Target {target.name}: OR + input {frw_signal.name}"

        else:
            # Fallback: add input anyway
            _add_input_to_gate(target, frw_signal)
            result['action'] = f"Target {target.name}: + input {frw_signal.name}"

    else:
        # Lines 15-22: Add FRW to masking gate
        if masking.type == "NOT":
            # M = NOT → M becomes NOR(Mi, S⊕u)
            _change_gate_type(masking, "NOR")
            _add_input_to_gate(masking, frw_signal)
            result['action'] = f"Masking {masking.name}: NOT -> NOR + {frw_signal.name}"

        elif masking.type == "OR":
            # M = OR → add extra input S⊕u
            _add_input_to_gate(masking, frw_signal)
            result['action'] = f"Masking {masking.name}: OR + input {frw_signal.name}"

        elif masking.type == "NOR":
            # M = NOR → add extra input S⊕u
            _add_input_to_gate(masking, frw_signal)
            result['action'] = f"Masking {masking.name}: NOR + input {frw_signal.name}"

        else:
            # Fallback
            _add_input_to_gate(masking, frw_signal)
            result['action'] = f"Masking {masking.name}: + input {frw_signal.name}"

    return result


def _add_frw_v0(circuit, source, u, target, masking, fo_t, result):
    """
    Algorithm 3: FRW Addition Rule for S(=u) => T(=0).

    When target is forced to 0:
    - Masking gate should have T=0 at its input
    - For OR/NOR masking: T=0 is non-controlling → can't add there
    - For AND/NAND/NOT masking: T=0 can be used
    """
    frw_signal = _get_frw_signal(circuit, source, u)

    # Line 7: Check if FRW should go to target instead of masking
    add_to_target = False
    if masking is None:
        add_to_target = True
    elif masking.type in ("OR", "NOR"):
        add_to_target = True
    elif fo_t > 1:
        add_to_target = True

    if add_to_target:
        # Lines 8-14: Add FRW to target gate
        if target.type == "NOT":
            # T = NOT → T becomes NOR(Ti, S⊕u)
            _change_gate_type(target, "NOR")
            _add_input_to_gate(target, frw_signal)
            result['action'] = f"Target {target.name}: NOT -> NOR + {frw_signal.name}"

        elif target.type == "NOR":
            # T = NOR → add extra input S⊕u
            _add_input_to_gate(target, frw_signal)
            result['action'] = f"Target {target.name}: NOR + input {frw_signal.name}"

        elif target.type == "AND":
            # T = AND → add extra input S⊕u
            _add_input_to_gate(target, frw_signal)
            result['action'] = f"Target {target.name}: AND + input {frw_signal.name}"

        else:
            _add_input_to_gate(target, frw_signal)
            result['action'] = f"Target {target.name}: + input {frw_signal.name}"

    else:
        # Lines 15-22: Add FRW to masking gate
        if masking.type == "NOT":
            # M = NOT → M becomes NAND(Mi, S⊕u)
            _change_gate_type(masking, "NAND")
            _add_input_to_gate(masking, frw_signal)
            result['action'] = f"Masking {masking.name}: NOT -> NAND + {frw_signal.name}"

        elif masking.type == "AND":
            # M = AND → add extra input S⊕u
            _add_input_to_gate(masking, frw_signal)
            result['action'] = f"Masking {masking.name}: AND + input {frw_signal.name}"

        elif masking.type == "NAND":
            # M = NAND → add extra input S⊕u
            _add_input_to_gate(masking, frw_signal)
            result['action'] = f"Masking {masking.name}: NAND + input {frw_signal.name}"

        else:
            _add_input_to_gate(masking, frw_signal)
            result['action'] = f"Masking {masking.name}: + input {frw_signal.name}"

    return result
