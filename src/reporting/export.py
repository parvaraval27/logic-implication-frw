import json

def export_graph_json(circuit_baseline, circuit_post_frw, output_path):
    """
    Exports the circuit topologies and probability states (baseline vs post-FRW)
    into a JSON format suitable for the React Flow frontend.
    """
    
    nodes_data = []
    
    # 1. Gather all unique node names (assumes both circuits share most nodes)
    all_node_names = set(circuit_baseline.nodes.keys()).union(set(circuit_post_frw.nodes.keys()))
    
    for name in all_node_names:
        base_node = circuit_baseline.nodes.get(name)
        post_node = circuit_post_frw.nodes.get(name)
        
        # Use post_node as primary source for topology if it exists, otherwise base_node
        primary_node = post_node if post_node else base_node
        
        node_entry = {
            "id": name,
            "type": primary_node.type,
            "role": primary_node.role,
            "baseline": None,
            "post_frw": None
        }
        
        if base_node:
            node_entry["baseline"] = {
                "Pdet_sa0": base_node.Pdet_sa0,
                "Pdet_sa1": base_node.Pdet_sa1,
                "P0": base_node.P0,
                "P1": base_node.P1
            }
            
        if post_node:
            node_entry["post_frw"] = {
                "Pdet_sa0": post_node.Pdet_sa0,
                "Pdet_sa1": post_node.Pdet_sa1,
                "P0": post_node.P0,
                "P1": post_node.P1
            }
            
        nodes_data.append(node_entry)
        
    # 2. Extract Edges
    # First, get baseline edges
    baseline_edges = set()
    for name, node in circuit_baseline.nodes.items():
        for fout in node.fanouts:
            baseline_edges.add((name, fout.name))
            
    # Then, get post_frw edges
    post_frw_edges = set()
    for name, node in circuit_post_frw.nodes.items():
        for fout in node.fanouts:
            post_frw_edges.add((name, fout.name))
            
    edges_data = []
    
    # All edges present in baseline (is_frw = False)
    for src, tgt in baseline_edges:
        # Check if it was removed in post_frw (rare, but possible if replacing)
        is_removed = (src, tgt) not in post_frw_edges
        edges_data.append({
            "id": f"edge-{src}-{tgt}-base",
            "source": src,
            "target": tgt,
            "is_frw": False,
            "is_removed": is_removed
        })
        
    # Edges present ONLY in post_frw (is_frw = True)
    for src, tgt in post_frw_edges:
        if (src, tgt) not in baseline_edges:
            edges_data.append({
                "id": f"edge-{src}-{tgt}-frw",
                "source": src,
                "target": tgt,
                "is_frw": True,
                "is_removed": False
            })
            
    from src.reporting.area import compute_area, compute_area_overhead
    
    orig_area = compute_area(circuit_baseline)
    mod_area = compute_area(circuit_post_frw)
    overhead = compute_area_overhead(orig_area, mod_area)
    
    def avg_pdet(circuit):
        gates = [n for n in circuit.nodes.values() if n.role not in ("PI", "CONST", "PO") and n.type not in ("PI", "WIRE")]
        if not gates: return 0
        total_pdet = sum((n.Pdet_sa0 + n.Pdet_sa1) / 2 for n in gates)
        return total_pdet / len(gates)
        
    avg_pdet_base = avg_pdet(circuit_baseline)
    avg_pdet_post = avg_pdet(circuit_post_frw)
    
    # 3. Compute Metrics
    metrics = {
        "baseline": {
            "pi_count": len(circuit_baseline.PIs),
            "po_count": len(circuit_baseline.POs),
            "gate_count": len(circuit_baseline.get_gates()),
            "area": orig_area,
            "avg_pdet": avg_pdet_base
        },
        "post_frw": {
            "pi_count": len(circuit_post_frw.PIs),
            "po_count": len(circuit_post_frw.POs),
            "gate_count": len(circuit_post_frw.get_gates()),
            "frw_added": len([e for e in edges_data if e["is_frw"]]),
            "area": mod_area,
            "area_overhead": overhead,
            "avg_pdet": avg_pdet_post
        }
    }

    # 4. Assemble and save
    payload = {
        "metrics": metrics,
        "nodes": nodes_data,
        "edges": edges_data
    }

    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2)
        
    print(f"Graph JSON exported successfully to {output_path}")

