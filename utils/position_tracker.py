from __future__ import annotations

import json
import logging
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, date, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

from config.settings import Settings, get_settings


LOGGER = logging.getLogger(__name__)


class InventoryClassification(str, Enum):
    FLAT = "FLAT"
    DIRECTIONAL_YES = "DIRECTIONAL_YES"
    DIRECTIONAL_NO = "DIRECTIONAL_NO"
    FULLY_HEDGED_ARB = "FULLY_HEDGED_ARB"
    PARTIALLY_HEDGED_ARB = "PARTIALLY_HEDGED_ARB"
    UNKNOWN_OR_MISMATCH = "UNKNOWN_OR_MISMATCH"


# ------------------------------------------------------------------
# Data classes
# ------------------------------------------------------------------

@dataclass
class Position:
    position_id: str
    symbol: str
    source: str           # "crypto" | "polymarket"
    side: str             # "BUY" | "SELL"
    entry_price: float
    entry_time: str       # ISO UTC
    size: float
    notional_size: float
    stop_loss: float
    take_profit: float
    order_id: str
    status: str = "open"  # open | closed | stopped_out | take_profit_hit
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    exit_price: float | None = None
    exit_time: str | None = None
    exit_reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PortfolioSummary:
    account_balance: float
    open_count: int
    total_exposure: float
    total_exposure_pct: float
    unrealized_pnl: float
    daily_realized_pnl: float
    daily_drawdown_pct: float
    peak_equity: float
    max_open_positions: int
    max_total_exposure: float
    max_daily_drawdown: float
    positions: list[Position] = field(default_factory=list)


@dataclass
class ReconciliationReport:
    classification: InventoryClassification
    block_new_trading: bool
    reason: str
    local_yes: float = 0.0
    local_no: float = 0.0
    clob_yes: float = 0.0
    clob_no: float = 0.0
    open_buy_orders: float = 0.0
    open_sell_orders: float = 0.0
    recent_filled_yes: float = 0.0
    recent_filled_no: float = 0.0
    local_positions: int = 0
    clob_positions: int = 0
    open_orders: int = 0
    mismatches: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(tz=UTC).isoformat().replace("+00:00", "Z"))


# ------------------------------------------------------------------
# Tracker
# ------------------------------------------------------------------

