"""
⚙️ الإعدادات المركزية - محدّثة للنسخة الموحدة v2.0
يدعم جميع أنماط التداول — جميع المفاتيح من ملف .env
تم دمج الإعدادات المحسنة مع الاحتفاظ بالتوافق مع البوتات القديمة
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ─── استيراد الإعدادات المحسّنة من config_unified (لكل الاستخدام المركزي) ───
try:
    from config_unified import *
except ImportError:
    pass

# ✅ تحميل المتغيرات من .env (يأخذ الأولوية على config_unified)
load_dotenv()

# ✅ SANDBOX_MODE — يقرأ من .env فقط، مع احتياطي True للأمان
SANDBOX_MODE = os.getenv("SANDBOX_MODE", "true").lower() == "true"

# ─── المفاتيح (من البيئة فقط) ───
API_KEY = os.getenv("BINANCE_API_KEY", "")
SECRET_KEY = os.getenv("BINANCE_SECRET", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
CF_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID", "")
CF_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN", "")

# ✅ توافق للوراثة — نفس أسلوب OnlyOne/config.py
CLOUDFLARE_ACCOUNT_ID = CF_ACCOUNT_ID
CLOUDFLARE_API_TOKEN = CF_API_TOKEN

# Telegram (دعم اسمين لتوافقية الكود القديم)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_TOKEN_ALIAS = TELEGRAM_BOT_TOKEN

# ─── البروكسي ───
PROXY_URL = os.getenv("PROXY_URL", "")
PROXY_DICT = {"http": PROXY_URL, "https": PROXY_URL} if PROXY_URL else {}
USE_PROXY = bool(PROXY_URL)

# ─── الإعدادات العامة ───
DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"
DEFAULT_MODE = os.getenv("DEFAULT_MODE", "swing").lower()
TIMEFRAME = os.getenv("TIMEFRAME", "1h")
HTF_TIMEFRAME = "4h"
LEVERAGE = int(os.getenv("LEVERAGE", "3"))
RISK_PER_TRADE = float(os.getenv("RISK_PER_TRADE", "0.01"))  # 1%
MAX_OPEN_POSITIONS = 3
MAX_DAILY_LOSS = 0.05  # 5%
MAX_CONSECUTIVE_LOSSES = 2
COOLDOWN_HOURS = 24
MIN_RR = 1.5
MIN_SCORE = 7.0

# ─── R:R الحد الأدنى لكل نمط (مدمج من KIMI + GPT + QWEN) ───
SCALP_MIN_RR = 1.5
DAY_MIN_RR = 2.5
SWING_MIN_RR = 3.0
POSITION_FUTURES_MIN_RR = 5.0
NEWS_MIN_RR = 2.0

# ─── إعدادات إضافية ───
SCAN_INTERVAL = 30
TRADING_START_HOUR = 6
TRADING_END_HOUR = 24

# ─── إعدادات السكالبر ───
RISK_PER_TRADE = 0.01  # 1% من الرصيد (1$ من 100$)

# ─── TP & SL ───
TP1_PCT = 1.5
TP2_PCT = 3.0
TP3_PCT = 5.0
TRAILING_STOP_PCT = 0.5
PENDING_ORDER_TIMEOUT = 10800

# ─── Funding ───
FUNDING_FILTER_ENABLED = True
FUNDING_EXTREME = 0.0005

# ─── أوقات التداول ───
KILLZONES_UTC = [(9.0, 12.0), (14.5, 17.5)]
SILVER_BULLETS_UTC = [10.0, 14.0, 15.0]
BAD_WEEKDAYS = [0, 4]

# ─── الأخبار ───
NEWS_BLACKOUTS = {
    "NFP": {"weekday": 4, "day_max": 7, "hour": 12, "minute": 30},
    "CPI": {"weekday": [2, 3], "day_min": 12, "day_max": 15, "hour": 12, "minute": 30},
    "FOMC": {"weekday": 2, "hour": 18, "minute": 0},
}
NEWS_BLACKOUT_MINUTES = 15
NEWS_CACHE_MINUTES = 30
NEWS_BLOCK_THRESHOLD = -0.5

# ─── الرموز المدعومة ───
SYMBOLS_CONFIG = {
    "BTC/USDT:USDT": {"type": "LEADER", "volatility": "low"},
    "ETH/USDT:USDT": {"type": "LEADER", "volatility": "low"},
    "SOL/USDT:USDT": {"type": "LEADER", "volatility": "low"},
}
SYMBOLS = list(SYMBOLS_CONFIG.keys())

# ─── مجموعات الارتباط ───
CORRELATION_GROUPS = {
    "LAYER1": ["BTC/USDT:USDT", "ETH/USDT:USDT", "SOL/USDT:USDT"],
}

# ─── مصادر الأخبار ───
NEWS_SOURCES = {
    "BTC": ["https://cointelegraph.com/rss/tag/bitcoin", "https://cryptoslate.com/feed/tag/bitcoin/"],
    "ETH": ["https://cointelegraph.com/rss/tag/ethereum", "https://cryptoslate.com/feed/tag/ethereum/"],
    "SOL": ["https://cointelegraph.com/rss/tag/solana", "https://cryptoslate.com/feed/tag/solana/"],
    "DEFAULT": ["https://cointelegraph.com/rss", "https://www.coindesk.com/arc/outboundfeeds/rss/"],
}

# ─── ملفات الحالة ───
STATE_FILE = Path("bot_state.json")
TRADE_HISTORY_FILE = Path("trade_history.json")
BACKTEST_RESULTS_FILE = Path("backtest_results.json")
