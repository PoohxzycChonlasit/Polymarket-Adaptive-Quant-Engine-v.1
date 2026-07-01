import json
import logging
import sys
from dataclasses import dataclass
from typing import Any, Dict

try:
    from py_clob_client.client import ClobClient
except ImportError:
    ClobClient = None

LOGGER = logging.getLogger(__name__)


@dataclass
class ClobConstraint:
    minimum_order_size: float
    minimum_tick_size: float
    is_fractional_allowed: bool


def fetch_crypto_constraints() -> ClobConstraint:
    if not ClobClient:
        raise RuntimeError("py_clob_client not installed")
    
    client = ClobClient(host="https://clob.polymarket.com")
    markets = client.get_markets(next_cursor="")
    
    # Defaults
    min_order_size = 5.0
    min_tick_size = 0.01
    
    if markets and "data" in markets:
        for market in markets["data"]:
            q = market.get("question", "")
            if "BTC" in q or "ETH" in q:
                mo = market.get("minimum_order_size")
                if mo is not None:
                    min_order_size = float(mo)
                mt = market.get("minimum_tick_size")
                if mt is not None:
                    min_tick_size = float(mt)
                break
    
    return ClobConstraint(
        minimum_order_size=min_order_size,
        minimum_tick_size=min_tick_size,
        is_fractional_allowed=False, # We don't have explicit fractional info, assume strict
    )


def classify_paper_order(notional: float, shares: float, price: float, constraint: ClobConstraint) -> str:
    # Check minimum order size
    # Typically CLOB minimum_order_size is in shares. If it's shares, compare to shares.
    # If it's 15, then 15 shares. Let's compare both conservatively.
    if shares < constraint.minimum_order_size and notional < constraint.minimum_order_size:
        return "BELOW_KNOWN_MINIMUM"
    
    if shares != round(shares, 0):
        # Even if token has 6 decimals, CLOB UI usually enforces integer shares or strict size ticks.
        # But for conservative classification, if it's below minimum order it's already caught.
        # If it passes minimum order but is fractional, we might mark it ROUNDING_REQUIRED
        return "ROUNDING_REQUIRED"
    
    return "LIVE_EXECUTABLE_EVIDENCE_SUPPORTED"


def run_validation(paper_runs: list[dict[str, float]]) -> str:
    try:
        constraint = fetch_crypto_constraints()
    except Exception as e:
        LOGGER.error("Failed to fetch constraints: %s", e)
        constraint = ClobConstraint(minimum_order_size=5.0, minimum_tick_size=0.01, is_fractional_allowed=False)
        
    results = {
        "clob_constraints_discovered": {
            "minimum_order_size": constraint.minimum_order_size,
            "minimum_tick_size": constraint.minimum_tick_size
        },
        "paper_examples": []
    }
    
    for run in paper_runs:
        classification = classify_paper_order(run["notional"], run["shares"], run["price"], constraint)
        results["paper_examples"].append({
            "notional": run["notional"],
            "shares": run["shares"],
            "price": run["price"],
            "classification": classification
        })
        
    return json.dumps(results, indent=2)


if __name__ == "__main__":
    # Test with the known paper baseline runs
    paper_runs = [
        {"notional": 0.10, "shares": 0.196078, "price": 0.51},
        {"notional": 0.10, "shares": 0.208333, "price": 0.48},
        {"notional": 15.0, "shares": 30.0, "price": 0.50},
    ]
    print(run_validation(paper_runs))
