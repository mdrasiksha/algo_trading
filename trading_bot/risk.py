"""Risk checks for paper and live option-selling workflows."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RiskLimits:
    max_daily_loss: float
    max_lots: int = 1
    stop_loss_multiplier: float = 1.6
    target_multiplier: float = 0.5


def calculate_quantity(lot_size: int, lots: int, limits: RiskLimits) -> int:
    """Calculate order quantity after enforcing lot limits."""

    if lots < 1:
        raise ValueError("lots must be at least 1")
    if lots > limits.max_lots:
        raise ValueError(f"Requested lots {lots} exceeds max lots {limits.max_lots}")
    return lot_size * lots


def combined_stop_loss(ce_price: float, pe_price: float, limits: RiskLimits) -> float:
    """Combined premium stop-loss threshold for a short straddle."""

    return (ce_price + pe_price) * limits.stop_loss_multiplier


def combined_target(ce_price: float, pe_price: float, limits: RiskLimits) -> float:
    """Combined premium profit target threshold for a short straddle."""

    return (ce_price + pe_price) * limits.target_multiplier


def ensure_daily_loss_not_breached(realized_pnl: float, limits: RiskLimits) -> None:
    """Block new trades once realized loss reaches the daily loss limit."""

    if limits.max_daily_loss > 0 and realized_pnl <= -abs(limits.max_daily_loss):
        raise RuntimeError(
            f"Daily loss limit breached: realized P&L {realized_pnl}, "
            f"limit -{abs(limits.max_daily_loss)}"
        )
