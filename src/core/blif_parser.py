"""
BLIF (Berkeley Logic Interchange Format) parser.

Reads .blif files and converts them into Circuit objects compatible
with the implication FRW pipeline.

Each .names block is a sum-of-products (SOP) cover. We infer the gate
type from the truth table pattern when possible, and decompose complex
SOPs into AND/OR/NOT trees otherwise.

Reference: LGSynth91 benchmark suite.
"""

from src.core.netlist_graph import Node, Circuit


def _infer_gate_type(inputs, onset_rows, default_output):
    """
    Infer a standard gate type from a .names truth table.

    Args:
        inputs: list of input signal names
        onset_rows: list of input pattern strings that produce output=1
                    (or output=0 for OFF-set covers)
        default_output: '1' if onset_rows define when output=1,
                        '0' if onset_rows define when output=0

    Returns:
        (gate_type, is_inverted_output, needs_input_inversions)
        or None if the pattern doesn't match a single gate.
    """
    n = len(inputs)

    if n == 0:
        # Constant
        return None

    # Single-input gates
    if n == 1:
        if len(onset_rows) == 1:
            row = onset_rows[0]
            if default_output == '1':
                if row == '1':
                    return 'BUF'
                elif row == '0':
                    return 'NOT'
            elif default_output == '0':
                if row == '1':
                    return 'NOT'
                elif row == '0':
                    return 'BUF'
        return None

    # Multi-input gates — check common patterns
    if default_output == '1':
        # onset_rows define when output = 1

        # AND: output=1 only when ALL inputs = 1
        if len(onset_rows) == 1 and onset_rows[0] == '1' * n:
            return 'AND'

        # OR: output=1 when ANY input = 1
        # Each row has exactly one '1' and rest '-'
        if len(onset_rows) == n:
            is_or = True
            for i, row in enumerate(onset_rows):
                expected = ['-'] * n
                expected[i] = '1'
                if row != ''.join(expected):
                    is_or = False
                    break
            if is_or:
                return 'OR'

        # OR (alternative): single row of all '-' except... check for 1- pattern
        if len(onset_rows) == n and all(
            row.count('1') == 1 and row.count('-') == n - 1
            for row in onset_rows
        ):
            return 'OR'

    elif default_output == '0':
        # onset_rows define when output = 0

        # NAND: output=0 only when ALL inputs = 1
        if len(onset_rows) == 1 and onset_rows[0] == '1' * n:
            return 'NAND'

        # NOR: output=0 when ANY input = 1
        if len(onset_rows) == n and all(
            row.count('1') == 1 and row.count('-') == n - 1
            for row in onset_rows
        ):
            return 'NOR'

    # Check for XOR (2-input)
    if n == 2 and default_output == '1':
        if set(onset_rows) == {'01', '10'}:
            return 'XOR'
    if n == 2 and default_output == '0':
        if set(onset_rows) == {'01', '10'}:
            return 'XNOR'

    return None


def _sanitize_name(name):
    """Clean up BLIF signal names that contain special characters."""
    # Replace problematic characters
    name = name.replace('(', '_').replace(')', '_').replace('[', '_').replace(']', '_')
    name = name.replace('\\', '_').replace('/', '_').replace(' ', '_')
    # Remove trailing underscores
    name = name.rstrip('_')
    return name


