import os
import sys
import glob
import json

from src.core.netlist_graph import parse_netlist, levelize, clone_circuit
from src.core.blif_parser import parse_blif
from src.faultsim.random_pattern_sim import run_fault_simulation
from src.implications.pipeline import run_implication_pipeline
from src.reporting.export import export_graph_json


def process_benchmark(file_path, output_dir):
    filename = os.path.basename(file_path)
    name = os.path.splitext(filename)[0]
    output_path = os.path.join(output_dir, f"{name}.json")
    
    print(f"Processing {name}...")
    
    try:
        if file_path.lower().endswith('.blif'):
            circuit = parse_blif(file_path)
        else:
            circuit = parse_netlist(file_path)
            
        # Skip massive circuits to prevent hanging in Python simulator
        num_nodes = len(circuit.nodes)
        if num_nodes > 150:
            print(f"  -> Skipping {name}: Circuit too large for quick simulation ({num_nodes} nodes).")
            return None
            
        levelize(circuit)
        
        # Run initial fault simulation to populate baseline probabilities
        run_fault_simulation(circuit, num_patterns=50, seed=42)
        
        original_circuit = clone_circuit(circuit)
        
        # Run pipeline with reasonable defaults for batching (fewer patterns for speed if needed)
        result = run_implication_pipeline(
            circuit,
            Th1=0.3,
            Th2=0.4,
            gain_threshold=0.02,
            num_patterns=50,
            seed=42,
            use_indirect=False,
            verbose=False,
            verify_fig4=False,
        )
        
        export_graph_json(original_circuit, circuit, output_path)
        
        from src.reporting.area import compute_area, compute_area_overhead
        orig_area = compute_area(original_circuit)
        mod_area = compute_area(circuit)
        overhead = compute_area_overhead(orig_area, mod_area)
        
        def avg_pdet(circ):
            gates = [n for n in circ.nodes.values() if n.role not in ("PI", "CONST", "PO") and n.type not in ("PI", "WIRE")]
            if not gates: return 0
            return sum((n.Pdet_sa0 + n.Pdet_sa1) / 2 for n in gates) / len(gates)
            
        orig_pdet = avg_pdet(original_circuit)
        post_pdet = avg_pdet(circuit)
        fr_red = ((orig_pdet - post_pdet) / orig_pdet * 100) if orig_pdet > 0 else 0.0
        
        stats = {
            'name': name,
            'gates': len(original_circuit.get_gates()),
            'frw_added': result.get('implications_added', 0),
            'orig_fr': orig_pdet,
            'post_fr': post_pdet,
            'orig_rel': 1.0 - orig_pdet,
            'post_rel': 1.0 - post_pdet,
            'fr_red': fr_red,
            'overhead': overhead
        }
        return stats
    except Exception as e:
        print(f"Failed to process {name}: {e}", flush=True)
        return None

def main():
    benchmarks_dir = "benchmarks"
    output_dir = os.path.join("dashboard", "public", "benchmarks")
    os.makedirs(output_dir, exist_ok=True)
    
    # Also process examples if requested
    target_files = glob.glob(os.path.join(benchmarks_dir, "*.txt"))
    target_files += glob.glob(os.path.join(benchmarks_dir, "*.blif"))
    target_files += glob.glob(os.path.join("examples", "*.txt"))
    target_files += glob.glob(os.path.join("examples", "*.blif"))
    
    successful_benchmarks = []
    table_data = []
    
    for file_path in target_files:
        stats = process_benchmark(file_path, output_dir)
        if stats:
            successful_benchmarks.append(stats['name'])
            table_data.append(stats)
            
    # Write index.json
    index_path = os.path.join(output_dir, "index.json")
    with open(index_path, "w") as f:
        json.dump(successful_benchmarks, f, indent=2)
        
    print(f"\nBatch processing complete. Successfully exported {len(successful_benchmarks)} benchmarks.\n", flush=True)
    
    # Print Table 1 matching paper format
    print("=" * 100, flush=True)
    print(f"{'Table 1: Soft Error Reliability and Area Overhead Results':^100}", flush=True)
    print("=" * 100, flush=True)
    print(f"{'Circuit':<24} | {'Gates':<6} | {'# Imp':<6} | {'Init Rel (1F)':<13} | {'Post Rel (1F)':<13} | {'% Red (FR)':<11} | {'Area Ovhd':<10}", flush=True)
    print("-" * 100, flush=True)
    for row in table_data:
        init_rel = f"{row['orig_rel']*100:.2f}%"
        post_rel = f"{row['post_rel']*100:.2f}%"
        red = f"{row['fr_red']:.2f}%"
        ovhd = f"{row['overhead']:.2f}%"
        print(f"{row['name']:<24} | {row['gates']:<6} | {row['frw_added']:<6} | {init_rel:<13} | {post_rel:<13} | {red:<11} | {ovhd:<10}", flush=True)
    print("=" * 100, flush=True)

if __name__ == "__main__":
    main()
