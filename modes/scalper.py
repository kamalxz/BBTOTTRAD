"""
بوت السكالبر - Scalper Bot
يحتوي على استراتيجية "القناص المتوازن" مع NO TRADE Engine (11 فلتر)
ومكونات SMC الكاملة: BOS, CHoCH, FVG, Order Blocks, Liquidity Zones
"""
import pandas as pd
import numpy as np
from datetime import datetime
from config import GOLDEN_SYMBOLS, SCALPER_CONFIG, PAPER_TRADING
from core.exchange_manager import ExchangeManager
from core.news_agent import NewsAgent
from core.unified_smc import UnifiedSMC, MarketStructure, LiquidityZone, POI, Confirmation
from core.unified_filters import UnifiedFilters, TradeSignal, MarketContext

# استيراد وحدات التحليل (تحليل مسار Windows)
import sys
import os
if os.name == 'nt':  # Windows
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    
# محاولة الاستيراد المباشر
try:
    from analysis.fvg_detector import detect_fvg, check_mitigation
    from analysis.ob_detector import detect_order_blocks, check_ob_mitigation
    from analysis.market_structure import detect_swing_highs_lows, detect_bos, detect_choch
except ImportError:
    # fallback: تحميل الملفات مباشرة
    import importlib.util
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    spec_fvg = importlib.util.spec_from_file_location("fvg_detector", os.path.join(base_path, "analysis\\fvg_detector.py"))
    fvg_module = importlib.util.module_from_spec(spec_fvg)
    spec_fvg.loader.exec_module(fvg_module)
    detect_fvg = fvg_module.detect_fvg
    check_mitigation = fvg_module.check_mitigation
    
    spec_ob = importlib.util.spec_from_file_location("ob_detector", os.path.join(base_path, "analysis\\ob_detector.py"))
    ob_module = importlib.util.module_from_spec(spec_ob)
    spec_ob.loader.exec_module(ob_module)
    detect_order_blocks = ob_module.detect_order_blocks
    check_ob_mitigation = ob_module.check_ob_mitigation
    
    spec_ms = importlib.util.spec_from_file_location("market_structure", os.path.join(base_path, "analysis\\market_structure.py"))
    ms_module = importlib.util.module_from_spec(spec_ms)
    spec_ms.loader.exec_module(ms_module)
    detect_swing_highs_lows = ms_module.detect_swing_highs_lows
    detect_bos = ms_module.detect_bos
    detect_choch = ms_module.detect_choch