def parse_blif(filepath):
    """
    Parse a BLIF file and return a Circuit object.

    Handles:
    - .model, .inputs, .outputs declarations
    - .names blocks (SOP truth tables)
    - Line continuations with backslash
    - Signal name sanitization

    Args:
        filepath: path to .blif file

    Returns:
        Circuit object
    """
    circuit = Circuit()
    circuit.name = ""

    # Read and join continuation lines
    with open(filepath, 'r') as f:
        raw_lines = f.readlines()

    # Join backslash-continued lines
    lines = []
    current = ""
    for line in raw_lines:
        line = line.rstrip('\n').rstrip('\r')
        if line.endswith('\\'):
            current += line[:-1] + " "
        else:
            current += line
            lines.append(current.strip())
            current = ""
    if current:
        lines.append(current.strip())

    # Parse declarations and .names blocks
    inputs = []
    outputs = []
    names_blocks = []  # list of (inputs_list, output, rows)
    constants = {}     # signal_name -> value

    i = 0
    while i < len(lines):
        line = lines[i]

        # Skip comments and empty lines
        if not line or line.startswith('#'):
            i += 1
            continue

        if line.startswith('.model'):
            circuit.name = line.split(None, 1)[1] if len(line.split()) > 1 else ""
            i += 1
            continue

        if line.startswith('.inputs'):
            tokens = line.split()[1:]
            inputs.extend([_sanitize_name(t) for t in tokens])
            i += 1
            continue

        if line.startswith('.outputs'):
            tokens = line.split()[1:]
            outputs.extend([_sanitize_name(t) for t in tokens])
            i += 1
            continue

        if line.startswith('.names'):
            tokens = line.split()[1:]
            signals = [_sanitize_name(t) for t in tokens]
            block_inputs = signals[:-1]
            block_output = signals[-1]

            # Collect truth table rows
            rows = []
            i += 1
            while i < len(lines):
                row_line = lines[i].strip()
                if not row_line or row_line.startswith('.') or row_line.startswith('#'):
                    break
                rows.append(row_line)
                i += 1

            names_blocks.append((block_inputs, block_output, rows))
            continue

        if line.startswith('.end'):
            break

        i += 1

    # Create PI nodes
    for name in inputs:
        node = Node(name, "PI")
        node.role = "PI"
        circuit.nodes[name] = node
        circuit.PIs.append(node)

    # Process .names blocks to create gate nodes
    gate_counter = [0]

    for block_inputs, block_output, rows in names_blocks:
        # Ensure all input signals exist
        for inp_name in block_inputs:
            if inp_name not in circuit.nodes:
                # Internal wire — will be defined by another .names block
                pass

        if not block_inputs:
            # Constant node
            if len(rows) == 1:
                val_parts = rows[0].split()
                if len(val_parts) == 1:
                    constants[block_output] = val_parts[0]
                    node = Node(block_output, "CONST")
                    node.role = "CONST"
                    node.value = val_parts[0]
                    circuit.nodes[block_output] = node
            elif len(rows) == 0:
                # No rows means output is always 0
                constants[block_output] = '0'
                node = Node(block_output, "CONST")
                node.role = "CONST"
                node.value = '0'
                circuit.nodes[block_output] = node
            continue

        # Parse truth table
        onset_rows = []
        offset_rows = []
        onset_output = '1'  # default: rows define when output = 1

        for row in rows:
            parts = row.split()
            if len(parts) == 2:
                pattern, out_val = parts
                if out_val == '1':
                    onset_rows.append(pattern)
                else:
                    offset_rows.append(pattern)
            elif len(parts) == 1:
                # For single-input, might be just the pattern (output=1 implied)
                onset_rows.append(parts[0])

        # Determine which set to use for gate inference
        if offset_rows and not onset_rows:
            # Only off-set rows — invert logic
            infer_rows = offset_rows
            onset_output = '0'
        elif onset_rows:
            infer_rows = onset_rows
            onset_output = '1'
        else:
            # No rows — output is always 0
            constants[block_output] = '0'
            node = Node(block_output, "CONST")
            node.role = "CONST"
            node.value = '0'
            circuit.nodes[block_output] = node
            continue

        # Try to infer a standard gate type
        gate_type = _infer_gate_type(block_inputs, infer_rows, onset_output)

        if gate_type is not None:
            # Simple gate — create directly
            _create_gate_node(circuit, block_output, gate_type,
                              block_inputs, outputs)
        else:
            # Complex SOP — decompose into AND/OR/NOT tree
            _decompose_sop(circuit, block_output, block_inputs,
                           onset_rows, outputs, gate_counter)

    # Mark PO nodes
    for name in outputs:
        if name in circuit.nodes:
            circuit.nodes[name].role = "PO"
            circuit.POs.append(circuit.nodes[name])

    # Wire up fanin/fanout connections
    _wire_connections(circuit)

    return circuit


