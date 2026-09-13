"""🚀 main.py — نقطة الدخول الموحدة لتشغيل جميع البوتات الخمسة (محدث بالتشغيل المتوازي + تلغرام)"""
import sys

# إصلاح ترميز Windows لدعم الإيموجي والعربية
if sys.stdout.encoding in ("cp1252", "cp1256"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import logging
from pathlib import Path
from datetime import datetime

import config

# 📲 استيراد نظام التنبيهات
try:
    from core.telegram_alerts import send_telegram_alert
except ImportError:
    send_telegram_alert = lambda msg, **kw: print(f"[TELEGRAM DISABLED] {msg}")

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
logger = logging.getLogger("main")


def menu():
    print("\n" + "=" * 60)
    print("🤖 نظام التداول الآلي المتكامل - Crypto Trading Bot")
    print("=" * 60)
    print("1️⃣  ⚡️  Scalper Bot (Futures - Demo Only)")
    print("2️⃣  🏹  Day Trader Bot (Futures - 15m/5m)")
    print("3️⃣  🌊  Swing Trader Bot (Futures - 4H/1D)")
    print("4️⃣  🏦  Position Trader Bot (Spot - DCA)")
    print("5️⃣  🏦⚠️  Position Trader Futures (5 طبقات)")
    print("6️⃣  🧵  تشغيل كل البوتات بالتوازي")
    print("7️⃣  📰  News Alert Agent (مراقبة الأخبار)")
    print("8️⃣  📈  News Trader Bot (تداول الأخبار)")
    print("9️⃣  📰  News Monitor (مراقبة فقط)")
    print("🔟  🌐  نظام التحكم بالتلغرام الموحد v2.0")
    print("0️⃣  🚪  خروج")
    print("=" * 60)
    return input("👉 اختر رقمًا [0-9]: ").strip()


def run_single_bot(choice):
    choice_map = {
        "1": ("modes.scalper", "ScalperBot"),
        "2": ("modes.day_trader", "DayTraderBot"),
        "3": ("modes.swing_trader", "SwingTraderBot"),
        "4": ("modes.position_trader", "PositionTraderBot"),
        "5": ("modes.position_trader_futures", "PositionTraderFuturesBot"),
    }

    module_path, class_name = choice_map[choice]
    logger.info(f"🔄 تحميل {class_name} من {module_path}")

    try:
        mod = __import__(module_path, fromlist=[class_name])
        bot_cls = getattr(mod, class_name)
        bot = bot_cls()
        logger.info(f"▶️  بدء تشغيل {class_name}")
        send_telegram_alert(f"🚀 تم تشغيل {class_name} على {config.SYMBOLS[0]}", disable_notification=True)
        bot.run()
    except ImportError as e:
        logger.error(f"❌ فشل تحميل الوحدة {module_path}: {e}")
        send_telegram_alert(f"❌ فشل تشغيل {class_name}: {e}")
    except AttributeError:
        logger.error(f"❌ الصنف {class_name} غير موجود في {module_path}")
        send_telegram_alert(f"❌ الصنف {class_name} غير موجود في {module_path}")
    except KeyboardInterrupt:
        logger.info("🛑 تم إيقاف البوت بواسطة المستخدم.")
        send_telegram_alert(f"🛑 إيقاف {class_name} بواسطة المستخدم.")
    except Exception as e:
        logger.error(f"❌ خطأ غير متوقع في {class_name}: {e}")
        send_telegram_alert(f"❌ خطأ في {class_name}: {e}")


def run_parallel():
    """🚀 تشغيل كل البوتات في خيوط مستقلة (Threading)"""
    import threading

    from modes.scalper import ScalperBot
    from modes.day_trader import DayTraderBot
    from modes.swing_trader import SwingTraderBot
    from modes.position_trader import PositionTraderBot
    from modes.position_trader_futures import PositionTraderFuturesBot
    from modes.news_trader import NewsTraderBot
    from news_alert_agent import NewsAlertAgent

    bots = [
        ("ScalerBot", ScalperBot),
        ("DayTrader", DayTraderBot),
        ("SwingTrader", SwingTraderBot),
        ("PositionSpot", PositionTraderBot),
        ("PositionFutures", PositionTraderFuturesBot),
        ("NewsMonitor", NewsAlertAgent),
    ]

    threads = []
    for name, bot_cls in bots:
        try:
            bot = bot_cls()
            t = threading.Thread(target=bot.run, name=name, daemon=True)
            t.start()
            threads.append(t)
            logger.info(f"🧵 تم بدء {name} في خيط منفصل")
        except Exception as e:
            logger.error(f"❌ فشل تشغيل {name}: {e}")
            send_telegram_alert(f"❌ فشل تشغيل {name}: {e}")

    logger.warning("⚠️ جميع البوتات تعمل في الخلفية. اضغط Ctrl+C للإيقاف.")
    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        logger.info("🛑 إيقاف جميع البوتات...")
        send_telegram_alert("🛑 إيقاف جميع البوتات بالتوازي")


def main():
    logger.info("🚀 تشغيل نظام التداول الآلي المتكامل...")
    send_telegram_alert("🚀 نظام التداول الآلي بدأ التشغيل — القائمة جاهزة")

    while True:
        try:
            choice = menu()

            if choice == "0":
                logger.info("🛑 إيقاف النظام.")
                send_telegram_alert("🛑 إيقاف نظام التداول الآلي")
                break

            elif choice == "6":
                run_parallel()

            elif choice == "7":
                from news_alert_agent import NewsAlertAgent
                logger.info("🚀 بدء تشغيل News Alert Agent...")
                send_telegram_alert("📰 تم تفعيل نظام مراقبة الأخبار الذكي")
                agent = NewsAlertAgent()
                agent.run()

            elif choice == "8":
                from modes.news_trader import NewsTraderBot
                logger.warning("⚠️ تشغيل News Trader Bot — تداول الأخبار (عالي المخاطر!)")
                bot = NewsTraderBot()
                bot.run()

            elif choice == "9":
                from news_alert_agent import NewsAlertAgent
                logger.info("📰 بدء تشغيل News Monitor (مراقبة فقط)...")
                send_telegram_alert("🔔 تم تفعيل نظام مراقبة الأخبار الذكي")
                agent = NewsAlertAgent()
                agent.run()

            elif choice == "🔟" or choice == "10":
                logger.info("🚀 بدء تشغيل النظام الموحد v2.0 عبر التلغرام...")
                send_telegram_alert("🚀 تم تفعيل نظام التحكم بالتلغرام الموحد")
                from telegram_control import TelegramBotController
                controller = TelegramBotController()
                controller.start()
                import time
                try:
                    while controller.is_running:
                        time.sleep(30)
                except KeyboardInterrupt:
                    controller.stop()

            elif choice in ["1", "2", "3", "4", "5"]:
                run_single_bot(choice)

            else:
                logger.warning("⚠️  خيار غير صالح — يرجى اختيار رقم من 0 إلى 9.")
                continue

        except KeyboardInterrupt:
            logger.info("🛑 تم إيقاف النظام بواسطة المستخدم.")
            break
        except Exception as e:
            logger.error(f"❌ خطأ غير متوقع في main.py: {e}")
            continue


if __name__ == "__main__":
    main()
