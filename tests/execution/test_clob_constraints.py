import pytest
from polymarket.execution.clob_constraints import validate_paper_order, DEFAULT_CRYPTO_5M_CONSTRAINTS, ClobConstraint

def test_dust_order_rejected():
    res = validate_paper_order(shares=0.196078, price=0.51)
    assert res["clob_size_valid"] is False
    assert res["execution_realism_status"] == "PAPER_ONLY_DUST_REJECTED"
    assert res["paper_reject_reason"] == "dust_unexecutable_min_order"

def test_15_shares_accepted():
    res = validate_paper_order(shares=15.0, price=0.50)
    assert res["clob_size_valid"] is True
    assert res["clob_tick_valid"] is True
    assert res["execution_realism_status"] == "LIVE_EXECUTABLE_EVIDENCE_SUPPORTED"

def test_tick_misalignment_rejected():
    # 0.505 doesn't align with 0.01 tick
    res = validate_paper_order(shares=15.0, price=0.505)
    assert res["clob_size_valid"] is True
    assert res["clob_tick_valid"] is False
    assert res["execution_realism_status"] == "PAPER_ONLY_TICK_REJECTED"
    assert res["paper_reject_reason"] == "tick_misaligned_rounding_required"

def test_unknown_constraints_do_not_classify_executable():
    # Let's say we pass a crazy large constraint
    huge_constraints = ClobConstraint(
        minimum_order_size_shares=1000.0,
        minimum_tick_size=0.10,
        constraint_source="test",
        constraint_scope="test_scope"
    )
    res = validate_paper_order(shares=15.0, price=0.50, constraints=huge_constraints)
    assert res["clob_size_valid"] is False
    assert res["clob_tick_valid"] is True
    assert res["execution_realism_status"] == "PAPER_ONLY_DUST_REJECTED"