def _create_gate_node(circuit, output_name, gate_type, input_names, po_names):
    """Create a simple gate node and add it to the circuit."""
    node = Node(output_name, gate_type)
    node.role = "PO" if output_name in po_names else "INTERNAL"
    node._input_names = input_names  # Store for wiring later
    circuit.nodes[output_name] = node


def _decompose_sop(circuit, output_name, input_names, onset_rows,
                   po_names, gate_counter):
    """
    Decompose a complex SOP (sum of products) into AND/OR/NOT gates.

    Each onset row becomes a product term (AND of literals).
    Multiple product terms are combined with OR.
    Inverted inputs use NOT gates.
    """
    if not onset_rows:
        # Constant 0
        node = Node(output_name, "CONST")
        node.role = "CONST"
        node.value = '0'
        circuit.nodes[output_name] = node
        return

    # Track which input inversions we need
    inv_cache = {}  # input_name -> inverted_node_name

    product_nodes = []

    for row_idx, pattern in enumerate(onset_rows):
        # Build the product term
        literals = []
        for j, ch in enumerate(pattern):
            if ch == '1':
                literals.append(input_names[j])
            elif ch == '0':
                # Need inverted input
                inv_name = f"_inv_{input_names[j]}"
                if inv_name not in inv_cache:
                    inv_node = Node(inv_name, "NOT")
                    inv_node.role = "INTERNAL"
                    inv_node._input_names = [input_names[j]]
                    circuit.nodes[inv_name] = inv_node
                    inv_cache[input_names[j]] = inv_name
                literals.append(inv_cache[input_names[j]])
            # '-' means don't care — skip this input

        if len(literals) == 0:
            # All don't-cares — this row always produces 1
            # Output is constant 1
            node = Node(output_name, "CONST")
            node.role = "CONST"
            node.value = '1'
            circuit.nodes[output_name] = node
            return
        elif len(literals) == 1:
            # Single literal — no AND needed
            product_nodes.append(literals[0])
        else:
            # AND gate for this product term
            gate_counter[0] += 1
            and_name = f"_and_{output_name}_{row_idx}"
            and_node = Node(and_name, "AND")
            and_node.role = "INTERNAL"
            and_node._input_names = literals
            circuit.nodes[and_name] = and_node
            product_nodes.append(and_name)

    if len(product_nodes) == 1:
        # Single product term — wire directly or create buffer
        if product_nodes[0] in circuit.nodes:
            # Rename the existing node to the output name
            old_name = product_nodes[0]
            if old_name != output_name:
                node = Node(output_name, "BUF")
                node.role = "PO" if output_name in po_names else "INTERNAL"
                node._input_names = [old_name]
                circuit.nodes[output_name] = node
        else:
            node = Node(output_name, "BUF")
            node.role = "PO" if output_name in po_names else "INTERNAL"
            node._input_names = [product_nodes[0]]
            circuit.nodes[output_name] = node
    else:
        # OR gate combining all product terms
        node = Node(output_name, "OR")
        node.role = "PO" if output_name in po_names else "INTERNAL"
        node._input_names = product_nodes
        circuit.nodes[output_name] = node


def _wire_connections(circuit):
    """Wire up fanin/fanout connections based on stored _input_names."""
    for node in circuit.nodes.values():
        input_names = getattr(node, '_input_names', None)
        if input_names is None:
            continue

        for inp_name in input_names:
            if inp_name in circuit.nodes:
                inp_node = circuit.nodes[inp_name]
                node.fanins.append(inp_node)
                inp_node.fanouts.append(node)

        # Clean up temporary attribute
        del node._input_names
