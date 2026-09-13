"""
📱 telegram_control.py — نظام تحكم تلغرام موحد للنظام التداولي v2.0
يدعم التحكم الكامل في جميع البوتات من خلال رسائل تلغرام
يدعم الأوامر التالية:
  /start - بدء التشغيل وإظهار القائمة
  /help - عرض جميع الأوامر
  /start_scalper - تشغيل Scalper Bot
  /start_day - تشغيل Day Trader Bot
  /start_swing - تشغيل Swing Trader Bot
  /start_position_spot - تشغيل Position Trader (Spot)
  /start_position_futures - تشغيل Position Trader (Futures)
  /start_news - تشغيل News Monitor
  /start_all - تشغيل جميع البوتات بالتوازي
  /stop_all - إيقاف جميع البوتات
  /stop_bot [name] - إيقاف بوت محدد
  /status - عرض حالة البوتات
  /scan [symbol] - مسح فوري لرمز محدد
  /dca [capital] [price] - حساب مستويات DCA
  /pnl [entry] [exit] [size] - حساب P&L
"""
import sys
import logging
import threading
import time
import json
from datetime import datetime
from typing import Dict, Optional, Set
from pathlib import Path

import requests

import config_unified as config

sys.stdout.reconfigure(encoding='utf-8')

logger = logging.getLogger("telegram_control")

LOG_DIR = Path("logs") / f"run_{datetime.now().strftime('%Y%m%d')}.log"
LOG_DIR.parent.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR, encoding="utf-8", errors="replace"),
        logging.StreamHandler(sys.stdout),
    ],
)
logging.getLogger("urllib3").setLevel(logging.WARNING)


