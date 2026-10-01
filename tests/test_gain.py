"""
Tests for Gain computation (Equations 1-3).

Deterministic oracle tests using paper's exact numbers — these tests
bypass simulation and feed in the paper's stated probabilities directly.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.implications.gain import update_detection_prob, compute_gain_simple


class TestEquation1:
    """Test detection probability update (Eq. 1)."""

    def test_basic_update(self):
        """G'_isa = G_isa × (1 - P_u) × PRP"""
        # With P_u = 0.5 and PRP = 1.0:
        # reduction = 0.8 * 0.5 * 1.0 = 0.4
        # G'_isa = 0.8 - 0.4 = 0.4
        new = update_detection_prob(0.8, 0.5, 1.0)
        assert abs(new - 0.4) < 0.001

    def test_zero_Pu(self):
        """If P_u = 0, no reduction."""
        new = update_detection_prob(0.8, 0.0, 1.0)
        assert abs(new - 0.8) < 0.001

    def test_zero_PRP(self):
        """If PRP = 0, no reduction."""
        new = update_detection_prob(0.8, 0.5, 0.0)
        assert abs(new - 0.8) < 0.001


class TestEquation3:
    """Test gain computation (Eq. 3) against paper's exact numbers."""

    def test_fig4_gain(self):
        """
        Paper Fig. 4 (§4, page 41):
        Before: {0.281, 0.563, 0.781, 0.781, 0.781}
        After:  {0.211, 0.422, 0.586, 0.586, 0.586}
        Expected gain: 0.796
        """
        old_probs = [0.281, 0.563, 0.781, 0.781, 0.781]
        new_probs = [0.211, 0.422, 0.586, 0.586, 0.586]

        gain = compute_gain_simple(None, old_probs, new_probs)

        assert abs(gain - 0.796) < 0.01, f"Fig 4 gain={gain}, expected ≈0.796"

    def test_fig5_gain(self):
        """
        Paper Fig. 5 (§4, page 41):
        Before: {0, 0, 0.563, 0.781, 0.781, 0.781}
        After:  {0, 0, 0.281, 0.391, 0.391, 0.391}
        Expected gain: 1.452
        """
        old_probs = [0, 0, 0.563, 0.781, 0.781, 0.781]
        new_probs = [0, 0, 0.281, 0.391, 0.391, 0.391]

        gain = compute_gain_simple(None, old_probs, new_probs)

        assert abs(gain - 1.452) < 0.01, f"Fig 5 gain={gain}, expected ≈1.452"

    def test_zero_gain(self):
        """No change in probabilities → zero gain."""
        probs = [0.5, 0.3, 0.7]
        gain = compute_gain_simple(None, probs, probs)
        assert gain == 0.0
