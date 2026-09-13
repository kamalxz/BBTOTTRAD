"""👑 DAY TRADER المحسّن — يدمج SMC الكامل (BOS, FVG, OB, CHoCH) مع تأكيد الحجم والوقت
يستخدم منطق Smart Money Concepts الكامل بدلاً من EMA البسيط.

التحسينات:
- إضافة Liquidity Sweep detection
- إضافة BOS/CHoCH من الـ unified_smc
- إضافة Order Block و FVG
- إضافة Volume filter (≥1.5x المتوسط)
- إضافة Killzone + News time filter
- R:R الأدنبي = 2.5 (من config)
"""
import logging
import time

import pandas as pd

from .base import BaseMode
from core.telegram_alerts import send_telegram_alert
import config
from time_filter import TimeFilter

from core.unified_smc import UnifiedSMC
from core.unified_filters import UnifiedFilters, MarketContext, TimeFilter as UnifiedTimeFilter

logger = logging.getLogger(__name__)


class DayTraderBot(BaseMode):
    name = "DAY TRADER"
    description = "👑 فكرة النظافة المحسّنة - SMC كامل على إطار 15m/1h"
    timeframe = "15m"
    htf_timeframe = "1h"
    day_leverage = 3
    risk_per_trade = 0.01
    min_rr_ratio = config.DAY_MIN_RR  # 2.5

    def __init__(self):
        super().__init__()
        self.smc = UnifiedSMC()
        self.filters = UnifiedFilters(mode="day")
        logger.info("👑 Day Trader Bot (SMC Enhanced) جاهز")

    def run(self):
        self._log_mode()
        while True:
            try:
                if TimeFilter.is_killzone() and not TimeFilter.is_news_time():
                    self._scan()
                elif TimeFilter.is_news_time():
                    logger.info("⏳ توقف مؤقت — وقت أخبار اقتصادية حية")
                else:
                    logger.info("💤 خارج منطقة الاستهداف — المسح متوقف حتى الفتح التالية")
                time.sleep(60)
            except Exception as e:
                logger.error(f"خطأ في DayTrader: {e}")
                time.sleep(10)

    def _scan(self):
        """مسح الرموز باستخدام SMC المحسّن."""
        for symbol in config.SYMBOLS:
            try:
                df_15m = self._get_ohlcv(symbol, self.timeframe, 100)
                df_1h = self._get_ohlcv(symbol, self.htf_timeframe, 50)
                if df_15m.empty or df_1h.empty:
                    continue

                signal = self._analyze_day(df_15m, df_1h, symbol)
                if signal:
                    logger.info(f"👑 إشارة Day Trade: {symbol} {signal['side']} R:R={signal['rr']:.2f}")
                    print(f"👑 إشارة: {symbol} {signal['side']} @ {signal['entry']:.2f} R:R={signal['rr']:.2f}")
                    self._on_signal(symbol, signal)
            except Exception as e:
                logger.debug(f"تحليل {symbol} فشل: {e}")

    def _analyze_day(self, df_15m, df_1h, symbol):
        """تحليل SMC كامل للـ Day Trading."""
        # 1. التحقق من HTF Bias (BOS على 1H)
        score, ms, poi_list, conf = self.smc.calculate_score(df_15m, df_1h, symbol)
        
        # HTF Bias إجباري
        if ms.trend_direction == "neutral" or not ms.structure_valid:
            return None

        # 2. فحص السيولة (Liquidity Sweep)
        liquidity_zones = self.smc.detect_liquidity_zones(df_15m, lookback=50)
        swept_liquidity = any(z.swept for z in liquidity_zones)
        
        if not swept_liquidity:
            return None  # مطلوب Liquidity Sweep

        # 3. فحص POIs (OB و FVG)
        if not poi_list:
            return None

        # 4. التحقق من التأكيد (CHoCH أو Engulfing)
        direction = "long" if ms.trend_direction == "bullish" else "short"
        confirmation = self.smc.get_confirmation(df_15m, direction)
        if not confirmation.confirmed or confirmation.strength < 0.5:
            return None

        # 5. فحص الحجم
        if not confirmation.volume_valid:
            return None  # مطلوب حجم أعلى من المتوسط

        # 6. حساب الدخول والخروج
        entry, sl, tp = self.smc.get_entry_and_exit_levels(df_15m, direction)
        if entry is None:
            return None

        rr_ratio = abs(tp - entry) / abs(entry - sl) if sl and sl != 0 else 0

        # 7. التحقق من R:R الأدنبي
        if rr_ratio < self.min_rr_ratio:
            logger.info(f"⚠️ {symbol}: R:R {rr_ratio:.2f} < {self.min_rr_ratio}")
            return None

        # 8. فحص المنطقة المناسبة (Discount/Premium)
        htf_bias = ms.trend_direction
        current_price = df_15m["close"].iloc[-1]
        
        # التحقق من أن السعر في المنطقة المناسبة
        swing_high = df_1h["high"].max()
        swing_low = df_1h["low"].min()
        equilibrium = (swing_high + swing_low) / 2

        if htf_bias == "bullish" and current_price > equilibrium:
            return None  # السعر في Premium — غير مثالي للـ Long
        if htf_bias == "bearish" and current_price < equilibrium:
            return None  # السعر في Discount — غير مثالي للـ Short

        return {
            "symbol": symbol,
            "side": ms.trend_direction.upper(),
            "entry": entry,
            "sl": sl,
            "tp": tp,
            "rr": rr_ratio,
            "score": score,
            "confidence": confirmation.strength,
            "reasons": [
                f"HTF Bias: {htf_bias}",
                f"Liquidity Swept: {swept_liquidity}",
                f"Confirmation: {confirmation.type}",
                f"R:R: {rr_ratio:.2f}",
            ],
        }

    def _on_signal(self, symbol, signal):
        """إرسال إشعار تيليجرام."""
        send_telegram_alert(
            f"<b>👑 إشارة Day Trade جديدة</b>\n"
            f"🪙 {symbol}\n"
            f"📊 الاتجاه: {signal['side']}\n"
            f"💰 الدخول: {signal['entry']:.2f}\n"
            f"🛑 SL: {signal['sl']:.2f}\n"
            f"🎯 TP: {signal['tp']:.2f}\n"
            f"⚖️ R:R: {signal['rr']:.2f}\n"
            f"📈 النقاط: {signal['score']}/10\n"
            f"💪 الثقة: {signal['confidence']*100:.0f}%"
        )
