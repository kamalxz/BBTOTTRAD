"""🧪 run_swing.py — وضع المحاكاة (Dry Run) للـ Swing Trader
يشغل البوت ويسجل كل الإشارات المحتملة في ملف CSV للاختبار والتحليل.
"""
import csv
import logging
import os
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# إعداد ترميز النظام على Windows لدعم الإيموجي
if sys.stdout.encoding in ("cp1252", "cp1256"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# إعداد التسجيل (Logging) — ملف + شاشة
LOG_FILE = Path("logs") / f"swing_dryrun_{datetime.now().strftime('%Y%m%d')}.log"
LOG_FILE.parent.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8", errors="replace"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("swing_dryrun")

# ملف CSV لتسجيل الإشارات
CSV_FILE = Path("swing_signals.csv")
CSV_HEADERS = ["timestamp", "symbol", "side", "entry", "sl", "tp", "rr", "poi_type", "funding_rate"]

# متغير التوقف الآمن
shutdown_requested = False


def signal_handler(signum, frame):
    """معالجة إشارة التوقف (Ctrl+C أو SIGTERM)."""
    global shutdown_requested
    shutdown_requested = True
    logger.info("🛑 تم طلب إيقاف البوت... جارٍ الإنهاء الآمن.")


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def init_csv():
    """إنشاء ملف CSV إذا لم يكن موجوداً."""
    if not CSV_FILE.exists():
        with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(CSV_HEADERS)
        logger.info(f"📄 تم إنشاء ملف التسجيل: {CSV_FILE}")


def log_signal(signal_data):
    """تسجيل الإشارة في ملف CSV."""
    timestamp = datetime.now(timezone.utc).isoformat()
    row = [
        timestamp,
        signal_data["symbol"],
        signal_data["side"],
        f"{signal_data['entry']:.2f}",
        f"{signal_data['sl']:.2f}",
        f"{signal_data['tp']:.2f}",
        f"{signal_data['rr_ratio']:.2f}",
        signal_data.get("poi_type", "OB"),
        f"{signal_data.get('funding_rate', 0):.4f}",
    ]

    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(row)

    logger.info(f"📝 تم تسجيل الإشارة في CSV: {signal_data['symbol']} {signal_data['side']} RR={signal_data['rr_ratio']:.2f}")


def main():
    init_csv()
    logger.info("🚀 بدء تشغيل Swing Trader في وضع المحاكاة (Dry Run)")
    logger.info(f"📊 الملفات: {LOG_FILE} | {CSV_FILE}")

    try:
        from modes.swing_trader import SwingTraderBot
        bot = SwingTraderBot()

        while not shutdown_requested:
            try:
                trade = bot._scan()
                if trade:
                    logger.info(f"⚡ إشارة صالحة: {trade}")
                    log_signal(trade)
                else:
                    logger.debug("لم يتم العثور على إشارات في هذه الدورة.")

                # النوم بين فحوصات
                time.sleep(60)

            except Exception as e:
                logger.error(f"خطأ في الحلقة الرئيسية: {e}")
                time.sleep(60)

    except KeyboardInterrupt:
        logger.info("🛑 إيقاف بواسطة المستخدم.")
    except Exception as e:
        logger.error(f"خطأ فادح: {e}")
        logger.info("إيقاف البوت.")
    finally:
        logger.info("🧹 البوت تم إيقافه بأمان.")
        if CSV_FILE.exists():
            with open(CSV_FILE) as f:
                lines = len(list(csv.reader(f)))
            logger.info(f"📊 إجمالي الإشارات المسجلة: {lines - 1} إشارة.")


if __name__ == "__main__":
    main()
