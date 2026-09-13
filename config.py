"""
إعدادات بوت السكالبر (Scalper Bot Configuration)
القائمة الذهبية، المؤشرات، مصادر الأخبار، وثوابت الاستراتيجية
"""

# --- القائمة الذهبية للعملات (GOLDEN SYMBOLS) ---
# العملات التي أثبتت نسبة فوز > 90% في اختبار الباك تيست
GOLDEN_SYMBOLS = [
    'BTC/USDT:USDT',
    'ETH/USDT:USDT',
    'SOL/USDT:USDT',
    'LTC/USDT:USDT',
    'BNB/USDT:USDT'
]

# --- إعدادات الفريمات الزمنية ---
TIMEFRAMES = {
    'entry': '1m',       # فريم الدخول (1 دقيقة)
    'trend': '15m'       # فريم تحديد الاتجاه (15 دقيقة)
}

# --- ثوابت المؤشرات الفنية ---
INDICATORS = {
    'ema_trend': 200,    # EMA لتحديد الاتجاه العام
    'ema_pullback': 50,  # EMA للارتداد
    'ema_fast': 20,      # EMA السريع
    'rsi_period': 14,
    'adx_period': 14,
    'atr_period': 14,
    'volume_ma_period': 20
}

# --- شروط الدخول (القناص المتوازن) ---
ENTRY_CONDITIONS = {
    'adx_min': 28,               # الحد الأدنى لـ ADX
    'rsi_long_min': 62,          # RSI للشراء
    'rsi_long_max': 75,          # تجنب التشبع الشرائي
    'rsi_short_min': 25,         # تجنب التشبع البيعي
    'rsi_short_max': 38,         # RSI للبيع
    'volume_multiplier': 1.2,    # ضعف حجم التداول المتوسط
    'ema_gap_min': 0.001         # الحد الأدنى للتباعد بين EMA
}

# --- إدارة المخاطر ---
RISK_MANAGEMENT = {
    'sl_atr_multiplier': 0.7,   # وقف الخسارة = 0.7 x ATR
    'tp_atr_multiplier': 0.5,   # جني الربح = 0.5 x ATR
    'trailing_stop_activation': 0.003,  # تفعيل trailing stop عند 0.3% ربح
    'trailing_stop_offset': 0.002,      # سحب وقف الخسارة عند 0.2%
    'max_risk_per_trade': 0.01,         # مخاطرة قصوى 1% من الرصيد
    'min_reward_risk_ratio': 1.2      # نسبة العائد للمخاطرة الدنيا
}

# --- فلتر الأخبار السلبية ---
NEGATIVE_KEYWORDS = [
    'crash', 'hack', 'exploit', 'lawsuit', 'ban', 'sec', 
    'attack', 'vulnerability', 'collapse', 'freeze', 'scam', 
    'investigation', 'fine', 'shut down', 'delist'
]

NEWS_SOURCES = {
    'BTC': ['https://cointelegraph.com/rss/tag/bitcoin', 'https://cryptoslate.com/feed/tag/bitcoin/'],
    'ETH': ['https://cointelegraph.com/rss/tag/ethereum', 'https://cryptoslate.com/feed/tag/ethereum/'],
    'SOL': ['https://cointelegraph.com/rss/tag/solana', 'https://cryptoslate.com/feed/tag/solana/'],
    'LTC': ['https://cointelegraph.com/rss/tag/litecoin', 'https://cryptoslate.com/feed/tag/litecoin/'],
    'BNB': ['https://cointelegraph.com/rss/tag/binance', 'https://cryptoslate.com/feed/tag/binance/'],
    'DEFAULT': ['https://cointelegraph.com/rss', 'https://www.coindesk.com/arc/outboundfeeds/rss/']
}

NEWS_CHECK_PERIOD_MINUTES = 30  # تحديث الأخبار كل 30 دقيقة
MAX_NEWS_ITEMS_TO_CHECK = 5     # فحص آخر 5 عناوين فقط

# --- إعدادات الجلسة ---
TRADING_SESSIONS = {
    'london': {'start': 7, 'end': 16},    # بالتوقيت العالمي UTC
    'new_york': {'start': 13, 'end': 22},
    'overlap': {'start': 13, 'end': 16}   # أفضل وقت (تداخل لندن ونيويورك)
}

# --- وضع التشغيل ---
PAPER_TRADING = True  # True للمحاكاة، False للتداول الحقيقي

# --- مفاتيح API (يجب وضعها في ملف .env) ---
# BINANCE_API_KEY = ""
# BINANCE_SECRET_KEY = ""
# TELEGRAM_BOT_TOKEN = ""
# TELEGRAM_CHAT_ID = ""
