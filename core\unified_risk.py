"""
💰 unified_risk.py — محرك إدارة المخاطر المتقدم
يدمج منهجية Risk Engine من CLOUD + صياغة Money Management من GPT/KIMI/QWEN
"""
import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta

import config_unified as config

logger = logging.getLogger("unified_risk")


@dataclass
class RiskParams:
    """معايير المخاطرة للصفقة الواحدة"""
    account_equity: float = 100.0
    risk_percent: float = 0.01  # 1%
    leverage: float = 3.0
    mode: str = "swing"
    spread: float = 0.0
    estimated_slippage: float = 0.0
    funding_cost_expected: float = 0.0


@dataclass
class PositionSize:
    """حجم الصفقة المحسوب"""
    risk_amount: float
    position_notional: float
    required_margin: float
    quantity: float
    fees_entry: float
    fees_exit: float
    total_fees: float
    net_risk: float
    rr_ratio: float
    is_valid: bool
    warnings: list = field(default_factory=list)


class UnifiedRiskEngine:
    """
    محرك إدارة المخاطر الموحد — يحسب حجم الصفقة وفق المعادلة:
    
    Account Equity → Risk % → Risk Amount → Stop Distance → Position Notional → Leverage → Required Margin
    """

    # رسوم التداول الافتراضية (من KIMI)
    FEE_RATES = {
        ("scalping", "futures"): 0.0008,  # 0.08%
        ("day", "futures"): 0.0006,       # 0.06%
        ("swing", "futures"): 0.0005,     # 0.05%
        ("position_futures", "futures"): 0.0006,  # 0.06%
        ("position_spot", "spot"): 0.001, # 0.1%
        ("news", "futures"): 0.0008,      # 0.08%
    }

    def __init__(self, mode: str = "swing"):
        self.mode = mode
        market_type = "futures" if mode != "position_spot" else "spot"
        self.fee_rate = self.FEE_RATES.get((mode, market_type), 0.0005)
        logger.info(f"💰 تم تهيئة RiskEngine للوضع: {mode}، سعر الرسوم: {self.fee_rate*100}%")

    def calculate_position_size(
        self,
        entry_price: float,
        sl_price: float,
        tp_price: float,
        params: RiskParams
    ) -> PositionSize:
        """
        حساب حجم الصفقة والمخاطرة الكاملة
        
        المعادلة الأساسية:
        Risk Amount = Account Equity × Risk %
        Position Notional = Risk Amount ÷ Stop Distance %
        Required Margin = Position Notional ÷ Leverage
        """
        risk_amount = params.account_equity * params.risk_percent
        stop_distance = abs(entry_price - sl_price) / entry_price
        if stop_distance == 0:
            stop_distance = 0.01  # fallback

        position_notional = risk_amount / stop_distance
        required_margin = position_notional / params.leverage if params.leverage > 0 else position_notional
        quantity = position_notional / entry_price

        # حساب الرسوم
        fees_entry = position_notional * self.fee_rate
        fees_exit = position_notional * self.fee_rate
        total_fees = fees_entry + fees_exit

        # R:R
        tp_distance = abs(tp_price - entry_price) / entry_price
        rr_ratio = tp_distance / stop_distance if stop_distance > 0 else 0

        # Net Risk (مع مراعاة الرسوم والسحب)
        gross_profit = position_notional * tp_distance
        net_profit = gross_profit - total_fees - (params.estimated_slippage * position_notional)
        net_risk = risk_amount + total_fees + (params.estimated_slippage * position_notional)

        # فحص الصلاحية
        warnings = []
        is_valid = True

        # 1. هل الهامض كافٍ؟
        if params.mode == "news":
            max_margin = params.account_equity * 0.85  # لا تستهلك أكثر من 85%
        else:
            max_margin = params.account_equity * 0.5  # 50% كحد أقصى
        
        if required_margin > max_margin:
            is_valid = False
            warnings.append(f"الهامض المطلوب ({required_margin:.2f}$) يتجاوز الحد الأقصى ({max_margin:.2f}$)")

        # 2. R:R الأدنى
        min_rr = config.MIN_RR.get(params.mode, 2.5)
        if rr_ratio < min_rr:
            warnings.append(f"R:R {rr_ratio:.2f} أقل من الحد الأدنى {min_rr}")
            # لا نرفض إذا كان الـScore العالي جدًا

        # 3. Funding Cost
        if params.funding_cost_expected > config.MAX_EXPECTED_FUNDING_COST:
            is_valid = False
            warnings.append(f"Expected Funding Cost {params.funding_cost_expected*100:.1f}% > {config.MAX_EXPECTED_FUNDING_COST*100:.0f}%")

        # 4. Fees تأكل الربح
        if total_fees > risk_amount * 2 and params.mode not in ("position_spot",):
            warnings.append(f"الرسوم ({total_fees:.3f}$) تتجاوز 200% من المخاطرة ({risk_amount:.3f}$)")

        return PositionSize(
            risk_amount=risk_amount,
            position_notional=position_notional,
            required_margin=required_margin,
            quantity=quantity,
            fees_entry=fees_entry,
            fees_exit=fees_exit,
            total_fees=total_fees,
            net_risk=net_risk,
            rr_ratio=rr_ratio,
            is_valid=is_valid,
            warnings=warnings
        )

    def calculate_dca_levels(self, capital: float, current_price: float) -> list:
        """
        حساب مستويات DCA للـPosition Trading (Spot)
        من KIMI/QWEN: 4 مستويات
        """
        levels = [
            {"level": 1, "allocation_pct": 0.20, "price_offset_pct": 0.0},
            {"level": 2, "allocation_pct": 0.20, "price_offset_pct": -0.05},
            {"level": 3, "allocation_pct": 0.25, "price_offset_pct": -0.10},
            {"level": 4, "allocation_pct": 0.35, "price_offset_pct": -0.15},
        ]

        result = []
        total_btc = 0
        total_spent = 0

        for lvl in levels:
            allocation = capital * lvl["allocation_pct"]
            price = current_price * (1 + lvl["price_offset_pct"])
            btc_amount = allocation / price
            total_btc += btc_amount
            total_spent += allocation
            avg_price = total_spent / total_btc if total_btc > 0 else price

            result.append({
                "level": lvl["level"],
                "allocation": allocation,
                "price": price,
                "btc_amount": btc_amount,
                "cumulative_avg": avg_price,
            })

        return result

    def calculate_expected_funding_cost(self, symbol: str, position_notional: float, 
                                       funding_rate: float, days: int = 90) -> float:
        """
        حساب التكلفة المتوقعة من التمويل (من CLOUD)
        
        Expected Cost = Position Notional × Funding Rate × Number of Intervals
        """
        intervals_per_day = 3  # Binance يحسب التمويل 3 مرات يوميًا
        total_intervals = intervals_per_day * days
        expected_cost = position_notional * funding_rate * total_intervals
        return expected_cost

    def check_daily_loss_limit(self, daily_loss: float, account_equity: float) -> bool:
        """التحقق من خسارة اليوم (5% الحد الأقصى)"""
        loss_pct = daily_loss / account_equity if account_equity > 0 else 0
        return loss_pct >= config.MAX_DAILY_LOSS

    def check_consecutive_losses(self, consecutive_losses: int) -> bool:
        """التحقق من الخسائر المتتالية"""
        return consecutive_losses >= config.MAX_CONSECUTIVE_LOSSES