class TelegramBotController:
    """
    وحدة تحكم تلغرام — تشغيل وإدارة جميع البوتات عبر رسائل تلغرام
    """

    def __init__(self, token: str = None, chat_id: str = None):
        self.token = token or config.TELEGRAM_BOT_TOKEN or config.TELEGRAM_TOKEN_ALIAS
        self.chat_id = chat_id or config.TELEGRAM_CHAT_ID
        
        if not self.token or not self.chat_id:
            logger.error("❌ TELEGRAM_TOKEN أو TELEGRAM_CHAT_ID غير محدد في .env")
            print("⚠️  يرجى تعيين TELEGRAM_TOKEN و TELEGRAM_CHAT_ID في ملف .env")
            self.token = ""
            self.chat_id = ""

        self.is_running = True
        self.last_update_id = 0
        self.bot_threads: Dict[str, threading.Thread] = {}
        self.bot_instances: Dict[str, object] = {}
        self.active_bots: Set[str] = set()

        self._get_last_update_id()

        # بدء مراقب البوتات في الخلفية
        self._start_health_monitor()

        # تسجيل الأوامر المتاحة
        self.commands = {
            "/start": self._cmd_start,
            "/help": self._cmd_help,
            "/status": self._cmd_status,
            "/start_scalper": self._cmd_start_bot("scalper"),
            "/start_day": self._cmd_start_bot("day"),
            "/start_swing": self._cmd_start_bot("swing"),
            "/start_position_spot": self._cmd_start_bot("position_spot"),
            "/start_position_futures": self._cmd_start_bot("position_futures"),
            "/start_news": self._cmd_start_bot("news"),
            "/start_all": self._cmd_start_all,
            "/stop_all": self._cmd_stop_all,
            "/stop_bot": self._cmd_stop_bot,
            "/scan": self._cmd_scan,
            "/dca": self._cmd_dca,
            "/pnl": self._cmd_pnl,
            "/unified": self._cmd_unified,
        }

    def _send_message(self, message: str, disable_notification: bool = False) -> bool:
        """إرسال رسالة إلى تلغرام"""
        if not self.token or not self.chat_id:
            print(f"[Telegram Disabled] {message}")
            return False

        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "HTML",
            "disable_notification": disable_notification,
        }
        try:
            resp = requests.post(url, json=payload, timeout=10)
            return resp.status_code == 200
        except Exception as e:
            logger.error(f"❌ خطأ إرسال التلغرام: {e}")
            return False

    def _get_last_update_id(self):
        """الحصول على آخر update_id لتجنب المعالجة المكررة"""
        try:
            url = f"https://api.telegram.org/bot{self.token}/getUpdates?offset=-1"
            r = requests.get(url, timeout=10).json()
            if r.get('ok') and r.get('result'):
                self.last_update_id = r['result'][-1]['update_id']
                logger.info(f"✅ آخر update_id: {self.last_update_id}")
        except Exception as e:
            logger.debug(f"Failed to get last update_id: {e}")

    def _start_health_monitor(self):
        """بدء مراقبة البوتات في الخلفية — يرسل تنبيهات فقط بدون إعادة تشغيل"""
        threading.Thread(target=self._health_monitor_loop, daemon=True).start()
        logger.info("🩺 مراقب البوتات قيد التشغيل (Health Monitor)")

    def _health_monitor_loop(self):
        """الحلقة الرئيسية للمراقبة — تتحقق من حالة البوتات كل 30 ثانية"""
        reported_down = set()  # تجنب تكرار التنبيهات

        while self.is_running:
            try:
                current_bots = set(self.active_bots)
                threads_to_check = {k: v for k, v in self.bot_threads.items() if k in current_bots}

                for bot_name, thread in threads_to_check.items():
                    if not thread.is_alive():
                        if bot_name not in reported_down:
                            logger.warning(f"🛑 البوت {bot_name} توقف عن العمل!")
                            self._send_message(
                                f"⚠️ <b>تنبيه: البوت توقف</b>\n"
                                f"🪙 البوت: {bot_name}\n"
                                f"⚠️ توقف التشغيل المنير للقلق. يرجى المراجعة اليدوية."
                            )
                            reported_down.add(bot_name)
                    else:
                        reported_down.discard(bot_name)  # تم الاستعادة

            except Exception as e:
                logger.debug(f"Health Monitor error: {e}")

            time.sleep(30)

    def start(self):
        """بدء الاستماع للرسائل في خلفية"""
        threading.Thread(target=self._listen, daemon=True).start()
        logger.info("📱 بدأ الاستماع لأوامر تلغرام")
        self._send_message(
            "🚀 <b>نظام التداول الموحد v2.0</b>\n"
            "📱 التحكم عبر التلغرام مفعل\n\n"
            "📋 أرسل /help لرؤية جميع الأوامر المتاحة"
        )

    def _listen(self):
        """الاستماع للرسائل الواردة"""
        while self.is_running:
            try:
                url = (
                    f"https://api.telegram.org/bot{self.token}/getUpdates"
                    f"?offset={self.last_update_id + 1}&timeout=30"
                )
                r = requests.get(url, timeout=35).json()
                if r.get('ok') and r.get('result'):
                    for upd in r['result']:
                        self.last_update_id = upd['update_id']
                        text = upd.get('message', {}).get('text', '').strip()
                        if text:
                            self._handle_command(text)
            except Exception as e:
                logger.debug(f"Telegram poll error: {e}")
                time.sleep(5)

    def _handle_command(self, text: str):
        """معالجة الأوامر"""
        logger.info(f"📩 استقبال أمر: {text}")
        
        # تحويل الأمر إلى شكل موحد
        cmd = text.split()[0].lower() if text else ""
        
        if cmd in self.commands:
            try:
                self.commands[cmd](text)
            except Exception as e:
                logger.error(f"❌ خطأ في معالجة الأمر {cmd}: {e}")
                self._send_message(f"❌ خطأ في الأمر: {str(e)}")
        else:
            self._send_message(
                "⚠️ أمر غير معروف.\n"
                "📋 أرسل /help لرؤية الأوامر المتاحة"
            )

    def _cmd_start(self, text: str = None):
        """بدء التشغيل"""
        self._send_message(self._help_text())

    def _cmd_help(self, text: str = None):
        """عرض المساعدة"""
        self._send_message(self._help_text())

    def _help_text(self) -> str:
        return (
            "🤖 <b>نظام التداول الموحد v2.0</b>\n\n"
            "📋 <b>الأوامر المتاحة:</b>\n\n"
            "⚙️ <b>إدارة البوتات:</b>\n"
            "/start_scalper - تشغيل Scalper Bot\n"
            "/start_day - تشغيل Day Trader Bot\n"
            "/start_swing - تشغيل Swing Trader Bot\n"
            "/start_position_spot - تشغيل Position Trader (Spot)\n"
            "/start_position_futures - تشغيل Position Trader (Futures)\n"
            "/start_news - تشغيل News Monitor\n"
            "/start_all - تشغيل جميع البوتات\n\n"
            "🛑 <b>إيقاف:</b>\n"
            "/stop_all - إيقاف جميع البوتات\n"
            "/stop_bot [name] - إيقاف بوت محدد\n\n"
            "📊 <b>أدوات التحليل:</b>\n"
            "/scan [symbol] - مسح فوري (مثال: /scan BTCUSDT)\n"
            "/dca [capital] [price] - حساب مستويات DCA\n"
            "/pnl [entry] [exit] [size] - حساب P&L\n\n"
            "📈 <b>الحالة:</b>\n"
            "/status - حالة البوتات النشطة\n\n"
            "🔄 <b>النظام الموحد:</b>\n"
            "/unified - تشغيل النظام الموحد التلقائي"
        )

    def _cmd_status(self, text: str = None):
        """عرض الحالة"""
        if not self.active_bots:
            self._send_message("📊 <b>لا توجد بوتات نشطة حالياً</b>\n\nأرسل /start_all أو أحد أوامر التشغيل")
        else:
            status = "📊 <b>البوتات النشطة:</b>\n\n"
            for name in self.active_bots:
                status += f"  ✅ {name}\n"
            status += f"\n🕐 آخر تحديث: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            self._send_message(status)

    def _cmd_start_bot(self, bot_type: str):
        """إنشاء دالة لتشغيل بوت محدد"""
        def handler(text: str = None):
            if bot_type in self.active_bots:
                self._send_message(f"⚠️ {bot_type} قيد التشغيل بالفعل!")
                return
            
            self._send_message(f"🔄 جاري تشغيل {bot_type}...")
            
            try:
                bot = self._create_bot(bot_type)
                if bot is None:
                    self._send_message(f"❌ فشل إنشاء {bot_type}")
                    return
                
                def run_bot():
                    try:
                        bot.run()
                    except Exception as e:
                        logger.error(f"❌ خطأ في {bot_type}: {e}")
                        self._send_message(f"❌ خطأ في {bot_type}: {e}")
                    finally:
                        self.active_bots.discard(bot_type)
                
                thread = threading.Thread(target=run_bot, name=f"Bot_{bot_type}", daemon=True)
                thread.start()
                self.bot_threads[bot_type] = thread
                self.bot_instances[bot_type] = bot
                self.active_bots.add(bot_type)
                
                self._send_message(f"✅ تم تشغيل {bot_type} بنجاح!")
                
            except Exception as e:
                logger.error(f"❌ خطأ في تشغيل {bot_type}: {e}")
                self._send_message(f"❌ فشل تشغيل {bot_type}: {e}")
        
        return handler

    def _cmd_start_all(self, text: str = None):
        """تشغيل جميع البوتات بالتوازي"""
        self._send_message("🚀 جاري تشغيل جميع البوتات...")
        
        all_bots = ["scalper", "day", "swing", "position_spot", "position_futures", "news"]
        started = []
        
        for bot_type in all_bots:
            if bot_type in self.active_bots:
                continue
            try:
                bot = self._create_bot(bot_type)
                if bot is None:
                    continue
                
                def run_bot(b=bot, bt=bot_type):
                    try:
                        b.run()
                    except Exception as e:
                        logger.error(f"❌ خطأ في {bt}: {e}")
                        self._send_message(f"❌ خطأ في {bt}: {e}")
                    finally:
                        self.active_bots.discard(bt)
                
                thread = threading.Thread(target=run_bot, name=f"Bot_{bot_type}", daemon=True)
                thread.start()
                self.bot_threads[bot_type] = thread
                self.bot_instances[bot_type] = bot
                self.active_bots.add(bot_type)
                started.append(bot_type)
                
            except Exception as e:
                logger.error(f"❌ فشل تشغيل {bot_type}: {e}")
            
            time.sleep(1)  # تجنب الازدحام
        
        if started:
            self._send_message(f"✅ تم تشغيل {len(started)} بوتات:\n{', '.join(started)}")
        else:
            self._send_message("⚠️ لم يتم تشغيل أي بوتات — ربما جميعها نشطة بالفعل")

    def _cmd_stop_all(self, text: str = None):
        """إيقاف جميع البوتات"""
        if not self.active_bots:
            self._send_message("⚠️ لا توجد بوتات نشطة")
            return
        
        self.active_bots.clear()
        self.bot_threads.clear()
        self.bot_instances.clear()
        
        self._send_message("🛑 تم إيقاف جميع البوتات ✓")
        logger.info("🛑 تم إيقاف جميع البوتات عبر تلغرام")

    def _cmd_stop_bot(self, text: str = None):
        """إيقاف بوت محدد"""
        parts = text.split()
        if len(parts) < 2:
            self._send_message("⚠️ الاستخدام: /stop_bot [name]\n\nالبوتات النشطة: " + ", ".join(self.active_bots) if self.active_bots else "لا توجد بوتات نشطة")
            return
        
        bot_name = parts[1]
        if bot_name in self.active_bots:
            self.active_bots.discard(bot_name)
            self.bot_threads.pop(bot_name, None)
            self.bot_instances.pop(bot_name, None)
            self._send_message(f"🛑 تم إيقاف {bot_name} ✓")
        else:
            self._send_message(f"⚠️ {bot_name} غير مفعال. البوتات النشطة: {', '.join(self.active_bots)}")

    def _cmd_scan(self, text: str = None):
        """مسح فوري لرمز محدد"""
        parts = text.split()
        symbol = parts[1] if len(parts) > 1 else "BTCUSDT"
        
        self._send_message(f"🔍 جاري مسح {symbol}...")
        
        try:
            from unified_trading_system import UnifiedTradingSystem
            system = UnifiedTradingSystem(mode="swing", account_equity=100.0)
            result = system.run_scan(symbol)
            
            if result["status"] == "trade_signal":
                sig = result["signal"]
                msg = (
                    f"✅ <b>📊 إشارة تداول مؤهلة</b>\n\n"
                    f"🪙 الزوج: {symbol}\n"
                    f"📊 الاتجاه: {sig['side']}\n"
                    f"💰 الدخول: {sig['entry_price']:.2f}\n"
                    f"🛑 SL: {sig['sl_price']:.2f}\n"
                    f"🎯 TP: {sig['tp_price']:.2f}\n"
                    f"⚖️ R:R: {sig['rr']:.2f}:1\n"
                    f"📈 النقاط: {result['score']}/10\n"
                    f"💪 الثقة: {result['confidence']*100:.0f}%"
                )
                self._send_message(msg)
            elif result["status"] == "no_trade":
                msg = (
                    f"⚪ <b>NO TRADE</b>\n\n"
                    f"🪙 الزوج: {symbol}\n"
                    f"📊 النقاط: {result.get('score', 0)}/10\n"
                    f"📋 الأسباب: {result.get('reasons', [])}"
                )
                self._send_message(msg)
            elif result["status"] == "rejected":
                msg = (
                    f"🔴 <b>مرفوض</b>\n\n"
                    f"🪙 الزوج: {symbol}\n"
                    f"⚠️ الأسباب: {result.get('reasons', [])}"
                )
                self._send_message(msg)
            else:
                self._send_message(f"⚠️ نتيجة غير معروفة: {result}")
                
        except Exception as e:
            logger.error(f"❌ خطأ في الفحص: {e}")
            self._send_message(f"❌ خطأ في الفحص: {str(e)}")

    def _cmd_dca(self, text: str = None):
        """حساب مستويات DCA"""
        parts = text.split()
        capital = float(parts[1]) if len(parts) > 1 else 100
        price = float(parts[2]) if len(parts) > 2 else 60000
        
        from core.unified_risk import UnifiedRiskEngine
        engine = UnifiedRiskEngine(mode="position_spot")
        levels = engine.calculate_dca_levels(capital, price)
        
        msg = f"📊 <b>محسوب DCA</b> — رأس مال: {capital} USDT، السعر: {price}$/BTC\n\n"
        for lvl in levels:
            msg += (
                f"المستوى {lvl['level']}: {lvl['allocation']:.1f} USDT @ {lvl['price']:.1f}$ "
                f"→ {lvl['btc_amount']:.6f} BTC\n"
            )
        msg += f"\n📈 المتوسط التراكمي: {sum(l['allocation'] for l in levels) / sum(l['btc_amount'] for l in levels):.1f}$"
        
        self._send_message(msg)

    def _cmd_pnl(self, text: str = None):
        """حساب P&L"""
        parts = text.split()
        if len(parts) < 4:
            self._send_message("⚠️ الاستخدام: /pnl [entry] [exit] [size]\nمثال: /pnl 50000 52000 1")
            return
        
        entry = float(parts[1])
        exit_price = float(parts[2])
        size = float(parts[3])
        
        pnl = (exit_price - entry) * size
        roi = pnl / (entry * size) * 100
        direction = "ربح" if pnl > 0 else "خسارة"
        
        emoji = "🟢" if pnl > 0 else "🔴"
        msg = (
            f"{emoji} <b>حساب P&L</b>\n\n"
            f"🎯 الدخول: {entry:.2f}\n"
            f"🎯 الخروج: {exit_price:.2f}\n"
            f"💰 الحجم: {size:.6f} BTC\n\n"
            f"📊 {direction}: {abs(pnl):.2f} USDT\n"
            f"📈 ROI: {roi:.2f}%\n"
            f"⚖️ R:R: {roi:.2f}%"
        )
        self._send_message(msg)

    def _cmd_unified(self, text: str = None):
        """تشغيل النظام الموحد التلقائي"""
        self._send_message("🚀 جاري تشغيل النظام الموحد التلقائي...")
        
        try:
            from unified_trading_system import UnifiedTradingSystem
            system = UnifiedTradingSystem(mode="swing", account_equity=100.0)
            
            def run_system():
                try:
                    system.run_continuous(symbols=config.SYMBOLS, interval=60)
                except Exception as e:
                    logger.error(f"❌ خطأ في النظام الموحد: {e}")
                    self._send_message(f"❌ خطأ في النظام الموحد: {e}")
                finally:
                    self.active_bots.discard("unified")
            
            thread = threading.Thread(target=run_system, name="UnifiedSystem", daemon=True)
            thread.start()
            self.bot_threads["unified"] = thread
            self.active_bots.add("unified")
            
            self._send_message("✅ تم تشغيل النظام الموحد التلقائي!\nسيتم مسح الأسواق كل 60 ثانية.")
            
        except Exception as e:
            logger.error(f"❌ فشل تشغيل النظام الموحد: {e}")
            self._send_message(f"❌ فشل تشغيل النظام الموحد: {e}")

    def _create_bot(self, bot_type: str):
        """إنشاء مثيل بوت حسب النوع"""
        try:
            if bot_type == "scalper":
                from modes.scalper import ScalperBot
                return ScalperBot()
            elif bot_type == "day":
                from modes.day_trader import DayTraderBot
                return DayTraderBot()
            elif bot_type == "swing":
                from modes.swing_trader import SwingTraderBot
                return SwingTraderBot()
            elif bot_type == "position_spot":
                from modes.position_trader import PositionTraderBot
                return PositionTraderBot()
            elif bot_type == "position_futures":
                from modes.position_trader_futures import PositionTraderFuturesBot
                return PositionTraderFuturesBot()
            elif bot_type == "news":
                from news_alert_agent import NewsAlertAgent
                return NewsAlertAgent()
            else:
                return None
        except Exception as e:
            logger.error(f"❌ فشل إنشاء {bot_type}: {e}")
            return None

    def stop(self):
        """إيقاف التحكم بالكامل"""
        self.is_running = False
        self._send_message("🛑 تم إيقاف نظام التحكم بالتلغرام")
        logger.info("🛑 تم إيقاف TelegramBotController")


