from datetime import datetime, timezone
from typing import Any

def enrich_market_time_truth(payload: dict[str, Any], trader: Any) -> dict[str, Any]:
    """
    Enriches a payload with canonical market-time truth fields.
    Does NOT overwrite existing stronger fields.
    Sets unknown fields to None to satisfy schema presence checks.
    """
    now = datetime.now(timezone.utc)
    now_iso = now.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    
    # 1. Ensure basic emitted_at_utc is present
    payload.setdefault("emitted_at_utc", now_iso)
    
    # 2. Add local_receive_ts_utc and quote_capture_ts_utc using last successful book time
    # (per Source Provenance Rule)
    ticker = payload.get("ticker", "")
    if isinstance(ticker, str):
        ticker = ticker.upper()
    else:
        ticker = ""
        
    if ticker and trader is not None:
        try:
            last_book_ts = trader._last_successful_yes_no_book_at_utc.get(ticker)
            if last_book_ts:
                payload.setdefault("local_receive_ts_utc", last_book_ts)
                payload.setdefault("quote_capture_ts_utc", last_book_ts)
        except AttributeError:
            pass

    # 3. Explicitly set unknown/unsupported fields to None
    # to signify PRESENT_UNKNOWN to the canonical builder
    unknown_fields = [
        "source_orderbook_ts_utc",
        "chainlink_reference_ts_utc",
        "settlement_ts_utc",
        "decision_ts_utc",
        "order_submit_ts_utc",
        "order_ack_ts_utc",
        "fill_ts_utc",
        "close_ts_utc",
        "submit_latency_ms",
        "fill_latency_ms",
        "clock_drift_status",
    ]
    for field in unknown_fields:
        payload.setdefault(field, None)
        
    return payload
