"""
Value Propagation (VP) Algorithm — Algorithm 4 from the paper.

Traverses gates from source to target, marking them with P (propagating)
or NP (non-propagating) markings to identify the implication path.

Markings:
  P0  = Propagating 0    P1  = Propagating 1
  NP0 = Non-propagating 0  NP1 = Non-propagating 1

Reference: Paper §3.2.3, Algorithm 4 (all 38 lines).
"""

from collections import deque
from src.core.netlist_graph import compute_logic_cone, reset_markings
from src.core.gate_lib import get_controlling_value, get_non_controlling_value, get_IP


def _marking_value(marking):
    """Extract the value ('0' or '1') from a marking like 'P0', 'NP1'."""
    if marking is None:
        return None
    return marking[-1]  # last char is always '0' or '1'


def _is_propagating(marking):
    """Check if marking is P (not NP)."""
    if marking is None:
        return False
    return marking.startswith('P') and not marking.startswith('NP')


def _is_any_marking(marking):
    """Check if a marking exists (P or NP)."""
    return marking is not None


def _xor_str(a, b):
    """XOR two single-char binary values, return as string."""
    return str(int(a) ^ int(b))


def mark_gates_vp(circuit, source, u, target):
    """
    Apply the Value Propagation algorithm (Algorithm 4) to mark gates
    from source to target.

    Args:
        circuit: Circuit object
        source: source Node
        u: source value ('0' or '1')
        target: target Node (the masking gate or original target)

    Returns:
        dict mapping node names to their VP markings ('P0','P1','NP0','NP1')

    Side effect: sets node.marking on all marked nodes.
    """
    # Reset all markings
    reset_markings(circuit)

    # Line 10-11: Compute logic cones
    cone_T = compute_logic_cone(circuit, target)
    cone_S = compute_logic_cone(circuit, source)

    processQ = deque()
    markings = {}  # name -> marking string

    # Line 12-13: Mark source gate output as P_u
    source_marking = f"P{u}"
    source.marking = source_marking
    markings[source.name] = source_marking

    # Line 14-17: If u ⊕ IP == NC, mark all inputs of source
    ip_s = get_IP(source.type)
    u_xor_ip = _xor_str(u, str(ip_s))
    nc_s = get_non_controlling_value(source.type)

    if nc_s is not None and u_xor_ip == nc_s:
        # Mark all inputs with P_{u⊕IP}
        input_marking = f"P{u_xor_ip}"
        for inp in source.fanins:
            inp.marking = input_marking
            markings[inp.name] = input_marking
            # Add fanouts of input in logic cone of T to processQ
            for fout in inp.fanouts:
                if fout in cone_T and fout not in cone_S:
                    if fout not in processQ:
                        processQ.append(fout)
                elif fout in cone_T and fout is target:
                    if fout not in processQ:
                        processQ.append(fout)

    # Line 18: Add all fanouts of source in cone of T to processQ
    for fout in source.fanouts:
        if fout in cone_T:
            processQ.append(fout)

    # Line 19-38: Process queue
    while processQ:
        cg = processQ.popleft()  # Line 20

        ip_cg = get_IP(cg.type)
        c_val = get_controlling_value(cg.type)
        nc_val = get_non_controlling_value(cg.type)

        # Get markings of all inputs
        input_markings = [(inp, inp.marking) for inp in cg.fanins]
        any_inputs_marked = any(m is not None for _, m in input_markings)

        old_marking = cg.marking
        new_marking = None

        # Line 21-23: If inputs not marked and u⊕IP == NC, mark all inputs
        if not any_inputs_marked and nc_val is not None:
            u_xor_ip_cg = _xor_str(u, str(ip_cg))
            if u_xor_ip_cg == nc_val:
                input_mark = f"P{u_xor_ip_cg}"
                for inp in cg.fanins:
                    inp.marking = input_mark
                    markings[inp.name] = input_mark
                    if inp in cone_T:
                        processQ.append(inp)

        # Now determine marking for CG based on its input markings
        # Refresh input markings after possible updates above
        input_markings = [(inp, inp.marking) for inp in cg.fanins]

        # Categorize inputs
        has_P_C = False
        count_P_C = 0
        all_P_NC = True
        has_P_NC = False
        has_NP_C = False
        all_NP_NC = True
        has_NP_NC = False
        any_marked = False

        for inp, m in input_markings:
            if m is None:
                # The paper §3.2.3 says: "implicitly treating unmarked inputs as P_NC...
                # (i.e. all_P_NC = TRUE)". So we do NOT set all_P_NC/all_NP_NC to False here.
                continue

            any_marked = True
            mv = _marking_value(m)
            is_p = _is_propagating(m)

            if c_val is not None and mv == c_val:
                if is_p:
                    has_P_C = True
                    count_P_C += 1
                else:
                    has_NP_C = True
                all_P_NC = False
                all_NP_NC = False
            elif nc_val is not None and mv == nc_val:
                if is_p:
                    has_P_NC = True
                    all_NP_NC = False
                else:
                    has_NP_NC = True
                    all_P_NC = False
            else:
                all_P_NC = False
                all_NP_NC = False

        if not any_marked:
            all_P_NC = False
            all_NP_NC = False

        # Apply marking rules (lines 24-34)
        if has_P_C:
            # Line 24-25: any input = P_C → mark as P_{C⊕IP}
            new_marking = f"P{_xor_str(c_val, str(ip_cg))}"
        elif all_P_NC and any_marked:
            # Line 26-27: all inputs = P_NC → mark as P_{NC⊕IP}
            new_marking = f"P{_xor_str(nc_val, str(ip_cg))}"
        elif has_P_NC and not has_P_C:
            # Line 28-29: any input = P_NC (but not all) → NP_{NC⊕IP}
            if not all_P_NC:
                new_marking = f"NP{_xor_str(nc_val, str(ip_cg))}"
            else:
                new_marking = f"P{_xor_str(nc_val, str(ip_cg))}"
        elif has_NP_C:
            # Line 30-31: any input = NP_C → NP_{C⊕IP}
            new_marking = f"NP{_xor_str(c_val, str(ip_cg))}"
        elif all_NP_NC and any_marked:
            # Line 32-33: all inputs = NP_NC → NP_{NC⊕IP}
            new_marking = f"NP{_xor_str(nc_val, str(ip_cg))}"

        # Handle gates without controlling/non-controlling values (NOT, BUF, XOR, etc.)
        if new_marking is None and any_marked:
            # For NOT/BUF: propagate with inversion
            if cg.type in ("NOT", "BUF", "WIRE"):
                for inp, m in input_markings:
                    if m is not None:
                        mv = _marking_value(m)
                        is_p = _is_propagating(m)
                        if cg.type == "NOT":
                            out_v = _xor_str(mv, '1')
                        else:
                            out_v = mv
                        prefix = "P" if is_p else "NP"
                        new_marking = f"{prefix}{out_v}"
                        break

        # Update marking if it changed or is better
        if new_marking is not None:
            # Upgrade: P is stronger than NP
            if old_marking is not None:
                old_is_p = _is_propagating(old_marking)
                new_is_p = _is_propagating(new_marking)
                if new_is_p and not old_is_p:
                    pass  # upgrade NP -> P
                elif old_is_p and not new_is_p:
                    new_marking = old_marking  # keep P
                # Same level: keep new if different value
            cg.marking = new_marking
            markings[cg.name] = new_marking

        # Line 35-37: If marking changed, add fanouts in cone(T) not in cone(S)
        if cg.marking != old_marking:
            for fout in cg.fanouts:
                if fout in cone_T and fout not in cone_S:
                    processQ.append(fout)
                elif fout in cone_T and fout is target:
                    # Always process the target itself
                    processQ.append(fout)

    return markings
