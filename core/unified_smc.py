"""
📊 unified_smc.py — محرك تحليل SMC (Smart Money Concepts) المحسّن
يدمج منطق الـ SMC من جميع الملفات الـREADME + الكود الحالي
يدعم BOS, CHoCH, FVG, Order Block, Liquidity Sweep, Market Structure
"""
import logging
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple
import pandas as pd
import numpy as np

logger = logging.getLogger("unified_smc")


@dataclass
class MarketStructure:
    """نتيجة تحليل هيكل السوق"""
    bos_detected: bool = False           # Break of Structure
    choch_detected: bool = False         # Change of Character
    displacement: float = 0.0           # نسبة التحرك (Displacement)
    structure_valid: bool = False
    trend_direction: str = "neutral"   # bullish/bearish/neutral
    swing_high: float = 0.0
    swing_low: float = 0.0
    higher_high: Optional[float] = None
    lower_low: Optional[float] = None
    higher_low: Optional[float] = None
    lower_high: Optional[float] = None


@dataclass
class LiquidityZone:
    """منطقة سيولة"""
    level: float
    zone_type: str  # BSL (Buy Side), SSL (Sell Side), EQH, EQL
    swept: bool = False
    confidence: float = 0.0


@dataclass
class POI:
    """Point of Interest - منطقة اهتمام"""
    level: float
    zone_type: str  # OB, FVG, Breaker, Mitigation
    timeframe: str
    fresh: bool = True  # غير مختبر
    mitigated: bool = False
    confidence: float = 0.0


@dataclass
class Confirmation:
    """إشارة تأكيد"""
    confirmed: bool
    type: str  # CHoCH, Engulfing, Rejection
    strength: float  # 0.0 - 1.0
    volume_valid: bool = False


@dataclass
class SMCAnalysis:
    """نتيجة تحليل SMC الكاملة"""
    market_structure: MarketStructure
    liquidity_zones: List[LiquidityZone]
    poi_list: List[POI]
    confirmation: Confirmation
    score: float  # 0-10
    htf_bias: str
    is_valid_setup: bool
    entry_zones: List[float]
    sl_level: Optional[float]
    tp_levels: List[float]


