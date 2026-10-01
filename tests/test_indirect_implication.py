import pytest
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.core.netlist_graph import parse_netlist, levelize
from src.implications.candidate_selection import select_targets
from src.implications.indirect_implication import learn_indirect_implications


@pytest.fixture
def fig5_circuit():
    circuit = parse_netlist("examples/fig5.txt")
    levelize(circuit)
    return circuit


def test_h0_implies_G3_0_fig5(fig5_circuit):
    """Test that h=0 indirectly implies G3=0 on Fig 5 (requires case split on G4)."""
    # Select h=0 as the only source
    sources = [(fig5_circuit.nodes['h'], '0')]
    targets = select_targets(fig5_circuit, 0.0) # all targets
    
    indirect = learn_indirect_implications(fig5_circuit, sources, targets, max_depth=2)
    
    # Check that h=0 => G3=0 was found
    found_g3 = False
    for imp in indirect:
        if imp.target.name == 'G3' and imp.v == '0':
            found_g3 = True
            break
            
    assert found_g3, "Failed to discover h=0 => G3=0 via recursive learning"


def test_no_duplicate_with_direct(fig5_circuit):
    """Test that indirect implication learner does not duplicate direct implications."""
    sources = [(fig5_circuit.nodes['h'], '0')]
    targets = select_targets(fig5_circuit, 0.0)
    
    indirect = learn_indirect_implications(fig5_circuit, sources, targets, max_depth=2)
    
    # h=0 => G5=1 is a direct implication, so it should NOT be in the indirect list
    found_g5 = any(imp.target.name == 'G5' for imp in indirect)
    assert not found_g5, "Indirect learner duplicated a direct implication"
