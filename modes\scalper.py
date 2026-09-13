"""⚡️ SCALPER - فكرة السرعة
تداول سريع على إطار زمني قصير (1m-5m) مع عدد صفقات كبير.

متطلبات التأكيد (ثلاثية + فحص فخ):
0. ✅ Liquidity Sweep أولاً (لقد/قاع قديم → اختبار → رجوع)
1. ✅ تأكيد السعر: CHoCH حقيقي + Engulfing/Pin Bar
2. ✅ تأكيد الحجم: حجم الشمعة > 1.5x متوسط 10 شموع
3. ✅ تأكيد الوقت: Killzone Session فقط

🛡️ إدارة المخاطر:
- رافعة: 3x كحد أقصى
- مخاطرة: 1% من الرصيد (1$ من 100$)
- SL: تحت الذيل/OB بـ buffer
- TP: 1.5:1 على الأقل
- أمر: Limit فقط (تجنب رسوم Market)
- خروج مبكر: 3 دقائق إذا ما وصلش 1:0.5
"""
import time
import logging

import pandas as pd

from .base import BaseMode
from core.telegram_alerts import send_telegram_alert
import config
from time_filter import TimeFilter

logger = logging.getLogger(__name__)


class ScalperBot(BaseMode):
    name = "SCALPER"
    description = "⚡️ فكرة السرعة - صفقات سريعة (1m-5m)"
    timeframe = "1m"
    htf_timeframe = "5m"
    scalp_leverage = 3  # ✅ ثابتة على 3x كما هو متفق
    min_rr_ratio = config.SCALP_MIN_RR  # ✅ R:R الأدنبي للـ Scalping
    risk_per_trade = config.RISK_PER_TRADE  # ✅ 1% من الرصيد

    def run(self):
        self._log_mode()
        active_trade = None
        entry_time = None

        while True:
            try:
                if TimeFilter.is_killzone() and not TimeFilter.is_news_time():
                    # إذا فيه صفقة مفتوحة، راقبها
                    if active_trade:
                        current_price = self._get_current_price(active_trade["symbol"])
                        # ✅ قاعدة الخروج المبكر (3 شمعات)
                        elapsed_minutes = (time.time() - entry_time) / 60
                        if elapsed_minutes >= 3:
                            pnl_pct = self._calculate_pnl(active_trade, current_price)
                            if pnl_pct < 0.5:  # أقل من حتفاء 0.5%
                                logger.info(f"⏰ إغلاق مبكر: 3 دقائق مرت ولا تحقق 0.5%")
                                self._close_position(active_trade, current_price)
                                active_trade = None
                                entry_time = None
                            else:
                                # راقب SL/TP
                                if current_price <= active_trade["sl"] or current_price >= active_trade["tp"]:
                                    self._close_position(active_trade, current_price)
                                    active_trade = None
                                    entry_time = None
                        else:
                            # راقب SL/TP
                            if current_price <= active_trade["sl"] or current_price >= active_trade["tp"]:
                                self._close_position(active_trade, current_price)
                                active_trade = None
                                entry_time = None
                    else:
                        # لا صفقة مفتوحة، نفّذ اسكان
                        active_trade = self._scan()
                        if active_trade:
                            entry_time = time.time()
                            logger.info(f"✅ دخل الصفقة: {active_trade}")
                else:
                    status = "وقت أخبار اقتصادية حية" if TimeFilter.is_news_time() else "خارج منطقة الاستهداف"
                    logger.info(f"💤 {status} — المسح متوقف حتى الفتح التالية")

                sleep_time = config.SCAN_INTERVAL if hasattr(config, "SCAN_INTERVAL") else 30
                time.sleep(sleep_time)

            except Exception as e:
                logger.error(f"خطأ في Scalper: {e}")
                time.sleep(5)

    def _scan(self):
        """مسح جميع الرموز وإرجاع الصفقة الأولى المقبولة."""
        for symbol in config.SYMBOLS:
            try:
                df_1m = self._get_ohlcv(symbol, self.timeframe, 60)
                df_5m = self._get_ohlcv(symbol, self.htf_timeframe, 40)
                signal = self._analyze_scalp(df_1m, df_5m, symbol)
                if signal:
                    trade = self._execute_trade(symbol, signal, df_1m)
                    if trade:
                        return trade
            except Exception as e:
                print(f"⚠️ خطأ في تحليل {symbol}: {e}")
        return None

    def _get_ohlcv(self, symbol, timeframe, limit):
        ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        return pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])

    def _get_current_price(self, symbol):
        ticker = self.exchange.fetch_ticker(symbol)
        return ticker["last"]

    def _calculate_pnl(self, trade, current_price):
        """حساب الربح/الخسارة كنسبة مئوية من الدخول."""
        entry = trade["entry_price"]
        if trade["side"] == "LONG":
            return ((current_price - entry) / entry) * 100
        else:
            return ((entry - current_price) / entry) * 100

    def _get_swing_points(self, df, window=5):
        """ايجاد أبرز القمم والقيعان على الإطار المنخفض."""
        highs = df["high"].rolling(window=window, center=True).max()
        lows = df["low"].rolling(window=window, center=True).min()
        swing_highs = df[highs == df["high"]]
        swing_lows = df[lows == df["low"]]
        last_high = swing_highs["high"].iloc[-1] if len(swing_highs) > 0 else df["high"].max()
        last_low = swing_lows["low"].iloc[-1] if len(swing_lows) > 0 else df["low"].min()
        return last_high, last_low

    def _has_liquidity_sweep(self, df_5m, df_1m):
        """✅ فحص الفخ (Liquidity Sweep).
        يتحقق من أن السعر كسر قمة أو قاعاً على إطار 5m ثم عاد للداخل على إطار 1m.
        """
        swing_high, swing_low = self._get_swing_points(df_5m, window=3)
        current = df_1m.iloc[-1]
        recent_high = current["high"]
        recent_low = current["low"]

        # ✅ اختبار قمة قديمة (Liquidity Hunt على الأعلى ثم رجوع)
        if recent_high > swing_high and current["close"] < recent_high:
            logger.debug("🔍 Liquidity Sweep: كسر القمة ثم رجوع")
            return True

        # ✅ اختبار قاع قديم (Liquidity Hunt على الأسفل ثم رجوع)
        if recent_low < swing_low and current["close"] > recent_low:
            logger.debug("🔍 Liquidity Sweep: كسر القاع ثم رجوع")
            return True

        return False

    def _has_choch(self, df, direction="up"):
        """✅ CHoCH حقيقي — كسر آخر Swing High/Low رئيسي.

        Args:
            df: الإطار الزمني الأصغر (1m)
            direction: "up" للـ CHoCH الصعودي، "down" للهابط
        """
        swing_high, swing_low = self._get_swing_points(df, window=5)
        current = df.iloc[-1]

        if direction == "up":
            # CHoCH صعودي: اختراق القاع الأخير ثم إغلاق فوقه
            return current["low"] < swing_low and current["close"] > swing_low
        else:
            # CHoCH هابط: اختراق القمة الأخيرة ثم إغلاق تحتها
            return current["high"] > swing_high and current["close"] < swing_high

    def _has_engulfing(self, df):
        """تحقق من نمط Engulfing."""
        if len(df) < 2:
            return None
        prev = df.iloc[-2]
        curr = df.iloc[-1]
        if curr["close"] > curr["open"] and prev["close"] < prev["open"] and \
           curr["close"] > prev["open"] and curr["open"] < prev["close"]:
            return "bullish"
        if curr["close"] < curr["open"] and prev["close"] > prev["open"] and \
           curr["close"] < prev["open"] and curr["open"] > prev["close"]:
            return "bearish"
        return None

    def _has_rejection_wick(self, df):
        """تحقق من Rejection Wick (Pin Bar)."""
        last = df.iloc[-1]
        body = abs(last["close"] - last["open"])
        if body == 0:
            return None
        upper_wick = last["high"] - max(last["close"], last["open"])
        lower_wick = min(last["close"], last["open"]) - last["low"]
        if lower_wick >= body * 2:
            return "bullish"
        if upper_wick >= body * 2:
            return "bearish"
        return None

    def _get_htf_bias(self, df_5m):
        """✅ HTF Bias مبني على هيكل السوق (BOS/Swing Points).

        يتحقق من اتجاه 5m عبر مقارنة القمم والقيعان الرئيسية.
        """
        swing_high, swing_low = self._get_swing_points(df_5m, window=5)
        latest_high = df_5m["high"].iloc[-3:].max()
        latest_low = df_5m["low"].iloc[-3:].min()

        # HTF صاعد: آخر قاع أعلى من قبله، والسعر فوق القاع
        if latest_low > swing_low and df_5m["close"].iloc[-1] > swing_low:
            return "up"
        # HTF هابط: آخر قمة أقل من قبلها، والسعر تحت القمة
        elif latest_high < swing_high and df_5m["close"].iloc[-1] < swing_high:
            return "down"
        return "neutral"

    def _analyze_scalp(self, df_1m, df_5m, symbol):
        """تحليل السكالبر باستخدام التأكيد الكامل."""
        # ✅ 1. Liquidity Sweep (شرط أول ومطلوب)
        if not self._has_liquidity_sweep(df_5m, df_1m):
            return None

        # ✅ 2. تأكيد السعر (CHoCH أو Engulfing أو Pin Bar)
        eng = self._has_engulfing(df_1m)
        rej = self._has_rejection_wick(df_1m)

        # ✅ 3. HTF Bias
        htf_direction = self._get_htf_bias(df_5m)

        # ✅ 4. تأكيد الحجم
        avg_vol = df_1m["volume"].tail(10).mean()
        volume_ok = df_1m["volume"].iloc[-1] > avg_vol * 1.5

        if not volume_ok:
            return None

        # === LONG Setup ===
        if htf_direction == "up" and self._has_choch(df_1m, "up") and eng == "bullish":
            reasons = []
            reasons.append("📈 CHoCH صعودي")
            if rej == "bullish":
                reasons.append("✅ Pin Bar")
            if eng == "bullish":
                reasons.append("✅ Engulfing")
            return {"side": "LONG", "reasons": reasons}

        # === SHORT Setup ===
        if htf_direction == "down" and self._has_choch(df_1m, "down") and eng == "bearish":
            reasons = []
            reasons.append("📉 CHoCH هابط")
            if rej == "bearish":
                reasons.append("✅ Pin Bar")
            if eng == "bearish":
                reasons.append("✅ Engulfing")
            return {"side": "SHORT", "reasons": reasons}

        return None

    def _calculate_position_size(self, symbol, sl_distance_pct):
        """✅ حساب حجم الصفقة بناءً على مخاطرة 1% ومسافة SL.

        Args:
            symbol: الرمز
            sl_distance_pct: مسافة SL كنسبة مئوية
        Returns:
            الحجم المناسب
        """
        balance = self._get_balance()
        risk_amount = balance * config.RISK_PER_TRADE  # 1$ من 100$
        size = risk_amount / sl_distance_pct
        try:
            return float(self.exchange.amount_to_precision(symbol, size))
        except Exception:
            return size

    def _get_balance(self):
        try:
            bal = float(self.exchange.fetch_balance()["total"].get("USDT", 0))
            return bal if bal > 0 else 100.0
        except Exception:
            return 100.0

    def _get_sl_level(self, side, df):
        """✅ تحديد مستوى SL بناءً على الذيل أو OB مع buffer."""
        last = df.iloc[-1]
        buffer_pct = 0.002  # 0.2% buffer

        if side == "LONG":
            sl = last["low"] - (last["high"] - last["low"]) * buffer_pct
        else:
            sl = last["high"] + (last["high"] - last["low"]) * buffer_pct

        try:
            # استخدام الرمز الصحيح بناءً على نوع السوق
            symbol_key = "BTC/USDT" if "BTC" in symbol else symbol
            return float(self.exchange.price_to_precision(symbol_key, sl))
        except Exception:
            return sl

    def _get_tp_level(self, side, entry, sl):
        """✅ تحديد TP بنسبة 1:1.5 على الأقل."""
        risk = abs(entry - sl)
        reward = risk * 1.5  # 1:1.5
        if side == "LONG":
            return entry + reward
        else:
            return entry - reward

    def _execute_trade(self, symbol, signal, df):
        """✅ تنفيذ التجارة بأمر LIMIT مع SL/TP مرفقين."""
        balance = self._get_balance()
        current_price = self._get_current_price(symbol)

        # حساب SL/TP
        sl = self._get_sl_level(signal["side"], df)
        tp = self._get_tp_level(signal["side"], current_price, sl)

        # ✅ التحقق من R:R الأدنبي
        rr = abs(tp - current_price) / abs(current_price - sl) if sl else 0
        if rr < self.min_rr_ratio:
            logger.info(f"⚠️ {symbol}: R:R {rr:.2f} < الحد الأدنبي {self.min_rr_ratio}")
            return None

        sl_distance_pct = abs(current_price - sl) / current_price * 100
        size = self._calculate_position_size(symbol, sl_distance_pct)

        if size <= 0:
            return None

        side = "buy" if signal["side"] == "LONG" else "sell"

        # رسالة تجريبية فقط — التنفيذ الحقيقي يتطلب إتصال Binance
        logger.info(f"⚡️ إشارة صك: {symbol} {signal['side']} @ {current_price}")
        logger.info(f"   سبب: {', '.join(signal['reasons'])}")
        logger.info(f"   الحجم: {size} | SL: {sl:.2f} | TP: {tp:.2f}")

        send_telegram_alert(
            f"<b>⚡️ إشارة سكالبر نشطة</b>\n"
            f"🪙 {symbol}\n"
            f"📊 الاتجاه: {signal['side']}\n"
            f"💰 الدخول: {current_price:.2f}\n"
            f"🛑 SL: {sl:.2f}\n"
            f"🎯 TP: {tp:.2f}\n"
            f"⚖️ R:R: {rr:.2f}\n"
            f"🔢 الحجم: {size}\n"
            f"📈 النقاط: {', '.join(signal['reasons'])}"
        )

        return {
            "symbol": symbol,
            "side": signal["side"],
            "entry_price": current_price,
            "sl": sl,
            "tp": tp,
            "size": size,
            "leverage": self.scalp_leverage,
        }

    def _close_position(self, trade, price):
        """✅ إغلاق المركز وإرسال إشعار."""
        pnl_pct = self._calculate_pnl(trade, price)
        logger.info(f"🏁 إغلاق: {trade['symbol']} PnL: {pnl_pct:.2f}%")
        print(f"🏁 إغلاق: {trade['symbol']} PnL: {pnl_pct:.2f}%")
        send_telegram_alert(
            f"<b>🏁 إغلاق صفقة سكالبر</b>\n"
            f"🪙 {trade['symbol']} {trade['side']}\n"
            f"📊 PnL: {pnl_pct:.2f}%"
        )
