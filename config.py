# إعدادات بوت السكالبر (Scalper Bot Configuration)
import os
from dotenv import load_dotenv

load_dotenv()

# --- مفاتيح API ---
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", "")
BINANCE_SECRET_KEY = os.getenv("BINANCE_SECRET_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# --- القائمة الذهبية للعملات (فقط العملات التي أثبتت كفاءة >90%) ---
GOLDEN_SYMBOLS = [
    "BTC/USDT:USDT",
    "ETH/USDT:USDT",
    "SOL/USDT:USDT",
    "LTC/USDT:USDT",
    "BNB/USDT:USDT"
]

# --- إعدادات استراتيجية السكالبر ---
SCALPER_CONFIG = {
    # الفريمات الزمنية
    "ENTRY_TIMEFRAME": "1m",      # فريم الدخول
    "TREND_TIMEFRAME": "15m",     # فريم تحديد الاتجاه
    
    # المؤشرات الفنية
    "EMA_TREND": 200,             # EMA لتحديد الاتجاه العام
    "EMA_PULLBACK": 50,           # EMA للارتداد
    "ADX_MIN": 28,                # الحد الأدنى للزخم
    "RSI_OVERBOUGHT": 75,         # تشبع شرائي
    "RSI_OVERSOLD": 25,           # تشبع بيعي
    "RSI_LONG_MIN": 62,           # حد RSI للدخول LONG
    "RSI_SHORT_MAX": 38,          # حد RSI للدخول SHORT
    "VOLUME_SPIKE_RATIO": 1.2,    # نسبة ارتفاع الحجم
    
    # إدارة المخاطر
    "ATR_PERIOD": 14,
    "SL_MULTIFIER": 0.7,          # وقف الخسارة = 0.7 x ATR
    "TP_MULTIFIER": 0.5,          # جني الربح = 0.5 x ATR
    "TRAILING_STOP_TRIGGER": 0.003,  # تفعيل trailing stop عند ربح 0.3%
    "TRAILING_STOP_OFFSET": 0.002,   # مسافة trailing stop 0.2%
    
    # فلاتر إضافية
    "MIN_TRADE_AMOUNT_USDT": 10,  # الحد الأدنى لحجم الصفقة
    "MAX_SPREAD_PERCENT": 0.05,   # الحد الأقصى للفروقات السعرية
    
    # أوقات التداول المفضلة (UTC)
    "PREFERRED_SESSIONS": [
        (7, 10),   # جلسة لندن
        (13, 16)   # جلسة نيويورك
    ]
}

# --- مصادر الأخبار والكلمات السلبية ---
NEWS_SOURCES = {
    "BTC": ["https://cointelegraph.com/rss/tag/bitcoin", "https://cryptoslate.com/feed/tag/bitcoin/"],
    "ETH": ["https://cointelegraph.com/rss/tag/ethereum", "https://cryptoslate.com/feed/tag/ethereum/"],
    "SOL": ["https://cointelegraph.com/rss/tag/solana", "https://cryptoslate.com/feed/tag/solana/"],
    "LTC": ["https://cointelegraph.com/rss/tag/litecoin", "https://cryptoslate.com/feed/tag/litecoin/"],
    "BNB": ["https://cointelegraph.com/rss/tag/binance", "https://cryptoslate.com/feed/tag/binance/"],
    "DEFAULT": ["https://cointelegraph.com/rss", "https://www.coindesk.com/arc/outboundfeeds/rss/"]
}

NEGATIVE_KEYWORDS = [
    "crash", "hack", "exploit", "lawsuit", "ban", "sec", 
    "attack", "vulnerability", "collapse", "freeze", 
    "scam", "fraud", "investigation", "warning"
]

# --- وضع التشغيل ---
PAPER_TRADING = True  # True للتجربة، False للتداول الحقيقي

