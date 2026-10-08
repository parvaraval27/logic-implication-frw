"""
Pipeline driver — Algorithm 1 from the paper.

Orchestrates the complete implication-based fault tolerance flow:
  1. Fault simulation (P0/P1/Pdet)
  2. Candidate selection (Th1/Th2)
  3. Implication learning (direct FAN)
  4. For each implication: VP + IPI + gain
  5. Iterative FRW addition (best gain first, until gain < threshold)

Reference: Paper §3.2, Algorithm 1 (all 26 lines).
"""

from src.core.netlist_graph import (
    levelize, clone_circuit, reset_markings,
    count_paths, count_paths_to_any_po, compute_fanout_cone
)
from src.core.gate_lib import get_controlling_value
from src.faultsim.random_pattern_sim import run_fault_simulation
from src.implications.candidate_selection import select_sources, select_targets
from src.implications.direct_implication import learn_direct_implications
from src.implications.indirect_implication import learn_indirect_implications
from src.implications.value_propagation import mark_gates_vp
from src.implications.path_identification import identify_path
from src.implications.gain import compute_gain, update_detection_prob, compute_PRP
from src.implications.frw_addition import add_frw, _needs_inverter
from src.implications.direct_implication import Implication


def _find_masking_gate_target(implication):
    """
    Determine the effective target for VP/IPI.
    If the FRW will be added to the masking gate, the masking gate
    becomes the new target for path identification.
    """
    target = implication.target
    v = implication.v

    # Check if we should use masking gate as target
    if not target.fanouts:
        return target  # No masking gate, use target itself

    masking = target.fanouts[0] if target.fanouts else None
    if masking is None:
        return target

    fo_t = len(target.fanouts)

    if v == '1':
        # Algorithm 2: add to target if M=AND/NAND or FO>1 or no masking
        if masking.type in ("AND", "NAND") or fo_t > 1:
            return target
        return masking
    else:
        # Algorithm 3: add to target if M=OR/NOR or FO>1 or no masking
        if masking.type in ("OR", "NOR") or fo_t > 1:
            return target
        return masking


def _would_add_existing_wire(implication):
    """
    Check if adding an FRW for this implication would attempt to connect
    a wire that already directly exists in the circuit (direct or inverted).
    """
    source = implication.source
    u = implication.u
    needs_inv = _needs_inverter(u)

    dest = _find_masking_gate_target(implication)
    target = implication.target

    def already_has_input(gate):
        if gate is None:
            return False
        # Direct fanin check
        if source in gate.fanins:
            return True
        # Inverted fanin check (through NOT gate or parser _inv_ / INV_ naming)
        for fi in gate.fanins:
            if fi.type in ("NOT", "INV") and source in fi.fanins:
                return True
            if fi.name in (f"INV_{source.name}", f"_inv_{source.name}"):
                return True
        return False

    return already_has_input(dest) or already_has_input(target)


def evaluate_implication(circuit, implication):
    """
    Evaluate a single implication by running VP + IPI + gain.

    Sets implication.path_gates and implication.gain.
    Returns the gain value.
    """
    if _would_add_existing_wire(implication):
        implication.path_gates = []
        implication.gain = 0.0
        return 0.0

    source = implication.source
    u = implication.u
    target = implication.target

    # Determine effective target (masking gate or original target)
    effective_target = _find_masking_gate_target(implication)

    # Run VP (Algorithm 4)
    markings = mark_gates_vp(circuit, source, u, target)

    # Run IPI (Algorithm 5)
    path_gates = identify_path(circuit, source, target, markings)

    # Compute gain (Eq. 3)
    gain = compute_gain(circuit, path_gates, effective_target, source, u, markings)

    implication.path_gates = path_gates
    implication.gain = gain

    # Clean up markings for next implication
    reset_markings(circuit)

    return gain


