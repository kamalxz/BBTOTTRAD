"""🌊 SWING TRADER - فكرة الصبر والثروة
يدور على صفقات ذات R:R ديناميكي بناءً على السيولة المتاحة على الإطار 4H والـ 1D.
يأخذ منطقة Discount (تحت 50% فيبوناتي) ثم ينتظر التأكيد على 1H.
يفلتر الصفقات عبر الـ Funding Rate.
"""
import logging
import time

import pandas as pd

import config
from analysis import (
    detect_bos,
    detect_ob,
    detect_swing_highs_lows,
    get_daily_bias,
    get_major_liquidity,
)
from time_filter import TimeFilter

from .base import BaseMode
from core.telegram_alerts import send_telegram_alert

logger = logging.getLogger(__name__)


class SwingTraderBot(BaseMode):
    name = "SWING_TRADER"
    description = "🌊 فكرة الصبر - اصطياد الموجات الكبرى (1D/4H)"

    htf_timeframe = "1d"
    mtf_timeframe = "4h"
    ltf_timeframe = "1h"
    day_leverage = 3
    risk_per_trade = 0.01
    min_rr_ratio = 3.0
    scan_interval = 14400  # 4 ساعات
    funding_filter_threshold = 0.05  # 0.05% = الحد الأقصى لرفع Long

    def run(self):
        self._log_mode()
        active_trade = None

        while True:
            try:
                if TimeFilter.is_killzone() and not TimeFilter.is_news_time():
                    if active_trade:
                        current_price = self._get_current_price(active_trade["symbol"])
                        active_trade = self._manage_trade(active_trade, current_price)
                    else:
                        trade = self._scan()
                        if trade:
                            active_trade = trade
                            logger.info(f"✅ صفقة Swing مفتوحة: {trade['symbol']} {trade['side']} RR={trade['rr']:.2f}")
                            print(f"✅ صفقة: {trade['symbol']} {trade['side']} @ {trade['entry']:.2f} SL={trade['sl']:.2f} TP={trade['tp']:.2f} RR={trade['rr']:.2f}")
                            self._on_signal(trade)

                time.sleep(self.scan_interval)

            except Exception as e:
                logger.error(f"خطأ في SwingTrader: {e}")
                time.sleep(60)

    def _scan(self):
        """مسح الرموز باستخدام SMC على الإطارات الكبرى."""
        for symbol in config.SYMBOLS:
            try:
                df_1d = self._get_ohlcv(symbol, self.htf_timeframe, 90)
                df_4h = self._get_ohlcv(symbol, self.mtf_timeframe, 90)
                df_1h = self._get_ohlcv(symbol, self.ltf_timeframe, 90)

                trade = self._analyze_swing_trade(df_1d, df_4h, df_1h, symbol)
                if trade:
                    return trade
            except Exception as e:
                logger.debug(f"تحليل {symbol} فشل: {e}")
        return None

    def _get_ohlcv(self, symbol, timeframe, limit):
        ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        return pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])

    def _get_current_price(self, symbol):
        ticker = self.exchange.fetch_ticker(symbol)
        return ticker["last"]

    def _get_funding_rate(self, symbol):
        """الحصول على الـ Funding Rate الحالي."""
        try:
            return float(self.exchange.fetch_funding_rate(symbol)["fundingRate"])
        except Exception:
            return 0.0

    def _calculate_fibonacci(self, df_4h, trend):
        """حساب مستويات الخصم (Discount Zone) باستخدام الفيبوناتي."""
        swing_points = detect_swing_highs_lows(df_4h, window=5)
        if len(swing_points) < 2:
            return None

        # آخر Swing High و Swing Low
        highs = [p for p in swing_points if p["type"] == "high"]
        lows = [p for p in swing_points if p["type"] == "low"]

        if trend == "bullish" and len(lows) >= 2:
            swing_low = min(p["price"] for p in lows[-5:])
            swing_high = max(p["price"] for p in highs[-5:])
            diff = swing_high - swing_low
            return {
                "fib_50": swing_low + diff * 0.5,
                "fib_62": swing_low + diff * 0.618,
                "fib_79": swing_low + diff * 0.786,
                "swing_low": swing_low,
                "swing_high": swing_high,
            }
        elif trend == "bearish" and len(highs) >= 2:
            swing_low = min(p["price"] for p in lows[-5:])
            swing_high = max(p["price"] for p in highs[-5:])
            diff = swing_high - swing_low
            return {
                "fib_50": swing_high - diff * 0.5,
                "fib_62": swing_high - diff * 0.62,
                "fib_79": swing_high - diff * 0.786,
                "swing_low": swing_low,
                "swing_high": swing_high,
            }
        return None

    def _analyze_swing_trade(self, df_1d, df_4h, df_1h, symbol):
        """التحليل الكامل لصفقة الـ Swing."""
        # 1. التاتج اليومي (Daily Bias)
        trend = get_daily_bias(df_1d)
        if trend == "neutral":
            return None

        # 2. فلتر الـ Funding Rate (لمنع الرسوم على Long)
        funding_rate = self._get_funding_rate(symbol)
        if trend == "bullish" and funding_rate > self.funding_filter_threshold:
            logger.info(f"⚠️ {symbol}: Funding {funding_rate:.2%} > {self.funding_filter_threshold:.2%}، رفض Long")
            return None

        # 3. حساب مناطق الخصم (Fibonacci Discount Zone)
        fib_zones = self._calculate_fibonacci(df_4h, trend)
        if not fib_zones:
            return None

        current_price = df_1h["close"].iloc[-1]

        # 4. التحقق من أن السعر في منطقة الخصم (أقل من 50%)
        if trend == "bullish":
            if current_price > fib_zones["fib_50"]:
                return None  # السعر مش بالخصم، انتظر التراجع
            # ✅ السعر في المنطقة المخفضة (Discount)
        else:
            if current_price < fib_zones["fib_50"]:
                return None
            # ✅ السعر في المنطقة المرتفعة (Premium)

        # 5. البحث عن OB أو FVG في منطقة الخصم على 4H
        obs = detect_ob(df_4h)
        valid_obs = [ob for ob in obs if
                     ob["type"] == ("bullish" if trend == "bullish" else "bearish") and
                     not ob["mitigated"] and
                     (min(ob["top"], ob["bottom"]) <= current_price <= max(ob["top"], ob["bottom"]))]

        if not valid_obs:
            return None

        best_ob = valid_obs[-1]  # آخث OB غير مُعوّق

        # 6. التأكيد على 1H: CHoCH أو Engulfing
        swing_points_1h = detect_swing_highs_lows(df_1h, window=3)
        bos = detect_bos(df_1h, swing_points_1h)

        if not bos or bos["type"] != ("bullish_bos" if trend == "bullish" else "bearish_bos"):
            return None

        # ✅ تأكيد وجد — نفذ الصفقة
        entry_price = current_price
        sl = fib_zones["fib_79"] if trend == "bullish" else fib_zones["fib_79"]
        major_liq = get_major_liquidity(df_1d)
        tp = major_liq["support"] if trend == "bearish" else major_liq["resistance"]

        sl_distance_pct = abs(entry_price - sl) / entry_price * 100
        tp_distance_pct = abs(tp - entry_price) / entry_price * 100
        rr_ratio = tp_distance_pct / sl_distance_pct if sl_distance_pct > 0 else 0

        # التحقق من الحد الأدنى للـ R:R
        if rr_ratio < config.DAY_MIN_RR:
            logger.info(f"⚠️ {symbol}: R:R {rr_ratio:.2f} < الحد الأدنى")
            return None

        side = "LONG" if trend == "bullish" else "SHORT"
        return {
            "symbol": symbol,
            "side": side,
            "entry": entry_price,
            "sl": sl,
            "tp": tp,
            "rr": rr_ratio,
            "ob_index": best_ob["index"],
            "funding_rate": funding_rate,
        }

    def _on_signal(self, signal):
        """📲 إرسال إشعار تيليجرام للإشارة"""
        send_telegram_alert(
            f"<b>🌊 إشارة Swing جديدة</b>\n"
            f"🪙 {signal['symbol']}\n"
            f"📈 الاتجاه: {signal['side']}\n"
            f"💰 الدخول: {signal['entry']:.2f}\n"
            f"🛑 SL: {signal['sl']:.2f}\n"
            f"🎯 TP: {signal['tp']:.2f}\n"
            f"⚖️ R:R: {signal['rr']:.2f}\n"
            f"💸 Funding Rate: {signal['funding_rate']:.4f}"
        )

    def _manage_trade(self, trade, current_price):
        """إدارة الصفقة الـ Swing: Break Even + Trailing Stop."""
        entry = trade["entry"]
        sl = trade["sl"]
        tp = trade["tp"]
        side = trade["side"]

        # 🛡️ Break Even: إذا وصل للـ 1:1
        if side == "LONG" and current_price >= entry * 1.01:
            trade["sl"] = entry  # نفس السعر
        elif side == "SHORT" and current_price <= entry * 0.99:
            trade["sl"] = entry

        # 🎯 إغلاق عند TP
        reached_tp = (side == "LONG" and current_price >= tp) or \
                     (side == "SHORT" and current_price <= tp)
        if reached_tp:
            self._close_trade(trade, current_price, "🎯 TP محقق")
            return None

        # ⛔ إغلاق عند SL
        hit_sl = (side == "LONG" and current_price <= sl) or \
                 (side == "SHORT" and current_price >= sl)
        if hit_sl:
            self._close_trade(trade, current_price, "⛔ SL مضروك")
            return None

        return trade

    def _close_trade(self, trade, price, reason):
        """إغلاق الصفقة وإرسال التقرير."""
        entry = trade["entry"]
        if trade["side"] == "LONG":
            pnl_pct = ((price - entry) / entry) * 100
        else:
            pnl_pct = ((entry - price) / price) * 100

        logger.info(f"🏁 إغلاق Swing: {trade['symbol']} | {reason} | PnL: {pnl_pct:.2f}%")
        print(f"🏁 إغلاق: {trade['symbol']} | {reason} | PnL: {pnl_pct:.2f}%")
