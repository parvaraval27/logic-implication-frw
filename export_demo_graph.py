import os
import sys
import json

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.netlist_graph import parse_netlist, levelize
from src.core.blif_parser import parse_blif
from src.faultsim.random_pattern_sim import run_fault_simulation
from src.reporting.export import export_graph_json


def main():
    benchmarks_dir = "examples"
    output_dir = os.path.join("dashboard", "public", "benchmarks")
    os.makedirs(output_dir, exist_ok=True)
    
    file_path = os.path.join(benchmarks_dir, "fig4.txt")
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found.")
        return

    name = "fig4"
    output_path = os.path.join(output_dir, f"{name}.json")
    
    print(f"Exporting Demo Graph for {name}...")
    
    # Parse circuit
    circuit = parse_netlist(file_path)
    levelize(circuit)
    
    # Run initial fault simulation to populate baseline probabilities
    print("Running fault simulation to generate probabilities...")
    run_fault_simulation(circuit, num_patterns=10000, seed=42)
    
    # Export graph
    export_graph_json(circuit, circuit, output_path)
    print(f"Exported to {output_path}")
    
    # Write index.json
    index_path = os.path.join(output_dir, "index.json")
    with open(index_path, "w") as f:
        json.dump([name], f, indent=2)
    print(f"Updated {index_path}")

if __name__ == "__main__":
    main()
