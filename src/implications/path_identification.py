"""
Implication Path Identification (IPI) Algorithm — Algorithm 5 from the paper.

Starts from the target gate and traces backward using VP markings
to identify the set of gates (PathG) whose detection probabilities
will be reduced when the implication FRW is added.

Reference: Paper §3.2.3, Algorithm 5 (all 37 lines).
"""

from collections import deque
from src.core.gate_lib import get_controlling_value, get_non_controlling_value


def _marking_value(marking):
    """Extract the value ('0' or '1') from a marking."""
    if marking is None:
        return None
    return marking[-1]


def _is_propagating(marking):
    """Check if marking is P (not NP)."""
    if marking is None:
        return False
    return marking.startswith('P') and not marking.startswith('NP')


def identify_path(circuit, source, target, markings):
    """
    Apply the IPI algorithm (Algorithm 5) to determine the implication path.

    Args:
        circuit: Circuit object
        source: source Node
        target: target Node (masking gate or original target)
        markings: dict of {node_name: marking} from VP algorithm

    Returns:
        list of Nodes in the implication path (PathG), excluding source and target.
    """
    path_G = []
    processQ = deque()
    in_queue = set()

    # Line 9: Add target to processQ
    processQ.append(target)
    in_queue.add(target.name)

    while processQ:
        cg = processQ.popleft()  # Line 11

        # Line 12-14: Add CG to PathG if it's not source
        if cg is not source:
            path_G.append(cg)

        # Get controlling/non-controlling values for this gate
        c_val = get_controlling_value(cg.type)
        nc_val = get_non_controlling_value(cg.type)

        # Get input markings
        input_markings = [(inp, markings.get(inp.name)) for inp in cg.fanins]

        # Count inputs with P_C markings
        pc_inputs = []
        pnc_inputs = []
        npc_inputs = []
        npnc_inputs = []

        for inp, m in input_markings:
            if m is None:
                continue
            mv = _marking_value(m)
            is_p = _is_propagating(m)

            if c_val is not None and mv == c_val:
                if is_p:
                    pc_inputs.append(inp)
                else:
                    npc_inputs.append(inp)
            elif nc_val is not None and mv == nc_val:
                if is_p:
                    pnc_inputs.append(inp)
                else:
                    npnc_inputs.append(inp)
            else:
                # For NOT/BUF, any marked input counts
                if cg.type in ("NOT", "BUF", "WIRE"):
                    if is_p:
                        pnc_inputs.append(inp)
                    else:
                        npnc_inputs.append(inp)

        # Apply IPI rules (lines 15-35)

        # Line 15-18: One input marked with P_C
        if len(pc_inputs) == 1:
            inp = pc_inputs[0]
            if inp.role != "PI" and inp.name not in in_queue:
                processQ.append(inp)
                in_queue.add(inp.name)
            # If source is a PI, we've reached the end

        # Line 15 special case (Paper Fig. 2):
        # If 2+ inputs marked P_C → don't follow (fault already masked)
        elif len(pc_inputs) >= 2:
            pass  # Don't add any inputs

        # Line 19-24: All inputs marked with P_NC
        elif len(pnc_inputs) == len([inp for inp in cg.fanins
                                      if markings.get(inp.name) is not None]) and len(pnc_inputs) > 0:
            for inp in pnc_inputs:
                if inp.role != "PI" and inp.name not in in_queue:
                    processQ.append(inp)
                    in_queue.add(inp.name)

        # Line 25-28: One input marked with NP_C
        elif len(npc_inputs) == 1:
            inp = npc_inputs[0]
            if inp.role != "PI" and inp.name not in in_queue:
                processQ.append(inp)
                in_queue.add(inp.name)

        elif len(npc_inputs) >= 2:
            pass  # Don't follow

        # Line 29-34: All inputs marked with NP_NC
        elif len(npnc_inputs) == len([inp for inp in cg.fanins
                                       if markings.get(inp.name) is not None]) and len(npnc_inputs) > 0:
            for inp in npnc_inputs:
                if inp.role != "PI" and inp.name not in in_queue:
                    processQ.append(inp)
                    in_queue.add(inp.name)

        # Handle NOT/BUF where there's only one input
        elif cg.type in ("NOT", "BUF", "WIRE") and cg.fanins:
            inp = cg.fanins[0]
            if markings.get(inp.name) is not None:
                if inp.role != "PI" and inp.name not in in_queue:
                    processQ.append(inp)
                    in_queue.add(inp.name)

    return path_G
