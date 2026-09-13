"""📲 telegram_alerts.py — إرسال إشعارات تلغرام فورية للبوتات"""
import logging

import requests

import config
logger = logging.getLogger("telegram_alerts")

_BOT_TOKEN = getattr(config, "TELEGRAM_BOT_TOKEN", "")
_CHAT_ID = getattr(config, "TELEGRAM_CHAT_ID", "")


def send_telegram_alert(message: str, disable_notification: bool = False) -> bool:
    """
    إرسال إشعار نصي إلى تيليجرام.
    يستخدم الاتصال المباشر دائماً — بدون بروكسي.
    """
    if not _BOT_TOKEN or not _CHAT_ID:
        logger.warning("⚠️  TELEGRAM_BOT_TOKEN أو TELEGRAM_CHAT_ID غير محدد — تم تخطي الإرسال")
        return False

    url = f"https://api.telegram.org/bot{_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": _CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_notification": disable_notification,
    }

    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code == 200:
            logger.info("✅ تم إرسال إشعار تيليجرام")
            return True
        else:
            logger.error(f"❌ فشل إرسال التيليجرام: {resp.status_code} {resp.text}")
            return False
    except Exception as e:
        logger.error(f"❌ خطأ في إرسال إشعار تيليجرام: {e}")
        return False


def format_trade_alert(symbol: str, side: str, entry: float, sl: float, tp: float, rr: float) -> str:
    """صياغة رسالة تداول جمالية."""
    emoji_side = "🟢 شراء" if side == "buy" else "🔴 بيع"
    return (
        f"<b>🚨 إشارة تداول جديدة</b>\n"
        f"🪙 الزوج: <code>{symbol}</code>\n"
        f"📊 الاتجاه: {emoji_side}\n"
        f"💰 الدخول: <code>{entry:.2f}</code>\n"
        f"🛑 SL: <code>{sl:.2f}</code>\n"
        f"🎯 TP: <code>{tp:.2f}</code>\n"
        f"⚖️ R:R: <code>{rr:.2f}</code>"
    )
