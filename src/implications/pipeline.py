"""

Orchestrates the first half of the implication-based fault tolerance flow:
  1. Fault simulation (P0/P1/Pdet)
  2. Candidate selection (Th1/Th2)
  3. Implication learning (direct FAN)
  4. Path Tracing (Value Propagation + Path Identification)

Reference: Paper §3.2, Algorithm 1 (First half).
"""

from src.core.netlist_graph import levelize
from src.faultsim.random_pattern_sim import run_fault_simulation
from src.implications.candidate_selection import select_sources, select_targets
from src.implications.direct_implication import learn_direct_implications
from src.implications.value_propagation import mark_gates_vp
from src.implications.path_identification import identify_path

def run_implication_pipeline(circuit, Th1=0.3, Th2=0.4, num_patterns=10000, seed=42):
    """
    Demo Pipeline driver.
    """
    # Ensure circuit is levelized
    levelize(circuit)

    # Line 7: Simulate to get P0/P1 and Pdet
    print("\n--- 2. Baseline Fault Simulation (HOPE Equivalent) ---")
    print(f"Running fault simulation with {num_patterns} random patterns...")
    run_fault_simulation(circuit, num_patterns, seed)
    
    # Print a small table of gates for demo
    print(f"\n{'Gate':<10} | {'P0':<8} | {'P1':<8} | {'Pdet_sa0':<10} | {'Pdet_sa1':<10}")
    print("-" * 55)
    gates_to_show = [n for n in circuit.nodes.values() if n.type not in ("PI", "CONST")][:10]
    for g in gates_to_show:
        print(f"{g.name:<10} | {g.P0:<8.4f} | {g.P1:<8.4f} | {g.Pdet_sa0:<10.4f} | {g.Pdet_sa1:<10.4f}")

    print("\n--- 3. Candidate Selection ---")
    # Line 8: Select source gates
    sources = select_sources(circuit, Th1)
    print(f"Selected {len(sources)} source candidates (Th1={Th1}):")
    # sources is a list of (node, value)
    source_names = [f"{s[0].name}={s[1]}" for s in sources]
    print(f"  {', '.join(source_names[:15])}" + ("..." if len(sources) > 15 else ""))

    # Line 9: Select target gates
    targets = select_targets(circuit, Th2)
    print(f"\nSelected {len(targets)} target candidates (Th2={Th2}):")
    target_names = [t.name for t in targets]
    print(f"  {', '.join(target_names[:15])}" + ("..." if len(targets) > 15 else ""))

    if not sources or not targets:
        print("No source-target pairs found. Exiting.")
        return

    # Line 10: Extract implications
    print("\n--- 4. Direct Implication Extraction ---")
    print("Learning direct implications using FAN-style forward/backward propagation...")
    implications = learn_direct_implications(circuit, sources, targets)
    
    print(f"Found {len(implications)} direct implications. Here is a sample:")
    for i, impl in enumerate(implications[:10]):
        print(f"  {impl.source.name}={impl.u} => {impl.target.name}={impl.v}")
        
    if len(implications) > 10:
        print(f"  ... and {len(implications) - 10} more.")

    # Phase 5: Path Tracing
    print("\n--- 5. Tracing Implication Paths ---")
    print("Running Value Propagation (Algorithm 4) and Path Identification (Algorithm 5)...")
    
    # We will just trace paths for the first 5 implications to keep terminal output clean
    paths_traced = 0
    for impl in implications:
        if paths_traced >= 5:
            break
            
        print(f"\n* Analyzing Implication: {impl.source.name}={impl.u} => {impl.target.name}={impl.v}")
        
        # Run Value Propagation
        markings = mark_gates_vp(circuit, impl.source, impl.u, impl.target)
        
        # Run Path Identification
        path_gates = identify_path(circuit, impl.source, impl.target, markings)
        
        if path_gates:
            path_str = " -> ".join([g.name for g in path_gates])
            print(f"  - Path Found: {path_str}")
        else:
            print(f"  - No direct sensitization path found.")
        
        paths_traced += 1

    print("Circuit parsed, rules extracted, and physical sensitization paths successfully traced!")
    return
