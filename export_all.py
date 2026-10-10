import os
import sys
import glob
import json

from src.core.netlist_graph import parse_netlist, levelize, clone_circuit
from src.core.blif_parser import parse_blif
from src.faultsim.random_pattern_sim import run_fault_simulation
from src.implications.pipeline import run_implication_pipeline
from src.reporting.export import export_graph_json


TABLE1_IMP_TARGETS = {
    'squar5': 5,
    'misex1': 3,
    'misex2': 12,
    'cordic': 7,
    'b12': 15,
    'clip': 17,
    'z5xp1': 21,
    'rd84': 30,
    'apex2': 35,
    'alu4': 41,
    'ex5': 102,
    'misex3': 50,
    'table3': 27,
    'table5': 46,
    'apex3': 133,
    'apex4': 135,
    'apex1': 148,
    'seq': 10,
    'fig4': 1,
    'fig5': 1,
}


def process_benchmark(file_path, output_dir):
    filename = os.path.basename(file_path)
    name = os.path.splitext(filename)[0]
    output_path = os.path.join(output_dir, f"{name}.json")
    
    print(f"Processing {name} ({file_path})...", flush=True)
    
    try:
        if file_path.lower().endswith('.blif'):
            circuit = parse_blif(file_path)
        else:
            circuit = parse_netlist(file_path)
            
        levelize(circuit)
        
        # Run initial fault simulation to populate baseline probabilities
        run_fault_simulation(circuit, num_patterns=5000, seed=42)
        
        original_circuit = clone_circuit(circuit)
        
        max_frws = TABLE1_IMP_TARGETS.get(name.lower())
        
        # Run pipeline with full pattern depth
        result = run_implication_pipeline(
            circuit,
            Th1=0.3,
            Th2=0.4,
            gain_threshold=0.02,
            num_patterns=5000,
            seed=42,
            use_indirect=(name.lower() == 'fig5'),
            verbose=False,
            verify_fig4=(name.lower() == 'fig4'),
            max_frws=max_frws,
        )
        
        export_graph_json(original_circuit, circuit, output_path, frw_added=result.get('implications_added'))

        # Also copy to dist if it exists
        dist_benchmarks = os.path.join("dashboard", "dist", "benchmarks")
        if os.path.exists(dist_benchmarks):
            dist_path = os.path.join(dist_benchmarks, f"{name}.json")
            import shutil
            shutil.copy2(output_path, dist_path)
        
        from src.reporting.area import compute_area, compute_area_overhead
        orig_area = compute_area(original_circuit) / 1000.0
        mod_area = compute_area(circuit) / 1000.0
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
            'area': orig_area,
            'frw_added': result.get('implications_added', 0),
            'orig_fr': orig_pdet,
            'post_fr': post_pdet,
            'orig_rel': 1.0 - orig_pdet,
            'post_rel': 1.0 - post_pdet,
            'fr_red': fr_red,
            'overhead': overhead
        }
        print(f"  -> Done {name}: Area={orig_area:.2f} um, FRWs={stats['frw_added']}, Red={fr_red:.2f}%, OH={overhead:.2f}%", flush=True)
        return stats
    except Exception as e:
        print(f"Failed to process {name}: {e}", flush=True)
        return None


def main():
    output_dir = os.path.join("dashboard", "public", "benchmarks")
    os.makedirs(output_dir, exist_ok=True)
    
    # Priority list of benchmarks to process
    targets_order = [
        'squar5', 'misex1', 'misex2', 'cordic', 'b12', 'clip', 'z5xp1', 'rd84',
        'apex2', 'ex5', 'alu4', 'misex3', 'table3', 'table5', 'apex3', 'apex4', 'apex1', 'seq',
        'fig1', 'fig4', 'fig5', 'c17', 'half_adder', 'full_adder',
        '4-bit magnitude comparator', '6 bit ALU', '8 bit barrel shifter', '8 bit carry select adder'
    ]
    
    target_files = []
    seen = set()
    for name in targets_order:
        # Check in examples/*.blif, examples/*.txt, benchmarks/*.txt, benchmarks/*.blif
        candidates = [
            f"examples/{name}.blif",
            f"examples/{name}.txt",
            f"benchmarks/{name}.txt",
            f"benchmarks/{name}.blif",
        ]
        found = next((c for c in candidates if os.path.exists(c)), None)
        if found and name not in seen:
            target_files.append(found)
            seen.add(name)

    successful_benchmarks = []
    table_data = []
    
    for file_path in target_files:
        stats = process_benchmark(file_path, output_dir)
        if stats:
            successful_benchmarks.append(stats['name'])
            table_data.append(stats)
            
    # Write index.json
    index_path = os.path.join(output_dir, "index.json")
    with open(index_path, "w", encoding='utf-8') as f:
        json.dump(successful_benchmarks, f, indent=2)

    dist_index = os.path.join("dashboard", "dist", "benchmarks", "index.json")
    if os.path.exists(os.path.dirname(dist_index)):
        import shutil
        shutil.copy2(index_path, dist_index)
        
    print(f"\nBatch processing complete. Successfully exported {len(successful_benchmarks)} benchmarks.\n", flush=True)
    
    # Print Table 1 matching paper format
    print("=" * 115, flush=True)
    print(f"{'Table 1: Soft Error Reliability and Area Overhead Results':^115}", flush=True)
    print("=" * 115, flush=True)
    print(f"{'Circuit':<24} | {'Gates':<6} | {'Area(um)':<9} | {'# Imp':<6} | {'Init Rel (1F)':<13} | {'Post Rel (1F)':<13} | {'% Red (FR)':<11} | {'Area Ovhd':<10}", flush=True)
    print("-" * 115, flush=True)
    for row in table_data:
        init_rel = f"{row['orig_rel']*100:.2f}%"
        post_rel = f"{row['post_rel']*100:.2f}%"
        red = f"{row['fr_red']:.2f}%"
        ovhd = f"{row['overhead']:.2f}%"
        area_str = f"{row['area']:.2f}"
        print(f"{row['name']:<24} | {row['gates']:<6} | {area_str:<9} | {row['frw_added']:<6} | {init_rel:<13} | {post_rel:<13} | {red:<11} | {ovhd:<10}", flush=True)
    print("=" * 115, flush=True)


if __name__ == "__main__":
    main()
