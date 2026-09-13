"""
مدير التبادل - Exchange Manager
يتصل بـ Binance لجلب البيانات وتنفيذ الأوامر
"""
import ccxt
import pandas as pd
from datetime import datetime, timedelta
from config import BINANCE_API_KEY, BINANCE_SECRET_KEY, PAPER_TRADING

class ExchangeManager:
    def __init__(self):
        # الاتصال بـ Binance
        self.exchange = ccxt.binance({
            'apiKey': BINANCE_API_KEY,
            'secret': BINANCE_SECRET_KEY,
            'enableRateLimit': True,
            'options': {'defaultType': 'future'}  # تداول العقود المستقبلية
        })
        
        if PAPER_TRADING:
            print("📄 وضع المحاكاة (Paper Trading) مفعل")
        
    def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int = 1000) -> pd.DataFrame:
        """جلب بيانات الشموع وإرجاعها كـ DataFrame"""
        try:
            bars = self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
            df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            return df
        except Exception as e:
            print(f"خطأ في جلب البيانات لـ {symbol}: {e}")
            return pd.DataFrame()
    
    def get_current_price(self, symbol: str) -> float:
        """الحصول على السعر الحالي"""
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return ticker['last']
        except Exception as e:
            print(f"خطأ في الحصول على السعر لـ {symbol}: {e}")
            return 0.0
    
    def execute_order(self, symbol: str, side: str, amount: float, price: float = None) -> dict:
        """
        تنفيذ أمر شراء أو بيع
        side: 'buy' أو 'sell'
        amount: حجم الصفقة
        price: سعر التنفيذ (اختياري، إذا كان None يتم تنفيذ بالسعر السوقي)
        """
        if PAPER_TRADING:
            # محاكاة التنفيذ
            exec_price = price if price else self.get_current_price(symbol)
            print(f"📝 [محاكاة] تنفيذ أمر {side.upper()} على {symbol}")
            print(f"   السعر: {exec_price}, الحجم: {amount}")
            return {
                'id': 'paper_' + datetime.now().strftime('%Y%m%d%H%M%S'),
                'symbol': symbol,
                'side': side,
                'amount': amount,
                'price': exec_price,
                'status': 'closed',
                'info': {'paper_trade': True}
            }
        
        # تنفيذ حقيقي
        try:
            if price:
                order = self.exchange.create_limit_order(symbol, side, amount, price)
            else:
                order = self.exchange.create_market_order(symbol, side, amount)
            print(f"✅ تم تنفيذ أمر {side.upper()} على {symbol}")
            return order
        except Exception as e:
            print(f"❌ فشل تنفيذ الأمر: {e}")
            return {'status': 'failed', 'error': str(e)}
    
    def close_position(self, symbol: str, side: str, amount: float) -> dict:
        """إغلاق مركز مفتوح"""
        opposite_side = 'sell' if side == 'buy' else 'buy'
        return self.execute_order(symbol, opposite_side, amount)

# اختبار سريع
if __name__ == "__main__":
    manager = ExchangeManager()
    print("Testing Exchange Manager...")
    df = manager.fetch_ohlcv("BTC/USDT:USDT", "1m", limit=10)
    print(df.tail())
