"""🏦⚠️ position_trader_futures.py — Position Trading على Futures مع 5 طبقات أمان"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

import pandas as pd

from analysis import (
    detect_fvg,
    detect_ob,
    check_fvg_mitigation,
    check_ob_mitigation,
)
from modes.base import BaseMode
from core.telegram_alerts import send_telegram_alert
import config

logger = logging.getLogger("position_trader_futures")


class PositionTraderFuturesBot(BaseMode):
    """Position Trading على Binance Futures — محمي بـ 5 طبقات أمان."""

    name = "POSITION_TRADER_FUTURES"
    description = "🏦⚠️ Position Trading على Futures (محمي بـ 5 طبقات)"

    htf_timeframe = "1d"
    mtf_timeframe = "4h"
    ltf_timeframe = "1h"

    leverage = 3
    margin_type = "isolated"

    risk_per_trade = 0.01
    min_rr_ratio = 5.0

    max_funding_rate_long = 0.0003
    max_funding_rate_short = -0.0003

    scan_interval = 14_400  # كل 4 ساعات
    max_position_duration = 7_776_000  # 90 يوم بالثواني
    weekly_check_interval = 604_800  # 7 أيام
    _last_weekly_check: float = 0.0

    def run(self):
        logger.warning("⚠️⚠️⚠️ تشغيل Position Trader على FUTURES ⚠️⚠️⚠️")
        logger.warning("⚠️ محمي بـ 5 طبقات أمان")
        logger.warning("=" * 60)

        # تهيئة وقت آخر فحص أسبوعي
        self._last_weekly_check = time.time()

        while True:
            try:
                self._manage_open_positions()

                now = time.time()
                if now - self._last_weekly_check >= self.weekly_check_interval:
                    logger.info("📅 بدء الفحص الأسبوعي الشامل...")
                    self._weekly_comprehensive_check()
                    self._last_weekly_check = now

                self._scan_opportunities()
                logger.info(f"⏳ النوم لمدة {self.scan_interval // 3600} ساعة")
                time.sleep(self.scan_interval)

            except Exception as e:
                logger.error(f"❌ خطأ في الحلقة الرئيسية: {e}")
                time.sleep(3600)

    # ─────────────────────────────────────────────
    # 🛡️ طبقة 1–4: إدارة المراكز المفتوحة + Duration Guard
    # ─────────────────────────────────────────────

    def _manage_open_positions(self):
        try:
            positions: List[Dict[str, Any]] = self.exchange.fetch_positions()
            for pos in positions:
                if pos.get("contracts", 0) == 0:
                    continue
                symbol = pos["symbol"]
                self._check_position_duration(symbol, pos)
                self._manage_trailing_stop(symbol, pos)
        except Exception as e:
            logger.error(f"❌ خطأ في إدارة المراكز: {e}")

    def _check_position_duration(self, symbol: str, pos: dict):
        """🔒 طبقة الحماية 5: إغلاق الصفقة إذا تخطت 90 يومًا."""
        try:
            info = pos.get("info", {})
            entry_time_ms = info.get("updateTime", 0)
            if entry_time_ms == 0:
                logger.warning(f"⚠️ {symbol}: لا يمكن تحديد وقت الدخول")
                return

            entry = pd.to_datetime(entry_time_ms, unit="ms")
            duration_s = (pd.Timestamp.now(tz="UTC") - entry).total_seconds()
            duration_days = duration_s / 86_400

            logger.info(f"📊 {symbol}: مدة الصفقة ≈ {duration_days:.1f} يوم")

            if duration_s > self.max_position_duration:
                logger.warning("=" * 60)
                logger.warning(f"⏰⏰⏰ {symbol}: إغلاق إجباري بعد 90 يوم ⏰⏰⏰")
                logger.warning("=" * 60)
                send_telegram_alert(
                    f"<b>⏰ إغلاق إجباري — Duration Guard</b>\n"
                    f"🪙 {symbol}\n"
                    f"📅 المدة: {duration_days:.1f} يوم (الحد الأقصى 90)\n"
                    f"⚠️ تم إغلاق الصفقة تلقائياً وفقاً لقاعدة الحماية الخامسة."
                )
                self._close_position_by_symbol(symbol)

        except Exception as e:
            logger.error(f"❌ خطأ في فحص مدة {symbol}: {e}")

    def _close_position_by_symbol(self, symbol: str) -> Optional[dict]:
        try:
            positions = self.exchange.fetch_positions([symbol])
            for pos in positions:
                if pos.get("contracts", 0) == 0:
                    continue

                side = pos["side"]  # 'long' أو 'short'
                close_side = "sell" if side == "long" else "buy"
                amount = abs(pos["contracts"])

                order = self.exchange.create_futures_order(
                    symbol=symbol,
                    side=close_side,
                    order_type="market",
                    amount=amount,
                    leverage=self.leverage,
                    margin_type=self.margin_type,
                )

                logger.info(f"✅ تم إغلاق {symbol} بنجاح")
                return order

        except Exception as e:
            logger.error(f"❌ خطأ في إغلاق {symbol}: {e}")
        return None

    def _manage_trailing_stop(self, symbol: str, pos: dict):
        """إدارة Trailing Stop — يمكن استبداؤها بنسخة أكثر تقدمًا من Swing Trader."""
        # Placeholder — نفس المنطق في swing_trader.py
        pass

    # ─────────────────────────────────────────────
    # 📅 فحص أسبوعي شامل
    # ─────────────────────────────────────────────

    def _weekly_comprehensive_check(self):
        logger.info("📅 بدء الفحص الأسبوعي الشامل...")
        try:
            positions = self.exchange.fetch_positions()

            for pos in positions:
                if pos.get("contracts", 0) == 0:
                    continue

                symbol = pos["symbol"]

                # 1. فحص المدة
                self._check_position_duration(symbol, pos)

                # 2. فحص Funding Rate الحالي
                rate = self.exchange.get_funding_rate(symbol)
                if rate is not None:
                    side = pos["side"]
                    if side == "long" and rate > 0.001:
                        logger.warning(f"⚠️ {symbol}: Funding Rate مرتفع ({rate:.4f}) — نظر في الإغلاق")
                    elif side == "short" and rate < -0.001:
                        logger.warning(f"⚠️ {symbol}: Funding Rate منخفض ({rate:.4f}) — نظر في الإغلاق")

                # 3. فحص PnL
                entry_price = float(pos.get("entryPrice", 0))
                mark_price = float(pos.get("markPrice", 0))
                if entry_price > 0 and mark_price > 0:
                    if side == "short":
                        pnl_pct = (entry_price - mark_price) / entry_price
                    else:
                        pnl_pct = (mark_price - entry_price) / entry_price
                    logger.info(f"💰 {symbol}: PnL ≈ {pnl_pct:.2%}")
                    if pnl_pct > 0.50:
                        logger.warning(f"🎯 {symbol}: ربح كبير — نظر في TP جزئي")

                # 4. Trailing Stop
                self._manage_trailing_stop(symbol, pos)

        except Exception as e:
            logger.error(f"❌ خطأ في الفحص الأسبوعي: {e}")

    # ─────────────────────────────────────────────
    # 🔍 مسح وتحليل الفرص
    # ─────────────────────────────────────────────

    def _scan_opportunities(self):
        symbols = getattr(config, "SYMBOLS_FUTURES", config.SYMBOLS)
        for symbol in symbols:
            try:
                df_1d = self._get_ohlcv(symbol, self.htf_timeframe, limit=100)
                df_4h = self._get_ohlcv(symbol, self.mtf_timeframe, limit=100)
                df_1h = self._get_ohlcv(symbol, self.ltf_timeframe, limit=50)

                if df_1d.empty or df_4h.empty or df_1h.empty:
                    continue

                funding_rate = self.exchange.get_funding_rate(symbol)
                if funding_rate is None:
                    continue

                signal = self._analyze_position_futures(df_1d, df_4h, df_1h, symbol, funding_rate)

                if signal:
                    logger.info(f"🎯 إشارة Position Futures على {symbol}: {signal['side']}")
                    self._execute_position_trade(symbol, signal)

            except Exception as e:
                logger.error(f"خطأ في فحص {symbol}: {e}")

    def _analyze_position_futures(self, df_1d, df_4h, df_1h, symbol, funding_rate):
        # 🚨 طبقة 1: حساب التكلفة المتوقعة للـ Funding Rate على 90 يوم
        expected_cost = abs(funding_rate) * (90 * 24 / 8) * self.leverage
        logger.info(f"💰 {symbol}: التكلفة المتوقعة على 3 أشهر = {expected_cost:.2%}")

        if expected_cost > 0.10:
            logger.warning(f"⚠️ {symbol}: تكلفة Funding عالية ({expected_cost:.2%}) → مرفوض")
            send_telegram_alert(
                f"<b>⚠️ رفض صفقة — تكلفة Funding مرتفعة</b>\n"
                f"🪙 {symbol}\n"
                f"💰 التكلفة المتوقعة: {expected_cost:.2%} (الحد الأقصى 10%)\n"
                f"⚠️ تم رفض الصفقة بموجب الطبقة الأولى من الحماية."
            )
            return None

        # 📊 المرحلة 2: تحديد الاتجاه اليومي
        trend = self._get_daily_trend(df_1d)
        if trend == "neutral":
            return None

        # 🎯 المرحلة 3: مناطق 4H
        obs = detect_ob(df_4h)
        fvgs = detect_fvg(df_4h)

        unmitigated_obs = check_ob_mitigation(df_4h, obs)
        unmitigated_fvgs = check_fvg_mitigation(df_4h, fvgs)

        valid_pois: list[dict] = []

        if trend == "bullish":
            valid_pois = [ob for ob in unmitigated_obs if ob["type"] == "bullish"]
            valid_pois += [f for f in unmitigated_fvgs if f["type"] == "bullish"]
        else:
            valid_pois = [ob for ob in unmitigated_obs if ob["type"] == "bearish"]
            valid_pois += [f for f in unmitigated_fvgs if f["type"] == "bearish"]

        if not valid_pois:
            return None

        current_price = df_4h["close"].iloc[-1]
        active_poi = self._find_nearest_poi(current_price, valid_pois)

        if not active_poi:
            return None

        # ⚡ المرحلة 4: التأكيد على 1H
        if not self._check_ltf_confirmation(df_1h, trend):
            return None

        # 🚨 طبقة 2: فحص Funding Rate النهائي
        if trend == "bullish" and funding_rate > self.max_funding_rate_long:
            logger.warning(f"⚠️ {symbol}: Funding Rate {funding_rate:.6f} > {self.max_funding_rate_long} → مرفوض")
            return None
        if trend == "bearish" and funding_rate < self.max_funding_rate_short:
            logger.warning(f"⚠️ {symbol}: Funding Rate {funding_rate:.6f} < {self.max_funding_rate_short} → مرفوض")
            return None

        # 🎯 المرحلة 6: حساب SL و TP
        sl_price = self._calculate_sl_price(active_poi, trend)
        tp_price = self._calculate_tp_price(df_1d, current_price, trend)

        sl_distance = abs(current_price - sl_price)
        tp_distance = abs(tp_price - current_price)
        rr_ratio = tp_distance / sl_distance if sl_distance > 0 else 0

        # 🚨 طبقة 3: R:R عالي الحد أدنى
        if rr_ratio < self.min_rr_ratio:
            logger.info(f"⚠️ {symbol}: R:R {rr_ratio:.2f} < {self.min_rr_ratio} → مرفوض")
            send_telegram_alert(
                f"<b>⚠️ رفض صفقة — R:R منخفض</b>\n"
                f"🪙 {symbol}\n"
                f"⚖️ R:R: {rr_ratio:.2f} (الحد الأدنى {self.min_rr_ratio})\n"
                f"⚠️ تم رفض الصفقة بموجب الطبقة الثالثة من الحماية."
            )
            return None

        return {
            "symbol": symbol,
            "side": "buy" if trend == "bullish" else "sell",
            "entry": current_price,
            "sl": sl_price,
            "tp": tp_price,
            "rr_ratio": rr_ratio,
            "funding_rate": funding_rate,
            "expected_funding_cost": expected_cost,
            "poi_type": active_poi.get("type", "OB"),
        }

    def _execute_position_trade(self, symbol, signal):
        balance = self._get_balance()
        risk_amount = balance * self.risk_per_trade

        sl_distance_pct = abs(signal["entry"] - signal["sl"]) / signal["entry"]
        position_size_usd = risk_amount / sl_distance_pct

        # 🚨 طبقة 4: التحقق من الهامش
        margin_required = position_size_usd / self.leverage
        if margin_required > balance:
            logger.warning(f"⚠️ رصيد غير كافٍ لتنفيذ صفقة على {symbol}")
            return

        logger.warning("=" * 60)
        logger.warning(f"⚠️ تنفيذ Position Trade على FUTURES: {symbol}")
        logger.warning(f"⚠️ الرافعة: {self.leverage}x")
        logger.warning(f"⚠️ Funding Rate: {signal['funding_rate']:.6f}")
        logger.warning(f"⚠️ التكلفة المتوقعة على 3 أشهر: {signal['expected_funding_cost']:.2%}")
        logger.warning(f"⚠️ R:R: {signal['rr_ratio']:.2f}")
        logger.warning("=" * 60)

        order = self.exchange.create_futures_order(
            symbol=symbol,
            side=signal["side"],
            order_type="limit",
            amount=position_size_usd,
            price=signal["entry"],
            leverage=self.leverage,
            margin_type=self.margin_type,
            stop_loss=signal["sl"],
            take_profit=signal["tp"],
        )

        if order:
            logger.info(f"✅ تم فتح Position Trade: {symbol} | R:R: {signal['rr_ratio']:.2f}")
            send_telegram_alert(
                f"<b>🎯 إشارة Position Futures</b>\n"
                f"🪙 {symbol}\n"
                f"📈 الاتجاه: {'شراء' if signal['side'] == 'buy' else 'بيع'}\n"
                f"💰 الدخول: {signal['entry']:.2f}\n"
                f"🛑 SL: {signal['sl']:.2f}\n"
                f"🎯 TP: {signal['tp']:.2f}\n"
                f"⚖️ R:R: {signal['rr_ratio']:.2f}\n"
                f"⚠️ الرافعة: {self.leverage}x\n"
                f"💰 التكلفة المتوقعة: {signal['expected_funding_cost']:.2%}"
            )

    # ─────────────────────────────────────────────
    # 🔧 دوال مساعدة
    # ─────────────────────────────────────────────

    def _get_daily_trend(self, df) -> str:
        if len(df) < 20:
            return "neutral"

        recent = df.tail(20)
        if recent["close"].iloc[-1] > recent["close"].iloc[0]:
            return "bullish"
        elif recent["close"].iloc[-1] < recent["close"].iloc[0]:
            return "bearish"
        return "neutral"

    def _find_nearest_poi(self, current_price, pois):
        for poi in pois:
            poi_price = poi.get("top", poi.get("bottom", 0))
            distance_pct = abs(current_price - poi_price) / current_price
            if distance_pct < 0.05:
                return poi
        return None

    def _check_ltf_confirmation(self, df, trend):
        # Placeholder — يمكن تطويره لفحص CHoCH على 1H
        return True

    def _calculate_sl_price(self, poi, trend):
        poi_price = poi.get("top", poi.get("bottom", 0))
        buffer = 0.02
        if trend == "bullish":
            return poi_price * (1 - buffer)
        else:
            return poi_price * (1 + buffer)

    def _calculate_tp_price(self, df_1d, current_price, trend):
        if trend == "bullish":
            return df_1d["high"].tail(50).max()
        else:
            return df_1d["low"].tail(50).min()

    def _get_balance(self):
        bal = self.exchange.get_balance("futures")
        return bal.get("free", 0)
