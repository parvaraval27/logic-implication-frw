"""
Report generation — Table 1-style output.

Generates a summary report showing:
  - Circuit statistics
  - Implications added
  - Area overhead
  - Detection probability changes

Reference: Paper §5, Table 1.
"""

from src.reporting.area import compute_area, compute_area_overhead


def generate_report(original_circuit, modified_circuit, pipeline_result,
                    original_area=None):
    """
    Generate a Table 1-style summary report.

    Args:
        original_circuit: Circuit before FRW addition
        modified_circuit: Circuit after FRW addition
        pipeline_result: dict from run_implication_pipeline
        original_area: pre-computed original area (optional)

    Returns:
        str: formatted report
    """
    if original_area is None:
        original_area = compute_area(original_circuit)
    new_area = compute_area(modified_circuit)
    overhead = compute_area_overhead(original_area, new_area)

    num_gates_orig = len([n for n in original_circuit.nodes.values()
                          if n.role not in ("PI", "CONST")
                          and n.type not in ("PI", "WIRE")])
    num_gates_new = len([n for n in modified_circuit.nodes.values()
                         if n.role not in ("PI", "CONST")
                         and n.type not in ("PI", "WIRE")])

    lines = []
    lines.append("=" * 65)
    lines.append("  Implication-Based FRW Fault Tolerance Report")
    lines.append("=" * 65)
    lines.append("")
    lines.append(f"  PIs:  {len(original_circuit.PIs)}")
    lines.append(f"  POs:  {len(original_circuit.POs)}")
    lines.append(f"  Gates (original):  {num_gates_orig}")
    lines.append(f"  Gates (modified):  {num_gates_new}")
    lines.append("")
    lines.append(f"  Original Area (transistors):  {original_area}")
    lines.append(f"  Modified Area (transistors):  {new_area}")
    lines.append(f"  Area Overhead:  {overhead:.2f}%")
    lines.append("")
    lines.append(f"  Source candidates:  {pipeline_result.get('sources', 'N/A')}")
    lines.append(f"  Target candidates:  {pipeline_result.get('targets', 'N/A')}")
    lines.append(f"  Implications added:  {pipeline_result.get('implications_added', 0)}")
    lines.append("")

    # FRW details
    frw_details = pipeline_result.get('frw_details', [])
    if frw_details:
        lines.append("  FRW Additions:")
        lines.append("  " + "-" * 50)
        for i, frw in enumerate(frw_details, 1):
            lines.append(f"    {i}. {frw.get('action', 'N/A')}")
        lines.append("")

    # Detection probability summary
    lines.append("  Gate Detection Probabilities (after FRW):")
    lines.append("  " + "-" * 50)
    lines.append(f"  {'Gate':<12} {'SA0':>8} {'SA1':>8} {'P0':>8} {'P1':>8}")
    lines.append("  " + "-" * 50)
    for node in sorted(modified_circuit.nodes.values(),
                       key=lambda n: n.level if n.level >= 0 else 999):
        if node.role in ("PI", "CONST"):
            continue
        if node.type in ("PI", "WIRE"):
            continue
        lines.append(f"  {node.name:<12} {node.Pdet_sa0:>8.4f} {node.Pdet_sa1:>8.4f}"
                     f" {node.P0:>8.4f} {node.P1:>8.4f}")

    lines.append("=" * 65)

    return "\n".join(lines)