def main():
    """تشغيل نظام التحكم بالتلغرام"""
    print("🚀 تشغيل نظام التحكم بتلغرام للنظام الموحد v2.0...")
    
    controller = TelegramBotController()
    if not controller.token:
        print("❌ لا يمكن بدء التشغيل: TELEGRAM_TOKEN غير محدد")
        return

    # ✅ فحص البروكسي قبل التشغيل (إن كان مفعّلاً)
    if config.USE_PROXY:
        print("🌍 جاري فحص البروكسي...")
        from core.ip_utils import test_proxy_connection
        if not test_proxy_connection():
            print("❌ فشل فحص البروكسي — يرجى التحقق من الإعدادات")
            controller._send_message("❌ فشل فحص البروكسي — تم إيقاف التشغيل")
            return
        else:
            print("✅ البروكسي يعمل بشكل صحيح")

    # ✅ فحص بنانس — التحقق من أن الـ IP مصرح به (يعمل على جميع الأوضاع)
    print("🏦 جاري فحص الاتصال ببنانز...")
    from core.exchange import BinanceExchange
    try:
        ex = BinanceExchange()
        balance = ex.get_balance("futures")
        if balance["total"] == 0 and balance["free"] == 0:
            print("⚠️ تحذير: الرصيد يبدو 0 — تحقق من الإعدادات")
        else:
            print(f"✅ متصل ببنانز — الرصيد: {balance['total']:.2f} USDT")
    except Exception as e:
        error_msg = str(e)
        if "-2015" in error_msg or "Invalid" in error_msg or "permissions" in error_msg.lower():
            from core.ip_utils import get_proxy_ip
            current_ip = get_proxy_ip()
            print(f"❌ بنانز رفض الـ IP: {current_ip}")
            controller._send_message(
                f"<b>❌ فشل الاتصال ببنانز — IP غير مصرح به</b>\n"
                f"🌍 الـ IP الحالي: <code>{current_ip}</code>\n\n"
                f"📝 أضف هذا الـ IP إلى Binance API Management:\n"
                f"https://www.binance.com/en/my/settings/settings/api-management"
            )
            return
        else:
            print(f"⚠️ تحذير: خطأ في بنانز — {e}")
            print("ملاحظة: قد لا يكون الـ IP مسبباً في المشكلة")

    controller.start()
    print("✅ نظام التحكم بالتلغرام قيد التشغيل")
    print("📱 أرسل أي أمر من القائمة إلى البوت")
    print("🛑 اضغط Ctrl+C للإيقاف")
    
    try:
        while True:
            time.sleep(30)
    except KeyboardInterrupt:
        print("\n🛑 إيقاف النظام...")
        controller.stop()


if __name__ == "__main__":
    main()
