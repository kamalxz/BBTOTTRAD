"""🌐 ip_utils.py — أدوات الحصول على عنوان IP الحالي"""
import requests

try:
    import config
except ImportError:
    config = None


def get_proxy_ip() -> str:
    """الحصول على الـ IP الحالي عبر البروكسي (إن كان مفعّلاً).

    يستخدم https://api.ipify.org للحصول على الـ IP العام.
    إذا كان البروكسي غير مفعّل، يرجع الـ IP المباشر للجهاز.
    """
    proxies = getattr(config, "PROXY_DICT", {}) if getattr(config, "USE_PROXY", False) else {}
    try:
        r = requests.get("https://api.ipify.org?format=json", proxies=proxies if proxies else None, timeout=10)
        if r.status_code == 200:
            return r.json().get("ip", "Unknown")
        return "Unknown"
    except Exception as e:
        try:
            import logging
            logger = logging.getLogger("ip_utils")
            logger.debug(f"فشل الحصول على الـ IP: {e}")
        except Exception:
            pass
        return "Unknown"


def test_proxy_connection() -> bool:
    """اختبار اتصال البروكسي — يتحقق من أن البروكسي يعمل بشكل صحيح.

    يرسل طلبًا تجريبيًا إلى api.ipify.org عبر البروكسي.
    إذا كان USE_PROXY = False، يرجع True مباشرةً (يعني لا حاجة للبروكسي).
    """
    if not getattr(config, "USE_PROXY", False):
        return True  # لا حاجة للبروكسي

    proxies = getattr(config, "PROXY_DICT", {})
    if not proxies:
        return True

    try:
        r = requests.get("https://api.ipify.org?format=json", proxies=proxies, timeout=10)
        if r.status_code == 200:
            ip = r.json().get("ip", "")
            try:
                import logging
                logger = logging.getLogger("ip_utils")
                logger.info(f"✅ البروكسي يعمل — IP: {ip}")
            except Exception:
                pass
            return True
        else:
            try:
                import logging
                logger = logging.getLogger("ip_utils")
                logger.error(f"❌ فشل البروكسي — HTTP {r.status_code}")
            except Exception:
                pass
            return False
    except Exception as e:
        try:
            import logging
            logger = logging.getLogger("ip_utils")
            logger.error(f"❌ البروكسي غير متاح: {e}")
        except Exception:
            pass
        return False