class PositionTracker:
    """Thread-safe tracker for open and closed positions.

    Responsibilities:
    - Enforce max open positions, max total exposure, daily drawdown.
    - Update unrealized PnL from live price ticks.
    - Auto-flag positions that hit stop-loss or take-profit.
    - Persist state to a JSON file so it survives restarts.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._lock = threading.Lock()
        self._positions: dict[str, Position] = {}
        self._daily_realized_pnl: float = 0.0
        self._peak_equity: float = self.settings.account_balance
        self._day_key: str = date.today().isoformat()

    # ------------------------------------------------------------------
    # Risk gate
    # ------------------------------------------------------------------

    def can_open(self, notional_size: float) -> tuple[bool, str]:
        """Return (True, '') if a new position can be opened, else (False, reason)."""
        with self._lock:
            open_positions = [p for p in self._positions.values() if p.status == "open"]

            if len(open_positions) >= self.settings.max_open_positions:
                return False, (
                    f"Max open positions reached ({len(open_positions)}/{self.settings.max_open_positions})."
                )

            current_exposure = sum(p.notional_size for p in open_positions)
            new_exposure = current_exposure + notional_size
            max_exposure = self.settings.account_balance * self.settings.max_total_exposure
            if new_exposure > max_exposure:
                return False, (
                    f"Total exposure would exceed limit: "
                    f"{new_exposure:.2f} > {max_exposure:.2f} "
                    f"({self.settings.max_total_exposure:.0%} of balance)."
                )

            current_equity = self.settings.account_balance + self._daily_realized_pnl
            drawdown = (self._peak_equity - current_equity) / self._peak_equity if self._peak_equity > 0 else 0.0
            if drawdown >= self.settings.max_daily_drawdown:
                return False, (
                    f"Daily drawdown limit hit: {drawdown:.2%} >= {self.settings.max_daily_drawdown:.2%}."
                )

            return True, ""

    # ------------------------------------------------------------------
    # Open / close
    # ------------------------------------------------------------------

    def open_position(
        self,
        symbol: str,
        source: str,
        side: str,
        entry_price: float,
        size: float,
        stop_loss: float,
        take_profit: float,
        order_id: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> Position:
        """Register a new open position and return it."""
        self._reset_day_if_needed()
        if source == "crypto" and side == "SELL" and stop_loss < entry_price < take_profit:
            stop_loss, take_profit = take_profit, stop_loss
        notional = size * entry_price
        position = Position(
            position_id=str(uuid.uuid4())[:8],
            symbol=symbol,
            source=source,
            side=side,
            entry_price=entry_price,
            entry_time=datetime.now(tz=UTC).isoformat().replace("+00:00", "Z"),
            size=size,
            notional_size=notional,
            stop_loss=stop_loss,
            take_profit=take_profit,
            order_id=order_id,
            status="open",
            metadata=metadata or {},
        )
        with self._lock:
            self._positions[position.position_id] = position
        LOGGER.info(
            "Position opened | id=%s symbol=%s side=%s price=%.4f size=%.6f notional=%.2f",
            position.position_id, symbol, side, entry_price, size, notional,
        )
        return position

    def close_position(
        self,
        position_id: str,
        exit_price: float,
        reason: str = "manual",
    ) -> Position | None:
        """Close a position and record realized PnL."""
        with self._lock:
            position = self._positions.get(position_id)
            if position is None or position.status != "open":
                LOGGER.warning("close_position: id=%s not found or already closed.", position_id)
                return None

            if position.source == "polymarket":
                realized = (exit_price - position.entry_price) * position.size
            elif position.side == "BUY":
                realized = (exit_price - position.entry_price) * position.size
            else:
                realized = (position.entry_price - exit_price) * position.size

            position.exit_price = exit_price
            position.exit_time = datetime.now(tz=UTC).isoformat().replace("+00:00", "Z")
            position.realized_pnl = round(realized, 6)
            position.unrealized_pnl = 0.0
            position.exit_reason = reason
            position.status = reason if reason in {"stopped_out", "take_profit_hit"} else "closed"

            self._daily_realized_pnl += realized
            current_equity = self.settings.account_balance + self._daily_realized_pnl
            if current_equity > self._peak_equity:
                self._peak_equity = current_equity

        LOGGER.info(
            "Position closed | id=%s symbol=%s realized_pnl=%.4f reason=%s",
            position_id, position.symbol, position.realized_pnl, reason,
        )
        return position

    # ------------------------------------------------------------------
    # Price update (called from realtime feed or polling)
    # ------------------------------------------------------------------

    def update_price(self, symbol: str, current_price: float) -> list[Position]:
        """Update unrealized PnL for all open positions matching symbol.

        Returns a list of positions that triggered stop-loss or take-profit.
        Caller is responsible for submitting the actual close orders.
        """
        triggered: list[Position] = []
        with self._lock:
            for position in self._positions.values():
                if position.status != "open" or position.symbol != symbol:
                    continue

                if position.side == "BUY":
                    position.unrealized_pnl = round(
                        (current_price - position.entry_price) * position.size, 6
                    )
                    hit_sl = current_price <= position.stop_loss
                    hit_tp = current_price >= position.take_profit
                else:
                    position.unrealized_pnl = round(
                        (position.entry_price - current_price) * position.size, 6
                    )
                    hit_sl = current_price >= position.stop_loss
                    hit_tp = current_price <= position.take_profit

                if hit_sl:
                    LOGGER.warning(
                        "Stop-loss triggered | id=%s symbol=%s price=%.4f sl=%.4f",
                        position.position_id, symbol, current_price, position.stop_loss,
                    )
                    triggered.append(position)
                elif hit_tp:
                    LOGGER.info(
                        "Take-profit triggered | id=%s symbol=%s price=%.4f tp=%.4f",
                        position.position_id, symbol, current_price, position.take_profit,
                    )
                    triggered.append(position)

        # Auto-close triggered positions
        for position in triggered:
            if position.side == "BUY":
                reason = "stopped_out" if current_price <= position.stop_loss else "take_profit_hit"
            else:
                reason = "stopped_out" if current_price >= position.stop_loss else "take_profit_hit"
            self.close_position(position.position_id, current_price, reason=reason)

        return triggered

    # ------------------------------------------------------------------
    # Binary Options (Polymarket)
    # ------------------------------------------------------------------

    def update_polymarket_unrealized(self, symbol: str, is_above_ptb: bool) -> None:
        """Update unrealized PnL for binary options by marking them at 0.95 or 0.05."""
        mark_price = 0.95 if is_above_ptb else 0.05
        with self._lock:
            for position in self._positions.values():
                if position.status != "open" or position.symbol != symbol:
                    continue

                if position.side == "BUY":
                    position.unrealized_pnl = round((mark_price - position.entry_price) * position.size, 6)
                else:
                    position.unrealized_pnl = round((0.95 - mark_price - position.entry_price) * position.size, 6)

    def settle_expired_binaries(self, symbol: str, is_above_ptb: bool) -> None:
        """Settle open binary positions at 1.0 or 0.0 based on outcome."""
        to_settle: list[Position] = []
        with self._lock:
            for position in self._positions.values():
                if position.status == "open" and position.symbol == symbol:
                    to_settle.append(position)
                    
        for position in to_settle:
            if position.side == "BUY":
                settlement_price = 1.0 if is_above_ptb else 0.0
            else:
                settlement_price = 0.0 if is_above_ptb else 1.0
                
            self.close_position(position.position_id, exit_price=settlement_price, reason="binary_settled")

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_stalled_positions(
        self,
        stall_seconds: int,
        current_prices: dict[str, float],
    ) -> list[Position]:
        """Return open BUY positions that are underwater and older than stall_seconds."""
        now = datetime.now(tz=UTC)
        threshold = timedelta(seconds=stall_seconds)
        stalled: list[Position] = []
        with self._lock:
            for pos in self._positions.values():
                if pos.status != "open" or pos.side != "BUY":
                    continue
                current_price = current_prices.get(pos.symbol)
                if current_price is None or current_price >= pos.entry_price:
                    continue
                try:
                    entry_dt = datetime.fromisoformat(pos.entry_time.replace("Z", "+00:00"))
                except ValueError:
                    continue
                if (now - entry_dt) > threshold:
                    stalled.append(pos)
        if stalled:
            LOGGER.warning("Stalled positions | count=%s threshold=%ss", len(stalled), stall_seconds)
        return stalled

    def open_positions(self) -> list[Position]:
        with self._lock:
            return [p for p in self._positions.values() if p.status == "open"]

    def closed_positions(self) -> list[Position]:
        with self._lock:
            return [p for p in self._positions.values() if p.status != "open"]

    def get_position(self, position_id: str) -> Position | None:
        with self._lock:
            return self._positions.get(position_id)

    # ------------------------------------------------------------------
    # Position reconciliation
    # ------------------------------------------------------------------

    def reconcile_inventory(
        self,
        *,
        polymarket_positions: list[dict[str, Any]] | None = None,
        open_orders: list[dict[str, Any]] | None = None,
        recently_filled_orders: list[dict[str, Any]] | None = None,
    ) -> ReconciliationReport:
        """Compare local tracker state with CLOB state and classify exposure.

        Live callers must pass real Polymarket positions and open orders. Paper
        mode may pass empty lists and rely on local tracker state.
        """
        local_positions = self.open_positions()
        clob_positions = polymarket_positions or []
        open_orders = open_orders or []
        recently_filled_orders = recently_filled_orders or []

        local_yes, local_no = self._sum_local_yes_no(local_positions)
        clob_yes, clob_no = self._sum_remote_yes_no(clob_positions)
        order_buy, order_sell = self._sum_open_order_exposure(open_orders)
        filled_yes, filled_no = self._sum_recent_fills(recently_filled_orders)

        mismatches: list[str] = []
        if clob_positions and local_positions:
            if abs(local_yes - clob_yes) > 1e-6:
                mismatches.append(f"local_yes={local_yes:.6f} clob_yes={clob_yes:.6f}")
            if abs(local_no - clob_no) > 1e-6:
                mismatches.append(f"local_no={local_no:.6f} clob_no={clob_no:.6f}")
        elif clob_positions and not local_positions:
            mismatches.append("clob_positions_without_local_tracker")
        elif local_positions and not clob_positions and not self.settings.paper_trading:
            mismatches.append("local_positions_without_clob_positions")

        total_yes = clob_yes if clob_positions or not self.settings.paper_trading else local_yes
        total_no = clob_no if clob_positions or not self.settings.paper_trading else local_no
        total_yes += filled_yes
        total_no += filled_no

        classification = self._classify_inventory(
            total_yes=total_yes,
            total_no=total_no,
            open_buy_orders=order_buy,
            open_sell_orders=order_sell,
            mismatches=mismatches,
        )
        block = classification in {
            InventoryClassification.PARTIALLY_HEDGED_ARB,
            InventoryClassification.UNKNOWN_OR_MISMATCH,
        }
        reason = self._reconciliation_reason(classification, mismatches, order_buy, order_sell)

        report = ReconciliationReport(
            classification=classification,
            block_new_trading=block,
            reason=reason,
            local_yes=local_yes,
            local_no=local_no,
            clob_yes=clob_yes,
            clob_no=clob_no,
            open_buy_orders=order_buy,
            open_sell_orders=order_sell,
            recent_filled_yes=filled_yes,
            recent_filled_no=filled_no,
            local_positions=len(local_positions),
            clob_positions=len(clob_positions),
            open_orders=len(open_orders),
            mismatches=mismatches,
        )

        level = logging.CRITICAL if block else logging.INFO
        LOGGER.log(
            level,
            "[RECONCILE] class=%s block=%s reason=%s local_yes=%.6f local_no=%.6f clob_yes=%.6f clob_no=%.6f open_buy=%.6f open_sell=%.6f",
            report.classification.value,
            report.block_new_trading,
            report.reason,
            report.local_yes,
            report.local_no,
            report.clob_yes,
            report.clob_no,
            report.open_buy_orders,
            report.open_sell_orders,
        )
        return report

    def summary(self) -> PortfolioSummary:
        self._reset_day_if_needed()
        with self._lock:
            open_pos = [p for p in self._positions.values() if p.status == "open"]
            total_exposure = sum(p.notional_size for p in open_pos)
            unrealized_pnl = sum(p.unrealized_pnl for p in open_pos)
            current_equity = self.settings.account_balance + self._daily_realized_pnl
            drawdown = (
                (self._peak_equity - current_equity) / self._peak_equity
                if self._peak_equity > 0 else 0.0
            )
            return PortfolioSummary(
                account_balance=self.settings.account_balance,
                open_count=len(open_pos),
                total_exposure=total_exposure,
                total_exposure_pct=total_exposure / self.settings.account_balance if self.settings.account_balance > 0 else 0.0,
                unrealized_pnl=unrealized_pnl,
                daily_realized_pnl=self._daily_realized_pnl,
                daily_drawdown_pct=drawdown,
                peak_equity=self._peak_equity,
                max_open_positions=self.settings.max_open_positions,
                max_total_exposure=self.settings.max_total_exposure,
                max_daily_drawdown=self.settings.max_daily_drawdown,
                positions=list(open_pos),
            )

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save_state(self, path: Path) -> None:
        """Persist all positions and daily stats to a JSON file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            payload = {
                "day_key": self._day_key,
                "daily_realized_pnl": self._daily_realized_pnl,
                "peak_equity": self._peak_equity,
                "positions": [asdict(p) for p in self._positions.values()],
            }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        LOGGER.debug("Position state saved to %s", path)

    def load_state(self, path: Path) -> None:
        """Load persisted positions and daily stats from a JSON file."""
        if not path.exists():
            LOGGER.info("No state file at %s — starting fresh.", path)
            return
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            saved_day = payload.get("day_key", "")
            today = date.today().isoformat()
            with self._lock:
                if saved_day == today:
                    self._daily_realized_pnl = float(payload.get("daily_realized_pnl", 0.0))
                    self._peak_equity = float(payload.get("peak_equity", self.settings.account_balance))
                else:
                    LOGGER.info("New trading day — resetting daily PnL and drawdown.")
                self._day_key = today
                positions = []
                for p in payload.get("positions", []):
                    p.setdefault("metadata", {})
                    positions.append(Position(**p))
                self._positions = {p.position_id: p for p in positions}
            LOGGER.info("Loaded %s positions from %s", len(self._positions), path)
        except Exception:
            LOGGER.exception("Failed to load position state from %s", path)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _reset_day_if_needed(self) -> None:
        today = date.today().isoformat()
        if today != self._day_key:
            LOGGER.info("New trading day %s — resetting daily PnL.", today)
            with self._lock:
                self._day_key = today
                self._daily_realized_pnl = 0.0
                self._peak_equity = max(
                    self._peak_equity,
                    self.settings.account_balance,
                )

    def _sum_local_yes_no(self, positions: list[Position]) -> tuple[float, float]:
        yes = 0.0
        no = 0.0
        for pos in positions:
            if pos.source != "polymarket":
                continue
            outcome = str((pos.metadata or {}).get("outcome", "")).upper()
            if not outcome:
                outcome = "YES" if pos.side == "BUY" else "NO"
            if outcome == "YES":
                yes += float(pos.size)
            elif outcome == "NO":
                no += float(pos.size)
        return yes, no

    def _sum_remote_yes_no(self, positions: list[dict[str, Any]]) -> tuple[float, float]:
        yes = 0.0
        no = 0.0
        for pos in positions:
            size = self._extract_size(pos)
            outcome = str(pos.get("outcome", pos.get("side", pos.get("name", "")))).upper()
            if outcome == "YES" or outcome.endswith("YES"):
                yes += size
            elif outcome == "NO" or outcome.endswith("NO"):
                no += size
            else:
                asset = str(pos.get("asset_id", pos.get("token_id", ""))).lower()
                if "yes" in asset:
                    yes += size
                elif "no" in asset:
                    no += size
        return yes, no

    def _sum_open_order_exposure(self, orders: list[dict[str, Any]]) -> tuple[float, float]:
        buys = 0.0
        sells = 0.0
        for order in orders:
            status = str(order.get("status", order.get("state", "open"))).lower()
            if status in {"cancelled", "canceled", "filled", "matched", "expired", "failed", "rejected"}:
                continue
            size = self._extract_remaining_size(order)
            side = str(order.get("side", "")).upper()
            if side == "BUY":
                buys += size
            elif side == "SELL":
                sells += size
        return buys, sells

    def _sum_recent_fills(self, orders: list[dict[str, Any]]) -> tuple[float, float]:
        yes = 0.0
        no = 0.0
        for order in orders:
            filled = self._extract_filled_size(order)
            if filled <= 0:
                continue
            outcome = str(order.get("outcome", "")).upper()
            if outcome == "YES":
                yes += filled
            elif outcome == "NO":
                no += filled
        return yes, no

    def _classify_inventory(
        self,
        *,
        total_yes: float,
        total_no: float,
        open_buy_orders: float,
        open_sell_orders: float,
        mismatches: list[str],
    ) -> InventoryClassification:
        eps = 1e-8
        if mismatches:
            return InventoryClassification.UNKNOWN_OR_MISMATCH
        if open_buy_orders > eps or open_sell_orders > eps:
            return InventoryClassification.UNKNOWN_OR_MISMATCH
        if total_yes <= eps and total_no <= eps:
            return InventoryClassification.FLAT
        if total_yes > eps and total_no <= eps:
            return InventoryClassification.DIRECTIONAL_YES
        if total_no > eps and total_yes <= eps:
            return InventoryClassification.DIRECTIONAL_NO
        if abs(total_yes - total_no) <= eps:
            return InventoryClassification.FULLY_HEDGED_ARB
        return InventoryClassification.PARTIALLY_HEDGED_ARB

    def _reconciliation_reason(
        self,
        classification: InventoryClassification,
        mismatches: list[str],
        open_buy_orders: float,
        open_sell_orders: float,
    ) -> str:
        if mismatches:
            return "; ".join(mismatches)
        if open_buy_orders > 0 or open_sell_orders > 0:
            return f"open_orders_present buy={open_buy_orders:.6f} sell={open_sell_orders:.6f}"
        return classification.value.lower()

    def _extract_size(self, payload: dict[str, Any]) -> float:
        for key in ("size", "balance", "amount", "quantity"):
            if key in payload:
                try:
                    return float(payload[key] or 0.0)
                except (TypeError, ValueError):
                    return 0.0
        return 0.0

    def _extract_remaining_size(self, payload: dict[str, Any]) -> float:
        for key in ("remaining_size", "remaining", "size_remaining"):
            if key in payload:
                try:
                    return float(payload[key] or 0.0)
                except (TypeError, ValueError):
                    return 0.0
        return self._extract_size(payload)

    def _extract_filled_size(self, payload: dict[str, Any]) -> float:
        for key in ("filled_size", "filled", "matched_size", "size_matched"):
            if key in payload:
                try:
                    return float(payload[key] or 0.0)
                except (TypeError, ValueError):
                    return 0.0
        return 0.0
