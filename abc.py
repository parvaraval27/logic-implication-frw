import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.netlist_graph import parse_netlist, levelize, Implication
from src.implications.pipeline import evaluate_implication
from src.faultsim.random_pattern_sim import run_fault_simulation

def main():
    print("Loading Fig 4 Circuit...")
    circuit = parse_netlist("examples/fig4.txt")
    levelize(circuit)

    # 1. Simulate with 1,000,000 patterns to match the paper's precision
    print("Running 1,000,000 pattern fault simulation...")
    run_fault_simulation(circuit, num_patterns=10000, seed=42)

    # 2. Manually isolate G4 and G3
    g4 = circuit.nodes.get("G4")
    g3 = circuit.nodes.get("G3")
    
    if not g4 or not g3:
        print("Error: G4 or G3 not found in netlist.")
        return

    # 3. Create the specific implication: G4=0 => G3=0
    impl = Implication(source=g4, u='0', target=g3, v='0')

    # 4. Print "Before" probabilities for the expected path
    expected_path_names = ["G6", "G8", "G1", "G2", "G3"]
    print("\n--- BEFORE FRW ---")
    for name in expected_path_names:
        node = circuit.nodes[name]
        print(f"{name} -> Pdet_sa0: {node.Pdet_sa0:.4f}, Pdet_sa1: {node.Pdet_sa1:.4f}")

    # 5. Run the evaluation (VP, IPI, and Gain)
    print("\n--- EVALUATING IMPLICATION ---")
    gain = evaluate_implication(circuit, impl)

    # 6. Print the Results
    identified_path = [g.name for g in impl.path_gates]
    print(f"Implication: {impl.source.name}={impl.u} => {impl.target.name}={impl.v}")
    print(f"Path Gates Identified by IPI Algorithm: {identified_path}")
    print(f"Calculated Gain: {gain:.4f}")

if __name__ == '__main__':
    main()