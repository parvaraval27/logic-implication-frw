import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.netlist_graph import parse_netlist, levelize
from src.implications.pipeline import run_implication_pipeline


def main():
    parser = argparse.ArgumentParser(
        description="Implication-Based Fault Tolerance Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --netlist examples/fig4.txt
  python main.py --netlist examples/fig4.txt --th1 0.3 --th2 0.4
        """
    )

    parser.add_argument('--netlist', '-n', required=True,
                        help='Path to the Verilog-style netlist file')
    parser.add_argument('--th1', type=float, default=0.3,
                        help='Source gate probability threshold (default: 0.3)')
    parser.add_argument('--th2', type=float, default=0.4,
                        help='Target gate detection probability threshold (default: 0.4)')
    parser.add_argument('--patterns', '-p', type=int, default=10000,
                        help='Number of random patterns for simulation (default: 10000)')
    parser.add_argument('--seed', type=int, default=42,
                        help='Random seed for reproducibility (default: 42)')

    args = parser.parse_args()

    if not os.path.exists(args.netlist):
        print(f"Error: Netlist file not found: {args.netlist}")
        sys.exit(1)

    # Parse circuit
    print("\n 1. Circuit Parsing & Structure ")
    circuit = parse_netlist(args.netlist)
    levelize(circuit)

    print(f"Successfully loaded and modeled: {args.netlist}")
    print(f"  Primary Inputs (PIs): {len(circuit.PIs)}")
    print(f"  Primary Outputs (POs): {len(circuit.POs)}")
    print(f"  Logic Gates: {len(circuit.get_internal_gates())}\n")

    # Run the implication pipeline
    run_implication_pipeline(
        circuit,
        Th1=args.th1,
        Th2=args.th2,
        num_patterns=args.patterns,
        seed=args.seed,
    )


if __name__ == '__main__':
    main()