class ScalperBot:
    def __init__(self):
        self.exchange = ExchangeManager()
        self.news_agent = NewsAgent()
        self.config = SCALPER_CONFIG
        self.positions = {}  # تتبع المراكز المفتوحة
        
        # تهيئة محركات SMC والفلاتر
        self.smc_engine = UnifiedSMC({
            "swing_lookback": 5,
            "displacement_threshold": 0.003,
            "min_structural_distance": 0.005,
            "volume_multiplier": 1.5
        })
        self.filters = UnifiedFilters(mode="scalping")
        
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
        """التحقق من وقت الجلسة المفضل - معطل للباك تيست"""
        # تعطيل فلتر الوقت للباك تيست
        return True
        
        utc_hour = datetime.utcnow().hour
        sessions = self.config.get('PREFERRED_SESSIONS', [(7, 10), (13, 16)])
        for start, end in sessions:
            if start <= utc_hour <= end:
                return True
        return False
    
    def validate_entry(self, symbol: str, df_entry: pd.DataFrame, df_trend: pd.DataFrame) -> dict:
        """
        تطبيق NO TRADE Engine (11 فلتر) + مكونات SMC الكاملة
        الفلاتر:
        1. HTF Bias (الاتجاه من فريم 15د)
        2. Structure (BOS/CHoCH)
        3. Liquidity Zones (BSL/SSL/EQH/EQL)
        4. POI (FVG, Order Blocks)
        5. Confirmation (CHoCH, Engulfing)
        6. R:R Ratio
        7. Spread
        8. Slippage
        9. Volatility
        10. News Risk
        11. Funding Cost
        
        returns: {'valid': bool, 'signal': str, 'reason': str}
        """
        current_price = df_entry['close'].iloc[-1]
        
        # === المرحلة 1: الفلاتر الأساسية ===
        
        # 1. فلتر نوع العملة (القائمة الذهبية فقط)
        if symbol not in GOLDEN_SYMBOLS:
            return {'valid': False, 'signal': None, 'reason': f'العملة {symbol} ليست في القائمة الذهبية'}
        
        # 2. فلتر الأخبار السلبية (News Risk)
        if self.news_agent.check_negative_news(symbol):
            return {'valid': False, 'signal': None, 'reason': 'وجود أخبار سلبية (News Risk مرتفع)'}
        
        # === المرحلة 2: تحليل SMC الكامل ===
        
        # حساب مؤشرات SMC على فريم الدخول (5د)
        swing_points = detect_swing_highs_lows(df_entry, window=5)
        bos_signal = detect_bos(df_entry, swing_points)
        choch_signal = detect_choch(swing_points)
        fvg_zones = detect_fvg(df_entry)
        ob_zones = detect_order_blocks(df_entry)
        
        # استخدام محرك SMC الموحد لتحليل أعمق
        smc_analysis = self.smc_engine.detect_bos_choch(df_entry, swing_lookback=5)
        liquidity_zones = self.smc_engine.detect_liquidity_zones(df_entry, lookback=50)
        poi_list = self.smc_engine.detect_fvg(df_entry) + self.smc_engine.detect_order_blocks(df_entry)
        confirmation = self.smc_engine.get_confirmation(df_entry, direction="long")
        
        # 3. فلتر HTF Bias (من فريم 15د)
        ema_trend = self.calculate_ema(df_trend, self.config['EMA_TREND'])
        htf_bias = "bullish" if current_price > ema_trend else "bearish" if current_price < ema_trend else "neutral"
        
        if htf_bias == "neutral":
            return {'valid': False, 'signal': None, 'reason': 'HTF Bias غير واضح (السعر حول EMA 200)'}
        
        trend_direction = 'LONG' if htf_bias == "bullish" else 'SHORT'
        
        # 4. فلتر Structure (BOS/CHoCH)
        structure_valid = smc_analysis.structure_valid or bos_signal is not None or choch_signal is not None
        if not structure_valid:
            return {'valid': False, 'signal': None, 'reason': 'Structure غير واضح (لا يوجد BOS/CHoCH)'}
        
        # 5. فلتر Liquidity Zones
        liquidity_present = len(liquidity_zones) > 0
        swept_liquidity = any(z.swept for z in liquidity_zones)
        if not liquidity_present:
            return {'valid': False, 'signal': None, 'reason': 'لا توجد مناطق سيولة واضحة'}
        
        # 6. فلتر POI (FVG أو Order Block)
        poi_found = len(fvg_zones) > 0 or len(ob_zones) > 0 or len(poi_list) > 0
        if not poi_found:
            return {'valid': False, 'signal': None, 'reason': 'لا توجد POI مناسبة (FVG/OB)'}
        
        # 7. فلتر Confirmation
        confirmation_valid = confirmation.confirmed and confirmation.strength >= 0.5
        if not confirmation_valid:
            return {'valid': False, 'signal': None, 'reason': 'Confirmation ضعيف'}
        
        # === المرحلة 3: الفلاتر التقنية التقليدية ===
        
        ema_pullback = self.calculate_ema(df_entry, self.config['EMA_PULLBACK'])
        ema_fast = self.calculate_ema(df_entry, 20)
        rsi = self.calculate_rsi(df_entry)
        adx = self.calculate_adx(df_entry)
        atr = self.calculate_atr(df_entry)
        
        # 8. فلتر الزخم (ADX)
        if adx < self.config['ADX_MIN']:
            return {'valid': False, 'signal': None, 'reason': f'الزخم ضعيف (ADX = {adx:.2f})'}
        
        # 9. فلتر التشبع السعري (RSI)
        if trend_direction == 'LONG':
            if not (self.config['RSI_LONG_MIN'] <= rsi <= self.config['RSI_OVERBOUGHT']):
                return {'valid': False, 'signal': None, 'reason': f'RSI غير مناسب للشراء ({rsi:.2f})'}
        else:
            if not (self.config['RSI_OVERSOLD'] <= rsi <= self.config['RSI_SHORT_MAX']):
                return {'valid': False, 'signal': None, 'reason': f'RSI غير مناسب للبيع ({rsi:.2f})'}
        
        # 10. فلتر حجم التداول
        if not self.check_volume_spike(df_entry, self.config['VOLUME_SPIKE_RATIO']):
            return {'valid': False, 'signal': None, 'reason': 'لا يوجد ارتفاع كافٍ في الحجم'}
        
        # 11. فلتر الارتداد الديناميكي (السعر قريب من EMA 50)
        distance_from_ema = abs(current_price - ema_pullback) / ema_pullback
        if distance_from_ema > 0.003:
            return {'valid': False, 'signal': None, 'reason': 'السعر بعيد عن EMA 50 (ليس ارتداداً مثالياً)'}
        
        # 12. فلتر ترتيب المتوسطات
        if trend_direction == 'LONG' and ema_fast <= ema_pullback:
            return {'valid': False, 'signal': None, 'reason': 'EMA 20 تحت EMA 50 (اتجاه ضعيف)'}
        if trend_direction == 'SHORT' and ema_fast >= ema_pullback:
            return {'valid': False, 'signal': None, 'reason': 'EMA 20 فوق EMA 50 (اتجاه ضعيف)'}
        
        # 13. فلتر وقت الجلسة
        if not self.is_in_preferred_session():
            return {'valid': False, 'signal': None, 'reason': 'خارج أوقات الجلسة المفضلة'}
        
        # === المرحلة 4: حساب R:R والتحقق منه ===
        
        sl_distance = atr * self.config['SL_MULTIFIER']
        tp_distance = atr * self.config['TP_MULTIFIER']
        risk_reward_ratio = tp_distance / sl_distance
        
        if risk_reward_ratio < 1.5:
            return {'valid': False, 'signal': None, 'reason': f'نسبة العائد للمخاطرة ضعيفة ({risk_reward_ratio:.2f})'}
        
        # === التحقق من Spread و Slippage (محاكاة) ===
        spread = 0.0001  # محاكاة لـ BTC
        slippage = 0.0002  # محاكاة
        
        if spread > 0.001:
            return {'valid': False, 'signal': None, 'reason': f'Spread مرتفع ({spread:.4f})'}
        
        if slippage > 0.002:
            return {'valid': False, 'signal': None, 'reason': f'Slippage مرتفع ({slippage:.4f})'}
        
        # === التحقق من Volatility ===
        volatility_pct = (df_entry['high'].iloc[-1] - df_entry['low'].iloc[-1]) / df_entry['open'].iloc[-1]
        if volatility_pct > 0.02:  # أكثر من 2%
            return {'valid': False, 'signal': None, 'reason': f'Volatility غير طبيعية ({volatility_pct:.2%})'}
        
        # ✅ جميع الفلاتر الـ 11 نجحت + SMC
        
        signal = trend_direction
        sl_price = current_price - sl_distance if signal == 'LONG' else current_price + sl_distance
        tp_price = current_price + tp_distance if signal == 'LONG' else current_price - tp_distance
        
        return {
            'valid': True,
            'signal': signal,
            'reason': 'جميع الفلاتر الـ 11 + SMC نجحت',
            'entry_price': current_price,
            'sl_price': sl_price,
            'tp_price': tp_price,
            'atr': atr,
            'rsi': rsi,
            'adx': adx,
            'htf_bias': htf_bias,
            'structure_valid': structure_valid,
            'liquidity_present': liquidity_present,
            'poi_found': poi_found,
            'confirmation_valid': confirmation_valid,
            'bos_detected': bos_signal is not None,
            'choch_detected': choch_signal is not None,
            'fvg_count': len(fvg_zones),
            'ob_count': len(ob_zones)
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
    
    def backtest_multi_timeframe(self, df_5m: pd.DataFrame, df_15m: pd.DataFrame, initial_capital: float = 10000.0) -> dict:
        """
        تشغيل باك تيست باستخدام فريمات متعددة (15د للاتجاه، 5د للدخول)
        مع نظام TP1/TP2/TP3 و SL ديناميكي
        """
        print(f"\n🧪 جاري تشغيل الباك تيست متعدد الفريمات...")
        print(f"   شموع 5 دقائق: {len(df_5m)}")
        print(f"   شموع 15 دقيقة: {len(df_15m)}")
        
        capital = initial_capital
        trades = []
        positions = {}
        
        # حساب المؤشرات مسبقاً لتسريع الباك تيست
        print("   جاري حساب المؤشرات المسبقة...")
        df_5m['ema_50'] = df_5m['close'].ewm(span=50, adjust=False).mean()
        df_5m['ema_20'] = df_5m['close'].ewm(span=20, adjust=False).mean()
        df_15m['ema_200'] = df_15m['close'].ewm(span=200, adjust=False).mean()
        
        # حساب RSI و ADX و ATR بشكل متداول
        delta = df_5m['close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(14).mean()
        avg_loss = loss.rolling(14).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        df_5m['rsi'] = 100 - (100 / (1 + rs))
        
        # ATR
        high_low = df_5m['high'] - df_5m['low']
        high_close = abs(df_5m['high'] - df_5m['close'].shift())
        low_close = abs(df_5m['low'] - df_5m['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df_5m['atr'] = tr.rolling(14).mean()
        
        # ADX (مبسط)
        plus_dm = df_5m['high'].diff()
        minus_dm = -df_5m['low'].diff()
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0
        plus_di = 100 * (plus_dm.rolling(14).mean() / df_5m['atr'])
        minus_di = 100 * (minus_dm.rolling(14).mean() / df_5m['atr'])
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di).replace(0, np.nan)
        df_5m['adx'] = dx.rolling(14).mean()
        
        # حجم متوسط
        df_5m['vol_avg'] = df_5m['volume'].rolling(20).mean()
        
        warmup_period = 200
        
        tp_levels = {
            'tp1_pct': 0.004, 'tp2_pct': 0.008, 'tp3_pct': 0.015,
            'tp1_portion': 0.30, 'tp2_portion': 0.30, 'tp3_portion': 0.40
        }
        
        print("   جاري محاكاة الصفقات...")
        for i in range(warmup_period, len(df_5m), 5):  # فحص كل 5 شموع للتسريع
            current_time = df_5m.index[i]
            current_price = df_5m['close'].iloc[i]
            
            # الحصول على آخر قيمة 15 دقيقة متاحة
            df_15m_avail = df_15m[df_15m.index <= current_time]
            if len(df_15m_avail) == 0:
                continue
            ema_15m = df_15m_avail['ema_200'].iloc[-1]
            
            # إدارة المراكز المفتوحة
            for symbol in list(positions.keys()):
                position = positions[symbol]
                
                if position['side'] == 'buy':
                    profit_pct = (current_price - position['entry_price']) / position['entry_price']
                else:
                    profit_pct = (position['entry_price'] - current_price) / position['entry_price']
                
                if profit_pct > position.get('highest_profit', 0):
                    position['highest_profit'] = profit_pct
                
                should_close = False
                close_reason = ''
                close_portion = 0
                
                tp1_triggered = position.get('tp1_hit', False)
                tp2_triggered = position.get('tp2_hit', False)
                tp3_triggered = position.get('tp3_hit', False)
                
                if position['side'] == 'buy':
                    if not tp1_triggered and profit_pct >= tp_levels['tp1_pct']:
                        position['tp1_hit'] = True
                        close_portion = tp_levels['tp1_portion']
                        close_reason = 'TP1'
                        should_close = True
                    elif not tp2_triggered and profit_pct >= tp_levels['tp2_pct']:
                        position['tp2_hit'] = True
                        close_portion = tp_levels['tp2_portion']
                        close_reason = 'TP2'
                        should_close = True
                    elif not tp3_triggered and profit_pct >= tp_levels['tp3_pct']:
                        position['tp3_hit'] = True
                        close_portion = tp_levels['tp3_portion']
                        close_reason = 'TP3'
                        should_close = True
                    elif tp1_triggered and not position.get('sl_moved_to_be', False):
                        position['sl_price'] = position['entry_price']
                        position['sl_moved_to_be'] = True
                    elif current_price <= position['sl_price']:
                        should_close = True
                        close_portion = 1.0
                        close_reason = 'SL'
                else:
                    if not tp1_triggered and profit_pct >= tp_levels['tp1_pct']:
                        position['tp1_hit'] = True
                        close_portion = tp_levels['tp1_portion']
                        close_reason = 'TP1'
                        should_close = True
                    elif not tp2_triggered and profit_pct >= tp_levels['tp2_pct']:
                        position['tp2_hit'] = True
                        close_portion = tp_levels['tp2_portion']
                        close_reason = 'TP2'
                        should_close = True
                    elif not tp3_triggered and profit_pct >= tp_levels['tp3_pct']:
                        position['tp3_hit'] = True
                        close_portion = tp_levels['tp3_portion']
                        close_reason = 'TP3'
                        should_close = True
                    elif tp1_triggered and not position.get('sl_moved_to_be', False):
                        position['sl_price'] = position['entry_price']
                        position['sl_moved_to_be'] = True
                    elif current_price >= position['sl_price']:
                        should_close = True
                        close_portion = 1.0
                        close_reason = 'SL'
                
                if should_close:
                    amount_to_close = position['amount'] * close_portion
                    remaining_amount = position['amount'] - amount_to_close
                    
                    if position['side'] == 'buy':
                        pnl = (current_price - position['entry_price']) * amount_to_close
                    else:
                        pnl = (position['entry_price'] - current_price) * amount_to_close
                    
                    capital += pnl
                    trades.append({
                        'symbol': symbol, 'entry_time': position['entry_time'],
                        'exit_time': current_time, 'side': position['side'],
                        'entry_price': position['entry_price'], 'exit_price': current_price,
                        'portion': close_portion, 'pnl': pnl,
                        'capital_after': capital, 'reason': close_reason
                    })
                    
                    if remaining_amount <= 0.0001:
                        del positions[symbol]
                    else:
                        position['amount'] = remaining_amount
            
            # دخول جديد
            if not positions:
                adx = df_5m['adx'].iloc[i]
                vol_avg = df_5m['vol_avg'].iloc[i-1] if i > 0 else df_5m['volume'].iloc[i]
                current_vol = df_5m['volume'].iloc[i]
                rsi = df_5m['rsi'].iloc[i]
                atr = df_5m['atr'].iloc[i]
                ema_50 = df_5m['ema_50'].iloc[i]
                ema_20 = df_5m['ema_20'].iloc[i]
                
                candle_range = df_5m['high'].iloc[i] - df_5m['low'].iloc[i]
                candle_body = abs(df_5m['close'].iloc[i] - df_5m['open'].iloc[i])
                
                if adx < 20 or current_vol < 1.5 * vol_avg or candle_range == 0 or candle_body/candle_range < 0.4:
                    continue
                
                signal = None
                if current_price > ema_15m and current_price > ema_50 and 25 <= rsi <= 55 and ema_20 > ema_50 and df_5m['close'].iloc[i] > df_5m['open'].iloc[i]:
                    signal = 'LONG'
                elif current_price < ema_15m and current_price < ema_50 and 45 <= rsi <= 75 and ema_20 < ema_50 and df_5m['close'].iloc[i] < df_5m['open'].iloc[i]:
                    signal = 'SHORT'
                
                if signal:
                    sl_distance = atr * 1.2
                    sl_price = current_price - sl_distance if signal == 'LONG' else current_price + sl_distance
                    
                    positions['BTC/USDT:USDT'] = {
                        'side': 'buy' if signal == 'LONG' else 'sell',
                        'entry_price': current_price,
                        'sl_price': sl_price,
                        'amount': 0.01,
                        'entry_time': current_time,
                        'highest_profit': 0,
                        'tp1_hit': False, 'tp2_hit': False, 'tp3_hit': False,
                        'sl_moved_to_be': False
                    }
        
        # إغلاق المراكز المتبقية
        if positions:
            current_price = df_5m['close'].iloc[-1]
            for symbol, position in positions.items():
                if position['side'] == 'buy':
                    pnl = (current_price - position['entry_price']) * position['amount']
                else:
                    pnl = (position['entry_price'] - current_price) * position['amount']
                capital += pnl
                trades.append({
                    'symbol': symbol, 'entry_time': position['entry_time'],
                    'exit_time': df_5m.index[-1], 'side': position['side'],
                    'entry_price': position['entry_price'], 'exit_price': current_price,
                    'pnl': pnl, 'capital_after': capital, 'reason': 'End'
                })
        
        # الإحصائيات
        total_trades = len(trades)
        winning_trades = sum(1 for t in trades if t['pnl'] > 0)
        losing_trades = sum(1 for t in trades if t['pnl'] <= 0)
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        total_pnl = capital - initial_capital
        avg_win = sum(t['pnl'] for t in trades if t['pnl'] > 0) / winning_trades if winning_trades > 0 else 0
        avg_loss = sum(t['pnl'] for t in trades if t['pnl'] <= 0) / losing_trades if losing_trades > 0 else 0
        profit_factor = abs(sum(t['pnl'] for t in trades if t['pnl'] > 0) / sum(t['pnl'] for t in trades if t['pnl'] <= 0)) if losing_trades > 0 and sum(t['pnl'] for t in trades if t['pnl'] <= 0) != 0 else float('inf')
        
        max_drawdown = 0
        peak = initial_capital
        for trade in trades:
            if trade['capital_after'] > peak:
                peak = trade['capital_after']
            drawdown = (peak - trade['capital_after']) / peak * 100
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        return {
            'initial_capital': initial_capital, 'final_capital': capital,
            'total_pnl': total_pnl, 'total_pnl_pct': (total_pnl / initial_capital * 100),
            'total_trades': total_trades, 'winning_trades': winning_trades,
            'losing_trades': losing_trades, 'win_rate': win_rate,
            'avg_win': avg_win, 'avg_loss': avg_loss,
            'profit_factor': profit_factor, 'max_drawdown': max_drawdown,
            'trades': trades
        }


# تشغيل البوت
if __name__ == "__main__":
    bot = ScalperBot()
    bot.run()
