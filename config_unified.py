"""
⚙️ الإعدادات المركزية الموحدة - نظام التداول الآلي v2.0
مدمج من 4 ملفات README (KIMI, GPT, CLOUD, QWEN) + منهجية 90% نجاح الصفقات
يدعم جميع أنماط التداول — جميع المفاتيح من ملف .env
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ─── المفاتيح (من البيئة فقط) ───
API_KEY = os.getenv("BINANCE_API_KEY", "")
SECRET_KEY = os.getenv("BINANCE_SECRET", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
CF_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID", "")
CF_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN", "")

# توافق للوراثة — نفس أسلوب OnlyOne/config.py
CLOUDFLARE_ACCOUNT_ID = CF_ACCOUNT_ID
CLOUDFLARE_API_TOKEN = CF_API_TOKEN
TELEGRAM_TOKEN_ALIAS = TELEGRAM_BOT_TOKEN

# ─── البروكسي ───
PROXY_URL = os.getenv("PROXY_URL", "")
PROXY_DICT = {"http": PROXY_URL, "https": PROXY_URL} if PROXY_URL else {}
USE_PROXY = bool(PROXY_URL)

# ─── إعدادات عامة ───
DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"
DEFAULT_MODE = os.getenv("DEFAULT_MODE", "swing").lower()
TIMEFRAME = os.getenv("TIMEFRAME", "1h")
HTF_TIMEFRAME = "4h"

# ─── إعدادات رافعة ومخاطرة ───
LEVERAGE = int(os.getenv("LEVERAGE", "3"))
RISK_PER_TRADE = float(os.getenv("RISK_PER_TRADE", "0.01"))  # 1%
MAX_OPEN_POSITIONS = 3
MAX_DAILY_LOSS = 0.05  # 5%
MAX_CONSECUTIVE_LOSSES = 2
COOLDOWN_HOURS = 24

# ─── منهجية 90% نجاح الصفقات ───
# R:R الأدنى لكل نمط (موحد من جميع الملفات)
MIN_RR = {
    "scalping": 1.5,
    "day": 2.5,
    "swing": 3.0,
    "position_spot": float('inf'),  # DCA غير محدد
    "position_futures": 5.0,
    "news": 2.0,
}

# R:R الأدنبي المفرد (للبوتات اللي تستخدمها مباشرة)
SCALP_MIN_RR = 1.5
DAY_MIN_RR = 2.5
SWING_MIN_RR = 3.0
POSITION_FUTURES_MIN_RR = 5.0
NEWS_MIN_RR = 2.0

MIN_SCORE = 7.0  # Score Engine من CLOUD

# ─── TP & SL ───
TP1_PCT = 1.5
TP2_PCT = 3.0
TP3_PCT = 5.0
TRAILING_STOP_PCT = 0.5
PENDING_ORDER_TIMEOUT = 10800

# ─── Funding Rate ───
FUNDING_FILTER_ENABLED = True
FUNDING_EXTREME = 0.0005  # 0.05%
# حدود Funding لكل نمط (من GPT + KIMI)
FUNDING_BOUNDS = {
    "swing": 0.0005,    # ±0.05%
    "position_futures": 0.0003,  # ±0.03%
}
# حد أقصى التكلفة المتوقعة (من CLOUD)
MAX_EXPECTED_FUNDING_COST = 0.10  # 10%

# ─── أوقات التداول ───
KILLZONES_UTC = [(9.0, 12.0), (14.5, 17.5)]  # London 11:00, NY 16:00
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

# ─── إعدادات الإنذار المبكر ───
NEWS_ALERT_INTERVAL = 300  # 5 دقائق
TIER1_KEYWORDS = ("CPI", "FOMC", "NFP", "FED")

# ─── الرموز المدعومة ───
SYMBOLS_CONFIG = {
    "BTC/USDT": {"type": "LEADER", "volatility": "low"},
    "ETH/USDT": {"type": "LEADER", "volatility": "low"},
    "SOL/USDT": {"type": "LEADER", "volatility": "low"},
}
SYMBOLS = list(SYMBOLS_CONFIG.keys())

# ─── مجموعات الارتباط ───
CORRELATION_GROUPS = {
    "LAYER1": ["BTC/USDT", "ETH/USDT", "SOL/USDT"],
}

# ─── مصادر الأخبار ───
NEWS_SOURCES = {
    "BTC": ["https://cointelegraph.com/rss/tag/bitcoin", "https://cryptoslate.com/feed/tag/bitcoin/"],
    "ETH": ["https://cointelegraph.com/rss/tag/ethereum", "https://cryptoslate.com/feed/tag/ethereum/"],
    "SOL": ["https://cointelegraph.com/rss/tag/solana", "https://cryptoslate.com/feed/tag/solana/"],
    "DEFAULT": ["https://cointelegraph.com/rss", "https://www.coindesk.com/arc/outboundfeeds/rss/"],
}

# ─── إعدادات SMC ───
SMC_CONFIG = {
    # Swing Definition (من CLOUD)
    "swing_lookback": 5,
    "displacement_threshold": 0.003,  # 0.3%
    "min_structural_distance": 0.005,  # 0.5%
    
    # FVG Detection
    "fvg_min_gap": 0.002,
    "fvg_fresh_mitigated": True,
    
    # Order Block
    "ob_min_displacement": True,
    
    # Volume Filter
    "volume_multiplier": 1.5,  # ≥ 1.5x متوسط 10 شموع
}

# ─── ملفات الحالة ───
STATE_FILE = Path("bot_state.json")
TRADE_HISTORY_FILE = Path("trade_history.json")
BACKTEST_RESULTS_FILE = Path("backtest_results.json")

# ─── إعدادات الاختبار ───
BACKTEST_WINDOW = 500  # عدد الشموع للباك تيست
WALK_FORWARD_PERIODS = 12  # شهر
MONTE_CARLO_SIMULATIONS = 1000

# ─── إعدادات التواصل ───
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
SCAN_INTERVAL = int(os.getenv("SCAN_INTERVAL", "30"))
TRADING_START_HOUR = 6
TRADING_END_HOUR = 24

# ─── متطلبات التشغيل الحي ───
# (من CLOUD - قائمة فحص ما قبل التداول الحي)
LIVE_TRADING_REQUIREMENTS = {
    "strategy_backtest": False,
    "out_of_sample_validation": False,
    "fees_included": True,
    "funding_included": True,
    "slippage_included": True,
    "execution_simulation": False,
    "drawdown_analysis": False,
    "consecutive_loss_analysis": False,
    "paper_trading": False,
    "emergency_stop_tested": False,
    "risk_engine_tested": False,
    "order_management_tested": False,
    "api_failure_tested": False,
}
