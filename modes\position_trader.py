"""🏦 Position Trader — Spot DCA bot based on Weekly Order Blocks"""
import logging
import time

from modes.base import BaseMode
from analysis import detect_ob, check_ob_mitigation
from core.telegram_alerts import send_telegram_alert
import config

logger = logging.getLogger("position_trader")


class PositionTraderBot(BaseMode):
    name = "POSITION_TRADER"
    description = "🏦 فكرة الاستثمار - بناء الثروة على المدى الطويل (Spot Only)"

    timeframe = "1w"
    leverage = 1
    margin_type = "spot"

    dca_levels = 4
    dca_step_pct = 0.05
    budget_per_symbol = 100.0

    def run(self):
        logger.info("🏦 بدء تشغيل Position Trader (Spot Mode)...")

        while True:
            try:
                self._scan_weekly_opportunities()
                logger.info("⏳ النوم لمدة 24 ساعة حتى الفحص الأسبوعي التالي...")
                time.sleep(86400)

            except Exception as e:
                logger.error(f"❌ خطأ في الحلقة الرئيسية لـ Position Trader: {e}")
                time.sleep(3600)

    def _scan_weekly_opportunities(self):
        symbols_to_scan = getattr(config, "SYMBOLS_SPOT", config.SYMBOLS)

        for symbol in symbols_to_scan:
            try:
                df_1w = self._get_ohlcv(symbol, "1w", limit=52)
                df_1d = self._get_ohlcv(symbol, "1d", limit=30)
                if df_1w is None or df_1w.empty or df_1d is None or df_1d.empty:
                    continue

                signal = self._analyze_position(df_1w, df_1d, symbol)
                if signal:
                    logger.info(
                        f"🎯 [SPOT] فرصة تراكم على {symbol}: "
                        f"السعر قريب من Weekly OB ({signal['poi_type']})"
                    )
                    self._execute_dca_strategy(symbol, signal)

            except Exception as e:
                logger.error(f"خطأ في فحص {symbol} (Spot): {e}")

    def _analyze_position(self, df_1w, df_1d, symbol):
        obs = detect_ob(df_1w)
        if not obs:
            return None

        mitigated = check_ob_mitigation(df_1w, obs)
        valid_pois = [ob for ob in mitigated if not ob.get("mitigated", False)]

        if not valid_pois:
            return None

        current_price = df_1w["close"].iloc[-1]

        # ✅ التحقق من 200W MA
        ma_200w = None
        if len(df_1w) >= 200:
            ma_200w = df_1w["close"].rolling(window=200).mean().iloc[-1]
            if current_price < ma_200w:
                logger.info(f"🚨 {symbol}: السعر تحت 200W MA = فرصة تاريخية!")

        for poi in valid_pois:
            if poi["type"] == "bullish":
                distance_pct = (current_price - poi["top"]) / poi["top"]
                if -0.05 <= distance_pct <= 0.05:
                    # ✅ التحقق من التأكيد اليومي
                    if self._has_daily_rejection(df_1d):
                        return {
                            "symbol": symbol,
                            "current_price": current_price,
                            "poi_price": poi["top"],
                            "poi_type": "Weekly Bullish OB",
                            "ma_200w": ma_200w,
                        }

        return None

    def _has_daily_rejection(self, df_1d):
        if len(df_1d) < 3:
            return False

        last = df_1d.iloc[-1]
        prev = df_1d.iloc[-2]

        body = abs(last["close"] - last["open"])
        lower_wick = min(last["open"], last["close"]) - last["low"]

        # Rejection Wick
        if lower_wick > body * 2:
            return True

        # Engulfing Bullish
        if (
            last["close"] > last["open"]
            and prev["close"] < prev["open"]
            and last["close"] > prev["open"]
        ):
            return True

        return False

    def _execute_dca_strategy(self, symbol, signal):
        current_price = signal["current_price"]
        amount_per_level = self.budget_per_symbol / self.dca_levels

        logger.info(f"💰 بدء استراتيجية DCA لـ {symbol} بميزانية {self.budget_per_symbol}$")

        # 📲 إشعار تيليجرام عند بدء DCA
        send_telegram_alert(
            f"<b>💰 بدء استراتيجية DCA (Spot)</b>\n"
            f"🪙 {symbol}\n"
            f"💵 الميزانية: ${self.budget_per_symbol:.2f}\n"
            f"📊 مستويات DCA: {self.dca_levels}"
        )

        for i in range(self.dca_levels):
            buy_price = current_price * (1 - i * self.dca_step_pct)
            try:
                logger.info(
                    f"✅ [DCA Level {i + 1}] أمر شراء Spot مُعَدَّد "
                    f"لـ {symbol} @ {buy_price:.2f} | القيمة: {amount_per_level:.2f}$"
                )
                # TODO: استدعاء self.exchange.create_spot_limit_buy_order(symbol, amount_per_level, buy_price)
            except Exception as e:
                logger.error(f"❌ فشل في وضع أمر DCA Level {i + 1} لـ {symbol}: {e}")

        logger.info(f"🏁 تم وضع جميع أوامر DCA الـ {self.dca_levels} لـ {symbol} بنجاح.")
