"""
Circuit model: Node, Circuit, Fault, parsing, levelization, simulation.

Ported from vlsi-testing-atpg/netlist_graph.py with extensions:
  - Node extended with P0/P1, Pdet_sa0/Pdet_sa1, marking attributes
  - Logic cone computation
  - DAG path counting for PRP (Eq. 2)
  - Circuit cloning for FRW mutation
"""

import os
import copy
from collections import deque


# --------------------------------------------------------------------------- #
#  Data classes
# --------------------------------------------------------------------------- #

class Node:
    def __init__(self, name, gate_type):
        self.name = name
        self.type = gate_type        # AND, OR, NAND, NOR, NOT, BUF, XOR, XNOR, WIRE, PI, CONST
        self.role = "INTERNAL"       # PI, PO, INTERNAL, CONST
        self.fanins = []             # list[Node]
        self.fanouts = []            # list[Node]
        self.value = 'X'             # 0, 1, X  (3-valued simulation)
        self.level = -1

        # --- Extensions for the paper ---
        self.P0 = 0.0                # probability of output value 0
        self.P1 = 0.0                # probability of output value 1
        self.Pdet_sa0 = 0.0          # stuck-at-0 fault detection probability
        self.Pdet_sa1 = 0.0          # stuck-at-1 fault detection probability
        self.marking = None          # VP marking: 'P0', 'P1', 'NP0', 'NP1', or None

    def __repr__(self):
        return f"Node({self.name}, {self.type}, role={self.role})"


class Circuit:
    def __init__(self):
        self.nodes = {}   # name -> Node
        self.PIs = []     # list[Node]
        self.POs = []     # list[Node]

    def get_gates(self):
        """Return all non-PI, non-CONST nodes (actual logic gates + PO wires)."""
        return [n for n in self.nodes.values()
                if n.role not in ("PI", "CONST")]

    def get_internal_gates(self):
        """Return only logic gates (not PI, not CONST, not bare PO wires)."""
        return [n for n in self.nodes.values()
                if n.role not in ("PI", "CONST")
                and n.type not in ("PI", "WIRE")]


class Fault:
    def __init__(self, node, stuck_at):
        self.node = node
        self.stuck_at = stuck_at   # 0 or 1

    def __repr__(self):
        return f"Fault({self.node.name}/SA{self.stuck_at})"


class Implication:
    """Represents S(=u) => T(=v)."""
    def __init__(self, source, u, target, v):
        self.source = source    # Node
        self.u = u              # '0' or '1'
        self.target = target    # Node
        self.v = v              # '0' or '1'
        self.path_gates = []    # list[Node] (PathG from Algorithm 5)
        self.gain = 0.0

    def __repr__(self):
        return f"Impl({self.source.name}={self.u} => {self.target.name}={self.v}, gain={self.gain:.4f})"


# --------------------------------------------------------------------------- #
#  Parsing  (ported from vlsi-testing-atpg)
# --------------------------------------------------------------------------- #

def get_or_create_node(circuit, name, gate_type="WIRE"):
    if name not in circuit.nodes:
        circuit.nodes[name] = Node(name, gate_type)
        if gate_type == "PI":
            circuit.nodes[name].role = "PI"
        elif gate_type == "PO":
            circuit.nodes[name].role = "PO"
            circuit.nodes[name].type = "WIRE"
    else:
        node = circuit.nodes[name]
        existing_type = node.type
        if gate_type == "PI":
            node.role = "PI"
            node.type = "PI"
        elif gate_type == "PO":
            node.role = "PO"
        elif gate_type not in ("WIRE", "PI", "PO"):
            if existing_type == "WIRE":
                node.type = gate_type
    return circuit.nodes[name]


def apply_constant_literal(node):
    token = node.name.strip().lower()
    if token == "1'b0":
        node.role = "CONST"
        node.type = "CONST"
        node.value = '0'
        node.level = 0
    elif token == "1'b1":
        node.role = "CONST"
        node.type = "CONST"
        node.value = '1'
        node.level = 0


