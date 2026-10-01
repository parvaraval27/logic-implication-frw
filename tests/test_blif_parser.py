import pytest
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.blif_parser import parse_blif, _infer_gate_type
from src.core.netlist_graph import levelize

def test_infer_gate_type():
    # NOT
    assert _infer_gate_type(['a'], ['0'], '1') == 'NOT'
    assert _infer_gate_type(['a'], ['1'], '0') == 'NOT'
    
    # BUF
    assert _infer_gate_type(['a'], ['1'], '1') == 'BUF'
    assert _infer_gate_type(['a'], ['0'], '0') == 'BUF'
    
    # AND2
    assert _infer_gate_type(['a', 'b'], ['11'], '1') == 'AND'
    
    # OR2
    assert _infer_gate_type(['a', 'b'], ['1-', '-1'], '1') == 'OR'
    
    # NAND2
    assert _infer_gate_type(['a', 'b'], ['11'], '0') == 'NAND'
    
    # NOR2
    assert _infer_gate_type(['a', 'b'], ['1-', '-1'], '0') == 'NOR'
    
    # XOR
    assert _infer_gate_type(['a', 'b'], ['01', '10'], '1') == 'XOR'
    
    # XNOR
    assert _infer_gate_type(['a', 'b'], ['01', '10'], '0') == 'XNOR'
    
    # Complex (should return None)
    assert _infer_gate_type(['a', 'b', 'c'], ['11-', '-01'], '1') is None

def test_parse_c17_blif():
    # C17 benchmark is located in the LGSynth91 folder
    circuit = parse_blif('benchmarks/LGSynth91/blif/C17.blif')
    levelize(circuit)
    
    assert circuit.name == "C17.iscas"
    assert len(circuit.PIs) == 5
    assert len(circuit.POs) == 2
    
    gate_nodes = [n for n in circuit.nodes.values() if n.role not in ('PI', 'CONST')]
    assert len(gate_nodes) == 6
    assert all(g.type == 'NAND' for g in gate_nodes)
