"""🧱 base.py — الواجهة الأساسية للبوتات (BaseMode)"""
from abc import ABC, abstractmethod
import logging

from core.exchange import BinanceExchange

logger = logging.getLogger("base_mode")


class BaseMode(ABC):
    """واجهة أساسية تُستثنى بها جميع البوتات."""

    name: str = "BaseMode"
    description: str = "Base trading mode"

    def __init__(self):
        self.exchange = BinanceExchange()
        logging.info(f"{self.name}: تم التهيئة ✅")

    @abstractmethod
    def run(self):
        """الحلقة الرئيسية للبوت — يجب تنفيذها في الفئات الفرعية."""
        pass

    def _log_mode(self):
        """Log mode startup information."""
        logging.info(f"{self.name}: جاهز ويدير التشغيل على الإطار {getattr(self, 'timeframe', 'N/A')}")

    def _get_ohlcv(self, symbol: str, timeframe: str, limit: int = 100):
        """جلب بيانات الشموع (OHLCV) من Binance.

        يحدد نوع السوق تلقائياً بناءً على وجود ':USDT' في اسم الرمز.
        """
        import pandas as pd

        market_type = "spot" if ":USDT" not in symbol else "futures"
        return self.exchange.fetch_ohlcv(symbol, timeframe, limit, market_type)

    def stop(self):
        """إيقاف البوت بشكل نظيف."""
        logging.info(f"{self.name}: تم إيقافه بشكل آمن ✅")