class UnifiedSMC:
    """
    محرك تحليل SMC الموحد — يدعم جميع أنماط التداول
    """

    def __init__(self, config_dict: dict = None):
        self.config = config_dict or {}
        self.swing_lookback = self.config.get("swing_lookback", 5)
        self.displacement_threshold = self.config.get("displacement_threshold", 0.003)
        self.min_structural_distance = self.config.get("min_structural_distance", 0.005)
        self.volume_multiplier = self.config.get("volume_multiplier", 1.5)
        logger.info("📊 تم تهيئة محرك SMC الموحد")

    def detect_swing_points(self, df: pd.DataFrame, lookback: int = 5) -> Tuple[List[int], List[int]]:
        """
        اكتشاف نقاط الارتداد (Swing Highs/Lows)
        """
        swing_highs = []
        swing_lows = []

        for i in range(lookback, len(df) - lookback):
            window = df.iloc[i - lookback:i + lookback + 1]
            if df['high'].iloc[i] == window['high'].max():
                swing_highs.append(i)
            if df['low'].iloc[i] == window['low'].min():
                swing_lows.append(i)

        return swing_highs, swing_lows

    def detect_bos_choch(self, df: pd.DataFrame, swing_lookback: int = 5) -> MarketStructure:
        """
        اكتشاف BOS (Break of Structure) و CHoCH (Change of Character)
        منطق مبني على Higher Highs/Lower Lows
        """
        swing_highs, swing_lows = self.detect_swing_points(df, swing_lookback)

        ms = MarketStructure()

        if len(swing_highs) < 2 or len(swing_lows) < 2:
            return ms

        latest_high = df['high'].iloc[swing_highs[-1]]
        prev_high = df['high'].iloc[swing_highs[-2]] if len(swing_highs) > 1 else latest_high
        latest_low = df['low'].iloc[swing_lows[-1]]
        prev_low = df['low'].iloc[swing_lows[-2]] if len(swing_lows) > 1 else latest_low

        ms.swing_high = latest_high
        ms.swing_low = latest_low

        # BOS Bullish: Higher High + Higher Low
        if latest_high > prev_high and latest_low > prev_low:
            ms.bos_detected = True
            ms.higher_high = latest_high
            ms.higher_low = latest_low
            ms.trend_direction = "bullish"
            ms.structure_valid = True

        # BOS Bearish: Lower Low + Lower High
        elif latest_low < prev_low and latest_high < prev_high:
            ms.bos_detected = True
            ms.lower_low = latest_low
            ms.lower_high = latest_high
            ms.trend_direction = "bearish"
            ms.structure_valid = True

        # CHoCH: تغيير في الاتجاه
        if len(swing_highs) >= 3 and len(swing_lows) >= 3:
            if (df['high'].iloc[swing_highs[-1]] > df['high'].iloc[swing_highs[-2]] and
                df['high'].iloc[swing_highs[-2]] > df['high'].iloc[swing_highs[-3]]):
                # Bullish CHoCH
                ms.choch_detected = True
                ms.trend_direction = "bullish"
            elif (df['low'].iloc[swing_lows[-1]] < df['low'].iloc[swing_lows[-2]] and
                  df['low'].iloc[swing_lows[-2]] < df['low'].iloc[swing_lows[-3]]):
                # Bearish CHoCH
                ms.choch_detected = True
                ms.trend_direction = "bearish"

        # حساب Displacement (الازدحار)
        if len(df) >= 2:
            displacement = abs(df['close'].iloc[-1] - df['close'].iloc[-2]) / df['close'].iloc[-2]
            ms.displacement = displacement

        return ms

    def detect_fvg(self, df: pd.DataFrame, min_gap: float = 0.002) -> List[POI]:
        """
        اكتشاف Fair Value Gaps (FVG)
        FVG يحدث عندما يفتق السعر بين الشمعة الأولى والثالثة (3 شموع)
        """
        fvg_zones = []

        for i in range(2, len(df) - 1):
            # Bullish FVG: الشمعة 1 الأعلى < الشمعة 3 الأسفل
            if df['low'].iloc[i] > df['high'].iloc[i - 2]:
                gap_size = (df['low'].iloc[i] - df['high'].iloc[i - 2]) / df['close'].iloc[i]
                if gap_size >= min_gap:
                    fvg_zones.append(POI(
                        level=(df['low'].iloc[i] + df['high'].iloc[i - 2]) / 2,
                        zone_type="FVG_Bullish",
                        timeframe="1m",  # يعتمد على الفريم المستخدم
                        fresh=not self._is_fvg_mitigated(df, i, "bullish"),
                        confidence=min(gap_size * 100, 1.0),
                    ))

            # Bearish FVG: الشمعة 1 الأسفل > الشمعة 3 الأعلى
            if df['high'].iloc[i] < df['low'].iloc[i - 2]:
                gap_size = (df['low'].iloc[i - 2] - df['high'].iloc[i]) / df['close'].iloc[i]
                if gap_size >= min_gap:
                    fvg_zones.append(POI(
                        level=(df['high'].iloc[i] + df['low'].iloc[i - 2]) / 2,
                        zone_type="FVG_Bearish",
                        timeframe="1m",
                        fresh=not self._is_fvg_mitigated(df, i, "bearish"),
                        confidence=min(gap_size * 100, 1.0),
                    ))

        return fvg_zones

    def _is_fvg_mitigated(self, df: pd.DataFrame, idx: int, direction: str) -> bool:
        """التحقق من تخليص FVG (Mitigation)"""
        for i in range(idx + 1, min(idx + 6, len(df))):
            if direction == "bullish" and df['close'].iloc[i] <= df['high'].iloc[i - 2]:
                return True
            if direction == "bearish" and df['close'].iloc[i] >= df['low'].iloc[i - 2]:
                return True
        return False

    def detect_order_blocks(self, df: pd.DataFrame, lookback: int = 20) -> List[POI]:
        """
        اكتشاف Order Blocks (OB)
        OB هو منطقة طلب/عرض واضحة سبقت حركة كبيرة
        """
        ob_zones = []

        for i in range(lookback, len(df) - 1):
            # Bullish OB: شمعة ذات شمعة سفلية طويلة تليها شمعة خضراء كبيرة
            if (df['close'].iloc[i] > df['open'].iloc[i] and  # شمعة خضراء
                df['low'].iloc[i] < df['open'].iloc[i - 1] and  # خلف تحت الشمعة السابقة
                df['high'].iloc[i] - df['low'].iloc[i] > df['close'].iloc[i] - df['open'].iloc[i]):
                
                displacement = (df['close'].iloc[i + 1] - df['close'].iloc[i]) / df['close'].iloc[i]
                if displacement > self.displacement_threshold:
                    ob_zones.append(POI(
                        level=df['open'].iloc[i],
                        zone_type="OB_Bullish",
                        timeframe="LTF",
                        fresh=True,
                        confidence=min(abs(displacement) * 10, 1.0),
                    ))

            # Bearish OB: شمعة ذات شمعة علوية طويلة تليها شمعةحمراء كبيرة
            if (df['close'].iloc[i] < df['open'].iloc[i] and  # شمعة حمراء
                df['high'].iloc[i] > df['open'].iloc[i - 1] and  # خلف فوق الشمعة السابقة
                df['high'].iloc[i] - df['low'].iloc[i] > df['open'].iloc[i] - df['close'].iloc[i]):
                
                displacement = (df['close'].iloc[i + 1] - df['close'].iloc[i]) / df['close'].iloc[i]
                if abs(displacement) > self.displacement_threshold:
                    ob_zones.append(POI(
                        level=df['open'].iloc[i],
                        zone_type="OB_Bearish",
                        timeframe="LTF",
                        fresh=True,
                        confidence=min(abs(displacement) * 10, 1.0),
                    ))

        return ob_zones

    def detect_liquidity_zones(self, df: pd.DataFrame, lookback: int = 50) -> List[LiquidityZone]:
        """
        اكتشاف مناطق السيولة (BSL/ SSL / EQH / EQL)
        """
        zones = []
        window = df.tail(lookback)

        # Buy Side Liquidity (BSL) - أعلى قمة
        bsl_level = window['high'].max()
        zones.append(LiquidityZone(
            level=bsl_level,
            zone_type="BSL",
            swept=df['close'].iloc[-1] > bsl_level,
            confidence=0.8
        ))

        # Sell Side Liquidity (SSL) - أدنى قاع
        ssl_level = window['low'].min()
        zones.append(LiquidityZone(
            level=ssl_level,
            zone_type="SSL",
            swept=df['close'].iloc[-1] < ssl_level,
            confidence=0.8
        ))

        # Equal Highs (EQH) - أعلى قم مكرر
        high_counts = window['high'].value_counts().head(5)
        for price, count in high_counts.items():
            if count >= 2:
                zones.append(LiquidityZone(
                    level=price,
                    zone_type="EQH",
                    swept=False,
                    confidence=min(count * 0.2, 1.0)
                ))

        # Equal Lows (EQL) - أدنى قاع مكرر
        low_counts = window['low'].value_counts().head(5)
        for price, count in low_counts.items():
            if count >= 2:
                zones.append(LiquidityZone(
                    level=price,
                    zone_type="EQL",
                    swept=False,
                    confidence=min(count * 0.2, 1.0)
                ))

        return zones

    def get_confirmation(self, df: pd.DataFrame, direction: str = "long") -> Confirmation:
        """
        الحصول على إشارة تأكيد — CHoCH, Engulfing, Rejection
        """
        if len(df) < 3:
            return Confirmation(confirmed=False, type="none", strength=0.0)

        confirmation = Confirmation(confirmed=False, type="none", strength=0.0)

        # التحقق من حجم السيولة
        volume_ma = df['volume'].iloc[-10:].mean()
        current_volume = df['volume'].iloc[-1]
        volume_valid = current_volume >= self.volume_multiplier * volume_ma
        confirmation.volume_valid = volume_valid

        # CHoCH
        ms = self.detect_bos_choch(df)
        if ms.choch_detected:
            expected_direction = "bullish" if direction == "long" else "bearish"
            if ms.trend_direction == expected_direction:
                confirmation.confirmed = True
                confirmation.type = "CHoCH"
                confirmation.strength = 0.8

        # Engulfing Pattern
        if (df['close'].iloc[-1] > df['open'].iloc[-1] and  # شمعة خضراء
            df['close'].iloc[-2] < df['open'].iloc[-2] and  # شمعة حمراء سابقة
            df['close'].iloc[-1] > df['open'].iloc[-2] and  # الإغلاق فوق الافتتاح
            df['open'].iloc[-1] < df['close'].iloc[-2]):    # الافتتاح تحت الإغلاق
            if direction == "long":
                confirmation.confirmed = True
                confirmation.type = "Engulfing_Bullish"
                confirmation.strength = 0.7 if volume_valid else 0.5

        if (df['close'].iloc[-1] < df['open'].iloc[-1] and  # شمعة حمراء
            df['close'].iloc[-2] > df['open'].iloc[-2] and  # شمعة خضراء سابقة
            df['close'].iloc[-1] < df['open'].iloc[-2] and
            df['open'].iloc[-1] > df['close'].iloc[-2]):
            if direction == "short":
                confirmation.confirmed = True
                confirmation.type = "Engulfing_Bearish"
                confirmation.strength = 0.7 if volume_valid else 0.5

        # Volume confirmation
        if volume_valid and confirmation.confirmed:
            confirmation.strength = min(confirmation.strength + 0.2, 1.0)

        return confirmation

    def calculate_score(self, df: pd.DataFrame, htf_df: pd.DataFrame = None,
                       symbol: str = "") -> Tuple[float, MarketStructure, List[POI], Confirmation]:
        """
        حساب النقاط الكلية (Score Engine من CLOUD)
        العوامل: HTF Bias (+2), Liquidity (+2), MSS/CHoCH (+2), 
                  Displacement (+1), FVG/OB (+1), Premium/Discount (+1),
                  Session (+1), Volume (+1), News Clear (+1)
        """
        score = 0.0

        # 1. HTF Bias (منطق Bullish/Bearish واضح على الفريم العلوي)
        if htf_df is not None and len(htf_df) >= 10:
            htf_ms = self.detect_bos_choch(htf_df, swing_lookback=5)
            if htf_ms.trend_direction == "bullish":
                score += 2
            elif htf_ms.trend_direction == "bearish":
                score += 2
            # إذا كان neutral، لا نضيف

        # 2. Liquidity Sweep
        liquidity_zones = self.detect_liquidity_zones(df, lookback=50)
        swept_zones = [z for z in liquidity_zones if z.swept]
        if swept_zones:
            score += 2

        # 3. MSS/CHoCH
        ms = self.detect_bos_choch(df, swing_lookback=5)
        if ms.choch_detected:
            score += 2

        # 4. Displacement
        if ms.displacement >= self.displacement_threshold:
            score += 1

        # 5. FVG
        fvg_zones = self.detect_fvg(df)
        if fvg_zones:
            score += 1

        # 6. Order Block
        ob_zones = self.detect_order_blocks(df)
        if ob_zones:
            score += 1

        # 7. Session (Killzone)
        from core.unified_filters import TimeFilter
        if TimeFilter.is_killzone():
            score += 1

        # 8. Volume
        if ms.structure_valid and len(df) >= 10:
            volume_ma = df['volume'].iloc[-10:].mean()
            if df['volume'].iloc[-1] >= self.volume_multiplier * volume_ma:
                score += 1

        # 9. News Clear
        from core.unified_filters import TimeFilter
        if not TimeFilter.is_news_release_soon(minutes=15):
            score += 1

        return score, ms, fvg_zones + ob_zones, self.get_confirmation(df)

    def get_premium_discount_zone(self, df: pd.DataFrame, lookback: int = 100) -> Tuple[float, float]:
        """
        حساب منطقة Premium/Discount من خلال فيبوناتشي
        """
        window = df.tail(lookback)
        high = window['high'].max()
        low = window['low'].min()
        equilibrium = (high + low) / 2

        return high, low, equilibrium

    def get_entry_and_exit_levels(self, df: pd.DataFrame, direction: str = "long") -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """
        حساب مستويات الدخول والخروج بناءً على SMC
        """
        fvg_zones = self.detect_fvg(df)
        ob_zones = self.detect_order_blocks(df)
        poi_list = fvg_zones + ob_zones

        if not poi_list:
            return None, None, None

        # أفضل POI
        best_poi = max(poi_list, key=lambda x: x.confidence)
        entry = best_poi.level

        # SL على مستوى هيكلي
        swing_highs, swing_lows = self.detect_swing_points(df)
        if direction == "long":
            sl = df['low'].iloc[swing_lows[-1]] if swing_lows else entry * 0.98
            tp = df['high'].iloc[-1]  # أعلى قمة
        else:
            sl = df['high'].iloc[swing_highs[-1]] if swing_highs else entry * 1.02
            tp = df['low'].iloc[-1]  # أدنى قاع

        return entry, sl, tp