def parse_netlist(filename):
    """Parse a Verilog-style gate-level netlist file."""
    circuit = Circuit()

    with open(filename, 'r', encoding='utf-8') as f:
        for raw_line in f:
            line = raw_line.strip()
            if "//" in line:
                line = line.split("//", 1)[0].strip()
            if not line or line.startswith("#"):
                continue

            if line.lower().startswith("input "):
                names = line[5:].strip().rstrip(";")
                for name in [n.strip() for n in names.split(",") if n.strip()]:
                    node = get_or_create_node(circuit, name, "PI")
                    if node not in circuit.PIs:
                        circuit.PIs.append(node)

            elif line.lower().startswith("output "):
                names = line[6:].strip().rstrip(";")
                for name in [n.strip() for n in names.split(",") if n.strip()]:
                    node = get_or_create_node(circuit, name, "PO")
                    if node not in circuit.POs:
                        circuit.POs.append(node)

            elif line.lower().startswith(("module", "wire", "endmodule")):
                continue

            else:
                stmt = line.rstrip(";")
                if "(" not in stmt or ")" not in stmt:
                    continue
                header = stmt[:stmt.find("(")].strip()
                body = stmt[stmt.find("(") + 1:stmt.rfind(")")]
                if not header:
                    continue
                gate_type = header.split()[0].upper()
                pins = [p.strip() for p in body.split(",") if p.strip()]
                if len(pins) < 2:
                    continue
                if gate_type in ("NOT", "BUF") and len(pins) != 2:
                    continue

                out_name = pins[0]
                in_names = pins[1:]
                node = get_or_create_node(circuit, out_name, gate_type)
                for inp in in_names:
                    in_node = get_or_create_node(circuit, inp)
                    apply_constant_literal(in_node)
                    if in_node not in node.fanins:
                        node.fanins.append(in_node)
                    if node not in in_node.fanouts:
                        in_node.fanouts.append(node)

    return circuit


# --------------------------------------------------------------------------- #
#  Levelization  (ported from vlsi-testing-atpg)
# --------------------------------------------------------------------------- #

def levelize(circuit):
    """Assign topological levels to all nodes (BFS from PIs/CONSTs)."""
    queue = deque()
    for node in circuit.nodes.values():
        node.level = -1
    for pi in circuit.PIs:
        pi.level = 0
        queue.append(pi)
    for node in circuit.nodes.values():
        if node.role == "CONST":
            node.level = 0
            queue.append(node)

    while queue:
        node = queue.popleft()
        for out in node.fanouts:
            if all(inp.level != -1 for inp in out.fanins):
                candidate_level = max(inp.level for inp in out.fanins) + 1
                if out.level == -1 or candidate_level > out.level:
                    out.level = candidate_level
                    queue.append(out)


# --------------------------------------------------------------------------- #
#  Gate evaluation  (ported from vlsi-testing-atpg)
# --------------------------------------------------------------------------- #

def _eval_and(vals):
    if '0' in vals:
        return '0'
    if 'X' in vals:
        return 'X'
    return '1'


def _eval_or(vals):
    if '1' in vals:
        return '1'
    if 'X' in vals:
        return 'X'
    return '0'


def eval_gate(node):
    """Evaluate a gate's output from its fanin values (3-valued: 0/1/X)."""
    vals = [inp.value for inp in node.fanins]

    if node.type == "AND":
        return _eval_and(vals)
    elif node.type == "OR":
        return _eval_or(vals)
    elif node.type == "NOT":
        if not vals or vals[0] == 'X':
            return 'X'
        return '1' if vals[0] == '0' else '0'
    elif node.type == "NAND":
        and_val = _eval_and(vals)
        if and_val == 'X':
            return 'X'
        return '1' if and_val == '0' else '0'
    elif node.type == "NOR":
        or_val = _eval_or(vals)
        if or_val == 'X':
            return 'X'
        return '1' if or_val == '0' else '0'
    elif node.type == "BUF":
        return vals[0] if vals else 'X'
    elif node.type == "XOR":
        if 'X' in vals:
            return 'X'
        ones = sum(1 for v in vals if v == '1')
        return '1' if ones % 2 == 1 else '0'
    elif node.type == "XNOR":
        if 'X' in vals:
            return 'X'
        ones = sum(1 for v in vals if v == '1')
        return '0' if ones % 2 == 1 else '1'
    # WIRE / fallback
    if len(vals) == 1:
        return vals[0]
    return 'X'


# --------------------------------------------------------------------------- #
#  Simulation  (ported from vlsi-testing-atpg)
# --------------------------------------------------------------------------- #

def simulate(circuit):
    """Level-order simulation (all gates evaluated once)."""
    nodes_sorted = sorted(circuit.nodes.values(), key=lambda n: n.level if n.level >= 0 else 999999)
    for node in nodes_sorted:
        if node.role in ("PI", "CONST"):
            continue
        if node.level == -1:
            continue
        node.value = eval_gate(node)


