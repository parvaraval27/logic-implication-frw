"""
CLI entry point for the implication-based FRW fault tolerance tool.

Usage:
    python main.py --netlist examples/fig4.txt --th1 0.3 --th2 0.4 --gain-th 0.02 --patterns 10000
"""

import argparse
import sys
import os

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.netlist_graph import parse_netlist, levelize, clone_circuit
from src.core.blif_parser import parse_blif
from src.implications.pipeline import run_implication_pipeline
from src.reporting.area import compute_area
from src.reporting.report import generate_report
from src.reporting.export import export_graph_json


def main():
    parser = argparse.ArgumentParser(
        description="Implication-based FRW Fault Tolerance Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --netlist examples/fig4.txt
  python main.py --netlist examples/fig4.txt --th1 0.3 --th2 0.4 --gain-th 0.02
  python main.py --netlist examples/fig4.txt --patterns 5000 --indirect
        """
    )

    parser.add_argument('--netlist', '-n', required=True,
                        help='Path to the Verilog-style netlist file')
    parser.add_argument('--th1', type=float, default=0.3,
                        help='Source gate probability threshold (default: 0.3)')
    parser.add_argument('--th2', type=float, default=0.4,
                        help='Target gate detection probability threshold (default: 0.4)')
    parser.add_argument('--gain-th', type=float, default=0.02,
                        help='Minimum gain threshold for FRW addition (default: 0.02)')
    parser.add_argument('--patterns', '-p', type=int, default=10000,
                        help='Number of random patterns for simulation (default: 10000)')
    parser.add_argument('--seed', type=int, default=42,
                        help='Random seed for reproducibility (default: 42)')
    parser.add_argument('--indirect', action='store_true',
                        help='Also use indirect implication learning')
    parser.add_argument('--quiet', '-q', action='store_true',
                        help='Suppress progress output')
    parser.add_argument('--verify-fig4', action='store_true',
                        help='Force logic to evaluate Fig 4 G4=0=>G3=0 implication and run HOPE cross-validation')
    parser.add_argument('--export-json', type=str,
                        help='Path to export the graph JSON for the React dashboard')


    args = parser.parse_args()

    if not os.path.exists(args.netlist):
        print(f"Error: Netlist file not found: {args.netlist}")
        sys.exit(1)

    # Parse circuit
    if args.netlist.lower().endswith('.blif'):
        circuit = parse_blif(args.netlist)
    else:
        circuit = parse_netlist(args.netlist)
    levelize(circuit)

    print(f"Loaded: {args.netlist}")
    print(f"  PIs: {len(circuit.PIs)}, POs: {len(circuit.POs)}, "
          f"Nodes: {len(circuit.nodes)}")

    # Save original for comparison
    original_area = compute_area(circuit)
    original_circuit = clone_circuit(circuit)

    # Run pipeline
    result = run_implication_pipeline(
        circuit,
        Th1=args.th1,
        Th2=args.th2,
        gain_threshold=args.gain_th,
        num_patterns=args.patterns,
        seed=args.seed,
        use_indirect=args.indirect,
        verbose=not args.quiet,
        verify_fig4=args.verify_fig4,
    )

    # Generate report
    report = generate_report(original_circuit, circuit, result, original_area)
    print("\n" + report)

    if args.export_json:
        export_graph_json(original_circuit, circuit, args.export_json)


if __name__ == '__main__':
    main()
