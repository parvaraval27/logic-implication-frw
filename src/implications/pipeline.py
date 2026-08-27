"""
Refer Paper section 3.2, Algorithm 1.
"""

from src.core.netlist_graph import levelize
from src.faultsim.random_pattern_sim import run_fault_simulation
from src.implications.candidate_selection import select_sources, select_targets

def run_implication_pipeline(circuit, Th1=0.3, Th2=0.4, num_patterns=10000, seed=42):
    # Ensure circuit is levelized
    levelize(circuit)

    # Line 7: Simulate to get P0/P1 and Pdet
    print("\n 2. Baseline Fault Simulation")
    print(f"Running fault simulation with {num_patterns} random patterns...")
    run_fault_simulation(circuit, num_patterns, seed)
    
    # Print a small table of gate statistics
    print(f"\n{'Gate':<10} | {'P0':<8} | {'P1':<8} | {'Pdet_sa0':<10} | {'Pdet_sa1':<10}")
    print("-" * 55)
    gates_to_show = [n for n in circuit.nodes.values() if n.type not in ("PI", "CONST")][:10]
    for g in gates_to_show:
        print(f"{g.name:<10} | {g.P0:<8.4f} | {g.P1:<8.4f} | {g.Pdet_sa0:<10.4f} | {g.Pdet_sa1:<10.4f}")

    print("\n 3. Candidate Selection ")
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
        print("No source-target candidate pairs found.")

    return