def _update_detection_probs(circuit, implication, effective_target):
    """
    After adding an FRW, update detection probabilities for gates
    along the implication path (Eq. 1).
    """
    source = implication.source
    u = implication.u

    # P_u
    P_u = source.P0 if u == '0' else source.P1

    # Re-run VP to get markings using original target
    markings = mark_gates_vp(circuit, source, u, implication.target)

    for gate in implication.path_gates:
        marking = markings.get(gate.name)
        if marking is None:
            continue

        gate_val = marking[-1]  # '0' or '1'
        prp = compute_PRP(circuit, gate, effective_target)

        if gate_val == '0':
            gate.Pdet_sa1 = update_detection_prob(gate.Pdet_sa1, P_u, prp)
        else:
            gate.Pdet_sa0 = update_detection_prob(gate.Pdet_sa0, P_u, prp)

    reset_markings(circuit)


def run_implication_pipeline(circuit, Th1=0.3, Th2=0.4, gain_threshold=0.02,
                              num_patterns=10000, seed=42,
                              use_indirect=False, verbose=True, verify_fig4=False,
                              max_frws=None):
    """
    Main pipeline driver — Algorithm 1.

    Args:
        circuit: Circuit object (will be modified in-place)
        Th1: source gate probability threshold (default 0.3)
        Th2: target gate detection probability threshold (default 0.4)
        gain_threshold: minimum gain to continue adding FRWs (default 0.02)
        num_patterns: number of random patterns for simulation (default 10000)
        seed: random seed for reproducibility
        use_indirect: whether to use indirect implication learning
        verbose: print progress information
        max_frws: optional maximum number of FRWs to add

    Returns:
        dict with pipeline results
    """
    # Ensure circuit is levelized
    levelize(circuit)

    # Line 7: Simulate to get P0/P1 and Pdet
    if verbose:
        print("Phase 1: Running fault simulation...")
    run_fault_simulation(circuit, num_patterns, seed)

    # Line 8: Select source gates
    sources = select_sources(circuit, Th1)
    if verbose:
        print(f"Phase 2: Selected {len(sources)} source candidates (Th1={Th1})")

    # Line 9: Select target gates
    targets = select_targets(circuit, Th2)
    if verbose:
        print(f"Phase 3: Selected {len(targets)} target candidates (Th2={Th2})")

    if verify_fig4:
        if verbose:
            print("\n*** VERIFY FIG 4 MODE ACTIVE ***")
            print("Bypassing standard candidate selection and injecting (G4=0) => (G3=0)\n")
        
        node_g4 = circuit.nodes.get('G4')
        node_g3 = circuit.nodes.get('G3')
        if not node_g4 or not node_g3:
            print("Error: G4 or G3 not found in circuit. Is this fig4.txt?")
            return {}
        
        impl = Implication(node_g4, '0', node_g3, '0')
        implications = [impl]
        sources = [node_g4]
        targets = [node_g3]
    else:
        if not sources or not targets:
            if verbose:
                print("No source-target pairs found. Exiting.")
            return {
                'implications_added': 0,
                'frw_details': [],
                'sources': len(sources),
                'targets': len(targets),
            }

    # Line 10: Extract implications
    if not verify_fig4:
        if verbose:
            print("Phase 4: Learning direct implications...")
        implications = learn_direct_implications(circuit, sources, targets)
        if verbose:
            print(f"  Found {len(implications)} direct implications")

        if use_indirect:
            if verbose:
                print("Phase 4b: Learning indirect implications...")
            indirect = learn_indirect_implications(circuit, sources, targets)
            if verbose:
                print(f"  Found {len(indirect)} indirect implications")
            implications.extend(indirect)

        if not implications:
            if verbose:
                print("No implications found. Exiting.")
            return {
                'implications_added': 0,
                'frw_details': [],
                'sources': len(sources),
                'targets': len(targets),
            }

    # Lines 12-15: Evaluate each implication (VP + IPI + gain)
    if verbose:
        print(f"Phase 5: Evaluating {len(implications)} implications...")
    for impl in implications:
        evaluate_implication(circuit, impl)

    # Lines 17-26: Iterative FRW addition
    if verbose:
        print("Phase 6: Adding FRWs iteratively...")

    frw_details = []
    iteration = 0

    while True:
        # Line 19: Select implication with highest gain
        if not implications:
            break
        best = max(implications, key=lambda imp: imp.gain)

        # Line 20: Check gain threshold
        if best.gain < gain_threshold:
            if verbose:
                print(f"  Best gain {best.gain:.4f} < threshold {gain_threshold}. Stopping.")
            break

        iteration += 1
        if verbose:
            print(f"  Iteration {iteration}: Adding {best} (gain={best.gain:.4f})")

        effective_target = _find_masking_gate_target(best)

        # To avoid combinational loops, source must not be in transitive fanout of effective_target
        cone_fout = compute_fanout_cone(circuit, effective_target)
        if best.source in cone_fout:
            if verbose:
                print(f"  Skipping {best}: would create combinational loop.")
            implications.remove(best)
            continue

        if _would_add_existing_wire(best):
            if verbose:
                print(f"  Skipping {best}: wire already directly exists.")
            implications.remove(best)
            continue

        # Line 21: Add FRW
        frw_result = add_frw(circuit, best)
        frw_result['gain'] = best.gain
        frw_details.append(frw_result)

        if max_frws is not None and len(frw_details) >= max_frws:
            if verbose:
                print(f"  Reached max_frws limit of {max_frws}. Stopping.")
            break

        # Re-levelize after structural change
        levelize(circuit)

        # For verify_fig4, capture the estimated probabilities before and after
        if verify_fig4 and iteration == 1:
            gates_to_check = ['G6', 'G8', 'G1', 'G2', 'G3']
            print(f"\n--- FIG 4 VERIFICATION: ESTIMATED PROBABILITIES ---")
            
            # Print pre-FRW actuals (from first sim)
            print("Pre-FRW (Actual baseline):")
            for g in gates_to_check:
                node = circuit.nodes.get(g)
                if node:
                    fault_type = "sa1" if g == "G3" else "sa0"
                    prob = node.Pdet_sa1 if fault_type == "sa1" else node.Pdet_sa0
                    print(f"  {g}{fault_type}: {prob:.3f}")
                    
        # Line 22: Update detection probabilities
        _update_detection_probs(circuit, best, effective_target)
        
        if verify_fig4 and iteration == 1:
            print("\nPost-FRW (Equation 1 Estimated):")
            for g in gates_to_check:
                node = circuit.nodes.get(g)
                if node:
                    fault_type = "sa1" if g == "G3" else "sa0"
                    prob = node.Pdet_sa1 if fault_type == "sa1" else node.Pdet_sa0
                    print(f"  {g}{fault_type}: {prob:.3f}")
            
            print(f"\nEstimated Path Gain: {best.gain:.4f}")
            print("---------------------------------------------------\n")
            
            print(f"--- FIG 4 VERIFICATION: HOPE CROSS-VALIDATION ---")
            print("Re-running full fault simulation (HOPE equivalent) for actual values...")
            run_fault_simulation(circuit, num_patterns, seed)
            
            print("\nPost-FRW (Actual HOPE Simulated):")
            for g in gates_to_check:
                node = circuit.nodes.get(g)
                if node:
                    fault_type = "sa1" if g == "G3" else "sa0"
                    prob = node.Pdet_sa1 if fault_type == "sa1" else node.Pdet_sa0
                    print(f"  {g}{fault_type}: {prob:.3f}")
            print("---------------------------------------------------\n")

            # Force exit after 1 iteration for Fig 4 test
            break

        # Remove the used implication
        implications.remove(best)

        # Line 23: Update gains for remaining implications
        # Only re-evaluate implications whose path gates had their detection probabilities
        # modified, or whose source/target overlaps with the newly added wire.
        updated_gate_names = {g.name for g in best.path_gates}
        dest_name = effective_target.name if effective_target else best.target.name
        source_name = best.source.name

        for impl in implications:
            if (any(g.name in updated_gate_names for g in impl.path_gates) or
                impl.target.name == dest_name or
                impl.source.name == source_name):
                evaluate_implication(circuit, impl)

    if verbose:
        print(f"\nDone: Added {len(frw_details)} FRWs in {iteration} iterations.")

    return {
        'implications_added': len(frw_details),
        'frw_details': frw_details,
        'sources': len(sources),
        'targets': len(targets),
        'total_implications_found': len(frw_details) + len(implications),
    }
