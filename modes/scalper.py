"""
بوت السكالبر - Scalper Bot
يحتوي على استراتيجية "القناص المتوازن" مع 11 فلتر
"""
import pandas as pd
import numpy as np
from datetime import datetime
from config import GOLDEN_SYMBOLS, SCALPER_CONFIG, PAPER_TRADING
from core.exchange_manager import ExchangeManager
from core.news_agent import NewsAgent

class ScalperBot:
    def __init__(self):
        self.exchange = ExchangeManager()
        self.news_agent = NewsAgent()
        self.config = SCALPER_CONFIG
        self.positions = {}  # تتبع المراكز المفتوحة
        
    def calculate_ema(self, df: pd.DataFrame, period: int) -> float:
        """حساب EMA"""
        return df['close'].ewm(span=period, adjust=False).mean().iloc[-1]
    
    def calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> float:
        """حساب RSI"""
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean().iloc[-1]
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean().iloc[-1]
        rs = gain / loss if loss != 0 else 0
        return 100 - (100 / (1 + rs))
    
    def calculate_adx(self, df: pd.DataFrame, period: int = 14) -> float:
        """حساب ADX (مبسط)"""
        high = df['high']
        low = df['low']
        close = df['close']
        
        plus_dm = high.diff()
        minus_dm = -low.diff()
        
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0
        
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        atr = tr.rolling(window=period).mean()
        plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)
        
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(window=period).mean().iloc[-1]
        return adx
    
    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """حساب ATR"""
        high = df['high']
        low = df['low']
        close = df['close'].shift()
        
        tr1 = high - low
        tr2 = abs(high - close)
        tr3 = abs(low - close)
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        return tr.rolling(window=period).mean().iloc[-1]
    
    def check_volume_spike(self, df: pd.DataFrame, multiplier: float = 1.2) -> bool:
        """التحقق من وجود ارتفاع في الحجم"""
        avg_volume = df['volume'].rolling(window=20).mean().iloc[-2]  # المتوسط قبل الشمعة الأخيرة
        current_volume = df['volume'].iloc[-1]
        return current_volume > (avg_volume * multiplier)
    
    def is_in_preferred_session(self) -> bool:
        """التحقق من وقت الجلسة المفضل"""
        utc_hour = datetime.utcnow().hour
        sessions = self.config.get('PREFERRED_SESSIONS', [(7, 10), (13, 16)])
        for start, end in sessions:
            if start <= utc_hour <= end:
                return True
        return False
    
    def validate_entry(self, symbol: str, df_entry: pd.DataFrame, df_trend: pd.DataFrame) -> dict:
        """
        تطبيق الفلاتر الـ 11 والتحقق من صلاحية الدخول
        returns: {'valid': bool, 'signal': str, 'reason': str}
        """
        # 1. فلتر نوع العملة (القائمة الذهبية فقط)
        if symbol not in GOLDEN_SYMBOLS:
            return {'valid': False, 'signal': None, 'reason': f'العملة {symbol} ليست في القائمة الذهبية'}
        
        # 2. فلتر الأخبار السلبية
        if self.news_agent.check_negative_news(symbol):
            return {'valid': False, 'signal': None, 'reason': 'وجود أخبار سلبية'}
        
        # حساب المؤشرات
        ema_trend = self.calculate_ema(df_trend, self.config['EMA_TREND'])
        ema_pullback = self.calculate_ema(df_entry, self.config['EMA_PULLBACK'])
        ema_fast = self.calculate_ema(df_entry, 20)
        rsi = self.calculate_rsi(df_entry)
        adx = self.calculate_adx(df_entry)
        atr = self.calculate_atr(df_entry)
        current_price = df_entry['close'].iloc[-1]
        
        # 3. فلتر الاتجاه العام (EMA 200 على فريم 15د)
        trend_direction = None
        if current_price > ema_trend:
            trend_direction = 'LONG'
        elif current_price < ema_trend:
            trend_direction = 'SHORT'
        else:
            return {'valid': False, 'signal': None, 'reason': 'لا يوجد اتجاه واضح (السعر حول EMA 200)'}
        
        # 4. فلتر الزخم (ADX)
        if adx < self.config['ADX_MIN']:
            return {'valid': False, 'signal': None, 'reason': f'الزخم ضعيف (ADX = {adx:.2f})'}
        
        # 5. فلتر التشبع السعري (RSI)
        if trend_direction == 'LONG':
            if not (self.config['RSI_LONG_MIN'] <= rsi <= self.config['RSI_OVERBOUGHT']):
                return {'valid': False, 'signal': None, 'reason': f'RSI غير مناسب للشراء ({rsi:.2f})'}
        else:  # SHORT
            if not (self.config['RSI_OVERSOLD'] <= rsi <= self.config['RSI_SHORT_MAX']):
                return {'valid': False, 'signal': None, 'reason': f'RSI غير مناسب للبيع ({rsi:.2f})'}
        
        # 6. فلتر حجم التداول
        if not self.check_volume_spike(df_entry, self.config['VOLUME_SPIKE_RATIO']):
            return {'valid': False, 'signal': None, 'reason': 'لا يوجد ارتفاع في الحجم'}
        
        # 7. فلتر الارتداد الديناميكي (السعر قريب من EMA 50)
        distance_from_ema = abs(current_price - ema_pullback) / ema_pullback
        if distance_from_ema > 0.005:  # أكثر من 0.5% بعيداً
            return {'valid': False, 'signal': None, 'reason': 'السعر بعيد عن EMA 50 (ليس ارتداداً)'}
        
        # 8. فلتر ترتيب المتوسطات (EMA 20 و EMA 50)
        if trend_direction == 'LONG' and ema_fast <= ema_pullback:
            return {'valid': False, 'signal': None, 'reason': 'EMA 20 تحت EMA 50 (اتجاه ضعيف)'}
        if trend_direction == 'SHORT' and ema_fast >= ema_pullback:
            return {'valid': False, 'signal': None, 'reason': 'EMA 20 فوق EMA 50 (اتجاه ضعيف)'}
        
        # 9. فلتر وقت الجلسة
        if not self.is_in_preferred_session():
            return {'valid': False, 'signal': None, 'reason': 'خارج أوقات الجلسة المفضلة'}
        
        # 10. فلتر نسبة العائد للمخاطرة
        sl_distance = atr * self.config['SL_MULTIFIER']
        tp_distance = atr * self.config['TP_MULTIFIER']
        risk_reward_ratio = tp_distance / sl_distance
        if risk_reward_ratio < 1.0:
            return {'valid': False, 'signal': None, 'reason': f'نسبة العائد للمخاطرة ضعيفة ({risk_reward_ratio:.2f})'}
        
        # 11. فلتر الانزلاق والفروقات (يتم التحقق منه عند التنفيذ)
        
        # ✅ جميع الفلاتر نجحت
        signal = trend_direction
        sl_price = current_price - sl_distance if signal == 'LONG' else current_price + sl_distance
        tp_price = current_price + tp_distance if signal == 'LONG' else current_price - tp_distance
        
        return {
            'valid': True,
            'signal': signal,
            'reason': 'جميع الفلاتر نجحت',
            'entry_price': current_price,
            'sl_price': sl_price,
            'tp_price': tp_price,
            'atr': atr,
            'rsi': rsi,
            'adx': adx
        }
    
    def run(self):
        """الحلقة الرئيسية للبوت"""
        print("🚀 بدء بوت السكالبر...")
        print(f"العملات المراقبة: {GOLDEN_SYMBOLS}")
        
        while True:
            for symbol in GOLDEN_SYMBOLS:
                try:
                    # جلب البيانات
                    df_entry = self.exchange.fetch_ohlcv(symbol, self.config['ENTRY_TIMEFRAME'], limit=100)
                    df_trend = self.exchange.fetch_ohlcv(symbol, self.config['TREND_TIMEFRAME'], limit=100)
                    
                    if df_entry.empty or df_trend.empty:
                        continue
                    
                    # التحقق من وجود مركز مفتوح
                    if symbol in self.positions:
                        # إدارة المركز الحالي (Trailing Stop)
                        self.manage_position(symbol)
                        continue
                    
                    # التحقق من إشارة دخول جديدة
                    result = self.validate_entry(symbol, df_entry, df_trend)
                    
                    if result['valid']:
                        print(f"\n🎯 إشارة دخول على {symbol}:")
                        print(f"   النوع: {result['signal']}")
                        print(f"   السعر: {result['entry_price']}")
                        print(f"   SL: {result['sl_price']}")
                        print(f"   TP: {result['tp_price']}")
                        print(f"   السبب: {result['reason']}")
                        
                        # تنفيذ الصفقة
                        self.open_position(symbol, result)
                    
                except Exception as e:
                    print(f"خطأ في معالجة {symbol}: {e}")
            
            # الانتظار 5 ثوانٍ قبل التكرار التالي
            import time
            time.sleep(5)
    
    def open_position(self, symbol: str, signal_data: dict):
        """فتح مركز جديد"""
        side = 'buy' if signal_data['signal'] == 'LONG' else 'sell'
        amount = 0.01  # حجم افتراضي للتجربة
        
        order = self.exchange.execute_order(symbol, side, amount)
        
        if order.get('status') == 'closed' or order.get('status') == 'open':
            self.positions[symbol] = {
                'side': side,
                'entry_price': signal_data['entry_price'],
                'sl_price': signal_data['sl_price'],
                'tp_price': signal_data['tp_price'],
                'amount': amount,
                'highest_profit': 0  # لتتبع أعلى ربح لـ Trailing Stop
            }
            print(f"✅ تم فتح مركز على {symbol}")
    
    def manage_position(self, symbol: str):
        """إدارة المركز الحالي (Trailing Stop)"""
        position = self.positions[symbol]
        current_price = self.exchange.get_current_price(symbol)
        
        # حساب الربح الحالي
        if position['side'] == 'buy':
            profit_pct = (current_price - position['entry_price']) / position['entry_price']
        else:
            profit_pct = (position['entry_price'] - current_price) / position['entry_price']
        
        # تحديث أعلى ربح
        if profit_pct > position['highest_profit']:
            position['highest_profit'] = profit_pct
        
        # تفعيل Trailing Stop
        if position['highest_profit'] >= self.config['TRAILING_STOP_TRIGGER']:
            trailing_stop_price = current_price * (1 - self.config['TRAILING_STOP_OFFSET']) if position['side'] == 'buy' else current_price * (1 + self.config['TRAILING_STOP_OFFSET'])
            
            # التحقق من الخروج
            if (position['side'] == 'buy' and current_price <= trailing_stop_price) or \
               (position['side'] == 'sell' and current_price >= trailing_stop_price):
                self.close_position(symbol)
                return
        
        # التحقق من Stop Loss أو Take Profit
        if (position['side'] == 'buy' and current_price <= position['sl_price']) or \
           (position['side'] == 'sell' and current_price >= position['sl_price']):
            self.close_position(symbol, reason='Stop Loss')
            return
        
        if (position['side'] == 'buy' and current_price >= position['tp_price']) or \
           (position['side'] == 'sell' and current_price <= position['tp_price']):
            self.close_position(symbol, reason='Take Profit')
    
    def close_position(self, symbol: str, reason: str = ''):
        """إغلاق المركز"""
        position = self.positions[symbol]
        side = 'sell' if position['side'] == 'buy' else 'buy'
        
        self.exchange.close_position(symbol, position['side'], position['amount'])
        
        print(f"❌ تم إغلاق مركز {symbol} - السبب: {reason}")
        del self.positions[symbol]

# تشغيل البوت
if __name__ == "__main__":
    bot = ScalperBot()
    bot.run()
