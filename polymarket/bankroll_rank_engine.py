from __future__ import annotations

import logging
import math
from typing import Any, Sequence
from polymarket.bankroll_tiers import BankrollTier, get_bankroll_tier, get_tier_config

LOGGER = logging.getLogger(__name__)

class CapitalState:
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    CRITICAL = "CRITICAL"

class RiskProfile:
    CONSERVATIVE = "CONSERVATIVE"
    MODERATE = "MODERATE"
    AGGRESSIVE = "AGGRESSIVE"

class BankrollRankEngine:
    """
    Enterprise-grade Bankroll Rank engine that continuously evaluates capital quality
    using runtime performance metrics, streaks, volatility, and recovery factors
    instead of static bankroll thresholds alone.
    """

    def __init__(
        self,
        alpha: float = 0.15,
        buffer_score: float = 0.05,
    ) -> None:
        self.alpha = alpha
        self.buffer_score = buffer_score
        
        # Stateful tracking
        self.smoothed_score: float = 1.0
        self.current_state: str = CapitalState.HEALTHY
        self.last_balance_series: list[float] = []
        self.max_history_len = 50

    def evaluate(
        self,
        *,
        current_bankroll: float,
        equity: float,
        realized_pnl: float,
        unrealized_pnl: float,
        drawdown_pct: float,
        closed_positions: Sequence[Any],
        risk_mode: str = "NORMAL",
        daily_pnl: float = 0.0,
    ) -> dict[str, Any]:
        """
        Evaluate capital quality metrics and compute smoothed transitions.
        """
        # 1. Update balance history for volatility calculation
        self.last_balance_series.append(equity)
        if len(self.last_balance_series) > self.max_history_len:
            self.last_balance_series.pop(0)

        # 2. Compute consecutive wins/losses from closed positions
        consecutive_wins = 0
        consecutive_losses = 0
        
        sorted_positions = sorted(
            [p for p in closed_positions if getattr(p, "exit_time", None)],
            key=lambda x: str(x.exit_time)
        )
        
        # Calculate streaks
        for pos in reversed(sorted_positions):
            pnl = getattr(pos, "realized_pnl", 0.0) or 0.0
            if pnl > 0:
                if consecutive_losses > 0:
                    break
                consecutive_wins += 1
            elif pnl < 0:
                if consecutive_wins > 0:
                    break
                consecutive_losses += 1

        # 3. Calculate recovery factor
        # Recovery Factor = Realized PnL / Max Drawdown (dollars)
        peak_val = max(self.last_balance_series) if self.last_balance_series else equity
        max_drawdown_usd = max(peak_val - equity, 0.0)
        
        if max_drawdown_usd > 0.01:
            # Shift realized pnl to be positive for the ratio if needed
            recovery_factor = max(realized_pnl, 0.0) / max_drawdown_usd
        else:
            recovery_factor = 10.0  # safe default high recovery factor when drawdown is negligible

        # 4. Calculate volatility of equity curve
        if len(self.last_balance_series) >= 5:
            mean = sum(self.last_balance_series) / len(self.last_balance_series)
            variance = sum((x - mean) ** 2 for x in self.last_balance_series) / (len(self.last_balance_series) - 1)
            volatility = math.sqrt(variance)
        else:
            volatility = 0.0

        # 5. Compute Capital Score (0.0 to 1.0)
        # Base score is 1.0, reduced by drawdown, streaks, and risk mode
        raw_score = 1.0
        
        # Drawdown penalty: linearly scale down to 0 if drawdown exceeds 15%
        raw_score -= min(drawdown_pct / 0.15, 0.5)
        
        # Consecutive loss penalty
        if consecutive_losses >= 3:
            raw_score -= min((consecutive_losses - 2) * 0.1, 0.3)
            
        # Volatility penalty if high relative to capital
        if equity > 0:
            vol_ratio = volatility / equity
            if vol_ratio > 0.02:
                raw_score -= min((vol_ratio - 0.02) * 2.0, 0.2)
                
        # Risk mode penalty
        if "SURVIVAL" in str(risk_mode).upper() or "LOCKDOWN" in str(risk_mode).upper():
            raw_score -= 0.3
            
        raw_score = max(0.0, min(1.0, raw_score))

        # 6. Apply smoothing (hysteresis) to Capital Score
        self.smoothed_score = self.alpha * raw_score + (1 - self.alpha) * self.smoothed_score

        # 7. Stateful transition logic with hysteresis buffers
        prev_state = self.current_state
        if self.current_state == CapitalState.HEALTHY:
            if self.smoothed_score < 0.40:
                self.current_state = CapitalState.CRITICAL
            elif self.smoothed_score < 0.65:
                self.current_state = CapitalState.DEGRADED
        elif self.current_state == CapitalState.DEGRADED:
            if self.smoothed_score >= 0.70:  # must clear 0.65 + buffer to promote back to healthy
                self.current_state = CapitalState.HEALTHY
            elif self.smoothed_score < 0.35:
                self.current_state = CapitalState.CRITICAL
        elif self.current_state == CapitalState.CRITICAL:
            if self.smoothed_score >= 0.45:  # must clear 0.40 + buffer to promote to degraded
                self.current_state = CapitalState.DEGRADED
            if self.smoothed_score >= 0.75:  # massive recovery jump straight to healthy
                self.current_state = CapitalState.HEALTHY

        # 8. Promotion/Demotion evaluation
        raw_tier = get_bankroll_tier(equity)
        tier_config = get_tier_config(raw_tier)
        
        promotion_candidate = (
            equity >= tier_config.upper_bound 
            and self.current_state == CapitalState.HEALTHY 
            and consecutive_losses == 0
        )
        
        demotion_candidate = (
            equity < tier_config.lower_bound 
            or self.current_state == CapitalState.CRITICAL
        )

        # 9. Expected Risk Profile
        if self.current_state == CapitalState.CRITICAL:
            expected_risk_profile = RiskProfile.CONSERVATIVE
        elif self.current_state == CapitalState.DEGRADED or consecutive_losses >= 2:
            expected_risk_profile = RiskProfile.MODERATE
        else:
            expected_risk_profile = RiskProfile.AGGRESSIVE

        return {
            "bankroll_rank": raw_tier.value,
            "bankroll_family": tier_config.family,
            "capital_score": round(self.smoothed_score, 4),
            "capital_state": self.current_state,
            "promotion_candidate": promotion_candidate,
            "demotion_candidate": demotion_candidate,
            "expected_risk_profile": expected_risk_profile,
            "metrics": {
                "consecutive_wins": consecutive_wins,
                "consecutive_losses": consecutive_losses,
                "recovery_factor": round(recovery_factor, 4),
                "volatility": round(volatility, 4),
                "raw_score": round(raw_score, 4),
            }
        }
