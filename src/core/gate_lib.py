"""
Gate library: controlling/non-controlling values, inversion polarity (IP),
and transistor count per gate type.

Used throughout the VP (Algorithm 4), IPI (Algorithm 5), FRW addition
(Algorithms 2 & 3), and area computation modules.

Reference: Paper §3.2.3, Algorithm 4 lines 3-4.
  IP = 1 for NOT, NAND, NOR (inverting gates)
  IP = 0 for AND, OR, BUF (non-inverting gates)
"""

# --------------------------------------------------------------------------- #
#  Gate metadata table
# --------------------------------------------------------------------------- #

GATE_INFO = {
    "AND":  {"controlling": "0", "non_controlling": "1", "IP": 0, "base_transistors": 6},
    "OR":   {"controlling": "1", "non_controlling": "0", "IP": 0, "base_transistors": 6},
    "NAND": {"controlling": "0", "non_controlling": "1", "IP": 1, "base_transistors": 4},
    "NOR":  {"controlling": "1", "non_controlling": "0", "IP": 1, "base_transistors": 4},
    "NOT":  {"controlling": None, "non_controlling": None, "IP": 1, "base_transistors": 2},
    "BUF":  {"controlling": None, "non_controlling": None, "IP": 0, "base_transistors": 4},
    "WIRE": {"controlling": None, "non_controlling": None, "IP": 0, "base_transistors": 0},
    "XOR":  {"controlling": None, "non_controlling": None, "IP": 0, "base_transistors": 8},
    "XNOR": {"controlling": None, "non_controlling": None, "IP": 1, "base_transistors": 8},
}


def get_controlling_value(gate_type):
    """Return the controlling input value for the gate type, or None."""
    info = GATE_INFO.get(gate_type.upper())
    return info["controlling"] if info else None


def get_non_controlling_value(gate_type):
    """Return the non-controlling input value for the gate type, or None."""
    info = GATE_INFO.get(gate_type.upper())
    return info["non_controlling"] if info else None


def get_IP(gate_type):
    """Return inversion polarity: 1 for inverting gates (NOT/NAND/NOR), else 0."""
    info = GATE_INFO.get(gate_type.upper())
    return info["IP"] if info else 0


def is_inverting(gate_type):
    """Convenience: True for NOT, NAND, NOR."""
    return get_IP(gate_type) == 1


def get_transistor_count(gate_type, num_inputs=2):
    """
    Estimate transistor count for a gate.
    For NAND/NOR: 2 * num_inputs (CMOS complementary).
    For AND/OR: 2 * num_inputs + 2 (NAND/NOR + inverter).
    For NOT/BUF: fixed 2 / 4.
    """
    gt = gate_type.upper()
    if gt in ("NOT",):
        return 2
    if gt in ("BUF", "WIRE"):
        return 4
    if gt in ("NAND", "NOR"):
        return 2 * num_inputs
    if gt in ("AND", "OR"):
        return 2 * num_inputs + 2  # complementary + output inverter
    if gt in ("XOR", "XNOR"):
        return 4 * num_inputs  # transmission-gate style
    return 2 * num_inputs  # fallback


def xor_value(val, ip):
    """Compute val XOR ip  (both are 0 or 1 integers), return as string '0'/'1'."""
    return str(int(val) ^ int(ip))


def get_gate_area_ptm130(gate_type, num_inputs=2):
    """
    Estimate area using PTM 130nm nMOS and pMOS drain widths.
    Standard logical effort sizing for equal worst-case rise/fall transitions:
      W_min = 130 nm
      INV: Wn = 1 * W_min, Wp = 2 * W_min
      NAND-k: Wn = k * W_min, Wp = 2 * W_min
      NOR-k: Wn = 1 * W_min, Wp = 2*k * W_min
    Returns area in nm (sum of drain widths).
    """
    W_min = 130
    gt = gate_type.upper()
    
    if gt == "NOT":
        Wn = W_min
        Wp = 2 * W_min
        return Wn + Wp
    elif gt == "NAND":
        Wn = num_inputs * W_min
        Wp = 2 * W_min
        return num_inputs * (Wn + Wp)
    elif gt == "NOR":
        Wn = W_min
        Wp = 2 * num_inputs * W_min
        return num_inputs * (Wn + Wp)
    elif gt == "AND":
        # NAND + INV
        return get_gate_area_ptm130("NAND", num_inputs) + get_gate_area_ptm130("NOT")
    elif gt == "OR":
        # NOR + INV
        return get_gate_area_ptm130("NOR", num_inputs) + get_gate_area_ptm130("NOT")
    elif gt in ("BUF", "WIRE"):
        # Two inverters
        return 2 * get_gate_area_ptm130("NOT")
    
    # Fallback for others based on basic transistor count * average width
    return get_transistor_count(gt, num_inputs) * 1.5 * W_min
