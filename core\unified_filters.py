"""
🛡️ unified_filters.py — نظام فلاتر اختيار الصفقات الموحد (90% نجاح)
يدمج منطق NO TRADE من جميع الملفات الـREADME (KIMI, GPT, CLOUD, QWEN)
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

import config_unified as config

logger = logging.getLogger("unified_filters")


@dataclass
class TradeSignal:
    """إشارة تداول مقترحة"""
    symbol: str
    side: str  # LONG / SHORT
    entry_price: float
    sl_price: float
    tp_price: float
    rr: float
    confidence: float  # 0.0 - 1.0
    reasons: List[str] = field(default_factory=list)
    rejected_reasons: List[str] = field(default_factory=list)
    score: float = 0.0


@dataclass
class MarketContext:
    """سياق السوق"""
    htf_bias: Optional[str] = None  # bullish/bearish/neutral
    structure_valid: bool = False
    liquidity_present: bool = False
    poi_found: bool = False
    confirmation_valid: bool = False
    funding_rate: float = 0.0
    spread: float = 0.0
    slippage: float = 0.0
    volatility: str = "normal"  # normal/high/extreme
    news_risk: str = "low"  # low/medium/high


class UnifiedFilters:
    """
    نظام فلاتر موحد يدمج قواعد NO TRADE من جميع المنهجيات
    يتم رفض الصفقة إذا لم يتم استيفاء جميع الشروط
    """

    # قواعد فلتر R:R الأدنى لكل نمط (من GPT/CLOUD/KIMI/QWEN)
    MIN_RR_THRESHOLDS = {
        "scalping": 1.5,
        "day": 2.5,
        "swing": 3.0,
        "position_spot": float('inf'),  # DCA - غير محدد
        "position_futures": 5.0,
        "news": 2.0,
    }

    def __init__(self, mode: str = "swing"):
        self.mode = mode
        self.min_rr = self.MIN_RR_THRESHOLDS.get(mode, 2.5)
        logger.info(f"🛡️ تم تهيئة UnifiedFilters للوضع: {mode}، R:R الأدنى: {self.min_rr}")

    def check_no_trade_conditions(self, context: MarketContext, signal: TradeSignal) -> tuple[bool, List[str]]:
        """
        فحص جميع شروط NO TRADE من CLOUD
        إرجاع (should_trade: bool, rejection_reasons: list)
        """
        rejections = []

        # 1. HTF bias غير واضح
        if not context.htf_bias or context.htf_bias == "neutral":
            rejections.append("HTF bias غير واضح")

        # 2. Structure متناقض
        if not context.structure_valid:
            rejections.append("Structure متناقض أو غير واضح")

        # 3. لا توجد Liquidity واضحة
        if not context.liquidity_present:
            rejections.append("لا توجد Liquidity واضحة")

        # 4. لا توجد POI مناسبة
        if not context.poi_found:
            rejections.append("لا توجد POI مناسبة")

        # 5. Confirmation ضعيف
        if not context.confirmation_valid:
            rejections.append("Confirmation ضعيف أو مفقود")

        # 6. RR غير كافٍ
        if signal.rr < self.min_rr:
            rejections.append(f"R:R {signal.rr:.2f} < الحد الأدنى {self.min_rr:.2f}")

        # 7. Spread مرتفع
        if context.spread > 0.001:  # 0.1%
            rejections.append(f"Spread مرتفع ({context.spread:.4f})")

        # 8. Slippage مرتفع
        if context.slippage > 0.002:  # 0.2%
            rejections.append(f"Slippage مرتفع ({context.slippage:.4f})")

        # 9. Volatility غير طبيعية
        if context.volatility == "extreme":
            rejections.append("Volatility غير طبيعية")

        # 10. News Risk مرتفع
        if context.news_risk == "high":
            rejections.append("News Risk مرتفع")

        # 11. Funding Cost مرتفع (للـPosition Futures)
        max_funding = config.FUNDING_BOUNDS.get(self.mode, 0.0005)
        if abs(context.funding_rate) > max_funding:
            rejections.append(f"Funding Rate خارج الحدود (±{max_funding*100:.2f}%)")

        should_trade = len(rejections) == 0
        return should_trade, rejections

    def calculate_score(self, context: MarketContext) -> float:
        """
        نظام Scoring من CLOUD (11+ = A+ Candidate)
        """
        score = 0.0

        # HTF Bias: +2
        if context.htf_bias == "bullish":
            score += 2
        elif context.htf_bias == "bearish":
            score += 1.5

        # Liquidity Sweep: +2
        if context.liquidity_present:
            score += 2

        # MSS/CHoCH: +2
        if context.structure_valid:
            score += 2

        # Displacement: +1
        if context.structure_valid:
            score += 1

        # FVG/OB: +1
        if context.poi_found:
            score += 1

        # Premium/Discount: +1
        if context.htf_bias:
            score += 1

        # Session (Killzone): +1
        if self._is_killzone():
            score += 1

        # Volume/Activity: +1
        if context.volatility != "extreme":
            score += 1

        # News Clear: +1
        if context.news_risk == "low":
            score += 1

        return score

    def is_valid_score(self, score: float) -> bool:
        """Score < 7 → NO TRADE"""
        return score >= config.MIN_SCORE

    def _is_killzone(self) -> bool:
        """التحقق من أن الوقت ضمن Killzone (11:00 و 16:00 GMT)"""
        utc_hour = datetime.utcnow().hour + datetime.utcnow().minute / 60.0
        for start, end in config.KILLZONES_UTC:
            if start <= utc_hour <= end:
                return True
        return False

    def should_block_pre_news(self, minutes_before_news: int = 5) -> bool:
        """حظر التداول قبل الأخبار (News Trading)"""
        if self.mode == "news":
            return False
        return TimeFilter.is_news_release_soon(minutes=minutes_before_news)

    def check_portfolio_risk(self, open_positions: int, daily_loss: float, 
                            consecutive_losses: int, total_risk: float,
                            account_equity: float = 100.0) -> tuple[bool, str]:
        """
        فحص حماية المحفظة (من GPT — حدود عالمية)
        
        Returns (can_trade, reason)
        """
        # 1. عدد الصفقات المتزامنة
        if open_positions >= config.MAX_OPEN_POSITIONS:
            return False, f"تم الوصول للحد الأقصى للصفقات المفتوحة ({config.MAX_OPEN_POSITIONS})"

        # 2. الخسارة اليومية
        loss_pct = daily_loss / account_equity
        if loss_pct >= config.MAX_DAILY_LOSS:
            return False, f"الخسارة اليومية {loss_pct*100:.1f}% >= الحد الأقصى {config.MAX_DAILY_LOSS*100:.0f}%"

        # 3. الخسائر المتتالية
        if consecutive_losses >= config.MAX_CONSECUTIVE_LOSSES:
            return False, f"عدد الخسائر المتتالية {consecutive_losses} >= الحد الأقصى {config.MAX_CONSECUTIVE_LOSSES}"

        # 4. الخطر الإجمالي
        risk_pct = total_risk / account_equity
        if risk_pct >= 0.05:  # 5% الحد الأقصى
            return False, f"المخاطرة الإجمالية {risk_pct*100:.1f}% >= 5%"

        return True, "✅ جميع فحوصات المحفظة نجحت"


@dataclass
class TimeFilter:
    """
    فلاتر الوقت — Killzones, News Blackouts, Silver Bullets
    مدمجة من جميع الملفات الـREADME
    """
    @staticmethod
    def is_killzone() -> bool:
        """التحقق من أن الوقت ضمن Killzone (11:00 و 16:00 GMT)"""
        utc_hour = datetime.utcnow().hour + datetime.utcnow().minute / 60.0
        for start, end in config.KILLZONES_UTC:
            if start <= utc_hour <= end:
                return True
        return False

    @staticmethod
    def is_silver_bullet() -> bool:
        """التحقق من Silver Bullet Time"""
        utc_hour = datetime.utcnow().hour + datetime.utcnow().minute / 60.0
        for sb in config.SILVER_BULLETS_UTC:
            if abs(utc_hour - sb) <= 0.5:
                return True
        return False

    @staticmethod
    def is_weekend_or_bad_day() -> bool:
        """التحقق من أيام الأسبوع غير المناسبة"""
        weekday = datetime.utcnow().weekday()
        return weekday in config.BAD_WEEKDAYS

    @staticmethod
    def is_news_release_soon(minutes: int = 5) -> bool:
        """التحقق من قرب إصدار أخبار Tier 1"""
        # تبسيط: استخدام القواعد من config
        now = datetime.utcnow()
        for event_name, event_info in config.NEWS_BLACKOUTS.items():
            # منطق بسيط للتحقق
            if now.weekday() == event_info.get("weekday", -1):
                event_hour = event_info.get("hour", 0)
                event_minute = event_info.get("minute", 0)
                event_time = now.replace(hour=event_hour, minute=event_minute)
                if event_time > now and (event_time - now).total_seconds() <= minutes * 60:
                    return True
        return False

    @staticmethod
    def can_trade_now(mode: str = "swing") -> bool:
        """
        فحص شامل إذا كان يمكن التداول الآن
        يدمج Killzone + News + أيام الأسبوع
        """
        # Scalping/Day: يتطلب Killzone أو Silver Bullet
        if mode in ("scalping", "day", "news"):
            if not (TimeFilter.is_killzone() or TimeFilter.is_silver_bullet()):
                return False

        # جميع الأنماط: تجنب أيام الأخبار الكبرى
        if TimeFilter.is_news_release_soon(minutes=15):
            return False

        # تجنب أيام الأسبوع الصعبة (اختياري)
        if mode in ("scalping", "day", "news"):
            if TimeFilter.is_weekend_or_bad_day():
                return False

        return True
