#!/usr/bin/env python3
"""
Kalshi 15-Minute Round Tracker & Decision Engine.
Aligns predictions with Kalshi's fixed quarter-hour cycles (:00, :15, :30, :45),
tracks CF Benchmarks Real-Time Index (BRTI & RTIs) round open and current delta,
and generates actionable trading signals for the current and upcoming 5-17 minute rounds.
"""

import time
import math
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional

from .utils import setup_logging

logger = setup_logging("KalshiEngine")


def normal_cdf(x: float) -> float:
    """Standard normal cumulative distribution function approximation."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


class KalshiRoundTracker:
    """Manages round boundaries, round open strike, and probability calculations."""

    SERIES_MAP = {
        "btc": "KXBTC15M",
        "bnb": "KXBNB15M",
        "hype": "KXHYPE15M"
    }

    RTI_NAME_MAP = {
        "btc": "CME CF BRTI (Bitcoin RTI)",
        "bnb": "CF Benchmarks BNB RTI",
        "hype": "CF Benchmarks HYPE RTI"
    }

    def __init__(self, data_store, coin_id: str):
        self.data_store = data_store
        self.coin_id = coin_id.lower()
        self.series = self.SERIES_MAP.get(self.coin_id, f"KX{self.coin_id.upper()}15M")
        self.rti_name = self.RTI_NAME_MAP.get(self.coin_id, f"CFB {self.coin_id.upper()} RTI")
        self._analysis_cache: Optional[Dict[str, Any]] = None
        self._analysis_cache_time: float = 0.0

    def get_round_timing(self, now: Optional[datetime] = None) -> Dict[str, Any]:
        """Compute current and next 15-minute round timing aligned to :00, :15, :30, :45."""
        if now is None:
            now = datetime.now(timezone.utc)
        elif now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        # Current round
        minute_slot = (now.minute // 15) * 15
        round_start = now.replace(minute=minute_slot, second=0, microsecond=0)
        round_end = round_start + timedelta(minutes=15)

        elapsed_sec = max(0, int((now - round_start).total_seconds()))
        remaining_sec = max(0, int((round_end - now).total_seconds()))
        elapsed_min = elapsed_sec / 60.0
        remaining_min = remaining_sec / 60.0
        progress_pct = round(min(100.0, (elapsed_sec / 900.0) * 100.0), 1)

        # Next round (upcoming 15m cycle, 5-17 mins ahead)
        next_start = round_end
        next_end = next_start + timedelta(minutes=15)

        return {
            "current_round": {
                "start_time": round_start.isoformat(),
                "end_time": round_end.isoformat(),
                "label": f"{round_start.strftime('%H:%M')} – {round_end.strftime('%H:%M')} UTC",
                "elapsed_seconds": elapsed_sec,
                "remaining_seconds": remaining_sec,
                "elapsed_minutes": round(elapsed_min, 2),
                "remaining_minutes": round(remaining_min, 2),
                "progress_pct": progress_pct,
                "is_settlement_minute": remaining_sec <= 60
            },
            "next_round": {
                "start_time": next_start.isoformat(),
                "end_time": next_end.isoformat(),
                "label": f"{next_start.strftime('%H:%M')} – {next_end.strftime('%H:%M')} UTC",
                "starts_in_seconds": remaining_sec,
                "starts_in_minutes": round(remaining_min, 2)
            }
        }

    def get_round_open_price(self, round_start_iso: str) -> Optional[float]:
        """Find the RTI price at or nearest after the start of the 15m round."""
        try:
            # Query price at or immediately after round start (within 90s)
            res = self.data_store.price_at_or_after(round_start_iso, window_seconds=90)
            if res:
                return float(res[0])
            # Fallback to nearest before
            res_before = self.data_store.price_at_or_before(round_start_iso, window_seconds=90)
            if res_before:
                return float(res_before[0])
        except Exception as e:
            logger.warning(f"Error getting round open price: {e}")
        return None

    def analyze_round(self,
                      current_price: float,
                      predicted_returns: Dict[int, float],
                      classifier_probs: Dict[int, Dict[str, float]],
                      news_features: Optional[Dict[str, float]] = None,
                      now: Optional[datetime] = None) -> Dict[str, Any]:
        """Generate full Kalshi round analysis, probabilities, and actionable trading decision."""
        now_ts = time.time()
        if now is None and (now_ts - self._analysis_cache_time < 2.5) and self._analysis_cache is not None:
            return self._analysis_cache

        timing = self.get_round_timing(now)
        cur_rnd = timing["current_round"]
        next_rnd = timing["next_round"]

        round_open = self.get_round_open_price(cur_rnd["start_time"])
        if round_open is None or round_open <= 0:
            round_open = current_price

        # Current Delta inside active round
        delta_usd = current_price - round_open
        delta_pct = (delta_usd / round_open) * 100.0 if round_open > 0 else 0.0

        # News contribution
        news_sentiment = 0.0
        if news_features:
            news_sentiment = news_features.get("news_compound_signal", 0.0)

        # Baseline per-minute volatility estimate (approximate 0.08% for BTC, 0.12% for BNB, 0.18% for HYPE)
        base_vol_1m = {
            "btc": 0.0008,
            "bnb": 0.0012,
            "hype": 0.0018
        }.get(self.coin_id, 0.0010)

        rem_min = max(0.2, cur_rnd["remaining_minutes"])
        sigma_rem = base_vol_1m * math.sqrt(rem_min)

        # Model predicted return for the remaining span (interpolate between 5m, 10m, 15m)
        pred_15 = predicted_returns.get(15, 0.0)
        pred_10 = predicted_returns.get(10, 0.0)
        pred_5 = predicted_returns.get(5, 0.0)

        # Weight predictions by remaining time
        if rem_min <= 5:
            model_drift = pred_5 * (rem_min / 5.0)
        elif rem_min <= 10:
            weight_5 = (10 - rem_min) / 5.0
            model_drift = weight_5 * pred_5 + (1.0 - weight_5) * pred_10
        else:
            weight_10 = (15 - rem_min) / 5.0
            model_drift = weight_10 * pred_10 + (1.0 - weight_10) * pred_15

        # News drift impact over remaining span
        news_drift = (news_sentiment * 0.0015) * (rem_min / 15.0)

        # Total expected price change from NOW to settlement
        total_expected_return = model_drift + news_drift
        projected_settlement_price = current_price * (1.0 + total_expected_return)

        # Probability calculation: Dual-Phase Engine
        # Phase 1 (Mins 0 - 6.5): Prime Early Entry Window (Kalshi contracts 40c - 60c)
        # Phase 2 (Mins 6.5 - 15): Settlement Tracking & Lock-in (Distance from Strike)
        diff_from_open_pct = (projected_settlement_price - round_open) / round_open
        z_score = diff_from_open_pct / max(1e-5, sigma_rem)
        physics_prob = normal_cdf(z_score)

        # Binary normalization of classifier (removes ternary 'flat' dilution)
        clf_15 = classifier_probs.get(15, {})
        up_raw = clf_15.get('up', 0.33)
        down_raw = clf_15.get('down', 0.33)
        total_dir = up_raw + down_raw
        norm_clf_up = (up_raw / total_dir) if total_dir > 0.05 else 0.50

        elapsed_min = cur_rnd["elapsed_minutes"]
        is_entry_window = elapsed_min <= 6.5

        if is_entry_window:
            # EARLY ENTRY PHASE: Leading signals drive entry before price runs away
            news_boost = news_sentiment * 0.12  # News shock impact
            prob_up = 0.55 * norm_clf_up + 0.25 * (0.50 + news_boost) + 0.20 * physics_prob
            # Multi-horizon consensus boost
            if pred_5 > 0 and pred_10 > 0 and pred_15 > 0:
                prob_up += 0.04
            elif pred_5 < 0 and pred_10 < 0 and pred_15 < 0:
                prob_up -= 0.04
        else:
            # SETTLEMENT PHASE: Actual delta vs round open strike governs
            prob_up = 0.65 * physics_prob + 0.25 * norm_clf_up + 0.10 * (0.50 + news_sentiment * 0.10)

        prob_up = max(0.04, min(0.96, prob_up))
        prob_down = round(1.0 - prob_up, 4)
        prob_up = round(prob_up, 4)

        # Generate Actionable Kalshi Recommendation
        confidence = round(abs(prob_up - 0.50) * 200.0, 1)

        if is_entry_window:
            phase_label = "EARLY ENTRY WINDOW (Mins 0–6)"
            if prob_up >= 0.58:
                decision = "STRONG EARLY ENTRY: BUY YES"
                bias = "UP"
                color = "#10b981"
            elif prob_up >= 0.53:
                decision = "EARLY ENTRY: BUY YES"
                bias = "UP"
                color = "#34d399"
            elif prob_down >= 0.58:
                decision = "STRONG EARLY ENTRY: BUY NO"
                bias = "DOWN"
                color = "#ef4444"
            elif prob_down >= 0.53:
                decision = "EARLY ENTRY: BUY NO"
                bias = "DOWN"
                color = "#f87171"
            else:
                decision = "WAIT FOR BREAKOUT (ENTRY WINDOW)"
                bias = "NEUTRAL"
                color = "#f59e0b"
        else:
            phase_label = "SETTLEMENT PHASE (Mins 7–15)"
            if prob_up >= 0.68:
                decision = "SETTLEMENT CONFIRMED: HOLD YES"
                bias = "UP"
                color = "#10b981"
            elif prob_up >= 0.56:
                decision = "LEAN YES (EXPIRY TRACKING)"
                bias = "UP"
                color = "#34d399"
            elif prob_down >= 0.68:
                decision = "SETTLEMENT CONFIRMED: HOLD NO"
                bias = "DOWN"
                color = "#ef4444"
            elif prob_down >= 0.56:
                decision = "LEAN NO (EXPIRY TRACKING)"
                bias = "DOWN"
                color = "#f87171"
            else:
                decision = "VOLATILITY PINNED (HIGH RISK)"
                bias = "NEUTRAL"
                color = "#9ca3af"

        # Analysis of Next Upcoming Round (5-17 minute span)
        next_model_ret = pred_15
        next_news_impact = news_sentiment * 0.0020
        next_composite_ret = round((next_model_ret + next_news_impact) * 100.0, 4)

        if next_composite_ret > 0.06:
            next_bias = "BULLISH (UP)"
            next_action = "PREPARE BUY YES"
        elif next_composite_ret < -0.06:
            next_bias = "BEARISH (DOWN)"
            next_action = "PREPARE BUY NO"
        else:
            next_bias = "RANGE-BOUND"
            next_action = "WAIT FOR BREAKOUT"

        return {
            "series": self.series,
            "benchmark_index": self.rti_name,
            "timing": timing,
            "phase": {
                "label": phase_label,
                "is_entry_window": is_entry_window,
            },
            "pricing": {
                "current_price": round(current_price, 4),
                "round_open_price": round(round_open, 4),
                "delta_usd": round(delta_usd, 4),
                "delta_pct": round(delta_pct, 4),
                "projected_settlement": round(projected_settlement_price, 4),
            },
            "decision": {
                "recommendation": decision,
                "bias": bias,
                "phase_label": phase_label,
                "is_entry_window": is_entry_window,
                "confidence_pct": confidence,
                "badge_color": color,
                "prob_yes_up": prob_up,
                "prob_no_down": prob_down,
                "edge_pct": round(abs(prob_up - 0.50) * 100.0, 2),
                "model_drift_pct": round(model_drift * 100.0, 4),
                "news_drift_pct": round(news_drift * 100.0, 4),
            },
            "next_round_outlook": {
                "label": next_rnd["label"],
                "bias": next_bias,
                "suggested_action": next_action,
                "projected_change_pct": next_composite_ret,
                "starts_in_min": next_rnd["starts_in_minutes"]
            }
        }
        self._analysis_cache = result
        self._analysis_cache_time = time.time()
        return result
