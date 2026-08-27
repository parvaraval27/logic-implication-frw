"""
Five-valued logic engine for D/D̄ fault-effect propagation.

Values: '0', '1', 'D' (good=1, faulty=0), 'D_bar' (good=0, faulty=1), 'X'
"""


def invert_logic(v):
    """Invert a 5-valued logic value."""
    inv = {
        '0': '1',
        '1': '0',
        'D': 'D_bar',
        'D_bar': 'D',
        'X': 'X',
    }
    return inv.get(v, 'X')


def logic_to_pair(v):
    """Convert 5-valued logic to (good, faulty) binary pair."""
    mapping = {
        '0': (0, 0),
        '1': (1, 1),
        'D': (1, 0),
        'D_bar': (0, 1),
        'X': (None, None),
    }
    return mapping.get(v, (None, None))


def pair_to_logic(good, faulty):
    """Convert (good, faulty) binary pair to 5-valued logic."""
    if good is None or faulty is None:
        return 'X'
    if good == 0 and faulty == 0:
        return '0'
    if good == 1 and faulty == 1:
        return '1'
    if good == 1 and faulty == 0:
        return 'D'
    if good == 0 and faulty == 1:
        return 'D_bar'
    return 'X'


def to_good_logic(v):
    """Extract good-circuit value from 5-valued logic."""
    if v == 'D':
        return '1'
    if v == 'D_bar':
        return '0'
    return v


def _inv_binary(v):
    return None if v is None else 1 - v


def _eval_and(vals):
    if 0 in vals:
        return 0
    if None in vals:
        return None
    return 1


def _eval_or(vals):
    if 1 in vals:
        return 1
    if None in vals:
        return None
    return 0


def _eval_not(vals):
    if not vals or vals[0] is None:
        return None
    return 1 - vals[0]


def _eval_buf(vals):
    if not vals:
        return None
    return vals[0]


def _eval_xor(vals):
    if None in vals:
        return None
    ones = sum(vals)
    return 1 if (ones % 2) else 0


def eval_binary_gate(gate_type, vals):
    """Evaluate a gate on binary (0/1/None) values."""
    handlers = {
        'AND': _eval_and,
        'OR': _eval_or,
        'NOT': _eval_not,
        'BUF': _eval_buf,
        'WIRE': _eval_buf,
        'XOR': _eval_xor,
        'XNOR': lambda v: _inv_binary(_eval_xor(v)),
        'NAND': lambda v: _inv_binary(_eval_and(v)),
        'NOR': lambda v: _inv_binary(_eval_or(v)),
    }
    handler = handlers.get(gate_type)
    if handler is not None:
        return handler(vals)
    if len(vals) == 1:
        return vals[0]
    return None


def eval_gate_5val(node, active_fault=None):
    vals = [inp.value for inp in node.fanins]
    if not vals and node.role == 'CONST':
        return node.value

    good_vals = []
    faulty_vals = []
    for v in vals:
        g, f = logic_to_pair(v)
        good_vals.append(g)
        faulty_vals.append(f)

    good_out = eval_binary_gate(node.type, good_vals)
    faulty_out = eval_binary_gate(node.type, faulty_vals)
    logic_out = pair_to_logic(good_out, faulty_out)

    # Inject fault effect if this node is the fault site
    if active_fault is not None and node is active_fault.node:
        good, _faulty = logic_to_pair(logic_out)
        if good is None:
            return 'X'
        return pair_to_logic(good, active_fault.stuck_at)

    return logic_out


def simulate_5val(circuit, active_fault=None):

    nodes_sorted = sorted(circuit.nodes.values(),
                          key=lambda n: n.level if n.level >= 0 else 999999)
    for node in nodes_sorted:
        if node.role in ("PI", "CONST"):
            continue
        if node.level == -1:
            continue
        node.value = eval_gate_5val(node, active_fault)


def has_fault_at_po(circuit):
    return any(po.value in ('D', 'D_bar') for po in circuit.POs)