@dataclass
class TradeJournal:
    """مفتش التداول - يسجل جميع الصفقات للتحليل (من CLOUD)"""
    timestamp: datetime
    symbol: str
    strategy: str
    direction: str
    htf_bias: str
    liquidity: str
    poi: str
    mss_bos: str
    fvg: str
    ob: str
    entry: float
    stop: float
    target: float
    risk: float
    position_size: float
    leverage: float
    fees: float
    funding: float
    slippage: float
    gross_pnl: float
    net_pnl: float
    exit_reason: str
    screenshot_ref: str = ""

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "symbol": self.symbol,
            "strategy": self.strategy,
            "direction": self.direction,
            "entry": self.entry,
            "exit": self.target,
            "risk": self.risk,
            "size": self.position_size,
            "net_pnl": self.net_pnl,
            "exit_reason": self.exit_reason,
        }


# أكواد أسباب الخروج (من CLOUD)
EXIT_REASON_CODES = {
    "TP": "Take Profit",
    "SL": "Stop Loss",
    "BE": "Break Even",
    "TRAILING_STOP": "Trailing Stop",
    "STRUCTURE_INVALIDATION": "Invalidation of Market Structure",
    "TIME_STOP": "Time-based Exit",
    "RISK_STOP": "Risk Management Stop",
    "NEWS_STOP": "News Event Closure",
    "MANUAL_STOP": "Manual Exit",
    "SYSTEM_ERROR": "System Error",
}
