import pytest
from tools.clob_min_order_validation import ClobConstraint, classify_paper_order

def test_classify_paper_order_below_minimum():
    constraint = ClobConstraint(minimum_order_size=15.0, minimum_tick_size=0.01, is_fractional_allowed=False)
    
    # Notional and shares are both below minimum
    res = classify_paper_order(notional=0.10, shares=0.196, price=0.51, constraint=constraint)
    assert res == "BELOW_KNOWN_MINIMUM"
    
def test_classify_paper_order_rounding_required():
    constraint = ClobConstraint(minimum_order_size=15.0, minimum_tick_size=0.01, is_fractional_allowed=False)
    
    # Passes minimum size, but has fractional shares
    res = classify_paper_order(notional=15.5, shares=31.5, price=0.50, constraint=constraint)
    assert res == "ROUNDING_REQUIRED"
    
def test_classify_paper_order_executable():
    constraint = ClobConstraint(minimum_order_size=15.0, minimum_tick_size=0.01, is_fractional_allowed=False)
    
    # Passes minimum size, integer shares
    res = classify_paper_order(notional=15.0, shares=30.0, price=0.50, constraint=constraint)
    assert res == "LIVE_EXECUTABLE_EVIDENCE_SUPPORTED"
