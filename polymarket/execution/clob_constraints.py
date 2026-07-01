from dataclasses import dataclass
from typing import Dict, Any

@dataclass(slots=True)
class ClobConstraint:
    minimum_order_size_shares: float
    minimum_tick_size: float
    constraint_source: str
    constraint_scope: str

# Defaults from FRACTIONAL_SHARE_MIN_ORDER_CLOB_VALIDATION_001
DEFAULT_CRYPTO_5M_CONSTRAINTS = ClobConstraint(
    minimum_order_size_shares=15.0,
    minimum_tick_size=0.01,
    constraint_source="FRACTIONAL_SHARE_MIN_ORDER_CLOB_VALIDATION_001",
    constraint_scope="crypto_5m_current_validated_default"
)

def validate_paper_order(
    shares: float, 
    price: float, 
    constraints: ClobConstraint = DEFAULT_CRYPTO_5M_CONSTRAINTS
) -> Dict[str, Any]:
    """
    Validates a paper order against live CLOB constraints.
    Returns a dictionary of telemetry fields and validation results.
    """
    proposed_notional = shares * price
    minimum_executable_notional = constraints.minimum_order_size_shares * price
    
    clob_size_valid = shares >= constraints.minimum_order_size_shares
    
    # Tick size check: ensure price aligns to minimum_tick_size
    # Floating point math can be tricky, so use round to verify
    # e.g. 0.51 / 0.01 = 51.0 -> round(51.0) == 51
    # 0.515 / 0.01 = 51.5 -> round(51.5) == 52 != 51.5
    price_ticks = price / constraints.minimum_tick_size
    clob_tick_valid = abs(price_ticks - round(price_ticks)) < 1e-7
    
    if not clob_size_valid:
        status = "PAPER_ONLY_DUST_REJECTED"
        reject_reason = "dust_unexecutable_min_order"
    elif not clob_tick_valid:
        status = "PAPER_ONLY_TICK_REJECTED"
        reject_reason = "tick_misaligned_rounding_required"
    else:
        status = "LIVE_EXECUTABLE_EVIDENCE_SUPPORTED"
        reject_reason = None

    return {
        "constraint_source": constraints.constraint_source,
        "constraint_scope": constraints.constraint_scope,
        "clob_min_order_size_shares": constraints.minimum_order_size_shares,
        "clob_min_tick_size": constraints.minimum_tick_size,
        "proposed_shares": shares,
        "proposed_notional": proposed_notional,
        "minimum_executable_notional": minimum_executable_notional,
        "clob_size_valid": clob_size_valid,
        "clob_tick_valid": clob_tick_valid,
        "execution_realism_status": status,
        "paper_reject_reason": reject_reason,
    }
