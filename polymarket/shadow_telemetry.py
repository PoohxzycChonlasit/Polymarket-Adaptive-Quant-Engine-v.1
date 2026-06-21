from typing import Any, Dict

FILTER_VERSION = "1.0.0"

def evaluate_shadow_filter(record: Dict[str, Any], filter_name: str) -> Dict[str, Any]:
    """
    Evaluates a single record against the named shadow filter.
    Maintains 100% parity with offline tools/shadow_filter_evaluator.py.
    """
    asset = record.get("asset")
    edge = record.get("edge")
    volatility_regime = record.get("volatility_regime")
    
    shadow_pass = True
    shadow_reject_reason = None
    params: Dict[str, Any] = {}
    
    if filter_name == "block_btc_shadow":
        params = {"target_asset": "BTC"}
        if asset == "BTC":
            shadow_pass = False
            shadow_reject_reason = "REJECT_BTC_ASSET"
            
    elif filter_name == "block_edge_lt_005_shadow":
        params = {"min_edge": 0.05}
        if edge is None:
            shadow_pass = False
            shadow_reject_reason = "MISSING_EDGE"
        elif edge < 0.05:
            shadow_pass = False
            shadow_reject_reason = "REJECT_EDGE_LT_005"
            
    elif filter_name == "block_normal_vol_shadow":
        params = {"target_regime": "NORMAL_VOL"}
        if volatility_regime is None:
            shadow_pass = False
            shadow_reject_reason = "MISSING_VOLATILITY_REGIME"
        elif volatility_regime == "NORMAL_VOL":
            shadow_pass = False
            shadow_reject_reason = "REJECT_NORMAL_VOL"
            
    elif filter_name == "combined_conservative_shadow":
        params = {"target_asset": "ETH", "min_edge": 0.05, "max_edge": 0.15}
        if asset != "ETH":
            shadow_pass = False
            shadow_reject_reason = "REJECT_NOT_ETH"
        elif edge is None:
            shadow_pass = False
            shadow_reject_reason = "MISSING_EDGE"
        elif edge < 0.05 or edge >= 0.15:
            shadow_pass = False
            shadow_reject_reason = "REJECT_EDGE_OUT_OF_BOUNDS"
            
    elif filter_name == "combined_broad_shadow":
        params = {"target_asset": "ETH", "min_edge": 0.05}
        if asset != "ETH":
            shadow_pass = False
            shadow_reject_reason = "REJECT_NOT_ETH"
        elif edge is None:
            shadow_pass = False
            shadow_reject_reason = "MISSING_EDGE"
        elif edge < 0.05:
            shadow_pass = False
            shadow_reject_reason = "REJECT_EDGE_LT_005"
    else:
        raise ValueError(f"Unknown shadow filter: {filter_name}")
        
    return {
        "filter_name": filter_name,
        "filter_version": FILTER_VERSION,
        "filter_params": params,
        "shadow_pass": shadow_pass,
        "shadow_reason": shadow_reject_reason,
        "would_trade": shadow_pass
    }