def simulate_event_driven(circuit, changed_inputs=None):
    """Event-driven simulation (only evaluates gates whose inputs changed)."""
    activity_queue = deque()
    queued = set()

    def schedule(node):
        if node not in queued:
            queued.add(node)
            activity_queue.append(node)

    if changed_inputs is None:
        seed_nodes = list(circuit.PIs)
    else:
        seed_nodes = list(changed_inputs)

    for node in seed_nodes:
        for fanout_gate in node.fanouts:
            schedule(fanout_gate)

    if changed_inputs is None:
        for node in circuit.nodes.values():
            if node.role == "CONST":
                for fanout_gate in node.fanouts:
                    schedule(fanout_gate)

    while activity_queue:
        node = activity_queue.popleft()
        queued.discard(node)
        if node.level == -1:
            continue
        old_value = node.value
        new_value = eval_gate(node)
        node.value = new_value
        if new_value != old_value:
            for fanout_gate in node.fanouts:
                schedule(fanout_gate)


# --------------------------------------------------------------------------- #
#  Fault generation  (ported from vlsi-testing-atpg)
# --------------------------------------------------------------------------- #

def generate_faults(circuit):
    """Generate all single stuck-at faults for every node."""
    faults = []
    for node in circuit.nodes.values():
        faults.append(Fault(node, 0))
        faults.append(Fault(node, 1))
    return faults


# --------------------------------------------------------------------------- #
#  Extensions for the paper
# --------------------------------------------------------------------------- #

def compute_logic_cone(circuit, root):
    """
    Compute the transitive fanin cone of `root`.
    Returns a set of Node objects that are in the logic cone (including root).
    Used by Algorithm 4, lines 10-11.
    """
    cone = set()
    queue = deque([root])
    while queue:
        node = queue.popleft()
        if node in cone:
            continue
        cone.add(node)
        for fin in node.fanins:
            if fin not in cone:
                queue.append(fin)
    return cone


def compute_fanout_cone(circuit, root):
    """
    Compute the transitive fanout cone of `root`.
    Returns a set of Node objects reachable from root via fanouts (including root).
    """
    cone = set()
    queue = deque([root])
    while queue:
        node = queue.popleft()
        if node in cone:
            continue
        cone.add(node)
        for fout in node.fanouts:
            if fout not in cone:
                queue.append(fout)
    return cone


def count_paths(source, target):
    """
    Count the number of distinct paths from `source` to `target` in the DAG.
    Traverses forward from source using BFS-like memoization.
    Used for PRP computation (Eq. 2).
    """
    # Memoized DFS approach
    memo = {}

    def _dfs(node):
        if node is target:
            return 1
        if node in memo:
            return memo[node]
        total = 0
        for fout in node.fanouts:
            total += _dfs(fout)
        memo[node] = total
        return total

    return _dfs(source)


def count_paths_to_any_po(circuit, source):
    """Count distinct paths from source to any primary output."""
    total = 0
    for po in circuit.POs:
        total += count_paths(source, po)
    return total


def clone_circuit(circuit):
    """
    Deep-copy a circuit, preserving the graph structure.
    Returns a new Circuit with new Node objects and correct fanin/fanout links.
    """
    new_circuit = Circuit()
    # Create all new nodes
    for name, node in circuit.nodes.items():
        new_node = Node(name, node.type)
        new_node.role = node.role
        new_node.value = node.value
        new_node.level = node.level
        new_node.P0 = node.P0
        new_node.P1 = node.P1
        new_node.Pdet_sa0 = node.Pdet_sa0
        new_node.Pdet_sa1 = node.Pdet_sa1
        new_node.marking = node.marking
        new_circuit.nodes[name] = new_node

    # Reconstruct fanin/fanout links
    for name, node in circuit.nodes.items():
        new_node = new_circuit.nodes[name]
        new_node.fanins = [new_circuit.nodes[fi.name] for fi in node.fanins]
        new_node.fanouts = [new_circuit.nodes[fo.name] for fo in node.fanouts]

    # Reconstruct PI/PO lists
    new_circuit.PIs = [new_circuit.nodes[pi.name] for pi in circuit.PIs]
    new_circuit.POs = [new_circuit.nodes[po.name] for po in circuit.POs]

    return new_circuit


def reset_values(circuit):
    """Reset all node values to 'X' (except CONSTs)."""
    for node in circuit.nodes.values():
        if node.role == "CONST":
            continue
        node.value = 'X'


def reset_markings(circuit):
    """Clear VP markings on all nodes."""
    for node in circuit.nodes.values():
        node.marking = None
