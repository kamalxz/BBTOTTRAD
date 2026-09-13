"""📰 news_trader.py — مراقب أخبار ذكي مع تحليل SMC + إرسال أفكار تداول"""
import logging
import time

import pandas as pd

from .base import BaseMode
from core.telegram_alerts import send_telegram_alert
import config
from time_filter import TimeFilter
from ai_news_agent import AINewsAgent

logger = logging.getLogger("news_trader")


class NewsTraderBot(BaseMode):
    name = "NEWS_TRADER"
    description = "📰 مراقب أخبار ذكي — يراقب الأخبار ويُرسل أفكار تداول (بدون تنفيذ تلقائي)"

    timeframe = "5m"
    htf_timeframe = "15m"
    # ⚠️ لا توجد رافعة — هذا مراقب فقط، لا تداول
    leverage = 1
    margin_type = "spot"
    scalp_leverage = 1  # تأكيد — بدون رافعة

    def __init__(self):
        super().__init__()
        self.news_agent = AINewsAgent()
        self._last_alerted: dict[str, float] = {}  # تجنب تكرار التنبيهات
        logger.info("📰 News Trader Bot مفعّل كـ مراقب أخبار آمن")

    def run(self):
        logger.info("📰 بدء تشغيل News Trader Bot (مراقبة فقط، لا تداول تلقائي)...")
        while True:
            try:
                if TimeFilter.is_news_release_soon(minutes=15):
                    self._scan()
                time.sleep(60)
            except KeyboardInterrupt:
                logger.info("🛑 إيقاف News Trader Bot")
                break
            except Exception as e:
                logger.error(f"خطأ في NewsTrader: {e}")
                time.sleep(30)

    def _scan(self):
        """مراقبة الأخبار وتوليد أفكار تداول."""
        for symbol in config.SYMBOLS:
            try:
                sentiment, summary = self.news_agent.analyze_news(symbol)
                logger.info(f"📰 {symbol}: مشاعر = {sentiment:.2f} | {summary}")

                # تجاهل الأخبار السلبية جداً
                if sentiment < config.NEWS_BLOCK_THRESHOLD:
                    logger.info(f"📰 {symbol}: رفض الصفقة (مشاعر سلبية جداً)")
                    continue

                # جلب بيانات 5m
                df_5m = self._get_ohlcv(symbol, "5m", 50)

                # توليد فكرة تداول
                signal = self._analyze_news_trade(df_5m, symbol, sentiment)

                if signal:
                    # منع التكرار: لا ترسل تنبيهًا لنفس الرمز خلال 30 دقيقة
                    last_time = self._last_alerted.get(symbol, 0)
                    if time.time() - last_time < 1800:
                        logger.debug(f"📰 {symbol}: تم تخطيه — تم إرسال تنبيه حديثاً")
                        continue

                    # 📲 إرسال فكرة التداول عبر تلغرام (بدون تنفيذ!)
                    message = (
                        f"<b>📰 فكرة تداول من الأخبار</b>\n\n"
                        f"🪙 {symbol}\n"
                        f"📊 الاتجاه المقترح: {signal.get('reason', 'N/A')}\n"
                        f"🧠 مشاعر الأخبار: {sentiment:.2f}\n"
                        f"📝 الملخص: {summary}\n\n"
                        f"⚠️ <b>تذكير:</b> هذا مرشح للمراجعة اليدوية. "
                        f"استخدم الخيارات التالية للتداول:\n"
                        f"• انتظر 60 ثانية بعد الخبر\n"
                        f"• استخدم رافعة 3x كحد أقصى\n"
                        f"• وقف خسارة ضيق (0.5-1%)"
                    )
                    send_telegram_alert(message)
                    logger.info(f"✅ إرسلت فكرة تداول لـ {symbol} عبر تلغرام")
                    self._last_alerted[symbol] = time.time()

            except Exception as e:
                logger.error(f"⚠️  خطأ في تحليل {symbol}: {e}")

    def _get_ohlcv(self, symbol, timeframe, limit):
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
            return pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
        except Exception as e:
            logger.error(f"❌ فشل جلب البيانات لـ {symbol}: {e}")
            return pd.DataFrame()

    def _analyze_news_trade(self, df, symbol, sentiment):
        """تحليل إشارة تداول بناءً على مشاعر الأخبار + حركة السعر."""
        if df.empty or len(df) < 13:
            return None

        ema_fast = df["close"].ewm(span=5, adjust=False).mean()
        ema_slow = df["close"].ewm(span=13, adjust=False).mean()

        if sentiment > 0 and ema_fast.iloc[-1] > ema_slow.iloc[-1]:
            return {"side": "LONG", "reason": f"📰 مشاعر إيجابية ({sentiment:.2f}) + اختراق EMA"}
        elif sentiment < 0 and ema_fast.iloc[-1] < ema_slow.iloc[-1]:
            return {"side": "SHORT", "reason": f"📰 مشاعر سلبية ({sentiment:.2f}) + انخفاض EMA"}
        return None
